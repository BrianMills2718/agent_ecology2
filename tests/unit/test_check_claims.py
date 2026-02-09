"""Tests for scripts/check_claims.py — claim management for worktree coordination."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def cc():
    """Import check_claims module."""
    import scripts.check_claims as mod
    return mod


@pytest.fixture
def tmp_claims(tmp_path, monkeypatch):
    """Set up temporary paths for claims testing."""
    import scripts.check_claims as mod

    yaml_path = tmp_path / ".claude" / "active-work.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml.dump({"claims": [], "completed": []}))

    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    sessions_dir = tmp_path / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(mod, "_MAIN_ROOT", tmp_path)
    monkeypatch.setattr(mod, "YAML_PATH", yaml_path)
    monkeypatch.setattr(mod, "PLANS_DIR", plans_dir)
    monkeypatch.setattr(mod, "SESSIONS_DIR", sessions_dir)

    return {
        "root": tmp_path,
        "yaml_path": yaml_path,
        "plans_dir": plans_dir,
        "sessions_dir": sessions_dir,
    }


class TestParseTimestamp:
    def test_iso_z(self, cc):
        result = cc.parse_timestamp("2026-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.hour == 10

    def test_iso_no_tz(self, cc):
        result = cc.parse_timestamp("2026-01-15T10:30:00")
        assert result is not None
        assert result.year == 2026

    def test_iso_minutes_only(self, cc):
        result = cc.parse_timestamp("2026-01-15T10:30")
        assert result is not None

    def test_date_only(self, cc):
        result = cc.parse_timestamp("2026-01-15")
        assert result is not None
        assert result.day == 15

    def test_empty_string(self, cc):
        assert cc.parse_timestamp("") is None

    def test_invalid_string(self, cc):
        assert cc.parse_timestamp("not a date") is None

    def test_none_string(self, cc):
        assert cc.parse_timestamp("") is None


class TestScopeConflict:
    def test_no_conflicts_empty(self, cc):
        conflicts = cc.check_scope_conflict(new_plan=42, new_feature=None, existing_claims=[])
        assert conflicts == []

    def test_plan_conflict(self, cc):
        existing = [{"plan": 42, "feature": None, "cc_id": "other"}]
        conflicts = cc.check_scope_conflict(new_plan=42, new_feature=None, existing_claims=existing)
        assert len(conflicts) == 1

    def test_no_plan_conflict_different(self, cc):
        existing = [{"plan": 99, "feature": None, "cc_id": "other"}]
        conflicts = cc.check_scope_conflict(new_plan=42, new_feature=None, existing_claims=existing)
        assert conflicts == []

    def test_feature_conflict(self, cc):
        existing = [{"plan": None, "feature": "ledger", "cc_id": "other"}]
        conflicts = cc.check_scope_conflict(new_plan=None, new_feature="ledger", existing_claims=existing)
        assert len(conflicts) == 1

    def test_shared_feature_never_conflicts(self, cc):
        existing = [{"plan": None, "feature": "shared", "cc_id": "other"}]
        conflicts = cc.check_scope_conflict(new_plan=None, new_feature="shared", existing_claims=existing)
        assert conflicts == []

    def test_shared_feature_existing_never_conflicts(self, cc):
        """Even if existing claim is on shared, no conflict."""
        existing = [{"plan": None, "feature": "shared", "cc_id": "other"}]
        conflicts = cc.check_scope_conflict(new_plan=None, new_feature="ledger", existing_claims=existing)
        assert conflicts == []


class TestCheckStaleClaims:
    def test_no_stale(self, cc):
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        claims = [{"claimed_at": now, "cc_id": "test"}]
        stale = cc.check_stale_claims(claims, hours=4)
        assert stale == []

    def test_stale_claim(self, cc):
        old = (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        claims = [{"claimed_at": old, "cc_id": "test"}]
        stale = cc.check_stale_claims(claims, hours=4)
        assert len(stale) == 1
        assert "age_hours" in stale[0]

    def test_missing_timestamp(self, cc):
        claims = [{"cc_id": "test"}]
        stale = cc.check_stale_claims(claims, hours=4)
        assert stale == []

    def test_mixed_fresh_and_stale(self, cc):
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        old = (datetime.now() - timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        claims = [
            {"claimed_at": now, "cc_id": "fresh"},
            {"claimed_at": old, "cc_id": "stale"},
        ]
        stale = cc.check_stale_claims(claims, hours=4)
        assert len(stale) == 1
        assert stale[0]["cc_id"] == "stale"


class TestVerifyHasClaim:
    def test_has_claim(self, cc):
        data = {"claims": [{"cc_id": "my-branch", "task": "Fix bug"}]}
        has, msg = cc.verify_has_claim(data, "my-branch")
        assert has is True
        assert "Fix bug" in msg

    def test_no_claim(self, cc):
        data = {"claims": [{"cc_id": "other-branch", "task": "Other"}]}
        has, msg = cc.verify_has_claim(data, "my-branch")
        assert has is False

    def test_main_branch_no_claim(self, cc):
        data = {"claims": []}
        has, msg = cc.verify_has_claim(data, "main")
        assert has is False
        assert "main" in msg.lower()


class TestCleanupCompleted:
    def test_removes_old_entries(self, cc, tmp_claims):
        old_time = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = {
            "claims": [],
            "completed": [
                {"cc_id": "old", "completed_at": old_time},
            ],
        }
        removed = cc.cleanup_old_completed(data, hours=24)
        assert removed == 1
        assert len(data["completed"]) == 0

    def test_keeps_recent_entries(self, cc, tmp_claims):
        recent_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = {
            "claims": [],
            "completed": [
                {"cc_id": "recent", "completed_at": recent_time},
            ],
        }
        removed = cc.cleanup_old_completed(data, hours=24)
        assert removed == 0
        assert len(data["completed"]) == 1


class TestYamlPersistence:
    def test_save_and_load(self, cc, tmp_claims):
        data = {
            "claims": [{"cc_id": "test", "task": "Work", "plan": 42}],
            "completed": [],
        }
        cc.save_yaml(data)
        loaded = cc.load_yaml()
        assert len(loaded["claims"]) == 1
        assert loaded["claims"][0]["cc_id"] == "test"

    def test_load_empty(self, cc, tmp_claims):
        tmp_claims["yaml_path"].write_text("")
        loaded = cc.load_yaml()
        assert loaded["claims"] == []
        assert loaded["completed"] == []

    def test_load_missing_file(self, cc, tmp_claims):
        tmp_claims["yaml_path"].unlink()
        loaded = cc.load_yaml()
        assert loaded["claims"] == []
        assert loaded["completed"] == []


class TestGetPlanStatus:
    def test_complete_plan(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** \u2705 Complete\n**Blocked By:** \u2014\n")
        status, blockers = cc.get_plan_status(42)
        assert status == "complete"
        assert blockers == []

    def test_in_progress_plan(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** —\n")
        status, blockers = cc.get_plan_status(42)
        assert status == "in_progress"

    def test_plan_with_blockers(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** #10, #20\n")
        status, blockers = cc.get_plan_status(42)
        assert status == "in_progress"
        assert blockers == [10, 20]

    def test_missing_plan(self, cc, tmp_claims):
        status, blockers = cc.get_plan_status(999)
        assert status == "unknown"
        assert blockers == []


class TestCheckPlanDependencies:
    def test_no_blockers(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** —\n")
        ok, issues = cc.check_plan_dependencies(42)
        assert ok is True
        assert issues == []

    def test_blocker_complete(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** #10\n")
        blocker_file = tmp_claims["plans_dir"] / "10_blocker.md"
        blocker_file.write_text("# Blocker\n\n**Status:** \u2705 Complete\n**Blocked By:** \u2014\n")
        ok, issues = cc.check_plan_dependencies(42)
        assert ok is True

    def test_blocker_incomplete(self, cc, tmp_claims):
        plan_file = tmp_claims["plans_dir"] / "42_test_plan.md"
        plan_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** #10\n")
        blocker_file = tmp_claims["plans_dir"] / "10_blocker.md"
        blocker_file.write_text("# Plan\n\n**Status:** 🚧 In Progress\n**Blocked By:** —\n")
        ok, issues = cc.check_plan_dependencies(42)
        assert ok is False
        assert len(issues) == 1
        assert "Plan #10" in issues[0]
