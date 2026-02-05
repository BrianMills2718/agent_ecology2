"""Simulation module - orchestrates the agent ecology simulation."""

from .runner import SimulationRunner
from .checkpoint import save_checkpoint, load_checkpoint
from .types import (
    PrincipalConfig,
    BalanceInfo,
    CheckpointData,
)
from .agent_loop import (
    AgentLoop, AgentLoopManager, AgentLoopConfig,
    AgentState, WakeCondition, AgentProtocol
)
from .artifact_loop import (  # Plan #255
    ArtifactLoop, ArtifactLoopManager, ArtifactLoopConfig, ArtifactState
)

__all__ = [
    "SimulationRunner",
    "save_checkpoint",
    "load_checkpoint",
    "PrincipalConfig",
    "BalanceInfo",
    "CheckpointData",
    "AgentLoop",
    "AgentLoopManager",
    "AgentLoopConfig",
    "AgentState",
    "WakeCondition",
    "AgentProtocol",
    # Plan #255: Artifact loops
    "ArtifactLoop",
    "ArtifactLoopManager",
    "ArtifactLoopConfig",
    "ArtifactState",
]
