## Summary

<!-- 1-3 bullet points describing what this PR does -->

-

## Plan Reference

<!-- Link to plan if applicable, or "[Trivial]" for small fixes -->
Plan #:

## Test Plan

<!-- How to verify this works -->

```bash
# Commands to test
```

---

## For Reviewers

**Review Focus:**
<!-- What specifically needs careful review in this PR? -->

**Reviewer Checklist** (copy to review comment when approving):

```
Code Quality:
- [ ] No `except:` without `# exception-ok:` comment
- [ ] No hardcoded magic numbers (use config)
- [ ] No TODO/FIXME without issue link

Testing:
- [ ] New code has tests
- [ ] Tests cover error paths

Security:
- [ ] No secrets in code
- [ ] Input validated before use

Docs:
- [ ] Docs updated if behavior changed
```

**Quick Commands:**
```bash
gh pr diff <number>           # View changes
gh pr checkout <number>       # Test locally
gh pr review <number> --approve --body "Checklist verified."
```

---
Generated with Claude Code
