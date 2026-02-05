"""Worker process for agent turn execution.

Plan #299: Legacy agent system removed. This module is now a stub.
The run_agent_turn function is retained for API compatibility but will
raise an error if called (legacy agents no longer exist).

For new artifact-based agents, see ArtifactLoopManager in artifact_loop.py.
"""

from __future__ import annotations

import time
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
    """Run a single agent turn - LEGACY STUB.

    Plan #299: Legacy agent system removed. This function will raise
    an error if called. Use ArtifactLoopManager for new agent execution.
    """
    return {
        "agent_id": agent_id,
        "success": False,
        "error": "Legacy agent system removed (Plan #299). Use artifact-based agents.",
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
