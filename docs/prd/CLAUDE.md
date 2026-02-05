# Product Requirements Documents (PRDs)

PRDs define **capabilities** - what the system must be able to do to achieve the thesis.

## Purpose

PRDs sit between the Thesis and Domain Models in the document hierarchy:

```
Thesis (why we exist)
    ↓
PRD (what capabilities enable the thesis)  ← You are here
    ↓
Domain Model (what concepts enable capabilities)
    ↓
ADR (how to implement concepts)
    ↓
Ontology (precise entity definitions)
    ↓
Code
```

## PRD Structure

Each PRD follows this structure:

```markdown
# PRD: {Domain} Capabilities

**Status:** Draft | Review | Accepted
**Thesis Refs:** [emergence, scarcity-drives-behavior, ...]

## Overview
What this domain is and why it matters.

## Capabilities

### capability-id-1
**Description:** What must be possible
**Why:** How this enables thesis goals
**Acceptance:** How we know it works

### capability-id-2
...

## Non-Goals
What this domain explicitly does NOT cover.

## Open Questions
Unresolved design questions.
```

## Current PRDs

| PRD | Domain | Status |
|-----|--------|--------|
| `agents.md` | Agent capabilities | Draft |
| (more to come) | | |

## Creating a New PRD

1. Copy the template from `TEMPLATE.md`
2. Fill in capabilities that enable thesis goals
3. Link to thesis using `thesis_refs` in frontmatter
4. Get review before accepting

## Linking

- PRDs reference thesis goals
- Domain models reference PRD capabilities
- Files in `scripts/relationships.yaml` link to PRD capabilities
