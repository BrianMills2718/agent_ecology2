"""Tests for rights module (Plan #166 Phase 3).

Tests the rights-as-artifacts model for resource management.
"""

import json
import pytest

from src.world.artifacts import ArtifactStore
from src.world.rights import (
    RightType,
    RightData,
    create_dollar_budget_right,
    create_rate_capacity_right,
    create_disk_quota_right,
    get_right_data,
    update_right_amount,
    find_rights_by_type,
    get_total_right_amount,
    DOLLAR_BUDGET_PREFIX,
    RATE_CAPACITY_PREFIX,
    DISK_QUOTA_PREFIX,
)


class TestRightType:
    """Tests for RightType enum."""

    def test_right_types_are_strings(self) -> None:
        """RightType values are strings for JSON serialization."""
        assert RightType.DOLLAR_BUDGET.value == "dollar_budget"
        assert RightType.RATE_CAPACITY.value == "rate_capacity"
        assert RightType.DISK_QUOTA.value == "disk_quota"

    def test_right_type_from_string(self) -> None:
        """Can create RightType from string value."""
        assert RightType("dollar_budget") == RightType.DOLLAR_BUDGET
        assert RightType("rate_capacity") == RightType.RATE_CAPACITY
        assert RightType("disk_quota") == RightType.DISK_QUOTA


class TestRightData:
    """Tests for RightData dataclass."""

    def test_to_dict_minimal(self) -> None:
        """to_dict includes required fields."""
        data = RightData(
            right_type=RightType.DOLLAR_BUDGET,
            resource="llm_dollars",
            amount=0.50,
        )
        result = data.to_dict()

        assert result == {
            "right_type": "dollar_budget",
            "resource": "llm_dollars",
            "amount": 0.50,
        }

    def test_to_dict_with_optional_fields(self) -> None:
        """to_dict includes optional fields when set."""
        data = RightData(
            right_type=RightType.RATE_CAPACITY,
            resource="llm_calls",
            amount=100.0,
            model="gemini",
            window="minute",
        )
        result = data.to_dict()

        assert result == {
            "right_type": "rate_capacity",
            "resource": "llm_calls",
            "amount": 100.0,
            "model": "gemini",
            "window": "minute",
        }

    def test_from_dict_minimal(self) -> None:
        """from_dict parses required fields."""
        data = {
            "right_type": "dollar_budget",
            "resource": "llm_dollars",
            "amount": 0.50,
        }
        result = RightData.from_dict(data)

        assert result.right_type == RightType.DOLLAR_BUDGET
        assert result.resource == "llm_dollars"
        assert result.amount == 0.50
        assert result.model is None
        assert result.window is None

    def test_from_dict_with_optional_fields(self) -> None:
        """from_dict parses optional fields."""
        data = {
            "right_type": "rate_capacity",
            "resource": "llm_calls",
            "amount": 100,
            "model": "gemini",
            "window": "minute",
        }
        result = RightData.from_dict(data)

        assert result.right_type == RightType.RATE_CAPACITY
        assert result.model == "gemini"
        assert result.window == "minute"

    def test_to_json_roundtrip(self) -> None:
        """JSON serialization roundtrips correctly."""
        original = RightData(
            right_type=RightType.DISK_QUOTA,
            resource="disk_bytes",
            amount=10000.0,
        )

        json_str = original.to_json()
        restored = RightData.from_json(json_str)

        assert restored.right_type == original.right_type
        assert restored.resource == original.resource
        assert restored.amount == original.amount

    def test_amount_converts_to_float(self) -> None:
        """Amount is converted to float."""
        data = {"right_type": "dollar_budget", "resource": "llm_dollars", "amount": 1}
        result = RightData.from_dict(data)
        assert isinstance(result.amount, float)
        assert result.amount == 1.0


