"""Tests for dashboard event parser.

Required tests per Plan #149:
- test_parse_action_event: Parses action events correctly
- test_parse_resource_event: Parses resource events correctly
- test_parse_unknown_event: Handles unknown events gracefully
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.dashboard.core_v2.event_parser import EventParser
from src.dashboard.models_v2.events import (
    ActionEvent,
    ResourceConsumedEvent,
    ResourceAllocatedEvent,
    ResourceSpentEvent,
    TickEvent,
    ThinkingEvent,
    EventEnvelope,
)


class TestParseActionEvent:
    """Tests for parsing action events."""

    def test_parse_action_event(self) -> None:
        """Parses action events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "action",
                "sequence": 42,
                "agent_id": "agent_alpha",
                "action_type": "invoke",
                "target": "genesis_ledger",
                "success": True,
                "duration_ms": 150,
            }
        )

        event = parser.parse_line(line)

        assert event is not None
        assert isinstance(event, ActionEvent)
        assert event.event_type == "action"
        assert event.sequence == 42
        assert event.agent_id == "agent_alpha"
        assert event.action_type == "invoke"
        assert event.target == "genesis_ledger"
        assert event.success is True
        assert event.duration_ms == 150

    def test_parse_action_with_principal_id(self) -> None:
        """Action events can use principal_id instead of agent_id."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "action",
                "sequence": 1,
                "principal_id": "agent_beta",
                "action_type": "read_artifact",
                "target": "some_artifact",
                "success": True,
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, ActionEvent)
        assert event.principal_id == "agent_beta"

    def test_parse_action_with_error(self) -> None:
        """Action events can include error information."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "action",
                "sequence": 1,
                "agent_id": "agent_alpha",
                "action_type": "invoke",
                "success": False,
                "error": "Permission denied",
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, ActionEvent)
        assert event.success is False
        assert event.error == "Permission denied"


class TestParseResourceEvent:
    """Tests for parsing resource events."""

    def test_parse_resource_consumed_event(self) -> None:
        """Parses resource_consumed events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "resource_consumed",
                "sequence": 42,
                "principal_id": "agent_alpha",
                "resource": "llm_tokens",
                "amount": 1500,
                "balance_after": 8500,
                "quota": 10000,
                "rate_window_remaining": 6500,
            }
        )

        event = parser.parse_line(line)

        assert event is not None
        assert isinstance(event, ResourceConsumedEvent)
        assert event.principal_id == "agent_alpha"
        assert event.resource == "llm_tokens"
        assert event.amount == 1500
        assert event.balance_after == 8500
        assert event.quota == 10000
        assert event.rate_window_remaining == 6500

    def test_parse_resource_allocated_event(self) -> None:
        """Parses resource_allocated events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "resource_allocated",
                "sequence": 43,
                "principal_id": "agent_alpha",
                "resource": "disk",
                "amount": 2048,
                "used_after": 5120,
                "quota": 10000,
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, ResourceAllocatedEvent)
        assert event.resource == "disk"
        assert event.amount == 2048
        assert event.used_after == 5120
        assert event.quota == 10000

    def test_parse_resource_spent_event(self) -> None:
        """Parses resource_spent events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "resource_spent",
                "sequence": 44,
                "principal_id": "agent_alpha",
                "resource": "llm_budget",
                "amount": 0.05,
                "balance_after": 0.95,
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, ResourceSpentEvent)
        assert event.resource == "llm_budget"
        assert event.amount == 0.05
        assert event.balance_after == 0.95


class TestParseUnknownEvent:
    """Tests for handling unknown events."""

    def test_parse_unknown_event(self) -> None:
        """Handles unknown events gracefully - returns generic envelope."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "some_future_event_type",
                "sequence": 99,
                "custom_field": "custom_value",
            }
        )

        event = parser.parse_line(line)

        assert event is not None
        assert isinstance(event, EventEnvelope)
        assert event.event_type == "some_future_event_type"
        assert event.sequence == 99
        # Extra fields should be preserved
        assert getattr(event, "custom_field", None) == "custom_value"

    def test_parse_empty_line(self) -> None:
        """Empty lines return None."""
        parser = EventParser()
        assert parser.parse_line("") is None
        assert parser.parse_line("   ") is None
        assert parser.parse_line("\n") is None

    def test_parse_invalid_json(self) -> None:
        """Invalid JSON returns None and increments error count."""
        parser = EventParser()
        assert parser.parse_line("not valid json") is None
        assert parser.parse_errors == 1

    def test_parse_non_dict_json(self) -> None:
        """Non-dict JSON returns None."""
        parser = EventParser()
        assert parser.parse_line('"just a string"') is None
        assert parser.parse_line("[1, 2, 3]") is None


