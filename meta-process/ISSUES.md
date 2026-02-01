# Meta-Process Issues

Observed problems, concerns, and technical debt for the meta-process framework itself.

Items start as **unconfirmed** observations and get triaged through investigation into
confirmed issues, plans, or dismissed.

**Last reviewed:** 2026-01-31

---

## Status Key

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `unconfirmed` | Observed, needs investigation | Investigate to confirm/dismiss |
| `monitoring` | Confirmed concern, watching for signals | Watch for trigger conditions |
| `confirmed` | Real problem, needs a fix | Create a plan |
| `planned` | Has a plan (link to plan) | Implement |
| `resolved` | Fixed | Record resolution |
| `dismissed` | Investigated, not a real problem | Record reasoning |

---

## Unconfirmed

(All items have been investigated. New observations go here.)

---

## Monitoring

### MP-012: No success metrics

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `monitoring`

**Finding:** Real gap. `meta_status.py` reports operational status (active claims, open
PRs, plan progress) but nothing tracks process effectiveness: rework rate, time-to-merge,
claim conflict frequency, or whether acceptance gates catch real issues vs adding ceremony.

The framework's philosophy emphasizes "observability over control" but doesn't observe
itself. No CI effectiveness tracking, no process ROI analysis.

**Why monitoring (not confirmed):** At current scale (1-2 CC instances), process overhead
is low and problems are visible without metrics. Metrics become important when the project
scales or when multiple adopters need to compare effectiveness.

**Trigger:** Revisit when (a) 3+ CC instances run concurrently, (b) time-to-merge
exceeds 24h regularly, or (c) a second project adopts the framework.

---

### MP-014: No convention for project-specific extensions

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `monitoring`

