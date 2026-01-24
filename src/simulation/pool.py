"""Worker pool for parallel agent turn execution (Plan #53 Phase 3).

The pool manages execution of agent turns across multiple workers,
enabling scaling to many agents without OOM issues.

Architecture:
- Pool maintains a fixed number of worker slots
- Each turn runs in a worker (currently in-process, can be subprocess)
- State is persisted to SQLite between turns
- Resources (memory, CPU) are measured per-turn

Usage:
    pool = WorkerPool(
        num_workers=4,
        state_db_path=Path("state.db"),
    )

    # Run turns for all agents
    results = pool.run_round(
        agent_ids=["alpha", "beta", "gamma"],
        world_state={"event_number": 1, ...},
    )

Future extensions:
- Subprocess workers for true isolation
- Resource quotas per worker
- Priority queue based on owned connection slots
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .worker import run_agent_turn, TurnResult

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for worker pool."""

    num_workers: int = 4
    state_db_path: Path = field(default_factory=lambda: Path("agent_state.db"))
    log_dir: str | None = None
    run_id: str | None = None

    # Resource limits (Phase 5)
    memory_limit_bytes: int = 100 * 1024 * 1024  # 100MB default
    cpu_timeout_seconds: float = 30.0  # 30s default


@dataclass
class RoundResults:
    """Results from running a full round across all agents."""

    event_number: int
    results: list[dict[str, Any]]
    total_memory_bytes: int = 0
    total_cpu_seconds: float = 0.0
    success_count: int = 0
    error_count: int = 0

    @property
    def all_success(self) -> bool:
        """Whether all agents completed successfully."""
        return self.error_count == 0


class WorkerPool:
    """Pool of workers for parallel agent turn execution.

    Currently uses ThreadPoolExecutor for simplicity.
    Can be extended to use ProcessPoolExecutor for true isolation.
    """

    def __init__(self, config: PoolConfig | None = None) -> None:
        """Initialize worker pool.

        Args:
            config: Pool configuration (uses defaults if None)
        """
        self.config = config or PoolConfig()
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None

    def __enter__(self) -> "WorkerPool":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()

    def start(self) -> None:
        """Start the worker pool."""
        if self._executor is not None:
            return

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.num_workers,
            thread_name_prefix="agent_worker",
        )
        logger.info(f"Started worker pool with {self.config.num_workers} workers")

    def stop(self) -> None:
        """Stop the worker pool and wait for completion."""
        if self._executor is None:
            return

        self._executor.shutdown(wait=True)
        self._executor = None
        logger.info("Worker pool stopped")

    def run_round(
        self,
        agent_ids: list[str],
        world_state: dict[str, Any],
    ) -> RoundResults:
        """Run a single round for all agents.

        Distributes work across workers and collects results.

        Args:
            agent_ids: List of agent IDs to run
            world_state: World state to pass to each agent

        Returns:
            RoundResults with all agent results and aggregate metrics
        """
        if self._executor is None:
            self.start()

        assert self._executor is not None

        event_number = world_state.get("event_number", world_state.get("tick", 0))
        logger.debug(f"Running round {event_number} for {len(agent_ids)} agents")

        # Submit all turns to the pool
        futures: dict[concurrent.futures.Future[dict[str, Any]], str] = {}
        for agent_id in agent_ids:
            future = self._executor.submit(
                run_agent_turn,
                agent_id=agent_id,
                state_db_path=self.config.state_db_path,
                world_state=world_state,
                log_dir=self.config.log_dir,
                run_id=self.config.run_id,
            )
            futures[future] = agent_id

        # Collect results
        results: list[dict[str, Any]] = []
        total_memory = 0
        total_cpu = 0.0
        success_count = 0
        error_count = 0

        for future in concurrent.futures.as_completed(futures):
            agent_id = futures[future]
            try:
                result = future.result()
                results.append(result)

                if result.get("success", False):
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(
                        f"Agent {agent_id} failed: {result.get('error', 'unknown')}"
                    )

                total_memory += result.get("memory_bytes", 0)
                total_cpu += result.get("cpu_seconds", 0.0)

            except Exception as e:
                error_count += 1
                logger.error(f"Agent {agent_id} raised exception: {e}")
                results.append({
                    "agent_id": agent_id,
                    "success": False,
                    "error": str(e),
                })

        logger.debug(
            f"Round {event_number} complete: {success_count} success, {error_count} errors, "
            f"{total_memory / 1024 / 1024:.1f}MB memory, {total_cpu:.2f}s CPU"
        )

        return RoundResults(
            event_number=event_number,
            results=results,
            total_memory_bytes=total_memory,
            total_cpu_seconds=total_cpu,
            success_count=success_count,
            error_count=error_count,
        )

    def run_single(
        self,
        agent_id: str,
        world_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a single agent turn (synchronous).

        Useful for testing or when parallelism isn't needed.

        Args:
            agent_id: Agent to run
            world_state: World state to pass

        Returns:
            Turn result dictionary
        """
        return run_agent_turn(
            agent_id=agent_id,
            state_db_path=self.config.state_db_path,
            world_state=world_state,
            log_dir=self.config.log_dir,
            run_id=self.config.run_id,
        )
