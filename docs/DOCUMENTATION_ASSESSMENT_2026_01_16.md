# Documentation Assessment & Recommendations

**Date:** 2026-01-16
**Status:** Awaiting Review
**Scope:** Full documentation audit of agent_ecology2

---

## Table of Contents

1. [Open Questions (Project Direction)](#1-open-questions-project-direction)
2. [Documentation Cleanup Plan](#2-documentation-cleanup-plan)
3. [Specific Issues Found](#3-specific-issues-found)
4. [docs/meta/ Critique](#4-docsmeta-critique)
5. [Recommendations Summary](#5-recommendations-summary)
6. [Files Reference](#6-files-reference)

---

## 1. Open Questions (Project Direction)

These questions emerged from comprehensive review and should inform future direction.

### On Emergence

| # | Question | Why It Matters |
|---|----------|----------------|
| Q1 | What specific emergent behaviors have you observed? (Specialization, price formation, firm-like structures?) | Core hypothesis validation |
| Q2 | What's the minimum viable complexity for emergence? Can you strip genesis artifacts and still see coordination? | Informs architecture direction |
| Q3 | How do you distinguish emergence from prompt-following? If agents coordinate because prompts say "coordinate", is that emergence? | Methodological clarity |
| Q4 | Does emergence scale with agent count? 2 vs 5 vs 20 agents—qualitative differences? | Experiment design |

### On Economics & Value

| # | Question | Why It Matters |
|---|----------|----------------|
| Q5 | How do you value artifacts objectively? LLM scoring is proxy—what external ground truth matters? | Economy grounding |
| Q6 | What happens when scrip is worthless? If agents have no reason to value scrip, the economy is cargo cult. | Incentive design |
| Q7 | Is debt actually used? Do agents borrow/lend? Have credit markets formed? | Feature validation |
| Q8 | What's the minimum scarcity level for interesting behavior? Current config has generous limits. | Experiment calibration |

### On Agent Intelligence

| # | Question | Why It Matters |
|---|----------|----------------|
| Q9 | What's your experience with agent competence? Do they use economic primitives effectively? | Bottleneck identification |
| Q10 | What minimal intelligence produces economic coordination? Is gemini-3-flash sufficient? | Model selection |
| Q11 | How do agents learn from experience? Does memory system improve behavior over time? | Learning validation |

### On Practical Matters

| # | Question | Why It Matters |
|---|----------|----------------|
| Q12 | What's your compute budget for experiments? $100 config—testing vs real emergence? | Resource planning |
| Q13 | How long do experiments run? Ticks, real-time, or until budget exhaustion? | Experiment design |
| Q14 | What visualization/analysis tools detect emergence patterns? Gini coefficient, trade graphs? | Observability |

### On Security & Risk

| # | Question | Why It Matters |
|---|----------|----------------|
| Q15 | What's the plan when agents do things you don't want? "Observe, don't prevent" is risky with external integrations. | Risk management |
| Q16 | How do you handle malicious artifacts? Executable artifacts run arbitrary code. | Security model |

### On Cold Start

| # | Question | Why It Matters |
|---|----------|----------------|
| Q17 | What happens without genesis artifacts? Have you tried minimal-genesis experiments? | Emergence validation |
| Q18 | Why do agents trust genesis artifacts? Initial prompts reference them—instruction not discovery. | Design philosophy |

### On Adoption & Complexity

| # | Question | Why It Matters |
|---|----------|----------------|
| Q19 | Is there a minimal viable onboarding path? 23 meta-patterns, 7+ CI gates is heavy. | Adoption barrier |
| Q20 | Who is the target audience? Researchers? Developers? Both need different docs. | Documentation strategy |

### Suggested Prioritization

| Priority | Questions | Rationale |
|----------|-----------|-----------|
| High | Q1, Q5, Q9 | Core hypothesis validation |
| Medium | Q2, Q6, Q17 | Informs architecture direction |
| Lower | Q12-14 | Operational, answer with data |
| Deferred | Q15-16 | Important when external integration happens |

---

## 2. Documentation Cleanup Plan

### Phase 1: Quick Wins (Low Risk)

| Item | File | Action | Risk |
|------|------|--------|------|
| 1.1 | `docs/TASK_LOG.md` | Delete | None—frozen at 2026-01-11, superseded |
| 1.2 | `docs/MULTI_CC_ANALYSIS.md` | Archive to `docs/archive/` | None—historical analysis |
| 1.3 | Root `CLAUDE.md` lines 8-24 | Remove TEMP rebase notice (if PRs merged) | Low |
| 1.4 | `docs/features/mint_auction.md` | Fix oracle to mint terminology | Low |

### Phase 2: Stale Content Updates (Medium Risk)

| Item | File | Issue | Action |
|------|------|-------|--------|
| 2.1 | `docs/architecture/current/mint.md` | Describes WAITING/BIDDING/CLOSED phases | Remove phase descriptions, reflect anytime bidding (Plan #5) |
| 2.2 | `docs/AGENT_HANDBOOK.md` | Lines 96, 346, 355-362 reference bidding windows | Remove outdated references |
| 2.3 | `docs/architecture/current/genesis_artifacts.md` | Shows `bidding_window: 3` in example | Mark as deprecated or remove |
| 2.4 | `docs/architecture/current/configuration.md` | Shows deprecated auction config | Mark bidding_window/first_auction_tick as deprecated |
| 2.5 | `docs/architecture/current/resources.md` | Uses "flow/stock" terminology | Update to depletable/allocatable/renewable |
| 2.6 | `docs/architecture/current/execution_model.md` | References "flow resources" | Update to "renewable resources" |
| 2.7 | Multiple docs | "Last verified" dates predate relevant plan completions | Audit and fix dates |

### Phase 3: Structural Improvements (Higher Risk)

| Item | Description | Rationale |
|------|-------------|-----------|
| 3.1 | Create `docs/meta/COMMAND_REFERENCE.md` | Single source for all script commands (currently in 4+ places) |
| 3.2 | Restructure root CLAUDE.md | Reduce from 702 to ~150 lines; move philosophy, detailed workflow elsewhere |
| 3.3 | Clarify gap tracking hierarchy | Document that docs/plans/ (34 gaps) is authoritative; docs/architecture/gaps/ (142) is reference |
| 3.4 | Fix workflow instructions | Clarify that `make worktree` is primary entry point (handles both creation + claiming) |

### Phase 4: Meta Pattern Cleanup

| Item | Pattern | Issue | Action |
|------|---------|-------|--------|
| 4.1 | All patterns | No status indicators | Add Stable/Beta/Proposed/Deprecated status to each |
| 4.2 | 09 (Documentation Graph) | Presented as current but not implemented | Mark as "Proposed - ADR-0005 not yet deployed" |
| 4.3 | 12 (Structured Logging) | 250 lines, not deployed | Mark as "Proposed - JSONL logging not deployed" |
| 4.4 | 13 (Feature-Driven Dev) | 600+ lines, partially aspirational | Clarify what's deployed vs aspirational |
| 4.5 | 16 (Plan Blocker Enforcement) | Script doesn't exist | Mark as "Proposed - script not implemented" |
| 4.6 | 21 (PR Coordination) | Full GHA workflow presented first, then admits not implemented | Reorder: simple approach first |
| 4.7 | 04 + 05 (Mocking) | Related but presented as independent | Merge or explicitly link |
| 4.8 | 18 + 19 (Claim + Worktree) | Tightly coupled but implicit | Document dependency |
| 4.9 | 15 + 18 | Trivial exemption duplicated | Consolidate to single source |
| 4.10 | 01 (README) | Claims 08+10 "subsumed" by 09 | Remove claim until 09 deployed |
| 4.11 | — | Referenced but missing | Create `docs/meta/TEMPLATE.md` |

### Phase 5: Post-V1 Cleanup (Defer)

| Item | File | Action | Timing |
|------|------|--------|--------|
| 5.1 | `docs/ARCHITECTURE_DECISIONS_2026_01.md` | Archive | After V1 decisions finalized |
| 5.2 | `docs/DESIGN_CLARIFICATIONS.md` | Archive | After V1, rationale in ADRs |
| 5.3 | `docs/GLOSSARY.md` | Delete | After V1, when TARGET becomes canonical |
| 5.4 | `docs/GLOSSARY_CURRENT.md` | Delete | After V1, merged into GLOSSARY |
| 5.5 | `docs/plans/08_agent_rights.md` | Archive | After V1 (explicitly post-V1) |
| 5.6 | `docs/plans/13_doc_line_refs.md` | Archive | After V1 (explicitly post-V1) |

---

## 3. Specific Issues Found

### 3.1 Critical: Stale Auction Phase Documentation

**Background:** Plan #5 (Oracle Anytime Bidding) is Complete. Bids are now accepted anytime—no WAITING/BIDDING/CLOSED phases.

**Affected Files:**

| File | Lines | Issue |
|------|-------|-------|
| `docs/architecture/current/mint.md` | 8-11 | Describes phases that no longer exist |
| `docs/architecture/current/mint.md` | 48 | "Only during BIDDING phase" |
| `docs/AGENT_HANDBOOK.md` | 96 | "Submit sealed bid during bidding window" |
| `docs/AGENT_HANDBOOK.md` | 346 | "Wait for bidding window" |
| `docs/AGENT_HANDBOOK.md` | 355-362 | Describes WAITING/BIDDING/CLOSED phases |
| `docs/features/mint_auction.md` | State machine section | Shows old phase transitions |

### 3.2 Critical: Oracle to Mint Rename Incomplete

**Background:** Plan #34 (Oracle to Mint Rename) is Complete (2026-01-13).

**Remaining References:**

| File | Issue |
|------|-------|
| `docs/features/mint_auction.md` | References `genesis_oracle.submit`, `genesis_oracle.bid` |
| `docs/GLOSSARY_CURRENT.md` | Line 78 shows `genesis.oracle.*` |

### 3.3 High: Deprecated Config Still Documented

**Config keys `bidding_window` and `first_auction_tick` are deprecated but documented:**

| File | Issue |
|------|-------|
| `docs/architecture/current/mint.md` | Lists both with defaults |
| `docs/architecture/current/configuration.md` | Shows full auction config with both |
| `docs/architecture/current/genesis_artifacts.md` | Shows `bidding_window: 3` example |

### 3.4 High: Root CLAUDE.md Issues

| Issue | Location | Details |
|-------|----------|---------|
| Oversized | Entire file | 702 lines—mixes 13+ topics |
| Stale notice | Lines 8-24 | "TEMP: PRs Need Rebase" dated 2026-01-15 |
| Conflicting workflow | Lines 6 vs 326 | "check_claims first" vs "make worktree handles both" |
| Philosophy duplication | Lines 35-94 | Duplicates README.md content |

### 3.5 High: Command Duplication

Commands appear in multiple places:

| Command | Locations |
|---------|-----------|
| `pytest tests/` | CLAUDE.md, tests/CLAUDE.md, scripts/CLAUDE.md |
| `check_claims.py --list` | CLAUDE.md (x2), docs/plans/CLAUDE.md, scripts/CLAUDE.md |
| `check_plan_tests.py --plan N` | CLAUDE.md (x2), scripts/CLAUDE.md, docs/plans/CLAUDE.md |
| `complete_plan.py --plan N` | CLAUDE.md (x2), scripts/CLAUDE.md, docs/plans/CLAUDE.md |

### 3.6 Medium: Terminology Drift

| File | Issue |
|------|-------|
| `docs/architecture/current/resources.md` | Uses "stock" and "flow" (deprecated) |
| `docs/architecture/current/execution_model.md` | References "flow resources" multiple times |
| `docs/GLOSSARY_CURRENT.md` | Shows deprecated terms as current |

### 3.7 Medium: "Last Verified" Date Issues

| File | Verified Date | Problem |
|------|---------------|---------|
| `mint.md` | 2026-01-12 | Plan #5 completed 2026-01-15 (should have updated) |
| `configuration.md` | 2026-01-16 (Plan #57) | Plan #57 is agent improvements, not auction config |

### 3.8 Medium: Gap Tracking Hierarchy Unclear

- **34 gaps** in `docs/plans/` (implementation tracking)
- **142 gaps** in `docs/architecture/gaps/` (detailed reference)
- No clear documentation of which is authoritative
- Both referenced interchangeably in root CLAUDE.md

### 3.9 Low: Files to Delete/Archive

| File | Reason | Action |
|------|--------|--------|
| `docs/TASK_LOG.md` | Frozen 2026-01-11, superseded by active-work.yaml | Delete |
| `docs/MULTI_CC_ANALYSIS.md` | Historical, improvements implemented | Archive |

---

## 4. docs/meta/ Critique

### 4.1 Overview

- **23 patterns** numbered 01-23
- **1 archived pattern** (handoff-protocol.md)
- **~4,500 lines** of process documentation

### 4.2 Critical Issues

#### 4.2.1 Aspirational Patterns Presented as Current

| Pattern | Claims | Reality |
|---------|--------|---------|
| 09 (Documentation Graph) | "Unified relationships.yaml" | File doesn't exist; separate governance.yaml and doc_coupling.yaml |
| 12 (Structured Logging) | "DualLogger with JSONL output" | No JSONL logging deployed |
| 13 (Feature-Driven Development) | "feature.yaml schema, locks" | features/ exists but isn't primary organization |
| 16 (Plan Blocker Enforcement) | "check_plan_blockers.py script" | Script doesn't exist |

**Impact:** Implementers will build for non-existent systems.

#### 4.2.2 README Claims Patterns "Subsumed" But They're Not

From `01_README.md` lines 32-36:
> "Patterns #08 (ADR Governance) and #10 (Doc-Code Coupling) are subsumed by #09 (Documentation Graph)"

But pattern 09 references ADR-0005 ("proposed")—the unified graph doesn't exist. Patterns 08 and 10 are what's actually deployed.

#### 4.2.3 Implicit Dependencies

| Pattern | Depends On | Stated? |
|---------|------------|---------|
| 05 (Mock Enforcement) | 04 (Mocking Policy) | No |
| 14 (Feature Linkage) | 13 (Feature-Driven Dev) | Implied |
| 19 (Worktree Enforcement) | 18 (Claim System) | No |

### 4.3 Structural Issues

#### 4.3.1 Numbering Is Arbitrary

Current 01-23 numbering doesn't reflect:
- Logical groupings (testing, docs, coordination)
- Dependencies (04 before 05, 18 before 19)
- Reading order or importance

#### 4.3.2 DRY Violations

Trivial exemption criteria appear identically in:
- Pattern 15 (Plan Workflow) lines 153-180
- Pattern 18 (Claim System) lines 219-230

#### 4.3.3 Missing Referenced Files

| Referenced | In Pattern | Exists? |
|------------|-----------|---------|
| `docs/meta/TEMPLATE.md` | 01 (README) | No |
| `scripts/check_plan_blockers.py` | 16 | No |
| `scripts/derive_governance.py` | 14 | No |
| `scripts/relationships.yaml` | 09 | No |

### 4.4 Pattern-by-Pattern Issues

| # | Pattern | Status | Issues |
|---|---------|--------|--------|
| 01 | README | Active | Claims 08+10 subsumed by unimplemented 09 |
| 03 | Testing Strategy | Stable | Markers described may not be consistently used |
| 04 | Mocking Policy | Stable | Should link to 05 |
| 05 | Mock Enforcement | Stable | Should link to 04; script is pseudo-code |
| 06 | Git Hooks | Stable | Platform-specific (Bash only) |
| 07 | ADR | Stable | "Optional" governance sync unclear |
| 08 | ADR Governance | Stable | Claimed "subsumed" but is what's deployed |
| 09 | Documentation Graph | **Proposed** | ADR-0005 not implemented; relationships.yaml doesn't exist |
| 10 | Doc-Code Coupling | Stable | Claimed "subsumed" but is what's deployed |
| 11 | Terminology | Incomplete | Just references GLOSSARY, no local summary |
| 12 | Structured Logging | **Proposed** | 250 lines, not deployed |
| 13 | Feature-Driven Dev | **Partial** | 600+ lines; features/ isn't primary org |
| 14 | Feature Linkage | **Partial** | Depends on 13 which is partial |
| 15 | Plan Workflow | Stable | Trivial exemption duplicated from 18 |
| 16 | Plan Blocker Enforcement | **Proposed** | Script doesn't exist |
| 17 | Verification Enforcement | Stable | Documents gaps but unclear if fixed |
| 18 | Claim System | Stable | Implicit dependency on 19; trivial exemption duplicated |
| 19 | Worktree Enforcement | Stable | Assumes jq available; implicit coupling to 18 |
| 20 | Rebase Workflow | Stable | Conflict resolution section brief |
| 21 | PR Coordination | **Misleading** | Full GHA workflow first, then admits not implemented |
| 22 | Human Review | Stable | Good pattern |
| 23 | Plan Status Validation | Stable | Good pattern |

### 4.5 Questions About docs/meta/

1. **Should aspirational patterns live elsewhere?** Perhaps `docs/meta/proposed/` to keep main directory for deployed patterns?

2. **Is Feature-Driven Development (13) or Plan Workflow (15) canonical?** Pattern 13 describes features.yaml as central, but docs/plans/ is the actual organizational hub.

3. **Who is the audience?** CC instances? Human developers? Both need different detail levels.

4. **Should patterns 08+10 merge with 09 or stay separate?** If 09 is the goal, maintain roadmap. If 09 is years away, remove "subsumed" language.

5. **Is 23 patterns too many?** Could merge (04+05, 18+19) and archive unused (12). Target ~15 stable patterns?

### 4.6 What's Working Well

Despite issues, several patterns are excellent:
- **03 (Testing Strategy)** - Clear hierarchy, good examples
- **06 (Git Hooks)** - Thorough, actionable
- **17 (Verification Enforcement)** - Honest about lessons learned
- **20 (Rebase Workflow)** - Practical, well-structured
- **22 (Human Review)** - Solves real problem clearly

The pattern template itself is good. The problem is deployment consistency, not design.

---

## 5. Recommendations Summary

### Immediate (Can Do Now)

| # | Action | Risk | Effort |
|---|--------|------|--------|
| R1 | Delete `docs/TASK_LOG.md` | None | 1 min |
| R2 | Archive `docs/MULTI_CC_ANALYSIS.md` | None | 1 min |
| R3 | Remove TEMP rebase notice from CLAUDE.md (if PRs merged) | Low | 1 min |
| R4 | Add "PROPOSED" banner to patterns 09, 12, 13, 16 | Low | 10 min |
| R5 | Remove "subsumed" claim from meta README | Low | 5 min |

### Short-Term (This Week)

| # | Action | Risk | Effort |
|---|--------|------|--------|
| R6 | Update mint.md for anytime bidding | Medium | 30 min |
| R7 | Update AGENT_HANDBOOK.md (remove bidding window refs) | Medium | 20 min |
| R8 | Fix oracle to mint terminology in feature docs | Low | 15 min |
| R9 | Create `docs/meta/TEMPLATE.md` | Low | 10 min |
| R10 | Add `depends_on` to meta patterns with dependencies | Low | 30 min |

### Medium-Term (This Month)

| # | Action | Risk | Effort |
|---|--------|------|--------|
| R11 | Create `docs/meta/COMMAND_REFERENCE.md` | Medium | 1 hr |
| R12 | Restructure root CLAUDE.md (~150 lines) | High | 2 hr |
| R13 | Add status metadata to all meta patterns | Medium | 1 hr |
| R14 | Consolidate trivial exemption (patterns 15+18) | Low | 20 min |
| R15 | Clarify gap tracking hierarchy in docs | Medium | 30 min |
| R16 | Update PR Coordination pattern (simple approach first) | Medium | 30 min |

### Long-Term (Post-V1)

| # | Action | Risk | Effort |
|---|--------|------|--------|
| R17 | Archive ARCHITECTURE_DECISIONS_2026_01.md | Low | 5 min |
| R18 | Archive DESIGN_CLARIFICATIONS.md | Low | 5 min |
| R19 | Merge glossaries (TARGET to GLOSSARY) | Medium | 30 min |
| R20 | Implement pattern 09 (Documentation Graph) or archive | High | Days |
| R21 | Deploy pattern 12 (Structured Logging) or archive | High | Days |

### Decision Points (Need Your Input)

| # | Decision | Options |
|---|----------|---------|
| D1 | Is Feature-Driven (13) or Plan-Driven (15) canonical? | A) Features, B) Plans, C) Both (clarify relationship) |
| D2 | Should aspirational patterns move to proposed/? | A) Yes, B) No (just add status banners) |
| D3 | Merge patterns 04+05 (Mocking)? | A) Merge, B) Keep separate with explicit link |
| D4 | Merge patterns 18+19 (Claim+Worktree)? | A) Merge, B) Keep separate with explicit link |
| D5 | Target number of stable patterns? | A) Keep 23, B) Consolidate to ~15 |

