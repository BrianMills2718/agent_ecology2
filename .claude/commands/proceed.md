First run:
```
python scripts/meta_status.py
```

Based on the output, provide:

1. **Recommendation** - A specific next action
2. **Alignment** - Which CLAUDE.md priority this satisfies
3. **Uncertainties** - Any questions before proceeding, or "None"

**Priority order** (per CLAUDE.md):
1. Surface uncertainties - ask before guessing
2. Merge passing PRs / resolve conflicts - keeps queue clear
3. Review pending PRs - unblocks parallel work
4. Update stale documentation
5. New implementation (requires plan + worktree)

**Response format:**
> **Recommended:** [specific action]
> **Alignment:** [which CLAUDE.md priority this satisfies]
> **Uncertainties:** [questions or "None"]

---

**Starting implementation:**
1. Find existing plan or create new one (`docs/plans/NN_*.md`)
2. `make worktree BRANCH=plan-NN-description` (claims work)
3. TDD: define tests in plan, write tests first, then implement
4. `make release` when done, verify PR created

**All work requires a plan.** Use `[Trivial]` only for <20 line non-src changes.

Implementation work must be in a worktree.
