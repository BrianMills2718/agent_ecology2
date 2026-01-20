"""Tests for session identity coordination (Plan #134).

Tests session-based ownership verification for multi-CC coordination.
"""

import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Import functions from check_claims
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from check_claims import (
    get_session_id,
    get_or_create_session,
    is_session_stale,
    update_session_heartbeat,
    add_claim,
    release_claim,
    load_yaml,
    save_yaml,
    STALENESS_MINUTES,
)


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Create a temporary sessions directory."""
    sessions_dir = tmp_path / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True)
    return sessions_dir


@pytest.fixture
def temp_claims_file(tmp_path):
    """Create a temporary claims file."""
    claims_file = tmp_path / ".claude" / "active-work.yaml"
    claims_file.parent.mkdir(parents=True, exist_ok=True)
    claims_file.write_text("claims: []\ncompleted: []\n")
    return claims_file


class TestSessionIdGeneration:
    """Test session ID generation."""

    def test_session_id_generated(self, temp_sessions_dir, monkeypatch):
        """Session ID is created on first call."""
        # Patch the sessions directory
        monkeypatch.setattr(
            "check_claims.SESSIONS_DIR",
            temp_sessions_dir
        )

        session = get_or_create_session()

        assert "session_id" in session
        assert len(session["session_id"]) == 36  # UUID format
        assert session["hostname"]
        assert session["pid"] == os.getpid()
        assert "started_at" in session
        assert "last_activity" in session

    def test_session_id_persists(self, temp_sessions_dir, monkeypatch):
        """Same session ID returned on subsequent calls."""
        monkeypatch.setattr(
            "check_claims.SESSIONS_DIR",
            temp_sessions_dir
        )

        session1 = get_or_create_session()
        session2 = get_or_create_session()

        assert session1["session_id"] == session2["session_id"]

    def test_get_session_id_returns_string(self, temp_sessions_dir, monkeypatch):
        """get_session_id returns a string UUID."""
        monkeypatch.setattr(
            "check_claims.SESSIONS_DIR",
            temp_sessions_dir
        )

        session_id = get_session_id()

        assert isinstance(session_id, str)
        # Verify it's a valid UUID
        uuid.UUID(session_id)


class TestClaimRecordsSession:
    """Test that claims include session_id."""

    def test_claim_records_session(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Claims include session_id when created."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        data = {"claims": [], "completed": []}
        session_id = get_session_id()

        success = add_claim(
            data,
            cc_id="test-branch",
            plan=999,
            feature=None,
            task="Test task",
        )

        assert success
        assert len(data["claims"]) == 1
        assert data["claims"][0]["session_id"] == session_id

    def test_claim_uses_provided_session(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Claims use provided session_id when given."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        data = {"claims": [], "completed": []}
        custom_session = str(uuid.uuid4())

        success = add_claim(
            data,
            cc_id="test-branch",
            plan=999,
            feature=None,
            task="Test task",
            session_id=custom_session,
        )

        assert success
        assert data["claims"][0]["session_id"] == custom_session


class TestOwnershipVerification:
    """Test ownership verification on release."""

    def test_release_blocked_wrong_session(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Cannot release claims owned by another session."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        # Create a claim with a different session
        other_session = str(uuid.uuid4())
        data = {
            "claims": [{
                "cc_id": "other-branch",
                "task": "Other task",
                "plan": 888,
                "session_id": other_session,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }],
            "completed": [],
        }

        # Create a session file for the other session to make it "active"
        other_session_file = temp_sessions_dir / f"other-host-12345.session"
        other_session_file.write_text(yaml.dump({
            "session_id": other_session,
            "hostname": "other-host",
            "pid": 12345,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }))

        # Try to release from this session
        my_session = get_session_id()
        success = release_claim(
            data,
            cc_id="other-branch",
            session_id=my_session,
        )

        assert not success
        assert len(data["claims"]) == 1  # Claim still exists

    def test_release_allowed_same_session(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Can release claims owned by this session."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        my_session = get_session_id()
        data = {
            "claims": [{
                "cc_id": "my-branch",
                "task": "My task",
                "plan": 777,
                "session_id": my_session,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }],
            "completed": [],
        }

        success = release_claim(
            data,
            cc_id="my-branch",
            session_id=my_session,
        )

        assert success
        assert len(data["claims"]) == 0

    def test_release_allowed_with_force(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Can force release claims owned by another session."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        other_session = str(uuid.uuid4())
        data = {
            "claims": [{
                "cc_id": "other-branch",
                "task": "Other task",
                "plan": 666,
                "session_id": other_session,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }],
            "completed": [],
        }

        # Create active session file for other session
        other_session_file = temp_sessions_dir / f"other-host-99999.session"
        other_session_file.write_text(yaml.dump({
            "session_id": other_session,
            "hostname": "other-host",
            "pid": 99999,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }))

        my_session = get_session_id()
        success = release_claim(
            data,
            cc_id="other-branch",
            session_id=my_session,
            force=True,
        )

        assert success
        assert len(data["claims"]) == 0


class TestHeartbeat:
    """Test heartbeat mechanism."""

    def test_heartbeat_updates_timestamp(self, temp_sessions_dir, monkeypatch):
        """Heartbeat updates last_activity timestamp."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)

        # Create initial session
        session1 = get_or_create_session()
        original_activity = session1["last_activity"]

        # Wait a tiny bit and update heartbeat
        import time
        time.sleep(0.01)

        session2 = update_session_heartbeat(working_on="Plan #134")

        assert session2["session_id"] == session1["session_id"]
        assert session2["last_activity"] >= original_activity
        assert session2["working_on"] == "Plan #134"


