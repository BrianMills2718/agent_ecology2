"""Oracle Scorer - Uses LLM to evaluate executable code artifacts.

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
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict

# Add llm_provider_standalone to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_provider import LLMProvider

from config import get


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


class OracleScorer:
    """Uses an LLM to score artifacts for the mock oracle.

    All settings (model, timeout, max_content_length) come from config.yaml.
    """

    llm: LLMProvider
    max_content_length: int
    _seen_hashes: set[str] = set()

    def __init__(self, model: str | None = None, log_dir: str | None = None) -> None:
        # Get config values with fallbacks
        model = model or get("oracle_scorer.model") or "gemini/gemini-3-flash-preview"
        log_dir = log_dir or get("logging.log_dir") or "llm_logs"
        timeout: int = get("oracle_scorer.timeout") or 30

        self.llm = LLMProvider(
            model=model,
            log_dir=log_dir,
            timeout=timeout
        )
        self.max_content_length: int = get("oracle_scorer.max_content_length") or 2000

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
        content: str
    ) -> ScoringResult:
        """
        Score an artifact using LLM evaluation.

        Args:
            artifact_id: The artifact's ID
            artifact_type: Type of artifact (e.g., "text", "executable")
            content: The artifact's content

        Returns:
            Dict with:
            - success: bool
            - score: int (0-100)
            - reason: str (explanation)
            - error: str (if failed)
        """
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
            # Run LLM call in thread pool to avoid async context issues
            # (litellm detects async event loop and refuses sync calls)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - run in thread pool
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.generate, prompt)
                    response_raw = future.result(timeout=60)
            except RuntimeError:
                # No async loop - call directly
                response_raw = self.llm.generate(prompt)
            response: str = str(response_raw)
        except Exception as e:
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

            # Clamp score to 0-100
            score = max(0, min(100, score))

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
_scorer: OracleScorer | None = None


def get_scorer(model: str | None = None, log_dir: str | None = None) -> OracleScorer:
    """Get or create the OracleScorer singleton.

    Model and log_dir default to config values if not specified.
    """
    global _scorer
    if _scorer is None:
        _scorer = OracleScorer(model=model, log_dir=log_dir)
    return _scorer
