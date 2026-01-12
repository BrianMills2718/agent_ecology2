# Meta Patterns

Reusable development process patterns. Each pattern solves a specific coordination or quality problem when working with AI coding assistants (Claude Code, etc.).

## Pattern Index

| Pattern | Problem Solved | Complexity |
|---------|----------------|------------|
| [CLAUDE.md Authoring](claude-md-authoring.md) | AI assistants lack project context | Low |
| [ADR](adr.md) | Architectural decisions get lost | Medium |
| [Documentation Graph](documentation-graph.md) | Can't trace decisions → code | Medium |
| [Mock Enforcement](mock-enforcement.md) | Green CI, broken production | Low |
| [PR Coordination](pr-coordination.md) | Lost review requests | Low |
| [Git Hooks](git-hooks.md) | CI failures caught late | Low |
| [Plan Workflow](plan-workflow.md) | Untracked work, scope creep | Medium |
| [Claim System](claim-system.md) | Parallel work conflicts | Medium |
| [Verification Enforcement](verification-enforcement.md) | Untested "complete" work | Medium |
| [Worktree Enforcement](worktree-enforcement.md) | Main directory corruption from parallel edits | Low |

### Subsumed Patterns

These patterns are now implementation details of [Documentation Graph](documentation-graph.md):

| Pattern | Status |
|---------|--------|
| [ADR Governance](adr-governance.md) | `governs` edges in relationships.yaml |
| [Doc-Code Coupling](doc-code-coupling.md) | `documented_by` edges in relationships.yaml |

## When to Use

**Start with these (low overhead):**
- CLAUDE.md Authoring - any project using AI coding assistants
- Mock Enforcement - if using pytest with mocks
- Git Hooks - any project with CI
- PR Coordination - if multiple people/instances work in parallel
- Worktree Enforcement - if multiple Claude Code instances share a repo

**Add these when needed (more setup):**
- ADR - when architectural decisions need to be preserved long-term
- Documentation Graph - when you need to trace ADR → target → current → code
- Plan Workflow - for larger features with multiple steps
- Claim System - for explicit parallel work coordination
- Verification Enforcement - when plans need proof of completion

## Pattern Template

When adding new patterns, follow this structure:

```markdown
# Pattern: [Name]

## Problem
What goes wrong without this?

## Solution
How does this pattern solve it?

## Files
| File | Purpose |
|------|---------|
| ... | ... |

## Setup
Steps to add to a new project.

## Usage
Day-to-day commands.

## Customization
What to change for different projects.

## Limitations
What this pattern doesn't solve.
```

## Archive

Deprecated patterns are in `archive/`:
- `handoff-protocol.md` - Superseded by automatic context compaction

## Origin

These patterns emerged from the [agent_ecology](https://github.com/BrianMills2718/agent_ecology2) project while coordinating multiple Claude Code instances on a shared codebase.
