#!/usr/bin/env python3
"""Check that mocked tests have corresponding real tests.

Mock test policy:
- Real tests are REQUIRED (marked @pytest.mark.external)
- Mock tests are OPTIONAL (named _mocked suffix)
- Every _mocked test must have a real counterpart

Usage:
    python scripts/check_mock_tests.py          # List mocked tests
    python scripts/check_mock_tests.py --list   # List all test functions
    python scripts/check_mock_tests.py --strict # Fail if violations found
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def find_test_functions(test_dir: Path) -> dict[str, list[tuple[str, bool, bool]]]:
    """Find all test functions in test files.

    Returns:
        Dict mapping file path to list of (func_name, is_mocked, has_external_marker)
    """
    results: dict[str, list[tuple[str, bool, bool]]] = {}

    for test_file in test_dir.glob("test_*.py"):
        functions: list[tuple[str, bool, bool]] = []

        try:
            tree = ast.parse(test_file.read_text())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                is_mocked = node.name.endswith("_mocked")

                # Check for @pytest.mark.external decorator
                has_external = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        # @pytest.mark.external
                        if decorator.attr == "external":
                            has_external = True
                    elif isinstance(decorator, ast.Call):
                        # @pytest.mark.external()
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == "external":
                                has_external = True

                functions.append((node.name, is_mocked, has_external))

        if functions:
            results[str(test_file)] = functions

    return results


def check_mock_policy(test_functions: dict[str, list[tuple[str, bool, bool]]]) -> list[str]:
    """Check that mocked tests have real counterparts.

    Returns list of violation messages.
    """
    violations: list[str] = []

    for file_path, functions in test_functions.items():
        # Get all function names (without _mocked suffix for comparison)
        func_names = {name.replace("_mocked", ""): (name, is_mocked, has_external)
                      for name, is_mocked, has_external in functions}

        for name, is_mocked, has_external in functions:
            if is_mocked:
                # Check for corresponding real test
                base_name = name.replace("_mocked", "")
                if base_name not in func_names or func_names[base_name][1]:
                    # No real test or real test is also mocked
                    violations.append(
                        f"{file_path}: {name} has no real test counterpart {base_name}"
                    )

    return violations


def list_tests(test_functions: dict[str, list[tuple[str, bool, bool]]]) -> None:
    """Print all test functions with their status."""
    print("Test Functions:")
    print("-" * 60)

    for file_path, functions in sorted(test_functions.items()):
        print(f"\n{file_path}:")
        for name, is_mocked, has_external in sorted(functions):
            status = []
            if is_mocked:
                status.append("mocked")
            if has_external:
                status.append("external")
            status_str = f" [{', '.join(status)}]" if status else ""
            print(f"  {name}{status_str}")


def main() -> int:
    """Main entry point."""
    test_dir = Path("tests")

    if not test_dir.exists():
        print("ERROR: tests/ directory not found")
        return 1

    test_functions = find_test_functions(test_dir)

    if "--list" in sys.argv:
        list_tests(test_functions)
        return 0

    violations = check_mock_policy(test_functions)

    # Count mocked tests
    mocked_count = sum(
        1 for funcs in test_functions.values()
        for _, is_mocked, _ in funcs if is_mocked
    )

    print(f"Found {mocked_count} mocked test(s)")

    if violations:
        print(f"\nViolations ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")

        if "--strict" in sys.argv:
            print("\nFailed: mocked tests must have real counterparts")
            return 1
        else:
            print("\nRun with --strict to fail on violations")
    else:
        print("All mocked tests have real counterparts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
