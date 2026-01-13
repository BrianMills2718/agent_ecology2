# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-13 (plan-required now blocks, unplanned-work removed)

---

## GitHub Actions Workflow

Located at `.github/workflows/ci.yml`

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

---

## Jobs

### 1. test

Runs the full pytest suite.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install -e . && pip install -r requirements.txt
- pytest tests/ -v --tb=short
```

**Environment:** `GEMINI_API_KEY` from GitHub secrets (for memory/embedding tests).

**What it catches:**
- Runtime errors
- Logic bugs
- Regression from code changes
- Integration issues between components

### 2. mypy

Runs strict type checking on core modules.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install -r requirements.txt && pip install mypy
- mypy --strict --ignore-missing-imports src/config.py src/world/*.py src/agents/*.py run.py
```

**What it catches:**
- Type mismatches
- Missing type annotations
- Invalid attribute access
- Incompatible return types

### 3. doc-coupling

Checks that documentation is updated when coupled source files change.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_doc_coupling.py --base origin/main --strict
```

**What it catches:**
- Source file changes without corresponding doc updates
- Documentation drift from implementation

### 4. plan-status-sync

Verifies plan statuses are consistent between individual plan files and the index.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/sync_plan_status.py --check
```

**What it catches:**
- Plan file status doesn't match index in `docs/plans/CLAUDE.md`
- Status drift after plan updates

### 5. plan-blockers

Checks for stale blockers - plans marked "Blocked" but whose blockers are already complete.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/check_plan_blockers.py --strict
```

**What it catches:**
- Plans blocked by completed plans (stale dependency chains)
- Blockers not updated when work completes

**Fixing stale blockers:**
```bash
python scripts/check_plan_blockers.py --apply  # Auto-fix
python scripts/sync_plan_status.py --sync       # Update index
```

### 6. plan-tests

Checks test requirements for implementation plans. **Strict** - blocks PRs if tests fail.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install -e . && pip install -r requirements.txt
- python scripts/check_plan_tests.py --list
- python scripts/check_plan_tests.py --all
```

**Environment:** `GEMINI_API_KEY` from GitHub secrets (for memory/embedding tests).

**What it catches:**
- Plans with missing required tests
- TDD workflow status (which tests need to be written)
- Test failures for plans with defined requirements

**Only checks active plans:** Plans in "In Progress" (`🚧`) or "Complete" (`✅`) status. Plans that are "Planned", "Needs Plan", or "Blocked" are skipped (TDD tests should be written when work starts, not when plan is created).

**Configuration:** Test requirements defined in each plan file's `## Required Tests` section.

### 7. mock-usage

Detects suspicious mock patterns that may hide real failures ("green CI, broken production").

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/check_mock_usage.py --strict
```

**What it catches:**
- Mocking internal `src.` code instead of testing it
- Mocking Memory, Agent, or other core classes
- Using MagicMock return values for internal code

**Allowed patterns (not flagged):**
- Mocking `time.`, `datetime`, `sleep` (timing)
- Mocking `requests.`, `httpx.`, `aiohttp.` (external HTTP)

**Justifying a mock:** Add `# mock-ok: <reason>` comment:
```python
# mock-ok: Testing error handling when memory unavailable
@patch("src.agents.memory.Memory.search")
def test_memory_error_handling():
    ...
```

### 7. governance-sync

