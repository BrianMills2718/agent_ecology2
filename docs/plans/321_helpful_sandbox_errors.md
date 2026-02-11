# Plan #321: Helpful Sandbox Error Messages

**Status:** ✅ Complete

## Context

V3 smoke test simulation revealed agents encountering errors that give no guidance on how to fix them. The #1 blocker: agents write `kernel.read_artifact()` (hallucinated API) and get a bare `NameError: name 'kernel' is not defined` — no hint about the correct sandbox API names (`kernel_state`, `kernel_actions`, `invoke`, etc.).

Error audit found 7 error categories across the codebase, with varying quality:
- Good: invoke_handler errors already suggest alternatives (e.g., "use kernel_actions.read_artifact()")
- Bad: NameError gives no hint, transfer errors show no amounts, unknown action errors don't list valid actions

## Changes

### 1. `src/world/executor.py` — NameError hints in `_format_runtime_error()`

Added `NameError` case with sandbox API listing. Special-case hints for common hallucinations:
- `kernel` → "Use kernel_state for reads, kernel_actions for writes"
- `world` / `World` → "Use kernel_state / kernel_actions"
- `state` / `self` → "Artifacts are stateless functions; store state via write_artifact"
- Any other → Lists full sandbox API

Also fixed 3 occurrences of `f"Argument error: {e}"` to use `_format_runtime_error(e, "Argument error")` so TypeError hints apply everywhere.

### 2. `src/world/permission_checker.py` — Unknown action lists valid actions

3 "Unknown action" errors now append: `"Valid actions: read, write, edit, invoke, delete"`

### 3. `src/world/kernel_interface.py` — Transfer errors show amounts

- `transfer_scrip`: "Insufficient balance" → "Insufficient balance: have {balance} scrip, need {amount}"
- `transfer_resource`: "Insufficient resource" → "Insufficient {resource}: have {current}, need {amount}"
- `transfer_quota`: Same pattern
- "Invalid amount" → "Invalid amount: {amount}. Amount must be positive"

### 4. `docs/architecture/current/artifacts_executor.md` — Doc coupling update

Added paragraph documenting the helpful error message system.

### 5. `tests/unit/test_executor.py` — 4 new tests

- `test_kernel_name_error_shows_correct_api`
- `test_world_name_error_shows_correct_api`
- `test_generic_name_error_shows_sandbox_api`
- `test_argument_error_uses_hint_system`

## Files Modified

| File | Change |
|------|--------|
| `src/world/executor.py` | NameError hints + TypeError fix |
| `src/world/permission_checker.py` | Valid actions in unknown-action errors |
| `src/world/kernel_interface.py` | Amounts in transfer errors |
| `docs/architecture/current/artifacts_executor.md` | Doc coupling |
| `tests/unit/test_executor.py` | 4 new tests |

## Verification

- 1680 tests pass, 2 pre-existing failures (v3 fixture counts)
- New tests verify NameError hints contain correct API names
