#!/usr/bin/env python3
"""Check that merged plan commits have verification evidence.

Plan #41 Gap 2: CI enforcement for complete_plan.py

Usage:
    # Check recent commits on main
    python scripts/check_plan_completion.py --recent-commits 5

    # Check specific plan
    python scripts/check_plan_completion.py --plan 40

    # List all plans missing evidence
    python scripts/check_plan_completion.py --list-missing
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_recent_commits(count: int) -> list[tuple[str, str]]:
    """Get recent commits from main branch.

    Returns list of (sha, message) tuples.
    """
    result = subprocess.run(
        ["git", "log", f"-{count}", "--format=%H|%s", "main"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            sha, msg = line.split("|", 1)
            commits.append((sha, msg))
    return commits


def extract_plan_number(commit_msg: str) -> int | None:
    """Extract plan number from commit message.

    Looks for [Plan #N] pattern.
    """
    match = re.search(r"\[Plan #(\d+)\]", commit_msg)
    if match:
        return int(match.group(1))
    return None


def check_plan_has_evidence(plan_number: int) -> tuple[bool, str]:
    """Check if a plan file has verification evidence.

    Returns (has_evidence, details).
    """
    plans_dir = Path(__file__).parent.parent / "docs" / "plans"

    # Find plan file
    plan_files = list(plans_dir.glob(f"{plan_number:02d}_*.md"))
    if not plan_files:
        return False, f"Plan file not found for #{plan_number}"

    plan_file = plan_files[0]
    content = plan_file.read_text()

    # Check for verification evidence block
    # Format: **Verified:** <timestamp>
    has_verified = bool(re.search(r"\*\*Verified:\*\*\s+\d{4}-\d{2}-\d{2}", content))

    # Check for Complete status
    is_complete = bool(re.search(r"\*\*Status:\*\*.*Complete|✅", content))

    if has_verified:
        return True, "Has verification evidence"
    elif is_complete:
        return False, "Marked Complete but no verification evidence"
    else:
        return True, "Not Complete (evidence not required)"


def check_recent_commits(count: int) -> list[dict]:
    """Check recent commits for plan completion evidence.

    Returns list of issues found.
    """
    commits = get_recent_commits(count)
    issues = []

    for sha, msg in commits:
        plan_num = extract_plan_number(msg)
        if plan_num is None:
            continue

        has_evidence, detail = check_plan_has_evidence(plan_num)
        if not has_evidence:
            issues.append({
                "sha": sha[:7],
                "message": msg,
                "plan": plan_num,
                "issue": detail
            })

    return issues


def list_missing_evidence() -> list[dict]:
    """List all Complete plans missing verification evidence."""
    plans_dir = Path(__file__).parent.parent / "docs" / "plans"
    missing = []

    for plan_file in sorted(plans_dir.glob("[0-9][0-9]_*.md")):
        content = plan_file.read_text()

        # Extract plan number
        match = re.match(r"(\d+)_", plan_file.name)
        if not match:
            continue
        plan_num = int(match.group(1))

        # Check status
        is_complete = bool(re.search(r"\*\*Status:\*\*.*Complete|✅", content))
        has_verified = bool(re.search(r"\*\*Verified:\*\*\s+\d{4}-\d{2}-\d{2}", content))

        if is_complete and not has_verified:
            missing.append({
                "plan": plan_num,
                "file": plan_file.name,
                "issue": "Complete but no verification evidence"
            })

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check plan completion evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--recent-commits", "-r",
        type=int,
        default=0,
        help="Check N recent commits for plan evidence"
    )
    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Check specific plan number"
    )
    parser.add_argument(
        "--list-missing", "-l",
        action="store_true",
        help="List all Complete plans missing evidence"
    )
    parser.add_argument(
        "--warn-only", "-w",
        action="store_true",
        help="Warn instead of fail (for post-merge checks)"
    )

    args = parser.parse_args()

    exit_code = 0

    if args.plan:
        has_evidence, detail = check_plan_has_evidence(args.plan)
        print(f"Plan #{args.plan}: {detail}")
        if not has_evidence:
            exit_code = 1

    elif args.recent_commits > 0:
        print(f"Checking {args.recent_commits} recent commits...")
        print("-" * 60)

        issues = check_recent_commits(args.recent_commits)

        if issues:
            print(f"\n⚠️  Found {len(issues)} plan(s) without verification evidence:\n")
            for issue in issues:
                print(f"  Plan #{issue['plan']}: {issue['issue']}")
                print(f"    Commit: {issue['sha']} {issue['message'][:50]}...")
                print()

            if not args.warn_only:
                exit_code = 1
        else:
            print("\n✅ All plan commits have verification evidence.")

    elif args.list_missing:
        missing = list_missing_evidence()

        if missing:
            print(f"Plans marked Complete without verification evidence:\n")
            for item in missing:
                print(f"  Plan #{item['plan']}: {item['file']}")
            print(f"\nTotal: {len(missing)} plan(s)")
            exit_code = 1
        else:
            print("✅ All Complete plans have verification evidence.")

    else:
        parser.print_help()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
