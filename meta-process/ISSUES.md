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

Items observed but not yet investigated in depth. Each needs someone to dig in
and determine whether it's a real problem, and if so, what category it falls into.

### MP-001: Identity crisis — portable framework vs project documentation

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Patterns are saturated with agent_ecology2-specific examples (escrow, kernel, ledger,
artifact trading). The framework claims portability (`install.sh`, generic docs) but
examples are deeply project-specific. A developer installing this into a different project
would need to mentally translate every example.

**To investigate:** Is the intent to be truly portable? If so, which patterns need
generic examples? If not, should `install.sh` and portability framing be removed?

---

### MP-006: Pattern 13 (Acceptance-Gate-Driven Development) is too large for a single pattern

**Observed:** 2026-01-31
**Status:** `unconfirmed`

At 725 lines, Pattern 13 includes a process flow diagram, schema definitions, CI
templates, role assignments, planning mode taxonomy, anti-cheating mechanisms, ADR
conformance checklists, and enterprise pattern comparisons. This is a specification
document, not a pattern.

**To investigate:** Would splitting into sub-documents (concept overview, schema
reference, process flow, CI integration) improve adoptability? Or is the monolithic
format intentional?

---

### MP-007: No tests for meta-process scripts

**Observed:** 2026-01-31
**Status:** `unconfirmed`

20 Python scripts totaling ~230KB of code with zero test files. `check_claims.py`
alone is 42KB. For a framework whose central thesis is TDD and "real tests over mocks,"
the absence of tests for its own tooling is a credibility gap.

**To investigate:** What's the risk profile? Are these scripts stable enough that
tests aren't needed, or are there latent bugs? What would a minimal test suite cover?

---

---

### MP-011: Circular documentation reading path

**Observed:** 2026-01-31
**Status:** `unconfirmed`

README says see GETTING_STARTED.md. GETTING_STARTED references pattern files. Pattern
files reference other patterns, ADRs, templates, and back to the README. A newcomer
has no clear entry point or reading order.

**To investigate:** Would a single "read this first" document (no forward references,
complete end-to-end overview) solve this? Or is the cross-referencing working fine for
actual adopters?

---

### MP-012: No success metrics

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Nothing measures whether the meta-process is helping. No way to track rework rate,
time to merge, claim conflict frequency, or whether acceptance gates catch real issues
vs adding ceremony.

**To investigate:** Is this a real problem or premature optimization? What lightweight
metrics would indicate the process is working (or not)? Does Traycer.ai or similar
tooling offer ideas here?

---

### MP-013: Overengineered for actual scale

**Observed:** 2026-01-31
**Status:** `unconfirmed`

The inter-CC messaging system, scope-based claim conflicts, file-level access control,
and locked spec enforcement appear designed for 10+ concurrent AI agents on a massive
codebase. The actual project runs 2-3 Claude Code instances.

**To investigate:** Is this forward-looking design (preparing for scale) or premature
complexity? Which features are earning their keep vs adding overhead? Could some be
disabled by default and documented as "enable at scale"?

---

### MP-014: No convention for project-specific extensions to the meta-process

**Observed:** 2026-01-31
**Status:** `unconfirmed`

The meta-process provides standard directories (`meta-process/patterns/`, `docs/plans/`,
`docs/adr/`, `meta/acceptance_gates/`). But when a project needs domain-specific tracking
— e.g., agent experiment results, design catalogs, simulation learnings — there's no
convention for how to add it.

Current result: project-specific concerns get invented ad-hoc (Plan #227 proposes
`experiments/`, `catalog.yaml`, and metrics scripts with no connection to existing
meta-process infrastructure like evidence recording, gap closure, or acceptance gates).

**Initial instinct:** A `meta/project/` (or similar) directory for project-specific
subdirectories, with configurable rules for how they integrate with the meta-process
(e.g., what links to gap closure, what feeds into evidence, what has a schema).

**To investigate:** What should the standard vs. project-specific boundary look like?
Should integration rules be pattern-based (guidance) or config-based (enforced)?
How does this relate to MP-001 (portability identity crisis)?

---

### MP-015: No plan-to-diff verification

**Observed:** 2026-01-31
**Status:** `unconfirmed`
**Source:** Traycer.ai research — their verification phase compares actual diffs against plans

Every plan declares a "Files Affected" section listing what will be touched. But nothing
checks whether the actual changes match that declaration. Undeclared file modifications
(scope creep) and declared files never touched (plan drift) go undetected.

