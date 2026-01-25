"""Rights Management - Resource rights as tradeable artifacts (Plan #166 Phase 3).

Rights are artifacts that represent claims on physical capacity:
- dollar_budget: The right to spend API dollars
- rate_capacity: The right to make API calls within a time window
- disk_quota: The right to use storage bytes

Key concepts:
- Rights are artifacts (following "everything is an artifact")
- Rights are tradeable via escrow or direct transfer
- Rights can be split/merged
- Usage (what was consumed) is separate from rights (what you're allowed to use)

See docs/plans/166_resource_rights_model.md for full design.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import ArtifactStore


class RightType(str, Enum):
    """Types of resource rights.

    Each right type represents a different kind of claim on physical capacity.
    """

    DOLLAR_BUDGET = "dollar_budget"
    """Right to spend API dollars. Consumable - amount decreases on use."""

    RATE_CAPACITY = "rate_capacity"
    """Right to make API calls within a time window. Renewable per window."""

    DISK_QUOTA = "disk_quota"
    """Right to use storage bytes. Allocatable - can be reclaimed."""


@dataclass
class RightData:
    """Structured representation of a right artifact's content.

    This is the data stored in the artifact's content field (as JSON).
    """

    right_type: RightType
    """The type of right (dollar_budget, rate_capacity, disk_quota)."""

    resource: str
    """What this right applies to (e.g., 'llm_dollars', 'disk_bytes')."""

    amount: float
    """Current amount of the right. Meaning depends on right_type:
    - dollar_budget: dollars remaining
    - rate_capacity: calls allowed per window
    - disk_quota: bytes allocated
    """

    model: str | None = None
    """For rate_capacity: specific model this right applies to."""

    window: str | None = None
    """For rate_capacity: time window ('minute', 'hour'). Note: Per design
    decision, window is system-wide config, stored here for reference only."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "right_type": self.right_type.value,
            "resource": self.resource,
            "amount": self.amount,
        }
        if self.model is not None:
            result["model"] = self.model
        if self.window is not None:
            result["window"] = self.window
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RightData":
        """Create from dictionary (e.g., parsed JSON)."""
        return cls(
            right_type=RightType(data["right_type"]),
            resource=data["resource"],
            amount=float(data["amount"]),
            model=data.get("model"),
            window=data.get("window"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string for artifact content."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "RightData":
        """Parse from JSON string (artifact content)."""
        return cls.from_dict(json.loads(json_str))


def create_dollar_budget_right(
    artifact_store: "ArtifactStore",
    owner_id: str,
    amount: float,
    artifact_id: str | None = None,
) -> str:
    """Create a dollar budget right artifact.

    Args:
        artifact_store: The artifact store to write to
        owner_id: Who owns this right
        amount: Dollar amount this right grants
        artifact_id: Optional custom ID (default: genesis_right_dollar_budget_{owner})

    Returns:
        The artifact ID of the created right
    """
    if artifact_id is None:
        artifact_id = f"genesis_right_dollar_budget_{owner_id}"

    right_data = RightData(
        right_type=RightType.DOLLAR_BUDGET,
        resource="llm_dollars",
        amount=amount,
    )

    artifact_store.write(
        artifact_id=artifact_id,
        type="right",
        content=right_data.to_json(),
        created_by=owner_id,
        executable=False,
        metadata={
            "right_type": RightType.DOLLAR_BUDGET.value,
            "resource": "llm_dollars",
        },
    )

    return artifact_id


def create_rate_capacity_right(
    artifact_store: "ArtifactStore",
    owner_id: str,
    model: str,
    calls_per_window: int,
    window: str = "minute",
    artifact_id: str | None = None,
) -> str:
    """Create a rate capacity right artifact.

    Args:
        artifact_store: The artifact store to write to
        owner_id: Who owns this right
        model: The LLM model this right applies to
        calls_per_window: Number of calls allowed per time window
        window: Time window ('minute' or 'hour')
        artifact_id: Optional custom ID (default: genesis_right_rate_capacity_{owner}_{model})

    Returns:
        The artifact ID of the created right
    """
    if artifact_id is None:
        artifact_id = f"genesis_right_rate_capacity_{owner_id}_{model}"

    right_data = RightData(
        right_type=RightType.RATE_CAPACITY,
        resource="llm_calls",
        amount=float(calls_per_window),
        model=model,
        window=window,
    )

    artifact_store.write(
        artifact_id=artifact_id,
        type="right",
        content=right_data.to_json(),
        created_by=owner_id,
        executable=False,
        metadata={
            "right_type": RightType.RATE_CAPACITY.value,
            "resource": "llm_calls",
            "model": model,
        },
    )

    return artifact_id


def create_disk_quota_right(
    artifact_store: "ArtifactStore",
    owner_id: str,
    bytes_quota: int,
    artifact_id: str | None = None,
) -> str:
    """Create a disk quota right artifact.

    Args:
        artifact_store: The artifact store to write to
        owner_id: Who owns this right
        bytes_quota: Storage bytes this right grants
        artifact_id: Optional custom ID (default: genesis_right_disk_quota_{owner})

    Returns:
        The artifact ID of the created right
    """
    if artifact_id is None:
        artifact_id = f"genesis_right_disk_quota_{owner_id}"

    right_data = RightData(
        right_type=RightType.DISK_QUOTA,
        resource="disk_bytes",
        amount=float(bytes_quota),
    )

    artifact_store.write(
        artifact_id=artifact_id,
        type="right",
        content=right_data.to_json(),
        created_by=owner_id,
        executable=False,
        metadata={
            "right_type": RightType.DISK_QUOTA.value,
            "resource": "disk_bytes",
        },
    )

    return artifact_id


def get_right_data(artifact_store: "ArtifactStore", artifact_id: str) -> RightData | None:
    """Get the right data from a right artifact.

    Args:
        artifact_store: The artifact store to read from
        artifact_id: The right artifact ID

    Returns:
        RightData if artifact exists and is a valid right, None otherwise
    """
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        return None

    if artifact.type != "right":
        return None

    try:
        return RightData.from_json(artifact.content)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def update_right_amount(
    artifact_store: "ArtifactStore",
    artifact_id: str,
    new_amount: float,
) -> bool:
    """Update the amount of a right artifact.

    Used when consuming rights (e.g., spending dollar budget).

    Args:
        artifact_store: The artifact store
        artifact_id: The right artifact ID
        new_amount: The new amount value

    Returns:
        True if update succeeded, False otherwise
    """
    artifact = artifact_store.get(artifact_id)
    if artifact is None or artifact.type != "right":
        return False

    try:
        right_data = RightData.from_json(artifact.content)
        right_data.amount = new_amount
        artifact.content = right_data.to_json()
        artifact.updated_at = datetime.now(timezone.utc).isoformat()
        return True
    except (json.JSONDecodeError, KeyError, ValueError):
        return False


def find_rights_by_type(
    artifact_store: "ArtifactStore",
    owner_id: str,
    right_type: RightType,
    model: str | None = None,
) -> list[str]:
    """Find all rights of a given type owned by an agent.

    Args:
        artifact_store: The artifact store
        owner_id: The owner to search for
        right_type: The type of right to find
        model: For rate_capacity rights, filter by specific model

    Returns:
        List of artifact IDs matching the criteria
    """
    # Use the owner index for efficient lookup
    owner_artifacts = artifact_store.query_by_owner(owner_id)

    result = []
    for artifact in owner_artifacts:
        if artifact.type != "right" or artifact.deleted:
            continue

        # Check metadata for quick filtering
        if artifact.metadata.get("right_type") != right_type.value:
            continue

        # For rate_capacity, optionally filter by model
        if right_type == RightType.RATE_CAPACITY and model is not None:
            if artifact.metadata.get("model") != model:
                continue

        result.append(artifact.id)

    return result


def get_total_right_amount(
    artifact_store: "ArtifactStore",
    owner_id: str,
    right_type: RightType,
    model: str | None = None,
) -> float:
    """Get the total amount of a right type owned by an agent.

    Sums the amounts of all matching rights (useful when rights are split).

    Args:
        artifact_store: The artifact store
        owner_id: The owner to search for
        right_type: The type of right to sum
        model: For rate_capacity rights, filter by specific model

    Returns:
        Total amount across all matching rights
    """
    right_ids = find_rights_by_type(artifact_store, owner_id, right_type, model)

    total = 0.0
    for right_id in right_ids:
        right_data = get_right_data(artifact_store, right_id)
        if right_data is not None:
            total += right_data.amount

    return total


# Constants for standard genesis right naming
GENESIS_RIGHT_PREFIX = "genesis_right_"
DOLLAR_BUDGET_PREFIX = f"{GENESIS_RIGHT_PREFIX}dollar_budget_"
RATE_CAPACITY_PREFIX = f"{GENESIS_RIGHT_PREFIX}rate_capacity_"
DISK_QUOTA_PREFIX = f"{GENESIS_RIGHT_PREFIX}disk_quota_"


__all__ = [
    # Enums
    "RightType",
    # Data classes
    "RightData",
    # Creation functions
    "create_dollar_budget_right",
    "create_rate_capacity_right",
    "create_disk_quota_right",
    # Query functions
    "get_right_data",
    "update_right_amount",
    "find_rights_by_type",
    "get_total_right_amount",
    # Constants
    "GENESIS_RIGHT_PREFIX",
    "DOLLAR_BUDGET_PREFIX",
    "RATE_CAPACITY_PREFIX",
    "DISK_QUOTA_PREFIX",
]
