"""Tests for scripts/cleanup_branches.py - stale remote branch cleanup."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from cleanup_branches import delete_branch, get_pr_status, get_unmerged_branches, main


class TestGetPrStatus:
    """Test PR status detection from GitHub CLI output."""

    def test_merged_pr(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {"number": 42, "state": "MERGED", "mergedAt": "2026-01-15T10:00:00Z"}
        )
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("plan-42-foo")
        assert status == "merged"
        assert merged_at == "2026-01-15T10:00:00Z"

    def test_abandoned_pr(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {"number": 43, "state": "CLOSED", "mergedAt": None}
        )
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("plan-43-bar")
        assert status == "abandoned"
        assert merged_at is None

    def test_open_pr(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {"number": 44, "state": "OPEN", "mergedAt": None}
        )
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("plan-44-baz")
        assert status == "open"
        assert merged_at is None

    def test_no_pr_found(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("random-branch")
        assert status == "no_pr"
        assert merged_at is None

    def test_gh_command_fails(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("plan-45-err")
        assert status == "no_pr"
        assert merged_at is None

    def test_malformed_json(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json {{"
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            status, merged_at = get_pr_status("plan-46-bad")
        assert status == "unknown"
        assert merged_at is None


class TestGetUnmergedBranches:
    """Test remote branch listing."""

    def test_parses_branch_list(self) -> None:
        fetch_result = MagicMock()
        fetch_result.returncode = 0
        branch_result = MagicMock()
        branch_result.stdout = (
            "  origin/plan-1-foo\n"
            "  origin/plan-2-bar\n"
            "  origin/HEAD -> origin/main\n"
        )

        # mock-ok: git fetch and git branch require real remote
        with patch("cleanup_branches.run_cmd", side_effect=[fetch_result, branch_result]):
            branches = get_unmerged_branches()
        assert branches == ["plan-1-foo", "plan-2-bar"]

    def test_empty_branch_list(self) -> None:
        fetch_result = MagicMock()
        fetch_result.returncode = 0
        branch_result = MagicMock()
        branch_result.stdout = ""

        # mock-ok: git fetch and git branch require real remote
        with patch("cleanup_branches.run_cmd", side_effect=[fetch_result, branch_result]):
            branches = get_unmerged_branches()
        assert branches == []


class TestDeleteBranch:
    """Test branch deletion."""

    def test_successful_delete(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        # mock-ok: git push --delete modifies remote
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            assert delete_branch("plan-1-foo") is True

    def test_failed_delete(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        # mock-ok: git push --delete modifies remote
        with patch("cleanup_branches.run_cmd", return_value=mock_result):
            assert delete_branch("plan-1-foo") is False


class TestMain:
    """Test CLI main function."""

    def _mock_branches_and_statuses(
        self,
        branches: list[str],
        statuses: dict[str, tuple[str, str | None]],
    ) -> tuple[MagicMock, MagicMock]:
        """Helper to mock get_unmerged_branches and get_pr_status."""
        mock_get_branches = MagicMock(return_value=branches)
        mock_get_status = MagicMock(side_effect=lambda b: statuses.get(b, ("unknown", None)))
        return mock_get_branches, mock_get_status

    def test_dry_run_lists_branches(self, capsys: pytest.CaptureFixture[str]) -> None:
        branches = ["plan-1-merged", "plan-2-open", "plan-3-abandoned"]
        statuses = {
            "plan-1-merged": ("merged", "2026-01-15T10:00:00Z"),
            "plan-2-open": ("open", None),
            "plan-3-abandoned": ("abandoned", None),
        }
        mock_get_branches, mock_get_status = self._mock_branches_and_statuses(branches, statuses)

        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_branches.get_unmerged_branches", mock_get_branches),
            patch("cleanup_branches.get_pr_status", mock_get_status),
            patch("sys.argv", ["cleanup_branches.py"]),
        ):
            result = main()

        assert result == 0
        output = capsys.readouterr().out
        assert "Merged PRs (safe to delete): 1" in output
        assert "Would delete 1 branches" in output
        assert "plan-1-merged" in output

    def test_delete_only_merged(self, capsys: pytest.CaptureFixture[str]) -> None:
        branches = ["plan-1-merged", "plan-2-abandoned"]
        statuses = {
            "plan-1-merged": ("merged", "2026-01-15T10:00:00Z"),
            "plan-2-abandoned": ("abandoned", None),
        }
        mock_get_branches, mock_get_status = self._mock_branches_and_statuses(branches, statuses)
        mock_delete = MagicMock(return_value=True)

        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_branches.get_unmerged_branches", mock_get_branches),
            patch("cleanup_branches.get_pr_status", mock_get_status),
            patch("cleanup_branches.delete_branch", mock_delete),
            patch("sys.argv", ["cleanup_branches.py", "--delete"]),
        ):
            result = main()

        assert result == 0
        mock_delete.assert_called_once_with("plan-1-merged")

    def test_delete_all_includes_abandoned(self, capsys: pytest.CaptureFixture[str]) -> None:
        branches = ["plan-1-merged", "plan-2-abandoned"]
        statuses = {
            "plan-1-merged": ("merged", "2026-01-15T10:00:00Z"),
            "plan-2-abandoned": ("abandoned", None),
        }
        mock_get_branches, mock_get_status = self._mock_branches_and_statuses(branches, statuses)
        mock_delete = MagicMock(return_value=True)

        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_branches.get_unmerged_branches", mock_get_branches),
            patch("cleanup_branches.get_pr_status", mock_get_status),
            patch("cleanup_branches.delete_branch", mock_delete),
            patch("sys.argv", ["cleanup_branches.py", "--delete", "--all"]),
        ):
            result = main()

        assert result == 0
        assert mock_delete.call_count == 2

    def test_no_branches_to_delete(self, capsys: pytest.CaptureFixture[str]) -> None:
        mock_get_branches = MagicMock(return_value=["plan-1-open"])
        mock_get_status = MagicMock(return_value=("open", None))

        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_branches.get_unmerged_branches", mock_get_branches),
            patch("cleanup_branches.get_pr_status", mock_get_status),
            patch("sys.argv", ["cleanup_branches.py"]),
        ):
            result = main()

        assert result == 0
        output = capsys.readouterr().out
        assert "No branches to delete" in output

    def test_failed_delete_returns_nonzero(self) -> None:
        branches = ["plan-1-merged"]
        statuses = {"plan-1-merged": ("merged", "2026-01-15T10:00:00Z")}
        mock_get_branches, mock_get_status = self._mock_branches_and_statuses(branches, statuses)
        mock_delete = MagicMock(return_value=False)

        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_branches.get_unmerged_branches", mock_get_branches),
            patch("cleanup_branches.get_pr_status", mock_get_status),
            patch("cleanup_branches.delete_branch", mock_delete),
            patch("sys.argv", ["cleanup_branches.py", "--delete"]),
        ):
            result = main()

        assert result == 1

    def test_cli_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/cleanup_branches.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--delete" in result.stdout
        assert "--all" in result.stdout
