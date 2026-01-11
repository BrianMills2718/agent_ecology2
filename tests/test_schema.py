"""Unit tests for action schema validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agents.schema import validate_action_json, ActionType


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


class TestResourcePolicyValidation:
    """Tests for resource_policy validation in parse_intent_from_json."""

    def test_valid_resource_policy_caller_pays(self) -> None:
        """resource_policy 'caller_pays' is valid."""
        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "my_tool",
            "artifact_type": "code",
            "content": "A service",
            "executable": true,
            "price": 10,
            "code": "def run(args, ctx): return {}",
            "resource_policy": "caller_pays"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["resource_policy"] == "caller_pays"

    def test_valid_resource_policy_owner_pays(self) -> None:
        """resource_policy 'owner_pays' is valid."""
        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "premium_tool",
            "artifact_type": "code",
            "content": "Premium service",
            "executable": true,
            "price": 50,
            "code": "def run(args, ctx): return {}",
            "resource_policy": "owner_pays"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        assert result["resource_policy"] == "owner_pays"

    def test_resource_policy_default_when_omitted(self) -> None:
        """resource_policy defaults when not specified."""
        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "tool",
            "artifact_type": "code",
            "content": "Service",
            "executable": true,
            "price": 10,
            "code": "def run(args, ctx): return {}"
        }'''
        result = validate_action_json(json_str)
        assert isinstance(result, dict)
        # resource_policy not in schema validation, only in parse_intent_from_json
        # So it's just not present in the validated dict
        assert result.get("resource_policy") is None


class TestResourcePolicyParseIntent:
    """Tests for resource_policy in parse_intent_from_json."""

    def test_parse_intent_with_resource_policy(self) -> None:
        """parse_intent_from_json handles resource_policy."""
        from world.actions import parse_intent_from_json, WriteArtifactIntent

        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "premium",
            "artifact_type": "code",
            "content": "Premium service",
            "executable": true,
            "price": 50,
            "code": "def run(args, ctx): return {}",
            "resource_policy": "owner_pays"
        }'''
        result = parse_intent_from_json("agent_1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.resource_policy == "owner_pays"

    def test_parse_intent_default_resource_policy(self) -> None:
        """parse_intent_from_json defaults to caller_pays."""
        from world.actions import parse_intent_from_json, WriteArtifactIntent

        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "basic",
            "artifact_type": "code",
            "content": "Basic service",
            "executable": true,
            "price": 10,
            "code": "def run(args, ctx): return {}"
        }'''
        result = parse_intent_from_json("agent_1", json_str)
        assert isinstance(result, WriteArtifactIntent)
        assert result.resource_policy == "caller_pays"

    def test_parse_intent_invalid_resource_policy(self) -> None:
        """parse_intent_from_json rejects invalid resource_policy."""
        from world.actions import parse_intent_from_json

        json_str = '''{
            "action_type": "write_artifact",
            "artifact_id": "invalid",
            "artifact_type": "code",
            "content": "Invalid policy",
            "executable": true,
            "price": 10,
            "code": "def run(args, ctx): return {}",
            "resource_policy": "invalid_value"
        }'''
        result = parse_intent_from_json("agent_1", json_str)
        assert isinstance(result, str)  # Error message
        assert "caller_pays" in result and "owner_pays" in result
