"""Tests for agent working memory functionality (Plan #59)."""

import json
import pytest
from unittest.mock import patch

from src.agents.agent import Agent, WorkingMemoryDict
from src.world.artifacts import Artifact, ArtifactStore


def create_test_artifact_store() -> ArtifactStore:
    """Create an ArtifactStore for tests to avoid Mem0 initialization."""
    return ArtifactStore()


def create_agent_artifact(
    agent_id: str,
    working_memory: dict | None = None,
    system_prompt: str = "Test agent",
    content_override: str | None = None
) -> Artifact:
    """Helper to create an agent artifact for testing."""
    if content_override:
        content = content_override
    else:
        content_dict = {
            "llm_model": "gemini/gemini-3-flash-preview",
            "system_prompt": system_prompt,
        }
        if working_memory:
            content_dict["working_memory"] = working_memory
        content = json.dumps(content_dict)

    return Artifact(
        id=agent_id,
        type="agent",
        content=content,
        owner_id=agent_id,
        created_at="2026-01-16T10:00:00Z",
        updated_at="2026-01-16T10:00:00Z",
        has_standing=True,
        can_execute=True,
    )


def mock_config_enabled(key: str) -> dict | str | int | bool | None:
    """Mock config_get with working memory enabled."""
    if key == "agent.working_memory":
        return {
            "enabled": True,
            "auto_inject": True,
            "max_size_bytes": 2000,
            "warn_on_missing": False
        }
    elif key == "agent.prompt.recent_events_count":
        return 5
    elif key == "agent.prompt.first_tick_enabled":
        return False
    elif key == "agent.rag":
        return {"enabled": False}
    return None


def mock_config_disabled(key: str) -> dict | str | int | bool | None:
    """Mock config_get with working memory disabled."""
    if key == "agent.working_memory":
        return {
            "enabled": False,
            "auto_inject": True,
            "max_size_bytes": 2000
        }
    elif key == "agent.prompt.recent_events_count":
        return 5
    elif key == "agent.prompt.first_tick_enabled":
        return False
    elif key == "agent.rag":
        return {"enabled": False}
    return None


class TestWorkingMemoryInjection:
    """Tests for working memory injection into agent prompts."""

    @pytest.mark.plans([59])
    def test_working_memory_injection_enabled(self) -> None:
        """Memory injected when config enabled and agent has working memory."""
        artifact = create_agent_artifact(
            "test_agent",
            working_memory={
                "current_goal": "Build a test service",
                "progress": {
                    "stage": "Implementation",
                    "completed": ["design"],
                    "next_steps": ["coding", "testing"]
                },
                "lessons": ["Testing is important"]
            }
        )
        store = create_test_artifact_store()
        # Store passed to avoid Mem0 initialization; artifact passed directly
        agent = Agent.from_artifact(artifact, store=store)

        with patch("src.agents.agent.config_get", side_effect=mock_config_enabled):
            world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Your Working Memory" in prompt
            assert "Build a test service" in prompt
            assert "Implementation" in prompt
            assert "Testing is important" in prompt

    @pytest.mark.plans([59])
    def test_working_memory_injection_disabled(self) -> None:
        """Memory NOT injected when config disabled."""
        artifact = create_agent_artifact(
            "test_agent",
            working_memory={"current_goal": "Build a test service"}
        )
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        with patch("src.agents.agent.config_get", side_effect=mock_config_disabled):
            world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Your Working Memory" not in prompt
            assert "Build a test service" not in prompt

    @pytest.mark.plans([59])
    def test_working_memory_auto_inject_disabled(self) -> None:
        """Memory NOT injected when auto_inject is false."""
        artifact = create_agent_artifact(
            "test_agent",
            working_memory={"current_goal": "Build a test service"}
        )
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        def mock_auto_inject_disabled(key: str) -> dict | str | int | bool | None:
            if key == "agent.working_memory":
                return {
                    "enabled": True,
                    "auto_inject": False,  # Auto-inject disabled
                    "max_size_bytes": 2000
                }
            elif key == "agent.prompt.recent_events_count":
                return 5
            elif key == "agent.prompt.first_tick_enabled":
                return False
            elif key == "agent.rag":
                return {"enabled": False}
            return None

        with patch("src.agents.agent.config_get", side_effect=mock_auto_inject_disabled):
            world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)

            assert "Your Working Memory" not in prompt


