# Plan 312: Expose Kernel Primitives for Agent-Built Coordination

**Status:** ✅ Complete
**Priority:** High

---

## Gap

**Current:** Agents can't build coordination patterns (like escrow) because three kernel primitives are missing or broken in the artifact execution context:
1. `has_standing` — `kernel_actions.write_artifact()` doesn't accept it, so agents can't create artifacts that hold scrip
2. `transfer` — `kernel_actions.transfer_scrip()` exists but loop code doesn't expose it in prompts or handlers
3. `invoke` — Loop code's invoke_artifact handler calls nonexistent `kernel_actions.invoke_artifact()`; also `artifact_loop.py` doesn't pass `ledger` to executor so `invoke()` global is never injected

**Target:** All three primitives work end-to-end so agents can compose basic coordination: create a principal artifact, transfer scrip to it, invoke its methods.

**Why High:** Without these, agents are stuck in a read/write/submit loop and can't build any emergent coordination.

---

## Files Affected

- `src/world/kernel_interface.py` (modify)
- `src/simulation/artifact_loop.py` (modify)
- `config/genesis/agents/discourse_analyst/loop_code.py` (modify)
- `config/genesis/agents/discourse_analyst_2/loop_code.py` (modify)
- `config/genesis/agents/discourse_analyst_3/loop_code.py` (modify)
- `config/genesis/agents/alpha_prime/loop_code.py` (modify)
- `tests/unit/test_kernel_interface.py` (modify)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/kernel_interface.py` | Add `has_standing` param to `write_artifact()`, auto-create principal |
| `src/simulation/artifact_loop.py` | Pass `ledger` to `execute_with_invoke` so `invoke()` global is injected |
| `config/genesis/agents/*/loop_code.py` | Add transfer handler, fix invoke handler, add has_standing, expand alpha_prime actions |
| `tests/unit/test_kernel_interface.py` | Tests for has_standing and invoke injection |

---

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_kernel_interface.py` | `test_write_artifact_with_has_standing_creates_principal` | has_standing creates ledger principal |
| `tests/unit/test_kernel_interface.py` | `test_write_artifact_has_standing_false_no_principal` | No principal without flag |
| `tests/unit/test_kernel_interface.py` | `test_has_standing_idempotent_on_update` | Update path is safe |
| `tests/unit/test_kernel_interface.py` | `test_invoke_available_when_ledger_passed` | invoke() works in execution context |
| `tests/unit/test_kernel_interface.py` | `test_invoke_not_available_without_ledger` | Baseline without ledger |

---

## Verification

- [x] All tests pass (1649 passed)
- [x] mypy clean
- [x] Doc-coupling passes
