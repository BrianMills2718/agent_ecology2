"""Genesis Artifacts Package

Genesis artifacts are special artifacts that:
1. Are owned by "system" (cannot be modified by agents)
2. Act as proxies to kernel functions (ledger, mint)
3. Have special cost rules (some functions are free)

These enable agents to interact with core infrastructure through
the same invoke_artifact mechanism they use for agent-created artifacts.

This package provides backward-compatible imports from the original genesis.py.
"""

# Base classes and utilities
from .base import (
    SYSTEM_OWNER,
    GenesisArtifact,
    GenesisMethod,
    _get_error_message,
)

# Type definitions
from .types import (
    # Common types
    MethodInfo,
    GenesisArtifactDict,
    # Ledger types
    BalanceResult,
    AllBalancesResult,
    TransferResult,
    SpawnPrincipalResult,
    TransferOwnershipResult,
    # Mint types
    MintStatusResult,
    SubmissionInfo,
    SubmitResult,
    CheckResult,
    ProcessResult,
    BidInfo,
    AuctionResult,
    # Rights registry types
    QuotaInfo,
    GenericQuotaInfo,
    CheckQuotaResult,
    AllQuotasResult,
    TransferQuotaResult,
    # Event log types
    ReadEventsResult,
    # Escrow types
    EscrowListing,
    EscrowDepositResult,
    EscrowPurchaseResult,
    # Debt types
    DebtRecord,
    DebtIssueResult,
    DebtCheckResult,
    # Store types
    StoreListResult,
    StoreGetResult,
    StoreSearchResult,
    StoreCountResult,
    # Factory types
    RightsConfig,
)

# Genesis artifact classes
from .ledger import GenesisLedger
from .mint import GenesisMint
from .rights_registry import GenesisRightsRegistry
from .event_log import GenesisEventLog
from .escrow import GenesisEscrow
from .debt_contract import GenesisDebtContract
from .store import GenesisStore
from .model_registry import GenesisModelRegistry
from .embedder import GenesisEmbedder  # Plan #146
from .memory import GenesisMemory  # Plan #146

# Factory function
from .factory import create_genesis_artifacts

__all__ = [
    # Base
    "SYSTEM_OWNER",
    "GenesisArtifact",
    "GenesisMethod",
    "_get_error_message",
    # Common types
    "MethodInfo",
    "GenesisArtifactDict",
    # Ledger types
    "BalanceResult",
    "AllBalancesResult",
    "TransferResult",
    "SpawnPrincipalResult",
    "TransferOwnershipResult",
    # Mint types
    "MintStatusResult",
    "SubmissionInfo",
    "SubmitResult",
    "CheckResult",
    "ProcessResult",
    "BidInfo",
    "AuctionResult",
    # Rights registry types
    "QuotaInfo",
    "GenericQuotaInfo",
    "CheckQuotaResult",
    "AllQuotasResult",
    "TransferQuotaResult",
    # Event log types
    "ReadEventsResult",
    # Escrow types
    "EscrowListing",
    "EscrowDepositResult",
    "EscrowPurchaseResult",
    # Debt types
    "DebtRecord",
    "DebtIssueResult",
    "DebtCheckResult",
    # Store types
    "StoreListResult",
    "StoreGetResult",
    "StoreSearchResult",
    "StoreCountResult",
    # Factory types
    "RightsConfig",
    # Genesis artifact classes
    "GenesisLedger",
    "GenesisMint",
    "GenesisRightsRegistry",
    "GenesisEventLog",
    "GenesisEscrow",
    "GenesisDebtContract",
    "GenesisStore",
    "GenesisModelRegistry",
    "GenesisEmbedder",  # Plan #146
    "GenesisMemory",  # Plan #146
    # Factory
    "create_genesis_artifacts",
]
