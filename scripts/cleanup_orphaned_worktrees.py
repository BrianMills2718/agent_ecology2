#!/usr/bin/env python3
"""Find and clean up orphaned git worktrees.

Orphaned worktrees occur when PRs are merged without using `make finish`:
- Direct GitHub merges (web UI, mobile app, API)
- `make merge` without `make finish`
- Non-standard worktree locations missed by cleanup hooks

This script finds worktrees whose branches have been deleted from remote
(indicating the PR was merged) and optionally cleans them up.

Usage:
    python scripts/cleanup_orphaned_worktrees.py          # Report only
    python scripts/cleanup_orphaned_worktrees.py --auto   # Auto-cleanup orphans
    python scripts/cleanup_orphaned_worktrees.py --force  # Skip uncommitted check
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
    """Run command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_worktrees() -> list[dict]:
    """Get all git worktrees with their paths and branches."""
    success, output = run_cmd(["git", "worktree", "list", "--porcelain"])
    if not success:
        return []

    worktrees = []
    current: dict = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True

    if current:
        worktrees.append(current)

    return worktrees


def remote_branch_exists(branch: str) -> bool:
    """Check if a branch exists on the remote."""
    success, output = run_cmd(["git", "ls-remote", "--heads", "origin", branch])
    return success and bool(output.strip())


def get_merged_prs() -> dict[str, dict]:
    """Get recently merged PRs (last 50) indexed by head branch."""
    success, output = run_cmd([
        "gh", "pr", "list",
        "--state", "merged",
        "--limit", "50",
        "--json", "number,title,headRefName,mergedAt"
    ])

    if not success or not output:
        return {}

    try:
        prs = json.loads(output)
        return {pr["headRefName"]: pr for pr in prs}
    except Exception:
        return {}


def has_uncommitted_changes(worktree_path: str) -> bool:
    """Check if worktree has uncommitted changes."""
    success, output = run_cmd(["git", "status", "--porcelain"], cwd=worktree_path)
    return success and bool(output.strip())


def extract_worktree_name(path: str) -> str | None:
    """Extract the worktree directory name from path.

    For /path/to/repo/worktrees/plan-91-foo, returns 'plan-91-foo'.
    For paths not containing /worktrees/, returns the last component.
    """
    p = Path(path)
    # Check various worktree locations
    if "worktrees" in p.parts:
        idx = p.parts.index("worktrees")
        if idx < len(p.parts) - 1:
            return p.parts[idx + 1]
    return p.name


def find_orphaned_worktrees() -> list[dict]:
    """Find worktrees whose branches have been deleted from remote."""
    worktrees = get_worktrees()
    merged_prs = get_merged_prs()
    orphans = []

    for wt in worktrees:
        path = wt.get("path", "")
        branch = wt.get("branch", "")
        is_detached = wt.get("detached", False)

        # Skip main worktree (no branch or is 'main')
        if not branch or branch == "main":
            continue

        # Check if branch exists on remote
        if not is_detached and remote_branch_exists(branch):
            continue  # Branch still exists, not orphaned

        # This is a candidate orphan
        name = extract_worktree_name(path)
        has_changes = has_uncommitted_changes(path)

        # Check if it was a merged PR
        merged_pr = merged_prs.get(branch)

        orphans.append({
            "path": path,
            "name": name,
            "branch": branch,
            "detached": is_detached,
            "has_uncommitted": has_changes,
            "merged_pr": merged_pr,
            "reason": "detached HEAD" if is_detached else "branch deleted from remote",
        })

    return orphans


def cleanup_worktree(worktree_path: str, force: bool = False) -> tuple[bool, str]:
    """Remove a worktree safely.

    Uses safe_worktree_remove.py if available, otherwise direct git commands.
    """
    # Try safe_worktree_remove.py first
    script_path = Path(__file__).parent / "safe_worktree_remove.py"
    if script_path.exists():
        cmd = ["python", str(script_path)]
        if force:
            cmd.append("--force")
        cmd.append(worktree_path)
        return run_cmd(cmd)

    # Fallback to direct git worktree remove
    cmd = ["git", "worktree", "remove"]
    if force:
        cmd.append("--force")
    cmd.append(worktree_path)
    success, output = run_cmd(cmd)

    if success:
        # Also run prune to clean up
        run_cmd(["git", "worktree", "prune"])

    return success, output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find and clean up orphaned git worktrees"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically clean up orphaned worktrees (skips those with uncommitted changes)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force cleanup even with uncommitted changes (LOSES DATA!)"
    )
    args = parser.parse_args()

    print("Scanning for orphaned worktrees...")
    print()

    orphans = find_orphaned_worktrees()

    if not orphans:
        print("No orphaned worktrees found.")
        return

    print(f"Found {len(orphans)} orphaned worktree(s):")
    print()

    cleaned = 0
    skipped = 0

    for orphan in orphans:
        name = orphan["name"]
        path = orphan["path"]
        branch = orphan["branch"]
        reason = orphan["reason"]
        has_changes = orphan["has_uncommitted"]
        merged_pr = orphan.get("merged_pr")

        # Format PR info
        pr_info = ""
        if merged_pr:
            pr_num = merged_pr.get("number", "?")
            pr_title = merged_pr.get("title", "")[:40]
            pr_info = f" (PR #{pr_num}: {pr_title})"

        # Status indicator
        if has_changes:
            status = "⚠️  HAS UNCOMMITTED CHANGES"
        else:
            status = "✓ clean"

        print(f"  {name}")
        print(f"    Path: {path}")
        print(f"    Branch: {branch}")
        print(f"    Reason: {reason}{pr_info}")
        print(f"    Status: {status}")

        if args.auto:
            if has_changes and not args.force:
                print(f"    Action: SKIPPED (uncommitted changes)")
                skipped += 1
            else:
                print(f"    Action: Cleaning up...")
                success, output = cleanup_worktree(path, force=args.force)
                if success:
                    print(f"    Result: ✓ Removed")
                    cleaned += 1
                else:
                    print(f"    Result: ✗ Failed - {output}")
                    skipped += 1
        else:
            # Report mode - show cleanup command
            force_flag = "--force " if has_changes else ""
            print(f"    Cleanup: make worktree-remove{'-force' if has_changes else ''} BRANCH={name}")

        print()

    # Summary
    if args.auto:
        print(f"Summary: {cleaned} cleaned, {skipped} skipped")
    else:
        print("To clean up, run:")
        print("  python scripts/cleanup_orphaned_worktrees.py --auto")
        print()
        print("Or manually:")
        for orphan in orphans:
            name = orphan["name"]
            has_changes = orphan["has_uncommitted"]
            force_flag = "-force" if has_changes else ""
            print(f"  make worktree-remove{force_flag} BRANCH={name}")


if __name__ == "__main__":
    main()
