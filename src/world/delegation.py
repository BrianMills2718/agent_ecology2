"""Charge delegation management — Plan #236.

Enables principals to delegate charging authority to other principals.
Delegation records are stored as kernel_protected artifacts with
deterministic IDs: ``charge_delegation:{payer_id}``.

Key invariants:
- Only the payer themselves can grant/revoke delegations
- Payer resolution uses metadata (authorized_principal/authorized_writer)
  per ADR-0028; delegation authorization prevents unauthorized charges (FM-2)
- Rate window tracking is ephemeral (same as RateTracker — no checkpoint)
- Settlement atomicity relies on single-threaded execution; see FM-1 note
  in action_executor.py
"""

from __future__ import annotations

import logging
import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from src.config import get as config_get
from src.world.constants import KERNEL_CONTRACT_PRIVATE

if TYPE_CHECKING:
    from src.world.artifacts import Artifact, ArtifactStore
    from src.world.ledger import Ledger
    from src.world.logger import EventLogger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DelegationEntry:
    """A single delegation grant from a payer to a charger."""

    charger_id: str
    max_per_call: float | None = None  # None = unlimited
    max_per_window: float | None = None  # None = unlimited
    window_seconds: int = 3600
    expires_at: str | None = None  # ISO 8601 timestamp or None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for artifact content."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DelegationEntry:
        """Deserialize from artifact content."""
        return cls(
            charger_id=data["charger_id"],
            max_per_call=data.get("max_per_call"),
            max_per_window=data.get("max_per_window"),
            window_seconds=data.get("window_seconds", 3600),
            expires_at=data.get("expires_at"),
        )


@dataclass
class ChargeRecord:
    """A single charge event for rate window tracking."""

    timestamp: float
    amount: float


# ---------------------------------------------------------------------------
# DelegationManager
# ---------------------------------------------------------------------------

# Default hard cap on charge history entries per (payer, charger) pair (FM-5)
_DEFAULT_MAX_ENTRIES_PER_PAIR: int = 1000


