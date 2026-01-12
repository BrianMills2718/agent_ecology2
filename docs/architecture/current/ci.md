# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-12 (updated for coordination-tables job)

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

### 5. plan-tests (Informational)

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

### 6. mock-usage

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

Ensures source files have correct governance headers matching `governance.yaml`.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/sync_governance.py --check
```

**What it catches:**
- Source files missing required ADR governance headers
- Stale or incorrect governance headers

### 8. coordination-tables

Ensures coordination tables in CLAUDE.md are auto-generated, not manually edited.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install pyyaml
- python scripts/generate_coordination_tables.py --check
```

**What it catches:**
- Manual edits to Active Work or Awaiting Review tables
- Tables out of sync with source data

**Why:** Prevents merge conflict cascades when multiple PRs try to update the same tables. Tables are auto-generated from `.claude/active-work.yaml` and `gh pr list`.

See [Coordination Table Automation](../../meta/coordination-table-automation.md) pattern for details.

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
- mock-usage
- governance-sync
- coordination-tables

---

## Auto-Sync Workflows

### sync-coordination-tables

Located at `.github/workflows/sync-coordination-tables.yml`

**Triggers:**
- Push to `main` branch
- Manual dispatch (for recovery)

**What it does:**
1. Runs after any merge to main
2. Regenerates coordination tables from source data
3. Commits and pushes if tables changed

**Why:** Keeps coordination tables accurate without manual PRs. Tables auto-update after every merge.

**Loop prevention:** Skips if commit message contains `[Auto] Sync coordination tables`.

---

## Future Additions

Consider adding:
- **Coverage reporting** - Track test coverage trends
- **Lint job** - ruff or flake8 for style consistency
- **Security scanning** - pip-audit for dependency vulnerabilities
- **PR template** - Checklist for manual review items
