#!/usr/bin/env python3
"""Check that source files are assigned to features.

Scans acceptance_gates/*.yaml for code: sections and compares against actual
source files in src/ and scripts/. Reports unassigned files.

Exit codes:
- 0: All source files are assigned to features
- 1: Some source files are unassigned
- 2: Warning only (when using --warn-only)

Usage:
    python scripts/check_feature_coverage.py
    python scripts/check_feature_coverage.py --warn-only
    python scripts/check_feature_coverage.py --show-assigned
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def load_feature_files(features_dir: Path) -> dict[str, dict[str, Any]]:
    """Load all feature files and return as dict keyed by feature name."""
    features: dict[str, dict[str, Any]] = {}

    if not features_dir.exists():
        return features

    for path in list(features_dir.glob("*.yaml")) + list(features_dir.glob("*.yml")):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                if data and "feature" in data:
                    features[data["feature"]] = data
        except (yaml.YAMLError, FileNotFoundError):
            continue

    return features


def extract_assigned_files(features: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Extract file -> feature mapping from all features."""
    assigned: dict[str, str] = {}

    for feature_name, data in features.items():
        code_files = data.get("code", [])
        for filepath in code_files:
            # Normalize path
            normalized = str(Path(filepath))
            assigned[normalized] = feature_name

    return assigned


def find_source_files(
    source_dirs: list[Path], exclude_patterns: list[str]
) -> list[Path]:
    """Find all Python source files in given directories."""
    source_files: list[Path] = []

    for source_dir in source_dirs:
        if not source_dir.exists():
            continue

        for path in source_dir.rglob("*.py"):
            # Skip excluded patterns
            path_str = str(path)
            skip = False
            for pattern in exclude_patterns:
                if pattern in path_str:
                    skip = True
                    break
            if skip:
                continue

            # Skip __pycache__ and similar
            if "__pycache__" in path_str:
                continue

            source_files.append(path)

    return source_files


def check_coverage(
    features_dir: Path,
    source_dirs: list[Path],
    exclude_patterns: list[str],
) -> tuple[dict[str, str], list[Path]]:
    """Check feature coverage and return assigned files and unassigned files."""
    features = load_feature_files(features_dir)
    assigned = extract_assigned_files(features)
    source_files = find_source_files(source_dirs, exclude_patterns)

    unassigned: list[Path] = []
    for source_file in source_files:
        normalized = str(source_file)
        if normalized not in assigned:
            unassigned.append(source_file)

    return assigned, unassigned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that source files are assigned to features"
    )
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=Path("features"),
        help="Directory containing feature files",
    )
    parser.add_argument(
        "--source-dirs",
        type=str,
        nargs="+",
        default=["src", "scripts"],
        help="Directories to scan for source files",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=["__init__.py", "conftest.py"],
        help="Patterns to exclude from coverage check",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit with warning (2) instead of error (1) for unassigned files",
    )
    parser.add_argument(
        "--show-assigned",
        action="store_true",
        help="Show assigned files as well as unassigned",
    )

    args = parser.parse_args()

    source_dirs = [Path(d) for d in args.source_dirs]
    assigned, unassigned = check_coverage(
        args.features_dir, source_dirs, args.exclude or []
    )

    # Print assigned files if requested
    if args.show_assigned:
        print("=== Assigned Files ===")
        for filepath, feature in sorted(assigned.items()):
            print(f"  ✓ {filepath} -> {feature}")
        print()

    # Print unassigned files
    if unassigned:
        print("=== Unassigned Files ===")
        for filepath in sorted(unassigned):
            print(f"  ✗ {filepath}")
        print()

    # Summary
    total_files = len(assigned) + len(unassigned)
    assigned_count = len(assigned)
    unassigned_count = len(unassigned)

    if total_files == 0:
        print("No source files found")
        return 0

    coverage_pct = (assigned_count / total_files) * 100 if total_files > 0 else 0

    print(f"Coverage: {assigned_count}/{total_files} files ({coverage_pct:.1f}%)")

    if unassigned_count > 0:
        print(f"\n{unassigned_count} file(s) not assigned to any feature")
        print("Add these files to a feature's 'code:' section in acceptance_gates/*.yaml")

        if args.warn_only:
            return 2
        return 1

    print("✓ All source files are assigned to features")
    return 0


if __name__ == "__main__":
    sys.exit(main())
