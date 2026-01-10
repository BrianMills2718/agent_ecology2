"""JSONL event logger - single source of truth for all world activity"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get


class EventLogger:
    """Append-only JSONL event log"""

    def __init__(self, output_file: str = None):
        output_file = output_file or get("logging.output_file") or "run.jsonl"
        self.output_path = Path(output_file)
        # Clear existing log on init (new run)
        self.output_path.write_text("")

    def log(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event to the JSONL file"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **data
        }
        with open(self.output_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def read_recent(self, n: int = None) -> list:
        """Read the last N events from the log.

        N defaults to logging.default_recent from config.
        """
        if n is None:
            n = get("logging.default_recent") or 50
        if not self.output_path.exists():
            return []
        lines = self.output_path.read_text().strip().split("\n")
        lines = [l for l in lines if l]  # filter empty
        recent = lines[-n:] if len(lines) > n else lines
        return [json.loads(l) for l in recent]
