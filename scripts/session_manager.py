#!/usr/bin/env python3
"""Session identity management for multi-CC coordination.

Each Claude Code session gets a unique identity (UUID) that:
- Distinguishes concurrent sessions in the same directory
- Enables ownership verification on claim operations
- Supports automatic staleness detection

Session files are stored in .claude/sessions/<hostname>-<pid>.session

Usage:
    # Get or create session ID for current process
    python scripts/session_manager.py --get

    # List active sessions
    python scripts/session_manager.py --list

    # Check if a session is stale (no activity for N minutes)
    python scripts/session_manager.py --check-stale <session_id>

    # Update heartbeat for current session
    python scripts/session_manager.py --heartbeat

    # Clean up stale sessions
    python scripts/session_manager.py --cleanup
"""

import argparse
import os
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


# Configuration
STALENESS_MINUTES = 30  # Sessions with no activity for this long are considered stale
SESSION_DIR_NAME = "sessions"


def get_main_repo_root() -> Path:
    """Get the main repo root (not worktree).

    For worktrees, returns the main repository's root directory.
    This ensures sessions are stored in a shared location.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_dir = Path(result.stdout.strip())
        # git-common-dir returns the .git directory, so parent is repo root
        return git_dir.parent
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def get_sessions_dir() -> Path:
    """Get the sessions directory path."""
    return get_main_repo_root() / ".claude" / SESSION_DIR_NAME


def get_session_file_name() -> str:
    """Generate session file name based on hostname and PID."""
    hostname = socket.gethostname()
    pid = os.getpid()
    return f"{hostname}-{pid}.session"


def get_session_file_path() -> Path:
    """Get the full path to this process's session file."""
    return get_sessions_dir() / get_session_file_name()


def load_session(session_file: Path) -> dict[str, Any] | None:
    """Load a session from file."""
    if not session_file.exists():
        return None
    try:
        with open(session_file) as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None


def save_session(session_file: Path, data: dict[str, Any]) -> None:
    """Save session data to file."""
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with open(session_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def get_or_create_session() -> dict[str, Any]:
    """Get existing session or create a new one.

    Returns the session data dict with:
    - session_id: UUID string
    - hostname: Machine hostname
    - pid: Process ID
    - started_at: ISO timestamp
    - last_activity: ISO timestamp
    """
    session_file = get_session_file_path()
    session = load_session(session_file)

    if session and session.get("session_id"):
        # Update last_activity
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        save_session(session_file, session)
        return session

    # Create new session
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": str(uuid.uuid4()),
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "started_at": now,
        "last_activity": now,
        "working_on": None,
    }
    save_session(session_file, session)
    return session


def get_session_id() -> str:
    """Get the session ID for the current process, creating if needed."""
    session = get_or_create_session()
    return session["session_id"]


def update_heartbeat(working_on: str | None = None) -> dict[str, Any]:
    """Update the session's last_activity timestamp.

    Args:
        working_on: Optional description of current work (e.g., "Plan #134")

    Returns:
        Updated session data
    """
    session_file = get_session_file_path()
    session = load_session(session_file)

    if not session:
        session = get_or_create_session()
    else:
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        if working_on is not None:
            session["working_on"] = working_on
        save_session(session_file, session)

    return session


def is_session_stale(
    session_id: str,
    staleness_minutes: int = STALENESS_MINUTES,
) -> tuple[bool, dict[str, Any] | None]:
    """Check if a session is stale (no activity for N minutes).

    Args:
        session_id: The session ID to check
        staleness_minutes: Minutes of inactivity before considered stale

    Returns:
        (is_stale, session_data) - session_data is None if session not found
    """
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return True, None

    # Find session file by session_id
    for session_file in sessions_dir.glob("*.session"):
        session = load_session(session_file)
        if session and session.get("session_id") == session_id:
            last_activity = session.get("last_activity")
            if not last_activity:
                return True, session

            try:
                last_time = datetime.fromisoformat(last_activity)
                # Ensure timezone aware
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                age = now - last_time

                if age > timedelta(minutes=staleness_minutes):
                    return True, session
                return False, session
            except ValueError:
                return True, session

    # Session not found
    return True, None


