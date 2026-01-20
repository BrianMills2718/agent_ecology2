# Gap 111: Genesis Deprivilege Audit

**Status:** 🚧 In Progress
**Priority:** **High**
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Genesis artifacts have privileged access to kernel internals that agent-built artifacts cannot obtain. For example, `genesis_ledger` holds a direct `self.ledger` reference and can call methods like `create_principal()` directly. Agent-built artifacts only receive `KernelState` and `KernelActions` interfaces.

**Target:** Genesis artifacts should use the exact same `KernelState`/`KernelActions` interfaces available to all artifacts. Any capability a genesis artifact needs must be exposed through these interfaces. The simulation should work with full capabilities even with zero genesis artifacts (other than genesis agents).

**Why High:** This violates a core philosophy principle: "Genesis artifacts use the same kernel interfaces as agent-built artifacts. They're cold-start conveniences, not special code." Privileged genesis artifacts prevent agents from building equivalent functionality and reduce emergence.

---

## References Reviewed

- `src/world/genesis/ledger.py:184-203` - `_spawn_principal()` uses `self.ledger.create_principal()` directly
- `src/world/genesis/mint.py` - May have privileged `self.ledger` access
- `src/world/genesis/escrow.py` - Uses `self.artifact_store` for ownership operations
- `src/world/genesis/store.py` - Direct `self.artifact_store` reference
- `src/world/genesis/rights_registry.py` - May have privileged access patterns
- `src/world/kernel_interface.py` - Defines KernelState/KernelActions available to artifacts
- `docs/architecture/current/genesis_artifacts.md` - Documents genesis philosophy
- `CLAUDE.md` - "Genesis Artifacts Are Not Privileged" principle

---

## Files Affected

- src/world/kernel_interface.py (modify) - Add missing capability methods
- src/world/genesis/ledger.py (modify) - Remove privileged access, use KernelActions
- src/world/genesis/mint.py (modify) - Audit and remove privileges
- src/world/genesis/escrow.py (modify) - Audit and remove privileges
- src/world/genesis/store.py (modify) - Audit and remove privileges
- src/world/genesis/rights_registry.py (modify) - Audit and remove privileges
- tests/unit/test_genesis_unprivileged.py (create) - Verify no privileged access

---

## Plan

### Phase 1: Audit All Genesis Artifacts

Identify every privileged access pattern:

| Genesis Artifact | Privileged Access Found | Required KernelActions Method |
|------------------|-------------------------|-------------------------------|
| `genesis_ledger` | `self.ledger.create_principal()` | `kernel_actions.create_principal()` |
| `genesis_ledger` | `self.ledger.all_balances()` | `kernel_state.get_all_balances()` |
| `genesis_mint` | Direct ledger credit | `kernel_actions.credit_principal()` (inflation) |
| `genesis_escrow` | `self.artifact_store.transfer_ownership()` | `kernel_actions.transfer_ownership()` |
| `genesis_store` | `self.artifact_store` direct access | Already uses KernelActions |
| `genesis_rights_registry` | TBD - audit required | TBD |

### Phase 2: Extend KernelState/KernelActions

Add missing methods that genesis artifacts need:

**KernelState (read-only):**
- `get_all_balances() -> dict[str, Decimal]` - List all principal balances
- `get_all_resources(resource: str) -> dict[str, float]` - All principals' resource allocations
- `list_all_principals() -> list[str]` - All registered principals

**KernelActions (write):**
- `create_principal(principal_id: str, starting_scrip: Decimal = 0) -> bool`
- `transfer_ownership(artifact_id: str, new_owner: str) -> bool`

**Decision: Minting stays kernel-only.** Inflation control is fundamental economics that should not be delegable. Minting is triggered by kernel (auction system), not by artifacts.

### Phase 3: Migrate Genesis Artifacts

For each genesis artifact:
1. Replace `self.ledger` with `kernel_state` / `kernel_actions`
2. Replace `self.artifact_store` with kernel interface methods
3. Remove any direct references to kernel internals
4. Verify behavior unchanged via existing tests

### Phase 4: Verification Test

Create a test that runs a minimal simulation with:
- Zero genesis artifacts loaded
- Agents start with only kernel-provided capabilities
- Verify agents can still: create artifacts, transfer scrip, discover each other

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_genesis_unprivileged.py` | `test_ledger_uses_kernel_when_world_set` | genesis_ledger uses KernelActions when _world is set |
| `tests/unit/test_genesis_unprivileged.py` | `test_mint_delegates_to_kernel` | genesis_mint delegates to kernel primitives |
| `tests/unit/test_genesis_unprivileged.py` | `test_escrow_uses_kernel_when_world_set` | genesis_escrow uses KernelActions when _world is set |
| `tests/unit/test_genesis_unprivileged.py` | `test_store_uses_kernel_interface` | genesis_store has no privileged write calls |
| `tests/unit/test_genesis_unprivileged.py` | `test_genesis_artifacts_can_work_with_kernel_only` | Genesis artifacts can work with kernel interfaces only |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_ledger.py` | Ledger behavior preserved |
| `tests/integration/test_escrow.py` | Escrow behavior preserved |
| `tests/integration/test_runner.py` | Simulation runner unchanged |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agents use standard kernel capabilities | 1. Disable genesis artifacts in config 2. Run simulation with agents 3. Verify agents can transfer, discover | Agents function without genesis |

```bash
# Run E2E verification
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 111`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [ ] `docs/architecture/current/genesis_artifacts.md` updated
- [ ] `docs/architecture/current/kernel_interface.md` updated (if exists)
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

**Why not delegate minting?** Scrip inflation is fundamental to the economic model. If agents could mint scrip, the currency would have no scarcity constraint. The auction system's control over minting is part of kernel "physics", not policy.

**Related plans:**
- Plan #39: Genesis Unprivilege (original goal, may be superseded)
- Plan #44: Genesis Full Unprivilege (related work)

**Migration risk:** Changing genesis artifact internals could break existing simulations. Phase 3 must verify behavior equivalence through comprehensive tests.
