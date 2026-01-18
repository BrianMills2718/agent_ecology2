# Plan #90: Full Cognitive Schema Configurability

**Status:** 📋 Post-V1
**Priority:** Low
**Depends on:** Plan #88 (OODA Cognitive Logging)

## Problem Statement

Plan #88 introduces a simple toggle between "simple" and "ooda" cognitive schemas. However, baking specific cognitive models into the kernel violates the "minimal kernel, maximum flexibility" principle.

Different use cases may benefit from different cognitive structures:
- **Cost-sensitive**: Minimal output (just action)
- **Research/debugging**: Full OODA with verbose situation assessment
- **Custom agents**: Domain-specific cognitive patterns
- **Self-modifying agents**: Agents that evolve their own cognitive structure

## Vision: Configurable Cognitive Schemas

Allow arbitrary cognitive schemas to be defined in config and selected per-agent:

```yaml
# config.yaml
agent:
  cognitive_schemas:
    minimal:
      description: "Just the action, no reasoning"
      fields:
        - name: action
          type: action
          required: true

    simple:
      description: "Current default - thought process + action"
      fields:
        - name: thought_process
          type: string
          description: "Internal reasoning"
        - name: action
          type: action
          required: true

    ooda:
      description: "OODA loop - situation, rationale, action"
      fields:
        - name: situation_assessment
          type: string
          description: "Analysis of current state and options"
        - name: action_rationale
          type: string
          description: "Concise explanation (1-2 sentences)"
          max_tokens: 50  # Enforce conciseness
        - name: action
          type: action
          required: true

    pdca:
      description: "Plan-Do-Check-Act cycle"
      fields:
        - name: plan
          type: string
          description: "What I intend to accomplish"
        - name: expected_outcome
          type: string
          description: "What I expect to happen"
        - name: action
          type: action
          required: true

    custom_research:
      description: "Verbose research-oriented output"
      fields:
        - name: observations
          type: list[string]
          description: "Key observations from world state"
        - name: hypotheses
          type: list[string]
          description: "Hypotheses about what might work"
        - name: chosen_approach
          type: string
          description: "Selected approach and why"
        - name: action
          type: action
          required: true

  default_schema: "simple"
```

### Per-Agent Schema Selection

```yaml
# agents/alpha/agent.yaml
cognitive_schema: ooda  # Override default

# agents/researcher/agent.yaml
cognitive_schema: custom_research
```

### Self-Modification

Agents can modify their own cognitive schema:

```json
{
  "action_type": "write_artifact",
  "artifact_id": "alpha",
  "content": {"cognitive_schema": "minimal"}
}
```

## Implementation Approach

### Dynamic Pydantic Models

Generate Pydantic models at runtime from schema definitions:

```python
def build_response_model(schema_config: dict) -> type[BaseModel]:
    """Dynamically create a Pydantic model from schema config."""
    fields = {}
    for field in schema_config["fields"]:
        if field["type"] == "action":
            fields[field["name"]] = (ActionField, ...)
        elif field["type"] == "string":
            fields[field["name"]] = (str, Field(description=field.get("description", "")))
        elif field["type"] == "list[string]":
            fields[field["name"]] = (list[str], Field(default_factory=list))

    return create_model(f"Response_{schema_config['name']}", **fields)
```

### Prompt Generation

Auto-generate prompt instructions from schema:

```python
def generate_schema_instructions(schema_config: dict) -> str:
    """Generate prompt instructions for a cognitive schema."""
    lines = [f"Respond with a JSON object containing:"]
    for field in schema_config["fields"]:
        if field["type"] != "action":
            lines.append(f"- {field['name']}: {field.get('description', '')}")
    lines.append("- action: Your chosen action (see action schema)")
    return "\n".join(lines)
```

### Logging Adaptation

Log events adapt to schema:

```python
def log_thinking_event(response: dict, schema_config: dict):
    """Log thinking event with schema-appropriate fields."""
    event = {"tick": tick, "principal_id": agent_id}
    for field in schema_config["fields"]:
        if field["name"] != "action" and field["name"] in response:
            event[field["name"]] = response[field["name"]]
    logger.log("thinking", event)
```

### Dashboard Adaptation

Dashboard renders based on available fields:

```javascript
function renderThinkingEvent(event) {
    // Render whatever cognitive fields are present
    const cognitiveFields = ['thought_process', 'situation_assessment',
                            'action_rationale', 'observations', 'hypotheses'];
    for (const field of cognitiveFields) {
        if (event[field]) {
            renderField(field, event[field]);
        }
    }
}
```

## Validation

- Schema must have exactly one `action` field
- Field names must be valid Python identifiers
- Field types must be supported (string, list[string], action)
- Optional: `max_tokens` constraint for conciseness enforcement

## Complexity Assessment

| Component | Complexity | Notes |
|-----------|------------|-------|
| Dynamic Pydantic models | Medium | Python's `create_model()` makes this feasible |
| Prompt generation | Low | Template-based |
| Logging adaptation | Low | Just include present fields |
| Dashboard adaptation | Medium | Need flexible rendering |
| Config validation | Medium | Schema-of-schemas validation |
| Per-agent selection | Low | Already have per-agent config |
| Self-modification | Medium | Need to reload schema on agent change |

## Why Defer?

1. **Plan #88 proves value first** - Validate OODA approach before generalizing
2. **Complexity** - Dynamic models add debugging difficulty
3. **Unknown requirements** - Don't know what schemas will be useful yet
4. **Emergence focus** - V1 should focus on core emergence, not meta-configurability

## Success Criteria (Future)

- [ ] Arbitrary schemas definable in config
- [ ] Per-agent schema selection
- [ ] Self-modification of cognitive schema
- [ ] Dashboard adapts to any schema
- [ ] Logging captures all cognitive fields
- [ ] No hardcoded schema assumptions in kernel

## Related

- Plan #88: OODA Cognitive Logging (prerequisite)
- ADR-0001: Everything is an artifact (agents own themselves)
- handbook_self: Agent self-modification
