"""Integration tests for agent working memory (Plan #59).

Tests that agents can update their own working memory via write_artifact.
"""

import pytest
import json
from typing import Any

from src.world.world import World
from src.world.artifacts import ArtifactStore


class TestAgentSelfUpdate:
    """Test that agents can update their own working memory."""

    @pytest.mark.plans([59])
    def test_agent_updates_own_memory(self, test_world: World) -> None:
        """Agent should be able to write to self to update working memory."""
        world = test_world
        # Get the agent artifact
        agent_id = "alpha"

        # Check if alpha exists, if not use first available agent
        if world.artifacts.get(agent_id) is None:
            # Get first agent artifact
            all_artifacts = list(world.artifacts.artifacts.values())
            agent_artifacts = [a for a in all_artifacts if a.has_standing]
            if not agent_artifacts:
                pytest.skip("No agent artifacts found")
            agent_id = agent_artifacts[0].id

        # Get current artifact content
        artifact = world.artifacts.get(agent_id)
        assert artifact is not None

        # Parse current content
        try:
            current_content = json.loads(artifact.content) if artifact.content else {}
        except json.JSONDecodeError:
            current_content = {}

        # Add working_memory to content
        new_content = current_content.copy()
        new_content["working_memory"] = {
            "current_goal": "Build trading system",
            "progress": {"stage": "Design", "completed": []},
            "lessons": [],
        }

        # Agent writes to self
        result = world.execute_action({
            "action_type": "write_artifact",
            "principal_id": agent_id,
            "artifact_id": agent_id,
            "content": json.dumps(new_content),
        })

        assert result.success, f"Write failed: {result.error}"

        # Verify the update persisted
        updated = world.artifacts.get(agent_id)
        assert updated is not None

        updated_content = json.loads(updated.content)
        assert "working_memory" in updated_content
        assert updated_content["working_memory"]["current_goal"] == "Build trading system"

    @pytest.mark.plans([59])
    def test_agent_cannot_update_other_agent_memory(self, test_world: World) -> None:
        """Agent should NOT be able to write to another agent's artifact."""
        world = test_world
        # Get two different agents
        all_artifacts = list(world.artifacts.artifacts.values())
        agents = [a.id for a in all_artifacts if a.has_standing]
        if len(agents) < 2:
            pytest.skip("Need at least 2 agents for this test")

        agent_a, agent_b = agents[0], agents[1]

        # Agent A tries to write to Agent B
        result = world.execute_action({
            "action_type": "write_artifact",
            "principal_id": agent_a,
            "artifact_id": agent_b,  # Trying to write to another agent!
            "content": json.dumps({"hacked": True}),
        })

        # Should fail - agents can only write to artifacts they own
        # (or the write should be rejected by ownership check)
        # Note: The exact behavior depends on ownership rules
        # If agents own themselves, this should fail ownership check
        if result.success:
            # If it succeeded, verify ownership allows it
            artifact_b = world.artifacts.get(agent_b)
            owner = artifact_b.owner_id if artifact_b else None
            assert owner == agent_a, "Write succeeded but agent_a doesn't own agent_b"