Ensures source files have correct governance headers matching governance.yaml.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/sync_governance.py --check
```

**What it catches:**
- Source files missing required ADR governance headers
- Governance headers out of sync with governance.yaml

### 8. validate-specs

Validates feature specification files in `features/*.yaml`.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/validate_spec.py --all
```

**What it catches:**
- Feature specs with fewer than 3 acceptance criteria
- Missing Given/When/Then format
- Missing category coverage (happy_path, error_case, edge_case)
- Missing design section when planning_mode is "detailed"

### 9. locked-sections (PRs only)

Detects modifications to locked acceptance criteria. Only runs on pull requests.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_locked_files.py --base origin/main
```

**What it catches:**
- Modifications to acceptance criteria marked with `locked: true`
- Deletion of locked criteria
- Changes to locked scenario, given, when, or then fields

### 10. feature-coverage (Informational)

Reports source files not assigned to features. Runs with `continue-on-error: true` - does not block PRs.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_feature_coverage.py --warn-only
```

**What it catches:**
- Source files in `src/` and `scripts/` not listed in any feature's `code:` section
- Coverage percentage across the codebase

### 11. new-code-tests

Ensures new source files have corresponding tests.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/check_new_code_tests.py --base origin/main --strict --suggest
```

**What it catches:**
- New files in `src/` or `scripts/` without tests
- Code added without test coverage

**Exemptions:**
- `__init__.py` files
- `conftest.py` files
- Template directories (`_template/`)
- `CLAUDE.md` files

### 12. plan-required (Strict)

**All work requires a plan.** Blocks PRs containing `[Unplanned]` commits.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- Check for [Unplanned] in commit messages
- exit 1 if found
```

**What it catches:**
- Work that bypassed the planning process
- Commits without `[Plan #N]` prefix

**To fix:**
1. Create a plan file: `docs/plans/NN_your_feature.md`
2. Amend commits to use `[Plan #NN]` prefix
3. Or rebase and squash with proper prefix

Plans can be lightweight for trivial work - see `docs/plans/TEMPLATE.md`.

### 13. claim-verification (PRs only, Informational)

Verifies PR branches were claimed before work started. Prevents duplicate work between Claude instances.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_claims.py (inline verification)
```

**What it catches:**
- PRs from branches without corresponding claims
- Work started without coordination

**Scope-based claims:**
Claims should specify a scope (`--plan N` and/or `--feature NAME`):
```bash
python scripts/check_claims.py --list-features    # See available features
python scripts/check_claims.py --claim --feature ledger --task "..."
```

Features are defined in `features/*.yaml` with their code files. Same plan number or same feature name blocks duplicate claims.

**Status:** Currently informational (`continue-on-error: true`). Will become strict once workflow is established.

See `docs/meta/claim-system.md` for full workflow.

---

## Doc-Code Coupling

**Configuration:** `scripts/doc_coupling.yaml` defines source-to-doc mappings:
```yaml
couplings:
  # Strict: CI fails if violated
  - sources: ["src/world/ledger.py"]
    docs: ["docs/architecture/current/resources.md"]
    description: "Resource accounting"

  # Soft: CI warns but doesn't fail
  - sources: ["docs/architecture/current/*.md"]
    docs: ["docs/plans/CLAUDE.md"]
    description: "Gap closure tracking"
    soft: true
```

**Coupling types:**
- **Strict** (default): CI fails if source changes without doc update
- **Soft** (`soft: true`): CI warns but doesn't fail - for reminder couplings

**Soft couplings include:**
- `current/` changes → `plans/CLAUDE.md` (did you close a gap?)
- Plan file changes → `plans/CLAUDE.md` index (sync status)
- Terminology files → GLOSSARY.md (new terms?)

**Script options:**
```bash
--suggest         # Show which docs to update
--validate-config # Check all docs in config exist
--strict          # Fail on strict violations (used in CI)
```

---

## Local Equivalents

Run these before pushing to catch issues early:

```bash
# Run tests
pytest tests/ -v

# Run mypy (same flags as CI)
python -m mypy --strict --ignore-missing-imports --exclude '__pycache__' --no-namespace-packages src/config.py src/world/*.py src/agents/*.py run.py

# Check doc-code coupling
python scripts/check_doc_coupling.py --base origin/main

# See which docs you should update
python scripts/check_doc_coupling.py --suggest --base origin/main

# Validate coupling config (check all doc paths exist)
python scripts/check_doc_coupling.py --validate-config

# List plan test status
python scripts/check_plan_tests.py --list

# TDD mode - see what tests to write for a plan
python scripts/check_plan_tests.py --plan 1 --tdd

# Run all required tests for a plan
python scripts/check_plan_tests.py --plan 1

# Check for suspicious mock patterns
python scripts/check_mock_usage.py

# Fail on suspicious mocks (as in CI)
python scripts/check_mock_usage.py --strict
```

---

## Required for Merge

All jobs must pass for PRs to be mergeable (when branch protection is enabled):
- test
- mypy
- doc-coupling
- plan-status-sync
- plan-blockers
- plan-tests
- mock-usage
- governance-sync
- validate-specs
- locked-sections (on PRs only)
- new-code-tests
- plan-required (all work needs a plan)

**Informational (doesn't block):**
- feature-coverage (warns about unassigned files)
- claim-verification (warns about unclaimed branches)

---

## Future Additions

Consider adding:
- **Coverage reporting** - Track test coverage trends
- **Lint job** - ruff or flake8 for style consistency
- **Security scanning** - pip-audit for dependency vulnerabilities
- **PR template** - Checklist for manual review items
