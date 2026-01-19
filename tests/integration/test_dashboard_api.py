"""Integration tests for dashboard API endpoints (Plan #76)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.plans(76)
class TestAgentMetricsEndpoint:
    """Tests for /api/agents/{id}/metrics endpoint."""

    def test_agent_metrics_endpoint(self) -> None:
        """API returns per-agent metrics for existing agent."""
        from src.dashboard.server import create_app

        # Create a minimal JSONL file with test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # World init with agents
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "alice", "starting_scrip": 100, "compute_quota": 100, "disk_quota": 1000},
                    {"id": "bob", "starting_scrip": 200, "compute_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')

            # Tick event
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:01",
                "tick": 1,
                "compute": {"alice": 80, "bob": 100},
                "scrip": {"alice": 100, "bob": 200},
            }) + '\n')

            # Action event for alice
            f.write(json.dumps({
                "event_type": "action",
                "timestamp": "2026-01-13T12:00:02",
                "intent": {
                    "principal_id": "alice",
                    "action_type": "read_artifact",
                    "artifact_id": "test_artifact",
                },
                "result": {},
            }) + '\n')

            # Tick 2
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:10",
                "tick": 2,
                "compute": {"alice": 60, "bob": 100},
                "scrip": {"alice": 100, "bob": 200},
            }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            # Test getting metrics for alice
            response = client.get("/api/agents/alice/metrics")
            assert response.status_code == 200

            data = response.json()

            # Check all expected fields are present
            assert "agent_id" in data
            assert "total_actions" in data
            assert "last_action_tick" in data
            assert "ticks_since_action" in data
            assert "is_frozen" in data
            assert "scrip_balance" in data
            assert "success_rate" in data

            # Verify values
            assert data["agent_id"] == "alice"
            assert data["total_actions"] == 1  # One action recorded
            assert data["last_action_tick"] == 1
            assert data["ticks_since_action"] == 1  # tick 2 - tick 1
            assert data["is_frozen"] is False  # Still has tokens
            assert data["scrip_balance"] == 100

        finally:
            Path(jsonl_path).unlink()

    def test_agent_metrics_endpoint_not_found(self) -> None:
        """API returns error for non-existent agent."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "alice", "starting_scrip": 100, "compute_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')
            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/agents/nonexistent/metrics")
            assert response.status_code == 200

            data = response.json()
            assert "error" in data
            assert "nonexistent" in data["error"]

        finally:
            Path(jsonl_path).unlink()

    def test_agent_metrics_frozen_detection(self) -> None:
        """API correctly identifies frozen agents."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "frozen_agent", "starting_scrip": 100, "compute_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')

            # Tick showing agent has exhausted compute quota
            f.write(json.dumps({
                "event_type": "tick",
                "timestamp": "2026-01-13T12:00:01",
                "tick": 1,
                "compute": {"frozen_agent": 0},  # 0 remaining = quota exhausted
                "scrip": {"frozen_agent": 100},
            }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/agents/frozen_agent/metrics")
            assert response.status_code == 200

            data = response.json()
            assert data["is_frozen"] is True  # Agent exhausted tokens

        finally:
            Path(jsonl_path).unlink()
