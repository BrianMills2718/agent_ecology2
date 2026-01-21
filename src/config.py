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


# Resource helpers
def get_stock_resource(name: str, field: str = "total") -> Any:
    """Get a stock resource config value."""
    return get(f"resources.stock.{name}.{field}")


def get_genesis_config(artifact: str, field: str) -> Any:
    """Get a genesis artifact config value."""
    return get(f"genesis.{artifact}.{field}")


# Computed defaults based on distribution
def compute_per_agent_quota(num_agents: int) -> PerAgentQuota:
    """Compute per-agent quotas based on distribution type and total resources.

    Args:
        num_agents: Number of agents to distribute resources among.

    Returns:
        Dict with llm_tokens_quota, disk_quota, llm_budget_quota.

    Note: llm_tokens_quota is derived from rate_limiting config.
    """
    if num_agents <= 0:
        num_agents = 1

    config = get_validated_config()

    # LLM tokens quota from rate_limiting (time-based)
    # Default to a sensible value if not configured
    llm_tokens_total = int(config.rate_limiting.resources.llm_tokens.max_per_window)
    if llm_tokens_total > 1_000_000:  # Effectively unlimited
        llm_tokens_total = 1000  # Use reasonable default for quota calculation

    # Disk (stock resource) - total, distributed equally
    disk_total = int(config.resources.stock.disk.total)

    # LLM budget (stock resource) - total $, distributed equally
    llm_total = config.resources.stock.llm_budget.total

    return {
        "llm_tokens_quota": llm_tokens_total // num_agents,
        "disk_quota": disk_total // num_agents,
        "llm_budget_quota": llm_total / num_agents,
    }


def set_config_value(key: str, value: Any) -> None:
    """Set a config value by dot-separated key path.

    Used for runtime overrides (e.g., CLI args).
    Does NOT re-validate - use with caution.

    Args:
        key: Dot-separated key path (e.g., "world.max_ticks")
        value: Value to set
    """
    global _config, _validated_config

    if _config is None:
        load_config()

    if _config is None:
        raise RuntimeError("Config failed to load. Call load_config() first.")

    keys = key.split(".")
    target = _config

    # Navigate to parent
    for k in keys[:-1]:
        if k not in target:
            target[k] = {}
        target = target[k]

    # Set the value
    target[keys[-1]] = value

    # Re-validate the config
    _validated_config = validate_config_dict(_config)
