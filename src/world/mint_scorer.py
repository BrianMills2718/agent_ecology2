"""Mint Scorer - Uses LLM to evaluate executable code artifacts.

Scores submitted code on quality and utility criteria:
- Correctness and functionality
- Usefulness (solves a real problem)
- Code structure and readability
- Error handling
- Originality (duplicate detection via content hash)

All configuration (model, timeout, max_content_length) comes from config.yaml.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypedDict

from .llm_client import call_llm
from ..config import get, get_validated_config


SCORING_PROMPT: str = """You are evaluating executable code submitted to an agent marketplace.
Rate this code on quality and utility.

Consider:
- Does it solve a real, useful problem?
- Is the code correct and functional?
- Is it well-structured and readable?
- Does it handle errors appropriately?
- Is it original (not trivial or boilerplate)?

Code to evaluate:
---
Artifact ID: {artifact_id}
Type: {artifact_type}
Code: {content}
---

Respond with ONLY a JSON object in this exact format:
{{"score": <number 0-100>, "reason": "<brief explanation>"}}

Score guidelines:
- 0-10: Broken, trivial, or useless (e.g., empty function, syntax errors)
- 11-30: Minimal utility, poor quality
- 31-50: Basic functionality, some utility
- 51-70: Solid tool, good quality
- 71-90: Excellent utility, well-crafted
- 91-100: Exceptional - innovative, high-value tool

Respond with ONLY the JSON object.
"""


class ScoringResult(TypedDict, total=False):
    """Result from artifact scoring."""
    success: bool
    score: int
    reason: str
    error: str


class MintScorer:
    """Uses an LLM to score artifacts for the mint.

    All settings (model, timeout, max_content_length) come from config.yaml.
    """

    model: str
    timeout: int
    max_content_length: int
    last_cost: float  # Cost of most recent LLM call (for mint_auction tracking)
    _seen_hashes: set[str] = set()

    def __init__(self, model: str | None = None, log_dir: str | None = None) -> None:
        # Get config values with fallbacks
        self.model = model or get("mint_scorer.model") or "gemini/gemini-3-flash-preview"
        self.timeout = get("mint_scorer.timeout") or 30
        self.max_content_length = get("mint_scorer.max_content_length") or 2000
        self.last_cost = 0.0

    def _compute_content_hash(self, content: str) -> str:
        """Compute MD5 hash of content for duplicate detection."""
        # Normalize: strip whitespace, lowercase
        normalized = content.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def is_original(self, content: str) -> bool:
        """Check if content is original (not seen before)."""
        content_hash = self._compute_content_hash(content)
        return content_hash not in self._seen_hashes

    def score_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        is_budget_exhausted: Callable[[], bool] | None = None,
    ) -> ScoringResult:
        """
        Score an artifact using LLM evaluation.

        Args:
            artifact_id: The artifact's ID
            artifact_type: Type of artifact (e.g., "text", "executable")
            content: The artifact's content
            is_budget_exhausted: Optional callback to check if budget is exhausted

        Returns:
            Dict with:
            - success: bool
            - score: int (0-100)
            - reason: str (explanation)
            - error: str (if failed)
        """
        # Check budget before making LLM call (defense in depth)
        if is_budget_exhausted is not None and is_budget_exhausted():
            return {
                "success": False,
                "score": 0,
                "reason": "",
                "error": "LLM budget exhausted - scoring skipped"
            }

        # Check for duplicate content (originality check)
        content_hash = self._compute_content_hash(content)
        if content_hash in self._seen_hashes:
            return {
                "success": True,
                "score": 0,
                "reason": "Duplicate content - no originality reward",
                "error": ""
            }
        # Mark as seen for future duplicate detection
        self._seen_hashes.add(content_hash)

        # Truncate very long content
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "... [truncated]"

        prompt = SCORING_PROMPT.format(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=content
        )

        try:
            messages = [{"role": "user", "content": prompt}]

            # Run LLM call in thread pool to avoid async context issues
            # (litellm detects async event loop and refuses sync calls)
            try:
                asyncio.get_running_loop()
                # We're in an async context - run in thread pool
                config = get_validated_config()
                workers = config.mint_scorer.thread_pool_workers
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    future = executor.submit(
                        call_llm, self.model, messages, timeout=self.timeout
                    )
                    llm_result = future.result(timeout=60)
            except RuntimeError:
                # No async loop - call directly
                llm_result = call_llm(self.model, messages, timeout=self.timeout)

            self.last_cost = llm_result.cost
            response: str = llm_result.content
        except Exception as e:  # exception-ok: LLM scoring can fail any way
            return {
                "success": False,
                "score": 0,
                "reason": "",
                "error": f"LLM call failed: {e}"
            }

        # Parse the response
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines: list[str] = []
                in_block = False
                for line in lines:
                    if line.startswith("```") and not in_block:
                        in_block = True
                        continue
                    elif line.startswith("```") and in_block:
                        break
                    elif in_block:
                        json_lines.append(line)
                response = "\n".join(json_lines)

            start = response.find("{")
            end = response.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found")

            data: dict[str, int | str] = json.loads(response[start:end])
            score = int(data.get("score", 0))
            reason = str(data.get("reason", ""))

            # Clamp score to configured bounds
            config = get_validated_config()
            score_min = config.mint_scorer.score_bounds.min
            score_max = config.mint_scorer.score_bounds.max
            score = max(score_min, min(score_max, score))

            return {
                "success": True,
                "score": score,
                "reason": reason,
                "error": ""
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            return {
                "success": False,
                "score": 0,
                "reason": "",
                "error": f"Failed to parse LLM response: {e}"
            }


# Singleton instance
_scorer: MintScorer | None = None


def get_scorer(model: str | None = None, log_dir: str | None = None) -> MintScorer:
    """Get or create the MintScorer singleton.

    Model and log_dir default to config values if not specified.
    """
    global _scorer
    if _scorer is None:
        _scorer = MintScorer(model=model, log_dir=log_dir)
    return _scorer
