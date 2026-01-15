"""Tests for scripts/check_adr_requirement.py.

Plan #43: Comprehensive Meta-Enforcement - Phase 2 CI Checks.
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_adr_requirement import (
    CORE_FILES,
    check_adr_requirement,
    has_adr_reference,
    requires_adr,
)


@pytest.mark.plans([43])
class TestADRRequirement:
    """Tests for ADR requirement checking."""

    def test_requires_adr_for_core(self) -> None:
        """Changes to core files should require ADR reference."""
        # Core files should be flagged
        changed = ["src/world/ledger.py", "README.md"]
        core_changes = requires_adr(changed)
        assert "src/world/ledger.py" in core_changes

    def test_no_adr_for_non_core(self) -> None:
        """Changes to non-core files should not require ADR."""
        changed = ["src/agents/loader.py", "tests/unit/test_foo.py"]
        core_changes = requires_adr(changed)
        assert len(core_changes) == 0

    def test_all_core_files_detected(self) -> None:
        """All defined core files should be detected."""
        for core_file in CORE_FILES:
            changed = [core_file]
            core_changes = requires_adr(changed)
            assert core_file in core_changes, f"{core_file} should require ADR"

    def test_has_adr_reference_variations(self) -> None:
        """Various ADR reference formats should be recognized."""
        # Standard format
        assert has_adr_reference(["Implements ADR-0001"])
        # Lowercase
        assert has_adr_reference(["implements adr-0001"])
        # With underscore
        assert has_adr_reference(["Per ADR_0001"])
        # In body
        assert has_adr_reference(["Short title\n\nThis implements ADR-0001."])
        # No reference
        assert not has_adr_reference(["Just a commit message"])

    def test_check_passes_when_adr_referenced(self) -> None:
        """Check should pass when core files changed AND ADR referenced."""
        changed = ["src/world/ledger.py"]
        messages = ["[Plan #43] Update ledger per ADR-0001"]

        passes, _ = check_adr_requirement(changed, messages)
        assert passes is True

    def test_check_fails_when_adr_missing(self) -> None:
        """Check should fail when core files changed but no ADR referenced."""
        changed = ["src/world/ledger.py"]
        messages = ["[Plan #43] Update ledger without ADR"]

        passes, message = check_adr_requirement(changed, messages)
        assert passes is False
        assert "ADR" in message

    def test_check_passes_for_non_core_changes(self) -> None:
        """Check should pass for non-core changes regardless of ADR."""
        changed = ["src/agents/loader.py"]
        messages = ["[Plan #43] Update agent loader"]

        passes, _ = check_adr_requirement(changed, messages)
        assert passes is True

    def test_check_passes_for_no_changes(self) -> None:
        """Check should pass when no files changed."""
        changed: list[str] = []
        messages: list[str] = []

        passes, _ = check_adr_requirement(changed, messages)
        assert passes is True
