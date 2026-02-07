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
from pathlib import Path
from typing import Any, TypedDict, TYPE_CHECKING, cast

from .ledger import Ledger
from .artifacts import ArtifactStore, Artifact, WriteResult
from .logger import EventLogger
from .actions import (
    ActionIntent, ActionResult, InvokeArtifactIntent,
    ReadArtifactIntent, WriteArtifactIntent,
)
from .kernel_queries import KernelQueryHandler
# Plan #254: Genesis removed - transfer/mint are now kernel actions
from .executor import get_executor
from .action_executor import ActionExecutor
from .rate_tracker import RateTracker
from .invocation_registry import InvocationRegistry
from .id_registry import IDRegistry
from .resource_manager import ResourceManager, ResourceType
from .resource_metrics import ResourceMetricsProvider
from .mint_auction import MintAuction, KernelMintSubmission, KernelMintResult
from .mint_tasks import MintTaskManager  # Plan #269
from .triggers import TriggerRegistry
from .delegation import DelegationManager

from ..config import get as config_get, PerAgentQuota
from ..genesis import load_genesis

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
        "method_not_found": "Method '{method}' not found on {artifact_id}. Available: {methods}. TIP: Call invoke_artifact('{artifact_id}', 'describe', []) to see method details before invoking.",
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) edit_artifact to set owner to escrow, 2) deposit.",
    }

    # Get from config (or use default)
    template: str = config_get(f"agent.errors.{error_type}") or defaults.get(error_type, f"Error: {error_type}")

    # Fill in placeholders
    try:
        return template.format(**kwargs)
    except KeyError:
        # Missing placeholder - return template as-is
        return template


class CostsConfig(TypedDict, total=False):
    """Costs configuration (token costs only)."""
    per_1k_input_tokens: int
    per_1k_output_tokens: int



# Note: ConfigDict is an alias for dict[str, Any] because the actual config
# contains many more keys than a narrow TypedDict can express (resources,
# artifacts, genesis, external_capabilities, etc.). Using a narrow TypedDict
# would require constant updating as config keys are added.
ConfigDict = dict[str, Any]


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


class StateSummary(TypedDict, total=False):
    """World state summary."""
    event_number: int
    balances: dict[str, Any]  # Uses ledger.BalanceInfo structure
    artifacts: list[dict[str, Any]]
    quotas: dict[str, QuotaInfo]
    mint_submissions: dict[str, MintSubmissionStatus]
    recent_events: list[dict[str, Any]]
    resource_metrics: dict[str, dict[str, Any]]  # Plan #93: Agent resource visibility
    time_context: dict[str, Any]  # Plan #157: Simulation time awareness