class TestWorkingMemorySizeLimit:
    """Tests for working memory size limits."""

    @pytest.mark.plans([59])
    def test_working_memory_size_limit(self) -> None:
        """Large memory truncated to max_size_bytes."""
        large_lessons = [f"Lesson {i}: " + "x" * 100 for i in range(50)]
        artifact = create_agent_artifact(
            "test_agent",
            working_memory={
                "current_goal": "Build a test service",
                "lessons": large_lessons,
                "strategic_objectives": ["Objective " + "y" * 100 for _ in range(20)]
            }
        )
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        def mock_small_limit(key: str) -> dict | str | int | bool | None:
            if key == "agent.working_memory":
                return {
                    "enabled": True,
                    "auto_inject": True,
                    "max_size_bytes": 500  # Small limit
                }
            return None

        with patch("src.agents.agent.config_get", side_effect=mock_small_limit):
            wm = agent._get_working_memory()
            assert wm is not None

            formatted = agent._format_working_memory(wm)
            assert len(formatted.encode('utf-8')) <= 520  # 500 + buffer for "truncated"
            assert "truncated" in formatted.lower()


class TestWorkingMemoryMissing:
    """Tests for graceful handling of missing working memory."""

    @pytest.mark.plans([59])
    def test_working_memory_missing_graceful(self) -> None:
        """No crash if working_memory absent from artifact."""
        # Create artifact WITHOUT working_memory
        artifact = create_agent_artifact("test_agent", working_memory=None)
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        with patch("src.agents.agent.config_get", side_effect=mock_config_enabled):
            wm = agent._get_working_memory()
            assert wm is None

            world_state = {"tick": 1, "balances": {"test_agent": 100}, "artifacts": []}
            prompt = agent.build_prompt(world_state)
            assert "Your Working Memory" not in prompt

    @pytest.mark.plans([59])
    def test_working_memory_non_artifact_backed_agent(self) -> None:
        """Non-artifact-backed agents return None for working memory."""
        # Create agent directly (not from artifact) with an artifact_store
        # to avoid Mem0 initialization
        store = create_test_artifact_store()
        agent = Agent(
            agent_id="test_agent",
            llm_model="gemini/gemini-3-flash-preview",
            artifact_store=store
        )

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = {"enabled": True}
            wm = agent._get_working_memory()
            assert wm is None

    @pytest.mark.plans([59])
    def test_working_memory_invalid_json(self) -> None:
        """Invalid JSON in artifact content handled gracefully."""
        artifact = create_agent_artifact(
            "test_agent",
            content_override="not valid json {"
        )
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = {"enabled": True, "warn_on_missing": False}
            wm = agent._get_working_memory()
            assert wm is None


class TestWorkingMemoryFormatting:
    """Tests for working memory formatting."""

    @pytest.mark.plans([59])
    def test_format_all_fields(self) -> None:
        """All working memory fields are properly formatted."""
        artifact = create_agent_artifact(
            "test_agent",
            working_memory={
                "current_goal": "Build a service",
                "started": "2026-01-16T10:30:00Z",
                "progress": {
                    "stage": "Testing",
                    "completed": ["design", "implementation"],
                    "next_steps": ["testing", "deployment"],
                    "actions_in_stage": 3
                },
                "lessons": ["Lesson A", "Lesson B"],
                "strategic_objectives": ["Obj 1", "Obj 2"]
            }
        )
        store = create_test_artifact_store()
        agent = Agent.from_artifact(artifact, store=store)

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = {
                "enabled": True,
                "max_size_bytes": 5000
            }

            wm = agent._get_working_memory()
            assert wm is not None

            formatted = agent._format_working_memory(wm)

            assert "Build a service" in formatted
            assert "Testing" in formatted
            assert "design, implementation" in formatted
            assert "testing, deployment" in formatted
            assert "3" in formatted  # actions_in_stage
            assert "Lesson A" in formatted
            assert "Obj 1" in formatted
            assert "2026-01-16T10:30:00Z" in formatted
