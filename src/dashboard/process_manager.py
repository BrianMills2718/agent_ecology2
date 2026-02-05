"""Simulation subprocess manager for dashboard control.

Manages spawning and stopping simulation subprocesses when the dashboard
is running in "dashboard-only" mode and the user wants to start a new simulation.
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml


class SimulationProcessManager:
    """Manages a spawned simulation subprocess.

    Singleton pattern - only one simulation can run at a time from the dashboard.
    """

    _instance: SimulationProcessManager | None = None

    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._config_path: Path | None = None
        self._start_time: float | None = None
        self._project_root = Path(__file__).parent.parent.parent

    @classmethod
    def get_instance(cls) -> SimulationProcessManager:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_running(self) -> bool:
        """Check if subprocess is currently running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(
        self,
        duration: int = 60,
        agents: int | None = None,
        budget: float = 0.50,
        model: str = "gemini/gemini-2.0-flash",
        rate_limit_delay: float = 5.0,
    ) -> dict[str, Any]:
        """Start a new simulation subprocess.

        Args:
            duration: Simulation duration in seconds
            agents: Number of agents (None = all available)
            budget: Max API cost in USD
            model: LLM model to use
            rate_limit_delay: Delay between API calls in seconds

        Returns:
            Status dict with success, pid, jsonl_path, or error
        """
        if self.is_running:
            return {
                "success": False,
                "error": "Simulation already running",
                "pid": self._process.pid if self._process else None,
            }

        # Create temp config file with overrides
        config_override = {
            "budget": {
                "max_api_cost": budget,
            },
            "llm": {
                "default_model": model,
                "rate_limit_delay": rate_limit_delay,
            },
        }

        # Write temp config
        fd, config_path = tempfile.mkstemp(suffix=".yaml", prefix="sim_config_")
        os.close(fd)
        self._config_path = Path(config_path)

        with open(self._config_path, "w") as f:
            yaml.dump(config_override, f)

        # Build command
        cmd = [
            "python", "run.py",
            "--dashboard",
            "--no-browser",
            "--config", str(self._config_path),
            "--duration", str(duration),
        ]

        if agents is not None:
            cmd.extend(["--agents", str(agents)])

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self._project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._start_time = time.time()

            # Give it a moment to start
            time.sleep(0.5)

            # Check if it crashed immediately
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                self._cleanup()
                return {
                    "success": False,
                    "error": f"Process exited immediately: {stderr[:500]}",
                }

            return {
                "success": True,
                "pid": self._process.pid,
                "jsonl_path": "logs/latest/events.jsonl",
            }

        except Exception as e:
            self._cleanup()
            return {
                "success": False,
                "error": str(e),
            }

    def stop(self, timeout: float = 10.0) -> dict[str, Any]:
        """Stop the running simulation gracefully.

        Sends SIGTERM first for graceful shutdown (allows checkpoint save),
        then SIGKILL if it doesn't stop within timeout.

        Args:
            timeout: Seconds to wait before force-killing

        Returns:
            Status dict with success and any error
        """
        process = self._process
        if process is None or not self.is_running:
            return {
                "success": True,
                "message": "No simulation running",
            }

        pid = process.pid

        try:
            # Send SIGTERM for graceful shutdown
            process.send_signal(signal.SIGTERM)

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if it didn't stop
                process.kill()
                process.wait(timeout=2)

            self._cleanup()

            return {
                "success": True,
                "pid": pid,
                "message": "Simulation stopped",
            }

        except Exception as e:
            self._cleanup()
            return {
                "success": False,
                "error": str(e),
            }

    def get_status(self) -> dict[str, Any]:
        """Get current subprocess status.

        Returns:
            Status dict with running state, pid, elapsed time
        """
        if not self.is_running:
            return {
                "has_subprocess": False,
                "subprocess_running": False,
            }

        elapsed = time.time() - self._start_time if self._start_time else 0

        return {
            "has_subprocess": True,
            "subprocess_running": True,
            "subprocess_pid": self._process.pid if self._process else None,
            "subprocess_elapsed_seconds": elapsed,
        }

    def resume_from_checkpoint(
        self,
        checkpoint_path: str,
        duration: int = 60,
    ) -> dict[str, Any]:
        """Start a simulation resuming from a checkpoint.

        Plan #224: Loads checkpoint state and continues from where it left off.

        Args:
            checkpoint_path: Path to the checkpoint.json file
            duration: Additional duration in seconds to run

        Returns:
            Status dict with success, pid, or error
        """
        if self.is_running:
            return {
                "success": False,
                "error": "Simulation already running",
                "pid": self._process.pid if self._process else None,
            }

        checkpoint_file = Path(checkpoint_path)
        if not checkpoint_file.exists():
            return {
                "success": False,
                "error": f"Checkpoint not found: {checkpoint_path}",
            }

        # Build command with --resume flag
        cmd = [
            "python", "run.py",
            "--dashboard",
            "--no-browser",
            "--resume", str(checkpoint_file),
            "--duration", str(duration),
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self._project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._start_time = time.time()

            # Give it a moment to start
            time.sleep(0.5)

            # Check if it crashed immediately
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                self._cleanup()
                return {
                    "success": False,
                    "error": f"Process exited immediately: {stderr[:500]}",
                }

            # Derive the jsonl path from checkpoint location
            checkpoint_dir = checkpoint_file.parent
            jsonl_path = checkpoint_dir / "events.jsonl"

            return {
                "success": True,
                "pid": self._process.pid,
                "jsonl_path": str(jsonl_path),
                "checkpoint_path": checkpoint_path,
            }

        except Exception as e:
            self._cleanup()
            return {
                "success": False,
                "error": str(e),
            }

    def _cleanup(self) -> None:
        """Clean up process references and temp files."""
        self._process = None
        self._start_time = None

        if self._config_path and self._config_path.exists():
            try:
                self._config_path.unlink()
            except OSError:
                pass
        self._config_path = None
