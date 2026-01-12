#!/usr/bin/env python3
"""Check for stale claims and manage active work.

Usage:
    # Check for stale claims (default: >4 hours old)
    python scripts/check_claims.py

    # List all claims
    python scripts/check_claims.py --list

    # Claim work on a plan
    python scripts/check_claims.py --claim CC-1 --plan 3 --task "Implement docker isolation"

    # Release a claim
    python scripts/check_claims.py --release CC-1

    # Sync YAML to CLAUDE.md table
    python scripts/check_claims.py --sync

Primary data store: .claude/active-work.yaml
Display: CLAUDE.md Active Work table (synced from YAML)
"""

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


YAML_PATH = Path(".claude/active-work.yaml")
CLAUDE_MD_PATH = Path("CLAUDE.md")


def load_yaml() -> dict[str, Any]:
    """Load claims from YAML file."""
    if not YAML_PATH.exists():
        return {"claims": [], "completed": []}

    with open(YAML_PATH) as f:
        data = yaml.safe_load(f) or {}

    return {
        "claims": data.get("claims") or [],
        "completed": data.get("completed") or [],
    }


def save_yaml(data: dict[str, Any]) -> None:
    """Save claims to YAML file."""
    YAML_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(YAML_PATH, "w") as f:
        f.write("# Active Work Lock File\n")
        f.write("# Machine-readable tracking for multi-CC coordination.\n")
        f.write("# Use: python scripts/check_claims.py --help\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def parse_timestamp(ts: str) -> datetime | None:
    """Parse various timestamp formats."""
    if not ts:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    return None


def get_age_string(ts: datetime) -> str:
    """Get human-readable age string."""
    now = datetime.now()
    hours = (now - ts).total_seconds() / 3600

    if hours < 1:
        return f"{int(hours * 60)}m ago"
    elif hours < 24:
        return f"{hours:.1f}h ago"
    else:
        return f"{hours / 24:.1f}d ago"


def check_stale_claims(claims: list[dict], hours: int) -> list[dict]:
    """Return claims older than the threshold."""
    now = datetime.now()
    threshold = timedelta(hours=hours)
    stale = []

    for claim in claims:
        ts = parse_timestamp(claim.get("claimed_at", ""))
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
    print("-" * 70)

    for claim in claims:
        ts = parse_timestamp(claim.get("claimed_at", ""))
        age = get_age_string(ts) if ts else "unknown"

        cc_id = claim.get("cc_id", "?")
        plan = claim.get("plan", "?")
        task = claim.get("task", "")[:35]
        branch = claim.get("branch", "")

        print(f"  {cc_id:8} | Plan #{plan:<3} | {task:35} | {age}")
        if branch:
            print(f"           Branch: {branch}")
        if claim.get("files"):
            print(f"           Files: {', '.join(claim['files'][:3])}")


def add_claim(
    data: dict[str, Any],
    cc_id: str,
    plan: int,
    task: str,
    branch: str | None = None,
    files: list[str] | None = None,
) -> bool:
    """Add a new claim."""
    # Check for existing claim by this CC
    for claim in data["claims"]:
        if claim.get("cc_id") == cc_id:
            print(f"Error: {cc_id} already has an active claim on Plan #{claim.get('plan')}")
            print("Release the existing claim first with --release")
            return False

    # Check for conflicting claim on same plan
    for claim in data["claims"]:
        if claim.get("plan") == plan:
            print(f"Warning: Plan #{plan} already claimed by {claim.get('cc_id')}")
            print("Proceed with caution to avoid conflicts.")

    new_claim = {
        "cc_id": cc_id,
        "plan": plan,
        "task": task,
        "claimed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if branch:
        new_claim["branch"] = branch
    if files:
        new_claim["files"] = files

    data["claims"].append(new_claim)
    save_yaml(data)
    print(f"Claimed: {cc_id} -> Plan #{plan}: {task}")
    return True


def release_claim(data: dict[str, Any], cc_id: str, commit: str | None = None) -> bool:
    """Release a claim and move to completed."""
    claim_to_remove = None

    for claim in data["claims"]:
        if claim.get("cc_id") == cc_id:
            claim_to_remove = claim
            break

    if not claim_to_remove:
        print(f"No active claim found for {cc_id}")
        return False

    data["claims"].remove(claim_to_remove)

    # Add to completed history
    completion = {
        "cc_id": cc_id,
        "plan": claim_to_remove.get("plan"),
        "task": claim_to_remove.get("task"),
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if commit:
        completion["commit"] = commit

    data["completed"].append(completion)

    # Keep only last 20 completions
    data["completed"] = data["completed"][-20:]

    save_yaml(data)
    print(f"Released: {cc_id} (Plan #{claim_to_remove.get('plan')})")
    return True


def sync_to_claude_md(claims: list[dict]) -> bool:
    """Sync claims from YAML to CLAUDE.md Active Work table."""
    if not CLAUDE_MD_PATH.exists():
        print(f"Error: {CLAUDE_MD_PATH} not found")
        return False

    content = CLAUDE_MD_PATH.read_text()

    # Build new table rows
    if not claims:
        rows = "| - | - | - | - | - |\n"
    else:
        rows = ""
        for claim in claims:
            cc_id = claim.get("cc_id", "?")
            plan = claim.get("plan", "?")
            task = claim.get("task", "")[:40]
            claimed = claim.get("claimed_at", "")[:16]  # Truncate to minute
            status = "Active"
            rows += f"| {cc_id} | {plan} | {task} | {claimed} | {status} |\n"

    # Replace table content (everything after header row until next section)
    pattern = (
        r"(\*\*Active Work:\*\*\n"
        r"<!-- [^>]+ -->\n"
        r"\| CC-ID \| Plan \| Task \| Claimed \| Status \|\n"
        r"\|[-\s|]+\n)"
        r"(?:\|[^\n]+\n)*"
    )

    replacement = r"\1" + rows

    new_content, count = re.subn(pattern, replacement, content)

    if count == 0:
        print("Warning: Could not find Active Work table in CLAUDE.md")
        return False

    CLAUDE_MD_PATH.write_text(new_content)
    print(f"Synced {len(claims)} claim(s) to CLAUDE.md")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage active work claims for multi-CC coordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--claim",
        metavar="CC_ID",
        help="Claim work (requires --plan and --task)"
    )
    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Plan number to claim"
    )
    parser.add_argument(
        "--task", "-t",
        help="Task description"
    )
    parser.add_argument(
        "--branch", "-b",
        help="Git branch name (optional)"
    )
    parser.add_argument(
        "--release", "-r",
        metavar="CC_ID",
        help="Release a claim"
    )
    parser.add_argument(
        "--commit",
        help="Commit hash when releasing (optional)"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync YAML claims to CLAUDE.md table"
    )

    args = parser.parse_args()

    data = load_yaml()
    claims = data.get("claims", [])

    # Handle claim
    if args.claim:
        if not args.plan or not args.task:
            print("Error: --claim requires --plan and --task")
            return 1
        success = add_claim(data, args.claim, args.plan, args.task, args.branch)
        if success:
            sync_to_claude_md(data["claims"])
        return 0 if success else 1

    # Handle release
    if args.release:
        success = release_claim(data, args.release, args.commit)
        if success:
            sync_to_claude_md(data["claims"])
        return 0 if success else 1

    # Handle sync
    if args.sync:
        return 0 if sync_to_claude_md(claims) else 1

    # Handle list
    if args.list:
        list_claims(claims)
        return 0

    # Default: check for stale claims
    stale = check_stale_claims(claims, args.hours)

    if not claims:
        print("No active claims.")
        return 0

    if not stale:
        print(f"No stale claims (threshold: {args.hours}h)")
        list_claims(claims)
        return 0

    print(f"STALE CLAIMS (>{args.hours}h old):")
    print("-" * 60)
    for claim in stale:
        print(f"  {claim.get('cc_id', '?'):8} | Plan #{claim.get('plan', '?'):<3} | {claim.get('age_hours', 0):.1f}h old")
        print(f"           Task: {claim.get('task', '')}")

    print()
    print("To release a stale claim:")
    print("  python scripts/check_claims.py --release <CC_ID>")

    return 1


if __name__ == "__main__":
    sys.exit(main())
