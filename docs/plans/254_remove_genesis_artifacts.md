# Plan #254: Remove Genesis Artifacts, Promote Transfer to Kernel

**Status:** ✅ Complete

**Verified:** 2026-02-02T05:33:37Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-02T05:33:37Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 73a9d14
```
**Priority:** High
**Created:** 2026-02-01
**Updated:** 2026-02-01 (Gemini advisory feedback integrated)
**Context:** V4 architecture stabilization. Genesis artifacts have been an ongoing source of confusion. Per Gemini advisory + user decision: eliminate genesis entirely, promote core "physics" functions to kernel.

---

## Problem

Genesis artifacts were intended as "cold-start conveniences" — unprivileged artifacts that agents could theoretically rebuild. In practice:

1. **Confusion**: Unclear whether genesis is "kernel" or "artifact" — it's neither cleanly
2. **Coupling**: 15+ files reference genesis; changes ripple everywhere
3. **Bloat**: ~250KB of code for features that may not work in stabilized V4
4. **Philosophy violation**: If "everything is an artifact," why are some artifacts pre-blessed?

The V4 architecture says: **Kernel provides physics, agents provide logic.** Genesis artifacts blur this line.

---

## Solution: The 11-Action Kernel

### The Narrow Waist (11 Physics Primitives)

Remove `configure_context` and `modify_system_prompt` (syntactic sugar), add `transfer` and `mint`:

| # | Action | Category | Purpose | Constraint |
|---|--------|----------|---------|------------|
| 1 | `noop` | Control | Yield turn | None |
| 2 | `read_artifact` | Storage | Get data | Permission |
| 3 | `write_artifact` | Storage | Create/replace | Disk quota |
| 4 | `edit_artifact` | Storage | Surgical modify | Disk quota |
| 5 | `delete_artifact` | Storage | Destroy | Permission |
| 6 | `invoke_artifact` | Execution | Run code / Think | LLM budget |
| 7 | `transfer` | Value | Move scrip | Balance ≥ amount |
| 8 | `mint` | Value | **Create scrip** | **Privileged** (`can_mint` capability) |
| 9 | `query_kernel` | Observation | Search/inspect world | None |
| 10 | `subscribe_artifact` | Signal | Wake on change + push data | None |
| 11 | `unsubscribe_artifact` | Signal | Stop signal | None |

### Key Design Decisions

#### 1. Minting is Privileged via Capability Flag

```python
# Kernel checks capability before allowing mint
if not artifact.has_capability("can_mint"):
    return permission_error("Minting requires can_mint capability")
```

**Bootstrap:** At T=0, seed `kernel_mint_agent` artifact with `can_mint=True` capability. This artifact handles auction/bounty submissions and calls `mint` when conditions are satisfied.

**Why capability flag (not hardcoded ID):** More flexible, allows external signals (e.g., GitHub stars) to trigger minting via different authorized artifacts.

#### 2. Ownership Transfer via `edit_artifact`

No separate `transfer_ownership` action. Ownership is just metadata (`created_by` field). To transfer:

```python
edit_artifact(artifact_id, old_owner_field, new_owner_field)
```

The artifact's **contract** decides if this edit is allowed.

#### 3. Principal Creation via `write_artifact`

No separate `spawn_principal` action. A principal is just an artifact with `has_standing=True`:

```python
write_artifact(
    artifact_id="new_agent",
    content={...},
    has_standing=True,  # Kernel auto-registers in ledger
    has_loop=True       # If autonomous
)
```

**Kernel behavior:** When `write_artifact` sees `has_standing=True`, it automatically:
- Calls `ledger.create_principal()`
- Calls `resource_manager.create_principal()`

#### 4. Subscription Semantics (Wake + Push)

When Artifact A changes, if Agent B is subscribed:
1. **Wake** Agent B (state → RUNNABLE)
2. **Push** change data into B's `run(context)`:
   ```python
   context.subscriptions = [
       {"event": "update", "source": "artifact_A", "diff": {...}}
   ]
   ```

**Key optimization:** No `read_artifact` call needed — data is already in context.

---

## What Gets Promoted to Kernel

| Genesis Function | Kernel Equivalent |
|------------------|-------------------|
| `genesis_ledger.transfer()` | `transfer` action |
| `genesis_ledger.balance()` | `query_kernel("balances", ...)` (exists) |
| `genesis_ledger.transfer_ownership()` | `edit_artifact` on metadata |
| `genesis_ledger.spawn_principal()` | `write_artifact` with `has_standing=True` |
| `genesis_mint.mint_scrip()` | `mint` action (privileged) |
| `genesis_mint.submit_bid()` | Standard artifact (auction pattern) |
| `genesis_event_log.log()` | Kernel automatic logging (exists) |
| `genesis_event_log.query()` | `query_kernel("events", ...)` (exists) |
| Model quotas | Kernel `ResourceManager` / `RateTracker` |

## What Gets Removed Entirely

Agents can rebuild these patterns using kernel primitives if needed:

- **GenesisMint class** — Keep auction *logic* in kernel (`MintAuction`), remove genesis wrapper
- **GenesisEscrow** — Trade pattern built on `transfer` + contracts
- **GenesisVoting** — Decision logic is not physics
- **GenesisMemory** — Service, not physics
- **GenesisEmbedder** — Service, not physics
- **GenesisModelRegistry** — Absorbed into kernel `ResourceManager`
- **GenesisDebtContract** — Lending pattern, not physics
- **GenesisPromptLibrary** — Service, not physics
- **GenesisRightsRegistry** — Absorbed into kernel `ResourceManager`
- **GenesisEventBus** — Handled by `subscribe`/`unsubscribe` actions
- **GenesisLedger** — Absorbed into kernel actions
- **Decision artifacts** — Helper patterns, not physics

---

## Implementation Phases

### Phase 0: Archive (Before Any Changes)

```bash
# Create archive branch
git checkout -b archive/genesis-artifacts-v3
git checkout main

