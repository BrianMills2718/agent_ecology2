# Gap 100: Contract System Overhaul

**Status:** 📋 Deferred
**Priority:** High
**Blocked By:** Testing/stabilization of current system
**Blocks:** Custom contracts, advanced access control patterns

---

## Overview

Major overhaul of the contract system to fully realize the target architecture where contracts are first-class artifacts with expanded capabilities.

**Scope:** XL (500+ lines, cross-component, multi-phase)
**Risk:** HIGH - touches core permission system

---

## Gap Summary

### Current State

The contract system is **partially implemented**:

| Aspect | Status | Notes |
|--------|--------|-------|
| Genesis contracts (4) | ✅ Done | freeware, self_owned, private, public |
| `access_contract_id` field | ✅ Done | Artifacts point to contracts |
| Permission checking via contracts | ✅ Done | `_check_permission_via_contract()` |
| Owner bypass removed | ✅ Done | Contracts are sole authority |
| Basic sandbox | ✅ Done | 1s timeout, restricted builtins |
| ExecutableContract class | ✅ Done | Dynamic code execution |
| ReadOnlyLedger | ✅ Done | Safe ledger access in contracts |

### Target State (Not Yet Implemented)

| Aspect | Status | Gap ID |
|--------|--------|--------|
| Contract caching | ❌ Missing | GAP-ART-003 |
| Cost model per contract | ⚠️ Partial | GAP-ART-004 |
| Permission depth limit (10) | ❌ Missing | GAP-ART-013, GAP-GEN-006 |
| Extended timeout (30s) | ❌ Needs change | GAP-ART-014 |
| Contract composition | ❌ Missing | GAP-ART-009, GAP-GEN-009 |
| LLM access in contracts | ❌ Missing | GAP-ART-011 |
| Expanded namespace | ⚠️ Partial | GAP-ART-012 |
| Custom contract creation | ❌ Missing | GAP-GEN-034 |
| Dangling contract handling | ❌ Undecided | GAP-ART-020, GAP-GEN-011 |

---

## Open Questions and Uncertainties

### Critical Design Decisions (Must Resolve Before Implementation)

#### 1. Dangling Contract Behavior
**Question:** What happens when `access_contract_id` points to a deleted contract?

| Option | Pros | Cons |
|--------|------|------|
| **A: Fail-open** | Artifacts stay accessible | Security risk - deletion grants access |
| **B: Fail-closed** | Secure - no unintended access | Artifacts locked forever |
| **C: Prevent deletion** | Referential integrity | Adds complexity, contracts immortal |

**Current position:** Undecided (docs say "deferred to implementation")
**Recommendation:** Option B (fail-closed) aligns with "contracts are sole authority"
**ADR needed:** Yes

#### 2. Contract Cost Model Semantics
**Question:** How exactly does `cost_model` work?

| Model | Who Pays | Use Case |
|-------|----------|----------|
| `invoker_pays` | Caller | Default - prevent spam |
| `owner_pays` | Artifact owner | Public services |
| `artifact_pays` | Artifact's balance | Self-sustaining services |
| `split` | Configurable | Revenue sharing |
| `custom` | Contract logic decides | Dynamic pricing |

**Uncertainty:** How does `artifact_pays` work if artifacts don't have scrip balances?
**Recommendation:** Clarify if artifacts can hold scrip, or if `artifact_pays` means owner's balance

#### 3. Contract Caching Semantics
**Question:** How does cache invalidation work?

- **TTL-based:** Simple, but stale permissions possible
- **Content-hash:** Invalidate when artifact/contract changes
- **Explicit:** Contracts call `invalidate_cache()`

**Uncertainty:** What's the cache key? `(artifact_id, action, requester_id)`? Or contract-defined?
**Recommendation:** Start with TTL-based (simplest), add content-hash for V2

#### 4. LLM Access in Contracts
**Question:** Should contracts really be able to call LLMs?

**Arguments for (from ADR-0003):**
- LLMs are just API calls like weather APIs
- Agents should choose complexity/cost tradeoff
- System already non-deterministic

**Arguments against:**
- Non-deterministic permission checks
- Cost uncertainty for callers
- Griefing potential (expensive permission checks)

**Current position:** Approved in ADR-0003 with mitigations (timeout, depth limit, invoker pays)
**Recommendation:** Implement but make it opt-in via contract declaration

#### 5. Depth Limit Scope
**Question:** Does MAX_PERMISSION_DEPTH=10 count:
- Only permission checks?
- All contract invocations?
- Including artifact invocations from within contracts?

