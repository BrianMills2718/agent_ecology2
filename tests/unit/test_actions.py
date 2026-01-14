"""Tests for ActionIntent reasoning field (Plan #49)

TDD tests for adding reasoning to the narrow waist.
"""

import pytest

from src.world.actions import (
    ActionIntent,
    ActionType,
    InvokeArtifactIntent,
    NoopIntent,
    ReadArtifactIntent,
    WriteArtifactIntent,
    parse_intent_from_json,
)


class TestActionIntentReasoning:
    """Tests for reasoning field in ActionIntent and subclasses (Plan #49)"""

    def test_action_intent_has_reasoning_field(self) -> None:
        """ActionIntent base class should have reasoning attribute"""
        # Create a basic ActionIntent
        intent = ActionIntent(ActionType.NOOP, "agent1")

        # Should have reasoning field, defaulting to empty string
        assert hasattr(intent, "reasoning")
        assert intent.reasoning == ""

    def test_noop_intent_accepts_reasoning(self) -> None:
        """NoopIntent should accept and store reasoning"""
        intent = NoopIntent("agent1", reasoning="Testing the system")

        assert intent.reasoning == "Testing the system"
        assert intent.action_type == ActionType.NOOP
        assert intent.principal_id == "agent1"

    def test_read_intent_accepts_reasoning(self) -> None:
        """ReadArtifactIntent should accept and store reasoning"""
        intent = ReadArtifactIntent(
            "agent1",
            "my_artifact",
            reasoning="Need to check artifact content"
        )

        assert intent.reasoning == "Need to check artifact content"
        assert intent.artifact_id == "my_artifact"

    def test_write_intent_accepts_reasoning(self) -> None:
        """WriteArtifactIntent should accept and store reasoning"""
        intent = WriteArtifactIntent(
            principal_id="agent1",
            artifact_id="my_tool",
            artifact_type="tool",
            content="def run(): pass",
            reasoning="Creating a new tool for trading"
        )

        assert intent.reasoning == "Creating a new tool for trading"
        assert intent.artifact_id == "my_tool"

    def test_invoke_intent_accepts_reasoning(self) -> None:
        """InvokeArtifactIntent should accept and store reasoning"""
        intent = InvokeArtifactIntent(
            principal_id="agent1",
            artifact_id="genesis_ledger",
            method="transfer",
            args=["agent1", "agent2", 100],
            reasoning="Paying for services rendered"
        )

        assert intent.reasoning == "Paying for services rendered"
        assert intent.artifact_id == "genesis_ledger"
        assert intent.method == "transfer"

    def test_reasoning_defaults_to_empty_string(self) -> None:
        """All intents should default reasoning to empty string"""
        noop = NoopIntent("agent1")
        read = ReadArtifactIntent("agent1", "artifact1")
        write = WriteArtifactIntent("agent1", "artifact1", "generic", "content")
        invoke = InvokeArtifactIntent("agent1", "artifact1", "method")

        assert noop.reasoning == ""
        assert read.reasoning == ""
        assert write.reasoning == ""
        assert invoke.reasoning == ""


class TestParseIntentReasoning:
    """Tests for reasoning extraction in parse_intent_from_json"""

    def test_parse_intent_extracts_reasoning(self) -> None:
        """parse_intent_from_json should extract reasoning from JSON"""
        json_str = '{"action_type": "noop", "reasoning": "Just waiting this tick"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, NoopIntent)
        assert intent.reasoning == "Just waiting this tick"

    def test_parse_intent_default_reasoning(self) -> None:
        """parse_intent_from_json should default reasoning to empty string"""
        json_str = '{"action_type": "noop"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, NoopIntent)
        assert intent.reasoning == ""

    def test_parse_read_intent_with_reasoning(self) -> None:
        """parse_intent_from_json should extract reasoning for read_artifact"""
        json_str = '{"action_type": "read_artifact", "artifact_id": "tool1", "reasoning": "Checking tool interface"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, ReadArtifactIntent)
        assert intent.reasoning == "Checking tool interface"

    def test_parse_write_intent_with_reasoning(self) -> None:
        """parse_intent_from_json should extract reasoning for write_artifact"""
        json_str = '{"action_type": "write_artifact", "artifact_id": "my_data", "artifact_type": "data", "content": "hello", "reasoning": "Storing results"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, WriteArtifactIntent)
        assert intent.reasoning == "Storing results"

    def test_parse_invoke_intent_with_reasoning(self) -> None:
        """parse_intent_from_json should extract reasoning for invoke_artifact"""
        json_str = '{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "balance", "args": ["agent1"], "reasoning": "Checking my balance"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, InvokeArtifactIntent)
        assert intent.reasoning == "Checking my balance"


class TestIntentToDictReasoning:
    """Tests for reasoning in to_dict() output"""

    def test_intent_to_dict_includes_reasoning(self) -> None:
        """to_dict() should include reasoning field"""
        intent = NoopIntent("agent1", reasoning="Test reasoning")
        result = intent.to_dict()

        assert "reasoning" in result
        assert result["reasoning"] == "Test reasoning"

    def test_read_intent_to_dict_includes_reasoning(self) -> None:
        """ReadArtifactIntent.to_dict() should include reasoning"""
        intent = ReadArtifactIntent("agent1", "artifact1", reasoning="Need data")
        result = intent.to_dict()

        assert result["reasoning"] == "Need data"

    def test_write_intent_to_dict_includes_reasoning(self) -> None:
        """WriteArtifactIntent.to_dict() should include reasoning"""
        intent = WriteArtifactIntent(
            "agent1", "artifact1", "generic", "content",
            reasoning="Saving state"
        )
        result = intent.to_dict()

        assert result["reasoning"] == "Saving state"

    def test_invoke_intent_to_dict_includes_reasoning(self) -> None:
        """InvokeArtifactIntent.to_dict() should include reasoning"""
        intent = InvokeArtifactIntent(
            "agent1", "genesis_ledger", "transfer", ["a", "b", 10],
            reasoning="Payment for service"
        )
        result = intent.to_dict()

        assert result["reasoning"] == "Payment for service"

    def test_empty_reasoning_still_in_dict(self) -> None:
        """Even empty reasoning should be in to_dict() output"""
        intent = NoopIntent("agent1")
        result = intent.to_dict()

        assert "reasoning" in result
        assert result["reasoning"] == ""
