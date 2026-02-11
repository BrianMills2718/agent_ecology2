"""Integration tests for agent working memory (Plan #59).

Tests that agents can update their own working memory via write_artifact.
"""

import pytest
import json

from src.world.world import World
from src.world.actions import WriteArtifactIntent


class TestAgentSelfUpdate:
    """Test that agents can update their own working memory."""

    @pytest.mark.plans([59])
    def test_agent_updates_own_memory(self, feature_world: World) -> None:
        """Agent should be able to write to self to update working memory."""
        world = feature_world

        # Create an agent artifact that alice owns
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_memory",
            artifact_type="generic",
            content=json.dumps({"notes": "initial"}),
            access_contract_id="kernel_contract_freeware",
        )
        result = world.execute_action(intent)
        assert result.success, f"Setup write failed: {result.message}"

        # Now alice updates her own artifact
        new_content = {
            "notes": "initial",
            "working_memory": {
                "current_goal": "Build trading system",
                "progress": {"stage": "Design", "completed": []},
                "lessons": [],
            },
        }
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_memory",
            artifact_type="generic",
            content=json.dumps(new_content),
            access_contract_id="kernel_contract_freeware",
        )
        result = world.execute_action(intent)
        assert result.success, f"Write failed: {result.message}"

        # Verify the update persisted
        updated = world.artifacts.get("alice_memory")
        assert updated is not None
        updated_content = json.loads(updated.content)
        assert "working_memory" in updated_content
        assert updated_content["working_memory"]["current_goal"] == "Build trading system"

    @pytest.mark.plans([59])
    def test_agent_cannot_update_other_agent_memory(self, feature_world: World) -> None:
        """Agent should NOT be able to write to another agent's artifact."""
        world = feature_world

        # Alice creates her own artifact
        intent = WriteArtifactIntent(
            principal_id="alice",
            artifact_id="alice_private",
            artifact_type="generic",
            content=json.dumps({"secret": "data"}),
            access_contract_id="kernel_contract_freeware",
        )
        result = world.execute_action(intent)
        assert result.success, f"Setup write failed: {result.message}"

        # Bob tries to write to Alice's artifact
        intent = WriteArtifactIntent(
            principal_id="bob",
            artifact_id="alice_private",
            artifact_type="generic",
            content=json.dumps({"hacked": True}),
            access_contract_id="kernel_contract_freeware",
        )
        result = world.execute_action(intent)

        # Should fail — bob doesn't own alice's artifact
        assert not result.success, "Bob should not be able to write to Alice's artifact"
