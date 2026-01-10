"""Configuration loader for Agent Ecology

All configurable values come from config/config.yaml.
No magic numbers in code - everything is configurable.

See config/schema.yaml for documentation of each field.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, TypedDict


class PerAgentQuota(TypedDict):
    """Per-agent resource quotas computed from distribution."""

    compute_quota: int
    disk_quota: int
    llm_budget_quota: float


# Global config instance
_config: dict[str, Any] | None = None

# Default config path
DEFAULT_CONFIG_PATH: Path = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml.

    Returns:
        Configuration dictionary.
    """
    global _config

    path: Path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        loaded: Any = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            raise TypeError(f"Config file must contain a dict, got {type(loaded)}")
        _config = loaded

    return _config


def get_config() -> dict[str, Any]:
    """Get the loaded configuration. Loads default if not already loaded."""
    global _config
    if _config is None:
        load_config()
    assert _config is not None
    return _config


def get(key: str, default: Any = None) -> Any:
    """Get a config value by dot-separated key path.

    Examples:
        get("resources.stock.llm_budget.total")
        get("costs.actions.noop")
        get("genesis.ledger.transfer_fee")
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


def get_flow_resource(name: str, field: str = "per_tick") -> Any:
    """Get a flow resource config value."""
    return get(f"resources.flow.{name}.{field}")


# Cost helpers
def get_action_cost(action: str) -> int:
    """Get the cost for an action type."""
    cost: Any = get(f"costs.actions.{action}", get("costs.default", 1))
    return int(cost) if cost is not None else 1


def get_genesis_config(artifact: str, field: str) -> Any:
    """Get a genesis artifact config value."""
    return get(f"genesis.{artifact}.{field}")


# Computed defaults based on distribution
def compute_per_agent_quota(num_agents: int) -> PerAgentQuota:
    """Compute per-agent quotas based on distribution type and total resources.

    Args:
        num_agents: Number of agents to distribute resources among.

    Returns:
        Dict with compute_quota, disk_quota, llm_budget_quota.
    """
    if num_agents <= 0:
        num_agents = 1

    # Compute (flow resource) - per tick, distributed equally by default
    compute_total: int = get_flow_resource("compute", "per_tick") or 1000
    compute_dist: str = get_flow_resource("compute", "distribution") or "equal"

    # Disk (stock resource) - total, distributed equally by default
    disk_total: int = get_stock_resource("disk", "total") or 50000
    disk_dist: str = get_stock_resource("disk", "distribution") or "equal"

    # LLM budget (stock resource) - total $, distributed equally by default
    llm_total: float = get_stock_resource("llm_budget", "total") or 1.00
    llm_dist: str = get_stock_resource("llm_budget", "distribution") or "equal"

    # Equal distribution (only type supported for now)
    # Note: compute_dist, disk_dist, llm_dist are read but only "equal" is implemented
    _ = (compute_dist, disk_dist, llm_dist)  # Acknowledge unused variables

    return {
        "compute_quota": compute_total // num_agents,
        "disk_quota": disk_total // num_agents,
        "llm_budget_quota": llm_total / num_agents,
    }
