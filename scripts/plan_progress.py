#!/usr/bin/env python3
"""Show progress on plan implementation.

Two modes of operation:

1. LEGACY MODE (default): Parses plan files for tests/checks/steps completion
2. TASK MODE (--tasks): Computes status from git history - Plan #118

Usage:
    # Legacy: Show progress for plan #1
    python scripts/plan_progress.py --plan 1

    # Legacy: Show progress for all plans
    python scripts/plan_progress.py --all --summary

    # Task mode: Compute status from git history (Plan #118)
    python scripts/plan_progress.py --plan 100 --tasks

    # Task mode: Include pending PR in calculation
    python scripts/plan_progress.py --plan 100 --tasks --include-pr 400

    # Task mode: JSON output for tooling
    python scripts/plan_progress.py --plan 100 --tasks --json

    # Task mode: Validate PR matches a plan task (for CI)
    python scripts/plan_progress.py --plan 100 --validate-pr 400
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


PLANS_DIR = Path("docs/plans")
FUZZY_THRESHOLD = 0.6  # Minimum similarity score for fuzzy matching


# =============================================================================
# LEGACY MODE CLASSES (default)
# =============================================================================


@dataclass
class ProgressMetrics:
    """Progress metrics for a plan (legacy mode)."""
    tests_exist: int
    tests_total: int
    checks_done: int
    checks_total: int
    steps_done: int
    steps_total: int


# =============================================================================
# TASK MODE CLASSES (Plan #118 - git-based status)
# =============================================================================


@dataclass
class Task:
    """A task defined in a plan file using <!-- tasks --> markers."""

    name: str
    phase: str
    gap_id: str | None = None
    completed: bool = False
    pr_number: int | None = None
    pr_merged_at: str | None = None


@dataclass
class PlanStatus:
    """Computed status for a plan from git history."""

    plan_number: int
    title: str
    tasks: list[Task] = field(default_factory=list)
    prs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.completed)

    def to_json(self) -> str:
        """Return JSON representation."""
        return json.dumps(
            {
                "plan_number": self.plan_number,
                "title": self.title,
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks,
                "tasks": [
                    {
                        "name": t.name,
                        "phase": t.phase,
                        "gap_id": t.gap_id,
                        "completed": t.completed,
                        "pr_number": t.pr_number,
                        "pr_merged_at": t.pr_merged_at,
                    }
                    for t in self.tasks
                ],
                "prs": self.prs,
            },
            indent=2,
        )

    def print_status(self) -> None:
        """Print human-readable status."""
        print(f"\nPlan #{self.plan_number} - {self.title}")
        print("=" * 60)

        if not self.tasks:
            print("\nNo task markers found in plan.")
            print("Add <!-- tasks:phaseName --> markers to enable tracking.")
            return

        # Group tasks by phase
        phases: dict[str, list[Task]] = {}
        for task in self.tasks:
            if task.phase not in phases:
                phases[task.phase] = []
            phases[task.phase].append(task)

        for phase_name, phase_tasks in phases.items():
            completed = sum(1 for t in phase_tasks if t.completed)
            total = len(phase_tasks)
            print(f"\n{phase_name}: ({completed}/{total} complete)")

            for task in phase_tasks:
                status = "✅" if task.completed else "❌"
                pr_info = ""
                if task.pr_number:
                    pr_info = f"  PR #{task.pr_number}"
                    if task.pr_merged_at:
                        pr_info += f"  {task.pr_merged_at[:10]}"
                print(f"  {status} {task.name}{pr_info}")

        print()


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


# =============================================================================
# TASK MODE FUNCTIONS (Plan #118 - git-based status)
# =============================================================================


def find_plan_file(plan_num: int) -> Path | None:
    """Find the plan file for a given plan number."""
    for pattern in [f"{plan_num}_*.md", f"0{plan_num}_*.md"]:
        matches = list(PLANS_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None


def parse_plan_tasks(plan_file: Path) -> list[Task]:
    """Parse tasks from a plan file using <!-- tasks:phase --> markers."""
    content = plan_file.read_text()
    tasks: list[Task] = []

    # Find all task blocks: <!-- tasks:phaseName --> ... <!-- /tasks -->
    pattern = r"<!--\s*tasks:(\w+)\s*-->\n(.*?)<!--\s*/tasks\s*-->"
    for match in re.finditer(pattern, content, re.DOTALL):
        phase = match.group(1)
        block = match.group(2)

        # Extract top-level bullet points (- Task name)
        # Ignore sub-bullets (lines starting with more than one space before -)
        for line in block.split("\n"):
            # Match lines starting with "- " (top-level bullets only)
            task_match = re.match(r"^-\s+(.+)$", line)
            if task_match:
                task_text = task_match.group(1).strip()

                # Extract GAP ID if present: "Task name (GAP-XXX-NNN)" or "(GAP-123)"
                gap_match = re.search(r"\(?(GAP-[A-Z]*-?\d+)\)?", task_text)
                gap_id = gap_match.group(1) if gap_match else None

                # Clean task name (remove GAP ID suffix)
                name = re.sub(r"\s*\(?GAP-[A-Z]*-?\d+\)?$", "", task_text).strip()

                tasks.append(Task(name=name, phase=phase, gap_id=gap_id))

    return tasks


def get_merged_prs_for_plan(plan_num: int) -> list[dict[str, Any]]:
    """Get all merged PRs for a plan using gh CLI."""
    try:
        # Search for merged PRs with [Plan #N] in title
        result = subprocess.run(
            [
                "gh", "pr", "list",
                "--state", "merged",
                "--search", f"[Plan #{plan_num}] in:title",
                "--json", "number,title,body,mergedAt",
                "--limit", "100",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout else []
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return []


def get_pr_info(pr_num: int) -> dict[str, Any] | None:
    """Get info for a specific PR."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_num), "--json", "number,title,body,mergedAt"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout else None
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def fuzzy_match(
    pr_title: str,
    task_name: str,
    pr_body: str = "",
    task_gap_id: str | None = None,
) -> bool:
    """Check if a PR matches a task using fuzzy matching.

    Matching strategies:
    1. Task name is substring of PR title (case-insensitive)
    2. Fuzzy similarity score above threshold
    3. GAP ID appears in PR body
    """
    pr_title_lower = pr_title.lower()
    task_name_lower = task_name.lower()

    # Strategy 1: Substring match
    if task_name_lower in pr_title_lower:
        return True

    # Strategy 2: Fuzzy similarity
    # Compare words to handle reordering
    pr_words = set(re.findall(r"\w+", pr_title_lower))
    task_words = set(re.findall(r"\w+", task_name_lower))

    # Check if most task words appear in PR title
    if task_words:
        overlap = len(task_words & pr_words) / len(task_words)
        if overlap >= FUZZY_THRESHOLD:
            return True

    # Also try sequence matching on full strings
    ratio = SequenceMatcher(None, pr_title_lower, task_name_lower).ratio()
    if ratio >= FUZZY_THRESHOLD:
        return True

    # Strategy 3: GAP ID match
    if task_gap_id and task_gap_id in pr_body:
        return True

    return False


