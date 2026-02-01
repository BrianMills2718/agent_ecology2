"""Pydantic schema for configuration validation.

All config values are validated at startup. Typos and invalid values
fail fast with clear error messages.

Usage:
    from config_schema import load_validated_config, AppConfig
    config = load_validated_config("config/config.yaml")
    # config is now a validated AppConfig instance
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, ValidationInfo


# =============================================================================
# BASE MODEL WITH STRICT VALIDATION
# =============================================================================

class StrictModel(BaseModel):
    """Base model that rejects unknown fields (catches typos)."""

    model_config = ConfigDict(extra="forbid")


# =============================================================================
# TIMEOUTS MODEL
# =============================================================================

class TimeoutsConfig(StrictModel):
    """Consolidated timeout values for all components."""

    agent_loop_stop: float = Field(
        default=5.0,
        gt=0,
        description="AgentLoop stop timeout in seconds"
    )
    loop_manager_stop: float = Field(
        default=10.0,
        gt=0,
        description="AgentLoopManager stop_all timeout in seconds"
    )
    simulation_shutdown: float = Field(
        default=5.0,
        gt=0,
        description="SimulationRunner shutdown timeout in seconds"
    )
    mcp_server: float = Field(
        default=5.0,
        gt=0,
        description="MCP server operations timeout in seconds"
    )
    state_store_lock: float = Field(
        default=30.0,
        gt=0,
        description="SQLite lock timeout in seconds"
    )
    state_store_retry_max: int = Field(
        default=10,
        ge=1,
        description="Max retry attempts for SQLite lock errors"
    )
    state_store_retry_base: float = Field(
        default=0.05,
        gt=0,
        description="Base backoff delay in seconds for SQLite retries"
    )
    state_store_retry_max_delay: float = Field(
        default=2.0,
        gt=0,
        description="Maximum backoff delay cap in seconds for SQLite retries"
    )
    dashboard_server: float = Field(
        default=30.0,
        gt=0,
        description="Dashboard server operations timeout in seconds"
    )


# =============================================================================
# RESOURCE MODELS
# =============================================================================

class StockResource(StrictModel):
    """A finite resource pool (doesn't refresh)."""

    total: float = Field(gt=0, description="Total amount of resource")
    unit: str = Field(description="Unit of measurement (e.g., 'bytes', 'dollars')")
    distribution: Literal["equal"] = Field(
        default="equal",
        description="How to distribute among agents"
    )


class StockResources(StrictModel):
    """All stock (finite pool) resources."""

    llm_budget: StockResource = Field(
        default_factory=lambda: StockResource(total=1.0, unit="dollars")
    )
    disk: StockResource = Field(
        default_factory=lambda: StockResource(total=500000, unit="bytes")
    )


class VisibilityDefaults(StrictModel):
    """Default visibility settings for agents."""

    resources: list[str] | None = Field(
        default=None,
        description="Resources to show by default (None = all resources)"
    )
    detail_level: Literal["minimal", "standard", "verbose"] = Field(
        default="standard",
        description="Default detail level: minimal (remaining), standard (core), verbose (all)"
    )
    see_others: bool = Field(
        default=False,
        description="Whether agents see other agents' resources by default"
    )


class VisibilityConfig(StrictModel):
    """Resource visibility configuration (Plan #93)."""

    enabled: bool = Field(
        default=True,
        description="Enable resource visibility in agent context"
    )
    compute_metrics: list[str] = Field(
        default=[
            "remaining", "initial", "spent", "percentage",
            "tokens_in", "tokens_out", "total_requests",
            "avg_cost_per_request", "burn_rate"
        ],
        description="Metrics to compute (affects performance)"
    )
    defaults: VisibilityDefaults = Field(
        default_factory=VisibilityDefaults,
        description="Default visibility settings for agents"
    )


class ResourcesConfig(StrictModel):
    """Resource configuration (stock only - flow resources use rate_limiting)."""

    stock: StockResources = Field(default_factory=StockResources)
    visibility: VisibilityConfig = Field(
        default_factory=VisibilityConfig,
        description="Resource visibility configuration (Plan #93)"
    )


# =============================================================================
# SCRIP MODEL
# =============================================================================

class ScripConfig(StrictModel):
    """Economic currency configuration."""

    starting_amount: int = Field(
        default=100,
        ge=0,
        description="Starting scrip for new agents"
    )


# =============================================================================
# COSTS MODEL
# =============================================================================

class CostsConfig(StrictModel):
    """Token cost configurations.

    DEPRECATED (Plan #153): These abstract "compute cost" rates are deprecated.
    The system now uses actual dollar costs from models.pricing.
    Kept for backward compatibility - will be ignored.
    """

    per_1k_input_tokens: int = Field(
        default=1,
        ge=0,
        description="DEPRECATED - use models.pricing (Plan #153)"
    )
    per_1k_output_tokens: int = Field(
        default=3,
        ge=0,
        description="DEPRECATED - use models.pricing (Plan #153)"
    )


# =============================================================================
# MODEL PRICING (Plan #153)
# =============================================================================

class ModelPricingEntry(StrictModel):
    """Pricing for a specific LLM model.

    Prices are in dollars per 1 million tokens.
    """

    input_per_1m: float = Field(
        default=3.0,
        ge=0,
        description="$ per 1 million input tokens"
    )
    output_per_1m: float = Field(
        default=15.0,
        ge=0,
        description="$ per 1 million output tokens"
    )


class ModelsConfig(StrictModel):
    """Model pricing configuration (Plan #153).

    Used for:
    1. Pre-flight budget checks (can agent afford this call?)
    2. Post-call deductions (actual cost from budget)
    3. Dashboard display (estimated tokens remaining)

    If a model isn't listed, LiteLLM's pricing is used as fallback.
    """

    pricing: dict[str, ModelPricingEntry] = Field(
        default_factory=dict,
        description="Per-model pricing (model_name -> pricing)"
    )
    default_pricing: ModelPricingEntry = Field(
        default_factory=lambda: ModelPricingEntry(input_per_1m=3.0, output_per_1m=15.0),
        description="Fallback pricing for unknown models"
    )


# =============================================================================
# GENESIS ARTIFACTS MODELS
# =============================================================================

class MethodConfig(StrictModel):
    """Configuration for a genesis artifact method."""

    cost: int = Field(default=0, ge=0, description="Compute cost to invoke method (not scrip)")
    description: str = Field(default="", description="Method description for agents")


class ArtifactEnabledConfig(StrictModel):
    """Whether an artifact is enabled."""

    enabled: bool = Field(default=True, description="Enable this artifact")


class GenesisArtifactsEnabled(StrictModel):
    """Which genesis artifacts to create."""

    ledger: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    mint: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    rights_registry: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    event_log: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    escrow: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    # genesis_store removed - use query_kernel action instead (Plan #190)
    debt_contract: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    voting: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)  # Plan #183
    model_registry: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)


