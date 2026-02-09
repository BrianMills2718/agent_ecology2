# Agent Ecology - Claude Code Context

## Philosophy & Goals

**What this is:** An experiment in emergent collective capability for LLM agents under real resource constraints.

**Core thesis:** Give agents scarcity (compute, disk, API budget), sound coordination primitives (contracts, escrow, ledger), and observe what emerges.

**Key principles:**
- **Physics-first** - Scarcity drives behavior; social structure emerges
- **Emergence over prescription** - No predefined roles; agents build what they need
- **Observability over control** - Make behavior observable, not "correct"
- **Accept risk, observe outcomes** - Learn from what happens

### Architecture Decision Heuristics

1. **Emergence is the goal** - Ask "what does this incentivize?"
2. **Minimal kernel, maximum flexibility** - Kernel provides primitives, not policy
3. **Align incentives** - Bad incentives = bad emergence
4. **Pragmatism over purity** - Don't let elegance obstruct goals
5. **Avoid defaults** - Prefer explicit choice; make defaults configurable
6. **Genesis as cold-start conveniences** - Genesis artifacts are unprivileged conveniences, not kernel features
7. **Selection pressure over protection** - Let agents fail and learn
8. **Observe, don't prevent** - Reputation emerges from observation
9. **When in doubt, contract decides** - Contracts are flexible; kernel isn't

---

## Design Principles

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

---

## Workflow

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

---

## Core Systems

See `docs/architecture/current/CORE_SYSTEMS.md` for full details.

| System | Purpose | Key Files |
|--------|---------|-----------|
| Resource Scarcity | LLM budgets, rate limits | `ledger.py`, `runner.py` |
| Economic Layer | Scrip currency, transfers | `ledger.py`, `mint_*.py` |
| Artifact System | Code/data storage, execution | `artifacts.py`, `executor.py` |
| Contract System | Access control | `contracts.py` |
| Agent Lifecycle | Loading, thinking, workflows | `agent.py`, `workflow.py` |
| Execution Model | Autonomous loops | `runner.py`, `agent_loop.py` |
| Kernel Interface | Artifact ↔ world boundary | `kernel_interface.py` |
| Event Logging | Observability | `logger.py` |

**Important:** All systems should **fail loud** - no silent fallbacks that hide bugs.

---

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  config/
    config.yaml             # Runtime values (Pydantic validated via src/config_schema.py)
  src/
    config.py               # Config helpers
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/
    plans/                  # Implementation plans
    adr/                    # Architecture Decision Records
    architecture/           # current/ (what IS) and target/ (what we WANT)
  scripts/                  # Utility scripts for CI and development
  hooks/                    # Git hooks (pre-commit, commit-msg)
```

---

## Documentation

See `docs/CLAUDE.md` for the full documentation index. Doc-code coupling is enforced by `make check`.

Script reference: see `scripts/CLAUDE.md`.
