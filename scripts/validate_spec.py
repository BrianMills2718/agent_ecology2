#!/usr/bin/env python3
"""Validate feature specification files.

Checks that feature files in features/*.yaml meet minimum requirements:
- At least 3 acceptance criteria scenarios
- Given/When/Then format for each scenario
- Design section required for detailed planning mode
- Design section optional for autonomous/guided modes

Exit codes:
- 0: All validations passed
- 1: Validation failed
- 2: Warning (non-blocking issues)

Usage:
    python scripts/validate_spec.py --all
    python scripts/validate_spec.py --feature escrow
    python scripts/validate_spec.py --file features/escrow.yaml
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


class ValidationError:
    """Represents a validation error."""

    def __init__(self, feature: str, message: str, severity: str = "error"):
        self.feature = feature
        self.message = message
        self.severity = severity  # "error" or "warning"

    def __str__(self) -> str:
        prefix = "ERROR" if self.severity == "error" else "WARNING"
        return f"[{prefix}] {self.feature}: {self.message}"


def load_feature_file(path: Path) -> dict[str, Any]:
    """Load and parse a feature YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def validate_acceptance_criteria(
    feature_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate acceptance criteria section."""
    errors: list[ValidationError] = []

    ac = data.get("acceptance_criteria", [])

    if not ac:
        errors.append(
            ValidationError(feature_name, "Missing acceptance_criteria section")
        )
        return errors

    # Check minimum scenarios (AC-1)
    if len(ac) < 3:
        errors.append(
            ValidationError(
                feature_name,
                f"Need at least 3 acceptance criteria, found {len(ac)}",
            )
        )

    # Check for category coverage (AC-1: happy_path, error_case, edge_case)
    # Categories can be specified via 'category' field or inferred from scenario name
    categories_found: set[str] = set()
    required_categories = {"happy_path", "error_case", "edge_case"}

    for criterion in ac:
        category = criterion.get("category", "").lower()
        scenario = criterion.get("scenario", "").lower()

        # Check explicit category
        if category:
            categories_found.add(category)
        # Infer from scenario name
        if "happy" in scenario or "success" in scenario or "valid" in scenario:
            categories_found.add("happy_path")
        if "error" in scenario or "fail" in scenario or "invalid" in scenario:
            categories_found.add("error_case")
        if "edge" in scenario or "boundary" in scenario or "limit" in scenario:
            categories_found.add("edge_case")

    missing_categories = required_categories - categories_found
    if missing_categories:
        errors.append(
            ValidationError(
                feature_name,
                f"Missing scenario categories: {', '.join(sorted(missing_categories))}. "
                "Consider adding scenarios for happy_path, error_case, and edge_case coverage.",
                severity="warning",
            )
        )

    # Check Given/When/Then format for each scenario (AC-1)
    for i, criterion in enumerate(ac):
        ac_id = criterion.get("id", f"AC-{i+1}")

        if "scenario" not in criterion:
            errors.append(
                ValidationError(feature_name, f"{ac_id}: Missing 'scenario' field")
            )

        if "given" not in criterion:
            errors.append(
                ValidationError(feature_name, f"{ac_id}: Missing 'given' field")
            )

        if "when" not in criterion:
            errors.append(
                ValidationError(feature_name, f"{ac_id}: Missing 'when' field")
            )

        if "then" not in criterion:
            errors.append(
                ValidationError(feature_name, f"{ac_id}: Missing 'then' field")
            )

        # Check 'then' has specific assertions
        then_clause = criterion.get("then", [])
        if isinstance(then_clause, list) and len(then_clause) == 0:
            errors.append(
                ValidationError(
                    feature_name, f"{ac_id}: 'then' clause has no assertions"
                )
            )

    return errors


def validate_design_section(
    feature_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate design section based on planning mode."""
    errors: list[ValidationError] = []

    planning_mode = data.get("planning_mode", "guided")
    has_design = "design" in data and data["design"] is not None

    # AC-5: Require design for detailed mode
    if planning_mode == "detailed" and not has_design:
        errors.append(
            ValidationError(
                feature_name,
                "planning_mode is 'detailed' but design section is missing",
            )
        )

    # AC-4: Allow autonomous mode without design (no error)
    # Guided mode: design is optional (no error either way)

    # If design exists, validate its structure
    if has_design:
        design = data["design"]

        if "approach" not in design:
            errors.append(
                ValidationError(
                    feature_name,
                    "design section missing 'approach' field",
                    severity="warning",
                )
            )

        if "key_decisions" not in design:
            errors.append(
                ValidationError(
                    feature_name,
                    "design section missing 'key_decisions' field",
                    severity="warning",
                )
            )

    return errors


def validate_required_fields(
    feature_name: str, data: dict[str, Any]
) -> list[ValidationError]:
    """Validate required top-level fields."""
    errors: list[ValidationError] = []

    if "feature" not in data:
        errors.append(ValidationError(feature_name, "Missing 'feature' field"))

    if "problem" not in data:
        errors.append(ValidationError(feature_name, "Missing 'problem' field"))

    if "out_of_scope" not in data:
        errors.append(
            ValidationError(
                feature_name,
                "Missing 'out_of_scope' field",
                severity="warning",
            )
        )

    return errors


def validate_feature_file(path: Path) -> list[ValidationError]:
    """Validate a single feature file."""
    feature_name = path.stem

    try:
        data = load_feature_file(path)
    except yaml.YAMLError as e:
        return [ValidationError(feature_name, f"Invalid YAML: {e}")]
    except FileNotFoundError:
        return [ValidationError(feature_name, f"File not found: {path}")]

    if data is None:
        return [ValidationError(feature_name, "Empty file")]

    errors: list[ValidationError] = []
    errors.extend(validate_required_fields(feature_name, data))
    errors.extend(validate_acceptance_criteria(feature_name, data))
    errors.extend(validate_design_section(feature_name, data))

    return errors


def find_feature_files(features_dir: Path) -> list[Path]:
    """Find all feature YAML files."""
    if not features_dir.exists():
        return []
    return list(features_dir.glob("*.yaml")) + list(features_dir.glob("*.yml"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate feature specification files")
    parser.add_argument("--all", action="store_true", help="Validate all feature files")
    parser.add_argument("--feature", type=str, help="Validate a specific feature by name")
    parser.add_argument("--file", type=Path, help="Validate a specific file path")
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=Path("features"),
        help="Directory containing feature files",
    )

    args = parser.parse_args()

    if not any([args.all, args.feature, args.file]):
        parser.print_help()
        return 1

    files_to_validate: list[Path] = []

    if args.file:
        files_to_validate.append(args.file)
    elif args.feature:
        feature_path = args.features_dir / f"{args.feature}.yaml"
        if not feature_path.exists():
            feature_path = args.features_dir / f"{args.feature}.yml"
        files_to_validate.append(feature_path)
    elif args.all:
        files_to_validate = find_feature_files(args.features_dir)
        if not files_to_validate:
            print(f"No feature files found in {args.features_dir}")
            return 0

    all_errors: list[ValidationError] = []
    for path in files_to_validate:
        errors = validate_feature_file(path)
        all_errors.extend(errors)

    # Print results
    has_errors = False
    has_warnings = False

    for error in all_errors:
        print(error)
        if error.severity == "error":
            has_errors = True
        else:
            has_warnings = True

    # Summary
    if not all_errors:
        print(f"✓ All {len(files_to_validate)} feature file(s) valid")
        return 0

    error_count = sum(1 for e in all_errors if e.severity == "error")
    warning_count = sum(1 for e in all_errors if e.severity == "warning")
    print(f"\nValidation complete: {error_count} error(s), {warning_count} warning(s)")

    if has_errors:
        return 1
    elif has_warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