def list_sessions() -> list[dict[str, Any]]:
    """List all sessions with their status."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return []

    sessions = []
    now = datetime.now(timezone.utc)

    for session_file in sessions_dir.glob("*.session"):
        session = load_session(session_file)
        if not session:
            continue

        # Calculate age
        last_activity = session.get("last_activity")
        if last_activity:
            try:
                last_time = datetime.fromisoformat(last_activity)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                age_minutes = (now - last_time).total_seconds() / 60
                session["age_minutes"] = age_minutes
                session["is_stale"] = age_minutes > STALENESS_MINUTES
            except ValueError:
                session["age_minutes"] = None
                session["is_stale"] = True
        else:
            session["age_minutes"] = None
            session["is_stale"] = True

        session["file"] = session_file.name
        sessions.append(session)

    return sessions


def cleanup_stale_sessions(staleness_minutes: int = STALENESS_MINUTES) -> int:
    """Remove session files for stale sessions.

    Returns number of sessions cleaned up.
    """
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return 0

    cleaned = 0
    now = datetime.now(timezone.utc)

    for session_file in sessions_dir.glob("*.session"):
        session = load_session(session_file)
        if not session:
            # Invalid session file, remove it
            session_file.unlink()
            cleaned += 1
            continue

        last_activity = session.get("last_activity")
        if not last_activity:
            session_file.unlink()
            cleaned += 1
            continue

        try:
            last_time = datetime.fromisoformat(last_activity)
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            age = now - last_time
            if age > timedelta(minutes=staleness_minutes):
                session_file.unlink()
                cleaned += 1
        except ValueError:
            session_file.unlink()
            cleaned += 1

    return cleaned


def find_session_by_id(session_id: str) -> dict[str, Any] | None:
    """Find a session by its ID."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return None

    for session_file in sessions_dir.glob("*.session"):
        session = load_session(session_file)
        if session and session.get("session_id") == session_id:
            return session

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Session identity management for multi-CC coordination"
    )

    parser.add_argument(
        "--get",
        action="store_true",
        help="Get or create session ID for current process"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all sessions"
    )
    parser.add_argument(
        "--check-stale",
        metavar="SESSION_ID",
        help="Check if a session is stale"
    )
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Update heartbeat for current session"
    )
    parser.add_argument(
        "--working-on",
        help="Description of current work (used with --heartbeat)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove stale session files"
    )
    parser.add_argument(
        "--staleness-minutes",
        type=int,
        default=STALENESS_MINUTES,
        help=f"Minutes of inactivity before session is stale (default: {STALENESS_MINUTES})"
    )

    args = parser.parse_args()

    if args.get:
        session_id = get_session_id()
        print(session_id)
        return 0

    if args.list:
        sessions = list_sessions()
        if not sessions:
            print("No active sessions.")
            return 0

        print("Active Sessions:")
        print("-" * 70)
        for s in sessions:
            sid = s.get("session_id", "?")[:8]
            hostname = s.get("hostname", "?")
            pid = s.get("pid", "?")
            age = s.get("age_minutes")
            stale = s.get("is_stale", False)
            working = s.get("working_on", "-")

            age_str = f"{age:.0f}m ago" if age is not None else "unknown"
            status = "STALE" if stale else "active"

            print(f"  {sid}... | {hostname}:{pid} | {age_str:10} | {status:6} | {working}")

        return 0

    if args.check_stale:
        is_stale, session = is_session_stale(
            args.check_stale,
            args.staleness_minutes
        )
        if session is None:
            print(f"Session {args.check_stale} not found")
            return 1
        if is_stale:
            print(f"Session {args.check_stale[:8]}... is STALE")
            return 1
        else:
            print(f"Session {args.check_stale[:8]}... is ACTIVE")
            return 0

    if args.heartbeat:
        session = update_heartbeat(args.working_on)
        print(f"Heartbeat updated for session {session['session_id'][:8]}...")
        return 0

    if args.cleanup:
        cleaned = cleanup_stale_sessions(args.staleness_minutes)
        if cleaned > 0:
            print(f"Cleaned up {cleaned} stale session(s)")
        else:
            print("No stale sessions to clean up")
        return 0

    # Default: show session ID
    session_id = get_session_id()
    print(f"Session ID: {session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
