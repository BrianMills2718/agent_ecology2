"""World kernel - the core simulation loop"""

from __future__ import annotations

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
    InvokeArtifactIntent, DeleteArtifactIntent
)
# NOTE: TransferIntent removed - all transfers via genesis_ledger.transfer()
from .genesis import (
    create_genesis_artifacts, GenesisArtifact, GenesisRightsRegistry,
    GenesisMint, GenesisDebtContract, RightsConfig, SubmissionInfo
)
from .executor import get_executor
from .errors import ErrorCode, ErrorCategory
from .rate_tracker import RateTracker
from .invocation_registry import InvocationRegistry, InvocationRecord
from .id_registry import IDRegistry

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
        "method_not_found": "Method '{method}' not found on {artifact_id}. Available: {methods}. See handbook_genesis for method details.",
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


class WorldConfig(TypedDict):
    """World configuration section."""
    max_ticks: int


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
    compute_quota: int
    disk_quota: int
    disk_used: int
    disk_available: int


class MintSubmissionStatus(TypedDict, total=False):
    """Status of a mint submission."""
    status: str
    submitter: str
    score: int | None


class KernelMintSubmission(TypedDict):
    """A mint submission stored in kernel state (Plan #44)."""
    submission_id: str
    principal_id: str
    artifact_id: str
    bid: int
    tick_submitted: int


class KernelMintResult(TypedDict, total=False):
    """Result of a mint auction resolution (Plan #44)."""
    winner_id: str | None
    artifact_id: str | None
    winning_bid: int
    price_paid: int  # Second-price auction
    score: int | None
    scrip_minted: int
    ubi_distributed: dict[str, int]
    error: str | None
    tick_resolved: int


class StateSummary(TypedDict):
    """World state summary."""
    tick: int
    balances: dict[str, BalanceInfo]
    artifacts: list[dict[str, Any]]
    quotas: dict[str, QuotaInfo]
    mint_submissions: dict[str, MintSubmissionStatus]
    recent_events: list[dict[str, Any]]


