"""Tests for scripts/check_claims.py - scope-based claim system.

Tests the shared scope and trivial exemption functionality.
"""

import sys
from pathlib import Path
from typing import Any

import pytest

# Add scripts to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_claims import (
    build_file_to_feature_map,
    check_files_claimed,
    check_scope_conflict,
    load_all_features,
)


class TestSharedScope:
    """Tests for shared scope - files that never conflict."""

    def test_shared_feature_exists(self) -> None:
        """The 'shared' feature should be defined in meta/acceptance_gates/shared.yaml."""
        features = load_all_features()
        assert "shared" in features, "shared feature should be defined"

    def test_shared_files_always_claimed(self) -> None:
        """Files in shared scope should always be considered claimed."""
        # Get files in shared feature
        file_map = build_file_to_feature_map()
        shared_files = [f for f, feat in file_map.items() if feat == "shared"]

        if not shared_files:
            pytest.skip("No shared files defined")

        # With no claims at all, shared files should still be "claimed"
        claims: list[dict[str, Any]] = []
        claimed, unclaimed = check_files_claimed(shared_files, claims)

        assert len(claimed) == len(shared_files), "All shared files should be claimed"
        assert len(unclaimed) == 0, "No shared files should be unclaimed"

    def test_shared_feature_never_conflicts(self) -> None:
        """Claiming 'shared' feature should never conflict with existing claims."""
        existing_claims: list[dict[str, Any]] = [
            {"cc_id": "other-branch", "feature": "shared", "task": "Some work"},
        ]

        # Trying to claim shared should not conflict
        conflicts = check_scope_conflict(None, "shared", existing_claims)
        assert len(conflicts) == 0, "shared feature should never conflict"

    def test_other_features_still_conflict(self) -> None:
        """Non-shared features should still have normal conflict behavior."""
        existing_claims: list[dict[str, Any]] = [
            {"cc_id": "other-branch", "feature": "ledger", "task": "Some work"},
        ]

        # Trying to claim ledger should conflict
        conflicts = check_scope_conflict(None, "ledger", existing_claims)
        assert len(conflicts) == 1, "non-shared features should conflict"


class TestFileToFeatureMapping:
    """Tests for file-to-feature mapping."""

    def test_build_file_map_includes_shared(self) -> None:
        """File map should include shared feature files."""
        file_map = build_file_to_feature_map()

        # Should have at least some mappings if features are defined
        features = load_all_features()
        if features:
            assert len(file_map) > 0, "Should have file mappings"

    def test_shared_files_are_mapped(self) -> None:
        """Files declared in shared.yaml should be mapped to 'shared' feature."""
        features = load_all_features()

        if "shared" not in features:
            pytest.skip("shared feature not defined")

        shared_data = features["shared"]
        shared_code = shared_data.get("code", [])

        if not shared_code:
            pytest.skip("No code files in shared feature")

        file_map = build_file_to_feature_map()

        for code_path in shared_code:
            # Skip directories (they end with /)
            if code_path.endswith("/"):
                continue
            normalized = str(Path(code_path))
            if normalized in file_map:
                assert file_map[normalized] == "shared", f"{code_path} should map to shared"


class TestScopeConflicts:
    """Tests for scope conflict detection."""

    def test_plan_conflict(self) -> None:
        """Same plan number should conflict."""
        existing: list[dict[str, Any]] = [
            {"cc_id": "branch-a", "plan": 3, "task": "Work on plan 3"},
        ]

        conflicts = check_scope_conflict(3, None, existing)
        assert len(conflicts) == 1

    def test_feature_conflict(self) -> None:
        """Same feature should conflict."""
        existing: list[dict[str, Any]] = [
            {"cc_id": "branch-a", "feature": "ledger", "task": "Work on ledger"},
        ]

        conflicts = check_scope_conflict(None, "ledger", existing)
        assert len(conflicts) == 1

    def test_no_conflict_different_scopes(self) -> None:
        """Different plans/features should not conflict."""
        existing: list[dict[str, Any]] = [
            {"cc_id": "branch-a", "plan": 3, "feature": "ledger", "task": "Work"},
        ]

        # Different plan
        conflicts = check_scope_conflict(4, None, existing)
        assert len(conflicts) == 0

        # Different feature
        conflicts = check_scope_conflict(None, "escrow", existing)
        assert len(conflicts) == 0


class TestClaimedFilesCheck:
    """Tests for check_files_claimed function."""

    def test_mixed_claimed_unclaimed(self) -> None:
        """Should correctly separate claimed and unclaimed files."""
        file_map = build_file_to_feature_map()
        features = load_all_features()

        if not features or "shared" not in features:
            pytest.skip("Need shared feature for this test")

        # Get a file from shared and check it's claimed even with no claims
        shared_files = [f for f, feat in file_map.items() if feat == "shared"]
        other_files = [f for f, feat in file_map.items() if feat != "shared"]

        if not shared_files:
            pytest.skip("No shared files defined")

        # Test with just shared files - should all be claimed
        claimed, unclaimed = check_files_claimed(shared_files[:1], [])
        assert len(claimed) == 1
        assert len(unclaimed) == 0

        # Test with other files - should be unclaimed without matching claim
        if other_files:
            claimed, unclaimed = check_files_claimed(other_files[:1], [])
            assert len(unclaimed) == 1


@pytest.mark.plans([43])
class TestVerifyBranch:
    """Tests for verify-branch functionality (Plan #43: Meta-Enforcement)."""

    def test_verify_branch_with_matching_claim(self) -> None:
        """Branch with matching claim should be verified."""
        from check_claims import verify_has_claim

        data: dict[str, Any] = {
            "claims": [
                {
                    "cc_id": "plan-43-test",
                    "task": "Test task",
                    "plan": 43,
                }
            ]
        }

        has_claim, message = verify_has_claim(data, "plan-43-test")
        assert has_claim is True
        # Message contains the task description
        assert "Test task" in message or "claim" in message.lower()

    def test_verify_branch_without_claim(self) -> None:
        """Branch without claim should fail verification."""
        from check_claims import verify_has_claim

        data: dict[str, Any] = {
            "claims": [
                {
                    "cc_id": "other-branch",
                    "task": "Other task",
                    "plan": 99,
                }
            ]
        }

        has_claim, message = verify_has_claim(data, "nonexistent-branch")
        assert has_claim is False

    def test_verify_branch_empty_claims(self) -> None:
        """Empty claims list should fail verification."""
        from check_claims import verify_has_claim

        data: dict[str, Any] = {"claims": []}

        has_claim, message = verify_has_claim(data, "any-branch")
        assert has_claim is False

    def test_verify_branch_matches_cc_id(self) -> None:
        """Verification should match on cc_id field."""
        from check_claims import verify_has_claim

        data: dict[str, Any] = {
            "claims": [
                {
                    "cc_id": "exact-branch-name",
                    "task": "Test task",
                }
            ]
        }

        # Exact match should work
        has_claim, _ = verify_has_claim(data, "exact-branch-name")
        assert has_claim is True

        # Partial match should not work
        has_claim, _ = verify_has_claim(data, "exact-branch")
        assert has_claim is False
