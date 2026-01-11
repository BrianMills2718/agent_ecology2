#!/usr/bin/env python3
"""
Concatenate target architecture documentation for external review.

Creates a single file with all relevant docs in optimal reading order.
"""

import os
from pathlib import Path
from datetime import datetime

# Optimal reading order for external review
READING_ORDER = [
    ("01", "README.md", "Project Overview"),
    ("02", "docs/architecture/target/README.md", "Target Architecture Overview"),
    ("03", "docs/architecture/target/execution_model.md", "Execution Model"),
    ("04", "docs/architecture/target/resources.md", "Resource Model"),
    ("05", "docs/architecture/target/agents.md", "Agent Model"),
    ("06", "docs/architecture/target/contracts.md", "Contract System"),
    ("07", "docs/architecture/target/oracle.md", "Oracle and Minting"),
    ("08", "docs/architecture/target/infrastructure.md", "Infrastructure"),
    ("09", "docs/DESIGN_CLARIFICATIONS.md", "Design Decisions and Rationale"),
    ("10", "docs/architecture/GAPS.md", "Implementation Gaps"),
]


def main() -> None:
    project_root = Path(__file__).parent.parent
    output_path = project_root / "docs" / "EXTERNAL_REVIEW_PACKAGE.md"

    lines: list[str] = []

    # Header
    lines.append("# Agent Ecology - External Review Package")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("This document concatenates all target architecture documentation ")
    lines.append("in recommended reading order for external review.")
    lines.append("")

    # Table of contents
    lines.append("## Table of Contents")
    lines.append("")
    for prefix, filepath, title in READING_ORDER:
        anchor = f"{prefix.lower()}-{title.lower().replace(' ', '-').replace('/', '-')}"
        lines.append(f"{prefix}. [{title}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Concatenate each document
    for prefix, filepath, title in READING_ORDER:
        full_path = project_root / filepath

        if not full_path.exists():
            lines.append(f"## {prefix}. {title}")
            lines.append("")
            lines.append(f"**FILE NOT FOUND: {filepath}**")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        content = full_path.read_text()

        # Add section header
        lines.append(f"## {prefix}. {title}")
        lines.append("")
        lines.append(f"*Source: `{filepath}`*")
        lines.append("")

        # Add content (skip the first H1 if it exists to avoid duplicate headers)
        content_lines = content.split('\n')
        skip_first_h1 = False
        for line in content_lines:
            if not skip_first_h1 and line.startswith('# '):
                skip_first_h1 = True
                continue
            lines.append(line)

        lines.append("")
        lines.append("---")
        lines.append("")

    # Write output
    output_path.write_text('\n'.join(lines))
    print(f"Created: {output_path}")
    print(f"Total documents: {len(READING_ORDER)}")


if __name__ == "__main__":
    main()
