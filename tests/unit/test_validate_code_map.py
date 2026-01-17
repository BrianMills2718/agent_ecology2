"""Tests for scripts/validate_code_map.py."""

import tempfile
from pathlib import Path

import pytest

# Import functions from validate_code_map module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from validate_code_map import (
    parse_code_map_table,
    validate_path,
    find_claude_md_files,
)


class TestParseCodeMapTable:
    """Tests for parse_code_map_table function."""

    def test_basic_table(self):
        """Parse basic Code Map table."""
        content = """
## Code Map

| Domain | Location | Purpose |
|--------|----------|---------|
| Core | src/core/ | Core logic |
| World | src/world/ | World state |
"""
        result = parse_code_map_table(content)

        assert len(result) == 2
        assert result[0]["_path"] == "src/core/"
        assert result[0]["domain"] == "Core"
        assert result[1]["_path"] == "src/world/"

    def test_file_column_format(self):
        """Parse table with 'File' column instead of 'Location'."""
        content = """
## Code Map (src/)

| File | Key Elements | Purpose |
|------|--------------|---------|
| world/ledger.py | Ledger class | Balance management |
| world/executor.py | Executor | Action execution |
"""
        result = parse_code_map_table(content)

        assert len(result) == 2
        assert result[0]["_path"] == "world/ledger.py"
        assert result[1]["_path"] == "world/executor.py"

    def test_path_column_format(self):
        """Parse table with 'Path' column."""
        content = """
## Code Map

| Path | Description |
|------|-------------|
| src/config.py | Config helpers |
"""
        result = parse_code_map_table(content)

        assert len(result) == 1
        assert result[0]["_path"] == "src/config.py"

    def test_backtick_paths(self):
        """Strip backticks from paths."""
        content = """
## Code Map

| Location | Purpose |
|----------|---------|
| `src/test.py` | Testing |
"""
        result = parse_code_map_table(content)

        assert len(result) == 1
        assert result[0]["_path"] == "src/test.py"

    def test_no_code_map_section(self):
        """No Code Map section returns empty list."""
        content = """
# CLAUDE.md

## Other Section

Some content here.
"""
        result = parse_code_map_table(content)
        assert result == []

    def test_multiple_code_map_sections(self):
        """Parse multiple Code Map sections."""
        content = """
## Code Map (src/)

| File | Purpose |
|------|---------|
| world/ledger.py | Ledger |

## Code Map (tests/)

| File | Purpose |
|------|---------|
| test_ledger.py | Tests |
"""
        result = parse_code_map_table(content)

        assert len(result) == 2
        paths = [r["_path"] for r in result]
        assert "world/ledger.py" in paths
        assert "test_ledger.py" in paths

    def test_empty_table(self):
        """Empty table returns empty list."""
        content = """
## Code Map

| Location | Purpose |
|----------|---------|
"""
        result = parse_code_map_table(content)
        assert result == []


class TestValidatePath:
    """Tests for validate_path function."""

    def test_existing_file(self):
        """Validate path that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            test_file = root / "src" / "test.py"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            exists, resolved = validate_path("src/test.py", root)

            assert exists is True
            assert "test.py" in resolved

    def test_nonexistent_file(self):
        """Validate path that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            exists, resolved = validate_path("nonexistent.py", root)

            assert exists is False
            assert resolved == "nonexistent.py"

    def test_with_base_dir(self):
        """Validate path relative to base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            test_file = root / "src" / "world" / "ledger.py"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            base_dir = root / "src"
            exists, resolved = validate_path("world/ledger.py", root, base_dir)

            assert exists is True

    def test_leading_slash_stripped(self):
        """Leading slash is stripped from path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            test_file = root / "src" / "test.py"
            test_file.parent.mkdir(parents=True)
            test_file.touch()

            exists, resolved = validate_path("/src/test.py", root)

            assert exists is True


class TestFindClaudeMdFiles:
    """Tests for find_claude_md_files function."""

    def test_finds_claude_md(self):
        """Find CLAUDE.md files in directory tree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create some CLAUDE.md files
            (root / "CLAUDE.md").touch()
            (root / "src").mkdir()
            (root / "src" / "CLAUDE.md").touch()
            (root / "docs").mkdir()
            (root / "docs" / "CLAUDE.md").touch()

            result = find_claude_md_files(root)

            assert len(result) == 3

    def test_no_claude_md(self):
        """No CLAUDE.md files returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            result = find_claude_md_files(root)

            assert result == []
