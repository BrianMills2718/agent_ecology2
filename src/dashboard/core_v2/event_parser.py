"""Event parser: Parse JSONL → typed events.

Responsible for:
- Reading JSONL files line by line
- Parsing JSON into typed event models
- Handling malformed or unknown events gracefully
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

from ..models_v2.events import (
    EventEnvelope,
    parse_event,
)

logger = logging.getLogger(__name__)


class EventParser:
    """Parse JSONL event streams into typed events.

    Usage:
        parser = EventParser()
        for event in parser.parse_file("run.jsonl"):
            print(event.event_type, event.sequence)
    """

    def __init__(self) -> None:
        self._events_parsed: int = 0
        self._parse_errors: int = 0

    @property
    def events_parsed(self) -> int:
        """Total events successfully parsed."""
        return self._events_parsed

    @property
    def parse_errors(self) -> int:
        """Total parse errors encountered."""
        return self._parse_errors

    def parse_line(self, line: str) -> EventEnvelope | None:
        """Parse a single JSONL line into a typed event.

        Returns None if the line cannot be parsed.
        """
        line = line.strip()
        if not line:
            return None

        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                logger.warning("Event is not a dict: %s", type(data))
                self._parse_errors += 1
                return None

            event = parse_event(data)
            self._events_parsed += 1
            return event

        except json.JSONDecodeError as e:
            logger.warning("JSON decode error: %s", e)
            self._parse_errors += 1
            return None
        except Exception as e:
            logger.warning("Event parse error: %s", e)
            self._parse_errors += 1
            return None

    def parse_lines(self, lines: Iterator[str]) -> Iterator[EventEnvelope]:
        """Parse multiple lines, yielding typed events."""
        for line in lines:
            event = self.parse_line(line)
            if event is not None:
                yield event

    def parse_file(
        self, file_path: str | Path, offset: int = 0
    ) -> Iterator[EventEnvelope]:
        """Parse a JSONL file, optionally starting at an offset.

        Args:
            file_path: Path to the JSONL file
            offset: Byte offset to start reading from

        Yields:
            Typed event objects
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("File not found: %s", path)
            return

        with open(path, "r", encoding="utf-8") as f:
            if offset > 0:
                f.seek(offset)
                # Skip partial line if we're in the middle
                f.readline()

            for line in f:
                event = self.parse_line(line)
                if event is not None:
                    yield event

    def parse_dict(self, data: dict[str, Any]) -> EventEnvelope:
        """Parse a dict directly into a typed event."""
        event = parse_event(data)
        self._events_parsed += 1
        return event

    def reset_stats(self) -> None:
        """Reset parsing statistics."""
        self._events_parsed = 0
        self._parse_errors = 0
