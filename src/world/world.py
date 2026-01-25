"""World kernel - the core simulation loop"""

from __future__ import annotations

__all__ = [
    # Main class
    "World",
    # TypedDicts (public API)
    "StateSummary",
    "BalanceInfo",
    "QuotaInfo",
    # Re-exported from mint_auction
    "KernelMintSubmission",
    "KernelMintResult",
]

import json
import time
import uuid
from pathlib import Path
from typing import Any, TypedDict, TYPE_CHECKING, cast

from .ledger import Ledger
from .artifacts import ArtifactStore, Artifact, WriteResult
from .logger import EventLogger
from .actions import (
    ActionIntent, ActionResult, ActionType,
    NoopIntent, ReadArtifactIntent, WriteArtifactIntent,
    EditArtifactIntent, InvokeArtifactIntent, DeleteArtifactIntent
)
# NOTE: TransferIntent removed - all transfers via genesis_ledger.transfer()
from .genesis import (
    create_genesis_artifacts, GenesisArtifact, GenesisRightsRegistry,
    GenesisMint, GenesisDebtContract, RightsConfig, SubmissionInfo
)
from .executor import get_executor, validate_args_against_interface, convert_positional_to_named_args, convert_named_to_positional_args, parse_json_args
from .errors import ErrorCode, ErrorCategory
from .rate_tracker import RateTracker
from .invocation_registry import InvocationRegistry, InvocationRecord
from .id_registry import IDRegistry
from .resource_manager import ResourceManager, ResourceType
from .resource_metrics import ResourceMetricsProvider
from .mint_auction import MintAuction, KernelMintSubmission, KernelMintResult

from ..config import get as config_get, compute_per_agent_quota, PerAgentQuota

if TYPE_CHECKING:
    from ..simulation.agent_loop import AgentLoopManager


def get_error_message(error_type: str, **kwargs: Any) -> str:
    """Get a configurable error message with placeholders filled in.

    Args:
        error_type: One of 'access_denied_read', 'access_denied_write',
                   'access_denied_invoke', 'method_not_found', 'escrow_not_owner'
        **kwargs: Placeholder values (artifact_id, method, methods, escrow_id)

    Returns:
        Formatted error message from config (or default if not configured).
    """
    # Defaults (in case config not loaded)
    defaults: dict[str, str] = {
        "access_denied_read": "Access denied: you are not allowed to read {artifact_id}. See handbook_actions for permissions.",
        "access_denied_write": "Access denied: you are not allowed to write to {artifact_id}. See handbook_actions for permissions.",
        "access_denied_invoke": "Access denied: you are not allowed to invoke {artifact_id}. See handbook_actions for permissions.",
        "method_not_found": "Use one of {methods} instead. Method '{method}' does not exist on {artifact_id}. See handbook_genesis for details.",
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) genesis_ledger.transfer_ownership([artifact_id, '{escrow_id}']), 2) deposit.",
    }

    # Get from config (or use default)
    template: str = config_get(f"agent.errors.{error_type}") or defaults.get(error_type, f"Error: {error_type}")

    # Fill in placeholders
    try:
        return template.format(**kwargs)
    except KeyError:
        # Missing placeholder - return template as-is
        return template


class PrincipalConfig(TypedDict, total=False):
    """Configuration for a principal."""
    id: str
    starting_scrip: int
    starting_credits: int  # Legacy name


class LoggingConfig(TypedDict, total=False):
    """Logging configuration."""
    output_file: str
    logs_dir: str


class CostsConfig(TypedDict, total=False):
    """Costs configuration (token costs only)."""
    per_1k_input_tokens: int
    per_1k_output_tokens: int


class WorldConfig(TypedDict, total=False):
    """World configuration section (minimal - continuous execution mode only)."""
    pass


class ConfigDict(TypedDict, total=False):
    """Full configuration dictionary."""
    world: WorldConfig
    costs: CostsConfig
    logging: LoggingConfig
    principals: list[PrincipalConfig]
    rights: RightsConfig


class BalanceInfo(TypedDict):
    """Balance information for an agent."""
    compute: int
    scrip: int


class QuotaInfo(TypedDict):
    """Quota information for an agent."""
    llm_tokens_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class MintSubmissionStatus(TypedDict, total=False):
    """Status of a mint submission."""
    status: str
    submitter: str
    score: int | None


class StateSummary(TypedDict):
    """World state summary."""
    event_number: int
    balances: dict[str, BalanceInfo]
    artifacts: list[dict[str, Any]]
    quotas: dict[str, QuotaInfo]
    mint_submissions: dict[str, MintSubmissionStatus]
    recent_events: list[dict[str, Any]]
    resource_metrics: dict[str, dict[str, Any]]  # Plan #93: Agent resource visibility


class World:
    """The world kernel - manages state, executes actions, logs everything"""

    config: ConfigDict
    event_number: int  # Monotonic counter for event ordering in logs
    costs: CostsConfig
    rights_config: RightsConfig
    ledger: Ledger
    artifacts: ArtifactStore
    logger: EventLogger
    genesis_artifacts: dict[str, GenesisArtifact]
    rights_registry: GenesisRightsRegistry | None
    principal_ids: list[str]
    # Rate limiting mode: when True, resources use rolling windows (RateTracker)
    use_rate_tracker: bool
    # Autonomous loop support
    use_autonomous_loops: bool
    rate_tracker: RateTracker | None
    loop_manager: "AgentLoopManager | None"
    # Invocation tracking for observability (Gap #27)
    invocation_registry: InvocationRegistry
    # Kernel mint state (Plan #44) - minting is kernel physics, not genesis privilege
    mint_auction: MintAuction  # Extracted mint logic (TD-001)
    # Unified resource management (Plan #95)
    # Replaces _quota_limits and _quota_usage with ResourceManager
    resource_manager: ResourceManager
    # Resource metrics for visibility (Plan #93)
    resource_metrics_provider: ResourceMetricsProvider
    _simulation_start_time: float
    _simulation_duration: float | None  # Plan #157: Total duration for time awareness
    # Installed libraries per agent (Plan #29)
    # Maps principal_id -> list of (library_name, version)
    _installed_libraries: dict[str, list[tuple[str, str | None]]]
    # Global ID registry for collision prevention (Plan #7)
    id_registry: IDRegistry

    def __init__(self, config: ConfigDict, run_id: str | None = None) -> None:
        self.config = config
        self.event_number = 0  # Monotonic counter for event ordering in logs
        self.costs = config["costs"]

        # Compute per-agent quotas from resource totals
        # Precision note (Plan #84): Quotas are typically whole numbers (compute units,
        # disk bytes) or simple decimals (llm_budget dollars). No Decimal arithmetic
        # needed here - precision issues only arise from repeated add/subtract operations,
        # which happen in ledger.py (where Decimal helpers are used).
        num_agents = len(config.get("principals", []))
        empty_quotas: PerAgentQuota = {"llm_tokens_quota": 0, "disk_quota": 0, "llm_budget_quota": 0.0}
        quotas: PerAgentQuota = compute_per_agent_quota(num_agents) if num_agents > 0 else empty_quotas

        # Rights configuration (Layer 2: Means of Production)
        # See docs/RESOURCE_MODEL.md for design rationale
        # Values come from config via compute_per_agent_quota()
        # Use new generic format with default_quotas dict
        if "rights" in config and "default_quotas" in config["rights"]:
            self.rights_config = config["rights"]
        else:
            # Build generic quotas from computed values (rolling window rate limiting)
            self.rights_config = {
                "default_quotas": {
                    "llm_tokens": float(quotas.get("llm_tokens_quota", 50)),
                    "disk": float(quotas.get("disk_quota", config_get("resources.stock.disk.total") or 10000))
                }
            }

        # Check if rate limiting (rolling windows) is enabled
        rate_limiting_config = cast(dict[str, Any], config.get("rate_limiting", {}))
        self.use_rate_tracker = rate_limiting_config.get("enabled", False)

        # Global ID registry for collision prevention (Plan #7)
        self.id_registry = IDRegistry()
        
        # Core state - create ledger with rate_limiting config and ID registry
        self.ledger = Ledger.from_config(cast(dict[str, Any], config), [], self.id_registry)
        self.artifacts = ArtifactStore(id_registry=self.id_registry)
        # Per-run logging if logs_dir and run_id provided, else legacy mode
        logs_dir = config.get("logging", {}).get("logs_dir")
        if logs_dir and run_id:
            self.logger = EventLogger(logs_dir=logs_dir, run_id=run_id)
        else:
            self.logger = EventLogger(output_file=config["logging"]["output_file"])

        # Unified resource manager (Plan #95)
        # Must be initialized BEFORE genesis artifacts since rights_registry delegates here
        self.resource_manager = ResourceManager()

        # Resource metrics provider for visibility (Plan #93)
        # Provides read-only aggregation of resource metrics for agent prompts
        self._simulation_start_time = time.time()
        self._simulation_duration = None  # Plan #157: Set by runner when duration known
        self.resource_metrics_provider = ResourceMetricsProvider(
            initial_allocations={
                "llm_budget": float(quotas.get("llm_budget_quota", 0.0)),
                "disk": float(quotas.get("disk_quota", 0)),
                "llm_tokens": float(quotas.get("llm_tokens_quota", 0)),
            },
            resource_units={
                "llm_budget": "dollars",
                "disk": "bytes",
                "llm_tokens": "tokens",
            },
        )

        # Installed libraries per agent (Plan #29)
        self._installed_libraries = {}

        # Initialize MintAuction (extracted from World - TD-001)
        # Must be before genesis_artifacts since mint_callback needs it
        self.mint_auction = MintAuction(
            ledger=self.ledger,
            artifacts=self.artifacts,
            logger=self.logger,
            get_event_number=lambda: self.event_number,
        )

        # Genesis artifacts (system-owned proxies)
        self.genesis_artifacts = create_genesis_artifacts(
            ledger=self.ledger,
            mint_callback=self.mint_auction.mint_scrip,
            artifact_store=self.artifacts,
            logger=self.logger,
            rights_config=self.rights_config
        )

        # Register genesis artifacts in artifact store for unified invoke path (Plan #15)
        for genesis_id, genesis in self.genesis_artifacts.items():
            artifact = self.artifacts.write(
                artifact_id=genesis_id,
                type="genesis",
                content=genesis.description,
                created_by="system",
                executable=True,
            )
            # Attach genesis methods for dispatch
            artifact.genesis_methods = genesis.methods

        # Store reference to rights registry for quota enforcement
        rights_registry = self.genesis_artifacts.get("genesis_rights_registry")
        self.rights_registry = rights_registry if isinstance(rights_registry, GenesisRightsRegistry) else None

