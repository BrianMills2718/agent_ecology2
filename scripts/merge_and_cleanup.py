#!/usr/bin/env python3
"""Merge a PR and clean up the branch."""

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def load_merge_gates_config() -> dict:
    """Load merge gates config from meta-process.yaml."""
    defaults = {
        "check_pr_status": True,
        "check_plan_complete": True,
        "strict": False,
    }
    config_path = Path("meta-process.yaml")
    if not config_path.exists():
        return defaults
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        gates = config.get("merge_gates", {})
        if gates:
            defaults.update(gates)
    except Exception:
        pass
    return defaults


def run_pre_merge_checks(pr_number: int) -> list[str]:
    """Run pre-merge gate checks. Returns list of warnings."""
    config = load_merge_gates_config()
    warnings = []

    # Check PR checks status
    if config.get("check_pr_status"):
        result = run(
            ["gh", "pr", "checks", str(pr_number), "--json", "name,state"],
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                checks = json.loads(result.stdout)
                failed = [c for c in checks if c.get("state") != "SUCCESS"]
                if failed:
                    names = ", ".join(c.get("name", "?") for c in failed[:3])
                    warnings.append(
                        f"PR has {len(failed)} non-passing check(s): {names}"
                    )
            except json.JSONDecodeError:
                pass

    # Check if PR references a plan and if that plan is complete
    if config.get("check_plan_complete"):
        result = run(
            ["gh", "pr", "view", str(pr_number), "--json", "title"],
            check=False,
        )
        if result.returncode == 0:
            try:
                title = json.loads(result.stdout).get("title", "")
                plan_match = re.search(r"\[Plan #(\d+)\]", title)
                if plan_match:
                    plan_num = plan_match.group(1)
                    plan_files = glob.glob(f"docs/plans/{plan_num}_*.md")
                    if plan_files:
                        content = Path(plan_files[0]).read_text()
                        if "✅" not in content:
                            warnings.append(
                                f"Plan #{plan_num} is not marked complete"
                            )
            except (json.JSONDecodeError, OSError):
                pass

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge PR and clean up branch")
    parser.add_argument("--branch", required=True, help="Branch name")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    parser.add_argument(
        "--skip-gates", action="store_true",
        help="Skip pre-merge gate checks",
    )
    args = parser.parse_args()

    # Verify we're on main
    result = run(["git", "branch", "--show-current"])
    if result.stdout.strip() != "main":
        print("ERROR: Must be on main branch to merge. Run: git checkout main")
        return 1

    # Pre-merge gate checks
    if not args.skip_gates:
        warnings = run_pre_merge_checks(args.pr)
        if warnings:
            config = load_merge_gates_config()
            strict = config.get("strict", False)
            label = "BLOCKING" if strict else "ADVISORY"
            print(f"\nPre-merge gates ({label}):")
            for w in warnings:
                print(f"  - {w}")
            print()
            if strict:
                print("ERROR: Pre-merge gates failed (strict mode).")
                print("Use --skip-gates to bypass.")
                return 1

    # Merge the PR
    print(f"Merging PR #{args.pr}...")
    result = run(["gh", "pr", "merge", str(args.pr), "--squash", "--delete-branch"], check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to merge PR #{args.pr}")
        print(result.stderr)
        return 1
    print(f"PR #{args.pr} merged.")

    # Pull latest main
    print("Pulling latest main...")
    run(["git", "pull", "--ff-only"])

    # Clean up local branch — use -D because squash-merge creates new hashes
    # so git branch -d (which checks merge status) fails on squash-merged branches
    result = run(["git", "branch", "-D", args.branch], check=False)
    if result.returncode == 0:
        print(f"Deleted local branch {args.branch}.")
    else:
        # Branch may not exist locally, which is fine
        if "not found" not in result.stderr:
            print(f"Warning: could not delete local branch {args.branch}: {result.stderr.strip()}")

    print(f"\nDone! PR #{args.pr} merged, branch {args.branch} cleaned up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
