"""Tests for Plan #191: Subscribed Artifacts.

Tests that agents can subscribe to artifacts for auto-injection into prompts.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.agent import Agent
from src.world.actions import (
    ActionResult,
    SubscribeArtifactIntent,
    UnsubscribeArtifactIntent,
    parse_intent_from_json,
)


class TestSubscribeArtifactIntent:
    """Tests for subscribe_artifact action parsing."""

    def test_parse_subscribe_artifact(self) -> None:
        """Test parsing subscribe_artifact action from JSON."""
        json_str = json.dumps({
            "action_type": "subscribe_artifact",
            "artifact_id": "my_handbook",
            "reasoning": "Want to keep handbook in context"
        })
        result = parse_intent_from_json("agent_001", json_str)
        assert isinstance(result, SubscribeArtifactIntent)
        assert result.artifact_id == "my_handbook"
        assert result.principal_id == "agent_001"
        assert result.reasoning == "Want to keep handbook in context"

    def test_parse_subscribe_requires_artifact_id(self) -> None:
        """Test that subscribe_artifact requires artifact_id."""
        json_str = json.dumps({
            "action_type": "subscribe_artifact"
        })
        result = parse_intent_from_json("agent_001", json_str)
        assert isinstance(result, str)
        assert "artifact_id" in result.lower()

    def test_parse_unsubscribe_artifact(self) -> None:
        """Test parsing unsubscribe_artifact action from JSON."""
        json_str = json.dumps({
            "action_type": "unsubscribe_artifact",
            "artifact_id": "old_handbook",
        })
        result = parse_intent_from_json("agent_001", json_str)
        assert isinstance(result, UnsubscribeArtifactIntent)
        assert result.artifact_id == "old_handbook"
        assert result.principal_id == "agent_001"

    def test_parse_unsubscribe_requires_artifact_id(self) -> None:
        """Test that unsubscribe_artifact requires artifact_id."""
        json_str = json.dumps({
            "action_type": "unsubscribe_artifact"
        })
        result = parse_intent_from_json("agent_001", json_str)
        assert isinstance(result, str)
        assert "artifact_id" in result.lower()

    def test_intent_to_dict(self) -> None:
        """Test SubscribeArtifactIntent.to_dict()."""
        intent = SubscribeArtifactIntent("agent_001", "my_handbook", reasoning="test")
        d = intent.to_dict()
        assert d["action_type"] == "subscribe_artifact"
        assert d["artifact_id"] == "my_handbook"
        assert d["principal_id"] == "agent_001"
        assert d["reasoning"] == "test"


class TestAgentSubscribedArtifacts:
    """Tests for agent subscribed_artifacts field and injection."""

    def test_agent_loads_subscribed_artifacts_from_content(self) -> None:
        """Test that agent loads subscribed_artifacts from artifact content."""
        # Create mock artifact with subscribed_artifacts
        mock_artifact = MagicMock()
        mock_artifact.id = "agent_001"
        mock_artifact.content = json.dumps({
            "llm_model": "test-model",
            "subscribed_artifacts": ["handbook_a", "handbook_b"]
        })

        # Create agent from artifact
        agent = Agent(
            agent_id="agent_001",
            artifact=mock_artifact,
        )

        assert agent._subscribed_artifacts == ["handbook_a", "handbook_b"]

    def test_agent_filters_invalid_subscribed_artifacts(self) -> None:
        """Test that agent filters non-string values from subscribed_artifacts."""
        mock_artifact = MagicMock()
        mock_artifact.id = "agent_001"
        mock_artifact.content = json.dumps({
            "llm_model": "test-model",
            "subscribed_artifacts": ["valid_id", 123, None, "another_valid"]
        })

        agent = Agent(
            agent_id="agent_001",
            artifact=mock_artifact,
        )

        # Only string values should be kept
        assert agent._subscribed_artifacts == ["valid_id", "another_valid"]

    def test_agent_default_empty_subscribed_artifacts(self) -> None:
        """Test that agent has empty subscribed_artifacts by default."""
        agent = Agent(agent_id="agent_001")
        assert agent._subscribed_artifacts == []

    @patch("src.agents.agent.config_get")  # mock-ok: config requires filesystem setup
    def test_subscribed_artifacts_injected_into_prompt(
        self, mock_config_get: MagicMock
    ) -> None:
        """Test that subscribed artifacts content is injected into prompt."""
        # Configure mock
        def config_side_effect(key: str) -> int | bool | None:
            if key == "agent.subscribed_artifacts.max_count":
                return 5
            if key == "agent.subscribed_artifacts.max_size_bytes":
                return 2000
            if key == "agent.working_memory":
                return {"enabled": False, "auto_inject": False}
            if key == "agent.prompt.first_tick_enabled":
                return False
            if key == "agent.prompt.recent_events_count":
                return 5
            if key == "agent.rag":
                return {"enabled": False}
            return None

        mock_config_get.side_effect = config_side_effect

        agent = Agent(agent_id="agent_001")
        agent._subscribed_artifacts = ["my_handbook"]

        # Build prompt with artifacts in world state
        world_state = {
            "tick": 1,
            "balances": {"agent_001": 100},
            "artifacts": [
                {
                    "id": "my_handbook",
                    "created_by": "genesis",
                    "type": "handbook",
                    "content": "This is the handbook content."
                }
            ],
            "quotas": {},
            "time_context": {"time_remaining_seconds": 300, "progress_percent": 10}
        }

        prompt = agent.build_prompt(world_state)

        # Check that handbook content is injected
        assert "Subscribed Artifacts" in prompt
        assert "my_handbook" in prompt
        assert "This is the handbook content" in prompt

    @patch("src.agents.agent.config_get")  # mock-ok: config requires filesystem setup
    def test_subscribed_artifacts_truncated_if_too_large(
        self, mock_config_get: MagicMock
    ) -> None:
        """Test that large subscribed artifacts are truncated."""
        def config_side_effect(key: str) -> int | bool | None:
            if key == "agent.subscribed_artifacts.max_count":
                return 5
            if key == "agent.subscribed_artifacts.max_size_bytes":
                return 100  # Very small limit for testing
            if key == "agent.working_memory":
                return {"enabled": False, "auto_inject": False}
            if key == "agent.prompt.first_tick_enabled":
                return False
            if key == "agent.prompt.recent_events_count":
                return 5
            if key == "agent.rag":
                return {"enabled": False}
            return None

        mock_config_get.side_effect = config_side_effect

        agent = Agent(agent_id="agent_001")
        agent._subscribed_artifacts = ["big_doc"]

        # Large content
        large_content = "X" * 500

        world_state = {
            "tick": 1,
            "balances": {"agent_001": 100},
            "artifacts": [
                {
                    "id": "big_doc",
                    "created_by": "agent_002",
                    "type": "document",
                    "content": large_content
                }
            ],
            "quotas": {},
            "time_context": {"time_remaining_seconds": 300, "progress_percent": 10}
        }

        prompt = agent.build_prompt(world_state)

        # Should be truncated
        assert "[...truncated]" in prompt
        # Should not contain full content
        assert large_content not in prompt

    @patch("src.agents.agent.config_get")  # mock-ok: config requires filesystem setup
    def test_max_subscribed_artifacts_limit(
        self, mock_config_get: MagicMock
    ) -> None:
        """Test that only max_count subscribed artifacts are injected."""
        def config_side_effect(key: str) -> int | bool | None:
            if key == "agent.subscribed_artifacts.max_count":
                return 2  # Only allow 2
            if key == "agent.subscribed_artifacts.max_size_bytes":
                return 2000
            if key == "agent.working_memory":
                return {"enabled": False, "auto_inject": False}
            if key == "agent.prompt.first_tick_enabled":
                return False
            if key == "agent.prompt.recent_events_count":
                return 5
            if key == "agent.rag":
                return {"enabled": False}
            return None

        mock_config_get.side_effect = config_side_effect

        agent = Agent(agent_id="agent_001")
        # Subscribe to 4 artifacts
        agent._subscribed_artifacts = ["art1", "art2", "art3", "art4"]

        world_state = {
            "tick": 1,
            "balances": {"agent_001": 100},
            "artifacts": [
                {"id": "art1", "created_by": "x", "type": "doc", "content": "Content 1"},
                {"id": "art2", "created_by": "x", "type": "doc", "content": "Content 2"},
                {"id": "art3", "created_by": "x", "type": "doc", "content": "Content 3"},
                {"id": "art4", "created_by": "x", "type": "doc", "content": "Content 4"},
            ],
            "quotas": {},
            "time_context": {"time_remaining_seconds": 300, "progress_percent": 10}
        }

        prompt = agent.build_prompt(world_state)

        # Only first 2 should be injected
        assert "Content 1" in prompt
        assert "Content 2" in prompt
        assert "Content 3" not in prompt
        assert "Content 4" not in prompt

    @patch("src.agents.agent.config_get")  # mock-ok: config requires filesystem setup
    def test_nonexistent_subscribed_artifact_skipped(
        self, mock_config_get: MagicMock
    ) -> None:
        """Test that non-existent subscribed artifacts are gracefully skipped."""
        def config_side_effect(key: str) -> int | bool | None:
            if key == "agent.subscribed_artifacts.max_count":
                return 5
            if key == "agent.subscribed_artifacts.max_size_bytes":
                return 2000
            if key == "agent.working_memory":
                return {"enabled": False, "auto_inject": False}
            if key == "agent.prompt.first_tick_enabled":
                return False
            if key == "agent.prompt.recent_events_count":
                return 5
            if key == "agent.rag":
                return {"enabled": False}
            return None

        mock_config_get.side_effect = config_side_effect

        agent = Agent(agent_id="agent_001")
        agent._subscribed_artifacts = ["exists", "does_not_exist"]

        world_state = {
            "tick": 1,
            "balances": {"agent_001": 100},
            "artifacts": [
                {"id": "exists", "created_by": "x", "type": "doc", "content": "Real content"},
            ],
            "quotas": {},
            "time_context": {"time_remaining_seconds": 300, "progress_percent": 10}
        }

        prompt = agent.build_prompt(world_state)

        # Existing artifact should be injected
        assert "Real content" in prompt
        # Non-existent artifact should be silently skipped (no error)
        assert "does_not_exist" not in prompt or "Subscribed: does_not_exist" not in prompt
