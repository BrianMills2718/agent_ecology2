"""Configuration loader for Agent Ecology

All configurable values come from config/config.yaml.
No magic numbers in code - everything is configurable.

See config/schema.yaml for documentation of each field.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional

# Global config instance
_config: Optional[Dict[str, Any]] = None

# Default config path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml.

    Returns:
        Configuration dictionary.
    """
    global _config

    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with open(path) as f:
        _config = yaml.safe_load(f)

    return _config


def get_config() -> Dict[str, Any]:
    """Get the loaded configuration. Loads default if not already loaded."""
    global _config
    if _config is None:
        load_config()
    return _config


def get(key: str, default: Any = None) -> Any:
    """Get a config value by dot-separated key path.

    Examples:
        get("resources.stock.llm_budget.total")
        get("costs.actions.noop")
        get("genesis.ledger.transfer_fee")
    """
    config = get_config()
    keys = key.split(".")

    value = config
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
    return get(f"costs.actions.{action}", get("costs.default", 1))


def get_genesis_config(artifact: str, field: str) -> Any:
    """Get a genesis artifact config value."""
    return get(f"genesis.{artifact}.{field}")


# Computed defaults based on distribution
def compute_per_agent_quota(num_agents: int) -> Dict[str, Any]:
    """Compute per-agent quotas based on distribution type and total resources.

    Args:
        num_agents: Number of agents to distribute resources among.

    Returns:
        Dict with compute_quota, disk_quota, llm_budget_quota.
    """
    if num_agents <= 0:
        num_agents = 1

    # Compute (flow resource) - per tick, distributed equally by default
    compute_total = get_flow_resource("compute", "per_tick") or 1000
    compute_dist = get_flow_resource("compute", "distribution") or "equal"

    # Disk (stock resource) - total, distributed equally by default
    disk_total = get_stock_resource("disk", "total") or 50000
    disk_dist = get_stock_resource("disk", "distribution") or "equal"

    # LLM budget (stock resource) - total $, distributed equally by default
    llm_total = get_stock_resource("llm_budget", "total") or 1.00
    llm_dist = get_stock_resource("llm_budget", "distribution") or "equal"

    # Equal distribution (only type supported for now)
    return {
        "compute_quota": compute_total // num_agents,
        "disk_quota": disk_total // num_agents,
        "llm_budget_quota": llm_total / num_agents
    }
