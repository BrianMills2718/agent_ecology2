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
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_genesis_config, get, get_validated_config
from config_schema import GenesisConfig

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


class SpawnPrincipalResult(TypedDict, total=False):
    """Result from spawn_principal operation."""
    success: bool
    error: str
    principal_id: str


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


class TransferOwnershipResult(TypedDict, total=False):
    """Result from transfer_ownership operation."""
    success: bool
    error: str
    artifact_id: str
    from_owner: str
    to_owner: str


class GenesisLedger(GenesisArtifact):
    """
    Genesis artifact that proxies to the world ledger.

    Two types of balances:
    - flow: Action budget (resets each tick) - real resource constraint
    - scrip: Economic currency (persistent) - medium of exchange

    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore | None

    def __init__(
        self,
        ledger: Ledger,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        ledger_cfg = cfg.ledger

        super().__init__(
            artifact_id=ledger_cfg.id,
            description=ledger_cfg.description
        )
        self.ledger = ledger
        self.artifact_store = artifact_store

        # Register methods with costs/descriptions from config
        self.register_method(
            name="balance",
            handler=self._balance,
            cost=ledger_cfg.methods.balance.cost,
            description=ledger_cfg.methods.balance.description
        )

        self.register_method(
            name="all_balances",
            handler=self._all_balances,
            cost=ledger_cfg.methods.all_balances.cost,
            description=ledger_cfg.methods.all_balances.description
        )

        self.register_method(
            name="transfer",
            handler=self._transfer,
            cost=ledger_cfg.methods.transfer.cost,
            description=ledger_cfg.methods.transfer.description
        )

        self.register_method(
            name="spawn_principal",
            handler=self._spawn_principal,
            cost=ledger_cfg.methods.spawn_principal.cost,
            description=ledger_cfg.methods.spawn_principal.description
        )

        self.register_method(
            name="transfer_ownership",
            handler=self._transfer_ownership,
            cost=ledger_cfg.methods.transfer_ownership.cost,
            description=ledger_cfg.methods.transfer_ownership.description
        )

    def _balance(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get balance for an agent (resources and scrip)."""
        if not args or len(args) < 1:
            return {"success": False, "error": "balance requires [agent_id]"}
        agent_id: str = args[0]
        compute = self.ledger.get_compute(agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            "flow": compute,  # Backward compat
            "compute": compute,  # Clearer name
            "scrip": self.ledger.get_scrip(agent_id),
            "resources": self.ledger.get_all_resources(agent_id)  # New: all resources
        }

    def _all_balances(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all balances (resources and scrip for each agent)."""
        # Include both legacy format and new format
        legacy = self.ledger.get_all_balances()
        full = self.ledger.get_all_balances_full()
        return {
            "success": True,
            "balances": legacy,  # Backward compat
            "balances_full": full  # New: includes all resources
        }

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

    def _spawn_principal(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Spawn a new principal with 0 scrip and 0 compute.

        The new principal starts with nothing - parent must transfer resources
        to keep it alive.

        Args:
            args: [] (no arguments needed, system generates ID)
            invoker_id: The agent spawning the new principal

        Returns:
            {"success": True, "principal_id": new_id} on success
        """
        # Generate a unique principal ID
        new_id = f"agent_{uuid.uuid4().hex[:8]}"

        # Create ledger entry with 0 scrip, 0 compute
        self.ledger.create_principal(new_id, starting_scrip=0, starting_compute=0)

        return {"success": True, "principal_id": new_id}

    def _transfer_ownership(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer ownership of an artifact to another principal.

        Args:
            args: [artifact_id, to_id] - artifact to transfer and new owner
            invoker_id: Must be the current owner of the artifact

        Returns:
            {"success": True, "artifact_id": ..., "from_owner": ..., "to_owner": ...}
        """
        if not args or len(args) < 2:
            return {"success": False, "error": "transfer_ownership requires [artifact_id, to_id]"}

        artifact_id: str = args[0]
        to_id: str = args[1]

        if not self.artifact_store:
            return {"success": False, "error": "Artifact store not configured"}

        # Get the artifact to verify ownership
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Security check: can only transfer artifacts you own
        if artifact.owner_id != invoker_id:
            return {
                "success": False,
                "error": f"Cannot transfer {artifact_id} - you are not the owner (owner is {artifact.owner_id})"
            }

        # Perform the transfer
        success = self.artifact_store.transfer_ownership(artifact_id, invoker_id, to_id)
        if success:
            return {
                "success": True,
                "artifact_id": artifact_id,
                "from_owner": invoker_id,
                "to_owner": to_id
            }
        else:
            return {"success": False, "error": "Transfer failed"}


class GenesisOracle(GenesisArtifact):
    """
    Genesis artifact for external minting.

    Uses LLM to evaluate submitted artifacts and estimate engagement score.
    Mints credits to submitters based on score.

    All method costs and descriptions are configurable via config.yaml.
    """

    mint_callback: Callable[[str, int], None]
    artifact_store: ArtifactStore | None
    submissions: dict[str, SubmissionInfo]
    _scorer: Any  # OracleScorer, lazy-loaded
    _mint_ratio: int  # Configurable mint ratio

    def __init__(
        self,
        mint_callback: Callable[[str, int], None],
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            mint_callback: Function(agent_id, amount) to mint credits
            artifact_store: ArtifactStore to look up submitted artifacts
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        oracle_cfg = cfg.oracle

        super().__init__(
            artifact_id=oracle_cfg.id,
            description=oracle_cfg.description
        )
        self.mint_callback = mint_callback
        self.artifact_store = artifact_store
        self.submissions = {}  # artifact_id -> submission info
        self._scorer = None  # Lazy-loaded
        self._mint_ratio = oracle_cfg.mint_ratio

        # Register methods with costs/descriptions from config
        self.register_method(
            name="status",
            handler=self._status,
            cost=oracle_cfg.methods.status.cost,
            description=oracle_cfg.methods.status.description
        )

        self.register_method(
            name="submit",
            handler=self._submit,
            cost=oracle_cfg.methods.submit.cost,
            description=oracle_cfg.methods.submit.description
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=oracle_cfg.methods.check.cost,
            description=oracle_cfg.methods.check.description
        )

        self.register_method(
            name="process",
            handler=self._process,
            cost=oracle_cfg.methods.process.cost,
            description=oracle_cfg.methods.process.description
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
            # Scale: score / mint_ratio (configurable via config.yaml)
            credits_to_mint = score // self._mint_ratio
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

        # Mint credits based on score (configurable via config.yaml)
        credits_to_mint = score // self._mint_ratio
        if credits_to_mint > 0:
            self.mint_callback(submission["submitter"], credits_to_mint)

        return True


class GenesisRightsRegistry(GenesisArtifact):
    """
    Genesis artifact for managing resource rights (means of production).

    Supports generic resources defined in config. Common resources:
    - compute: LLM tokens per tick (renews each tick)
    - disk: Bytes of storage (fixed pool)

    See docs/RESOURCE_MODEL.md for full design rationale.
    All method costs and descriptions are configurable via config.yaml.
    """

    default_quotas: dict[str, float]
    artifact_store: ArtifactStore | None
    quotas: dict[str, dict[str, float]]

    def __init__(
        self,
        default_quotas: dict[str, float] | None = None,
        artifact_store: ArtifactStore | None = None,
        genesis_config: GenesisConfig | None = None,
        # Backward compat kwargs
        default_compute: int = 0,
        default_disk: int = 0,
    ) -> None:
        """
        Args:
            default_quotas: Dict of {resource_name: default_amount} for all resources
            artifact_store: ArtifactStore to calculate actual disk usage
            genesis_config: Optional genesis config (uses global if not provided)
            default_compute: DEPRECATED - use default_quotas
            default_disk: DEPRECATED - use default_quotas
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        rights_cfg = cfg.rights_registry

        super().__init__(
            artifact_id=rights_cfg.id,
            description=rights_cfg.description
        )

        # Build default quotas from explicit dict or backward compat params
        if default_quotas:
            self.default_quotas = dict(default_quotas)
        else:
            # Backward compat: build from positional args
            self.default_quotas = {}
            if default_compute > 0:
                self.default_quotas["compute"] = float(default_compute)
            if default_disk > 0:
                self.default_quotas["disk"] = float(default_disk)

        self.artifact_store = artifact_store

        # Track quotas per agent: {agent_id: {resource: amount}}
        self.quotas = {}

        # Register methods with costs/descriptions from config
        self.register_method(
            name="check_quota",
            handler=self._check_quota,
            cost=rights_cfg.methods.check_quota.cost,
            description=rights_cfg.methods.check_quota.description
        )

        self.register_method(
            name="all_quotas",
            handler=self._all_quotas,
            cost=rights_cfg.methods.all_quotas.cost,
            description=rights_cfg.methods.all_quotas.description
        )

        self.register_method(
            name="transfer_quota",
            handler=self._transfer_quota,
            cost=rights_cfg.methods.transfer_quota.cost,
            description=rights_cfg.methods.transfer_quota.description
        )

    def ensure_agent(self, agent_id: str) -> None:
        """Ensure an agent has quota entries (initialize with defaults)"""
        if agent_id not in self.quotas:
            self.quotas[agent_id] = dict(self.default_quotas)

    def get_quota(self, agent_id: str, resource: str) -> float:
        """Get quota for a specific resource."""
        self.ensure_agent(agent_id)
        return self.quotas[agent_id].get(resource, 0.0)

    def set_quota(self, agent_id: str, resource: str, amount: float) -> None:
        """Set quota for a specific resource."""
        self.ensure_agent(agent_id)
        self.quotas[agent_id][resource] = amount

    def get_all_quotas(self, agent_id: str) -> dict[str, float]:
        """Get all quotas for an agent."""
        self.ensure_agent(agent_id)
        return dict(self.quotas[agent_id])

    # Backward compat: compute = "compute" resource
    def get_compute_quota(self, agent_id: str) -> int:
        """Get compute quota (tokens/tick) for an agent."""
        return int(self.get_quota(agent_id, "compute"))

    # Backward compat: disk = "disk" resource
    def get_disk_quota(self, agent_id: str) -> int:
        """Get disk quota (bytes) for an agent."""
        return int(self.get_quota(agent_id, "disk"))

    def get_disk_used(self, agent_id: str) -> int:
        """Get actual disk space used by an agent."""
        if self.artifact_store:
            return self.artifact_store.get_owner_usage(agent_id)
        return 0

    def can_write(self, agent_id: str, additional_bytes: int) -> bool:
        """Check if agent can write additional_bytes without exceeding disk quota."""
        quota = self.get_disk_quota(agent_id)
        used = self.get_disk_used(agent_id)
        return (used + additional_bytes) <= quota

    # Backward compat aliases
    def get_flow_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_compute_quota()."""
        return self.get_compute_quota(agent_id)

    def get_stock_quota(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_quota()."""
        return self.get_disk_quota(agent_id)

    def get_stock_used(self, agent_id: str) -> int:
        """DEPRECATED: Use get_disk_used()."""
        return self.get_disk_used(agent_id)

    def _check_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check quotas for an agent."""
        if not args or len(args) < 1:
            return {"success": False, "error": "check_quota requires [agent_id]"}

        agent_id: str = args[0]
        self.ensure_agent(agent_id)

        all_quotas = self.quotas[agent_id]
        disk_used = self.get_disk_used(agent_id)
        disk_quota = int(all_quotas.get("disk", 0))

        # Include both legacy format and new generic format
        return {
            "success": True,
            "agent_id": agent_id,
            "compute_quota": int(all_quotas.get("compute", 0)),
            "disk_quota": disk_quota,
            "disk_used": disk_used,
            "disk_available": disk_quota - disk_used,
            "quotas": all_quotas  # New: all resource quotas
        }

    def _all_quotas(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get all agent quotas."""
        result: dict[str, Any] = {}
        for agent_id, quota in self.quotas.items():
            disk_used = self.get_disk_used(agent_id)
            disk_quota = int(quota.get("disk", 0))
            result[agent_id] = {
                "compute_quota": int(quota.get("compute", 0)),
                "disk_quota": disk_quota,
                "disk_used": disk_used,
                "disk_available": disk_quota - disk_used,
                "quotas": quota  # New: all resource quotas
            }
        return {"success": True, "quotas": result}

    def _transfer_quota(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer quota between agents. Works with any resource type."""
        if not args or len(args) < 4:
            return {"success": False, "error": "transfer_quota requires [from_id, to_id, resource, amount]"}

        from_id: str = args[0]
        to_id: str = args[1]
        resource: str = args[2]
        amount: Any = args[3]

        # Security check: can only transfer FROM yourself
        if from_id != invoker_id:
            return {"success": False, "error": f"Cannot transfer from {from_id} - you are {invoker_id}"}

        # Validate resource exists in defaults (to prevent typos)
        if resource not in self.default_quotas:
            valid_resources = list(self.default_quotas.keys())
            return {"success": False, "error": f"Unknown resource '{resource}'. Valid: {valid_resources}"}

        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"success": False, "error": "amount must be positive number"}

        self.ensure_agent(from_id)
        self.ensure_agent(to_id)

        # Check if sender has enough quota
        current = self.quotas[from_id].get(resource, 0.0)
        if current < amount:
            return {
                "success": False,
                "error": f"Insufficient {resource} quota. Have {current}, need {amount}"
            }

        # Transfer
        self.quotas[from_id][resource] = current - amount
        self.quotas[to_id][resource] = self.quotas[to_id].get(resource, 0.0) + amount

        return {
            "success": True,
            "transferred": amount,
            "quota_type": resource,  # Keep legacy field name
            "resource": resource,    # New field name
            "from": from_id,
            "to": to_id,
            "from_new_quota": self.quotas[from_id][resource],
            "to_new_quota": self.quotas[to_id][resource]
        }


class GenesisEventLog(GenesisArtifact):
    """
    Genesis artifact for passive observability.

    This is the only way agents can learn about world events.
    Nothing is injected into prompts - agents must actively read.
    Reading is FREE in scrip, but costs real input tokens.

    All method costs and descriptions are configurable via config.yaml.
    """

    logger: EventLogger
    _max_per_read: int
    _buffer_size: int

    def __init__(self, logger: EventLogger, genesis_config: GenesisConfig | None = None) -> None:
        """
        Args:
            logger: The world's EventLogger instance
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        event_log_cfg = cfg.event_log

        super().__init__(
            artifact_id=event_log_cfg.id,
            description=event_log_cfg.description
        )
        self.logger = logger
        self._max_per_read = event_log_cfg.max_per_read
        self._buffer_size = event_log_cfg.buffer_size

        # Register methods with costs/descriptions from config
        self.register_method(
            name="read",
            handler=self._read,
            cost=event_log_cfg.methods.read.cost,
            description=event_log_cfg.methods.read.description
        )

    def _read(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Read events from the log.

        Args format: [offset, limit]
        - offset: skip this many events from the end (default 0)
        - limit: return at most this many events (default from config)
        """
        offset = 0
        default_limit: int = get("logging.default_recent") or 50
        limit = default_limit

        if args and len(args) >= 1 and isinstance(args[0], int):
            offset = args[0]
        if args and len(args) >= 2 and isinstance(args[1], int):
            limit = min(args[1], self._max_per_read)  # Cap to prevent abuse

        # Get all recent events then slice
        all_events = self.logger.read_recent(self._buffer_size)

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


class GenesisEscrow(GenesisArtifact):
    """
    Genesis artifact for trustless artifact trading.

    Implements the Gatekeeper pattern:
    1. Seller transfers artifact ownership to escrow
    2. Seller registers listing with price
    3. Buyer pays price -> escrow transfers ownership to buyer, scrip to seller

    This enables safe trading without trusting counterparties.
    All method costs and descriptions are configurable via config.yaml.
    """

    ledger: Ledger
    artifact_store: ArtifactStore
    listings: dict[str, EscrowListing]

    def __init__(
        self,
        ledger: Ledger,
        artifact_store: ArtifactStore,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            ledger: The world's Ledger instance (for scrip transfers)
            artifact_store: The world's ArtifactStore (for ownership transfers)
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        escrow_cfg = cfg.escrow

        super().__init__(
            artifact_id=escrow_cfg.id,
            description=escrow_cfg.description
        )
        self.ledger = ledger
        self.artifact_store = artifact_store
        self.listings = {}

        # Register methods with costs/descriptions from config
        self.register_method(
            name="deposit",
            handler=self._deposit,
            cost=escrow_cfg.methods.deposit.cost,
            description=escrow_cfg.methods.deposit.description
        )

        self.register_method(
            name="purchase",
            handler=self._purchase,
            cost=escrow_cfg.methods.purchase.cost,
            description=escrow_cfg.methods.purchase.description
        )

        self.register_method(
            name="cancel",
            handler=self._cancel,
            cost=escrow_cfg.methods.cancel.cost,
            description=escrow_cfg.methods.cancel.description
        )

        self.register_method(
            name="check",
            handler=self._check,
            cost=escrow_cfg.methods.check.cost,
            description=escrow_cfg.methods.check.description
        )

        self.register_method(
            name="list_active",
            handler=self._list_active,
            cost=escrow_cfg.methods.list_active.cost,
            description=escrow_cfg.methods.list_active.description
        )

    def _deposit(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Deposit an artifact into escrow for sale.

        IMPORTANT: You must first transfer ownership to escrow:
        invoke_artifact("genesis_ledger", "transfer_ownership", [artifact_id, "genesis_escrow"])

        Args: [artifact_id, price] or [artifact_id, price, buyer_id]
        - artifact_id: The artifact to sell (must already be owned by escrow)
        - price: Sale price in scrip
        - buyer_id: Optional - restrict purchase to specific buyer
        """
        if not args or len(args) < 2:
            return {"success": False, "error": "deposit requires [artifact_id, price] or [artifact_id, price, buyer_id]"}

        artifact_id: str = args[0]
        price: Any = args[1]
        buyer_id: str | None = args[2] if len(args) > 2 else None

        # Validate price
        if not isinstance(price, int) or price <= 0:
            return {"success": False, "error": "Price must be a positive integer"}

        # Check artifact exists
        artifact = self.artifact_store.get(artifact_id)
        if not artifact:
            return {"success": False, "error": f"Artifact {artifact_id} not found"}

        # Verify escrow owns the artifact (seller must have transferred first)
        if artifact.owner_id != self.id:
            return {
                "success": False,
                "error": f"Escrow does not own {artifact_id}. First transfer ownership: "
                         f"invoke_artifact('genesis_ledger', 'transfer_ownership', ['{artifact_id}', '{self.id}'])"
            }

        # Check not already listed
        if artifact_id in self.listings and self.listings[artifact_id]["status"] == "active":
            return {"success": False, "error": f"Artifact {artifact_id} is already listed"}

        # Create listing
        self.listings[artifact_id] = {
            "artifact_id": artifact_id,
            "seller_id": invoker_id,
            "price": price,
            "buyer_id": buyer_id,
            "status": "active"
        }

        return {
            "success": True,
            "artifact_id": artifact_id,
            "price": price,
            "seller": invoker_id,
            "message": f"Listed {artifact_id} for {price} scrip" + (f" (restricted to {buyer_id})" if buyer_id else "")
        }

    def _purchase(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Purchase an artifact from escrow.

        Transfers price from buyer to seller, ownership from escrow to buyer.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "purchase requires [artifact_id]"}

        artifact_id: str = args[0]

        # Check listing exists and is active
        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]
        if listing["status"] != "active":
            return {"success": False, "error": f"Listing for {artifact_id} is not active (status: {listing['status']})"}

        # Check buyer restriction
        if listing["buyer_id"] and listing["buyer_id"] != invoker_id:
            return {"success": False, "error": f"This listing is restricted to buyer {listing['buyer_id']}"}

        # Can't buy your own listing
        if listing["seller_id"] == invoker_id:
            return {"success": False, "error": "Cannot purchase your own listing"}

        price = listing["price"]
        seller_id = listing["seller_id"]

        # Check buyer can afford
        if not self.ledger.can_afford_scrip(invoker_id, price):
            return {
                "success": False,
                "error": f"Insufficient scrip. Need {price}, have {self.ledger.get_scrip(invoker_id)}"
            }

        # Execute the trade atomically:
        # 1. Transfer scrip from buyer to seller
        if not self.ledger.transfer_scrip(invoker_id, seller_id, price):
            return {"success": False, "error": "Scrip transfer failed"}

        # 2. Transfer ownership from escrow to buyer
        if not self.artifact_store.transfer_ownership(artifact_id, self.id, invoker_id):
            # Rollback scrip transfer
            self.ledger.transfer_scrip(seller_id, invoker_id, price)
            return {"success": False, "error": "Ownership transfer failed (scrip refunded)"}

        # Mark listing as completed
        listing["status"] = "completed"

        return {
            "success": True,
            "artifact_id": artifact_id,
            "price": price,
            "seller": seller_id,
            "buyer": invoker_id,
            "message": f"Purchased {artifact_id} for {price} scrip from {seller_id}"
        }

    def _cancel(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Cancel an escrow listing and return artifact to seller.

        Only the seller can cancel. Only active listings can be cancelled.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "cancel requires [artifact_id]"}

        artifact_id: str = args[0]

        # Check listing exists
        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]

        # Only seller can cancel
        if listing["seller_id"] != invoker_id:
            return {"success": False, "error": "Only the seller can cancel a listing"}

        # Must be active
        if listing["status"] != "active":
            return {"success": False, "error": f"Listing is not active (status: {listing['status']})"}

        # Return ownership to seller
        if not self.artifact_store.transfer_ownership(artifact_id, self.id, invoker_id):
            return {"success": False, "error": "Failed to return ownership to seller"}

        # Mark as cancelled
        listing["status"] = "cancelled"

        return {
            "success": True,
            "artifact_id": artifact_id,
            "seller": invoker_id,
            "message": f"Cancelled listing for {artifact_id}, ownership returned to {invoker_id}"
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check the status of an escrow listing.

        Args: [artifact_id]
        """
        if not args or len(args) < 1:
            return {"success": False, "error": "check requires [artifact_id]"}

        artifact_id: str = args[0]

        if artifact_id not in self.listings:
            return {"success": False, "error": f"No listing found for {artifact_id}"}

        listing = self.listings[artifact_id]
        return {
            "success": True,
            "listing": listing
        }

    def _list_active(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all active escrow listings.

        Args: []
        """
        active = [
            listing for listing in self.listings.values()
            if listing["status"] == "active"
        ]
        return {
            "success": True,
            "listings": active,
            "count": len(active)
        }


class RightsConfig(TypedDict, total=False):
    """Configuration for rights registry."""
    default_quotas: dict[str, float]  # Generic: {resource: amount}
    default_compute_quota: int  # Legacy
    default_disk_quota: int  # Legacy
    default_flow_quota: int  # Legacy
    default_stock_quota: int  # Legacy


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
        artifact_store: ArtifactStore for oracle to look up artifacts
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

    # Create oracle if enabled
    if cfg.artifacts.oracle.enabled:
        genesis_oracle = GenesisOracle(
            mint_callback,
            artifact_store=artifact_store,
            genesis_config=cfg
        )
        artifacts[genesis_oracle.id] = genesis_oracle

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
            compute_fallback: int = get("resources.flow.compute.per_tick") or 50
            disk_fallback: int = get("resources.stock.disk.total") or 10000
            default_compute = rights_config.get("default_compute_quota",
                              rights_config.get("default_flow_quota", compute_fallback))
            default_disk = rights_config.get("default_disk_quota",
                           rights_config.get("default_stock_quota", disk_fallback))
            default_quotas = {
                "compute": float(default_compute),
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

    return artifacts
