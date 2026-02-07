"""Configuration loader for Agent Ecology

All configurable values come from config/config.yaml.
No magic numbers in code - everything is configurable.

Configuration is validated at load time using Pydantic.
Typos and invalid values fail fast with clear error messages.

Usage:
    from config import load_config, get, get_validated_config

    # Load and validate (call once at startup)
    load_config("config/config.yaml")

    # Get values by dot-path
    cost = get("costs.per_1k_input_tokens")

    # Or use the typed config object (preferred)
    config = get_validated_config()
    cost = config.costs.per_1k_input_tokens
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path
from typing import Any, TypedDict

from .config_schema import AppConfig, load_validated_config, validate_config_dict


class PerAgentQuota(TypedDict):
    """Per-agent resource quotas computed from distribution."""

    llm_tokens_quota: int
    disk_quota: int
    llm_budget_quota: float


# Global config instances
_config: dict[str, Any] | None = None
_validated_config: AppConfig | None = None

# Default config path
DEFAULT_CONFIG_PATH: Path = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load and validate configuration from YAML file.

    Validates the config against the Pydantic schema. Invalid configs
    raise a ValidationError with details about what's wrong.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml.

    Returns:
        Configuration dictionary (for backward compatibility).

    Raises:
        FileNotFoundError: If config file doesn't exist.
        pydantic.ValidationError: If config is invalid.
    """
    global _config, _validated_config

    path: Path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    # Load and validate with Pydantic
    _validated_config = load_validated_config(path)

    # Also keep raw dict for backward compatibility
    with open(path) as f:
        loaded: Any = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            loaded = {}
        _config = loaded

    return _config


def get_config() -> dict[str, Any]:
    """Get the loaded configuration dict. Loads default if not already loaded.

    For typed access, use get_validated_config() instead.
    """
    global _config
    if _config is None:
        load_config()
    if _config is None:
        raise RuntimeError("Config failed to load. Call load_config() first.")
    return _config


def get_validated_config() -> AppConfig:
    """Get the validated configuration object.

    Returns a typed AppConfig instance with IDE autocompletion support.
    Loads default config if not already loaded.
    """
    global _validated_config
    if _validated_config is None:
        load_config()
    if _validated_config is None:
        raise RuntimeError("Validated config failed to load. Call load_config() first.")
    return _validated_config


def get(key: str, default: Any = None) -> Any:
    """Get a config value by dot-separated key path.

    Examples:
        get("resources.stock.llm_budget.total")
        get("costs.actions.noop")
        get("genesis.ledger.methods.transfer.cost")
    """
    config: dict[str, Any] = get_config()
    keys: list[str] = key.split(".")

    value: Any = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value

