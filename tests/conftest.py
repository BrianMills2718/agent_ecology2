"""Pytest fixtures for agent_ecology tests.

Common fixtures for testing the agent ecology simulation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.world.ledger import Ledger
from src.world.world import World, ConfigDict


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "plans(nums): mark test as belonging to plan number(s). "
        "Usage: @pytest.mark.plans([1, 6]) or @pytest.mark.plans(6)"
    )
    config.addinivalue_line(
        "markers",
        "feature_type(type): mark test as 'feature', 'enabler', or 'refactor'"
    )
    config.addinivalue_line(
        "markers",
        "external: mark test as requiring external services (real API calls)"
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options."""
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="Run tests marked as external (real API calls, slow)",
    )
    parser.addoption(
        "--plan",
        action="store",
        type=int,
        default=None,
        help="Run tests for a specific plan number",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Filter tests based on command-line options."""
    # Handle --run-external
    if not config.getoption("--run-external"):
        skip_external = pytest.mark.skip(reason="need --run-external option to run")
        for item in items:
            if "external" in item.keywords:
                item.add_marker(skip_external)

    # Handle --plan N
    plan_filter = config.getoption("--plan")
    if plan_filter is not None:
        selected = []
        deselected = []
        for item in items:
            marker = item.get_closest_marker("plans")
            if marker is not None:
                plans_arg = marker.args[0] if marker.args else []
                # Handle both @pytest.mark.plans(6) and @pytest.mark.plans([1, 6])
                if isinstance(plans_arg, int):
                    plans_arg = [plans_arg]
                if plan_filter in plans_arg:
                    selected.append(item)
                    continue
            deselected.append(item)
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


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
