#!/usr/bin/env python3
"""Check for stale claims in the Active Work table.

Usage:
    # Check for stale claims (default: >4 hours old)
    python scripts/check_claims.py

    # Custom threshold
    python scripts/check_claims.py --hours 8

    # List all claims
    python scripts/check_claims.py --list

    # Clear a specific stale claim (interactive)
    python scripts/check_claims.py --clear
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path


def parse_claims(claude_md_path: Path) -> list[dict]:
    """Parse the Active Work table from CLAUDE.md."""
    content = claude_md_path.read_text()

    # Find Active Work table
    table_match = re.search(
        r"\*\*Active Work:\*\*.*?\n\|[^\n]+\n\|[-\s|]+\n((?:\|[^\n]+\n)*)",
        content,
        re.DOTALL
    )

    if not table_match:
        return []

    claims = []
    for line in table_match.group(1).strip().split("\n"):
        if not line.strip():
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 4 and cells[0] != "-":
            claims.append({
                "cc_id": cells[0],
                "plan": cells[1] if len(cells) > 1 else "",
                "task": cells[2] if len(cells) > 2 else "",
                "claimed": cells[3] if len(cells) > 3 else "",
                "status": cells[4] if len(cells) > 4 else "",
            })

    return claims


def parse_timestamp(ts: str) -> datetime | None:
    """Parse various timestamp formats."""
    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    return None


def check_stale_claims(claims: list[dict], hours: int) -> list[dict]:
    """Return claims older than the threshold."""
    now = datetime.now()
    threshold = timedelta(hours=hours)
    stale = []

    for claim in claims:
        ts = parse_timestamp(claim["claimed"])
        if ts and (now - ts) > threshold:
            claim["age_hours"] = (now - ts).total_seconds() / 3600
            stale.append(claim)

    return stale


def list_claims(claims: list[dict]) -> None:
    """Print all current claims."""
    if not claims:
        print("No active claims.")
        return

    print("Active Claims:")
    print("-" * 60)
    now = datetime.now()

    for claim in claims:
        ts = parse_timestamp(claim["claimed"])
        age = ""
        if ts:
            hours = (now - ts).total_seconds() / 3600
            if hours < 1:
                age = f"({int(hours * 60)}m ago)"
            else:
                age = f"({hours:.1f}h ago)"

        print(f"  {claim['cc_id']:8} | Plan {claim['plan']:4} | {claim['task'][:30]:30} | {claim['claimed']} {age}")


def clear_claim(claude_md_path: Path, cc_id: str) -> bool:
    """Remove a claim from the Active Work table."""
    content = claude_md_path.read_text()

    # Find and remove the line with this CC-ID
    pattern = rf"(\| {re.escape(cc_id)} \|[^\n]+\n)"
    match = re.search(pattern, content)

    if not match:
        print(f"No claim found for {cc_id}")
        return False

    # Replace with empty placeholder if this is the only claim
    new_content = re.sub(pattern, "", content)

    # Check if table is now empty (only has header and separator)
    table_check = re.search(
        r"\*\*Active Work:\*\*.*?\n\|[^\n]+\n\|[-\s|]+\n(\|[^\n]+\n)",
        new_content,
        re.DOTALL
    )

    if not table_check:
        # Add placeholder row
        new_content = re.sub(
            r"(\*\*Active Work:\*\*.*?\n\|[^\n]+\n\|[-\s|]+\n)",
            r"\1| - | - | - | - | - |\n",
            new_content
        )

    claude_md_path.write_text(new_content)
    print(f"Cleared claim for {cc_id}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check for stale claims in Active Work table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--hours", "-H",
        type=int,
        default=4,
        help="Hours before a claim is considered stale (default: 4)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all active claims"
    )
    parser.add_argument(
        "--clear", "-c",
        metavar="CC_ID",
        help="Clear a specific claim by CC-ID"
    )
    parser.add_argument(
        "--claude-md",
        type=Path,
        default=Path("CLAUDE.md"),
        help="Path to CLAUDE.md (default: CLAUDE.md)"
    )

    args = parser.parse_args()

    if not args.claude_md.exists():
        print(f"Error: {args.claude_md} not found")
        return 1

    claims = parse_claims(args.claude_md)

    if args.clear:
        return 0 if clear_claim(args.claude_md, args.clear) else 1

    if args.list:
        list_claims(claims)
        return 0

    # Default: check for stale claims
    stale = check_stale_claims(claims, args.hours)

    if not stale:
        print(f"No stale claims (threshold: {args.hours}h)")
        return 0

    print(f"STALE CLAIMS (>{args.hours}h old):")
    print("-" * 60)
    for claim in stale:
        print(f"  {claim['cc_id']:8} | Plan {claim['plan']:4} | {claim['age_hours']:.1f}h old")
        print(f"           Task: {claim['task']}")

    print()
    print("To clear a stale claim:")
    print(f"  python scripts/check_claims.py --clear <CC_ID>")

    return 1


if __name__ == "__main__":
    sys.exit(main())
