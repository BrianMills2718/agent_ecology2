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


class FlowResource(StrictModel):
    """A rate-limited resource (refreshes per tick)."""

    per_tick: int = Field(ge=0, description="Amount available per tick")
    unit: str = Field(description="Unit of measurement")
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
        default_factory=lambda: StockResource(total=50000, unit="bytes")
    )


class FlowResources(StrictModel):
    """All flow (rate-limited) resources."""

    compute: FlowResource = Field(
        default_factory=lambda: FlowResource(per_tick=1000, unit="token_units")
    )
    bandwidth: FlowResource = Field(
        default_factory=lambda: FlowResource(per_tick=0, unit="bytes")
    )


class ResourcesConfig(StrictModel):
    """Resource configuration (stock and flow)."""

    stock: StockResources = Field(default_factory=StockResources)
    flow: FlowResources = Field(default_factory=FlowResources)


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

    Actions themselves are free. Real costs come from:
    - LLM tokens (thinking) - costs from compute budget
    - Disk usage (writing) - costs from disk quota
    - Genesis method costs (configured per-method)
    """

    per_1k_input_tokens: int = Field(
        default=1,
        ge=0,
        description="Compute cost per 1K input tokens"
    )
    per_1k_output_tokens: int = Field(
        default=3,
        ge=0,
        description="Compute cost per 1K output tokens"
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
    store: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)
    debt_contract: ArtifactEnabledConfig = Field(default_factory=ArtifactEnabledConfig)


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

    # Legacy support
    transfer_fee: int | None = Field(default=None, description="DEPRECATED: Use methods.transfer.cost")

    @model_validator(mode="after")
    def migrate_legacy_transfer_fee(self) -> "LedgerConfig":
        """Migrate legacy transfer_fee to methods.transfer.cost."""
        if self.transfer_fee is not None:
            self.methods.transfer.cost = self.transfer_fee
        return self


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

    period: int = Field(
        default=50,
        gt=0,
        description="Ticks between auctions"
    )
    bidding_window: int = Field(
        default=10,
        gt=0,
        description="Duration of bidding phase (ticks)"
    )
    first_auction_tick: int = Field(
        default=50,
        ge=0,
        description="Grace period before first auction (0 = start immediately)"
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

    @field_validator("bidding_window")
    @classmethod
    def bidding_window_less_than_period(cls, v: int, info: ValidationInfo) -> int:
        """Ensure bidding window is less than period."""
        # Note: Can't access period here easily, validated at runtime
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
        if self.auction.bidding_window >= self.auction.period:
            raise ValueError(
                f"bidding_window ({self.auction.bidding_window}) must be less than "
                f"period ({self.auction.period})"
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

    # Legacy support
    transfer_fee: int | None = Field(default=None, description="DEPRECATED: Use methods.transfer_quota.cost")

    @model_validator(mode="after")
    def migrate_legacy_transfer_fee(self) -> "RightsRegistryConfig":
        """Migrate legacy transfer_fee to methods.transfer_quota.cost."""
        if self.transfer_fee is not None:
            self.methods.transfer_quota.cost = self.transfer_fee
        return self


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


class StoreMethodsConfig(StrictModel):
    """Genesis store method configurations."""

    list: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List artifacts with optional filter. Args: [filter?] - filter is dict with type/owner/has_standing/can_execute/limit/offset"
        )
    )
    get: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Get single artifact details. Args: [artifact_id]"
        )
    )
    search: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Search artifacts by content match. Args: [query, field?, limit?]"
        )
    )
    list_by_type: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List artifacts of specific type. Args: [type] - type is 'agent'|'memory'|'data'|'executable'|'genesis'"
        )
    )
    list_by_owner: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List artifacts by owner. Args: [owner_id]"
        )
    )
    list_agents: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List all agent artifacts (has_standing=True AND can_execute=True). Args: []"
        )
    )
    list_principals: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="List all principals (artifacts with has_standing=True). Args: []"
        )
    )
    count: MethodConfig = Field(
        default_factory=lambda: MethodConfig(
            cost=0,
            description="Count artifacts matching filter. Args: [filter?]"
        )
    )


class StoreConfig(StrictModel):
    """Genesis store configuration for artifact discovery."""

    id: str = Field(default="genesis_store", description="Artifact ID")
    description: str = Field(
        default="Artifact registry and discovery. Search, list, and browse artifacts.",
        description="Artifact description"
    )
    methods: StoreMethodsConfig = Field(default_factory=StoreMethodsConfig)


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


class GenesisConfig(StrictModel):
    """Configuration for all genesis artifacts."""

    artifacts: GenesisArtifactsEnabled = Field(default_factory=GenesisArtifactsEnabled)
    ledger: LedgerConfig = Field(default_factory=LedgerConfig)
    mint: MintConfig = Field(default_factory=MintConfig)
    rights_registry: RightsRegistryConfig = Field(default_factory=RightsRegistryConfig)
    event_log: EventLogConfig = Field(default_factory=EventLogConfig)
    escrow: EscrowConfig = Field(default_factory=EscrowConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    debt_contract: DebtContractConfig = Field(default_factory=DebtContractConfig)
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


class ExecutionConfig(StrictModel):
    """Configuration for agent execution model."""

    use_autonomous_loops: bool = Field(
        default=False,
        description="Enable continuous autonomous agent loops (default: tick-based)"
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


# =============================================================================
# LOGGING MODEL
# =============================================================================

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


# =============================================================================
# WORLD MODEL
# =============================================================================

class WorldConfig(StrictModel):
    """World simulation configuration."""

    max_ticks: int = Field(
        default=100,
        gt=0,
        description="Maximum simulation ticks"
    )


# =============================================================================
# BUDGET MODEL
# =============================================================================

class BudgetConfig(StrictModel):
    """API budget configuration."""

    max_api_cost: float = Field(
        default=1.0,
        ge=0,
        description="Maximum API cost in dollars (0 = unlimited)"
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


class AgentConfig(StrictModel):
    """Configuration for agent behavior."""

    prompt: AgentPromptConfig = Field(default_factory=AgentPromptConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    errors: ErrorMessagesConfig = Field(default_factory=ErrorMessagesConfig)


# =============================================================================
# MEMORY CONFIG
# =============================================================================

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


# =============================================================================
# LIBRARIES MODEL (Plan #29)
# =============================================================================

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
# ROOT CONFIG MODEL
# =============================================================================

class AppConfig(StrictModel):
    """Root configuration model for the entire application.

    All fields have sensible defaults, so an empty config file is valid.
    """

    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    scrip: ScripConfig = Field(default_factory=ScripConfig)
    costs: CostsConfig = Field(default_factory=CostsConfig)
    genesis: GenesisConfig = Field(default_factory=GenesisConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    rate_limiting: RateLimitingConfig = Field(default_factory=RateLimitingConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    mint_scorer: MintScorerConfig = Field(default_factory=MintScorerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    world: WorldConfig = Field(default_factory=WorldConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    memory: MemoryConfigModel = Field(default_factory=MemoryConfigModel)
    libraries: LibrariesConfig = Field(default_factory=LibrariesConfig)

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
    "StoreConfig",
    "StoreMethodsConfig",
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
    "LLMConfig",
    "LoggingConfig",
    "WorldConfig",
    "BudgetConfig",
    "DashboardConfig",
    "AgentConfig",
    "AgentPromptConfig",
    "RAGConfig",
    "ErrorMessagesConfig",
    # Functions
    "load_validated_config",
    "validate_config_dict",
]
