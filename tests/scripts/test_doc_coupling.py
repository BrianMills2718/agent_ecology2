"""Tests for check_doc_coupling.py - Plan #178."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_doc_coupling import (
    check_couplings,
    load_meta_config,
)


class TestLoadMetaConfig:
    """Tests for load_meta_config function in check_doc_coupling."""

    def test_returns_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        """Should return defaults when meta-process.yaml doesn't exist."""
        with patch("check_doc_coupling.META_CONFIG_FILE", tmp_path / "nonexistent.yaml"):
            config = load_meta_config()

        assert config["enforcement"]["strict_doc_coupling"] is True
        assert config["enforcement"]["show_strictness_warning"] is True

    def test_reads_config_from_file(self, tmp_path: Path) -> None:
        """Should read settings from meta-process.yaml."""
        config_file = tmp_path / "meta-process.yaml"
        config_file.write_text("""
enforcement:
  strict_doc_coupling: false
  show_strictness_warning: false
""")

        with patch("check_doc_coupling.META_CONFIG_FILE", config_file):
            config = load_meta_config()

        assert config["enforcement"]["strict_doc_coupling"] is False
        assert config["enforcement"]["show_strictness_warning"] is False


class TestCheckCouplings:
    """Tests for check_couplings function with force_strict parameter."""

    def test_soft_coupling_is_warning_when_not_forced(self) -> None:
        """Should put soft couplings in warnings when force_strict is False."""
        couplings = [
            {
                "sources": ["src/test.py"],
                "docs": ["docs/test.md"],
                "description": "Test coupling",
                "soft": True,
            }
        ]
        changed_files = {"src/test.py"}

        strict, soft = check_couplings(changed_files, couplings, force_strict=False)

        assert len(strict) == 0
        assert len(soft) == 1
        assert soft[0]["description"] == "Test coupling"

    def test_soft_coupling_is_strict_when_forced(self) -> None:
        """Should put soft couplings in strict violations when force_strict is True."""
        couplings = [
            {
                "sources": ["src/test.py"],
                "docs": ["docs/test.md"],
                "description": "Test coupling",
                "soft": True,
            }
        ]
        changed_files = {"src/test.py"}

        strict, soft = check_couplings(changed_files, couplings, force_strict=True)

        assert len(strict) == 1
        assert len(soft) == 0
        assert strict[0]["description"] == "Test coupling"

    def test_strict_coupling_always_strict(self) -> None:
        """Should always put non-soft couplings in strict violations."""
        couplings = [
            {
                "sources": ["src/test.py"],
                "docs": ["docs/test.md"],
                "description": "Test coupling",
                # No soft: True
            }
        ]
        changed_files = {"src/test.py"}

        strict, soft = check_couplings(changed_files, couplings, force_strict=False)

        assert len(strict) == 1
        assert len(soft) == 0

        # Also when force_strict is True
        strict, soft = check_couplings(changed_files, couplings, force_strict=True)

        assert len(strict) == 1
        assert len(soft) == 0

    def test_no_violation_when_doc_updated(self) -> None:
        """Should not report violation when coupled doc is also changed."""
        couplings = [
            {
                "sources": ["src/test.py"],
                "docs": ["docs/test.md"],
                "description": "Test coupling",
            }
        ]
        changed_files = {"src/test.py", "docs/test.md"}

        strict, soft = check_couplings(changed_files, couplings, force_strict=True)

        assert len(strict) == 0
        assert len(soft) == 0