class World:
    """The world kernel - manages state, executes actions, logs everything"""

    config: ConfigDict
    event_number: int  # Monotonic counter for event ordering in logs
    costs: CostsConfig
    ledger: Ledger
    artifacts: ArtifactStore
    logger: EventLogger
    # Plan #254: genesis_artifacts removed - use kernel actions instead
    # principal_ids is a derived property (Plan #231)
    # Autonomous loop support
    rate_tracker: RateTracker
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
    # Charge delegation management (Plan #236)
    delegation_manager: DelegationManager

    def __init__(self, config: ConfigDict, run_id: str | None = None) -> None:
        self.config = config
        self.event_number = 0  # Monotonic counter for event ordering in logs
        self.costs = config["costs"]

        # Compute per-agent quotas from resource totals (Plan #282)
        # Read from passed config dict, NOT global config (for test isolation)
        # Precision note (Plan #84): Quotas are typically whole numbers (compute units,
        # disk bytes) or simple decimals (llm_budget dollars). No Decimal arithmetic
        # needed here - precision issues only arise from repeated add/subtract operations,
        # which happen in ledger.py (where Decimal helpers are used).
        num_agents = len(config.get("principals", []))
        resources_config = config.get("resources", {})
        stock_config = resources_config.get("stock", {})
        llm_budget_config = stock_config.get("llm_budget", {})
        disk_config = stock_config.get("disk", {})

        # Get totals from config, default to 0 if not configured
        llm_budget_total = float(llm_budget_config.get("total", 0.0))
        disk_total = int(disk_config.get("total", 0))

        quotas: PerAgentQuota = {
            "llm_tokens_quota": 0,  # Derived from rate_limiting, not stock
            "disk_quota": disk_total // num_agents if num_agents > 0 else 0,
            "llm_budget_quota": llm_budget_total / num_agents if num_agents > 0 else 0.0,
        }

        # Plan #254: Rights configuration removed - ResourceManager handles quotas

        # Global ID registry for collision prevention (Plan #7)
        self.id_registry = IDRegistry()

        # Core state - create ledger with rate_limiting config and ID registry
        self.ledger = Ledger.from_config(config, [], self.id_registry)

        # Plan #182: Get indexed metadata fields from artifacts config
        artifacts_config = config.get("artifacts", {})
        indexed_metadata_fields = artifacts_config.get("indexed_metadata_fields", [])
        self.artifacts = ArtifactStore(
            id_registry=self.id_registry,
            indexed_metadata_fields=indexed_metadata_fields,
        )

        # Event trigger system (Plan #180)
        # TriggerRegistry watches for trigger artifacts and queues invocations on matching events
        self.trigger_registry = TriggerRegistry(self.artifacts)

        # Per-run logging if logs_dir and run_id provided, else legacy mode
        logs_dir = config.get("logging", {}).get("logs_dir")
        if logs_dir and run_id:
            self.logger = EventLogger(logs_dir=logs_dir, run_id=run_id)
        else:
            self.logger = EventLogger(output_file=config["logging"]["output_file"])

        # TD-011: Wire event logger to ledger for scrip mutation logging
        self.ledger.set_logger(self.logger)

        # Unified resource manager (Plan #95)
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
        self._installed_libraries: dict[str, list[dict[str, Any]]] = {}

        # External capabilities manager (Plan #300)
        # Manages access to external APIs that require human approval
        from .capabilities import CapabilityManager
        external_caps_config = config.get("external_capabilities", {})
        self.capability_manager = CapabilityManager(self, external_caps_config)

        # Initialize MintAuction (extracted from World - TD-001)
        # TD-012: Read auction params from config instead of hardcoding
        mint_config = config.get("genesis", {}).get("mint", {})
        auction_config = mint_config.get("auction", {})
        self.mint_auction = MintAuction(
            ledger=self.ledger,
            artifacts=self.artifacts,
            logger=self.logger,
            get_event_number=lambda: self.event_number,
            first_auction_delay_seconds=auction_config.get("first_auction_delay_seconds", 30.0),
            bidding_window_seconds=auction_config.get("bidding_window_seconds", 60.0),
            period_seconds=auction_config.get("period_seconds", 120.0),
            mint_ratio=mint_config.get("mint_ratio", 10),
        )

        # Initialize MintTaskManager (Plan #269)
        self.mint_task_manager: MintTaskManager | None = None
        if config_get("mint_tasks.enabled", False):
            from .executor import get_executor
            self.mint_task_manager = MintTaskManager(
                ledger=self.ledger,
                artifacts=self.artifacts,
                executor=get_executor(),
                logger=self.logger,
            )
            # Seed tasks from config
            seed_tasks = config_get("mint_tasks.seed_tasks", [])
            if seed_tasks:
                self.mint_task_manager.seed_from_config(seed_tasks)

        # Plan #298: Load genesis artifacts from config/genesis/
        # This replaces embedded bootstrap methods with config-driven loading.
        # Order: kernel/ (mint_agent, llm_gateway), artifacts/ (handbook), agents/ (alpha_prime)
        load_genesis(self, config=config)

        # Initialize principals from config (Plan #231: principal_ids is now a derived property)
        default_starting_scrip: int = config_get("scrip.starting_amount") or 100

        # Per-agent LLM budget (Plan #12, Plan #282)
        # Use computed quota from resources.stock.llm_budget.total / num_agents
        # Per-principal override via "llm_budget" field still supported
        default_llm_budget: float = float(quotas.get("llm_budget_quota", 0.0))

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
            # Plan #231: ResourceManager entry for init-time principals
            self.resource_manager.create_principal(p["id"])
            # Plan #254: Set disk quota (previously done by rights_registry.ensure_agent)
            disk_quota = float(quotas.get("disk_quota", 10000))
            self.resource_manager.set_quota(p["id"], "disk", disk_quota)

        # Plan #247: RateTracker is always active. Use the one from Ledger.
        self.rate_tracker = self.ledger.rate_tracker

        # AgentLoopManager will be created by SimulationRunner when autonomous mode is enabled
        self.loop_manager = None

        # Invocation registry for observability (Gap #27)
        self.invocation_registry = InvocationRegistry()

        # Charge delegation management (Plan #236)
        self.delegation_manager = DelegationManager(self.artifacts, self.ledger)
        # TD-011: Wire event logger to delegation manager
        self.delegation_manager.set_logger(self.logger)
        # Kernel query handler (Plan #184)
        # Provides read-only access to kernel state via query_kernel action
        self.kernel_query_handler = KernelQueryHandler(self)

        # Action executor (Plan #181: Split large files)
        # Handles all action intent processing
        self._action_executor = ActionExecutor(self)

        self.logger.log("world_init", {
            "costs": self.costs,
            "principals": [
                {
                    "id": p["id"],
                    "starting_scrip": p.get("starting_scrip", p.get("starting_credits", default_starting_scrip)),
                    "llm_tokens_quota": int(quotas.get("llm_tokens_quota", 50))
                }
                for p in config["principals"]
            ]
        })

    @property
    def principal_ids(self) -> list[str]:
        """Derived from ledger state (Plan #231). Excludes system principals."""
        return self.ledger.get_agent_principal_ids()

    def validate_principal_invariant(self) -> list[str]:
        """Check that has_standing <-> ledger entry invariant holds (Plan #231).

        Returns list of violation descriptions (empty = valid).
        """
        violations: list[str] = []
        agent_pids = self.ledger.get_agent_principal_ids()

        for pid in agent_pids:
            artifact = self.artifacts.artifacts.get(pid)
            if artifact and not artifact.has_standing:
                violations.append(f"{pid}: in ledger but has_standing=False")

        for aid, artifact in self.artifacts.artifacts.items():
            if artifact.has_standing and aid not in self.ledger.scrip:
                violations.append(f"{aid}: has_standing=True but not in ledger")

        return violations

    # Plan #298: Bootstrap methods moved to src/genesis/loader.py
    # See config/genesis/ for kernel, artifacts, and agents manifests

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

        Plan #181: Delegates to ActionExecutor for all action processing.

        Actions are free. Real costs come from:
        - LLM tokens (thinking) - costs from LLM budget
        - Disk quota (writing) - costs from disk allocation
        - Artifact prices (scrip paid to owner)
        """
        return self._action_executor.execute(intent)

    def increment_event_counter(self) -> int:
        """Increment the event counter and return the new value.

        The event counter serves two purposes:
        1. Event ordering in logs (observability)
        2. Scheduled trigger firing (Plan #185)

        Note: This is NOT the primary execution control. Agents run based on:
        - Time duration (seconds)
        - LLM budget (dollars)
        """
        self.event_number += 1

        # Plan #185: Check for scheduled triggers at this event
        self.check_scheduled_triggers()

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
        all_artifacts: list[dict[str, Any]] = self.artifacts.list_all()

        # Plan #254: Quota info now managed by ResourceManager
        # For now, return empty quotas - callers should use query_kernel("quotas") instead
        quotas: dict[str, QuotaInfo] = {}

        # Get mint submission status from mint_auction directly
        mint_status: dict[str, MintSubmissionStatus] = {}
        for submission in self.mint_auction.get_submissions():
            # Cast to dict[str, Any] since runtime data may have extra fields
            # beyond the KernelMintSubmission TypedDict (e.g. score, status, submitter)
            sub: dict[str, Any] = dict(submission)
            artifact_id = sub.get("artifact_id", "")
            if artifact_id:
                mint_status[artifact_id] = {
                    "status": str(sub.get("status", "unknown")),
                    "submitter": str(sub.get("submitter", "unknown")),
                    "score": int(sub["score"]) if sub.get("status") == "scored" and sub.get("score") is not None else None
                }

        # Get resource metrics for all agents (Plan #93)
        resource_metrics: dict[str, dict[str, Any]] = {}
        for agent_id in self.principal_ids:
            if agent_id.startswith(("SYSTEM", "kernel_")):
                continue  # Skip system principals
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
        System artifacts (kernel_*, SYSTEM-owned) cannot be deleted.

        Args:
            artifact_id: ID of artifact to delete
            requester_id: ID of principal requesting deletion

        Returns:
            {"success": True} on success
            {"success": False, "error": "..."} on failure
        """
        from datetime import datetime, timezone
        from src.world.executor import get_executor

        # Check if system artifact (kernel-level protection)
        if artifact_id.startswith(("kernel_", "handbook_")):
            return {"success": False, "error": "Cannot delete system artifacts"}

        # Check if artifact exists
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Check if already deleted
        if artifact.deleted:
            return {"success": False, "error": f"Artifact {artifact_id} is already deleted"}

        # Plan #140: Check delete permission via contract (not hardcoded created_by check)
        executor = get_executor()
        perm_result = executor._check_permission(requester_id, "delete", artifact)
        if not perm_result.allowed:
            return {"success": False, "error": f"Delete not permitted: {perm_result.reason}"}

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

        # LLM tokens (renewable via rate tracker)
        llm_tokens_used = self.ledger.get_resource(agent_id, "llm_tokens")
        resources["llm_tokens"] = {
            "used": float(llm_tokens_used),
        }

        # LLM budget (depletable)
        llm_budget = self.ledger.get_resource(agent_id, "llm_budget")
        resources["llm_budget"] = {
            "remaining": float(llm_budget),
        }

        # Disk usage tracked by artifact store
        disk_used = self.artifacts.get_owner_usage(agent_id)
        resources["disk"] = {
            "used": float(disk_used),
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

    # --- Trigger System (Plan #180) ---

    def _emit_event(self, event: dict[str, Any]) -> int:
        """Emit an event and queue any matching trigger invocations.

        This is called after state-changing operations to enable pub-sub patterns.
        Triggers are processed asynchronously (queued, not synchronous).

        Args:
            event: Event dictionary with type and data

        Returns:
            Number of trigger invocations queued
        """
        return self.trigger_registry.queue_matching_invocations(event)

    def refresh_triggers(self) -> None:
        """Refresh the trigger registry from current artifacts.

        Should be called when trigger artifacts are created/updated/deleted.
        Plan #185: Also updates current event number for scheduling.
        """
        self.trigger_registry.set_current_event_number(self.event_number)
        self.trigger_registry.refresh()

    def process_pending_triggers(self) -> list[ActionResult]:
        """Process all pending trigger invocations.

        Executes each pending trigger callback by invoking the callback artifact.
        Returns results of all invocations.

        Returns:
            List of ActionResult from trigger callbacks
        """
        results: list[ActionResult] = []
        pending = self.trigger_registry.get_pending_invocations()

        for invocation in pending:
            # Build invoke intent for the callback
            intent = InvokeArtifactIntent(
                principal_id=invocation["owner"],  # Trigger owner calls their callback
                artifact_id=invocation["callback_artifact"],
                method=invocation["callback_method"],
                args=[invocation["event"]],  # Pass event as first arg
            )

            # Execute the invoke (Plan #181: delegates to ActionExecutor)
            result = self.execute_action(intent)
            results.append(result)

        # Clear processed invocations
        self.trigger_registry.clear_pending_invocations()
        return results

    def get_pending_trigger_count(self) -> int:
        """Get number of pending trigger invocations.

        Returns:
            Number of invocations waiting to be processed
        """
        return len(self.trigger_registry.get_pending_invocations())

    # --- Scheduled Triggers (Plan #185) ---

    def check_scheduled_triggers(self) -> int:
        """Check and queue any triggers scheduled for the current event number.

        This should be called after incrementing the event counter to fire
        any triggers scheduled for this event.

        Returns:
            Number of scheduled triggers fired
        """
        self.trigger_registry.set_current_event_number(self.event_number)
        return self.trigger_registry.fire_scheduled_triggers(self.event_number)

    def get_scheduled_trigger_count(self) -> int:
        """Get number of triggers currently scheduled for future events.

        Returns:
            Number of scheduled triggers waiting to fire
        """
        return self.trigger_registry.get_scheduled_count()

    def cancel_scheduled_trigger(self, trigger_id: str) -> bool:
        """Cancel a scheduled trigger before it fires.

        Args:
            trigger_id: ID of the trigger artifact to cancel

        Returns:
            True if the trigger was found and cancelled
        """
        return self.trigger_registry.cancel_scheduled_trigger(trigger_id)
