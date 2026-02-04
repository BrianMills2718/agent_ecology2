# Context Provision Exploration Notes

**Goal:** Understand how context actually flows to Claude and where it breaks down.

**Date:** 2026-02-04

---

## Experiment 1: What context do I actually have right now?

Let me inventory what I know about this codebase just from auto-loaded context.

### What CLAUDE.md tells me:
- Philosophy: emergence, scarcity, physics-first
- Design principles: fail loud, strong typing, no mocks, etc.
- Commands: make worktree, make check, make finish, etc.
- Meta-process workflow: worktree → implement → verify → ship
- Key rules: always run from main, claims, plans
- Core systems TABLE (brief): lists systems + key files
- Project structure: directory tree

### What I DON'T know without looking up:
- What "scrip" actually IS (mentioned but undefined)
- What "artifact" actually IS (mentioned, has a table row, but no definition)
- What fields an Artifact has
- What "contract" does (mentioned as "access control" but no detail)
- What actions exist (read, write, invoke? no list)
- What the kernel interface methods are
- What terms are FORBIDDEN (non_existence in conceptual model)
- What "principal" means (never mentioned in CLAUDE.md!)
- Difference between "created_by" and "owner"

### Key observation:
CLAUDE.md gives me PROCESS context (how to work) but NOT DOMAIN context (what things are).
The "Core Systems" table is just labels + file pointers, not explanations.

---

## Experiment 2: Terminology compliance

Can I use the wrong terms without being corrected?

### Test: Use "owner" instead of "created_by"
- **Result: NOTHING STOPPED ME**
- Added comment with "owner", "credits", "account" to artifacts.py
- No hook blocked, no warning shown
- Edit succeeded silently

### Observation: The code itself already uses "owner" extensively!
- artifacts.py lines 137, 142, 144, 152 all say "owner"
- CONCEPTUAL_MODEL.yaml line 199 says "owner_term: DOES NOT EXIST"
- Even src/world/CLAUDE.md uses "ownership" in the description
- **The prohibition is not enforced anywhere**

### Observation: CONCEPTUAL_MODEL.yaml is internally inconsistent
- Line 199: owner_term "DOES NOT EXIST"
- Lines 141-143: "owner-only write", "owner-only everything"
- Uses the forbidden term in its own definitions!

---

## Experiment 3: Hook injection

What does the governance hook actually inject?

### Test: Read a governed file (ledger.py)
- **Hook DOES inject context** - appears as `<system-reminder>` after file content
- Shows: "Governed by ADR-0001, ADR-0002"
- Shows: "Related docs (update required): resources.md"
- Shows: "Related docs (advisory): GLOSSARY.md, CONCEPTUAL_MODEL.yaml, CORE_SYSTEMS.md"
- Shows: Governance context snippet

### Problems with the hook:
1. **Only triggers on Read, not Edit** - I can edit without reading first
2. **Tells me ABOUT docs but doesn't SHOW content** - I still have to manually look them up
3. **Doesn't surface forbidden terms** - non_existence from CONCEPTUAL_MODEL not shown
4. **Advisory only** - Nothing stops me from ignoring
5. **Appears AFTER the file content** - Easy to miss in long files

### What would be better?
- Inject non_existence terms as warnings BEFORE edit
- Actually inline critical context, not just references
- Block edit if doc hasn't been read recently?

---

## Experiment 4: Missing context scenarios

Simulate scenarios where I lack necessary context.

### Test: Modify ledger.py to allow negative balances
- **NOTHING STOPPED ME**
- Made edit that directly violates ADR-0002 ("No compute debt")
- Made edit that violates governance context ("Never allow negative balances")
- No hook blocked the edit
- No warning was shown

### Key finding: Governance hook only triggers on Read, not Edit
- Reading from MAIN triggers the hook
- Reading from WORKTREE does NOT trigger the hook (bug?)
- Editing never triggers governance context
- I can make violating edits without ever seeing the governance rules

### Test: Edit artifacts.py without understanding conceptual model
- Earlier edit succeeded with "owner", "credits", "account"
- All three are wrong per GLOSSARY/CONCEPTUAL_MODEL
- No enforcement whatsoever

### Test: Would CI catch the violation?
- `check_doc_coupling.py --staged --strict` → **PASSES** (no output)
- `check_doc_coupling.py --suggest-all src/world/ledger.py` → Shows related ADRs and docs
- **But doc-coupling only checks IF docs need updating, not IF code violates principles**
- ADR-0002 says "No compute debt" but nothing checks if code allows debt

---

## Findings

### What Works
1. **Governance headers in files** - ADR references embedded in source
2. **Governance hook on Read (from main)** - Shows related docs after reading
3. **Doc-coupling enforcement** - CI fails if docs not updated with code
4. **Tooling knows relationships** - `--suggest-all` shows full graph

