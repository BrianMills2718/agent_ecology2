First run:
```
python scripts/meta_status.py
```

**IMPORTANT:** This format is the standard for ALL recommendations, not just "what next?" situations. Any time you suggest an action, use this format to confirm alignment with metaprocess.

**OWNERSHIP CHECK (Priority 0):**
Look at the "Yours?" column in meta_status.py output.
- Only act on items marked "✓ YOURS"
- For "NOT YOURS" items: note status only, do NOT fix/merge/modify
- Allowed on others' work: read, review, provide feedback
- NOT allowed: fix CI, resolve conflicts, merge, complete claims

Based on the output, provide:

1. **Recommendation** - A specific next action
2. **Ownership** - Is this YOUR work? (cite the "Yours?" status)
3. **Alignment** - Which CLAUDE.md priority this satisfies (cite the number)
4. **Uncertainties** - Any questions before proceeding, or "None"

**Priority order** (per CLAUDE.md):
0. Check ownership - verify item is yours before acting
1. Surface uncertainties - ask before guessing
2. Merge passing PRs / resolve conflicts - keeps queue clear (YOUR PRs only)
3. Review pending PRs - unblocks parallel work (review is allowed)
4. Update stale documentation
5. New implementation (requires plan + worktree)

**Response format (ALWAYS use this for recommendations):**
> **Recommended:** [specific action]
> **Ownership:** ✓ YOURS / NOT YOURS (only act if yours)
> **Alignment:** Priority #N - [description]
> **Uncertainties:** [questions or "None"]

Example:
> **Recommended:** Merge PR #152 (trivial /proceed improvement)
> **Ownership:** ✓ YOURS (branch: plan-152-proceed)
> **Alignment:** Priority #2 - Merge passing PRs
> **Uncertainties:** None

Example (when NOT yours):
> **Status:** PR #153 is blocked on CI
> **Ownership:** NOT YOURS (owned by: plan-153-feature)
> **Action:** Review/feedback allowed; do not fix or merge

---

**Starting implementation:**
1. Find existing plan or create new one (`docs/plans/NN_*.md`)
2. `make worktree BRANCH=plan-NN-description` (claims work)
3. TDD: define tests in plan, write tests first, then implement
4. `make release` when done, verify PR created

**All work requires a plan.** Use `[Trivial]` only for <20 line non-src changes.

Implementation work must be in a worktree.
