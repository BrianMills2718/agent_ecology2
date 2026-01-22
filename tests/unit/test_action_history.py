"""Tests for action history tracking (Plan #156).

Action history enables loop detection by showing agents their recent actions.
"""

import pytest
from src.agents.agent import Agent


class TestActionHistoryTracking:
    """Test action history accumulates correctly."""

    def test_action_history_starts_empty(self) -> None:
        """New agents have empty action history."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )
        assert agent.action_history == []

    def test_action_history_accumulates(self) -> None:
        """Actions are recorded to history."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        # Record several actions (ActionType is a string literal)
        agent.set_last_result("read_artifact", True, "Read my_artifact")
        agent.set_last_result("write_artifact", True, "Created new_artifact")
        agent.set_last_result("invoke_artifact", False, "Target not found")

        assert len(agent.action_history) == 3
        assert "read_artifact" in agent.action_history[0].lower()
        assert "SUCCESS" in agent.action_history[0]
        assert "write_artifact" in agent.action_history[1].lower()
        assert "invoke_artifact" in agent.action_history[2].lower()
        assert "FAILED" in agent.action_history[2]


class TestActionHistoryMaxLength:
    """Test old entries are dropped when max length reached."""

    def test_max_length_enforced(self) -> None:
        """History is truncated to max length."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )
        # Force a smaller max for testing
        agent._action_history_max = 5

        # Record more actions than max
        for i in range(10):
            agent.set_last_result("noop", True, f"Action {i}")

        assert len(agent.action_history) == 5
        # Should have the most recent 5 (5-9)
        assert "Action 5" in agent.action_history[0]
        assert "Action 9" in agent.action_history[4]


class TestActionHistoryFormat:
    """Test action history renders correctly for prompt."""

    def test_format_empty_history(self) -> None:
        """Empty history returns placeholder."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )
        formatted = agent._format_action_history()
        assert formatted == "(No actions yet)"

    def test_format_with_actions(self) -> None:
        """History formats as numbered list."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        agent.set_last_result("read_artifact", True, "Read artifact_a")
        agent.set_last_result("write_artifact", True, "Wrote artifact_b")

        formatted = agent._format_action_history()

        assert "1." in formatted
        assert "2." in formatted
        assert "read_artifact" in formatted.lower()
        assert "write_artifact" in formatted.lower()


class TestActionHistoryInContext:
    """Test action history is included in workflow context."""

    def test_context_includes_action_history(self) -> None:
        """Workflow context contains action_history."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        agent.set_last_result("invoke_artifact", True, "Invoked genesis_ledger")

        world_state = {
            "tick": 1,
            "balances": {"test_agent": 100},
            "artifacts": [],
        }

        context = agent._build_workflow_context(world_state)

        assert "action_history" in context
        assert "invoke" in context["action_history"].lower()
        assert "action_history_length" in context
        assert context["action_history_length"] == agent._action_history_max


class TestActionHistoryWithTarget:
    """Test action history includes artifact_id for loop detection."""

    def test_history_includes_artifact_id(self) -> None:
        """History entry includes artifact_id when provided in data."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        # Simulate write_artifact with artifact_id in data
        agent.set_last_result(
            "write_artifact",
            True,
            "Wrote artifact",
            data={"artifact_id": "factorial_calculator"}
        )

        assert len(agent.action_history) == 1
        assert "factorial_calculator" in agent.action_history[0]
        assert "write_artifact(factorial_calculator)" in agent.action_history[0]

    def test_history_includes_method_for_invoke(self) -> None:
        """History entry includes method name for invoke actions."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        # Simulate invoke_artifact with artifact_id and method in data
        agent.set_last_result(
            "invoke_artifact",
            True,
            "Invoked method",
            data={"artifact_id": "genesis_store", "method": "search"}
        )

        assert len(agent.action_history) == 1
        assert "genesis_store.search" in agent.action_history[0]
        assert "invoke_artifact(genesis_store.search)" in agent.action_history[0]

    def test_repeated_same_artifact_visible(self) -> None:
        """Agent can see when same artifact is written multiple times."""
        agent = Agent(
            agent_id="test_agent",
            system_prompt="Test",
        )

        # Write same artifact 3 times
        for _ in range(3):
            agent.set_last_result(
                "write_artifact",
                True,
                "Wrote artifact",
                data={"artifact_id": "my_tool"}
            )

        formatted = agent._format_action_history()

        # Should clearly show 3 writes to same artifact
        assert formatted.count("my_tool") == 3
        assert formatted.count("write_artifact(my_tool)") == 3
