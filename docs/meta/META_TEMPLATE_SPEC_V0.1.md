# Claude Code Meta-Process Template v0.1

**Purpose**: Reusable coordination patterns for AI-assisted development with Claude Code.

**Scope**: Single or multi-instance, greenfield or existing codebases.

---

## Configuration Schema

```yaml
# .claude/template-config.yaml

# === PROJECT CONTEXT ===
project:
  state: existing | greenfield          # Existing codebase vs new project
  cc_instances: single | multi          # One Claude Code or parallel instances

# === ENFORCEMENT LEVELS ===
# Gradations: hook (hard block) > ci (blocks merge) > warning > honor
enforcement:
  preset: strict | balanced | lenient   # Quick selection

  # Granular overrides (optional)
  overrides:
    plan_required: ci              # Require plan for non-trivial work
    test_before_merge: ci          # Tests must pass
    doc_coupling: warning          # Docs should match code
    claim_required: hook           # Multi-CC: must claim work
    worktree_required: hook        # Multi-CC: no edits in main

# === PRESETS (what each level sets) ===
# strict:   All at 'ci' or 'hook' level, plus pre-commit hooks
# balanced: plan_required=ci, test=ci, doc_coupling=warning, claims=hook
# lenient:  plan_required=warning, test=ci, doc_coupling=honor, claims=warning

# === WORK ORGANIZATION ===
work:
  primary: plans                   # Plans are the work unit (not features)
  trivial_exemption: true          # Allow [Trivial] for small changes
  trivial_max_lines: 20            # Max lines for trivial
  trivial_excludes:                # Trivial can't touch these
    - "src/"
    - "config/"

# === DOCUMENTATION ===
documentation:
  coupling:
    enabled: true
    strictness: warning            # ci | warning | honor
    mappings_file: scripts/doc_coupling.yaml

  glossary:
    location: docs/GLOSSARY.md     # Single source of truth
    enforce_terms: true            # Warn on term violations

  architecture:
    current_dir: docs/architecture/current/   # What IS implemented
    target_dir: docs/architecture/target/     # Destination (not route)
    plans_dir: docs/plans/                    # Route to target

    # Target vs Plan distinction:
    # - target/: "I want escrow functionality" (WHAT)
    # - plans/: "Implement escrow in 3 phases" (HOW)

# === MULTI-CC COORDINATION (only if cc_instances: multi) ===
coordination:
  claims_file: .claude/active-work.yaml
  worktrees_dir: worktrees/
  hooks:
    - check_claims.py              # Verify work is claimed
    - check_worktree.py            # Block edits in main directory
```

---

## Directory Structure

### Minimal Core (All Projects)

```
project/
├── CLAUDE.md                      # Root: universal rules, philosophy
├── .claude/
│   ├── template-config.yaml       # Template configuration
│   └── settings.json              # Claude Code settings
├── docs/
│   ├── CLAUDE.md                  # Contextual: doc-specific rules
│   ├── GLOSSARY.md                # Single terminology source
│   └── plans/
│       ├── CLAUDE.md              # Plan template and workflow
│       └── NN_plan_name.md        # Individual plans
└── src/
    └── CLAUDE.md                  # Contextual: code conventions
```

### Extended (Mature Projects)

```
project/
├── ...core structure above...
├── docs/
│   ├── architecture/
│   │   ├── current/              # What IS implemented
│   │   └── target/               # Destination only (no HOW)
│   ├── adr/                      # Architecture Decision Records
│   └── meta/                     # Reusable process patterns
├── scripts/
│   ├── doc_coupling.yaml         # Doc-to-code mappings
│   ├── check_doc_coupling.py     # Coupling enforcement
│   └── governance.yaml           # ADR-to-file mappings
└── .github/
    └── workflows/
        └── ci.yml                # CI with enforcement checks
```

### Multi-CC Extended

```
project/
├── ...extended structure above...
├── .claude/
│   ├── active-work.yaml          # Current claims
│   └── hooks/
│       ├── pre-commit-check-claim.sh
│       └── pre-commit-check-worktree.sh
└── worktrees/                    # Isolated per-instance directories
    ├── plan-01-feature/
    └── plan-02-bugfix/
```

---

## Core Modules

### 1. CLAUDE.md Hierarchy (Required)

**Principle**: Contextual, compendious (minimize tokens while maximizing relevance)

| File | Contains | Loaded When |
|------|----------|-------------|
| `/CLAUDE.md` | Philosophy, universal rules, quick reference | Always |
| `/docs/CLAUDE.md` | Doc conventions, update protocols | In docs/ |
| `/src/CLAUDE.md` | Code style, testing rules, typing | In src/ |
| `/docs/plans/CLAUDE.md` | Plan template, workflow | Working on plans |

**Rules**:
- Root CLAUDE.md: Max 500 lines, links to details elsewhere
- Subdirectory CLAUDE.md: Max 200 lines, specific to that context
- Never duplicate content between hierarchy levels

### 2. Plans Workflow (Required)

**Why plans, not features**: Investigation found features.yaml never used in practice. All claims are plan-based.

```yaml
# docs/plans/NN_plan_name.md structure
---
status: "🚧 In Progress"  # or ✅ Complete, 📋 Planned
---

## Problem Statement
What problem does this solve?

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Plan
Step-by-step implementation route.

## Required Tests
- test_function_name: What it validates

## Verification Evidence
<!-- Filled by completion script -->
```