# Wire up GenesisMint to use kernel primitives (Plan #44)
        genesis_mint = self.genesis_artifacts.get("genesis_mint")
        if isinstance(genesis_mint, GenesisMint):
            genesis_mint.set_world(self)

        # Wire up rights registry to delegate to kernel (Plan #42)
        if self.rights_registry is not None:
            self.rights_registry.set_world(self)

        # Seed genesis_handbook artifact (readable documentation for agents)
        self._seed_handbook()

        # Initialize principals from config
        self.principal_ids = []
        default_starting_scrip: int = config_get("scrip.starting_amount") or 100

        # Per-agent LLM budget (Plan #12)
        # Get default from agents.initial_resources.llm_budget or budget.per_agent_budget
        budget_config = cast(dict[str, Any], config.get("budget", {}))
        agents_config = cast(dict[str, Any], config.get("agents", {}))
        initial_resources = cast(dict[str, Any], agents_config.get("initial_resources", {}))
        default_llm_budget: float = float(initial_resources.get(
            "llm_budget",
            budget_config.get("per_agent_budget", 0.0)  # 0 = no per-agent enforcement
        ))

        for p in config["principals"]:
            # Initialize with starting scrip (persistent currency)
            starting_scrip = p.get("starting_scrip", p.get("starting_credits", default_starting_scrip))

            # Per-agent LLM budget (stock resource, Plan #12)
            # Can be overridden per-principal or use default
            llm_budget_raw = p.get("llm_budget", default_llm_budget)
            llm_budget: float = float(cast(float, llm_budget_raw)) if llm_budget_raw is not None else 0.0
            starting_resources: dict[str, float] = {}
            if llm_budget > 0:
                starting_resources["llm_budget"] = llm_budget

            self.ledger.create_principal(
                p["id"],
                starting_scrip=starting_scrip,
                starting_resources=starting_resources if starting_resources else None,
            )
            self.principal_ids.append(p["id"])
            # Initialize agent in rights registry
            if self.rights_registry:
                self.rights_registry.ensure_agent(p["id"])

        # Autonomous loop support (INT-003)
        # Check if autonomous mode is enabled via config
        execution_config = cast(dict[str, Any], config.get("execution", {}))
        self.use_autonomous_loops = execution_config.get("use_autonomous_loops", False)

        # Create rate tracker if rate limiting is enabled (rate_limiting_config defined above)
        if self.use_rate_tracker:
            window_seconds = rate_limiting_config.get("window_seconds", 60.0)
            self.rate_tracker = RateTracker(window_seconds=window_seconds)
            # Configure limits for each resource
            resources_config = rate_limiting_config.get("resources", {})
            for resource_name, resource_cfg in resources_config.items():
                if isinstance(resource_cfg, dict):
                    max_per_window = resource_cfg.get("max_per_window", float("inf"))
                    self.rate_tracker.configure_limit(resource_name, max_per_window)
        else:
            self.rate_tracker = None

        # AgentLoopManager will be created by SimulationRunner when autonomous mode is enabled
        # We store it here so it's accessible to components that need it
        self.loop_manager = None

        # Invocation registry for observability (Gap #27)
        # Tracks all artifact invocations for stats and reputation emergence
        self.invocation_registry = InvocationRegistry()

        # NOTE: _quota_limits and _quota_usage are initialized earlier (line ~222)
        # to ensure they exist before rights_registry.ensure_agent() is called


        # Log world init
        default_quotas = self.rights_config.get("default_quotas", {})
        self.logger.log("world_init", {
            "rights": self.rights_config,
            "costs": self.costs,
            "principals": [
                {
                    "id": p["id"],
                    "starting_scrip": p.get("starting_scrip", p.get("starting_credits", default_starting_scrip)),
                    "llm_tokens_quota": int(default_quotas.get("llm_tokens", quotas.get("llm_tokens_quota", 50)))
                }
                for p in config["principals"]
            ]
        })

    def _seed_handbook(self) -> None:
        """Seed handbook artifacts from src/agents/_handbook/ files.

        Each .md file becomes a separate artifact (handbook_<name>).
        Agents can read specific sections they need.
        """
        handbook_dir = Path(__file__).parent.parent / "agents" / "_handbook"

        # Map of filename (without .md) to artifact_id
        handbook_sections = {
            "_index": "handbook_toc",
            "actions": "handbook_actions",
            "tools": "handbook_tools",
            "genesis": "handbook_genesis",
            "resources": "handbook_resources",
            "trading": "handbook_trading",
            "mint": "handbook_mint",
            "coordination": "handbook_coordination",
            "external": "handbook_external",
            "self": "handbook_self",
        }

        for section_name, artifact_id in handbook_sections.items():
            section_path = handbook_dir / f"{section_name}.md"
            if section_path.exists():
                content = section_path.read_text()
                self.artifacts.write(
                    artifact_id=artifact_id,
                    type="documentation",
                    content=content,
                    created_by="system",
                    executable=False,
                )

    # --- Kernel Mint Primitives (Plan #44) - Delegated to MintAuction (TD-001) ---

    def submit_for_mint(self, principal_id: str, artifact_id: str, bid: int) -> str:
        """Submit artifact for mint consideration. Returns submission_id."""
        return self.mint_auction.submit(principal_id, artifact_id, bid)

    def get_mint_submissions(self) -> list[KernelMintSubmission]:
        """Get all pending mint submissions."""
        return self.mint_auction.get_submissions()

    def get_mint_history(self, limit: int = 100) -> list[KernelMintResult]:
        """Get mint history (most recent first)."""
        return self.mint_auction.get_history(limit)

    def cancel_mint_submission(self, principal_id: str, submission_id: str) -> bool:
        """Cancel a mint submission and refund the bid."""
        return self.mint_auction.cancel(principal_id, submission_id)

    def resolve_mint_auction(self, _mock_score: int | None = None) -> KernelMintResult:
        """Resolve the current mint auction."""
        return self.mint_auction.resolve(_mock_score)

    def execute_action(self, intent: ActionIntent) -> ActionResult:
        """Execute an action intent. Returns the result.

        Actions are free. Real costs come from:
        - LLM tokens (thinking) - costs from compute budget
        - Disk quota (writing) - costs from disk allocation
        - Genesis method costs (configurable per-method)
        - Artifact prices (scrip paid to owner)
        """
        # Execute based on action type
        if isinstance(intent, NoopIntent):
            result = ActionResult(success=True, message="Noop executed")

        elif isinstance(intent, ReadArtifactIntent):
            # Check regular artifacts first
            artifact = self.artifacts.get(intent.artifact_id)
            if artifact:
                # Check read permission via contracts
                executor = get_executor()
                allowed, reason = executor._check_permission(intent.principal_id, "read", artifact)
                if not allowed:
                    result = ActionResult(
                        success=False,
                        message=get_error_message("access_denied_read", artifact_id=intent.artifact_id),
                        error_code=ErrorCode.NOT_AUTHORIZED.value,
                        error_category=ErrorCategory.PERMISSION.value,
                        retriable=False,
                    )
                else:
                    # Check if can afford read_price (economic cost -> SCRIP)
                    read_price: int = artifact.policy.get("read_price", 0)
                    if read_price > 0 and not self.ledger.can_afford_scrip(intent.principal_id, read_price):
                        result = ActionResult(
                            success=False,
                            message=f"Cannot afford read price: {read_price} scrip (have {self.ledger.get_scrip(intent.principal_id)})",
                            error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                            error_category=ErrorCategory.RESOURCE.value,
                            retriable=True,  # Can get more scrip and retry
                            error_details={"required": read_price, "available": self.ledger.get_scrip(intent.principal_id)},
                        )
                    else:
                        # Pay read_price to owner (economic transfer -> SCRIP)
                        if read_price > 0:
                            self.ledger.deduct_scrip(intent.principal_id, read_price)
                            self.ledger.credit_scrip(artifact.created_by, read_price)
                        result = ActionResult(
                            success=True,
                            message=f"Read artifact {intent.artifact_id}" + (f" (paid {read_price} scrip to {artifact.created_by})" if read_price > 0 else ""),
                            data={"artifact": artifact.to_dict(), "read_price_paid": read_price}
                        )
            # Check genesis artifacts (always public, free)
            elif intent.artifact_id in self.genesis_artifacts:
                genesis = self.genesis_artifacts[intent.artifact_id]
                result = ActionResult(
                    success=True,
                    message=f"Read genesis artifact {intent.artifact_id}",
                    data={"artifact": genesis.to_dict()}
                )
            else:
                # Plan #160: Suggest discovery via genesis_store
                result = ActionResult(
                    success=False,
                    message=(
                        f"Artifact '{intent.artifact_id}' not found. "
                        f"Use genesis_store.list([]) or genesis_store.search(['{intent.artifact_id[:10]}']) to find artifacts."
                    ),
                    error_code=ErrorCode.NOT_FOUND.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=False,
                    error_details={"artifact_id": intent.artifact_id},
                )

        elif isinstance(intent, WriteArtifactIntent):
            result = self._execute_write(intent)

        elif isinstance(intent, EditArtifactIntent):
            result = self._execute_edit(intent)

        elif isinstance(intent, InvokeArtifactIntent):
            result = self._execute_invoke(intent)

        elif isinstance(intent, DeleteArtifactIntent):
            result = self._execute_delete(intent)

        else:
            result = ActionResult(success=False, message="Unknown action type")

        self._log_action(intent, result)
        return result

    def _log_action(self, intent: ActionIntent, result: ActionResult) -> None:
        """Log an action execution"""
        # Plan #80: Use truncated result to prevent log file bloat
        max_data_size = config_get("logging.truncation.result_data")
        if not isinstance(max_data_size, int):
            max_data_size = 1000  # Default if not configured
        self.logger.log("action", {
            "event_number": self.event_number,
            "intent": intent.to_dict(),
            "result": result.to_dict_truncated(max_data_size),
            "scrip_after": self.ledger.get_scrip(intent.principal_id)
        })

    def _execute_write(self, intent: WriteArtifactIntent) -> ActionResult:
        """Execute a write_artifact action.

        Handles:
        - Protection of genesis artifacts
        - Write permission checks (policy-based)
        - Disk quota enforcement (when rights_registry available)
        - Executable code validation
        - Artifact creation/update via ArtifactStore.write_artifact()
        """
        # Protect genesis artifacts from modification
        if intent.artifact_id in self.genesis_artifacts:
            return ActionResult(
                success=False,
                message=f"Cannot modify system artifact {intent.artifact_id}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Check write permission for existing artifacts via contracts
        existing = self.artifacts.get(intent.artifact_id)
        if existing:
            executor = get_executor()
            allowed, reason = executor._check_permission(intent.principal_id, "write", existing)
            if not allowed:
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_write", artifact_id=intent.artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )

        # Calculate disk bytes
        new_size = len(intent.content.encode('utf-8')) + len(intent.code.encode('utf-8'))
        existing_size = self.artifacts.get_artifact_size(intent.artifact_id)
        net_new_bytes = max(0, new_size - existing_size)

        # Check disk quota if rights_registry is available (Layer 2: Stock Rights)
        if self.rights_registry:
            if net_new_bytes > 0 and not self.rights_registry.can_write(intent.principal_id, net_new_bytes):
                quota = self.rights_registry.get_disk_quota(intent.principal_id)
                used = self.rights_registry.get_disk_used(intent.principal_id)
                return ActionResult(
                    success=False,
                    message=f"Disk quota exceeded. Need {net_new_bytes} bytes, have {quota - used} available (quota: {quota}, used: {used})",
                    error_code=ErrorCode.QUOTA_EXCEEDED.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=True,  # Can free space or acquire more quota
                    error_details={"required": net_new_bytes, "available": quota - used, "quota": quota, "used": used},
                )

        # Validate executable code if provided
        if intent.executable:
            executor = get_executor()
            valid, error = executor.validate_code(intent.code)
            if not valid:
                return ActionResult(
                    success=False,
                    message=f"Invalid executable code: {error}",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"validation_error": error},
                )

        # Plan #160: Validate JSON for agent artifacts to prevent silent reload failures
        # Check if this is an agent artifact (either by type or existing artifact)
        is_agent_artifact = (
            intent.artifact_type == "agent" or
            (existing is not None and getattr(existing, 'is_agent', False))
        )
        if is_agent_artifact:
            import json
            try:
                json.loads(intent.content)
            except json.JSONDecodeError as e:
                return ActionResult(
                    success=False,
                    message=f"Invalid JSON in agent config: {e}. Self-modification requires valid JSON.",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=True,  # Agent can fix and retry
                    error_details={"json_error": str(e), "position": e.pos},
                )

        # Plan #114: Get interface requirement config
        require_interface = config_get("executor.require_interface_for_executables")
        if require_interface is None:
            require_interface = True  # Default to requiring interfaces

        # Write the artifact
        write_result: WriteResult = self.artifacts.write_artifact(
            artifact_id=intent.artifact_id,
            artifact_type=intent.artifact_type,
            content=intent.content,
            created_by=intent.principal_id,
            executable=intent.executable,
            price=intent.price,
            code=intent.code,
            policy=intent.policy,
            interface=intent.interface,
            require_interface=bool(require_interface),
            access_contract_id=intent.access_contract_id,
            metadata=intent.metadata,  # Plan #168: User-defined metadata
        )

        # Track resource consumption (disk bytes written)
        resources_consumed: dict[str, float] = {}
        if net_new_bytes > 0:
            resources_consumed["disk_bytes"] = float(net_new_bytes)

        # Plan #151: Emit disk allocation event on successful write
        if write_result["success"] and net_new_bytes > 0 and self.rights_registry:
            used_after = self.rights_registry.get_disk_used(intent.principal_id)
            quota = self.rights_registry.get_disk_quota(intent.principal_id)
            self.logger.log_resource_allocated(
                principal_id=intent.principal_id,
                resource="disk",
                amount=float(net_new_bytes),
                used_after=float(used_after),
                quota=float(quota),
            )

        return ActionResult(
            success=write_result["success"],
            message=write_result["message"],
            data=write_result["data"],
            resources_consumed=resources_consumed if resources_consumed else None,
            charged_to=intent.principal_id,
        )

    def _execute_edit(self, intent: EditArtifactIntent) -> ActionResult:
        """Execute an edit_artifact action.

        Plan #131: Claude Code-style editing using old_string/new_string replacement.

        Handles:
        - Protection of genesis artifacts
        - Write permission checks (policy-based)
        - Uniqueness validation (old_string must appear exactly once)
        - Artifact editing via ArtifactStore.edit_artifact()
        """
        # Protect genesis artifacts from modification
        if intent.artifact_id in self.genesis_artifacts:
            return ActionResult(
                success=False,
                message=f"Cannot modify system artifact {intent.artifact_id}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Check if artifact exists
        existing = self.artifacts.get(intent.artifact_id)
        if not existing:
            return ActionResult(
                success=False,
                message=f"Artifact '{intent.artifact_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check edit permission via contracts (ADR-0019: edit is distinct from write)
        executor = get_executor()
        allowed, reason = executor._check_permission(intent.principal_id, "edit", existing)
        if not allowed:
            return ActionResult(
                success=False,
                message=get_error_message("access_denied_edit", artifact_id=intent.artifact_id),
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Execute the edit
        edit_result: WriteResult = self.artifacts.edit_artifact(
            artifact_id=intent.artifact_id,
            old_string=intent.old_string,
            new_string=intent.new_string,
        )

        if not edit_result["success"]:
            # Determine appropriate error code based on the error
            error_data = edit_result.get("data") or {}
            error_type = error_data.get("error", "")

            if error_type == "not_unique":
                error_code = ErrorCode.INVALID_ARGUMENT.value
                error_category = ErrorCategory.VALIDATION.value
            elif error_type == "not_found_in_content":
                error_code = ErrorCode.INVALID_ARGUMENT.value
                error_category = ErrorCategory.VALIDATION.value
            elif error_type == "deleted":
                error_code = ErrorCode.NOT_FOUND.value
                error_category = ErrorCategory.RESOURCE.value
            else:
                error_code = ErrorCode.INVALID_ARGUMENT.value
                error_category = ErrorCategory.VALIDATION.value

            return ActionResult(
                success=False,
                message=edit_result["message"],
                error_code=error_code,
                error_category=error_category,
                retriable=False,
                error_details=error_data,
            )

        return ActionResult(
            success=True,
            message=edit_result["message"],
            data=edit_result["data"],
            charged_to=intent.principal_id,
        )

    def _execute_invoke(self, intent: InvokeArtifactIntent) -> ActionResult:
        """Execute an invoke_artifact action.

        Handles both:
        - Genesis artifacts (system proxies to ledger, mint, etc.)
        - Executable artifacts (agent-created code)

        Cost model:
        - Genesis method costs: Configurable compute cost per method
        - Artifact prices: Scrip paid to owner on successful invocation

        Invocation tracking (Gap #27):
        - Logs invoke_success/invoke_failure events
        - Records invocations in the registry for observability
        """
        artifact_id = intent.artifact_id
        method_name = intent.method
        args = intent.args
        start_time = time.perf_counter()

        # Plan #15: Unified invoke path - all artifacts via artifact store
        artifact = self.artifacts.get(artifact_id)
        if artifact:
            if not artifact.executable:
                # Plan #160: Suggest alternative - use read_artifact for data/config artifacts
                duration_ms = (time.perf_counter() - start_time) * 1000
                helpful_msg = (
                    f"Artifact {artifact_id} is not executable (it's a data artifact). "
                    f"Use read_artifact with artifact_id='{artifact_id}' to read its content."
                )
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "not_executable", helpful_msg
                )
                return ActionResult(
                    success=False,
                    message=helpful_msg,
                    error_code=ErrorCode.INVALID_TYPE.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"artifact_id": artifact_id, "executable": False},
                )

            # Check invoke permission via contracts (ADR-0019: pass method/args in context)
            executor = get_executor()
            allowed, reason = executor._check_permission(
                intent.principal_id, "invoke", artifact, method=method_name, args=args
            )
            if not allowed:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "permission_denied",
                    reason
                )
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_invoke", artifact_id=artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )

            # Plan #161: Auto-describe method
            # Every artifact automatically has a 'describe' method that returns its interface.
            # This helps agents discover what methods an artifact has before invoking.
            if method_name == "describe":
                interface = artifact.interface or {}
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_success(
                    intent.principal_id, artifact_id, method_name, duration_ms, "dict"
                )
                return ActionResult(
                    success=True,
                    message=f"Interface for {artifact_id}",
                    data={
                        "artifact_id": artifact_id,
                        "type": artifact.type,
                        "created_by": artifact.created_by,
                        "executable": artifact.executable,
                        "description": interface.get("description", artifact.content),
                        "methods": [
                            {
                                "name": t.get("name"),
                                "description": t.get("description", ""),
                                "parameters": t.get("inputSchema", {}).get("properties", {}),
                            }
                            for t in interface.get("tools", [])
                        ],
                    },
                )

            # Plan #160: Config artifact methods (cognitive self-modification)
            # Agents can read/modify their own configuration at runtime
            if artifact.type == "config":
                # Only the owner can access their config
                if artifact.created_by != intent.principal_id:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "not_authorized",
                        "Only the config owner can access it"
                    )
                    return ActionResult(
                        success=False,
                        message=f"Permission denied: only {artifact.created_by} can access this config",
                        error_code=ErrorCode.NOT_AUTHORIZED.value,
                        error_category=ErrorCategory.PERMISSION.value,
                        retriable=False,
                    )

                config_data: dict[str, Any] = json.loads(artifact.content) if artifact.content else {}

                if method_name == "get":
                    key = args.get("key") if isinstance(args, dict) else (args[0] if args else None)
                    if not key:
                        return ActionResult(
                            success=False,
                            message="Missing required argument: key",
                            error_code=ErrorCode.INVALID_ARGUMENT.value,
                            error_category=ErrorCategory.VALIDATION.value,
                            retriable=False,
                        )
                    value = config_data.get(key)
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_success(
                        intent.principal_id, artifact_id, method_name, duration_ms, type(value).__name__
                    )
                    return ActionResult(
                        success=True,
                        message=f"Config value for '{key}': {value}",
                        data={"key": key, "value": value},
                    )

                elif method_name == "set":
                    key = args.get("key") if isinstance(args, dict) else (args[0] if len(args) > 0 else None)
                    value = args.get("value") if isinstance(args, dict) else (args[1] if len(args) > 1 else None)
                    if not key:
                        return ActionResult(
                            success=False,
                            message="Missing required argument: key",
                            error_code=ErrorCode.INVALID_ARGUMENT.value,
                            error_category=ErrorCategory.VALIDATION.value,
                            retriable=False,
                        )
                    old_value = config_data.get(key)
                    config_data[key] = value
                    artifact.content = json.dumps(config_data)
                    from datetime import datetime, timezone
                    artifact.updated_at = datetime.now(timezone.utc).isoformat()
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_success(
                        intent.principal_id, artifact_id, method_name, duration_ms, "bool"
                    )
                    return ActionResult(
                        success=True,
                        message=f"Config '{key}' updated: {old_value} -> {value}",
                        data={"key": key, "old_value": old_value, "new_value": value},
                    )

                elif method_name == "list_keys":
                    keys = list(config_data.keys())
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_success(
                        intent.principal_id, artifact_id, method_name, duration_ms, "list"
                    )
                    return ActionResult(
                        success=True,
                        message=f"Config keys: {keys}",
                        data={"keys": keys, "config": config_data},
                    )

                else:
                    return ActionResult(
                        success=False,
                        message=f"Unknown config method: {method_name}. Available: get, set, list_keys, describe",
                        error_code=ErrorCode.NOT_FOUND.value,
                        error_category=ErrorCategory.RESOURCE.value,
                        retriable=False,
                    )

            # Plan #86: Interface validation
            # Validate args against artifact's declared interface schema if available
            from ..config import get_validated_config
            validation_mode = get_validated_config().executor.interface_validation

            # Plan #160: Parse JSON strings in args BEFORE validation
            # LLMs often generate ['{"key": "value"}'] instead of [{"key": "value"}]
            # This converts stringified JSON to actual Python objects
            parsed_args: list[Any] | dict[str, Any] = intent.args or []
            if isinstance(parsed_args, list):
                parsed_args = parse_json_args(parsed_args)

            # Convert args list to named dict for validation
            # Maps positional args like ["genesis_ledger"] to {"artifact_id": "genesis_ledger"}
            # based on the interface schema's property names
            args_dict: dict[str, Any] = {}
            if parsed_args:
                if isinstance(parsed_args, dict):
                    args_dict = parsed_args
                elif isinstance(parsed_args, list) and len(parsed_args) > 0:
                    # If first arg is already a dict (after JSON parsing), use it directly
                    if len(parsed_args) == 1 and isinstance(parsed_args[0], dict):
                        args_dict = parsed_args[0]
                    else:
                        # Use interface schema to map positional args to named properties
                        args_dict = convert_positional_to_named_args(
                            interface=artifact.interface,
                            method_name=method_name,
                            args=parsed_args,
                        )

            validation_result = validate_args_against_interface(
                interface=artifact.interface,
                method_name=method_name,
                args=args_dict,
                validation_mode=validation_mode,
            )

            if not validation_result.proceed:
                # Strict mode - reject the invocation
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "interface_validation_failed",
                    validation_result.error_message
                )
                return ActionResult(
                    success=False,
                    message=f"Interface validation failed: {validation_result.error_message}",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"validation_error": validation_result.error_message},
                )

            # Plan #160: Use coerced args if available (e.g., "5" -> 5)
            # Convert coerced dict back to positional list for genesis methods
            effective_args = args
            if validation_result.coerced_args is not None:
                effective_args = convert_named_to_positional_args(
                    interface=artifact.interface,
                    method_name=method_name,
                    args_dict=validation_result.coerced_args,
                )

            # Plan #15: Genesis method dispatch (if genesis_methods is set)
            # Plan #125: Extracted to _invoke_genesis_method for clarity
            if artifact.genesis_methods is not None:
                return self._invoke_genesis_method(intent, artifact, method_name, effective_args, start_time)

            # Regular artifact code execution path
            # Plan #125: Extracted to _invoke_user_artifact for clarity
            return self._invoke_user_artifact(intent, artifact, method_name, effective_args, start_time)

        # Artifact not found - Plan #160: Suggest discovery via genesis_store
        duration_ms = (time.perf_counter() - start_time) * 1000
        helpful_msg = (
            f"Artifact '{artifact_id}' not found. "
            f"Use genesis_store.list([]) or genesis_store.search(['{artifact_id[:10]}']) to find artifacts."
        )
        self._log_invoke_failure(
            intent.principal_id, artifact_id, method_name,
            duration_ms, "not_found", helpful_msg
        )
        return ActionResult(
            success=False,
            message=helpful_msg,
            error_code=ErrorCode.NOT_FOUND.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=False,
            error_details={"artifact_id": artifact_id},
        )

    def _execute_delete(self, intent: DeleteArtifactIntent) -> ActionResult:
        """Execute a delete_artifact action (Plan #57, #140).

        Soft deletes an artifact, freeing disk quota.
        Permission is checked via the artifact's access contract (Plan #140).
        Genesis artifacts cannot be deleted.
        """
        # Check if genesis artifact (kernel-level protection, not policy)
        if intent.artifact_id.startswith("genesis_"):
            return ActionResult(
                success=False,
                message="Cannot delete genesis artifacts",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check if artifact exists
        artifact = self.artifacts.get(intent.artifact_id)
        if not artifact:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check if already deleted
        if artifact.deleted:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} is already deleted",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Plan #140: Check delete permission via contract (not hardcoded created_by check)
        executor = get_executor()
        allowed, reason = executor._check_permission(intent.principal_id, "delete", artifact)
        if not allowed:
            return ActionResult(
                success=False,
                message=f"Delete not permitted: {reason}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Calculate freed disk space before deletion
        freed_bytes = len(artifact.content.encode("utf-8")) + len(artifact.code.encode("utf-8"))

        # Perform soft delete
        from datetime import datetime, timezone
        artifact.deleted = True
        artifact.deleted_at = datetime.now(timezone.utc).isoformat()
        artifact.deleted_by = intent.principal_id

        # Log the deletion
        self.logger.log("artifact_deleted", {
            "event_number": self.event_number,
            "artifact_id": intent.artifact_id,
            "deleted_by": intent.principal_id,
            "deleted_at": artifact.deleted_at,
        })

        return ActionResult(
            success=True,
            message=f"Deleted artifact {intent.artifact_id}",
            data={"artifact_id": intent.artifact_id, "freed_bytes": freed_bytes},
        )

    def _log_invoke_success(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        duration_ms: float,
        result_type: str,
    ) -> None:
        """Log a successful invocation and record in registry."""
        self.logger.log("invoke_success", {
            "event_number": self.event_number,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "result_type": result_type,
        })
        self.invocation_registry.record_invocation(InvocationRecord(
            event_number=self.event_number,
            invoker_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            success=True,
            duration_ms=duration_ms,
        ))

    def _log_invoke_failure(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        duration_ms: float,
        error_type: str,
        error_message: str,
    ) -> None:
        """Log a failed invocation and record in registry."""
        self.logger.log("invoke_failure", {
            "event_number": self.event_number,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "error_type": error_type,
            "error_message": error_message,
        })
        self.invocation_registry.record_invocation(InvocationRecord(
            event_number=self.event_number,
            invoker_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
        ))

    def _invoke_genesis_method(
        self,
        intent: InvokeArtifactIntent,
        artifact: Artifact,
        method_name: str,
        args: Any,
        start_time: float,
    ) -> ActionResult:
        """Execute a genesis artifact method.

        Plan #125: Extracted from _execute_invoke() for clarity.

        Handles:
        - Method lookup in genesis_methods
        - Compute affordability check
        - Compute cost deduction
        - Method execution with error handling
        """
        artifact_id = intent.artifact_id

        # genesis_methods is guaranteed non-None here (caller checks)
        assert artifact.genesis_methods is not None
        method = artifact.genesis_methods.get(method_name)
        if not method:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "method_not_found",
                f"Method {method_name} not found"
            )
            return ActionResult(
                success=False,
                message=get_error_message(
                    "method_not_found",
                    method=method_name,
                    artifact_id=artifact_id,
                    methods=list(artifact.genesis_methods.keys())
                ),
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"method": method_name, "artifact_id": artifact_id},
            )

        # Genesis method costs are LLM tokens (physical resource, not scrip)
        if method.cost > 0 and not self.ledger.can_spend_llm_tokens(intent.principal_id, method.cost):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "insufficient_llm_tokens",
                f"Cannot afford method cost: {method.cost}"
            )
            return ActionResult(
                success=False,
                message=f"Cannot afford method cost: {method.cost} llm_tokens (have {self.ledger.get_llm_tokens(intent.principal_id)})",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"required": method.cost, "available": self.ledger.get_llm_tokens(intent.principal_id)},
            )

        # Deduct LLM token cost FIRST (always paid, even on failure)
        resources_consumed: dict[str, float] = {}
        if method.cost > 0:
            self.ledger.spend_llm_tokens(intent.principal_id, method.cost)
            resources_consumed["llm_tokens"] = float(method.cost)

        # Execute the genesis method
        try:
            result_data: dict[str, Any] = method.handler(args, intent.principal_id)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if result_data.get("success"):
                self._log_invoke_success(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, type(result_data.get("result")).__name__
                )
                # Plan #160: Show brief result preview for better feedback
                result_value = result_data.get("result")
                result_preview = ""
                if result_value is not None:
                    result_str = str(result_value)[:100]
                    if len(str(result_value)) > 100:
                        result_str += "..."
                    result_preview = f". Result: {result_str}"
                return ActionResult(
                    success=True,
                    message=f"Invoked {artifact_id}.{method_name}{result_preview}",
                    data=result_data,
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=intent.principal_id,
                )
            else:
                error_code = result_data.get("code", ErrorCode.RUNTIME_ERROR.value)
                error_category = result_data.get("category", ErrorCategory.EXECUTION.value)
                retriable = result_data.get("retriable", False)
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "method_failed",
                    result_data.get("error", "Method failed")
                )
                return ActionResult(
                    success=False,
                    message=result_data.get("error", "Method failed"),
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=intent.principal_id,
                    error_code=error_code,
                    error_category=error_category,
                    retriable=retriable,
                    error_details=result_data.get("details"),
                )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "exception",
                str(e)
            )
            return ActionResult(
                success=False,
                message=f"Method execution error: {str(e)}",
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=intent.principal_id,
                error_code=ErrorCode.RUNTIME_ERROR.value,
                error_category=ErrorCategory.EXECUTION.value,
                retriable=False,
                error_details={"exception": str(e)},
            )

    def _invoke_user_artifact(
        self,
        intent: InvokeArtifactIntent,
        artifact: Artifact,
        method_name: str,
        args: Any,
        start_time: float,
    ) -> ActionResult:
        """Execute a user-defined artifact method.

        Plan #125: Extracted from _execute_invoke() for clarity.

        Handles:
        - Scrip price affordability check
        - Code execution via executor
        - Resource consumption tracking
        - Price payment to owner
        """
        artifact_id = intent.artifact_id
        price = artifact.price
        created_by = artifact.created_by
        resource_payer = intent.principal_id

        # Check if caller can afford the price (scrip)
        if price > 0 and not self.ledger.can_afford_scrip(intent.principal_id, price):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "insufficient_scrip",
                f"Insufficient scrip for price: need {price}"
            )
            return ActionResult(
                success=False,
                message=f"Insufficient scrip for price: need {price}, have {self.ledger.get_scrip(intent.principal_id)}",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"required": price, "available": self.ledger.get_scrip(intent.principal_id)},
            )

        # Execute the code with invoke() capability for composition
        # Pass world for kernel interface injection (Plan #39 - Genesis Unprivilege)
        executor = get_executor()
        exec_result = executor.execute_with_invoke(
            code=artifact.code,
            args=args,
            caller_id=intent.principal_id,
            artifact_id=artifact_id,
            ledger=self.ledger,
            artifact_store=self.artifacts,
            world=self,
        )

        # Extract resource consumption from executor
        resources_consumed = exec_result.get("resources_consumed", {})
        duration_ms = exec_result.get("execution_time_ms", (time.perf_counter() - start_time) * 1000)

        # Resources use different tracking mechanisms:
        # - Rate-limited (renewable via rolling window): cpu_seconds
        # - Balance-based (depletable): llm_tokens, disk_bytes, etc.
        rate_limited_resources = {"cpu_seconds"}

        if exec_result.get("success"):
            # Deduct physical resources from caller
            for resource, amount in resources_consumed.items():
                if resource in rate_limited_resources:
                    # Rate-limited resource: record in rolling window rate tracker
                    self.ledger.consume_resource(resource_payer, resource, amount)
                elif not self.ledger.can_spend_resource(resource_payer, resource, amount):
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "insufficient_resource",
                        f"Insufficient {resource}: need {amount}"
                    )
                    return ActionResult(
                        success=False,
                        message=f"Insufficient {resource}: need {amount}",
                        resources_consumed=resources_consumed,
                        charged_to=resource_payer,
                        error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                        error_category=ErrorCategory.RESOURCE.value,
                        retriable=True,
                        error_details={"resource": resource, "required": amount},
                    )
                else:
                    self.ledger.spend_resource(resource_payer, resource, amount)

            # Pay price to owner from SCRIP (only on success)
            if price > 0 and created_by != intent.principal_id:
                self.ledger.deduct_scrip(intent.principal_id, price)
                self.ledger.credit_scrip(created_by, price)
                # Plan #160: Log revenue/cost events so agents can track money flow
                self.logger.log("scrip_earned", {
                    "event_number": self.event_number,
                    "recipient": created_by,
                    "amount": price,
                    "from": intent.principal_id,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })
                self.logger.log("scrip_spent", {
                    "event_number": self.event_number,
                    "spender": intent.principal_id,
                    "amount": price,
                    "to": created_by,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })

            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name,
                duration_ms, type(exec_result.get("result")).__name__
            )
            # Plan #160: Clarify self-invoke feedback - agent needs to understand it doesn't earn revenue
            if price > 0 and created_by == intent.principal_id:
                price_msg = f" (self-invoke: no scrip transferred, you paid yourself)"
            elif price > 0:
                price_msg = f" (paid {price} scrip to {created_by})"
            else:
                price_msg = ""
            # Plan #160: Show brief result preview for better feedback
            result_value = exec_result.get("result")
            result_preview = ""
            if result_value is not None:
                result_str = str(result_value)[:100]
                if len(str(result_value)) > 100:
                    result_str += "..."
                result_preview = f". Result: {result_str}"
            return ActionResult(
                success=True,
                message=f"Invoked {artifact_id}{price_msg}{result_preview}",
                data={
                    "result": exec_result.get("result"),
                    "price_paid": price,
                    "owner": created_by
                },
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=resource_payer,
            )
        else:
            # Execution failed - still charge resources (they were consumed)
            for resource, amount in resources_consumed.items():
                if resource in rate_limited_resources:
                    # Rate-limited: record in rolling window
                    self.ledger.consume_resource(resource_payer, resource, amount)
                elif self.ledger.can_spend_resource(resource_payer, resource, amount):
                    self.ledger.spend_resource(resource_payer, resource, amount)

            error_msg = exec_result.get("error", "Unknown error")
            # Determine error type and code from error message
            error_type = "execution"
            error_code = ErrorCode.RUNTIME_ERROR.value
            error_category = ErrorCategory.EXECUTION.value
            retriable = False
            if "timed out" in error_msg.lower():
                error_type = "timeout"
                error_code = ErrorCode.TIMEOUT.value
                retriable = True
            elif "syntax" in error_msg.lower():
                error_type = "validation"
                error_code = ErrorCode.SYNTAX_ERROR.value
                error_category = ErrorCategory.VALIDATION.value

            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, error_type, error_msg
            )
            return ActionResult(
                success=False,
                message=f"Execution failed: {error_msg}",
                data={"error": error_msg},
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=resource_payer,
                error_code=error_code,
                error_category=error_category,
                retriable=retriable,
                error_details={"artifact_id": artifact_id, "error": error_msg},
            )

    def increment_event_counter(self) -> int:
        """Increment the event counter and return the new value.

        Used for event ordering in logs. Not related to execution timing.
        """
        self.event_number += 1

        # Update event_number in debt contract if present (for backward compat)
        # Note: Debt contract still uses tick internally - needs separate redesign
        debt_contract = self.genesis_artifacts.get("genesis_debt_contract")
        if isinstance(debt_contract, GenesisDebtContract):
            debt_contract.set_tick(self.event_number)

        return self.event_number

    def advance_tick(self) -> bool:
        """Increment event counter. Deprecated - use increment_event_counter().

        .. deprecated:: Plan #102
            This method is retained for backward compatibility with tests.
            Execution limits are now time-based (duration) or cost-based (budget).
            Always returns True.
        """
        self.increment_event_counter()
        return True

    def get_state_summary(self) -> StateSummary:
        """Get a summary of current world state"""
        # Get all artifacts from store (includes genesis artifacts which
        # were registered in __init__ via artifacts.write())
        all_artifacts: list[dict[str, Any]] = self.artifacts.list_all()

        # Get quota info for all agents
        quotas: dict[str, QuotaInfo] = {}
        if self.rights_registry:
            for pid in self.principal_ids:
                quotas[pid] = {
                    "llm_tokens_quota": self.rights_registry.get_llm_tokens_quota(pid),
                    "disk_quota": self.rights_registry.get_disk_quota(pid),
                    "disk_used": self.rights_registry.get_disk_used(pid),
                    "disk_available": self.rights_registry.get_disk_quota(pid) - self.rights_registry.get_disk_used(pid)
                }

        # Get mint submission status
        mint_status: dict[str, MintSubmissionStatus] = {}
        mint = self.genesis_artifacts.get("genesis_mint")
        if mint and isinstance(mint, GenesisMint) and hasattr(mint, 'submissions'):
            for artifact_id, sub in mint.submissions.items():
                mint_status[artifact_id] = {
                    "status": sub.get("status", "unknown"),
                    "submitter": sub.get("submitter", "unknown"),
                    "score": sub.get("score") if sub.get("status") == "scored" else None
                }

        # Get resource metrics for all agents (Plan #93)
        # Note: We iterate over principal_ids since World doesn't have agents dict
        # LLM stats will be supplemented in build_prompt()
        resource_metrics: dict[str, dict[str, Any]] = {}
        for agent_id in self.principal_ids:
            if agent_id.startswith("genesis_"):
                continue  # Skip genesis artifacts
            metrics = self.resource_metrics_provider.get_agent_metrics(
                agent_id=agent_id,
                ledger_resources=self.ledger.resources,
                agents={},  # World doesn't have access to agents; LLM stats added in build_prompt
                start_time=self._simulation_start_time,
                visibility_config=None,  # Use default (verbose) for state summary
            )
            resource_metrics[agent_id] = {
                "timestamp": metrics.timestamp,
                "resources": {
                    name: {
                        "resource_name": rm.resource_name,
                        "unit": rm.unit,
                        "remaining": rm.remaining,
                        "initial": rm.initial,
                        "spent": rm.spent,
                        "percentage": rm.percentage,
                        "burn_rate": rm.burn_rate,
                    }
                    for name, rm in metrics.resources.items()
                },
            }

        # Plan #157: Time context for goal clarity
        elapsed = time.time() - self._simulation_start_time
        time_context: dict[str, Any] = {
            "elapsed_seconds": elapsed,
            "duration_seconds": self._simulation_duration,
            "time_remaining_seconds": (self._simulation_duration - elapsed) if self._simulation_duration else None,
            "progress_percent": (elapsed / self._simulation_duration * 100) if self._simulation_duration else None,
        }

        return {
            "event_number": self.event_number,
            "balances": self.ledger.get_all_balances(),
            "artifacts": all_artifacts,
            "quotas": quotas,
            "mint_submissions": mint_status,
            "recent_events": self.get_recent_events(10),
            "resource_metrics": resource_metrics,
            "time_context": time_context,  # Plan #157
        }

    def set_simulation_duration(self, duration: float) -> None:
        """Set the total simulation duration for time awareness (Plan #157)."""
        self._simulation_duration = duration

    def get_recent_events(self, n: int = 20) -> list[dict[str, Any]]:
        """Get recent events from the log"""
        return self.logger.read_recent(n)

    # -------------------------------------------------------------------------
    # Convenience methods for artifact operations (Plan #18)
    # -------------------------------------------------------------------------

    def delete_artifact(self, artifact_id: str, requester_id: str) -> dict[str, Any]:
        """Delete an artifact (soft delete with tombstone).

        Permission is checked via the artifact's access contract (Plan #140).
        Genesis artifacts cannot be deleted (kernel-level protection).

        Args:
            artifact_id: ID of artifact to delete
            requester_id: ID of principal requesting deletion

        Returns:
            {"success": True} on success
            {"success": False, "error": "..."} on failure
        """
        from datetime import datetime, timezone
        from src.world.executor import get_executor

        # Check if genesis artifact (kernel-level protection)
        if artifact_id.startswith("genesis_"):
            return {"success": False, "error": "Cannot delete genesis artifacts"}

        # Check if artifact exists
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Check if already deleted
        if artifact.deleted:
            return {"success": False, "error": f"Artifact {artifact_id} is already deleted"}

        # Plan #140: Check delete permission via contract (not hardcoded created_by check)
        executor = get_executor()
        allowed, reason = executor._check_permission(requester_id, "delete", artifact)
        if not allowed:
            return {"success": False, "error": f"Delete not permitted: {reason}"}

        # Soft delete - mark as tombstone
        artifact.deleted = True
        artifact.deleted_at = datetime.now(timezone.utc).isoformat()
        artifact.deleted_by = requester_id

        # Log the deletion
        self.logger.log("artifact_deleted", {
            "event_number": self.event_number,
            "artifact_id": artifact_id,
            "deleted_by": requester_id,
            "deleted_at": artifact.deleted_at,
        })

        return {"success": True}

    def read_artifact(self, requester_id: str, artifact_id: str) -> dict[str, Any]:
        """Read an artifact's content.

        Returns tombstone metadata if artifact is deleted.

        Args:
            requester_id: ID of principal reading
            artifact_id: ID of artifact to read

        Returns:
            Artifact data including deletion fields if deleted
        """
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Return tombstone metadata for deleted artifacts
        if artifact.deleted:
            return {
                "id": artifact.id,
                "created_by": artifact.created_by,
                "deleted": True,
                "deleted_at": artifact.deleted_at,
                "deleted_by": artifact.deleted_by,
            }

        # Use execute_action for full permission/pricing logic
        intent = ReadArtifactIntent(principal_id=requester_id, artifact_id=artifact_id)
        result = self.execute_action(intent)
        if result.success and result.data:
            artifact_data: dict[str, Any] = result.data.get("artifact", {})
            return artifact_data
        return {"success": False, "error": result.message}

    def write_artifact(
        self,
        agent_id: str,
        artifact_id: str,
        artifact_type: str,
        content: str,
        executable: bool = False,
        price: int = 0,
        code: str = "",
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write or create an artifact.

        Cannot write to deleted artifacts.

        Args:
            agent_id: ID of principal writing
            artifact_id: ID of artifact to write
            artifact_type: Type of artifact
            content: Artifact content
            executable: Whether artifact is executable
            price: Invoke price
            code: Code for executable artifacts
            policy: Access policy

        Returns:
            {"success": True, "message": "..."} on success
            {"success": False, "message": "..."} on failure
        """
        # Check if artifact exists and is deleted
        existing = self.artifacts.get(artifact_id)
        if existing and existing.deleted:
            return {"success": False, "message": f"Cannot write to deleted artifact {artifact_id}"}

        intent = WriteArtifactIntent(
            principal_id=agent_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=content,
            executable=executable,
            price=price,
            code=code,
            policy=policy,
        )
        result = self.execute_action(intent)
        return {"success": result.success, "message": result.message}

    def invoke_artifact(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        args: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke a method on an artifact.

        Returns DELETED error if artifact is deleted.

        Args:
            invoker_id: ID of principal invoking
            artifact_id: ID of artifact to invoke
            method: Method name to invoke
            args: Arguments to pass to method

        Returns:
            {"success": True, ...} on success
            {"success": False, "error_code": "DELETED", ...} if deleted
        """
        # Check if deleted (for regular artifacts)
        artifact = self.artifacts.get(artifact_id)
        if artifact and artifact.deleted:
            return {
                "success": False,
                "error_code": "DELETED",
                "error": f"Artifact {artifact_id} was deleted at {artifact.deleted_at}",
            }

        intent = InvokeArtifactIntent(
            principal_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            args=args,
        )
        result = self.execute_action(intent)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }

    # -------------------------------------------------------------------------
    # Vulture Observability - Freeze/Unfreeze Events (Plan #26)
    # -------------------------------------------------------------------------

    def is_agent_frozen(self, agent_id: str) -> bool:
        """Check if an agent is frozen (compute exhausted).

        An agent is frozen when their llm_tokens (compute) resource is <= 0.
        With rate limiting enabled, checks the rate limiter's remaining capacity.

        Args:
            agent_id: ID of agent to check

        Returns:
            True if agent is frozen, False otherwise
        """
        # Check rate limiter first (primary source of truth for compute)
        remaining = self.ledger.get_resource_remaining(agent_id, "llm_tokens")
        if remaining != float("inf"):
            # Rate limiting is enabled - use rate limiter
            return remaining <= 0

        # Fallback to stock resource check (legacy mode)
        compute = self.ledger.get_resource(agent_id, "llm_tokens")
        return compute <= 0

    def get_frozen_agents(self) -> list[str]:
        """Get list of all frozen agents.

        Returns:
            List of agent IDs that are currently frozen
        """
        frozen = []
        for pid in self.principal_ids:
            if self.is_agent_frozen(pid):
                frozen.append(pid)
        return frozen

    def emit_agent_frozen(
        self,
        agent_id: str,
        reason: str = "compute_exhausted",
        last_action_at: int | None = None,
    ) -> None:
        """Emit an AGENT_FROZEN event for vulture observability.

        Args:
            agent_id: ID of agent that froze
            reason: Why agent froze (compute_exhausted, rate_limited, etc.)
            last_action_at: Event number of agent's last successful action
        """
        self.logger.log("agent_frozen", {
            "event_number": self.event_number,
            "agent_id": agent_id,
            "reason": reason,
            "scrip_balance": self.ledger.get_scrip(agent_id),
            "compute_remaining": self.ledger.get_resource(agent_id, "llm_tokens"),
            "owned_artifacts": self.artifacts.get_artifacts_by_owner(agent_id),
            "last_action_at": last_action_at or self.event_number,
        })

        # Plan #151: Emit agent_state event per ADR-0020
        self._emit_agent_state(agent_id, frozen_reason=reason)

    def emit_agent_unfrozen(
        self,
        agent_id: str,
        unfrozen_by: str = "self",
        resources_transferred: dict[str, float] | None = None,
    ) -> None:
        """Emit an AGENT_UNFROZEN event for vulture observability.

        Args:
            agent_id: ID of agent that unfroze
            unfrozen_by: ID of agent who transferred resources ("self" for natural recovery)
            resources_transferred: Resources that were transferred to unfreeze
        """
        self.logger.log("agent_unfrozen", {
            "event_number": self.event_number,
            "agent_id": agent_id,
            "unfrozen_by": unfrozen_by,
            "resources_transferred": resources_transferred or {},
        })

        # Plan #151: Emit agent_state event per ADR-0020
        self._emit_agent_state(agent_id)

    def _emit_agent_state(self, agent_id: str, frozen_reason: str | None = None) -> None:
        """Emit an agent_state event with full resource info (Plan #151, ADR-0020).

        Args:
            agent_id: The agent whose state changed
            frozen_reason: If frozen, the reason why
        """
        # Determine status
        if self.is_agent_frozen(agent_id):
            status = "frozen"
        else:
            status = "active"

        # Build resource state
        resources: dict[str, dict[str, float]] = {}

        # LLM tokens (renewable)
        llm_tokens_used = self.ledger.get_resource(agent_id, "llm_tokens")
        if self.rights_registry:
            llm_tokens_quota = self.rights_registry.get_llm_tokens_quota(agent_id)
            resources["llm_tokens"] = {
                "used": float(llm_tokens_used),
                "quota": float(llm_tokens_quota),
                "remaining": float(llm_tokens_quota - llm_tokens_used),
            }

        # Disk (allocatable)
        if self.rights_registry:
            disk_used = self.rights_registry.get_disk_used(agent_id)
            disk_quota = self.rights_registry.get_disk_quota(agent_id)
            resources["disk"] = {
                "used": float(disk_used),
                "quota": float(disk_quota),
            }

        self.logger.log_agent_state(
            agent_id=agent_id,
            status=status,
            scrip=float(self.ledger.get_scrip(agent_id)),
            resources=resources,
            frozen_reason=frozen_reason,
        )

    # -------------------------------------------------------------------------
    # Kernel Quota Primitives (Plan #42)
    # -------------------------------------------------------------------------

    def set_quota(self, principal_id: str, resource: str, amount: float) -> None:
        """Set quota limit for a principal's resource.

        This is kernel state - quotas are physics, not genesis artifact state.
        Delegates to ResourceManager (Plan #95).

        Args:
            principal_id: The principal to set quota for
            resource: Resource name (e.g., "cpu_seconds_per_minute", "llm_tokens_per_minute")
            amount: Quota limit (must be >= 0)
        """
        if amount < 0:
            raise ValueError(f"Quota amount must be >= 0, got {amount}")

        # Ensure principal exists in ResourceManager
        if not self.resource_manager.principal_exists(principal_id):
            self.resource_manager.create_principal(principal_id)

        self.resource_manager.set_quota(principal_id, resource, amount)

        self.logger.log("quota_set", {
            "event_number": self.event_number,
            "principal_id": principal_id,
            "resource": resource,
            "amount": amount,
        })

    def get_quota(self, principal_id: str, resource: str) -> float:
        """Get quota limit for a principal's resource.

        Delegates to ResourceManager (Plan #95).

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Quota limit, or 0.0 if not set
        """
        return self.resource_manager.get_quota(principal_id, resource)

    def consume_quota(self, principal_id: str, resource: str, amount: float) -> bool:
        """Record resource usage against quota.

        Delegates to ResourceManager.allocate() (Plan #95).

        Args:
            principal_id: The principal consuming resources
            resource: Resource name
            amount: Amount consumed (must be >= 0)

        Returns:
            True if consumption recorded successfully, False if would exceed quota
        """
        if amount < 0:
            raise ValueError(f"Consumption amount must be >= 0, got {amount}")

        # Ensure principal exists in ResourceManager
        if not self.resource_manager.principal_exists(principal_id):
            self.resource_manager.create_principal(principal_id)

        # ResourceManager.allocate() checks balance + amount vs quota
        return self.resource_manager.allocate(principal_id, resource, amount)

    def get_quota_usage(self, principal_id: str, resource: str) -> float:
        """Get current usage of a resource for a principal.

        Delegates to ResourceManager.get_balance() (Plan #95).
        In ResourceManager, quota usage is tracked via balances for allocatable resources.

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Current usage, or 0.0 if none recorded
        """
        return self.resource_manager.get_balance(principal_id, resource)

    def get_available_capacity(self, principal_id: str, resource: str) -> float:
        """Get remaining capacity (quota - usage) for a resource.

        Delegates to ResourceManager.get_available_quota() (Plan #95).

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Remaining capacity, or 0.0 if no quota set
        """
        return self.resource_manager.get_available_quota(principal_id, resource)

    # -------------------------------------------------------------------------
    # Library Installation (Plan #29)
    # -------------------------------------------------------------------------

    def record_library_install(
        self, principal_id: str, library_name: str, version: str | None = None
    ) -> None:
        """Record that a library was installed for an agent.

        This tracks installed libraries per-agent for observability and
        potential future enforcement (e.g., preventing duplicate installs).

        Args:
            principal_id: The agent who installed the library
            library_name: Package name
            version: Optional version constraint
        """
        if principal_id not in self._installed_libraries:
            self._installed_libraries[principal_id] = []
        self._installed_libraries[principal_id].append((library_name, version))

        # Log the installation event
        self.logger.log(
            "library_installed",
            {
                "principal_id": principal_id,
                "library": library_name,
                "version": version,
            },
        )

    def get_installed_libraries(self, principal_id: str) -> list[tuple[str, str | None]]:
        """Get list of libraries installed by an agent.

        Args:
            principal_id: The agent to query

        Returns:
            List of (library_name, version) tuples
        """
        return self._installed_libraries.get(principal_id, [])
