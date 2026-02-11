"""Tests for ActionIntent reasoning field (Plan #49)

TDD tests for adding reasoning to the narrow waist.
"""

import json

import pytest

from src.world.actions import (
    ActionIntent,
    ActionType,
    DeleteArtifactIntent,
    EditArtifactIntent,
    InvokeArtifactIntent,
    NoopIntent,
    ReadArtifactIntent,
    UpdateMetadataIntent,
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

    def test_edit_intent_accepts_reasoning(self) -> None:
        """EditArtifactIntent should accept and store reasoning (Plan #131)"""
        intent = EditArtifactIntent(
            principal_id="agent1",
            artifact_id="my_doc",
            old_string="old value",
            new_string="new value",
            reasoning="Fixing typo in document"
        )

        assert intent.reasoning == "Fixing typo in document"
        assert intent.artifact_id == "my_doc"
        assert intent.old_string == "old value"
        assert intent.new_string == "new value"
        assert intent.action_type == ActionType.EDIT_ARTIFACT

    def test_reasoning_defaults_to_empty_string(self) -> None:
        """All intents should default reasoning to empty string"""
        noop = NoopIntent("agent1")
        read = ReadArtifactIntent("agent1", "artifact1")
        write = WriteArtifactIntent("agent1", "artifact1", "generic", "content")
        edit = EditArtifactIntent("agent1", "artifact1", "old", "new")
        invoke = InvokeArtifactIntent("agent1", "artifact1", "method")

        assert noop.reasoning == ""
        assert read.reasoning == ""
        assert write.reasoning == ""
        assert edit.reasoning == ""
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

    def test_parse_edit_intent_with_reasoning(self) -> None:
        """parse_intent_from_json should extract reasoning for edit_artifact (Plan #131)"""
        json_str = '{"action_type": "edit_artifact", "artifact_id": "my_doc", "old_string": "old text", "new_string": "new text", "reasoning": "Fixing typo"}'
        intent = parse_intent_from_json("agent1", json_str)

        assert isinstance(intent, EditArtifactIntent)
        assert intent.reasoning == "Fixing typo"
        assert intent.artifact_id == "my_doc"
        assert intent.old_string == "old text"
        assert intent.new_string == "new text"


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

    def test_edit_intent_to_dict_includes_reasoning(self) -> None:
        """EditArtifactIntent.to_dict() should include reasoning (Plan #131)"""
        intent = EditArtifactIntent(
            "agent1", "my_doc", "old text", "new text",
            reasoning="Fixing typo"
        )
        result = intent.to_dict()

        assert result["reasoning"] == "Fixing typo"
        assert result["artifact_id"] == "my_doc"
        assert result["old_string"] == "old text"
        assert result["new_string"] == "new text"

    def test_empty_reasoning_still_in_dict(self) -> None:
        """Even empty reasoning should be in to_dict() output"""
        intent = NoopIntent("agent1")
        result = intent.to_dict()

        assert "reasoning" in result
        assert result["reasoning"] == ""


class TestEditArtifactParsing:
    """Tests for edit_artifact parsing validation (Plan #131)"""

    def test_parse_edit_requires_artifact_id(self) -> None:
        """edit_artifact requires artifact_id"""
        json_str = '{"action_type": "edit_artifact", "old_string": "old", "new_string": "new"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "artifact_id" in result.lower()

    def test_parse_edit_requires_old_string(self) -> None:
        """edit_artifact requires old_string"""
        json_str = '{"action_type": "edit_artifact", "artifact_id": "doc", "new_string": "new"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "old_string" in result.lower()

    def test_parse_edit_requires_new_string(self) -> None:
        """edit_artifact requires new_string"""
        json_str = '{"action_type": "edit_artifact", "artifact_id": "doc", "old_string": "old"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "new_string" in result.lower()

    def test_parse_edit_rejects_same_strings(self) -> None:
        """edit_artifact rejects when old_string equals new_string"""
        json_str = '{"action_type": "edit_artifact", "artifact_id": "doc", "old_string": "same", "new_string": "same"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "different" in result.lower() or "same" in result.lower()

    def test_parse_edit_valid_intent(self) -> None:
        """edit_artifact with all required fields creates valid intent"""
        json_str = '{"action_type": "edit_artifact", "artifact_id": "doc", "old_string": "old", "new_string": "new"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, EditArtifactIntent)
        assert result.artifact_id == "doc"
        assert result.old_string == "old"
        assert result.new_string == "new"
        assert result.principal_id == "agent1"

    def test_edit_intent_to_dict_truncates_long_strings(self) -> None:
        """EditArtifactIntent.to_dict() should truncate long old_string/new_string"""
        long_string = "x" * 200
        intent = EditArtifactIntent(
            "agent1", "doc", long_string, long_string + "y"
        )
        result = intent.to_dict()

        # Should be truncated to ~100 chars with "..."
        assert len(result["old_string"]) < 110
        assert result["old_string"].endswith("...")
        assert len(result["new_string"]) < 110
        assert result["new_string"].endswith("...")


class TestWriteArtifactAccessContractParsing:
    """Tests for access_contract_id extraction in write_artifact parsing."""

    def test_parse_write_extracts_access_contract_id(self) -> None:
        """parse_intent_from_json should extract access_contract_id for write_artifact."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_doc",
            "artifact_type": "data",
            "content": "hello",
            "access_contract_id": "my_contract",
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.access_contract_id == "my_contract"

    def test_parse_write_access_contract_id_defaults_to_none(self) -> None:
        """access_contract_id defaults to None when not provided."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_doc",
            "artifact_type": "data",
            "content": "hello",
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.access_contract_id is None

    def test_parse_write_rejects_non_string_access_contract_id(self) -> None:
        """Non-string access_contract_id returns validation error."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_doc",
            "artifact_type": "data",
            "content": "hello",
            "access_contract_id": 123,
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, str)
        assert "access_contract_id" in result


class TestWriteArtifactDictContentSerialization:
    """Tests for auto-serialization of dict/list content in write_artifact."""

    def test_parse_write_serializes_dict_content(self) -> None:
        """Dict content should be auto-serialized to JSON string."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_data",
            "artifact_type": "json",
            "content": {"key": "value", "count": 42},
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.content == '{"key": "value", "count": 42}'

    def test_parse_write_serializes_list_content(self) -> None:
        """List content should be auto-serialized to JSON string."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_list",
            "artifact_type": "json",
            "content": [1, 2, 3],
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.content == "[1, 2, 3]"

    def test_parse_write_string_content_unchanged(self) -> None:
        """String content should pass through unchanged."""
        json_str = json.dumps({
            "action_type": "write_artifact",
            "artifact_id": "my_doc",
            "artifact_type": "text",
            "content": "hello world",
        })
        result = parse_intent_from_json("agent1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.content == "hello world"


@pytest.mark.plans([308])
class TestUpdateMetadataParsing:
    """Tests for update_metadata parsing validation (Plan #308)"""

    def test_parse_update_metadata_requires_artifact_id(self) -> None:
        """update_metadata requires artifact_id"""
        json_str = '{"action_type": "update_metadata", "key": "tag", "value": "v1"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "artifact_id" in result.lower()

    def test_parse_update_metadata_requires_key(self) -> None:
        """update_metadata requires key"""
        json_str = '{"action_type": "update_metadata", "artifact_id": "doc", "value": "v1"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, str)
        assert "key" in result.lower()

    def test_parse_update_metadata_valid_intent(self) -> None:
        """update_metadata with all required fields creates valid intent"""
        json_str = '{"action_type": "update_metadata", "artifact_id": "doc", "key": "tag", "value": "v1"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, UpdateMetadataIntent)
        assert result.artifact_id == "doc"
        assert result.key == "tag"
        assert result.value == "v1"
        assert result.principal_id == "agent1"

    def test_parse_update_metadata_value_defaults_to_none(self) -> None:
        """update_metadata without value defaults to None (key deletion)"""
        json_str = '{"action_type": "update_metadata", "artifact_id": "doc", "key": "tag"}'
        result = parse_intent_from_json("agent1", json_str)

        assert isinstance(result, UpdateMetadataIntent)
        assert result.value is None