class LedgerMethodsConfig(StrictModel):
    """Genesis ledger method configurations."""

    balance: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get flow and scrip balance for an agent. Args: [agent_id]"
        )
    )
    all_balances: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get all agent balances (flow and scrip). Args: []"
        )
    )
    transfer: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer SCRIP to another agent. Args: [from_id, to_id, amount]"
        )
    )
    spawn_principal: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Spawn a new principal with 0 scrip and 0 compute. Args: []"
        )
    )
    transfer_ownership: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer artifact ownership to another principal. Args: [artifact_id, to_id]"
        )
    )
    transfer_budget: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer LLM budget to another agent. Args: [to_id, amount]"
        )
    )
    get_budget: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get LLM budget for an agent. Args: [agent_id]"
        )
    )


class LedgerConfig(StrictModel):
    """Genesis ledger configuration."""

    id: str = Field(default="genesis_ledger", description="Artifact ID")
    description: str = Field(
        default="System ledger - check balances (flow/scrip) and transfer scrip",
        description="Artifact description"
    )
    methods: LedgerMethodsConfig = Field(default_factory=LedgerMethodsConfig)


class MintMethodsConfig(StrictModel):
    """Genesis mint method configurations."""

    status: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check auction status (phase, tick, bid count). Args: []"
        )
    )
    bid: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Submit sealed bid during bidding window. Args: [artifact_id, amount]"
        )
    )
    check: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check your bid/submission status. Args: [artifact_id]"
        )
    )


class MintAuctionConfig(StrictModel):
    """Mint auction configuration."""

    period_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Seconds between auction starts"
    )
    bidding_window_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Duration of bidding phase (seconds)"
    )
    first_auction_delay_seconds: float = Field(
        default=30.0,
        ge=0,
        description="Delay before first auction (0 = start immediately)"
    )
    slots_per_auction: int = Field(
        default=1,
        gt=0,
        description="Number of winners per auction"
    )
    minimum_bid: int = Field(
        default=1,
        gt=0,
        description="Floor bid amount"
    )
    tie_breaking: Literal["random", "first_bid"] = Field(
        default="random",
        description="How to break ties: 'random' or 'first_bid'"
    )
    show_bid_count: bool = Field(
        default=True,
        description="Show number of bids during bidding window"
    )
    allow_bid_updates: bool = Field(
        default=True,
        description="Allow agents to update their bid during window"
    )
    refund_on_scoring_failure: bool = Field(
        default=True,
        description="Refund winner's bid if LLM scoring fails"
    )

    @field_validator("bidding_window_seconds")
    @classmethod
    def bidding_window_less_than_period(cls, v: float, info: ValidationInfo) -> float:
        """Ensure bidding window is less than period."""
        # Note: Can't access period here easily, validated at runtime in MintConfig
        return v


class MintConfig(StrictModel):
    """Genesis mint configuration."""

    id: str = Field(default="genesis_mint", description="Artifact ID")
    description: str = Field(
        default="Auction-based mint - bid to submit artifacts for LLM scoring",
        description="Artifact description"
    )
    mint_ratio: int = Field(
        default=10,
        gt=0,
        description="Divisor for score-to-scrip conversion (score / ratio = scrip)"
    )
    auction: MintAuctionConfig = Field(default_factory=MintAuctionConfig)
    methods: MintMethodsConfig = Field(default_factory=MintMethodsConfig)

    @model_validator(mode="after")
    def validate_bidding_window(self) -> "MintConfig":
        """Ensure bidding window is less than period."""
        if self.auction.bidding_window_seconds >= self.auction.period_seconds:
            raise ValueError(
                f"bidding_window_seconds ({self.auction.bidding_window_seconds}) must be less than "
                f"period_seconds ({self.auction.period_seconds})"
            )
        return self


class RightsRegistryMethodsConfig(StrictModel):
    """Genesis rights registry method configurations."""

    check_quota: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check quotas for an agent. Args: [agent_id]"
        )
    )
    all_quotas: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get all agent quotas. Args: []"
        )
    )
    transfer_quota: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer quota to another agent. Args: [from_id, to_id, 'compute'|'disk', amount]"
        )
    )


class RightsRegistryConfig(StrictModel):
    """Genesis rights registry configuration."""

    id: str = Field(default="genesis_rights_registry", description="Artifact ID")
    description: str = Field(
        default="Rights registry - manage compute and disk quotas",
        description="Artifact description"
    )
    methods: RightsRegistryMethodsConfig = Field(default_factory=RightsRegistryMethodsConfig)


class EventLogMethodsConfig(StrictModel):
    """Genesis event log method configurations."""

    read: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Read recent events. Args: [offset, limit] - both optional. Default: last 50 events."
        )
    )


class EventLogConfig(StrictModel):
    """Genesis event log configuration."""

    id: str = Field(default="genesis_event_log", description="Artifact ID")
    description: str = Field(
        default="World event log - passive observability. Reading is free but costs input tokens.",
        description="Artifact description"
    )
    max_per_read: int = Field(
        default=100,
        gt=0,
        description="Maximum events returned per read"
    )
    buffer_size: int = Field(
        default=1000,
        gt=0,
        description="Maximum events kept in memory"
    )
    methods: EventLogMethodsConfig = Field(default_factory=EventLogMethodsConfig)


class EscrowMethodsConfig(StrictModel):
    """Genesis escrow method configurations."""

    deposit: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Deposit artifact for sale. First transfer ownership to escrow. Args: [artifact_id, price] or [artifact_id, price, buyer_id]"
        )
    )
    purchase: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Purchase a listed artifact. Pays price to seller, transfers ownership to buyer. Args: [artifact_id]"
        )
    )
    cancel: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Cancel listing and return artifact to seller. Only seller can cancel. Args: [artifact_id]"
        )
    )
    check: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check status of an escrow listing. Args: [artifact_id]"
        )
    )
    list_active: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List all active escrow listings. Args: []"
        )
    )