**Recommendation:** Separate limits:
- `MAX_PERMISSION_DEPTH = 10` for permission check chains
- `MAX_INVOKE_DEPTH = 5` (existing) for artifact invocations

---

### Medium-Certainty Questions

#### 6. Contract Interface Validation
**Question:** How strictly should contract interfaces be validated?

**Options:**
- **Strict:** Contract must declare `check_permission` in interface, validated at creation
- **Loose:** Just check the function exists when invoked
- **Optional:** Interface is for discoverability, not enforcement

**Current implementation:** Loose (validates function exists)
**Recommendation:** Keep loose for V1, add strict option for V2

#### 7. Timeout Handling
**Question:** Current timeout is 1 second, target is 30 seconds. What's appropriate?

**Considerations:**
- 1s too short for LLM calls in contracts
- 30s too long for simple permission checks
- Different timeouts for different operations?

**Recommendation:**
- Base permission checks: 5 seconds
- Contracts with `call_llm` declared: 30 seconds
- Configurable per contract via `timeout_seconds` field

#### 8. Contract Composition: AND vs OR
**Question:** When artifact has multiple `access_contracts`, is it AND or OR?

**Target says:** AND (all must allow)
**Alternative:** OR (any allows), or contract-specified

**Recommendation:** AND is safer (more restrictive), stick with target

---

### Low-Certainty Questions (Deferred)

#### 9. Contract Upgrade Pattern
**Question:** How do you upgrade a contract that many artifacts reference?

**Options:**
- Modify contract in place (breaks immutability)
- Create new contract, migrate references (expensive)
- Contract versioning with automatic migration

**Recommendation:** Defer to V2. For now: create new contract manually.

#### 10. Contract Inheritance/Composition
**Question:** Can contracts inherit from or compose other contracts?

**Options:**
- No inheritance (keep simple)
- Delegation pattern (contract A calls contract B internally)
- Formal inheritance system

**Recommendation:** Defer. Delegation pattern already possible.

#### 11. Contract Testing/Simulation
**Question:** How do agents test contracts before deploying?

**Options:**
- Dry-run mode that doesn't persist
- Testnet/sandbox world
- Contract simulation API

**Recommendation:** Defer. Agents can create test artifacts.

---

## Files Affected

### Core Implementation Files

| File | Lines | Changes Required |
|------|-------|------------------|
| `src/world/contracts.py` | ~500 | Add caching, expand namespace, depth tracking |
| `src/world/genesis_contracts.py` | ~300 | Add cache_policy, cost_model fields |
| `src/world/executor.py` | ~1100 | Permission caching, depth limits, LLM integration |
| `src/world/artifacts.py` | ~400 | Add cache_policy, cost_model, timeout fields |
| `src/world/actions.py` | ~200 | Handle dangling contracts |
| `src/world/world.py` | ~1800 | Permission cache management |
| `src/world/ledger.py` | ~400 | Support artifact_pays cost model |

### Configuration Files

| File | Changes Required |
|------|------------------|
| `config/schema.yaml` | Add contract config section |
| `config/config.yaml` | Contract defaults |
| `src/config_schema.py` | Contract config validation |

### Test Files

| File | Changes Required |
|------|------------------|
| `tests/unit/test_contracts.py` | Test caching, depth limits, namespace |
| `tests/unit/test_genesis_contracts.py` | Test new fields |
| `tests/integration/test_contracts_acceptance.py` | Full flow tests |
| `tests/integration/test_contracts_v1_acceptance.py` | Update for new features |
| New: `tests/unit/test_contract_caching.py` | Cache-specific tests |
| New: `tests/integration/test_custom_contracts.py` | Agent-created contracts |

### Documentation Files

| File | Changes Required |
|------|------------------|
| `docs/architecture/current/contracts.md` | Update after implementation |
| `docs/architecture/target/05_contracts.md` | Verify accuracy |
| `docs/DESIGN_CLARIFICATIONS.md` | Record decisions |
| New ADR: `docs/adr/NNNN-dangling-contracts.md` | Dangling contract decision |
| New ADR: `docs/adr/NNNN-contract-cost-models.md` | Cost model semantics |

---

## Implementation Phases

### Phase 1: Foundation (Prerequisites)

**Goal:** Resolve design decisions, create ADRs

| Task | Effort | Risk |
|------|--------|------|
| ADR: Dangling contract behavior | S | Low |
| ADR: Contract cost model semantics | S | Low |
| ADR: Contract caching semantics | S | Low |
| Update target docs with decisions | S | Low |

### Phase 2: Core Enhancements

**Goal:** Add missing core features

