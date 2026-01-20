# Plan 119: Documentation Consistency Fixes

**Status:** ✅ Complete

**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Several documentation files contain outdated terminology and concepts that contradict accepted ADRs:

1. **ADR README** missing ADRs 0015-0018 in index
2. **AGENT_HANDBOOK** uses "oracle" (should be "mint"), "per-tick", and `transfer_ownership`
3. **DESIGN_CLARIFICATIONS** has "Negative Balance Rules" section that contradicts ADR-0012

**Target:** Documentation consistent with accepted ADRs.

**Why:** Inconsistent docs confuse both humans and LLMs reading the codebase.

---

## Changes Required

### 1. docs/adr/README.md

Add missing ADRs to index:

| ADR | Title |
|-----|-------|
| 0015 | Contracts as artifacts |
| 0016 | Created-by not owner |
| 0017 | Dangling contracts fail open |
| 0018 | Bootstrap and Eris |

### 2. docs/AGENT_HANDBOOK.md

| Find | Replace | Reason |
|------|---------|--------|
| "oracle" | "mint" | ADR-0004 renamed Oracle to Mint |
| "per-tick" / "per_tick" | time-based language | ADR-0014 continuous execution |
| `transfer_ownership` | Remove or update | ADR-0016 replaced ownership with created_by |

### 3. docs/DESIGN_CLARIFICATIONS.md

- Remove or update "Negative Balance Rules" section (lines ~227-248)
- ADR-0012 clearly states scrip cannot go negative
- Debt is modeled as contract artifacts, not negative balances

---

## Files Affected

- docs/adr/README.md (modify - add index entries)
- docs/AGENT_HANDBOOK.md (modify - terminology updates)
- docs/DESIGN_CLARIFICATIONS.md (modify - remove contradictory section)

---

## Verification

- [x] ADR README lists all 18 ADRs
- [x] AGENT_HANDBOOK has no "oracle" references (except historical context)
- [x] AGENT_HANDBOOK has no "per-tick" execution model references
- [x] DESIGN_CLARIFICATIONS has no "Balance < 0" behavior descriptions (marked SUPERSEDED)
- [x] All docs consistent with ADR-0004, ADR-0012, ADR-0014, ADR-0016

---

## Notes

- This is documentation-only cleanup
- No code changes required
- Identified via cross-reference analysis of ADRs vs other docs