class EscrowConfig(StrictModel):
    """Genesis escrow configuration."""

    id: str = Field(default="genesis_escrow", description="Artifact ID")
    description: str = Field(
        default="Trustless escrow for artifact trading. Seller deposits, buyer purchases, escrow handles exchange.",
        description="Artifact description"
    )
    methods: EscrowMethodsConfig = Field(default_factory=EscrowMethodsConfig)


class DebtContractMethodsConfig(StrictModel):
    """Genesis debt contract method configurations."""

    issue: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Issue a debt. Invoker becomes debtor. Args: [creditor_id, principal, interest_rate, due_tick]"
        )
    )
    accept: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Accept a pending debt (creditor must call). Args: [debt_id]"
        )
    )
    repay: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Repay debt (debtor pays creditor). Args: [debt_id, amount]"
        )
    )
    collect: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Collect overdue debt (creditor only, after due_tick). Args: [debt_id]"
        )
    )
    transfer_creditor: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer creditor rights to another principal (sell the debt). Args: [debt_id, new_creditor_id]"
        )
    )
    check: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check status of a debt. Args: [debt_id]"
        )
    )
    list_debts: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List debts for a principal. Args: [principal_id]"
        )
    )
    list_all: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List all debts. Args: []"
        )
    )


class DebtContractConfig(StrictModel):
    """Genesis debt contract configuration."""

    id: str = Field(default="genesis_debt_contract", description="Artifact ID")
    description: str = Field(
        default="Non-privileged debt contract example. Issue, accept, repay, collect debts. No magic enforcement.",
        description="Artifact description"
    )
    methods: DebtContractMethodsConfig = Field(default_factory=DebtContractMethodsConfig)


class VotingMethodsConfig(StrictModel):
    """Genesis voting method configurations (Plan #183)."""

    create_proposal: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Create a proposal. Args: [{title, description?, options?, quorum?, threshold?, deadline_seconds?}]"
        )
    )
    vote: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Vote on a proposal. Args: [{proposal_id, choice}]"
        )
    )
    get_result: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get proposal results. Args: [proposal_id]"
        )
    )
    list_proposals: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List proposals with optional filter. Args: [{status?, creator?, limit?}]"
        )
    )


class VotingConfig(StrictModel):
    """Genesis voting configuration (Plan #183)."""

    id: str = Field(default="genesis_voting", description="Artifact ID")
    description: str = Field(
        default="Multi-party voting for consensus. Create proposals, vote, track results.",
        description="Artifact description"
    )
    methods: VotingMethodsConfig = Field(default_factory=VotingMethodsConfig)


# genesis_store removed - use query_kernel action instead (Plan #190)
# StoreMethodsConfig and StoreConfig classes removed


# =============================================================================
# MCP SERVER MODELS
# =============================================================================

class McpServerConfig(StrictModel):
    """Configuration for a single MCP server.

    MCP servers run as subprocesses and communicate via JSON-RPC over stdio.
    """

    enabled: bool = Field(
        default=False,
        description="Enable this MCP server"
    )
    command: str = Field(
        default="npx",
        description="Command to start the MCP server"
    )
    args: list[str] = Field(
        default_factory=list,
        description="Arguments to pass to the command"
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the server process"
    )


class McpConfig(StrictModel):
    """MCP server configurations.

    Phase 1 (MVP): fetch, filesystem, web_search
    Phase 2+: puppeteer, sqlite, context7, etc.
    """

    fetch: McpServerConfig = Field(
        default_factory=lambda: McpServerConfig(
            enabled=False,
            command="npx",
            args=["@anthropic/mcp-server-fetch"]
        ),
        description="HTTP fetch capability"
    )
    filesystem: McpServerConfig = Field(
        default_factory=lambda: McpServerConfig(
            enabled=False,
            command="npx",
            args=["@anthropic/mcp-server-filesystem", "/tmp/agent_sandbox"]
        ),
        description="Sandboxed file I/O"
    )
    web_search: McpServerConfig = Field(
        default_factory=lambda: McpServerConfig(
            enabled=False,
            command="npx",
            args=["@anthropic/mcp-server-brave-search"]
        ),
        description="Internet search via Brave Search"
    )


class ModelRegistryMethodsConfig(StrictModel):
    """Genesis model registry method configurations."""

    list_models: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List available models and their properties. Args: []"
        )
    )
    get_quota: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Check agent's quota for a model. Args: [agent_id, model_id]"
        )
    )
    request_access: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Request quota allocation from pool. Args: [agent_id, model_id, amount]"
        )
    )
    release_quota: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Release unused quota back to pool. Args: [agent_id, model_id, amount]"
        )
    )
    transfer_quota: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=1,
            description="Transfer quota to another agent. Args: [to_agent, model_id, amount]"
        )
    )
    get_available_models: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get models agent has capacity for. Args: [agent_id]"
        )
    )
    consume: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Record usage against quota. Args: [agent_id, model_id, amount]"
        )
    )


class ModelRegistryConfig(StrictModel):
    """Genesis model registry configuration."""

    artifact_id: str = Field(
        default="genesis_model_registry",
        description="Artifact ID for the model registry"
    )
    description: str = Field(
        default="Model access management - list models, check/transfer quotas",
        description="Description of the model registry"
    )
    methods: ModelRegistryMethodsConfig = Field(
        default_factory=ModelRegistryMethodsConfig
    )


class GenesisConfig(StrictModel):
    """Configuration for all genesis artifacts."""

    artifacts: GenesisArtifactsEnabled = Field(default_factory=GenesisArtifactsEnabled)
    ledger: LedgerConfig = Field(default_factory=LedgerConfig)
    mint: MintConfig = Field(default_factory=MintConfig)
    rights_registry: RightsRegistryConfig = Field(default_factory=RightsRegistryConfig)
    event_log: EventLogConfig = Field(default_factory=EventLogConfig)
    escrow: EscrowConfig = Field(default_factory=EscrowConfig)
    debt_contract: DebtContractConfig = Field(default_factory=DebtContractConfig)
    voting: VotingConfig = Field(default_factory=VotingConfig)  # Plan #183
    model_registry: ModelRegistryConfig = Field(default_factory=ModelRegistryConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)


