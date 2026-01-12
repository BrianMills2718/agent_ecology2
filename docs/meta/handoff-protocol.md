# Pattern: Handoff Protocol

## Problem

When a Claude Code session ends (via `/clear`, terminal close, or context exhaustion):
- Work in progress is lost
- The next session doesn't know what was happening
- Partially completed tasks get duplicated or abandoned
- Context about blockers and decisions is lost

## Solution

Before ending a session, write a structured handoff file that captures:
- What was done
- Current state (file + line number)
- Blockers and context
- Next steps

## Files

| File | Purpose |
|------|---------|
| `.claude/handoff_template.md` | Template for handoff notes |
| `.claude/handoff.md` | Current handoff (gitignored) |
| `CLAUDE.md` | Documents the protocol |

## Setup

### 1. Create template

```markdown
<!-- .claude/handoff_template.md -->
# Session Handoff

## Session Summary
<!-- What did you accomplish this session? -->

## Changes Made
<!-- List files modified with brief descriptions -->
- `file.py` - Description of change

## Current State
<!-- Where exactly did you leave off? -->
- **File:** `path/to/file.py`
- **Line:** 123
- **Function/Section:** `function_name()`

## Context
<!-- Important decisions, discoveries, or constraints -->

## Blockers
<!-- What's preventing progress? -->
- [ ] Blocker 1
- [ ] Blocker 2

## Next Steps
<!-- What should the next session do? -->
1. Step one
2. Step two

## Commands to Resume
```bash
# Commands to run to continue work
```

## Related
<!-- PRs, issues, plan numbers -->
- Plan #N
- PR #X
```

### 2. Add to .gitignore

```
# Handoff file (session-specific, not committed)
.claude/handoff.md
```

### 3. Document in CLAUDE.md

```markdown
### Before /clear - Handoff Protocol

**CRITICAL:** Before ending a session (running `/clear`, closing terminal, or switching tasks), write a handoff file:

```bash
# Copy template and fill in
cp .claude/handoff_template.md .claude/handoff.md
# Edit .claude/handoff.md with session details
```

The template includes:
- Session summary and changes made
- Current state (file + line number)
- Context and blockers
- Next steps for continuation
- Commands to resume

This enables smooth continuation in the next session.
```

## Usage

### Before ending session

```bash
# Copy template
cp .claude/handoff_template.md .claude/handoff.md

# Edit with session details (Claude does this)
# ... fill in the template ...
```

### Starting new session

```bash
# Check for handoff from previous session
cat .claude/handoff.md

# If exists, read and continue from where left off
```

### After completing handoff work

```bash
# Remove handoff file (work is done)
rm .claude/handoff.md
```

## Template Sections

### Session Summary
Brief description of what was accomplished. Helps next session understand context quickly.

### Changes Made
List of files modified with descriptions. Allows next session to review changes.

### Current State
Precise location in code where work stopped. Include:
- File path
- Line number
- Function or section name

### Context
Important information that isn't obvious from the code:
- Why certain decisions were made
- Constraints discovered
- Dependencies identified

### Blockers
What's preventing progress:
- Missing information
- Bugs encountered
- Waiting on external input

### Next Steps
Ordered list of what to do next. Should be actionable and specific.

### Commands to Resume
Shell commands to run to get back to working state:
- Navigate to correct directory
- Activate environment
- Run specific tests
- Open specific files

## Integration with Claims

Handoff complements the claims system:

| System | Purpose | Persistence |
|--------|---------|-------------|
| Claims | Track who owns what work | Persists in YAML/CLAUDE.md |
| Handoff | Track session state | Temporary, per-session |

When handing off:
1. Don't release claim (work not done)
2. Write handoff file
3. Next session reads handoff, continues work
4. Release claim when work complete

## Customization

### Additional sections

Add project-specific sections to template:
- Test status
- Build status
- Environment variables needed
- Related documentation

### Team handoffs

For human-AI or AI-AI handoffs, add:
- Who handed off
- Timestamp
- Expected resumption time

```markdown
## Handoff Details
- **From:** CC-instance-1
- **Time:** 2026-01-12 08:30 UTC
- **Expected resume:** Within 4 hours
```

## When to Use

**Always use before:**
- Running `/clear`
- Closing terminal
- Switching to different task
- Context window getting full

**Not needed when:**
- Work is fully complete
- PR is merged
- Just taking short break (same session)
