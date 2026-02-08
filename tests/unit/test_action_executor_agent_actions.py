"""Tests for agent self-modification actions in action_executor (Plan #241).

Regression tests for subscribe, unsubscribe, configure_context, and
modify_system_prompt handlers. These actions update the agent's own artifact
and previously crashed due to accessing `agent_artifact.artifact_type`
instead of `agent_artifact.type`.
"""

import json
from pathlib import Path

import pytest

from src.world.world import World
from src.world.actions import (
    ActionResult,
    SubscribeArtifactIntent,
    UnsubscribeArtifactIntent,
    ConfigureContextIntent,
    ModifySystemPromptIntent,
    WriteArtifactIntent,
    UpdateMetadataIntent,
)
from src.world.artifacts import create_agent_artifact


@pytest.fixture
def world(tmp_path: Path) -> World:
    """Create a test World with an agent principal and agent artifact."""
    config = {
        "world": {},
        "principals": [
            {"id": "agent_001", "starting_scrip": 100},
        ],
        "costs": {"per_1k_input_tokens": 1, "per_1k_output_tokens": 3},
        "logging": {"output_file": str(tmp_path / "test.jsonl")},
        "resources": {
            "stock": {
                "disk": {"total": 10000, "unit": "bytes"},
            }
        },
    }
    w = World(config)

    # Create agent artifact directly in store (like create_agent_artifacts does)
    agent_artifact = create_agent_artifact(
        agent_id="agent_001",
        created_by="agent_001",
        agent_config={"llm_model": "test-model", "subscribed_artifacts": []},
    )
    w.artifacts.artifacts["agent_001"] = agent_artifact

    return w


def _create_target_artifact(world: World, artifact_id: str = "handbook") -> None:
    """Create a target artifact to subscribe to."""
    intent = WriteArtifactIntent(
        principal_id="agent_001",
        artifact_id=artifact_id,
        artifact_type="document",
        content="Handbook content here.",
    )
    result = world.execute_action(intent)
    assert result.success, f"Failed to create target artifact: {result.message}"


@pytest.mark.plans([241])
class TestSubscribeAction:
    """Tests that subscribe_artifact works through the action executor."""

    def test_subscribe_succeeds(self, world: World) -> None:
        """subscribe_artifact should add artifact to subscribed list."""
        _create_target_artifact(world)

        intent = SubscribeArtifactIntent("agent_001", "handbook")
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        assert "handbook" in result.data["subscribed_artifacts"]

    def test_subscribe_updates_agent_content(self, world: World) -> None:
        """subscribe_artifact should persist the change in agent artifact content."""
        _create_target_artifact(world)

        intent = SubscribeArtifactIntent("agent_001", "handbook")
        world.execute_action(intent)

        agent = world.artifacts.get("agent_001")
        assert agent is not None
        config = json.loads(agent.content)
        assert "handbook" in config["subscribed_artifacts"]


@pytest.mark.plans([241])
class TestUnsubscribeAction:
    """Tests that unsubscribe_artifact works through the action executor."""

    def test_unsubscribe_succeeds(self, world: World) -> None:
        """unsubscribe_artifact should remove artifact from subscribed list."""
        _create_target_artifact(world)

        # Subscribe first
        world.execute_action(SubscribeArtifactIntent("agent_001", "handbook"))

        # Then unsubscribe
        intent = UnsubscribeArtifactIntent("agent_001", "handbook")
        result = world.execute_action(intent)

        assert result.success is True
        assert result.data is not None
        assert "handbook" not in result.data["subscribed_artifacts"]


@pytest.mark.plans([241])
class TestConfigureContextAction:
    """Tests that configure_context works through the action executor."""

    def test_configure_context_succeeds(self, world: World) -> None:
        """configure_context should update context section settings."""
        intent = ConfigureContextIntent(
            principal_id="agent_001",
            sections={"subscribed_artifacts": True},
            priorities={"subscribed_artifacts": 5},
        )
        result = world.execute_action(intent)

        assert result.success is True


@pytest.mark.plans([241])
class TestModifySystemPromptAction:
    """Tests that modify_system_prompt works through the action executor."""

    def test_modify_system_prompt_append(self, world: World) -> None:
        """modify_system_prompt append should add to prompt modifications."""
        intent = ModifySystemPromptIntent(
            principal_id="agent_001",
            operation="append",
            content="Always be helpful.",
        )
        result = world.execute_action(intent)

        assert result.success is True

        # Verify persisted in agent artifact
        agent = world.artifacts.get("agent_001")
        assert agent is not None
        config = json.loads(agent.content)
        assert "system_prompt_modifications" in config
        mods = config["system_prompt_modifications"]
        assert "Always be helpful." in str(mods)


@pytest.mark.plans([308])
class TestUpdateMetadataAction:
    """Tests that update_metadata works through the action executor (Plan #308)."""

    def test_update_metadata_success(self, world: World) -> None:
        """update_metadata should set a metadata key on an artifact."""
        _create_target_artifact(world)

        intent = UpdateMetadataIntent("agent_001", "handbook", "tag", "important")
        result = world.execute_action(intent)

        assert result.success is True
        artifact = world.artifacts.get("handbook")
        assert artifact is not None
        assert artifact.metadata["tag"] == "important"

    def test_update_metadata_not_found(self, world: World) -> None:
        """update_metadata on nonexistent artifact should fail."""
        intent = UpdateMetadataIntent("agent_001", "nonexistent", "tag", "val")
        result = world.execute_action(intent)

        assert result.success is False

    def test_update_metadata_permission_denied(self, world: World) -> None:
        """update_metadata without write access should fail."""
        # Create artifact owned by SYSTEM with private contract
        world.artifacts.write(
            artifact_id="private_doc",
            type="document",
            content="secret",
            created_by="SYSTEM",
            access_contract_id="private",
        )

        intent = UpdateMetadataIntent("agent_001", "private_doc", "tag", "val")
        result = world.execute_action(intent)

        assert result.success is False

    def test_update_metadata_delete_key(self, world: World) -> None:
        """update_metadata with value=None should delete the key."""
        _create_target_artifact(world)

        # Set a key first
        world.execute_action(UpdateMetadataIntent("agent_001", "handbook", "tag", "temp"))
        artifact = world.artifacts.get("handbook")
        assert artifact is not None
        assert "tag" in artifact.metadata

        # Delete it
        result = world.execute_action(UpdateMetadataIntent("agent_001", "handbook", "tag", None))

        assert result.success is True
        artifact = world.artifacts.get("handbook")
        assert artifact is not None
        assert "tag" not in artifact.metadata

    def test_update_metadata_rejects_authorized_writer(self, world: World) -> None:
        """update_metadata must reject attempts to set authorized_writer."""
        _create_target_artifact(world)

        intent = UpdateMetadataIntent("agent_001", "handbook", "authorized_writer", "agent_001")
        result = world.execute_action(intent)

        assert result.success is False
        assert "protected" in result.message.lower() or "escrow" in result.message.lower()

    def test_update_metadata_rejects_authorized_principal(self, world: World) -> None:
        """update_metadata must reject attempts to set authorized_principal."""
        _create_target_artifact(world)

        intent = UpdateMetadataIntent("agent_001", "handbook", "authorized_principal", "agent_001")
        result = world.execute_action(intent)

        assert result.success is False
        assert "protected" in result.message.lower() or "escrow" in result.message.lower()