class TestParseOtherEvents:
    """Tests for other event types."""

    def test_parse_tick_event(self) -> None:
        """Parses tick events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "tick",
                "sequence": 10,
                "tick": 10,
                "simulation_time": 60.5,
                "total_scrip": 1000,
                "total_artifacts": 25,
                "active_agents": 3,
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, TickEvent)
        assert event.simulation_time == 60.5
        assert event.total_scrip == 1000
        assert event.total_artifacts == 25
        assert event.active_agents == 3

    def test_parse_thinking_event(self) -> None:
        """Parses thinking events correctly."""
        parser = EventParser()
        line = json.dumps(
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "event_type": "thinking",
                "sequence": 5,
                "agent_id": "agent_alpha",
                "phase": "observe",
                "thinking": "I see 3 artifacts available...",
            }
        )

        event = parser.parse_line(line)

        assert isinstance(event, ThinkingEvent)
        assert event.agent_id == "agent_alpha"
        assert event.phase == "observe"
        assert event.thinking == "I see 3 artifacts available..."


class TestParseFile:
    """Tests for file parsing."""

    def test_parse_file(self) -> None:
        """Can parse a JSONL file."""
        parser = EventParser()

        events_data = [
            {"timestamp": "2026-01-25T12:00:00Z", "event_type": "tick", "sequence": 1},
            {
                "timestamp": "2026-01-25T12:00:01Z",
                "event_type": "action",
                "sequence": 2,
                "agent_id": "agent_alpha",
                "action_type": "read_artifact",
                "success": True,
            },
            {"timestamp": "2026-01-25T12:00:02Z", "event_type": "tick", "sequence": 3},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for event in events_data:
                f.write(json.dumps(event) + "\n")
            temp_path = f.name

        try:
            events = list(parser.parse_file(temp_path))
            assert len(events) == 3
            assert events[0].event_type == "tick"
            assert events[1].event_type == "action"
            assert events[2].event_type == "tick"
            assert parser.events_parsed == 3
        finally:
            Path(temp_path).unlink()

    def test_parse_nonexistent_file(self) -> None:
        """Parsing nonexistent file yields no events."""
        parser = EventParser()
        events = list(parser.parse_file("/nonexistent/path/file.jsonl"))
        assert events == []


class TestParserStats:
    """Tests for parser statistics."""

    def test_stats_tracking(self) -> None:
        """Parser tracks events parsed and errors."""
        parser = EventParser()

        # Parse valid events
        parser.parse_line('{"event_type": "tick", "timestamp": "T", "sequence": 1}')
        parser.parse_line('{"event_type": "tick", "timestamp": "T", "sequence": 2}')

        # Parse invalid events
        parser.parse_line("invalid json")
        parser.parse_line("also invalid")

        assert parser.events_parsed == 2
        assert parser.parse_errors == 2

    def test_reset_stats(self) -> None:
        """Can reset parser statistics."""
        parser = EventParser()
        parser.parse_line('{"event_type": "tick", "timestamp": "T", "sequence": 1}')
        parser.parse_line("invalid")

        parser.reset_stats()

        assert parser.events_parsed == 0
        assert parser.parse_errors == 0
