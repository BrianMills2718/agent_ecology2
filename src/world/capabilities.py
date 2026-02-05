"""External Capabilities Manager - Plan #300

Manages access to external services that cost real money and require human approval.

Key concepts:
- Capabilities are external APIs (embeddings, payments, etc.) that cost real $
- Agents can REQUEST capabilities, but humans must APPROVE them
- Once approved (API key in config), agents can USE the capability
- All usage is logged and tracked against optional budget limits

This is NOT a kernel primitive per API - it's ONE mechanism for all external capabilities.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.world.world import World


class CapabilityManager:
    """Manages external capability configuration and usage.

    Capabilities are external services that:
    - Cost real money (not internal scrip/quota)
    - Require API keys or credentials
    - Need human approval before use

    The manager handles:
    - Checking if capabilities are configured/enabled
    - Executing capability actions
    - Tracking spend against budget limits
    - Logging all requests and usage
    """

    def __init__(self, world: World, config: dict[str, Any]) -> None:
        """Initialize capability manager.

        Args:
            world: World instance for logging and state
            config: external_capabilities section from config.yaml
        """
        self._world = world
        self._capabilities = config or {}
        # Track spend per capability (in-memory, reset on restart)
        self._spend: dict[str, float] = {}

    def is_enabled(self, name: str) -> bool:
        """Check if a capability is configured and enabled.

        Args:
            name: Capability name (e.g., "openai_embeddings")

        Returns:
            True if capability exists in config and enabled=True
        """
        cap = self._capabilities.get(name)
        if not cap:
            return False
        return cap.get("enabled", False)

    def get_config(self, name: str) -> dict[str, Any] | None:
        """Get configuration for a capability.

        Args:
            name: Capability name

        Returns:
            Capability config dict or None if not found
        """
        return self._capabilities.get(name)

    def get_api_key(self, name: str) -> str | None:
        """Get API key for a capability, resolving env vars.

        Args:
            name: Capability name

        Returns:
            API key string or None if not configured
        """
        cap = self._capabilities.get(name)
        if not cap:
            return None

        api_key = cap.get("api_key")
        if not api_key:
            return None

        # Resolve environment variable references like ${OPENAI_API_KEY}
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            return os.environ.get(env_var)

        return api_key

    def get_budget_limit(self, name: str) -> float | None:
        """Get budget limit for a capability.

        Args:
            name: Capability name

        Returns:
            Budget limit in dollars, or None if unlimited
        """
        cap = self._capabilities.get(name)
        if not cap:
            return None
        return cap.get("budget_limit")

    def get_current_spend(self, name: str) -> float:
        """Get current spend for a capability.

        Args:
            name: Capability name

        Returns:
            Total spend so far (resets on restart)
        """
        return self._spend.get(name, 0.0)

    def track_spend(self, name: str, amount: float) -> bool:
        """Track spend against a capability's budget.

        Args:
            name: Capability name
            amount: Amount to add to spend

        Returns:
            True if within budget, False if would exceed limit
        """
        limit = self.get_budget_limit(name)
        current = self.get_current_spend(name)

        if limit is not None and current + amount > limit:
            return False

        self._spend[name] = current + amount
        return True

    def execute(
        self,
        name: str,
        action: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a capability action.

        This dispatches to capability-specific implementations.

        Args:
            name: Capability name
            action: Action to perform (capability-specific)
            params: Action parameters

        Returns:
            {"success": True, "result": ...} or {"success": False, "error": ...}
        """
        if not self.is_enabled(name):
            return {
                "success": False,
                "error": f"Capability '{name}' is not enabled",
                "error_code": "NOT_ENABLED",
            }

        api_key = self.get_api_key(name)
        if not api_key:
            return {
                "success": False,
                "error": f"Capability '{name}' has no API key configured",
                "error_code": "NO_API_KEY",
            }

        config = self.get_config(name)
        if not config:
            return {
                "success": False,
                "error": f"Capability '{name}' not found",
                "error_code": "NOT_FOUND",
            }

        # Dispatch to capability-specific handler
        handler = _CAPABILITY_HANDLERS.get(name)
        if not handler:
            return {
                "success": False,
                "error": f"No handler for capability '{name}'",
                "error_code": "NO_HANDLER",
            }

        try:
            return handler(config, api_key, action, params)
        except Exception as e:
            logger.exception("Capability '%s' execution failed", name)
            return {
                "success": False,
                "error": f"Capability execution failed: {str(e)}",
                "error_code": "EXECUTION_ERROR",
            }

    def list_capabilities(self) -> list[dict[str, Any]]:
        """List all configured capabilities and their status.

        Returns:
            List of capability info dicts
        """
        result = []
        for name, config in self._capabilities.items():
            has_key = self.get_api_key(name) is not None
            result.append({
                "name": name,
                "enabled": config.get("enabled", False),
                "has_api_key": has_key,
                "budget_limit": config.get("budget_limit"),
                "current_spend": self.get_current_spend(name),
            })
        return result


