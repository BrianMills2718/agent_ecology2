"""Fixtures for plan-specific E2E tests.

This directory contains feature-specific E2E tests organized by plan number.
Each plan's tests verify that its feature works end-to-end.

Structure:
    tests/plans/
    ├── conftest.py          # This file
    ├── plan_01/
    │   └── test_rate_limiting_e2e.py
    ├── plan_06/
    │   └── test_unified_ontology_e2e.py
    └── ...

Usage:
    # Run all plan E2E tests
    pytest tests/plans/ -v

    # Run tests for a specific plan
    pytest tests/plans/plan_06/ -v

    # Run tests marked with a plan number
    pytest --plan 6 tests/
"""

from __future__ import annotations

from typing import Any
from pathlib import Path

import pytest


@pytest.fixture
def plan_e2e_config(tmp_path: Path) -> dict[str, Any]:
    """Standard configuration for plan E2E tests.

    Provides a reasonable default config for testing features.
    Individual plan tests can override as needed.
    """
    log_file = tmp_path / "plan_e2e.jsonl"

    return {
        "world": {
            "max_ticks": 3,
        },
        "costs": {
            "per_1k_input_tokens": 1,
            "per_1k_output_tokens": 3,
        },
        "logging": {
            "output_file": str(log_file),
            "log_dir": str(tmp_path / "llm_logs"),
        },
        "principals": [
            {"id": "test_agent", "starting_scrip": 100},
        ],
        "rights": {
            "default_compute_quota": 100,
            "default_disk_quota": 10000,
        },
        "llm": {
            "default_model": "gemini/gemini-2.0-flash",
            "rate_limit_delay": 0,
        },
        "budget": {
            "max_api_cost": 0.10,
            "checkpoint_interval": 0,
            "checkpoint_on_end": False,
        },
        "rate_limiting": {
            "enabled": False,
        },
        "execution": {
            "use_autonomous_loops": False,
        },
    }
