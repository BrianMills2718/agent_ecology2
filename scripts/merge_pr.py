#!/usr/bin/env python3
"""Merge PR with distributed locking to prevent race conditions.

Usage:
    python scripts/merge_pr.py 123           # Merge PR #123
    python scripts/merge_pr.py 123 --dry-run # Check without merging
    python scripts/merge_pr.py --status      # Show current merge lock
    python scripts/merge_pr.py --release     # Force release stale lock

This script ensures only one PR is merged at a time across all CC instances
by using a lock in .claude/active-work.yaml.

Workflow:
1. Check if another merge is in progress
2. Acquire lock (update YAML, commit, push)
3. Merge the PR via gh
4. Release lock (update YAML, commit, push)
5. Pull latest main
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


YAML_PATH = Path(".claude/active-work.yaml")
LOCK_TIMEOUT_MINUTES = 10  # Consider locks stale after this


def run_cmd(
    cmd: list[str], check: bool = True, capture: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a command, optionally capturing output."""
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"  # Fix for gh CLI
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        env=env,
    )


def get_cc_id() -> str:
    """Get current CC instance ID (branch name or 'main')."""
    try:
        result = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip() or "main"
    except subprocess.CalledProcessError:
        return "main"


def load_yaml() -> dict[str, list[dict[str, str]] | dict[str, str] | None]:
    """Load active-work.yaml."""
    if not YAML_PATH.exists():
        return {"claims": [], "completed": [], "merging": None}

    with open(YAML_PATH) as f:
        data = yaml.safe_load(f) or {}

    return {
        "claims": data.get("claims") or [],
        "completed": data.get("completed") or [],
        "merging": data.get("merging"),
    }


def save_yaml(data: dict[str, list[dict[str, str]] | dict[str, str] | None]) -> None:
    """Save active-work.yaml."""
    YAML_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Filter out None merging field for cleaner output
    save_data = {k: v for k, v in data.items() if v is not None}

    with open(YAML_PATH, "w") as f:
        f.write("# Active Work Lock File\n")
        f.write("# Machine-readable tracking for multi-CC coordination.\n")
        f.write("# Use: python scripts/check_claims.py --help\n\n")
        yaml.dump(save_data, f, default_flow_style=False, sort_keys=False)


def get_merge_lock(
    data: dict[str, list[dict[str, str]] | dict[str, str] | None],
) -> dict[str, str] | None:
    """Get current merge lock if exists and not stale."""
    lock = data.get("merging")
    if not lock or not isinstance(lock, dict):
        return None

    # Check if lock is stale
    try:
        locked_at_str = lock.get("locked_at", "")
        locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - locked_at
        if age > timedelta(minutes=LOCK_TIMEOUT_MINUTES):
            print(f"⚠️  Stale lock detected (age: {age}). Ignoring.")
            return None
    except (KeyError, ValueError):
        return None

    return lock


