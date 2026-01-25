# Plan #187: Extended Thinking for Genesis Agents

**Status:** ✅ Complete
**Priority:** Medium
**Complexity:** Medium
**Blocks:** Improved agent reasoning quality

## Problem

Genesis agents make decisions in a single LLM call without extended reasoning. Claude's `reasoning_effort` parameter enables "thinking time" before responding, which improves complex decision quality. Currently:

1. LLMProvider doesn't pass `reasoning_effort` to LiteLLM
2. No config option to enable extended thinking
3. Agents can't benefit from deeper reasoning on complex decisions

## Solution

Add `reasoning_effort` parameter support throughout the LLM call chain.

### Config Options

```yaml
# In config.yaml
llm:
  reasoning_effort: "none"          # "none" | "low" | "medium" | "high"
  # Note: Only works with Anthropic Claude models
```

### Implementation

1. **LLMProvider**: Add `reasoning_effort` parameter to `generate()` and `generate_async()`
2. **Agent**: Pass `reasoning_effort` from config to LLMProvider calls
3. **Config**: Add `llm.reasoning_effort` option
4. **Cost tracking**: Track reasoning tokens separately (already supported in token tracking)

### Code Changes

```python
# In LLMProvider.generate_async():
async def generate_async(
    self,
    prompt: str | dict,
    response_model: type[T] | None = None,
    reasoning_effort: str | None = None,  # NEW
    **kwargs
) -> T | str:
    # ... existing code ...

    if reasoning_effort and reasoning_effort != "none":
        # Only pass to Anthropic models
        if "anthropic" in self.model or "claude" in self.model:
            completion_kwargs["reasoning_effort"] = reasoning_effort

# In Agent.propose_action():
reasoning_effort = self.config.get("llm", {}).get("reasoning_effort", "none")
response = await self.llm.generate_async(
    prompt=prompt,
    response_model=FlatActionResponse,
    reasoning_effort=reasoning_effort,
)
```

## Files Affected

- llm_provider_standalone/llm_provider.py (modify) - Add reasoning_effort parameter
- src/agents/agent.py (modify) - Pass reasoning_effort to LLM calls
- src/config_schema.py (modify) - Add reasoning_effort to LLMConfig
- config/schema.yaml (modify) - Document reasoning_effort option
- config/config.yaml (modify) - Add default value
- tests/unit/test_reasoning_effort.py (create) - Unit tests for reasoning_effort
- docs/GLOSSARY.md (modify) - Add reasoning_effort term
- docs/architecture/current/configuration.md (modify) - Document LLM config option

## Testing

1. Verify reasoning_effort passed to LiteLLM for Claude models
2. Verify reasoning_effort ignored for non-Claude models
3. Verify token tracking includes reasoning tokens
4. Test with reasoning_effort: "high" produces more thoughtful responses

## Acceptance Criteria

1. Config option `llm.reasoning_effort` available
2. Parameter passed through to Anthropic API
3. Reasoning tokens tracked in cost accounting
4. No impact on non-Anthropic models

## Risks

- **Cost explosion**: Extended thinking is 5-10x more expensive
- **Token limits**: Claude has lower output limits with extended thinking
- **Model-specific**: Only works with Anthropic Claude models

## Mitigation

- Default to "none" (disabled)
- Add pre-flight cost estimate before expensive calls
- Log warning if reasoning_effort used with non-Claude model
