# Pattern: Project Terminology

## Why Terminology Matters

Inconsistent terminology causes:
- Miscommunication between team members
- Documentation that contradicts itself
- Confusion about what's being tracked

This document defines the canonical terms for project organization.

## Core Hierarchy

```
Phase (optional grouping)
└── Feature (the deliverable)
    └── Plan (the implementation document)
        └── Task (atomic work item)
```

### Definitions

| Term | Definition | Identifier | Tests At Level |
|------|------------|------------|----------------|
| **Feature** | A user-visible or system capability that can be verified E2E | Plan number (1:1 with plan) | E2E required |
| **Plan** | Document describing how to implement a feature | `NN_name.md` | References tests |
| **Task** | Atomic work item within a plan | Checklist item | May have unit test |
| **Phase** | Optional grouping of related features | "Phase 1" | No tests (just grouping) |

### Key Insight: Feature = Plan

In this system, each plan implements exactly one feature. The plan number IS the feature ID.

```
Feature: "Rate Limiting"
    └── Plan: 01_rate_allocation.md
        └── Tasks:
            - Create TokenBucket class
            - Update config schema
            - Add tests
```

## Plan Types

Not all plans are features. Distinguish between:

| Type | Definition | E2E Required? | Examples |
|------|------------|---------------|----------|
| **Feature Plan** | Delivers testable capability | Yes | Rate limiting, Escrow, MCP servers |
| **Enabler Plan** | Improves dev process | No | Dev tooling, ADR governance |
| **Refactor Plan** | Changes internals, not behavior | Existing E2E must pass | Terminology cleanup |

Mark in plan header:
```markdown
**Type:** Feature  # or Enabler, Refactor
```

## Status Terms

| Status | Emoji | Meaning |
|--------|-------|---------|
| **Planned** | 📋 | Has implementation design, ready to start |
| **In Progress** | 🚧 | Actively being implemented |
| **Blocked** | ⏸️ | Waiting on dependency |
| **Needs Plan** | ❌ | Gap identified, needs design work |
| **Complete** | ✅ | Implemented, tested, documented |

## Resource Terms

See `docs/GLOSSARY.md` for canonical resource terminology:

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency with economics literature |
| `principal` | `account` | Principals include artifacts, not just agents |
| `tick` | `turn` | Game theory convention |
| `artifact` | `object/entity` | Everything is an artifact |

## Test Organization Terms

| Term | Definition |
|------|------------|
| **Unit test** | Tests single component in isolation |
| **Integration test** | Tests multiple components together |
| **E2E test** | Tests full system end-to-end |
| **Smoke test** | Basic E2E that verifies system runs |
| **Plan test** | Test(s) required for a specific plan |

## Enforcement

Terminology is enforced through:

1. **Code review** - Reviewers flag incorrect terms
2. **Glossary reference** - `docs/GLOSSARY.md` is authoritative
3. **Search and replace** - Periodic terminology audits
4. **CI (future)** - Could add terminology linting

## Usage Examples

### Correct

> "Plan #6 (Unified Ontology) is a feature plan that delivers artifact-backed agents."

> "Task: Create the TokenBucket class (part of Plan #1)"

> "Phase 1 includes Plans #1, #2, and #3"

### Incorrect

> "Feature #6 is blocked" (use "Plan #6")

> "The rate limiting task needs E2E tests" (tasks don't have E2E; plans do)

> "The credits system" (use "scrip")

## Origin

Defined to resolve confusion between "feature", "plan", "gap", and "task" during coordination.
