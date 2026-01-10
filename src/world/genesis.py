"""Genesis Artifacts - System-owned proxy artifacts

Genesis artifacts are special artifacts that:
1. Are owned by "system" (cannot be modified by agents)
2. Act as proxies to kernel functions (ledger, oracle)
3. Have special cost rules (some functions are free)

These enable agents to interact with core infrastructure through
the same invoke_artifact mechanism they use for agent-created artifacts.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_genesis_config, get

from .ledger import Ledger
from .artifacts import ArtifactStore
from .logger import EventLogger


# System owner ID - cannot be modified by agents
SYSTEM_OWNER: str = "system"


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


class OracleStatusResult(TypedDict):
    """Result from oracle status query."""
    success: bool
    oracle: str
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


@dataclass
class GenesisMethod:
    """A method exposed by a genesis artifact"""
    name: str
    handler: Callable[[list[Any], str], dict[str, Any]]
    cost: int  # 0 = free (system-subsidized)
    description: str


class GenesisArtifact:
    """Base class for genesis artifacts (system proxies)"""

    id: str
    type: str
    owner_id: str
    description: str
    methods: dict[str, GenesisMethod]

    def __init__(self, artifact_id: str, description: str) -> None:
        self.id = artifact_id
        self.type = "genesis"
        self.owner_id = SYSTEM_OWNER
        self.description = description
        self.methods = {}

    def register_method(
        self,
        name: str,
        handler: Callable[[list[Any], str], dict[str, Any]],
        cost: int = 0,
        description: str = ""
    ) -> None:
        """Register a callable method on this genesis artifact"""
        self.methods[name] = GenesisMethod(
            name=name,
            handler=handler,
            cost=cost,
            description=description
        )

    def get_method(self, method_name: str) -> GenesisMethod | None:
        """Get a method by name"""
        return self.methods.get(method_name)

    def list_methods(self) -> list[MethodInfo]:
        """List available methods"""
        return [
            {"name": m.name, "cost": m.cost, "description": m.description}
            for m in self.methods.values()
        ]

    def to_dict(self) -> GenesisArtifactDict:
        """Convert to dict for artifact listing"""
        return {
            "id": self.id,
            "type": self.type,
            "owner_id": self.owner_id,
            "content": self.description,
            "methods": self.list_methods()
        }


class GenesisLedger(GenesisArtifact):
    """
    Genesis artifact that proxies to the world ledger.

    Two types of balances:
    - flow: Action budget (resets each tick) - real resource constraint
    - scrip: Economic currency (persistent) - medium of exchange

    Methods:
    - balance(agent_id) -> {flow, scrip}  [FREE]
    - all_balances() -> {agent_id: {flow, scrip}}  [FREE]
    - transfer(from_id, to_id, amount) -> bool  [1 scrip fee] - transfers SCRIP
    """

    ledger: Ledger

    def __init__(self, ledger: Ledger) -> None:
        super().__init__(
            artifact_id="genesis_ledger",
            description="System ledger - check balances (flow/scrip) and transfer scrip"
        )
        self.ledger = ledger

        # Register methods
        self.register_method(
            name="balance",
            handler=self._balance,
            cost=0,  # Free - reading your balance shouldn't cost
            description="Get flow and scrip balance for an agent. Args: [agent_id]"
        )

        self.register_method(
            name="all_balances",
            handler=self._all_balances,
            cost=0,  # Free - public information
            description="Get all agent balances (flow and scrip). Args: []"
        )

        self.register_method(
            name="transfer",
            handler=self._transfer,
            cost=get_genesis_config("ledger", "transfer_fee") or 1,
            description="Transfer SCRIP to another agent. Args: [from_id, to_id, amount]"
        )

    def _balance(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get balance for an agent (both flow and scrip)"""
        if not args or len(args) < 1:
            return {"success": False, "error": "balance requires [agent_id]"}
        agent_id: str = args[0]
        return {
            "success": True,
            "agent_id": agent_id,
            "flow": self.ledger.get_flow(agent_id),
            "scrip": self.ledger.get_scrip(agent_id)
        }

    def _all_balances(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all balances (flow and scrip for each agent)"""
        return {"success": True, "balances": self.ledger.get_all_balances()}

    def _transfer(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer SCRIP between agents (not flow - flow is non-transferable)"""
        if not args or len(args) < 3:
            return {"success": False, "error": "transfer requires [from_id, to_id, amount]"}

        from_id: str = args[0]
        to_id: str = args[1]
        amount: Any = args[2]

        # Security check: invoker can only transfer FROM themselves
        if from_id != invoker_id:
            return {"success": False, "error": f"Cannot transfer from {from_id} - you are {invoker_id}"}

        if not isinstance(amount, int) or amount <= 0:
            return {"success": False, "error": "Amount must be positive integer"}

        success = self.ledger.transfer_scrip(from_id, to_id, amount)
        if success:
            return {
                "success": True,
                "transferred": amount,
                "currency": "scrip",
                "from": from_id,
                "to": to_id,
                "from_scrip_after": self.ledger.get_scrip(from_id),
                "to_scrip_after": self.ledger.get_scrip(to_id)
            }
        else:
            return {"success": False, "error": "Transfer failed (insufficient scrip or invalid recipient)"}


class GenesisOracle(GenesisArtifact):
    """
    Genesis artifact for external minting.

    Uses LLM to evaluate submitted artifacts and estimate engagement score.
    Mints credits to submitters based on score.

    Methods:
    - status() -> dict  [FREE]
    - submit(artifact_id) -> receipt  [COSTS submission fee]
    - check(artifact_id) -> status  [FREE]
    - process() -> result  [FREE] - processes one pending submission
    """

    mint_callback: Callable[[str, int], None]
    artifact_store: ArtifactStore | None
    submissions: dict[str, SubmissionInfo]
    _scorer: Any  # OracleScorer, lazy-loaded

    def __init__(
        self,
        mint_callback: Callable[[str, int], None],
        artifact_store: ArtifactStore | None = None
    ) -> None:
        """
        Args:
            mint_callback: Function(agent_id, amount) to mint credits
            artifact_store: ArtifactStore to look up submitted artifacts
        """
        super().__init__(
            artifact_id="genesis_oracle",
            description="External feedback oracle - submit artifacts for LLM scoring"
        )
        self.mint_callback = mint_callback
        self.artifact_store = artifact_store
        self.submissions = {}  # artifact_id -> submission info
        self._scorer = None  # Lazy-loaded

        self.register_method(
            name="status",
            handler=self._status,
            cost=0,
            description="Check oracle status. Args: []"
        )

        self.register_method(
            name="submit",
            handler=self._submit,
            cost=get_genesis_config("oracle", "submit_fee") or 5,
            description="Submit artifact for scoring. Args: [artifact_id]"
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=0,
            description="Check submission status. Args: [artifact_id]"
        )

        self.register_method(
            name="process",
            handler=self._process,
            cost=0,  # Free - encourages processing
            description="Process one pending submission with LLM scoring. Args: []"
        )

    def _status(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Return oracle status"""
        pending = sum(1 for s in self.submissions.values() if s["status"] == "pending")
        scored = sum(1 for s in self.submissions.values() if s["status"] == "scored")
        return {
            "success": True,
            "oracle": "genesis_oracle",
            "type": "llm_mock",
            "pending_submissions": pending,
            "scored_submissions": scored,
            "total_submissions": len(self.submissions)
        }

    def _submit(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Submit an artifact for external scoring.

        IMPORTANT: Only executable (code) artifacts are accepted.
        Text-only submissions are rejected.
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "submit requires [artifact_id]"}

        artifact_id: str = args[0]

        # Check if artifact exists
        if self.artifact_store:
            artifact = self.artifact_store.get(artifact_id)
            if not artifact:
                return {"success": False, "error": f"Artifact {artifact_id} not found"}

            # CODE ONLY: Reject non-executable artifacts
            if not artifact.executable:
                return {
                    "success": False,
                    "error": f"Oracle only accepts executable (code) artifacts. '{artifact_id}' is not executable. Create an artifact with executable=true, price, and code fields."
                }

        # Check if already submitted
        if artifact_id in self.submissions:
            return {"success": False, "error": f"Artifact {artifact_id} already submitted"}

        # Record submission
        self.submissions[artifact_id] = {
            "submitter": invoker_id,
            "status": "pending",
            "score": None,
            "reason": None
        }

        return {
            "success": True,
            "message": f"Artifact {artifact_id} submitted for scoring",
            "receipt": artifact_id
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check status of a submission"""
        if not args or len(args) < 1:
            return {"success": False, "error": "check requires [artifact_id]"}

        artifact_id: str = args[0]
        submission = self.submissions.get(artifact_id)

        if not submission:
            return {"success": False, "error": f"No submission found for {artifact_id}"}

        return {"success": True, "submission": submission}

    def _process(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Process one pending submission using LLM scoring"""
        # Find a pending submission
        pending_id: str | None = None
        for artifact_id, submission in self.submissions.items():
            if submission["status"] == "pending":
                pending_id = artifact_id
                break

        if not pending_id:
            return {"success": True, "message": "No pending submissions to process"}

        # Get the artifact content
        if not self.artifact_store:
            return {"success": False, "error": "Oracle not configured with artifact store"}

        artifact = self.artifact_store.get(pending_id)
        if not artifact:
            # Artifact was deleted - mark as failed
            self.submissions[pending_id]["status"] = "failed"
            self.submissions[pending_id]["reason"] = "Artifact not found"
            return {"success": False, "error": f"Artifact {pending_id} not found"}

        # Lazy-load the scorer
        if self._scorer is None:
            from .oracle_scorer import get_scorer
            self._scorer = get_scorer()

        # Score the artifact
        result: dict[str, Any] = self._scorer.score_artifact(
            artifact_id=pending_id,
            artifact_type=artifact.type,
            content=artifact.content
        )

        submission = self.submissions[pending_id]

        if result["success"]:
            score: int = result["score"]
            reason: str = result["reason"]

            submission["status"] = "scored"
            submission["score"] = score
            submission["reason"] = reason

            # Mint credits based on score (score 0-100 -> credits)
            # Scale: score / mint_ratio (configurable)
            mint_ratio: int = get_genesis_config("oracle", "mint_ratio") or 10
            credits_to_mint = score // mint_ratio
            if credits_to_mint > 0:
                self.mint_callback(submission["submitter"], credits_to_mint)

            return {
                "success": True,
                "artifact_id": pending_id,
                "score": score,
                "reason": reason,
                "credits_minted": credits_to_mint,
                "submitter": submission["submitter"]
            }
        else:
            submission["status"] = "failed"
            submission["reason"] = result["error"]
            return {
                "success": False,
                "artifact_id": pending_id,
                "error": result["error"]
            }

    def mock_score(self, artifact_id: str, score: int) -> bool:
        """
        Mock scoring - for testing without LLM.
        Mints credits to the submitter based on score.
        """
        if artifact_id not in self.submissions:
            return False

        submission = self.submissions[artifact_id]
        submission["status"] = "scored"
        submission["score"] = score
        submission["reason"] = "Mock score for testing"

        # Mint credits based on score
        mint_ratio: int = get_genesis_config("oracle", "mint_ratio") or 10
        credits_to_mint = score // mint_ratio
        if credits_to_mint > 0:
            self.mint_callback(submission["submitter"], credits_to_mint)

        return True


class GenesisRightsRegistry(GenesisArtifact):
    """
    Genesis artifact for managing resource rights (means of production).

    Resource categories and actual resources:
    - compute: LLM tokens per tick (renews each tick)
    - disk: Bytes of storage (fixed pool)

    See docs/RESOURCE_MODEL.md for full design rationale.

    Methods:
    - check_quota(agent_id) -> dict  [FREE]
    - all_quotas() -> dict  [FREE]
    - transfer_quota(from, to, 'compute'|'disk', amount) -> bool  [1 scrip fee]
    """

    default_compute: int
    default_disk: int
    artifact_store: ArtifactStore | None
    quotas: dict[str, dict[str, int]]

    def __init__(
        self,
        default_compute: int,
        default_disk: int,
        artifact_store: ArtifactStore | None = None
    ) -> None:
        """
        Args:
            default_compute: Default compute quota per tick for new agents
            default_disk: Default disk quota (bytes) for new agents
            artifact_store: ArtifactStore to calculate actual disk usage
        """
        super().__init__(
            artifact_id="genesis_rights_registry",
            description="Rights registry - manage compute and disk quotas"
        )
        self.default_compute = default_compute
        self.default_disk = default_disk
        self.artifact_store = artifact_store

        # Track quotas per agent: {agent_id: {"compute": int, "disk": int}}
        self.quotas = {}

        self.register_method(
            name="check_quota",
            handler=self._check_quota,
            cost=0,
            description="Check quotas for an agent. Args: [agent_id]"
        )

        self.register_method(
            name="all_quotas",
            handler=self._all_quotas,
            cost=0,
            description="Get all agent quotas. Args: []"
        )

        self.register_method(
            name="transfer_quota",
            handler=self._transfer_quota,
            cost=get_genesis_config("rights_registry", "transfer_fee") or 1,
            description="Transfer quota to another agent. Args: [from_id, to_id, 'compute'|'disk', amount]"
        )

    def ensure_agent(self, agent_id: str) -> None:
        """Ensure an agent has quota entries (initialize with defaults)"""
        if agent_id not in self.quotas:
            self.quotas[agent_id] = {
                "compute": self.default_compute,
                "disk": self.default_disk
            }

    def get_compute_quota(self, agent_id: str) -> int:
        """Get compute quota (tokens/tick) for an agent"""
        self.ensure_agent(agent_id)
        return self.quotas[agent_id]["compute"]

    def get_disk_quota(self, agent_id: str) -> int:
        """Get disk quota (bytes) for an agent"""
        self.ensure_agent(agent_id)
        return self.quotas[agent_id]["disk"]

    def get_disk_used(self, agent_id: str) -> int:
        """Get actual disk space used by an agent"""
        if self.artifact_store:
            return self.artifact_store.get_owner_usage(agent_id)
        return 0

    def can_write(self, agent_id: str, additional_bytes: int) -> bool:
        """Check if agent can write additional_bytes without exceeding disk quota"""
        quota = self.get_disk_quota(agent_id)
        used = self.get_disk_used(agent_id)
        return (used + additional_bytes) <= quota

    # Backward compat aliases
    def get_flow_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_compute_quota()"""
        return self.get_compute_quota(agent_id)

    def get_stock_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_quota()"""
        return self.get_disk_quota(agent_id)

    def get_stock_used(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_used()"""
        return self.get_disk_used(agent_id)

    def _check_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check quotas for an agent"""
        if not args or len(args) < 1:
            return {"success": False, "error": "check_quota requires [agent_id]"}

        agent_id: str = args[0]
        self.ensure_agent(agent_id)

        quota = self.quotas[agent_id]
        disk_used = self.get_disk_used(agent_id)

        return {
            "success": True,
            "agent_id": agent_id,
            "compute_quota": quota["compute"],
            "disk_quota": quota["disk"],
            "disk_used": disk_used,
            "disk_available": quota["disk"] - disk_used
        }

    def _all_quotas(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all agent quotas"""
        result: dict[str, QuotaInfo] = {}
        for agent_id, quota in self.quotas.items():
            disk_used = self.get_disk_used(agent_id)
            result[agent_id] = {
                "compute_quota": quota["compute"],
                "disk_quota": quota["disk"],
                "disk_used": disk_used,
                "disk_available": quota["disk"] - disk_used
            }
        return {"success": True, "quotas": result}

    def _transfer_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer quota between agents"""
        if not args or len(args) < 4:
            return {"success": False, "error": "transfer_quota requires [from_id, to_id, 'compute'|'disk', amount]"}

        from_id: str = args[0]
        to_id: str = args[1]
        quota_type: str = args[2]
        amount: Any = args[3]

        # Security check: can only transfer FROM yourself
        if from_id != invoker_id:
            return {"success": False, "error": f"Cannot transfer from {from_id} - you are {invoker_id}"}

        if quota_type not in ["compute", "disk"]:
            return {"success": False, "error": "quota_type must be 'compute' or 'disk'"}

        if not isinstance(amount, int) or amount <= 0:
            return {"success": False, "error": "amount must be positive integer"}

        self.ensure_agent(from_id)
        self.ensure_agent(to_id)

        # Check if sender has enough quota
        if self.quotas[from_id][quota_type] < amount:
            return {
                "success": False,
                "error": f"Insufficient {quota_type} quota. Have {self.quotas[from_id][quota_type]}, need {amount}"
            }

        # Transfer
        self.quotas[from_id][quota_type] -= amount
        self.quotas[to_id][quota_type] += amount

        return {
            "success": True,
            "transferred": amount,
            "quota_type": quota_type,
            "from": from_id,
            "to": to_id,
            "from_new_quota": self.quotas[from_id][quota_type],
            "to_new_quota": self.quotas[to_id][quota_type]
        }


class GenesisEventLog(GenesisArtifact):
    """
    Genesis artifact for passive observability.

    This is the only way agents can learn about world events.
    Nothing is injected into prompts - agents must actively read.
    Reading is FREE in scrip, but costs real input tokens.

    Methods:
    - read([offset, limit]) -> list of events  [FREE]
    """

    logger: EventLogger

    def __init__(self, logger: EventLogger) -> None:
        """
        Args:
            logger: The world's EventLogger instance
        """
        super().__init__(
            artifact_id="genesis_event_log",
            description="World event log - passive observability. Reading is free but costs input tokens."
        )
        self.logger = logger

        self.register_method(
            name="read",
            handler=self._read,
            cost=0,  # Free in scrip - but consumes input tokens on next turn
            description="Read recent events. Args: [offset, limit] - both optional. Default: last 50 events."
        )

    def _read(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Read events from the log.

        Args format: [offset, limit]
        - offset: skip this many events from the end (default 0)
        - limit: return at most this many events (default from config)
        """
        offset = 0
        default_limit: int = get("logging.default_recent") or 50
        max_per_read: int = get_genesis_config("event_log", "max_per_read") or 100
        buffer_size: int = get_genesis_config("event_log", "buffer_size") or 1000
        limit = default_limit

        if args and len(args) >= 1 and isinstance(args[0], int):
            offset = args[0]
        if args and len(args) >= 2 and isinstance(args[1], int):
            limit = min(args[1], max_per_read)  # Cap to prevent abuse

        # Get all recent events then slice
        all_events = self.logger.read_recent(buffer_size)

        if offset > 0:
            # Slice from offset
            end_idx = len(all_events) - offset
            start_idx = max(0, end_idx - limit)
            events = all_events[start_idx:end_idx]
        else:
            # Just the most recent
            events = all_events[-limit:] if len(all_events) > limit else all_events

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "total_available": len(all_events),
            "warning": "Reading events costs input tokens on your next turn. Be strategic about what you read."
        }


class RightsConfig(TypedDict, total=False):
    """Configuration for rights registry."""
    default_compute_quota: int
    default_disk_quota: int
    default_flow_quota: int  # Legacy name
    default_stock_quota: int  # Legacy name


def create_genesis_artifacts(
    ledger: Ledger,
    mint_callback: Callable[[str, int], None],
    artifact_store: ArtifactStore | None = None,
    logger: EventLogger | None = None,
    rights_config: RightsConfig | None = None
) -> dict[str, GenesisArtifact]:
    """
    Factory function to create all genesis artifacts.

    Args:
        ledger: The world's Ledger instance
        mint_callback: Function(agent_id, amount) to mint new scrip
        artifact_store: ArtifactStore for oracle to look up artifacts
        logger: EventLogger for genesis_event_log
        rights_config: Dict with 'default_compute_quota' and 'default_disk_quota'
                       (also accepts legacy 'default_flow_quota'/'default_stock_quota')

    Returns:
        Dict mapping artifact_id -> GenesisArtifact
    """
    genesis_ledger = GenesisLedger(ledger)
    genesis_oracle = GenesisOracle(mint_callback, artifact_store=artifact_store)

    artifacts: dict[str, GenesisArtifact] = {
        genesis_ledger.id: genesis_ledger,
        genesis_oracle.id: genesis_oracle
    }

    # Add event log if logger provided
    if logger:
        genesis_event_log = GenesisEventLog(logger)
        artifacts[genesis_event_log.id] = genesis_event_log

    # Add rights registry if config provided
    if rights_config:
        # Support both new names and legacy names, with config fallback
        compute_fallback: int = get("resources.flow.compute.per_tick") or 50
        disk_fallback: int = get("resources.stock.disk.total") or 10000
        default_compute = rights_config.get("default_compute_quota",
                          rights_config.get("default_flow_quota", compute_fallback))
        default_disk = rights_config.get("default_disk_quota",
                       rights_config.get("default_stock_quota", disk_fallback))
        genesis_rights = GenesisRightsRegistry(
            default_compute=default_compute,
            default_disk=default_disk,
            artifact_store=artifact_store
        )
        artifacts[genesis_rights.id] = genesis_rights

    return artifacts
