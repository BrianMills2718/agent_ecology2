First run:
```
python scripts/check_claims.py --list && gh pr list
```

Then read CLAUDE.md and proceed as you think best, consistent with CLAUDE.md.

Consider (roughly in order, use judgment):
- Surface uncertainties first - ask before guessing
- Merge passing PRs / resolve conflicts - keeps queue clear
- Review other instances' PRs - unblocks parallel work
- Update stale documentation
- New implementation

If finishing work: make release, verify PR created, check CI status.

If starting new implementation: use make worktree (handles claiming).

Implementation work must be in a worktree.
