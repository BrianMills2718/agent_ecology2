#!/usr/bin/env python3
"""Unified file context loader for the engineering workflow (Pattern #34).

Given source file paths, outputs all relevant context:
- CLAUDE.md chain (root → module → submodule)
- Governing ADRs with summaries (from relationships.yaml)
- Coupled docs (from relationships.yaml)
- Banned/deprecated terms (from GLOSSARY.md)
- CONCERNS.md and TECH_DEBT.md references
- Custom docs (from meta-process.yaml custom_docs section)

Reuses existing scripts:
- get_governance_context.py for ADR/coupling lookup
- extract_relevant_context.py for glossary/ontology matching

Usage:
    python scripts/file_context.py src/world/contracts.py
    python scripts/file_context.py src/world/contracts.py src/world/kernel_contracts.py
    python scripts/file_context.py src/world/contracts.py --json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_claude_md_chain(file_path: str) -> list[dict[str, str]]:
    """Find all CLAUDE.md files in the directory chain for a file.

    Returns list from root to most specific, each with path and first heading.
    """
    chain = []
    target = REPO_ROOT / file_path
    current = target.parent if target.is_file() else target

    # Walk from the file's directory up to repo root
    dirs_to_check = []
    while current >= REPO_ROOT:
        dirs_to_check.append(current)
        if current == REPO_ROOT:
            break
        current = current.parent

    # Reverse so we go root → specific
    for d in reversed(dirs_to_check):
        claude_md = d / "CLAUDE.md"
        if claude_md.exists():
            # Extract first heading as summary
            try:
                text = claude_md.read_text()
                first_line = ""
                for line in text.split("\n"):
                    if line.startswith("# "):
                        first_line = line.lstrip("# ").strip()
                        break
                chain.append({
                    "path": str(claude_md.relative_to(REPO_ROOT)),
                    "heading": first_line,
                })
            except Exception:
                chain.append({
                    "path": str(claude_md.relative_to(REPO_ROOT)),
                    "heading": "(unreadable)",
                })

    return chain


def get_adr_summary(adr_num: int) -> str:
    """Read an ADR file and return its first paragraph after the title."""
    adr_dir = REPO_ROOT / "docs" / "adr"
    # Try common naming patterns
    for pattern in [f"{adr_num:04d}-*.md", f"{adr_num:04d}_*.md"]:
        matches = list(adr_dir.glob(pattern))
        if matches:
            try:
                text = matches[0].read_text()
                # Skip title and metadata, find first paragraph
                lines = text.split("\n")
                in_body = False
                paragraph = []
                for line in lines:
                    if line.startswith("## Context") or line.startswith("## Decision"):
                        in_body = True
                        continue
                    if in_body:
                        if line.strip() == "" and paragraph:
                            break
                        if line.strip():
                            paragraph.append(line.strip())
                return " ".join(paragraph)[:200] if paragraph else ""
            except Exception:
                return ""
    return ""


def get_governance_info(file_path: str) -> dict:
    """Get ADRs and coupled docs from relationships.yaml."""
    rel_path = REPO_ROOT / "scripts" / "relationships.yaml"
    if not rel_path.exists():
        return {"adrs": [], "docs": [], "context": None, "banned_terms": []}

    with open(rel_path) as f:
        data = yaml.safe_load(f) or {}

    result: dict = {"adrs": [], "docs": [], "context": None, "banned_terms": []}
    adr_defs = data.get("adrs", {})

    # Check governance entries
    for entry in data.get("governance", []):
        if entry.get("source") == file_path:
            for adr_num in entry.get("adrs", []):
                adr_info = adr_defs.get(adr_num, {})
                result["adrs"].append({
                    "num": adr_num,
                    "title": adr_info.get("title", "Unknown"),
                    "summary": get_adr_summary(adr_num),
                })
            if entry.get("context"):
                result["context"] = entry["context"].strip()

    # Check couplings
    for coupling in data.get("couplings", []):
        sources = coupling.get("sources", [])
        for source_pattern in sources:
            if source_pattern == file_path or _glob_match(source_pattern, file_path):
                for doc in coupling.get("docs", []):
                    result["docs"].append({
                        "path": doc,
                        "description": coupling.get("description", ""),
                        "strict": not coupling.get("soft", False),
                    })
                break

    # Check banned terms
    banned = data.get("banned_terms", [])
    if isinstance(banned, dict):
        for term, info in banned.items():
            result["banned_terms"].append({
                "term": term,
                "reason": info if isinstance(info, str) else str(info),
            })
    elif isinstance(banned, list):
        for item in banned:
            if isinstance(item, dict):
                result["banned_terms"].append(item)

    return result


def _glob_match(pattern: str, path: str) -> bool:
    """Simple glob matching."""
    import fnmatch
    if "**" in pattern:
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
            path, pattern.replace("**", "*")
        )
    return fnmatch.fnmatch(path, pattern)


def search_file_references(doc_path: str, file_path: str) -> list[str]:
    """Search a markdown doc for references to a file or its module."""
    full_path = REPO_ROOT / doc_path
    if not full_path.exists():
        return []

    # Build search terms from file path
    parts = Path(file_path).parts
    stem = Path(file_path).stem
    search_terms = [stem, file_path]
    # Also search for the module name (e.g., "contracts" for "src/world/contracts.py")
    if len(parts) >= 2:
        search_terms.append(parts[-2])  # parent dir name

    try:
        text = full_path.read_text()
        matches = []
        for i, line in enumerate(text.split("\n"), 1):
            for term in search_terms:
                if term in line.lower():
                    matches.append(f"  L{i}: {line.strip()[:120]}")
                    break
        return matches[:5]  # Cap at 5 matches
    except Exception:
        return []


def get_custom_docs(file_path: str) -> list[dict[str, str]]:
    """Get repo-specific docs from meta-process.yaml custom_docs section."""
    config_path = REPO_ROOT / "meta-process.yaml"
    if not config_path.exists():
        return []

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    custom_docs = config.get("custom_docs", {})
    result = []

    for name, spec in custom_docs.items():
        if not isinstance(spec, dict):
            continue
        surface_when = spec.get("surface_when", [])
        doc_path = spec.get("path", "")

        for pattern in surface_when:
            if pattern == "*" or file_path.startswith(pattern):
                result.append({
                    "name": name,
                    "path": doc_path,
                })
                break

    return result


def build_context(file_path: str) -> dict:
    """Build complete context for a single file."""
    ctx: dict = {
        "file": file_path,
        "claude_md_chain": find_claude_md_chain(file_path),
        "governance": get_governance_info(file_path),
        "concerns": search_file_references("docs/CONCERNS.md", file_path),
        "tech_debt": search_file_references("docs/TECH_DEBT.md", file_path),
        "custom_docs": get_custom_docs(file_path),
    }
    return ctx


def format_context(ctx: dict) -> str:
    """Format context dict into readable text."""
    lines = []
    lines.append(f"=== Context for {ctx['file']} ===")
    lines.append("")

    # CLAUDE.md chain
    if ctx["claude_md_chain"]:
        lines.append("CLAUDE.md chain:")
        for item in ctx["claude_md_chain"]:
            lines.append(f"  {item['path']} — {item['heading']}")
        lines.append("")

    # Governing ADRs
    gov = ctx["governance"]
    if gov["adrs"]:
        lines.append("Governing ADRs:")
        for adr in gov["adrs"]:
            lines.append(f"  ADR-{adr['num']:04d}: {adr['title']}")
            if adr.get("summary"):
                lines.append(f"    {adr['summary']}")
        lines.append("")

    # Governance context
    if gov.get("context"):
        lines.append(f"Context: {gov['context']}")
        lines.append("")

    # Coupled docs
    if gov["docs"]:
        lines.append("Coupled docs:")
        for doc in gov["docs"]:
            strict = "STRICT" if doc.get("strict") else "soft"
            lines.append(f"  [{strict}] {doc['path']}")
            if doc.get("description"):
                lines.append(f"    {doc['description']}")
        lines.append("")

    # Banned terms
    if gov.get("banned_terms"):
        lines.append("Banned terms:")
        for bt in gov["banned_terms"]:
            lines.append(f"  {bt['term']}: {bt.get('reason', '')}")
        lines.append("")

    # Concerns
    if ctx["concerns"]:
        lines.append("CONCERNS.md references:")
        for ref in ctx["concerns"]:
            lines.append(ref)
        lines.append("")

    # Tech debt
    if ctx["tech_debt"]:
        lines.append("TECH_DEBT.md references:")
        for ref in ctx["tech_debt"]:
            lines.append(ref)
        lines.append("")

    # Custom docs
    if ctx["custom_docs"]:
        lines.append("Repo-specific docs to check:")
        for doc in ctx["custom_docs"]:
            lines.append(f"  {doc['name']}: {doc['path']}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load hierarchical context for source files (Pattern #34)"
    )
    parser.add_argument("files", nargs="+", help="Source file paths (relative to repo root)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    contexts = []
    for file_path in args.files:
        # Normalize path
        fp = file_path.replace(str(REPO_ROOT) + "/", "")
        ctx = build_context(fp)
        contexts.append(ctx)

    if args.json:
        print(json.dumps(contexts, indent=2))
    else:
        for ctx in contexts:
            print(format_context(ctx))

    return 0


if __name__ == "__main__":
    sys.exit(main())
