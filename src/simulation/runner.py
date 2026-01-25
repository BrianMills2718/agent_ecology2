"""SimulationRunner - Main orchestrator for agent ecology simulation.

Handles:
- World and agent initialization
- Checkpoint restore
- Autonomous agent loops with time-based rate limiting
- Budget tracking
- Dynamic agent creation
"""

from __future__ import annotations

import asyncio
import json
import random
import time
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
from ..world.logger import SummaryCollector
from ..config import get_validated_config

from .types import (
    PrincipalConfig,
    CheckpointData,
    ActionProposal,
    ThinkingResult,
    ErrorStats,
)
from .checkpoint import save_checkpoint, load_checkpoint
from .agent_loop import AgentLoopManager, AgentLoopConfig
from .pool import WorkerPool, PoolConfig
from ..agents.state_store import AgentStateStore
from ..agents.reflex import ReflexExecutor, build_reflex_context


def _derive_provider(model: str) -> str:
    """Derive LLM provider from model name using LiteLLM's model registry.

    Uses litellm.get_model_info() for authoritative provider detection,
    with string-matching fallback for unknown models.
    """
    # Try LiteLLM's model registry first (authoritative source)
    try:
        import litellm
        info = litellm.get_model_info(model)
        if info and "litellm_provider" in info:
            return str(info["litellm_provider"])
    except Exception:  # exception-ok: litellm may not have model info
        pass  # Fall through to heuristic

    # Fallback: string matching for models not in LiteLLM registry
    model_lower = model.lower()
    if "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    elif "gpt" in model_lower or "openai" in model_lower:
        return "openai"
    elif "gemini" in model_lower or "google" in model_lower:
        return "google"
    elif "llama" in model_lower or "meta" in model_lower:
        return "meta"
    return "unknown"


