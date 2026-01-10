"""Mock Oracle Scorer - Uses LLM to estimate engagement score

Simulates external feedback (like Reddit upvotes) by having an LLM
evaluate artifact quality and estimate likely engagement.

This is a mock for testing the external minting mechanism without
requiring actual Reddit API integration.

All configuration (model, timeout, max_content_length) comes from config.yaml.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add llm_provider_standalone to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'llm_provider_standalone'))

from llm_provider import LLMProvider

# Add src to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get


SCORING_PROMPT = """You are evaluating content that was submitted to a community platform.
Rate this content on how much engagement (upvotes) it would likely receive.

Consider:
- Is it useful, interesting, or entertaining?
- Is it well-written and clear?
- Would people want to share or discuss it?
- Is it original or creative?

Content to evaluate:
---
Title/ID: {artifact_id}
Type: {artifact_type}
Content: {content}
---

Respond with ONLY a JSON object in this exact format:
{{"score": <number 0-100>, "reason": "<brief explanation>"}}

Score guidelines:
- 0-10: Low quality, spam, or unhelpful
- 11-30: Mediocre, nothing special
- 31-50: Decent, some value
- 51-70: Good, engaging content
- 71-90: Excellent, high quality
- 91-100: Exceptional, viral potential

Respond with ONLY the JSON object.
"""


class OracleScorer:
    """Uses an LLM to score artifacts for the mock oracle.

    All settings (model, timeout, max_content_length) come from config.yaml.
    """

    def __init__(self, model: str = None, log_dir: str = None):
        # Get config values with fallbacks
        model = model or get("oracle_scorer.model") or "gemini/gemini-2.0-flash"
        log_dir = log_dir or get("logging.log_dir") or "llm_logs"
        timeout = get("oracle_scorer.timeout") or 30

        self.llm = LLMProvider(
            model=model,
            log_dir=log_dir,
            timeout=timeout
        )
        self.max_content_length = get("oracle_scorer.max_content_length") or 2000

    def score_artifact(self, artifact_id: str, artifact_type: str, content: str) -> Dict[str, Any]:
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
        # Truncate very long content
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "... [truncated]"

        prompt = SCORING_PROMPT.format(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=content
        )

        try:
            response = self.llm.generate(prompt)
        except Exception as e:
            return {
                "success": False,
                "score": 0,
                "reason": "",
                "error": f"LLM call failed: {e}"
            }

        # Parse the response
        import json
        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
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

            data = json.loads(response[start:end])
            score = int(data.get("score", 0))
            reason = data.get("reason", "")

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
_scorer = None


def get_scorer(model: str = None, log_dir: str = None) -> OracleScorer:
    """Get or create the OracleScorer singleton.

    Model and log_dir default to config values if not specified.
    """
    global _scorer
    if _scorer is None:
        _scorer = OracleScorer(model=model, log_dir=log_dir)
    return _scorer
