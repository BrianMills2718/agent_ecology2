"""Unit tests for run_manager.py (Plan #224)."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.dashboard.run_manager import RunInfo, RunManager


@pytest.fixture
def temp_logs_dir():
    """Create a temporary logs directory with sample runs."""
    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = Path(tmp) / "logs"
        logs_dir.mkdir()

        # Create run_1 with complete data
        run1 = logs_dir / "run_20260126_090000"
        run1.mkdir()
        with open(run1 / "events.jsonl", "w") as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-26T09:00:00+00:00",
                "principals": [{"id": "alpha"}, {"id": "beta"}],
            }) + "\n")
            f.write(json.dumps({
                "event_type": "thinking",
                "timestamp": "2026-01-26T09:05:00+00:00",
                "principal_id": "alpha",
            }) + "\n")
            f.write(json.dumps({
                "event_type": "simulation_complete",
                "timestamp": "2026-01-26T09:10:00+00:00",
            }) + "\n")

        # Create run_2 with checkpoint
        run2 = logs_dir / "run_20260126_100000"
        run2.mkdir()
        with open(run2 / "events.jsonl", "w") as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-26T10:00:00+00:00",
                "principals": [{"id": "gamma"}],
            }) + "\n")
        with open(run2 / "checkpoint.json", "w") as f:
            f.write("{}")

        yield logs_dir


def test_run_manager_init():
    """Test RunManager initialization."""
    manager = RunManager(logs_dir=Path("nonexistent"))
    assert manager.current_run_id is None


def test_list_runs_empty(tmp_path):
    """Test listing runs from empty directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    manager = RunManager(logs_dir=logs_dir)

    runs = manager.list_runs()
    assert runs == []


def test_list_runs(temp_logs_dir):
    """Test listing runs with metadata extraction."""
    manager = RunManager(logs_dir=temp_logs_dir)

    runs = manager.list_runs()

    # Should have 2 runs
    assert len(runs) == 2

    # Runs should be sorted by start_time descending (newest first)
    assert runs[0].run_id == "run_20260126_100000"
    assert runs[1].run_id == "run_20260126_090000"


def test_run_metadata_extraction(temp_logs_dir):
    """Test that run metadata is correctly extracted."""
    manager = RunManager(logs_dir=temp_logs_dir)

    runs = manager.list_runs()
    run1 = next(r for r in runs if r.run_id == "run_20260126_090000")

    # Check metadata
    assert run1.event_count == 3
    assert set(run1.agent_ids) == {"alpha", "beta"}
    assert run1.status == "completed"
    assert run1.has_checkpoint is False
    assert run1.duration_seconds == 600.0  # 10 minutes


def test_run_with_checkpoint(temp_logs_dir):
    """Test that checkpoint detection works."""
    manager = RunManager(logs_dir=temp_logs_dir)

    runs = manager.list_runs()
    run2 = next(r for r in runs if r.run_id == "run_20260126_100000")

    assert run2.has_checkpoint is True
    assert run2.status == "stopped"  # No completion event


def test_get_run(temp_logs_dir):
    """Test getting a specific run."""
    manager = RunManager(logs_dir=temp_logs_dir)

    run = manager.get_run("run_20260126_090000")
    assert run is not None
    assert run.run_id == "run_20260126_090000"

    not_found = manager.get_run("nonexistent")
    assert not_found is None


def test_set_current_run(temp_logs_dir):
    """Test setting the current run."""
    manager = RunManager(logs_dir=temp_logs_dir)

    # Initially no current run
    assert manager.current_run_id is None

    # Set current run
    run = manager.set_current_run("run_20260126_090000")
    assert run is not None
    assert manager.current_run_id == "run_20260126_090000"

    # Get current run
    current = manager.get_current_run()
    assert current is not None
    assert current.run_id == "run_20260126_090000"


def test_run_info_to_dict():
    """Test RunInfo serialization."""
    run = RunInfo(
        run_id="test_run",
        run_dir=Path("/tmp/logs/test_run"),
        start_time=datetime(2026, 1, 26, 9, 0, 0),
        end_time=datetime(2026, 1, 26, 9, 10, 0),
        duration_seconds=600.0,
        event_count=100,
        agent_ids=["alpha", "beta"],
        has_checkpoint=True,
        status="completed",
        jsonl_path=Path("/tmp/logs/test_run/events.jsonl"),
    )

    d = run.to_dict()

    assert d["run_id"] == "test_run"
    assert d["duration_seconds"] == 600.0
    assert d["event_count"] == 100
    assert d["agent_ids"] == ["alpha", "beta"]
    assert d["has_checkpoint"] is True
    assert d["status"] == "completed"
    assert "start_time" in d
    assert "end_time" in d
