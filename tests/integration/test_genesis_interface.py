"""Tests for genesis artifact interfaces (Plan #54).

These tests verify that genesis artifacts have properly structured
interfaces using the reserved terms for discoverability.
"""

import pytest
from typing import Any

from src.world.genesis import (
    GenesisLedger,
    GenesisMint,
    GenesisEscrow,
    GenesisEventLog,
)
from src.world.artifacts import ArtifactStore
from src.world.world import World
from src.config import get_validated_config


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a basic artifact store for testing."""
    return ArtifactStore()


class TestGenesisLedgerInterface:
    """Test GenesisLedger has proper interface."""
    
    def test_genesis_ledger_interface(self) -> None:
        """GenesisLedger has interface with reserved terms."""
        config = get_validated_config()
        ledger = GenesisLedger(config.genesis.ledger)
        
        interface = ledger.get_interface()
        
        # Must have description
        assert "description" in interface
        assert isinstance(interface["description"], str)
        assert len(interface["description"]) > 0
        
        # Should have methods (tools in MCP parlance)
        assert "tools" in interface or "methods" in interface
        methods = interface.get("tools") or interface.get("methods", [])
        assert len(methods) > 0
        
        # Each method should have name and description
        for method in methods:
            assert "name" in method
            assert "description" in method
    
    def test_genesis_ledger_balance_method(self) -> None:
        """GenesisLedger interface includes balance method."""
        config = get_validated_config()
        ledger = GenesisLedger(config.genesis.ledger)
        
        interface = ledger.get_interface()
        methods = interface.get("tools") or interface.get("methods", [])
        method_names = [m["name"] for m in methods]
        
        assert "balance" in method_names
    
    def test_genesis_ledger_transfer_method(self) -> None:
        """GenesisLedger interface includes transfer method."""
        config = get_validated_config()
        ledger = GenesisLedger(config.genesis.ledger)
        
        interface = ledger.get_interface()
        methods = interface.get("tools") or interface.get("methods", [])
        method_names = [m["name"] for m in methods]
        
        assert "transfer" in method_names


class TestGenesisMintInterface:
    """Test GenesisMint has proper interface."""
    
    def test_genesis_mint_interface(self) -> None:
        """GenesisMint has interface with reserved terms."""
        config = get_validated_config()
        mint = GenesisMint(config.genesis.mint)
        
        interface = mint.get_interface()
        
        # Must have description
        assert "description" in interface
        assert isinstance(interface["description"], str)
        
        # Should have methods
        assert "tools" in interface or "methods" in interface
        methods = interface.get("tools") or interface.get("methods", [])
        assert len(methods) > 0


class TestGenesisEscrowInterface:
    """Test GenesisEscrow has proper interface."""
    
    def test_genesis_escrow_interface(self, artifact_store: ArtifactStore) -> None:
        """GenesisEscrow has interface with reserved terms."""
        config = get_validated_config()
        escrow = GenesisEscrow(config.genesis.escrow, artifact_store)
        
        interface = escrow.get_interface()
        
        # Must have description
        assert "description" in interface
        assert isinstance(interface["description"], str)
        
        # Should have methods
        assert "tools" in interface or "methods" in interface


class TestGenesisEventLogInterface:
    """Test GenesisEventLog has proper interface."""
    
    def test_genesis_event_log_interface(self) -> None:
        """GenesisEventLog has interface with reserved terms."""
        config = get_validated_config()
        event_log = GenesisEventLog(config.genesis.event_log)
        
        interface = event_log.get_interface()
        
        # Must have description
        assert "description" in interface
        assert isinstance(interface["description"], str)
