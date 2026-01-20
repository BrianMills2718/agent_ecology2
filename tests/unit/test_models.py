"""Unit tests for Pydantic action models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agents.models import (
    NoopAction,
    ReadArtifactAction,
    WriteArtifactAction,
    InvokeArtifactAction,
    ActionResponse,
    PolicyDict,
    _coerce_action,
)


class TestNoopAction:
    """Tests for NoopAction model."""

    def test_noop_action_valid(self) -> None:
        """NoopAction can be created with default action_type."""
        action = NoopAction()
        assert action.action_type == "noop"

    def test_noop_action_explicit(self) -> None:
        """NoopAction can be created with explicit action_type."""
        action = NoopAction(action_type="noop")
        assert action.action_type == "noop"


class TestReadArtifactAction:
    """Tests for ReadArtifactAction model."""

    def test_read_artifact_action_valid(self) -> None:
        """ReadArtifactAction can be created with artifact_id."""
        action = ReadArtifactAction(artifact_id="genesis_ledger")
        assert action.action_type == "read_artifact"
        assert action.artifact_id == "genesis_ledger"

    def test_read_artifact_missing_id(self) -> None:
        """ReadArtifactAction requires artifact_id."""
        with pytest.raises(ValidationError) as exc_info:
            ReadArtifactAction()
        assert "artifact_id" in str(exc_info.value)


class TestWriteArtifactAction:
    """Tests for WriteArtifactAction model."""

    def test_write_artifact_action_valid(self) -> None:
        """WriteArtifactAction can be created with required fields."""
        action = WriteArtifactAction(
            artifact_id="my_notes",
            content="Hello world"
        )
        assert action.action_type == "write_artifact"
        assert action.artifact_id == "my_notes"
        assert action.content == "Hello world"
        assert action.artifact_type == "data"
        assert action.executable is False
        assert action.price == 0
        assert action.code == ""

    def test_write_artifact_with_all_fields(self) -> None:
        """WriteArtifactAction can be created with all optional fields."""
        policy = PolicyDict(read_price=5, invoke_price=10)
        action = WriteArtifactAction(
            artifact_id="my_tool",
            artifact_type="executable",
            content="A calculator tool",
            executable=True,
            price=15,
            code="def run(*args): return sum(args)",
            policy=policy
        )
        assert action.artifact_id == "my_tool"
        assert action.artifact_type == "executable"
        assert action.executable is True
        assert action.price == 15
        assert action.code == "def run(*args): return sum(args)"
        assert action.policy.read_price == 5
        assert action.policy.invoke_price == 10

    def test_write_artifact_executable_requires_code(self) -> None:
        """WriteArtifactAction with executable=True requires non-empty code."""
        with pytest.raises(ValidationError) as exc_info:
            WriteArtifactAction(
                artifact_id="my_tool",
                content="A tool",
                executable=True,
                code=""
            )
        assert "code is required when executable=True" in str(exc_info.value)

    def test_write_artifact_executable_with_code(self) -> None:
        """WriteArtifactAction with executable=True and code is valid."""
        action = WriteArtifactAction(
            artifact_id="my_tool",
            content="A tool",
            executable=True,
            code="def run(): pass"
        )
        assert action.executable is True
        assert action.code == "def run(): pass"


class TestInvokeArtifactAction:
    """Tests for InvokeArtifactAction model."""

    def test_invoke_artifact_action_valid(self) -> None:
        """InvokeArtifactAction can be created with required fields."""
        action = InvokeArtifactAction(
            artifact_id="genesis_ledger",
            method="balance"
        )
        assert action.action_type == "invoke_artifact"
        assert action.artifact_id == "genesis_ledger"
        assert action.method == "balance"
        assert action.args == []

    def test_invoke_artifact_with_args(self) -> None:
        """InvokeArtifactAction can be created with args."""
        action = InvokeArtifactAction(
            artifact_id="genesis_ledger",
            method="transfer",
            args=["agent_001", "agent_002", 50]
        )
        assert action.artifact_id == "genesis_ledger"
        assert action.method == "transfer"
        assert action.args == ["agent_001", "agent_002", 50]

    def test_invoke_artifact_missing_method(self) -> None:
        """InvokeArtifactAction requires method."""
        with pytest.raises(ValidationError) as exc_info:
            InvokeArtifactAction(artifact_id="genesis_ledger")
        assert "method" in str(exc_info.value)


class TestActionResponse:
    """Tests for ActionResponse model."""

    def test_action_response_valid(self) -> None:
        """ActionResponse can be created with reasoning and action."""
        response = ActionResponse(
            reasoning="I should do nothing this tick.",
            action=NoopAction()
        )
        assert response.reasoning == "I should do nothing this tick."
        assert response.action.action_type == "noop"

    def test_action_response_with_dict_action(self) -> None:
        """ActionResponse coerces dict to appropriate action type."""
        response = ActionResponse(
            reasoning="Reading the ledger.",
            action={"action_type": "read_artifact", "artifact_id": "genesis_ledger"}
        )
        assert response.reasoning == "Reading the ledger."
        assert response.action.action_type == "read_artifact"
        assert response.action.artifact_id == "genesis_ledger"

    def test_action_response_coerces_all_action_types(self) -> None:
        """ActionResponse coerces all action types from dicts."""
        # Test noop
        resp_noop = ActionResponse(
            reasoning="Noop",
            action={"action_type": "noop"}
        )
        assert resp_noop.action.action_type == "noop"

        # Test write_artifact
        resp_write = ActionResponse(
            reasoning="Writing",
            action={
                "action_type": "write_artifact",
                "artifact_id": "test",
                "content": "data"
            }
        )
        assert resp_write.action.action_type == "write_artifact"

        # Test invoke_artifact
        resp_invoke = ActionResponse(
            reasoning="Invoking",
            action={
                "action_type": "invoke_artifact",
                "artifact_id": "test",
                "method": "run"
            }
        )
        assert resp_invoke.action.action_type == "invoke_artifact"


class TestInvalidActionType:
    """Tests for invalid action type handling."""

    def test_invalid_action_type_rejected(self) -> None:
        """Unknown action_type in dict is rejected by coercion."""
        # The _coerce_action function returns the dict unchanged for unknown types
        # This will then fail Pydantic validation
        with pytest.raises(ValidationError):
            ActionResponse(
                reasoning="Unknown action",
                action={"action_type": "unknown_action", "data": "test"}
            )


class TestPolicyDict:
    """Tests for PolicyDict model."""

    def test_policy_dict_defaults(self) -> None:
        """PolicyDict has correct default values."""
        policy = PolicyDict()
        assert policy.read_price == 0
        assert policy.invoke_price == 0
        assert policy.allow_read == ["*"]
        assert policy.allow_write == []
        assert policy.allow_invoke == ["*"]

    def test_policy_dict_custom_values(self) -> None:
        """PolicyDict accepts custom values."""
        policy = PolicyDict(
            read_price=10,
            invoke_price=20,
            allow_read=["agent_001", "agent_002"],
            allow_write=["agent_001"],
            allow_invoke=[]
        )
        assert policy.read_price == 10
        assert policy.invoke_price == 20
        assert policy.allow_read == ["agent_001", "agent_002"]
        assert policy.allow_write == ["agent_001"]
        assert policy.allow_invoke == []
