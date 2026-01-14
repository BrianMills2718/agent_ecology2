First run:
```
python scripts/meta_status.py
```

**IMPORTANT:** This format is the standard for ALL recommendations, not just "what next?" situations. Any time you suggest an action, use this format to confirm alignment with metaprocess.

Based on the output, provide:

1. **Recommendation** - A specific next action
2. **Alignment** - Which CLAUDE.md priority this satisfies (cite the number)
3. **Uncertainties** - Any questions before proceeding, or "None"

**Priority order** (per CLAUDE.md):
1. Surface uncertainties - ask before guessing
2. Merge passing PRs / resolve conflicts - keeps queue clear
3. Review pending PRs - unblocks parallel work
4. Update stale documentation
5. New implementation (requires plan + worktree)

**Response format (ALWAYS use this for recommendations):**
> **Recommended:** [specific action]
> **Alignment:** Priority #N - [description]
> **Uncertainties:** [questions or "None"]

Example:
> **Recommended:** Merge PR #152 (trivial /proceed improvement)
> **Alignment:** Priority #2 - Merge passing PRs
> **Uncertainties:** None

---

**Starting implementation:**
1. Find existing plan or create new one (`docs/plans/NN_*.md`)
2. `make worktree BRANCH=plan-NN-description` (claims work)
3. TDD: define tests in plan, write tests first, then implement
4. `make release` when done, verify PR created

**All work requires a plan.** Use `[Trivial]` only for <20 line non-src changes.

Implementation work must be in a worktree.
