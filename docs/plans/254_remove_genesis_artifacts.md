# Plan #254: Remove Genesis Artifacts, Promote Transfer to Kernel

**Status:** 📋 Planned
**Priority:** High
**Created:** 2026-02-01
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

## Solution: The 10-Action Kernel

### New Action Model

Remove `configure_context` and `modify_system_prompt` (syntactic sugar), add `transfer`:

| # | Action | Category | Purpose |
|---|--------|----------|---------|
| 1 | `noop` | Control | Wait/pass |
| 2 | `read_artifact` | Storage | Get data |
| 3 | `write_artifact` | Storage | Create/replace |
| 4 | `edit_artifact` | Storage | Surgical modify |
| 5 | `delete_artifact` | Storage | Destroy |
| 6 | `invoke_artifact` | Execution | Run code |
| 7 | `transfer` | **Value** | Move scrip between principals |
| 8 | `query_kernel` | Observation | Discover world state |
| 9 | `subscribe_artifact` | Attention | Push notifications |
| 10 | `unsubscribe_artifact` | Attention | Stop notifications |

### What Gets Promoted to Kernel

| Genesis Function | Kernel Equivalent |
|------------------|-------------------|
| `genesis_ledger.transfer()` | `transfer` action (new) |
| `genesis_ledger.balance()` | `query_kernel("balances", ...)` (exists) |
| `genesis_ledger.transfer_ownership()` | `transfer_ownership` action (new) OR kernel internal |
| `genesis_event_log.log()` | Kernel automatic logging (exists) |
| `genesis_event_log.query()` | `query_kernel("events", ...)` (exists) |

### What Gets Removed Entirely

Agents can rebuild these patterns using kernel primitives if needed:

- **GenesisMint** — Auction logic is not physics
- **GenesisEscrow** — Trade pattern built on `transfer` + contracts
- **GenesisVoting** — Decision logic is not physics
- **GenesisMemory** — Service, not physics
- **GenesisEmbedder** — Service, not physics
- **GenesisModelRegistry** — Quota management (may merge into kernel resources)
- **GenesisDebtContract** — Lending pattern, not physics
- **GenesisPromptLibrary** — Service, not physics
- **GenesisRightsRegistry** — May merge into kernel resources
- **GenesisEventBus** — Handled by `subscribe`/`unsubscribe` actions
- **Decision artifacts** — Helper patterns, not physics

---

## Implementation Phases

### Phase 0: Archive (Before Any Changes)

```bash
# Create archive branch
git checkout -b archive/genesis-artifacts-v3
git checkout main

# Also create tarball for external storage
git archive HEAD:src/world/genesis/ -o backups/genesis-artifacts-v3-$(date +%Y%m%d).tar.gz
```

### Phase 1: Add `transfer` Action

**Files to modify:**

| File | Change |
|------|--------|
| `src/world/actions.py` | Add `ActionType.TRANSFER`, `TransferIntent` class |
| `src/world/action_executor.py` | Add `_execute_transfer()` method |
| `src/world/ledger.py` | Ensure `transfer_scrip()` works standalone (no genesis) |

**New action signature:**
```python
class TransferIntent(ActionIntent):
    """Transfer scrip between principals."""
    recipient_id: str
    amount: int  # Scrip is integer, non-negative
    memo: str | None = None  # Optional note
```

**Execution logic:**
```python
def _execute_transfer(self, intent: TransferIntent) -> ActionResult:
    # Validate sender has balance
    # Validate recipient exists (is principal)
    # Deduct from sender, credit to recipient
    # Log the transfer
    # Return success/failure
```

### Phase 2: Absorb Remaining Ledger Functions

| Function | Disposition |
|----------|-------------|
| `balance()` | Already in `query_kernel("balances")` |
| `all_balances()` | Already in `query_kernel("balances")` |
| `transfer_ownership()` | Add to kernel OR keep as artifact method |
| `spawn_principal()` | Move to kernel (creates principals) |
| `transfer_budget()` | Move to kernel (resource transfer) |

