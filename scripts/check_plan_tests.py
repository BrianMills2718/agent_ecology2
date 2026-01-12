#!/usr/bin/env python3
"""Verify that required tests for a plan exist and pass.

Usage:
    # Check all tests for plan #1
    python scripts/check_plan_tests.py --plan 1

    # TDD mode - show which tests need to be written
    python scripts/check_plan_tests.py --plan 1 --tdd

    # Check all plans with tests defined
    python scripts/check_plan_tests.py --all

    # List plans and their test requirements
    python scripts/check_plan_tests.py --list
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class TestRequirement:
    """A required test for a plan."""
    file: str
    function: str | None = None  # None means all tests in file
    description: str = ""
    is_new: bool = False  # New test to create (TDD) vs existing


@dataclass
class PlanTests:
    """Test requirements for a plan."""
    plan_number: int
    plan_name: str
    plan_file: Path
    status: str
    new_tests: list[TestRequirement] = field(default_factory=list)
    existing_tests: list[TestRequirement] = field(default_factory=list)


def parse_plan_file(plan_file: Path) -> PlanTests | None:
    """Parse a plan file for test requirements."""
    content = plan_file.read_text()

    # Extract plan number from filename
    match = re.match(r"(\d+)_(.+)\.md", plan_file.name)
    if not match:
        return None

    plan_number = int(match.group(1))
    plan_name = match.group(2).replace("_", " ").title()

    # Extract status
    status_match = re.search(r"\*\*Status:\*\*\s*(.+)", content)
    status = status_match.group(1).strip() if status_match else "Unknown"

    plan = PlanTests(
        plan_number=plan_number,
        plan_name=plan_name,
        plan_file=plan_file,
        status=status
    )

    # Find Required Tests section
    tests_section = re.search(
        r"## Required Tests\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL
    )

    if not tests_section:
        return plan

    section_content = tests_section.group(1)

    # Parse New Tests table
    new_tests_match = re.search(
        r"### New Tests.*?\n\|.*?\n\|[-\s|]+\n((?:\|.*?\n)*)",
        section_content,
        re.DOTALL
    )

    if new_tests_match:
        for line in new_tests_match.group(1).strip().split("\n"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2:
                test_file = cells[0].strip("`")
                test_func = cells[1].strip("`") if cells[1] else None
                desc = cells[2] if len(cells) > 2 else ""
                plan.new_tests.append(TestRequirement(
                    file=test_file,
                    function=test_func,
                    description=desc,
                    is_new=True
                ))

    # Parse Existing Tests table
    existing_match = re.search(
        r"### Existing Tests.*?\n\|.*?\n\|[-\s|]+\n((?:\|.*?\n)*)",
        section_content,
        re.DOTALL
    )

    if existing_match:
        for line in existing_match.group(1).strip().split("\n"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 1:
                pattern = cells[0].strip("`")
                desc = cells[1] if len(cells) > 1 else ""

                # Parse pattern - could be file or file::function
                if "::" in pattern:
                    file_part, func_part = pattern.split("::", 1)
                else:
                    file_part, func_part = pattern, None

                plan.existing_tests.append(TestRequirement(
                    file=file_part,
                    function=func_part,
                    description=desc,
                    is_new=False
                ))

    return plan


def find_plan_files(plans_dir: Path) -> list[Path]:
    """Find all plan files."""
    return sorted(
        [f for f in plans_dir.glob("*.md")
         if re.match(r"\d+_", f.name)],
        key=lambda f: int(f.name.split("_")[0])
    )


def check_test_exists(req: TestRequirement, project_root: Path) -> bool:
    """Check if a test file/function exists."""
    test_file = project_root / req.file

    if not test_file.exists():
        return False

    if req.function:
        # Check if function exists in file
        content = test_file.read_text()
        pattern = rf"def\s+{re.escape(req.function)}\s*\("
        return bool(re.search(pattern, content))

    return True


def run_tests(requirements: list[TestRequirement], project_root: Path) -> tuple[int, str]:
    """Run pytest for the given requirements. Returns (exit_code, output)."""
    if not requirements:
        return 0, "No tests to run"

    pytest_args = ["pytest", "-v"]

    for req in requirements:
        if req.function:
            pytest_args.append(f"{req.file}::{req.function}")
        else:
            pytest_args.append(req.file)

    result = subprocess.run(
        pytest_args,
        cwd=project_root,
        capture_output=True,
        text=True
    )

    return result.returncode, result.stdout + result.stderr


def list_plans(plans_dir: Path) -> None:
    """List all plans and their test requirements."""
    for plan_file in find_plan_files(plans_dir):
        plan = parse_plan_file(plan_file)
        if not plan:
            continue

        total_tests = len(plan.new_tests) + len(plan.existing_tests)
        test_info = f"{total_tests} tests" if total_tests else "no tests defined"
        print(f"#{plan.plan_number:2d} {plan.plan_name:30s} {plan.status:20s} ({test_info})")


def check_plan(plan: PlanTests, project_root: Path, tdd_mode: bool = False) -> int:
    """Check tests for a single plan. Returns exit code."""
    print(f"\n{'='*60}")
    print(f"Plan #{plan.plan_number}: {plan.plan_name}")
    print(f"Status: {plan.status}")
    print(f"File: {plan.plan_file}")
    print(f"{'='*60}\n")

    all_requirements = plan.new_tests + plan.existing_tests

    if not all_requirements:
        print("No test requirements defined for this plan.")
        print("Add a '## Required Tests' section to define tests.")
        return 0

    # Check which tests exist
    print("Test Existence Check:")
    print("-" * 40)

    missing_tests: list[TestRequirement] = []
    existing_tests: list[TestRequirement] = []

    for req in all_requirements:
        exists = check_test_exists(req, project_root)
        status = "[EXISTS]" if exists else "[MISSING]"
        test_name = f"{req.file}::{req.function}" if req.function else req.file
        marker = " (NEW)" if req.is_new else ""
        print(f"  {status} {test_name}{marker}")

        if exists:
            existing_tests.append(req)
        else:
            missing_tests.append(req)

    print()

    # TDD Mode: Just report what needs to be written
    if tdd_mode:
        if missing_tests:
            print("TDD Mode - Tests to write:")
            print("-" * 40)
            for req in missing_tests:
                test_name = f"{req.file}::{req.function}" if req.function else req.file
                print(f"  - {test_name}")
                if req.description:
                    print(f"    Purpose: {req.description}")
            return 1
        else:
            print("All required tests exist!")
            print("Run without --tdd to execute them.")
            return 0

    # Normal mode: Run existing tests
    if missing_tests:
        print("WARNING: Some required tests are missing!")
        print("Use --tdd to see what needs to be written.\n")

    if not existing_tests:
        print("No existing tests to run.")
        return 1 if missing_tests else 0

    print("Running Tests:")
    print("-" * 40)

    exit_code, output = run_tests(existing_tests, project_root)
    print(output)

    if exit_code == 0 and not missing_tests:
        print("\nAll required tests pass!")
        return 0
    elif exit_code == 0:
        print("\nExisting tests pass, but some tests are missing.")
        return 1
    else:
        print("\nSome tests failed!")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify plan test requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Plan number to check (e.g., 1 for plan #1)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Check all plans with test requirements"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all plans and their test status"
    )
    parser.add_argument(
        "--tdd",
        action="store_true",
        help="TDD mode - show which tests need to be written"
    )
    parser.add_argument(
        "--plans-dir",
        type=Path,
        default=Path("docs/plans"),
        help="Plans directory (default: docs/plans)"
    )

    args = parser.parse_args()

    project_root = Path.cwd()
    plans_dir = project_root / args.plans_dir

    if not plans_dir.exists():
        print(f"Error: Plans directory not found: {plans_dir}")
        return 1

    if args.list:
        list_plans(plans_dir)
        return 0

    if args.plan:
        # Find specific plan
        plan_files = [f for f in find_plan_files(plans_dir)
                     if f.name.startswith(f"{args.plan:02d}_") or
                        f.name.startswith(f"{args.plan}_")]

        if not plan_files:
            print(f"Error: No plan found with number {args.plan}")
            return 1

        plan = parse_plan_file(plan_files[0])
        if not plan:
            print(f"Error: Could not parse plan file: {plan_files[0]}")
            return 1

        return check_plan(plan, project_root, args.tdd)

    if args.all:
        exit_code = 0
        for plan_file in find_plan_files(plans_dir):
            plan = parse_plan_file(plan_file)
            if plan and (plan.new_tests or plan.existing_tests):
                result = check_plan(plan, project_root, args.tdd)
                if result != 0:
                    exit_code = 1
        return exit_code

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