### What Doesn't Work
1. **Terminology enforcement** - CONCEPTUAL_MODEL says "owner" doesn't exist, but:
   - Code uses "owner" extensively
   - CLAUDE.md uses "ownership"
   - Nothing stops me from using wrong terms

2. **Governance hook gaps**:
   - Only triggers on Read, not Edit
   - Only works from main, NOT from worktrees (bug?)
   - Shows doc references but not actual content
   - Doesn't surface non_existence terms

3. **Architectural principle enforcement**:
   - ADR-0002 says "No compute debt"
   - Governance context says "Never allow negative balances"
   - **Nothing stops me from coding violations**
   - Doc-coupling checks doc updates, not code correctness

4. **Context provision is purely advisory**:
   - CLAUDE.md tells me docs exist but doesn't make me read them
   - Hook tells me about related docs but doesn't show content
   - I can make bad edits without ever seeing the rules

### The Core Problem

**There's a gap between "context exists" and "context is used":**

| What exists | What's enforced |
|-------------|-----------------|
| CONCEPTUAL_MODEL with non_existence | Nothing |
| GLOSSARY with correct terms | Nothing |
| ADRs with principles | Only doc-coupling (not code correctness) |
| Governance headers | Only tells me, doesn't stop violations |

### Possible Improvements

1. **PreToolUse hook on Edit** that:
   - Shows non_existence terms as warnings
   - Requires acknowledgment before editing governed files
   - Injects critical context BEFORE edit, not after read

2. **Terminology linter** that:
   - Scans for forbidden terms (owner, credits, account)
   - Runs in pre-commit
   - Fails CI on violations

3. **ADR principle checker** (harder):
   - Parse ADR principles
   - Check if code changes violate them
   - Likely needs AI/LLM to evaluate

4. **Fix worktree hook bug**:
   - Governance hook should work from worktrees too
   - Currently only triggers on main
   - **Root cause found:** The sed pattern for stripping worktree prefix fails on relative paths
   - Pattern: `sed 's|.*/[^/]*worktrees/[^/]*/||'`
   - Works: `/home/.../worktrees/X/src/...` → `src/...`
   - Fails: `worktrees/X/src/...` → unchanged (no match)
   - Fix: Add case for relative paths starting with `worktrees/`

---

## Experiment 5: Realistic scenario - "Add a new resource type"

**Task:** Add a new resource type called "memory_bytes"

### What context do I NEED to know?
1. What types of resources exist? (depletable, allocatable, renewable)
2. How do I add a new one? (config? code? both?)
3. What's the naming convention?
4. What docs need updating?

### What context do I GET automatically?
From CLAUDE.md:
- "Resources" mentioned in Core Systems table → points to ledger.py, runner.py
- No explanation of resource types

From reading ledger.py:
- Governance hook (IF it worked from worktree) says: "see resources.md, GLOSSARY.md"
- Docstring mentions "renewable" and "stock" resources
- No list of valid resource types

### What I'd have to do manually:
1. Search for "resource" in codebase
2. Read resources.md (but I have to know it exists)
3. Read GLOSSARY.md section on resources (have to find it in 494 lines)
4. Read config_schema.py to understand validation
5. Check CONCEPTUAL_MODEL.yaml resources section

### Friction points:
- **Discovery:** How do I know resources.md exists? (governance hook, IF it worked)
- **Navigation:** GLOSSARY is huge - where's the resource section?
- **Completeness:** Did I read everything I need? No checklist.

### What would actually help:

**Option A: Smarter context injection**
When I READ a file like ledger.py or resources.py, inject:
```
RESOURCES CONTEXT:
- Types: depletable (llm_budget), allocatable (disk), renewable (rate-limited)
- Config: Add to config/config.yaml under resources section
- Docs to update: resources.md, GLOSSARY.md if new term
- FORBIDDEN: Don't allow negative balances (ADR-0002)
```

**Option B: Task-specific context files**
`docs/howto/add_resource_type.md` with step-by-step + relevant rules

**Option C: Interactive exploration**
`python scripts/explain.py resources` → dumps all relevant context

---

