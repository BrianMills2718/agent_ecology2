"""Tests for scripts/parse_plan.py."""

import json
import tempfile
from pathlib import Path

import pytest

# Import functions from parse_plan module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from parse_plan import (
    parse_files_affected,
    parse_references_reviewed,
    check_file_in_scope,
    get_plan_number_from_branch,
)


class TestParseFilesAffected:
    """Tests for parse_files_affected function."""

    def test_basic_parsing(self):
        """Parse basic Files Affected section."""
        content = """
## Files Affected

- src/world/executor.py (modify)
- src/world/rate_limiter.py (create)
- tests/test_rate_limiter.py (create)
"""
        result = parse_files_affected(content)

        assert len(result) == 3
        assert result[0] == {"path": "src/world/executor.py", "action": "modify"}
        assert result[1] == {"path": "src/world/rate_limiter.py", "action": "create"}
        assert result[2] == {"path": "tests/test_rate_limiter.py", "action": "create"}

    def test_no_action_defaults_to_modify(self):
        """Files without action default to modify."""
        content = """
## Files Affected

- src/world/executor.py
"""
        result = parse_files_affected(content)

        assert len(result) == 1
        assert result[0] == {"path": "src/world/executor.py", "action": "modify"}

    def test_alternate_header_format(self):
        """Parse 'File Affected' (singular) section."""
        content = """
## File Affected

- src/test.py (modify)
"""
        result = parse_files_affected(content)

        assert len(result) == 1
        assert result[0]["path"] == "src/test.py"

    def test_empty_section(self):
        """Empty Files Affected returns empty list."""
        content = """
## Files Affected

## Other Section
"""
        result = parse_files_affected(content)
        assert result == []

    def test_no_section(self):
        """No Files Affected section returns empty list."""
        content = """
# Some Plan

## Other Section
- stuff
"""
        result = parse_files_affected(content)
        assert result == []

    def test_asterisk_bullets(self):
        """Parse files with asterisk bullets."""
        content = """
## Files Affected

* src/test1.py (modify)
* src/test2.py (create)
"""
        result = parse_files_affected(content)

        assert len(result) == 2
        assert result[0]["path"] == "src/test1.py"

    def test_skips_comments_and_empty(self):
        """Skip comment lines and empty lines."""
        content = """
## Files Affected

- src/real.py (modify)
# This is a comment
- src/another.py (create)

"""
        result = parse_files_affected(content)

        assert len(result) == 2
        assert result[0]["path"] == "src/real.py"
        assert result[1]["path"] == "src/another.py"


class TestParseReferencesReviewed:
    """Tests for parse_references_reviewed function."""

    def test_basic_parsing(self):
        """Parse basic References Reviewed section."""
        content = """
## References Reviewed

- src/world/executor.py:45-89 - existing action handling
- docs/architecture/current/actions.md - action design
"""
        result = parse_references_reviewed(content)

        assert len(result) == 2
        assert result[0]["path"] == "src/world/executor.py"
        assert result[0]["lines"] == {"start": 45, "end": 89}
        assert result[0]["description"] == "existing action handling"
        assert result[1]["path"] == "docs/architecture/current/actions.md"
        assert result[1]["description"] == "action design"

    def test_single_line_reference(self):
        """Parse single line reference (start only)."""
        content = """
## References Reviewed

- src/test.py:100 - specific function
"""
        result = parse_references_reviewed(content)

        assert len(result) == 1
        assert result[0]["lines"] == {"start": 100, "end": 100}

    def test_no_lines_or_description(self):
        """Parse reference with just path."""
        content = """
## References Reviewed

- src/test.py
"""
        result = parse_references_reviewed(content)

        assert len(result) == 1
        assert result[0]["path"] == "src/test.py"
        assert "lines" not in result[0]
        assert "description" not in result[0] or result[0]["description"] == ""

    def test_empty_section(self):
        """Empty section returns empty list."""
        content = """
## References Reviewed

## Other Section
"""
        result = parse_references_reviewed(content)
        assert result == []


class TestCheckFileInScope:
    """Tests for check_file_in_scope function."""

    def test_exact_match(self):
        """File exactly matches declared path."""
        files_affected = [
            {"path": "src/world/ledger.py", "action": "modify"},
        ]

        in_scope, reason = check_file_in_scope("src/world/ledger.py", files_affected)

        assert in_scope is True
        assert "modify" in reason.lower()

    def test_not_in_scope(self):
        """File not in declared scope."""
        files_affected = [
            {"path": "src/world/ledger.py", "action": "modify"},
        ]

        in_scope, reason = check_file_in_scope("src/world/executor.py", files_affected)

        assert in_scope is False
        assert "not in" in reason.lower()

    def test_directory_prefix_match(self):
        """File under declared directory is in scope."""
        files_affected = [
            {"path": "src/world", "action": "modify"},
        ]

        in_scope, reason = check_file_in_scope("src/world/ledger.py", files_affected)

        assert in_scope is True
        assert "directory" in reason.lower()

    def test_empty_files_affected(self):
        """Empty files affected list means nothing in scope."""
        in_scope, reason = check_file_in_scope("src/test.py", [])

        assert in_scope is False


class TestGetPlanNumberFromBranch:
    """Tests for get_plan_number_from_branch function."""

    def test_standard_format(self):
        """Parse plan-NN-description format."""
        assert get_plan_number_from_branch("plan-15-feature") == 15
        assert get_plan_number_from_branch("plan-01-rate-allocation") == 1
        assert get_plan_number_from_branch("plan-123-long-name-here") == 123

    def test_no_plan_prefix(self):
        """Branch without plan prefix returns None."""
        assert get_plan_number_from_branch("main") is None
        assert get_plan_number_from_branch("feature/something") is None
        assert get_plan_number_from_branch("work/test") is None

    def test_invalid_format(self):
        """Invalid plan format returns None."""
        assert get_plan_number_from_branch("plan-abc-feature") is None
        assert get_plan_number_from_branch("plans-15-feature") is None
