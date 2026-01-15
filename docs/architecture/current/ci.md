# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-15 (Plan #43 - ADR check uses script; Plan #48 optimizations)

---

## GitHub Actions Workflow

Located at `.github/workflows/ci.yml`

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

**Concurrency:**
- Cancels in-progress runs when new commits push to same branch
- Prevents wasted CI on superseded commits

---

## Jobs (Consolidated)

The CI workflow has 7 consolidated jobs (reduced from 15+ for efficiency):

| Job | Checks | Caching |
|-----|--------|---------|
| `test` | pytest | ✓ pip cache |
| `mypy` | type checking | ✓ pip cache |
| `docs` | doc-coupling, governance-sync | - |
| `plans` | plan-status-sync, plan-blockers, plan-tests, plan-required | ✓ pip cache |
| `code-quality` | mock-usage, new-code-tests, feature-coverage | - |
| `meta` | locked-sections, validate-specs, claim-verification, human-review, adr-requirement | - |
| `post-merge` | plan-completion-evidence | - |

### 1. test

Runs the full pytest suite.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- uses: actions/cache@v4 (pip cache)
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
- uses: actions/cache@v4 (pip cache)
- pip install -r requirements.txt && pip install mypy
- mypy --strict --ignore-missing-imports src/config.py src/world/*.py src/agents/*.py run.py
```

**What it catches:**
- Type mismatches
- Missing type annotations
- Invalid attribute access
- Incompatible return types

### 3. docs

Combines documentation-related checks into a single job.

**Checks:**
1. **doc-coupling** - Checks that documentation is updated when coupled source files change
2. **governance-sync** - Ensures source files have correct governance headers

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_doc_coupling.py --base origin/main --strict
- python scripts/sync_governance.py --check
```

**What it catches:**
- Source file changes without corresponding doc updates
- Documentation drift from implementation
- Source files missing required ADR governance headers

### 4. plans

Combines plan-related checks into a single job.

**Checks:**
1. **plan-status-sync** - Verifies plan statuses are consistent
2. **plan-blockers** - Checks for stale blockers
3. **plan-tests** - Validates plan test requirements (strict)
4. **plan-required** - Ensures all commits have plan references

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- uses: actions/cache@v4 (pip cache)
- pip install -e . && pip install -r requirements.txt
- python scripts/sync_plan_status.py --check
- python scripts/check_plan_blockers.py --strict
- python scripts/check_plan_tests.py --list
- python scripts/check_plan_tests.py --all --strict
- (inline plan-required check)
```

**What it catches:**
- Plan file status doesn't match index
- Plans blocked by completed plans (stale dependency chains)
- Plans with missing required tests
- In Progress plans without test definitions
- Work without `[Plan #N]` or `[Trivial]` prefix

### 5. code-quality

Combines code quality checks into a single job.

**Checks:**
1. **mock-usage** - Detects suspicious mock patterns
2. **new-code-tests** - Ensures new source files have tests
3. **feature-coverage** - Reports files not assigned to features (informational)

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_mock_usage.py --strict
- python scripts/check_new_code_tests.py --base origin/main --strict --suggest
- python scripts/check_feature_coverage.py --warn-only  # continue-on-error
```

**What it catches:**
- Mocking internal `src.` code instead of testing it
- New files without test coverage
- Unassigned source files (informational)

### 6. meta (PRs only)

Combines meta-process checks. Only runs on pull requests.

**Checks:**
1. **locked-sections** - Detects modifications to locked acceptance criteria
2. **validate-specs** - Validates feature specification files
3. **claim-verification** - Verifies branch was claimed (informational)
4. **human-review-check** - Checks for plans requiring human review (informational)
5. **adr-requirement** - Checks ADR coverage for core files (informational)

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/check_locked_files.py --base origin/main
- python scripts/validate_spec.py --all
- (inline claim verification)  # continue-on-error
- (inline human review check)  # continue-on-error
- (inline ADR requirement check)  # continue-on-error
```

**What it catches:**
- Modifications to locked acceptance criteria
- Invalid feature specification format
- PRs from unclaimed branches (informational)
- PRs for plans with `## Human Review Required` section
- Core file changes without ADR references

**Human Review Check:**
Extracts plan numbers from commit messages, checks if plan files have `## Human Review Required` section, and warns if human review is needed before merge.

**ADR Requirement Check:**
Monitors changes to core architecture files (`src/world/{ledger,executor,genesis_*,action}.py`). If modified, checks if commits reference ADRs and provides informational guidance.

### 7. post-merge (main only)

Runs post-merge checks. Only runs on push to main.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 10)
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/check_plan_completion.py --recent-commits 5 --warn-only
```

**What it catches:**
- Plans marked Complete without verification evidence
- Commits referencing plans that lack verification

**Status:** Informational (`continue-on-error: true`).

---

## Dependency Caching

Jobs that need heavy dependencies use pip caching:

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

**Benefits:**
- Faster dependency installation (~30s savings per job)
- Less bandwidth usage
- More consistent builds

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

# Check plan tests
python scripts/check_plan_tests.py --list
python scripts/check_plan_tests.py --plan N

# Check for suspicious mock patterns
python scripts/check_mock_usage.py --strict
```

---

## Required for Merge

All jobs must pass for PRs to be mergeable:
- test
- mypy
- docs
- plans
- code-quality
- meta (on PRs only)

**Informational (doesn't block):**
- feature-coverage (within code-quality, warns about unassigned files)
- claim-verification (within meta, warns about unclaimed branches)
- human-review-check (within meta, warns about human review requirements)
- adr-requirement (within meta, warns about ADR coverage)
- post-merge (only runs after merge)

---

## Future Additions

Consider adding:
- **Coverage reporting** - Track test coverage trends
- **Lint job** - ruff or flake8 for style consistency
- **Security scanning** - pip-audit for dependency vulnerabilities
- **Conditional execution** - Skip jobs when irrelevant files change