## Summary: The Ontology Problem

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ CLAUDE.md (auto-loaded)                                         │
│   - Process context (how to work)                               │
│   - Core Systems table (labels only, no definitions)            │
│   - References to docs/CLAUDE.md                                │
└─────────────────────────────────────────────────────────────────┘
         │
         │ "see docs/CLAUDE.md for more"
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ docs/CLAUDE.md (must manually read)                             │
│   - Document Hierarchy diagram                                  │
│   - Key Files table                                            │
│   - References to GLOSSARY, CONCEPTUAL_MODEL, etc.             │
└─────────────────────────────────────────────────────────────────┘
         │
         │ "see GLOSSARY.md, CONCEPTUAL_MODEL.yaml"
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Reference Docs (must manually read, large)                      │
│   - GLOSSARY.md (494 lines)                                    │
│   - CONCEPTUAL_MODEL.yaml (215 lines)                          │
│   - architecture/target/* (aspirational)                       │
└─────────────────────────────────────────────────────────────────┘
```

**Problem:** Each layer just POINTS to the next. Nothing actually PROVIDES the content.

### What Gets Enforced

| Mechanism | What it enforces |
|-----------|------------------|
| protect-main.sh | Can't edit in main directory |
| doc-coupling | Docs must update when code changes |
| governance headers | ADR references embedded in code |
| mypy | Type correctness |
| pytest | Behavior correctness |

**NOT enforced:**
- Terminology (owner, credits, etc.)
- Architectural principles (no debt, fail loud)
- Conceptual model (non_existence terms)
- Reading docs before editing

### The Gap

**"Context exists" ≠ "Context is used"**

We have excellent documentation:
- CONCEPTUAL_MODEL defines what entities ARE
- GLOSSARY defines correct terminology
- ADRs document decisions
- Architecture docs explain systems

But the DELIVERY mechanism is broken:
- Prompting in CLAUDE.md doesn't ensure compliance
- Hook shows doc REFERENCES, not content
- Nothing surfaces CRITICAL info (forbidden terms, principles)
- Nothing blocks bad edits

### Design Questions

1. **What level of enforcement do we want?**
   - Advisory (show context, hope Claude reads it)
   - Blocking (require acknowledgment before editing governed files)
   - Validating (check edits against rules, fail on violations)

2. **What context is CRITICAL vs nice-to-have?**
   - Critical: non_existence terms, ADR principles
   - Nice: related docs, reading suggestions

3. **How much friction is acceptable?**
   - Every edit shows 500 lines of context? Too much.
   - No context ever? Too little.
   - Smart injection of RELEVANT subset? Ideal but hard.

4. **Who curates the "relevant subset"?**
   - Manual: high quality but maintenance burden
   - Automatic: may miss nuance
   - Hybrid: templates + auto-population

---

## Next Steps (Proposed)

1. **Fix the worktree hook bug** - Low effort, immediate improvement

2. **Add PreToolUse hook for Edit** - Show critical context BEFORE editing:
   - non_existence terms for touched files
   - ADR principles that govern this code
   - Maybe require "I understand" acknowledgment?

3. **Create domain context files** - Per-subsystem context:
   - `docs/context/resources.md` - Everything about resources in one place
   - `docs/context/artifacts.md` - Everything about artifacts
   - Curated, focused, maintained

4. **Terminology linter** - Pre-commit check for forbidden terms

5. **Rethink the hook output** - Instead of "see GLOSSARY.md", inject:
   - The SPECIFIC glossary entries relevant to this file
   - The SPECIFIC ADR principles that apply

---

## Implementation: extract_relevant_context.py + inject-edit-context.sh

Built a working prototype that:

### 1. Extracts terms from the file being edited
- Uses AST to get class names, function names, identifiers
- Extracts string literals that might be domain terms
- Matches against GLOSSARY entries, CONCEPTUAL_MODEL sections

### 2. Surfaces warnings for deprecated/forbidden terms
```
⚠️  WARNINGS:
   DEPRECATED TERM 'credits': Use 'scrip' instead. Consistency
   FORBIDDEN TERM 'owner': DOES NOT EXIST — use 'created_by' for creator
```

### 3. Injects relevant context BEFORE the edit
- ADR principles that govern this file
- Governance context from relationships.yaml
- Key glossary terms extracted from the file
- Conceptual model sections (resources, etc.)
- Docs to check after editing

### Example output for editing ledger.py:
```
📋 ADR PRINCIPLES (must follow):
   [ADR-0002] **Scrip cannot go negative** - Debt implemented via contract artifacts, not negative balances
   [ADR-0002] **Compute cannot go negative** - Blocked until rolling window allows more

📌 GOVERNANCE CONTEXT:
   All balance mutations go through here.
   Never allow negative balances - fail loud.

📖 KEY TERMS:
   • Scrip: Internal economic currency
   • Principal: Any artifact with standing (can hold resources, bear costs)
   • depletable/allocatable/renewable resource types

📄 DOCS TO CHECK AFTER EDITING:
   • docs/architecture/current/resources.md
   • docs/GLOSSARY.md
```

### Files created:
- `scripts/extract_relevant_context.py` - Main extraction logic
- `.claude/hooks/inject-edit-context.sh` - PreToolUse hook for Edit
- `.claude/settings.json` - Updated to register the hook

### What this achieves:
| Before | After |
|--------|-------|
| Context shown after Read | Context shown BEFORE Edit |
| Shows doc references | Shows actual content |
| No term warnings | Warns on deprecated/forbidden terms |
| ADR principles hidden | ADR principles surfaced |

---
