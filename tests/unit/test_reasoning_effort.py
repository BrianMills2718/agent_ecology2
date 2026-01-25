"""Tests for Plan #187: Extended Thinking (reasoning_effort) support.

Tests verify:
1. LLMProvider accepts reasoning_effort parameter
2. Parameter is passed to Claude models
3. Parameter is ignored for non-Claude models with warning
4. Config integration works correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLLMProviderReasoningEffort:
    """Tests for reasoning_effort parameter in LLMProvider."""

    def test_generate_async_accepts_reasoning_effort_parameter(self) -> None:
        """Verify generate_async accepts reasoning_effort parameter."""
        from llm_provider_standalone.llm_provider import LLMProvider

        provider = LLMProvider(model="test-model", log_dir="/tmp/test_logs")
        # Check the method signature accepts the parameter
        import inspect
        sig = inspect.signature(provider.generate_async)
        assert "reasoning_effort" in sig.parameters, "reasoning_effort parameter missing"

    def test_generate_accepts_reasoning_effort_parameter(self) -> None:
        """Verify sync generate accepts reasoning_effort parameter."""
        from llm_provider_standalone.llm_provider import LLMProvider

        provider = LLMProvider(model="test-model", log_dir="/tmp/test_logs")
        import inspect
        sig = inspect.signature(provider.generate)
        assert "reasoning_effort" in sig.parameters, "reasoning_effort parameter missing"

    def test_is_claude_model_detection(self) -> None:
        """Test Claude model detection helper."""
        from llm_provider_standalone.llm_provider import LLMProvider

        provider = LLMProvider(model="test", log_dir="/tmp/test_logs")

        # Should detect Claude models
        assert provider._is_claude_model("anthropic/claude-3-opus") is True
        assert provider._is_claude_model("claude-3-sonnet") is True
        assert provider._is_claude_model("ANTHROPIC/CLAUDE-3.5") is True

        # Should not detect non-Claude models
        assert provider._is_claude_model("gpt-4") is False
        assert provider._is_claude_model("gemini/gemini-2.0-flash") is False
        assert provider._is_claude_model("llama-3") is False

    @pytest.mark.asyncio
    async def test_reasoning_effort_passed_to_claude_model(self) -> None:
        """Verify reasoning_effort is passed to LiteLLM for Claude models."""
        from llm_provider_standalone.llm_provider import LLMProvider
        from dataclasses import dataclass
        import tempfile

        @dataclass
        class MockUsage:
            total_tokens: int = 100
            prompt_tokens: int = 50
            completion_tokens: int = 50

        @dataclass
        class MockMessage:
            content: str = "test response"

        @dataclass
        class MockChoice:
            message: MockMessage = None
            def __post_init__(self):
                if self.message is None:
                    self.message = MockMessage()

        @dataclass
        class MockResponse:
            choices: list = None
            usage: MockUsage = None
            def __post_init__(self):
                if self.choices is None:
                    self.choices = [MockChoice()]
                if self.usage is None:
                    self.usage = MockUsage()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LLMProvider(
                model="anthropic/claude-3-opus",
                log_dir=tmpdir
            )

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = MockResponse()

                await provider.generate_async(
                    "test prompt",
                    reasoning_effort="high"
                )

                # Check that reasoning_effort was passed to acompletion
                mock_completion.assert_called_once()
                call_kwargs = mock_completion.call_args.kwargs
                assert call_kwargs.get("reasoning_effort") == "high", \
                    f"Expected reasoning_effort='high', got {call_kwargs}"

    @pytest.mark.asyncio
    async def test_reasoning_effort_ignored_for_non_claude_model(self) -> None:
        """Verify reasoning_effort is ignored for non-Claude models."""
        from llm_provider_standalone.llm_provider import LLMProvider
        from dataclasses import dataclass
        import logging
        import tempfile

        @dataclass
        class MockUsage:
            total_tokens: int = 100
            prompt_tokens: int = 50
            completion_tokens: int = 50

        @dataclass
        class MockMessage:
            content: str = "test response"

        @dataclass
        class MockChoice:
            message: MockMessage = None
            def __post_init__(self):
                if self.message is None:
                    self.message = MockMessage()

        @dataclass
        class MockResponse:
            choices: list = None
            usage: MockUsage = None
            def __post_init__(self):
                if self.choices is None:
                    self.choices = [MockChoice()]
                if self.usage is None:
                    self.usage = MockUsage()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LLMProvider(
                model="gemini/gemini-2.0-flash",
                log_dir=tmpdir
            )

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = MockResponse()

                with patch.object(logging, "warning") as mock_warning:
                    await provider.generate_async(
                        "test prompt",
                        reasoning_effort="high"
                    )

                    # Check that reasoning_effort was NOT passed
                    call_kwargs = mock_completion.call_args.kwargs
                    assert "reasoning_effort" not in call_kwargs, \
                        "reasoning_effort should not be passed to non-Claude models"

                    # Check that warning was logged
                    mock_warning.assert_called()
                    warning_msg = mock_warning.call_args[0][0]
                    assert "reasoning_effort" in warning_msg
                    assert "ignored" in warning_msg

    @pytest.mark.asyncio
    async def test_reasoning_effort_none_not_passed(self) -> None:
        """Verify reasoning_effort='none' is not passed to the API."""
        from llm_provider_standalone.llm_provider import LLMProvider
        from dataclasses import dataclass
        import tempfile

        @dataclass
        class MockUsage:
            total_tokens: int = 100
            prompt_tokens: int = 50
            completion_tokens: int = 50

        @dataclass
        class MockMessage:
            content: str = "test response"

        @dataclass
        class MockChoice:
            message: MockMessage = None
            def __post_init__(self):
                if self.message is None:
                    self.message = MockMessage()

        @dataclass
        class MockResponse:
            choices: list = None
            usage: MockUsage = None
            def __post_init__(self):
                if self.choices is None:
                    self.choices = [MockChoice()]
                if self.usage is None:
                    self.usage = MockUsage()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LLMProvider(
                model="anthropic/claude-3-opus",
                log_dir=tmpdir
            )

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = MockResponse()

                await provider.generate_async(
                    "test prompt",
                    reasoning_effort="none"
                )

                # reasoning_effort="none" should not be passed
                call_kwargs = mock_completion.call_args.kwargs
                assert "reasoning_effort" not in call_kwargs, \
                    "reasoning_effort='none' should not be passed to API"

    @pytest.mark.asyncio
    async def test_reasoning_effort_logged_in_metadata(self) -> None:
        """Verify reasoning_effort is included in call metadata."""
        from llm_provider_standalone.llm_provider import LLMProvider
        from dataclasses import dataclass
        import json
        import os
        import tempfile

        @dataclass
        class MockUsage:
            total_tokens: int = 10
            prompt_tokens: int = 5
            completion_tokens: int = 5

        @dataclass
        class MockMessage:
            content: str = "test"

        @dataclass
        class MockChoice:
            message: MockMessage = None
            def __post_init__(self):
                if self.message is None:
                    self.message = MockMessage()

        @dataclass
        class MockResponse:
            choices: list = None
            usage: MockUsage = None
            def __post_init__(self):
                if self.choices is None:
                    self.choices = [MockChoice()]
                if self.usage is None:
                    self.usage = MockUsage()

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LLMProvider(
                model="anthropic/claude-3-opus",
                log_dir=tmpdir
            )

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = MockResponse()

                await provider.generate_async(
                    "test prompt",
                    reasoning_effort="medium"
                )

            # Find and read the log file
            log_files = []
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith(".json"):
                        log_files.append(os.path.join(root, f))

            assert len(log_files) == 1, f"Expected 1 log file, found {len(log_files)}"

            with open(log_files[0]) as f:
                log_data = json.load(f)

            # Check that reasoning_effort is in the parameters
            assert log_data["parameters"]["reasoning_effort"] == "medium"


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
