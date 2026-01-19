# Plan 86: Interface Validation

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** #14 (Artifact Interface Schema) - ✅ Complete
**Blocks:** None

---

## Gap

**Current:** Artifact interfaces (added in Plan #14) are declarative only. No runtime validation that invocations match declared schemas. Interfaces can lie without consequence.

**Target:** Optional validation that artifact invocations match their declared interface schemas, with configurable enforcement modes.

**Why:** Interface validation enables:
- Early detection of interface/invocation mismatches
- Observability for interface trustworthiness (selection pressure)
- Better debugging when artifacts are called incorrectly
- Foundation for reputation systems based on interface honesty

---

## Design

### Validation Modes (Config)

```yaml
executor:
  interface_validation: warn  # Options: none, warn, strict
```

| Mode | Behavior |
|------|----------|
| `none` | No validation - trust interfaces |
| `warn` | Log warning if args don't match schema, proceed anyway |
| `strict` | Reject invoke if args don't match schema |

### What Gets Validated

1. **Input arguments against inputSchema** - Are args compatible with declared schema?
2. **Method existence** - Does the invoked method exist in interface?
3. **Required fields** - Are all required parameters provided?

### Implementation Approach

| Component | Change |
|-----------|--------|
| `config/schema.yaml` | Add `executor.interface_validation` option |
| `src/config_schema.py` | Add validation mode to ExecutorConfig |
| `src/world/executor.py` | Add `validate_args_against_interface()` function |
| `src/world/world.py` | Call validation before invoke execution |

---

## Files Affected

- config/schema.yaml (modify)
- config/config.yaml (modify)
- src/config_schema.py (modify)
- src/world/executor.py (modify)
- src/world/world.py (modify)
- tests/unit/test_interface_validation.py (create)
- docs/architecture/current/artifacts_executor.md (modify)
- docs/architecture/current/configuration.md (modify)
- requirements.txt (modify)

---

## Required Tests

| Test | Description |
|------|-------------|
| `tests/unit/test_interface_validation.py::test_validation_mode_none_skips_check` | No validation when mode is none |
| `tests/unit/test_interface_validation.py::test_validation_mode_warn_logs_mismatch` | Warning logged when args don't match |
| `tests/unit/test_interface_validation.py::test_validation_mode_strict_rejects_mismatch` | Invoke rejected when args don't match |
| `tests/unit/test_interface_validation.py::test_valid_args_pass_validation` | Correct args pass validation |
| `tests/unit/test_interface_validation.py::test_missing_required_field_detected` | Missing required field caught |
| `tests/unit/test_interface_validation.py::test_no_interface_skips_validation` | Artifacts without interface skip validation |

---

## Implementation Steps

1. Add config option for validation mode
2. Create `validate_args_against_interface()` in executor.py
3. Integrate validation into invoke path in world.py
4. Add tests for all validation modes
5. Update documentation

---

## Notes

- Uses jsonschema library (already a dependency via Pydantic)
- Default to `warn` mode for observability without breaking changes
- Strict mode useful for testing and debugging
- Future: Could add interface vs code consistency checking (inspect function signatures)
