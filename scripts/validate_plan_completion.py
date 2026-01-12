#!/usr/bin/env python3
"""Validate that a plan meets all completion criteria before marking complete.

Usage:
    # Validate plan #1 is ready for completion
    python scripts/validate_plan_completion.py --plan 1

    # Validate all plans marked as complete
    python scripts/validate_plan_completion.py --check-complete

    # Show what's needed to complete a plan
    python scripts/validate_plan_completion.py --plan 1 --verbose
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    name: str
    passed: bool
    message: str


def find_plan_file(plan_number: int, plans_dir: Path) -> Path | None:
    """Find plan file by number."""
    for f in plans_dir.glob("*.md"):
        if f.name.startswith(f"{plan_number:02d}_") or f.name.startswith(f"{plan_number}_"):
            return f
    return None


def get_plan_status(plan_file: Path) -> str:
    """Extract status from plan file."""
    content = plan_file.read_text()
    match = re.search(r"\*\*Status:\*\*\s*(.+)", content)
    return match.group(1).strip() if match else "Unknown"


def get_index_status(plan_number: int, plans_dir: Path) -> str:
    """Extract status from plans/CLAUDE.md index."""
    index_file = plans_dir / "CLAUDE.md"
    if not index_file.exists():
        return "Index not found"

    content = index_file.read_text()
    # Look for row like: | 1 | [Rate Allocation](...) | **High** | 📋 Planned |
    pattern = rf"\|\s*{plan_number}\s*\|[^|]+\|[^|]+\|\s*([^|]+)\s*\|"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else "Not in index"


def check_tests_pass(plan_number: int) -> ValidationResult:
    """Check if plan tests pass."""
    result = subprocess.run(
        ["python", "scripts/check_plan_tests.py", "--plan", str(plan_number)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return ValidationResult("Plan tests", True, "All required tests pass")

    # Check if it's because no tests defined
    if "No test requirements defined" in result.stdout:
        return ValidationResult("Plan tests", True, "No tests defined (OK)")

    # Check for missing tests
    if "MISSING" in result.stdout:
        missing_count = result.stdout.count("[MISSING]")
        return ValidationResult("Plan tests", False, f"{missing_count} required tests missing")

    return ValidationResult("Plan tests", False, "Some tests failing")


def check_doc_coupling() -> ValidationResult:
    """Check if doc-coupling passes."""
    result = subprocess.run(
        ["python", "scripts/check_doc_coupling.py", "--strict"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return ValidationResult("Doc coupling", True, "No violations")

    return ValidationResult("Doc coupling", False, "Coupling violations exist")


def check_pytest() -> ValidationResult:
    """Check if full test suite passes."""
    result = subprocess.run(
        ["pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        # Extract pass count
        match = re.search(r"(\d+) passed", result.stdout)
        count = match.group(1) if match else "?"
        return ValidationResult("Test suite", True, f"{count} tests pass")

    # Extract failure info
    match = re.search(r"(\d+) failed", result.stdout)
    fail_count = match.group(1) if match else "?"
    return ValidationResult("Test suite", False, f"{fail_count} tests failing")


def check_status_consistency(plan_number: int, plan_file: Path, plans_dir: Path) -> ValidationResult:
    """Check if plan file and index have consistent status."""
    file_status = get_plan_status(plan_file)
    index_status = get_index_status(plan_number, plans_dir)

    # Normalize for comparison (remove emoji variations)
    def normalize(s: str) -> str:
        return re.sub(r"[^\w\s]", "", s).strip().lower()

    if normalize(file_status) == normalize(index_status):
        return ValidationResult("Status sync", True, f"Both show: {file_status}")

    return ValidationResult(
        "Status sync", False,
        f"Mismatch - File: {file_status}, Index: {index_status}"
    )


def check_no_todo_comments(plan_number: int) -> ValidationResult:
    """Check for TODO comments referencing this plan."""
    # Search for TODO comments mentioning this plan
    result = subprocess.run(
        ["grep", "-r", "-n", f"TODO.*[Pp]lan.*{plan_number}", "src/", "tests/"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:  # grep returns 1 if no matches
        return ValidationResult("No TODOs", True, "No plan-related TODOs found")

    lines = result.stdout.strip().split("\n")
    return ValidationResult("No TODOs", False, f"{len(lines)} TODO(s) reference this plan")


def validate_plan(plan_number: int, plans_dir: Path, verbose: bool = False) -> bool:
    """Run all validation checks for a plan."""
    plan_file = find_plan_file(plan_number, plans_dir)
    if not plan_file:
        print(f"Error: Plan #{plan_number} not found")
        return False

    print(f"Validating Plan #{plan_number}: {plan_file.stem}")
    print("=" * 60)

    results: list[ValidationResult] = []

    # Run checks
    print("Running checks...")
    results.append(check_tests_pass(plan_number))
    results.append(check_pytest())
    results.append(check_doc_coupling())
    results.append(check_status_consistency(plan_number, plan_file, plans_dir))
    results.append(check_no_todo_comments(plan_number))

    # Print results
    print()
    all_passed = True
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"  {icon} {r.name}: {r.message}")
        if not r.passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ All checks pass - plan ready for completion!")
        return True
    else:
        print("❌ Some checks failed - address issues before marking complete")
        return False


def check_completed_plans(plans_dir: Path) -> int:
    """Validate all plans marked as complete."""
    index_file = plans_dir / "CLAUDE.md"
    if not index_file.exists():
        print("Error: plans/CLAUDE.md not found")
        return 1

    content = index_file.read_text()

    # Find plans marked complete
    complete_pattern = r"\|\s*(\d+)\s*\|[^|]+\|[^|]+\|\s*✅\s*Complete"
    matches = re.findall(complete_pattern, content)

    if not matches:
        print("No plans marked as complete.")
        return 0

    print(f"Checking {len(matches)} completed plan(s)...")
    print()

    failures = 0
    for plan_num in matches:
        if not validate_plan(int(plan_num), plans_dir):
            failures += 1
        print()

    if failures:
        print(f"❌ {failures} completed plan(s) have issues")
        return 1

    print("✅ All completed plans validated successfully")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate plan completion criteria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Plan number to validate"
    )
    parser.add_argument(
        "--check-complete",
        action="store_true",
        help="Validate all plans marked as complete"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
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

    if args.check_complete:
        return check_completed_plans(args.plans_dir)

    if args.plan:
        return 0 if validate_plan(args.plan, args.plans_dir, args.verbose) else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
