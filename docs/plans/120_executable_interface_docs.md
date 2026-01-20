# Plan #120: Document Executable Interface Requirement

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Agent ability to create executables, mint submissions

## Files Affected

- src/agents/_handbook/actions.md (modify)
- src/agents/_handbook/tools.md (modify)

## Problem

Agents are trying to create executable artifacts but failing with:
```
"Interface schema required for executable artifact 'gamma_3_hash_verifier'.
Provide an interface dict with 'description' and 'tools' keys describing
the artifact's methods and their input schemas."
```

**Root cause**: The handbooks (`actions.md`, `tools.md`) show examples of creating executables WITHOUT the required `interface` field. Agents follow these examples and fail.

Current documentation shows:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Description",
  "executable": true,
  "code": "def run(*args):\n    return {'result': 'hello'}"
}
```

But the system requires:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Description",
  "executable": true,
  "code": "def run(*args):\n    return {'result': 'hello'}",
  "interface": {
    "description": "What this service does",
    "tools": [
      {
        "name": "run",
        "description": "Main entry point",
        "inputSchema": {
          "type": "object",
          "properties": {
            "arg1": {"type": "string", "description": "First argument"}
          }
        }
      }
    ]
  }
}
```

## Impact

- **4 mint auctions with zero submissions** - agents can't create executables
- **gamma_3 and delta_3 both failed** to create artifacts they designed
- **No economic activity** - can't build → can't mint → can't earn

## Solution

Update handbook documentation to include the required `interface` field in all executable examples.

## Changes

### 1. Update `src/agents/_handbook/actions.md`

Add interface to the executable example (lines 18-29):

```json
{
  "action_type": "write_artifact",
  "artifact_id": "<id>",
  "artifact_type": "executable",
  "content": "Description of what it does",
  "executable": true,
  "price": 5,
  "code": "def run(x, y):\n    return {'sum': x + y}",
  "interface": {
    "description": "Adds two numbers together",
    "tools": [{
      "name": "run",
      "description": "Add two numbers",
      "inputSchema": {
        "type": "object",
        "properties": {
          "x": {"type": "number", "description": "First number"},
          "y": {"type": "number", "description": "Second number"}
        },
        "required": ["x", "y"]
      }
    }]
  }
}
```

Also update the pricing example (lines 52-63) with interface.

### 2. Update `src/agents/_handbook/tools.md`

Add interface to Basic Structure section (lines 7-19):

```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Description for discovery",
  "executable": true,
  "code": "def run(*args):\n    return {'result': 'hello'}",
  "interface": {
    "description": "Returns a greeting",
    "tools": [{
      "name": "run",
      "description": "Get a hello message",
      "inputSchema": {"type": "object", "properties": {}}
    }]
  },
  "policy": {
    "invoke_price": 5,
    "allow_invoke": ["*"]
  }
}
```

Update the table (lines 22-27) to include interface:

| Field | Purpose |
|-------|---------|
| `executable: true` | Marks this as runnable code |
| `code` | Python code with a `run(*args)` function |
| `interface` | **REQUIRED** - Describes methods and input schemas |
| `invoke_price` | Scrip charged per invocation (paid to you) |
| `allow_invoke` | Who can call it |

### 3. Add new section to `tools.md`: "Defining Your Interface"

Add after the Basic Structure section:

```markdown
## Defining Your Interface (REQUIRED)

Every executable MUST include an `interface` field describing how to call it:

### Minimal Interface
```json
"interface": {
  "description": "What your service does",
  "tools": [{
    "name": "run",
    "description": "Main method",
    "inputSchema": {"type": "object", "properties": {}}
  }]
}
```

### Interface with Arguments
```json
"interface": {
  "description": "Validates artifact content",
  "tools": [{
    "name": "run",
    "description": "Check if artifact is valid",
    "inputSchema": {
      "type": "object",
      "properties": {
        "artifact_id": {
          "type": "string",
          "description": "ID of artifact to validate"
        }
      },
      "required": ["artifact_id"]
    }
  }]
}
```

### Why Interface is Required

1. **Discovery** - Other agents use `genesis_store.get_interface()` to learn how to call your service
2. **Validation** - System validates inputs match your schema
3. **Documentation** - Your interface IS your API documentation

**Without an interface, your executable will not be created.**
```

### 4. Update agent system prompts (optional enhancement)

Consider adding a reminder to agent prompts that executable artifacts require interface. This is a secondary improvement.

## Files Modified

| File | Change |
|------|--------|
| `src/agents/_handbook/actions.md` | Add interface to executable examples |
| `src/agents/_handbook/tools.md` | Add interface to examples, add "Defining Your Interface" section |

## Testing

### Manual Verification
1. Run simulation for ~2 minutes
2. Check if agents successfully create executables
3. Check if mint has submissions

### Automated Test
```python
def test_handbook_executable_examples_have_interface():
    """Verify all executable examples in handbooks include interface field."""
    actions = Path("src/agents/_handbook/actions.md").read_text()
    tools = Path("src/agents/_handbook/tools.md").read_text()

    # Find JSON blocks with executable: true
    # Verify they all have interface field
    ...
```

## Acceptance Criteria

- [ ] All executable examples in `actions.md` include `interface` field
- [ ] All executable examples in `tools.md` include `interface` field
- [ ] New "Defining Your Interface" section added to `tools.md`
- [ ] Agents can successfully create executable artifacts
- [ ] Mint receives submissions

## Notes

- This is the highest-impact fix for getting productive agent behavior
- The interface requirement exists for good reasons (discovery, validation)
- We're fixing documentation, not changing system behavior
