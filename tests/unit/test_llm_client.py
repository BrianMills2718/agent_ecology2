"""Tests for src/world/llm_client.py (Plan #311).

Tests the thin LLM client module:
- call_llm returns LLMCallResult
- call_llm extracts content from response
- call_llm computes cost via litellm.completion_cost
- call_llm passes num_retries
- call_llm passes reasoning_effort for Claude models only
- call_llm raises on error (fail loud)
- call_llm_with_tools passes tools and extracts tool_calls
"""

import pytest
from dataclasses import dataclass
from unittest.mock import patch, MagicMock

from src.world.llm_client import (
    call_llm,
    call_llm_with_tools,
    LLMCallResult,
)


# --- Mock helpers ---

@dataclass
class MockUsage:
    prompt_tokens: int = 10
    completion_tokens: int = 5
    total_tokens: int = 15


@dataclass
class MockMessage:
    content: str = "Hello, world!"
    tool_calls: list | None = None


@dataclass
class MockChoice:
    message: MockMessage | None = None

    def __post_init__(self) -> None:
        if self.message is None:
            self.message = MockMessage()


@dataclass
class MockResponse:
    choices: list | None = None
    usage: MockUsage | None = None

    def __post_init__(self) -> None:
        if self.choices is None:
            self.choices = [MockChoice()]
        if self.usage is None:
            self.usage = MockUsage()


def _mock_response(
    content: str = "Hello, world!",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> MockResponse:
    return MockResponse(
        choices=[MockChoice(message=MockMessage(content=content))],
        usage=MockUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


# --- Tests ---

@pytest.mark.plans([311])
class TestCallLLM:
    """Test call_llm function."""

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_returns_llm_call_result(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm returns an LLMCallResult dataclass."""
        mock_completion.return_value = _mock_response()
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        assert isinstance(result, LLMCallResult)

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_extracts_content(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm extracts content from response.choices[0].message.content."""
        mock_completion.return_value = _mock_response(content="Test response")
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        assert result.content == "Test response"

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.0042)
    @patch("src.world.llm_client.litellm.completion")
    def test_computes_cost(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm computes cost via litellm.completion_cost."""
        mock_completion.return_value = _mock_response()
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        assert result.cost == 0.0042

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_passes_num_retries(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm passes num_retries to litellm.completion."""
        mock_completion.return_value = _mock_response()
        call_llm("gpt-4", [{"role": "user", "content": "Hi"}], num_retries=5)
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["num_retries"] == 5

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_passes_reasoning_effort_for_claude(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm passes reasoning_effort for Claude models."""
        mock_completion.return_value = _mock_response()
        call_llm(
            "anthropic/claude-3-opus",
            [{"role": "user", "content": "Hi"}],
            reasoning_effort="high",
        )
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["reasoning_effort"] == "high"

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_ignores_reasoning_effort_for_non_claude(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm ignores reasoning_effort for non-Claude models."""
        mock_completion.return_value = _mock_response()
        call_llm(
            "gpt-4",
            [{"role": "user", "content": "Hi"}],
            reasoning_effort="high",
        )
        call_kwargs = mock_completion.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion")
    def test_raises_on_error(self, mock_completion: MagicMock) -> None:
        """call_llm raises on LLM errors (fail loud, no silent fallbacks)."""
        mock_completion.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            call_llm("gpt-4", [{"role": "user", "content": "Hi"}])

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_extracts_usage(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm extracts token usage from response."""
        mock_completion.return_value = _mock_response(
            prompt_tokens=20, completion_tokens=10
        )
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        assert result.usage["prompt_tokens"] == 20
        assert result.usage["completion_tokens"] == 10
        assert result.usage["total_tokens"] == 30

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", side_effect=Exception("no cost data"))
    @patch("src.world.llm_client.litellm.completion")
    def test_cost_fallback_on_error(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm falls back to token-based cost if completion_cost fails."""
        mock_completion.return_value = _mock_response()
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        # Fallback: 15 tokens * 0.000001 = 0.000015
        assert result.cost == pytest.approx(0.000015)

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_empty_tool_calls_by_default(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm returns empty tool_calls by default."""
        mock_completion.return_value = _mock_response()
        result = call_llm("gpt-4", [{"role": "user", "content": "Hi"}])
        assert result.tool_calls == []


@pytest.mark.plans([311])
class TestCallLLMWithTools:
    """Test call_llm_with_tools function."""

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_passes_tools_param(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm_with_tools passes tools to litellm.completion."""
        mock_completion.return_value = _mock_response()
        tools = [{"type": "function", "function": {"name": "test"}}]
        call_llm_with_tools("gpt-4", [{"role": "user", "content": "Hi"}], tools)
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["tools"] == tools

    # mock-ok: LLM calls are external API
    @patch("src.world.llm_client.litellm.completion_cost", return_value=0.001)
    @patch("src.world.llm_client.litellm.completion")
    def test_extracts_tool_calls(
        self, mock_completion: MagicMock, mock_cost: MagicMock
    ) -> None:
        """call_llm_with_tools extracts tool_calls from response."""
        mock_tc = MagicMock()
        mock_tc.id = "call_123"
        mock_tc.type = "function"
        mock_tc.function.name = "test_func"
        mock_tc.function.arguments = '{"arg": "value"}'

        mock_msg = MockMessage(content="", tool_calls=[mock_tc])
        response = MockResponse(
            choices=[MockChoice(message=mock_msg)],
            usage=MockUsage(),
        )
        mock_completion.return_value = response

        tools = [{"type": "function", "function": {"name": "test_func"}}]
        result = call_llm_with_tools(
            "gpt-4", [{"role": "user", "content": "Hi"}], tools
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["function"]["name"] == "test_func"
