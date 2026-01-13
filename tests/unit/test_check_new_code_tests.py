"""Tests for scripts/check_new_code_tests.py

These tests verify the new code test checker works correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_new_code_tests import (
    requires_tests,
    is_exempt,
    find_test_file,
    suggest_test_location,
)


class TestRequiresTests:
    """Tests for requires_tests function."""

    def test_src_file_requires_tests(self) -> None:
        """Source files in src/ require tests."""
        assert requires_tests(Path("src/world/ledger.py"))
        assert requires_tests(Path("src/agents/agent.py"))

    def test_scripts_require_tests(self) -> None:
        """Scripts require tests."""
        assert requires_tests(Path("scripts/check_plan_blockers.py"))

    def test_non_python_does_not_require(self) -> None:
        """Non-Python files don't require tests."""
        assert not requires_tests(Path("src/world/README.md"))
        assert not requires_tests(Path("scripts/setup_hooks.sh"))

    def test_test_files_dont_require_tests(self) -> None:
        """Test files themselves don't require tests."""
        assert not requires_tests(Path("tests/unit/test_ledger.py"))

    def test_init_files_exempt(self) -> None:
        """__init__.py files are exempt."""
        assert not requires_tests(Path("src/world/__init__.py"))

    def test_conftest_exempt(self) -> None:
        """conftest.py files are exempt."""
        assert not requires_tests(Path("tests/conftest.py"))


class TestIsExempt:
    """Tests for is_exempt function."""

    def test_init_exempt(self) -> None:
        """__init__.py is exempt."""
        assert is_exempt(Path("src/__init__.py"))

    def test_conftest_exempt(self) -> None:
        """conftest.py is exempt."""
        assert is_exempt(Path("tests/conftest.py"))

    def test_template_exempt(self) -> None:
        """Template files are exempt."""
        assert is_exempt(Path("src/agents/_template/agent.py"))

    def test_claude_md_exempt(self) -> None:
        """CLAUDE.md files are exempt."""
        assert is_exempt(Path("src/CLAUDE.md"))

    def test_normal_file_not_exempt(self) -> None:
        """Normal files are not exempt."""
        assert not is_exempt(Path("src/world/ledger.py"))


class TestFindTestFile:
    """Tests for find_test_file function."""

    def test_finds_unit_test(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Finds test in unit/ directory."""
        # Create test file
        test_dir = tmp_path / "tests" / "unit"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test_ledger.py"
        test_file.write_text("# test")

        # Monkeypatch Path.exists to check in tmp_path
        monkeypatch.chdir(tmp_path)

        result = find_test_file(Path("src/world/ledger.py"))
        assert result is not None
        assert result.name == "test_ledger.py"

    def test_returns_none_when_no_test(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when no test file exists."""
        monkeypatch.chdir(tmp_path)

        result = find_test_file(Path("src/world/missing.py"))
        assert result is None


class TestSuggestTestLocation:
    """Tests for suggest_test_location function."""

    def test_scripts_go_to_unit(self) -> None:
        """Scripts should have unit tests."""
        result = suggest_test_location(Path("scripts/check_foo.py"))
        assert result == "tests/unit/test_check_foo.py"

    def test_world_goes_to_unit(self) -> None:
        """World module goes to unit tests."""
        result = suggest_test_location(Path("src/world/ledger.py"))
        assert result == "tests/unit/test_ledger.py"

    def test_simulation_goes_to_integration(self) -> None:
        """Simulation module goes to integration tests."""
        result = suggest_test_location(Path("src/simulation/runner.py"))
        assert result == "tests/integration/test_runner.py"
