#!/usr/bin/env python3
"""Safely remove a git worktree, checking for uncommitted changes first.

This prevents accidental data loss when removing worktrees that have
uncommitted changes (which are lost forever when the worktree is removed).

Usage:
    python scripts/safe_worktree_remove.py <worktree-path>
    python scripts/safe_worktree_remove.py worktrees/plan-46-review-fix

    # Force removal (skips safety check)
    python scripts/safe_worktree_remove.py --force <worktree-path>
"""

import argparse
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
            env={**subprocess.os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def has_uncommitted_changes(worktree_path: str) -> tuple[bool, str]:
    """Check if worktree has uncommitted changes.

    Returns (has_changes, details).
    """
    # Check for modified/staged/untracked files
    success, output = run_cmd(
        ["git", "status", "--porcelain"],
        cwd=worktree_path
    )

    if not success:
        return False, f"Could not check status: {output}"

    if output.strip():
        return True, output

    return False, ""


def get_worktree_branch(worktree_path: str) -> str | None:
    """Get the branch name of a worktree."""
    success, output = run_cmd(
        ["git", "branch", "--show-current"],
        cwd=worktree_path
    )
    return output if success else None


def remove_worktree(worktree_path: str, force: bool = False) -> bool:
    """Remove a worktree safely.

    Returns True if removal succeeded, False otherwise.
    """
    path = Path(worktree_path)

    if not path.exists():
        print(f"❌ Worktree path does not exist: {worktree_path}")
        return False

    # Check for uncommitted changes
    has_changes, details = has_uncommitted_changes(worktree_path)

    if has_changes and not force:
        branch = get_worktree_branch(worktree_path) or "unknown"
        print(f"❌ BLOCKED: Worktree '{worktree_path}' has uncommitted changes!")
        print(f"   Branch: {branch}")
        print(f"   Changes:")
        for line in details.split("\n")[:10]:  # Show first 10 changes
            print(f"      {line}")
        if details.count("\n") > 10:
            print(f"      ... and {details.count(chr(10)) - 10} more")
        print()
        print("   Options:")
        print(f"   1. Commit changes: cd {worktree_path} && git add -A && git commit -m 'WIP'")
        print(f"   2. Discard changes: cd {worktree_path} && git checkout -- .")
        print(f"   3. Force remove (LOSES CHANGES): python scripts/safe_worktree_remove.py --force {worktree_path}")
        return False

    # Remove the worktree
    success, output = run_cmd(["git", "worktree", "remove", worktree_path])

    if success:
        print(f"✅ Worktree removed: {worktree_path}")
        return True
    else:
        # Try with --force if regular remove failed (e.g., untracked files)
        if force:
            success, output = run_cmd(["git", "worktree", "remove", "--force", worktree_path])
            if success:
                print(f"✅ Worktree force-removed: {worktree_path}")
                return True

        print(f"❌ Failed to remove worktree: {output}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely remove a git worktree, checking for uncommitted changes first."
    )
    parser.add_argument(
        "worktree_path",
        help="Path to the worktree to remove (e.g., worktrees/plan-46-review-fix)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force removal even if there are uncommitted changes (DATA LOSS WARNING)"
    )

    args = parser.parse_args()

    if args.force:
        print("⚠️  WARNING: Force mode - uncommitted changes will be LOST!")

    success = remove_worktree(args.worktree_path, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