# =============================================================================
# EXECUTOR MODEL
# =============================================================================

class ExecutorConfig(StrictModel):
    """Code executor configuration."""

    timeout_seconds: int = Field(
        default=5,
        gt=0,
        description="Maximum execution time in seconds"
    )
    max_invoke_depth: int = Field(
        default=5,
        gt=0,
        description="Maximum artifact invocation nesting depth"
    )
    max_contract_depth: int = Field(
        default=10,
        gt=0,
        description="Maximum contract permission check depth (Plan #100)"
    )
    contract_timeout: int = Field(
        default=5,
        gt=0,
        description="Default contract permission check timeout in seconds (Plan #100)"
    )
    contract_llm_timeout: int = Field(
        default=30,
        gt=0,
        description="Timeout for contracts with call_llm capability (Plan #100)"
    )
    interface_validation: str = Field(
        default="warn",
        pattern="^(none|warn|strict)$",
        description="Interface validation mode: 'none' (skip), 'warn' (log), 'strict' (reject) - Plan #86"
    )
    require_interface_for_executables: bool = Field(
        default=True,
        description="Require interface schema when creating executable artifacts - Plan #114"
    )
    preloaded_imports: list[str] = Field(
        default_factory=lambda: ["math", "json", "random", "datetime"],
        description="Modules pre-loaded into execution namespace (NOT a security whitelist)"
    )
    # Legacy name support
    allowed_imports: list[str] | None = Field(
        default=None,
        description="DEPRECATED: Use preloaded_imports"
    )

    @model_validator(mode="after")
    def migrate_legacy_imports(self) -> "ExecutorConfig":
        """Migrate legacy allowed_imports to preloaded_imports."""
        if self.allowed_imports is not None and not self.preloaded_imports:
            self.preloaded_imports = self.allowed_imports
        return self


# =============================================================================
# VALIDATION MODEL
# =============================================================================

class ValidationConfig(StrictModel):
    """Input validation limits to prevent DoS attacks."""

    max_artifact_id_length: int = Field(
        default=128,
        gt=0,
        description="Maximum characters for artifact IDs"
    )
    max_method_name_length: int = Field(
        default=64,
        gt=0,
        description="Maximum characters for method names"
    )


# =============================================================================
# EXECUTION MODEL (Agent Loop Configuration)
# =============================================================================

class AgentLoopExecutionConfig(StrictModel):
    """Configuration for agent autonomous loop execution."""

    min_loop_delay: float = Field(
        default=0.1,
        ge=0,
        description="Minimum seconds between actions"
    )
    max_loop_delay: float = Field(
        default=10.0,
        gt=0,
        description="Maximum backoff delay on errors"
    )
    resource_check_interval: float = Field(
        default=1.0,
        gt=0,
        description="Seconds between resource checks when paused"
    )
    max_consecutive_errors: int = Field(
        default=5,
        gt=0,
        description="Errors before forced pause"
    )
    resources_to_check: list[str] = Field(
        default_factory=lambda: ["llm_calls", "disk_writes", "bandwidth_bytes"],
        description="Resource types to check before each iteration"
    )
    resource_exhaustion_policy: Literal["skip", "block"] = Field(
        default="skip",
        description="Policy when resources exhausted: 'skip' (try again next iteration) or 'block' (wait for capacity)"
    )


class WorkerPoolConfig(StrictModel):
    """Configuration for worker pool execution (Plan #53)."""

    num_workers: int = Field(
        default=4,
        gt=0,
        description="Number of worker threads for parallel execution"
    )
    state_db_path: str = Field(
        default="agent_state.db",
        description="Path to SQLite database for agent state persistence"
    )


class ExecutionConfig(StrictModel):
    """Configuration for agent execution model."""

    use_autonomous_loops: bool = Field(
        default=False,
        description="Enable continuous autonomous agent loops (default: tick-based)"
    )
    use_worker_pool: bool = Field(
        default=False,
        description="Use worker pool for process-isolated turns (Plan #53)"
    )
    worker_pool: WorkerPoolConfig = Field(
        default_factory=WorkerPoolConfig
    )
    agent_loop: AgentLoopExecutionConfig = Field(
        default_factory=AgentLoopExecutionConfig
    )


# =============================================================================
# RATE LIMITING MODEL
# =============================================================================

class RateLimitResourceConfig(StrictModel):
    """Configuration for a single rate-limited resource."""

    max_per_window: float = Field(
        gt=0,
        description="Maximum amount allowed within the rolling window"
    )


class RateLimitingResourcesConfig(StrictModel):
    """Per-resource rate limit configurations."""

    llm_tokens: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=1000),
        description="LLM token consumption per rolling window"
    )
    llm_calls: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=100)
    )
    disk_writes: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=1000)
    )
    bandwidth_bytes: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=10485760)  # 10MB
    )
    cpu_seconds: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=5.0),
        description="CPU time per rolling window (renewable resource)"
    )
    memory_bytes: RateLimitResourceConfig = Field(
        default_factory=lambda: RateLimitResourceConfig(max_per_window=104857600),  # 100MB
        description="Memory usage per rolling window (allocatable resource)"
    )


class RateLimitingConfig(StrictModel):
    """Rolling window rate limiting configuration.

    Time-based rate limiting independent of simulation ticks.
    Tracks usage within a sliding time window and enforces configurable limits.
    """

    enabled: bool = Field(
        default=False,
        description="Enable rate limiting (disabled by default during migration)"
    )
    window_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Rolling window duration in seconds"
    )
    resources: RateLimitingResourcesConfig = Field(
        default_factory=RateLimitingResourcesConfig
    )


# =============================================================================
# MINT SCORER MODEL
# =============================================================================

class ScoreBoundsConfig(StrictModel):
    """Score clamping bounds."""

    min: int = Field(
        default=0,
        ge=0,
        description="Minimum score"
    )
    max: int = Field(
        default=100,
        gt=0,
        description="Maximum score"
    )


class MintScorerConfig(StrictModel):
    """LLM-based mint scorer configuration."""

    model: str = Field(
        default="gemini/gemini-3-flash-preview",
        description="LLM model for scoring artifacts"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="Timeout for scoring requests"
    )
    max_content_length: int = Field(
        default=200000,
        gt=0,
        description="Maximum content length to score"
    )
    score_bounds: ScoreBoundsConfig = Field(
        default_factory=ScoreBoundsConfig,
        description="Score clamping bounds"
    )
    thread_pool_workers: int = Field(
        default=1,
        gt=0,
        description="Thread pool size for scoring"
    )