def compute_plan_status(
    plan_num: int,
    include_pr: int | None = None,
) -> PlanStatus:
    """Compute status for a plan by matching PRs to tasks."""
    plan_file = find_plan_file(plan_num)
    if not plan_file:
        return PlanStatus(plan_number=plan_num, title="Plan not found", tasks=[])

    # Extract title from plan file
    content = plan_file.read_text()
    title_match = re.search(r"^#\s*(?:Plan\s*\d+[:\s]*)?(.+?)(?:\n|$)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else plan_file.stem

    # Parse tasks
    tasks = parse_plan_tasks(plan_file)

    # Get merged PRs
    prs = get_merged_prs_for_plan(plan_num)

    # Add pending PR if specified
    if include_pr:
        pending = get_pr_info(include_pr)
        if pending:
            prs.append(pending)

    # Match PRs to tasks
    for task in tasks:
        for pr in prs:
            if fuzzy_match(
                pr.get("title", ""),
                task.name,
                pr.get("body", ""),
                task.gap_id,
            ):
                task.completed = True
                task.pr_number = pr.get("number")
                task.pr_merged_at = pr.get("mergedAt")
                break  # First match wins

    return PlanStatus(
        plan_number=plan_num,
        title=title,
        tasks=tasks,
        prs=prs,
    )


def validate_pr(plan_num: int, pr_num: int) -> bool:
    """Validate that a PR matches a task in the plan.

    Returns True if match found, False otherwise.
    Prints warning if no match.
    """
    plan_file = find_plan_file(plan_num)
    if not plan_file:
        print(f"Warning: Plan #{plan_num} not found")
        return False

    tasks = parse_plan_tasks(plan_file)
    if not tasks:
        # Plan has no task markers - skip validation
        print(f"Plan #{plan_num} has no task markers - skipping validation")
        return True

    pr_info = get_pr_info(pr_num)
    if not pr_info:
        print(f"Warning: Could not fetch PR #{pr_num}")
        return False

    # Check if PR matches any task
    for task in tasks:
        if fuzzy_match(
            pr_info.get("title", ""),
            task.name,
            pr_info.get("body", ""),
            task.gap_id,
        ):
            print(f"✓ PR #{pr_num} matches task: {task.name}")
            return True

    # No match found
    print(f"Warning: PR #{pr_num} does not match any task in Plan #{plan_num}")
    print(f"  PR title: {pr_info.get('title', 'N/A')}")
    print(f"  Available tasks:")
    for task in tasks:
        print(f"    - {task.name}")
    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


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
        default=Path("docs/plans"),
        help="Plans directory (default: docs/plans)"
    )

    # Task mode arguments (Plan #118)
    parser.add_argument(
        "--tasks", "-t",
        action="store_true",
        help="Task mode: compute status from git history (Plan #118)"
    )
    parser.add_argument(
        "--include-pr",
        type=int,
        help="(Task mode) Include pending PR in calculation"
    )
    parser.add_argument(
        "--validate-pr",
        type=int,
        help="(Task mode) Validate PR matches a plan task (for CI)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="(Task mode) Output JSON format"
    )

    args = parser.parse_args()

    if not args.plans_dir.exists():
        print(f"Error: Plans directory not found: {args.plans_dir}")
        return 1

    # Task mode: validate PR
    if args.validate_pr:
        if not args.plan:
            print("Error: --validate-pr requires --plan")
            return 1
        success = validate_pr(args.plan, args.validate_pr)
        return 0 if success else 1

    # Task mode: compute status from git
    if args.tasks:
        if not args.plan:
            print("Error: --tasks requires --plan")
            return 1
        status = compute_plan_status(args.plan, include_pr=args.include_pr)
        if args.json:
            print(status.to_json())
        else:
            status.print_status()
        return 0

    # Legacy mode
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