**To investigate:** How hard would a script be that compares `git diff --name-only`
against the plan's "Files Affected" list? Could this be added to `make check`? What's
the false positive rate (e.g., touching conftest.py that's not in the plan)?

---

### MP-016: No implementation-time escalation convention

**Observed:** 2026-01-31
**Status:** `unconfirmed`
**Source:** Traycer.ai's "Bart" orchestrator pauses and asks the human when code conflicts with spec

Question-driven planning (Pattern 28) surfaces unknowns *before* implementation. But
when a CC instance discovers mid-implementation that the plan's assumptions are wrong,
there's no structured response. The instance either silently deviates from the plan or
stops without explanation.

**To investigate:** Would a convention like "if reality contradicts the plan, update
CONTEXT.md with the conflict and stop" be sufficient? Should this be a hook, a pattern,
or just CLAUDE.md guidance? How does Traycer's approach compare?

---

### MP-017: CONTEXT.md is optional and often forgotten

**Observed:** 2026-01-31
**Status:** `unconfirmed`
**Source:** Traycer.ai's "Ralph" pattern — aggressive externalization of state to disk prevents context rot

Each worktree has a `.claude/CONTEXT.md` for tracking progress across sessions, but it's
advisory. In practice it often doesn't get updated. Traycer's approach treats externalized
state as mandatory — the agent reads state from disk on every cycle rather than relying
on chat history.

**To investigate:** Could a hook warn when CONTEXT.md hasn't been updated in the current
worktree? Would that be annoying or useful? What's the minimum useful content for
CONTEXT.md to actually help session continuity?

---

## Monitoring

(None yet — items move here from Unconfirmed after investigation confirms
they're real but not urgent)

---

## Confirmed

### MP-002: GETTING_STARTED.md config examples don't match actual meta-process.yaml

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Original observation:** Thought no script read `meta-process.yaml` and three config
formats contradicted each other.

**Finding:** `meta-process.yaml` IS actively parsed by 5+ scripts (`meta_process_config.py`,
`check_doc_coupling.py`, `sync_plan_status.py`, `check_planning_patterns.py`,
`bootstrap_meta_process.py`, `health_check.py`, `meta_config.py`). The central config is
real and functional.

**Remaining problem:** `GETTING_STARTED.md` shows config examples (`enabled: { plans: true }`,
`weight: medium`) that don't match the actual `meta-process.yaml` format. An adopter
following the docs would write a config that doesn't match what scripts expect.

**Fix:** Update GETTING_STARTED.md examples to match the actual schema, or add a config
validation script that catches format mismatches.

---

### MP-004: Phantom script/file references (5 of 7 confirmed)

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Original observation:** 7 referenced scripts/files appeared missing.

**Finding:** 2 of 7 actually exist:
- `view_log.py` — exists at `scripts/view_log.py`
- `relationships.yaml` — exists at `scripts/relationships.yaml` (deployed file, not a template)

5 references are genuinely phantom:

| Referenced | In Pattern | Status |
|-----------|-----------|--------|
| `generate_tests.py` | 13 (Acceptance Gates) | Not implemented |
| `migrate_to_relationships.py` | 09 (Documentation Graph) | Not implemented (pattern notes it's optional) |
| `features.yaml` | 14 (Gate Linkage) | Not implemented, no template |
| `config/spec_requirements.yaml` | 13 | Not implemented, no template |
| `config/defaults.yaml` | 13 | Not implemented, no template |

**Fix:** Either implement the missing scripts/templates or remove the references from
the patterns. Most of these come from Pattern 13 which is already flagged as oversized
(MP-006) — removing aspirational references during a refactor would be natural.

---

### MP-005: Pattern 12 listed as active in index but marked PROPOSED

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Finding confirmed:** `01_README.md` line 21 lists Pattern 12 as
`[Structured Logging](12_structured-logging.md) | Unreadable logs | Low` with no
status qualifier. But the pattern file itself says:

> **STATUS: PROPOSED** — Currently NOT DEPLOYED. The system uses standard Python logging.
> See Plan #60 for the current logging approach (SummaryLogger).

**Fix:** Add a status column to the pattern index table, or annotate undeployed patterns
inline (e.g., "Structured Logging *(proposed)*"). Minimal change, high clarity gain.

---

### MP-008: install.sh — all 6 reported issues confirmed, never tested externally

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

All 6 originally reported issues confirmed through investigation:

| Issue | Severity | Detail |
|-------|----------|--------|
| `cd "$TARGET_DIR"` (line 202) changes CWD | Low | Runs in subshell so doesn't leak, but violates the framework's own CWD principles |
| `docs/plans/CLAUDE.md` copy logic duplicated | Low | Lines 154-156 copy the file; lines 252-256 try again but it's dead code (file already exists) |
| Hardcoded principles ("Fail Loud", "Test First") | Medium | `sed` substitutions at lines 223-233 bake agent_ecology2 principles into any adopter's CLAUDE.md |
| `--minimal` mode references `scripts/doc_coupling.yaml` | Medium | Final instructions (line 270) tell user to edit a file that only exists after `--full` |
| No `--dry-run` option | Medium | Compare with `export_meta_process.py` which has `--dry-run` |
| No uninstall or upgrade path | Medium | No way to cleanly remove or update the meta-process |

**Additional finding:** No evidence this script has ever been run on a non-agent_ecology2
project. No test files, no CI coverage, no external usage documentation. The portability
claim is untested.

**Fix:** This overlaps with MP-001 (identity crisis). If the framework is meant to be
portable, install.sh needs significant rework. If not, it should be simplified to just
set up the current project.

---

### MP-009: 11+ patterns have undocumented dependencies; 3 aren't patterns

**Observed:** 2026-01-31
**Investigated:** 2026-01-31
**Status:** `confirmed`

**Finding:** Of 30 listed patterns, 11+ have implicit dependencies that aren't documented
anywhere. Key dependency chains:

- Pattern 17 (Verification) requires 15 (Plan Workflow) + 3 (Testing Strategy)
- Pattern 19 (Worktree Enforcement) requires 18 (Claims) + 20 (Branch Naming)
- Pattern 21 (PR Coordination) requires 15 + 18
- Pattern 22 (Human Review) requires 15 + 17
- Pattern 13 (Acceptance Gates) requires 7 (ADR) + 8 + 11 + 14

**3 patterns are categorically misclassified:**
- Pattern 6 (Git Hooks) — tool configuration, not a coordination pattern
- Pattern 11 (Terminology) — naming convention / glossary
- Pattern 26 (Ownership Respect) — behavioral norm / discipline

The pattern index presents all 30 as equally independent with only a complexity rating.
An adopter has no way to know which patterns can be adopted standalone vs which form
prerequisite chains.

**Fix:** Add `Requires` and `Works With` columns to `01_README.md`. Consider reclassifying
non-patterns as "conventions" or "infrastructure" in a separate section.

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| - | - | - | - |

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