# =============================================================================
# LLM MODEL
# =============================================================================

class LLMConfig(StrictModel):
    """LLM provider configuration."""

    default_model: str = Field(
        default="gemini/gemini-3-flash-preview",
        description="Default LLM model for agents"
    )
    timeout: int = Field(
        default=60,
        gt=0,
        description="Timeout for LLM requests"
    )
    rate_limit_delay: float = Field(
        default=15.0,
        ge=0,
        description="Delay between LLM calls in seconds"
    )
    allowed_models: list[str] = Field(
        default_factory=lambda: ["gemini/gemini-3-flash-preview"],
        description="Models agents are permitted to use (for future self-modification)"
    )
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = Field(
        default=None,
        description="Claude extended thinking level. Only works with Anthropic Claude models. "
                    "Values: 'none' (disabled), 'low', 'medium', 'high'. "
                    "Higher values improve reasoning but increase cost significantly (5-10x)."
    )


# =============================================================================
# LOGGING MODEL
# =============================================================================

class LoggingTruncationConfig(StrictModel):
    """Log message truncation limits."""

    content: int = Field(
        default=100,
        gt=0,
        description="Artifact content truncation limit in logs"
    )
    code: int = Field(
        default=100,
        gt=0,
        description="Code snippet truncation limit in logs"
    )
    errors: int = Field(
        default=100,
        gt=0,
        description="Error message truncation limit"
    )
    detailed: int = Field(
        default=500,
        gt=0,
        description="Detailed log truncation limit"
    )
    result_data: int = Field(
        default=1000,
        gt=0,
        description="ActionResult.data truncation limit (Plan #80)"
    )


class LoggingConfig(StrictModel):
    """Logging configuration."""

    output_file: str = Field(
        default="run.jsonl",
        description="JSONL file for simulation events"
    )
    logs_dir: str = Field(
        default="logs",
        description="Per-run logs directory (e.g., logs/run_20260115_120000/)"
    )
    log_dir: str = Field(
        default="llm_logs",
        description="Directory for LLM request/response logs"
    )
    default_recent: int = Field(
        default=50,
        gt=0,
        description="Default number of recent events to return"
    )
    truncation: LoggingTruncationConfig = Field(
        default_factory=LoggingTruncationConfig,
        description="Log message truncation limits"
    )


# =============================================================================
# MONITORING MODEL
# =============================================================================

class ThresholdConfig(StrictModel):
    """Warning and critical threshold pair."""

    warning: float = Field(description="Warning threshold")
    critical: float | None = Field(default=None, description="Critical threshold (optional)")


class AuditThresholdsConfig(StrictModel):
    """Audit alert thresholds."""

    gini: ThresholdConfig = Field(
        default_factory=lambda: ThresholdConfig(warning=0.7, critical=0.9),
        description="Gini coefficient thresholds"
    )
    frozen_ratio: ThresholdConfig = Field(
        default_factory=lambda: ThresholdConfig(warning=0.2, critical=0.5),
        description="Frozen agent ratio thresholds"
    )
    active_ratio: ThresholdConfig = Field(
        default_factory=lambda: ThresholdConfig(warning=0.3, critical=0.1),
        description="Active agent ratio thresholds"
    )
    burn_rate: ThresholdConfig = Field(
        default_factory=lambda: ThresholdConfig(warning=0.1, critical=0.25),
        description="Budget burn rate thresholds"
    )
    scrip_velocity_low: ThresholdConfig = Field(
        default_factory=lambda: ThresholdConfig(warning=0.001),
        description="Scrip velocity low threshold"
    )


class HealthScoringConfig(StrictModel):
    """Health score calculation parameters."""

    warning_penalty: float = Field(
        default=0.1,
        ge=0,
        description="Penalty per warning"
    )
    critical_penalty: float = Field(
        default=0.2,
        ge=0,
        description="Penalty per critical"
    )
    trend_threshold: float = Field(
        default=0.1,
        ge=0,
        description="Threshold for trend detection"
    )
    trend_history_ticks: int = Field(
        default=10,
        gt=0,
        description="Ticks of history to analyze for trends"
    )


class MonitoringConfig(StrictModel):
    """Ecosystem health monitoring configuration."""

    audit_thresholds: AuditThresholdsConfig = Field(
        default_factory=AuditThresholdsConfig,
        description="Audit alert thresholds"
    )
    health_scoring: HealthScoringConfig = Field(
        default_factory=HealthScoringConfig,
        description="Health score calculation parameters"
    )
    active_agent_threshold_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Seconds of inactivity before agent considered inactive"
    )


# =============================================================================
# WORLD MODEL
# =============================================================================

class WorldConfig(StrictModel):
    """World simulation configuration.

    Note: max_ticks was removed in Plan #102. Use duration-based execution
    via rate_limiting and execution.use_autonomous_loops instead.
    """

    # Placeholder to allow world: {} in config files without error
    # All actual execution limits are in rate_limiting and budget sections
    pass


# =============================================================================
# BUDGET MODEL
# =============================================================================

class BudgetConfig(StrictModel):
    """API budget configuration."""

    max_api_cost: float = Field(
        default=0.50,
        ge=0,
        description="Maximum API cost in dollars (0 = unlimited). Default $0.50 for safety."
    )
    max_runtime_seconds: int = Field(
        default=3600,
        ge=0,
        description="Maximum simulation runtime in seconds (0 = unlimited). Default 1 hour. "
                    "Hard backstop to prevent runaway processes."
    )
    checkpoint_file: str = Field(
        default="checkpoint.json",
        description="File for saving simulation checkpoints"
    )
    checkpoint_interval: int = Field(
        default=10,
        ge=0,
        description="Save checkpoint every N ticks (0 = disable periodic saves)"
    )
    checkpoint_on_end: bool = Field(
        default=True,
        description="Save checkpoint when simulation ends normally"
    )


# =============================================================================
# DASHBOARD MODEL
# =============================================================================

