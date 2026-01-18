# Prioritized Actions from Code & Documentation Review

**Date:** 2026-01-16
**Purpose:** Organized by decision difficulty so you can quickly approve easy wins

---

## Tier 1: Obvious Wins (Just approve - no design decisions needed)

These are low-risk, clear benefit. Say "do tier 1" to approve all.

| # | Action | Why Obvious | Effort |
|---|--------|-------------|--------|
| 1.1 | Update `cryptography` 41.0.7 → 46.0.3 | HIGH severity CVEs | 2 min |
| 1.2 | Update `urllib3` 2.0.7 → 2.6.3 | HIGH severity security patches | 2 min |
| 1.3 | Delete `docs/TASK_LOG.md` | Frozen 2026-01-11, superseded by active-work.yaml | 1 min |
| 1.4 | Archive `docs/MULTI_CC_ANALYSIS.md` to `docs/archive/` | Historical analysis, improvements implemented | 1 min |
| 1.5 | Remove TEMP rebase notice from CLAUDE.md (lines 8-24) | PRs are merged | 1 min |
| 1.6 | Fix `docs/acceptance_gates/mint_auction.md` oracle→mint terminology | Plan #34 completed but refs remain | 5 min |
| 1.7 | Fix `docs/GLOSSARY_CURRENT.md` line 78 oracle→mint | Same issue | 2 min |
| 1.8 | Add "PROPOSED" banner to pattern 09 (Documentation Graph) | Not implemented, misleads implementers | 2 min |
| 1.9 | Add "PROPOSED" banner to pattern 12 (Structured Logging) | Not deployed | 2 min |
| 1.10 | Add "PROPOSED" banner to pattern 16 (Plan Blocker) | Script doesn't exist | 2 min |
| 1.11 | Create `docs/meta/TEMPLATE.md` | Referenced but missing | 10 min |
| 1.12 | Remove "subsumed" claim from `docs/meta/01_README.md` | Claims 08+10 subsumed by unimplemented 09 | 2 min |
| 1.13 | Move `types-PyYAML` from requirements.txt to requirements-dev.txt | Type stubs don't belong in production | 2 min |

**Total Tier 1:** ~30 minutes, zero risk

---

## Tier 2: Likely Wins (Probably good - minor considerations)

Low risk but touch more files. Review briefly then approve.

| # | Action | Consideration | Effort |
|---|--------|---------------|--------|
| 2.1 | Update `docs/architecture/current/mint.md` - remove auction phases | Reflects Plan #5 (anytime bidding) | 20 min |
| 2.2 | Update `docs/AGENT_HANDBOOK.md` - remove bidding window refs (lines 96, 346, 355-362) | Same issue | 15 min |
| 2.3 | Mark `bidding_window`/`first_auction_tick` deprecated in config docs | Config still accepts them but unused | 10 min |
| 2.4 | Update terminology: "stock"→"depletable/allocatable", "flow"→"renewable" | In resources.md, execution_model.md | 30 min |
| 2.5 | Add `depends_on` field to meta patterns with implicit dependencies (04→05, 18→19) | Makes relationships explicit | 20 min |
| 2.6 | Consolidate trivial exemption (duplicated in patterns 15 and 18) | DRY violation | 15 min |
| 2.7 | Reorder pattern 21 (PR Coordination) - simple approach first | Currently shows unimplemented GHA workflow first | 15 min |
| 2.8 | Clarify pattern 13 (Feature-Driven Dev) - mark partial sections | 600+ lines, partially aspirational | 20 min |
| 2.9 | Update `fastapi` 0.116.1 → latest | 11 versions behind, MEDIUM priority | 5 min |

**Total Tier 2:** ~2.5 hours, low risk

---

## Tier 3: Needs Brief Discussion (Pick an option)

These have clear options. Just tell me A, B, or C.

### 3.1 Root CLAUDE.md is 702 lines

**Problem:** Mixes 13+ topics, philosophy duplicates README, conflicting workflow instructions.

**Options:**
- **A) Aggressive restructure** → Reduce to ~150 lines, move details elsewhere
- **B) Light cleanup** → Just fix conflicts and remove duplication (~400 lines)
- **C) Leave it** → It works, optimization is premature

### 3.2 genesis.py is 2,961 lines (7 classes)

**Problem:** Hard to navigate, all genesis artifacts in one file.

**Options:**
- **A) Split into 7 files** → `genesis/ledger.py`, `genesis/mint.py`, etc.
- **B) Split into 3 files** → Group by function (economic, storage, observability)
- **C) Leave it** → Monolith is fine for now

