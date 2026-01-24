"""Checkpoint save/load functionality for simulation state.

Plan #163: Checkpoint Completeness
- Version 1: Original format (event_number, balances, artifacts, agent_ids, reason)
- Version 2: Added agent_states for behavioral continuity, atomic writes
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..world import World
from ..agents import Agent

from .types import CheckpointData, BalanceInfo, AgentCheckpointState

# Current checkpoint format version
CHECKPOINT_VERSION = 2


def save_checkpoint(
    world: World,
    agents: list[Agent],
    cumulative_cost: float,
    config: dict[str, Any],
    reason: str,
) -> str:
    """Save simulation state to checkpoint file for later resumption.

    Uses atomic write (temp file + rename) to prevent corruption from
    partial writes during interruption.

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

    # Build agent states for behavioral continuity (Plan #163)
    agent_states: dict[str, AgentCheckpointState] = {}
    for agent in agents:
        agent_states[agent.agent_id] = agent.export_state()  # type: ignore[assignment]

    checkpoint: CheckpointData = {
        "version": CHECKPOINT_VERSION,
        "event_number": world.event_number,
        "tick": world.event_number,  # Legacy alias for backward compat
        "balances": world.ledger.get_all_balances(),
        "cumulative_api_cost": cumulative_cost,
        "artifacts": [a.to_dict() for a in world.artifacts.artifacts.values()],
        "agent_ids": [a.agent_id for a in agents],
        "agent_states": agent_states,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }

    # Atomic write: write to temp file, then rename (Plan #163 Phase 2)
    # os.rename is atomic on POSIX systems
    temp_file = f"{checkpoint_file}.tmp"
    with open(temp_file, "w") as f:
        json.dump(checkpoint, f, indent=2)

    # Atomic rename - if interrupted here, original checkpoint remains valid
    os.replace(temp_file, checkpoint_file)

    return checkpoint_file


def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate version 1 checkpoint to version 2 format.

    Version 1 lacks agent_states - we add empty state dicts.
    """
    data["version"] = 2
    data["agent_states"] = {
        agent_id: {}
        for agent_id in data.get("agent_ids", [])
    }
    return data


def load_checkpoint(checkpoint_file: str) -> CheckpointData | None:
    """Load simulation state from checkpoint file.

    Handles version migration for older checkpoint formats.

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

    # Check version and migrate if needed (Plan #163 Phase 3)
    version = data.get("version", 1)
    if version == 1:
        data = _migrate_v1_to_v2(data)

    # Parse balances - handle both old format (int) and new format (BalanceInfo dict)
    raw_balances: dict[str, Any] = data["balances"]
    balances: dict[str, BalanceInfo] = {}
    for agent_id, balance_data in raw_balances.items():
        if isinstance(balance_data, dict):
            # Support both old "compute" key and new "llm_tokens" key
            llm_tokens_raw = balance_data.get("llm_tokens", balance_data.get("compute", 0))
            llm_tokens = int(llm_tokens_raw) if llm_tokens_raw is not None else 0
            balances[agent_id] = {
                "llm_tokens": llm_tokens,
                "scrip": int(balance_data.get("scrip", 0)),
            }
        else:
            # Legacy format: just scrip value as int
            balances[agent_id] = {"llm_tokens": 0, "scrip": int(balance_data)}

    # Parse agent states (v2+)
    agent_states: dict[str, AgentCheckpointState] = {}
    raw_agent_states = data.get("agent_states", {})
    for agent_id, state_data in raw_agent_states.items():
        if isinstance(state_data, dict):
            agent_states[agent_id] = state_data  # type: ignore[assignment]
        else:
            agent_states[agent_id] = {}  # type: ignore[assignment]

    # Support both event_number and legacy tick field
    event_num = int(data.get("event_number", data.get("tick", 0)))
    checkpoint: CheckpointData = {
        "version": int(data.get("version", 2)),
        "event_number": event_num,
        "tick": event_num,  # Legacy alias for backward compat
        "balances": balances,
        "cumulative_api_cost": float(data["cumulative_api_cost"]),
        "artifacts": list(data["artifacts"]),
        "agent_ids": list(data["agent_ids"]),
        "agent_states": agent_states,
        "reason": str(data["reason"]),
    }

    # Include timestamp if present
    if "timestamp" in data:
        checkpoint["timestamp"] = str(data["timestamp"])

    return checkpoint


def restore_agent_states(agents: list[Agent], checkpoint: CheckpointData) -> None:
    """Restore agent runtime state from checkpoint.

    Matches agents by agent_id and restores their behavioral state
    (action history, metrics, etc.) for continuity after resume.

    Args:
        agents: List of Agent instances to restore
        checkpoint: CheckpointData with agent_states
    """
    agent_states = checkpoint.get("agent_states", {})

    for agent in agents:
        state = agent_states.get(agent.agent_id)
        if state:
            # Cast to dict[str, Any] since AgentCheckpointState is a TypedDict
            agent.restore_state(dict(state))
