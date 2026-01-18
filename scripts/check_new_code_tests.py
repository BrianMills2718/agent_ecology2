#!/usr/bin/env python3
"""Check that new source files have corresponding tests.

Enforces that new .py files in src/ or scripts/ have tests.
This prevents adding code without tests.

Usage:
    python scripts/check_new_code_tests.py                    # Check against origin/main
    python scripts/check_new_code_tests.py --base HEAD~1      # Check against last commit
    python scripts/check_new_code_tests.py --strict           # Fail if missing tests
    python scripts/check_new_code_tests.py --suggest          # Show which tests to create

Exit codes:
    0 - All new files have tests (or no new files)
    1 - Missing tests (strict mode) or error
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# Directories that require tests
REQUIRES_TESTS = ["src/", "scripts/"]

# Files that are exempt from test requirements
EXEMPT_PATTERNS = [
    "__init__.py",
    "conftest.py",
    "CLAUDE.md",
    "_template",
    "setup.py",
    # Genesis package split (Plan #66) - infrastructure files
    "genesis/base.py",  # Abstract base class, tested via subclasses
    "genesis/types.py",  # Pure TypedDicts, no logic to test
    "genesis/factory.py",  # Factory tested via integration tests
]

# Explicit source -> test file mappings for non-standard names
# Used when test file doesn't follow test_{name}.py convention
EXPLICIT_TEST_MAPPINGS: dict[str, str] = {
    "src/world/genesis/mint.py": "tests/integration/test_mint_auction.py",
    "src/world/genesis/store.py": "tests/integration/test_genesis_store.py",
    "src/world/genesis/event_log.py": "tests/unit/test_freeze_events.py",
    "src/world/genesis/rights_registry.py": "tests/unit/test_genesis_invoke.py",
}


def get_new_files(base: str) -> list[Path]:
    """Get list of new files added since base."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", base, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [Path(f) for f in result.stdout.strip().split("\n") if f]
        return files
    except subprocess.CalledProcessError:
        # Fallback: check staged files
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", "--cached"],
            capture_output=True,
            text=True,
        )
        files = [Path(f) for f in result.stdout.strip().split("\n") if f]
        return files


def is_exempt(file_path: Path) -> bool:
    """Check if file is exempt from test requirements."""
    path_str = str(file_path)
    return any(pattern in path_str for pattern in EXEMPT_PATTERNS)


def requires_tests(file_path: Path) -> bool:
    """Check if file requires tests."""
    if not file_path.suffix == ".py":
        return False

    path_str = str(file_path)
    if not any(path_str.startswith(prefix) for prefix in REQUIRES_TESTS):
        return False

    if is_exempt(file_path):
        return False

    return True


def find_test_file(source_file: Path) -> Path | None:
    """Find the corresponding test file for a source file."""
    # Check explicit mappings first
    source_str = str(source_file)
    if source_str in EXPLICIT_TEST_MAPPINGS:
        explicit_path = Path(EXPLICIT_TEST_MAPPINGS[source_str])
        if explicit_path.exists():
            return explicit_path

    # Extract the module name
    name = source_file.stem

    # Possible test file locations
    candidates = [
        Path(f"tests/unit/test_{name}.py"),
        Path(f"tests/integration/test_{name}.py"),
        Path(f"tests/test_{name}.py"),
    ]

    # For scripts, also check the scripts test location
    if str(source_file).startswith("scripts/"):
        candidates.insert(0, Path(f"tests/unit/test_{name}.py"))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def check_test_content(test_file: Path, source_name: str) -> bool:
    """Check if test file actually tests the source file."""
    if not test_file.exists():
        return False

    content = test_file.read_text()

    # Check for import or reference to the source
    indicators = [
        f"from {source_name}",
        f"import {source_name}",
        f"test_{source_name}",
        source_name.replace("_", " "),  # In docstrings
    ]

    return any(indicator in content for indicator in indicators)


def suggest_test_location(source_file: Path) -> str:
    """Suggest where to create a test file."""
    name = source_file.stem

    if str(source_file).startswith("scripts/"):
        return f"tests/unit/test_{name}.py"
    elif str(source_file).startswith("src/world/"):
        return f"tests/unit/test_{name}.py"
    elif str(source_file).startswith("src/agents/"):
        return f"tests/unit/test_{name}.py"
    elif str(source_file).startswith("src/simulation/"):
        return f"tests/integration/test_{name}.py"
    else:
        return f"tests/unit/test_{name}.py"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that new source files have tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base",
        default="origin/main",
        help="Base ref to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if tests are missing",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Show suggested test file locations",
    )

    args = parser.parse_args()

    # Get new files
    new_files = get_new_files(args.base)

    # Filter to files that require tests
    files_needing_tests = [f for f in new_files if requires_tests(f)]

    if not files_needing_tests:
        print("No new source files requiring tests.")
        return 0

    print(f"Checking {len(files_needing_tests)} new source file(s) for tests...\n")

    missing_tests: list[tuple[Path, str]] = []
    has_tests: list[tuple[Path, Path]] = []

    for source_file in files_needing_tests:
        test_file = find_test_file(source_file)

        if test_file:
            has_tests.append((source_file, test_file))
        else:
            suggested = suggest_test_location(source_file)
            missing_tests.append((source_file, suggested))

    # Report files with tests
    if has_tests:
        print("Files with tests:")
        for source, test in has_tests:
            print(f"  ✅ {source} -> {test}")
        print()

    # Report missing tests
    if missing_tests:
        print("=" * 60)
        print("MISSING TESTS")
        print("=" * 60)
        print()
        for source, suggested in missing_tests:
            print(f"  ❌ {source}")
            if args.suggest:
                print(f"     Create: {suggested}")
        print()

        if args.suggest:
            print("Example test template:")
            print('"""Tests for {module}."""')
            print()
            print("import pytest")
            print("from {import_path} import {names}")
            print()
            print("class Test{ClassName}:")
            print('    """Tests for {ClassName}."""')
            print()
            print("    def test_basic(self):")
            print('        """Basic functionality test."""')
            print("        pass")
            print()

        if args.strict:
            print(f"FAILED: {len(missing_tests)} new file(s) missing tests")
            return 1
    else:
        print("All new source files have tests!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
