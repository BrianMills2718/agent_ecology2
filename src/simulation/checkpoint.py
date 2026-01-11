"""Checkpoint save/load functionality for simulation state."""

import json
from pathlib import Path
from typing import Any

from ..world import World
from ..agents import Agent

from .types import CheckpointData, BalanceInfo


def save_checkpoint(
    world: World,
    agents: list[Agent],
    cumulative_cost: float,
    config: dict[str, Any],
    reason: str,
) -> str:
    """Save simulation state to checkpoint file for later resumption.

    Args:
        world: The World instance to checkpoint
        agents: List of Agent instances
        cumulative_cost: Total API cost so far
        config: Configuration dictionary (for checkpoint file path)
        reason: Reason for checkpointing (e.g., "budget_exhausted")

    Returns:
        Path to the saved checkpoint file
    """
    checkpoint_file: str = config.get("budget", {}).get(
        "checkpoint_file", "checkpoint.json"
    )
    checkpoint: CheckpointData = {
        "tick": world.tick,
        "balances": world.ledger.get_all_balances(),
        "cumulative_api_cost": cumulative_cost,
        "artifacts": [a.to_dict() for a in world.artifacts.artifacts.values()],
        "agent_ids": [a.agent_id for a in agents],
        "reason": reason,
    }
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f, indent=2)
    return checkpoint_file


def load_checkpoint(checkpoint_file: str) -> CheckpointData | None:
    """Load simulation state from checkpoint file.

    Args:
        checkpoint_file: Path to the checkpoint JSON file.

    Returns:
        CheckpointData dict if file exists and is valid, None otherwise.
    """
    checkpoint_path: Path = Path(checkpoint_file)
    if not checkpoint_path.exists():
        return None

    with open(checkpoint_path) as f:
        data: dict[str, Any] = json.load(f)

    # Parse balances - handle both old format (int) and new format (BalanceInfo dict)
    raw_balances: dict[str, Any] = data["balances"]
    balances: dict[str, BalanceInfo] = {}
    for agent_id, balance_data in raw_balances.items():
        if isinstance(balance_data, dict):
            balances[agent_id] = {
                "compute": int(balance_data.get("compute", 0)),
                "scrip": int(balance_data.get("scrip", 0)),
            }
        else:
            # Legacy format: just scrip value as int
            balances[agent_id] = {"compute": 0, "scrip": int(balance_data)}

    checkpoint: CheckpointData = {
        "tick": int(data["tick"]),
        "balances": balances,
        "cumulative_api_cost": float(data["cumulative_api_cost"]),
        "artifacts": list(data["artifacts"]),
        "agent_ids": list(data["agent_ids"]),
        "reason": str(data["reason"]),
    }
    return checkpoint
