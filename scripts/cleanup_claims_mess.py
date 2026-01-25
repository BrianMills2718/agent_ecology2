#!/usr/bin/env python3
"""One-time cleanup of stale claims and orphaned state.

This script cleans up the meta-process state that has accumulated issues:
- Duplicate claims (in both claims and completed)
- Claims without worktrees
- Claims for merged branches
- Inconsistent field names
- Legacy flags

Usage:
    python scripts/cleanup_claims_mess.py --dry-run   # Show what would be cleaned
    python scripts/cleanup_claims_mess.py --apply     # Actually clean up
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ACTIVE_WORK_FILE = Path(".claude/active-work.yaml")


def load_claims() -> dict:
    """Load the active work file."""
    if not ACTIVE_WORK_FILE.exists():
        return {"claims": [], "completed": []}
    with open(ACTIVE_WORK_FILE) as f:
        return yaml.safe_load(f) or {"claims": [], "completed": []}


def save_claims(data: dict) -> None:
    """Save the active work file."""
    ACTIVE_WORK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIVE_WORK_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_merged_branches() -> set[str]:
    """Get list of branches that have been merged to main."""
    try:
        result = subprocess.run(
            ["git", "branch", "-r", "--merged", "origin/main"],
            capture_output=True,
            text=True,
            check=True,
        )
        branches = set()
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and not line.endswith("/main") and not line.endswith("/HEAD"):
                # Remove origin/ prefix
                branch = line.replace("origin/", "")
                branches.add(branch)
        return branches
    except subprocess.CalledProcessError:
        return set()


def worktree_exists(path: str) -> bool:
    """Check if worktree path exists."""
    if not path:
        return False
    return Path(path).exists()


def get_all_worktrees() -> set[str]:
    """Get all git worktree paths."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        paths = set()
        for line in result.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                paths.add(line.replace("worktree ", ""))
        return paths
    except subprocess.CalledProcessError:
        return set()


def cleanup_claims(dry_run: bool = True) -> dict:
    """Clean up claims and return summary of actions."""
    data = load_claims()
    actions = {
        "removed_duplicates": [],
        "removed_no_worktree": [],
        "removed_merged": [],
        "standardized_fields": [],
        "removed_legacy": [],
    }

    merged_branches = get_merged_branches()
    existing_worktrees = get_all_worktrees()

    # Track cc_ids we've seen in completed
    completed_ids = {c.get("cc_id") for c in data.get("completed", []) if c.get("cc_id")}

    new_claims = []
    for claim in data.get("claims", []):
        cc_id = claim.get("cc_id") or claim.get("branch")
        worktree_path = claim.get("worktree_path", "")

        # Skip if duplicate (also in completed)
        if cc_id in completed_ids:
            actions["removed_duplicates"].append(cc_id)
            continue

        # Skip if worktree doesn't exist and not in git worktree list
        if worktree_path and not worktree_exists(worktree_path):
            if worktree_path not in existing_worktrees:
                actions["removed_no_worktree"].append(f"{cc_id} ({worktree_path})")
                continue

        # Skip if branch is merged
        if cc_id in merged_branches:
            actions["removed_merged"].append(cc_id)
            continue

        # Standardize fields
        if "branch" in claim and "cc_id" not in claim:
            claim["cc_id"] = claim.pop("branch")
            actions["standardized_fields"].append(cc_id)

        # Remove legacy flag
        if "_legacy" in claim:
            del claim["_legacy"]
            actions["removed_legacy"].append(cc_id)

        new_claims.append(claim)

    # Clean up completed list (remove duplicates, old entries)
    seen_completed = set()
    new_completed = []
    for entry in data.get("completed", []):
        cc_id = entry.get("cc_id")
        if cc_id and cc_id not in seen_completed:
            seen_completed.add(cc_id)
            # Remove legacy flag
            if "_legacy" in entry:
                del entry["_legacy"]
            new_completed.append(entry)

    if not dry_run:
        data["claims"] = new_claims
        data["completed"] = new_completed
        save_claims(data)

    return actions


def print_summary(actions: dict, dry_run: bool) -> None:
    """Print summary of cleanup actions."""
    prefix = "[DRY RUN] Would " if dry_run else ""

    print(f"\n{'=' * 60}")
    print(f"{'DRY RUN - ' if dry_run else ''}Claim Cleanup Summary")
    print(f"{'=' * 60}\n")

    if actions["removed_duplicates"]:
        print(f"{prefix}remove {len(actions['removed_duplicates'])} duplicates:")
        for item in actions["removed_duplicates"]:
            print(f"  - {item}")

    if actions["removed_no_worktree"]:
        print(f"\n{prefix}remove {len(actions['removed_no_worktree'])} claims without worktrees:")
        for item in actions["removed_no_worktree"]:
            print(f"  - {item}")

    if actions["removed_merged"]:
        print(f"\n{prefix}remove {len(actions['removed_merged'])} claims for merged branches:")
        for item in actions["removed_merged"]:
            print(f"  - {item}")

    if actions["standardized_fields"]:
        print(f"\n{prefix}standardize {len(actions['standardized_fields'])} field names:")
        for item in actions["standardized_fields"]:
            print(f"  - {item}")

    if actions["removed_legacy"]:
        print(f"\n{prefix}remove legacy flags from {len(actions['removed_legacy'])} entries:")
        for item in actions["removed_legacy"]:
            print(f"  - {item}")

    total = sum(len(v) for v in actions.values())
    if total == 0:
        print("No cleanup needed - claims are clean!")
    else:
        print(f"\nTotal actions: {total}")
        if dry_run:
            print("\nRun with --apply to execute these changes.")


def main():
    parser = argparse.ArgumentParser(description="Clean up stale claims and orphaned state")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without making changes")
    parser.add_argument("--apply", action="store_true", help="Actually apply the cleanup")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: specify --dry-run or --apply")
        print("  --dry-run  Show what would be cleaned")
        print("  --apply    Actually clean up")
        sys.exit(1)

    dry_run = not args.apply
    actions = cleanup_claims(dry_run=dry_run)
    print_summary(actions, dry_run=dry_run)

    if args.apply:
        print("\n✅ Cleanup applied successfully!")


if __name__ == "__main__":
    main()