class World:
    """The world kernel - manages state, executes actions, logs everything"""

    config: ConfigDict
    tick: int
    max_ticks: int
    costs: CostsConfig
    rights_config: RightsConfig
    ledger: Ledger
    artifacts: ArtifactStore
    logger: EventLogger
    genesis_artifacts: dict[str, GenesisArtifact]
    rights_registry: GenesisRightsRegistry | None
    principal_ids: list[str]
    # Rate limiting mode: when True, resources use rolling windows (RateTracker)
    # instead of tick-based reset
    use_rate_tracker: bool
    # Autonomous loop support
    use_autonomous_loops: bool
    rate_tracker: RateTracker | None
    loop_manager: "AgentLoopManager | None"
    # Invocation tracking for observability (Gap #27)
    invocation_registry: InvocationRegistry
    # Kernel mint state (Plan #44) - minting is kernel physics, not genesis privilege
    _mint_submissions: dict[str, KernelMintSubmission]
    _mint_held_bids: dict[str, int]  # principal_id -> escrowed bid amount
    _mint_history: list[KernelMintResult]
    # Quota state - kernel-level storage (Plan #42)
    # Maps principal_id -> resource -> quota limit
    _quota_limits: dict[str, dict[str, float]]
    # Maps principal_id -> resource -> current usage
    _quota_usage: dict[str, dict[str, float]]
    # Installed libraries per agent (Plan #29)
    # Maps principal_id -> list of (library_name, version)
    _installed_libraries: dict[str, list[tuple[str, str | None]]]
    # Global ID registry for collision prevention (Plan #7)
    id_registry: IDRegistry

    def __init__(self, config: ConfigDict, run_id: str | None = None) -> None:
        self.config = config
        self.tick = 0
        self.max_ticks = config["world"]["max_ticks"]
        self.costs = config["costs"]

        # Compute per-agent quotas from resource totals
        num_agents = len(config.get("principals", []))
        empty_quotas: PerAgentQuota = {"compute_quota": 0, "disk_quota": 0, "llm_budget_quota": 0.0}
        quotas: PerAgentQuota = compute_per_agent_quota(num_agents) if num_agents > 0 else empty_quotas

        # Rights configuration (Layer 2: Means of Production)
        # See docs/RESOURCE_MODEL.md for design rationale
        # Values come from config via compute_per_agent_quota()
        # Use new generic format with default_quotas dict
        if "rights" in config and "default_quotas" in config["rights"]:
            self.rights_config = config["rights"]
        else:
            # Build generic quotas from legacy format or computed values
            self.rights_config = {
                "default_quotas": {
                    "compute": float(quotas.get("compute_quota", config_get("resources.flow.compute.per_tick") or 50)),
                    "disk": float(quotas.get("disk_quota", config_get("resources.stock.disk.total") or 10000))
                }
            }

        # Check if rate limiting (rolling windows) is enabled
        # When enabled, resources use RateTracker instead of tick-based reset
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

        # Kernel quota state (Plan #42)
        # Must be initialized BEFORE genesis artifacts since rights_registry delegates here
        self._quota_limits = {}
        self._quota_usage = {}
        # Installed libraries per agent (Plan #29)
        self._installed_libraries = {}

        # Genesis artifacts (system-owned proxies)
        self.genesis_artifacts = create_genesis_artifacts(
            ledger=self.ledger,
            mint_callback=self._mint_scrip,
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
                owner_id="system",
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
            # Flow will be set when first tick starts
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

        # Kernel mint state (Plan #44) - minting is kernel physics
        self._mint_submissions = {}
        self._mint_held_bids = {}
        self._mint_history = []
        # NOTE: _quota_limits and _quota_usage are initialized earlier (line ~222)
        # to ensure they exist before rights_registry.ensure_agent() is called


        # Log world init
        default_quotas = self.rights_config.get("default_quotas", {})
        self.logger.log("world_init", {
            "max_ticks": self.max_ticks,
            "rights": self.rights_config,
            "costs": self.costs,
            "principals": [
                {
                    "id": p["id"],
                    "starting_scrip": p.get("starting_scrip", p.get("starting_credits", default_starting_scrip)),
                    "compute_quota": int(default_quotas.get("compute", quotas.get("compute_quota", 50)))
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
            "actions": "handbook_actions",
            "genesis": "handbook_genesis",
            "resources": "handbook_resources",
            "trading": "handbook_trading",
            "mint": "handbook_mint",
            "coordination": "handbook_coordination",
        }

        for section_name, artifact_id in handbook_sections.items():
            section_path = handbook_dir / f"{section_name}.md"
            if section_path.exists():
                content = section_path.read_text()
                self.artifacts.write(
                    artifact_id=artifact_id,
                    type="documentation",
                    content=content,
                    owner_id="system",
                    executable=False,
                )

    def _mint_scrip(self, principal_id: str, amount: int) -> None:
        """Mint new scrip for a principal (used by genesis_mint).

        Scrip is the economic currency - minting adds purchasing power.
        """
        self.ledger.credit_scrip(principal_id, amount)
        self.logger.log("mint", {
            "tick": self.tick,
            "principal_id": principal_id,
            "amount": amount,
            "scrip_after": self.ledger.get_scrip(principal_id)
        })

    # --- Kernel Mint Primitives (Plan #44) ---

    def submit_for_mint(self, principal_id: str, artifact_id: str, bid: int) -> str:
        """Submit artifact for mint consideration. Returns submission_id.

        This is a kernel primitive - minting is physics, not genesis privilege.
        The actual auction resolution happens via resolve_mint_auction().

        Args:
            principal_id: Who is submitting
            artifact_id: Artifact to submit for minting
            bid: Amount of scrip to bid

        Returns:
            submission_id: Unique ID for this submission

        Raises:
            ValueError: If validation fails (insufficient scrip, not owner, etc.)
        """
        # Validate artifact exists and is owned by principal
        artifact = self.artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} not found")
        if artifact.owner_id != principal_id:
            raise ValueError(f"Principal {principal_id} is not owner of {artifact_id}")
        if not artifact.executable:
            raise ValueError(f"Artifact {artifact_id} is not executable")

        # Validate bid amount
        if bid <= 0:
            raise ValueError("Bid must be positive")

        # Check principal has sufficient scrip
        available_scrip = self.ledger.get_scrip(principal_id)
        if available_scrip < bid:
            raise ValueError(f"Insufficient scrip: have {available_scrip}, need {bid}")

        # Escrow the bid
        self.ledger.deduct_scrip(principal_id, bid)
        current_held = self._mint_held_bids.get(principal_id, 0)
        self._mint_held_bids[principal_id] = current_held + bid

        # Create submission
        submission_id = f"mint_sub_{uuid.uuid4().hex[:8]}"
        self._mint_submissions[submission_id] = {
            "submission_id": submission_id,
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "bid": bid,
            "tick_submitted": self.tick,
        }

        self.logger.log("mint_submission", {
            "tick": self.tick,
            "submission_id": submission_id,
            "principal_id": principal_id,
            "artifact_id": artifact_id,
            "bid": bid,
        })

        return submission_id

    def get_mint_submissions(self) -> list[KernelMintSubmission]:
        """Get all pending mint submissions.

        Returns:
            List of pending submissions (public data)
        """
        return list(self._mint_submissions.values())

    def get_mint_history(self, limit: int = 100) -> list[KernelMintResult]:
        """Get mint history (most recent first).

        Args:
            limit: Maximum number of results

        Returns:
            List of mint results, newest first
        """
        return list(reversed(self._mint_history[-limit:]))

    def cancel_mint_submission(self, principal_id: str, submission_id: str) -> bool:
        """Cancel a mint submission and refund the bid.

        Args:
            principal_id: Who is cancelling (must own the submission)
            submission_id: Which submission to cancel

        Returns:
            True if cancelled, False if not allowed
        """
        if submission_id not in self._mint_submissions:
            return False

        submission = self._mint_submissions[submission_id]

        # Can only cancel your own submission
        if submission["principal_id"] != principal_id:
            return False

        # Refund the bid
        bid_amount = submission["bid"]
        self.ledger.credit_scrip(principal_id, bid_amount)

        # Update held bids
        current_held = self._mint_held_bids.get(principal_id, 0)
        self._mint_held_bids[principal_id] = max(0, current_held - bid_amount)

        # Remove submission
        del self._mint_submissions[submission_id]

        self.logger.log("mint_cancellation", {
            "tick": self.tick,
            "submission_id": submission_id,
            "principal_id": principal_id,
            "refunded": bid_amount,
        })

        return True

    def resolve_mint_auction(self, _mock_score: int | None = None) -> KernelMintResult:
        """Resolve the current mint auction.

        Called by tick advancement or manually for testing.
        Picks winner (highest bid), runs second-price auction,
        scores artifact, mints scrip, distributes UBI.

        Args:
            _mock_score: For testing - use this score instead of LLM scoring

        Returns:
            KernelMintResult with auction outcome
        """
        if not self._mint_submissions:
            result: KernelMintResult = {
                "winner_id": None,
                "artifact_id": None,
                "winning_bid": 0,
                "price_paid": 0,
                "score": None,
                "scrip_minted": 0,
                "ubi_distributed": {},
                "error": "No submissions",
                "tick_resolved": self.tick,
            }
            self._mint_history.append(result)
            return result

        # Sort by bid amount (descending)
        submissions = list(self._mint_submissions.values())
        sorted_subs = sorted(submissions, key=lambda s: s["bid"], reverse=True)

        winner = sorted_subs[0]
        winner_id = winner["principal_id"]
        artifact_id = winner["artifact_id"]
        winning_bid = winner["bid"]

        # Second-price: pay the second-highest bid (or minimum if only one)
        minimum_bid = 1  # Could come from config
        if len(sorted_subs) > 1:
            price_paid = sorted_subs[1]["bid"]
        else:
            price_paid = minimum_bid

        # Refund losing bidders
        for sub in sorted_subs[1:]:
            self.ledger.credit_scrip(sub["principal_id"], sub["bid"])

        # Winner pays second price (refund difference)
        refund_to_winner = winning_bid - price_paid
        if refund_to_winner > 0:
            self.ledger.credit_scrip(winner_id, refund_to_winner)

        # Clear held bids
        self._mint_held_bids.clear()

        # Distribute UBI from price paid
        ubi_distribution = self.ledger.distribute_ubi(price_paid, exclude=winner_id)

        # Score the artifact
        score: int | None = None
        scrip_minted = 0
        error: str | None = None

        if _mock_score is not None:
            # Testing mode - use provided score
            score = _mock_score
            mint_ratio = 10  # Default, could come from config
            scrip_minted = score // mint_ratio
            if scrip_minted > 0:
                self._mint_scrip(winner_id, scrip_minted)
        else:
            # Production mode - use LLM scorer
            artifact = self.artifacts.get(artifact_id)
            if artifact:
                try:
                    from .mint_scorer import get_scorer
                    scorer = get_scorer()
                    score_result = scorer.score_artifact(
                        artifact_id=artifact_id,
                        artifact_type=artifact.type,
                        content=artifact.content
                    )
                    if score_result["success"]:
                        score = score_result["score"]
                        mint_ratio = 10  # Could come from config
                        scrip_minted = score // mint_ratio
                        if scrip_minted > 0:
                            self._mint_scrip(winner_id, scrip_minted)
                    else:
                        error = score_result.get("error", "Scoring failed")
                except Exception as e:
                    error = f"Scoring error: {str(e)}"
            else:
                error = f"Artifact {artifact_id} not found"

        result = KernelMintResult(
            winner_id=winner_id,
            artifact_id=artifact_id,
            winning_bid=winning_bid,
            price_paid=price_paid,
            score=score,
            scrip_minted=scrip_minted,
            ubi_distributed=ubi_distribution,
            error=error,
            tick_resolved=self.tick,
        )
        self._mint_history.append(result)

        # Clear submissions for next auction
        self._mint_submissions.clear()

        self.logger.log("mint_auction_resolved", {
            "tick": self.tick,
            "winner_id": winner_id,
            "artifact_id": artifact_id,
            "winning_bid": winning_bid,
            "price_paid": price_paid,
            "score": score,
            "scrip_minted": scrip_minted,
            "error": error,
        })

        return result

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
                # Check read permission (policy)
                if not artifact.can_read(intent.principal_id):
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
                            self.ledger.credit_scrip(artifact.owner_id, read_price)
                        result = ActionResult(
                            success=True,
                            message=f"Read artifact {intent.artifact_id}" + (f" (paid {read_price} scrip to {artifact.owner_id})" if read_price > 0 else ""),
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
                result = ActionResult(
                    success=False,
                    message=f"Artifact {intent.artifact_id} not found",
                    error_code=ErrorCode.NOT_FOUND.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=False,
                    error_details={"artifact_id": intent.artifact_id},
                )

        elif isinstance(intent, WriteArtifactIntent):
            result = self._execute_write(intent)

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
        self.logger.log("action", {
            "tick": self.tick,
            "intent": intent.to_dict(),
            "result": result.to_dict(),
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

        # Check write permission for existing artifacts (policy-based)
        existing = self.artifacts.get(intent.artifact_id)
        if existing and not existing.can_write(intent.principal_id):
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

        # Write the artifact
        write_result: WriteResult = self.artifacts.write_artifact(
            artifact_id=intent.artifact_id,
            artifact_type=intent.artifact_type,
            content=intent.content,
            owner_id=intent.principal_id,
            executable=intent.executable,
            price=intent.price,
            code=intent.code,
            policy=intent.policy,
        )

        # Track resource consumption (disk bytes written)
        resources_consumed: dict[str, float] = {}
        if net_new_bytes > 0:
            resources_consumed["disk_bytes"] = float(net_new_bytes)

        return ActionResult(
            success=write_result["success"],
            message=write_result["message"],
            data=write_result["data"],
            resources_consumed=resources_consumed if resources_consumed else None,
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
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "not_executable",
                    f"Artifact {artifact_id} is not executable"
                )
                return ActionResult(
                    success=False,
                    message=f"Artifact {artifact_id} is not executable",
                    error_code=ErrorCode.INVALID_TYPE.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"artifact_id": artifact_id, "executable": False},
                )

            # Check invoke permission (policy-based)
            if not artifact.can_invoke(intent.principal_id):
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "permission_denied",
                    "Access denied"
                )
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_invoke", artifact_id=artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )

            # Plan #15: Genesis method dispatch (if genesis_methods is set)
            if artifact.genesis_methods is not None:
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

                # Genesis method costs are COMPUTE (physical resource, not scrip)
                if method.cost > 0 and not self.ledger.can_spend_compute(intent.principal_id, method.cost):
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "insufficient_compute",
                        f"Cannot afford method cost: {method.cost}"
                    )
                    return ActionResult(
                        success=False,
                        message=f"Cannot afford method cost: {method.cost} compute (have {self.ledger.get_compute(intent.principal_id)})",
                        error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                        error_category=ErrorCategory.RESOURCE.value,
                        retriable=True,
                        error_details={"required": method.cost, "available": self.ledger.get_compute(intent.principal_id)},
                    )

                # Deduct compute cost FIRST (always paid, even on failure)
                resources_consumed: dict[str, float] = {}
                if method.cost > 0:
                    self.ledger.spend_compute(intent.principal_id, method.cost)
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
                        return ActionResult(
                            success=True,
                            message=f"Invoked {artifact_id}.{method_name}",
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

            # Regular artifact code execution path
            # Price (SCRIP) - economic payment to owner
            price = artifact.price
            owner_id = artifact.owner_id

            # Caller pays for physical resources
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
                        # This tracks usage over time; agent blocked when window limit exceeded
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
                if price > 0 and owner_id != intent.principal_id:
                    self.ledger.deduct_scrip(intent.principal_id, price)
                    self.ledger.credit_scrip(owner_id, price)

                self._log_invoke_success(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, type(exec_result.get("result")).__name__
                )
                return ActionResult(
                    success=True,
                    message=f"Invoked {artifact_id}" + (f" (paid {price} scrip to {owner_id})" if price > 0 else ""),
                    data={
                        "result": exec_result.get("result"),
                        "price_paid": price,
                        "owner": owner_id
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
                    retriable = True  # Timeout might not happen on retry
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

        # Artifact not found
        duration_ms = (time.perf_counter() - start_time) * 1000
        self._log_invoke_failure(
            intent.principal_id, artifact_id, method_name,
            duration_ms, "not_found",
            f"Artifact {artifact_id} not found"
        )
        return ActionResult(
            success=False,
            message=f"Artifact {artifact_id} not found",
            error_code=ErrorCode.NOT_FOUND.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=False,
            error_details={"artifact_id": artifact_id},
        )

    def _execute_delete(self, intent: DeleteArtifactIntent) -> ActionResult:
        """Execute a delete_artifact action (Plan #57).

        Soft deletes an artifact, freeing disk quota for the owner.
        Only the artifact owner can delete. Genesis artifacts cannot be deleted.
        """
        result = self.delete_artifact(intent.artifact_id, intent.principal_id)
        
        if result.get("success"):
            # Calculate freed disk space
            artifact = self.artifacts.get(intent.artifact_id)
            freed_bytes = 0
            if artifact:
                freed_bytes = len(artifact.content.encode("utf-8")) + len(artifact.code.encode("utf-8"))
            
            return ActionResult(
                success=True,
                message=f"Deleted artifact {intent.artifact_id}",
                data={"artifact_id": intent.artifact_id, "freed_bytes": freed_bytes},
            )
        else:
            return ActionResult(
                success=False,
                message=result.get("error", "Delete failed"),
                error_code=ErrorCode.NOT_AUTHORIZED.value if "owner" in result.get("error", "") else ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.PERMISSION.value if "owner" in result.get("error", "") else ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
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
            "tick": self.tick,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "result_type": result_type,
        })
        self.invocation_registry.record_invocation(InvocationRecord(
            tick=self.tick,
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
            "tick": self.tick,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "error_type": error_type,
            "error_message": error_message,
        })
        self.invocation_registry.record_invocation(InvocationRecord(
            tick=self.tick,
            invoker_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
        ))

    def advance_tick(self) -> bool:
        """
        Advance to the next tick. Optionally renews FLOW RESOURCES for all principals.
        Returns False if max_ticks reached.

        Resource reset behavior depends on use_rate_tracker:
        - When use_rate_tracker=False (legacy): FLOW RESOURCES reset each tick based on quotas.
        - When use_rate_tracker=True: Resources flow continuously via RateTracker, NO tick-based reset.

        SCRIP (economic currency) is NEVER reset - it persists and accumulates.

        See docs/RESOURCE_MODEL.md for design rationale.
        """
        if self.tick >= self.max_ticks:
            return False

        self.tick += 1

        # Update tick in debt contract if present
        debt_contract = self.genesis_artifacts.get("genesis_debt_contract")
        if isinstance(debt_contract, GenesisDebtContract):
            debt_contract.set_tick(self.tick)

        # Only reset FLOW RESOURCES when NOT using rate tracker (legacy tick-based mode)
        # When rate limiting is enabled, resources flow continuously via RateTracker
        if not self.use_rate_tracker:
            # Reset FLOW RESOURCES for all principals (use it or lose it)
            # Only flow resources reset - scrip is persistent economic currency
            for pid in self.principal_ids:
                if self.rights_registry:
                    # Use generic quota API - get all quotas for this principal
                    all_quotas = self.rights_registry.get_all_quotas(pid)
                    # Reset flow resources to their quotas
                    # For now, only "compute" is a flow resource (resets each tick)
                    # Stock resources like "disk" don't reset
                    if "compute" in all_quotas:
                        self.ledger.set_resource(pid, "llm_tokens", all_quotas["compute"])
                else:
                    # Fallback to config
                    config_compute: int | None = config_get("resources.flow.compute.per_tick")
                    default_quotas = self.rights_config.get("default_quotas", {})
                    default_compute = default_quotas.get("compute", config_compute or 50)
                    self.ledger.set_resource(pid, "llm_tokens", float(default_compute))

        self.logger.log("tick", {
            "tick": self.tick,
            "compute": self.ledger.get_all_compute(),  # Backward compat log format
            "scrip": self.ledger.get_all_scrip(),
            "artifact_count": self.artifacts.count(),
            "rate_tracker_mode": self.use_rate_tracker,
        })

        return True

    def get_state_summary(self) -> StateSummary:
        """Get a summary of current world state"""
        # Combine regular artifacts with genesis artifacts
        all_artifacts: list[dict[str, Any]] = self.artifacts.list_all()
        for genesis in self.genesis_artifacts.values():
            # Cast to dict[str, Any] since GenesisArtifactDict is a TypedDict
            genesis_dict = dict(genesis.to_dict())
            all_artifacts.append(genesis_dict)

        # Get quota info for all agents
        quotas: dict[str, QuotaInfo] = {}
        if self.rights_registry:
            for pid in self.principal_ids:
                quotas[pid] = {
                    "compute_quota": self.rights_registry.get_compute_quota(pid),
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

        return {
            "tick": self.tick,
            "balances": self.ledger.get_all_balances(),
            "artifacts": all_artifacts,
            "quotas": quotas,
            "mint_submissions": mint_status,
            "recent_events": self.get_recent_events(10)
        }

    def get_recent_events(self, n: int = 20) -> list[dict[str, Any]]:
        """Get recent events from the log"""
        return self.logger.read_recent(n)

    # -------------------------------------------------------------------------
    # Convenience methods for artifact operations (Plan #18)
    # -------------------------------------------------------------------------

    def delete_artifact(self, artifact_id: str, requester_id: str) -> dict[str, Any]:
        """Delete an artifact (soft delete with tombstone).

        Only the artifact owner can delete. Genesis artifacts cannot be deleted.

        Args:
            artifact_id: ID of artifact to delete
            requester_id: ID of principal requesting deletion

        Returns:
            {"success": True} on success
            {"success": False, "error": "..."} on failure
        """
        from datetime import datetime

        # Check if genesis artifact
        if artifact_id.startswith("genesis_"):
            return {"success": False, "error": "Cannot delete genesis artifacts"}

        # Check if artifact exists
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Check if already deleted
        if artifact.deleted:
            return {"success": False, "error": f"Artifact {artifact_id} is already deleted"}

        # Check ownership
        if artifact.owner_id != requester_id:
            return {"success": False, "error": "Only owner can delete artifact"}

        # Soft delete - mark as tombstone
        artifact.deleted = True
        artifact.deleted_at = datetime.utcnow().isoformat()
        artifact.deleted_by = requester_id

        # Log the deletion
        self.logger.log("artifact_deleted", {
            "tick": self.tick,
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
                "owner_id": artifact.owner_id,
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

        Args:
            agent_id: ID of agent to check

        Returns:
            True if agent is frozen, False otherwise
        """
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
        last_action_tick: int | None = None,
    ) -> None:
        """Emit an AGENT_FROZEN event for vulture observability.

        Args:
            agent_id: ID of agent that froze
            reason: Why agent froze (compute_exhausted, rate_limited, etc.)
            last_action_tick: Tick of agent's last successful action
        """
        self.logger.log("agent_frozen", {
            "tick": self.tick,
            "agent_id": agent_id,
            "reason": reason,
            "scrip_balance": self.ledger.get_scrip(agent_id),
            "compute_remaining": self.ledger.get_resource(agent_id, "llm_tokens"),
            "owned_artifacts": self.artifacts.get_artifacts_by_owner(agent_id),
            "last_action_tick": last_action_tick or self.tick,
        })

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
            "tick": self.tick,
            "agent_id": agent_id,
            "unfrozen_by": unfrozen_by,
            "resources_transferred": resources_transferred or {},
        })

    # -------------------------------------------------------------------------
    # Kernel Quota Primitives (Plan #42)
    # -------------------------------------------------------------------------

    def set_quota(self, principal_id: str, resource: str, amount: float) -> None:
        """Set quota limit for a principal's resource.

        This is kernel state - quotas are physics, not genesis artifact state.

        Args:
            principal_id: The principal to set quota for
            resource: Resource name (e.g., "cpu_seconds_per_minute", "llm_tokens_per_minute")
            amount: Quota limit (must be >= 0)
        """
        if amount < 0:
            raise ValueError(f"Quota amount must be >= 0, got {amount}")

        if principal_id not in self._quota_limits:
            self._quota_limits[principal_id] = {}
        self._quota_limits[principal_id][resource] = amount

        self.logger.log("quota_set", {
            "tick": self.tick,
            "principal_id": principal_id,
            "resource": resource,
            "amount": amount,
        })

    def get_quota(self, principal_id: str, resource: str) -> float:
        """Get quota limit for a principal's resource.

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Quota limit, or 0.0 if not set
        """
        return self._quota_limits.get(principal_id, {}).get(resource, 0.0)

    def consume_quota(self, principal_id: str, resource: str, amount: float) -> bool:
        """Record resource usage against quota.

        Args:
            principal_id: The principal consuming resources
            resource: Resource name
            amount: Amount consumed (must be >= 0)

        Returns:
            True if consumption recorded successfully, False if would exceed quota
        """
        if amount < 0:
            raise ValueError(f"Consumption amount must be >= 0, got {amount}")

        quota = self.get_quota(principal_id, resource)
        current_usage = self._quota_usage.get(principal_id, {}).get(resource, 0.0)

        # Check if this would exceed quota
        if current_usage + amount > quota:
            return False

        # Record usage
        if principal_id not in self._quota_usage:
            self._quota_usage[principal_id] = {}
        self._quota_usage[principal_id][resource] = current_usage + amount

        return True

    def get_quota_usage(self, principal_id: str, resource: str) -> float:
        """Get current usage of a resource for a principal.

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Current usage, or 0.0 if none recorded
        """
        return self._quota_usage.get(principal_id, {}).get(resource, 0.0)

    def get_available_capacity(self, principal_id: str, resource: str) -> float:
        """Get remaining capacity (quota - usage) for a resource.

        Args:
            principal_id: The principal to query
            resource: Resource name

        Returns:
            Remaining capacity, or 0.0 if no quota set
        """
        quota = self.get_quota(principal_id, resource)
        usage = self.get_quota_usage(principal_id, resource)
        return max(0.0, quota - usage)

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
