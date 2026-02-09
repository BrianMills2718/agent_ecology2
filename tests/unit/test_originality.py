"""Tests for the originality oracle in MintScorer.

Tests the duplicate detection and originality checking functionality
of the mint scorer module.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.world.llm_client import LLMCallResult
from src.world.mint_scorer import MintScorer


def _mock_call_llm_result(
    content: str = '{"score": 50, "reason": "OK"}',
    cost: float = 0.001,
) -> LLMCallResult:
    """Create a mock LLMCallResult for testing."""
    return LLMCallResult(
        content=content,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        cost=cost,
        model="test-model",
    )


@pytest.fixture
def scorer() -> MintScorer:
    """Create a fresh MintScorer instance for testing.

    # mock-ok: LLM calls are external API
    """
    scorer = MintScorer(model="test-model", log_dir="/tmp/test_logs")
    scorer._seen_hashes = set()
    return scorer


@pytest.fixture
def scorer_with_mock_llm():  # type: ignore[no-untyped-def]
    """Create a MintScorer with a mocked call_llm that returns valid JSON.

    Yields (scorer, mock) so the patch remains active during the test.
    # mock-ok: LLM calls are external API
    """
    mock_llm = MagicMock(return_value=_mock_call_llm_result(
        content='{"score": 75, "reason": "Good content"}'
    ))
    with patch("src.world.mint_scorer.call_llm", mock_llm):
        scorer = MintScorer(model="test-model", log_dir="/tmp/test_logs")
        scorer._seen_hashes = set()
        yield scorer, mock_llm


class TestOriginalityOracle:
    """Tests for originality detection in MintScorer."""

    def test_first_submission_is_original(self, scorer: MintScorer) -> None:
        """Verify that the first content submission returns True for is_original."""
        content = "This is brand new unique content."

        result = scorer.is_original(content)

        assert result is True

    def test_duplicate_content_not_original(self, scorer: MintScorer) -> None:
        """Verify that submitting the same content twice returns False."""
        content = "This content will be submitted twice."

        # First submission - mark as seen via score_artifact
        # mock-ok: LLM calls are external API
        with patch("src.world.mint_scorer.call_llm", return_value=_mock_call_llm_result()):
            scorer.score_artifact("artifact_1", "text", content)

        # Second submission should not be original
        result = scorer.is_original(content)

        assert result is False

    def test_whitespace_normalized(self, scorer: MintScorer) -> None:
        """Verify that 'hello' and ' hello ' are treated as the same content."""
        content_no_whitespace = "hello"
        content_with_whitespace = "  hello  "

        # First submission
        # mock-ok: LLM calls are external API
        with patch("src.world.mint_scorer.call_llm", return_value=_mock_call_llm_result()):
            scorer.score_artifact("artifact_1", "text", content_no_whitespace)

        # Whitespace-padded version should be detected as duplicate
        result = scorer.is_original(content_with_whitespace)

        assert result is False

    def test_case_normalized(self, scorer: MintScorer) -> None:
        """Verify that 'Hello' and 'hello' are treated as the same content."""
        content_lower = "hello"
        content_mixed = "Hello"
        content_upper = "HELLO"

        # First submission
        # mock-ok: LLM calls are external API
        with patch("src.world.mint_scorer.call_llm", return_value=_mock_call_llm_result()):
            scorer.score_artifact("artifact_1", "text", content_lower)

        # Different case versions should be detected as duplicates
        assert scorer.is_original(content_mixed) is False
        assert scorer.is_original(content_upper) is False

    def test_different_content_is_original(self, scorer: MintScorer) -> None:
        """Verify that different content is correctly identified as original."""
        content_1 = "First piece of content"
        content_2 = "Completely different content"

        # Submit first content
        # mock-ok: LLM calls are external API
        with patch("src.world.mint_scorer.call_llm", return_value=_mock_call_llm_result()):
            scorer.score_artifact("artifact_1", "text", content_1)

        # Different content should still be original
        result = scorer.is_original(content_2)

        assert result is True

    def test_duplicate_gets_zero_score(self, scorer: MintScorer) -> None:
        """Verify that score_artifact returns 0 score for duplicate content."""
        content = "Content that will be duplicated"

        # First submission
        # mock-ok: LLM calls are external API
        with patch("src.world.mint_scorer.call_llm", return_value=_mock_call_llm_result()):
            first_result = scorer.score_artifact("artifact_1", "text", content)

        # Second submission with same content
        second_result = scorer.score_artifact("artifact_2", "text", content)

        assert second_result["success"] is True
        assert second_result["score"] == 0
        assert "Duplicate" in second_result["reason"]

    def test_original_gets_scored(
        self, scorer_with_mock_llm: tuple[MintScorer, MagicMock]
    ) -> None:
        """Verify that score_artifact proceeds with LLM scoring for original content."""
        scorer, mock_llm = scorer_with_mock_llm
        content = "Original content that should be scored by LLM"

        result = scorer.score_artifact("artifact_1", "text", content)

        # Verify LLM was called
        mock_llm.assert_called_once()

        # Verify the result contains the mocked score
        assert result["success"] is True
        assert result["score"] == 75
        assert result["reason"] == "Good content"
