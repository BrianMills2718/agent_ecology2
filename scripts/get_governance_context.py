#!/usr/bin/env python3
"""Get documentation graph context for a file from relationships.yaml.

Usage:
    python scripts/get_governance_context.py <file_path>
    python scripts/get_governance_context.py <file_path> --full  # Full JSON output

Outputs JSON string with context, or nothing if file has no relationships.

Example output:
    "This file is governed by ADR-0001 (Everything is an artifact). Related docs: resources.md, GLOSSARY.md. Context: All balance mutations go through here."
"""

import fnmatch
import json
import sys
from pathlib import Path

import yaml


def match_glob(pattern: str, path: str) -> bool:
    """Check if path matches a glob pattern."""
    # Handle ** patterns
    if "**" in pattern:
        # Convert to regex-like matching
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
            path, pattern.replace("**", "*")
        )
    return fnmatch.fnmatch(path, pattern)


def get_full_context(file_path: str) -> dict | None:
    """Get full documentation graph context for a file.

    Args:
        file_path: Path to the file (relative to repo root).

    Returns:
        Dict with adrs, docs, and context, or None if no relationships.
    """
    relationships_path = Path("scripts/relationships.yaml")
    if not relationships_path.exists():
        return None

    with open(relationships_path) as f:
        data = yaml.safe_load(f) or {}

    result: dict = {"adrs": [], "docs": [], "context": None}
    adr_defs = data.get("adrs", {})

    # Check governance entries (ADR → Code)
    for entry in data.get("governance", []):
        if entry.get("source") == file_path:
            for adr_num in entry.get("adrs", []):
                adr_info = adr_defs.get(adr_num, {})
                result["adrs"].append(
                    {"num": adr_num, "title": adr_info.get("title", "Unknown")}
                )
            if entry.get("context"):
                result["context"] = entry["context"].strip()

    # Check couplings (Code → Doc)
    for coupling in data.get("couplings", []):
        sources = coupling.get("sources", [])
        for source_pattern in sources:
            if match_glob(source_pattern, file_path) or source_pattern == file_path:
                for doc in coupling.get("docs", []):
                    doc_name = Path(doc).name
                    if doc_name not in [d["name"] for d in result["docs"]]:
                        result["docs"].append(
                            {
                                "path": doc,
                                "name": doc_name,
                                "description": coupling.get("description", ""),
                                "soft": coupling.get("soft", False),
                            }
                        )
                break

    # Check target_current_links (Target ↔ Current architecture)
    result["target_link"] = None
    for link in data.get("target_current_links", []):
        if link.get("current") == file_path:
            result["target_link"] = {
                "path": link["target"],
                "direction": "target",
                "description": link.get("description", ""),
            }
            break
        elif link.get("target") == file_path:
            result["target_link"] = {
                "path": link["current"],
                "direction": "current",
                "description": link.get("description", ""),
            }
            break

    if not result["adrs"] and not result["docs"] and not result["target_link"]:
        return None

    return result


def format_context(ctx: dict) -> str:
    """Format context dict into a readable string."""
    parts = []

    if ctx["adrs"]:
        adr_strs = [f"ADR-{a['num']:04d} ({a['title']})" for a in ctx["adrs"]]
        parts.append(f"This file is governed by {', '.join(adr_strs)}.")

    if ctx["docs"]:
        # Show strict docs first, then soft
        strict_docs = [d["name"] for d in ctx["docs"] if not d.get("soft")]
        soft_docs = [d["name"] for d in ctx["docs"] if d.get("soft")]

        if strict_docs:
            parts.append(f"Related docs (update required): {', '.join(strict_docs)}.")
        if soft_docs:
            parts.append(f"Related docs (advisory): {', '.join(soft_docs)}.")

    if ctx["context"]:
        parts.append(f"Governance context: {ctx['context']}")

    if ctx.get("target_link"):
        link = ctx["target_link"]
        if link["direction"] == "target":
            parts.append(f"Target vision: {link['path']}")
        else:
            parts.append(f"Current implementation: {link['path']}")

    return " ".join(parts)


def get_governance_context(file_path: str) -> str | None:
    """Get governance context for a file (backwards compatible).

    Args:
        file_path: Path to the file (relative to repo root).

    Returns:
        Formatted context string, or None if file has no relationships.
    """
    ctx = get_full_context(file_path)
    if ctx is None:
        return None
    return format_context(ctx)


def main() -> int:
    if len(sys.argv) < 2:
        return 1

    file_path = sys.argv[1]
    full_mode = "--full" in sys.argv

    if full_mode:
        ctx = get_full_context(file_path)
        if ctx:
            print(json.dumps(ctx, indent=2))
    else:
        context = get_governance_context(file_path)
        if context:
            # Output as JSON string (properly escaped)
            print(json.dumps(context))

    return 0


if __name__ == "__main__":
    sys.exit(main())
