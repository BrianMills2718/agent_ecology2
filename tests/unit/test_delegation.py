"""Tests for charge delegation (Plan #236).

Tests delegation grant/revoke, authorization, rate window enforcement,
payer resolution, and security invariants.
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from src.world.artifacts import ArtifactStore, Artifact
from src.world.delegation import (
    ChargeRecord,
    DelegationEntry,
    DelegationManager,
)
from src.world.ledger import Ledger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ledger() -> Ledger:
    """Ledger with two principals."""
    led = Ledger()
    led.create_principal("alice", starting_scrip=1000)
    led.create_principal("bob", starting_scrip=500)
    return led


@pytest.fixture
def store() -> ArtifactStore:
    """Fresh artifact store."""
    return ArtifactStore()


@pytest.fixture
def dm(store: ArtifactStore, ledger: Ledger) -> DelegationManager:
    """DelegationManager wired to store and ledger."""
    return DelegationManager(store, ledger)


# ---------------------------------------------------------------------------
# Grant / Revoke
# ---------------------------------------------------------------------------


@pytest.mark.plans(236)
class TestDelegationGrant:
    """Tests for grant_charge_delegation."""

    def test_grant_delegation_creates_artifact(
        self, dm: DelegationManager, store: ArtifactStore
    ) -> None:
        """Granting a delegation creates a charge_delegation:{caller} artifact."""
        result = dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=10.0,
            max_per_window=100.0,
            window_seconds=3600,
        )
        assert result is True

        artifact = store.get("charge_delegation:alice")
        assert artifact is not None
        assert artifact.type == "charge_delegation"
        assert artifact.created_by == "alice"
        assert artifact.kernel_protected is True

        content = json.loads(artifact.content)
        assert len(content["delegations"]) == 1
        assert content["delegations"][0]["charger_id"] == "bob"
        assert content["delegations"][0]["max_per_call"] == 10.0

    def test_grant_delegation_only_self(
        self, dm: DelegationManager, store: ArtifactStore
    ) -> None:
        """ArtifactStore rejects creating charge_delegation:X by non-X caller.

        The reserved namespace enforcement (Plan #235) blocks this at
        the store level. DelegationManager.grant passes caller_id as
        created_by, so the store enforces the constraint.
        """
        # DelegationManager.grant uses caller_id as created_by for the artifact.
        # If someone could call grant(caller_id="alice", ...) with a different
        # identity, the ArtifactStore would block it. Test the store constraint:
        with pytest.raises(PermissionError, match="charge_delegation"):
            store.write(
                "charge_delegation:alice",
                "charge_delegation",
                "{}",
                "attacker",  # Not alice
            )

    def test_grant_updates_existing(
        self, dm: DelegationManager, store: ArtifactStore
    ) -> None:
        """Second grant to a different charger adds to the list."""
        dm.grant(caller_id="alice", charger_id="bob", max_per_call=10.0)
        dm.grant(caller_id="alice", charger_id="charlie", max_per_call=20.0)

        # Need charlie as a principal for this to work
        artifact = store.get("charge_delegation:alice")
        assert artifact is not None
        content = json.loads(artifact.content)
        assert len(content["delegations"]) == 2
        charger_ids = {d["charger_id"] for d in content["delegations"]}
        assert charger_ids == {"bob", "charlie"}


@pytest.mark.plans(236)
class TestDelegationRevoke:
    """Tests for revoke_charge_delegation."""

    def test_revoke_delegation(self, dm: DelegationManager) -> None:
        """Revoking removes the delegation; subsequent authorize fails."""
        dm.grant(caller_id="alice", charger_id="bob", max_per_call=10.0)

        result = dm.revoke(caller_id="alice", charger_id="bob")
        assert result is True

        authorized, reason = dm.authorize_charge(
            charger_id="bob", payer_id="alice", amount=5.0
        )
        assert authorized is False
        assert "no delegation" in reason.lower()

    def test_revoke_nonexistent_returns_false(self, dm: DelegationManager) -> None:
        """Revoking a delegation that doesn't exist returns False."""
        result = dm.revoke(caller_id="alice", charger_id="bob")
        assert result is False


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


@pytest.mark.plans(236)
class TestAuthorizeCharge:
    """Tests for authorize_charge."""

    def test_authorize_charge_valid(self, dm: DelegationManager) -> None:
        """Authorization succeeds with valid delegation and within caps."""
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=50.0,
            max_per_window=200.0,
            window_seconds=3600,
        )

        authorized, reason = dm.authorize_charge(
            charger_id="bob", payer_id="alice", amount=30.0
        )
        assert authorized is True

    def test_authorize_charge_no_delegation(self, dm: DelegationManager) -> None:
        """Authorization fails without any delegation."""
        authorized, reason = dm.authorize_charge(
            charger_id="bob", payer_id="alice", amount=5.0
        )
        assert authorized is False
        assert "no delegation" in reason.lower()

    def test_authorize_charge_exceeds_per_call_cap(
        self, dm: DelegationManager
    ) -> None:
        """Authorization fails when amount exceeds max_per_call."""
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=10.0,
        )

        authorized, reason = dm.authorize_charge(
            charger_id="bob", payer_id="alice", amount=15.0
        )
        assert authorized is False
        assert "per_call" in reason.lower() or "per-call" in reason.lower()

    def test_authorize_charge_expired(self, dm: DelegationManager) -> None:
        """Authorization fails when delegation has expired."""
        # Use an expiry time in the past
        past = "2020-01-01T00:00:00+00:00"
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=50.0,
            expires_at=past,
        )

        authorized, reason = dm.authorize_charge(
            charger_id="bob", payer_id="alice", amount=5.0
        )
        assert authorized is False
        assert "expired" in reason.lower()


