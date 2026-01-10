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
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
        default_factory=lambda: FlowResource(per_tick=1000, unit="cycles")
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

class ActionCosts(StrictModel):
    """Cost in compute units for each action type."""

    noop: int = Field(default=1, ge=0)
    read_artifact: int = Field(default=2, ge=0)
    write_artifact: int = Field(default=5, ge=0)
    invoke_artifact: int = Field(default=1, ge=0)


class CostsConfig(StrictModel):
    """All cost configurations."""

    actions: ActionCosts = Field(default_factory=ActionCosts)
    execution_gas: int = Field(
        default=2,
        ge=0,
        description="Gas cost for executing agent code"
    )
    default: int = Field(
        default=1,
        ge=0,
        description="Default cost for unspecified actions"
    )
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

class LedgerConfig(StrictModel):
    """Genesis ledger configuration."""

    transfer_fee: int = Field(
        default=1,
        ge=0,
        description="Scrip fee for transfers"
    )


class OracleConfig(StrictModel):
    """Genesis oracle configuration."""

    submit_fee: int = Field(
        default=5,
        ge=0,
        description="Scrip fee to submit artifact for scoring"
    )
    mint_ratio: int = Field(
        default=10,
        gt=0,
        description="Divisor for score-to-scrip conversion (score / ratio = scrip)"
    )


class RightsRegistryConfig(StrictModel):
    """Genesis rights registry configuration."""

    transfer_fee: int = Field(
        default=1,
        ge=0,
        description="Scrip fee for quota transfers"
    )


class EventLogConfig(StrictModel):
    """Genesis event log configuration."""

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


class GenesisConfig(StrictModel):
    """Configuration for all genesis artifacts."""

    ledger: LedgerConfig = Field(default_factory=LedgerConfig)
    oracle: OracleConfig = Field(default_factory=OracleConfig)
    rights_registry: RightsRegistryConfig = Field(default_factory=RightsRegistryConfig)
    event_log: EventLogConfig = Field(default_factory=EventLogConfig)


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
# ORACLE SCORER MODEL
# =============================================================================

class OracleScorerConfig(StrictModel):
    """LLM-based oracle scorer configuration."""

    model: str = Field(
        default="gemini/gemini-2.0-flash",
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
        default="gemini/gemini-2.0-flash",
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


# =============================================================================
# LOGGING MODEL
# =============================================================================

class LoggingConfig(StrictModel):
    """Logging configuration."""

    output_file: str = Field(
        default="run.jsonl",
        description="JSONL file for simulation events"
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


# =============================================================================
# COOLDOWN MODEL (optional)
# =============================================================================

class CooldownConfig(StrictModel):
    """Cooldown configuration for agents."""

    tokens_per_tick_capacity: int = Field(
        default=500,
        gt=0,
        description="Output tokens before cooldown kicks in"
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
    oracle_scorer: OracleScorerConfig = Field(default_factory=OracleScorerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    world: WorldConfig = Field(default_factory=WorldConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    cooldown: CooldownConfig = Field(default_factory=CooldownConfig)

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


def validate_config_dict(config_dict: dict) -> AppConfig:
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
    "ActionCosts",
    "GenesisConfig",
    "LedgerConfig",
    "OracleConfig",
    "RightsRegistryConfig",
    "EventLogConfig",
    "ExecutorConfig",
    "OracleScorerConfig",
    "LLMConfig",
    "LoggingConfig",
    "WorldConfig",
    "BudgetConfig",
    "CooldownConfig",
    # Functions
    "load_validated_config",
    "validate_config_dict",
]
