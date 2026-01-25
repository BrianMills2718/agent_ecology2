#!/usr/bin/env python3
"""Meta-process health check.

Validates the entire meta-process system state:
- No orphaned worktrees
- No stale claims
- Hooks are configured correctly
- Config files are valid
- Git state is clean

Usage:
    python scripts/health_check.py          # Run all checks
    python scripts/health_check.py --fix    # Auto-fix what can be fixed
    python scripts/health_check.py --quiet  # Only show problems
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Get repo root (where this script lives is scripts/, so parent is root)
REPO_ROOT = Path(__file__).parent.parent.resolve()


class HealthCheck:
    """Run health checks and report results."""

    def __init__(self, fix: bool = False, quiet: bool = False):
        self.fix = fix
        self.quiet = quiet
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.fixed: list[str] = []

    def log(self, msg: str) -> None:
        if not self.quiet:
            print(msg)

    def issue(self, msg: str) -> None:
        self.issues.append(msg)
        print(f"  ❌ {msg}")

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  ⚠️  {msg}")

    def ok(self, msg: str) -> None:
        if not self.quiet:
            print(f"  ✅ {msg}")

    def fixed_msg(self, msg: str) -> None:
        self.fixed.append(msg)
        print(f"  🔧 {msg}")

    def run_command(self, cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=REPO_ROOT,
        )

    def check_orphaned_worktrees(self) -> None:
        """Check for worktrees whose branches have been merged."""
        self.log("\n📁 Checking worktrees...")

        result = self.run_command(["git", "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            self.issue("Failed to list worktrees")
            return

        worktrees = []
        current_wt = {}
        for line in result.stdout.strip().split("\n"):
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[9:]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[7:].replace("refs/heads/", "")
        if current_wt:
            worktrees.append(current_wt)

        # Check each worktree (skip main)
        orphaned = []
        for wt in worktrees:
            if wt["path"] == str(REPO_ROOT):
                continue
            branch = wt.get("branch", "")
            if not branch:
                continue

            # Check if branch's PR is merged
            result = self.run_command([
                "gh", "pr", "list", "--state", "merged", "--head", branch,
                "--json", "number", "--limit", "1"
            ])
            if result.returncode == 0 and result.stdout.strip() not in ["", "[]"]:
                orphaned.append(wt)

        if orphaned:
            for wt in orphaned:
                self.warning(f"Orphaned worktree: {wt['path']} (branch {wt.get('branch', 'unknown')} merged)")
                if self.fix:
                    # Auto-fix: remove the worktree
                    rm_result = self.run_command(["git", "worktree", "remove", wt["path"], "--force"])
                    if rm_result.returncode == 0:
                        self.fixed_msg(f"Removed orphaned worktree: {wt['path']}")
        else:
            self.ok("No orphaned worktrees")

    def check_stale_claims(self) -> None:
        """Check for stale claims."""
        self.log("\n📋 Checking claims...")

        result = self.run_command([
            "python", "scripts/check_claims.py", "--cleanup-stale",
            "--stale-hours", "8", "--dry-run"
        ])

        if "Would release" in result.stdout:
            lines = [l for l in result.stdout.split("\n") if l.strip().startswith("-")]
            for line in lines:
                self.warning(f"Stale claim: {line.strip()}")

            if self.fix:
                fix_result = self.run_command([
                    "python", "scripts/check_claims.py", "--cleanup-stale", "--stale-hours", "8"
                ])
                if fix_result.returncode == 0:
                    self.fixed_msg("Cleaned up stale claims")
        else:
            self.ok("No stale claims")

    def check_orphaned_claims(self) -> None:
        """Check for claims without worktrees."""
        result = self.run_command([
            "python", "scripts/check_claims.py", "--cleanup-orphaned", "--dry-run"
        ])

        if "Would remove" in result.stdout or "orphaned" in result.stdout.lower():
            self.warning("Orphaned claims exist (claims without worktrees)")
            if self.fix:
                fix_result = self.run_command([
                    "python", "scripts/check_claims.py", "--cleanup-orphaned"
                ])
                if fix_result.returncode == 0:
                    self.fixed_msg("Cleaned up orphaned claims")
        else:
            self.ok("No orphaned claims")

    def check_hooks_configured(self) -> None:
        """Check if Claude Code hooks are configured."""
        self.log("\n🪝 Checking hooks...")

        settings_file = REPO_ROOT / ".claude" / "settings.json"
        if not settings_file.exists():
            self.issue("Missing .claude/settings.json (hooks not configured)")
            return

        import json
        try:
            with open(settings_file) as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})
            if not hooks:
                self.warning("No hooks configured in .claude/settings.json")
            else:
                hook_count = sum(len(v) for v in hooks.values() if isinstance(v, list))
                self.ok(f"Hooks configured ({hook_count} hook entries)")
        except json.JSONDecodeError as e:
            self.issue(f"Invalid JSON in .claude/settings.json: {e}")

    def check_config_valid(self) -> None:
        """Check if meta-process.yaml is valid."""
        self.log("\n⚙️  Checking configuration...")

        config_file = REPO_ROOT / "meta-process.yaml"
        if not config_file.exists():
            self.warning("Missing meta-process.yaml")
            return

        try:
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)

            if not config:
                self.warning("Empty meta-process.yaml")
            else:
                self.ok("meta-process.yaml is valid")
        except Exception as e:
            self.issue(f"Invalid meta-process.yaml: {e}")

    def check_git_state(self) -> None:
        """Check git state is clean in main."""
        self.log("\n🔀 Checking git state...")

        result = self.run_command(["git", "status", "--porcelain"])
        if result.stdout.strip():
            uncommitted = len(result.stdout.strip().split("\n"))
            self.warning(f"Main has {uncommitted} uncommitted change(s)")
        else:
            self.ok("Main is clean")

        # Check if on main branch
        result = self.run_command(["git", "branch", "--show-current"])
        branch = result.stdout.strip()
        if branch != "main":
            self.warning(f"Not on main branch (on '{branch}')")
        else:
            self.ok("On main branch")

    def check_open_prs(self) -> None:
        """Check for open PRs that might need attention."""
        self.log("\n🔄 Checking open PRs...")

        result = self.run_command(["gh", "pr", "list", "--state", "open", "--json", "number,title"])
        if result.returncode != 0:
            self.warning("Could not check open PRs (gh CLI issue?)")
            return

        import json
        try:
            prs = json.loads(result.stdout)
            if prs:
                self.warning(f"{len(prs)} open PR(s)")
                for pr in prs[:5]:  # Show first 5
                    print(f"      #{pr['number']}: {pr['title'][:50]}")
            else:
                self.ok("No open PRs")
        except json.JSONDecodeError:
            self.ok("No open PRs")

    def run_all(self) -> int:
        """Run all health checks and return exit code."""
        print("=" * 60)
        print("META-PROCESS HEALTH CHECK")
        print("=" * 60)

        self.check_git_state()
        self.check_hooks_configured()
        self.check_config_valid()
        self.check_orphaned_worktrees()
        self.check_orphaned_claims()
        self.check_stale_claims()
        self.check_open_prs()

        print("\n" + "=" * 60)
        if self.fixed:
            print(f"🔧 Fixed {len(self.fixed)} issue(s)")
        if self.issues:
            print(f"❌ {len(self.issues)} issue(s) found")
            return 1
        elif self.warnings:
            print(f"⚠️  {len(self.warnings)} warning(s)")
            return 0
        else:
            print("✅ All checks passed!")
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Meta-process health check")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show problems")
    args = parser.parse_args()

    checker = HealthCheck(fix=args.fix, quiet=args.quiet)
    return checker.run_all()


if __name__ == "__main__":
    sys.exit(main())