class DashboardConfig(StrictModel):
    """Dashboard server configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable dashboard server"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind (0.0.0.0 for all interfaces)"
    )
    port: int = Field(
        default=8080,
        gt=0,
        description="Port number"
    )
    static_dir: str = Field(
        default="src/dashboard/static",
        description="Path to static files directory"
    )
    jsonl_file: str = Field(
        default="run.jsonl",
        description="Path to JSONL event log to monitor"
    )
    websocket_path: str = Field(
        default="/ws",
        description="WebSocket endpoint path"
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins"
    )
    max_events_cache: int = Field(
        default=10000,
        gt=0,
        description="Max events to cache in memory"
    )
    debounce_delay_ms: int = Field(
        default=100,
        gt=0,
        description="File watcher debounce delay in milliseconds"
    )
    poll_interval: float = Field(
        default=0.5,
        gt=0,
        description="Polling interval in seconds"
    )
    use_polling: bool = Field(
        default=False,
        description="Use polling instead of watchdog for file changes (WSL compatibility)"
    )
    version: str = Field(
        default="v1",
        description="Dashboard version: 'v1' (vanilla JS) or 'v2' (React)"
    )


# =============================================================================
# AGENT CONFIG
# =============================================================================

class AgentPromptConfig(StrictModel):
    """Configuration for what agents see in their prompts."""

    recent_events_count: int = Field(
        default=5,
        gt=0,
        description="Number of recent events to show in agent prompt"
    )
    memory_limit: int = Field(
        default=5,
        gt=0,
        description="Maximum number of relevant memories to include"
    )
    first_tick_hint: str = Field(
        default="TIP: New to this world? Read handbook_genesis to learn available methods, or handbook_trading for how to buy/sell.",
        description="Hint shown on first tick (empty string to disable)"
    )
    first_tick_enabled: bool = Field(
        default=True,
        description="Whether to show first_tick_hint on tick 1"
    )


DEFAULT_RAG_QUERY_TEMPLATE: str = """Tick {tick}. I am {agent_id} with {balance} scrip.
My artifacts: {my_artifacts}.
Other agents: {other_agents}.
{last_action}
What worked before? What should I try?"""


class RAGConfig(StrictModel):
    """Configuration for RAG (Retrieval-Augmented Generation).

    Can be overridden per-agent in agent.yaml.
    """

    enabled: bool = Field(
        default=True,
        description="Enable/disable RAG for this agent"
    )
    limit: int = Field(
        default=5,
        gt=0,
        description="Maximum memories to retrieve"
    )
    query_template: str = Field(
        default=DEFAULT_RAG_QUERY_TEMPLATE,
        description="Template for RAG query. Variables: {tick}, {agent_id}, {balance}, {my_artifacts}, {other_agents}, {last_action}"
    )


class ErrorMessagesConfig(StrictModel):
    """Configurable error messages with handbook references.

    Use {placeholders} for dynamic values:
    - {artifact_id}: The artifact involved
    - {method}: The method name
    - {methods}: List of available methods
    - {escrow_id}: The escrow artifact ID
    """

    access_denied_read: str = Field(
        default="Access denied: you are not allowed to read {artifact_id}. See handbook_actions for permissions.",
        description="Error when read access denied"
    )
    access_denied_write: str = Field(
        default="Access denied: you are not allowed to write to {artifact_id}. See handbook_actions for permissions.",
        description="Error when write access denied"
    )
    access_denied_invoke: str = Field(
        default="Access denied: you are not allowed to invoke {artifact_id}. See handbook_actions for permissions.",
        description="Error when invoke access denied"
    )
    method_not_found: str = Field(
        default="Method '{method}' not found on {artifact_id}. Available: {methods}. See handbook_genesis for method details.",
        description="Error when method doesn't exist"
    )
    escrow_not_owner: str = Field(
        default="Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) genesis_ledger.transfer_ownership([artifact_id, '{escrow_id}']), 2) deposit.",
        description="Error when trying to deposit artifact not owned by escrow"
    )


class InterfaceDiscoveryConfig(StrictModel):
    """Configuration for how agents discover artifact interfaces (Plan #137).

    Controls agent behavior when invoking unfamiliar artifacts - whether to
    check interfaces first or learn from error feedback.
    """

    mode: Literal["try_and_learn", "check_first", "hybrid"] = Field(
        default="try_and_learn",
        description=(
            "Interface discovery strategy: "
            "'try_and_learn' (default) - invoke and learn from errors, "
            "'check_first' - always call get_interface before invoking, "
            "'hybrid' - check for complex methods, try simple ones"
        )
    )
    cache_in_memory: bool = Field(
        default=True,
        description="Cache learned interfaces in working memory for reuse"
    )


class WorkingMemoryConfig(StrictModel):
    """Configuration for agent working memory (Plan #59).

    Working memory provides structured context that persists across agent turns,
    enabling complex multi-step goal pursuit.
    """

    enabled: bool = Field(
        default=False,
        description="Master switch for working memory feature"
    )
    auto_inject: bool = Field(
        default=True,
        description="Automatically inject working memory into agent prompts"
    )
    max_size_bytes: int = Field(
        default=2000,
        gt=0,
        description="Maximum size of working memory in bytes (prevents prompt bloat)"
    )
    include_in_rag: bool = Field(
        default=False,
        description="Also include working memory in semantic search"
    )
    structured_format: bool = Field(
        default=True,
        description="Enforce YAML schema vs freeform working memory"
    )
    warn_on_missing: bool = Field(
        default=False,
        description="Log warning if agent has no working memory"
    )


class SubscribedArtifactsConfig(StrictModel):
    """Configuration for subscribed artifacts auto-injection (Plan #191)."""

    max_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum artifacts an agent can subscribe to"
    )
    max_size_bytes: int = Field(
        default=2000,
        ge=100,
        le=50000,
        description="Maximum content size per subscribed artifact (truncated if exceeded)"
    )


class PlanningConfig(StrictModel):
    """Configuration for agent deliberative planning (Plan #188)."""

    enabled: bool = Field(
        default=False,
        description="Enable plan artifact pattern for deliberative agent behavior"
    )
    max_steps: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of steps in a plan"
    )
    replan_on_failure: bool = Field(
        default=True,
        description="Generate new plan if a step fails"
    )


class AgentConfig(StrictModel):
    """Configuration for agent behavior."""

    prompt: AgentPromptConfig = Field(default_factory=AgentPromptConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    errors: ErrorMessagesConfig = Field(default_factory=ErrorMessagesConfig)
    working_memory: WorkingMemoryConfig = Field(default_factory=WorkingMemoryConfig)
    interface_discovery: InterfaceDiscoveryConfig = Field(
        default_factory=InterfaceDiscoveryConfig,
        description="Interface discovery behavior (Plan #137)"
    )
    subscribed_artifacts: SubscribedArtifactsConfig = Field(
        default_factory=SubscribedArtifactsConfig,
        description="Subscribed artifacts auto-injection (Plan #191)"
    )
    planning: PlanningConfig = Field(
        default_factory=PlanningConfig,
        description="Deliberative planning behavior (Plan #188)"
    )
    failure_history_max: int = Field(
        default=5,
        ge=0,
        description="Max recent failures to track per agent (Plan #88)"
    )
    action_history_max: int = Field(
        default=15,
        ge=0,
        description="Max recent actions to track per agent for loop detection (Plan #156)"
    )
    # Plan #132: Removed cognitive_schema - single standardized response format with 'reasoning' field
    # Plan #195: Context budget is defined separately in ContextBudgetModel


# =============================================================================
# MEMORY CONFIG
# =============================================================================


class TierBoostsModel(StrictModel):
    """Configuration for memory tier boost values."""

    pinned: float = Field(
        default=1.0,
        description="Score boost for pinned (tier 0) memories"
    )
    critical: float = Field(
        default=0.3,
        description="Score boost for critical (tier 1) memories"
    )
    important: float = Field(
        default=0.15,
        description="Score boost for important (tier 2) memories"
    )
    normal: float = Field(
        default=0.0,
        description="Score boost for normal (tier 3) memories"
    )
    low: float = Field(
        default=-0.1,
        description="Score boost for low (tier 4) memories"
    )


class MemoryConfigModel(StrictModel):
    """Configuration for Mem0/Qdrant memory system."""

    llm_model: str = Field(
        default="gemini-3-flash-preview",
        description="Model for Mem0's LLM (no provider prefix)"
    )
    embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Embedding model for vector search"
    )
    embedding_dims: int = Field(
        default=768,
        gt=0,
        description="Embedding dimensions"
    )
    temperature: float = Field(
        default=0.1,
        ge=0,
        le=2,
        description="Temperature for Mem0's LLM"
    )
    collection_name: str = Field(
        default="agent_memories",
        description="Qdrant collection name"
    )
    max_pinned: int = Field(
        default=5,
        gt=0,
        description="Maximum number of pinned memories per agent"
    )
    tier_boosts: TierBoostsModel = Field(
        default_factory=TierBoostsModel,
        description="Score boosts for each memory tier"
    )


# =============================================================================
# CONTEXT BUDGET MODEL (Plan #195)
# =============================================================================


class ContextBudgetSectionModel(StrictModel):
    """Budget allocation for a single prompt section."""

    max_tokens: int = Field(
        default=500,
        gt=0,
        description="Maximum tokens for this section"
    )
    priority: str = Field(
        default="medium",
        pattern="^(required|high|medium|low)$",
        description="Section priority: required, high, medium, low"
    )
    truncation_strategy: str = Field(
        default="end",
        pattern="^(end|start|middle)$",
        description="Where to truncate: end (newest), start (oldest), middle"
    )


class ContextBudgetSectionsModel(StrictModel):
    """Budget allocations per prompt section."""

    system_prompt: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=800, priority="required", truncation_strategy="end"
        ),
        description="System prompt budget"
    )
    working_memory: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=600, priority="high", truncation_strategy="end"
        ),
        description="Working memory budget"
    )
    rag_memories: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=400, priority="medium", truncation_strategy="end"
        ),
        description="RAG memories budget"
    )
    action_history: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=300, priority="medium", truncation_strategy="start"
        ),
        description="Action history budget (truncate oldest)"
    )
    failure_history: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=200, priority="medium", truncation_strategy="start"
        ),
        description="Failure history budget (truncate oldest)"
    )
    recent_events: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=300, priority="low", truncation_strategy="start"
        ),
        description="Recent events budget"
    )
    subscribed_artifacts: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=400, priority="medium", truncation_strategy="end"
        ),
        description="Subscribed artifacts budget"
    )
    world_state: ContextBudgetSectionModel = Field(
        default_factory=lambda: ContextBudgetSectionModel(
            max_tokens=500, priority="required", truncation_strategy="end"
        ),
        description="World state section budget"
    )


