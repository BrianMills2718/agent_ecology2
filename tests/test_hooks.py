"""Tests for Claude Code enforcement hooks.

Tests for:
- check-file-scope.sh: Blocks edits to files not in plan's Files Affected
- check-references-reviewed.sh: Warns when plan lacks References Reviewed

These hooks enforce planning discipline in CC workflows.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# Mark all tests with plan 89
pytestmark = pytest.mark.plans([89])


class TestFileScopeHook:
    """Tests for check-file-scope.sh hook."""

    @pytest.fixture
    def hook_path(self) -> Path:
        """Get path to the file scope hook."""
        return Path(__file__).parent.parent / ".claude/hooks/check-file-scope.sh"

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repo for testing."""
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            capture_output=True,
        )

        # Create initial commit
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo,
            capture_output=True,
        )

        return repo

    def create_plan_file(
        self, repo: Path, plan_num: int, files_affected: list[str]
    ) -> Path:
        """Create a plan file with Files Affected section."""
        plans_dir = repo / "docs/plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        plan_content = f"""# Plan {plan_num}: Test Plan

**Status:** 🚧 In Progress

## Files Affected

"""
        for f in files_affected:
            plan_content += f"- {f} (modify)\n"

        plan_file = plans_dir / f"{plan_num:02d}_test_plan.md"
        plan_file.write_text(plan_content)
        return plan_file

    def run_hook(
        self,
        hook_path: Path,
        repo: Path,
        file_path: str,
        branch: str = "main",
    ) -> tuple[int, str, str]:
        """Run the hook with given input and return (exit_code, stdout, stderr)."""
        # Create tool input JSON with relative path (what CC actually uses)
        # The hook runs from repo root, so relative paths work correctly
        tool_input = {"tool_input": {"file_path": file_path}}
        input_json = json.dumps(tool_input)

        # Checkout branch if not main
        if branch != "main":
            subprocess.run(
                ["git", "checkout", "-b", branch],
                cwd=repo,
                capture_output=True,
            )

        # Copy hook to temp location (since it references scripts/)
        # Actually, we'll need to set up the scripts directory too
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Copy parse_plan.py
        original_parse = Path(__file__).parent.parent / "scripts/parse_plan.py"
        if original_parse.exists():
            (scripts_dir / "parse_plan.py").write_text(original_parse.read_text())

        # Run hook
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            cwd=repo,
            env={**os.environ, "DEBUG": ""},  # Disable debug output
        )

        return result.returncode, result.stdout, result.stderr

    def test_file_scope_blocks_undeclared(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook blocks edit to file not in Files Affected."""
        # Create plan that declares src/allowed.py but not src/blocked.py
        self.create_plan_file(temp_repo, 99, ["src/allowed.py"])

        # Create the source directories
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/blocked.py").write_text("# blocked")

        # Run hook on undeclared file
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/blocked.py",
            branch="plan-99-test",
        )

        # Should block (exit 2)
        assert exit_code == 2, f"Expected exit 2, got {exit_code}. stderr: {stderr}"
        assert "BLOCKED" in stderr
        assert "not in plan's declared scope" in stderr.lower() or "not in plan" in stderr.lower()

    def test_file_scope_allows_declared(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook allows edit to file in Files Affected."""
        # Create plan that declares src/allowed.py
        self.create_plan_file(temp_repo, 99, ["src/allowed.py"])

        # Create the source directory
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/allowed.py").write_text("# allowed")

        # Run hook on declared file
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/allowed.py",
            branch="plan-99-test",
        )

        # Should allow (exit 0)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. stderr: {stderr}"

    def test_file_scope_allows_no_plan(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook allows edit when branch has no plan number."""
        # Create source file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/somefile.py").write_text("# test")

        # Run hook on non-plan branch
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/somefile.py",
            branch="trivial-fix",  # No plan number
        )

        # Should allow (exit 0)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. stderr: {stderr}"

    def test_file_scope_allows_coordination_files(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook always allows coordination files (.claude/, CLAUDE.md, docs/plans/)."""
        # Create plan (doesn't declare .claude files)
        self.create_plan_file(temp_repo, 99, ["src/other.py"])

        # Test various coordination files
        coordination_files = [
            ".claude/settings.json",
            "CLAUDE.md",
            "docs/plans/CLAUDE.md",
            "docs/plans/99_test_plan.md",
        ]

        for coord_file in coordination_files:
            # Create parent dir and file
            coord_path = temp_repo / coord_file
            coord_path.parent.mkdir(parents=True, exist_ok=True)
            coord_path.write_text("# coordination")

            exit_code, stdout, stderr = self.run_hook(
                hook_path,
                temp_repo,
                coord_file,
                branch="plan-99-test",
            )

            assert exit_code == 0, (
                f"Coordination file {coord_file} should be allowed. "
                f"Got exit {exit_code}, stderr: {stderr}"
            )

    def test_file_scope_allows_main_branch(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook allows any file on main branch (review mode)."""
        # Create source file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/anyfile.py").write_text("# test")

        # Run hook on main branch
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/anyfile.py",
            branch="main",
        )

        # Should allow (exit 0) - main is for reviews
        assert exit_code == 0, f"Expected exit 0 on main, got {exit_code}. stderr: {stderr}"


