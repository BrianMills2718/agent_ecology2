# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-12 (added --staged mode for pre-commit)

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

### 4. plan-tests (Informational)

Checks test requirements for implementation plans. Runs with `continue-on-error: true` - does not block PRs.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install -e . && pip install -r requirements.txt
- python scripts/check_plan_tests.py --list
- python scripts/check_plan_tests.py --all
```

**What it catches:**
- Plans with missing required tests
- TDD workflow status (which tests need to be written)
- Test failures for plans with defined requirements

**Configuration:** Test requirements defined in each plan file's `## Required Tests` section.

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
```

---

## Required for Merge

All three jobs must pass for PRs to be mergeable (when branch protection is enabled).

---

## Future Additions

Consider adding:
- **Coverage reporting** - Track test coverage trends
- **Lint job** - ruff or flake8 for style consistency
- **Security scanning** - pip-audit for dependency vulnerabilities
- **PR template** - Checklist for manual review items
