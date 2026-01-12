# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-12

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

**Configuration:** `scripts/doc_coupling.yaml` defines source-to-doc mappings:
```yaml
couplings:
  - sources: ["src/world/ledger.py"]
    docs: ["docs/architecture/current/resources.md"]
    description: "Resource accounting"
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
