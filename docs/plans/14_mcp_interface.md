# Gap 14: MCP-Style Artifact Interface

**Status:** ✅ Complete

**Verified:** 2026-01-14T06:35:02Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T06:35:02Z
tests:
  unit: 1218 passed, 1 skipped in 15.10s
  e2e_smoke: PASSED (2.17s)
  doc_coupling: passed
commit: 228f2e4
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No formal interface field on artifacts. Executable artifacts use `run(*args)` with untyped positional arguments.

**Target:** Executable artifacts have MCP-compatible schema describing their interface (inputs, outputs, description).

---

## Problem Statement

Currently, artifact invocation is loosely typed:

```python
# Current: No schema, just positional args
result = executor.execute(code, args=["arg1", 42, {"key": "value"}])

# Agent-created artifacts define run(*args) with no type info
def run(*args):
    # Caller must know what args to pass
    ...
```

Problems:
1. **Discovery**: Agents can't learn what parameters an artifact expects
2. **Validation**: No way to validate inputs before execution
3. **Documentation**: No structured way to describe artifact behavior
4. **Interop**: Incompatible with MCP tool protocol

MCP tools define schemas:
```json
{
  "name": "calculator",
  "description": "Performs arithmetic",
  "inputSchema": {
    "type": "object",
    "properties": {
      "operation": {"type": "string", "enum": ["add", "subtract"]},
      "a": {"type": "number"},
      "b": {"type": "number"}
    },
    "required": ["operation", "a", "b"]
  }
}
```

---

## Plan

### Phase 1: Add Interface Field to Artifact

Extend the `Artifact` dataclass:

```python
@dataclass
class Artifact:
    ...
    interface: dict[str, Any] | None = None  # MCP-compatible schema
```

Schema structure (MCP-compatible):
```python
interface = {
    "description": "What this artifact does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
            "param2": {"type": "number"}
        },
        "required": ["param1"]
    },
    "outputSchema": {  # Optional
        "type": "object",
        "properties": {...}
    }
}
```

### Phase 2: Update Genesis Artifacts

Add interface schemas to genesis artifacts:

```python
class GenesisLedger:
    def _get_interface(self) -> dict:
        return {
            "methods": {
                "get_balance": {
                    "description": "Get scrip balance for a principal",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "principal_id": {"type": "string"}
                        },
                        "required": ["principal_id"]
                    }
                },
                "transfer": {
                    "description": "Transfer scrip to another principal",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string"},
                            "amount": {"type": "integer", "minimum": 1}
                        },
                        "required": ["to", "amount"]
                    }
                }
            }
        }
```

### Phase 3: Schema Validation (Optional)

Add optional validation on invoke:

```python
def validate_args(interface: dict, args: dict) -> tuple[bool, str | None]:
    """Validate args against inputSchema."""
    # Use jsonschema library or simple type checking
    ...
```

Configuration:
```yaml
executor:
  validate_artifact_args: true  # Enable/disable validation
```

### Phase 4: Interface Discovery

Add method to query artifact interface:

```python
# In World or genesis_store
def get_artifact_interface(artifact_id: str) -> dict | None:
    """Get the interface schema for an artifact."""
    artifact = self.artifacts.get(artifact_id)
    if artifact:
        return artifact.interface
    return None
```

Expose via genesis_store:
```python
genesis_store.get_interface(artifact_id) -> interface dict
```

---

## Changes Required

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Add `interface` field to Artifact |
| `src/world/genesis.py` | Add interface schemas to genesis artifacts |
| `src/world/executor.py` | Optional: Add schema validation |
| `config/schema.yaml` | Add `validate_artifact_args` option |
| `docs/architecture/current/artifacts_executor.md` | Document interface schema |

---

## Required Tests

### Unit Tests
- `test_artifact_interface.py::test_interface_field_optional` - Interface can be None
- `test_artifact_interface.py::test_interface_schema_structure` - Valid schema format
- `test_artifact_interface.py::test_genesis_has_interfaces` - All genesis artifacts have schemas

### Integration Tests
- `test_artifact_interface.py::test_interface_discovery` - Can query artifact interface
- `test_artifact_interface.py::test_validation_rejects_bad_args` - Invalid args rejected (if validation enabled)

---

## E2E Verification

```bash
# Run simulation, check that genesis artifacts expose interfaces
python -c "
from src.world import World
w = World({...})
ledger = w.genesis_artifacts['genesis_ledger']
print(ledger.get_interface())
"
```

---

## Backward Compatibility

- `interface` field defaults to None - existing artifacts work unchanged
- Validation is opt-in via config
- Agent-created artifacts without interface field continue to work

---

## Verification

- [x] Tests pass (7 tests in test_artifact_interface.py)
- [x] Docs updated (artifacts_executor.md)
- [x] Genesis artifacts have interface schemas (GenesisLedger implemented)
- [ ] Interface discoverable via genesis_store (Phase 4 - future)

---

## Notes

This is foundational for agent interoperability. With schemas:
- Agents can discover what artifacts do before invoking
- LLMs can generate correct invocation arguments
- Validation catches errors early

The schema format follows MCP tool protocol for future compatibility with external MCP servers.

Not implementing full JSON Schema validation initially - start with the data model, add validation later if needed.
