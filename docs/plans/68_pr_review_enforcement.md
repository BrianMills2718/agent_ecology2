# Plan 68: PR Review Process Enforcement

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Quality assurance for all future PRs

---

## Gap

**Current:** CLAUDE.md documents cross-instance review requirement, but:
- 0 out of 100+ merged PRs have any GitHub reviews
- Review instructions are vague ("Are tests meaningful?")
- No enforcement mechanism
- No workflow for how reviewers get assigned

**Target:**
- All non-trivial PRs require review before merge
- Concrete, actionable review checklist
- Clear workflow for review assignment
- GitHub branch protection enforces requirement

**Why High:** Without functioning reviews, quality depends entirely on CI. Human/CC reviewers can catch issues CI cannot (design problems, unclear code, missing edge cases).

---

## References Reviewed

- CLAUDE.md "Cross-Instance Review" section - vague criteria
- `gh pr list --state merged` - 0/100 PRs have reviews
- GitHub branch protection settings - currently not requiring reviews

---

## Files Affected

- CLAUDE.md (modify) - Add concrete review checklist, clarify workflow
- docs/meta/25_pr-review-process.md (create) - Detailed review guide
- .github/pull_request_template.md (modify) - PR template with review hints
- GitHub repo settings (configure) - Enable required reviews

---

## Plan

### Phase 1: Review Checklist

Add concrete, actionable checklist to CLAUDE.md:

```markdown
### Review Checklist (Concrete Items)

**Code Quality:**
- [ ] No `except:` or `except Exception:` without `# exception-ok:` comment
- [ ] No hardcoded values that should be in config
- [ ] No TODO/FIXME without issue link
- [ ] Functions over 50 lines have clear structure

**Testing:**
- [ ] New code has tests
- [ ] Tests cover error paths, not just happy path
- [ ] No `# mock-ok:` without clear justification

**Security:**
- [ ] No secrets/credentials in code
- [ ] User input validated before use
- [ ] No SQL string concatenation

**Documentation:**
- [ ] Public functions have docstrings
- [ ] Complex logic has inline comments
- [ ] CLAUDE.md updated if behavior changes

**What to REJECT:**
- Silent exception swallowing
- Tests that only check happy path
- Magic numbers without config
- Missing error handling on external calls
```

### Phase 2: Review Workflow

Add clear assignment workflow:

```markdown
### Review Assignment

**For CC instances:**
1. On session start, check `gh pr list --state open`
2. PRs without reviews need attention
3. Review PRs you didn't author
4. Use GitHub review feature (not just comments)

**For humans:**
1. GitHub notifications for PR creation
2. Review when available
3. Can delegate to CC with guidance
```

### Phase 3: PR Template

Create `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Summary
<!-- 1-3 bullet points of what this PR does -->

## Test Plan
<!-- How to verify this works -->

## Review Focus
<!-- What specifically needs careful review -->

---
**Reviewer Checklist** (copy to review comment):
- [ ] Code quality items checked
- [ ] Tests are meaningful
- [ ] No security concerns
- [ ] Docs updated appropriately
```

### Phase 4: Branch Protection

Enable GitHub branch protection:
- Require 1 review before merge
- Require review from code owners (optional)
- Dismiss stale reviews on new commits

### Phase 5: Meta Documentation

Create `docs/meta/25_pr-review-process.md` with:
- Full review guide
- Examples of good vs bad reviews
- When to approve vs request changes
- How to give constructive feedback

---

## Required Tests

### Existing Tests (Must Pass)

No new tests needed - this is documentation/process only.

| Test Pattern | Why |
|--------------|-----|
| `pytest tests/` | All tests still pass |
| `python scripts/check_doc_coupling.py` | Doc coupling satisfied |

### Manual Verification
- [ ] Review checklist is in CLAUDE.md
- [ ] PR template appears on new PRs

---

## E2E Verification

Create a test PR and verify:
1. Cannot merge without review
2. Review checklist is visible
3. PR template is populated

---

## Verification

### Documentation
- [x] CLAUDE.md has concrete review checklist
- [x] docs/meta/25_pr-review-process.md created
- [x] .github/PULL_REQUEST_TEMPLATE.md created

### Enforcement
- [x] ~~GitHub branch protection requires reviews~~ **Skipped** - All CC instances use same GitHub account, so can't approve each other's PRs. Process-based enforcement via checklist instead.
- [x] Review process documented and PR template created

### Completion Ceremony
- [ ] Plan file status -> Complete
- [ ] plans/CLAUDE.md index updated
- [ ] Claim released

---

## Notes

### Design Decisions

1. **Start with 1 required review** - Can increase later if needed
2. **CC can review CC** - No human bottleneck, but humans can review too
3. **Checklist over prose** - Concrete items are actionable
4. **PR template is optional** - GitHub will show it but authors can modify

### Resolved Questions

1. **GitHub enforcement?** No - all CC instances use same account, can't self-approve. Process-based instead.
2. **Human review for src/?** Not required - CC review is sufficient with checklist.
3. **Urgent fixes?** Use `[Trivial]` exemption for small fixes.

### Risk

Medium risk - may slow down merge velocity initially. Mitigated by clear checklist making reviews faster.
