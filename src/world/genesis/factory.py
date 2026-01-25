"""Genesis Artifacts - Factory function

Creates all genesis artifacts based on configuration.
"""

# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Genesis artifacts: ledger, mint, escrow, event_log, rights_registry, store.
# System-provided, solve cold-start problem. Split into package (Plan #66).
# --- GOVERNANCE END ---
from __future__ import annotations

from typing import Any, Callable

from ...config import get, get_validated_config
from ...config_schema import GenesisConfig
from ..ledger import Ledger
from ..artifacts import ArtifactStore
from ..logger import EventLogger
from .base import GenesisArtifact
from .types import RightsConfig
from .ledger import GenesisLedger
from .mint import GenesisMint
from .rights_registry import GenesisRightsRegistry
from .event_log import GenesisEventLog
from .escrow import GenesisEscrow
from .debt_contract import GenesisDebtContract
from .store import GenesisStore
from .voting import GenesisVoting
from .model_registry import GenesisModelRegistry
from .embedder import GenesisEmbedder
from .memory import GenesisMemory
from ..genesis_contracts import GENESIS_CONTRACTS


def _create_contract_artifacts(artifact_store: ArtifactStore) -> None:
    """Create readable artifacts for genesis contracts (Plan #165).

    These artifacts describe the contract rules in a human-readable format.
    They are not executable - the actual permission checking still uses
    the Python contract classes. This enables:
    - Discovery via genesis_store.list(type="contract")
    - Reading rules via genesis_store.get("genesis_contract_freeware")
    - Filtering by metadata.rules using Plan #168 metadata feature

    Args:
        artifact_store: Store to write contract artifacts to
    """
    # Contract descriptions and rule summaries
    contract_info = {
        "freeware": {
            "description": (
                "Freeware access contract - shared artifact pattern.\n\n"
                "Rules:\n"
                "- READ: Anyone can read\n"
                "- INVOKE: Anyone can invoke\n"
                "- WRITE: Only owner can modify\n"
                "- DELETE: Only owner can delete\n\n"
                "Use for: Shared services, public data, libraries."
            ),
            "rules": {
                "read": "anyone",
                "invoke": "anyone",
                "write": "owner_only",
                "edit": "owner_only",
                "delete": "owner_only",
            },
        },
        "private": {
            "description": (
                "Private access contract - owner-only pattern.\n\n"
                "Rules:\n"
                "- All actions: Only owner allowed\n\n"
                "Use for: Sensitive data, private configurations."
            ),
            "rules": {
                "read": "owner_only",
                "invoke": "owner_only",
                "write": "owner_only",
                "edit": "owner_only",
                "delete": "owner_only",
            },
        },
        "self_owned": {
            "description": (
                "Self-owned access contract - artifact self-access pattern.\n\n"
                "Rules:\n"
                "- Owner: Full access\n"
                "- Artifact itself: Can access itself (caller == target)\n"
                "- Others: Denied\n\n"
                "Use for: Agent memory, private state, self-modifying artifacts."
            ),
            "rules": {
                "read": "owner_or_self",
                "invoke": "owner_or_self",
                "write": "owner_or_self",
                "edit": "owner_or_self",
                "delete": "owner_or_self",
            },
        },
        "public": {
            "description": (
                "Public access contract - true commons pattern.\n\n"
                "Rules:\n"
                "- All actions: Anyone can do anything\n\n"
                "WARNING: Anyone can modify or delete!\n"
                "Use for: Collaborative workspaces, shared resources."
            ),
            "rules": {
                "read": "anyone",
                "invoke": "anyone",
                "write": "anyone",
                "edit": "anyone",
                "delete": "anyone",
            },
        },
    }

    for contract_type, info in contract_info.items():
        contract_id = f"genesis_contract_{contract_type}"
        artifact_store.write(
            artifact_id=contract_id,
            type="contract",
            content=info["description"],
            created_by="system",
            executable=False,
            metadata={"rules": info["rules"], "contract_type": contract_type},
        )


