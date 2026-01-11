# Agent Ecology - Claude Code Context

This file is always loaded. Keep it lean. Reference other docs for details.

## What This Is

A simulation where LLM agents interact under real resource constraints (compute, disk, API budget).

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  pyproject.toml            # Package config
  config/
    config.yaml             # Runtime values
    schema.yaml             # Structure + defaults
  src/
    config.py               # Config helpers: get(), get_genesis_config()
    config_schema.py        # Pydantic config validation
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/                     # Extended documentation
```

## Key Commands

```bash
pip install -e .                              # Required for imports
python run.py --ticks 10 --agents 1           # Run simulation
pytest tests/                                 # Run tests (must pass)
python -m mypy src/ --ignore-missing-imports  # Type check (must pass)
```

---

## Design Principles

### 1. Fail Loud, No Silent Fallbacks

**All errors must fail immediately. No silent degradation. No graceful fallbacks.**

- No `except: pass` - all exceptions must propagate or be handled explicitly
- No fallback behavior - if something fails, the system fails
- No "log and continue" - logging a warning and using a default is still a silent fallback
- Use `raise RuntimeError()` not `assert` for runtime checks

```python
# WRONG - silent fallback
except Exception:
    result = default

# WRONG - logged fallback is still a fallback
except APIError as e:
    logger.warning("API failed, using cache: %s", e)
    return cached_value

# RIGHT - fail immediately
result = do_the_thing()  # Raises exception on failure
```

**If fallback is genuinely needed for production:**
1. It MUST be behind a feature flag
2. Feature flag MUST be OFF by default
3. Development ALWAYS uses the optimal path (flag off = exception on failure)
4. Document in `docs/FALLBACKS.md` with explicit justification

```python
# Only if absolutely necessary for production resilience
if get("feature_flags.enable_api_fallback"):  # OFF by default!
    try:
        result = api_call()
    except APIError:
        result = cached_fallback()
else:
    result = api_call()  # Fails loudly - this is the development path
```

### 2. Maximum Observability

**Every significant operation must be traceable.**

- Log all state changes with context (agent_id, tick, action)
- Use structured logging (key=value pairs)
- Errors must include full context for debugging
- Never swallow exceptions without logging

### 3. No Magic Numbers - All Config in Config Files

**Zero numeric literals in code. All values come from configuration files.**

```python
# WRONG - magic number in code
disk_quota = 10000

# WRONG - default value in code
disk_quota = config.get("disk") or 10000

# WRONG - default in schema class
class ResourceConfig(BaseModel):
    disk: int = Field(default=10000)

# RIGHT - value from config, fails if missing
disk_quota = config.get("disk")  # Raises if not in config

# RIGHT - defaults in schema, runtime values in config.yaml
# config/schema.yaml documents structure and defaults
# config/config.yaml contains actual values
# code:
disk_quota = config.get("disk")  # From config.yaml, validated by schema
```

**Configuration files:**
```
config/
  schema.yaml      # Structure documentation and default reference
  config.yaml      # Actual runtime values
```

- `schema.yaml` documents structure and expected types
- `config.yaml` contains all runtime values
- Code reads config via `src/config.py` helpers
- Missing required values = immediate failure with clear error message

### 4. Strong Typing

- `mypy --strict` compliance required
- Pydantic models for structured data
- No `Any` without explicit justification

### 5. Physics-First

- Stock resources (llm_budget, disk): Finite, never refresh
- Flow resources (compute): Quota per tick, use-or-lose
- Scrip: Economic signal, separate from physical constraints

---

## Coding Standards

### Imports

```python
# Within src/ - relative imports
from ..config import get
from .ledger import Ledger

