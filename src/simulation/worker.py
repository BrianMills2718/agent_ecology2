"""Worker process for agent turn execution (Plan #53 Phase 3).

Workers execute agent turns in isolation, enabling:
- Process-per-turn model for scaling to many agents
- Resource measurement (memory, CPU) per-turn
- Resource enforcement (kill turns exceeding quotas)

Usage (in-process):
    result = run_agent_turn(
        agent_id="alpha",
        state_db_path=Path("state.db"),
        world_state={"event_number": 1, ...},
    )

Usage (subprocess):
    # See pool.py for subprocess orchestration
"""

from __future__ import annotations

import signal
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

# Optional psutil for memory measurement
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


T = TypeVar("T")


@dataclass
class TurnResult:
    """Result of executing an agent turn."""

    agent_id: str
    success: bool
    action: dict[str, Any] | None = None
    error: str | None = None
    memory_bytes: int = 0
    cpu_seconds: float = 0.0
    killed: bool = False


def run_agent_turn(
    agent_id: str,
    state_db_path: Path,
    world_state: dict[str, Any],
    *,
    log_dir: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run a single agent turn, loading from and saving to state store.

    This function:
    1. Loads agent state from SQLite
    2. Reconstructs the Agent instance
    3. Calls propose_action with world_state
    4. Saves updated state back to SQLite
    5. Returns the proposed action

    Args:
        agent_id: ID of agent to run
        state_db_path: Path to SQLite state database
        world_state: World state to pass to agent
        log_dir: Directory for LLM logs
        run_id: Run ID for log organization

    Returns:
        Dict with agent_id, action/error, and resource usage
    """
    from ..agents.state_store import AgentStateStore
    from ..agents.agent import Agent

    start_time = time.perf_counter()
    memory_start = _get_memory_usage()

    try:
        # Load state
        store = AgentStateStore(state_db_path)
        state = store.load(agent_id)

        if state is None:
            return {
                "agent_id": agent_id,
                "success": False,
                "error": f"Agent '{agent_id}' not found in state store",
            }

        # Reconstruct agent
        agent = Agent.from_state(state, log_dir=log_dir, run_id=run_id)

        # Run turn
        action_result = agent.propose_action(world_state)

        # Update state with turn results (ensure serializable)
        try:
            import json
            # Try to serialize to ensure it's JSON-safe
            json.dumps(action_result)
            state.last_action_result = str(action_result)
        except (TypeError, ValueError):
            # Not serializable, convert to string representation
            state.last_action_result = repr(action_result)

        state.last_tick = world_state.get("event_number", world_state.get("tick", 0))
        action_type = None
        if isinstance(action_result, dict):
            action_type = action_result.get("action")
        state.turn_history.append({
            "event_number": world_state.get("event_number", world_state.get("tick", 0)),
            "action": action_type,
        })

        # Save updated state
        store.save(state)

        # Calculate resource usage
        elapsed = time.perf_counter() - start_time
        memory_end = _get_memory_usage()
        memory_used = max(0, memory_end - memory_start)

        return {
            "agent_id": agent_id,
            "success": True,
            "action": action_result,
            "cpu_seconds": elapsed,
            "memory_bytes": memory_used,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "agent_id": agent_id,
            "success": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
            "cpu_seconds": elapsed,
        }


def measure_turn_resources(func: Callable[[], T]) -> dict[str, Any]:
    """Measure resource usage during function execution.

    Args:
        func: Function to execute and measure

    Returns:
        Dict with memory_bytes, cpu_seconds, and result
    """
    start_time = time.perf_counter()
    memory_start = _get_memory_usage()

    try:
        result = func()
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)

    elapsed = time.perf_counter() - start_time
    memory_end = _get_memory_usage()
    memory_used = max(0, memory_end - memory_start)

    return {
        "success": success,
        "result": result,
        "error": error,
        "cpu_seconds": elapsed,
        "memory_bytes": memory_used,
    }


def run_with_memory_limit(
    func: Callable[[], T],
    memory_limit_bytes: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Run function with memory and time limits.

    Note: True memory limiting requires process isolation (subprocess).
    This implementation uses timeout and best-effort memory checking.

    Args:
        func: Function to execute
        memory_limit_bytes: Maximum memory allowed
        timeout_seconds: Maximum execution time

    Returns:
        Dict with success, result/error, and whether killed
    """

    class TimeoutError(Exception):
        pass

    def timeout_handler(signum: int, frame: Any) -> None:
        raise TimeoutError("Turn exceeded time limit")

    # Set up timeout (Unix only)
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    except (ValueError, AttributeError):
        # Windows or no signal support - fall back to no timeout
        pass

    start_time = time.perf_counter()
    memory_start = _get_memory_usage()

    try:
        result = func()

        # Check memory (best effort, may already be deallocated)
        memory_end = _get_memory_usage()
        memory_used = max(0, memory_end - memory_start)

        if memory_used > memory_limit_bytes:
            return {
                "success": False,
                "error": f"Memory limit exceeded: {memory_used} > {memory_limit_bytes}",
                "killed": True,
                "memory_bytes": memory_used,
            }

        elapsed = time.perf_counter() - start_time
        return {
            "success": True,
            "result": result,
            "memory_bytes": memory_used,
            "cpu_seconds": elapsed,
            "killed": False,
        }

    except TimeoutError:
        elapsed = time.perf_counter() - start_time
        return {
            "success": False,
            "error": f"Timeout after {elapsed:.2f}s (limit: {timeout_seconds}s)",
            "killed": True,
            "cpu_seconds": elapsed,
        }

    except MemoryError:
        return {
            "success": False,
            "error": "Memory limit exceeded (MemoryError)",
            "killed": True,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "success": False,
            "error": f"{type(e).__name__}: {e}",
            "cpu_seconds": elapsed,
            "killed": False,
        }

    finally:
        # Restore signal handler
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass


def _get_memory_usage() -> int:
    """Get current process memory usage in bytes.

    Returns 0 if psutil is not available.
    """
    if not HAS_PSUTIL:
        return 0

    try:
        process = psutil.Process()
        return int(process.memory_info().rss)
    except Exception:
        return 0
