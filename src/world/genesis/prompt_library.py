"""Genesis Prompt Library - Tradeable prompt templates (Plan #146 Phase 2)

Provides a library of prompt templates that agents can:
1. Read and use for their own behavior
2. Fork and modify (by creating their own prompt artifacts)
3. Trade (by selling prompt artifacts)

This enables emergent sharing of successful strategies.
"""

from __future__ import annotations

import logging
from typing import Any

from ...config_schema import GenesisConfig
from .base import GenesisArtifact

logger = logging.getLogger(__name__)


# Default prompt templates - agents can use these or create their own
DEFAULT_PROMPTS: dict[str, dict[str, Any]] = {
    "observe_base": {
        "description": "Base observation prompt for gathering context",
        "template": """=== OBSERVATION PHASE ===
Gather context before acting. Consider:
- What do you know about the current situation?
- What information do you need?
- Check your memory for relevant past experiences.

Available actions: read_artifact, query_kernel, invoke
""",
        "variables": [],
        "tags": ["observation", "context-gathering"],
    },
    "ideate_base": {
        "description": "Base ideation prompt for generating ideas",
        "template": """=== IDEATION PHASE ===
Generate ideas for creating value. Consider:
- What problems exist that you could solve?
- What do other agents need that doesn't exist yet?
- What skills or knowledge could you monetize?

Focus on ideas that can be implemented as artifacts.
""",
        "variables": [],
        "tags": ["ideation", "creativity"],
    },
    "implement_base": {
        "description": "Base implementation prompt for building artifacts",
        "template": """=== IMPLEMENTATION PHASE ===
Build your artifact. Remember:
- def run(*args) is the entry point for executable artifacts
- Set invoke_price > 0 to earn scrip when others use it
- Write clean code with clear error messages
- Test edge cases in your logic

Use write_artifact to create or update your artifact.
""",
        "variables": [],
        "tags": ["implementation", "building"],
    },
    "reflect_base": {
        "description": "Base reflection prompt for learning from outcomes",
        "template": """=== REFLECTION PHASE ===
Learn from your recent actions. Consider:
- What worked well? Why?
- What failed? What could you do differently?
- What patterns are emerging in your behavior?
- Should you adjust your strategy?

Record insights to your working memory for future reference.
""",
        "variables": [],
        "tags": ["reflection", "learning"],
    },
    "trading_base": {
        "description": "Base trading prompt for market interactions",
        "template": """=== TRADING PHASE ===
Engage with the market. Consider:
- What artifacts are available for purchase?
- What do you have that others might want?
- Is the price fair for the value provided?

Use genesis_escrow for safe trades.
""",
        "variables": [],
        "tags": ["trading", "market"],
    },
    "meta_learning": {
        "description": "Meta-learning prompt for improving decision-making",
        "template": """=== META-LEARNING ===
Before deciding, review your working memory for lessons learned.
After outcomes, record what worked or failed.

Pattern: Observe -> Hypothesize -> Act -> Learn -> Repeat

Key questions:
- What have I tried before in similar situations?
- What were the outcomes?
- How can I improve this time?
""",
        "variables": [],
        "tags": ["meta-learning", "self-improvement"],
    },
}


class GenesisPromptLibrary(GenesisArtifact):
    """Genesis artifact providing prompt templates for agents.

    This enables agents to:
    - Access proven prompt patterns
    - Fork and customize prompts for their needs
    - Share successful prompts as tradeable artifacts

    Methods:
    - list: List available prompts with optional tag filter
    - get: Get a specific prompt template by ID
    - get_template: Get just the template text (for direct use)
    """

    _prompts: dict[str, dict[str, Any]]

    def __init__(self, genesis_config: GenesisConfig | None = None) -> None:
        """Initialize the prompt library.

        Args:
            genesis_config: Optional genesis configuration
        """
        artifact_id = "genesis_prompt_library"
        description = "Library of prompt templates for agent behavior patterns"

        super().__init__(
            artifact_id=artifact_id,
            description=description
        )
        self._prompts = DEFAULT_PROMPTS.copy()

        # Register methods (all free - no cost to read prompts)
        self.register_method(
            name="list",
            handler=self._method_list,
            cost=0,
            description="List available prompts with optional tag filter. Args: [tag (optional)]"
        )
        self.register_method(
            name="get",
            handler=self._method_get,
            cost=0,
            description="Get full prompt data. Args: [prompt_id]"
        )
        self.register_method(
            name="get_template",
            handler=self._method_get_template,
            cost=0,
            description="Get template text with optional variable substitution. Args: [prompt_id, variables (optional dict)]"
        )

    def _method_list(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        """List available prompts.

        Args (optional):
            tag: Filter by tag (e.g., "observation", "trading")

        Returns:
            List of prompt summaries with id, description, tags
        """
        tag_filter = args[0] if args else None

        results = []
        for prompt_id, prompt_data in self._prompts.items():
            # Apply tag filter if specified
            if tag_filter and tag_filter not in prompt_data.get("tags", []):
                continue

            results.append({
                "id": prompt_id,
                "description": prompt_data.get("description", ""),
                "tags": prompt_data.get("tags", []),
                "variables": prompt_data.get("variables", []),
            })

        return {
            "success": True,
            "prompts": results,
            "count": len(results),
        }

    def _method_get(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        """Get a specific prompt template with all metadata.

        Args:
            prompt_id: ID of the prompt to retrieve

        Returns:
            Full prompt data including template, description, tags, variables
        """
        if not args:
            return {"success": False, "error": "prompt_id required"}

        prompt_id = str(args[0])
        prompt_data = self._prompts.get(prompt_id)

        if not prompt_data:
            return {
                "success": False,
                "error": f"Prompt '{prompt_id}' not found",
                "available": list(self._prompts.keys()),
            }

        return {
            "success": True,
            "prompt_id": prompt_id,
            **prompt_data,
        }

    def _method_get_template(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        """Get just the template text for a prompt.

        Args:
            prompt_id: ID of the prompt
            variables: Optional dict of variable values to substitute

        Returns:
            The template text, optionally with variables filled in
        """
        if not args:
            return {"success": False, "error": "prompt_id required"}

        prompt_id = str(args[0])
        variables = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}

        prompt_data = self._prompts.get(prompt_id)
        if not prompt_data:
            return {
                "success": False,
                "error": f"Prompt '{prompt_id}' not found",
            }

        template = prompt_data.get("template", "")

        # Substitute variables if provided
        if variables:
            try:
                template = template.format(**variables)
            except KeyError as e:
                return {
                    "success": False,
                    "error": f"Missing variable: {e}",
                    "required_variables": prompt_data.get("variables", []),
                }

        return {
            "success": True,
            "template": template,
        }

    def get_interface(self) -> dict[str, Any]:
        """Get the interface description for this artifact."""
        return {
            "artifact_id": "genesis_prompt_library",
            "description": "Library of prompt templates for agent behavior patterns",
            "methods": {
                "list": {
                    "description": "List available prompts with optional tag filter",
                    "args": ["tag (optional)"],
                    "returns": "List of prompt summaries",
                    "cost": 0,
                },
                "get": {
                    "description": "Get full prompt data including template and metadata",
                    "args": ["prompt_id"],
                    "returns": "Prompt data with template, description, tags, variables",
                    "cost": 0,
                },
                "get_template": {
                    "description": "Get just the template text, optionally with variables filled",
                    "args": ["prompt_id", "variables (optional dict)"],
                    "returns": "Template text ready to use",
                    "cost": 0,
                },
            },
            "available_prompts": list(self._prompts.keys()),
        }
