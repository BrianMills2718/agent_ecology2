# Agent Ecology - Claude Code Context

> **ALWAYS RUN FROM MAIN.** Your CWD should be `/home/brian/brian_projects/agent_ecology2/` (main).
> Use worktrees as **paths** for file isolation, not as working directories.
> **NEVER use `cd worktrees/...` as a separate command** - always chain with `&&` or use `git -C`.
> This lets you handle the full lifecycle: create worktree → edit → commit → merge → cleanup.

---

## Quick Reference - Make Commands

The Makefile has 15 targets. Use `make help` to see them all.

### Core Workflow
```bash
make status              # Git status + active claims
make worktree            # Create worktree with claim (ALWAYS use this to start work)
make test                # Run pytest
make check               # All CI checks (test + mypy + lint + doc-coupling)
make pr-ready            # Rebase + push
make pr                  # Create PR
make finish BRANCH=X PR=N  # Merge + cleanup + auto-complete (from main)
```

### Other
```bash
make worktree-remove BRANCH=X  # Safe removal (add FORCE=1 to skip checks)
make clean               # Remove __pycache__, .pytest_cache, .mypy_cache
make run                 # Run simulation (DURATION=60 AGENTS=2)
make dash                # View dashboard
make kill                # Stop simulation
```

### Non-interactive worktree creation (for CC sessions):
```bash
bash scripts/create_worktree.sh --branch plan-N-desc --plan N --task "description"
```

Claim and worktree cleanup runs automatically on session startup.

Script reference: see `scripts/CLAUDE.md`.

---

## Meta-Process Workflow

### The Complete Cycle (4 Steps)

```
1. START            -->  make worktree PLAN=N (claim + create isolated workspace)
       |
2. IMPLEMENT        -->  Edit files in worktrees/plan-N-xxx/src/... (paths from main)
       |
3. VERIFY           -->  make check (run from main)
       |
4. SHIP             -->  make pr-ready && make pr && make finish BRANCH=X PR=N
```

**Key insight:** You stay in main the whole time. Worktrees are paths for file isolation:
- Edit: `worktrees/plan-123-foo/src/world/ledger.py`
- Commit: `git -C worktrees/plan-123-foo commit -m "..."`
- When you run `make finish`, the worktree is deleted but your CWD (main) stays valid.

### Per-Worktree Context File

Each worktree has a `.claude/CONTEXT.md` file for tracking progress:

```
worktrees/plan-123-foo/.claude/CONTEXT.md
```

**Update this file as you work.** It helps:
- Resume after context compaction
- Document decisions made
- Track which files were changed
- Hand off to another session if needed

The file is ephemeral - deleted when the worktree is removed after merge.

Example workflow:
```bash
make worktree PLAN=123                    # Creates worktrees/plan-123-foo/
# Edit files using paths: worktrees/plan-123-foo/src/...
git -C worktrees/plan-123-foo add -A && git -C worktrees/plan-123-foo commit -m "[Plan #123] ..."
make pr-ready BRANCH=plan-123-foo         # Rebase and push
make pr BRANCH=plan-123-foo               # Create PR
make finish BRANCH=plan-123-foo PR=456    # Merge, cleanup, done!
```

### Commit Messages

```bash
[Plan #N] Description       # Links to plan (required for significant work)
[Trivial] Fix typo          # For tiny changes (<20 lines, no src/ changes)
```

**Convention:** `[Plan #N]` or `[Trivial]` required for all commits.

---

## Key Rules

### Always Run From Main
- **Your CWD:** Always `/home/brian/brian_projects/agent_ecology2/` (main)
- **Worktrees:** Paths for file isolation, NOT working directories
- **Why:** You can handle full lifecycle (create → edit → merge → cleanup) without CWD issues

### Ownership
- Check claims before acting on any PR/worktree
- If work is claimed by another session: **read only**, move on to other work
- Self-merge your own PRs when ready (no review required)
- Only the owner should run `make finish` to merge + cleanup their worktree

### Plans
- All significant work requires a plan in `docs/plans/NN_name.md`
- Use `[Trivial]` only for: <20 lines, no `src/` changes, no new files
- Complete plans with: `python scripts/complete_plan.py --plan N`

### Never
- Commit directly to main (use feature branches)
- Use `git worktree rmv` directly (use `make worktree-remove`)
- Use `gh pr merge` directly (use `make finish`)
- Skip the claim when creating worktrees (use `make worktree`)
- Use `cd worktrees/...` as a separate command (chain with `&&` or use `git -C`)

---

## Meta-Process Guarantees

### Why Worktrees Exist

Worktrees provide **file isolation** for parallel work:

- Each plan gets its own directory with independent working state
- Changes in one worktree never affect another (no merge conflicts during work)
- Multiple plans can be in progress simultaneously
- Main stays clean (no uncommitted changes)

**Key:** Worktrees are paths (`worktrees/plan-X/src/file.py`), not CWDs. You always run from main.

### Why Claims Exist

Claims provide **coordination** so work doesn't collide:

- Branch-based: if a `plan-N-*` branch exists, work is claimed
- Stale detection: branches merged or inactive >48h with no worktree = stale
- Auto-release: when branches merge, claims automatically release
- Visible: check with `make status` or `python scripts/check_claims.py --list`

