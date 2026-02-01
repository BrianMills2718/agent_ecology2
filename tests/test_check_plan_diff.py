"""Tests for scripts/check_plan_diff.py - plan-to-diff verification."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from check_plan_diff import (
    Finding,
    classify_findings,
    check_plan_diff,
    format_findings,
    get_diff_files,
    is_whitelisted,
    main,
)


SAMPLE_PLAN_CONTENT = """\
# Plan 99: Test Plan

## Files Affected

- `scripts/foo.py` (create)
- `src/world/bar.py` (modify)
- `tests/test_foo.py` (create)

---

## Other Section
"""

PLAN_NO_FILES_SECTION = """\
# Plan 99: Test Plan

## Overview

Some plan without Files Affected section.

## Steps

1. Do something
"""


class TestIsWhitelisted:
    """Test whitelist matching logic."""

    def test_conftest_whitelisted(self) -> None:
        assert is_whitelisted("tests/conftest.py") is True

    def test_init_file_whitelisted(self) -> None:
        assert is_whitelisted("src/world/__init__.py") is True

    def test_plan_md_whitelisted(self) -> None:
        assert is_whitelisted("docs/plans/249_plan_to_diff_verification.md") is True

    def test_context_md_whitelisted(self) -> None:
        assert is_whitelisted(".claude/CONTEXT.md") is True

    def test_claim_yaml_whitelisted(self) -> None:
        assert is_whitelisted(".claim.yaml") is True

    def test_regular_file_not_whitelisted(self) -> None:
        assert is_whitelisted("src/world/ledger.py") is False

    def test_custom_whitelist(self) -> None:
        assert is_whitelisted("Makefile", ["Makefile"]) is True


class TestGetDiffFiles:
    """Test git diff file extraction."""

    # mock-ok: git diff requires real repository state
    @patch("check_plan_diff.subprocess.run")
    def test_returns_files(self, mock_run: MagicMock) -> None:
        # mock-ok: git diff requires real repository state
        mock_run.return_value = MagicMock(
            returncode=0, stdout="src/foo.py\ntests/test_foo.py\n"
        )
        files = get_diff_files("plan-99-test")
        assert files == ["src/foo.py", "tests/test_foo.py"]

    # mock-ok: git diff requires real repository state
    @patch("check_plan_diff.subprocess.run")
    def test_empty_diff(self, mock_run: MagicMock) -> None:
        # mock-ok: git diff requires real repository state
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        files = get_diff_files("plan-99-test")
        assert files == []

    # mock-ok: git diff requires real repository state
    @patch("check_plan_diff.subprocess.run")
    def test_git_failure(self, mock_run: MagicMock) -> None:
        # mock-ok: git diff requires real repository state
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        files = get_diff_files("nonexistent-branch")
        assert files == []


class TestClassifyFindings:
    """Test finding classification logic."""

    def test_no_discrepancies(self) -> None:
        """Clean diff matches plan exactly -> no findings."""
        declared = [
            {"path": "src/world/bar.py", "action": "modify"},
            {"path": "tests/test_foo.py", "action": "create"},
        ]
        diff_files = ["src/world/bar.py", "tests/test_foo.py"]
        findings = classify_findings(declared, diff_files)
        assert len(findings) == 0

    def test_undeclared_src_is_high(self) -> None:
        """Undeclared src/ changes flagged HIGH."""
        declared = [{"path": "src/world/bar.py", "action": "modify"}]
        diff_files = ["src/world/bar.py", "src/world/sneaky.py"]
        findings = classify_findings(declared, diff_files)
        high = [f for f in findings if f.severity == "HIGH"]
        assert len(high) == 1
        assert high[0].path == "src/world/sneaky.py"

    def test_undeclared_tests_is_medium(self) -> None:
        """Undeclared test/ changes flagged MEDIUM."""
        declared = [{"path": "src/world/bar.py", "action": "modify"}]
        diff_files = ["src/world/bar.py", "tests/test_extra.py"]
        findings = classify_findings(declared, diff_files)
        medium = [f for f in findings if f.severity == "MEDIUM"]
        assert len(medium) == 1
        assert medium[0].path == "tests/test_extra.py"

    def test_untouched_declared_is_warn(self) -> None:
        """Declared but untouched files flagged WARN."""
        declared = [
            {"path": "src/world/bar.py", "action": "modify"},
            {"path": "src/world/planned_but_skipped.py", "action": "create"},
        ]
        diff_files = ["src/world/bar.py"]
        findings = classify_findings(declared, diff_files)
        warn = [f for f in findings if f.severity == "WARN"]
        assert len(warn) == 1
        assert warn[0].path == "src/world/planned_but_skipped.py"

    def test_whitelist_suppresses(self) -> None:
        """Whitelisted files excluded from scope creep findings."""
        declared: list[dict] = []
        diff_files = ["tests/conftest.py", "src/world/__init__.py", "docs/plans/CLAUDE.md"]
        findings = classify_findings(declared, diff_files)
        # All whitelisted, so only plan drift (none declared) = no findings
        assert len(findings) == 0

    def test_custom_whitelist_suppresses(self) -> None:
        """Custom whitelist patterns also suppress."""
        declared: list[dict] = []
        diff_files = ["Makefile"]
        findings = classify_findings(declared, diff_files, whitelist=["Makefile"])
        assert len(findings) == 0

    def test_undeclared_other_file_is_medium(self) -> None:
        """Non-src, non-test undeclared files are MEDIUM."""
        declared: list[dict] = []
        diff_files = ["scripts/some_script.py"]
        findings = classify_findings(declared, diff_files)
        medium = [f for f in findings if f.severity == "MEDIUM"]
        assert len(medium) == 1


class TestCheckPlanDiff:
    """Test the main check_plan_diff function."""

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_no_files_affected_section(
        self, mock_find: MagicMock, mock_diff: MagicMock
    ) -> None:
        """Missing Files Affected section -> skip with warning, no findings."""
        mock_plan = MagicMock()
        mock_plan.exists.return_value = True
        mock_plan.read_text.return_value = PLAN_NO_FILES_SECTION
        mock_find.return_value = mock_plan
        mock_diff.return_value = ["src/foo.py"]

        findings, exit_code = check_plan_diff(99, branch="plan-99-test")
        assert len(findings) == 0
        assert exit_code == 0

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_plan_not_found(self, mock_find: MagicMock, mock_diff: MagicMock) -> None:
        """Missing plan file -> exit code 1."""
        mock_find.return_value = None
        findings, exit_code = check_plan_diff(999)
        assert exit_code == 1

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_exit_code_strict_mode(
        self, mock_find: MagicMock, mock_diff: MagicMock
    ) -> None:
        """--strict + HIGH findings -> non-zero exit code."""
        mock_plan = MagicMock()
        mock_plan.exists.return_value = True
        mock_plan.read_text.return_value = SAMPLE_PLAN_CONTENT
        mock_find.return_value = mock_plan
        mock_diff.return_value = [
            "scripts/foo.py",
            "src/world/bar.py",
            "tests/test_foo.py",
            "src/world/undeclared.py",  # HIGH: not in plan
        ]

        findings, exit_code = check_plan_diff(99, branch="plan-99-test", strict=True)
        high = [f for f in findings if f.severity == "HIGH"]
        assert len(high) >= 1
        assert exit_code == 1

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_advisory_mode_always_zero(
        self, mock_find: MagicMock, mock_diff: MagicMock
    ) -> None:
        """Default (advisory) mode -> exit 0 even with HIGH findings."""
        mock_plan = MagicMock()
        mock_plan.exists.return_value = True
        mock_plan.read_text.return_value = SAMPLE_PLAN_CONTENT
        mock_find.return_value = mock_plan
        mock_diff.return_value = [
            "scripts/foo.py",
            "src/world/bar.py",
            "tests/test_foo.py",
            "src/world/undeclared.py",
        ]

        findings, exit_code = check_plan_diff(99, branch="plan-99-test", strict=False)
        assert exit_code == 0

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_empty_diff(self, mock_find: MagicMock, mock_diff: MagicMock) -> None:
        """Empty diff -> no findings, exit 0."""
        mock_plan = MagicMock()
        mock_plan.exists.return_value = True
        mock_plan.read_text.return_value = SAMPLE_PLAN_CONTENT
        mock_find.return_value = mock_plan
        mock_diff.return_value = []

        findings, exit_code = check_plan_diff(99, branch="plan-99-test")
        assert len(findings) == 0
        assert exit_code == 0


class TestFormatFindings:
    """Test human-readable output formatting."""

    def test_no_findings(self) -> None:
        output = format_findings([], 99)
        assert "All files align" in output

    def test_findings_grouped(self) -> None:
        findings = [
            Finding("HIGH", "src/bad.py", "Scope creep"),
            Finding("WARN", "src/missing.py", "Plan drift"),
        ]
        output = format_findings(findings, 99)
        assert "HIGH" in output
        assert "WARN" in output
        assert "2 finding(s)" in output


class TestMain:
    """Test CLI entry point."""

    # mock-ok: find_plan_file requires filesystem; git diff requires repo
    @patch("check_plan_diff.get_diff_files")
    @patch("check_plan_diff.find_plan_file")
    def test_json_output(self, mock_find: MagicMock, mock_diff: MagicMock) -> None:
        mock_plan = MagicMock()
        mock_plan.exists.return_value = True
        mock_plan.read_text.return_value = SAMPLE_PLAN_CONTENT
        mock_find.return_value = mock_plan
        mock_diff.return_value = ["scripts/foo.py", "src/world/bar.py", "tests/test_foo.py"]

        with patch("sys.argv", ["check_plan_diff.py", "--plan", "99", "--json"]):
            exit_code = main()
        assert exit_code == 0
