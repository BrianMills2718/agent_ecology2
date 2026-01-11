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
from typing import Any, cast, get_args

from ..world import World
from ..world.actions import parse_intent_from_json, ActionIntent
from ..world.simulation_engine import SimulationEngine
from ..world.world import StateSummary, ConfigDict
from ..world.genesis import GenesisOracle, AuctionResult
from ..agents import Agent
from ..agents.loader import load_agents, AgentConfig
from ..agents.agent import ActionResult as AgentActionResult, TokenUsage
from ..agents.schema import ActionType

from .types import (
    PrincipalConfig,
    CheckpointData,
    ActionProposal,
    ThinkingResult,
)
from .checkpoint import save_checkpoint


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
        self.world = World(cast(ConfigDict, config))

        # Restore checkpoint if provided
        if checkpoint:
            self._restore_checkpoint(checkpoint)

        # Initialize agents
        self.agents = self._create_agents(agent_configs)

        # Pause/resume state
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self._running = False

    def _restore_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Restore world state from checkpoint."""
        # Restore tick (subtract 1 because advance_tick increments before first iteration)
        self.world.tick = checkpoint["tick"] - 1

        # Restore balances
        for agent_id, balance_info in checkpoint["balances"].items():
            if agent_id in self.world.ledger.scrip:
                self.world.ledger.scrip[agent_id] = balance_info["scrip"]

        # Restore artifacts
        for artifact_data in checkpoint["artifacts"]:
            self.world.artifacts.write(
                artifact_id=artifact_data["id"],
                type=artifact_data.get("type", "data"),
                content=artifact_data.get("content", ""),
                owner_id=artifact_data.get("owner_id", "system"),
                executable=artifact_data.get("executable", False),
                price=artifact_data.get("price", 0),
                code=artifact_data.get("code", ""),
                policy=artifact_data.get("policy"),
            )

        if self.verbose:
            print("=== Resuming from checkpoint ===")
            print(f"Previous tick: {checkpoint['tick']}")
            print(f"Previous reason: {checkpoint['reason']}")
            print(f"Cumulative API cost: ${self.engine.cumulative_api_cost:.4f}")
            print(f"Restored artifacts: {len(checkpoint['artifacts'])}")
            print()

    def _create_agents(self, agent_configs: list[AgentConfig]) -> list[Agent]:
        """Create Agent instances from config."""
        agents: list[Agent] = []
        for a in agent_configs:
            agent = Agent(
                agent_id=a["id"],
                llm_model=a.get("llm_model") or self.config["llm"]["default_model"],
                system_prompt=a.get("system_prompt", ""),
                action_schema=a.get("action_schema", ""),
                log_dir=self.config["logging"]["log_dir"],
                run_id=self.run_id,
            )
            agents.append(agent)
        return agents

    def _check_for_new_principals(self) -> list[Agent]:
        """Check ledger for principals without Agent instances.

        Creates default Agent instances for spawned principals.
        """
        ledger_principals: set[str] = set(self.world.ledger.scrip.keys())
        existing_agent_ids: set[str] = {agent.agent_id for agent in self.agents}
        new_principal_ids: set[str] = ledger_principals - existing_agent_ids

        new_agents: list[Agent] = []
        default_model: str = self.config.get("llm", {}).get(
            "default_model", "gemini/gemini-3-flash-preview"
        )
        log_dir: str = self.config.get("logging", {}).get("log_dir", "llm_logs")
        default_system_prompt: str = (
            "You are a new agent. Survive and thrive. "
            "You start with nothing - seek resources and opportunities. "
            "See docs/AGENT_HANDBOOK.md for rules."
        )

        for principal_id in new_principal_ids:
            new_agent = Agent(
                agent_id=principal_id,
                llm_model=default_model,
                system_prompt=default_system_prompt,
                action_schema="",
                log_dir=log_dir,
                run_id=self.run_id,
            )
            new_agents.append(new_agent)

            if self.verbose:
                print(f"  [NEW AGENT] Created agent for principal: {principal_id}")

        return new_agents

    def _handle_oracle_tick(self) -> AuctionResult | None:
        """Handle oracle auction tick.

        Calls the oracle's on_tick method to:
        - Start new bidding windows
        - Resolve completed auctions
        - Distribute UBI from winning bids

        Returns:
            AuctionResult dict if an auction was resolved, None otherwise.
        """
        oracle = self.world.genesis_artifacts.get("genesis_oracle")
        if oracle is None:
            return None

        # Check if oracle has on_tick method (auction-based oracle)
        if not hasattr(oracle, "on_tick"):
            return None

        # Cast to GenesisOracle since we verified it has on_tick
        result = cast(GenesisOracle, oracle).on_tick(self.world.tick)

        # Log auction result if there was one
        if result:
            self.world.logger.log(
                "oracle_auction",
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
            self.engine.track_api_cost(api_cost)

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

    def _execute_proposals(self, proposals: list[ActionProposal]) -> None:
        """Execute proposals in randomized order (Phase 2)."""
        if self.verbose and proposals:
            print(f"  [PHASE 2] Executing {len(proposals)} proposals in randomized order...")

        random.shuffle(proposals)

        for action_proposal in proposals:
            agent = action_proposal["agent"]
            proposal = action_proposal["proposal"]

            action_dict: dict[str, Any] = proposal["action"]
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
            valid_types = get_args(ActionType)
            action_type: ActionType = raw_action_type if raw_action_type in valid_types else "noop"
            agent.set_last_result(action_type, result.success, result.message)
            agent.record_action(action_type, json.dumps(action_dict), result.success)

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

    async def run(self) -> World:
        """Run the simulation asynchronously.

        Uses parallel agent thinking via asyncio.gather().

        Returns:
            The World instance after simulation completes.
        """
        SimulationRunner._active_runner = self
        self._running = True
        self._print_startup_info()

        while self.world.advance_tick():
            # Wait if paused
            await self._pause_event.wait()

            if self.verbose:
                print(f"--- Tick {self.world.tick} ---")

            # Handle oracle auction tick (resolve auctions, start bidding windows)
            oracle_result = self._handle_oracle_tick()
            if oracle_result and self.verbose:
                if oracle_result.get("winner_id"):
                    print(f"  [AUCTION] Winner: {oracle_result['winner_id']}, "
                          f"paid {oracle_result['price_paid']} scrip, "
                          f"score: {oracle_result.get('score')}, "
                          f"minted: {oracle_result['scrip_minted']}")
                elif oracle_result.get("error"):
                    print(f"  [AUCTION] {oracle_result['error']}")

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
                return self.world

            # PHASE 1: Parallel thinking
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

            if self.verbose:
                print(f"  End of tick. Scrip: {self.world.ledger.get_all_scrip()}")
                print()

        self._running = False
        SimulationRunner._active_runner = None
        self._print_final_summary()
        return self.world

    def run_sync(self) -> World:
        """Run the simulation synchronously.

        Wrapper around run() using asyncio.run().

        Returns:
            The World instance after simulation completes.
        """
        return asyncio.run(self.run())
