"""JSONL event logger - single source of truth for all world activity"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get


class EventLogger:
    """Append-only JSONL event log with per-run directory support.
    
    Supports two modes:
    1. Per-run mode (run_id + logs_dir): Creates timestamped directories
       - logs/{run_id}/events.jsonl
       - logs/latest -> {run_id} (symlink)
    2. Legacy mode (output_file only): Single file, overwritten each run
    """

    output_path: Path
    _logs_dir: Path | None
    _run_id: str | None

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
        """Log an event to the JSONL file"""
        event: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **data,
        }
        with open(self.output_path, "a") as f:
            f.write(json.dumps(event) + "\n")

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
