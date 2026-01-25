"""Tests for Plan #165: Genesis Contracts as Artifacts.

Tests that genesis contracts are discoverable as artifacts, so agents can
read them via query_kernel to understand permission rules.

Note: genesis_store was removed in Plan #190. Discovery now uses query_kernel action.
"""

import pytest

from src.world.artifacts import ArtifactStore
from src.world.ledger import Ledger
from src.world.genesis.factory import create_genesis_artifacts
from src.world.genesis_contracts import (
    get_contract_by_id,
    list_genesis_contracts,
)


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a fresh artifact store."""
    return ArtifactStore()


@pytest.fixture
def ledger() -> Ledger:
    """Create a fresh ledger."""
    return Ledger()


@pytest.fixture
def genesis_artifacts(ledger: Ledger, artifact_store: ArtifactStore) -> dict:
    """Create genesis artifacts with default config."""
    def mint_callback(agent_id: str, amount: int) -> None:
        ledger.credit_scrip(agent_id, amount)

    return create_genesis_artifacts(
        ledger=ledger,
        mint_callback=mint_callback,
        artifact_store=artifact_store,
    )


class TestContractArtifactDiscovery:
    """Test that contracts are discoverable via genesis_store."""

    def test_contract_artifacts_created(
        self,
        artifact_store: ArtifactStore,
        genesis_artifacts: dict,
    ) -> None:
        """Genesis contract info artifacts are created."""
        # Contract artifacts should exist in artifact store
        assert artifact_store.exists("genesis_contract_freeware")
        assert artifact_store.exists("genesis_contract_private")
        assert artifact_store.exists("genesis_contract_self_owned")
        assert artifact_store.exists("genesis_contract_public")

    def test_contract_artifacts_have_correct_type(
        self,
        artifact_store: ArtifactStore,
        genesis_artifacts: dict,
    ) -> None:
        """Contract artifacts have type 'contract'."""
        freeware = artifact_store.get("genesis_contract_freeware")
        assert freeware is not None
        assert freeware.type == "contract"

    def test_contract_artifact_content_describes_rules(
        self,
        artifact_store: ArtifactStore,
        genesis_artifacts: dict,
    ) -> None:
        """Contract artifact content describes the permission rules."""
        freeware = artifact_store.get("genesis_contract_freeware")
        assert freeware is not None
        content = freeware.content

        # Should describe the rules
        assert "read" in content.lower()
        assert "write" in content.lower()
        assert "freeware" in content.lower()

    def test_contract_artifact_not_executable(
        self,
        artifact_store: ArtifactStore,
        genesis_artifacts: dict,
    ) -> None:
        """Contract artifacts are not executable (just info)."""
        freeware = artifact_store.get("genesis_contract_freeware")
        assert freeware is not None
        assert freeware.executable is False

    # Note: genesis_store tests removed in Plan #190
    # Contract discovery now uses query_kernel action


class TestContractPermissionCheckingUnchanged:
    """Test that permission checking still uses Python classes."""

    def test_get_contract_by_id_still_works(self) -> None:
        """get_contract_by_id returns the Python contract object."""
        contract = get_contract_by_id("genesis_contract_freeware")
        assert contract is not None
        assert hasattr(contract, "check_permission")

    def test_freeware_allows_read(self) -> None:
        """Freeware contract still allows read access."""
        from src.world.contracts import PermissionAction

        contract = get_contract_by_id("genesis_contract_freeware")
        assert contract is not None

        result = contract.check_permission(
            caller="anyone",
            action=PermissionAction.READ,
            target="some_artifact",
            context={"target_created_by": "owner"},
        )
        assert result.allowed is True

    def test_private_denies_non_owner(self) -> None:
        """Private contract still denies non-owner access."""
        from src.world.contracts import PermissionAction

        contract = get_contract_by_id("genesis_contract_private")
        assert contract is not None

        result = contract.check_permission(
            caller="not_owner",
            action=PermissionAction.READ,
            target="some_artifact",
            context={"target_created_by": "owner"},
        )
        assert result.allowed is False


class TestContractArtifactMetadata:
    """Test contract artifact metadata (Plan #168 integration)."""

    def test_contract_artifact_has_rules_metadata(
        self,
        artifact_store: ArtifactStore,
        genesis_artifacts: dict,
    ) -> None:
        """Contract artifacts have metadata describing rules."""
        freeware = artifact_store.get("genesis_contract_freeware")
        assert freeware is not None

        # Metadata should contain structured rule info
        assert "rules" in freeware.metadata
        rules = freeware.metadata["rules"]
        assert rules["read"] == "anyone"
        assert rules["invoke"] == "anyone"
        assert rules["write"] == "owner_only"

    # Note: test_filter_contracts_by_metadata removed in Plan #190
    # Contract filtering now uses query_kernel action with params
