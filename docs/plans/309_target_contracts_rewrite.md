# Plan 309: Rewrite Target Contract Architecture

**Status:** ✅ Complete
**Priority:** High

---

## Gap

**Current:** Target contract architecture doc (`05_contracts.md`) contains contradictions with ADR-0028, ADR-0019, and the user's actual design intent. Current docs have stale references to renamed modules and false claims about `created_by` usage.

**Target:** Consistent target architecture document reflecting resolved design decisions: contracts as sole authority, scrip as artificial scarcity, self-governing artifacts, contract persistent state, three-concern PermissionResult.

**Why High:** Architectural confusion propagates to implementation decisions.

---

## References Reviewed

- `docs/architecture/target/05_contracts.md` - previous version with contradictions
- `docs/architecture/current/contracts.md` - current implementation doc
- `docs/adr/0028-created-by-informational.md` - created_by is informational
- `docs/adr/0019-unified-permission-architecture.md` - unified permissions
- `docs/adr/0015-contracts-as-artifacts.md` - contracts are artifacts
- `docs/adr/0011-standing-pays-costs.md` - standing pays costs
- `src/world/kernel_contracts.py` - actual contract implementations
- `config/config.yaml` - current contract configuration

---

## Open Questions

### Resolved

1. [x] **Question:** Should `require_explicit` be configurable?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes, configurable. Currently set to `true` (every artifact must specify contract).

2. [x] **Question:** Can artifacts be self-governing (inline contracts)?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes, `access_contract_id` can point to the artifact itself.

3. [x] **Question:** How does contract state work?
   - **Status:** ✅ RESOLVED
   - **Answer:** `state` dict passed in, `state_updates` returned, kernel commits atomically.

4. [x] **Question:** Is scrip related to real dollars?
   - **Status:** ✅ RESOLVED
   - **Answer:** No. Scrip is artificial scarcity. Real resources (LLM $, disk) are kernel physics. Scrip is artifact-level.

5. [x] **Question:** Is delegation redundant with contracts?
   - **Status:** ✅ RESOLVED
   - **Answer:** For scrip, yes. Delegation only needed for real resource authorization.

---

## Files Affected

- `docs/architecture/target/05_contracts.md` (modify - full rewrite)
- `docs/architecture/current/contracts.md` (modify - fix stale reference)
- `docs/architecture/current/artifacts_executor.md` (modify - fix false claim)
- `docs/architecture/current/ci.md` (modify - update last verified)
- `scripts/relationships.yaml` (modify - add coupling, fix description)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `05_contracts.md` | Full rewrite resolving contradictions |
| `contracts.md` | `genesis_contracts.py` → `kernel_contracts.py` |
| `artifacts_executor.md` | Fix false `target_created_by` claim |
| `relationships.yaml` | Add target doc coupling, fix description |
| `ci.md` | Update last verified date |

---

## Verification

### Tests & Quality
- [x] Full test suite passes (1626 passed)
- [x] Type check passes (mypy clean)
- [x] Doc-coupling check passes

### Documentation
- [x] Current docs updated (contracts.md, artifacts_executor.md)
- [x] Target doc rewritten (05_contracts.md)
- [x] Doc-coupling check passes

---

## Notes

This plan documents a deep architectural discussion that resolved long-standing contradictions in the contract system design. Key decisions:
- Contracts are sole authority (no kernel bypass, no metadata intermediary)
- Three concerns in PermissionResult: access, scrip (artificial), resources (real)
- Self-governing artifacts supported
- Contract persistent state via state/state_updates pattern
- External value signals (bounties, GitHub stars) inject scrip via mint
