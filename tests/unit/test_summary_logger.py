"""Tests for SummaryLogger (Plan #60).

Tests the summary logging system that creates tractable periodic summaries
alongside the full event log.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestSummaryLogger:
    """Tests for SummaryLogger class."""

    @pytest.mark.plans([60])
    def test_creates_summary_file(self) -> None:
        """SummaryLogger creates summary.jsonl file."""
        from src.world.logger import SummaryLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = SummaryLogger(Path(tmpdir) / "summary.jsonl")
            logger.log_summary(
                event_number=1,
                agents_active=3,
                actions_executed=5,
            )

            assert (Path(tmpdir) / "summary.jsonl").exists()

    @pytest.mark.plans([60])
    def test_writes_one_line_per_summary(self) -> None:
        """SummaryLogger writes exactly one line per summary."""
        from src.world.logger import SummaryLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "summary.jsonl"
            logger = SummaryLogger(path)

            for event_num in range(5):
                logger.log_summary(
                    event_number=event_num,
                    agents_active=3,
                    actions_executed=event_num + 1,
                )

            lines = path.read_text().strip().split("\n")
            assert len(lines) == 5

    @pytest.mark.plans([60])
    def test_summary_format_has_required_fields(self) -> None:
        """Summary JSON contains all required fields."""
        from src.world.logger import SummaryLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "summary.jsonl"
            logger = SummaryLogger(path)

            logger.log_summary(
                event_number=1,
                agents_active=3,
                actions_executed=5,
                actions_by_type={"invoke": 3, "write": 2},
                total_llm_tokens=150,
                total_scrip_transferred=25,
                artifacts_created=1,
                errors=0,
                highlights=["alpha created tool_x"],
            )

            line = path.read_text().strip()
            data = json.loads(line)

            # Required fields
            assert "event_number" in data
            assert "timestamp" in data
            assert "agents_active" in data
            assert "actions_executed" in data
            assert "actions_by_type" in data
            assert "total_llm_tokens" in data
            assert "total_scrip_transferred" in data
            assert "artifacts_created" in data
            assert "errors" in data
            assert "highlights" in data

            # Check values
            assert data["event_number"] == 1
            assert data["agents_active"] == 3
            assert data["actions_executed"] == 5
            assert data["actions_by_type"] == {"invoke": 3, "write": 2}
            assert data["highlights"] == ["alpha created tool_x"]

    @pytest.mark.plans([60])
    def test_summary_with_defaults(self) -> None:
        """Summary uses sensible defaults for optional fields."""
        from src.world.logger import SummaryLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "summary.jsonl"
            logger = SummaryLogger(path)

            # Minimal call - only required fields
            logger.log_summary(
                event_number=0,
                agents_active=2,
                actions_executed=0,
            )

            line = path.read_text().strip()
            data = json.loads(line)

            # Defaults should be present
            assert data["actions_by_type"] == {}
            assert data["total_llm_tokens"] == 0
            assert data["total_scrip_transferred"] == 0
            assert data["artifacts_created"] == 0
            assert data["errors"] == 0
            assert data["highlights"] == []


class TestSummaryLoggerIntegration:
    """Tests for SummaryLogger integration with EventLogger."""

    @pytest.mark.plans([60])
    def test_event_logger_creates_summary_logger(self) -> None:
        """EventLogger in per-run mode creates companion SummaryLogger."""
        from src.world.logger import EventLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EventLogger(
                logs_dir=tmpdir,
                run_id="test_run",
            )

            assert logger.summary_logger is not None
            assert logger.summary_logger.output_path.name == "summary.jsonl"

    @pytest.mark.plans([60])
    def test_event_logger_legacy_mode_no_summary(self) -> None:
        """EventLogger in legacy mode does not create summary logger."""
        from src.world.logger import EventLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EventLogger(output_file=str(Path(tmpdir) / "run.jsonl"))

            # Legacy mode - no summary logger
            assert logger.summary_logger is None


class TestSummaryCollection:
    """Tests for collecting summary data."""

    @pytest.mark.plans([60])
    def test_summary_collector_tracks_actions(self) -> None:
        """SummaryCollector accumulates action counts."""
        from src.world.logger import SummaryCollector

        collector = SummaryCollector()

        collector.record_action("invoke", success=True)
        collector.record_action("write", success=True)
        collector.record_action("invoke", success=False)

        summary = collector.finalize(event_number=1, agents_active=2)

        assert summary["actions_executed"] == 3
        assert summary["actions_by_type"] == {"invoke": 2, "write": 1}
        assert summary["errors"] == 1

    @pytest.mark.plans([60])
    def test_summary_collector_tracks_llm_tokens(self) -> None:
        """SummaryCollector accumulates LLM token usage."""
        from src.world.logger import SummaryCollector

        collector = SummaryCollector()

        collector.record_llm_tokens(100)
        collector.record_llm_tokens(50)

        summary = collector.finalize(event_number=1, agents_active=2)

        assert summary["total_llm_tokens"] == 150

    @pytest.mark.plans([60])
    def test_summary_collector_tracks_scrip(self) -> None:
        """SummaryCollector accumulates scrip transfers."""
        from src.world.logger import SummaryCollector

        collector = SummaryCollector()

        collector.record_scrip_transfer(25)
        collector.record_scrip_transfer(10)

        summary = collector.finalize(event_number=1, agents_active=2)

        assert summary["total_scrip_transferred"] == 35

    @pytest.mark.plans([60])
    def test_summary_collector_captures_highlights(self) -> None:
        """SummaryCollector captures significant events as highlights."""
        from src.world.logger import SummaryCollector

        collector = SummaryCollector()

        collector.add_highlight("alpha created tool_x")
        collector.add_highlight("beta transferred 50 scrip to gamma")

        summary = collector.finalize(event_number=1, agents_active=2)

        assert len(summary["highlights"]) == 2
        assert "alpha created tool_x" in summary["highlights"]

    @pytest.mark.plans([60])
    def test_summary_collector_reset(self) -> None:
        """SummaryCollector resets state after finalize."""
        from src.world.logger import SummaryCollector

        collector = SummaryCollector()

        collector.record_action("invoke", success=True)
        collector.finalize(event_number=1, agents_active=2)

        # After finalize, collector should be reset
        summary = collector.finalize(event_number=2, agents_active=2)
        assert summary["actions_executed"] == 0
