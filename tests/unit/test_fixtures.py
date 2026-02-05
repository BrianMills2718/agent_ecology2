"""Tests to verify that pytest fixtures work correctly."""

from __future__ import annotations

import pytest

from src.world.ledger import Ledger
from src.world.world import World


class TestFixtures:
    """Tests to verify conftest fixtures work properly."""

    def test_minimal_config_fixture(self, minimal_config):
        """Verify minimal_config fixture provides required keys."""
        assert "world" in minimal_config
        # Note: max_ticks removed in Plan #102 - world section now optional/empty
        assert "costs" in minimal_config
        assert "logging" in minimal_config
        assert "principals" in minimal_config
        assert len(minimal_config["principals"]) >= 1
        assert "rate_limiting" in minimal_config  # Required for compute

    def test_test_ledger_fixture(self, test_ledger):
        """Verify test_ledger fixture creates a valid Ledger."""
        assert isinstance(test_ledger, Ledger)
        # Check principals were created
        assert test_ledger.get_scrip("test_agent_1") == 100
        assert test_ledger.get_scrip("test_agent_2") == 200
        # Note: Resources are set up separately via set_resource(), not in fixture

    def test_test_world_fixture(self, test_world):
        """Verify test_world fixture creates a valid World."""
        assert isinstance(test_world, World)
        assert test_world.event_number == 0  # Event counter starts at 0
        # Note: max_ticks removed in Plan #102 - execution limits now time-based
        assert len(test_world.principal_ids) == 2
        assert "agent_1" in test_world.principal_ids
        assert "agent_2" in test_world.principal_ids

    def test_empty_ledger_fixture(self, empty_ledger):
        """Verify empty_ledger fixture creates an empty Ledger."""
        assert isinstance(empty_ledger, Ledger)
        assert empty_ledger.get_all_scrip() == {}

    def test_single_agent_config_fixture(self, single_agent_config):
        """Verify single_agent_config has exactly one principal."""
        assert len(single_agent_config["principals"]) == 1
        assert single_agent_config["principals"][0]["id"] == "solo_agent"
        assert single_agent_config["principals"][0]["starting_scrip"] == 500

    def test_single_agent_world_fixture(self, single_agent_world):
        """Verify single_agent_world creates a World with one agent."""
        assert isinstance(single_agent_world, World)
        assert len(single_agent_world.principal_ids) == 1
        assert "solo_agent" in single_agent_world.principal_ids

    def test_world_advance_tick(self, test_world):
        """Verify World can advance ticks."""
        initial_tick = test_world.event_number
        assert test_world.advance_tick() is True
        assert test_world.event_number == initial_tick + 1

    def test_ledger_operations(self, test_ledger):
        """Verify basic Ledger operations work."""
        # Test scrip transfer
        assert test_ledger.transfer_scrip("test_agent_2", "test_agent_1", 50) is True
        assert test_ledger.get_scrip("test_agent_1") == 150
        assert test_ledger.get_scrip("test_agent_2") == 150
