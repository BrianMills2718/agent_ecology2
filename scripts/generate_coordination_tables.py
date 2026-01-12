#!/usr/bin/env python3
"""Generate coordination tables for CLAUDE.md from source of truth.

Generates:
- Active Work table from .claude/active-work.yaml
- Awaiting Review table from `gh pr list`

Usage:
    python scripts/generate_coordination_tables.py          # Show what would be generated
    python scripts/generate_coordination_tables.py --check  # Exit 1 if tables differ (for CI)
    python scripts/generate_coordination_tables.py --apply  # Update CLAUDE.md in place
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


def load_active_work() -> list[dict]:
    """Load claims from .claude/active-work.yaml."""
    path = Path(".claude/active-work.yaml")
    if not path.exists():
        return []

    with open(path) as f:
        data = yaml.safe_load(f)

    return data.get("claims", []) or []


def get_open_prs() -> list[dict]:
    """Get open PRs from GitHub via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json",
             "number,title,headRefName,createdAt"],
            capture_output=True,
            text=True,
            env={"GIT_CONFIG_NOSYSTEM": "1", **dict(__import__("os").environ)},
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not fetch PRs from GitHub: {e}", file=sys.stderr)
        return []


def format_datetime(iso_str: str, include_time: bool = False) -> str:
    """Format ISO datetime string for display."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if include_time:
            return dt.strftime("%Y-%m-%dT%H:%M")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return iso_str[:10] if iso_str else "-"


def generate_active_work_table(claims: list[dict]) -> str:
    """Generate Active Work markdown table."""
    lines = [
        "**Active Work:**",
        "<!-- AUTO-GENERATED from .claude/active-work.yaml - Do not edit manually -->",
        "<!-- Run: python scripts/generate_coordination_tables.py --apply -->",
        "| CC-ID | Plan | Task | Claimed | Status |",
        "|-------|------|------|---------|--------|",
    ]

    if not claims:
        lines.append("| - | - | - | - | - |")
    else:
        for claim in claims:
            cc_id = claim.get("cc_id", "-")
            plan = claim.get("plan", "-")
            task = claim.get("task", "-")
            claimed = format_datetime(claim.get("claimed_at", ""), include_time=True)
            status = "Active"
            lines.append(f"| {cc_id} | {plan} | {task} | {claimed} | {status} |")

    return "\n".join(lines)


def generate_awaiting_review_table(prs: list[dict]) -> str:
    """Generate Awaiting Review markdown table."""
    lines = [
        "**Awaiting Review:**",
        "<!-- AUTO-GENERATED from `gh pr list` - Do not edit manually -->",
        "<!-- Run: python scripts/generate_coordination_tables.py --apply -->",
        "| PR | Branch | Title | Created |",
        "|----|--------|-------|---------|",
    ]

    if not prs:
        lines.append("| - | - | - | - |")
    else:
        # Sort by PR number
        for pr in sorted(prs, key=lambda p: p.get("number", 0)):
            number = f"#{pr.get('number', '?')}"
            branch = pr.get("headRefName", "-")
            title = pr.get("title", "-")
            created = format_datetime(pr.get("createdAt", ""))
            lines.append(f"| {number} | {branch} | {title} | {created} |")

    lines.append("")
    lines.append("**After PR merged:** Remove happens automatically on next sync.")

    return "\n".join(lines)


def extract_current_tables(content: str) -> tuple[str, str]:
    """Extract current Active Work and Awaiting Review tables from CLAUDE.md."""
    # Pattern for Active Work table (from **Active Work:** to next ** or ###)
    active_pattern = r"(\*\*Active Work:\*\*.*?)(?=\n\*\*|\n###|\n---|\Z)"
    active_match = re.search(active_pattern, content, re.DOTALL)
    active_current = active_match.group(1).strip() if active_match else ""

    # Pattern for Awaiting Review table
    review_pattern = r"(\*\*Awaiting Review:\*\*.*?)(?=\n###|\n---|\Z)"
    review_match = re.search(review_pattern, content, re.DOTALL)
    review_current = review_match.group(1).strip() if review_match else ""

    return active_current, review_current


def update_claude_md(active_table: str, review_table: str) -> str:
    """Update CLAUDE.md with new tables, return new content."""
    path = Path("CLAUDE.md")
    content = path.read_text()

    # Replace Active Work section
    active_pattern = r"\*\*Active Work:\*\*.*?(?=\n\*\*Awaiting Review:\*\*)"
    content = re.sub(active_pattern, active_table + "\n\n", content, flags=re.DOTALL)

    # Replace Awaiting Review section
    review_pattern = r"\*\*Awaiting Review:\*\*.*?\*\*After PR merged:\*\*[^\n]*"
    content = re.sub(review_pattern, review_table, content, flags=re.DOTALL)

    return content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if tables differ from generated (for CI)")
    parser.add_argument("--apply", action="store_true",
                        help="Update CLAUDE.md in place")
    args = parser.parse_args()

    # Generate tables
    claims = load_active_work()
    prs = get_open_prs()

    active_table = generate_active_work_table(claims)
    review_table = generate_awaiting_review_table(prs)

    print("=== Generated Active Work Table ===")
    print(active_table)
    print()
    print("=== Generated Awaiting Review Table ===")
    print(review_table)
    print()

    if args.check or args.apply:
        claude_md = Path("CLAUDE.md")
        if not claude_md.exists():
            print("Error: CLAUDE.md not found", file=sys.stderr)
            return 1

        content = claude_md.read_text()
        active_current, review_current = extract_current_tables(content)

        # Normalize for comparison (strip whitespace, ignore comment differences)
        def normalize(s: str) -> str:
            # Remove comment lines and normalize whitespace
            lines = [l.strip() for l in s.split("\n") if not l.strip().startswith("<!--")]
            return "\n".join(l for l in lines if l)

        active_match = normalize(active_current) == normalize(active_table)
        review_match = normalize(review_current) == normalize(review_table)

        if args.check:
            if not active_match:
                print("Active Work table is out of sync!", file=sys.stderr)
            if not review_match:
                print("Awaiting Review table is out of sync!", file=sys.stderr)

            if active_match and review_match:
                print("Tables are in sync.")
                return 0
            else:
                print("Run: python scripts/generate_coordination_tables.py --apply",
                      file=sys.stderr)
                return 1

        if args.apply:
            new_content = update_claude_md(active_table, review_table)
            claude_md.write_text(new_content)
            print(f"Updated {claude_md}")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
