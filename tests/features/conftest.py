"""Fixtures for per-feature E2E tests.

These tests operate at a higher level than unit tests, exercising
features end-to-end through the World API.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.world.ledger import Ledger
from src.world.artifacts import ArtifactStore
from src.world.world import World, ConfigDict
from src.world.genesis import GenesisEscrow, GenesisMint, GenesisStore


@pytest.fixture
def feature_world(tmp_path: Path) -> World:
    """Create a World configured for feature testing.

    Includes multiple agents with sufficient resources for trading scenarios.
    """
    log_file = tmp_path / "feature_test.jsonl"
    config: ConfigDict = {
        "world": {"max_ticks": 100},
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
            "default_compute_quota": 100,
            "default_disk_quota": 10000
        }
    }
    world = World(config)
    world.advance_tick()  # Initialize tick 1
    return world


@pytest.fixture
def ledger_with_principals() -> Ledger:
    """Ledger with test principals for ledger feature tests."""
    ledger = Ledger()
    ledger.create_principal("alice", starting_scrip=1000, starting_compute=100)
    ledger.create_principal("bob", starting_scrip=500, starting_compute=100)
    ledger.create_principal("charlie", starting_scrip=200, starting_compute=100)
    return ledger


@pytest.fixture
def escrow_with_store() -> tuple[GenesisEscrow, ArtifactStore, Ledger]:
    """Set up escrow with store and ledger for escrow feature tests."""
    ledger = Ledger()
    store = ArtifactStore()
    ledger.create_principal("seller", starting_scrip=100, starting_compute=50)
    ledger.create_principal("buyer", starting_scrip=500, starting_compute=50)
    ledger.create_principal("restricted_buyer", starting_scrip=500, starting_compute=50)

    escrow = GenesisEscrow(ledger, store)
    return escrow, store, ledger


@pytest.fixture
def store_with_ledger() -> tuple[GenesisStore, ArtifactStore, Ledger]:
    """Set up genesis_store with artifacts and ledger."""
    ledger = Ledger()
    artifacts = ArtifactStore()
    ledger.create_principal("creator", starting_scrip=100, starting_compute=50)

    store = GenesisStore(artifacts)
    return store, artifacts, ledger