**Lifecycle**:
1. Create plan with acceptance criteria
2. Claim work (multi-CC)
3. Implement with TDD
4. Complete via script (validates tests, updates status atomically)

### 3. Trivial Exemption (Required)

**Purpose**: Reduce friction for small changes without abandoning traceability.

```bash
# Valid trivial commit
git commit -m "[Trivial] Fix typo in README"

# Criteria (ALL must be true):
# - Less than N lines changed (configurable, default 20)
# - No changes to excluded paths (src/, config/)
# - No new files created
# - No test logic changes (typo fixes ok)
```

CI validates trivial commits don't exceed configured limits.

### 4. Doc Coupling (Required, Configurable Strictness)

**Purpose**: Ensure documentation matches code.

```yaml
# scripts/doc_coupling.yaml
mappings:
  - source: src/world/ledger.py
    docs:
      - docs/architecture/current/resources.md
    type: strict     # CI fails if source changes without doc update

  - source: src/config_schema.py
    docs:
      - docs/architecture/current/configuration.md
    type: soft       # Warning only
```

**Future expansion**: Code graph coupling (function-level, not just file-level)

---

## Optional Modules

### 5. Multi-CC Coordination (If cc_instances: multi)

**Claims System**:
```yaml
# .claude/active-work.yaml
claims:
  - cc_id: plan-48-ci-optimization
    plan: 48
    task: "Optimize CI workflow"
    claimed_at: 2026-01-16T14:21:00
```

**Worktree Enforcement**:
```bash
# Pre-commit hook blocks edits in main directory
if [ "$PWD" = "$(git rev-parse --show-toplevel)" ]; then
  echo "ERROR: Cannot edit files in main. Use make worktree BRANCH=..."
  exit 1
fi
```

**Why This Matters**: Investigation found 20 dangling commits - duplicate work from multi-CC conflicts. Worktree enforcement prevents this.

### 6. ADR Governance (Mature Projects)

**Purpose**: Link architecture decisions to code that implements them.

```yaml
# scripts/governance.yaml
adr-0001-everything-artifact:
  files:
    - src/world/genesis.py
    - src/world/ledger.py
```

Files get headers showing which ADRs govern them. CI ensures sync.

### 7. Target Architecture (Mature Projects)

**Key Distinction**:
- `docs/architecture/target/`: DESTINATION ("I want escrow")
- `docs/plans/`: ROUTE ("Implement escrow via these 3 phases")

Target describes the end state without implementation details. Plans describe how to get there.

---

## Enforcement Presets

### Strict
```yaml
enforcement:
  preset: strict
  # Equivalent to:
  overrides:
    plan_required: hook      # Can't commit without plan reference
    test_before_merge: hook  # Pre-commit runs tests
    doc_coupling: ci         # Fails CI if docs outdated
    claim_required: hook     # Multi-CC: must claim first
    worktree_required: hook  # Multi-CC: no main edits
```

### Balanced (Recommended)
```yaml
enforcement:
  preset: balanced
  # Equivalent to:
  overrides:
    plan_required: ci        # CI checks plan reference
    test_before_merge: ci    # CI runs tests
    doc_coupling: warning    # Warns but doesn't block
    claim_required: hook     # Multi-CC: must claim first
    worktree_required: hook  # Multi-CC: no main edits
```

### Lenient
```yaml
enforcement:
  preset: lenient
  # Equivalent to:
  overrides:
    plan_required: warning   # Warns about missing plan
    test_before_merge: ci    # Still require tests
    doc_coupling: honor      # Trust developers
    claim_required: warning  # Multi-CC: warn if unclaimed
    worktree_required: honor # Multi-CC: trust developers
```

---

## Migration Guide

### From Nothing (Greenfield)
1. Create `CLAUDE.md` with philosophy and rules
2. Create `docs/plans/` with first plan
3. Add `.claude/template-config.yaml` with `lenient` preset
4. Increase enforcement as team grows

### From Existing Process
1. Audit current patterns (what's actually used vs aspirational)
2. Map existing docs to new structure
3. Start with `balanced` preset
4. Kill unused patterns (e.g., features.yaml if claims are plan-based)
5. Consolidate redundant docs (e.g., multiple glossaries)

### Adding Multi-CC
1. Add `coordination` section to config
2. Create `.claude/active-work.yaml`
3. Add pre-commit hooks for claims and worktrees
4. Document worktree workflow in CLAUDE.md

---

## Anti-Patterns (From Investigation)

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Features + Plans | Redundant, features never used | Kill features, use plans only |
| Two-tier docs (current/target) without graduation | Drift, never graduates | Clear distinction: target=destination, plans=route |
| Multiple glossaries | Inconsistency | Single GLOSSARY.md |
| Honor-system claims | Work overwrites | Hook-based enforcement |
| Editing in main directory | Conflicts, lost work | Mandatory worktrees for multi-CC |

---

## Checklist for New Projects

- [ ] Create root `CLAUDE.md` with philosophy
- [ ] Create `docs/plans/CLAUDE.md` with plan template
- [ ] Create `.claude/template-config.yaml`
- [ ] Set enforcement preset based on team/risk
- [ ] If multi-CC: Add claims and worktree hooks
- [ ] Create first plan before first code change
- [ ] Add doc coupling for critical files

---

## Version History

- **v0.1** (2026-01-16): Initial spec based on agent_ecology investigation
  - 23 patterns audited, 14 active, 5 partial, 3 aspirational
  - 20 dangling commits analyzed (duplicate work, not lost)
  - Simplified from features+plans to plans-only
  - Added enforcement presets