class TestCreateDollarBudgetRight:
    """Tests for create_dollar_budget_right function."""

    def test_creates_artifact(self) -> None:
        """Creates a right artifact in the store."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        artifact = store.get(artifact_id)
        assert artifact is not None
        assert artifact.type == "right"
        assert artifact.created_by == "agent_1"

    def test_default_id_format(self) -> None:
        """Uses standard ID format when not specified."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        assert artifact_id == f"{DOLLAR_BUDGET_PREFIX}agent_1"

    def test_custom_id(self) -> None:
        """Uses custom ID when specified."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(
            store, "agent_1", 0.50, artifact_id="my_custom_right"
        )

        assert artifact_id == "my_custom_right"

    def test_content_is_valid_json(self) -> None:
        """Content is valid JSON with right data."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        artifact = store.get(artifact_id)
        assert artifact is not None
        content = json.loads(artifact.content)

        assert content["right_type"] == "dollar_budget"
        assert content["resource"] == "llm_dollars"
        assert content["amount"] == 0.50

    def test_metadata_set(self) -> None:
        """Metadata includes right_type and resource for indexing."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        artifact = store.get(artifact_id)
        assert artifact is not None
        assert artifact.metadata["right_type"] == "dollar_budget"
        assert artifact.metadata["resource"] == "llm_dollars"


class TestCreateRateCapacityRight:
    """Tests for create_rate_capacity_right function."""

    def test_creates_artifact(self) -> None:
        """Creates a right artifact in the store."""
        store = ArtifactStore()
        artifact_id = create_rate_capacity_right(store, "agent_1", "gemini", 100)

        artifact = store.get(artifact_id)
        assert artifact is not None
        assert artifact.type == "right"

    def test_default_id_format(self) -> None:
        """Uses standard ID format when not specified."""
        store = ArtifactStore()
        artifact_id = create_rate_capacity_right(store, "agent_1", "gemini", 100)

        assert artifact_id == f"{RATE_CAPACITY_PREFIX}agent_1_gemini"

    def test_content_includes_model(self) -> None:
        """Content includes model field."""
        store = ArtifactStore()
        artifact_id = create_rate_capacity_right(store, "agent_1", "claude", 50)

        artifact = store.get(artifact_id)
        assert artifact is not None
        content = json.loads(artifact.content)

        assert content["model"] == "claude"
        assert content["amount"] == 50.0

    def test_metadata_includes_model(self) -> None:
        """Metadata includes model for filtering."""
        store = ArtifactStore()
        artifact_id = create_rate_capacity_right(store, "agent_1", "gemini", 100)

        artifact = store.get(artifact_id)
        assert artifact is not None
        assert artifact.metadata["model"] == "gemini"


class TestCreateDiskQuotaRight:
    """Tests for create_disk_quota_right function."""

    def test_creates_artifact(self) -> None:
        """Creates a right artifact in the store."""
        store = ArtifactStore()
        artifact_id = create_disk_quota_right(store, "agent_1", 10000)

        artifact = store.get(artifact_id)
        assert artifact is not None
        assert artifact.type == "right"

    def test_default_id_format(self) -> None:
        """Uses standard ID format when not specified."""
        store = ArtifactStore()
        artifact_id = create_disk_quota_right(store, "agent_1", 10000)

        assert artifact_id == f"{DISK_QUOTA_PREFIX}agent_1"

    def test_content_correct(self) -> None:
        """Content has correct structure."""
        store = ArtifactStore()
        artifact_id = create_disk_quota_right(store, "agent_1", 10000)

        artifact = store.get(artifact_id)
        assert artifact is not None
        content = json.loads(artifact.content)

        assert content["right_type"] == "disk_quota"
        assert content["resource"] == "disk_bytes"
        assert content["amount"] == 10000.0


class TestGetRightData:
    """Tests for get_right_data function."""

    def test_returns_right_data(self) -> None:
        """Returns RightData for valid right artifact."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        result = get_right_data(store, artifact_id)

        assert result is not None
        assert result.right_type == RightType.DOLLAR_BUDGET
        assert result.amount == 0.50

    def test_returns_none_for_missing(self) -> None:
        """Returns None for non-existent artifact."""
        store = ArtifactStore()
        result = get_right_data(store, "nonexistent")
        assert result is None

    def test_returns_none_for_non_right(self) -> None:
        """Returns None for artifact that is not a right."""
        store = ArtifactStore()
        store.write(
            artifact_id="not_a_right",
            type="generic",
            content="some content",
            created_by="agent_1",
        )

        result = get_right_data(store, "not_a_right")
        assert result is None

    def test_returns_none_for_invalid_content(self) -> None:
        """Returns None for right artifact with invalid JSON content."""
        store = ArtifactStore()
        store.write(
            artifact_id="bad_right",
            type="right",
            content="not valid json",
            created_by="agent_1",
        )

        result = get_right_data(store, "bad_right")
        assert result is None