# Also create tarball for external storage
mkdir -p backups
git archive HEAD:src/world/genesis/ -o backups/genesis-artifacts-v3-$(date +%Y%m%d).tar.gz
```

### Phase 1: Add `transfer` and `mint` Actions

**Files to modify:**

| File | Change |
|------|--------|
| `src/world/actions.py` | Add `ActionType.TRANSFER`, `ActionType.MINT`, intent classes |
| `src/world/action_executor.py` | Add `_execute_transfer()`, `_execute_mint()` methods |
| `src/world/ledger.py` | Ensure `transfer_scrip()`, `credit_scrip()` work standalone |
| `src/world/artifacts.py` | Add `has_capability()` method for privilege checking |

**New action signatures:**
```python
class TransferIntent(ActionIntent):
    """Transfer scrip between principals."""
    recipient_id: str
    amount: int  # Scrip is integer, non-negative
    memo: str | None = None

class MintIntent(ActionIntent):
    """Create new scrip (privileged)."""
    recipient_id: str
    amount: int
    reason: str  # Why minting (audit trail)
```

**Execution logic:**
```python
def _execute_transfer(self, intent: TransferIntent) -> ActionResult:
    # Validate sender has balance >= amount
    # Validate recipient exists and is principal
    # Deduct from sender, credit to recipient
    # Log the transfer
    # Return success/failure

def _execute_mint(self, intent: MintIntent) -> ActionResult:
    # Check caller has can_mint capability
    if not self._has_capability(intent.principal_id, "can_mint"):
        return permission_error("Minting requires can_mint capability")
    # Credit scrip to recipient
    # Log the mint with reason
    # Return success
