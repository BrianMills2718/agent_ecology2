# Domain Models

Domain models define the **concepts** that enable PRD capabilities.

## Purpose

Domain models sit between PRDs and ADRs in the document hierarchy:

```
Thesis (why we exist)
    ↓
PRD (what capabilities enable the thesis)
    ↓
Domain Model (what concepts enable capabilities)  ← You are here
    ↓
ADR (how to implement concepts)
    ↓
Ontology (precise entity definitions)
    ↓
Code
```

## What's a Domain Model?

A domain model captures:
- **Concepts** - The key abstractions in a domain
- **Relationships** - How concepts relate to each other
- **Behaviors** - What concepts can do
- **Constraints** - Invariants that must hold

Domain models are **conceptual** - they describe the problem space, not the implementation.

## Domain Model vs Ontology

| Aspect | Domain Model | Ontology |
|--------|--------------|----------|
| Purpose | Explain concepts | Define precisely |
| Format | YAML + prose | Strict YAML |
| Audience | Humans (understanding) | Machines + humans |
| Level | Conceptual | Field-level |
| Example | "Agent pursues Goals" | `artifact.goal_hierarchy: list[Goal]` |

## Structure

Each domain model follows this structure:

```yaml
# domain_model/{domain}.yaml
---
id: domain_model/{domain}
type: domain_model
domain: {domain}
prd_refs:
  - prd/{domain}#capability-1
  - prd/{domain}#capability-2
---

concepts:
  ConceptName:
    description: "What this concept represents"
    enables: [capability-1, capability-2]  # Links to PRD capabilities
    relationships:
      - "has many X"
      - "belongs to Y"
    behaviors:
      - "can do Z"
    constraints:
      - "must always have W"

  AnotherConcept:
    ...
```

## Current Domain Models

| Model | Domain | Status |
|-------|--------|--------|
| `agents.yaml` | Agent cognitive architecture | Draft |
| `resources.yaml` | Resource scarcity concepts | Draft |
| `contracts.yaml` | Access control concepts | Draft |
| `artifacts.yaml` | Storage and execution concepts | Draft |

## Creating a New Domain Model

1. Start from a PRD - what capabilities need concepts?
2. Identify the key abstractions
3. Define relationships and behaviors
4. Link back to PRD capabilities via `enables`
5. Document constraints

## Linking

- Domain models reference PRD capabilities via `prd_refs`
- ADRs reference domain model concepts
- Ontology provides precise definitions of concepts