### 3.3 45+ generic exception catches violate "Fail Loud"

**Problem:** `except Exception as e:` throughout codebase, some may swallow real errors.

**Options:**
- **A) Audit all 45+** → Replace with specific exceptions or add `# exception-ok: reason`
- **B) Fix critical paths only** → executor.py (10), memory.py (7)
- **C) Leave it** → Working code, don't touch

### 3.4 Merge related meta patterns?

**Problem:** Patterns 04+05 (Mocking) and 18+19 (Claim+Worktree) are tightly coupled but separate.

**Options:**
- **A) Merge both pairs** → 21 patterns instead of 23
- **B) Just add explicit links** → Keep separate, document relationship
- **C) Leave as-is**

### 3.5 Dependency version bounds

**Problem:** All deps use `>=` (loose). Major version jumps possible.

**Options:**
- **A) Add upper bounds** → `>=1.0,<2.0` style
- **B) Pin exact versions** → `==1.0.0` style (most strict)
- **C) Leave loose** → Flexibility over stability

### 3.6 Escrow rollback bug

**Problem:** If ownership transfer fails after scrip transfer, rollback may fail. Buyer loses scrip.

**Options:**
- **A) Fix with proper transaction** → Add atomic rollback
- **B) Add warning log** → Document risk, don't fix
- **C) Accept risk** → Selection pressure, agents learn

---

## Tier 4: Design Decisions (Need real thought)

These affect project direction. Take time on these.

### 4.1 Should escrow be visible in prompts?

**Current:** Escrow only mentioned in `handbook_trading`. Agents may never discover monetization.

**Question:** Is the discovery burden intentional (emergence) or too high (frustrating)?

**Your call:** Make escrow first-class in prompts, or keep as discovery challenge?

---

### 4.2 Is prescriptive role design intentional?

**Current:** Prompts say "Alpha is drawn to building", "Beta is drawn to trading".

**Question:** Does this limit emergence? Should prompts describe incentives instead of roles?

**Your call:** Keep prescriptive, or switch to incentive-based?

---

### 4.3 What's the security model for external integrations?

**Current:** Docker is the boundary. Agents can make network calls, run shell commands.

**Question:** When Reddit/web integrations are added, agents could cause real-world harm.

**Your call:** Accept risk, add graduated isolation, or defer until needed?

---

### 4.4 Should run logs be preserved?

**Current:** `run.jsonl` generated per-run but overwritten. No historical record.

**Question:** Want to analyze emergence patterns? Need preserved logs.

**Your call:** Add log rotation/archival, or keep overwriting?

---

### 4.5 Real LLM calls in CI - keep or mock?

**Current:** `plans` job makes real Gemini calls (~$0.01-0.05 per PR, 4+ minutes).

**Question:** Is this intentional (testing reality) or wasteful (could mock)?

**Your call:** Keep real calls, add mocking, or make conditional?

---

### 4.6 Is Feature-Driven (pattern 13) or Plan-Driven (pattern 15) canonical?

**Current:** Both exist. Pattern 13 describes features.yaml as central, but docs/plans/ is actual org.

**Question:** Which is the source of truth for work organization?

**Your call:** A) Features canonical, B) Plans canonical, C) Clarify relationship

---

## Tier 5: Research Questions (Need data, not decisions)

Can't act on these without running experiments or reflecting on experience.

| # | Question | Why It Matters |
|---|----------|----------------|
| 5.1 | What emergent behaviors have you actually observed? | Core hypothesis validation |
| 5.2 | Have you run long simulations with real LLM? | No logs exist showing this |
| 5.3 | At what scale does interesting behavior appear? (2 vs 5 vs 20 agents) | Experiment design |
| 5.4 | How do you distinguish emergence from prompt-following? | Methodological clarity |
| 5.5 | Is the resource scarcity sufficient? | Current limits may be too generous |
| 5.6 | What's typical real-world token consumption? | Tests use mocks |
| 5.7 | Do agents actually use debt/escrow effectively? | Feature validation |

**Suggestion:** Run a real simulation and record observations before answering these.

---

## Quick Reference: What to Say

| To approve... | Say... |
|---------------|--------|
| All obvious wins | "do tier 1" |
| All likely wins | "do tier 2" |
| Specific items | "do 1.3, 2.1, 2.4" |
| Tier 3 decisions | "3.1: A, 3.2: B, 3.3: C" etc. |
| Tier 4 decisions | Answer the questions in prose |
| Skip something | "skip 1.5" or "defer tier 4" |

---

**End of Prioritized Actions**
