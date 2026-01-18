"""Tests for meta_status.py ownership features (Plan #71)."""

import subprocess
from unittest.mock import patch

import pytest


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_returns_branch_name(self) -> None:
        """Should return current branch name."""
        from scripts.meta_status import get_current_branch

        # This runs in actual git repo, so should return something
        branch = get_current_branch()
        assert isinstance(branch, str)
        assert len(branch) > 0

    def test_handles_git_failure(self) -> None:
        """Should return empty string on git failure."""
        from scripts.meta_status import get_current_branch

        with patch("scripts.meta_status.run_cmd") as mock_run:
            mock_run.return_value = (False, "error")  # mock-ok: testing error handling
            branch = get_current_branch()
            assert branch == ""


class TestGetMyIdentity:
    """Tests for get_my_identity function."""

    def test_returns_identity_dict(self) -> None:
        """Should return dict with branch, is_main, cc_id."""
        from scripts.meta_status import get_my_identity

        identity = get_my_identity()
        assert isinstance(identity, dict)
        assert "branch" in identity
        assert "is_main" in identity
        assert "cc_id" in identity

    def test_is_main_true_on_main_branch(self) -> None:
        """Should set is_main=True when on main branch."""
        from scripts.meta_status import get_my_identity

        with patch("scripts.meta_status.get_current_branch") as mock_branch:
            mock_branch.return_value = "main"  # mock-ok: testing branch detection logic
            with patch("scripts.meta_status.get_claims") as mock_claims:
                mock_claims.return_value = []  # mock-ok: testing without claims file
                identity = get_my_identity()
                assert identity["is_main"] is True
                assert identity["branch"] == "main"

    def test_is_main_false_on_feature_branch(self) -> None:
        """Should set is_main=False when on feature branch."""
        from scripts.meta_status import get_my_identity

        with patch("scripts.meta_status.get_current_branch") as mock_branch:
            mock_branch.return_value = "plan-71-test"  # mock-ok: testing branch detection
            with patch("scripts.meta_status.get_claims") as mock_claims:
                mock_claims.return_value = []  # mock-ok: testing without claims file
                identity = get_my_identity()
                assert identity["is_main"] is False
                assert identity["branch"] == "plan-71-test"

    def test_finds_matching_claim(self) -> None:
        """Should find cc_id from matching claim."""
        from scripts.meta_status import get_my_identity

        with patch("scripts.meta_status.get_current_branch") as mock_branch:
            mock_branch.return_value = "plan-71-test"  # mock-ok: testing claim matching
            with patch("scripts.meta_status.get_claims") as mock_claims:
                mock_claims.return_value = [  # mock-ok: testing claim matching logic
                    {"cc_id": "plan-71-test", "branch": "plan-71-test", "plan": 70}
                ]
                identity = get_my_identity()
                assert identity["cc_id"] == "plan-71-test"

