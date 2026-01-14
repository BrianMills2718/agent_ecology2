# Plan #44: Genesis Artifact Full Unprivilege

**Status:** 🚧 In Progress

**Priority:** High
**Blocked By:** Plan #42 (Kernel Quota Primitives)
**Blocks:** None

---

## Problem

Plan #39 (Genesis Unprivilege) created `KernelState` and `KernelActions` interfaces but explicitly left minting as "admin-only". This means:

1. **GenesisMint is still privileged** - Has direct `mint_callback` access instead of using kernel primitives
2. **Naming is inconsistent** - Genesis artifacts don't distinguish between kernel API wrappers and pure contracts
3. **Architecture unclear** - What's kernel state vs. artifact state isn't obvious

### Current State

| Artifact | Privileged? | Issue |
|----------|-------------|-------|
| `genesis_ledger` | Partial | Uses Ledger directly (OK - Ledger is injected) |
| `genesis_mint` | **Yes** | Has direct `mint_callback` - can mint scrip |
| `genesis_rights_registry` | No | Now delegates to kernel (Plan #42) |
| `genesis_store` | No | Uses ArtifactStore (injected) |
| `genesis_event_log` | No | Uses EventLogger (injected) |
| `genesis_escrow` | No | Pure contract logic, no kernel access needed |

### Target State

| Artifact | New Name | Role |
|----------|----------|------|
| `genesis_ledger` | `genesis_ledger_api` | Wrapper around kernel ledger primitives |
| `genesis_mint` | `genesis_mint_api` | Wrapper around kernel mint primitives |
| `genesis_rights_registry` | `genesis_rights_api` | Wrapper around kernel quota primitives |
| `genesis_store` | `genesis_store_api` | Wrapper around kernel artifact store |
| `genesis_event_log` | `genesis_event_log_api` | Wrapper around kernel event log |
| `genesis_escrow` | `genesis_escrow_contract` | Pure contract (no kernel privilege needed) |

---

## Solution

### Phase 1: Kernel Mint Primitives

Add mint state and operations to kernel:

```python
# In World (kernel state)
_mint_submissions: dict[str, MintSubmission]
_mint_history: list[MintResult]

# Kernel primitives
def submit_for_mint(self, principal_id: str, artifact_id: str, bid: int) -> str:
    """Submit artifact for mint consideration. Returns submission_id."""
    ...

def get_mint_submissions(self) -> list[MintSubmission]:
    """Get current pending submissions."""
    ...

def get_mint_history(self, limit: int = 100) -> list[MintResult]:
    """Get minting history."""
    ...

# Internal (called by tick advancement)
def _resolve_mint_auction(self) -> None:
    """Run auction, score winners, mint scrip, distribute UBI."""
    ...
```

### Phase 2: KernelState/KernelActions Mint Methods

```python
class KernelState:
    def get_mint_submissions(self) -> list[MintSubmission]:
        """Read pending mint submissions (public)."""
        ...

    def get_mint_history(self, limit: int = 100) -> list[MintResult]:
        """Read mint history (public)."""
        ...

class KernelActions:
    def submit_for_mint(
        self, caller_id: str, artifact_id: str, bid: int
    ) -> dict[str, Any]:
        """Submit artifact for minting. Caller must own artifact."""
        ...

    def cancel_mint_submission(self, caller_id: str, submission_id: str) -> bool:
        """Cancel own submission, get bid back."""
        ...
```

### Phase 3: Refactor GenesisMint

```python
class GenesisMintApi(GenesisArtifact):
    """Unprivileged wrapper around kernel mint primitives."""

    def _submit(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        # Use kernel interface, not direct callback
        kernel_actions = KernelActions(self._world)
        return kernel_actions.submit_for_mint(caller_id, args[0], args[1])

    def _status(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        kernel_state = KernelState(self._world)
        return {"submissions": kernel_state.get_mint_submissions()}

    def _history(self, args: list[Any], caller_id: str) -> dict[str, Any]:
        kernel_state = KernelState(self._world)
        return {"history": kernel_state.get_mint_history()}
```

### Phase 4: Apply Naming Convention

Rename all genesis artifacts:

| Old Name | New Name | Type |
|----------|----------|------|
| `genesis_ledger` | `genesis_ledger_api` | API wrapper |
| `genesis_mint` | `genesis_mint_api` | API wrapper |
| `genesis_rights_registry` | `genesis_rights_api` | API wrapper |
| `genesis_store` | `genesis_store_api` | API wrapper |
| `genesis_event_log` | `genesis_event_log_api` | API wrapper |
| `genesis_escrow` | `genesis_escrow_contract` | Contract |

Update all references in:
- Config files (`config/schema.yaml`, `config/config.yaml`)
- Source code (imports, string literals)
- Tests
- Documentation
- Handbook files

---

## Required Tests

### Unit Tests
- [ ] `test_kernel_mint_primitives.py::test_submit_for_mint` - Submission stored in kernel
- [ ] `test_kernel_mint_primitives.py::test_get_submissions` - Can query pending submissions
- [ ] `test_kernel_mint_primitives.py::test_get_history` - Can query mint history
- [ ] `test_kernel_mint_primitives.py::test_auction_resolution` - Kernel resolves auctions

### Integration Tests
- [ ] `test_genesis_mint_unprivileged.py::test_mint_via_kernel` - GenesisMintApi uses kernel primitives
- [ ] `test_genesis_mint_unprivileged.py::test_agent_equivalent` - Agent could build equivalent
- [ ] `test_naming_convention.py::test_api_vs_contract_naming` - All artifacts correctly named

### E2E Tests
- [ ] `test_mint_e2e.py::test_full_auction_cycle` - Auction works end-to-end with new architecture

---

## Acceptance Criteria

1. GenesisMint no longer has direct `mint_callback` access
2. All mint operations go through `KernelState`/`KernelActions`
3. Naming convention applied (`genesis_*_api` vs `genesis_*_contract`)
4. An agent-built artifact could theoretically implement equivalent mint API
5. All tests pass
6. Documentation updated

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/world.py` | Add mint state and primitives to kernel |
| `src/world/kernel_interface.py` | Add mint methods to KernelState/KernelActions |
| `src/world/genesis.py` | Refactor GenesisMint, apply naming |
| `config/schema.yaml` | Update artifact IDs |
| `config/config.yaml` | Update artifact IDs |
| `src/agents/_handbook/*.md` | Update artifact references |
| `docs/architecture/current/genesis_artifacts.md` | Document new architecture |

---

## Migration Notes

The artifact ID changes will break existing configs. Options:
1. **Aliases** - Keep old names as aliases pointing to new names
2. **Migration script** - Update configs automatically
3. **Breaking change** - Document in release notes

Recommend option 1 (aliases) for backward compatibility.

---

## Notes

This completes the unprivilege work started in Plan #39. The key insight is that minting should be kernel physics (like quotas), with GenesisMint being a convenience wrapper that any agent could theoretically rebuild.

Reference: Conversation on 2026-01-14 about mint kernel primitives.