class TestReferencesReviewedHook:
    """Tests for check-references-reviewed.sh hook."""

    @pytest.fixture
    def hook_path(self) -> Path:
        """Get path to the references reviewed hook."""
        return Path(__file__).parent.parent / ".claude/hooks/check-references-reviewed.sh"

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repo for testing."""
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            capture_output=True,
        )

        # Create initial commit
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo,
            capture_output=True,
        )

        return repo

    def create_plan_file(
        self,
        repo: Path,
        plan_num: int,
        references: list[str] | None = None,
    ) -> Path:
        """Create a plan file with optional References Reviewed section."""
        plans_dir = repo / "docs/plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        plan_content = f"""# Plan {plan_num}: Test Plan

**Status:** 🚧 In Progress

"""
        if references is not None:
            plan_content += "## References Reviewed\n\n"
            for ref in references:
                plan_content += f"- {ref}\n"

        plan_file = plans_dir / f"{plan_num:02d}_test_plan.md"
        plan_file.write_text(plan_content)
        return plan_file

    def run_hook(
        self,
        hook_path: Path,
        repo: Path,
        file_path: str,
        branch: str = "main",
    ) -> tuple[int, str, str]:
        """Run the hook with given input and return (exit_code, stdout, stderr)."""
        # Create tool input JSON with relative path (what CC actually uses)
        tool_input = {"tool_input": {"file_path": file_path}}
        input_json = json.dumps(tool_input)

        # Checkout branch if not main
        if branch != "main":
            subprocess.run(
                ["git", "checkout", "-b", branch],
                cwd=repo,
                capture_output=True,
            )

        # Set up scripts directory
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Copy parse_plan.py
        original_parse = Path(__file__).parent.parent / "scripts/parse_plan.py"
        if original_parse.exists():
            (scripts_dir / "parse_plan.py").write_text(original_parse.read_text())

        # Clean up any session marker to ensure warning fires
        session_marker = f"/tmp/.claude_refs_warned_{os.getpid()}"
        if os.path.exists(session_marker):
            os.remove(session_marker)

        # Run hook
        result = subprocess.run(
            ["bash", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            cwd=repo,
        )

        return result.returncode, result.stdout, result.stderr

    def test_references_warns_missing(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook warns when References Reviewed missing."""
        # Create plan without references section
        self.create_plan_file(temp_repo, 99, references=None)

        # Create source file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/somefile.py").write_text("# test")

        # Run hook
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/somefile.py",
            branch="plan-99-test",
        )

        # Should still allow (exit 0) but warn
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert "EXPLORATION WARNING" in stderr or "insufficient" in stderr.lower()

    def test_references_warns_insufficient(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook warns when References Reviewed has fewer than 2 entries."""
        # Create plan with only 1 reference (need at least 2)
        self.create_plan_file(
            temp_repo, 99,
            references=["src/one.py:1-10 - just one reference"]
        )

        # Create source file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/somefile.py").write_text("# test")

        # Run hook
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/somefile.py",
            branch="plan-99-test",
        )

        # Should still allow (exit 0) but warn
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert "WARNING" in stderr or "insufficient" in stderr.lower()

    def test_references_silent_when_present(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook silent when References Reviewed exists with enough entries."""
        # Create plan with 2+ references
        self.create_plan_file(
            temp_repo, 99,
            references=[
                "src/first.py:1-10 - first reference",
                "src/second.py:20-30 - second reference",
            ]
        )

        # Create source file
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src/somefile.py").write_text("# test")

        # Run hook
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "src/somefile.py",
            branch="plan-99-test",
        )

        # Should allow (exit 0) without warning
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        # Should NOT contain warning
        assert "WARNING" not in stderr
        assert "EXPLORATION" not in stderr

    def test_references_skips_non_source_files(
        self, hook_path: Path, temp_repo: Path
    ) -> None:
        """Hook doesn't check references for non-source files (docs, config)."""
        # Create plan without references
        self.create_plan_file(temp_repo, 99, references=None)

        # Create a doc file
        (temp_repo / "docs").mkdir(exist_ok=True)
        (temp_repo / "docs/readme.md").write_text("# doc")

        # Run hook on doc file
        exit_code, stdout, stderr = self.run_hook(
            hook_path,
            temp_repo,
            "docs/readme.md",
            branch="plan-99-test",
        )

        # Should allow without warning (docs don't require references)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}"
        assert "WARNING" not in stderr