# =============================================================================
# CAPABILITY HANDLERS
# =============================================================================
# Each capability has a handler function that implements its actions.
# Add new capabilities by adding handlers here.


def _handle_openai_embeddings(
    config: dict[str, Any],
    api_key: str,
    action: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle OpenAI embeddings capability.

    Actions:
        embed: Get embedding for text
            params: {"text": str} or {"texts": list[str]}
            returns: {"embedding": list[float]} or {"embeddings": list[list[float]]}
    """
    if action != "embed":
        return {
            "success": False,
            "error": f"Unknown action '{action}' for openai_embeddings",
            "error_code": "UNKNOWN_ACTION",
        }

    try:
        import openai
    except ImportError:
        return {
            "success": False,
            "error": "openai package not installed. Use kernel_actions.install_library('openai')",
            "error_code": "MISSING_DEPENDENCY",
        }

    model = config.get("model", "text-embedding-3-small")
    client = openai.OpenAI(api_key=api_key)

    # Handle single text or batch
    text = params.get("text")
    texts = params.get("texts")

    if text:
        response = client.embeddings.create(model=model, input=text)
        return {
            "success": True,
            "embedding": response.data[0].embedding,
            "model": model,
            "dimensions": len(response.data[0].embedding),
        }
    elif texts:
        response = client.embeddings.create(model=model, input=texts)
        embeddings = [d.embedding for d in response.data]
        return {
            "success": True,
            "embeddings": embeddings,
            "model": model,
            "dimensions": len(embeddings[0]) if embeddings else 0,
            "count": len(embeddings),
        }
    else:
        return {
            "success": False,
            "error": "Missing 'text' or 'texts' parameter",
            "error_code": "MISSING_PARAM",
        }


def _handle_anthropic_api(
    config: dict[str, Any],
    api_key: str,
    action: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Handle Anthropic API capability (separate from configured LLM).

    Actions:
        chat: Send a message to Claude
            params: {"messages": list[dict], "model": str (optional)}
            returns: {"response": str, "usage": dict}
    """
    if action != "chat":
        return {
            "success": False,
            "error": f"Unknown action '{action}' for anthropic_api",
            "error_code": "UNKNOWN_ACTION",
        }

    try:
        import anthropic
    except ImportError:
        return {
            "success": False,
            "error": "anthropic package not installed. Use kernel_actions.install_library('anthropic')",
            "error_code": "MISSING_DEPENDENCY",
        }

    model = params.get("model", config.get("model", "claude-3-haiku-20240307"))
    messages = params.get("messages", [])

    if not messages:
        return {
            "success": False,
            "error": "Missing 'messages' parameter",
            "error_code": "MISSING_PARAM",
        }

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=params.get("max_tokens", 1024),
        messages=messages,
    )

    # Extract text from first content block
    response_text = ""
    if response.content and hasattr(response.content[0], "text"):
        response_text = response.content[0].text  # type: ignore[union-attr]

    return {
        "success": True,
        "response": response_text,
        "model": model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }


# Registry of capability handlers
_CAPABILITY_HANDLERS: dict[str, Any] = {
    "openai_embeddings": _handle_openai_embeddings,
    "anthropic_api": _handle_anthropic_api,
}


def register_capability_handler(name: str, handler: Any) -> None:
    """Register a custom capability handler.

    This allows extending the system with new capabilities without
    modifying this file.

    Args:
        name: Capability name
        handler: Handler function(config, api_key, action, params) -> dict
    """
    _CAPABILITY_HANDLERS[name] = handler
