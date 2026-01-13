"""Integration tests for dashboard health endpoint."""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json

from src.dashboard.server import create_app


@pytest.fixture
def temp_jsonl() -> Path:
    """Create a temporary JSONL file with test events."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write some basic simulation events
        events = [
            {"event_type": "simulation_start", "tick": 0, "timestamp": "2026-01-13T10:00:00"},
            {"event_type": "agent_registered", "tick": 0, "agent_id": "alice", "scrip": 1000},
            {"event_type": "agent_registered", "tick": 0, "agent_id": "bob", "scrip": 1000},
            {"event_type": "agent_registered", "tick": 0, "agent_id": "charlie", "scrip": 1000},
            {"event_type": "tick_summary", "tick": 1, "action_count": 3},
            {"event_type": "tick_summary", "tick": 2, "action_count": 2},
        ]
        for event in events:
            f.write(json.dumps(event) + "\n")
        return Path(f.name)


@pytest.fixture
def client(temp_jsonl: Path) -> TestClient:
    """Create a test client with temporary JSONL."""
    app = create_app(jsonl_path=temp_jsonl)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_endpoint(self, client: TestClient) -> None:
        """API should return valid health report."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()

        # Check required fields
        assert "timestamp" in data
        assert "overall_status" in data
        assert data["overall_status"] in ["healthy", "warning", "critical"]
        assert "health_score" in data
        assert 0.0 <= data["health_score"] <= 1.0
        assert "trend" in data
        assert data["trend"] in ["improving", "stable", "declining", "unknown"]
        assert "concerns" in data
        assert isinstance(data["concerns"], list)
        assert "kpis" in data

    def test_health_endpoint_concerns_structure(self, client: TestClient) -> None:
        """Concerns should have proper structure."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()

        # Each concern should have required fields
        for concern in data["concerns"]:
            assert "metric" in concern
            assert "value" in concern
            assert "threshold" in concern
            assert "severity" in concern
            assert concern["severity"] in ["warning", "critical"]
            assert "message" in concern

    def test_health_endpoint_kpis_subset(self, client: TestClient) -> None:
        """Health endpoint should include key KPIs."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        kpis = data["kpis"]

        # Check key KPIs are present
        assert "total_scrip" in kpis
        assert "gini_coefficient" in kpis
        assert "active_agent_ratio" in kpis
        assert "frozen_agent_count" in kpis
        assert "llm_budget_burn_rate" in kpis
        assert "scrip_velocity" in kpis


class TestHealthWithSimulation:
    """Tests for health assessment with simulation data."""

    def test_health_with_simulation(self, client: TestClient) -> None:
        """Health reports should reflect simulation state."""
        # First call - should return unknown trend (no previous data)
        response1 = client.get("/api/health")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["trend"] == "unknown"

        # Second call - should have trend info based on comparison
        response2 = client.get("/api/health")
        assert response2.status_code == 200
        data2 = response2.json()
        # Trend should now be known (stable since same data)
        assert data2["trend"] in ["improving", "stable", "declining"]

    def test_health_status_consistency(self, client: TestClient) -> None:
        """Health status should be consistent with concerns."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()

        has_critical = any(c["severity"] == "critical" for c in data["concerns"])
        has_warning = any(c["severity"] == "warning" for c in data["concerns"])

        if has_critical:
            assert data["overall_status"] == "critical"
        elif has_warning:
            assert data["overall_status"] == "warning"
        else:
            assert data["overall_status"] == "healthy"
