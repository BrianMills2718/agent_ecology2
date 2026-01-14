#!/usr/bin/env python3
"""Clean up stale remote branches whose PRs have been merged.

Usage:
    python scripts/cleanup_branches.py           # List stale branches
    python scripts/cleanup_branches.py --delete  # Delete stale branches
    python scripts/cleanup_branches.py --all     # Include abandoned PRs too
"""

import argparse
import json
import os
import subprocess
import sys


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command with gh CLI fix."""
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return subprocess.run(cmd, check=check, capture_output=True, text=True, env=env)


def get_unmerged_branches() -> list[str]:
    """Get remote branches not merged into main."""
    run_cmd(["git", "fetch", "--prune", "origin"], check=False)
    result = run_cmd(["git", "branch", "-r", "--no-merged", "origin/main"])
    branches = [
        b.strip().replace("origin/", "")
        for b in result.stdout.strip().split("\n")
        if b.strip() and "HEAD" not in b
    ]
    return branches


def get_pr_status(branch: str) -> tuple[str, str | None]:
    """Get PR status for a branch. Returns (status, merged_at)."""
    result = run_cmd(
        ["gh", "pr", "list", "--state", "all", "--head", branch,
         "--json", "number,state,mergedAt", "--jq", ".[0]"],
        check=False
    )

    if result.returncode != 0 or not result.stdout.strip():
        return "no_pr", None

    try:
        data = json.loads(result.stdout)
        if data.get("mergedAt"):
            return "merged", data["mergedAt"]
        elif data.get("state") == "CLOSED":
            return "abandoned", None
        elif data.get("state") == "OPEN":
            return "open", None
    except json.JSONDecodeError:
        pass

    return "unknown", None


def delete_branch(branch: str) -> bool:
    """Delete a remote branch."""
    result = run_cmd(
        ["git", "push", "origin", "--delete", branch],
        check=False
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up stale remote branches")
    parser.add_argument("--delete", action="store_true", help="Actually delete branches")
    parser.add_argument("--all", action="store_true", help="Include abandoned PRs too")
    args = parser.parse_args()

    print("Analyzing remote branches...")
    branches = get_unmerged_branches()

    merged: list[tuple[str, str]] = []
    abandoned: list[str] = []
    open_prs: list[str] = []
    no_pr: list[str] = []

    for branch in branches:
        status, merged_at = get_pr_status(branch)
        if status == "merged":
            merged.append((branch, merged_at or ""))
        elif status == "abandoned":
            abandoned.append(branch)
        elif status == "open":
            open_prs.append(branch)
        else:
            no_pr.append(branch)

    print(f"\nBranch Analysis ({len(branches)} unmerged branches):")
    print(f"  - Merged PRs (safe to delete): {len(merged)}")
    print(f"  - Abandoned PRs (closed without merge): {len(abandoned)}")
    print(f"  - Open PRs (active work): {len(open_prs)}")
    print(f"  - No PR found: {len(no_pr)}")

    to_delete = merged.copy()
    if args.all:
        to_delete.extend([(b, "") for b in abandoned])

    if not to_delete:
        print("\nNo branches to delete.")
        return 0

    if not args.delete:
        print(f"\nWould delete {len(to_delete)} branches:")
        for branch, merged_at in to_delete[:10]:
            print(f"  - {branch}" + (f" (merged: {merged_at[:10]})" if merged_at else ""))
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")
        print("\nRun with --delete to actually delete them.")
        return 0

    print(f"\nDeleting {len(to_delete)} branches...")
    deleted = 0
    failed = 0
    for branch, _ in to_delete:
        if delete_branch(branch):
            print(f"  Deleted: {branch}")
            deleted += 1
        else:
            print(f"  Failed: {branch}")
            failed += 1

    print(f"\nDone. Deleted: {deleted}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
