"""Genesis Event Log - Passive observability

This is the only way agents can learn about world events.
Nothing is injected into prompts - agents must actively read.
"""

from __future__ import annotations

from typing import Any

from ...config import get, get_validated_config
from ...config_schema import GenesisConfig
from ..logger import EventLogger
from .base import GenesisArtifact


class GenesisEventLog(GenesisArtifact):
    """
    Genesis artifact for passive observability.

    This is the only way agents can learn about world events.
    Nothing is injected into prompts - agents must actively read.
    Reading is FREE in scrip, but costs real input tokens.

    All method costs and descriptions are configurable via config.yaml.
    """

    logger: EventLogger
    _max_per_read: int
    _buffer_size: int

    def __init__(self, logger: EventLogger, genesis_config: GenesisConfig | None = None) -> None:
        """
        Args:
            logger: The world's EventLogger instance
            genesis_config: Optional genesis config (uses global if not provided)
        """
        # Get config (use provided or load from global)
        cfg = genesis_config or get_validated_config().genesis
        event_log_cfg = cfg.event_log

        super().__init__(
            artifact_id=event_log_cfg.id,
            description=event_log_cfg.description
        )
        self.logger = logger
        self._max_per_read = event_log_cfg.max_per_read
        self._buffer_size = event_log_cfg.buffer_size

        # Register methods with costs/descriptions from config
        self.register_method(
            name="read",
            handler=self._read,
            cost=event_log_cfg.methods.read.cost,
            description=event_log_cfg.methods.read.description
        )
        self.register_method(
            name="get_invokers",
            handler=self._get_invokers,
            cost=event_log_cfg.methods.read.cost,  # Same cost as read
            description="Get list of principals that have invoked a specific artifact"
        )

    def _read(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Read events from the log.

        Args format: [offset, limit]
        - offset: skip this many events from the end (default 0)
        - limit: return at most this many events (default from config)
        """
        offset = 0
        default_limit: int = get("logging.default_recent") or 50
        limit = default_limit

        if args and len(args) >= 1 and isinstance(args[0], int):
            offset = args[0]
        if args and len(args) >= 2 and isinstance(args[1], int):
            limit = min(args[1], self._max_per_read)  # Cap to prevent abuse

        # Get all recent events then slice
        all_events = self.logger.read_recent(self._buffer_size)

        if offset > 0:
            # Slice from offset
            end_idx = len(all_events) - offset
            start_idx = max(0, end_idx - limit)
            events = all_events[start_idx:end_idx]
        else:
            # Just the most recent
            events = all_events[-limit:] if len(all_events) > limit else all_events

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "total_available": len(all_events),
            "warning": "Reading events costs input tokens when you next think. Be strategic about what you read."
        }

    def _get_invokers(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Get list of principals that have invoked a specific artifact (Plan #170).

        Args format: [artifact_id]
        - artifact_id: The artifact to query invokers for

        Returns:
            dict with success, invokers list, and count
        """
        if not args or len(args) < 1:
            return {
                "success": False,
                "error": "get_invokers requires [artifact_id]"
            }

        target_artifact_id = str(args[0])

        # Read all events from the buffer
        all_events = self.logger.read_recent(self._buffer_size)

        # Find unique invokers for this artifact
        invokers: set[str] = set()
        for event in all_events:
            if not isinstance(event, dict):
                continue
            # Check if this is an invocation event for the target artifact
            if (event.get("event_type") == "invoke" and
                    event.get("artifact_id") == target_artifact_id):
                invoker = event.get("invoker")
                if invoker:
                    invokers.add(str(invoker))

        invokers_list = sorted(invokers)  # Sort for deterministic output

        return {
            "success": True,
            "artifact_id": target_artifact_id,
            "invokers": invokers_list,
            "count": len(invokers_list),
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the event log (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "read",
                    "description": "Read recent events from the world log. Free in scrip but costs input tokens.",
                    "cost": self.methods["read"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "offset": {
                                "type": "integer",
                                "description": "Skip this many events from the end (default 0)",
                                "minimum": 0
                            },
                            "limit": {
                                "type": "integer",
                                "description": f"Return at most this many events (max {self._max_per_read})",
                                "minimum": 1,
                                "maximum": self._max_per_read
                            }
                        }
                    }
                },
                {
                    "name": "get_invokers",
                    "description": "Get list of principals that have invoked a specific artifact (Plan #170)",
                    "cost": self.methods["get_invokers"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "artifact_id": {
                                "type": "string",
                                "description": "ID of the artifact to query invokers for"
                            }
                        },
                        "required": ["artifact_id"]
                    }
                }
            ]
        }
