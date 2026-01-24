"""JSONL event logger - single source of truth for all world activity"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get


class SummaryLogger:
    """Writes periodic summary lines to summary.jsonl.

    Creates a tractable overview of simulation activity alongside
    the full event log. One line per summary period with key metrics.
    """

    output_path: Path

    def __init__(self, path: Path) -> None:
        """Initialize the summary logger.

        Args:
            path: Path to the summary.jsonl file
        """
        self.output_path = path
        # Create parent directory if needed
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def log_summary(
        self,
        event_number: int,
        agents_active: int,
        actions_executed: int,
        actions_by_type: dict[str, int] | None = None,
        total_llm_tokens: int = 0,
        total_scrip_transferred: int = 0,
        artifacts_created: int = 0,
        errors: int = 0,
        highlights: list[str] | None = None,
    ) -> None:
        """Log a summary.

        Args:
            event_number: The current event number
            agents_active: Number of agents that acted in this period
            actions_executed: Total actions executed
            actions_by_type: Breakdown of actions by type (e.g., {"invoke": 3, "write": 2})
            total_llm_tokens: Total LLM tokens consumed
            total_scrip_transferred: Total scrip transferred
            artifacts_created: Number of artifacts created
            errors: Number of errors/failures
            highlights: List of notable events (e.g., "alpha created tool_x")
        """
        summary: dict[str, Any] = {
            "event_number": event_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents_active": agents_active,
            "actions_executed": actions_executed,
            "actions_by_type": actions_by_type or {},
            "total_llm_tokens": total_llm_tokens,
            "total_scrip_transferred": total_scrip_transferred,
            "artifacts_created": artifacts_created,
            "errors": errors,
            "highlights": highlights or [],
        }
        with open(self.output_path, "a") as f:
            f.write(json.dumps(summary) + "\n")


class SummaryCollector:
    """Accumulates metrics for summary logging.

    Use this to track actions, tokens, scrip, and highlights during
    a period, then call finalize() to get the summary dict.
    """

    def __init__(self) -> None:
        """Initialize the collector with zeroed counters."""
        self._reset()

    def _reset(self) -> None:
        """Reset all counters to initial state."""
        self._actions_executed: int = 0
        self._actions_by_type: dict[str, int] = {}
        self._errors: int = 0
        self._llm_tokens: int = 0
        self._scrip_transferred: int = 0
        self._artifacts_created: int = 0
        self._highlights: list[str] = []
        # Per-agent tracking (Plan #76)
        self._per_agent: dict[str, dict[str, int]] = {}

    def record_action(
        self,
        action_type: str,
        success: bool = True,
        agent_id: str | None = None,
    ) -> None:
        """Record an action execution.

        Args:
            action_type: The type of action (e.g., "invoke", "write", "read")
            success: Whether the action succeeded
            agent_id: Optional agent ID for per-agent tracking (Plan #76)
        """
        self._actions_executed += 1
        self._actions_by_type[action_type] = self._actions_by_type.get(action_type, 0) + 1
        if not success:
            self._errors += 1

        # Per-agent tracking (Plan #76)
        if agent_id is not None:
            if agent_id not in self._per_agent:
                self._per_agent[agent_id] = {"actions": 0, "successes": 0, "failures": 0, "tokens": 0}
            self._per_agent[agent_id]["actions"] += 1
            if success:
                self._per_agent[agent_id]["successes"] += 1
            else:
                self._per_agent[agent_id]["failures"] += 1

    def record_llm_tokens(self, count: int, agent_id: str | None = None) -> None:
        """Record LLM token usage.

        Args:
            count: Number of tokens consumed
            agent_id: Optional agent ID for per-agent tracking (Plan #76)
        """
        self._llm_tokens += count

        # Per-agent tracking (Plan #76)
        if agent_id is not None:
            if agent_id not in self._per_agent:
                self._per_agent[agent_id] = {"actions": 0, "successes": 0, "failures": 0, "tokens": 0}
            self._per_agent[agent_id]["tokens"] += count

    def record_scrip_transfer(self, amount: int) -> None:
        """Record a scrip transfer.

        Args:
            amount: Amount of scrip transferred
        """
        self._scrip_transferred += amount

    def record_artifact_created(self) -> None:
        """Record that an artifact was created."""
        self._artifacts_created += 1

    def add_highlight(self, text: str) -> None:
        """Add a notable event to highlights.

        Args:
            text: Description of the notable event
        """
        self._highlights.append(text)

    def finalize(self, event_number: int, agents_active: int) -> dict[str, Any]:
        """Finalize and return summary dict.

        Resets the collector state after returning.

        Args:
            event_number: The current event number
            agents_active: Number of agents that were active

        Returns:
            Summary dict suitable for SummaryLogger.log_summary()
        """
        summary: dict[str, Any] = {
            "event_number": event_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents_active": agents_active,
            "actions_executed": self._actions_executed,
            "actions_by_type": self._actions_by_type.copy(),
            "total_llm_tokens": self._llm_tokens,
            "total_scrip_transferred": self._scrip_transferred,
            "artifacts_created": self._artifacts_created,
            "errors": self._errors,
            "highlights": self._highlights.copy(),
            # Per-agent tracking (Plan #76)
            "per_agent": {k: v.copy() for k, v in self._per_agent.items()},
        }
        self._reset()
        return summary


class EventLogger:
    """Append-only JSONL event log with per-run directory support.

    Supports two modes:
    1. Per-run mode (run_id + logs_dir): Creates timestamped directories
       - logs/{run_id}/events.jsonl
       - logs/{run_id}/summary.jsonl (companion SummaryLogger)
       - logs/latest -> {run_id} (symlink)
    2. Legacy mode (output_file only): Single file, overwritten each run

    Plan #151: Added sequence counter and resource event helpers per ADR-0020.
    """

    output_path: Path
    summary_logger: SummaryLogger | None
    _logs_dir: Path | None
    _run_id: str | None
    _sequence: int  # Monotonic event counter (Plan #151)

    def __init__(
        self,
        output_file: str | None = None,
        logs_dir: str | None = None,
        run_id: str | None = None,
    ) -> None:
        """Initialize the event logger.

        Args:
            output_file: Legacy mode - single file path (default: run.jsonl)
            logs_dir: Per-run mode - base directory for run logs
            run_id: Per-run mode - unique run identifier (e.g., run_20260115_120000)
        """
        self._logs_dir = Path(logs_dir) if logs_dir else None
        self._run_id = run_id
        self.summary_logger = None  # Set in _setup_per_run_logging if applicable
        self._sequence = 0  # Plan #151: monotonic event counter

        if logs_dir and run_id:
            # Per-run mode: create timestamped directory
            self._setup_per_run_logging()
        else:
            # Legacy mode: single file
            self._setup_legacy_logging(output_file)

    def _setup_per_run_logging(self) -> None:
        """Set up per-run directory logging."""
        if self._logs_dir is None or self._run_id is None:
            raise ValueError("Both logs_dir and run_id required for per-run mode")

        # Create run directory
        run_dir = self._logs_dir / self._run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Set output path
        self.output_path = run_dir / "events.jsonl"
        self.output_path.write_text("")  # Clear/create file

        # Create companion SummaryLogger for tractable periodic summaries
        self.summary_logger = SummaryLogger(run_dir / "summary.jsonl")

        # Create/update 'latest' symlink
        latest_link = self._logs_dir / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        elif latest_link.exists():
            # If it's a regular file/dir, remove it
            if latest_link.is_dir():
                import shutil
                shutil.rmtree(latest_link)
            else:
                latest_link.unlink()

        # Create symlink (relative path for portability)
        latest_link.symlink_to(self._run_id)

    def _setup_legacy_logging(self, output_file: str | None) -> None:
        """Set up legacy single-file logging."""
        resolved_file = output_file or get("logging.output_file") or "run.jsonl"
        if not isinstance(resolved_file, str):
            resolved_file = "run.jsonl"
        self.output_path = Path(resolved_file)
        # Clear existing log on init (new run)
        self.output_path.write_text("")

    def log(self, event_type: str, data: dict[str, Any]) -> None:
        """Log an event to the JSONL file.

        Plan #151: All events include a monotonic 'sequence' field for ordering.
        Events also include 'event_number' from the caller for correlation.
        """
        self._sequence += 1
        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": self._sequence,  # Plan #151: monotonic counter
            "event_type": event_type,
            **data,
        }
        with open(self.output_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    # ========== Plan #151: Resource Event Helpers (ADR-0020) ==========

    def log_resource_consumed(
        self,
        principal_id: str,
        resource: str,
        amount: float,
        balance_after: float,
        quota: float | None = None,
        rate_window_remaining: float | None = None,
    ) -> None:
        """Log consumption of a renewable (rate-limited) resource.

        Args:
            principal_id: The agent/artifact consuming the resource
            resource: Resource name (e.g., "llm_tokens")
            amount: Amount consumed
            balance_after: Balance after consumption
            quota: Optional quota limit
            rate_window_remaining: Optional remaining capacity in rate window
        """
        data: dict[str, Any] = {
            "principal_id": principal_id,
            "resource": resource,
            "amount": amount,
            "balance_after": balance_after,
        }
        if quota is not None:
            data["quota"] = quota
        if rate_window_remaining is not None:
            data["rate_window_remaining"] = rate_window_remaining
        self.log("resource_consumed", data)

    def log_resource_allocated(
        self,
        principal_id: str,
        resource: str,
        amount: float,
        used_after: float,
        quota: float,
    ) -> None:
        """Log allocation of an allocatable (quota-based) resource.

        Args:
            principal_id: The agent/artifact allocating the resource
            resource: Resource name (e.g., "disk")
            amount: Amount allocated (can be negative for deallocation)
            used_after: Total usage after allocation
            quota: Quota limit
        """
        self.log("resource_allocated", {
            "principal_id": principal_id,
            "resource": resource,
            "amount": amount,
            "used_after": used_after,
            "quota": quota,
        })

    def log_resource_spent(
        self,
        principal_id: str,
        resource: str,
        amount: float,
        balance_after: float,
    ) -> None:
        """Log spending of a depletable resource.

        Args:
            principal_id: The agent/artifact spending the resource
            resource: Resource name (e.g., "llm_budget")
            amount: Amount spent
            balance_after: Balance after spending
        """
        self.log("resource_spent", {
            "principal_id": principal_id,
            "resource": resource,
            "amount": amount,
            "balance_after": balance_after,
        })

    def log_agent_state(
        self,
        agent_id: str,
        status: str,
        scrip: float,
        resources: dict[str, dict[str, float]],
        frozen_reason: str | None = None,
    ) -> None:
        """Log agent state change.

        Args:
            agent_id: The agent whose state changed
            status: Current status ("active", "frozen", "terminated")
            scrip: Current scrip balance
            resources: Resource state dict with structure:
                {
                    "llm_tokens": {"used": X, "quota": Y, "rate_remaining": Z},
                    "llm_budget": {"used": X, "initial": Y},
                    "disk": {"used": X, "quota": Y}
                }
            frozen_reason: If frozen, the reason why
        """
        data: dict[str, Any] = {
            "agent_id": agent_id,
            "status": status,
            "scrip": scrip,
            "resources": resources,
        }
        if frozen_reason is not None:
            data["frozen_reason"] = frozen_reason
        self.log("agent_state", data)

    def read_recent(self, n: int | None = None) -> list[dict[str, Any]]:
        """Read the last N events from the log.

        N defaults to logging.default_recent from config.
        """
        if n is None:
            default_recent = get("logging.default_recent")
            if isinstance(default_recent, int):
                n = default_recent
            else:
                n = 50
        if not self.output_path.exists():
            return []
        lines = self.output_path.read_text().strip().split("\n")
        lines = [line for line in lines if line]  # filter empty
        recent = lines[-n:] if len(lines) > n else lines
        return [json.loads(line) for line in recent]

    @property
    def run_id(self) -> str | None:
        """Return the run ID if in per-run mode."""
        return self._run_id

    @property
    def logs_dir(self) -> Path | None:
        """Return the logs directory if in per-run mode."""
        return self._logs_dir
