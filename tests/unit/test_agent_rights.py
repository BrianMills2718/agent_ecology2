"""Unit tests for agent rights trading (Plan #8).

Tests the dynamic config reload feature that allows agents to pick up
configuration changes made by other agents without restarting.

Test cases:
- test_config_reload_picks_up_changes: Config changes are reflected after reload
- test_config_reload_handles_missing_artifact: Graceful handling of deleted artifact
- test_config_reload_handles_invalid_json: Graceful handling of malformed content
- test_config_reload_without_artifact_store: No-op for non-artifact-backed agents
"""

from __future__ import annotations

import json

import pytest

from src.agents.agent import Agent
from src.world.artifacts import Artifact, ArtifactStore, create_agent_artifact


class TestAgentConfigReload:
    """Tests for agent.reload_from_artifact() (Plan #8)."""

    def test_config_reload_picks_up_changes(self) -> None:
        """Config changes made to artifact are reflected after reload."""
        # Create an artifact store
        store = ArtifactStore()

        # Create an agent artifact with initial config
        initial_config = {
            "system_prompt": "Initial prompt",
            "llm_model": "gemini/gemini-3-flash-preview",
        }
        artifact = create_agent_artifact(
            agent_id="test_agent",
            agent_config=initial_config,
            created_by="test_agent",
        )
        store.artifacts[artifact.id] = artifact

        # Create agent backed by artifact (artifact_store avoids Mem0 init)
        agent = Agent(
            agent_id="test_agent",
            artifact=artifact,
            artifact_store=store,
        )

        # Verify initial config
        assert agent.system_prompt == "Initial prompt"

        # Modify the artifact in the store (simulating another agent's write)
        updated_config = {
            "system_prompt": "Updated prompt by new owner",
            "llm_model": "gemini/gemini-3-flash-preview",
        }
        updated_artifact = Artifact(
            id="test_agent",
            type="agent",
            content=json.dumps(updated_config),
            created_by="test_agent",
            created_at=artifact.created_at,
            updated_at="2026-01-20T15:00:00",
            has_standing=True,
            has_loop=True,
        )
        store.artifacts[updated_artifact.id] = updated_artifact

        # Reload config
        result = agent.reload_from_artifact()

        # Verify reload succeeded and config updated
        assert result is True
        assert agent.system_prompt == "Updated prompt by new owner"

    def test_config_reload_handles_missing_artifact(self) -> None:
        """Reload returns False and keeps config when artifact deleted."""
        # Create an artifact store
        store = ArtifactStore()

        # Create an agent artifact
        initial_config = {
            "system_prompt": "Original prompt",
            "llm_model": "gemini/gemini-3-flash-preview",
        }
        artifact = create_agent_artifact(
            agent_id="test_agent",
            agent_config=initial_config,
            created_by="test_agent",
        )
        store.artifacts[artifact.id] = artifact

        # Create agent backed by artifact
        agent = Agent(
            agent_id="test_agent",
            artifact=artifact,
            artifact_store=store,
        )

        # Delete the artifact from store
        del store.artifacts["test_agent"]

        # Reload should return False
        result = agent.reload_from_artifact()

        # Verify reload failed but config preserved
        assert result is False
        assert agent.system_prompt == "Original prompt"

    def test_config_reload_handles_invalid_json(self) -> None:
        """Reload handles artifact with invalid JSON content gracefully."""
        # Create an artifact store
        store = ArtifactStore()

        # Create an agent artifact with valid config
        initial_config = {
            "system_prompt": "Original prompt",
            "llm_model": "gemini/gemini-3-flash-preview",
        }
        artifact = create_agent_artifact(
            agent_id="test_agent",
            agent_config=initial_config,
            created_by="test_agent",
        )
        store.artifacts[artifact.id] = artifact

        # Create agent backed by artifact
        agent = Agent(
            agent_id="test_agent",
            artifact=artifact,
            artifact_store=store,
        )

        # Replace artifact with one containing invalid JSON
        invalid_artifact = Artifact(
            id="test_agent",
            type="agent",
            content="not valid json {{{",
            created_by="test_agent",
            created_at=artifact.created_at,
            updated_at="2026-01-20T15:00:00",
            has_standing=True,
            has_loop=True,
        )
        store.artifacts[invalid_artifact.id] = invalid_artifact

        # Reload should succeed (invalid JSON is handled by _load_from_artifact)
        result = agent.reload_from_artifact()

        # Verify reload succeeded but config fields may be unchanged
        # (invalid JSON results in empty config dict, so no overrides happen)
        assert result is True

    def test_config_reload_without_artifact_store(self) -> None:
        """Reload returns False for non-artifact-backed agents."""
        # Create an artifact store to avoid Mem0 init, but don't use it for agent
        store = ArtifactStore()

        # Create agent with artifact_store but no artifact
        # This bypasses Mem0 but tests the "no artifact" case
        agent = Agent(
            agent_id="standalone_agent",
            system_prompt="Standalone prompt",
            artifact_store=store,  # Avoids Mem0 init
        )
        # Manually clear the artifact store reference to simulate no-store case
        agent._artifact_store = None

        # Reload should return False (no artifact store)
        result = agent.reload_from_artifact()

        # Verify reload failed and config unchanged
        assert result is False
        assert agent.system_prompt == "Standalone prompt"

    def test_config_reload_updates_multiple_fields(self) -> None:
        """Reload updates all config fields, not just system_prompt."""
        # Create an artifact store
        store = ArtifactStore()

        # Create an agent artifact with initial config
        initial_config = {
            "system_prompt": "Initial prompt",
            "llm_model": "model-a",
            "working_memory": {"current_goal": "goal 1"},
        }
        artifact = create_agent_artifact(
            agent_id="test_agent",
            agent_config=initial_config,
            created_by="test_agent",
        )
        store.artifacts[artifact.id] = artifact

        # Create agent backed by artifact
        agent = Agent(
            agent_id="test_agent",
            artifact=artifact,
            artifact_store=store,
        )

        # Verify initial config
        assert agent.system_prompt == "Initial prompt"
        assert agent._llm_model == "model-a"

        # Modify multiple fields
        updated_config = {
            "system_prompt": "New prompt",
            "llm_model": "model-b",
            "working_memory": {"current_goal": "goal 2"},
        }
        updated_artifact = Artifact(
            id="test_agent",
            type="agent",
            content=json.dumps(updated_config),
            created_by="test_agent",
            created_at=artifact.created_at,
            updated_at="2026-01-20T15:00:00",
            has_standing=True,
            has_loop=True,
        )
        store.artifacts[updated_artifact.id] = updated_artifact

        # Reload config
        result = agent.reload_from_artifact()

        # Verify all fields updated
        assert result is True
        assert agent.system_prompt == "New prompt"
        assert agent._llm_model == "model-b"
        assert agent._working_memory == {"current_goal": "goal 2"}
