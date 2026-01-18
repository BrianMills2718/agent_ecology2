"""Genesis Artifacts - Type definitions

Shared TypedDict definitions used across genesis artifacts.
"""

from typing import Any, TypedDict


class MethodInfo(TypedDict):
    """Information about a genesis method for listing."""
    name: str
    cost: int
    description: str


class BalanceResult(TypedDict):
    """Result from balance query."""
    success: bool
    agent_id: str
    flow: int
    scrip: int


class AllBalancesResult(TypedDict):
    """Result from all_balances query."""
    success: bool
    balances: dict[str, dict[str, int]]


class TransferResult(TypedDict, total=False):
    """Result from transfer operation."""
    success: bool
    error: str
    transferred: int
    currency: str
    to: str
    from_scrip_after: int
    to_scrip_after: int


class SpawnPrincipalResult(TypedDict, total=False):
    """Result from spawn_principal operation."""
    success: bool
    error: str
    principal_id: str


class MintStatusResult(TypedDict):
    """Result from mint status query."""
    success: bool
    mint: str
    type: str
    pending_submissions: int
    scored_submissions: int
    total_submissions: int


class SubmissionInfo(TypedDict, total=False):
    """Information about a submission."""
    submitter: str
    status: str
    score: int | None
    reason: str | None


class SubmitResult(TypedDict, total=False):
    """Result from submit operation."""
    success: bool
    error: str
    message: str
    receipt: str


class CheckResult(TypedDict, total=False):
    """Result from check operation."""
    success: bool
    error: str
    submission: SubmissionInfo


class ProcessResult(TypedDict, total=False):
    """Result from process operation."""
    success: bool
    message: str
    artifact_id: str
    score: int
    reason: str
    credits_minted: int
    submitter: str
    error: str


class QuotaInfo(TypedDict):
    """Quota information for an agent."""
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class GenericQuotaInfo(TypedDict):
    """Generic quota information for an agent (all resources)."""
    quotas: dict[str, float]
    disk_used: int
    disk_available: int


class CheckQuotaResult(TypedDict, total=False):
    """Result from check_quota operation."""
    success: bool
    error: str
    agent_id: str
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class AllQuotasResult(TypedDict):
    """Result from all_quotas operation."""
    success: bool
    quotas: dict[str, QuotaInfo]


class TransferQuotaResult(TypedDict, total=False):
    """Result from transfer_quota operation."""
    success: bool
    error: str
    transferred: int
    quota_type: str
    to: str
    from_new_quota: int
    to_new_quota: int


class ReadEventsResult(TypedDict):
    """Result from read events operation."""
    success: bool
    events: list[dict[str, Any]]
    count: int
    total_available: int
    warning: str


class GenesisArtifactDict(TypedDict):
    """Dictionary representation of a genesis artifact."""
    id: str
    type: str
    owner_id: str
    content: str
    methods: list[MethodInfo]


class TransferOwnershipResult(TypedDict, total=False):
    """Result from transfer_ownership operation."""
    success: bool
    error: str
    artifact_id: str
    from_owner: str
    to_owner: str


# Mint-specific types
class BidInfo(TypedDict):
    """Information about a bid in the mint auction."""
    agent_id: str
    artifact_id: str
    amount: int
    tick_submitted: int


class AuctionResult(TypedDict):
    """Result of an auction resolution."""
    winner_id: str | None
    artifact_id: str | None
    winning_bid: int
    price_paid: int  # Second-price
    score: int | None
    scrip_minted: int
    ubi_distributed: dict[str, int]
    error: str | None


# Escrow-specific types
class EscrowListing(TypedDict):
    """An active escrow listing."""
    artifact_id: str
    seller_id: str
    price: int
    buyer_id: str | None  # If set, only this buyer can purchase
    status: str  # "active", "completed", "cancelled"


class EscrowDepositResult(TypedDict, total=False):
    """Result from escrow deposit."""
    success: bool
    error: str
    artifact_id: str
    price: int
    seller: str


class EscrowPurchaseResult(TypedDict, total=False):
    """Result from escrow purchase."""
    success: bool
    error: str
    artifact_id: str
    price: int
    seller: str
    buyer: str


# Debt-specific types
class DebtRecord(TypedDict):
    """Record of a debt."""
    debt_id: str
    debtor_id: str
    creditor_id: str
    principal: int
    interest_rate: float
    due_tick: int
    amount_owed: int  # Principal + accrued interest
    amount_paid: int
    status: str  # "pending", "active", "paid", "defaulted"
    created_tick: int


class DebtIssueResult(TypedDict, total=False):
    """Result from debt issue operation."""
    success: bool
    error: str
    debt_id: str
    debtor: str
    creditor: str
    principal: int
    due_tick: int


class DebtCheckResult(TypedDict, total=False):
    """Result from debt check operation."""
    success: bool
    error: str
    debt: DebtRecord


# Store-specific types
class StoreListResult(TypedDict):
    """Result from store list operation."""
    success: bool
    artifacts: list[dict[str, Any]]
    count: int


class StoreGetResult(TypedDict, total=False):
    """Result from store get operation."""
    success: bool
    error: str
    artifact: dict[str, Any]


class StoreSearchResult(TypedDict):
    """Result from store search operation."""
    success: bool
    artifacts: list[dict[str, Any]]
    query: str


class StoreCountResult(TypedDict):
    """Result from store count operation."""
    success: bool
    count: int


# Factory config type
class RightsConfig(TypedDict, total=False):
    """Configuration for rights registry."""
    default_quotas: dict[str, float]  # Generic: {resource: amount}
    default_compute_quota: int  # Legacy
    default_disk_quota: int  # Legacy
    default_flow_quota: int  # Legacy
    default_stock_quota: int  # Legacy
