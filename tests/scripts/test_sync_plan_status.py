"""Tests for sync_plan_status.py - Plan #178."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from sync_plan_status import (
    add_missing_plans_to_index,
    load_meta_config,
    parse_plan_status,
)


class TestLoadMetaConfig:
    """Tests for load_meta_config function."""

    def test_returns_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        """Should return defaults when meta-process.yaml doesn't exist."""
        with patch("sync_plan_status.META_CONFIG_FILE", tmp_path / "nonexistent.yaml"):
            config = load_meta_config()

        assert config["enforcement"]["plan_index_auto_add"] is True
        assert config["enforcement"]["strict_doc_coupling"] is True
        assert config["enforcement"]["show_strictness_warning"] is True

    def test_reads_config_from_file(self, tmp_path: Path) -> None:
        """Should read settings from meta-process.yaml."""
        config_file = tmp_path / "meta-process.yaml"
        config_file.write_text("""
enforcement:
  plan_index_auto_add: false
  strict_doc_coupling: false
""")

        with patch("sync_plan_status.META_CONFIG_FILE", config_file):
            config = load_meta_config()

        assert config["enforcement"]["plan_index_auto_add"] is False
        assert config["enforcement"]["strict_doc_coupling"] is False
        # Default should still apply for unspecified keys
        assert config["enforcement"]["show_strictness_warning"] is True


class TestAddMissingPlansToIndex:
    """Tests for add_missing_plans_to_index function."""

    def test_adds_missing_plan_to_index(self, tmp_path: Path) -> None:
        """Should add a plan that exists as file but not in index."""
        # Create plan directory
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)

        # Create a plan file
        plan_file = plans_dir / "99_test_plan.md"
        plan_file.write_text("""# Plan 99: Test Plan

**Status:** 📋 Planned
**Priority:** High

---

## Gap

Test gap description.

## Plan

Test plan content.
""")

        # Create index file without plan 99
        index_content = """# Implementation Plans

## Gap Summary

| # | Gap | Priority | Status | Blocks |
|---|-----|----------|--------|--------|
| 1 | [Rate Allocation](01_rate_allocation.md) | **High** | ✅ Complete | - |
| 2 | [Other Plan](02_other.md) | Medium | 📋 Planned | - |
"""

        index_file = plans_dir / "CLAUDE.md"
        index_file.write_text(index_content)

        # Parse plan status
        plan_status = parse_plan_status(plan_file)
        plan_statuses = {plan_status["number"]: plan_status}

        # Patch INDEX_FILE to use our temp file
        with patch("sync_plan_status.INDEX_FILE", index_file):
            new_content, added = add_missing_plans_to_index(index_content, plan_statuses)

        assert added == 1
        assert "| 99 |" in new_content
        assert "[Test Plan](99_test_plan.md)" in new_content
        assert "📋 Planned" in new_content

    def test_returns_zero_when_all_plans_present(self, tmp_path: Path) -> None:
        """Should return 0 added when all plans already in index."""
        plans_dir = tmp_path / "docs" / "plans"
        plans_dir.mkdir(parents=True)

        # Create a plan file
        plan_file = plans_dir / "1_test.md"
        plan_file.write_text("""# Plan 1: Test

**Status:** ✅ Complete
""")

        # Create index with plan 1 already present
        index_content = """# Implementation Plans

## Gap Summary

| # | Gap | Priority | Status | Blocks |
|---|-----|----------|--------|--------|
| 1 | [Test](01_test.md) | **High** | ✅ Complete | - |
"""

        index_file = plans_dir / "CLAUDE.md"
        index_file.write_text(index_content)

        plan_status = parse_plan_status(plan_file)
        plan_statuses = {plan_status["number"]: plan_status}

        with patch("sync_plan_status.INDEX_FILE", index_file):
            new_content, added = add_missing_plans_to_index(index_content, plan_statuses)

        assert added == 0
        # Content should be unchanged
        assert new_content == index_content
