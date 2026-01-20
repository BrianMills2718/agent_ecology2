# Plan #138: Provider-Level Union Schema Transformation

**Status:** 📋 Deferred (until problems arise with Plan #137)
**Priority:** Low
**Blocked By:** Plan #137 must show problems first
**Blocks:** None

## Context

This plan describes an alternative approach to handling Gemini's structured output limitations. It is **deferred** because Plan #137 implements a simpler solution (always use flat models). This plan should only be implemented if Plan #137's approach causes issues.

## Problem (if Plan #137 fails)

If always using `FlatActionResponse` causes problems (e.g., validation issues, schema bloat affecting LLM quality, or need for true type discrimination), we would need a provider-level solution.

## Alternative Approach: Schema Transform in Provider

Instead of maintaining separate Pydantic models (ActionResponse vs FlatActionResponse), the `llm_provider_standalone` could automatically transform union schemas for Gemini.

### How It Would Work

1. **Detect union schemas** - Check if response_model's JSON schema contains `anyOf`/`oneOf`
2. **Flatten for Gemini** - Merge all union variants into single object with all properties optional
3. **Parse response** - LLM returns flat JSON
4. **Reconstruct typed variant** - Use discriminator field (e.g., `action_type`) to instantiate correct Pydantic class

### Implementation Sketch

```python
# In llm_provider.py

def _flatten_union_schema(self, schema: dict) -> tuple[dict, dict]:
    """Flatten anyOf/oneOf union into single object schema.

    Returns:
        (flattened_schema, variant_map) where variant_map maps
        discriminator values to their original schemas
    """
    if 'anyOf' not in schema and 'oneOf' not in schema:
        return schema, {}

    variants = schema.get('anyOf') or schema.get('oneOf')
    all_properties = {}
    variant_map = {}

    for variant in variants:
        # Get discriminator value (e.g., action_type: "noop")
        discriminator = self._get_discriminator_value(variant)
        variant_map[discriminator] = variant

        # Merge properties
        for prop, prop_schema in variant.get('properties', {}).items():
            if prop not in all_properties:
                all_properties[prop] = prop_schema

    flattened = {
        'type': 'object',
        'properties': all_properties,
        'required': []  # Make all optional since variants differ
    }

    return flattened, variant_map

def _reconstruct_from_flat(self, flat_data: dict, variant_map: dict,
                           discriminator_field: str = 'action_type') -> BaseModel:
    """Reconstruct typed Pydantic model from flat response."""
    discriminator = flat_data.get(discriminator_field)
    if discriminator in variant_map:
        # Get the original model class for this variant
        model_class = self._get_model_for_discriminator(discriminator)
        return model_class(**flat_data)
    raise ValueError(f"Unknown discriminator: {discriminator}")
```

### Challenges

1. **Nested unions** - `ArgValue = str | int | float | bool | None` also creates anyOf
2. **Discriminator detection** - Need to identify which field discriminates variants
3. **Model reconstruction** - Need mapping from discriminator values to Pydantic classes
4. **Testing complexity** - Must test all providers with all union variants

## Why Deferred

Plan #137's approach (always use FlatActionResponse) is:
- Simpler - no schema transformation logic
- Tested - flat models already work with all providers
- Explicit - code is clear about what schema is used

This plan adds complexity that's only justified if flat models cause problems.

## When to Revisit

Implement this plan if:
1. Flat models cause LLM quality issues (too many irrelevant fields confuse the model)
2. Type discrimination is needed at parse time (not just after conversion)
3. Schema size becomes a problem (unlikely with current action types)

## Files That Would Be Affected

- llm_provider_standalone/llm_provider.py (major changes)
- src/agents/agent.py (remove flat model usage, use union models)
- src/agents/models.py (could remove Flat* classes)
- tests/ (new tests for schema transformation)

## References

- Plan #137: Agent Improvements (the active implementation)
- Plan #128: Gemini Schema Interface Fix (original Gemini workarounds)
- StructGPT paper: Iterative Reading-then-Reasoning framework context
