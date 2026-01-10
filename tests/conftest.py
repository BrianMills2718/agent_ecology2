"""Pytest fixtures for agent_ecology tests.

Common fixtures for testing the agent ecology simulation.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from world.ledger import Ledger
from world.world import World, ConfigDict


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
            "actions": {
                "noop": 1,
                "read_artifact": 2,
                "write_artifact": 5,
                "invoke_artifact": 1
            },
            "default": 1,
            "execution_gas": 2
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
            "actions": {
                "noop": 1,
                "read_artifact": 2,
                "write_artifact": 5,
                "invoke_artifact": 1
            },
            "default": 1,
            "execution_gas": 2
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
