"""Tests for scripts/cleanup_orphaned_worktrees.py - orphaned worktree cleanup."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from cleanup_orphaned_worktrees import (
    cleanup_worktree,
    extract_worktree_name,
    find_orphaned_worktrees,
    get_merged_prs,
    get_worktrees,
    has_uncommitted_changes,
    main,
    remote_branch_exists,
    run_cmd,
)


class TestRunCmd:
    """Test subprocess wrapper."""

    def test_successful_command(self) -> None:
        # mock-ok: avoid running real commands in tests
        with patch("cleanup_orphaned_worktrees.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output\n")  # mock-ok: subprocess
            success, output = run_cmd(["echo", "hello"])
        assert success is True
        assert output == "output"

    def test_failed_command(self) -> None:
        # mock-ok: avoid running real commands in tests
        with patch("cleanup_orphaned_worktrees.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="error\n")  # mock-ok: subprocess
            success, output = run_cmd(["false"])
        assert success is False
        assert output == "error"

    def test_exception_returns_false(self) -> None:
        # mock-ok: simulate subprocess exception
        with patch("cleanup_orphaned_worktrees.subprocess.run", side_effect=OSError("no such file")):
            success, output = run_cmd(["nonexistent"])
        assert success is False
        assert "no such file" in output

    def test_passes_cwd(self) -> None:
        # mock-ok: verify cwd argument forwarding
        with patch("cleanup_orphaned_worktrees.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")  # mock-ok: subprocess
            run_cmd(["ls"], cwd="/tmp")
        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["cwd"] == "/tmp"


class TestExtractWorktreeName:
    """Test worktree name extraction from paths."""

    def test_standard_worktree_path(self) -> None:
        assert extract_worktree_name("/repo/worktrees/plan-91-foo") == "plan-91-foo"

    def test_nested_worktree_path(self) -> None:
        assert extract_worktree_name("/a/b/worktrees/plan-5-bar") == "plan-5-bar"

    def test_no_worktrees_in_path(self) -> None:
        assert extract_worktree_name("/some/other/path") == "path"

    def test_worktrees_at_end_of_path(self) -> None:
        # "worktrees" is the last component, no child
        assert extract_worktree_name("/repo/worktrees") == "worktrees"

    def test_absolute_path_no_worktrees(self) -> None:
        assert extract_worktree_name("/home/user/project") == "project"


class TestGetWorktrees:
    """Test parsing of git worktree list --porcelain output."""

    def test_parses_multiple_worktrees(self) -> None:
        porcelain_output = (
            "worktree /repo\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /repo/worktrees/plan-1-foo\n"
            "HEAD def456\n"
            "branch refs/heads/plan-1-foo\n"
            "\n"
            "worktree /repo/worktrees/plan-2-bar\n"
            "HEAD 789abc\n"
            "branch refs/heads/plan-2-bar\n"
        )
        # mock-ok: git worktree list requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, porcelain_output)):
            result = get_worktrees()

        assert len(result) == 3
        assert result[0]["path"] == "/repo"
        assert result[0]["branch"] == "main"
        assert result[1]["path"] == "/repo/worktrees/plan-1-foo"
        assert result[1]["branch"] == "plan-1-foo"
        assert result[2]["branch"] == "plan-2-bar"

    def test_handles_detached_head(self) -> None:
        porcelain_output = (
            "worktree /repo/worktrees/detached-wt\n"
            "HEAD abc123\n"
            "detached\n"
        )
        # mock-ok: git worktree list requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, porcelain_output)):
            result = get_worktrees()

        assert len(result) == 1
        assert result[0]["detached"] is True
        assert "branch" not in result[0]

    def test_handles_bare_repo(self) -> None:
        porcelain_output = "worktree /repo\nHEAD abc123\nbare\n"
        # mock-ok: git worktree list requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, porcelain_output)):
            result = get_worktrees()

        assert len(result) == 1
        assert result[0]["bare"] is True

    def test_empty_output(self) -> None:
        # mock-ok: git worktree list requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "")):
            result = get_worktrees()
        assert result == []

    def test_command_failure(self) -> None:
        # mock-ok: git worktree list requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(False, "error")):
            result = get_worktrees()
        assert result == []


class TestRemoteBranchExists:
    """Test remote branch existence check."""

    def test_branch_exists(self) -> None:
        # mock-ok: git ls-remote requires real remote
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "abc123\trefs/heads/plan-1-foo")):
            assert remote_branch_exists("plan-1-foo") is True

    def test_branch_missing(self) -> None:
        # mock-ok: git ls-remote requires real remote
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "")):
            assert remote_branch_exists("plan-1-foo") is False

    def test_command_fails(self) -> None:
        # mock-ok: git ls-remote requires real remote
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(False, "")):
            assert remote_branch_exists("plan-1-foo") is False


class TestGetMergedPrs:
    """Test merged PR listing from GitHub CLI."""

    def test_parses_pr_list(self) -> None:
        import json

        pr_data = [
            {"number": 100, "title": "Plan 1", "headRefName": "plan-1-foo", "mergedAt": "2026-01-15T10:00:00Z"},
            {"number": 101, "title": "Plan 2", "headRefName": "plan-2-bar", "mergedAt": "2026-01-16T10:00:00Z"},
        ]
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, json.dumps(pr_data))):
            result = get_merged_prs()

        assert "plan-1-foo" in result
        assert result["plan-1-foo"]["number"] == 100
        assert "plan-2-bar" in result

    def test_empty_output(self) -> None:
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "")):
            assert get_merged_prs() == {}

    def test_command_failure(self) -> None:
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(False, "")):
            assert get_merged_prs() == {}

    def test_malformed_json(self) -> None:
        # mock-ok: gh pr list requires GitHub API access
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "not json {{")):
            assert get_merged_prs() == {}


class TestHasUncommittedChanges:
    """Test uncommitted changes detection."""

    def test_clean_worktree(self) -> None:
        # mock-ok: git status requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "")):
            assert has_uncommitted_changes("/path") is False

    def test_dirty_worktree(self) -> None:
        # mock-ok: git status requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(True, "M file.py")):
            assert has_uncommitted_changes("/path") is True

    def test_command_failure(self) -> None:
        # mock-ok: git status requires real repo
        with patch("cleanup_orphaned_worktrees.run_cmd", return_value=(False, "")):
            assert has_uncommitted_changes("/path") is False


class TestFindOrphanedWorktrees:
    """Test orphan detection logic."""

    def test_finds_orphan_branch_deleted(self) -> None:
        worktrees = [
            {"path": "/repo", "branch": "main"},
            {"path": "/repo/worktrees/plan-1-foo", "branch": "plan-1-foo"},
        ]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
            patch("cleanup_orphaned_worktrees.remote_branch_exists", return_value=False),
            patch("cleanup_orphaned_worktrees.has_uncommitted_changes", return_value=False),
        ):
            orphans = find_orphaned_worktrees()

        assert len(orphans) == 1
        assert orphans[0]["branch"] == "plan-1-foo"
        assert orphans[0]["reason"] == "branch deleted from remote"

    def test_skips_main_worktree(self) -> None:
        worktrees = [
            {"path": "/repo", "branch": "main"},
        ]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
        ):
            orphans = find_orphaned_worktrees()

        assert len(orphans) == 0

    def test_skips_worktree_with_remote_branch(self) -> None:
        worktrees = [
            {"path": "/repo/worktrees/plan-1-foo", "branch": "plan-1-foo"},
        ]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
            patch("cleanup_orphaned_worktrees.remote_branch_exists", return_value=True),
        ):
            orphans = find_orphaned_worktrees()

        assert len(orphans) == 0

    def test_detached_head_skipped(self) -> None:
        """Detached HEAD has no branch, so `not branch` skips it."""
        worktrees = [
            {"path": "/repo/worktrees/detached-wt", "branch": "", "detached": True},
        ]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
        ):
            orphans = find_orphaned_worktrees()

        assert len(orphans) == 0

    def test_tracks_uncommitted_changes(self) -> None:
        worktrees = [
            {"path": "/repo/worktrees/plan-1-foo", "branch": "plan-1-foo"},
        ]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
            patch("cleanup_orphaned_worktrees.remote_branch_exists", return_value=False),
            patch("cleanup_orphaned_worktrees.has_uncommitted_changes", return_value=True),
        ):
            orphans = find_orphaned_worktrees()

        assert orphans[0]["has_uncommitted"] is True

    def test_includes_merged_pr_info(self) -> None:
        worktrees = [
            {"path": "/repo/worktrees/plan-1-foo", "branch": "plan-1-foo"},
        ]
        merged = {"plan-1-foo": {"number": 100, "title": "Plan 1"}}
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value=merged),
            patch("cleanup_orphaned_worktrees.remote_branch_exists", return_value=False),
            patch("cleanup_orphaned_worktrees.has_uncommitted_changes", return_value=False),
        ):
            orphans = find_orphaned_worktrees()

        assert orphans[0]["merged_pr"]["number"] == 100

    def test_skips_no_branch(self) -> None:
        """Worktree with no branch key (like main bare) is skipped."""
        worktrees = [{"path": "/repo"}]
        # mock-ok: git/gh commands require real repo/API
        with (
            patch("cleanup_orphaned_worktrees.get_worktrees", return_value=worktrees),
            patch("cleanup_orphaned_worktrees.get_merged_prs", return_value={}),
        ):
            orphans = find_orphaned_worktrees()

        assert len(orphans) == 0


class TestCleanupWorktree:
    """Test worktree removal logic."""

    def test_uses_safe_script_when_available(self, tmp_path: Path) -> None:
        """When safe_worktree_remove.py exists, delegates to it."""
        fake_script = tmp_path / "safe_worktree_remove.py"
        fake_script.write_text("# placeholder")

        calls: list[list[str]] = []

        def fake_run_cmd(cmd: list[str], **kwargs: object) -> tuple[bool, str]:
            calls.append(cmd)
            return (True, "removed")

        # mock-ok: avoid running real cleanup commands
        with (
            patch("cleanup_orphaned_worktrees.run_cmd", side_effect=fake_run_cmd),
            patch("cleanup_orphaned_worktrees.Path", wraps=Path) as MockPath,
        ):
            # Make __file__ resolve to our tmp_path so script_path finds our fake
            MockPath.__file__ = str(tmp_path / "cleanup_orphaned_worktrees.py")
            cleanup_worktree("/repo/worktrees/plan-1-foo")

        # Should call python with the safe_worktree_remove.py script
        assert len(calls) == 1
        assert "safe_worktree_remove" in str(calls[0])

    def test_fallback_to_git_worktree_remove(self) -> None:
        """When safe_worktree_remove.py doesn't exist, uses git directly."""
        calls = []

        def fake_run_cmd(cmd: list[str], **kwargs: object) -> tuple[bool, str]:
            calls.append(cmd)
            return (True, "removed")

        # mock-ok: avoid running real git worktree remove
        with (
            patch("cleanup_orphaned_worktrees.run_cmd", side_effect=fake_run_cmd),
            patch("cleanup_orphaned_worktrees.Path") as MockPath,
        ):
            mock_script = MagicMock()
            mock_script.exists.return_value = False
            MockPath.__file__ = "fake"
            MockPath.return_value.parent.__truediv__ = MagicMock(return_value=mock_script)

            success, output = cleanup_worktree("/repo/worktrees/plan-1-foo")

        assert success is True
        # Should have called git worktree remove, then git worktree prune
        assert any("worktree" in str(c) for c in calls)

    def test_force_flag_passed(self) -> None:
        """Force flag is included in the git command."""
        calls = []

        def fake_run_cmd(cmd: list[str], **kwargs: object) -> tuple[bool, str]:
            calls.append(cmd)
            return (True, "")

        # mock-ok: avoid running real git worktree remove
        with (
            patch("cleanup_orphaned_worktrees.run_cmd", side_effect=fake_run_cmd),
            patch("cleanup_orphaned_worktrees.Path") as MockPath,
        ):
            mock_script = MagicMock()
            mock_script.exists.return_value = False
            MockPath.return_value.parent.__truediv__ = MagicMock(return_value=mock_script)

            cleanup_worktree("/repo/worktrees/plan-1-foo", force=True)

        # The git worktree remove call should include --force
        remove_calls = [c for c in calls if "remove" in c]
        assert any("--force" in c for c in remove_calls)


