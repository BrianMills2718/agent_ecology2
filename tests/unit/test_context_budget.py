"""Tests for context budget management (Plan #195).

Tests that context budgets are applied to prompt sections
and truncation works correctly.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agents.agent import Agent


class TestTokenCounting:
    """Test token counting functionality."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch.object(Agent, "__init__", lambda x: None):
            agent = Agent()
            agent._llm_model = "gpt-4"
            return agent

    def test_count_tokens_empty_string(self, mock_agent: Agent) -> None:
        """Empty string should return 0 tokens."""
        assert mock_agent._count_tokens("") == 0

    @patch("litellm.token_counter")
    def test_count_tokens_uses_litellm(
        self, mock_counter: MagicMock, mock_agent: Agent
    ) -> None:
        """Token counting should use litellm.token_counter."""
        mock_counter.return_value = 42

        result = mock_agent._count_tokens("hello world")

        assert result == 42
        mock_counter.assert_called_once()

    @patch("litellm.token_counter", side_effect=Exception("fail"))
    def test_count_tokens_fallback_on_error(
        self, mock_counter: MagicMock, mock_agent: Agent
    ) -> None:
        """Should fallback to estimation if litellm fails."""
        # 20 chars / 4 = 5 tokens (estimation)
        result = mock_agent._count_tokens("12345678901234567890")
        assert result == 5


class TestTruncation:
    """Test truncation strategies."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch.object(Agent, "__init__", lambda x: None):
            agent = Agent()
            agent._llm_model = "gpt-4"
            return agent

    def test_truncate_no_op_when_under_budget(self, mock_agent: Agent) -> None:
        """Content under budget should not be truncated."""
        with patch.object(mock_agent, "_count_tokens", return_value=10):
            content = "short content"
            result, tokens = mock_agent._truncate_to_budget("test", content, 100)

            assert result == content
            assert tokens == 10

    def test_truncate_end_strategy(self, mock_agent: Agent) -> None:
        """End strategy should remove lines from end."""
        content = "line1\nline2\nline3\nline4"

        # Mock: first call returns 40 (over), subsequent return smaller values
        call_count = [0]
        def mock_count(text: str) -> int:
            call_count[0] += 1
            lines = text.split("\n")
            return len(lines) * 10  # 10 tokens per line

        with patch.object(mock_agent, "_count_tokens", side_effect=mock_count):
            result, _ = mock_agent._truncate_to_budget("test", content, 25, "end")

            # Should have truncated, keeping start
            assert "line1" in result
            assert "[...truncated]" in result

    def test_truncate_start_strategy(self, mock_agent: Agent) -> None:
        """Start strategy should remove lines from start."""
        content = "old1\nold2\nnew1\nnew2"

        def mock_count(text: str) -> int:
            lines = text.split("\n")
            return len(lines) * 10

        with patch.object(mock_agent, "_count_tokens", side_effect=mock_count):
            result, _ = mock_agent._truncate_to_budget("test", content, 25, "start")

            # Should have truncated oldest, keeping newest
            assert "new2" in result
            assert "[...older entries truncated]" in result


class TestSectionBudget:
    """Test section budget configuration."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch.object(Agent, "__init__", lambda x: None):
            agent = Agent()
            agent._llm_model = "gpt-4"
            return agent

    @patch("src.agents.agent.config_get")
    def test_get_section_budget_from_config(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """Should read budget from config."""
        mock_config.return_value = {
            "working_memory": {
                "max_tokens": 600,
                "priority": "high",
                "truncation_strategy": "end",
            }
        }

        max_tokens, priority, strategy = mock_agent._get_section_budget("working_memory")

        assert max_tokens == 600
        assert priority == "high"
        assert strategy == "end"

    @patch("src.agents.agent.config_get")
    def test_get_section_budget_defaults(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """Should use defaults for missing config."""
        mock_config.return_value = {}

        max_tokens, priority, strategy = mock_agent._get_section_budget("unknown_section")

        assert max_tokens == 500  # default
        assert priority == "medium"  # default
        assert strategy == "end"  # default


class TestApplyContextBudget:
    """Test applying budget to all sections."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch.object(Agent, "__init__", lambda x: None):
            agent = Agent()
            agent._llm_model = "gpt-4"
            return agent

    @patch("src.agents.agent.config_get")
    def test_budget_disabled_returns_original(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """When budget disabled, should return original content."""
        mock_config.return_value = False  # budget not enabled

        sections = {"test": "content"}
        with patch.object(mock_agent, "_count_tokens", return_value=10):
            result, stats = mock_agent._apply_context_budget(sections)

        assert result == sections
        assert "test" in stats

    @patch("src.agents.agent.config_get")
    def test_budget_enabled_truncates_sections(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """When budget enabled, should truncate sections over budget."""
        def config_side_effect(key: str):
            if key == "context_budget.enabled":
                return True
            if key == "context_budget.sections":
                return {"test": {"max_tokens": 5, "priority": "medium", "truncation_strategy": "end"}}
            return None

        mock_config.side_effect = config_side_effect

        sections = {"test": "this is a long content that exceeds budget"}

        with patch.object(mock_agent, "_truncate_to_budget") as mock_truncate:
            mock_truncate.return_value = ("truncated", 5)
            result, stats = mock_agent._apply_context_budget(sections)

        assert result["test"] == "truncated"
        mock_truncate.assert_called_once()


class TestBudgetVisibility:
    """Test budget usage visibility in prompts."""

    @pytest.fixture
    def mock_agent(self) -> Agent:
        """Create a mock agent for testing."""
        with patch.object(Agent, "__init__", lambda x: None):
            agent = Agent()
            agent._llm_model = "gpt-4"
            return agent

    @patch("src.agents.agent.config_get")
    def test_format_budget_hidden_when_disabled(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """Budget usage should be hidden when show_budget_usage is false."""
        mock_config.return_value = False

        stats = {"test": (100, 200)}
        result = mock_agent._format_budget_usage(stats)

        assert result == ""

    @patch("src.agents.agent.config_get")
    def test_format_budget_visible_when_enabled(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """Budget usage should be visible when show_budget_usage is true."""
        def config_side_effect(key: str):
            if key == "context_budget.show_budget_usage":
                return True
            if key == "context_budget.total_tokens":
                return 4000
            return None

        mock_config.side_effect = config_side_effect

        stats = {"working_memory": (500, 600), "rag_memories": (350, 400)}
        result = mock_agent._format_budget_usage(stats)

        assert "## Context Budget" in result
        assert "working_memory" in result
        assert "rag_memories" in result
        assert "500/600" in result

    @patch("src.agents.agent.config_get")
    def test_format_budget_warns_near_limit(
        self, mock_config: MagicMock, mock_agent: Agent
    ) -> None:
        """Budget should show warning when section is near limit (>90%)."""
        def config_side_effect(key: str):
            if key == "context_budget.show_budget_usage":
                return True
            if key == "context_budget.total_tokens":
                return 4000
            return None

        mock_config.side_effect = config_side_effect

        stats = {"working_memory": (570, 600)}  # 95% usage
        result = mock_agent._format_budget_usage(stats)

        assert "⚠️" in result
