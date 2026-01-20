# Plan #128: Fix Gemini Schema for Interface Field

**Status:** 📋 Planned
**Priority:** Critical
**Blocked By:** None
**Blocks:** All agent LLM calls, thought capture, simulation functionality

## Files Affected

- src/agents/models.py (modify)
- src/world/actions.py (modify)

## Problem

ALL agent LLM calls are failing with:
```
GeminiException BadRequestError - interface.any_of[0].properties: should be non-empty for OBJECT type
```

**Impact:** ~99% of agent LLM calls fail. Agents cannot think, act, or generate thought_process. This makes the simulation non-functional.

## Root Cause

In `src/agents/models.py` line 115:
```python
interface: dict[str, Any] | None = None  # Plan #114
```

When Pydantic generates a JSON schema for Gemini structured output:
- `dict[str, Any]` becomes `{type: "object", properties: {}}`
- Gemini rejects schemas with empty properties for OBJECT type
- The `anyOf` from `Optional[dict]` triggers this validation

## Evidence

LLM logs from run_20260120_060711:
- **610 agent calls failed** with the schema error
- **2 calls succeeded** (mint scoring calls that don't use FlatActionResponse)
- All 3026 thinking events have `thought_process: ""`

Earlier runs (run_20260120_045642) worked because:
- The model was `gemini/gemini-3-flash-preview`
- Some calls succeeded before quota exhaustion or API changes

## Solution Options

### Option A: Define Interface Schema Explicitly (Recommended)

Replace `dict[str, Any]` with a properly typed schema:

```python
class InterfaceTool(BaseModel):
    """Tool definition in interface."""
    name: str
    description: str = ""
    inputSchema: dict[str, Any] = Field(default_factory=dict)

class InterfaceSchema(BaseModel):
    """Schema for executable artifact interface."""
    description: str = ""
    tools: list[InterfaceTool] = Field(default_factory=list)

class FlatAction(BaseModel):
    # ... other fields ...
    interface: InterfaceSchema | None = None
```

**Pros:** Proper typing, validation, clear structure
**Cons:** More rigid schema, may need migration

### Option B: Use JSON String Instead

```python
interface: str | None = None  # JSON string, parsed after validation
```

**Pros:** Simple, avoids schema issues
**Cons:** No validation, error-prone, loses structured benefit

### Option C: Conditional Schema Generation

Override Pydantic's JSON schema generation for the interface field:

```python
class FlatAction(BaseModel):
    interface: dict[str, Any] | None = None

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        schema = super().model_json_schema(*args, **kwargs)
        # Modify interface to have minimal properties
        if "interface" in schema.get("properties", {}):
            schema["properties"]["interface"]["anyOf"][0]["properties"] = {
                "description": {"type": "string"},
                "tools": {"type": "array"}
            }
        return schema
```

**Pros:** Keeps flexibility
**Cons:** Fragile, schema override complexity

## Recommended Approach

**Option A** - Define proper InterfaceSchema. Benefits:
1. Gemini-compatible schema
2. Better validation of interface structures
3. Clearer API contract
4. Aligns with Plan #114's intent

## Files to Modify

| File | Change |
|------|--------|
| `src/agents/models.py` | Add InterfaceSchema, InterfaceTool models |
| `src/agents/models.py` | Update FlatAction.interface type |
| `src/world/actions.py` | Update interface handling if needed |

## Testing

```bash
# Run short simulation to verify agent calls succeed
python run.py --dashboard --no-browser &
sleep 60
pkill -f "python run.py"

# Verify LLM calls succeeded
grep '"success": true' llm_logs/$(date +%Y%m%d)/*.json | grep FlatActionResponse | wc -l

# Verify thought_process captured
grep '"thinking"' logs/latest/events.jsonl | grep -v '"thought_process": ""' | wc -l
```

## Acceptance Criteria

- [ ] Agent LLM calls succeed with Gemini structured output
- [ ] thought_process is captured in >90% of thinking events
- [ ] Existing tests pass
- [ ] Interface validation still works for write_artifact

## Notes

- This is the actual root cause of what Plan #121 reported as "thought capture variance"
- Plan #121's per-agent variance data was likely from an earlier period before this bug
- The model change to gemini-2.5-flash (PR #420) didn't fix this because it's a schema issue, not a quota issue
- This is a regression from Plan #114 (Interface Discovery)