class TestMain:
    """Test CLI main function."""

    def test_no_orphans_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=[]),
            patch("sys.argv", ["cleanup_orphaned_worktrees.py"]),
        ):
            main()

        output = capsys.readouterr().out
        assert "No orphaned worktrees found" in output

    def test_report_mode_shows_orphans(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-foo",
                "name": "plan-1-foo",
                "branch": "plan-1-foo",
                "detached": False,
                "has_uncommitted": False,
                "merged_pr": None,
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("sys.argv", ["cleanup_orphaned_worktrees.py"]),
        ):
            main()

        output = capsys.readouterr().out
        assert "plan-1-foo" in output
        assert "branch deleted from remote" in output
        assert "1 orphaned worktree" in output

    def test_auto_cleans_clean_orphans(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-foo",
                "name": "plan-1-foo",
                "branch": "plan-1-foo",
                "detached": False,
                "has_uncommitted": False,
                "merged_pr": None,
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not real cleanup
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("cleanup_orphaned_worktrees.cleanup_worktree", return_value=(True, "")) as mock_cleanup,
            patch("sys.argv", ["cleanup_orphaned_worktrees.py", "--auto"]),
        ):
            main()

        mock_cleanup.assert_called_once_with("/repo/worktrees/plan-1-foo", force=False)
        output = capsys.readouterr().out
        assert "1 cleaned" in output

    def test_auto_skips_uncommitted_without_force(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-dirty",
                "name": "plan-1-dirty",
                "branch": "plan-1-dirty",
                "detached": False,
                "has_uncommitted": True,
                "merged_pr": None,
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not real cleanup
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("sys.argv", ["cleanup_orphaned_worktrees.py", "--auto"]),
        ):
            main()

        output = capsys.readouterr().out
        assert "SKIPPED" in output
        assert "1 skipped" in output

    def test_auto_force_cleans_uncommitted(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-dirty",
                "name": "plan-1-dirty",
                "branch": "plan-1-dirty",
                "detached": False,
                "has_uncommitted": True,
                "merged_pr": None,
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not real cleanup
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("cleanup_orphaned_worktrees.cleanup_worktree", return_value=(True, "")) as mock_cleanup,
            patch("sys.argv", ["cleanup_orphaned_worktrees.py", "--auto", "--force"]),
        ):
            main()

        mock_cleanup.assert_called_once_with("/repo/worktrees/plan-1-dirty", force=True)

    def test_failed_cleanup_counted(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-foo",
                "name": "plan-1-foo",
                "branch": "plan-1-foo",
                "detached": False,
                "has_uncommitted": False,
                "merged_pr": None,
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not real cleanup
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("cleanup_orphaned_worktrees.cleanup_worktree", return_value=(False, "permission denied")),
            patch("sys.argv", ["cleanup_orphaned_worktrees.py", "--auto"]),
        ):
            main()

        output = capsys.readouterr().out
        assert "Failed" in output
        assert "1 skipped" in output

    def test_shows_merged_pr_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        orphans = [
            {
                "path": "/repo/worktrees/plan-1-foo",
                "name": "plan-1-foo",
                "branch": "plan-1-foo",
                "detached": False,
                "has_uncommitted": False,
                "merged_pr": {"number": 42, "title": "Add feature X"},
                "reason": "branch deleted from remote",
            },
        ]
        # mock-ok: testing CLI flow, not git/gh commands
        with (
            patch("cleanup_orphaned_worktrees.find_orphaned_worktrees", return_value=orphans),
            patch("sys.argv", ["cleanup_orphaned_worktrees.py"]),
        ):
            main()

        output = capsys.readouterr().out
        assert "PR #42" in output

    def test_cli_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/cleanup_orphaned_worktrees.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--auto" in result.stdout
        assert "--force" in result.stdout
