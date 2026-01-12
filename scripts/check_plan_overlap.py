#!/usr/bin/env python3
"""Check for file overlaps between plans.

Prevents conflicting PRs by detecting when multiple plans modify the same files.

Usage:
    python scripts/check_plan_overlap.py              # Show all overlaps
    python scripts/check_plan_overlap.py --overlaps   # Same as above
    python scripts/check_plan_overlap.py --plan 3     # Show files for plan 3
    python scripts/check_plan_overlap.py --file path  # Show plans touching file
    python scripts/check_plan_overlap.py --check 3    # Check if plan 3 overlaps with active claims
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_files_from_plan(plan_path: Path) -> set[str]:
    """Extract file paths mentioned in a plan's markdown tables.

    Looks for patterns like:
    - | `src/foo.py` | ... |
    - | src/foo.py | ... |
    - | File | ... | where File column contains paths
    """
    files: set[str] = set()
    content = plan_path.read_text()

    # Pattern for table rows with file paths
    # Matches: | `path` | or | path |
    table_pattern = re.compile(r'\|\s*`?([a-zA-Z0-9_./\-*]+\.[a-zA-Z0-9]+)`?\s*\|')

    for match in table_pattern.finditer(content):
        path = match.group(1)
        # Filter out obvious non-file patterns
        if not path.startswith(('http', '#', '@', '.')):
            files.add(path)

    # Also look for inline code blocks with file paths
    inline_pattern = re.compile(r'`([a-zA-Z0-9_./\-]+\.[a-zA-Z0-9]+)`')
    for match in inline_pattern.finditer(content):
        path = match.group(1)
        if '/' in path and not path.startswith('http'):
            files.add(path)

    return files


def get_plan_number(plan_path: Path) -> int | None:
    """Extract plan number from filename like 03_docker_isolation.md."""
    name = plan_path.stem
    match = re.match(r'^(\d+)_', name)
    if match:
        return int(match.group(1))
    return None


def load_all_plans(plans_dir: Path) -> dict[int, tuple[str, set[str]]]:
    """Load all plan files and their associated files.

    Returns:
        Dict mapping plan number to (plan_name, set of files)
    """
    plans: dict[int, tuple[str, set[str]]] = {}

    for plan_file in plans_dir.glob("*.md"):
        if plan_file.name == "CLAUDE.md":
            continue

        plan_num = get_plan_number(plan_file)
        if plan_num is None:
            continue

        files = extract_files_from_plan(plan_file)
        plans[plan_num] = (plan_file.stem, files)

    return plans


def find_overlaps(plans: dict[int, tuple[str, set[str]]]) -> list[tuple[int, int, set[str]]]:
    """Find overlapping files between plans.

    Returns:
        List of (plan1, plan2, overlapping_files) tuples
    """
    overlaps: list[tuple[int, int, set[str]]] = []
    plan_nums = sorted(plans.keys())

    for i, plan1 in enumerate(plan_nums):
        for plan2 in plan_nums[i + 1:]:
            _, files1 = plans[plan1]
            _, files2 = plans[plan2]
            common = files1 & files2
            if common:
                overlaps.append((plan1, plan2, common))

    return overlaps


def show_overlaps(plans: dict[int, tuple[str, set[str]]]) -> None:
    """Display all file overlaps between plans."""
    overlaps = find_overlaps(plans)

    if not overlaps:
        print("No file overlaps found between plans.")
        return

    print(f"Found {len(overlaps)} plan overlap(s):\n")

    for plan1, plan2, files in overlaps:
        name1, _ = plans[plan1]
        name2, _ = plans[plan2]
        print(f"Plan #{plan1} ({name1}) and Plan #{plan2} ({name2}):")
        for f in sorted(files):
            print(f"  - {f}")
        print()


def show_plan_files(plans: dict[int, tuple[str, set[str]]], plan_num: int) -> None:
    """Show files touched by a specific plan."""
    if plan_num not in plans:
        print(f"Plan #{plan_num} not found")
        return

    name, files = plans[plan_num]
    print(f"Plan #{plan_num} ({name}) touches {len(files)} file(s):\n")
    for f in sorted(files):
        print(f"  - {f}")


def show_file_plans(plans: dict[int, tuple[str, set[str]]], file_path: str) -> None:
    """Show which plans touch a specific file."""
    touching: list[tuple[int, str]] = []

    for plan_num, (name, files) in plans.items():
        if file_path in files:
            touching.append((plan_num, name))

    if not touching:
        print(f"No plans touch {file_path}")
        return

    print(f"Plans touching {file_path}:\n")
    for plan_num, name in sorted(touching):
        print(f"  - Plan #{plan_num} ({name})")


def check_overlap_with_active(plans: dict[int, tuple[str, set[str]]], plan_num: int) -> bool:
    """Check if plan overlaps with active work claims.

    Returns True if no conflicts, False if conflicts found.
    """
    # Read active claims from YAML
    claims_file = Path(".claude/active-work.yaml")
    if not claims_file.exists():
        print("No active claims found")
        return True

    import yaml
    claims = yaml.safe_load(claims_file.read_text()) or {}
    active_plans = [
        c.get("plan") for c in claims.get("claims", [])
        if c.get("plan") and c.get("plan") != plan_num
    ]

    if not active_plans:
        print("No other active plan claims")
        return True

    if plan_num not in plans:
        print(f"Plan #{plan_num} not found")
        return False

    _, files = plans[plan_num]
    conflicts: list[tuple[int, set[str]]] = []

    for other_plan in active_plans:
        if other_plan in plans:
            _, other_files = plans[other_plan]
            common = files & other_files
            if common:
                conflicts.append((other_plan, common))

    if not conflicts:
        print(f"Plan #{plan_num} has no file conflicts with active claims")
        return True

    print(f"Plan #{plan_num} has file conflicts:\n")
    for other_plan, common_files in conflicts:
        other_name, _ = plans[other_plan]
        print(f"  Conflicts with Plan #{other_plan} ({other_name}):")
        for f in sorted(common_files):
            print(f"    - {f}")

    return False


def main() -> int:
    """Main entry point."""
    plans_dir = Path("docs/plans")

    if not plans_dir.exists():
        print("ERROR: docs/plans/ directory not found")
        return 1

    plans = load_all_plans(plans_dir)

    if "--plan" in sys.argv:
        idx = sys.argv.index("--plan")
        if idx + 1 < len(sys.argv):
            plan_num = int(sys.argv[idx + 1])
            show_plan_files(plans, plan_num)
            return 0

    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            file_path = sys.argv[idx + 1]
            show_file_plans(plans, file_path)
            return 0

    if "--check" in sys.argv:
        idx = sys.argv.index("--check")
        if idx + 1 < len(sys.argv):
            plan_num = int(sys.argv[idx + 1])
            success = check_overlap_with_active(plans, plan_num)
            return 0 if success else 1

    # Default: show all overlaps
    show_overlaps(plans)
    return 0


if __name__ == "__main__":
    sys.exit(main())
