# Agent Ecology

LLM agents operating under real resource constraints (compute, disk, API budget) with economic coordination primitives (contracts, escrow, ledger). The goal is a production system where agents build collective capability.

---

## About This File

**This file is automatically loaded by Claude Code for every conversation in this repo.**

Keep it minimal. This file should contain ONLY:
- Commands you need frequently (not setup/install - that's README)
- Design principles that apply to ALL code changes
- Pointers to detailed docs (not the details themselves)

Domain-specific context belongs in subdir CLAUDE.md files (e.g., `src/world/CLAUDE.md`).

---

## Quick Start

```bash
./check                   # Run all CI checks locally
make help                 # Show all available commands
```

## Essential Commands

| Command | Purpose |
|---------|---------|
| `./check` | **Run all CI checks locally** (do this before push) |
| `./check --quick` | Fast check (skips claim listing) |
| `make test` | Run pytest |
| `make mypy` | Run type checker |
| `make status` | Show git + claims status |
| `make gaps` | Show gap implementation status |

### Workflow Commands

| Command | Purpose |
|---------|---------|
| `make branch PLAN=3 NAME=docker` | Create plan branch |
| `make claim TASK="..." PLAN=3` | Claim work on a plan |
| `make claim TASK="Fix bug"` | Claim non-plan work |
| `make release` | Release claim with TDD validation |
| `make pr` | Open PR creation in browser |

### Other Useful Commands

| Command | Purpose |
|---------|---------|
| `make lint-suggest` | Show which docs need updates |
| `make gaps-sync` | Sync plan statuses if drifted |
| `make clean` | Remove generated files |
| `make run TICKS=10 AGENTS=2` | Run simulation |

---

## Project Structure

```
agent_ecology/
  run.py              # Entry point
  config/config.yaml  # All runtime values (no magic numbers in code)
  src/
    world/            # Ledger, artifacts, executor, genesis services
    agents/           # Agent loading, LLM, memory
    simulation/       # Runner, checkpoint
    dashboard/        # HTML dashboard
  tests/              # pytest suite
  docs/               # Extended documentation
```

---

## Design Principles

### 1. Fail Loud

All errors fail immediately. No silent fallbacks or graceful degradation that masks problems.

```python
# BAD - hides failure
except APIError:
    return cached_fallback()

# BAD - graceful degradation that tricks you
except Exception:
    logger.warning("Using reduced functionality")
    return partial_result()

# OK - expected retry with logging
except RateLimitError:
    logger.info("Rate limited, retrying in %s", delay)
    await asyncio.sleep(delay)
    return await retry()

# GOOD - fail immediately
result = do_the_thing()  # Raises on failure
```

If fallback is genuinely needed for production, it MUST be behind a feature flag (OFF by default).

### 2. No Magic Numbers

All values come from `config/config.yaml`. Missing config = immediate failure.

### 3. Strong Typing

`mypy --strict` compliance. Pydantic for structured data. No `Any` without justification.

### 4. Observability

Log state changes with context (agent_id, tick, action). Never swallow exceptions.

---

## Code Style

### Edits
- **Prefer editing existing files** over creating new ones
- **Don't add to unchanged code**: no new comments, docstrings, or type annotations to code you didn't modify
- **Avoid over-engineering**: don't add abstractions, helpers, or configurability beyond what's requested
- **Delete unused code completely**: no `_unused` renames, no `# removed` comments

### Imports
```python
# Within src/ - use relative imports
from ..config import get
from .ledger import Ledger

# From run.py or tests/ - use absolute imports
from src.world import World
```

### Commits
```bash
# Link to plan when applicable
git commit -m "[Plan #3] Implement docker isolation

- Added Dockerfile
- Added docker-compose.yml

Co-Authored-By: Claude <noreply@anthropic.com>"

# For non-plan work
git commit -m "Fix: Correct rate limit calculation

- Fixed off-by-one in window expiry
- Added test for edge case"
```

---

## Key Documentation

| Doc | Purpose |
|-----|---------|
| `docs/architecture/gaps/CLAUDE.md` | **Gap tracking** - what to work on next |
| `docs/architecture/current/` | What IS implemented |
| `docs/architecture/target/` | What we WANT |
| `docs/GLOSSARY.md` | Terminology (scrip, principal, tick, etc.) |
| `config/schema.yaml` | All config options |
| `README.md` | Philosophy and theoretical grounding |

---

## Multi-Instance Coordination

Multiple Claude Code instances can work simultaneously. Branch name = instance identity.

### Full Workflow

```bash
# 1. Create branch and claim
make branch PLAN=3 NAME=docker
make claim TASK="Implement docker isolation" PLAN=3

# 2. Do work (TDD: write tests first)
# ... implement ...

# 3. Validate locally
./check

# 4. Push and create PR
git add -A && git commit -m "[Plan #3] Implement docker isolation"
git push -u origin plan-3-docker
make pr

# 5. Get review (ideally different CC instance)
# 6. Merge PR
# 7. Release claim
make release
```

### Parallel Work (Multiple CCs)

```bash
# Use git worktrees - each CC gets isolated workspace
git worktree add ../ecology-plan-3 plan-3-docker
cd ../ecology-plan-3 && claude
# When done:
git worktree remove ../ecology-plan-3
```

### What's Enforced (GitHub Branch Protection)

| Rule | Effect |
|------|--------|
| PR required | Can't push directly to main |
| 1 approval required | Someone must approve PR |
| CI must pass | `test`, `mypy`, `doc-coupling`, `plan-status-sync` |
| Conversations resolved | Must address review comments |
| Stale approvals dismissed | Re-review needed after new commits |

### Dependency Checking

```bash
# Check if a plan's dependencies are complete
python scripts/check_claims.py --check-deps 7
# Claiming a plan with incomplete deps is blocked (use --force to override)
```

### Cross-Instance Review

For significant changes, different CC instance should review:
```bash
# Reviewer in separate worktree or after /clear
git fetch origin
git diff main..origin/plan-3-docker
# Review, then approve PR
```

---

## Gap Tracking

Single source of truth: `docs/architecture/gaps/CLAUDE.md`

- 142 gaps organized by workstream (ws1-ws6 YAML files)
- 31 epics grouping related gaps
- Implementation plans in `gaps/plans/`

**Workflow:** Read gap → Write tests → Claim in CLAUDE.md → Implement → Update status

---

## Subdir CLAUDE.md Files

This root file covers universal essentials. Subdirectories have their own CLAUDE.md with area-specific context:

- `src/world/CLAUDE.md` - Ledger, artifacts, genesis services
- `docs/architecture/gaps/CLAUDE.md` - Gap tracking details
- `config/CLAUDE.md` - Configuration structure