class ContextBudgetModel(StrictModel):
    """Configuration for agent context budget management (Plan #195)."""

    enabled: bool = Field(
        default=False,
        description="Enable context budget management"
    )
    total_tokens: int = Field(
        default=4000,
        gt=0,
        description="Total tokens available for prompt"
    )
    output_reserve: int = Field(
        default=1000,
        ge=0,
        description="Tokens reserved for model output"
    )
    show_budget_usage: bool = Field(
        default=False,
        description="Show budget usage section in prompt"
    )
    overflow_policy: str = Field(
        default="truncate",
        pattern="^(truncate|drop)$",
        description="Policy when over budget: truncate or drop low priority"
    )
    sections: ContextBudgetSectionsModel = Field(
        default_factory=ContextBudgetSectionsModel,
        description="Per-section budget allocations"
    )


# =============================================================================
# LIBRARIES MODEL (Plan #29)
# =============================================================================

# =============================================================================
# ID GENERATION MODEL
# =============================================================================

class IdGenerationConfig(StrictModel):
    """Settings for artifact ID generation."""

    uuid_hex_length: int = Field(
        default=8,
        gt=0,
        le=32,
        description="Characters from UUID hex for IDs"
    )


class LibrariesConfig(StrictModel):
    """Library installation configuration for agents."""

    genesis: list[str] = Field(
        default_factory=lambda: [
            "requests", "aiohttp", "urllib3",  # HTTP
            "numpy", "pandas", "python-dateutil",  # Data
            "scipy", "matplotlib",  # Scientific
            "cryptography",  # Crypto
            "pyyaml", "pydantic", "jinja2",  # Core (already installed)
        ],
        description="Pre-installed libraries (don't count against quota)"
    )
    blocked: list[str] = Field(
        default_factory=lambda: [
            "docker",  # Docker daemon access
            "debugpy",  # Debugger attachment
            "pyautogui",  # Desktop automation
            "keyboard",  # Keyboard input capture
            "pynput",  # Input device control
        ],
        description="Blocked packages (security risks)"
    )