def create_genesis_artifacts(
    ledger: Ledger,
    mint_callback: Callable[[str, int], None],
    artifact_store: ArtifactStore | None = None,
    logger: EventLogger | None = None,
    rights_config: RightsConfig | None = None,
    genesis_config: GenesisConfig | None = None
) -> dict[str, GenesisArtifact]:
    """
    Factory function to create all genesis artifacts.

    Which artifacts are created is controlled by genesis.artifacts config.
    All method costs and descriptions come from config.

    Args:
        ledger: The world's Ledger instance
        mint_callback: Function(agent_id, amount) to mint new scrip
        artifact_store: ArtifactStore for mint to look up artifacts
        logger: EventLogger for genesis_event_log
        rights_config: Dict with 'default_quotas' (preferred) or legacy keys
                       'default_compute_quota', 'default_disk_quota'
        genesis_config: Optional genesis config (uses global if not provided)

    Returns:
        Dict mapping artifact_id -> GenesisArtifact
    """
    # Get config (use provided or load from global)
    cfg = genesis_config or get_validated_config().genesis

    artifacts: dict[str, GenesisArtifact] = {}

    # Create ledger if enabled
    if cfg.artifacts.ledger.enabled:
        genesis_ledger = GenesisLedger(
            ledger,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_ledger.id] = genesis_ledger

    # Create mint if enabled
    if cfg.artifacts.mint.enabled:
        # Create UBI callback using ledger
        def ubi_callback(amount: int, exclude: str | None) -> dict[str, int]:
            return ledger.distribute_ubi(amount, exclude)

        genesis_mint = GenesisMint(
            mint_callback,
            ubi_callback=ubi_callback,
            artifact_store=artifact_store,
            ledger=ledger,
            genesis_config=cfg
        )
        artifacts[genesis_mint.id] = genesis_mint

    # Add event log if enabled and logger provided
    if cfg.artifacts.event_log.enabled and logger:
        genesis_event_log = GenesisEventLog(logger, genesis_config=cfg)
        artifacts[genesis_event_log.id] = genesis_event_log

    # Add rights registry if enabled and config provided
    if cfg.artifacts.rights_registry.enabled and rights_config:
        # Check for new generic format first
        if "default_quotas" in rights_config:
            default_quotas = rights_config["default_quotas"]
        else:
            # Build from legacy keys with config fallback
            # Note: compute uses rate_limiting now (rolling window)
            compute_fallback: int = 50
            disk_fallback: int = get("resources.stock.disk.total") or 10000
            default_llm_tokens = rights_config.get("default_llm_tokens_quota",
                              rights_config.get("default_compute_quota",
                              rights_config.get("default_flow_quota", compute_fallback)))
            default_disk = rights_config.get("default_disk_quota",
                           rights_config.get("default_stock_quota", disk_fallback))
            default_quotas = {
                "llm_tokens": float(default_llm_tokens),
                "disk": float(default_disk)
            }

        genesis_rights = GenesisRightsRegistry(
            default_quotas=default_quotas,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_rights.id] = genesis_rights

    # Add escrow if enabled and artifact_store provided
    if cfg.artifacts.escrow.enabled and artifact_store:
        genesis_escrow = GenesisEscrow(
            ledger=ledger,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_escrow.id] = genesis_escrow

    # Add store if enabled and artifact_store provided
    if cfg.artifacts.store.enabled and artifact_store:
        genesis_store = GenesisStore(
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_store.id] = genesis_store

    # Add debt contract if enabled
    if cfg.artifacts.debt_contract.enabled:
        genesis_debt = GenesisDebtContract(
            ledger=ledger,
            genesis_config=cfg
        )
        artifacts[genesis_debt.id] = genesis_debt

    # Add model registry if enabled (Plan #113)
    if cfg.artifacts.model_registry.enabled:
        genesis_model_registry = GenesisModelRegistry(genesis_config=cfg)
        artifacts[genesis_model_registry.id] = genesis_model_registry

    # Add voting if enabled (Plan #183)
    if cfg.artifacts.voting.enabled:
        genesis_voting = GenesisVoting(genesis_config=cfg)
        artifacts[genesis_voting.id] = genesis_voting

    # Add embedder (Plan #146: Unified Artifact Intelligence)
    # Always enabled for now - provides embedding generation for semantic memory
    genesis_embedder = GenesisEmbedder(genesis_config=cfg)
    artifacts[genesis_embedder.id] = genesis_embedder

    # Add memory manager (Plan #146: Unified Artifact Intelligence)
    # Always enabled for now - provides semantic memory operations
    if artifact_store:
        genesis_memory = GenesisMemory(
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_memory.id] = genesis_memory

    # Add MCP artifacts if any are enabled
    from ..mcp_bridge import create_mcp_artifacts
    mcp_artifacts = create_mcp_artifacts(cfg.mcp)
    for artifact_id, mcp_artifact in mcp_artifacts.items():
        artifacts[artifact_id] = mcp_artifact

    # Plan #165: Create contract artifacts for discoverability
    # These are readable artifacts that describe the genesis contract rules
    if artifact_store:
        _create_contract_artifacts(artifact_store)

    # Add aliases for new naming convention (Plan #44)
    # Maps old names -> new names (both can be used to access same artifact)
    # API wrappers: genesis_*_api - wrap kernel primitives
    # Contracts: genesis_*_contract - pure contract logic
    alias_mapping = {
        "genesis_ledger": "genesis_ledger_api",
        "genesis_mint": "genesis_mint_api",
        "genesis_rights_registry": "genesis_rights_api",
        "genesis_store": "genesis_store_api",
        "genesis_event_log": "genesis_event_log_api",
        "genesis_escrow": "genesis_escrow_contract",
        "genesis_model_registry": "genesis_model_registry_api",
        "genesis_embedder": "genesis_embedder_api",  # Plan #146
        "genesis_memory": "genesis_memory_api",  # Plan #146
    }
    for old_name, new_name in alias_mapping.items():
        if old_name in artifacts:
            artifacts[new_name] = artifacts[old_name]

    return artifacts