---

## 6. Files Reference

### Files to Delete

| File | Reason |
|------|--------|
| `docs/TASK_LOG.md` | Frozen, superseded by active-work.yaml |

### Files to Archive

| File | Reason | Timing |
|------|--------|--------|
| `docs/MULTI_CC_ANALYSIS.md` | Historical analysis, improvements implemented | Now |
| `docs/ARCHITECTURE_DECISIONS_2026_01.md` | Date-stamped working doc | Post-V1 |
| `docs/DESIGN_CLARIFICATIONS.md` | V1/V2 staging, rationale now in ADRs | Post-V1 |

### Files to Update (Stale Content)

| File | Issue |
|------|-------|
| `docs/architecture/current/mint.md` | Auction phases, deprecated config |
| `docs/AGENT_HANDBOOK.md` | Bidding window references |
| `docs/architecture/current/genesis_artifacts.md` | Deprecated config example |
| `docs/architecture/current/configuration.md` | Deprecated config |
| `docs/architecture/current/resources.md` | flow/stock terminology |
| `docs/architecture/current/execution_model.md` | flow resources terminology |
| `docs/features/mint_auction.md` | oracle terminology |

### Files to Update (Meta Patterns)

| File | Issue |
|------|-------|
| `docs/meta/01_README.md` | "Subsumed" claim for unimplemented pattern |
| `docs/meta/09_documentation-graph.md` | Needs "PROPOSED" status |
| `docs/meta/12_structured-logging.md` | Needs "PROPOSED" status |
| `docs/meta/13_feature-driven-development.md` | Needs clarity on what's deployed |
| `docs/meta/16_plan-blocker-enforcement.md` | Needs "PROPOSED" status |
| `docs/meta/21_pr-coordination.md` | Reorder (simple approach first) |

### Files to Create

| File | Purpose |
|------|---------|
| `docs/meta/TEMPLATE.md` | Pattern template (referenced but missing) |
| `docs/meta/COMMAND_REFERENCE.md` | Single source for script commands |

### Files to Merge/Consolidate (Post-V1)

| Files | Into |
|-------|------|
| `GLOSSARY.md` + `GLOSSARY_CURRENT.md` + `GLOSSARY_TARGET.md` | Single `GLOSSARY.md` |

---

**End of Assessment**

*This document captures all findings from the 2026-01-16 documentation audit. No changes have been made. All actions require explicit approval.*
