"""Pytest fixtures for agent_ecology tests.

Common fixtures for testing the agent ecology simulation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.world.ledger import Ledger
from src.world.world import World, ConfigDict


# =============================================================================
# Auto-mock memory when API key unavailable
# =============================================================================

@pytest.fixture(autouse=True)
def mock_memory_without_api_key() -> Any:
    """Auto-mock AgentMemory when GEMINI_API_KEY is not available.

    This allows tests that create Agent objects to run in CI without
    requiring real API credentials. Tests that specifically need real
    memory should use a real API key.
    """
    if os.getenv("GEMINI_API_KEY"):
        # Real API key available, don't mock
        yield None
        return

    # Create a mock memory that does nothing
    mock_memory = MagicMock()
    mock_memory.add.return_value = {"id": "mock-memory-id"}
    mock_memory.search.return_value = []
    mock_memory.get_all.return_value = []

    # Patch the get_memory function to return our mock
    with patch("src.agents.agent.get_memory", return_value=mock_memory):
        yield mock_memory


@pytest.fixture
def minimal_config() -> ConfigDict:
    """Create a minimal configuration dict for testing.

    This provides the minimum required configuration to instantiate
    a World object without needing external config files.
    """
    return {
        "world": {
            "max_ticks": 10
        },
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3
        },
        "logging": {
            "output_file": "test_run.jsonl"
        },
        "principals": [
            {"id": "agent_1", "starting_scrip": 100},
            {"id": "agent_2", "starting_scrip": 100}
        ],
        "rights": {
            "default_compute_quota": 50,
            "default_disk_quota": 10000
        }
    }


@pytest.fixture
def test_ledger() -> Ledger:
    """Create a test Ledger instance with some principals.

    Pre-configured with two test principals:
    - test_agent_1: 100 scrip, 50 compute
    - test_agent_2: 200 scrip, 50 compute
    """
    ledger = Ledger()
    ledger.create_principal("test_agent_1", starting_scrip=100, starting_compute=50)
    ledger.create_principal("test_agent_2", starting_scrip=200, starting_compute=50)
    return ledger


@pytest.fixture
def test_world(minimal_config: ConfigDict, tmp_path: Path) -> World:
    """Create a test World instance with minimal configuration.

    Uses a temporary directory for the log file to avoid polluting
    the project directory during tests.

    Args:
        minimal_config: The minimal configuration fixture
        tmp_path: Pytest's temporary path fixture

    Returns:
        A configured World instance ready for testing
    """
    # Use temp directory for log file
    log_file = tmp_path / "test_run.jsonl"
    config = minimal_config.copy()
    config["logging"] = {"output_file": str(log_file)}

    return World(config)


@pytest.fixture
def empty_ledger() -> Ledger:
    """Create an empty Ledger instance with no principals."""
    return Ledger()


@pytest.fixture
def single_agent_config() -> ConfigDict:
    """Create a config with a single agent for simpler tests."""
    return {
        "world": {
            "max_ticks": 5
        },
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3
        },
        "logging": {
            "output_file": "test_single.jsonl"
        },
        "principals": [
            {"id": "solo_agent", "starting_scrip": 500}
        ],
        "rights": {
            "default_compute_quota": 100,
            "default_disk_quota": 5000
        }
    }


@pytest.fixture
def single_agent_world(single_agent_config: ConfigDict, tmp_path: Path) -> World:
    """Create a test World with a single agent.

    Useful for tests that don't need multi-agent interactions.
    """
    log_file = tmp_path / "test_single.jsonl"
    config = single_agent_config.copy()
    config["logging"] = {"output_file": str(log_file)}

    return World(config)
