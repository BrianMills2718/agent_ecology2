#!/usr/bin/env python3
"""Read meta-process configuration.

Provides a simple interface for reading meta-process.yaml settings.
Used by hooks and scripts to check if features are enabled.

Usage:
    # Python
    from scripts.meta_config import get_config, is_hook_enabled
    if is_hook_enabled("protect_main"):
        ...

    # CLI
    python scripts/meta_config.py --hook protect_main  # exits 0 if enabled, 1 if not
    python scripts/meta_config.py --get hooks.protect_main  # prints value
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def get_repo_root() -> Path:
    """Get repository root directory."""
    # Try git first
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fall back to script location
    return Path(__file__).parent.parent


def get_config() -> dict[str, Any]:
    """Load meta-process.yaml configuration.

    Returns empty dict if file doesn't exist (all defaults apply).
    """
    config_path = get_repo_root() / "meta-process.yaml"
    if not config_path.exists():
        return {}

    try:
        return yaml.safe_load(config_path.read_text()) or {}
    except yaml.YAMLError:
        return {}


def get_value(key_path: str, default: Any = None) -> Any:
    """Get a config value by dot-separated path.

    Example:
        get_value("hooks.protect_main", True)
        get_value("workflow.stale_claim_hours", 8)
    """
    config = get_config()
    keys = key_path.split(".")

    value = config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default

        if value is None:
            return default

    return value


def is_hook_enabled(hook_name: str) -> bool:
    """Check if a hook is enabled.

    Hooks default to True if not specified in config.
    """
    return get_value(f"hooks.{hook_name}", True)


def is_enforcement_enabled(enforcement_name: str) -> bool:
    """Check if an enforcement setting is enabled.

    Enforcement settings default to True if not specified.
    """
    return get_value(f"enforcement.{enforcement_name}", True)


def get_workflow_setting(setting_name: str, default: Any = None) -> Any:
    """Get a workflow setting."""
    return get_value(f"workflow.{setting_name}", default)


def main() -> None:
    """CLI interface for meta_config."""
    parser = argparse.ArgumentParser(description="Read meta-process configuration")
    parser.add_argument(
        "--hook",
        help="Check if hook is enabled (exits 0 if yes, 1 if no)",
    )
    parser.add_argument(
        "--get",
        help="Get config value by dot-path (e.g., hooks.protect_main)",
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump entire config as YAML",
    )

    args = parser.parse_args()

    if args.hook:
        enabled = is_hook_enabled(args.hook)
        sys.exit(0 if enabled else 1)

    if args.get:
        value = get_value(args.get)
        if value is None:
            sys.exit(1)
        print(value)
        sys.exit(0)

    if args.dump:
        config = get_config()
        print(yaml.dump(config, default_flow_style=False))
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