### Phase 3: Remove Genesis References

**Files with genesis imports (~15 files):**

| File | Change |
|------|--------|
| `src/world/__init__.py` | Remove genesis exports |
| `src/world/action_executor.py` | Remove genesis artifact special-casing |
| `src/world/artifacts.py` | Remove genesis artifact checks |
| `src/simulation/runner.py` | Remove genesis initialization |
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

### Phase 5: Update Tests

Many tests depend on genesis. Options:
1. **Delete tests** for removed functionality
2. **Rewrite tests** to use kernel actions directly
3. **Mark as skipped** with TODO for future patterns

### Phase 6: Update Documentation

| Doc | Change |
|-----|--------|
| `docs/architecture/current/genesis_artifacts.md` | Delete or convert to "historical" |
| `docs/architecture/current/resources.md` | Update to reflect kernel-native transfers |
| `docs/architecture/current/artifacts_executor.md` | Document new `transfer` action |
| `docs/GLOSSARY.md` | Remove genesis terms or mark deprecated |
| `README.md` | Remove genesis references |
| `CLAUDE.md` files | Update throughout |

---

## Migration Path for Agents

Agents currently using genesis will need updates:

| Old Pattern | New Pattern |
|-------------|-------------|
| `invoke("genesis_ledger", "transfer", [to, amount])` | `transfer(recipient_id=to, amount=amount)` |
| `invoke("genesis_ledger", "balance", [id])` | `query_kernel("balances", {"principal_id": id})` |
| `invoke("genesis_mint", "submit_bid", [...])` | *Removed — agents rebuild if needed* |
| `invoke("genesis_escrow", "create_escrow", [...])` | *Removed — pattern using transfer + contracts* |
| `invoke("genesis_memory", "store", [...])` | *Removed — use write_artifact or external service* |

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing agents | Phase carefully, test each phase |
| Losing useful patterns | Archive thoroughly, document patterns |
| Scope creep | Strict phase boundaries, don't add new features |
| Tests failing | Accept temporary test reduction, rebuild incrementally |

---

## Success Criteria

1. `src/world/genesis/` directory does not exist
2. No imports of `genesis` anywhere in `src/`
3. `transfer` action works: `TransferIntent("alice", "bob", 100)`
4. `query_kernel("balances")` returns correct balances
5. `make check` passes (after test updates)
6. Agents can transfer scrip without invoking any artifact

---

## Estimated Scope

| Phase | Effort |
|-------|--------|
| Phase 0: Archive | 10 min |
| Phase 1: Add transfer action | 2-3 hours |
| Phase 2: Absorb ledger functions | 2-3 hours |
| Phase 3: Remove genesis references | 4-6 hours |
| Phase 4: Delete genesis | 5 min |
| Phase 5: Update tests | 3-4 hours |
| Phase 6: Update docs | 2-3 hours |
| **Total** | **~2-3 days** |

---

## Open Questions

1. **`transfer_ownership`** — Should this be a kernel action or handled differently?
2. **`spawn_principal`** — Is creating new principals a kernel primitive or requires special handling?
3. **Model access quotas** — Currently in `GenesisModelRegistry`. Merge into kernel resources?
4. **Subscriptions** — Current `subscribe_artifact` injects into prompts. In V4, what does it do?

---

## Dependencies

- Plan #251 (resource terminology) — Should complete first for clean naming
- Plan #252 (tick cleanup) — Can be parallel
- Plan #255 (kernel_llm_gateway) — Blocked until this completes (no genesis = need LLM access path)

---

## Future Work (Not This Plan)

- **Plan #255**: `kernel_llm_gateway` — LLM access as kernel primitive or first "real" artifact
- **Plan #256**: Hybrid agent mode — Testing V4 patterns
- **Rebuild patterns**: Agents that want escrow/voting/mint can build them
