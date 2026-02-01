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

### MP-002: Configuration schema contradictions

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Three different config formats appear in documentation:

1. `GETTING_STARTED.md` shows `enabled: { plans: true }` flat format
2. `templates/meta-process.yaml.example` uses `meta_process.plans.enabled` nested format
3. `GETTING_STARTED.md` also shows `weight: medium` / `planning:` format

No script appears to actually read `meta-process.yaml`. Each script has its own config
file (`doc_coupling.yaml`, `governance.yaml`, etc.).

**To investigate:** Does any script parse `meta-process.yaml`? If not, is the config
file purely aspirational? Should we pick one schema and make scripts actually use it,
or drop the central config?

---

### MP-003: Competing "single source of truth" architectures

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Three patterns each claim to be the single source of truth for file relationships:

- Pattern 09 (Documentation Graph): `relationships.yaml` with nodes/edges
- Pattern 14 (Acceptance Gate Linkage): `features.yaml` with gate-based mappings
- Pattern 13 (Acceptance-Gate-Driven Development): `acceptance_gates/*.yaml` per-gate files

These are mutually contradictory architectures. Pattern 09 says it "subsumes" patterns
08 and 10, but `install.sh` still installs `governance.yaml` and `doc_coupling.yaml`
as separate files.

**To investigate:** Which approach does the actual project use? Which (if any) is
the intended direction? Should losing patterns be marked superseded?

---

### MP-004: Phantom script/file references

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Multiple patterns reference scripts and files that don't exist:

| Referenced | In Pattern | Exists? |
|-----------|-----------|---------|
| `generate_tests.py` | 13 (Acceptance Gates) | No |
| `migrate_to_relationships.py` | 09 (Documentation Graph) | No |
| `view_log.py` | 12 (Structured Logging) | No |
| `features.yaml` | 14 (Gate Linkage) | No template |
| `relationships.yaml` template | 09 (Documentation Graph) | No template |
| `config/spec_requirements.yaml` | 13 | No template |
| `config/defaults.yaml` | 13 | No template |

**To investigate:** Are these planned but not yet built, or stale references from
earlier designs? Should they be removed or implemented?

---

### MP-005: Pattern 12 (Structured Logging) is undeployed but listed alongside deployed patterns

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Pattern 12 is explicitly marked "PROPOSED" / "NOT DEPLOYED" in its body, but the
pattern index (`01_README.md`) lists it without any such distinction. An adopter
scanning the index has no way to know this pattern isn't battle-tested.

**To investigate:** Should it be removed from the index, marked differently in the
index, or moved to an "experimental" section?

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

### MP-008: install.sh issues

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Several potential problems in the installation script:

- Line 196: `cd "$TARGET_DIR"` changes CWD permanently (ironic given the CWD docs)
- Lines 153-156 vs 246-251: `docs/plans/CLAUDE.md` copy logic appears duplicated
- Template substitution hardcodes agent_ecology2 principles ("Fail Loud", "Test First")
- Line 265 references `scripts/doc_coupling.yaml` even in `--minimal` mode (file only
  exists after `--full`)
- No `--dry-run` option
- No uninstall or upgrade path

**To investigate:** How broken is this in practice? Has anyone actually run `install.sh`
on a non-agent_ecology2 project?

---

### MP-009: 30 patterns with invisible dependency chains

**Observed:** 2026-01-31
**Status:** `unconfirmed`

Pattern dependencies are undocumented. Pattern 17 (Verification Enforcement) requires
15 (Plan Workflow) and 18 (Claims), but nothing says so. Pattern 21 (PR Coordination)
requires GitHub Actions. Pattern 22 (Human Review) requires a label system. The
"Low/Medium/High" complexity ratings describe setup effort, not prerequisites.

Some listed patterns aren't patterns in the traditional sense — they're tool configs
(Pattern 6: Git Hooks), naming conventions (Pattern 11: Terminology), or behavioral
norms (Pattern 26: Ownership Respect).

**To investigate:** Would a dependency graph in the pattern index help? Should some
items be reclassified as "conventions" vs "patterns"? What's the minimal set of
genuinely independent patterns?

---

### MP-010: Documentation repetition across files

**Observed:** 2026-01-31
**Status:** `unconfirmed`

The CWD rule is explained in: root CLAUDE.md, UNDERSTANDING_CWD.md (228 lines),
CWD_INCIDENT_LOG.md, Pattern 19, GETTING_STARTED.md, and hooks/README.md. The claim
system is similarly explained in 4+ places.

Same information, slightly different wording, creates maintenance burden and drift risk.

**To investigate:** Is the repetition intentional (each doc is self-contained) or
accidental drift? Would a "single source, reference elsewhere" approach work without
hurting readability?

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

(None yet — items move here when they need a fix but don't have a plan yet)

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| - | - | - | - |

---

## Dismissed

| ID | Description | Why Dismissed | Date |
|----|-------------|---------------|------|
| - | - | - | - |

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
