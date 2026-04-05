# Plan #324: Governance Bootstrap

**Status:** ✅ Complete
**Priority:** Low
**Blocked By:** —
**Blocks:** —

---

## Gap

**Current:** Repo classified as `partial` by governed-repo-audit. Missing: in-sync AGENTS.md, validator:file_context, validator:validate_plan, validator:check_markdown_links. CLAUDE.md missing required Commands and References sections.

**Target:** Repo classified as `governed`. AGENTS.md regenerated and in sync. All required validators present.

**Why Low:** Governance hygiene; no functional impact on running code.

---

## References Reviewed

- `CLAUDE.md` — missing Commands and References sections
- `AGENTS.md` — out of sync with CLAUDE.md
- `enforced-planning/scripts/install_governed_repo.py` — installer behavior

---

## Acceptance Criteria

- [ ] `audit_repo()` returns `classification: governed`
- [ ] `AGENTS.md` regenerated from current `CLAUDE.md`
- [ ] Validators present: `check_markdown_links.py`, pre-commit hooks updated

---

## Implementation

1. Add `Commands` and `References` sections to `CLAUDE.md`
2. Run `install_governed_repo.py --write`
3. Commit via PR (branch protection active on main)