**Without claims:** Two sessions might start the same plan simultaneously, creating conflicting PRs.

### What Happens If You Bypass

| Bypass | Consequence |
|--------|-------------|
| Edit in main directly | No isolation, changes can conflict with other work |
| Skip `make worktree` | No claim = others can't see your work |
| Use `git worktree add` directly | Bypasses claim system, causes coordination failures |
| Use `git worktree remove` directly | Bypasses safety checks |
| Use `gh pr merge` directly | Bypasses validation, may break checks |
| Run from inside worktree | If worktree is deleted, your shell breaks |

### Git Commands in Worktrees - CRITICAL

**NEVER** use `cd worktrees/...` as a separate command. This permanently changes your shell CWD.

```bash
# WRONG - shell CWD stays in worktree after command
cd worktrees/plan-123-foo
git add -A
git commit -m "..."
# Shell is now stuck in worktree - if deleted, shell breaks

# RIGHT - CWD stays at main
git -C worktrees/plan-123-foo add -A && git -C worktrees/plan-123-foo commit -m "..."
```

**Why this matters:** If your shell CWD is inside a worktree when `make finish` deletes it, all subsequent bash commands fail with no output. The shell is broken and needs a session restart.

### How to Recover

**Stale claim blocking your work:**
```bash
python scripts/check_claims.py --cleanup-orphaned  # Remove claims with missing worktrees
python scripts/check_claims.py --cleanup-merged     # Remove claims for merged branches
```

**Orphaned worktree (branch merged but worktree remains):**
```bash
python scripts/cleanup_orphaned_worktrees.py         # Find orphaned worktrees
python scripts/cleanup_orphaned_worktrees.py --auto  # Auto-cleanup (safe only)
```

**Full diagnostics:**
```bash
python scripts/health_check.py        # Check everything
python scripts/health_check.py --fix  # Auto-fix issues
```

---

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
2. **Minimal kernel, maximum flexibility** - Kernel provides primitives for maximum agent capability. "Minimal" means focused on physics/primitives, NOT fewer features. If a kernel primitive expands what agents can do, it increases flexibility. Kernel should not impose policy - just provide building blocks agents compose.
3. **Align incentives** - Bad incentives = bad emergence
4. **Pragmatism over purity** - Don't let elegance obstruct goals
5. **Avoid defaults** - Prefer explicit choice; make defaults configurable
6. **Genesis as cold-start conveniences** - Genesis artifacts (ledger, escrow) and genesis contracts (freeware, private) are unprivileged conveniences that solve cold-start. They're NOT kernel features - agents could build equivalents. Kernel defaults (what happens when no contract exists) are separate from genesis.
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

- Don't jump into coding complex problems. Brainstorm first, finalize the approach together.
- Recommend the simplest solution. Present multiple approaches when they exist and ask which is preferred.
- Raise concerns early. If something feels off or unclear, ask rather than assume.
- **Delete > Comment.** Remove unused code, don't comment it out.
- **Flat > Nested.** Prefer flat structures over deep hierarchies.

### Process Awareness

If you find yourself doing something that isn't covered by the meta-process
(no pattern, no template, no convention), treat it as a signal:

- Either the meta-process has a gap — record it in `meta-process/ISSUES.md`
- Or you're deviating from process — stop and ask before continuing

Don't silently invent new conventions. Make them explicit.

---

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  config/
    config.yaml             # Runtime values
    # Validation via Pydantic in src/config_schema.py
  src/
    config.py               # Config helpers
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/
    plans/                  # Implementation plans (gaps)
    adr/                    # Architecture Decision Records
    architecture/           # current/ and target/ state
  meta/
    acceptance_gates/       # This project's feature specifications (YAML)
  meta-process/             # Portable framework (copy to other projects)
    patterns/               # Pattern documentation (26 patterns)
    scripts/                # Portable scripts
    hooks/                  # Hook templates
  scripts/                  # Utility scripts for CI and development
  hooks/                    # Git hooks (pre-commit, commit-msg)
  dashboard-v2/             # React dashboard frontend (builds to src/dashboard/static-v2/)
```

---

## Documentation

See `docs/CLAUDE.md` for the full documentation index. Doc-code coupling is enforced by `make check`.

---

## Session Continuity

When context compacts, you'll see:
```
read the full transcript at: ~/.claude/projects/.../[session-id].jsonl
```

Use the Read tool on that file if you need prior context.

---

## Pre-Merge Checklist

- [ ] `make check` passes (runs test + mypy + lint + doc-coupling)
- [ ] Code matches task description
- [ ] Plan status updated

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full philosophy, theoretical grounding |
| `docs/plans/CLAUDE.md` | Plan index and template |
| `meta-process/patterns/01_README.md` | Meta-pattern index |
| `docs/GLOSSARY.md` | Canonical terminology |
| `scripts/CLAUDE.md` | Script usage reference |
| `src/config_schema.py` | All config options (Pydantic) |

---

## Active Work

Check current claims with:
```bash
python scripts/check_claims.py --list
```

Claims are stored locally in `.claude/active-work.yaml` (not tracked in git) to prevent conflicts when PRs merge.
