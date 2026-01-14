"""Integration tests for action logging with reasoning (Plan #49)"""

import tempfile
from typing import Any

import pytest

from src.world.actions import NoopIntent, InvokeArtifactIntent
from src.world.world import World


def make_test_world(output_file: str) -> World:
    """Create a minimal World for testing."""
    config: dict[str, Any] = {
        "world": {"max_ticks": 10},
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 1},
        "logging": {"output_file": output_file},
        "principals": [
            {"id": "agent1", "starting_scrip": 100},
            {"id": "agent2", "starting_scrip": 100},
        ],
        "rights": {
            "default_quotas": {"compute": 1000.0, "disk": 10000.0}
        },
    }
    return World(config)


class TestActionEventReasoning:
    """Test that action events include reasoning in the log"""

    def test_action_event_includes_reasoning(self) -> None:
        """Action events logged via _log_action include reasoning field"""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Execute a noop action with reasoning
        intent = NoopIntent("agent1", reasoning="Testing the system before doing real work")
        world.execute_action(intent)

        # Read the logged events
        events = world.logger.read_recent(50)

        # Find the action event
        action_events = [e for e in events if e.get("event_type") == "action"]
        assert len(action_events) >= 1, "Expected at least one action event"

        action_event = action_events[-1]  # Get the last action event

        # Verify reasoning is in the intent
        assert "intent" in action_event
        assert "reasoning" in action_event["intent"]
        assert action_event["intent"]["reasoning"] == "Testing the system before doing real work"

    def test_action_event_empty_reasoning(self) -> None:
        """Action events include empty reasoning when not provided"""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Execute without reasoning
        intent = NoopIntent("agent1")
        world.execute_action(intent)

        events = world.logger.read_recent(50)

        action_events = [e for e in events if e.get("event_type") == "action"]
        assert len(action_events) >= 1

        action_event = action_events[-1]
        assert "reasoning" in action_event["intent"]
        assert action_event["intent"]["reasoning"] == ""

    def test_invoke_action_includes_reasoning(self) -> None:
        """Invoke artifact actions include reasoning in log"""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_file = f.name

        world = make_test_world(output_file)
        world.advance_tick()

        # Execute an invoke action with reasoning
        intent = InvokeArtifactIntent(
            principal_id="agent1",
            artifact_id="genesis_ledger",
            method="balance",
            args=["agent1"],
            reasoning="Checking my balance to plan next trade"
        )
        world.execute_action(intent)

        events = world.logger.read_recent(50)

        action_events = [e for e in events if e.get("event_type") == "action"]
        assert len(action_events) >= 1

        action_event = action_events[-1]
        assert action_event["intent"]["reasoning"] == "Checking my balance to plan next trade"
        assert action_event["intent"]["artifact_id"] == "genesis_ledger"
        assert action_event["intent"]["method"] == "balance"
