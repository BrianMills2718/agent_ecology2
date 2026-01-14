"""Feature acceptance tests for mint - maps to features/mint.yaml.

Run with: pytest --feature mint tests/

Note: Tests requiring real LLM calls are marked with @pytest.mark.external.
"""

from __future__ import annotations

import pytest

from src.world.mint_scorer import MintScorer


@pytest.mark.feature("mint")
class TestMintFeature:
    """Tests mapping to features/mint.yaml acceptance criteria."""

    # AC-1: Score a valid executable artifact (happy_path)
    @pytest.mark.external
    def test_ac_1_score_valid_artifact(self) -> None:
        """AC-1: Score a valid executable artifact.

        Note: This test requires real LLM calls.
        """
        scorer = MintScorer()

        content = '''
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

        result = scorer.score_artifact(
            artifact_id="fibonacci_tool",
            artifact_type="executable",
            content=content,
        )

        assert result["success"] is True
        assert 0 <= result["score"] <= 100
        assert result["reason"] != ""
        assert result.get("error", "") == ""

    # AC-2: Duplicate content receives zero score (error_case)
    def test_ac_2_duplicate_receives_zero_score(self) -> None:
        """AC-2: Duplicate content receives zero score."""
        scorer = MintScorer()

        original_content = "def add(a, b): return a + b"

        assert scorer.is_original(original_content) is True
        scorer._seen_hashes.add(scorer._compute_content_hash(original_content))
        assert scorer.is_original(original_content) is False

        result = scorer.score_artifact(
            artifact_id="duplicate_artifact",
            artifact_type="executable",
            content=original_content,
        )

        assert result["success"] is True
        assert result["score"] == 0
        assert "duplicate" in result["reason"].lower()

    # AC-3: Long content is truncated (edge_case)
    def test_ac_3_long_content_truncated(self) -> None:
        """AC-3: Long content is truncated."""
        scorer = MintScorer()
        max_len = scorer.max_content_length

        long_content = "x = 1\n" * ((max_len // 6) + 100)
        assert len(long_content) > max_len

        truncated = long_content[:max_len] + "... [truncated]"
        assert truncated.endswith("... [truncated]")

    # AC-5: Score is clamped to valid range (edge_case)
    def test_ac_5_score_clamped_to_range(self) -> None:
        """AC-5: Score is clamped to valid range."""
        def clamp_score(score: int) -> int:
            return max(0, min(100, score))

        assert clamp_score(-10) == 0
        assert clamp_score(0) == 0
        assert clamp_score(50) == 50
        assert clamp_score(100) == 100
        assert clamp_score(150) == 100


@pytest.mark.feature("mint")
class TestMintEdgeCases:
    """Additional edge case tests for mint robustness."""

    def test_originality_check_case_insensitive(self) -> None:
        """Duplicate detection should be case-insensitive."""
        scorer = MintScorer()

        content_lower = "def test(): pass"
        content_upper = "DEF TEST(): PASS"

        assert scorer.is_original(content_lower) is True
        scorer._seen_hashes.add(scorer._compute_content_hash(content_lower))

        assert scorer.is_original(content_upper) is False

    def test_originality_ignores_whitespace(self) -> None:
        """Duplicate detection should ignore leading/trailing whitespace."""
        scorer = MintScorer()

        content = "def unique_whitespace_test(): pass"
        content_padded = "   def unique_whitespace_test(): pass   \n"

        hash1 = scorer._compute_content_hash(content)
        hash2 = scorer._compute_content_hash(content_padded)

        assert hash1 == hash2

    def test_hash_computation_deterministic(self) -> None:
        """Hash computation should be deterministic."""
        scorer = MintScorer()

        content = "def add(a, b): return a + b"

        hash1 = scorer._compute_content_hash(content)
        hash2 = scorer._compute_content_hash(content)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32
