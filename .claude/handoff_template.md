# Session Handoff Template

Copy this to `handoff.md` and fill in before ending your session.

---

# Session Handoff

**Date:** YYYY-MM-DD HH:MM
**Plan:** #N - Name (or "No specific plan")
**Branch:** branch-name

## Session Summary
<!-- 2-3 sentences: what was the goal, what was achieved -->


## Changes Made
<!-- Files created/modified with brief description -->
- `path/to/file.py` - What changed


## Current State
<!-- Where exactly did you stop? Be specific. -->
- Working in: `path/to/file.py:123` (function name)
- Test status: X pass, Y fail, Z not written
- Blocking issue: None / Describe blocker


## Context for Next Session
<!-- What does the next instance need to know that isn't in the code/docs? -->
- Design decision: ...
- Edge case found: ...
- Question for user: ...


## Next Steps
<!-- Ordered list of what to do next -->
1. [ ] First thing
2. [ ] Second thing
3. [ ] ...


## Commands to Resume
<!-- Copy-paste commands to get back to working state -->
```bash
git checkout branch-name
pytest tests/test_specific.py -v
# any other setup
```
