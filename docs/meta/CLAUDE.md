# Meta Patterns Directory

Reusable development process patterns for AI-assisted development.

## Purpose

These patterns solve coordination and quality problems when working with AI coding assistants (Claude Code). They emerged from this project and are designed to be portable to other projects.

## File Structure

Files are numbered for reading order:

| Range | Category |
|-------|----------|
| 01-02 | Overview, CLAUDE.md authoring |
| 03-06 | Testing and hooks |
| 07-12 | Documentation patterns |
| 13-17 | Feature and plan workflows |
| 18-26 | Coordination patterns |

## Pattern Status

Most patterns are **deployed** and actively used. A few are **proposed** (documented but not yet implemented):

| Pattern | Status | Notes |
|---------|--------|-------|
| 09_documentation-graph.md | Proposed | Unified graph concept; 08 + 10 are deployed instead |
| 12_structured-logging.md | Proposed | DualLogger concept; standard Python logging used |
| 21_pr-coordination.md | Partial | Full GitHub Actions workflow not deployed; simplified `gh pr list` approach used |

All other patterns (01-08, 10-11, 13-20, 22-26) are **deployed**.

## Key Patterns

| Pattern | When to Use | Status |
|---------|-------------|--------|
| `02_claude-md-authoring.md` | Any AI-assisted project | Deployed |
| `15_plan-workflow.md` | Multi-step implementations | Deployed |
| `18_claim-system.md` | Parallel AI instances | Deployed |
| `19_worktree-enforcement.md` | Multiple CC in same repo | Deployed |
| `26_ownership-respect.md` | Prevent CC interference | Deployed |

## Build Script

```bash
./build_meta_review_package.sh  # Concatenates all patterns
```

Output: `META_REVIEW_PACKAGE.md` (gitignored, regeneratable)

## Adding New Patterns

1. Create `NN_pattern-name.md` (next number in sequence)
2. Follow template in `01_README.md`
3. Update `01_README.md` pattern index
4. Update `build_meta_review_package.sh`
5. Regenerate the review package
