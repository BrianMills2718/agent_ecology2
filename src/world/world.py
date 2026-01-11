"""World kernel - the core simulation loop"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from .ledger import Ledger
from .artifacts import ArtifactStore, Artifact, WriteResult
from .logger import EventLogger
from .actions import (
    ActionIntent, ActionResult, ActionType,
    NoopIntent, ReadArtifactIntent, WriteArtifactIntent,
    InvokeArtifactIntent
)
# NOTE: TransferIntent removed - all transfers via genesis_ledger.transfer()
from .genesis import (
    create_genesis_artifacts, GenesisArtifact, GenesisRightsRegistry,
    GenesisOracle, RightsConfig, SubmissionInfo
)
from .executor import get_executor

from ..config import get as config_get, compute_per_agent_quota, PerAgentQuota


class PrincipalConfig(TypedDict, total=False):
    """Configuration for a principal."""
    id: str
    starting_scrip: int
    starting_credits: int  # Legacy name


class LoggingConfig(TypedDict):
    """Logging configuration."""
    output_file: str


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


class OracleSubmissionStatus(TypedDict, total=False):
    """Status of an oracle submission."""
    status: str
    submitter: str
    score: int | None


class StateSummary(TypedDict):
    """World state summary."""
    tick: int
    balances: dict[str, BalanceInfo]
    artifacts: list[dict[str, Any]]
    quotas: dict[str, QuotaInfo]
    oracle_submissions: dict[str, OracleSubmissionStatus]
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

    def __init__(self, config: ConfigDict) -> None:
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

        # Core state
        self.ledger = Ledger()
        self.artifacts = ArtifactStore()
        self.logger = EventLogger(config["logging"]["output_file"])

        # Genesis artifacts (system-owned proxies)
        self.genesis_artifacts = create_genesis_artifacts(
            ledger=self.ledger,
            mint_callback=self._mint_scrip,
            artifact_store=self.artifacts,
            logger=self.logger,
            rights_config=self.rights_config
        )

        # Store reference to rights registry for quota enforcement
        rights_registry = self.genesis_artifacts.get("genesis_rights_registry")
        self.rights_registry = rights_registry if isinstance(rights_registry, GenesisRightsRegistry) else None

        # Seed genesis_handbook artifact (readable documentation for agents)
        self._seed_handbook()

        # Initialize principals from config
        self.principal_ids = []
        default_starting_scrip: int = config_get("scrip.starting_amount") or 100
        for p in config["principals"]:
            # Initialize with starting scrip (persistent currency)
            # Flow will be set when first tick starts
            starting_scrip = p.get("starting_scrip", p.get("starting_credits", default_starting_scrip))
            self.ledger.create_principal(p["id"], starting_scrip=starting_scrip)
            self.principal_ids.append(p["id"])
            # Initialize agent in rights registry
            if self.rights_registry:
                self.rights_registry.ensure_agent(p["id"])

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
            "oracle": "handbook_oracle",
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
        """Mint new scrip for a principal (used by oracle).

        Scrip is the economic currency - minting adds purchasing power.
        """
        self.ledger.credit_scrip(principal_id, amount)
        self.logger.log("mint", {
            "tick": self.tick,
            "principal_id": principal_id,
            "amount": amount,
            "scrip_after": self.ledger.get_scrip(principal_id)
        })

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
                        message=f"Access denied: you are not allowed to read {intent.artifact_id}"
                    )
                else:
                    # Check if can afford read_price (economic cost -> SCRIP)
                    read_price: int = artifact.policy.get("read_price", 0)
                    if read_price > 0 and not self.ledger.can_afford_scrip(intent.principal_id, read_price):
                        result = ActionResult(
                            success=False,
                            message=f"Cannot afford read price: {read_price} scrip (have {self.ledger.get_scrip(intent.principal_id)})"
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
                    message=f"Artifact {intent.artifact_id} not found"
                )

        elif isinstance(intent, WriteArtifactIntent):
            result = self._execute_write(intent)

        elif isinstance(intent, InvokeArtifactIntent):
            result = self._execute_invoke(intent)

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
                message=f"Cannot modify system artifact {intent.artifact_id}"
            )

        # Check write permission for existing artifacts (policy-based)
        existing = self.artifacts.get(intent.artifact_id)
        if existing and not existing.can_write(intent.principal_id):
            return ActionResult(
                success=False,
                message=f"Access denied: you are not allowed to write to {intent.artifact_id}"
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
                    message=f"Disk quota exceeded. Need {net_new_bytes} bytes, have {quota - used} available (quota: {quota}, used: {used})"
                )

        # Validate executable code if provided
        if intent.executable:
            executor = get_executor()
            valid, error = executor.validate_code(intent.code)
            if not valid:
                return ActionResult(
                    success=False,
                    message=f"Invalid executable code: {error}"
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
        - Genesis artifacts (system proxies to ledger, oracle, etc.)
        - Executable artifacts (agent-created code)

        Cost model:
        - Genesis method costs: Configurable compute cost per method
        - Artifact prices: Scrip paid to owner on successful invocation
        """
        artifact_id = intent.artifact_id
        method_name = intent.method
        args = intent.args

        # Check genesis artifacts first
        if artifact_id in self.genesis_artifacts:
            genesis = self.genesis_artifacts[artifact_id]
            method = genesis.get_method(method_name)

            if not method:
                return ActionResult(
                    success=False,
                    message=f"Method '{method_name}' not found on {artifact_id}. Available: {[m['name'] for m in genesis.list_methods()]}"
                )

            # Genesis method costs are COMPUTE (physical resource, not scrip)
            if method.cost > 0 and not self.ledger.can_spend_compute(intent.principal_id, method.cost):
                return ActionResult(
                    success=False,
                    message=f"Cannot afford method cost: {method.cost} compute (have {self.ledger.get_compute(intent.principal_id)})"
                )

            # Deduct compute cost FIRST (always paid, even on failure)
            # Genesis methods always charge caller (system services)
            resources_consumed: dict[str, float] = {}
            if method.cost > 0:
                self.ledger.spend_compute(intent.principal_id, method.cost)
                resources_consumed["llm_tokens"] = float(method.cost)

            # Execute the genesis method
            try:
                result_data: dict[str, Any] = method.handler(args, intent.principal_id)

                if result_data.get("success"):
                    return ActionResult(
                        success=True,
                        message=f"Invoked {artifact_id}.{method_name}",
                        data=result_data,
                        resources_consumed=resources_consumed if resources_consumed else None,
                        charged_to=intent.principal_id,
                    )
                else:
                    return ActionResult(
                        success=False,
                        message=result_data.get("error", "Method failed"),
                        resources_consumed=resources_consumed if resources_consumed else None,
                        charged_to=intent.principal_id,
                    )
            except Exception as e:
                return ActionResult(
                    success=False,
                    message=f"Method execution error: {str(e)}",
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=intent.principal_id,
                )

        # Check regular artifacts for executable invocation
        regular_artifact = self.artifacts.get(artifact_id)
        if regular_artifact:
            if not regular_artifact.executable:
                return ActionResult(
                    success=False,
                    message=f"Artifact {artifact_id} is not executable"
                )

            # Check invoke permission (policy-based)
            if not regular_artifact.can_invoke(intent.principal_id):
                return ActionResult(
                    success=False,
                    message=f"Access denied: you are not allowed to invoke {artifact_id}"
                )

            # Price (SCRIP) - economic payment to owner
            price = regular_artifact.price
            owner_id = regular_artifact.owner_id

            # Caller pays for physical resources
            resource_payer = intent.principal_id

            # Check if caller can afford the price (scrip)
            if price > 0 and not self.ledger.can_afford_scrip(intent.principal_id, price):
                return ActionResult(
                    success=False,
                    message=f"Insufficient scrip for price: need {price}, have {self.ledger.get_scrip(intent.principal_id)}"
                )

            # Execute the code
            executor = get_executor()
            exec_result = executor.execute(regular_artifact.code, args)

            # Extract resource consumption from executor
            resources_consumed = exec_result.get("resources_consumed", {})

            if exec_result.get("success"):
                # Deduct physical resources from caller
                for resource, amount in resources_consumed.items():
                    if not self.ledger.can_spend_resource(resource_payer, resource, amount):
                        return ActionResult(
                            success=False,
                            message=f"Insufficient {resource}: need {amount}",
                            resources_consumed=resources_consumed,
                            charged_to=resource_payer,
                        )
                    self.ledger.spend_resource(resource_payer, resource, amount)

                # Pay price to owner from SCRIP (only on success)
                if price > 0 and owner_id != intent.principal_id:
                    self.ledger.deduct_scrip(intent.principal_id, price)
                    self.ledger.credit_scrip(owner_id, price)

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
                    if self.ledger.can_spend_resource(resource_payer, resource, amount):
                        self.ledger.spend_resource(resource_payer, resource, amount)

                return ActionResult(
                    success=False,
                    message=f"Execution failed: {exec_result.get('error')}",
                    data={"error": exec_result.get("error")},
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=resource_payer,
                )

        # Artifact not found
        return ActionResult(
            success=False,
            message=f"Artifact {artifact_id} not found"
        )

    def advance_tick(self) -> bool:
        """
        Advance to the next tick. Renews FLOW RESOURCES for all principals.
        Returns False if max_ticks reached.

        FLOW RESOURCES (compute/llm_tokens) reset each tick based on quotas.
        SCRIP (economic currency) is NOT reset - it persists and accumulates.

        See docs/RESOURCE_MODEL.md for design rationale.
        """
        if self.tick >= self.max_ticks:
            return False

        self.tick += 1

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
            "artifact_count": self.artifacts.count()
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

        # Get oracle submission status
        oracle_status: dict[str, OracleSubmissionStatus] = {}
        oracle = self.genesis_artifacts.get("genesis_oracle")
        if oracle and isinstance(oracle, GenesisOracle) and hasattr(oracle, 'submissions'):
            for artifact_id, sub in oracle.submissions.items():
                oracle_status[artifact_id] = {
                    "status": sub.get("status", "unknown"),
                    "submitter": sub.get("submitter", "unknown"),
                    "score": sub.get("score") if sub.get("status") == "scored" else None
                }

        return {
            "tick": self.tick,
            "balances": self.ledger.get_all_balances(),
            "artifacts": all_artifacts,
            "quotas": quotas,
            "oracle_submissions": oracle_status,
            "recent_events": self.get_recent_events(10)
        }

    def get_recent_events(self, n: int = 20) -> list[dict[str, Any]]:
        """Get recent events from the log"""
        return self.logger.read_recent(n)