class DelegationManager:
    """Manages delegation artifacts and charge authorization.

    This is a service class used by kernel primitives (KernelActions).
    It is NOT exposed directly to artifacts.

    Rate window state (``_charge_history``) is ephemeral — same pattern
    as ``RateTracker``. Windows reset on simulation restart, which is safe
    because rate limits are per-window, not cumulative.
    """

    def __init__(self, artifacts: "ArtifactStore", ledger: "Ledger") -> None:
        self._artifacts = artifacts
        self._ledger = ledger
        # In-memory rate window: (payer_id, charger_id) -> deque[ChargeRecord]
        self._charge_history: dict[tuple[str, str], deque[ChargeRecord]] = {}
        # TD-012: Read max entries from config, fall back to default
        max_entries = config_get("delegation.max_history")
        self._max_entries_per_pair: int = (
            int(max_entries) if max_entries is not None
            else _DEFAULT_MAX_ENTRIES_PER_PAIR
        )
        # TD-011: Optional event logger for observability
        self._event_logger: "EventLogger | None" = None

    def set_logger(self, event_logger: "EventLogger") -> None:
        """Set the event logger for delegation event logging (TD-011)."""
        self._event_logger = event_logger

    # ------------------------------------------------------------------
    # Delegation CRUD
    # ------------------------------------------------------------------

    def grant(
        self,
        caller_id: str,
        charger_id: str,
        max_per_call: float | None = None,
        max_per_window: float | None = None,
        window_seconds: int = 3600,
        expires_at: str | None = None,
    ) -> bool:
        """Grant permission for *charger_id* to charge *caller_id*'s account.

        Creates or updates the ``charge_delegation:{caller_id}`` artifact.
        The artifact is ``kernel_protected`` so only this manager (via
        ``modify_protected_content``) can update it after creation.

        Args:
            caller_id: The payer granting the delegation (must be the payer).
            charger_id: The principal being authorized to charge.
            max_per_call: Maximum amount per single charge (None = unlimited).
            max_per_window: Maximum cumulative amount per window (None = unlimited).
            window_seconds: Rolling window duration in seconds.
            expires_at: ISO 8601 expiry timestamp (None = no expiry).

        Returns:
            True on success.
        """
        entry = DelegationEntry(
            charger_id=charger_id,
            max_per_call=max_per_call,
            max_per_window=max_per_window,
            window_seconds=window_seconds,
            expires_at=expires_at,
        )

        artifact_id = f"charge_delegation:{caller_id}"
        existing = self._artifacts.get(artifact_id)

        if existing is None:
            # Create new delegation artifact.
            # ArtifactStore.write() enforces reserved namespace: only caller_id
            # can create charge_delegation:{caller_id} (Plan #235 FM-4).
            content = json.dumps({"delegations": [entry.to_dict()]})
            artifact = self._artifacts.write(
                artifact_id,
                "charge_delegation",
                content,
                caller_id,
                access_contract_id=KERNEL_CONTRACT_PRIVATE,
            )
            artifact.kernel_protected = True
            self._log_event("delegation_granted", {
                "payer": caller_id, "charger": charger_id,
                "max_per_call": max_per_call, "max_per_window": max_per_window,
                "window_seconds": window_seconds, "created": True,
            })
            return True

        # Update existing: load, upsert entry, save via modify_protected_content
        delegations = self._load_delegations_from_artifact(existing)

        # Replace existing entry for this charger, or append
        updated = False
        for i, d in enumerate(delegations):
            if d.charger_id == charger_id:
                delegations[i] = entry
                updated = True
                break
        if not updated:
            delegations.append(entry)

        new_content = json.dumps(
            {"delegations": [d.to_dict() for d in delegations]}
        )
        self._artifacts.modify_protected_content(artifact_id, content=new_content)
        self._log_event("delegation_granted", {
            "payer": caller_id, "charger": charger_id,
            "max_per_call": max_per_call, "max_per_window": max_per_window,
            "window_seconds": window_seconds, "updated": not updated,
        })
        return True

    def revoke(self, caller_id: str, charger_id: str) -> bool:
        """Revoke a previously granted charge delegation.

        Args:
            caller_id: The payer revoking the delegation.
            charger_id: The charger whose delegation is being revoked.

        Returns:
            True if a delegation was found and removed, False otherwise.
        """
        artifact_id = f"charge_delegation:{caller_id}"
        existing = self._artifacts.get(artifact_id)
        if existing is None:
            return False

        delegations = self._load_delegations_from_artifact(existing)
        original_len = len(delegations)
        delegations = [d for d in delegations if d.charger_id != charger_id]

        if len(delegations) == original_len:
            return False  # Nothing was removed

        new_content = json.dumps(
            {"delegations": [d.to_dict() for d in delegations]}
        )
        self._artifacts.modify_protected_content(artifact_id, content=new_content)
        self._log_event("delegation_revoked", {
            "payer": caller_id, "charger": charger_id,
        })
        return True

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def authorize_charge(
        self,
        charger_id: str,
        payer_id: str,
        amount: float,
    ) -> tuple[bool, str]:
        """Check if *charger_id* is authorized to charge *payer_id*.

        Steps:
        1. Load ``charge_delegation:{payer_id}`` artifact
        2. Find entry for *charger_id*
        3. Check expiry
        4. Check per-call cap
        5. Check per-window cap against charge history

        Args:
            charger_id: Who wants to charge.
            payer_id: Whose account would be charged.
            amount: The charge amount.

        Returns:
            ``(True, "ok")`` if authorized, ``(False, reason)`` otherwise.
        """
        artifact_id = f"charge_delegation:{payer_id}"
        existing = self._artifacts.get(artifact_id)
        if existing is None:
            return False, f"No delegation artifact for payer '{payer_id}'"

        delegations = self._load_delegations_from_artifact(existing)
        entry: DelegationEntry | None = None
        for d in delegations:
            if d.charger_id == charger_id:
                entry = d
                break

        if entry is None:
            return False, f"No delegation from '{payer_id}' to '{charger_id}'"

        # Check expiry
        if entry.expires_at is not None:
            try:
                expires = datetime.fromisoformat(entry.expires_at)
                if datetime.now(timezone.utc) >= expires:
                    return False, f"Delegation expired at {entry.expires_at}"
            except ValueError:
                return False, f"Invalid expires_at format: {entry.expires_at}"

        # Check per-call cap
        if entry.max_per_call is not None and amount > entry.max_per_call:
            return (
                False,
                f"Amount {amount} exceeds per_call cap {entry.max_per_call}",
            )

        # Check per-window cap
        if entry.max_per_window is not None:
            window_usage = self._get_window_usage(
                payer_id, charger_id, entry.window_seconds
            )
            if window_usage + amount > entry.max_per_window:
                return (
                    False,
                    f"Amount {amount} would exceed window cap "
                    f"{entry.max_per_window} (used: {window_usage})",
                )

        return True, "ok"

    # ------------------------------------------------------------------
    # Charge recording
    # ------------------------------------------------------------------

    def record_charge(
        self, payer_id: str, charger_id: str, amount: float
    ) -> None:
        """Record a completed charge for rate window tracking.

        Also prunes old entries beyond the delegation's window and enforces
        the hard cap of ``_MAX_ENTRIES_PER_PAIR`` (FM-5).
        """
        key = (payer_id, charger_id)
        now = time.time()

        if key not in self._charge_history:
            self._charge_history[key] = deque()

        self._charge_history[key].append(ChargeRecord(timestamp=now, amount=amount))

        # Prune: find max window for this pair from delegation
        max_window = self._get_max_window_seconds(payer_id, charger_id)
        self._prune_history(key, max_window)

    # ------------------------------------------------------------------
    # Payer resolution
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_payer(
        charge_to: str,
        caller_id: str,
        artifact: "Artifact",
    ) -> str:
        """Resolve who should pay based on the ``charge_to`` directive.

        ADR-0028: Uses metadata (authorized_principal/authorized_writer)
        to determine the contract-recognized owner. Delegation authorization
        (authorize_charge) prevents unauthorized charges.

        Args:
            charge_to: One of "caller", "target", "contract",
                       or "pool:{principal_id}".
            caller_id: The invoker's principal ID.
            artifact: The artifact being invoked.

        Returns:
            A principal ID (never an artifact ID).

        Raises:
            ValueError: If *charge_to* is not recognized.
        """
        if charge_to == "caller":
            return caller_id

        if charge_to == "target":
            # ADR-0028: Resolve via metadata, not created_by
            metadata = artifact.metadata or {}
            return (
                metadata.get("authorized_principal")
                or metadata.get("authorized_writer")
                or artifact.created_by  # Final fallback for untagged artifacts
            )

        if charge_to == "contract":
            # Resolve to the authorized principal of the artifact.
            # ADR-0028: Use metadata, not created_by.
            metadata = artifact.metadata or {}
            return (
                metadata.get("authorized_principal")
                or metadata.get("authorized_writer")
                or artifact.created_by  # Final fallback for untagged artifacts
            )

        if charge_to.startswith("pool:"):
            # Explicit payer ID after the "pool:" prefix
            payer_id = charge_to.split(":", 1)[1]
            if not payer_id:
                raise ValueError(f"Empty pool ID in charge_to: '{charge_to}'")
            return payer_id

        raise ValueError(f"Unknown charge_to: '{charge_to}'")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_delegations_from_artifact(
        self, artifact: "Artifact"
    ) -> list[DelegationEntry]:
        """Parse delegation entries from an artifact's JSON content."""
        try:
            data = json.loads(artifact.content)
            return [
                DelegationEntry.from_dict(d)
                for d in data.get("delegations", [])
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _get_window_usage(
        self, payer_id: str, charger_id: str, window_seconds: int
    ) -> float:
        """Sum charges within the rolling window."""
        key = (payer_id, charger_id)
        history = self._charge_history.get(key)
        if not history:
            return 0.0

        cutoff = time.time() - window_seconds
        return sum(r.amount for r in history if r.timestamp >= cutoff)

    def _get_max_window_seconds(self, payer_id: str, charger_id: str) -> float:
        """Get the window_seconds for a (payer, charger) delegation."""
        artifact_id = f"charge_delegation:{payer_id}"
        existing = self._artifacts.get(artifact_id)
        if existing is None:
            return 3600.0  # Default

        delegations = self._load_delegations_from_artifact(existing)
        for d in delegations:
            if d.charger_id == charger_id:
                return float(d.window_seconds)
        return 3600.0

    def _prune_history(self, key: tuple[str, str], max_age: float) -> None:
        """Prune old entries and enforce hard cap (FM-5)."""
        history = self._charge_history.get(key)
        if history is None:
            return

        cutoff = time.time() - max_age

        # Remove entries older than window
        while history and history[0].timestamp < cutoff:
            history.popleft()

        # Hard cap: keep only the most recent entries
        while len(history) > self._max_entries_per_pair:
            history.popleft()

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log a delegation event if logger is available."""
        if self._event_logger is not None:
            self._event_logger.log(event_type, data)
