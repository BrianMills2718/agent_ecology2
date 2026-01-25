#!/usr/bin/env python3
"""Meta-process recovery tool.

Automatically recovers from common meta-process issues:
- Orphaned worktrees (merged but not cleaned up)
- Stale claims (old claims blocking work)
- Orphaned claims (claims without worktrees)
- Invalid CWD (worktree deleted but shell still references it)

Usage:
    python scripts/recover.py              # Interactive recovery
    python scripts/recover.py --auto       # Auto-fix everything
    python scripts/recover.py --dry-run    # Show what would be fixed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Get repo root
REPO_ROOT = Path(__file__).parent.parent.resolve()


class Recovery:
    """Recovery operations for meta-process issues."""

    def __init__(self, auto: bool = False, dry_run: bool = False):
        self.auto = auto
        self.dry_run = dry_run
        self.actions_taken: list[str] = []

    def run_command(
        self, cmd: list[str], capture: bool = True, check: bool = False
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=REPO_ROOT,
            check=check,
        )

    def confirm(self, msg: str) -> bool:
        """Ask for confirmation unless auto mode."""
        if self.auto:
            return True
        if self.dry_run:
            print(f"  [DRY RUN] Would: {msg}")
            return False
        response = input(f"  {msg} [y/N]: ")
        return response.lower() in ("y", "yes")

    def recover_orphaned_worktrees(self) -> int:
        """Remove worktrees whose PRs have been merged."""
        print("\n📁 Checking for orphaned worktrees...")

        result = self.run_command(["git", "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            print("  ❌ Failed to list worktrees")
            return 0

        # Parse worktrees
        worktrees = []
        current_wt: dict = {}
        for line in result.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[9:]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[7:].replace("refs/heads/", "")
        if current_wt:
            worktrees.append(current_wt)

        fixed = 0
        for wt in worktrees:
            if wt["path"] == str(REPO_ROOT):
                continue

            branch = wt.get("branch", "")
            if not branch:
                continue

            # Check if PR is merged
            result = self.run_command([
                "gh", "pr", "list", "--state", "merged", "--head", branch,
                "--json", "number", "--limit", "1"
            ])

            if result.returncode == 0 and result.stdout.strip() not in ["", "[]"]:
                print(f"  Found orphaned worktree: {wt['path']}")
                if self.confirm(f"Remove worktree {wt['path']}?"):
                    if not self.dry_run:
                        rm_result = self.run_command([
                            "git", "worktree", "remove", wt["path"], "--force"
                        ])
                        if rm_result.returncode == 0:
                            print(f"    ✅ Removed")
                            self.actions_taken.append(f"Removed worktree: {wt['path']}")
                            fixed += 1
                        else:
                            print(f"    ❌ Failed to remove")

        if fixed == 0:
            print("  ✅ No orphaned worktrees found")
        return fixed

    def recover_orphaned_claims(self) -> int:
        """Remove claims that don't have worktrees."""
        print("\n📋 Checking for orphaned claims...")

        if self.dry_run:
            result = self.run_command([
                "python", "scripts/check_claims.py", "--cleanup-orphaned", "--dry-run"
            ])
            if "Would remove" in result.stdout or "Removed" in result.stdout:
                print(result.stdout)
            else:
                print("  ✅ No orphaned claims found")
            return 0

        if self.auto or self.confirm("Clean up orphaned claims?"):
            result = self.run_command([
                "python", "scripts/check_claims.py", "--cleanup-orphaned"
            ])
            if "Removed" in result.stdout:
                print(result.stdout)
                self.actions_taken.append("Cleaned up orphaned claims")
                return 1
            else:
                print("  ✅ No orphaned claims found")
        return 0

    def recover_stale_claims(self, hours: int = 8) -> int:
        """Remove claims that are stale (inactive for too long)."""
        print(f"\n⏰ Checking for stale claims (>{hours}h inactive)...")

        if self.dry_run:
            result = self.run_command([
                "python", "scripts/check_claims.py", "--cleanup-stale",
                "--stale-hours", str(hours), "--dry-run"
            ])
            if "Would release" in result.stdout:
                print(result.stdout)
            else:
                print("  ✅ No stale claims found")
            return 0

        if self.auto or self.confirm(f"Clean up claims inactive for >{hours} hours?"):
            result = self.run_command([
                "python", "scripts/check_claims.py", "--cleanup-stale",
                "--stale-hours", str(hours)
            ])
            if "Released" in result.stdout:
                print(result.stdout)
                self.actions_taken.append("Cleaned up stale claims")
                return 1
            else:
                print("  ✅ No stale claims found")
        return 0

    def recover_git_state(self) -> int:
        """Ensure we're on main and up to date."""
        print("\n🔀 Checking git state...")

        # Check current branch
        result = self.run_command(["git", "branch", "--show-current"])
        branch = result.stdout.strip()

        if branch != "main":
            print(f"  Currently on branch '{branch}'")
            if self.confirm("Switch to main?"):
                if not self.dry_run:
                    self.run_command(["git", "checkout", "main"])
                    self.actions_taken.append("Switched to main branch")
                    print("    ✅ Switched to main")

        # Prune worktree references
        print("  Pruning stale worktree references...")
        if not self.dry_run:
            self.run_command(["git", "worktree", "prune"])

        # Pull latest
        if self.auto or self.confirm("Pull latest main?"):
            if not self.dry_run:
                result = self.run_command(["git", "pull", "origin", "main"])
                if result.returncode == 0:
                    print("    ✅ Pulled latest")
                    self.actions_taken.append("Pulled latest main")

        return 1 if self.actions_taken else 0

    def show_cwd_recovery(self) -> None:
        """Show instructions for CWD recovery."""
        print("\n💡 CWD Recovery Instructions")
        print("  If your shell is broken (worktree deleted), run:")
        print(f"    cd {REPO_ROOT}")
        print("  Then start a new Claude Code session.")

    def run(self) -> int:
        """Run all recovery operations."""
        print("=" * 60)
        print("META-PROCESS RECOVERY")
        if self.dry_run:
            print("(DRY RUN - no changes will be made)")
        elif self.auto:
            print("(AUTO MODE - will fix everything)")
        print("=" * 60)

        self.recover_git_state()
        self.recover_orphaned_worktrees()
        self.recover_orphaned_claims()
        self.recover_stale_claims()
        self.show_cwd_recovery()

        print("\n" + "=" * 60)
        if self.actions_taken:
            print(f"✅ Took {len(self.actions_taken)} recovery action(s):")
            for action in self.actions_taken:
                print(f"   - {action}")
        else:
            print("✅ No recovery actions needed (or dry run)")

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Meta-process recovery tool")
    parser.add_argument(
        "--auto", action="store_true",
        help="Automatically fix all issues without prompting"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be fixed without making changes"
    )
    args = parser.parse_args()

    recovery = Recovery(auto=args.auto, dry_run=args.dry_run)
    return recovery.run()


if __name__ == "__main__":
    sys.exit(main())
