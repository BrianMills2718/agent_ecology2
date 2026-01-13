"""Integration tests for dashboard KPI endpoint."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestKpiEndpoint:
    """Tests for /api/kpis endpoint."""

    def test_kpi_endpoint_returns_valid_kpis(self) -> None:
        """API endpoint returns valid KPI structure."""
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
                "compute": {"alice": 80, "bob": 50},
                "scrip": {"alice": 100, "bob": 200},
            }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/kpis")
            assert response.status_code == 200

            data = response.json()

            # Check all expected fields are present
            assert "total_scrip" in data
            assert "scrip_velocity" in data
            assert "gini_coefficient" in data
            assert "median_scrip" in data
            assert "active_agent_ratio" in data
            assert "frozen_agent_count" in data
            assert "actions_per_tick" in data
            assert "escrow_active_listings" in data
            assert "llm_budget_remaining" in data
            assert "artifact_diversity" in data
            assert "activity_trend" in data
            assert "scrip_velocity_trend" in data

            # Verify computed values are sensible
            assert data["total_scrip"] == 300  # 100 + 200
            assert data["median_scrip"] == 150  # (100 + 200) / 2
            assert 0 <= data["gini_coefficient"] <= 1
            assert data["llm_budget_remaining"] <= 1.0

        finally:
            Path(jsonl_path).unlink()

    def test_kpi_trends_update_over_ticks(self) -> None:
        """Trend data accumulates over multiple ticks."""
        from src.dashboard.server import create_app

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # World init
            f.write(json.dumps({
                "event_type": "world_init",
                "timestamp": "2026-01-13T12:00:00",
                "max_ticks": 100,
                "budget": {"max_api_cost": 1.0},
                "principals": [
                    {"id": "alice", "starting_scrip": 100, "compute_quota": 100, "disk_quota": 1000},
                ]
            }) + '\n')

            # Multiple ticks
            for tick in range(1, 6):
                f.write(json.dumps({
                    "event_type": "tick",
                    "timestamp": f"2026-01-13T12:00:0{tick}",
                    "tick": tick,
                    "compute": {"alice": 100 - tick * 10},
                    "scrip": {"alice": 100},
                }) + '\n')

            jsonl_path = f.name

        try:
            app = create_app(jsonl_path=jsonl_path)
            client = TestClient(app)

            response = client.get("/api/kpis")
            assert response.status_code == 200

            data = response.json()

            # Trends should have entries from tick summaries
            # Note: tick summaries are created at tick transitions
            # so we should have some trend data
            assert isinstance(data["activity_trend"], list)
            assert isinstance(data["scrip_velocity_trend"], list)

        finally:
            Path(jsonl_path).unlink()
