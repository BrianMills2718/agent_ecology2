"""Tests for Plan #160: Cognitive Self-Modification.

Tests verify:
1. Action pattern analysis works correctly
2. Metacognitive prompting appears appropriately
3. Config reload error handling works
4. No hardcoded enforcement rules exist
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agents.agent import Agent
from src.world.artifacts import Artifact


class TestActionPatternAnalysis:
    """Tests for _analyze_action_patterns method."""

    def test_empty_history_returns_empty_string(self) -> None:
        """Pattern analysis returns empty string for no history."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.action_history = []

        result = agent._analyze_action_patterns()

        assert result == ""

    def test_no_repeats_returns_empty(self) -> None:
        """Pattern analysis returns empty for < 3 repetitions."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        # Each action only once or twice - not enough for pattern
        agent.action_history = [
            "read_artifact(genesis_store) → SUCCESS: Read complete",
            "write_artifact(my_tool) → SUCCESS: Created",
            "read_artifact(genesis_store) → SUCCESS: Read complete",
        ]

        result = agent._analyze_action_patterns()

        assert result == ""  # No action repeated 3+ times

    def test_detects_repeated_patterns(self) -> None:
        """Pattern analysis shows actions repeated 3+ times with success/fail counts."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.action_history = [
            "read_artifact(genesis_store) → SUCCESS: Read complete",
            "read_artifact(genesis_store) → SUCCESS: Read complete",
            "read_artifact(genesis_store) → FAILED: Not found",
            "write_artifact(tool) → SUCCESS: Created",
        ]

        result = agent._analyze_action_patterns()

        assert "read_artifact(genesis_store)" in result
        assert "3x" in result
        assert "2 ok" in result
        assert "1 fail" in result

    def test_multiple_repeated_patterns(self) -> None:
        """Pattern analysis detects multiple repeated action types."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.action_history = [
            "read_artifact(a) → SUCCESS: ok",
            "read_artifact(a) → SUCCESS: ok",
            "read_artifact(a) → SUCCESS: ok",
            "invoke_artifact(b) → FAILED: error",
            "invoke_artifact(b) → FAILED: error",
            "invoke_artifact(b) → FAILED: error",
        ]

        result = agent._analyze_action_patterns()

        assert "read_artifact(a)" in result
        assert "invoke_artifact(b)" in result
        assert "3 ok" in result  # read_artifact successes
        assert "3 fail" in result  # invoke_artifact failures


class TestMetacognitivePrompting:
    """Tests for metacognitive prompting in build_prompt."""

    def test_metacognitive_section_appears_after_3_actions(self) -> None:
        """Metacognitive prompting section appears when actions_taken >= 3."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.actions_taken = 3

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = None  # Default values

            world_state = {
                "tick": 5,
                "balances": {"test_agent": 100},
                "artifacts": [],
            }

            prompt = agent.build_prompt(world_state)

            assert "Self-Evaluation" in prompt
            assert "think before acting" in prompt

    def test_metacognitive_disabled_before_3_actions(self) -> None:
        """Metacognitive section not shown before 3 actions taken."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.actions_taken = 2  # Less than 3

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = None

            world_state = {
                "tick": 3,
                "balances": {"test_agent": 100},
                "artifacts": [],
            }

            prompt = agent.build_prompt(world_state)

            assert "Self-Evaluation" not in prompt

    def test_metacognitive_respects_section_control(self) -> None:
        """Metacognitive section respects context section control (Plan #192)."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent.actions_taken = 5
        # Disable metacognitive section
        agent._context_sections = {"metacognitive": False}

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = None

            world_state = {
                "tick": 10,
                "balances": {"test_agent": 100},
                "artifacts": [],
            }

            prompt = agent.build_prompt(world_state)

            assert "Self-Evaluation" not in prompt


class TestConfigReloadErrorHandling:
    """Tests for config reload error tracking."""

    def test_config_reload_error_tracked(self) -> None:
        """Config parse errors stored in _last_reload_error."""
        artifact = Artifact(
            id="test_agent",
            type="agent",
            content="invalid json {{{",
            created_by="genesis",
            created_at=0.0,
            updated_at=0.0,
        )

        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent._load_from_artifact(artifact)

        assert agent._last_reload_error is not None
        assert "Config parse error" in agent._last_reload_error

    def test_config_reload_clears_error_on_success(self) -> None:
        """Successful config reload clears previous error."""
        # First, set an error
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent._last_reload_error = "Previous error"

        # Now load valid config
        artifact = Artifact(
            id="test_agent",
            type="agent",
            content=json.dumps({"llm_model": "test-model"}),
            created_by="genesis",
            created_at=0.0,
            updated_at=0.0,
        )
        agent._load_from_artifact(artifact)

        assert agent._last_reload_error is None

    def test_config_error_shown_in_prompt(self) -> None:
        """Config errors appear in prompt feedback section."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")
        agent._last_reload_error = "Test error: invalid JSON"

        with patch("src.agents.agent.config_get") as mock_config:
            mock_config.return_value = None

            world_state = {
                "tick": 1,
                "balances": {"test_agent": 100},
                "artifacts": [],
            }

            prompt = agent.build_prompt(world_state)

            assert "CONFIG ERROR" in prompt
            assert "Test error: invalid JSON" in prompt


class TestNoHardcodedEnforcement:
    """Tests ensuring no hardcoded enforcement rules exist."""

    def test_no_action_blocking(self) -> None:
        """Verify no action is blocked based on patterns."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")

        # Add many repeated failing actions
        agent.action_history = [
            "invoke_artifact(bad) → FAILED: error"
            for _ in range(20)
        ]

        # Pattern analysis should show the pattern but NOT block
        result = agent._analyze_action_patterns()

        # Should show the pattern
        assert "invoke_artifact(bad)" in result
        assert "20x" in result

        # Agent should still be able to think (propose_action would work)
        # We verify by checking agent is still in valid state
        assert agent._alive is True

    def test_action_history_is_informational_only(self) -> None:
        """Action history and pattern analysis are informational, not blocking."""
        agent = Agent(agent_id="test_agent", log_dir="/tmp/test_logs")

        # Simulate 100 failed actions of same type
        for i in range(100):
            agent.action_history.append(
                f"noop() → FAILED: test failure {i}"
            )

        # Agent should still be functional
        assert len(agent.action_history) == 100

        # Pattern analysis should work (not raise)
        result = agent._analyze_action_patterns()
        assert "noop()" in result
