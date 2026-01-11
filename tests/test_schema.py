"""Unit tests for action schema validation."""

from pathlib import Path

from src.agents.schema import validate_action_json, ActionType


class TestValidActions:
    """Tests for valid action JSON inputs."""

    def test_valid_noop(self) -> None:
        """Valid noop action passes validation."""
        json_str = '{"action_type": "noop"}'
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "noop"

    def test_valid_read_artifact(self) -> None:
        """Valid read_artifact action passes validation."""
        json_str = '{"action_type": "read_artifact", "artifact_id": "genesis_ledger"}'
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "read_artifact"
        assert result["artifact_id"] == "genesis_ledger"

    def test_valid_write_artifact(self) -> None:
        """Valid write_artifact action passes validation."""
        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "my_notes",
            "artifact_type": "text",
            "content": "Hello world"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "write_artifact"
        assert result["artifact_id"] == "my_notes"
        assert result["content"] == "Hello world"

    def test_valid_write_executable(self) -> None:
        """Valid executable artifact passes validation."""
        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "my_tool",
            "artifact_type": "executable",
            "content": "A simple calculator",
            "executable": true,
            "price": 5,
            "code": "def run(*args):\\n    return sum(args)"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "write_artifact"
        assert result["artifact_id"] == "my_tool"
        assert result["executable"] is True
        assert result["price"] == 5
        assert "def run" in result["code"]

    def test_valid_invoke_artifact(self) -> None:
        """Valid invoke_artifact action passes validation."""
        json_str = '''{
            "action_type": "invoke_artifact",
            "artifact_id": "genesis_ledger",
            "method": "balance",
            "args": ["agent_001"]
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "invoke_artifact"
        assert result["artifact_id"] == "genesis_ledger"
        assert result["method"] == "balance"
        assert result["args"] == ["agent_001"]


class TestInvalidActions:
    """Tests for invalid action JSON inputs."""

    def test_invalid_json(self) -> None:
        """Malformed JSON returns error string."""
        json_str = '{"action_type": "noop",}'  # Trailing comma is invalid JSON
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "Invalid JSON" in result

    def test_missing_action_type(self) -> None:
        """Missing action_type field returns error."""
        json_str = '{"artifact_id": "test"}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "Invalid action_type" in result

    def test_invalid_action_type(self) -> None:
        """Unknown action type returns error (tests Literal enforcement)."""
        json_str = '{"action_type": "unknown_action"}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "Invalid action_type" in result
        assert "unknown_action" in result

    def test_missing_required_field(self) -> None:
        """Missing artifact_id returns error."""
        json_str = '{"action_type": "read_artifact"}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "requires 'artifact_id'" in result

    def test_typo_action_type(self) -> None:
        """Typo like 'trasfer' returns error."""
        json_str = '{"action_type": "trasfer", "from": "a", "to": "b", "amount": 10}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "Invalid action_type" in result
        assert "trasfer" in result


class TestEdgeCases:
    """Tests for edge cases and special handling."""

    def test_transfer_deprecation_message(self) -> None:
        """Transfer action type returns helpful deprecation message."""
        json_str = '{"action_type": "transfer", "from": "a", "to": "b", "amount": 10}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "transfer is not a kernel action" in result
        assert "invoke_artifact" in result

    def test_invoke_missing_method(self) -> None:
        """invoke_artifact without method returns error."""
        json_str = '{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger"}'
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "requires 'method'" in result

    def test_invoke_args_not_list(self) -> None:
        """invoke_artifact with non-list args returns error."""
        json_str = '''{
            "action_type": "invoke_artifact",
            "artifact_id": "genesis_ledger",
            "method": "balance",
            "args": "not_a_list"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "'args' must be a list" in result

    def test_markdown_code_block_handling(self) -> None:
        """JSON wrapped in markdown code block is properly parsed."""
        json_str = '''```json
{"action_type": "noop"}
```'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "noop"

    def test_json_with_surrounding_text(self) -> None:
        """JSON with surrounding text is properly extracted."""
        json_str = 'Here is my action: {"action_type": "noop"} That is all.'
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["action_type"] == "noop"

    def test_no_json_object_found(self) -> None:
        """Response without JSON object returns error."""
        json_str = "I don't know what to do."
        result = validate_action_json(json_str)
        assert isinstance(result, str)
        assert "No JSON object found" in result

    def test_action_type_case_insensitive(self) -> None:
        """action_type is normalized to lowercase."""
        json_str = '{"action_type": "NOOP"}'
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        # The function lowercases action_type for comparison but returns original data
        assert result["action_type"] == "NOOP"
