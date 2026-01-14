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
| 18-23 | Coordination patterns |

## Key Patterns

| Pattern | When to Use |
|---------|-------------|
| `02_claude-md-authoring.md` | Any AI-assisted project |
| `15_plan-workflow.md` | Multi-step implementations |
| `18_claim-system.md` | Parallel AI instances |
| `19_worktree-enforcement.md` | Multiple CC in same repo |

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
