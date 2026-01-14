# Continuous Integration

Documentation of CI/CD setup.

Last verified: 2026-01-14 (Plan #43 - added human-review-check and adr-requirement)

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

Checks test requirements for implementation plans. **Strict** - blocks PRs if tests fail or In Progress plans lack tests.

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5 (Python 3.11)
- pip install -e . && pip install -r requirements.txt
- python scripts/check_plan_tests.py --list
- python scripts/check_plan_tests.py --all --strict
```

**Environment:** `GEMINI_API_KEY` from GitHub secrets (for memory/embedding tests).

**What it catches:**
- Plans with missing required tests
- **In Progress plans without any test definitions** (`--strict` mode, Plan #41 Step 4)
- TDD workflow status (which tests need to be written)
- Test failures for plans with defined requirements

**Only checks active plans:** Plans in "In Progress" (`🚧`) or "Complete" (`✅`) status. Plans that are "Planned", "Needs Plan", or "Blocked" are skipped (TDD tests should be written when work starts, not when plan is created).

**Strict mode:** With `--strict`, CI fails for any In Progress plan without a `## Required Tests` section. This ensures TDD workflow is followed - tests must be defined before implementation.

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

**All significant work requires a plan.** Blocks PRs containing `[Unplanned]` commits.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- Check for [Unplanned] in commit messages
- Validate [Trivial] commits don't exceed limits
- exit 1 if unplanned found
```

**What it catches:**
- Work that bypassed the planning process
- Commits without `[Plan #N]` or `[Trivial]` prefix

**Allowed prefixes:**
- `[Plan #N]` - Links to plan in `docs/plans/NN_*.md`
- `[Trivial]` - For tiny changes (see below)

**Trivial exemption:** Use `[Trivial]` for tiny changes:
```bash
git commit -m "[Trivial] Fix typo in README"
```

**Trivial criteria (ALL must be true):**
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created

CI validates trivial commits and warns if limits exceeded.

**To fix [Unplanned] commits:**
1. Create a plan file: `docs/plans/NN_your_feature.md`
2. Amend commits to use `[Plan #NN]` prefix
3. Or use `[Trivial]` if criteria are met

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

### 14. plan-completion-evidence (Post-merge, Informational)

Checks that merged plan commits have verification evidence. Runs post-merge on main to catch plans completed without using `complete_plan.py`.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 10)
- uses: actions/setup-python@v5 (Python 3.11)
- python scripts/check_plan_completion.py --recent-commits 5 --warn-only
```

**What it catches:**
- Plans marked Complete without `**Verified:**` timestamp
- Commits referencing plan numbers where plan lacks verification evidence

**When it runs:**
- Only on push to main (post-merge)
- Not on PRs (to avoid false positives for in-progress work)

**Script options:**
```bash
python scripts/check_plan_completion.py --recent-commits 5  # Check last 5 commits
python scripts/check_plan_completion.py --plan N            # Check specific plan
python scripts/check_plan_completion.py --list-missing      # All plans missing evidence
```

**Status:** Informational (`continue-on-error: true`, `--warn-only`). Reports issues but doesn't block main.

### 15. human-review-check (PRs only, Informational)

Checks if PRs touch plans with `## Human Review Required` section. Warns to ensure human review before merge.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- uses: actions/setup-python@v5 (Python 3.11)
- Extract plan numbers from commit messages
- Check if plan files have ## Human Review Required
```

**What it catches:**
- PRs implementing plans that require human approval
- Changes to sensitive features flagged for review

**Status:** Informational (`continue-on-error: true`). Will become strict when process is established.

### 16. adr-requirement (PRs only, Informational)

Checks if core architecture files are modified and warns if no ADR is referenced.

```yaml
- uses: actions/checkout@v4 (with fetch-depth: 0)
- Check if core files modified: src/world/{ledger,executor,genesis_*,action}.py
- Check if commits reference ADR-NNNN
```

**Core files:**
- `src/world/ledger.py`
- `src/world/executor.py`
- `src/world/artifacts/genesis_*.py`
- `src/world/action.py`

**What it catches:**
- Architectural changes without documented decisions
- Core file modifications that may need ADR coverage

**Status:** Informational (`continue-on-error: true`). Tracks ADR coverage without blocking.


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
