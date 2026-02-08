#!/usr/bin/env python3
"""Meta-process weight configuration (Plan #218).

This module provides weight-aware check control for the meta-process.
Scripts can check if specific checks are enabled at the current weight level.

Usage:
    from meta_process_config import Weight, get_weight, check_enabled

    if check_enabled("doc_coupling_strict", Weight.MEDIUM):
        run_strict_doc_coupling()

Weight levels (highest to lowest):
    HEAVY   - Full enforcement, all checks blocking
    MEDIUM  - Balanced, most checks run (default)
    LIGHT   - Low friction, warnings instead of blocks
    MINIMAL - Almost nothing, just plan validation
"""

from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml


class Weight(IntEnum):
    """Meta-process weight levels (higher = more enforcement)."""

    MINIMAL = 0
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3


# Check definitions: check_name -> minimum weight required
# Checks are enabled at this weight level and above
CHECK_WEIGHTS: dict[str, Weight] = {
    # Always enabled (even at minimal)
    "plan_validation": Weight.MINIMAL,
    # Enabled at light and above
    "plan_required_for_commits": Weight.LIGHT,
    "doc_coupling_warning": Weight.LIGHT,
    "context_injection": Weight.LIGHT,
    "test_requirements": Weight.LIGHT,
    # Enabled at medium and above
    "doc_coupling_strict": Weight.MEDIUM,
    "adr_governance_headers": Weight.MEDIUM,
    "stale_plan_warning": Weight.MEDIUM,
    "pre_merge_gates": Weight.MEDIUM,
    # Enabled only at heavy
    "bidirectional_prompts": Weight.HEAVY,
    "symbol_level_checks": Weight.HEAVY,
}


def load_config() -> dict[str, Any]:
    """Load meta-process configuration from meta-process.yaml."""
    config_path = Path("meta-process.yaml")

    # Try worktree root first, then current directory
    if not config_path.exists():
        # Check if we're in a subdirectory
        for parent in Path.cwd().parents:
            candidate = parent / "meta-process.yaml"
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_weight() -> Weight:
    """Get the configured meta-process weight level.

    Returns:
        Weight enum value. Defaults to MEDIUM if not configured.
    """
    config = load_config()
    weight_str = config.get("weight", "medium")

    if isinstance(weight_str, str):
        try:
            return Weight[weight_str.upper()]
        except KeyError:
            # Unknown weight, default to medium
            return Weight.MEDIUM

    return Weight.MEDIUM


def get_override(check_name: str) -> str | None:
    """Get override setting for a specific check.

    Args:
        check_name: Name of the check to look up

    Returns:
        "strict", "disabled", or None if no override
    """
    config = load_config()
    overrides = config.get("overrides", {})

    if overrides is None:
        return None

    return overrides.get(check_name)


def check_enabled(check_name: str, min_weight: Weight | None = None) -> bool:
    """Check if a specific check is enabled at current weight.

    Args:
        check_name: Name of the check (must be in CHECK_WEIGHTS or min_weight provided)
        min_weight: Optional override for minimum weight (uses CHECK_WEIGHTS if not provided)

    Returns:
        True if the check is enabled, False otherwise

    Raises:
        ValueError: If check_name not in CHECK_WEIGHTS and min_weight not provided
    """
    # Check for explicit override first
    override = get_override(check_name)
    if override == "disabled":
        return False
    if override == "strict":
        return True

    # Get minimum weight for this check
    if min_weight is None:
        if check_name not in CHECK_WEIGHTS:
            raise ValueError(
                f"Unknown check '{check_name}'. "
                f"Valid checks: {list(CHECK_WEIGHTS.keys())}"
            )
        min_weight = CHECK_WEIGHTS[check_name]

    # Compare current weight to minimum required
    current_weight = get_weight()
    return current_weight >= min_weight


def get_enabled_checks() -> list[str]:
    """Get list of all checks enabled at current weight.

    Returns:
        List of check names that are enabled
    """
    return [name for name in CHECK_WEIGHTS if check_enabled(name)]


def get_disabled_checks() -> list[str]:
    """Get list of all checks disabled at current weight.

    Returns:
        List of check names that are disabled
    """
    return [name for name in CHECK_WEIGHTS if not check_enabled(name)]


def weight_description(weight: Weight) -> str:
    """Get human-readable description of a weight level.

    Args:
        weight: Weight level to describe

    Returns:
        Description string
    """
    descriptions = {
        Weight.MINIMAL: "Minimal - Almost nothing enforced, just plan validation",
        Weight.LIGHT: "Light - Low friction, warnings instead of blocks",
        Weight.MEDIUM: "Medium - Balanced enforcement, most checks run",
        Weight.HEAVY: "Heavy - Full enforcement, all checks blocking",
    }
    return descriptions.get(weight, "Unknown weight level")


def print_weight_status() -> None:
    """Print current weight status and enabled/disabled checks."""
    weight = get_weight()
    print(f"Meta-Process Weight: {weight.name}")
    print(f"  {weight_description(weight)}")
    print()

    enabled = get_enabled_checks()
    disabled = get_disabled_checks()

    if enabled:
        print("Enabled checks:")
        for check in enabled:
            override = get_override(check)
            suffix = " (override: strict)" if override == "strict" else ""
            print(f"  - {check}{suffix}")

    if disabled:
        print("\nDisabled checks:")
        for check in disabled:
            override = get_override(check)
            suffix = " (override: disabled)" if override == "disabled" else ""
            print(f"  - {check}{suffix}")


def main() -> None:
    """CLI entry point for checking weight status."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check meta-process weight configuration"
    )
    parser.add_argument(
        "--check",
        help="Check if a specific check is enabled",
        metavar="CHECK_NAME",
    )
    parser.add_argument(
        "--weight",
        help="Show current weight level only",
        action="store_true",
    )
    parser.add_argument(
        "--list-checks",
        help="List all available checks and their minimum weights",
        action="store_true",
    )

    args = parser.parse_args()

    if args.check:
        try:
            enabled = check_enabled(args.check)
            print(f"{args.check}: {'enabled' if enabled else 'disabled'}")
        except ValueError as e:
            print(f"Error: {e}")
            return
    elif args.weight:
        print(get_weight().name.lower())
    elif args.list_checks:
        print("Available checks and minimum weights:")
        for check, min_weight in sorted(CHECK_WEIGHTS.items(), key=lambda x: x[1]):
            print(f"  {check}: {min_weight.name}")
    else:
        print_weight_status()


if __name__ == "__main__":
    main()
