"""SimulationRunner - Main orchestrator for agent ecology simulation.

Handles:
- World and artifact-based agent initialization
- Checkpoint restore
- Autonomous artifact loops with time-based rate limiting
- Budget tracking
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from ..world import World
from ..world.simulation_engine import SimulationEngine
from ..world.mint_auction import KernelMintResult
from ..world.logger import SummaryCollector
from ..config import get_validated_config

from .types import (
    CheckpointData,
    ErrorStats,
)
from .agent_loop import AgentLoopManager, AgentLoopConfig
from .artifact_loop import ArtifactLoopManager  # Plan #255: V4 artifact loops


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
    - World initialization and artifact-based agent discovery
    - Autonomous artifact loops with time-based rate limiting
    - Budget tracking and checkpointing
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

        # Principals are created by genesis loader, not agent configs
        config["principals"] = []

        # Initialize world
        self.world = World(config, run_id=self.run_id)

        # Restore checkpoint if provided
        if checkpoint:
            self._restore_checkpoint(checkpoint)

        # Wire up cost tracking callbacks for genesis embedder (Plan #153)
        self._wire_embedder_cost_callbacks()

        # Create AgentLoopManager (always autonomous mode, Plan #102)
        # Plan #247: Ledger.from_config() always creates a RateTracker
        rate_tracker = self.world.rate_tracker
        self.world.loop_manager = AgentLoopManager(rate_tracker)

        # Plan #255: Create ArtifactLoopManager for V4 has_loop artifacts
        self.artifact_loop_manager = ArtifactLoopManager(self.world, rate_tracker)

        # Pause/resume state
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        self._running = False

        # Summary logging (Plan #60)
        self._summary_collector: SummaryCollector | None = None

    def _wire_embedder_cost_callbacks(self) -> None:
        """Wire up cost tracking callbacks for kernel components.

        This integrates API costs into the global budget tracking system:
        - MintAuction (kernel): scorer LLM calls during auction resolution
        """
        def _track_cost(cost: float) -> None:
            self.engine.track_api_cost(cost)

        # Wire up kernel mint auction scorer callbacks
        self.world.mint_auction.set_cost_callbacks(
            is_budget_exhausted=self.engine.is_budget_exhausted,
            track_api_cost=_track_cost,
        )

    def _restore_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Restore world state from checkpoint.

        Properly restores agent artifacts with their principal capabilities
        (has_standing, has_loop, memory_artifact_id) for unified ontology.
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
            if artifact_data.get("has_loop") or artifact_data.get("can_execute"):
                artifact.has_loop = True
            if artifact_data.get("memory_artifact_id"):
                artifact.memory_artifact_id = artifact_data["memory_artifact_id"]

        # Plan #231: Enforce has_standing <-> ledger invariant after restore
        for pid in self.world.ledger.scrip:
            if pid.startswith("genesis_"):
                continue
            maybe_artifact = self.world.artifacts.artifacts.get(pid)
            if maybe_artifact and not maybe_artifact.has_standing:
                maybe_artifact.has_standing = True

        for aid, artifact in self.world.artifacts.artifacts.items():
            if artifact.has_standing and aid not in self.world.ledger.scrip:
                # Fix drift: has standing but no ledger entry.
                # Use raw dict access because ID is already registered as 'artifact'
                # in IDRegistry — create_principal() would raise IDCollisionError.
                self.world.ledger.scrip[aid] = 0
                self.world.ledger.resources[aid] = {}

        if self.verbose:
            print("=== Resuming from checkpoint ===")
            print(f"Event counter: {checkpoint.get('event_number', checkpoint.get('tick', 0))}")
            print(f"Previous reason: {checkpoint['reason']}")
            print(f"Cumulative API cost: ${self.engine.cumulative_api_cost:.4f}")
            print(f"Restored artifacts: {len(checkpoint['artifacts'])}")
            print()

    def _handle_mint_update(self) -> KernelMintResult | None:
        """Handle mint auction update (Plan #83 - time-based).

        Calls the kernel mint auction's update method to check if auctions need to:
        - Start new bidding windows
        - Resolve completed auctions
        - Distribute UBI from winning bids

        Returns:
            KernelMintResult dict if an auction was resolved, None otherwise.
        """
        # Plan #254: Use kernel mint_auction directly
        result = self.world.mint_auction.update()

        self._log_mint_result(result)
        return result

    def _log_mint_result(self, result: KernelMintResult | None) -> None:
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

    def _print_startup_info(self) -> None:
        """Print simulation startup information."""
        if not self.verbose:
            return

        print("=== Agent Ecology Simulation ===")
        print("Mode: Autonomous (artifact-based agent loops)")

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

        # Show rate limit info
        rate_config = self.config.get("rate_limiting", {})
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
            "artifact_loop_count": self.artifact_loop_manager.loop_count,
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
        """Run simulation in autonomous mode with independent artifact loops.

        Artifact-based agents run continuously in their own loops, resource-gated
        by RateTracker.
        Plan #83: Mint auctions run on wall-clock time via periodic update().

        Args:
            duration: Maximum seconds to run (optional, runs until stopped if not provided)
        """
        if not self.world.loop_manager:
            raise RuntimeError("loop_manager not initialized")

        # Plan #255: Discover has_loop artifacts (V4 artifact-based agents)
        artifact_loop_ids = self.artifact_loop_manager.discover_loops()
        if artifact_loop_ids and self.verbose:
            print(f"  [AUTONOMOUS] Discovered {len(artifact_loop_ids)} artifact loops: {artifact_loop_ids}")

        if self.verbose:
            print(f"  [AUTONOMOUS] Starting all loops...")

        # Start all loops
        await self.world.loop_manager.start_all()

        # Plan #255: Start artifact loops
        if self.artifact_loop_manager.loop_count > 0:
            if self.verbose:
                print(f"  [AUTONOMOUS] Starting {self.artifact_loop_manager.loop_count} artifact loops...")
            await self.artifact_loop_manager.start_all()

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
            # Plan #255: Stop artifact loops
            if self.artifact_loop_manager.loop_count > 0:
                await self.artifact_loop_manager.stop_all()
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

    async def shutdown(self, timeout: float | None = None) -> None:
        """Gracefully stop the simulation.

        Stops all agent loops and artifact loops.

        Args:
            timeout: Maximum seconds to wait for loops to stop.
                     Defaults to config timeouts.simulation_shutdown.
        """
        if timeout is None:
            timeout = get_validated_config().timeouts.simulation_shutdown
        if self.world.loop_manager:
            await self.world.loop_manager.stop_all(timeout=timeout)
        # Plan #255: Stop artifact loops
        if self.artifact_loop_manager.loop_count > 0:
            await self.artifact_loop_manager.stop_all(timeout=timeout)
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
