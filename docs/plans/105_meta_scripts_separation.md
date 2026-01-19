# Plan 105: Meta-Process Scripts Separation

**Status:** 📋 Deferred

**Priority:** Low
**Blocked By:** #103, #104
**Blocks:** None

---

## Gap

**Current:** Meta-process scripts live in `scripts/` mixed with project-specific scripts. Scripts have hardcoded paths assuming current directory structure.

**Target:** Meta-process scripts moved to `meta/scripts/` with configurable paths.

**Why:** Completes meta-process consolidation, enables extraction as standalone package.

**Why Deferred:**
- Plans #103 and #104 must complete first
- **High risk**: Scripts have many hardcoded paths
- Requires updating CI workflow, Makefile, CLAUDE.md
- Tests import these scripts
- Significant effort with high breakage potential
- Only needed when actually extracting to separate repo

---

## Scope

This plan covers **Phase 4** of meta-process separation:
- Move meta-process scripts to `meta/scripts/`
- Keep project-specific scripts in `scripts/`
- Update all path references
- Make paths configurable for portability

---

## Scripts to Move

### Meta-Process Scripts (move to `meta/scripts/`)

| Script | Purpose |
|--------|---------|
| `check_claims.py` | Claim system |
| `check_plan_tests.py` | Plan test verification |
| `check_plan_completion.py` | Completion evidence check |
| `check_plan_blockers.py` | Blocker detection |
| `check_plan_exclusivity.py` | Plan number uniqueness |
| `check_locked_files.py` | Locked section protection |
| `complete_plan.py` | Plan completion ceremony |
| `validate_plan.py` | Pre-implementation validation |
| `validate_spec.py` | Spec YAML validation |
| `sync_plan_status.py` | Plan status synchronization |
| `check_doc_coupling.py` | Doc-code coupling |
| `sync_governance.py` | ADR governance |
| `check_mock_usage.py` | Mock policy enforcement |
| `check_new_code_tests.py` | New code test coverage |
| `check_feature_coverage.py` | Feature file assignment |
| `check_adr_requirement.py` | ADR coverage check |
| `merge_pr.py` | PR merge helper |
| `cleanup_branches.py` | Stale branch cleanup |
| `setup_hooks.sh` | Hook installation |
| `create_worktree.sh` | Worktree creation |

### Project-Specific Scripts (keep in `scripts/`)

| Script | Purpose |
|--------|---------|
| `view_log.py` | Parse run.jsonl |
| `concat_for_review.py` | File concatenation |
| `meta_status.py` | Project dashboard |
| `plan_progress.py` | Plan progress display |
| `send_message.py` | Inter-CC messaging |
| `check_messages.py` | Message checking |

---

## Changes Required

### Path Refactoring

Every moved script needs path updates:

```python
# Before (hardcoded)
plans_dir = Path(__file__).parent.parent / "docs" / "plans"

# After (configurable)
from meta.config import get_meta_paths
paths = get_meta_paths()
plans_dir = paths.plans_dir
```

### New Configuration

```python
# meta/config.py
class MetaPaths:
    """Configurable paths for meta-process scripts."""

    def __init__(self, root: Path = None):
        self.root = root or Path(__file__).parent.parent

    @property
    def plans_dir(self) -> Path:
        return self.root / "docs" / "plans"

    @property
    def acceptance_gates_dir(self) -> Path:
        return self.root / "meta" / "acceptance_gates"

    # ... etc
```

### Files to Update

| File | Change |
|------|--------|
| `Makefile` | Update all script paths |
| `.github/workflows/ci.yml` | Update all script paths |
| `CLAUDE.md` | Update script references |
| `scripts/CLAUDE.md` | Split into `meta/scripts/CLAUDE.md` |
| `tests/unit/test_*.py` | Update imports |
| `tests/scripts/test_*.py` | Update imports |
| `scripts/doc_coupling.yaml` | Update paths |

---

## Implementation Steps

1. Wait for Plans #103 and #104 to complete
2. Create `meta/scripts/` directory
3. Create `meta/config.py` with path configuration
4. Move scripts one at a time, updating paths
5. Update Makefile targets
6. Update CI workflow
7. Update test imports
8. Update CLAUDE.md files
9. Full test suite verification
10. Manual verification of all make commands

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/` | All existing tests must pass |
| `tests/scripts/` | Script-specific tests must pass |

### Manual Verification

Every make command must work:
- [ ] `make test`
- [ ] `make check`
- [ ] `make mypy`
- [ ] `make lint`
- [ ] `make pr-ready`
- [ ] `make merge PR=N`
- [ ] `make worktree`
- [ ] `make release`
- [ ] `make claims`

---

## Acceptance Criteria

- [ ] Meta scripts in `meta/scripts/`
- [ ] Project scripts remain in `scripts/`
- [ ] All make commands work
- [ ] All CI checks pass
- [ ] Test suite passes
- [ ] Path configuration is centralized
- [ ] Documentation updated

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broken script paths | High | Careful testing, staged rollout |
| CI failures | High | Test in PR before merge |
| Make commands fail | High | Verify each command |
| Import errors in tests | Medium | Update systematically |
| Developer confusion | Medium | Clear documentation |

---

## Alternative: pip Package

Instead of moving scripts, could package meta-process as installable:

```bash
pip install agent-ecology-meta
```

Scripts become entry points:
```toml
[project.scripts]
ae-check-claims = "agent_ecology_meta.check_claims:main"
ae-complete-plan = "agent_ecology_meta.complete_plan:main"
```

This approach is cleaner but requires more infrastructure. Consider for future.

---

## Related

- Plan #103: Meta-Process Documentation Separation (Phase 1-2) - **blocks this**
- Plan #104: Meta-Process Hooks Separation (Phase 3) - **blocks this**