| Task | Effort | Risk | Gap ID |
|------|--------|------|--------|
| Permission depth limit | M | Medium | GAP-ART-013 |
| Contract timeout configuration | S | Low | GAP-ART-014 |
| Permission caching (TTL-based) | L | Medium | GAP-ART-003 |
| Dangling contract handling | M | High | GAP-ART-020 |

### Phase 3: Cost Model

**Goal:** Implement per-contract cost models

| Task | Effort | Risk | Gap ID |
|------|--------|------|--------|
| Add cost_model field | S | Low | GAP-ART-004 |
| Implement invoker_pays | M | Medium | - |
| Implement owner_pays | M | Medium | - |
| Implement charge() function | M | Medium | GAP-ART-012 |

### Phase 4: Extended Capabilities

**Goal:** Add advanced contract features

| Task | Effort | Risk | Gap ID |
|------|--------|------|--------|
| Expand contract namespace | L | High | GAP-ART-012 |
| Add call_llm() capability | L | High | GAP-ART-011 |
| Contract composition support | M | Medium | GAP-ART-009 |
| Custom contract creation by agents | L | High | GAP-GEN-034 |

### Phase 5: Polish

**Goal:** Documentation, testing, performance

| Task | Effort | Risk |
|------|--------|------|
| Update all architecture docs | M | Low |
| Performance testing & tuning | M | Medium |
| Contract development guide | M | Low |
| Example contracts (paid-read, multi-sig) | M | Low |

---

## Dependencies

### Internal Dependencies

| This Plan | Depends On | Why |
|-----------|------------|-----|
| Phase 2 | ADRs from Phase 1 | Need design decisions |
| Phase 3 | Phase 2 | Cost model needs working contracts |
| Phase 4 | Phase 2, 3 | Advanced features need foundation |

### External Dependencies

| Feature | Depends On |
|---------|------------|
| `call_llm()` | LiteLLM integration (exists) |
| Caching | No external deps |
| Custom contracts | Interface validation (Plan #86 - done) |

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing contracts | High | Medium | Comprehensive tests, backward compat |
| Performance regression | Medium | Medium | Caching, benchmarks |
| Security holes in expanded namespace | High | Low | Careful sandboxing, code review |
| Non-deterministic permissions (LLM) | Medium | High | Make LLM opt-in, document clearly |
| Cache invalidation bugs | Medium | Medium | Start simple (TTL), add complexity later |

---

## Alternatives Considered

### Alternative 1: Keep Contracts Simple
**Option:** Don't add LLM/invoke capabilities to contracts
**Pros:** Simpler, deterministic
**Cons:** Limits expressiveness, doesn't match target architecture
**Decision:** Rejected - target architecture is approved

### Alternative 2: Contract DSL Instead of Python
**Option:** Create a domain-specific language for contracts
**Pros:** Safer, more constrained
**Cons:** Learning curve, implementation effort
**Decision:** Rejected - Python with restrictions is sufficient

### Alternative 3: External Contract Execution
**Option:** Run contracts in separate processes/containers
**Pros:** Better isolation
**Cons:** Performance overhead, complexity
**Decision:** Deferred to V2 - process isolation sufficient for V1

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| All existing tests pass | CI green |
| Permission caching reduces load | Benchmark shows >50% reduction in contract invocations |
| Depth limit prevents recursion | Test with circular contracts |
| Custom contracts work | Agent can create and use paywall contract |
| Documentation complete | All affected docs updated |

---

## References

### Gap Documentation
- `docs/architecture/gaps/ws5_artifacts.yaml` - 22 artifact gaps
- `docs/architecture/gaps/ws4_genesis.yaml` - 28 genesis gaps

### Architecture Docs
- `docs/architecture/target/05_contracts.md` - Target contract architecture
- `docs/architecture/current/contracts.md` - Current implementation
- `docs/adr/0003-contracts-can-do-anything.md` - Capability decision

### Related Plans
- Plan #14: Artifact Interface Schema (complete) - Interface validation
- Plan #86: Interface Validation (complete) - Schema validation

---

## Notes

This plan consolidates multiple gaps from ws4_genesis.yaml and ws5_artifacts.yaml:
- GAP-ART-003, GAP-ART-004, GAP-ART-009, GAP-ART-011, GAP-ART-012, GAP-ART-013, GAP-ART-014, GAP-ART-020
- GAP-GEN-004, GAP-GEN-005, GAP-GEN-006, GAP-GEN-008, GAP-GEN-009, GAP-GEN-011, GAP-GEN-034

The contract system is foundational - changes here affect every permission check in the system. Proceed carefully with comprehensive testing.