class SimulationRunner:
    """Orchestrates the agent ecology simulation.

    Encapsulates all simulation state and logic:
    - World, agents, and physics engine
    - Autonomous agent loops with time-based rate limiting
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
            delay: Rate limit delay (defaults to config value)
            checkpoint: Checkpoint data to resume from (optional)
        """
        self.config = config
        self.max_agents = max_agents
        self.verbose = verbose
        self.delay = delay if delay is not None else config.get("llm", {}).get("rate_limit_delay", 15.0)
        self.checkpoint = checkpoint

        # Generate run ID for log organization
        self.run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

        # Error tracking (Plan #129)
        self.error_stats = ErrorStats()

        # Initialize engine
        self.engine = SimulationEngine.from_config(config)
        if checkpoint:
            self.engine.reset_budget(checkpoint["cumulative_api_cost"])

        # Runtime timeout backstop (0 = unlimited)
        budget_config = config.get("budget", {})
        self.max_runtime_seconds: int = budget_config.get("max_runtime_seconds", 3600)
        self._run_start_time: float | None = None  # Set when run() is called

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

        # Wire up cost tracking callbacks for genesis embedder (Plan #153)
        self._wire_embedder_cost_callbacks()

        # Initialize agents
        self.agents = self._create_agents(agent_configs)

        # Autonomous loop support (INT-003)
        # Plan #102: Tick-based mode removed - always use autonomous loops
        self.use_autonomous_loops = True

        # Create AgentLoopManager (always needed in autonomous mode)
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
        self._summary_collector: SummaryCollector | None = None

    def _wire_embedder_cost_callbacks(self) -> None:
        """Wire up cost tracking callbacks for genesis artifacts.

        This integrates all genesis artifact API costs into the global budget
        tracking system, including:
        - Embedder: embedding API calls
        - Mint (genesis): scorer LLM calls during artifact evaluation
        - MintAuction (kernel): scorer LLM calls during auction resolution
        """
        from ..world.genesis.embedder import GenesisEmbedder
        from ..world.genesis.mint import GenesisMint

        # Wire up embedder callbacks
        embedder = self.world.genesis_artifacts.get("genesis_embedder")
        if embedder is not None and isinstance(embedder, GenesisEmbedder):
            embedder.set_cost_callbacks(
                is_budget_exhausted=self.engine.is_budget_exhausted,
                track_api_cost=lambda cost: self.engine.track_api_cost(cost),
            )

        # Wire up genesis mint scorer callbacks
        mint = self.world.genesis_artifacts.get("genesis_mint")
        if mint is not None and isinstance(mint, GenesisMint):
            mint.set_cost_callbacks(
                is_budget_exhausted=self.engine.is_budget_exhausted,
                track_api_cost=lambda cost: self.engine.track_api_cost(cost),
            )

        # Wire up kernel mint auction scorer callbacks
        self.world.mint_auction.set_cost_callbacks(
            is_budget_exhausted=self.engine.is_budget_exhausted,
            track_api_cost=lambda cost: self.engine.track_api_cost(cost),
        )

    def _restore_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Restore world state from checkpoint.

        Properly restores agent artifacts with their principal capabilities
        (has_standing, can_execute, memory_artifact_id) for unified ontology.
        """
        # Restore event counter from checkpoint
        # In autonomous mode this is used for event ordering in logs, not execution control
        self.world.event_number = checkpoint.get("event_number", checkpoint.get("tick", 0))

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
                created_by=artifact_data.get("created_by", "system"),
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
            print(f"Event counter: {checkpoint.get('event_number', checkpoint.get('tick', 0))}")
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

        # Load prior learnings if cross-run learning enabled (Plan #186)
        prior_states = self._load_prior_learnings()
        if prior_states:
            learning_config = self.config.get("learning", {}).get("cross_run", {})
            for agent in agents:
                if agent.agent_id in prior_states:
                    prior_state = prior_states[agent.agent_id]
                    # Only restore working_memory by default
                    if learning_config.get("load_working_memory", True):
                        wm = prior_state.get("working_memory")
                        if wm:
                            agent._working_memory = wm
                            print(f"  Restored working_memory for {agent.agent_id}")

        return agents


    def _load_prior_learnings(self) -> dict[str, dict[str, Any]]:
        """Load agent states from previous run checkpoint (Plan #186).

        Enables cross-run learning by restoring working_memory from
        a prior simulation. Only loads working_memory by default,
        not per-run state like action_history.

        Returns:
            Dict mapping agent_id -> agent_state from prior checkpoint.
        """
        learning_config = self.config.get("learning", {}).get("cross_run", {})

        if not learning_config.get("enabled", False):
            return {}

        checkpoint_path = learning_config.get("prior_checkpoint")
        if not checkpoint_path and learning_config.get("auto_discover", True):
            checkpoint_path = self._find_latest_checkpoint()

        if not checkpoint_path:
            return {}

        import os
        if not os.path.exists(checkpoint_path):
            print(f"Cross-run learning: checkpoint not found at {checkpoint_path}")
            return {}

        checkpoint = load_checkpoint(checkpoint_path)
        if not checkpoint:
            return {}

        agent_states = checkpoint.get("agent_states", {})
        print(f"Cross-run learning: loaded states for {len(agent_states)} agents from {checkpoint_path}")
        return agent_states

    def _find_latest_checkpoint(self) -> str | None:
        """Find the most recent checkpoint file in logs directory.

        Auto-discovers checkpoints for cross-run learning when
        prior_checkpoint is not explicitly specified.

        Returns:
            Path to latest checkpoint, or None if not found.
        """
        import os
        import glob

        # Look for checkpoint.json in common locations
        search_paths = [
            "checkpoint.json",  # Default location
            "logs/checkpoint.json",
            "*.checkpoint.json",
        ]

        candidates = []
        for pattern in search_paths:
            candidates.extend(glob.glob(pattern))

        if not candidates:
            return None

        # Return most recently modified
        candidates.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        return candidates[0]

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
                    # Plan #190: Spawned agents are not genesis agents
                    new_agent = Agent.from_artifact(
                        artifact,
                        store=self.world.artifacts,
                        log_dir=log_dir,
                        run_id=self.run_id,
                        is_genesis=False,
                    )
                    new_agents.append(new_agent)
                    if self.verbose:
                        print(f"  [NEW AGENT] Loaded agent from artifact: {principal_id}")
                    continue

            # Create memory artifact for new agent
            memory_id = f"{principal_id}_memory"
            memory_artifact = create_memory_artifact(
                memory_id=memory_id,
                created_by=principal_id,
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
                created_by=principal_id,  # Self-created
                agent_config=agent_config,
                memory_artifact_id=memory_id,
            )
            self.world.artifacts.artifacts[principal_id] = agent_artifact

            # Create agent from artifact
            # Plan #190: Spawned agents are not genesis agents
            new_agent = Agent.from_artifact(
                agent_artifact,
                store=self.world.artifacts,
                log_dir=log_dir,
                run_id=self.run_id,
                is_genesis=False,
            )
            new_agents.append(new_agent)

            if self.verbose:
                print(f"  [NEW AGENT] Created artifact-backed agent: {principal_id}")

        return new_agents

    def _handle_mint_update(self) -> AuctionResult | None:
        """Handle mint auction update (Plan #83 - time-based).

        Calls the mint's update method to check if auctions need to:
        - Start new bidding windows
        - Resolve completed auctions
        - Distribute UBI from winning bids

        Returns:
            AuctionResult dict if an auction was resolved, None otherwise.
        """
        mint = self.world.genesis_artifacts.get("genesis_mint")
        if mint is None:
            return None

        # Check if mint has update method (time-based mint)
        if not hasattr(mint, "update"):
            return None

        # Cast to GenesisMint since we verified it has update
        result = cast(GenesisMint, mint).update()

        self._log_mint_result(result)
        return result

    def _log_mint_result(self, result: AuctionResult | None) -> None:
        """Log a mint auction result if one occurred."""
        if result:
            self.world.logger.log(
                "mint_auction",
                {
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

    async def _think_agent(
        self,
        agent: Agent,
        current_state: StateSummary,
    ) -> ThinkingResult:
        """Have a single agent think (async).

        Returns ThinkingResult with proposal or skip/error info.
        """
        llm_tokens_before: int = self.world.ledger.get_llm_tokens(agent.agent_id)

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
            proposal: AgentActionResult = await agent.propose_action_async(cast(dict[str, Any], current_state))
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
                "skip_reason": f"insufficient_compute (cost {thinking_cost} > {llm_tokens_before})",
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

            # Deduct from agent's llm_budget resource if allocated (Plan #12, #153)
            if api_cost > 0:
                self.world.ledger.deduct_llm_cost(agent.agent_id, api_cost)

            if result.get("skipped"):
                reason = result.get("skip_reason", "unknown")
                error = result.get("error", "")

                # Record error for summary (Plan #129)
                if "llm_error" in reason and error:
                    self._record_error("llm_error", agent.agent_id, error)
                elif "intent_rejected" in reason and error:
                    self._record_error("intent_rejected", agent.agent_id, error)

                if "insufficient_compute" in reason:
                    self.world.logger.log(
                        "thinking_failed",
                        {
                            "event_number": self.world.event_number,
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
                            "event_number": self.world.event_number,
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
                            "event_number": self.world.event_number,
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
            if self._summary_collector:
                self._summary_collector.record_llm_tokens(input_tokens + output_tokens)

            # Extract reasoning from proposal if available (Plan #132: standardized field)
            proposal_data = result.get("proposal", {})
            reasoning = proposal_data.get("reasoning", "")

            # Build thinking event data with full observability
            model = agent.llm_model
            provider = _derive_provider(model)

            thinking_data: dict[str, Any] = {
                "event_number": self.world.event_number,
                "principal_id": agent.agent_id,
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "api_cost": api_cost,
                "thinking_cost": thinking_cost,
                "llm_tokens_after": self.world.ledger.get_llm_tokens(agent.agent_id),
                "llm_budget_after": self.world.ledger.get_llm_budget(agent.agent_id),  # Plan #153
                "reasoning": reasoning,
            }

            self.world.logger.log("thinking", thinking_data)

            if self.verbose:
                budget_remaining = self.world.ledger.get_llm_budget(agent.agent_id)
                cost_str = f" (${api_cost:.4f}, budget: ${budget_remaining:.4f})" if api_cost > 0 else ""
                print(f"    {agent.agent_id}: {input_tokens} in, {output_tokens} out{cost_str}")

            proposals.append({
                "agent": agent,
                "proposal": result["proposal"],
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
            })

        return proposals

    def _process_pool_results(
        self, round_results: Any  # RoundResults from pool
    ) -> list[ActionProposal]:
        """Process pool results and return valid proposals (Plan #53).

        Converts RoundResults from WorkerPool.run_round() to ActionProposal list
        for Phase 2 execution.
        """
        from .pool import RoundResults

        proposals: list[ActionProposal] = []

        # Build agent lookup by ID
        agents_by_id = {agent.agent_id: agent for agent in self.agents}

        for result in round_results.results:
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
                self._record_error("pool_turn_failed", agent_id, error)  # Plan #129
                self.world.logger.log(
                    "pool_turn_failed",
                    {
                        "event_number": self.world.event_number,
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
                error_msg = action_result.get("error", "")
                self._record_error("propose_action_error", agent_id, error_msg)  # Plan #129
                self.world.logger.log(
                    "thinking_failed",
                    {
                        "event_number": self.world.event_number,
                        "principal_id": agent_id,
                        "reason": "propose_action_error",
                        "error": error_msg,
                    },
                )
                if self.verbose:
                    print(f"    {agent_id}: ERROR: {error_msg[:100]}")
                continue

            # Extract usage info for cost tracking
            usage = action_result.get("usage", {})
            api_cost = usage.get("cost", 0.0)
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            # Track costs (Plan #153: use deduct_llm_cost)
            self.engine.track_api_cost(api_cost, agent_id=agent_id)
            if api_cost > 0:
                self.world.ledger.deduct_llm_cost(agent_id, api_cost)

            # Track LLM tokens for summary (Plan #60)
            if self._summary_collector:
                self._summary_collector.record_llm_tokens(input_tokens + output_tokens)

            # Log the thinking (Plan #132: standardized reasoning field)
            reasoning = action_result.get("reasoning", "")
            model = action_result.get("model", "unknown")
            provider = _derive_provider(model)

            thinking_data: dict[str, Any] = {
                "event_number": self.world.event_number,
                "principal_id": agent_id,
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "api_cost": api_cost,
                "thinking_cost": input_tokens + output_tokens,
                "llm_budget_after": self.world.ledger.get_llm_budget(agent_id),  # Plan #153
                "cpu_seconds": result.get("cpu_seconds", 0),
                "memory_bytes": result.get("memory_bytes", 0),
                "reasoning": reasoning,
            }

            self.world.logger.log("thinking", thinking_data)

            if self.verbose:
                budget_remaining = self.world.ledger.get_llm_budget(agent_id)
                cost_str = f" (${api_cost:.4f}, budget: ${budget_remaining:.4f})" if api_cost > 0 else ""
                print(f"    {agent_id}: {input_tokens} in, {output_tokens} out{cost_str}")

            # Create proposal (Plan #132: standardized reasoning field)
            proposal_dict: AgentActionResult = {
                "action": action_result.get("action", {}),
                "reasoning": reasoning,
            }

            proposals.append({
                "agent": agent,
                "proposal": proposal_dict,
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
            # Plan #49/#132: Pass reasoning to narrow waist
            action_dict["reasoning"] = proposal.get("reasoning", "")
            intent: ActionIntent | str = parse_intent_from_json(
                agent.agent_id, json.dumps(action_dict)
            )

            if isinstance(intent, str):
                self.world.logger.log(
                    "intent_rejected",
                    {
                        "event_number": self.world.event_number,
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
            if self._summary_collector:
                self._summary_collector.record_action(raw_action_type, success=result.success)

                # Track artifact creation
                if raw_action_type == "write_artifact" and result.success:
                    self._summary_collector.record_artifact_created()
                    artifact_id = action_dict.get("artifact_id", "unknown")
                    self._summary_collector.add_highlight(f"{agent.agent_id} created {artifact_id}")

                # Track scrip transfers from invoke results
                if raw_action_type == "invoke" and result.success and result.data:
                    transfer_amount = result.data.get("scrip_transferred", 0)
                    if transfer_amount > 0:
                        self._summary_collector.record_scrip_transfer(transfer_amount)
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
        print("Mode: Autonomous (agents run independently)")
        print(f"Agents: {[a.agent_id for a in self.agents]}")

        # Show LLM budget (the real depletable resource)
        if self.engine.max_api_cost > 0:
            print(f"LLM budget: ${self.engine.max_api_cost:.2f}")

        # Show runtime limit (hard backstop)
        if self.max_runtime_seconds > 0:
            hours = self.max_runtime_seconds // 3600
            mins = (self.max_runtime_seconds % 3600) // 60
            if hours > 0:
                print(f"Runtime limit: {hours}h {mins}m")
            else:
                print(f"Runtime limit: {mins}m")

        # Show rate limit info if rate limiting is enabled
        rate_config = self.config.get("rate_limiting", {})
        if rate_config.get("enabled", False):
            window = rate_config.get("window_seconds", 60.0)
            llm_limit = rate_config.get("resources", {}).get("llm_tokens", {}).get("max_per_window", 0)
            if llm_limit > 0 and llm_limit < 1_000_000_000:  # Don't show if "unlimited"
                print(f"LLM rate limit: {llm_limit:,} tokens/{window}s window")

        print(f"Starting scrip: {self.world.ledger.get_all_scrip()}")
        print()

    def _record_error(
        self,
        error_type: str,
        agent_id: str,
        message: str,
    ) -> None:
        """Record an error for the error summary (Plan #129).

        Args:
            error_type: Category of error (e.g., 'llm_error', 'intent_rejected')
            agent_id: The agent that encountered the error
            message: The error message
        """
        # Import here to avoid circular import
        from run import get_error_suggestion

        suggestion = get_error_suggestion(message)
        self.error_stats.record_error(error_type, agent_id, message, suggestion)

    def _print_error_summary(self) -> None:
        """Print error summary at end of simulation (Plan #129)."""
        stats = self.error_stats
        if stats.total_errors == 0:
            return

        print("\n" + "=" * 60)
        print("SIMULATION ERROR SUMMARY")
        print("=" * 60)
        print(f"Total errors: {stats.total_errors}")

        if stats.by_type:
            print("\nBy type:")
            for error_type, count in sorted(
                stats.by_type.items(), key=lambda x: -x[1]
            ):
                pct = count * 100 / stats.total_errors
                print(f"  {error_type}: {count} ({pct:.0f}%)")

        if stats.by_agent:
            print("\nBy agent:")
            for agent_id, count in sorted(
                stats.by_agent.items(), key=lambda x: -x[1]
            )[:5]:  # Top 5 agents
                print(f"  {agent_id}: {count}")

        if stats.recent_errors:
            print("\nMost recent error:")
            recent = stats.recent_errors[-1]
            print(f"  Type: {recent.error_type}")
            print(f"  Agent: {recent.agent_id}")
            print(f"  Message: {recent.message[:200]}")
            if recent.suggestion:
                print(f"  Suggestion: {recent.suggestion}")

        print("=" * 60)

    def _print_final_summary(self) -> None:
        """Print simulation completion summary."""
        if not self.verbose:
            return

        # Count actual events from the log file
        log_path = self.world.logger.output_path
        try:
            with open(log_path) as f:
                event_count = sum(1 for _ in f)
        except (FileNotFoundError, IOError):
            event_count = 0

        print("=== Simulation Complete ===")
        print(f"Events logged: {event_count}")
        print(f"Final scrip: {self.world.ledger.get_all_scrip()}")
        print(f"Total artifacts: {self.world.artifacts.count()}")
        print(f"Log file: {log_path}")

        # Print error summary (Plan #129)
        self._print_error_summary()

    def pause(self) -> None:
        """Pause the simulation after the current action completes."""
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
            "event_count": self.world.event_number,  # Monotonic event counter
            "agent_count": len(self.agents),
            "api_cost": self.engine.cumulative_api_cost,
            "max_api_cost": self.engine.max_api_cost,
            "max_runtime_seconds": self.max_runtime_seconds,
        }

    def is_runtime_exceeded(self) -> bool:
        """Check if maximum runtime has been exceeded.

        Returns:
            True if max_runtime_seconds > 0 and elapsed time exceeds it.
        """
        if self.max_runtime_seconds <= 0:
            return False  # Unlimited runtime
        if self._run_start_time is None:
            return False  # Run hasn't started yet
        elapsed = time.time() - self._run_start_time
        return elapsed >= self.max_runtime_seconds

    async def run(
        self,
        duration: float | None = None,
    ) -> World:
        """Run the simulation asynchronously.

        Runs in autonomous mode where agents operate independently with
        time-based rate limiting. Continuous execution is the only mode.

        Args:
            duration: Maximum seconds to run (optional, runs until stopped if not provided)

        Returns:
            The World instance after simulation completes.
        """
        SimulationRunner._active_runner = self
        self._running = True
        self._run_start_time = time.time()  # Track runtime for timeout
        self._print_startup_info()

        try:
            await self._run_autonomous(duration)
        finally:
            self._running = False
            SimulationRunner._active_runner = None

        self._print_final_summary()
        return self.world

    async def _run_autonomous(self, duration: float | None = None) -> None:
        """Run simulation in autonomous mode with independent agent loops.

        Agents run continuously in their own loops, resource-gated by RateTracker.
        Plan #83: Mint auctions run on wall-clock time via periodic update().

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

        # Plan #83: Start mint update background task
        mint_task = asyncio.create_task(self._mint_update_loop())

        try:
            if duration is not None:
                # Plan #157: Tell world about duration for time awareness
                self.world.set_simulation_duration(duration)
                # Run for specified duration, checking budget periodically
                if self.verbose:
                    print(f"  [AUTONOMOUS] Running for {duration} seconds...")
                start_time = asyncio.get_event_loop().time()
                while True:
                    # Check budget exhaustion (critical fix for runaway costs)
                    if self.engine.is_budget_exhausted():
                        if self.verbose:
                            print(f"  [AUTONOMOUS] Budget exhausted "
                                  f"(${self.engine.cumulative_api_cost:.2f} >= "
                                  f"${self.engine.max_api_cost:.2f})")
                        break
                    # Check runtime timeout (hard backstop)
                    if self.is_runtime_exceeded():
                        if self.verbose:
                            print(f"  [AUTONOMOUS] Runtime timeout "
                                  f"({self.max_runtime_seconds}s exceeded)")
                        break
                    # Check if duration exceeded
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= duration:
                        break
                    # Sleep for short interval to allow budget checks
                    await asyncio.sleep(min(0.5, duration - elapsed))
            else:
                # Run until all agents stop, budget exhausted, timeout, or interrupted
                if self.verbose:
                    print(f"  [AUTONOMOUS] Running until all agents stop...")
                while self.world.loop_manager.running_count > 0:
                    # Check budget exhaustion (critical fix for runaway costs)
                    if self.engine.is_budget_exhausted():
                        if self.verbose:
                            print(f"  [AUTONOMOUS] Budget exhausted "
                                  f"(${self.engine.cumulative_api_cost:.2f} >= "
                                  f"${self.engine.max_api_cost:.2f})")
                        break
                    # Check runtime timeout (hard backstop)
                    if self.is_runtime_exceeded():
                        if self.verbose:
                            print(f"  [AUTONOMOUS] Runtime timeout "
                                  f"({self.max_runtime_seconds}s exceeded)")
                        break
                    # Wait if paused
                    await self._pause_event.wait()
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            if self.verbose:
                print(f"  [AUTONOMOUS] Cancelled, stopping loops...")
        finally:
            # Stop mint update task
            mint_task.cancel()
            try:
                await mint_task
            except asyncio.CancelledError:
                pass

            # Graceful shutdown
            await self.world.loop_manager.stop_all()
            if self.verbose:
                print(f"  [AUTONOMOUS] All loops stopped.")

    async def _mint_update_loop(self) -> None:
        """Background task to periodically update mint auctions (Plan #83).

        Runs continuously, calling mint.update() every second to check if
        any auction phase transitions are needed.
        """
        try:
            while True:
                # Skip mint updates if budget exhausted (prevents scorer LLM calls)
                if self.engine.is_budget_exhausted():
                    await asyncio.sleep(1.0)
                    continue

                # Check for auction state changes
                result = self._handle_mint_update()

                # Log if an auction was resolved
                if result and self.verbose:
                    if result.get("winner_id"):
                        print(f"  [AUCTION] Winner: {result['winner_id']}, "
                              f"paid {result['price_paid']} scrip, "
                              f"score: {result.get('score')}, "
                              f"minted: {result['scrip_minted']}")
                    elif result.get("error"):
                        print(f"  [AUCTION] {result['error']}")

                # Poll interval - check once per second
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            # Normal shutdown
            pass

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
        If agent has a reflex, tries reflex first (Plan #143).

        Args:
            agent: The agent making the decision.

        Returns:
            Action dict or None if agent chose to skip.
        """
        # Check global budget before making LLM call (defense in depth)
        if self.engine.is_budget_exhausted():
            return None  # Skip LLM call, budget exceeded

        # Reload config from artifact before each decision (Plan #8)
        # This allows config changes made by other agents to take effect
        agent.reload_from_artifact()

        # Get current world state
        current_state = self.world.get_state_summary()

        # Plan #143: Check reflex before LLM
        reflex_action = await self._try_reflex(agent)
        if reflex_action is not None:
            return reflex_action

        # Call the agent's propose method
        result = await agent.propose_action_async(cast(dict[str, Any], current_state))

        # Check for error FIRST - don't log thinking events for failed LLM calls (Plan #121)
        if "error" in result:
            # Log thinking_failed event instead of empty thinking event
            self.world.logger.log(
                "thinking_failed",
                {
                    "event_number": self.world.event_number,
                    "principal_id": agent.agent_id,
                    "reason": "llm_call_failed",
                    "error": result.get("error", ""),
                },
            )
            return None

        # Track API cost (only for successful calls)
        usage = result.get("usage") or {"cost": 0.0, "input_tokens": 0, "output_tokens": 0}
        api_cost = usage.get("cost", 0.0)
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        self.engine.track_api_cost(api_cost)

        # Log thinking event for dashboard (Plan #132: standardized reasoning field)
        reasoning = result.get("reasoning", "")

        # Plan #121: Warn if reasoning is empty despite successful LLM call
        if not reasoning.strip():
            import logging
            logging.getLogger(__name__).warning(
                f"Empty reasoning for {agent.agent_id} despite successful LLM call "
                f"(tokens: {input_tokens}/{output_tokens})"
            )

        model = result.get("model", agent.llm_model)
        provider = _derive_provider(model)

        thinking_data: dict[str, Any] = {
            "event_number": self.world.event_number,
            "principal_id": agent.agent_id,
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "api_cost": api_cost,
            "thinking_cost": 0,
            "reasoning": reasoning,
        }

        self.world.logger.log("thinking", thinking_data)

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

        # Record the action for the agent
        action_type = action.get("action_type", "noop")
        agent.set_last_result(action_type, result.success, result.message, result.data)
        agent.record_action(action_type, json.dumps(action), result.success)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }

    async def _try_reflex(self, agent: Agent) -> dict[str, Any] | None:
        """Try to execute agent's reflex before LLM (Plan #143).

        If agent has a reflex_artifact_id, loads the reflex code from the
        artifact and executes it. If the reflex fires (returns an action),
        returns it to skip the LLM call.

        Args:
            agent: The agent to check reflex for.

        Returns:
            Action dict if reflex fired, None to fall through to LLM.
        """
        # Check if agent has a reflex
        if not agent.has_reflex:
            return None

        reflex_artifact_id = agent.reflex_artifact_id
        if not reflex_artifact_id:
            return None

        # Load reflex artifact
        reflex_artifact = self.world.artifacts.get(reflex_artifact_id)
        if not reflex_artifact:
            # Log missing reflex artifact (soft reference)
            self.world.logger.log(
                "reflex_error",
                {
                    "event_number": self.world.event_number,
                    "principal_id": agent.agent_id,
                    "reflex_artifact_id": reflex_artifact_id,
                    "error": "reflex artifact not found",
                },
            )
            return None

        # Get reflex code from artifact content
        reflex_code = reflex_artifact.content
        if not reflex_code:
            return None

        # Build reflex context
        context = build_reflex_context(agent.agent_id, self.world)

        # Execute reflex
        executor = ReflexExecutor()
        result = executor.execute(reflex_code, context)

        # Log reflex execution
        self.world.logger.log(
            "reflex_executed",
            {
                "event_number": self.world.event_number,
                "principal_id": agent.agent_id,
                "reflex_artifact_id": reflex_artifact_id,
                "fired": result.fired,
                "execution_time_ms": result.execution_time_ms,
                "error": result.error,
            },
        )

        # If reflex fired, return the action
        if result.fired and result.action is not None:
            if self.verbose:
                print(
                    f"    {agent.agent_id}: REFLEX fired "
                    f"({result.execution_time_ms:.1f}ms)"
                )
            return result.action

        # Reflex didn't fire - fall through to LLM
        if result.error:
            if self.verbose:
                print(
                    f"    {agent.agent_id}: REFLEX error: {result.error[:100]}"
                )

        return None

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

    def run_sync(self, duration: float | None = None) -> World:
        """Run the simulation synchronously.

        Wrapper around run() using asyncio.run().

        Args:
            duration: Maximum seconds to run (passed to run()). If None,
                runs until stopped. For tests, use a short duration like 0.5s.

        Returns:
            The World instance after simulation completes.
        """
        return asyncio.run(self.run(duration=duration))
