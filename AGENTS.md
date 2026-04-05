# Agent Ecology - Claude Code Context

<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- generated_by: scripts/meta/render_agents_md.py -->
<!-- canonical_claude: CLAUDE.md -->
<!-- canonical_relationships: scripts/relationships.yaml -->
<!-- canonical_relationships_sha256: 771f83f0ce82 -->
<!-- sync_check: python scripts/meta/check_agents_sync.py --check -->

This file is a generated Codex-oriented projection of repo governance.
Edit the canonical sources instead of editing this file directly.

Canonical governance sources:
- `CLAUDE.md` — human-readable project rules, workflow, and references
- `scripts/relationships.yaml` — machine-readable ADR, coupling, and required-reading graph

## Purpose

Agent Ecology - Claude Code Context uses `CLAUDE.md` as canonical repo governance and workflow policy.

## Commands

```bash
make check              # Run tests + type check + lint
make test               # Run tests
make status             # Git status
make cost               # Show LLM spend (DAYS=7)
make errors             # Show recent error breakdown

# Worktree workflow (branch protection requires PRs)
make worktree BRANCH=name TASK="..." PLAN=N
make session-start BRANCH=name
```

## Operating Rules

This projection keeps the highest-signal rules in always-on Codex context.
For full project structure, detailed terminology, and any rule omitted here,
read `CLAUDE.md` directly.

### Principles

1. **Fail Loud** - No silent fallbacks, no `except: pass`
2. **Maximum Observability** - Log all state changes with context
3. **Maximum Configurability** - All values from `config/config.yaml`
4. **Strong Typing** - `mypy --strict`, Pydantic models
5. **Real Tests, Not Mocks** - Use `# mock-ok: <reason>` if mock needed
6. **Prefer Libraries** - Ask before hand-rolling algorithms
7. **Simplest thing that works** - Every solution should be the simplest that solves the problem

### Hard Rules - Stop and Ask If Tempted

Before writing code, check if you're about to:

- **Hack** - Workaround instead of fixing the root cause
- **Overengineer** - Add abstraction, config, or flexibility "for later"
- **Add fallbacks** - Handle cases that won't happen
- **Support legacy** - Keep old code paths "just in case"
- **Leave dead code** - Commented out, unused, or orphaned code
- **Create complexity** - Giant files, deep folder nesting, abstract inheritance

If yes → **stop and ask** before proceeding.

### Working Style

- Brainstorm first, finalize the approach together.
- Recommend the simplest solution. Present multiple approaches when they exist.
- Raise concerns early. Ask rather than assume.
- **Delete > Comment.** Remove unused code, don't comment it out.
- **Flat > Nested.** Prefer flat structures over deep hierarchies.

### Hook-Injected Context (IMPORTANT)

Hooks inject governance context, constraint checks, and quizzes as system-reminders after reading or editing src/ files. These serve two purposes: (1) giving you the right context before making changes, and (2) keeping the user informed.

**SHOW_USER rule:** When a system-reminder contains `[SHOW_USER]...[/SHOW_USER]` tags, you **MUST** display that content to the user before proceeding. Do not silently absorb it. This is how the meta-process surfaces constraints and quiz questions to the human in the loop.

Specifically:
1. **After editing a src/ file:** A post-edit quiz appears. Show the quiz questions to the user and answer each one explicitly.
2. **Before editing a src/ file:** Constraint checks appear. State how your edit respects each constraint. If a constraint is irrelevant, say so.
3. **After reading a governed file:** Governance context appears. Mention relevant ADRs and constraints when they affect your planned changes.

Visibility is configurable via `meta-process.yaml` → `visibility` section. When set to `on-demand`, tags are omitted but you still see and use the context.

### User Review and Quiz (On-Demand)

The user may ask to review context or be quizzed at any time:
- **"Show me the context for [file]"** → Run `python scripts/get_governance_context.py [file]` and `python scripts/file_context.py [file]`, display results.
- **"Quiz me on [area]"** → Run `python scripts/generate_quiz.py [file]`, display the questions to the user and let them answer.

### Workflow

### Commit Messages

```bash
[Plan #N] Description       # Links to plan (required for significant work)
[Trivial] Fix typo          # For tiny changes (<20 lines, no src/ changes)
```

### Make Commands

```bash
make status              # Git status
make test                # Run pytest
make check               # All CI checks (test + mypy + doc-coupling)
make pr-ready            # Rebase + push
make pr                  # Create PR (opens browser)
make finish BRANCH=X PR=N  # Merge PR + cleanup branch
make branches            # List stale remote branches
make branches-delete     # Delete stale remote branches (merged PRs)
make run                 # Run simulation (DURATION=60 AGENTS=2)
make clean               # Remove __pycache__, .pytest_cache, .mypy_cache
make worktree BRANCH=X   # Create worktree + claim for parallel CC isolation
make worktree-list       # List active worktrees
make worktree-remove BRANCH=X  # Safely remove worktree
```

### Parallel CC Instances (Worktree Isolation)

When running multiple Claude Code instances on this repo, each must use a worktree:

1. `make worktree BRANCH=plan-NN-description TASK="what you're doing"`
2. Edit files using absolute paths: `$(pwd)/worktrees/BRANCH/src/...`
3. Use `git -C worktrees/BRANCH` for git commands
4. Do NOT `cd` into the worktree
5. When done: `make finish BRANCH=X PR=N` (merges PR, releases claim, removes worktree)

### Plans

All significant work requires a plan in `docs/plans/NN_name.md`. Use `[Trivial]` only for: <20 lines, no `src/` changes, no new files.

### Pre-commit Hook Failures

When a pre-commit hook fails: STOP, explain what failed, ask user how to proceed. If user approves bypass: `git commit --no-verify -m "message"`. Do NOT bypass unilaterally.

## Machine-Readable Governance

`scripts/relationships.yaml` is the source of truth for machine-readable governance in this repo: ADR coupling, required-reading edges, and doc-code linkage. This generated file does not inline that graph; it records the canonical path and sync marker, then points operators and validators back to the source graph. Prefer deterministic validators over prompt-only memory when those scripts are available.

## References

- `CLAUDE.md` — This file (canonical operating guidance)
- `AGENTS.md` — Generated mirror for non-Claude agents
- `docs/CLAUDE.md` — Full documentation index
- `scripts/CLAUDE.md` — Script reference
- `scripts/relationships.yaml` — Doc-code coupling graph
