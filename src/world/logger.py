"""JSONL event logger - single source of truth for all world activity"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import get


class EventLogger:
    """Append-only JSONL event log"""

    output_path: Path

    def __init__(self, output_file: str | None = None) -> None:
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
