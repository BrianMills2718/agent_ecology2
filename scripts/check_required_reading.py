#!/usr/bin/env python3
"""Check whether required documentation has been read before editing a file.

Looks up the target file in relationships.yaml to find:
1. Coupled docs (from couplings section) — must be read before editing
2. Governing ADRs (from governance section) — key constraints to confirm

Checks a session reads file to see what's been read.

Usage:
    python scripts/check_required_reading.py src/world/contracts.py
    python scripts/check_required_reading.py src/world/contracts.py --reads-file /tmp/.claude_reads
    python scripts/check_required_reading.py src/world/contracts.py --json
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_relationships(repo_root: Path) -> dict:  # type: ignore[type-arg]
    """Load relationships.yaml."""
    rel_path = repo_root / "scripts" / "relationships.yaml"
    if not rel_path.exists():
        return {}
    with open(rel_path) as f:
        return yaml.safe_load(f) or {}


def get_required_reading(
    rel_path: str, relationships: dict  # type: ignore[type-arg]
) -> dict:  # type: ignore[type-arg]
    """Get required reading for a file from relationships.yaml.

    Returns:
        {
            "coupled_docs": [{"path": "docs/...", "description": "..."}],
            "governance": {"adrs": [...], "context": "..."},
        }
    """
    result: dict = {"coupled_docs": [], "governance": None}  # type: ignore[type-arg]

    # Find coupled docs
    for coupling in relationships.get("couplings", []):
        sources = coupling.get("sources", [])
        # Check if our file matches any source pattern
        for source in sources:
            if _matches(rel_path, source):
                for doc in coupling.get("docs", []):
                    entry = {
                        "path": doc,
                        "description": coupling.get("description", ""),
                        "soft": coupling.get("soft", False),
                    }
                    if entry not in result["coupled_docs"]:
                        result["coupled_docs"].append(entry)

    # Find governance (ADRs)
    adrs_info = relationships.get("adrs", {})
    for gov in relationships.get("governance", []):
        if gov.get("source") == rel_path:
            adr_details = []
            for adr_num in gov.get("adrs", []):
                adr_info = adrs_info.get(adr_num, {})
                adr_details.append(
                    {
                        "number": adr_num,
                        "title": adr_info.get("title", "Unknown"),
                        "file": f"docs/adr/{adr_info.get('file', '')}",
                    }
                )
            result["governance"] = {
                "adrs": adr_details,
                "context": gov.get("context", "").strip(),
            }
            break

    return result


def get_session_reads(reads_file: Path) -> set[str]:
    """Get set of file paths that have been read this session."""
    if not reads_file.exists():
        return set()
    content = reads_file.read_text()
    return {line.strip() for line in content.splitlines() if line.strip()}


def _matches(file_path: str, pattern: str) -> bool:
    """Check if file matches a source pattern (supports glob-like **)."""
    if "**" in pattern:
        prefix = pattern.split("**")[0]
        return file_path.startswith(prefix)
    if "*" in pattern:
        prefix = pattern.split("*")[0]
        return file_path.startswith(prefix)
    return file_path == pattern


def format_gate_message(
    file_path: str,
    required: dict,  # type: ignore[type-arg]
    reads: set[str],
    repo_root: Path,
) -> str:
    """Format a structured gate message for the edit hook."""
    lines = []

    # Required docs
    missing_docs = []
    read_docs = []
    for doc in required["coupled_docs"]:
        doc_path = doc["path"]
        # Check if doc or any file starting with doc path was read
        was_read = any(r == doc_path or r.startswith(doc_path) for r in reads)
        if was_read:
            read_docs.append(doc)
        elif not doc.get("soft", False):
            missing_docs.append(doc)

    if missing_docs:
        lines.append(f"BLOCKED: Required reading not complete for {file_path}")
        lines.append("")
        lines.append("Before editing this file, you MUST read:")
        for doc in missing_docs:
            lines.append(f"  - {doc['path']} — {doc['description']}")
        lines.append("")

    if read_docs:
        lines.append("Already read:")
        for doc in read_docs:
            lines.append(f"  ✓ {doc['path']}")
        lines.append("")

    # Governance constraints — directive format that forces active engagement
    gov = required.get("governance")
    if gov and gov.get("adrs"):
        adr_nums = ", ".join(
            f"ADR-{a['number']:04d}" for a in gov["adrs"]
        )
        lines.append(
            f"CONSTRAINT CHECK for {file_path} (governed by {adr_nums}):"
        )
        lines.append("")
        lines.append(
            "You MUST explicitly address each constraint in your response:"
        )
        lines.append("")
        if gov.get("context"):
            for i, ctx_line in enumerate(
                gov["context"].splitlines(), 1
            ):
                ctx_line = ctx_line.strip()
                if ctx_line:
                    lines.append(f"  {i}. \"{ctx_line}\"")
                    lines.append(
                        f"     → How does your edit relate to this?"
                    )
                    lines.append("")
        lines.append(
            "State how each constraint is respected by this edit. "
            "If a constraint is irrelevant to this specific change, "
            "say so explicitly."
        )
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check required reading before editing a file"
    )
    parser.add_argument("file_path", help="File being edited (relative to repo root)")
    parser.add_argument(
        "--reads-file",
        default="/tmp/.claude_session_reads",
        help="Path to session reads tracking file",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    repo_root = Path.cwd()
    relationships = load_relationships(repo_root)
    if not relationships:
        # No relationships.yaml — nothing to check
        sys.exit(0)

    required = get_required_reading(args.file_path, relationships)
    reads = get_session_reads(Path(args.reads_file))

    if args.json:
        output = {
            "file": args.file_path,
            "required": required,
            "session_reads": sorted(reads),
            "missing_docs": [
                doc["path"]
                for doc in required["coupled_docs"]
                if not doc.get("soft", False)
                and not any(
                    r == doc["path"] or r.startswith(doc["path"]) for r in reads
                )
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        msg = format_gate_message(args.file_path, required, reads, repo_root)
        if msg.startswith("BLOCKED"):
            print(msg)
            sys.exit(1)
        else:
            # All reading done — show constraints as advisory
            print(msg)

    sys.exit(0)


if __name__ == "__main__":
    main()