# From run.py or tests - absolute
from src.world import World
```

### Terminology

See `docs/GLOSSARY.md` for full definitions. Quick reference:

| Use | Not | Why |
|-----|-----|-----|
| `compute` | `flow` | Use specific resource name |
| `disk` | `stock` | Use specific resource name |
| `scrip` | `credits` | Consistency |
| `principal` | `account` | Principals include artifacts/contracts |
| `tick` | `turn` | Consistency |
| `llm_tokens` | `compute` (in code) | Code uses `llm_tokens` internally |

### Testing Philosophy

1. **Prefer real tests over mocks** - Test actual behavior, not mocked interfaces
2. **Mock only when necessary** - External APIs, network calls, time-sensitive operations
3. **If mocking, document why** - Comment explaining why mock is required
4. **Integration tests are valuable** - Test components working together

### Documentation Rules

**Canonical Sources:**
- `docs/architecture/current/` - What IS implemented (ground truth)
- `docs/architecture/target/` - What we WANT (ground truth)
- `docs/architecture/GAPS.md` - Delta between them

**Staleness:**
- Every `architecture/` doc must have `Last verified: YYYY-MM-DD`
- Stale = not verified in 7+ days
- Before code changes: check if relevant current/ doc is stale. If so, verify first.

**Code Change Protocol:**
1. Change code
2. Update `architecture/current/` to match
3. If gap closed, update `GAPS.md`
4. Update "Last verified" date

**Style:**
- Reference by function name, not line number (lines go stale)
- Keep CLAUDE.md lean (always in context)
- Reference other docs, don't duplicate

---

## Genesis Artifacts

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Balances, transfers, ownership |
| `genesis_oracle` | Auction-based scoring, minting |
| `genesis_rights_registry` | Quota management |
| `genesis_event_log` | Passive observability |
| `genesis_escrow` | Trustless artifact trading |
| `genesis_handbook` | Seeded documentation for agents |

---

## Multi-CC Instance Coordination

Multiple Claude Code instances may work simultaneously.

### Workflow

1. **Claim**: Move task from Backlog to In Progress, add CC-ID
2. **Plan**: Document approach in `temp_plan/CC-[ID]_[task].md`
3. **Implement**: Do work, update docs
4. **Mark Done**: Move to Awaiting Review
5. **Review**: Another CC verifies (tests + mypy pass, code correct)
6. **Archive**: Reviewer moves to `docs/TASK_LOG.md`

### Active Instances

| CC-ID | Task | Started |
|-------|------|---------|
| CC-1 | Available | - |
| CC-2 | Available | - |
| CC-3 | Available | - |
| CC-4 | Available | - |

### Task Backlog

| Task | Description | Priority |
|------|-------------|----------|
| (none) | - | - |

### In Progress

| Task | CC-ID | Started | Notes |
|------|-------|---------|-------|
| (none) | - | - | - |

### Awaiting Review

| Task | CC-ID | Completed | Reviewer |
|------|-------|-----------|----------|
| (none) | - | - | - |

### Coordination Rules

1. **One task at a time** - Finish or abandon before claiming another
2. **Update this file first** - Claim before starting work
3. **Tests + mypy must pass** - Before marking done
4. **Review required** - Another CC verifies before archiving to `docs/TASK_LOG.md`

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] Code matches task description
- [ ] No new silent fallbacks
- [ ] Relevant docs updated

---

## Architecture Documentation

### Canonical Sources

| Directory | Purpose | Update When |
|-----------|---------|-------------|
| `docs/architecture/current/` | How system works TODAY | Code changes |
| `docs/architecture/target/` | What we're building toward | Architecture decisions |
| `docs/architecture/GAPS.md` | Prioritized gaps, links to plans | Gap identified/closed |
| `docs/plans/` | HOW to close gaps (detailed steps) | Planning/completing work |
| `docs/DESIGN_CLARIFICATIONS.md` | WHY decisions were made (rationale archive) | Architecture discussions |

### Documentation Lifecycle

```
[Architecture Decision]
        ↓
   Update target/ + DESIGN_CLARIFICATIONS.md
        ↓
   Add gap to GAPS.md (if new)
        ↓
[Create Implementation Plan]
        ↓
   Write docs/plans/xxx.md
        ↓
[Implement]
        ↓
   Update docs/architecture/current/
        ↓
   Mark complete in GAPS.md
```

### Update Rules

1. **Code change → Update current/**
   - Any behavioral change must be reflected in current/ docs
   - Update line number references if they shifted
   - Update "Last verified" date in doc header

2. **Architecture decision → Update target/ + rationale**
   - Design decisions go in target/ docs
   - Record WHY in DESIGN_CLARIFICATIONS.md
   - Add to GAPS.md if creates new gap

3. **Starting implementation → Link to plan**
   - Ensure plan exists in docs/plans/
   - Mark plan status 🚧 In Progress
   - Add CC-ID to CLAUDE.md coordination section

4. **Completing implementation → Sync all docs**
   - Update current/ to match new reality
   - Mark gap ✅ Complete in GAPS.md
   - Update plan status

### Conflict Resolution

When multiple CCs update the same doc: **Last verified date wins.**

- Always update "Last verified: YYYY-MM-DD" when modifying a doc
- The most recent date is authoritative
- This encourages frequent verification and avoids merge conflicts

### Gap Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Has implementation plan |
| 🚧 In Progress | Being implemented |
| ⏸️ Blocked | Waiting on dependency |
| ❌ No Plan | Gap identified, no plan yet |
| ✅ Complete | Implemented, docs updated |

---

## References

| Doc | Purpose |
|-----|---------|
| `docs/architecture/GAPS.md` | **Gap tracking** - current vs target |
| `docs/GLOSSARY.md` | **Canonical terminology** - use these terms |
| `docs/DESIGN_CLARIFICATIONS.md` | **Decision rationale** - why we decided things |
| `docs/TASK_LOG.md` | Completed task history |
| `docs/DEFERRED_FEATURES.md` | Features considered but deferred |
| `config/schema.yaml` | All config options documented |