class TestStalenessDetection:
    """Test staleness detection."""

    def test_stale_session_detection(self, temp_sessions_dir, monkeypatch):
        """Sessions are detected as stale after inactivity threshold."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)

        # Create a session with old last_activity
        old_session_id = str(uuid.uuid4())
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=STALENESS_MINUTES + 5)).isoformat()

        session_file = temp_sessions_dir / "old-host-11111.session"
        session_file.write_text(yaml.dump({
            "session_id": old_session_id,
            "hostname": "old-host",
            "pid": 11111,
            "started_at": old_time,
            "last_activity": old_time,
        }))

        is_stale, session = is_session_stale(old_session_id)

        assert is_stale
        assert session is not None
        assert session["session_id"] == old_session_id

    def test_active_session_not_stale(self, temp_sessions_dir, monkeypatch):
        """Recent sessions are not detected as stale."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)

        # Create a session with recent last_activity
        recent_session_id = str(uuid.uuid4())
        recent_time = datetime.now(timezone.utc).isoformat()

        session_file = temp_sessions_dir / "recent-host-22222.session"
        session_file.write_text(yaml.dump({
            "session_id": recent_session_id,
            "hostname": "recent-host",
            "pid": 22222,
            "started_at": recent_time,
            "last_activity": recent_time,
        }))

        is_stale, session = is_session_stale(recent_session_id)

        assert not is_stale
        assert session is not None

    def test_missing_session_is_stale(self, temp_sessions_dir, monkeypatch):
        """Non-existent sessions are considered stale."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)

        nonexistent_id = str(uuid.uuid4())
        is_stale, session = is_session_stale(nonexistent_id)

        assert is_stale
        assert session is None


class TestOrphanTakeover:
    """Test taking over claims from stale sessions."""

    def test_orphan_takeover(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Can take over claims from stale sessions."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        # Create a claim from a stale session
        stale_session_id = str(uuid.uuid4())
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=STALENESS_MINUTES + 5)).isoformat()

        # Create stale session file
        session_file = temp_sessions_dir / "stale-host-33333.session"
        session_file.write_text(yaml.dump({
            "session_id": stale_session_id,
            "hostname": "stale-host",
            "pid": 33333,
            "started_at": old_time,
            "last_activity": old_time,
        }))

        data = {
            "claims": [{
                "cc_id": "stale-branch",
                "task": "Stale task",
                "plan": 555,
                "session_id": stale_session_id,
                "claimed_at": old_time,
            }],
            "completed": [],
        }

        # Get current session
        my_session = get_session_id()

        # Should be able to release (take over) the stale claim
        success = release_claim(
            data,
            cc_id="stale-branch",
            session_id=my_session,
        )

        assert success
        assert len(data["claims"]) == 0


class TestLegacyCompatibility:
    """Test backwards compatibility with claims without session_id."""

    def test_legacy_claim_without_session(self, temp_sessions_dir, temp_claims_file, monkeypatch):
        """Claims without session_id are handled gracefully."""
        monkeypatch.setattr("check_claims.SESSIONS_DIR", temp_sessions_dir)
        monkeypatch.setattr("check_claims.YAML_PATH", temp_claims_file)

        # Legacy claim without session_id
        data = {
            "claims": [{
                "cc_id": "legacy-branch",
                "task": "Legacy task",
                "plan": 444,
                # No session_id
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }],
            "completed": [],
        }

        my_session = get_session_id()

        # Should be able to release legacy claims
        success = release_claim(
            data,
            cc_id="legacy-branch",
            session_id=my_session,
        )

        assert success
        assert len(data["claims"]) == 0
