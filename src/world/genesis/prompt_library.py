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
    # Plan #146 Phase 5: Additional comprehensive prompts
    "error_recovery": {
        "description": "Prompt for handling and recovering from errors",
        "template": """=== ERROR RECOVERY ===
An error occurred. Analyze and recover:

1. DIAGNOSE: What went wrong?
   - Parse the error message carefully
   - Check if it's a permission, resource, or logic error
   - Identify the root cause

2. DECIDE: What's the best recovery strategy?
   - Retry with different parameters?
   - Fall back to a simpler approach?
   - Abandon and try something else?

3. LEARN: Record this for future reference
   - Add to working memory: what caused it, how you fixed it
   - Avoid repeating the same mistake

Error recovery is progress - you learned something!
""",
        "variables": [],
        "tags": ["error-handling", "recovery", "resilience"],
    },
    "coordination_request": {
        "description": "Prompt for initiating coordination with other agents",
        "template": """=== COORDINATION REQUEST ===
You want to coordinate with another agent. Consider:

1. VALUE PROPOSITION: What do you offer?
   - What artifact or service can you provide?
   - What unique capability do you have?

2. REQUIREMENTS: What do you need?
   - Be specific about what you're requesting
   - What's the expected exchange rate?

3. MECHANISM: How will you coordinate?
   - Use genesis_escrow for trustless trades
   - Consider creating a simple contract artifact
   - Specify clear success criteria

Remember: Other agents are also trying to maximize scrip.
Make your offer attractive enough to compete.
""",
        "variables": [],
        "tags": ["coordination", "multi-agent", "trading"],
    },
    "resource_optimization": {
        "description": "Prompt for optimizing resource usage",
        "template": """=== RESOURCE OPTIMIZATION ===
Resources are scarce. Optimize your usage:

COMPUTE (per-tick):
- Minimize unnecessary LLM calls
- Use reflexes for routine decisions
- Batch operations when possible

DISK (persistent):
- Delete artifacts you don't need
- Overwrite rather than create new
- Keep content concise

SCRIP (economic):
- Track your burn rate
- Generate revenue before spending
- Save for valuable opportunities

Ask: Is this action worth its resource cost?
""",
        "variables": [],
        "tags": ["resources", "optimization", "efficiency"],
    },
    "artifact_design": {
        "description": "Prompt for designing high-quality artifacts",
        "template": """=== ARTIFACT DESIGN ===
Design artifacts that others will pay to use:

1. INTERFACE: Make it obvious
   - Clear description of what it does
   - Document input/output formats
   - Include example usage

2. RELIABILITY: Make it robust
   - Handle edge cases gracefully
   - Return meaningful error messages
   - Don't crash on bad input

3. VALUE: Make it useful
   - Solve a real problem
   - Be better than alternatives
   - Price it to encourage adoption

4. DISCOVERABILITY: Make it findable
   - Use descriptive artifact_id
   - Set appropriate type
   - Consider read_price vs invoke_price

Great artifacts generate passive income.
""",
        "variables": [],
        "tags": ["building", "design", "monetization"],
    },
    "market_analysis": {
        "description": "Prompt for analyzing market opportunities",
        "template": """=== MARKET ANALYSIS ===
Analyze the current market to find opportunities:

1. SUPPLY: What artifacts exist?
   - Use query_kernel to list artifacts
   - Check what types are common/rare
   - Note who owns what

2. DEMAND: What do agents need?
   - What services are expensive?
   - What problems have no solutions?
   - What would you pay for?

3. GAPS: Where are the opportunities?
   - Underserved niches
   - Overpriced services you could undercut
   - Complementary services to bundle

4. COMPETITION: Who else is building?
   - Watch for new artifacts
   - Track mint auction results
   - Learn from successful agents

First mover advantage matters. Act on insights quickly.
""",
        "variables": [],
        "tags": ["market", "analysis", "strategy"],
    },
    "intelligence_trading": {
        "description": "Prompt for trading cognitive artifacts (prompts, memories, workflows)",
        "template": """=== INTELLIGENCE TRADING ===
Your prompts, memories, and workflows are tradeable assets.

WHAT YOU CAN TRADE:
- Personality prompts: Your decision-making style
- Long-term memories: Your learned experiences
- Workflows: Your behavioral patterns

HOW TO TRADE:
1. Create artifact with your prompt/memory content
2. Set invoke_price or read_price
3. Use genesis_escrow for one-time sales

PRICING STRATEGY:
- Prompts that increase success rate: HIGH value
- Memories of profitable strategies: MEDIUM value
- General knowledge: LOW value (others can learn)

BUYING INTELLIGENCE:
- Look for agents with high success rates
- Check their prompt/memory artifacts
- Test before paying full price

Your experiences have value. Monetize them!
""",
        "variables": [],
        "tags": ["intelligence", "trading", "memory", "prompts"],
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
