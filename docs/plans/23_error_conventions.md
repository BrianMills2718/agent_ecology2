# Plan #23: Error Response Conventions

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Problem

Error handling is inconsistent across the codebase:

1. **Multiple return patterns:**
   - `{"success": False, "error": "message"}` (ExecutionResult)
   - `(False, "error message")` (tuple returns in contracts.py)
   - Exceptions (some places)
   - String error messages (genesis artifacts)

2. **No error classification:**
   - Can't distinguish user errors from system errors
   - No error codes for programmatic handling
   - Agents can't easily categorize failures

3. **Inconsistent error messages:**
   - Some include context, some don't
   - No standard format for what information to include

---

## Solution

### Standard Error Response Schema

All functions that can fail should return a consistent structure:

```python
class ErrorResponse(TypedDict):
    """Standard error response format."""
    success: Literal[False]
    error_code: str          # Machine-readable (e.g., "INSUFFICIENT_FUNDS")
    error_message: str       # Human-readable description
    error_context: dict      # Optional additional details


class SuccessResponse(TypedDict):
    """Standard success response format."""
    success: Literal[True]
    result: Any              # The actual result


# Union type for all responses
Response = SuccessResponse | ErrorResponse
```

### Error Code Categories

| Prefix | Category | Example |
|--------|----------|---------|
| `AUTH_` | Permission/ownership | `AUTH_NOT_OWNER` |
| `VAL_` | Validation/input | `VAL_INVALID_AMOUNT` |
| `RES_` | Resource limits | `RES_INSUFFICIENT_FUNDS` |
| `SYS_` | System errors | `SYS_TIMEOUT` |
| `NOT_` | Not found | `NOT_ARTIFACT_MISSING` |

### Standard Error Messages

Error messages should follow format:
```
{action} failed: {reason}. {context}
```

Examples:
- "Transfer failed: insufficient funds. Required 100, available 50."
- "Invoke failed: method not found. Artifact 'genesis_ledger' has no method 'foo'."

---

## Implementation Steps

1. **Define types** in `src/world/errors.py`:
   - `ErrorResponse`, `SuccessResponse` TypedDicts
   - Error code constants
   - Helper functions to create responses

2. **Migrate executor.py**:
   - Update `ExecutionResult` to use new format
   - Add error codes to all error returns

3. **Migrate genesis.py**:
   - Update artifact methods to return standard responses
   - Add context to error messages

4. **Migrate contracts.py**:
   - Change tuple returns to standard responses

5. **Update documentation**:
   - Add error handling section to developer docs
   - Document all error codes

---

## Required Tests

- `tests/unit/test_errors.py::test_error_response_format`
- `tests/unit/test_errors.py::test_success_response_format`
- `tests/unit/test_errors.py::test_error_code_categories`
- `tests/integration/test_error_responses.py::test_executor_errors`
- `tests/integration/test_error_responses.py::test_genesis_errors`

---

## Acceptance Criteria

1. All functions that can fail return `Response` type
2. All errors include error_code from defined categories
3. All error messages follow standard format
4. Backward compatibility maintained (success field still works)
5. Tests verify all error paths

---

## Notes

This is a refactoring task. Should be done incrementally:
1. Add new types alongside existing
2. Migrate one module at a time
3. Remove old patterns after all migrated

See GAPS.md archive for detailed context.