# ---------------------------------------------------------------------------
# Rate Window Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.plans(236)
class TestRateWindow:
    """Tests for per-window cap enforcement."""

    def test_rate_window_enforcement(self, dm: DelegationManager) -> None:
        """Per-window cap is enforced across multiple charges."""
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=60.0,
            max_per_window=100.0,
            window_seconds=3600,
        )

        # First charge: 60 of 100 used
        ok1, _ = dm.authorize_charge("bob", "alice", 60.0)
        assert ok1 is True
        dm.record_charge("alice", "bob", 60.0)

        # Second charge: 60 more would exceed 100 cap
        ok2, reason = dm.authorize_charge("bob", "alice", 60.0)
        assert ok2 is False
        assert "window" in reason.lower()

        # But 40 is still within cap
        ok3, _ = dm.authorize_charge("bob", "alice", 40.0)
        assert ok3 is True

    def test_concurrent_charges_respect_caps(
        self, dm: DelegationManager
    ) -> None:
        """Sequential invariant: cumulative charges never exceed window cap.

        Note: The execution model is single-threaded so true concurrency
        cannot occur. This test verifies the logical invariant that the
        authorize+record pattern correctly tracks cumulative usage.
        """
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_call=30.0,
            max_per_window=100.0,
            window_seconds=3600,
        )

        total_charged = 0.0
        for _ in range(10):
            ok, _ = dm.authorize_charge("bob", "alice", 30.0)
            if ok:
                dm.record_charge("alice", "bob", 30.0)
                total_charged += 30.0
            else:
                break

        # Should have allowed 3 charges (90) and denied the 4th (120 > 100)
        assert total_charged == 90.0

    def test_window_accounting_bounded_memory(
        self, dm: DelegationManager
    ) -> None:
        """Charge history is pruned and does not grow unboundedly."""
        dm.grant(
            caller_id="alice",
            charger_id="bob",
            max_per_window=1_000_000.0,
            window_seconds=1,  # Very short window
        )

        # Record many charges
        for _ in range(1500):
            dm.record_charge("alice", "bob", 1.0)

        key = ("alice", "bob")
        history = dm._charge_history.get(key)
        assert history is not None
        # Hard cap is 1000 entries per pair
        assert len(history) <= 1000


# ---------------------------------------------------------------------------
# Payer Resolution
# ---------------------------------------------------------------------------


@pytest.mark.plans(236)
class TestPayerResolution:
    """Tests for resolve_payer static method."""

    def _make_artifact(self, created_by: str, **metadata: Any) -> Artifact:
        """Helper to create a minimal Artifact for testing."""
        store = ArtifactStore()
        art = store.write("test-art", "executable", "code", created_by)
        for k, v in metadata.items():
            art.metadata[k] = v
        return art

    def test_payer_resolution_ignores_forgeable_metadata(self) -> None:
        """resolve_payer uses created_by for 'target', never metadata fields.

        FM-2: A malicious artifact could set metadata["authorized_writer"]
        to a rich victim. resolve_payer must ignore all mutable metadata.
        """
        artifact = self._make_artifact(
            created_by="real_owner",
            authorized_writer="rich_victim",
        )

        payer = DelegationManager.resolve_payer(
            charge_to="target",
            caller_id="invoker",
            artifact=artifact,
        )
        assert payer == "real_owner"
        assert payer != "rich_victim"

    def test_payer_resolution_caller(self) -> None:
        """charge_to='caller' returns the caller_id."""
        artifact = self._make_artifact(created_by="owner")
        payer = DelegationManager.resolve_payer("caller", "invoker", artifact)
        assert payer == "invoker"

    def test_payer_resolution_pool(self) -> None:
        """charge_to='pool:treasury' returns 'treasury'."""
        artifact = self._make_artifact(created_by="owner")
        payer = DelegationManager.resolve_payer(
            "pool:treasury", "invoker", artifact
        )
        assert payer == "treasury"

    def test_payer_must_be_principal_not_artifact(self) -> None:
        """resolve_payer always returns a principal ID, not an artifact ID.

        FM-3: Artifacts cannot be payers. charge_to='target' resolves to
        artifact.created_by (the principal), not the artifact_id.
        """
        artifact = self._make_artifact(created_by="alice")
        payer = DelegationManager.resolve_payer(
            "target", "invoker", artifact
        )
        # The result must be a principal (created_by), not the artifact
        assert payer == "alice"
        assert payer != artifact.id

    def test_payer_resolution_unknown_raises(self) -> None:
        """Unknown charge_to value raises ValueError."""
        artifact = self._make_artifact(created_by="owner")
        with pytest.raises(ValueError, match="Unknown charge_to"):
            DelegationManager.resolve_payer("invalid", "invoker", artifact)
