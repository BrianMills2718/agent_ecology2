"""SimulationRunner - Main orchestrator for agent ecology simulation.

Handles:
- World and agent initialization
- Checkpoint restore
- Tick loop with two-phase commit
- Budget tracking
- Dynamic agent creation
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime
from typing import Any, cast, get_args, TYPE_CHECKING

from ..world import World
from ..world.actions import parse_intent_from_json, ActionIntent
from ..world.simulation_engine import SimulationEngine
from ..world.world import StateSummary, ConfigDict
from ..world.genesis import GenesisMint, AuctionResult
from ..world.rate_tracker import RateTracker
from ..agents import Agent
from ..agents.loader import load_agents, create_agent_artifacts, load_agents_from_store, AgentConfig
from ..agents.agent import ActionResult as AgentActionResult, TokenUsage
from ..agents.schema import ActionType
from ..world.artifacts import create_agent_artifact, create_memory_artifact
from ..world.logger import TickSummaryCollector
from ..config import get_validated_config

from .types import (
    PrincipalConfig,
    CheckpointData,
    ActionProposal,
    ThinkingResult,
)
from .checkpoint import save_checkpoint
from .agent_loop import AgentLoopManager, AgentLoopConfig
from .pool import WorkerPool, PoolConfig
from ..agents.state_store import AgentStateStore


class SimulationRunner:
    """Orchestrates the agent ecology simulation.

    Encapsulates all simulation state and logic:
    - World, agents, and physics engine
    - Two-phase commit tick execution
    - Budget tracking and checkpointing
    - Dynamic agent creation for spawned principals
    - Pause/resume control for dashboard integration

    Usage:
        runner = SimulationRunner(config)
        world = await runner.run()  # or runner.run_sync()
    """

    # Class-level reference for dashboard access
    _active_runner: "SimulationRunner | None" = None

    @classmethod
    def get_active(cls) -> "SimulationRunner | None":
        """Get the currently running simulation runner."""
        return cls._active_runner

    def __init__(
        self,
        config: dict[str, Any],
        max_agents: int | None = None,
        verbose: bool = True,
        delay: float | None = None,
        checkpoint: CheckpointData | None = None,
    ) -> None:
        """Initialize the simulation runner.

        Args:
            config: Configuration dictionary
            max_agents: Limit number of agents (optional)
            verbose: Print progress (default True)
            delay: Seconds between ticks (defaults to config value)
            checkpoint: Checkpoint data to resume from (optional)
        """
        self.config = config
        self.max_agents = max_agents
        self.verbose = verbose
        self.delay = delay if delay is not None else config.get("llm", {}).get("rate_limit_delay", 15.0)
        self.checkpoint = checkpoint

        # Generate run ID for log organization
        self.run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

        # Initialize engine
        self.engine = SimulationEngine.from_config(config)
        if checkpoint:
            self.engine.reset_budget(checkpoint["cumulative_api_cost"])

        # Load agent configs
        agent_configs: list[AgentConfig] = load_agents()
        if max_agents:
            agent_configs = agent_configs[:max_agents]
        self.agent_configs = agent_configs

        # Build principals list for world initialization
        default_starting_scrip: int = config.get("scrip", {}).get("starting_amount", 100)
        principals: list[PrincipalConfig] = []
        for a in agent_configs:
            scrip = a.get("starting_scrip") or a.get("starting_credits") or default_starting_scrip
            principals.append({
                "id": a["id"],
                "starting_scrip": scrip if isinstance(scrip, int) else default_starting_scrip,
            })
        config["principals"] = principals

        # Initialize world
        self.world = World(cast(ConfigDict, config), run_id=self.run_id)

        # Restore checkpoint if provided
        if checkpoint:
            self._restore_checkpoint(checkpoint)

        # Initialize agents
        self.agents = self._create_agents(agent_configs)

        # Autonomous loop support (INT-003)
        # Store reference to the flag for convenience
        self.use_autonomous_loops = self.world.use_autonomous_loops

        # Create AgentLoopManager if autonomous mode is enabled
        if self.use_autonomous_loops:
            # Need a RateTracker for resource gating
            # Use world's rate_tracker if available, otherwise create one
            rate_tracker = self.world.rate_tracker
            if rate_tracker is None:
                # Create a default rate tracker for autonomous mode
                rate_tracker = RateTracker(window_seconds=60.0)
                self.world.rate_tracker = rate_tracker
            self.world.loop_manager = AgentLoopManager(rate_tracker)

        # Worker pool support (Plan #53)
        execution_config = config.get("execution", {})
        self.use_worker_pool = execution_config.get("use_worker_pool", False)
        self._worker_pool: WorkerPool | None = None
        self._state_store: AgentStateStore | None = None

        if self.use_worker_pool:
            # Initialize state store and save initial agent states
            pool_config = execution_config.get("worker_pool", {})
            from pathlib import Path
            state_db_path = Path(pool_config.get("state_db_path", "agent_state.db"))
            self._state_store = AgentStateStore(state_db_path)

            # Save all agent states to SQLite
            for agent in self.agents:
                state = agent.to_state()
                self._state_store.save(state)

            # Create worker pool
            self._worker_pool = WorkerPool(PoolConfig(
                num_workers=pool_config.get("num_workers", 4),
                state_db_path=state_db_path,
                log_dir=config.get("llm", {}).get("log_dir"),
                run_id=self.run_id,
            ))
            self._worker_pool.start()

        # Pause/resume state
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self._running = False

        # Summary logging (Plan #60)
        self._tick_collector: TickSummaryCollector | None = None

    def _restore_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Restore world state from checkpoint.

        Properly restores agent artifacts with their principal capabilities
        (has_standing, can_execute, memory_artifact_id) for unified ontology.
        """
        # Restore tick (subtract 1 because advance_tick increments before first iteration)
        self.world.tick = checkpoint["tick"] - 1

        # Restore balances
        for agent_id, balance_info in checkpoint["balances"].items():
            if agent_id in self.world.ledger.scrip:
                self.world.ledger.scrip[agent_id] = balance_info["scrip"]

        # Restore artifacts
        for artifact_data in checkpoint["artifacts"]:
            artifact = self.world.artifacts.write(
                artifact_id=artifact_data["id"],
                type=artifact_data.get("type", "data"),
                content=artifact_data.get("content", ""),
                owner_id=artifact_data.get("owner_id", "system"),
                executable=artifact_data.get("executable", False),
                price=artifact_data.get("price", 0),
                code=artifact_data.get("code", ""),
                policy=artifact_data.get("policy"),
            )

            # Restore principal capabilities (unified ontology)
            if artifact_data.get("has_standing"):
                artifact.has_standing = True
            if artifact_data.get("can_execute"):
                artifact.can_execute = True
            if artifact_data.get("memory_artifact_id"):
                artifact.memory_artifact_id = artifact_data["memory_artifact_id"]

        if self.verbose:
            print("=== Resuming from checkpoint ===")
            print(f"Previous tick: {checkpoint['tick']}")
            print(f"Previous reason: {checkpoint['reason']}")
            print(f"Cumulative API cost: ${self.engine.cumulative_api_cost:.4f}")
            print(f"Restored artifacts: {len(checkpoint['artifacts'])}")
            print()

    def _create_agents(self, agent_configs: list[AgentConfig]) -> list[Agent]:
        """Create artifact-backed Agent instances from config.

        Uses the unified ontology (Gap #6): agents are artifacts with
        has_standing=True and can_execute=True. Agent artifacts are
        stored in the world's artifact store, enabling persistence
        and trading.
        """
        # Fill in default model for configs that don't specify one
        default_model: str = self.config["llm"]["default_model"]
        for config in agent_configs:
            if not config.get("llm_model"):
                config["llm_model"] = default_model

        # Create agent artifacts in the world's artifact store
        # This populates the store with agent and memory artifacts
        create_agent_artifacts(
            self.world.artifacts,
            agent_configs,
            create_memory=True,
        )

        # Load agents from the artifact store
        # Each agent is backed by its artifact in the store
        agents = load_agents_from_store(
            self.world.artifacts,
            log_dir=self.config["logging"]["log_dir"],
            run_id=self.run_id,
        )

        return agents

    def _check_for_new_principals(self) -> list[Agent]:
        """Check ledger for principals without Agent instances.

        Creates artifact-backed Agent instances for spawned principals.
        Uses the unified ontology (Gap #6): spawned agents are also
        artifacts with has_standing=True and can_execute=True.
        """
        ledger_principals: set[str] = set(self.world.ledger.scrip.keys())
        existing_agent_ids: set[str] = {agent.agent_id for agent in self.agents}
        new_principal_ids: set[str] = ledger_principals - existing_agent_ids

        # Filter out genesis artifacts (they're not agents)
        new_principal_ids = {
            pid for pid in new_principal_ids
            if not pid.startswith("genesis_")
        }

        new_agents: list[Agent] = []
        default_model: str = self.config.get("llm", {}).get(
            "default_model", "gemini/gemini-3-flash-preview"
        )
        log_dir: str = self.config.get("logging", {}).get("log_dir", "llm_logs")
        default_system_prompt: str = (
            "You are a new agent. Survive and thrive. "
            "You start with nothing - seek resources and opportunities. "
            "Read handbook_toc to learn the rules."
        )

        for principal_id in new_principal_ids:
            # Skip if agent artifact already exists (e.g., from checkpoint restore)
            if principal_id in self.world.artifacts.artifacts:
                artifact = self.world.artifacts.get(principal_id)
                if artifact and artifact.is_agent:
                    # Load agent from existing artifact
                    new_agent = Agent.from_artifact(
                        artifact,
                        store=self.world.artifacts,
                        log_dir=log_dir,
                        run_id=self.run_id,
                    )
                    new_agents.append(new_agent)
                    if self.verbose:
                        print(f"  [NEW AGENT] Loaded agent from artifact: {principal_id}")
                    continue

            # Create memory artifact for new agent
            memory_id = f"{principal_id}_memory"
            memory_artifact = create_memory_artifact(
                memory_id=memory_id,
                owner_id=principal_id,
            )
            self.world.artifacts.artifacts[memory_id] = memory_artifact

            # Create agent artifact with default config
            agent_config = {
                "llm_model": default_model,
                "system_prompt": default_system_prompt,
                "action_schema": "",
            }
            agent_artifact = create_agent_artifact(
                agent_id=principal_id,
                owner_id=principal_id,  # Self-owned
                agent_config=agent_config,
                memory_artifact_id=memory_id,
            )
            self.world.artifacts.artifacts[principal_id] = agent_artifact

            # Create agent from artifact
            new_agent = Agent.from_artifact(
                agent_artifact,
                store=self.world.artifacts,
                log_dir=log_dir,
                run_id=self.run_id,
            )
            new_agents.append(new_agent)

            if self.verbose:
                print(f"  [NEW AGENT] Created artifact-backed agent: {principal_id}")

        return new_agents

    def _handle_mint_tick(self) -> AuctionResult | None:
        """Handle mint auction tick.

        Calls the mint's on_tick method to:
        - Start new bidding windows
        - Resolve completed auctions
        - Distribute UBI from winning bids

        Returns:
            AuctionResult dict if an auction was resolved, None otherwise.
        """
        mint = self.world.genesis_artifacts.get("genesis_mint")
        if mint is None:
            return None

        # Check if mint has on_tick method (auction-based mint)
        if not hasattr(mint, "on_tick"):
            return None

        # Cast to GenesisMint since we verified it has on_tick
        result = cast(GenesisMint, mint).on_tick(self.world.tick)

        # Log auction result if there was one
        if result:
            self.world.logger.log(
                "mint_auction",
                {
                    "tick": self.world.tick,
                    "winner_id": result.get("winner_id"),
                    "artifact_id": result.get("artifact_id"),
                    "winning_bid": result.get("winning_bid"),
                    "price_paid": result.get("price_paid"),
                    "score": result.get("score"),
                    "scrip_minted": result.get("scrip_minted"),
                    "ubi_distributed": result.get("ubi_distributed"),
                    "error": result.get("error"),
                },
            )

        return result

    async def _think_agent(
        self,
        agent: Agent,
        tick_state: StateSummary,
    ) -> ThinkingResult:
        """Have a single agent think (async).

        Returns ThinkingResult with proposal or skip/error info.
        """
        compute_before: int = self.world.ledger.get_compute(agent.agent_id)

        # Check per-agent LLM budget (Plan #12)
        # If agent has llm_budget allocated but it's exhausted, skip thinking
        llm_budget = self.world.ledger.get_resource(agent.agent_id, "llm_budget")
        # Only enforce if the agent has ever had budget allocated (> 0 at genesis)
        # A budget of 0 from genesis means "no per-agent budget enforcement"
        has_budget_config = agent.agent_id in self.world.ledger.resources and \
            "llm_budget" in self.world.ledger.resources[agent.agent_id]
        if has_budget_config and llm_budget <= 0:
            return {
                "agent": agent,
                "skipped": True,
                "skip_reason": "insufficient_llm_budget",
                "thinking_cost": 0,
                "api_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            }

        try:
            proposal: AgentActionResult = await agent.propose_action_async(cast(dict[str, Any], tick_state))
        except Exception as e:
            return {
                "agent": agent,
                "error": f"LLM call failed: {e}",
                "skipped": True,
                "skip_reason": "llm_error",
            }

        # Extract token usage
        usage = proposal.get("usage") or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost": 0.0}
        api_cost: float = usage.get("cost", 0.0)
        input_tokens: int = usage.get("input_tokens", 0)
        output_tokens: int = usage.get("output_tokens", 0)

        # Deduct thinking cost
        rate_input, rate_output = self.engine.get_rates()
        thinking_result = self.world.ledger.deduct_thinking_cost(
            agent.agent_id, input_tokens, output_tokens, rate_input, rate_output
        )
        thinking_success: bool = thinking_result[0]
        thinking_cost: int = thinking_result[1]

        if not thinking_success:
            return {
                "agent": agent,
                "skipped": True,
                "skip_reason": f"insufficient_compute (cost {thinking_cost} > {compute_before})",
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        if "error" in proposal:
            return {
                "agent": agent,
                "skipped": True,
                "skip_reason": "intent_rejected",
                "error": proposal["error"],
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        return {
            "agent": agent,
            "proposal": proposal,
            "thinking_cost": thinking_cost,
            "api_cost": api_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "skipped": False,
        }

    def _process_thinking_results(
        self, results: list[ThinkingResult]
    ) -> list[ActionProposal]:
        """Process thinking results and return valid proposals."""
        proposals: list[ActionProposal] = []

        for result in results:
            agent = result["agent"]
            api_cost = result.get("api_cost", 0.0)
            # Track global and per-agent costs (Plan #12)
            self.engine.track_api_cost(api_cost, agent_id=agent.agent_id)

            # Deduct from agent's llm_budget resource if allocated (Plan #12)
            if api_cost > 0:
                self.world.ledger.spend_resource(
                    agent.agent_id, "llm_budget", api_cost
                )

            if result.get("skipped"):
                reason = result.get("skip_reason", "unknown")
                error = result.get("error", "")

                if "insufficient_compute" in reason:
                    self.world.logger.log(
                        "thinking_failed",
                        {
                            "tick": self.world.tick,
                            "principal_id": agent.agent_id,
                            "reason": "insufficient_compute",
                            "thinking_cost": result.get("thinking_cost", 0),
                            "tokens": {
                                "input": result.get("input_tokens", 0),
                                "output": result.get("output_tokens", 0),
                            },
                        },
                    )
                    if self.verbose:
                        print(f"    {agent.agent_id}: OUT OF COMPUTE ({reason})")
                elif "insufficient_llm_budget" in reason:
                    # Per-agent LLM budget exhausted (Plan #12)
                    self.world.logger.log(
                        "thinking_failed",
                        {
                            "tick": self.world.tick,
                            "principal_id": agent.agent_id,
                            "reason": "insufficient_llm_budget",
                            "llm_budget_remaining": self.world.ledger.get_resource(
                                agent.agent_id, "llm_budget"
                            ),
                        },
                    )
                    if self.verbose:
                        print(f"    {agent.agent_id}: OUT OF LLM BUDGET")
                elif "intent_rejected" in reason:
                    self.world.logger.log(
                        "intent_rejected",
                        {
                            "tick": self.world.tick,
                            "principal_id": agent.agent_id,
                            "error": error,
                        },
                    )
                    if self.verbose:
                        print(f"    {agent.agent_id}: REJECTED: {error[:100]}")
                else:
                    if self.verbose:
                        print(f"    {agent.agent_id}: SKIPPED ({reason})")
                continue

            # Valid proposal
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            thinking_cost = result.get("thinking_cost", 0)

            # Track LLM tokens for summary (Plan #60)
            if self._tick_collector:
                self._tick_collector.record_llm_tokens(input_tokens + output_tokens)

            # Extract thought process from proposal if available
            thought_process = result.get("proposal", {}).get("thought_process", "")

            self.world.logger.log(
                "thinking",
                {
                    "tick": self.world.tick,
                    "principal_id": agent.agent_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_cost": thinking_cost,
                    "compute_after": self.world.ledger.get_compute(agent.agent_id),
                    "thought_process": thought_process,
                },
            )

            if self.verbose:
                cost_str = f" (${api_cost:.4f}, total: ${self.engine.cumulative_api_cost:.4f})" if api_cost > 0 else ""
                print(f"    {agent.agent_id}: {input_tokens} in, {output_tokens} out -> {thinking_cost} compute{cost_str}")

            proposals.append({
                "agent": agent,
                "proposal": result["proposal"],
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
            })

        return proposals

    def _process_pool_results(
        self, tick_results: Any  # TickResults from pool
    ) -> list[ActionProposal]:
        """Process pool results and return valid proposals (Plan #53).

        Converts TickResults from WorkerPool.run_tick() to ActionProposal list
        for Phase 2 execution.
        """
        from .pool import TickResults

        proposals: list[ActionProposal] = []

        # Build agent lookup by ID
        agents_by_id = {agent.agent_id: agent for agent in self.agents}

        for result in tick_results.results:
            agent_id = result["agent_id"]
            agent = agents_by_id.get(agent_id)

            if agent is None:
                # Agent not found - could be a newly spawned agent
                if self.verbose:
                    print(f"    {agent_id}: NOT FOUND (skipping)")
                continue

            if not result.get("success", False):
                # Turn failed
                error = result.get("error", "unknown error")
                self.world.logger.log(
                    "pool_turn_failed",
                    {
                        "tick": self.world.tick,
                        "principal_id": agent_id,
                        "error": error,
                        "cpu_seconds": result.get("cpu_seconds", 0),
                        "memory_bytes": result.get("memory_bytes", 0),
                    },
                )
                if self.verbose:
                    print(f"    {agent_id}: FAILED: {error[:100]}")
                continue

            # Successful turn - extract action
            action_result = result.get("action", {})
            if not action_result:
                if self.verbose:
                    print(f"    {agent_id}: NO ACTION")
                continue

            # Handle error responses from propose_action
            if "error" in action_result and "action" not in action_result:
                self.world.logger.log(
                    "thinking_failed",
                    {
                        "tick": self.world.tick,
                        "principal_id": agent_id,
                        "reason": "propose_action_error",
                        "error": action_result.get("error", ""),
                    },
                )
                if self.verbose:
                    print(f"    {agent_id}: ERROR: {action_result.get('error', '')[:100]}")
                continue

            # Extract usage info for cost tracking
            usage = action_result.get("usage", {})
            api_cost = usage.get("cost", 0.0)
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            # Track costs
            self.engine.track_api_cost(api_cost, agent_id=agent_id)
            if api_cost > 0:
                self.world.ledger.spend_resource(agent_id, "llm_budget", api_cost)

            # Track LLM tokens for summary (Plan #60)
            if self._tick_collector:
                self._tick_collector.record_llm_tokens(input_tokens + output_tokens)

            # Log the thinking
            thought_process = action_result.get("thought_process", "")
            self.world.logger.log(
                "thinking",
                {
                    "tick": self.world.tick,
                    "principal_id": agent_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_cost": input_tokens + output_tokens,
                    "cpu_seconds": result.get("cpu_seconds", 0),
                    "memory_bytes": result.get("memory_bytes", 0),
                    "thought_process": thought_process,
                },
            )

            if self.verbose:
                cost_str = f" (${api_cost:.4f})" if api_cost > 0 else ""
                print(f"    {agent_id}: {input_tokens} in, {output_tokens} out{cost_str}")

            # Create proposal
            proposals.append({
                "agent": agent,
                "proposal": {
                    "action": action_result.get("action", {}),
                    "thought_process": thought_process,
                },
                "thinking_cost": input_tokens + output_tokens,
                "api_cost": api_cost,
            })

        return proposals

    def _execute_proposals(self, proposals: list[ActionProposal]) -> None:
        """Execute proposals in randomized order (Phase 2)."""
        if self.verbose and proposals:
            print(f"  [PHASE 2] Executing {len(proposals)} proposals in randomized order...")

        random.shuffle(proposals)

        for action_proposal in proposals:
            agent = action_proposal["agent"]
            proposal = action_proposal["proposal"]

            action_dict: dict[str, Any] = proposal["action"]
            # Plan #49: Pass thought_process as reasoning to narrow waist
            action_dict["reasoning"] = proposal.get("thought_process", "")
            intent: ActionIntent | str = parse_intent_from_json(
                agent.agent_id, json.dumps(action_dict)
            )

            if isinstance(intent, str):
                self.world.logger.log(
                    "intent_rejected",
                    {
                        "tick": self.world.tick,
                        "principal_id": agent.agent_id,
                        "error": intent,
                        "action_dict": action_dict,
                    },
                )
                if self.verbose:
                    print(f"    {agent.agent_id}: PARSE ERROR: {intent}")
                continue

            result = self.world.execute_action(intent)
            if self.verbose:
                status: str = "SUCCESS" if result.success else "FAILED"
                print(f"    {agent.agent_id}: {status}: {result.message}")

            raw_action_type = action_dict.get("action_type", "noop")

            # Track action for summary (Plan #60)
            if self._tick_collector:
                self._tick_collector.record_action(raw_action_type, success=result.success)

                # Track artifact creation
                if raw_action_type == "write_artifact" and result.success:
                    self._tick_collector.record_artifact_created()
                    artifact_id = action_dict.get("artifact_id", "unknown")
                    self._tick_collector.add_highlight(f"{agent.agent_id} created {artifact_id}")

                # Track scrip transfers from invoke results
                if raw_action_type == "invoke" and result.success and result.data:
                    transfer_amount = result.data.get("scrip_transferred", 0)
                    if transfer_amount > 0:
                        self._tick_collector.record_scrip_transfer(transfer_amount)
            valid_types = get_args(ActionType)
            action_type: ActionType = raw_action_type if raw_action_type in valid_types else "noop"
            agent.set_last_result(action_type, result.success, result.message, result.data)
            agent.record_action(action_type, json.dumps(action_dict), result.success)

            # Store artifact content in memory when successfully read
            if action_type == "read_artifact" and result.success and result.data:
                artifact_data = result.data.get("artifact", {})
                artifact_id = artifact_data.get("id", action_dict.get("artifact_id", "unknown"))
                content = artifact_data.get("content", "")
                # Truncate long content for memory storage
                if len(content) > 500:
                    content = content[:500] + "..."
                observation = f"Read {artifact_id}: {content}"
                agent.record_observation(observation)

    def _print_startup_info(self) -> None:
        """Print simulation startup information."""
        if not self.verbose:
            return

        print("=== Agent Ecology Simulation ===")
        print(f"Max ticks: {self.world.max_ticks}")
        print(f"Agents: {[a.agent_id for a in self.agents]}")
        print(
            f"Token rates: {self.engine.rate_input} compute/1K input, "
            f"{self.engine.rate_output} compute/1K output"
        )
        if self.engine.max_api_cost > 0:
            print(f"API budget: ${self.engine.max_api_cost:.2f}")
        print(f"Starting scrip: {self.world.ledger.get_all_scrip()}")
        print(f"Compute quota/tick: {self.world.rights_config.get('default_compute_quota', 50)}")
        print()

    def _print_final_summary(self) -> None:
        """Print simulation completion summary."""
        if not self.verbose:
            return

        print("=== Simulation Complete ===")
        print(f"Final tick: {self.world.tick}")
        print(f"Final scrip: {self.world.ledger.get_all_scrip()}")
        print(f"Total artifacts: {self.world.artifacts.count()}")
        print(f"Log file: {self.config['logging']['output_file']}")

    def pause(self) -> None:
        """Pause the simulation after the current tick completes."""
        self._paused = True
        self._pause_event.clear()
        if self.verbose:
            print("\n[PAUSED] Simulation paused. Use resume() to continue.")

    def resume(self) -> None:
        """Resume a paused simulation."""
        self._paused = False
        self._pause_event.set()
        if self.verbose:
            print("[RESUMED] Simulation resumed.")

    @property
    def is_paused(self) -> bool:
        """Check if the simulation is paused."""
        return self._paused

    @property
    def is_running(self) -> bool:
        """Check if the simulation is currently running."""
        return self._running

    def get_status(self) -> dict[str, Any]:
        """Get current simulation status for dashboard."""
        return {
            "running": self._running,
            "paused": self._paused,
            "tick": self.world.tick,
            "max_ticks": self.world.max_ticks,
            "agent_count": len(self.agents),
            "api_cost": self.engine.cumulative_api_cost,
            "max_api_cost": self.engine.max_api_cost,
        }

    async def run(
        self,
        max_ticks: int | None = None,
        duration: float | None = None,
    ) -> World:
        """Run the simulation asynchronously.

        Dispatches to either autonomous or tick-based mode based on config.

        Args:
            max_ticks: Maximum ticks to run (tick-based mode, optional)
            duration: Maximum seconds to run (autonomous mode, optional)

        Returns:
            The World instance after simulation completes.
        """
        SimulationRunner._active_runner = self
        self._running = True
        self._print_startup_info()

        try:
            if self.use_autonomous_loops:
                await self._run_autonomous(duration)
            else:
                await self._run_tick_based(max_ticks)
        finally:
            self._running = False
            SimulationRunner._active_runner = None

        self._print_final_summary()
        return self.world

    async def _run_tick_based(self, max_ticks: int | None = None) -> None:
        """Run simulation in tick-based mode (legacy).

        Uses parallel agent thinking via asyncio.gather().

        Args:
            max_ticks: Maximum ticks to run (optional, uses config value if not provided)
        """
        # Use provided max_ticks or fall back to world's max_ticks
        target_max_ticks = max_ticks or self.world.max_ticks

        while self.world.tick < target_max_ticks and self.world.advance_tick():
            # Wait if paused
            await self._pause_event.wait()

            if self.verbose:
                print(f"--- Tick {self.world.tick} ---")

            # Initialize tick summary collector (Plan #60)
            self._tick_collector = TickSummaryCollector()

            # Handle mint auction tick (resolve auctions, start bidding windows)
            mint_result = self._handle_mint_tick()
            if mint_result and self.verbose:
                if mint_result.get("winner_id"):
                    print(f"  [AUCTION] Winner: {mint_result['winner_id']}, "
                          f"paid {mint_result['price_paid']} scrip, "
                          f"score: {mint_result.get('score')}, "
                          f"minted: {mint_result['scrip_minted']}")
                elif mint_result.get("error"):
                    print(f"  [AUCTION] {mint_result['error']}")

            # Check for spawned principals
            new_agents = self._check_for_new_principals()
            self.agents.extend(new_agents)

            # Capture state snapshot (Two-Phase Commit: Observe)
            tick_state: StateSummary = self.world.get_state_summary()

            # Check budget before thinking
            if self.engine.is_budget_exhausted():
                checkpoint_file = save_checkpoint(
                    self.world, self.agents, self.engine.cumulative_api_cost,
                    self.config, "budget_exhausted"
                )
                if self.verbose:
                    print("\n=== BUDGET EXHAUSTED ===")
                    print(f"API cost: ${self.engine.cumulative_api_cost:.4f} >= ${self.engine.max_api_cost:.2f}")
                    print(f"Checkpoint saved to: {checkpoint_file}")
                self.world.logger.log(
                    "budget_pause",
                    {
                        "tick": self.world.tick,
                        "cumulative_api_cost": self.engine.cumulative_api_cost,
                        "max_api_cost": self.engine.max_api_cost,
                        "checkpoint_file": checkpoint_file,
                    },
                )
                return

            # PHASE 1: Parallel thinking
            if self.use_worker_pool and self._worker_pool is not None:
                # Pool mode: Use worker pool for process-isolated turns
                if self.verbose:
                    print(f"  [PHASE 1/POOL] {len(self.agents)} agents thinking via pool...")

                # Convert world state summary to dict format expected by pool
                # StateSummary is a TypedDict, so cast to dict[str, Any]
                world_state_dict: dict[str, Any] = dict(tick_state)

                # Run all agents through the pool
                agent_ids = [agent.agent_id for agent in self.agents]
                pool_results = self._worker_pool.run_tick(
                    agent_ids=agent_ids,
                    world_state=world_state_dict,
                )

                # Convert pool results to proposals
                proposals = self._process_pool_results(pool_results)
            else:
                # Traditional mode: Use asyncio.gather
                if self.verbose:
                    print(f"  [PHASE 1] {len(self.agents)} agents thinking in parallel...")

                thinking_tasks = [
                    self._think_agent(agent, tick_state)
                    for agent in self.agents
                ]
                thinking_results = await asyncio.gather(*thinking_tasks)

                # Process results
                proposals = self._process_thinking_results(thinking_results)

            # PHASE 2: Execute in random order
            self._execute_proposals(proposals)

            # Inter-tick delay
            if self.delay > 0:
                await asyncio.sleep(self.delay)

            # Periodic checkpoint saving
            checkpoint_interval: int = self.config.get("budget", {}).get("checkpoint_interval", 10)
            if checkpoint_interval > 0 and self.world.tick % checkpoint_interval == 0:
                checkpoint_file = save_checkpoint(
                    self.world, self.agents, self.engine.cumulative_api_cost,
                    self.config, f"periodic_tick_{self.world.tick}"
                )
                if self.verbose:
                    print(f"  [CHECKPOINT] Saved to {checkpoint_file}")

            # Log tick summary (Plan #60)
            if self._tick_collector and self.world.logger.summary_logger:
                summary = self._tick_collector.finalize(
                    tick=self.world.tick,
                    agents_active=len(proposals),  # Agents that produced valid proposals
                )
                self.world.logger.summary_logger.log_tick_summary(
                    tick=summary["tick"],
                    agents_active=summary["agents_active"],
                    actions_executed=summary["actions_executed"],
                    actions_by_type=summary["actions_by_type"],
                    total_llm_tokens=summary["total_llm_tokens"],
                    total_scrip_transferred=summary["total_scrip_transferred"],
                    artifacts_created=summary["artifacts_created"],
                    errors=summary["errors"],
                    highlights=summary["highlights"],
                )

            if self.verbose:
                print(f"  End of tick. Scrip: {self.world.ledger.get_all_scrip()}")
                print()

        # Save final checkpoint if configured
        checkpoint_on_end: bool = self.config.get("budget", {}).get("checkpoint_on_end", True)
        if checkpoint_on_end:
            checkpoint_file = save_checkpoint(
                self.world, self.agents, self.engine.cumulative_api_cost,
                self.config, "simulation_complete"
            )
            if self.verbose:
                print(f"\n=== SIMULATION COMPLETE ===")
                print(f"Checkpoint saved to: {checkpoint_file}")

    async def _run_autonomous(self, duration: float | None = None) -> None:
        """Run simulation in autonomous mode with independent agent loops.

        Agents run continuously in their own loops, resource-gated by RateTracker.

        Args:
            duration: Maximum seconds to run (optional, runs until stopped if not provided)
        """
        if not self.world.loop_manager:
            raise RuntimeError(
                "loop_manager not initialized. Ensure use_autonomous_loops=True in config "
                "and rate_limiting.enabled=True"
            )

        if self.verbose:
            print(f"  [AUTONOMOUS] Creating loops for {len(self.agents)} agents...")

        # Create loops for all agents
        for agent in self.agents:
            self._create_agent_loop(agent)

        if self.verbose:
            print(f"  [AUTONOMOUS] Starting all agent loops...")

        # Start all loops
        await self.world.loop_manager.start_all()

        try:
            if duration is not None:
                # Run for specified duration
                if self.verbose:
                    print(f"  [AUTONOMOUS] Running for {duration} seconds...")
                await asyncio.sleep(duration)
            else:
                # Run until all agents stop or interrupted
                if self.verbose:
                    print(f"  [AUTONOMOUS] Running until all agents stop...")
                while self.world.loop_manager.running_count > 0:
                    # Wait if paused
                    await self._pause_event.wait()
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            if self.verbose:
                print(f"  [AUTONOMOUS] Cancelled, stopping loops...")
        finally:
            # Graceful shutdown
            await self.world.loop_manager.stop_all()
            if self.verbose:
                print(f"  [AUTONOMOUS] All loops stopped.")

    def _create_agent_loop(self, agent: Agent) -> None:
        """Create an agent loop with appropriate config and callbacks.

        Args:
            agent: The agent to create a loop for.
        """
        if not self.world.loop_manager:
            raise RuntimeError("loop_manager not initialized")

        # Get loop config from execution config
        execution_config = self.config.get("execution", {})
        loop_config_dict = execution_config.get("agent_loop", {})

        config = AgentLoopConfig(
            min_loop_delay=loop_config_dict.get("min_loop_delay", 0.1),
            max_loop_delay=loop_config_dict.get("max_loop_delay", 10.0),
            resource_check_interval=loop_config_dict.get("resource_check_interval", 1.0),
            max_consecutive_errors=loop_config_dict.get("max_consecutive_errors", 5),
            resources_to_check=loop_config_dict.get("resources_to_check", ["llm_calls"]),
        )

        # Create the loop using callbacks that adapt the Agent to AgentProtocol
        # Note: lambdas with default args to capture agent reference
        self.world.loop_manager.create_loop(
            agent_id=agent.agent_id,
            decide_action=lambda a=agent: self._agent_decide_action(a),  # type: ignore[misc]
            execute_action=lambda action, a=agent: self._agent_execute_action(a, action),  # type: ignore[misc]
            config=config,
            is_alive=lambda a=agent: getattr(a, "alive", True),  # type: ignore[misc]
        )

    async def _agent_decide_action(self, agent: Agent) -> dict[str, Any] | None:
        """Decide callback for agent loop.

        Calls the agent's propose_action_async and returns the action dict.

        Args:
            agent: The agent making the decision.

        Returns:
            Action dict or None if agent chose to skip.
        """
        # Get current world state
        tick_state = self.world.get_state_summary()

        # Call the agent's propose method
        result = await agent.propose_action_async(cast(dict[str, Any], tick_state))

        # Track API cost
        usage = result.get("usage") or {"cost": 0.0, "input_tokens": 0, "output_tokens": 0}
        api_cost = usage.get("cost", 0.0)
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        self.engine.track_api_cost(api_cost)

        # Log thinking event for dashboard
        thought_process = result.get("thought_process", "")
        self.world.logger.log(
            "thinking",
            {
                "tick": self.world.tick,
                "principal_id": agent.agent_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_cost": 0,
                "thought_process": thought_process,
            },
        )

        # Check for error
        if "error" in result:
            return None

        # Return the action dict
        return result.get("action")

    async def _agent_execute_action(
        self, agent: Agent, action: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute callback for agent loop.

        Parses the action and executes it via the world.

        Args:
            agent: The agent executing the action.
            action: The action dict to execute.

        Returns:
            Result dict with success flag and other info.
        """
        # Parse the action intent
        intent = parse_intent_from_json(agent.agent_id, json.dumps(action))

        if isinstance(intent, str):
            # Parse error
            return {"success": False, "error": intent}

        # Execute via world
        result = self.world.execute_action(intent)

        # Log action event for dashboard
        self.world.logger.log(
            "action",
            {
                "tick": self.world.tick,
                "agent_id": agent.agent_id,
                "action_type": action.get("action_type", "noop"),
                "artifact_id": action.get("artifact_id", ""),
                "method": action.get("method", ""),
                "success": result.success,
                "message": result.message,
            },
        )

        # Record the action for the agent
        action_type = action.get("action_type", "noop")
        agent.set_last_result(action_type, result.success, result.message, result.data)
        agent.record_action(action_type, json.dumps(action), result.success)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }

    async def shutdown(self, timeout: float | None = None) -> None:
        """Gracefully stop the simulation.

        Stops all agent loops if in autonomous mode.
        Stops worker pool if in pool mode.

        Args:
            timeout: Maximum seconds to wait for loops to stop.
                     Defaults to config timeouts.simulation_shutdown.
        """
        if timeout is None:
            timeout = get_validated_config().timeouts.simulation_shutdown
        if self.use_autonomous_loops and self.world.loop_manager:
            await self.world.loop_manager.stop_all(timeout=timeout)
        if self._worker_pool is not None:
            self._worker_pool.stop()
            self._worker_pool = None
        self._running = False

    def run_sync(self) -> World:
        """Run the simulation synchronously.

        Wrapper around run() using asyncio.run().

        Returns:
            The World instance after simulation completes.
        """
        return asyncio.run(self.run())
