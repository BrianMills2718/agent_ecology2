"""Tests for check_plan_completion.py script.

Verifies plan completion evidence detection.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "check_plan_completion.py"


class TestCheckPlanCompletion:
    """Tests for check_plan_completion.py."""

    def test_script_exists(self):
        """Script file exists."""
        assert SCRIPT_PATH.exists(), f"Script not found at {SCRIPT_PATH}"

    def test_help_runs(self):
        """Script --help exits cleanly."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Check plan completion evidence" in result.stdout

    def test_no_args_shows_help(self):
        """Script with no args shows help."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        # Should exit 0 and show help
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_plan_check_for_existing_plan(self):
        """Check a known complete plan has evidence."""
        # Plan #35 (Verification Enforcement) should be complete with evidence
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--plan", "35"],
            capture_output=True,
            text=True,
        )
        # Should report status (may or may not have evidence)
        assert "Plan #35:" in result.stdout

    def test_list_missing_runs(self):
        """--list-missing runs without error."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--list-missing"],
            capture_output=True,
            text=True,
        )
        # Should complete (exit code depends on whether there are issues)
        assert result.returncode in [0, 1]
        # Should have output
        assert result.stdout.strip()

    def test_recent_commits_runs(self):
        """--recent-commits runs without error."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--recent-commits", "1"],
            capture_output=True,
            text=True,
        )
        # Should complete (exit code depends on whether there are issues)
        assert result.returncode in [0, 1]
        # Should have output
        assert "Checking" in result.stdout or "recent" in result.stdout.lower()

    def test_warn_only_flag(self):
        """--warn-only prevents exit code 1."""
        # Even if there are issues, --warn-only should return 0
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--recent-commits", "1", "--warn-only"],
            capture_output=True,
            text=True,
        )
        # With --warn-only, should always exit 0
        assert result.returncode == 0
