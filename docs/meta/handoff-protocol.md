# Pattern: Handoff Protocol

## Problem

AI coding assistants lose all context when:
- Session ends (`/clear`, terminal close)
- Context window fills up (auto-summarization)
- User switches to different task

The next session starts from scratch. Without handoff:
- Work gets duplicated
- Context gets re-discovered slowly
- Decisions get forgotten
- Momentum is lost

## Solution

Before ending a session, write a handoff file capturing:
1. What was done
2. Current state (exact location)
3. Context that isn't in code/docs
4. Next steps
5. Commands to resume

## Files

| File | Purpose |
|------|---------|
| `.claude/handoff_template.md` | Template to copy |
| `.claude/handoff.md` | Current handoff (gitignored) |

## Setup

### 1. Create template

```markdown
# Session Handoff

**Date:** YYYY-MM-DD HH:MM
**Plan:** #N - Name (or "No specific plan")
**Branch:** branch-name

## Session Summary
<!-- 2-3 sentences: what was the goal, what was achieved -->


## Changes Made
<!-- Files modified with brief description -->
- `path/to/file.py` - What changed


## Current State
<!-- Where exactly did you stop? -->
- Working in: `path/to/file.py:123` (function name)
- Test status: X pass, Y fail
- Blocking issue: None / Describe


## Context for Next Session
<!-- What isn't captured in code/docs? -->
- Design decision: ...
- Edge case found: ...


## Next Steps
<!-- Ordered list -->
1. [ ] First thing
2. [ ] Second thing


## Commands to Resume
```bash
git checkout branch-name
pytest tests/test_specific.py -v
```
```

### 2. Add to .gitignore

```gitignore
# Handoff files (session-specific, not committed)
.claude/handoff.md
```

### 3. Document in CLAUDE.md

```markdown
### Before /clear - Handoff Protocol

**CRITICAL:** Before ending a session, write a handoff file:

```bash
cp .claude/handoff_template.md .claude/handoff.md
# Edit with session details
```
```

## Usage

### Ending a session

```bash
# 1. Copy template
cp .claude/handoff_template.md .claude/handoff.md

# 2. Fill in sections:
#    - Session Summary
#    - Changes Made
#    - Current State
#    - Context for Next Session
#    - Next Steps
#    - Commands to Resume

# 3. Then safe to /clear or close terminal
```

### Starting a session

```bash
# 1. Check for handoff
cat .claude/handoff.md 2>/dev/null || echo "No handoff"

# 2. If exists, review and resume from where left off

# 3. Delete after resuming (or keep for reference)
rm .claude/handoff.md
```

### AI assistant prompts

**Before ending:**
> "Before I clear context, let me write a handoff file so the next session can continue smoothly."

**When starting:**
> "Let me check for a handoff file from the previous session."

## Handoff Quality Checklist

### Essential

- [ ] **Current State** is specific (file:line, function name)
- [ ] **Next Steps** are actionable (not vague)
- [ ] **Commands to Resume** actually work

### Good to Have

- [ ] **Context** captures non-obvious insights
- [ ] **Changes Made** helps verify nothing was lost
- [ ] **Blocking Issue** is clear if present

## Customization

### Minimal handoff (quick tasks)

```markdown
# Handoff

Branch: `feature-x`
Stopped at: `src/module.py:45` - halfway through `process_data()`
Next: Finish function, add tests
Resume: `git checkout feature-x && pytest tests/test_module.py`
```

### Detailed handoff (complex work)

Use full template with all sections filled.

### Team handoff (human-to-human)

Add:
```markdown
## Questions for Reviewer
- Should we use approach A or B for X?
- Is the test coverage sufficient?

## Risks
- Migration might break Y
- Performance not tested at scale
```

### Auto-handoff (tooling)

```python
# In your AI assistant hooks
def on_session_end():
    """Auto-generate handoff from git state."""
    branch = get_current_branch()
    changes = get_uncommitted_changes()
    # Generate handoff.md
```

## Limitations

- **Manual process** - Requires discipline to write before ending
- **Can go stale** - If session doesn't end cleanly, handoff may be outdated
- **Not a substitute for docs** - Handoffs are ephemeral, docs are permanent
- **Context loss** - Some nuance always lost in summarization

## When to Skip

| Situation | Skip? | Why |
|-----------|-------|-----|
| Work fully committed & merged | Yes | Nothing to hand off |
| Quick question answered | Yes | No ongoing work |
| Context auto-summarized | No | Write handoff of what you remember |
| Interrupted unexpectedly | Try | Write what you can recall |

## Integration with Other Patterns

### With Claim System

```markdown
## Session Summary
Claimed Plan #3, completed steps 1-2.

## Current State
Claim still active in CLAUDE.md Active Work table.
```

### With Plan Workflow

```markdown
## Next Steps
1. [ ] Complete step 3 of Plan #3
2. [ ] Update plan status to Complete
3. [ ] Release claim
```

## See Also

- [Claim system pattern](claim-system.md) - Track who's working on what
- [CLAUDE.md authoring pattern](claude-md-authoring.md) - Permanent context
- [Plan workflow pattern](plan-workflow.md) - Structured task tracking
