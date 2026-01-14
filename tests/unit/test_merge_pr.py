"""Tests for merge_pr.py distributed locking."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from merge_pr import (
    get_merge_lock,
    load_yaml,
    save_yaml,
    check_pr_mergeable,
    LOCK_TIMEOUT_MINUTES,
)


class TestGetMergeLock:
    """Tests for get_merge_lock function."""

    def test_no_lock_returns_none(self) -> None:
        """No merging field returns None."""
        data: dict = {"claims": [], "completed": [], "merging": None}
        assert get_merge_lock(data) is None

    def test_empty_merging_returns_none(self) -> None:
        """Empty merging dict returns None."""
        data: dict = {"claims": [], "completed": [], "merging": {}}
        assert get_merge_lock(data) is None

    def test_valid_lock_returns_lock(self) -> None:
        """Valid recent lock is returned."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lock = {"pr": "123", "cc_id": "test", "locked_at": now}
        data: dict = {"claims": [], "completed": [], "merging": lock}

        result = get_merge_lock(data)
        assert result is not None
        assert result["pr"] == "123"

    def test_stale_lock_returns_none(self) -> None:
        """Lock older than timeout returns None."""
        from datetime import datetime, timezone, timedelta

        old_time = datetime.now(timezone.utc) - timedelta(minutes=LOCK_TIMEOUT_MINUTES + 5)
        lock = {
            "pr": "123",
            "cc_id": "test",
            "locked_at": old_time.isoformat().replace("+00:00", "Z"),
        }
        data: dict = {"claims": [], "completed": [], "merging": lock}

        result = get_merge_lock(data)
        assert result is None


class TestLoadSaveYaml:
    """Tests for YAML load/save functions."""

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """Missing file returns default structure."""
        # mock-ok: Testing file operations without real filesystem side effects
        with patch("merge_pr.YAML_PATH", tmp_path / "nonexistent.yaml"):
            result = load_yaml()
            assert result["claims"] == []
            assert result["completed"] == []
            assert result["merging"] is None

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Data survives save/load cycle."""
        yaml_path = tmp_path / ".claude" / "active-work.yaml"

        # mock-ok: Testing file operations in isolated temp directory
        with patch("merge_pr.YAML_PATH", yaml_path):
            data: dict = {
                "claims": [{"cc_id": "test", "task": "Test task"}],
                "completed": [],
                "merging": {"pr": "42", "cc_id": "test", "locked_at": "2026-01-14T00:00:00Z"},
            }
            save_yaml(data)

            loaded = load_yaml()
            assert loaded["claims"] == data["claims"]
            merging = loaded["merging"]
            assert merging is not None
            assert isinstance(merging, dict)
            assert merging["pr"] == "42"


class TestCheckPrMergeable:
    """Tests for PR mergeable check."""

    def test_conflicting_pr_not_mergeable(self) -> None:
        """PR with conflicts is not mergeable."""
        # mock-ok: Avoiding real GitHub API calls in unit tests
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}'

        with patch("merge_pr.run_cmd", return_value=mock_result):
            mergeable, reason = check_pr_mergeable(123)
            assert mergeable is False
            assert "conflicts" in reason.lower()

    def test_behind_pr_not_mergeable(self) -> None:
        """PR behind main is not mergeable."""
        # mock-ok: Avoiding real GitHub API calls in unit tests
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"mergeable": "MERGEABLE", "mergeStateStatus": "BEHIND"}'

        with patch("merge_pr.run_cmd", return_value=mock_result):
            mergeable, reason = check_pr_mergeable(123)
            assert mergeable is False
            assert "behind" in reason.lower()

    def test_mergeable_pr_returns_ok(self) -> None:
        """Clean PR is mergeable."""
        # mock-ok: Avoiding real GitHub API calls in unit tests
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = (
            '{"mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "statusCheckRollup": []}'
        )

        with patch("merge_pr.run_cmd", return_value=mock_result):
            mergeable, reason = check_pr_mergeable(123)
            assert mergeable is True
            assert reason == "OK"
