"""Tests for artifact interface schemas (Plan #14)."""

from __future__ import annotations

import pytest

from src.world.artifacts import Artifact, default_policy
from src.world.genesis import GenesisLedger
from src.world.ledger import Ledger


class TestArtifactInterface:
    """Tests for the interface field on artifacts."""

    def test_interface_field_optional(self) -> None:
        """Interface can be None (optional field)."""
        artifact = Artifact(
            id="test",
            type="data",
            content="test content",
            created_by="alice",
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )
        assert artifact.interface is None

    def test_interface_field_can_be_set(self) -> None:
        """Interface can be set with a schema."""
        interface = {
            "description": "A test artifact",
            "tools": [
                {
                    "name": "greet",
                    "description": "Say hello",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            ]
        }
        artifact = Artifact(
            id="test",
            type="executable",
            content="",
            created_by="alice",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            executable=True,
            interface=interface,
        )
        assert artifact.interface is not None
        assert artifact.interface["tools"][0]["name"] == "greet"

    def test_interface_included_in_to_dict(self) -> None:
        """Interface is included in to_dict() when set."""
        interface = {"description": "Test", "tools": []}
        artifact = Artifact(
            id="test",
            type="data",
            content="test",
            created_by="alice",
            created_at="2024-01-01",
            updated_at="2024-01-01",
            interface=interface,
        )
        result = artifact.to_dict()
        assert "interface" in result
        assert result["interface"]["description"] == "Test"

    def test_interface_not_in_to_dict_when_none(self) -> None:
        """Interface is not included in to_dict() when None."""
        artifact = Artifact(
            id="test",
            type="data",
            content="test",
            created_by="alice",
            created_at="2024-01-01",
            updated_at="2024-01-01",
        )
        result = artifact.to_dict()
        assert "interface" not in result


class TestGenesisInterface:
    """Tests for genesis artifact interfaces."""

    def test_genesis_ledger_has_interface(self) -> None:
        """GenesisLedger has a detailed interface schema."""
        ledger = Ledger()
        genesis_ledger = GenesisLedger(ledger)

        interface = genesis_ledger.get_interface()

        assert "description" in interface
        assert "tools" in interface
        assert len(interface["tools"]) > 0

    def test_genesis_ledger_interface_has_input_schemas(self) -> None:
        """GenesisLedger interface includes inputSchema for each method."""
        ledger = Ledger()
        genesis_ledger = GenesisLedger(ledger)

        interface = genesis_ledger.get_interface()

        # Find the transfer method
        transfer_tool = None
        for tool in interface["tools"]:
            if tool["name"] == "transfer":
                transfer_tool = tool
                break

        assert transfer_tool is not None
        assert "inputSchema" in transfer_tool
        assert transfer_tool["inputSchema"]["type"] == "object"
        assert "to" in transfer_tool["inputSchema"]["properties"]
        assert "amount" in transfer_tool["inputSchema"]["properties"]
        assert "to" in transfer_tool["inputSchema"]["required"]
        assert "amount" in transfer_tool["inputSchema"]["required"]

    def test_genesis_ledger_balance_schema(self) -> None:
        """Balance method has correct input schema."""
        ledger = Ledger()
        genesis_ledger = GenesisLedger(ledger)

        interface = genesis_ledger.get_interface()

        balance_tool = None
        for tool in interface["tools"]:
            if tool["name"] == "balance":
                balance_tool = tool
                break

        assert balance_tool is not None
        assert balance_tool["inputSchema"]["properties"]["agent_id"]["type"] == "string"
        assert "agent_id" in balance_tool["inputSchema"]["required"]
