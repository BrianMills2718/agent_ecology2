#!/usr/bin/env python3
"""Get governance context for a file from relationships.yaml.

Usage:
    python scripts/get_governance_context.py <file_path>

Outputs JSON string with governance context, or nothing if file is not governed.

Example output:
    "This file is governed by ADR-0001 (Everything is an artifact) and ADR-0003 (Contracts can do anything). Context: Permission checks are the hot path - keep them fast."
"""

import json
import sys
from pathlib import Path

import yaml


def get_governance_context(file_path: str) -> str | None:
    """Get governance context for a file.

    Args:
        file_path: Path to the file (relative to repo root).

    Returns:
        Formatted context string, or None if file is not governed.
    """
    relationships_path = Path("scripts/relationships.yaml")
    if not relationships_path.exists():
        return None

    with open(relationships_path) as f:
        data = yaml.safe_load(f) or {}

    # Check governance entries
    for entry in data.get("governance", []):
        if entry.get("source") == file_path:
            adrs = entry.get("adrs", [])
            context = entry.get("context", "").strip()
            adr_defs = data.get("adrs", {})

            if not adrs and not context:
                return None

            # Build context string
            parts = []

            if adrs:
                adr_strs = []
                for adr_num in adrs:
                    adr_info = adr_defs.get(adr_num, {})
                    title = adr_info.get("title", "Unknown")
                    adr_strs.append(f"ADR-{adr_num:04d} ({title})")
                parts.append(f"This file is governed by {', '.join(adr_strs)}.")

            if context:
                parts.append(f"Governance context: {context}")

            return " ".join(parts)

    return None


def main() -> int:
    if len(sys.argv) < 2:
        return 1

    file_path = sys.argv[1]
    context = get_governance_context(file_path)

    if context:
        # Output as JSON string (properly escaped)
        print(json.dumps(context))

    return 0


if __name__ == "__main__":
    sys.exit(main())
