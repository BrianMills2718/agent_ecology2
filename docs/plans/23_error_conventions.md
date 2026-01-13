# Gap 23: Error Response Conventions

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No standard error format. Errors returned as `{"success": False, "error": "message"}` inconsistently.

**Target:** Consistent error response schema with error codes and categories.

---

## Problem Statement

Artifact invocations currently return errors as simple dictionaries:
```python
{"success": False, "error": "Some error message"}
```

Issues with current approach:
1. **No error codes** - Can't programmatically distinguish error types
2. **No categories** - Hard to know if error is user's fault or system's fault
3. **Inconsistent fields** - Some add extra context, some don't
4. **No retry guidance** - No way to know if error is retriable

Agents need to:
- Know if they caused the error (validation) vs system issue (timeout)
- Know if they should retry
- Identify specific error conditions for recovery logic

---

## Plan

### Phase 1: Define Error Schema

**1.1 ErrorResponse Dataclass**

```python
# src/world/errors.py

from dataclasses import dataclass
from enum import Enum

class ErrorCategory(str, Enum):
    """Categories for error classification."""
    VALIDATION = "validation"      # Invalid input, bad arguments
    PERMISSION = "permission"      # Not authorized, wrong owner
    RESOURCE = "resource"          # Not found, already exists
    EXECUTION = "execution"        # Runtime error, timeout
    SYSTEM = "system"              # Internal error, unexpected

class ErrorCode(str, Enum):
    """Specific error codes for programmatic handling."""
    # Validation errors
    MISSING_ARGUMENT = "missing_argument"
    INVALID_ARGUMENT = "invalid_argument"
    INVALID_TYPE = "invalid_type"

    # Permission errors
    NOT_OWNER = "not_owner"
    NOT_AUTHORIZED = "not_authorized"
    INSUFFICIENT_FUNDS = "insufficient_funds"

    # Resource errors
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    ALREADY_LISTED = "already_listed"

    # Execution errors
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"
    SYNTAX_ERROR = "syntax_error"

    # System errors
    INTERNAL_ERROR = "internal_error"
    NOT_CONFIGURED = "not_configured"

@dataclass
class ErrorResponse:
    """Standardized error response."""
    success: bool = False  # Always False for errors
    error: str = ""        # Human-readable message
    code: str = ""         # Machine-readable error code
    category: str = ""     # Error category (validation, permission, etc.)
    retriable: bool = False  # Whether the operation should be retried
    details: dict | None = None  # Optional additional context

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "success": self.success,
            "error": self.error,
            "code": self.code,
            "category": self.category,
            "retriable": self.retriable,
        }
        if self.details:
            result["details"] = self.details
        return result
```

**1.2 Error Factory Functions**

```python
def validation_error(message: str, code: ErrorCode = ErrorCode.INVALID_ARGUMENT, **details) -> dict:
    """Create a validation error response."""
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.VALIDATION.value,
        retriable=False,
        details=details or None,
    ).to_dict()

def permission_error(message: str, code: ErrorCode = ErrorCode.NOT_AUTHORIZED, **details) -> dict:
    """Create a permission error response."""
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.PERMISSION.value,
        retriable=False,
        details=details or None,
    ).to_dict()

def resource_error(message: str, code: ErrorCode = ErrorCode.NOT_FOUND, **details) -> dict:
    """Create a resource error response."""
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.RESOURCE.value,
        retriable=False,
        details=details or None,
    ).to_dict()

def execution_error(message: str, code: ErrorCode = ErrorCode.RUNTIME_ERROR, retriable: bool = False, **details) -> dict:
    """Create an execution error response."""
    return ErrorResponse(
        error=message,
        code=code.value,
        category=ErrorCategory.EXECUTION.value,
        retriable=retriable,
        details=details or None,
    ).to_dict()
```

### Phase 2: Migrate Genesis Artifacts

Update genesis artifacts to use new error helpers:

**Before:**
```python
return {"success": False, "error": "transfer requires [from_id, to_id, amount]"}
```

**After:**
```python
return validation_error(
    "transfer requires [from_id, to_id, amount]",
    code=ErrorCode.MISSING_ARGUMENT,
    required=["from_id", "to_id", "amount"],
)
```

### Phase 3: Backwards Compatibility

The new schema is backwards compatible:
- Still has `success` and `error` fields
- New `code`, `category`, `retriable` fields are additive
- Existing code checking `result["success"]` continues to work

### Implementation Steps

1. **Create `src/world/errors.py`** - ErrorResponse, ErrorCode, ErrorCategory, factory functions
2. **Update genesis_ledger** - Use new error helpers
3. **Update genesis_mint** - Use new error helpers
4. **Update genesis_escrow** - Use new error helpers
5. **Update genesis_store** - Use new error helpers
6. **Update executor** - Use new error helpers for code execution
7. **Add tests** - Unit tests for error helpers
8. **Update docs** - Document error schema

---

## Required Tests

### Unit Tests
- `tests/unit/test_errors.py::test_validation_error_format` - Correct structure
- `tests/unit/test_errors.py::test_permission_error_format` - Correct structure
- `tests/unit/test_errors.py::test_error_to_dict` - Serialization works
- `tests/unit/test_errors.py::test_error_code_enum` - All codes valid
- `tests/unit/test_errors.py::test_backwards_compatible` - Has success/error fields

### Integration Tests
- `tests/integration/test_genesis_errors.py::test_ledger_error_format` - Ledger returns new format
- `tests/integration/test_genesis_errors.py::test_escrow_error_format` - Escrow returns new format

---

## E2E Verification

Invoke genesis artifact with invalid arguments and verify error format:

```bash
python -c "
from src.world.genesis import GenesisLedger
ledger = GenesisLedger()
result = ledger.invoke('transfer', [], 'alice')
print(result)
assert 'code' in result
assert 'category' in result
"
```

---

## Out of Scope

- **Exception hierarchy** - Keep using dict returns for now
- **Retry logic** - Just provide `retriable` flag, let callers decide
- **Error logging changes** - Existing logging remains
- **Dashboard error UI** - Future enhancement

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This is a quality-of-life improvement that enables better agent error handling.

Key design decisions:
- **Dict-based, not exceptions** - Matches existing pattern
- **Backwards compatible** - Existing code keeps working
- **Simple enums** - Easy to extend
- **Factory functions** - Less boilerplate

See also:
- `src/world/genesis.py` - Current error patterns
- `src/world/executor.py` - Code execution errors
