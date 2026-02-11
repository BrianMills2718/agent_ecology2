"""Pytest fixtures for agent_ecology tests.

Common fixtures for testing the agent ecology simulation.
"""

from __future__ import annotations

# Load environment variables from .env before any tests run
# Tries current directory first, then main repo location for worktrees
from pathlib import Path
from dotenv import load_dotenv

def _find_main_repo_env() -> Path | None:
    """Find .env in main repo if we're in a worktree."""
    git_file = Path.cwd() / ".git"
    if git_file.is_file():
        # Worktree: .git is a file pointing to main repo
        # Format: "gitdir: /path/to/main/.git/worktrees/branch-name"
        content = git_file.read_text().strip()
        if content.startswith("gitdir:"):
            git_path = Path(content.split(": ", 1)[1])
            # Navigate up from .git/worktrees/branch to main repo
            main_repo = git_path.parent.parent.parent
            main_env = main_repo / ".env"
            if main_env.exists():
                return main_env
    return None

# Try to load from current directory
if not load_dotenv():
    # Fallback: try main repo location (for worktrees)
    main_env = _find_main_repo_env()
    if main_env:
        load_dotenv(main_env)

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
        "feature(name): mark test as belonging to a feature. "
        "Usage: @pytest.mark.feature('escrow') - maps to meta/acceptance_gates/<name>.yaml"
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
    parser.addoption(
        "--feature",
        action="store",
        type=str,
        default=None,
        help="Run tests for a specific feature (e.g., --feature escrow)",
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
        return  # Don't apply feature filter if plan filter was used

    # Handle --feature NAME
    feature_filter = config.getoption("--feature")
    if feature_filter is not None:
        selected = []
        deselected = []
        for item in items:
            marker = item.get_closest_marker("feature")
            if marker is not None:
                feature_name = marker.args[0] if marker.args else ""
                if feature_name == feature_filter:
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

    Note: max_ticks removed in Plan #102. Execution limits are now
    time-based (duration) or cost-based (budget). Rate limiting provides compute.
    """
    return {
        "world": {},
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
            "default_llm_tokens_quota": 50,
            "default_disk_quota": 10000
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}}
        },
        # Disable genesis agents for test isolation
        "discourse_analyst": {"enabled": False},
        "discourse_analyst_2": {"enabled": False},
        "discourse_analyst_3": {"enabled": False},
        "discourse_v2": {"enabled": False},
        "discourse_v2_2": {"enabled": False},
        "discourse_v2_3": {"enabled": False},
        "alpha_prime": {"enabled": False},
    }


@pytest.fixture
def test_ledger() -> Ledger:
    """Create a test Ledger instance with some principals.

    Pre-configured with two test principals:
    - test_agent_1: 100 scrip
    - test_agent_2: 200 scrip

    Note: Resources (like llm_budget) are set up separately via set_resource().
    """
    ledger = Ledger()
    ledger.create_principal("test_agent_1", starting_scrip=100)
    ledger.create_principal("test_agent_2", starting_scrip=200)
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
        "world": {},
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
            "default_llm_tokens_quota": 100,
            "default_disk_quota": 5000
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}}
        },
        # Disable genesis agents for test isolation
        "discourse_analyst": {"enabled": False},
        "discourse_analyst_2": {"enabled": False},
        "discourse_analyst_3": {"enabled": False},
        "discourse_v2": {"enabled": False},
        "discourse_v2_2": {"enabled": False},
        "discourse_v2_3": {"enabled": False},
        "alpha_prime": {"enabled": False},
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


# --- Feature Acceptance Test Fixtures ---
# These fixtures support acceptance tests in tests/integration/*_acceptance.py


from src.world.artifacts import ArtifactStore
# Plan #254: Genesis removed - escrow fixtures removed


@pytest.fixture
def feature_world(tmp_path: Path) -> World:
    """Create a World configured for feature testing.

    Includes multiple agents with sufficient resources for trading scenarios.
    """
    log_file = tmp_path / "feature_test.jsonl"
    config: ConfigDict = {
        "world": {},
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "logging": {"output_file": str(log_file)},
        "principals": [
            {"id": "alice", "starting_scrip": 1000},
            {"id": "bob", "starting_scrip": 500},
            {"id": "charlie", "starting_scrip": 200},
        ],
        "rights": {
            "default_llm_tokens_quota": 100,
            "default_disk_quota": 10000
        },
        "rate_limiting": {
            "enabled": True,
            "window_seconds": 60.0,
            "resources": {"llm_tokens": {"max_per_window": 1000}}
        },
        # Disable genesis agents for test isolation
        "discourse_analyst": {"enabled": False},
        "discourse_analyst_2": {"enabled": False},
        "discourse_analyst_3": {"enabled": False},
        "discourse_v2": {"enabled": False},
        "discourse_v2_2": {"enabled": False},
        "discourse_v2_3": {"enabled": False},
        "alpha_prime": {"enabled": False},
    }
    world = World(config)
    world.increment_event_counter()  # Initialize event count
    return world


@pytest.fixture
def ledger_with_principals() -> Ledger:
    """Ledger with test principals for ledger feature tests."""
    ledger = Ledger()
    ledger.create_principal("alice", starting_scrip=1000)
    ledger.create_principal("bob", starting_scrip=500)
    ledger.create_principal("charlie", starting_scrip=200)
    return ledger


# Plan #254: escrow_with_store fixture removed - genesis deleted
