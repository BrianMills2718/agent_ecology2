"""Thin LLM client wrapping litellm (Plan #311).

Three functions, no class, no mutable state:
- call_llm: basic completion
- call_llm_structured: instructor-based Pydantic extraction
- call_llm_with_tools: tool/function calling

Cost returned per-call as a value, not stored as mutable state.
Retry delegated to litellm's num_retries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Silence litellm's noisy default logging
litellm.suppress_debug_info = True


@dataclass
class LLMCallResult:
    """Result from an LLM call. Returned by all call_llm* functions."""

    content: str
    usage: dict[str, Any]
    cost: float
    model: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def _is_claude_model(model: str) -> bool:
    """Check if model string refers to a Claude model."""
    return "claude" in model.lower() or "anthropic" in model.lower()


def _extract_usage(response: Any) -> dict[str, Any]:
    """Extract token usage dict from litellm response."""
    usage = response.usage
    return {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


def _compute_cost(response: Any) -> float:
    """Compute cost via litellm.completion_cost, with fallback."""
    try:
        cost = float(litellm.completion_cost(completion_response=response))
        return cost
    except Exception:
        # Fallback: rough estimate based on total tokens
        total: int = response.usage.total_tokens
        fallback = total * 0.000001  # $1 per million tokens as rough floor
        logger.warning(
            "completion_cost failed, using fallback: $%.6f for %d tokens",
            fallback,
            total,
        )
        return fallback


def _extract_tool_calls(message: Any) -> list[dict[str, Any]]:
    """Extract tool calls from response message into plain dicts."""
    if not message.tool_calls:
        return []
    result: list[dict[str, Any]] = []
    for tc in message.tool_calls:
        result.append({
            "id": tc.id,
            "type": tc.type,
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        })
    return result


def call_llm(
    model: str,
    messages: list[dict[str, Any]],
    *,
    timeout: int = 60,
    num_retries: int = 2,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> LLMCallResult:
    """Call LLM via litellm.completion.

    Args:
        model: Model name (e.g., "gpt-4", "anthropic/claude-3-opus")
        messages: Chat messages in OpenAI format
        timeout: Request timeout in seconds
        num_retries: Number of retries on failure
        reasoning_effort: Reasoning effort level (Claude models only)
        **kwargs: Additional params passed to litellm.completion

    Returns:
        LLMCallResult with content, usage, cost, and model
    """
    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
        "num_retries": num_retries,
        **kwargs,
    }

    # Only pass reasoning_effort for Claude models
    if reasoning_effort and _is_claude_model(model):
        call_kwargs["reasoning_effort"] = reasoning_effort
    elif reasoning_effort:
        logger.debug(
            "reasoning_effort=%s ignored for non-Claude model %s",
            reasoning_effort,
            model,
        )

    response = litellm.completion(**call_kwargs)

    content: str = response.choices[0].message.content or ""
    usage = _extract_usage(response)
    cost = _compute_cost(response)
    tool_calls = _extract_tool_calls(response.choices[0].message)

    logger.debug(
        "LLM call: model=%s tokens=%d cost=$%.6f",
        model,
        usage["total_tokens"],
        cost,
    )

    return LLMCallResult(
        content=content,
        usage=usage,
        cost=cost,
        model=model,
        tool_calls=tool_calls,
    )


def call_llm_structured(
    model: str,
    messages: list[dict[str, Any]],
    response_model: type[T],
    *,
    timeout: int = 60,
    num_retries: int = 2,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> tuple[T, LLMCallResult]:
    """Call LLM with structured output via instructor.

    Uses instructor.from_litellm() for reliable Pydantic extraction
    across all providers.

    Args:
        model: Model name
        messages: Chat messages in OpenAI format
        response_model: Pydantic model class for structured extraction
        timeout: Request timeout in seconds
        num_retries: Number of retries on failure
        reasoning_effort: Reasoning effort level (Claude models only)
        **kwargs: Additional params passed to litellm.completion

    Returns:
        Tuple of (parsed Pydantic model, LLMCallResult)
    """
    import instructor

    client = instructor.from_litellm(litellm.completion)

    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_model": response_model,
        "timeout": timeout,
        "max_retries": num_retries,
        **kwargs,
    }

    # Only pass reasoning_effort for Claude models
    if reasoning_effort and _is_claude_model(model):
        call_kwargs["reasoning_effort"] = reasoning_effort

    result, raw_response = client.chat.completions.create_with_completion(
        **call_kwargs,
    )

    usage = _extract_usage(raw_response)
    cost = _compute_cost(raw_response)
    content = str(result.model_dump_json())

    llm_result = LLMCallResult(
        content=content,
        usage=usage,
        cost=cost,
        model=model,
    )

    return result, llm_result


def call_llm_with_tools(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    *,
    timeout: int = 60,
    num_retries: int = 2,
    reasoning_effort: str | None = None,
    **kwargs: Any,
) -> LLMCallResult:
    """Call LLM with tool/function calling support.

    Args:
        model: Model name
        messages: Chat messages in OpenAI format
        tools: Tool definitions in OpenAI format
        timeout: Request timeout in seconds
        num_retries: Number of retries on failure
        reasoning_effort: Reasoning effort level (Claude models only)
        **kwargs: Additional params passed to litellm.completion

    Returns:
        LLMCallResult with tool_calls populated if model chose to use tools
    """
    return call_llm(
        model,
        messages,
        timeout=timeout,
        num_retries=num_retries,
        reasoning_effort=reasoning_effort,
        tools=tools,
        **kwargs,
    )
