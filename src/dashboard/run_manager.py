"""Run management for discovering and switching between simulation runs.

Plan #224: Enables dashboard to list, select, and resume historical simulation runs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class RunInfo:
    """Metadata about a simulation run."""
    run_id: str
    run_dir: Path
    start_time: datetime | None
    end_time: datetime | None
    duration_seconds: float
    event_count: int
    agent_ids: list[str]
    has_checkpoint: bool
    status: Literal["running", "completed", "stopped"]
    jsonl_path: Path

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict."""
        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "event_count": self.event_count,
            "agent_ids": self.agent_ids,
            "has_checkpoint": self.has_checkpoint,
            "status": self.status,
            "jsonl_path": str(self.jsonl_path),
        }


class RunManager:
    """Manages discovery and selection of simulation runs.

    Scans the logs directory for run_* folders and extracts metadata
    from each events.jsonl file. Supports switching the current run
    for viewing in the dashboard.
    """

    def __init__(
        self,
        logs_dir: Path | str = Path("logs"),
        current_jsonl: Path | str | None = None,
    ) -> None:
        """Initialize run manager.

        Args:
            logs_dir: Directory containing run folders
            current_jsonl: Currently active jsonl path (for run detection)
        """
        self.logs_dir = Path(logs_dir)
        self._current_run_id: str | None = None
        self._current_jsonl = Path(current_jsonl) if current_jsonl else None

    @property
    def current_run_id(self) -> str | None:
        """Get the currently selected run ID."""
        return self._current_run_id

    def list_runs(self) -> list[RunInfo]:
        """List all available runs with metadata.

        Returns:
            List of RunInfo sorted by start_time descending (newest first)
        """
        runs: list[RunInfo] = []

        if not self.logs_dir.exists():
            return runs

        # Find all run directories
        for run_dir in sorted(self.logs_dir.glob("run_*"), reverse=True):
            if not run_dir.is_dir():
                continue

            # Check for events.jsonl
            events_file = run_dir / "events.jsonl"
            if not events_file.exists():
                continue

            try:
                run_info = self._extract_metadata(run_dir, events_file)
                runs.append(run_info)
            except Exception as e:
                logger.warning(f"Failed to extract metadata from {run_dir}: {e}")
                continue

        # Also check for legacy run.jsonl in root
        root_jsonl = self.logs_dir.parent / "run.jsonl"
        if root_jsonl.exists():
            try:
                run_info = self._extract_metadata_from_jsonl(root_jsonl, "legacy")
                runs.append(run_info)
            except Exception as e:
                logger.warning(f"Failed to extract metadata from {root_jsonl}: {e}")

        # Sort by start_time descending
        runs.sort(
            key=lambda r: r.start_time if r.start_time else datetime.min,
            reverse=True
        )

        return runs

    def get_run(self, run_id: str) -> RunInfo | None:
        """Get metadata for a specific run.

        Args:
            run_id: The run ID to look up

        Returns:
            RunInfo if found, None otherwise
        """
        for run in self.list_runs():
            if run.run_id == run_id:
                return run
        return None

    def set_current_run(self, run_id: str) -> RunInfo | None:
        """Set the currently active run for viewing.

        Args:
            run_id: The run ID to switch to

        Returns:
            RunInfo for the new current run, or None if not found
        """
        run = self.get_run(run_id)
        if run:
            self._current_run_id = run_id
            self._current_jsonl = run.jsonl_path
        return run

    def get_current_run(self) -> RunInfo | None:
        """Get metadata for the current run."""
        if self._current_run_id:
            return self.get_run(self._current_run_id)
        return None

    def _extract_metadata(self, run_dir: Path, events_file: Path) -> RunInfo:
        """Extract run metadata from a run directory.

        Args:
            run_dir: Directory containing the run
            events_file: Path to events.jsonl

        Returns:
            RunInfo with extracted metadata
        """
        run_id = run_dir.name

        # Check for checkpoint
        has_checkpoint = (run_dir / "checkpoint.json").exists()

        # Parse events for metadata
        return self._extract_metadata_from_jsonl(events_file, run_id, has_checkpoint)

    def _extract_metadata_from_jsonl(
        self,
        jsonl_path: Path,
        run_id: str,
        has_checkpoint: bool = False,
    ) -> RunInfo:
        """Extract metadata by parsing the events file.

        Reads first and last events for timing, and scans for agent IDs.
        Uses efficient sampling for large files.
        """
        start_time: datetime | None = None
        end_time: datetime | None = None
        agent_ids: set[str] = set()
        event_count = 0
        status: Literal["running", "completed", "stopped"] = "stopped"

        # Read the file efficiently
        try:
            with open(jsonl_path, "r") as f:
                first_event = None
                last_event = None

                for line in f:
                    if not line.strip():
                        continue
                    event_count += 1

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Save first event
                    if first_event is None:
                        first_event = event

                    # Always update last_event
                    last_event = event

                    # Extract agent IDs from relevant events
                    event_type = event.get("event_type", "")

                    # From world_init principals
                    if event_type == "world_init":
                        for p in event.get("principals", []):
                            if p.get("id"):
                                agent_ids.add(p["id"])

                    # From thinking events
                    if event_type == "thinking":
                        pid = event.get("principal_id")
                        if pid:
                            agent_ids.add(pid)

                    # From action events
                    if event_type == "action":
                        intent = event.get("intent", {})
                        pid = intent.get("principal_id")
                        if pid:
                            agent_ids.add(pid)

                    # Check for simulation end
                    if event_type == "simulation_complete":
                        status = "completed"
                    elif event_type == "budget_pause":
                        status = "completed"

                # Extract timestamps
                if first_event:
                    ts = first_event.get("timestamp")
                    if ts:
                        try:
                            start_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                if last_event:
                    ts = last_event.get("timestamp")
                    if ts:
                        try:
                            end_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except ValueError:
                            pass

        except OSError as e:
            logger.warning(f"Failed to read {jsonl_path}: {e}")

        # Calculate duration
        duration_seconds = 0.0
        if start_time and end_time:
            duration_seconds = (end_time - start_time).total_seconds()

        # Determine run directory
        run_dir = jsonl_path.parent
        if run_id == "legacy":
            run_dir = jsonl_path.parent  # Root directory for legacy run.jsonl

        return RunInfo(
            run_id=run_id,
            run_dir=run_dir,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            event_count=event_count,
            agent_ids=sorted(agent_ids),
            has_checkpoint=has_checkpoint,
            status=status,
            jsonl_path=jsonl_path,
        )

    def detect_current_run(self) -> str | None:
        """Detect which run is currently active based on the latest symlink.

        Returns:
            Run ID of the current run, or None if not found
        """
        latest_link = self.logs_dir / "latest"
        if latest_link.is_symlink():
            target = latest_link.resolve()
            if target.is_dir():
                self._current_run_id = target.name
                self._current_jsonl = target / "events.jsonl"
                return self._current_run_id
        return None
