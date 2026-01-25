# ARCHITECTURE_DECISIONS_2026_01.md Audit

**Date:** 2026-01-24
**Purpose:** Cross-reference ARCHITECTURE_DECISIONS_2026_01.md against existing ADRs to identify coverage gaps.

---

## Executive Summary

The ARCHITECTURE_DECISIONS_2026_01.md file contains 19 sections of architectural decisions. After cross-referencing with the 20 existing ADRs:

- **Fully Covered:** 10 sections
- **Partially Covered:** 5 sections
- **Not Covered (need ADRs):** 2 sections
- **Discussion/Context (no ADR needed):** 2 sections

---

## Section-by-Section Analysis

### Section 1: Kernel vs Agent World
**Status:** ✅ Covered
**ADRs:** ADR-0001 (Everything is artifact), ADR-0004 (Mint system primitive), ADR-0015 (Contracts as artifacts)
**Notes:** The two-layer architecture (kernel vs agent world) is implicitly captured across multiple ADRs.

### Section 2: Akashic Records and Visibility
**Status:** ⚠️ Partially Covered
**ADRs:** ADR-0020 (Event schema contract) covers event logging, but visibility model (what's opaque vs observable) not explicitly captured.
**Gap:** Consider ADR for visibility model if this becomes implementation-critical.

### Section 3: Access Control and Rights
**Status:** ✅ Fully Covered
**ADRs:** ADR-0003, ADR-0015, ADR-0016, ADR-0019 (unified permission architecture)
**Notes:** ADR-0019 consolidates all permission decisions.

### Section 4: Owner Concept
**Status:** ✅ Fully Covered
**ADRs:** ADR-0016 (created_by replaces owner_id)
**Notes:** Key clarification that owner_id is data, not privilege, is captured.

### Section 5: Genesis Artifacts
**Status:** ✅ Fully Covered
**ADRs:** ADR-0004 (mint system primitive), ADR-0018 (bootstrap and Eris)
**Notes:** Genesis artifacts as cold-start conveniences, not privileged, is well documented.

### Section 6: Ledger Model
**Status:** ✅ Fully Covered
**ADRs:** ADR-0002 (no compute debt), ADR-0012 (scrip non-negative)
**Notes:** Core ledger principles captured.

### Section 7: Resource Attribution
**Status:** ❌ NOT COVERED - NEEDS ADR
**ADRs:** None
**Content needing ADR:**
- `billing_principal` tracking (who started call chain)
- `resource_payer` contract field ("billing_principal" | "self")
- Subscription/sponsorship patterns enabled by self-paying artifacts
**Recommendation:** Create ADR-0021: Resource Attribution Model

### Section 8: Agent Execution Model
**Status:** ✅ Fully Covered
**ADRs:** ADR-0010 (continuous agent loops), ADR-0014 (continuous execution primary)
**Notes:** Sleep/wake model and continuous async execution covered.

### Section 9: Event System and Coordination
**Status:** ⚠️ Partially Covered
**ADRs:** ADR-0020 (event schema contract)
**Notes:** Event schema covered; event bus/subscription model less explicit.

### Section 10: Interface Discovery
**Status:** ⚠️ Partially Covered
**ADRs:** ADR-0001 mentions interface field, but MCP-style discovery not formalized.
**Notes:** The decision "don't mandate MCP, use flexible JSON" is not captured.

### Section 11: Reasoning and Observability
**Status:** ⚠️ Not Covered (but may not need ADR)
**Notes:** Mandatory reasoning field on LLM calls is implementation detail, not architecture.

### Section 12: Security Considerations
**Status:** ⚠️ Partially Covered
**ADRs:** ADR-0003 mentions sandbox/timeout as mitigations.
**Notes:** Contract sandboxing approach (subprocess + seccomp vs WASM) not formalized. May warrant ADR when implementation decision needed.

### Section 13: Storage and Persistence
**Status:** ✅ Fully Covered
**ADRs:** ADR-0006 (minimal external dependencies)
**Notes:** In-memory for v1, PostgreSQL when needed.

### Section 14: Open Questions
**Status:** 📝 Discussion (no ADR needed)
**Notes:** These are tracked questions, not decisions. Some resolved in later sections.

### Section 15: Remaining Unresolved Issues
**Status:** 📝 Gap Tracking (no ADR needed)
**Notes:** Implementation tracking, not architectural decisions.

### Section 16: Prioritized Resolution Plan
**Status:** ✅ Most items resolved
**Notes:** Tier 1-3 items marked RESOLVED with ADR references.

### Section 17: Edge Case Decisions
**Status:** ⚠️ Partially Covered
**ADRs:** ADR-0017 (dangling contracts fail-open) covers one case.
**Notes:** 25 edge cases documented. Most are implementation details (e.g., reentrancy = accept risk). Key edge cases worth preserving:
- Contract `check_permission()` throws → deny by default
- Payment splits must sum to 10000 basis points
- Storage rent configuration

### Section 18: Resource Model Decisions
**Status:** ❌ NOT COVERED - NEEDS ADR
**ADRs:** None
**Content needing ADR:**
- Explicit artifact creation (no auto-detection)
- Charge at computation time (not at artifact creation)
- ResourceMeasurer → Ledger integration
- billing_principal tracking (also in Section 7)
**Recommendation:** Create ADR-0021: Resource Attribution Model (covers both Section 7 and 18)

### Section 19: Implementation Gap Analysis
**Status:** 📝 Gap Tracking (no ADR needed)
**Notes:** Documents current vs target gaps. Not architectural decision material.

---

## Action Items

### New ADRs Needed

1. **ADR-0021: Resource Attribution Model**
   - `billing_principal` tracking in invocation context
   - `resource_payer` field ("billing_principal" | "self")
   - Subscription/sponsorship patterns
   - Charge at computation time
   - Consolidates Section 7 and Section 18 decisions

### ADRs to Consider (Lower Priority)

2. **ADR for Visibility Model** (if implementation needs clarity)
   - What's observable vs opaque
   - Action log visibility rules
   - Artifact content opacity

3. **ADR for Sandbox Approach** (when implementation decision made)
   - subprocess + seccomp vs WASM
   - Security boundaries

### Content to Preserve in Research

Some valuable context in ARCHITECTURE_DECISIONS that's not ADR material but worth keeping:
- Section 14 open questions → move to research for future work
- Section 17 edge cases → document in architecture/target as implementation notes
- Visual diagrams (Section 1) → useful for onboarding docs

---

---

## DOCUMENTATION_ASSESSMENT Issues Status

Checking issues identified in DOCUMENTATION_ASSESSMENT_2026_01_16.md:

### Critical Issues

| Issue | Status | Notes |
|-------|--------|-------|
| Stale auction phases in mint.md | ✅ Fixed | Updated 2026-01-17, says "anytime" |
| Oracle to mint rename | ✅ Mostly Fixed | GLOSSARY.md correct. Some archive files still have oracle refs. |

### Still Open Issues

| Issue | Files Affected | Status |
|-------|---------------|--------|
| bidding_window refs in execution_model.md | lines 102, 111, 131 | ❌ Still stale |
| bidding_window refs in configuration.md | line 170 | ❌ Still stale |
| bidding window refs in genesis_artifacts.md | line 90 | ❌ Still stale |
| "When bidding window closes" in mint.md | line 89 | ❌ Inconsistent with anytime model |

### Recommendations from DOCUMENTATION_ASSESSMENT (Phase 1-2)

| Item | Status |
|------|--------|
| Delete TASK_LOG.md | 🔄 Pending |
| Archive MULTI_CC_ANALYSIS.md | 🔄 Pending |
| Remove TEMP rebase notice from CLAUDE.md | 🔄 Check if still present |
| Update mint.md for anytime bidding | ✅ Done (mostly) |

---

## Conclusion

ARCHITECTURE_DECISIONS_2026_01.md can be archived after:

1. ✅ Created ADR-0021 for resource attribution (billing_principal, resource_payer)
2. ✅ Bidding window references reviewed - execution_model.md correctly documents phases AND notes anytime bidding
3. ✅ Fixed mint.md line 89 ("When bidding window closes" → "When auction period elapses")
4. ⬜ Moving valuable open questions to docs/research (future work)

The file has served its purpose as a working document. Its resolved decisions are now captured in ADRs 0001-0021.