class TestUpdateRightAmount:
    """Tests for update_right_amount function."""

    def test_updates_amount(self) -> None:
        """Updates the amount in the right artifact."""
        store = ArtifactStore()
        artifact_id = create_dollar_budget_right(store, "agent_1", 0.50)

        result = update_right_amount(store, artifact_id, 0.25)

        assert result is True
        right_data = get_right_data(store, artifact_id)
        assert right_data is not None
        assert right_data.amount == 0.25

    def test_returns_false_for_missing(self) -> None:
        """Returns False for non-existent artifact."""
        store = ArtifactStore()
        result = update_right_amount(store, "nonexistent", 0.25)
        assert result is False

    def test_returns_false_for_non_right(self) -> None:
        """Returns False for non-right artifact."""
        store = ArtifactStore()
        store.write(
            artifact_id="not_a_right",
            type="generic",
            content="some content",
            created_by="agent_1",
        )

        result = update_right_amount(store, "not_a_right", 0.25)
        assert result is False

    def test_preserves_other_fields(self) -> None:
        """Preserves other right fields when updating amount."""
        store = ArtifactStore()
        artifact_id = create_rate_capacity_right(store, "agent_1", "gemini", 100)

        update_right_amount(store, artifact_id, 50)

        right_data = get_right_data(store, artifact_id)
        assert right_data is not None
        assert right_data.amount == 50
        assert right_data.model == "gemini"
        assert right_data.right_type == RightType.RATE_CAPACITY


class TestFindRightsByType:
    """Tests for find_rights_by_type function."""

    def test_finds_rights_by_owner_and_type(self) -> None:
        """Finds all rights of given type owned by agent."""
        store = ArtifactStore()
        create_dollar_budget_right(store, "agent_1", 0.50)
        create_dollar_budget_right(store, "agent_1", 0.25, artifact_id="extra_budget")
        create_disk_quota_right(store, "agent_1", 10000)

        result = find_rights_by_type(store, "agent_1", RightType.DOLLAR_BUDGET)

        assert len(result) == 2
        assert "genesis_right_dollar_budget_agent_1" in result
        assert "extra_budget" in result

    def test_excludes_other_owners(self) -> None:
        """Does not include rights owned by other agents."""
        store = ArtifactStore()
        create_dollar_budget_right(store, "agent_1", 0.50)
        create_dollar_budget_right(store, "agent_2", 0.30)

        result = find_rights_by_type(store, "agent_1", RightType.DOLLAR_BUDGET)

        assert len(result) == 1
        assert "genesis_right_dollar_budget_agent_1" in result

    def test_filters_rate_capacity_by_model(self) -> None:
        """Filters rate_capacity rights by model when specified."""
        store = ArtifactStore()
        create_rate_capacity_right(store, "agent_1", "gemini", 100)
        create_rate_capacity_right(store, "agent_1", "claude", 50)

        gemini_rights = find_rights_by_type(
            store, "agent_1", RightType.RATE_CAPACITY, model="gemini"
        )
        claude_rights = find_rights_by_type(
            store, "agent_1", RightType.RATE_CAPACITY, model="claude"
        )
        all_rights = find_rights_by_type(store, "agent_1", RightType.RATE_CAPACITY)

        assert len(gemini_rights) == 1
        assert len(claude_rights) == 1
        assert len(all_rights) == 2

    def test_returns_empty_for_no_matches(self) -> None:
        """Returns empty list when no matching rights."""
        store = ArtifactStore()
        create_dollar_budget_right(store, "agent_1", 0.50)

        result = find_rights_by_type(store, "agent_1", RightType.DISK_QUOTA)

        assert result == []


class TestGetTotalRightAmount:
    """Tests for get_total_right_amount function."""

    def test_sums_multiple_rights(self) -> None:
        """Sums amounts across multiple rights of same type."""
        store = ArtifactStore()
        create_dollar_budget_right(store, "agent_1", 0.50)
        create_dollar_budget_right(store, "agent_1", 0.25, artifact_id="extra_budget")

        result = get_total_right_amount(store, "agent_1", RightType.DOLLAR_BUDGET)

        assert result == 0.75

    def test_single_right(self) -> None:
        """Returns single right's amount."""
        store = ArtifactStore()
        create_dollar_budget_right(store, "agent_1", 0.50)

        result = get_total_right_amount(store, "agent_1", RightType.DOLLAR_BUDGET)

        assert result == 0.50

    def test_no_rights_returns_zero(self) -> None:
        """Returns 0 when no matching rights."""
        store = ArtifactStore()

        result = get_total_right_amount(store, "agent_1", RightType.DOLLAR_BUDGET)

        assert result == 0.0

    def test_filters_by_model(self) -> None:
        """Filters rate_capacity by model when summing."""
        store = ArtifactStore()
        create_rate_capacity_right(store, "agent_1", "gemini", 100)
        create_rate_capacity_right(store, "agent_1", "claude", 50)

        gemini_total = get_total_right_amount(
            store, "agent_1", RightType.RATE_CAPACITY, model="gemini"
        )
        all_total = get_total_right_amount(store, "agent_1", RightType.RATE_CAPACITY)

        assert gemini_total == 100.0
        assert all_total == 150.0
