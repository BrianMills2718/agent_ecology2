"""Tests for Plan #187: Extended Thinking (reasoning_effort) support.

Tests verify:
1. call_llm accepts reasoning_effort parameter
2. Parameter is passed to litellm.completion for Claude models
3. Parameter is not passed for non-Claude models (with warning)
4. Config integration works correctly
"""

import pytest
from unittest.mock import MagicMock, patch

from src.world.llm_client import call_llm, _is_claude_model


def _make_mock_response() -> MagicMock:
    """Create a mock litellm response object."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = "test response"
    mock.choices[0].message.tool_calls = None
    mock.usage.prompt_tokens = 50
    mock.usage.completion_tokens = 50
    mock.usage.total_tokens = 100
    return mock


class TestCallLLMReasoningEffort:
    """Tests for reasoning_effort parameter in call_llm."""

    def test_is_claude_model_detection(self) -> None:
        """Test Claude model detection helper."""
        # Should detect Claude models
        assert _is_claude_model("anthropic/claude-3-opus") is True
        assert _is_claude_model("claude-3-sonnet") is True
        assert _is_claude_model("ANTHROPIC/CLAUDE-3.5") is True

        # Should not detect non-Claude models
        assert _is_claude_model("gpt-4") is False
        assert _is_claude_model("gemini/gemini-2.0-flash") is False
        assert _is_claude_model("llama-3") is False

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.01)
    @patch("src.world.llm_client.litellm.completion")
    def test_reasoning_effort_passed_to_claude_model(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """Verify reasoning_effort is passed to litellm.completion for Claude models."""
        mock_completion.return_value = _make_mock_response()

        call_llm(
            model="anthropic/claude-3-opus",
            messages=[{"role": "user", "content": "test"}],
            reasoning_effort="high",
        )

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "high"

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.01)
    @patch("src.world.llm_client.litellm.completion")
    def test_reasoning_effort_not_passed_for_non_claude_model(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """Verify reasoning_effort is not passed for non-Claude models."""
        mock_completion.return_value = _make_mock_response()

        call_llm(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": "test"}],
            reasoning_effort="high",
        )

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.01)
    @patch("src.world.llm_client.litellm.completion")
    def test_reasoning_effort_none_not_passed(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """Verify reasoning_effort=None is not passed to litellm."""
        mock_completion.return_value = _make_mock_response()

        call_llm(
            model="anthropic/claude-3-opus",
            messages=[{"role": "user", "content": "test"}],
            reasoning_effort=None,
        )

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs


class TestConfigIntegration:
    """Tests for reasoning_effort config integration."""

    def test_llm_config_has_reasoning_effort_field(self) -> None:
        """Verify LLMConfig schema includes reasoning_effort."""
        from src.config_schema import LLMConfig

        # Check field exists and has correct type
        fields = LLMConfig.model_fields
        assert "reasoning_effort" in fields, "reasoning_effort field missing from LLMConfig"

        field = fields["reasoning_effort"]
        # Check default is None
        assert field.default is None, f"Expected default=None, got {field.default}"

    def test_llm_config_validates_reasoning_effort_values(self) -> None:
        """Verify only valid reasoning_effort values are accepted."""
        from src.config_schema import LLMConfig
        from pydantic import ValidationError

        # Valid values should work
        for value in [None, "none", "low", "medium", "high"]:
            config = LLMConfig(reasoning_effort=value)
            assert config.reasoning_effort == value

        # Invalid values should fail
        with pytest.raises(ValidationError):
            LLMConfig(reasoning_effort="invalid")

        with pytest.raises(ValidationError):
            LLMConfig(reasoning_effort="NONE")  # Case sensitive

    def test_config_get_reasoning_effort(self) -> None:
        """Test that reasoning_effort is a valid config path."""
        # Just verify the config schema supports the path
        from src.config_schema import LLMConfig

        # Create a config with reasoning_effort
        config = LLMConfig(reasoning_effort="high")
        assert config.reasoning_effort == "high"

        # Verify None is the default
        default_config = LLMConfig()
        assert default_config.reasoning_effort is None
