"""Tests for the originality oracle in OracleScorer.

Tests the duplicate detection and originality checking functionality
of the oracle scorer module.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from world.oracle_scorer import OracleScorer


@pytest.fixture
def scorer() -> OracleScorer:
    """Create a fresh OracleScorer instance for testing.

    Uses mocked LLMProvider to avoid actual API calls.
    """
    with patch("world.oracle_scorer.LLMProvider"):
        scorer = OracleScorer(model="test-model", log_dir="/tmp/test_logs")
        # Clear any seen hashes from previous tests
        scorer._seen_hashes = set()
        return scorer


@pytest.fixture
def scorer_with_mock_llm() -> tuple[OracleScorer, MagicMock]:
    """Create an OracleScorer with a mocked LLM that returns valid JSON.

    Returns both the scorer and the mock LLM for verification.
    """
    with patch("world.oracle_scorer.LLMProvider") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = '{"score": 75, "reason": "Good content"}'
        mock_llm_class.return_value = mock_llm

        scorer = OracleScorer(model="test-model", log_dir="/tmp/test_logs")
        scorer._seen_hashes = set()
        return scorer, mock_llm


class TestOriginalityOracle:
    """Tests for originality detection in OracleScorer."""

    def test_first_submission_is_original(self, scorer: OracleScorer) -> None:
        """Verify that the first content submission returns True for is_original."""
        content = "This is brand new unique content."

        result = scorer.is_original(content)

        assert result is True

    def test_duplicate_content_not_original(self, scorer: OracleScorer) -> None:
        """Verify that submitting the same content twice returns False."""
        content = "This content will be submitted twice."

        # First submission - mark as seen via score_artifact
        scorer.score_artifact("artifact_1", "text", content)

        # Second submission should not be original
        result = scorer.is_original(content)

        assert result is False

    def test_whitespace_normalized(self, scorer: OracleScorer) -> None:
        """Verify that 'hello' and ' hello ' are treated as the same content."""
        content_no_whitespace = "hello"
        content_with_whitespace = "  hello  "

        # First submission
        scorer.score_artifact("artifact_1", "text", content_no_whitespace)

        # Whitespace-padded version should be detected as duplicate
        result = scorer.is_original(content_with_whitespace)

        assert result is False

    def test_case_normalized(self, scorer: OracleScorer) -> None:
        """Verify that 'Hello' and 'hello' are treated as the same content."""
        content_lower = "hello"
        content_mixed = "Hello"
        content_upper = "HELLO"

        # First submission
        scorer.score_artifact("artifact_1", "text", content_lower)

        # Different case versions should be detected as duplicates
        assert scorer.is_original(content_mixed) is False
        assert scorer.is_original(content_upper) is False

    def test_different_content_is_original(self, scorer: OracleScorer) -> None:
        """Verify that different content is correctly identified as original."""
        content_1 = "First piece of content"
        content_2 = "Completely different content"

        # Submit first content
        scorer.score_artifact("artifact_1", "text", content_1)

        # Different content should still be original
        result = scorer.is_original(content_2)

        assert result is True

    def test_duplicate_gets_zero_score(self, scorer: OracleScorer) -> None:
        """Verify that score_artifact returns 0 score for duplicate content."""
        content = "Content that will be duplicated"

        # First submission
        first_result = scorer.score_artifact("artifact_1", "text", content)

        # Second submission with same content
        second_result = scorer.score_artifact("artifact_2", "text", content)

        assert second_result["success"] is True
        assert second_result["score"] == 0
        assert "Duplicate" in second_result["reason"]

    def test_original_gets_scored(
        self, scorer_with_mock_llm: tuple[OracleScorer, MagicMock]
    ) -> None:
        """Verify that score_artifact proceeds with LLM scoring for original content."""
        scorer, mock_llm = scorer_with_mock_llm
        content = "Original content that should be scored by LLM"

        result = scorer.score_artifact("artifact_1", "text", content)

        # Verify LLM was called
        mock_llm.generate.assert_called_once()

        # Verify the result contains the mocked score
        assert result["success"] is True
        assert result["score"] == 75
        assert result["reason"] == "Good content"
