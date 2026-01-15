"""Tests for EventLogger per-run logging (Plan #56)

TDD tests - write first, then implement.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.world.logger import EventLogger


class TestPerRunLogging:
    """Test per-run directory logging"""

    def test_per_run_directory_created(self, tmp_path: Path) -> None:
        """Directory created with run_id"""
        logs_dir = tmp_path / "logs"
        run_id = "run_20260115_120000"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(logs_dir=str(logs_dir), run_id=run_id)

        expected_dir = logs_dir / run_id
        assert expected_dir.exists(), f"Expected directory {expected_dir} to exist"
        assert expected_dir.is_dir()

    def test_events_written_to_run_directory(self, tmp_path: Path) -> None:
        """Events go to correct path"""
        logs_dir = tmp_path / "logs"
        run_id = "run_20260115_120000"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(logs_dir=str(logs_dir), run_id=run_id)
            logger.log("test_event", {"key": "value"})

        events_file = logs_dir / run_id / "events.jsonl"
        assert events_file.exists(), f"Expected events file at {events_file}"

        content = events_file.read_text().strip()
        event = json.loads(content)
        assert event["event_type"] == "test_event"
        assert event["key"] == "value"

    def test_latest_symlink_created(self, tmp_path: Path) -> None:
        """Symlink points to latest run"""
        logs_dir = tmp_path / "logs"
        run_id = "run_20260115_120000"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(logs_dir=str(logs_dir), run_id=run_id)

        latest_link = logs_dir / "latest"
        assert latest_link.exists() or latest_link.is_symlink(), "latest symlink should exist"
        # Resolve symlink and check it points to correct directory
        resolved = latest_link.resolve()
        expected = (logs_dir / run_id).resolve()
        assert resolved == expected, f"latest should point to {expected}, got {resolved}"

    def test_multiple_runs_preserved(self, tmp_path: Path) -> None:
        """Previous runs not overwritten"""
        logs_dir = tmp_path / "logs"

        # Create first run
        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger1 = EventLogger(logs_dir=str(logs_dir), run_id="run_20260115_100000")
            logger1.log("event1", {"run": 1})

        # Create second run
        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger2 = EventLogger(logs_dir=str(logs_dir), run_id="run_20260115_110000")
            logger2.log("event2", {"run": 2})

        # Both runs should exist
        run1_events = logs_dir / "run_20260115_100000" / "events.jsonl"
        run2_events = logs_dir / "run_20260115_110000" / "events.jsonl"

        assert run1_events.exists(), "First run should be preserved"
        assert run2_events.exists(), "Second run should exist"

        # Verify content
        event1 = json.loads(run1_events.read_text().strip())
        event2 = json.loads(run2_events.read_text().strip())
        assert event1["run"] == 1
        assert event2["run"] == 2

    def test_backward_compat_no_run_id(self, tmp_path: Path) -> None:
        """Works without run_id (legacy mode)"""
        output_file = tmp_path / "run.jsonl"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            # No run_id or logs_dir - should use legacy single-file mode
            logger = EventLogger(output_file=str(output_file))
            logger.log("legacy_event", {"mode": "legacy"})

        assert output_file.exists(), "Legacy mode should write to single file"
        event = json.loads(output_file.read_text().strip())
        assert event["event_type"] == "legacy_event"


class TestEventLoggerBasics:
    """Basic EventLogger functionality (existing behavior)"""

    def test_log_creates_file(self, tmp_path: Path) -> None:
        """Logging creates output file"""
        output_file = tmp_path / "test.jsonl"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(output_file=str(output_file))
            logger.log("test", {"data": 123})

        assert output_file.exists()

    def test_log_appends_events(self, tmp_path: Path) -> None:
        """Multiple logs append to file"""
        output_file = tmp_path / "test.jsonl"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(output_file=str(output_file))
            logger.log("event1", {"n": 1})
            logger.log("event2", {"n": 2})

        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_read_recent(self, tmp_path: Path) -> None:
        """read_recent returns last N events"""
        output_file = tmp_path / "test.jsonl"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(output_file=str(output_file))
            for i in range(10):
                logger.log("event", {"n": i})

            recent = logger.read_recent(3)

        assert len(recent) == 3
        assert recent[0]["n"] == 7
        assert recent[1]["n"] == 8
        assert recent[2]["n"] == 9

    def test_event_has_timestamp(self, tmp_path: Path) -> None:
        """Logged events include timestamp"""
        output_file = tmp_path / "test.jsonl"

        with patch("src.config.get") as mock_get:
            mock_get.return_value = None
            logger = EventLogger(output_file=str(output_file))
            logger.log("test", {})

        event = json.loads(output_file.read_text().strip())
        assert "timestamp" in event
        assert "event_type" in event