# =============================================================================
# CONTRACTS CONFIG
# =============================================================================

class ContractsConfig(StrictModel):
    """Contract system configuration (Plan #100, ADR-0017, ADR-0019)."""

    default_when_null: str = Field(
        default="creator_only",
        description="Behavior when access_contract_id is NULL. Options: 'creator_only' (only creator can access, ADR-0019 default), 'freeware' (legacy behavior)"
    )
    default_on_missing: str = Field(
        default="kernel_contract_freeware",
        description="Default contract to use when access_contract_id points to deleted/missing contract (ADR-0017)"
    )



# =============================================================================
# LEARNING CONFIG (Plan #186)
# =============================================================================

class CrossRunLearningConfig(StrictModel):
    """Cross-run learning configuration for agents."""

    enabled: bool = Field(
        default=False,
        description="Enable loading learnings from prior runs"
    )
    prior_checkpoint: str | None = Field(
        default=None,
        description="Path to checkpoint file (null = auto-discover)"
    )
    auto_discover: bool = Field(
        default=True,
        description="Auto-find latest checkpoint in logs/"
    )
    load_working_memory: bool = Field(
        default=True,
        description="Load working_memory from prior run"
    )


class LearningConfig(StrictModel):
    """Learning configuration for agents."""

    cross_run: CrossRunLearningConfig = Field(
        default_factory=CrossRunLearningConfig,
        description="Cross-run learning settings"
    )


# =============================================================================
# PROMPT INJECTION CONFIG (Plan #197)
# =============================================================================

class PromptInjectionConfig(StrictModel):
    """Configuration for mandatory prompt injection.

    This allows injecting content into agent prompts that agents cannot override.
    Used for experimenting with different incentive framings.
    """

    enabled: bool = Field(
        default=False,
        description="Enable prompt injection"
    )
    scope: Literal["none", "genesis", "all"] = Field(
        default="all",
        description="Which agents receive injection: 'none', 'genesis' (only genesis agents), or 'all'"
    )
    mandatory_prefix: str = Field(
        default="",
        description="Content injected BEFORE the agent's system prompt"
    )
    mandatory_suffix: str = Field(
        default="",
        description="Content injected AFTER the agent's system prompt"
    )


# =============================================================================
# ROOT CONFIG MODEL
# =============================================================================

class AppConfig(StrictModel):
    """Root configuration model for the entire application.

    All fields have sensible defaults, so an empty config file is valid.
    """

    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    scrip: ScripConfig = Field(default_factory=ScripConfig)
    costs: CostsConfig = Field(default_factory=CostsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)  # Plan #153
    genesis: GenesisConfig = Field(default_factory=GenesisConfig)
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    contracts: ContractsConfig = Field(default_factory=ContractsConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    mint_scorer: MintScorerConfig = Field(default_factory=MintScorerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    world: WorldConfig = Field(default_factory=WorldConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    context_budget: ContextBudgetModel = Field(default_factory=ContextBudgetModel)  # Plan #195
    memory: MemoryConfigModel = Field(default_factory=MemoryConfigModel)
    libraries: LibrariesConfig = Field(default_factory=LibrariesConfig)
    id_generation: IdGenerationConfig = Field(default_factory=IdGenerationConfig)
    learning: LearningConfig = Field(default_factory=LearningConfig)  # Plan #186
    prompt_injection: PromptInjectionConfig = Field(default_factory=PromptInjectionConfig)  # Plan #197

    # Dynamic fields set at runtime
    principals: list[dict[str, int | str]] = Field(
        default_factory=list,
        description="List of principal configs (set at runtime)"
    )


# =============================================================================
# LOADING FUNCTIONS
# =============================================================================

def load_validated_config(config_path: str | Path = "config/config.yaml") -> AppConfig:
    """Load and validate configuration from YAML file.

    Args:
        config_path: Path to config YAML file.

    Returns:
        Validated AppConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        pydantic.ValidationError: If config is invalid (with detailed error message).
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw_config = yaml.safe_load(f) or {}

    return AppConfig.model_validate(raw_config)


def validate_config_dict(config_dict: dict[str, Any]) -> AppConfig:
    """Validate a configuration dictionary.

    Args:
        config_dict: Configuration as a dictionary.

    Returns:
        Validated AppConfig instance.

    Raises:
        pydantic.ValidationError: If config is invalid.
    """
    return AppConfig.model_validate(config_dict)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Root config
    "AppConfig",
    # Sub-configs
    "ResourcesConfig",
    "StockResources",
    "FlowResources",
    "StockResource",
    "FlowResource",
    "ScripConfig",
    "CostsConfig",
    # Timeouts
    "TimeoutsConfig",
    # Genesis configs
    "GenesisConfig",
    "GenesisArtifactsEnabled",
    "ArtifactEnabledConfig",
    "MethodConfig",
    "LedgerConfig",
    "LedgerMethodsConfig",
    "MintConfig",
    "MintMethodsConfig",
    "MintAuctionConfig",
    "RightsRegistryConfig",
    "RightsRegistryMethodsConfig",
    "EventLogConfig",
    "EventLogMethodsConfig",
    "EscrowConfig",
    "EscrowMethodsConfig",
    "DebtContractConfig",
    "DebtContractMethodsConfig",
    # MCP configs
    "McpConfig",
    "McpServerConfig",
    # Rate limiting configs
    "RateLimitingConfig",
    "RateLimitingResourcesConfig",
    "RateLimitResourceConfig",
    # Execution configs
    "ExecutionConfig",
    "AgentLoopExecutionConfig",
    # Other configs
    "ExecutorConfig",
    "MintScorerConfig",
    "ScoreBoundsConfig",
    "LLMConfig",
    "LoggingConfig",
    "LoggingTruncationConfig",
    "MonitoringConfig",
    "AuditThresholdsConfig",
    "HealthScoringConfig",
    "ThresholdConfig",
    "WorldConfig",
    "BudgetConfig",
    "DashboardConfig",
    "AgentConfig",
    "AgentPromptConfig",
    "RAGConfig",
    "ErrorMessagesConfig",
    "InterfaceDiscoveryConfig",
    "WorkingMemoryConfig",
    "IdGenerationConfig",
    # Functions
    "load_validated_config",
    "validate_config_dict",
]
