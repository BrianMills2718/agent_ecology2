# Schema Audit Report

**Date:** 2026-01-31
**Status:** AUDIT CLOSED — All actionable items resolved. Remaining items deferred to target architecture plans.
**Scope:** Artifact schema definitions, cross-document consistency, code-doc alignment
**Method:** Systematic cross-reference of CONCEPTUAL_MODEL.yaml, CONCEPTUAL_MODEL_FULL.yaml, GLOSSARY.md, DESIGN_CLARIFICATIONS.md, architecture docs, and source code.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Code Bugs](#2-code-bugs)
3. [Security Gaps](#3-security-gaps)
4. [Cross-Document Inconsistencies](#4-cross-document-inconsistencies)
5. [Conceptual Model Divergence](#5-conceptual-model-divergence)
6. [Glossary Staleness](#6-glossary-staleness)
7. [Architecture Doc Issues](#7-architecture-doc-issues)
8. [Design Debt](#8-design-debt)
9. [Recommendations](#9-recommendations)
10. [External Review Notes](#10-external-review-notes)

---

## 1. Executive Summary

This audit found **3 code-level issues** (1 bug, 2 security gaps), **17 cross-document inconsistencies**, and **7 architecture doc issues**. The root cause is a documentation transition from ADR-0019 (kernel-mediated permissions) to ADR-0024 (artifact self-handled access) that was applied unevenly across docs.

**Resolution status (2026-01-31):** All 17 cross-document inconsistencies resolved by CMF v3 rewrite. Code bugs fixed by Plan #239. Security gaps fixed by Plan #235 Phase 0+1.

**Priority triage:**

| Priority | Issue | Action |
|----------|-------|--------|
| P0 (bug) | `_execute_edit` is broken | **FIXED** (Plan #239) |
| P0 (security) | `access_contract_id` mutable by any writer | **FIXED** (Plan #235 Phase 0) |
| P0 (security) | `type` mutable + unvalidated | **FIXED** (Plan #235 Phase 0) |
| P1 (semantic) | `depends_on` split-brain | **FIXED** (Plan #239) |
| P2 (doc drift) | CMF not updated for ADR-0024 | **RESOLVED** (CMF v3 rewrite) |
| P2 (doc drift) | GLOSSARY describes ADR-0019 only | Update for ADR-0024 |
| P3 (tech debt) | `price` vs `policy["invoke_price"]` | Defer |
| P3 (naming) | `can_execute` vs `has_loop` | Plan #230 (completed) |

---

## 2. Code Bugs

### 2.1 `_execute_edit` is entirely broken

**Location:** `src/world/action_executor.py:374-488`
**Severity:** Runtime crash on any `edit_artifact` action through the action executor

**Problem:** The `_execute_edit` method has two compounding bugs:

1. **Accesses nonexistent fields.** It reads `intent.content`, `intent.code`, `intent.executable`, `intent.price`, `intent.interface`, `intent.access_contract_id`, `intent.metadata` — none of which exist on `EditArtifactIntent` (which only has `artifact_id`, `old_string`, `new_string`). Crashes with `AttributeError` at line 420.

2. **Calls nonexistent method.** Line 476 calls `w.artifacts.update(intent.artifact_id, updates)` but `ArtifactStore` has no `update()` method. Even if bug #1 were fixed, this would crash.

**Root cause:** `_execute_edit` was written as a "field-level partial update" handler but was never rewritten when Plan #131 introduced the old_string/new_string `EditArtifactIntent`. The actual old_string/new_string logic lives in `ArtifactStore.edit_artifact()` (line 1199), which `_execute_edit` never calls.

**Why tests don't catch it:** `tests/unit/test_edit_artifact.py` tests `ArtifactStore.edit_artifact()` directly, bypassing the action executor dispatch.

**The dispatch is wired up:**
```python
# action_executor.py:99-100
elif isinstance(intent, EditArtifactIntent):
    result = self._execute_edit(intent)
```

Any agent sending an `edit_artifact` action hits this broken code path.

**Fix:** Rewrite `_execute_edit` to call `w.artifacts.edit_artifact(intent.artifact_id, intent.old_string, intent.new_string)` with proper permission checking, quota tracking, and logging.

### 2.2 `depends_on` queried from wrong source

**Location:** `src/world/kernel_queries.py:472`
**Severity:** Silent wrong results

**Problem:**
```python
depends_on = artifact.metadata.get("depends_on", [])  # WRONG
```

Queries `metadata["depends_on"]` (user-defined, unvalidated) instead of `artifact.depends_on` (the dataclass field with cycle detection and validation).

If an artifact has `depends_on=["A", "B"]` set via the proper field, a `query_kernel` for dependencies returns `[]` because metadata is a separate dict.

**Fix:** Change to `depends_on = artifact.depends_on`.

---

## 3. Security Gaps

These are already documented in DESIGN_CLARIFICATIONS.md sections 3.1-3.3 but are confirmed by this audit with additional context.

### 3.1 `access_contract_id` mutable by any writer (FM-7)

**Confirmed at:**
- `action_executor.py:467-468` (edit path — currently broken, but would be reachable once fixed)
- `action_executor.py:340` (write path — via `ArtifactStore.write()`)
- `artifacts.py` write method sets fields without creator check

**Attack scenario:** Agent A has write permission on artifact X (e.g., via a permissive contract). Agent A changes `access_contract_id` to `kernel_contract_freeware`, making X publicly accessible. All other protections on X are bypassed.

**Status:** Plan #235 Phase 0 (creator-only restriction).

### 3.2 `type` mutable + unvalidated (FM-6)

**Confirmed at:**
- `artifacts.py` write method — `artifact.type = type` on every write (no immutability)
- No validation against allowed types anywhere

**Kernel branching locations (verified):**
- `action_executor.py:220` — `type == "trigger"` triggers refresh
- `action_executor.py:614` — `type == "config"` routes to special config invoke
- `triggers.py:209` — `type != "trigger"` skip
- `genesis/memory.py:187` — `type != "memory_store"` reject
- `genesis/event_bus.py:238` — `type != "trigger"` skip

**Attack scenario:** Create a normal artifact, then write it again with `type="trigger"` to inject arbitrary trigger logic, or `type="config"` to access the cognitive self-modification path.

**Status:** Plan #235 Phase 0 (immutability + registry).

---

## 4. Cross-Document Inconsistencies

> **All 17 inconsistencies below resolved by CMF v3 rewrite (2026-01-31).** Both CM and CMF are now version 3, status `current_implementation`, with code as source of truth. The key structural fix is separating Part 1 (current ADR-0019) from Part 2 (target ADR-0024), eliminating all mixed-architecture confusion.

### 4.1 CM vs CMF: Version and Status

**RESOLVED:** Both are now version 3 with status `current_implementation`.

CM is version 2 (2026-01-31). CMF is version 1 (2026-01-28). CMF was not updated when CM was revised. They should be the same model (CM line 8: "For full version with examples, see: CONCEPTUAL_MODEL_FULL.yaml").

CMF header says "DRAFT - under active discussion" but its `status` field says `accepted`.

### 4.2 Artifact Required Fields — Direct Contradiction

**RESOLVED:** CMF v3 lists all 21 dataclass fields with types, defaults, and mutability. CM v3 lists all fields in required/optional groups matching code.

| Field | CM | CMF | Code |
|-------|-----|------|------|
| `id` | Required | Required | Required |
| `content` | Required | Required | Required |
| `code` | **Required** | Not listed | Optional (default `""`) |
| `created_by` | Required | Required | Required |
| `interface` | Separate section | **Required** | Optional (default `None`) |
| `access_contract_id` | Not listed | **Required** / "OPTIONAL" / "REMOVED" | Optional (default `"kernel_contract_freeware"`) |
| `type` | Not listed | Not listed | **Required** (no default) |
| `created_at` | Not listed | Not listed | **Required** (no default) |
| `updated_at` | Not listed | Not listed | **Required** (no default) |

No two sources agree on what fields an artifact must have.

### 4.3 `access_contract_id` — Triple Contradiction Within CMF

**RESOLVED:** CMF v3 Part 1: optional field with default `"kernel_contract_freeware"`. Part 2 (target): field removed. No contradiction.

- CMF:47-51 — Listed as **required** field (but "OPTIONAL METADATA")
- CMF:286 — "Every artifact has exactly one governing contract (or **null = default**)"
- CMF:1334-1339 — Status: **"REMOVED"**

Required, optional, and removed in the same document.

### 4.4 Kernel Permission Checking — CMF Contradicts Itself

**RESOLVED:** CMF v3 separates Part 1 (ADR-0019: kernel checks contracts) from Part 2 (ADR-0024: artifacts handle own). No mixing.

| CMF Location | Says |
|----------|------|
| Line 454-458 | "Kernel does NOT check them automatically" (ADR-0024) |
| Line 584 | Kernel enforces "Contract-based permissions" (ADR-0019) |
| Line 652-665 | "Kernel handles execution of all permission checks" (ADR-0019) |
| Line 882-883 | "Kernel does NOT enforce permissions" (ADR-0024) |

The `open_questions` section (lines 646-873) was written under ADR-0019 and never updated.

### 4.5 Null Contract — CMF Self-Contradiction

**RESOLVED:** CMF v3 Part 1: default is `kernel_contract_freeware` (not null). Part 2: no defaults. Clean separation.

- CMF:470-472 — "SUPERSEDED by ADR-0024. No kernel defaults."
- CMF:286 — "or null = default"
- CMF:853-860 — "Null contract means creator has all rights"

### 4.6 Actions Framing Differs

**RESOLVED:** Both CM v3 and CMF v3 Part 1 describe core actions as "contract-checked (ADR-0019)". Part 2 describes "artifact-handled (ADR-0024)".

- CM:183-184 — Core actions "Route through artifact handler (ADR-0024)"
- CMF:301-305 — Core actions "Go through contract permission checking" / "Kernel executes contract logic" (ADR-0019)

### 4.7 `interface` — Required vs Advisory vs Optional

**RESOLVED:** CMF v3 Part 1: optional field (default `None`), enforcement configurable. CM v3 lists as optional. Matches code.

| Source | Says |
|--------|------|
| CM:76 | `required_on: "ALL artifacts"` |
| CMF:69 | `required_on: "ALL artifacts"` |
| DESIGN_CLARIFICATIONS:296 | "advisory" |
| Code | `interface: dict[str, Any] \| None = None` (optional) |

### 4.8 `labels` Field — Documented but Nonexistent

**RESOLVED:** CMF v3 and CM v3 both explicitly state labels are "CONCEPTUAL ONLY — NOT a dataclass field." No longer implies a field exists.

CM:83-86 and CMF:81-85 define a `labels` field with common values (`data`, `service`, `contract`, `right`, `principal`, `agent`). No such field exists on the `Artifact` dataclass.

### 4.9 `code` Field — Required in CM, Optional in Code

**RESOLVED:** CMF v3 Part 1: optional (default `""`). Part 2: required for active artifacts under ADR-0024. CM v3 lists as optional. Matches code.

CM line 59: required ("all artifacts have handlers"). CMF `artifact_self_handling` line 1326: required. Code: `code: str = ""` (optional).

### 4.10 Missing Fields in Both Conceptual Models

**RESOLVED:** CMF v3 lists all 21 dataclass fields with types, defaults, mutability, and source references. CM v3 lists all fields in required/optional groups.

Fields in code but absent from CM/CMF required or optional fields:

`type`, `created_at`, `updated_at`, `deleted`/`deleted_at`/`deleted_by`, `depends_on`, `metadata`, `genesis_methods`, `policy`.

---

## 5. Conceptual Model Divergence

### 5.1 CMF contains two incompatible architectures

**RESOLVED:** CMF v3 separates Part 1 (current ADR-0019) from Part 2 (target ADR-0024) with clear banners. No mixing.

CMF lines 33-872 (main body) describe **ADR-0019**: kernel checks contracts before execution, `access_contract_id` required, null contract has defaults.

CMF lines 1268-1601 (`artifact_self_handling` section) describe **ADR-0024**: artifacts handle own access, `access_contract_id` removed, no kernel defaults.

The `open_questions` section resolves questions under ADR-0019 while the `kernel_responsibilities` section (line 878-906) gives ADR-0024 answers.

### 5.2 CM is consistent but incomplete

**RESOLVED:** CM v3 lists all 21 fields, all 11 actions, and all kernel interface methods. Describes current implementation (ADR-0019), not target.

CM (version 2) is consistently ADR-0024 but only lists 4 required fields and omits most dataclass fields. It describes the target, not code.

### 5.3 Neither model matches current code

**RESOLVED:** CMF v3 Part 1 and CM v3 both match current code (ADR-0019). Written from code as source of truth.

Code follows ADR-0019: kernel checks `access_contract_id` before execution, null contract falls back to configurable default, `run(*args)` interface.

---

## 6. Glossary Staleness

> **All glossary issues resolved (2026-01-31).** GLOSSARY.md updated with 12 fixes covering missing fields, incorrect values, and incomplete descriptions.

### 6.1 Describes ADR-0019 exclusively

**RESOLVED:** GLOSSARY correctly describes current implementation (ADR-0019). ADR-0024 is target architecture, documented separately in CMF v3 Part 2.

- Line 207: "Contracts can do anything. See ADR-0019"
- Line 211: "access_contract_id: Field on every artifact pointing to its governing contract"
- Line 214: Null contract default documented
- Line 215: Dangling contract fallback documented
- No mention of ADR-0024 anywhere

### 6.2 Phantom `is_memory` field

**RESOLVED:** `is_memory` was already absent from GLOSSARY (never existed in code). No action needed.

Line 59: `is_memory: bool — Is a memory artifact`. **Does not exist** in the Artifact dataclass. Zero grep matches.

### 6.3 `tick` vs `event_number`

**RESOLVED:** GLOSSARY correctly defines both terms. `tick` = metrics observation window, `event_number` = per-action counter. CLAUDE.md says use `event_number` not `tick` for action sequencing, which is consistent.

- GLOSSARY line 15: Use `tick` not `turn`
- GLOSSARY line 297: Tick = metrics observation window
- CLAUDE.md root: Use `event_number` not `tick`

### 6.4 "owner" — different position than CM/CMF

**RESOLVED:** GLOSSARY has "Creator vs Owner" section clarifying the distinction. CM/CMF v3 explicitly ban the term. Positions are different but intentionally so — GLOSSARY explains why the term persists informally while CMF forbids it technically.

- GLOSSARY: Informal shorthand, "not a kernel concept"
- CM/CMF: "TERM DOES NOT EXIST. Do not use."

---

## 7. Architecture Doc Issues

> **Mixed resolution status.** §7.2 fixed by Plan #239. Remaining items are target-architecture issues deferred to dedicated plans.

### 7.1 Ontology quadrant not in conceptual models

**Deferred** — Target architecture taxonomy. Reconciliation deferred until ADR-0024 migration (Plan #234).

`docs/architecture/target/agents/01_ontology.md` defines Agent/Tool/Account/Data quadrant. "Tool" and "Account" don't appear in CM/CMF labels.

### 7.2 Action count: "6" vs 11

**FIXED** (Plan #239) — `execution_model.md` updated to reflect 11 action types.

`execution_model.md` says "The Narrow Waist: 6 Action Types." Code `ActionType` has 11 values. GLOSSARY lists 11.

### 7.3 `{tick}` used in target agent context variables

**Deferred** — Target architecture doc. Will be addressed when target agent docs are updated.

`docs/architecture/target/agents/02_execution.md` uses `{tick}` as an agent context variable, contradicting its definition as "metrics window."

### 7.4 "Agents never die" vs STOPPED state

**Deferred** — Target architecture aspiration vs current reality. Gap already documented in architecture gap analysis.

Target: "never die." Current: STOPPED is a valid state. Not called out as a gap.

### 7.5 Agent content schema: no canonical definition

**Deferred** — Needs dedicated plan for canonical agent content schema.

Described differently in `agents.md`, `01_ontology.md`, and CMF.

### 7.6 Workflow transitions: static vs dynamic

**Deferred** — Plan #222 tracks this gap.

Target doc says static-only (Plan #222 needed). Current doc says LLM transitions work (85% mature).

### 7.7 Memory system described three ways

**Deferred** — Needs dedicated plan for memory system documentation reconciliation.

Current docs disagree between themselves. Target drops Mem0.

---

## 8. Design Debt

> **Mostly resolved.** §8.2 and §8.3 fixed. §8.1 acknowledged as low-priority tech debt.

### 8.1 `price` vs `policy["invoke_price"]`

**Deferred** — Works but fragile. Low priority; revisit during ADR-0024 migration if pricing model changes.

Three representations of one value: `write()` parameter, `WriteArtifactIntent.price`, `policy["invoke_price"]`. Works but fragile.

### 8.2 `can_execute` vs `has_loop` naming

**FIXED** (Plan #230) — Rename completed. Code now uses `has_loop`.

Plan #230 completed the rename. Code now uses `has_loop`.

### 8.3 Artifact `type` not enumerated

**FIXED** (Plan #235 Phase 0) — Type is now immutable after creation and validated against `ALLOWED_TYPES` registry.

`type` is `str` with no canonical list. Kernel branches on specific values but a typo silently bypasses type-specific behavior.

---

## 9. Recommendations

> **All actionable recommendations resolved.** §9.1-5 fixed by Plans #239 and #235. §9.6-7 resolved by CMF v3 and GLOSSARY updates. §9.8 deferred. §9.9-12 done.

### Immediate (before next simulation run)

1. **Fix `_execute_edit`** — **DONE** (Plan #239). Rewritten to call `ArtifactStore.edit_artifact()` with proper permission checking.

2. **Fix `kernel_queries.py:472`** — **DONE** (Plan #239). Changed to `artifact.depends_on`.

### Soon (Plan #235 Phase 0)

3. **Make `type` immutable after creation** — **DONE** (Plan #235 Phase 0).

4. **Restrict `access_contract_id` to creator-only** — **DONE** (Plan #235 Phase 0).

5. **Add type validation** — **DONE** (Plan #235 Phase 0). `ALLOWED_TYPES` registry added.

### Documentation reconciliation

6. **Reconcile CMF with CM** — **DONE** (CMF v3 rewrite). Both are version 3, code as source of truth, Part 1/Part 2 separation.

7. **Update GLOSSARY for ADR-0024** — **DONE** (GLOSSARY updated with 12 fixes). GLOSSARY describes ADR-0019 (current); ADR-0024 is target, documented in CMF v3 Part 2.

8. **Reconcile ontology taxonomies** — **Deferred**. Target architecture taxonomy, revisit during ADR-0024 migration.

9. **Fix action count in `execution_model.md`** — **DONE** (Plan #239). Updated to 11 action types.

### Principles to record

10. **Kernel-meaningful fields must be system-controlled** — **DONE**. Recorded in `SECURITY.md` "Kernel-Level Security Invariants" section and `DESIGN_CLARIFICATIONS.md` §9.

11. **One source of truth per concept** — **DONE**. CMF v3 canonical for artifact fields. GLOSSARY canonical for terminology. Code canonical for both.

12. **CURRENT and TARGET must be visually distinct** — **DONE**. CMF v3 uses clear Part 1 (current) / Part 2 (target) banners.

---

## 10. External Review Notes

An external review (ChatGPT, 2026-01-31) identified several of these issues independently. Verification:

| Claim | Verdict | Notes |
|-------|---------|-------|
| `update()` bug is a hard crash | **Correct, understated** | Whole `_execute_edit` method is broken |
| `access_contract_id` hijack | **Correct** | Requires write permission first |
| `depends_on` split-brain | **Correct** | `kernel_queries.py:472` queries wrong source |
| `type` unvalidated | **Correct** | Mutable + no registry |
| `has_loop` as scheduling concept | **Partially correct** | Doesn't match code architecture |
| Need CURRENT SPEC file | **Correct diagnosis** | Existing infra needs maintenance, not replacement |
| Narrow waist != 6 actions | **Correct** | Code has 11 values |

**What the external review missed:** CMF stale open_questions, _execute_edit wrong intent fields, phantom `is_memory`, ontology taxonomy conflict, three memory descriptions, no canonical agent content schema.

---

## References

- **Source:** `src/world/artifacts.py`, `src/world/action_executor.py`, `src/world/kernel_queries.py`
- **Docs:** CONCEPTUAL_MODEL.yaml, CONCEPTUAL_MODEL_FULL.yaml, GLOSSARY.md, DESIGN_CLARIFICATIONS.md
- **Architecture:** `docs/architecture/current/{agents,agent_cognition,execution_model,genesis_agents}.md`, `docs/architecture/target/{03_agents,agents/01_ontology,agents/02_execution,agents/04_memory}.md`
- **ADRs:** 0001, 0010, 0013, 0016, 0019, 0024
- **Plans:** #131, #230, #234, #235, #236
