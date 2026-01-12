#!/usr/bin/env python3
"""Show progress on plan implementation.

Parses plan files to calculate completion percentage based on:
- Required tests written vs defined
- Verification checklist items checked
- Implementation steps completed

Usage:
    # Show progress for plan #1
    python scripts/plan_progress.py --plan 1

    # Show progress for all plans
    python scripts/plan_progress.py --all

    # Summary view (one line per plan)
    python scripts/plan_progress.py --all --summary
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ProgressMetrics:
    """Progress metrics for a plan."""
    tests_exist: int
    tests_total: int
    checks_done: int
    checks_total: int
    steps_done: int
    steps_total: int


def find_plan_files(plans_dir: Path) -> list[Path]:
    """Find all plan files."""
    return sorted(
        [f for f in plans_dir.glob("*.md") if re.match(r"\d+_", f.name)],
        key=lambda f: int(f.name.split("_")[0])
    )


def get_plan_info(plan_file: Path) -> tuple[int, str, str]:
    """Extract plan number, name, and status."""
    content = plan_file.read_text()

    match = re.match(r"(\d+)_(.+)\.md", plan_file.name)
    plan_num = int(match.group(1)) if match else 0
    plan_name = match.group(2).replace("_", " ").title() if match else plan_file.stem

    status_match = re.search(r"\*\*Status:\*\*\s*(.+)", content)
    status = status_match.group(1).strip() if status_match else "Unknown"

    return plan_num, plan_name, status


def count_tests(plan_file: Path) -> tuple[int, int]:
    """Count existing vs required tests.

    Returns (existing_count, total_required).
    """
    content = plan_file.read_text()

    # Find Required Tests section
    tests_section = re.search(
        r"## Required Tests\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL
    )

    if not tests_section:
        return 0, 0

    section = tests_section.group(1)

    # Count test rows in New Tests table
    new_tests_match = re.search(
        r"### New Tests.*?\n\|.*?\n\|[-\s|]+\n((?:\|.*?\n)*)",
        section,
        re.DOTALL
    )

    total = 0
    if new_tests_match:
        rows = [r for r in new_tests_match.group(1).strip().split("\n") if r.strip()]
        total = len(rows)

    # Check which tests exist
    existing = 0
    if total > 0:
        result = subprocess.run(
            ["python", "scripts/check_plan_tests.py", "--plan",
             str(int(plan_file.name.split("_")[0])), "--tdd"],
            capture_output=True,
            text=True
        )
        existing = result.stdout.count("[EXISTS]")

    return existing, total


def count_checklist_items(plan_file: Path) -> tuple[int, int]:
    """Count checked vs total checklist items in Verification section.

    Returns (checked_count, total_count).
    """
    content = plan_file.read_text()

    # Find Verification section
    verif_section = re.search(
        r"## Verification\s*\n(.*?)(?=\n## |\n---|\Z)",
        content,
        re.DOTALL
    )

    if not verif_section:
        return 0, 0

    section = verif_section.group(1)

    # Count checkbox items
    checked = len(re.findall(r"- \[x\]", section, re.IGNORECASE))
    unchecked = len(re.findall(r"- \[ \]", section))
    total = checked + unchecked

    return checked, total


def count_steps(plan_file: Path) -> tuple[int, int]:
    """Count completed vs total steps.

    Returns (completed_count, total_count).
    """
    content = plan_file.read_text()

    # Find Steps section (or numbered lists in Plan section)
    steps_section = re.search(
        r"## (?:Steps|Plan)\s*\n(.*?)(?=\n## |\n---|\Z)",
        content,
        re.DOTALL
    )

    if not steps_section:
        return 0, 0

    section = steps_section.group(1)

    # Count numbered list items and sub-items with checkboxes
    # Format: 1. Step or - [x] Sub-step
    total_steps = len(re.findall(r"^###\s+Step", section, re.MULTILINE))
    if total_steps == 0:
        total_steps = len(re.findall(r"^\d+\.\s+", section, re.MULTILINE))

    # Check for completed markers (strikethrough or checkboxes)
    completed = len(re.findall(r"~~.+~~|^###\s+Step.*✅", section, re.MULTILINE))

    return completed, total_steps


def calculate_progress(metrics: ProgressMetrics) -> float:
    """Calculate overall progress percentage."""
    total_items = metrics.tests_total + metrics.checks_total + metrics.steps_total
    if total_items == 0:
        return 0.0

    done_items = metrics.tests_exist + metrics.checks_done + metrics.steps_done
    return (done_items / total_items) * 100


def show_plan_progress(plan_file: Path, verbose: bool = True) -> ProgressMetrics:
    """Show progress for a single plan."""
    plan_num, plan_name, status = get_plan_info(plan_file)
    tests_exist, tests_total = count_tests(plan_file)
    checks_done, checks_total = count_checklist_items(plan_file)
    steps_done, steps_total = count_steps(plan_file)

    metrics = ProgressMetrics(
        tests_exist=tests_exist,
        tests_total=tests_total,
        checks_done=checks_done,
        checks_total=checks_total,
        steps_done=steps_done,
        steps_total=steps_total
    )

    progress = calculate_progress(metrics)

    if verbose:
        print(f"Plan #{plan_num}: {plan_name}")
        print(f"Status: {status}")
        print("-" * 40)

        if tests_total > 0:
            pct = (tests_exist / tests_total * 100) if tests_total else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            print(f"  Tests:    [{bar}] {tests_exist}/{tests_total} ({pct:.0f}%)")
        else:
            print(f"  Tests:    No tests defined")

        if checks_total > 0:
            pct = (checks_done / checks_total * 100) if checks_total else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            print(f"  Checks:   [{bar}] {checks_done}/{checks_total} ({pct:.0f}%)")
        else:
            print(f"  Checks:   No checklist found")

        if steps_total > 0:
            pct = (steps_done / steps_total * 100) if steps_total else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            print(f"  Steps:    [{bar}] {steps_done}/{steps_total} ({pct:.0f}%)")
        else:
            print(f"  Steps:    No steps defined")

        print()
        bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
        print(f"  Overall:  [{bar}] {progress:.0f}%")

    return metrics


def show_summary(plans_dir: Path) -> None:
    """Show one-line summary for each plan."""
    print(f"{'#':>3} {'Plan':<30} {'Status':<15} {'Progress':<12} {'Tests':<10}")
    print("-" * 75)

    for plan_file in find_plan_files(plans_dir):
        plan_num, plan_name, status = get_plan_info(plan_file)

        # Truncate status for display
        status_short = status[:13] + ".." if len(status) > 15 else status

        tests_exist, tests_total = count_tests(plan_file)
        checks_done, checks_total = count_checklist_items(plan_file)

        metrics = ProgressMetrics(
            tests_exist=tests_exist,
            tests_total=tests_total,
            checks_done=checks_done,
            checks_total=checks_total,
            steps_done=0,
            steps_total=0
        )

        progress = calculate_progress(metrics)
        bar = "█" * int(progress / 20) + "░" * (5 - int(progress / 20))

        tests_str = f"{tests_exist}/{tests_total}" if tests_total > 0 else "-"

        print(f"{plan_num:>3} {plan_name[:30]:<30} {status_short:<15} [{bar}] {progress:>3.0f}% {tests_str:>10}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show plan implementation progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Plan number to show progress for"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Show progress for all plans"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Summary view (one line per plan)"
    )
    parser.add_argument(
        "--plans-dir",
        type=Path,
        default=Path("docs/plans_archived"),
        help="Plans directory (default: docs/plans)"
    )

    args = parser.parse_args()

    if not args.plans_dir.exists():
        print(f"Error: Plans directory not found: {args.plans_dir}")
        return 1

    if args.summary or (args.all and not args.plan):
        show_summary(args.plans_dir)
        return 0

    if args.plan:
        plan_files = [f for f in find_plan_files(args.plans_dir)
                      if f.name.startswith(f"{args.plan:02d}_") or f.name.startswith(f"{args.plan}_")]
        if not plan_files:
            print(f"Error: Plan #{args.plan} not found")
            return 1
        show_plan_progress(plan_files[0])
        return 0

    if args.all:
        for plan_file in find_plan_files(args.plans_dir):
            show_plan_progress(plan_file)
            print()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
