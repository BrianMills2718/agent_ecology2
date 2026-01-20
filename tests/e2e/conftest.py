"""E2E test fixtures.

Provides mocked LLM for E2E tests to avoid real API costs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.models import FlatActionResponse, FlatAction


@pytest.fixture
def mock_llm_response() -> FlatActionResponse:
    """Create a standard mock LLM response."""
    return FlatActionResponse(
        reasoning="I will perform a noop action to observe the world state.",
        action=FlatAction(action_type="noop"),
    )


@pytest.fixture
def mock_llm_usage() -> dict[str, Any]:
    """Create mock token usage stats."""
    return {
        "input_tokens": 150,
        "output_tokens": 50,
        "total_tokens": 200,
        "cost": 0.0001,
    }


@pytest.fixture
def mock_llm(
    mock_llm_response: FlatActionResponse,
    mock_llm_usage: dict[str, Any],
) -> Generator[MagicMock, None, None]:
    """Mock LLM provider for E2E tests.

    This patches litellm.acompletion to return a mocked response,
    avoiding real API calls during E2E tests.

    Usage:
        def test_something(mock_llm):
            # LLM calls are now mocked
            runner = SimulationRunner(config)
            world = runner.run_sync()
    """
    # Create async mock for litellm.acompletion
    mock_completion = AsyncMock()

    # Create mock response that looks like litellm response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = mock_llm_response.model_dump_json()
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = mock_llm_usage["input_tokens"]
    mock_response.usage.completion_tokens = mock_llm_usage["output_tokens"]
    mock_response.usage.total_tokens = mock_llm_usage["total_tokens"]

    mock_completion.return_value = mock_response

    # Also mock synchronous completion
    mock_sync = MagicMock(return_value=mock_response)

    with patch("litellm.acompletion", mock_completion), \
         patch("litellm.completion", mock_sync):
        yield mock_completion


@pytest.fixture
def e2e_config(tmp_path: Path) -> dict[str, Any]:
    """Create E2E test configuration.

    Uses minimal settings for fast test execution.
    Plan #109: Removed max_ticks (tick mode removed in Plan #102).
    Tests must call run_sync(duration=X) with a short duration.
    """
    log_file = tmp_path / "e2e_test.jsonl"

    return {
        "world": {},  # Plan #102: max_ticks removed, use duration param instead
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "logging": {
            "output_file": str(log_file),
            "log_dir": str(tmp_path / "llm_logs"),
        },
        "principals": [
            {"id": "test_agent_1", "starting_scrip": 100},
        ],
        "rights": {
            "default_compute_quota": 100,
            "default_disk_quota": 10000,
        },
        "llm": {
            "default_model": "gemini/gemini-3-flash-preview",
            "rate_limit_delay": 0,  # No delay for tests
        },
        "budget": {
            "max_api_cost": 0,  # Unlimited (mocked anyway)
            "checkpoint_interval": 0,  # Disable checkpoints
            "checkpoint_on_end": False,
        },
        "rate_limiting": {
            "enabled": False,
        },
        # Plan #102: use_autonomous_loops removed - runner is always autonomous now
    }


@pytest.fixture
def e2e_autonomous_config(e2e_config: dict[str, Any]) -> dict[str, Any]:
    """Configuration for autonomous mode E2E tests."""
    config = e2e_config.copy()
    config["execution"] = {
        "use_autonomous_loops": True,
        "agent_loop": {
            "min_loop_delay": 0.01,
            "max_loop_delay": 0.1,
            "resource_check_interval": 0.01,
            "max_consecutive_errors": 2,
            "resources_to_check": [],
        },
    }
    config["rate_limiting"] = {
        "enabled": True,
        "window_seconds": 1.0,
        "resources": {
            "llm_calls": {"max_per_window": 100},
        },
    }
    return config