```

### Phase 2: Absorb Functions into Kernel

| Function | Implementation |
|----------|----------------|
| `write_artifact` + `has_standing` | Add hook in `_execute_write()` to auto-create principal |
| `edit_artifact` for ownership | Contract validates; kernel just does the edit |
| Model quotas | Already in `ResourceManager` — remove genesis wrapper |
| Subscription push | Update `AgentLoop` to inject subscription data into `run(context)` |

### Phase 3: Remove Genesis References

**Files with genesis imports (~15 files):**

| File | Change |
|------|--------|
| `src/world/__init__.py` | Remove genesis exports |
| `src/world/action_executor.py` | Remove genesis artifact special-casing |
| `src/world/artifacts.py` | Remove genesis artifact checks |
| `src/simulation/runner.py` | Remove genesis initialization, seed `kernel_mint_agent` |
| `src/agents/agent.py` | Change `invoke("genesis_*")` to kernel actions |
| `src/agents/memory.py` | Remove genesis_memory dependency |
| `src/agents/reflex.py` | Update genesis references |
| `src/agents/schema.py` | Remove genesis artifact schemas |
| `src/config_schema.py` | Remove `genesis` config section |
| `config/config.yaml` | Remove `genesis:` block |
| `src/dashboard/*` | Update parsers/displays |

### Phase 4: Delete Genesis Directory

```bash
rm -rf src/world/genesis/
```

**Keep:** `src/world/mint_auction.py` (auction logic, not genesis)

### Phase 5: Bootstrap the Mint Agent

Create `kernel_mint_agent` artifact at world init:
```python
# In World.__init__ or runner setup
self.artifacts.create(
    artifact_id="kernel_mint_agent",
    content={"type": "mint_authority", "auction_config": {...}},
    created_by="SYSTEM",
    has_standing=True,
    capabilities=["can_mint"]  # Privileged
)
```

### Phase 6: Update Tests

1. **Delete tests** for removed genesis functionality
2. **Rewrite tests** to use kernel actions directly
3. **Add tests** for new `transfer` and `mint` actions
4. **Add tests** for capability checking

### Phase 7: Update Documentation

| Doc | Change |
|-----|--------|
| `docs/architecture/current/genesis_artifacts.md` | Delete or convert to "historical" |
| `docs/architecture/current/resources.md` | Update to reflect kernel-native transfers |
| `docs/architecture/current/artifacts_executor.md` | Document `transfer`, `mint`, capability system |
| `docs/GLOSSARY.md` | Remove genesis terms, add capability terms |
| `README.md` | Remove genesis references |
| `CLAUDE.md` files | Update throughout |

---

## Migration Path for Agents

| Old Pattern | New Pattern |
|-------------|-------------|
| `invoke("genesis_ledger", "transfer", [to, amount])` | `transfer(recipient_id=to, amount=amount)` |
| `invoke("genesis_ledger", "balance", [id])` | `query_kernel("balances", {"principal_id": id})` |
| `invoke("genesis_ledger", "spawn_principal", [...])` | `write_artifact(..., has_standing=True)` |
| `invoke("genesis_mint", "submit_bid", [...])` | `invoke("kernel_mint_agent", "submit", [...])` |
| `invoke("genesis_escrow", ...)` | *Rebuild as standard artifact or use transfer + contracts* |
| `invoke("genesis_memory", ...)` | *Use write_artifact or external service* |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing agents | Phase carefully, test each phase |
| Losing useful patterns | Archive thoroughly, document patterns |
| Scope creep | Strict phase boundaries, don't add new features |
| Tests failing | Accept temporary test reduction, rebuild incrementally |
| Mint abuse | Capability system limits who can mint |

---

## Success Criteria

1. `src/world/genesis/` directory does not exist
2. No imports of `genesis` anywhere in `src/`
3. `transfer` action works: `TransferIntent(principal, recipient, 100)`
4. `mint` action works (with capability): `MintIntent(mint_agent, recipient, 50, "bounty")`
5. `write_artifact(..., has_standing=True)` auto-creates principal
6. `query_kernel("balances")` returns correct balances
7. Subscriptions push data to `run(context)` without read
8. `make check` passes (after test updates)

---

## Estimated Scope

| Phase | Effort |
|-------|--------|
| Phase 0: Archive | 10 min |
| Phase 1: Add transfer + mint actions | 3-4 hours |
| Phase 2: Absorb functions into kernel | 2-3 hours |
| Phase 3: Remove genesis references | 4-6 hours |
| Phase 4: Delete genesis | 5 min |
| Phase 5: Bootstrap mint agent | 1 hour |
| Phase 6: Update tests | 3-4 hours |
| Phase 7: Update docs | 2-3 hours |
| **Total** | **~2-3 days** |

---

## Resolved Questions

| Question | Resolution |
|----------|------------|
| Who can call `mint`? | Artifacts with `can_mint` capability (checked by kernel) |
| How is mint authorized? | Capability flag, not hardcoded ID |
| `transfer_ownership`? | Use `edit_artifact` on metadata; contract validates |
| `spawn_principal`? | Use `write_artifact` with `has_standing=True`; kernel auto-registers |
| Model quotas? | Already in `ResourceManager`; remove genesis wrapper |
| Subscription semantics? | Wake + Push (data in `run(context)`, no read needed) |
| Starting scrip? | Kernel mints at init based on config |

---

## Dependencies

- Plan #251 (resource terminology) — Should complete first for clean naming
- Plan #252 (tick cleanup) — Can be parallel
- Plan #255 (kernel_llm_gateway) — Blocked until this completes (no genesis = need LLM access path)

---

## Future Work (Not This Plan)

- **Plan #255**: `kernel_llm_gateway` — LLM access as kernel primitive or standard artifact
- **Plan #256**: Hybrid agent mode — Testing V4 patterns with real agents
- **Rebuild patterns**: Agents that want escrow/voting/memory can build them as standard artifacts
- **Bounty system**: Eventually configure mint with bounties instead of just auctions
