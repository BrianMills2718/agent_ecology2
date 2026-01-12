#!/usr/bin/env python3
"""Sync and verify plan status across all locations.

Usage:
    # Check for inconsistencies
    python scripts/sync_plan_status.py --check

    # Sync index to match plan files (plan files are source of truth)
    python scripts/sync_plan_status.py --sync

    # Show all plan statuses
    python scripts/sync_plan_status.py --list

Status is tracked in two places:
1. Individual plan files (docs/plans/NN_*.md) - SOURCE OF TRUTH
2. Index table in docs/plans/CLAUDE.md

This script ensures they stay in sync.
"""

import argparse
import re
import sys
from pathlib import Path


PLANS_DIR = Path("docs/plans_archived")
INDEX_FILE = PLANS_DIR / "CLAUDE.md"

# Status emoji mapping
STATUS_MAP = {
    "📋": "Planned",
    "🚧": "In Progress",
    "⏸️": "Blocked",
    "❌": "Needs Plan",
    "✅": "Complete",
}

REVERSE_STATUS_MAP = {v: k for k, v in STATUS_MAP.items()}


def parse_plan_status(plan_path: Path) -> dict | None:
    """Parse status from a plan file."""
    if not plan_path.exists():
        return None

    content = plan_path.read_text()

    # Extract plan number from filename
    match = re.match(r"(\d+)_", plan_path.name)
    if not match:
        return None

    plan_num = int(match.group(1))

    # Extract status line
    status_match = re.search(r"\*\*Status:\*\*\s*(.+?)(?:\n|$)", content)
    if not status_match:
        return None

    status_text = status_match.group(1).strip()

    # Determine status emoji
    status_emoji = None
    for emoji, name in STATUS_MAP.items():
        if emoji in status_text or name.lower() in status_text.lower():
            status_emoji = emoji
            break

    # Extract title from first heading
    title_match = re.search(r"^#\s*(?:Gap\s*\d+[:\s]*)?(.+?)(?:\n|$)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else plan_path.stem

    return {
        "number": plan_num,
        "file": plan_path.name,
        "title": title,
        "status_raw": status_text,
        "status_emoji": status_emoji or "❓",
    }


def parse_index_table(index_path: Path) -> dict[int, dict]:
    """Parse the gap summary table from index file."""
    if not index_path.exists():
        return {}

    content = index_path.read_text()

    # Find the Gap Summary table
    table_match = re.search(
        r"## Gap Summary\s+\|[^\n]+\n\|[-\s|]+\n((?:\|[^\n]+\n)*)",
        content
    )

    if not table_match:
        return {}

    plans = {}
    for line in table_match.group(1).strip().split("\n"):
        if not line.strip():
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 4:
            continue

        try:
            plan_num = int(cells[0])
        except ValueError:
            continue

        # Extract status emoji
        status_cell = cells[3]
        status_emoji = None
        for emoji in STATUS_MAP.keys():
            if emoji in status_cell:
                status_emoji = emoji
                break

        plans[plan_num] = {
            "number": plan_num,
            "title_cell": cells[1],
            "priority": cells[2],
            "status_cell": status_cell,
            "status_emoji": status_emoji or "❓",
            "blocks": cells[4] if len(cells) > 4 else "",
        }

    return plans


def check_consistency() -> list[dict]:
    """Check for inconsistencies between plan files and index."""
    issues = []

    # Get all plan files
    plan_files = sorted(PLANS_DIR.glob("[0-9][0-9]_*.md"))

    # Parse each plan file
    plan_statuses = {}
    for pf in plan_files:
        status = parse_plan_status(pf)
        if status:
            plan_statuses[status["number"]] = status

    # Parse index
    index_statuses = parse_index_table(INDEX_FILE)

    # Compare
    all_nums = set(plan_statuses.keys()) | set(index_statuses.keys())

    for num in sorted(all_nums):
        plan = plan_statuses.get(num)
        index = index_statuses.get(num)

        if plan and not index:
            issues.append({
                "plan": num,
                "issue": "missing_from_index",
                "message": f"Plan #{num} exists but not in index table",
            })
        elif index and not plan:
            # This is OK - some plans may be superseded or have no file
            pass
        elif plan and index:
            if plan["status_emoji"] != index["status_emoji"]:
                issues.append({
                    "plan": num,
                    "issue": "status_mismatch",
                    "message": f"Plan #{num}: file has {plan['status_emoji']} but index has {index['status_emoji']}",
                    "file_status": plan["status_raw"],
                    "index_status": index["status_cell"],
                })

    return issues


def sync_index_to_plans() -> int:
    """Update index table to match plan file statuses."""
    if not INDEX_FILE.exists():
        print(f"Error: {INDEX_FILE} not found")
        return 1

    content = INDEX_FILE.read_text()

    # Get plan file statuses
    plan_files = sorted(PLANS_DIR.glob("[0-9][0-9]_*.md"))
    plan_statuses = {}
    for pf in plan_files:
        status = parse_plan_status(pf)
        if status:
            plan_statuses[status["number"]] = status

    # Find and update each row in the table
    def replace_status(match: re.Match) -> str:
        line = match.group(0)
        cells = [c.strip() for c in line.split("|")[1:-1]]

        try:
            plan_num = int(cells[0])
        except ValueError:
            return line

        if plan_num not in plan_statuses:
            return line

        plan = plan_statuses[plan_num]
        new_status = plan["status_emoji"]

        # Check if status already contains text after emoji
        old_status = cells[3]
        status_text = ""
        for emoji in STATUS_MAP.keys():
            if emoji in old_status:
                # Extract any text after the emoji
                parts = old_status.split(emoji, 1)
                if len(parts) > 1:
                    status_text = parts[1].strip()
                break

        # Rebuild the status cell
        if status_text:
            cells[3] = f"{new_status} {status_text}"
        else:
            cells[3] = f"{new_status} {STATUS_MAP.get(new_status, '')}"

        return "| " + " | ".join(cells) + " |"

    # Match table rows (| number | ... format)
    new_content = re.sub(
        r"^\|\s*\d+\s*\|[^\n]+$",
        replace_status,
        content,
        flags=re.MULTILINE
    )

    if new_content != content:
        INDEX_FILE.write_text(new_content)
        print("Updated index table to match plan files.")
        return 0
    else:
        print("Index already in sync.")
        return 0


def list_statuses() -> None:
    """List all plan statuses."""
    plan_files = sorted(PLANS_DIR.glob("[0-9][0-9]_*.md"))

    print("Plan Statuses:")
    print("-" * 60)

    for pf in plan_files:
        status = parse_plan_status(pf)
        if status:
            emoji = status["status_emoji"]
            num = status["number"]
            title = status["title"][:40]
            print(f"  {emoji} #{num:2} {title}")

    # Also show index-only entries
    index_statuses = parse_index_table(INDEX_FILE)
    plan_nums = {parse_plan_status(pf)["number"] for pf in plan_files if parse_plan_status(pf)}

    index_only = set(index_statuses.keys()) - plan_nums
    if index_only:
        print("\nIndex-only (no plan file):")
        for num in sorted(index_only):
            entry = index_statuses[num]
            print(f"  {entry['status_emoji']} #{num:2} {entry['title_cell'][:40]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync and verify plan status across all locations",
    )

    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check for inconsistencies (default action)",
    )
    parser.add_argument(
        "--sync", "-s",
        action="store_true",
        help="Sync index table to match plan files",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all plan statuses",
    )

    args = parser.parse_args()

    # Default to check if no action specified
    if not any([args.check, args.sync, args.list]):
        args.check = True

    if args.list:
        list_statuses()
        return 0

    if args.sync:
        return sync_index_to_plans()

    if args.check:
        issues = check_consistency()

        if not issues:
            print("All plan statuses are consistent.")
            return 0

        print("STATUS INCONSISTENCIES FOUND:")
        print("-" * 60)
        for issue in issues:
            print(f"  Plan #{issue['plan']}: {issue['message']}")
            if "file_status" in issue:
                print(f"    File:  {issue['file_status']}")
                print(f"    Index: {issue['index_status']}")

        print()
        print("To fix, run: python scripts/sync_plan_status.py --sync")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