**Finding:** The gap is real but not currently causing problems. Project-specific
directories (`logs/`, `llm_logs/`, `dashboard-v2/`) are properly documented in architecture
docs. `src/agents/catalog.yaml` (Plan #227) works fine as an ad-hoc domain catalog —
it tracks agent lineage, versions, and genotypes without formal framework integration.

The lack of convention means no discoverability pattern, no schema validation for
project-specific catalogs, and no integration with evidence recording or gap closure.
But these aren't causing friction yet.

**Relates to:** MP-001 (identity crisis). If the framework becomes truly portable,
extension conventions become critical.

**Trigger:** Revisit when (a) another project-specific catalog or tracking structure
is created, (b) Plan #227 Phase 2 (experiments/, metrics scripts) is implemented,
or (c) a second project adopts the framework.

---

### MP-017: CONTEXT.md is optional and often forgotten

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `monitoring`
**Source:** Traycer.ai's "Ralph" pattern

**Finding:** CONTEXT.md is systematically created by `create_worktree.sh` but zero
evidence of being updated after creation (0 commits referencing CONTEXT.md updates in
a 6-day window with 50+ commits merged). The feature is inert.

**Root causes:** (1) Advisory with no enforcement — every other practice has hooks but
CONTEXT.md has none. (2) No workflow integration — not staged in git, not included in
PR descriptions. (3) Most work completes in a single session, so session continuity
isn't needed.

**When it would help:** Multi-session work (3+ sessions on same branch), complex
explorations with decision branches, handoffs between developers. These are currently
rare.

**Fix options (when triggered):** Lighten the template to 2 sections ("What Changed &
Why" + "Open Questions"), integrate into PR workflow (`make pr` pulls from CONTEXT.md),
or add a hook that only warns on branches older than 24h.

**Trigger:** Revisit when multi-session work exceeds 20% of PRs, or when handoffs
between CC instances become common.

---

## Confirmed

---

### MP-006: Pattern 13 is too large — 724 lines, 3x average, mixed concerns

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Finding:** At 724 lines with 22 major sections, Pattern 13 is 3x the average pattern
size (231 lines) and 65% larger than the 2nd-largest pattern (Pattern 15 at 440 lines).

The content is cohesive but mixes conceptual framework with operational reference:
YAML schema definitions (82 lines), CI enforcement templates (23 lines), 8-step process
flow diagram (76 lines), 4 planning depth modes, AI anti-cheating mechanisms, ADR
conformance checklists, and an incomplete enterprise pattern comparison.

**Natural split points identified:**
- YAML schema → separate reference document (~82 lines saved)
- CI enforcement template → repository's `.github/workflows/` (~23 lines)
- Incomplete enterprise comparison → expand or remove (~13 lines)
- Process flow diagram → simplify to ~40 lines

**Fix:** Keep Pattern 13 as conceptual/process pattern (~500 lines), extract YAML
schema to reference doc, move CI template to actual workflow files, address the
incomplete enterprise section. Reduces size while losing zero learning content.

---

### MP-007: Script testing gap — 49 scripts, ~20% tested, critical scripts untested

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Original observation:** "20 Python scripts with zero tests" was inaccurate.

**Corrected finding:** 49 Python scripts totaling ~17,881 lines. ~10 scripts (20%)
have test coverage via 9 test files with ~1,854 lines of tests. The remaining 39
scripts (80%) are untested.

**Critical untested scripts (destructive or core):**

| Script | Lines | Risk |
|--------|-------|------|
| `cleanup_orphaned_worktrees.py` | 275 | Deletes worktrees with `--force` — logic error = lost work |
| `cleanup_claims_mess.py` | 220 | Modifies `.claude/active-work.yaml` — no rollback |
| `recover.py` | 247 | Auto-repair orchestrator — can corrupt state |
| `check_plan_blockers.py` | 276 | Modifies plan files — missed blockers block release |
| `check_plan_overlap.py` | 238 | Complex PR analysis — false negatives allow collisions |

**Scripts safe to deprioritize:** `concat_for_review.py`, `get_governance_context.py`,
`view_log.py`, `meta_config.py` (read-only, simple transformations).

**Fix:** Priority test investment: (1) cleanup_orphaned_worktrees.py, (2) check_claims.py
gap coverage, (3) cleanup_claims_mess.py, (4) recover.py.

---

### MP-008: install.sh — 4 of 6 issues fixed, 2 deferred as feature additions

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed` (partially resolved)

4 of 6 originally reported issues have been fixed:

| Issue | Status | Fix |
|-------|--------|-----|
| `cd "$TARGET_DIR"` changes CWD | Fixed | Replaced with `git -C "$TARGET_DIR"` |
| `docs/plans/CLAUDE.md` copy logic duplicated | Fixed | Removed dead code (lines 251-257) |
| Hardcoded principles ("Fail Loud", "Test First") | Fixed | Changed to generic `YOUR_PRINCIPLE_N` + TODO prompts |
| `--minimal` mode references `scripts/doc_coupling.yaml` | Fixed | Made conditional on `--full` mode |
| No `--dry-run` option | Deferred | Feature addition — needs a plan |
| No uninstall or upgrade path | Deferred | Feature addition — needs a plan |

**Relates to:** MP-001 (identity crisis).

---

---

### MP-015: Plan-to-diff verification — partial infrastructure, plan drift undetected

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`
**Source:** Traycer.ai research

**Finding:** Infrastructure partially exists but the gap is real:

- `parse_plan.py` (137 lines) already parses "Files Affected" sections from plans
- `check-file-scope.sh` hook blocks edits to undeclared files during implementation
  (disabled by default — "too strict for exploratory work")
- 56% of active plans (9/16) have "Files Affected" sections (required by template)

**What's missing:** No script compares `git diff --name-only` against the plan's
declarations at merge time. Scope creep prevention exists (hook, disabled), but **plan
drift** (declared files never touched = incomplete implementation) is completely undetected.

**False positive risk:** Moderate. Common false positives: `tests/conftest.py`,
`config/schema.yaml`, `__init__.py`, `.claude/CONTEXT.md`. Manageable with a whitelist.

**Fix:** Add a merge-time check that compares actual diff to declared files. Flag
undeclared `src/` modifications as HIGH (scope creep), undeclared `tests/` as MEDIUM,
and untouched declared files as WARN (plan drift). Could integrate into `make check`.

---

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| MP-002 | GETTING_STARTED.md config examples wrong | Updated config examples to match actual `meta-process.yaml` format (`weight:`, `hooks:`, `enforcement:`, `planning:` sections). Fixed `scripts/meta/` → `scripts/` path references. | 2026-01-31 |
| MP-004 | Phantom script/file references | Annotated all 5 phantom references as "not yet implemented" in Patterns 09, 13, 14. Added status note to Pattern 14 explaining `features.yaml` is not yet built. | 2026-01-31 |
| MP-005 | Pattern 12 unlabeled as PROPOSED in index | Added *(proposed)* annotation to Pattern 12 entry in `01_README.md` index. | 2026-01-31 |
| MP-009 | Undocumented pattern dependencies; 3 non-patterns | Added `Requires` column to pattern index in `01_README.md` with prerequisite numbers for 14 patterns. Added note identifying 3 convention/infrastructure entries (06, 11, 26). | 2026-01-31 |
| MP-016 | No implementation-time escalation convention | Added "Escalation: When Plan Meets Reality" section to Pattern 28 with 3-step process (record in CONTEXT.md, update plan, decide continue/reduce/stop). Added "Discovered Conflicts" section to CONTEXT.md template. | 2026-01-31 |
| MP-011 | Circular docs with no linear reading path | Added "Core Concepts" glossary before adoption path in GETTING_STARTED.md. Reordered Day 1-2 reading list to follow dependency order (18 before 19). Pattern index Requires column (MP-009) addresses prerequisite visibility. | 2026-01-31 |
| MP-013 | ~30% of infrastructure unused at current scale | Added "Multi-CC only" tier to pattern index "When to Use" section, listing 5 patterns + 4 scripts to skip for solo/small setups. Added "skip for solo" note to GETTING_STARTED.md adoption stage. Features remain available but clearly marked as scale-dependent. | 2026-01-31 |
| MP-001 | Portable framework, project-specific examples | Added "Customizing for Your Project" section to README.md with find-replace table for 8 agent_ecology2-specific terms. Identified the 4 most affected patterns. Low-effort fix; medium/high-effort options (example rewrites, core/project split) remain as future work. | 2026-01-31 |

---

## Dismissed

| ID | Description | Why Dismissed | Date |
|----|-------------|---------------|------|
| MP-003 | Competing "single source of truth" architectures | Not competing. `relationships.yaml` (Pattern 09) is the unified source of truth for doc-code coupling, actively enforced by `check_doc_coupling.py` and `sync_governance.py`. `doc_coupling.yaml` and `governance.yaml` are deprecated (have explicit headers). Acceptance gates (`meta/acceptance_gates/*.yaml`, Patterns 13/14) serve an orthogonal purpose: feature completion verification, not doc-code relationships. The patterns describe different concerns, not contradictory architectures. | 2026-01-31 |
| MP-010 | Documentation repetition across files | Intentional audience segmentation, not accidental drift. CWD rule appears in 5 places but each serves a distinct audience: CLAUDE.md (canonical rules), UNDERSTANDING_CWD.md (deep reference), CWD_INCIDENT_LOG.md (forensic/historical), GETTING_STARTED.md (onboarding with cross-refs to deep docs), Pattern 19 (enforcement mechanism). Claims similarly follow progressive disclosure. Minor issue: GETTING_STARTED.md line 103 references `scripts/meta/check_claims.py` (wrong path, should be `scripts/check_claims.py`). | 2026-01-31 |

---

## How to Use This File

1. **Observe something off?** Add an entry under Unconfirmed with what you saw and
   what investigation would look like
2. **Investigating?** Update the entry with findings, move to appropriate status
3. **Confirmed and needs a fix?** Create a plan, link it, move to Confirmed/Planned
4. **Not actually a problem?** Move to Dismissed with reasoning
5. **Watching a concern?** Move to Monitoring with trigger conditions

This file tracks issues with the **meta-process framework itself**, not the
agent_ecology2 system. For system-level issues, see `docs/CONCERNS.md` and
`docs/architecture/TECH_DEBT.md`.