def acquire_lock(pr_number: int, dry_run: bool = False) -> bool:
    """Acquire merge lock. Returns True if successful."""
    # Fetch latest
    print("📥 Fetching latest...")
    run_cmd(["git", "fetch", "origin"], check=False)

    # Check for conflicts with main
    result = run_cmd(["git", "rev-list", "HEAD..origin/main", "--count"], check=False)
    if result.returncode == 0 and int(result.stdout.strip() or "0") > 0:
        print(f"⚠️  Local branch is {result.stdout.strip()} commits behind main.")
        print("   Run: git pull --rebase origin main")

    # Load current state
    data = load_yaml()

    # Check existing lock
    existing = get_merge_lock(data)
    if existing:
        print("❌ Another merge is in progress:")
        print(f"   PR: #{existing.get('pr')}")
        print(f"   By: {existing.get('cc_id')}")
        print(f"   At: {existing.get('locked_at')}")
        print()
        print("   Wait for it to complete, or use --release to force unlock.")
        return False

    if dry_run:
        print("✅ Lock available (dry-run, not acquiring)")
        return True

    # Acquire lock
    cc_id = get_cc_id()
    data["merging"] = {
        "pr": str(pr_number),
        "cc_id": cc_id,
        "locked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    save_yaml(data)

    # Commit and push lock
    print(f"🔒 Acquiring merge lock for PR #{pr_number}...")
    try:
        run_cmd(["git", "add", str(YAML_PATH)])
        run_cmd(
            ["git", "commit", "-m", f"[Trivial] Acquire merge lock for PR #{pr_number}"]
        )
        run_cmd(["git", "push", "origin", "HEAD"])
        print("✅ Lock acquired")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push lock: {e}")
        # Rollback local commit
        run_cmd(["git", "reset", "--hard", "HEAD~1"], check=False)
        return False


def release_lock(pr_number: int | None = None) -> bool:
    """Release merge lock. Returns True if successful."""
    data = load_yaml()

    if not data.get("merging"):
        print("ℹ️  No merge lock to release")
        return True

    # Clear lock
    data["merging"] = None
    save_yaml(data)

    # Commit and push
    msg = "[Trivial] Release merge lock" + (
        f" for PR #{pr_number}" if pr_number else ""
    )
    print("🔓 Releasing merge lock...")
    try:
        run_cmd(["git", "add", str(YAML_PATH)])
        run_cmd(["git", "commit", "-m", msg])
        run_cmd(["git", "push", "origin", "HEAD"])
        print("✅ Lock released")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to push lock release: {e}")
        return False


def check_pr_mergeable(pr_number: int) -> tuple[bool, str]:
    """Check if PR is mergeable. Returns (mergeable, reason)."""
    result = run_cmd(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "mergeable,mergeStateStatus,statusCheckRollup",
        ],
        check=False,
    )

    if result.returncode != 0:
        return False, f"Failed to get PR status: {result.stderr}"

    data = json.loads(result.stdout)

    mergeable = data.get("mergeable", "UNKNOWN")
    state = data.get("mergeStateStatus", "UNKNOWN")

    if mergeable == "CONFLICTING":
        return False, "PR has merge conflicts - needs rebase"

    if state == "BEHIND":
        return False, "PR is behind main - needs rebase"

    if state == "BLOCKED":
        # Check which checks are failing
        checks = data.get("statusCheckRollup", []) or []
        failing = [
            c.get("context", "unknown")
            for c in checks
            if c.get("conclusion") == "FAILURE"
            and c.get("context") != "feature-coverage"
        ]
        if failing:
            return False, f"Required checks failing: {', '.join(failing)}"

        pending = [
            c.get("context", "unknown")
            for c in checks
            if c.get("status") in ("IN_PROGRESS", "QUEUED", "PENDING")
        ]
        if pending:
            return False, f"Checks still running: {', '.join(pending)}"

    return True, "OK"


def merge_pr(pr_number: int, dry_run: bool = False) -> bool:
    """Merge a PR with locking. Returns True if successful."""
    print(f"🔍 Checking PR #{pr_number}...")

    # Check if PR is mergeable
    mergeable, reason = check_pr_mergeable(pr_number)
    if not mergeable:
        print(f"❌ PR #{pr_number} cannot be merged: {reason}")
        return False

    print(f"✅ PR #{pr_number} is mergeable")

    # Acquire lock
    if not acquire_lock(pr_number, dry_run):
        return False

    if dry_run:
        print(f"\n🔍 Dry run complete. PR #{pr_number} is ready to merge.")
        return True

    # Merge
    print(f"🚀 Merging PR #{pr_number}...")
    try:
        result = run_cmd(
            ["gh", "pr", "merge", str(pr_number), "--squash", "--delete-branch"],
            check=False,
        )

        if result.returncode != 0:
            print(f"❌ Merge failed: {result.stderr}")
            release_lock(pr_number)
            return False

        print(f"✅ PR #{pr_number} merged successfully")

    except subprocess.CalledProcessError as e:
        print(f"❌ Merge failed: {e}")
        release_lock(pr_number)
        return False

    # Release lock
    release_lock(pr_number)

    # Pull latest
    print("📥 Pulling latest main...")
    run_cmd(["git", "pull", "--rebase", "origin", "main"], check=False)

    print(f"\n✅ Done! PR #{pr_number} has been merged.")
    return True


def show_status() -> None:
    """Show current merge lock status."""
    data = load_yaml()
    lock = data.get("merging")

    if not lock or not isinstance(lock, dict):
        print("ℹ️  No merge lock currently held")
        return

    print("🔒 Current merge lock:")
    print(f"   PR: #{lock.get('pr')}")
    print(f"   By: {lock.get('cc_id')}")
    print(f"   At: {lock.get('locked_at')}")

    # Check if stale
    try:
        locked_at_str = lock.get("locked_at", "")
        locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - locked_at
        if age > timedelta(minutes=LOCK_TIMEOUT_MINUTES):
            print(f"   ⚠️  STALE (age: {age})")
        else:
            remaining = timedelta(minutes=LOCK_TIMEOUT_MINUTES) - age
            print(f"   ⏱️  Expires in: {remaining}")
    except (KeyError, ValueError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge PR with distributed locking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pr", type=int, nargs="?", help="PR number to merge")
    parser.add_argument("--dry-run", action="store_true", help="Check without merging")
    parser.add_argument("--status", action="store_true", help="Show current merge lock")
    parser.add_argument("--release", action="store_true", help="Force release lock")

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.release:
        return 0 if release_lock() else 1

    if not args.pr:
        parser.print_help()
        return 1

    return 0 if merge_pr(args.pr, args.dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
