# Plan #40: ActionResult Error Integration

**Status:** ✅ Complete

**Verified:** 2026-01-14T07:27:41Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T07:27:41Z
tests:
  unit: 1241 passed, 1 skipped in 15.58s
  e2e_smoke: PASSED (1.98s)
  doc_coupling: passed
commit: eef887a
```

**Priority:** High
**Blocked By:** None (Plan #23 error infrastructure complete)
**Blocks:** None

---

## Problem

Plan #23 established error response conventions (ErrorCode, ErrorCategory, ErrorResponse), but **agents don't receive structured errors through the narrow waist**.

Current flow:
```
genesis_ledger._transfer()
  → returns {"success": False, "code": "insufficient_funds", ...}  # ✅ Has error code
world._execute_invoke()
  → ActionResult(success=False, message="...", data=result_data)   # ❌ No error_code field
Agent receives ActionResult.to_dict()
  → {"success": false, "message": "...", "data": {...}}            # ❌ Error code buried in data
```

**Consequences:**
1. Agents can't programmatically categorize errors (must parse strings)
2. Can't determine if error is retriable
3. Inconsistent error format across read/write/invoke actions
4. Agents can't adjust behavior based on error type

---

## Solution

### Extend ActionResult

Add error fields to ActionResult that surface structured error info:

```python
@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None
    resources_consumed: dict[str, float] | None = None
    charged_to: str | None = None
    # NEW: Structured error fields
    error_code: str | None = None           # e.g., "insufficient_funds"
    error_category: str | None = None       # e.g., "resource"
    retriable: bool = False                 # Can agent retry?
    error_details: dict[str, Any] | None = None  # Additional context
```

### Update Narrow Waist Actions

All three action types must populate error fields:

#### read_artifact errors
| Error | Code | Category | Retriable |
|-------|------|----------|-----------|
| Artifact not found | `not_found` | resource | No |
| Access denied | `not_authorized` | permission | No |
| Artifact deleted | `deleted` | resource | No |
| Insufficient scrip for read_price | `insufficient_funds` | resource | Yes |

#### write_artifact errors
| Error | Code | Category | Retriable |
|-------|------|----------|-----------|
| Cannot modify genesis | `not_authorized` | permission | No |
| Write permission denied | `not_authorized` | permission | No |
| Disk quota exceeded | `quota_exceeded` | resource | Yes |
| Invalid executable code | `invalid_argument` | validation | No |

#### invoke_artifact errors
| Error | Code | Category | Retriable |
|-------|------|----------|-----------|
| Artifact not found | `not_found` | resource | No |
| Artifact deleted | `deleted` | resource | No |
| Not executable | `invalid_type` | validation | No |
| Method not found | `not_found` | resource | No |
| Insufficient compute | `insufficient_funds` | resource | Yes |
| Insufficient scrip | `insufficient_funds` | resource | Yes |
| Permission denied | `not_authorized` | permission | No |
| Execution timeout | `timeout` | execution | Yes |
| Runtime error | `runtime_error` | execution | No |

---

## Implementation Steps

1. **Extend ActionResult** in `src/world/actions.py`:
   - Add `error_code`, `error_category`, `retriable`, `error_details` fields
   - Update `to_dict()` to include new fields when present
   - Maintain backward compatibility (success/message still work)

2. **Update `_execute_read`** in `src/world/world.py`:
   - Use ErrorCode constants for all error paths
   - Populate ActionResult error fields

3. **Update `_execute_write`** in `src/world/world.py`:
   - Use ErrorCode constants for all error paths
   - Populate ActionResult error fields

4. **Update `_execute_invoke`** in `src/world/world.py`:
   - Extract error info from genesis artifact responses
   - Use ErrorCode constants for executor errors
   - Populate ActionResult error fields

5. **Update tests**:
   - Test ActionResult error field population
   - Test error code consistency across all action types
   - Test retriability flags

6. **Update documentation**:
   - Document error codes for each action type
   - Add to target architecture docs

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_action_result_errors.py` | ActionResult error fields unit tests |
| `tests/integration/test_narrow_waist_errors.py` | Narrow waist error handling integration tests |

---

## Acceptance Criteria

1. ActionResult includes `error_code`, `error_category`, `retriable` fields
2. All read_artifact errors populate structured error fields
3. All write_artifact errors populate structured error fields
4. All invoke_artifact errors populate structured error fields
5. Genesis artifact error codes are surfaced (not buried in data)
6. Backward compatibility maintained (success/message still work)
7. Tests verify all error paths for all three action types

---

## Design Rationale

**Why extend ActionResult vs nest ErrorResponse?**
- ActionResult is already the contract between World and agents
- Extending is simpler than nesting and checking two levels
- Flat structure easier for agents to consume

**Why retriable flag?**
- Agents need to know: should I retry or give up?
- Resource errors (quota, funds) may resolve after waiting
- Permission errors won't change without external action

**Why error_details?**
- Some errors need context (e.g., "required 100, have 50")
- Agents can use this for smarter retry logic

---

## Notes

This completes the error response work started in Plan #23. After this:
- Agents receive structured errors through the narrow waist
- All three action types have consistent error format
- Agents can programmatically handle errors and adjust behavior
