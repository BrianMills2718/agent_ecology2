First run:
```
python scripts/check_claims.py --list && python scripts/check_claims.py --list-features && gh pr list
```

Then read CLAUDE.md and proceed as you think best, consistent with CLAUDE.md.

Consider (roughly in order, use judgment):
- Surface uncertainties first - ask before guessing
- Merge passing PRs / resolve conflicts - keeps queue clear
- Review other instances' PRs - unblocks parallel work
- Update stale documentation
- New implementation (see below)

**Finishing work:** `make release`, verify PR created, check CI status.

**Starting ANY implementation:**
1. Find existing plan or create new one (`docs/plans/NN_*.md`)
2. Define required tests in the plan (TDD workflow)
3. `make worktree BRANCH=plan-NN-description` (claims work)
4. Write tests first, then implement
5. If plan has `## Human Review Required`, flag human before completing

**All work requires a plan. No exceptions.**

Commits must use `[Plan #NN]` prefix. CI blocks `[Unplanned]` commits.
Plans can be lightweight for trivial work - see `docs/plans/TEMPLATE.md`.

Implementation work must be in a worktree.
