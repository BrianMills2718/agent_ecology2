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
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
    """Run command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
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


def get_main_repo_root() -> Path:
    """Get the main repo root (not worktree).

    For worktrees, returns the main repository's root directory.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        git_dir = Path(result.stdout.strip())
        return git_dir.parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def check_worktree_claimed(
    worktree_path: str,
    claims_file: Path | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """Check if a worktree has an active claim.

    Args:
        worktree_path: Path to the worktree to check
        claims_file: Optional path to claims file (for testing)

    Returns:
        (is_claimed, claim_info) - claim_info is the claim dict if found
    """
    if claims_file is None:
        claims_file = get_main_repo_root() / ".claude" / "active-work.yaml"

    if not claims_file.exists():
        return False, None

    try:
        data = yaml.safe_load(claims_file.read_text()) or {}
    except yaml.YAMLError:
        return False, None

    claims = data.get("claims", [])

    # Normalize the worktree path for comparison
    normalized_path = str(Path(worktree_path).resolve())

    for claim in claims:
        claim_worktree = claim.get("worktree_path")
        if claim_worktree:
            # Normalize claim's worktree path too
            normalized_claim_path = str(Path(claim_worktree).resolve())
            if normalized_path == normalized_claim_path:
                return True, claim

    return False, None


def should_block_removal(
    worktree_path: str,
    force: bool = False,
    claims_file: Path | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """Determine if worktree removal should be blocked due to active claim.

    Args:
        worktree_path: Path to the worktree
        force: If True, don't block for claims (still returns info)
        claims_file: Optional path to claims file (for testing)

    Returns:
        (should_block, claim_info) - should_block is False if force=True
    """
    is_claimed, claim_info = check_worktree_claimed(worktree_path, claims_file)

    if is_claimed and not force:
        return True, claim_info

    return False, claim_info


def remove_worktree(worktree_path: str, force: bool = False) -> bool:
    """Remove a worktree safely.

    Returns True if removal succeeded, False otherwise.
    """
    path = Path(worktree_path)

    if not path.exists():
        print(f"❌ Worktree path does not exist: {worktree_path}")
        return False

    # Check for active claims (Plan #52: Worktree Session Tracking)
    should_block, claim_info = should_block_removal(worktree_path, force)
    if should_block and claim_info:
        cc_id = claim_info.get("cc_id", "unknown")
        task = claim_info.get("task", "")[:50]
        plan = claim_info.get("plan")
        print(f"❌ BLOCKED: Worktree has an active claim!")
        print(f"   Claimed by: {cc_id}")
        if plan:
            print(f"   Plan: #{plan}")
        print(f"   Task: {task}")
        print()
        print("   A Claude session may be actively using this worktree.")
        print("   Removing it will break their shell (CWD becomes invalid).")
        print()
        print("   Options:")
        print(f"   1. Release the claim first: python scripts/check_claims.py --release --id {cc_id}")
        print(f"   2. Force remove (BREAKS SESSION): python scripts/safe_worktree_remove.py --force {worktree_path}")
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
