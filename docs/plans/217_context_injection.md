# Plan 217: Context Injection for Claude Code

**Status:** Planned
**Phase:** 2a of 5 (Meta-Process Improvements)
**Depends on:** Plan #215 (Unified Documentation Graph) - Complete
**Blocked by:** None (can be done in parallel with Plan #218)

## Problem

Claude Code doesn't internalize knowledge like humans. When editing a governed file like `contracts.py`, Claude doesn't automatically know:
- Which ADRs govern this code
- What design decisions were made and why
- What invariants must be preserved

Currently this context exists in `relationships.yaml` but isn't surfaced at the right moment.

## Solution

Inject relevant context when Claude Code reads governed files. Use Claude Code's hook system to intercept file reads and append context from `relationships.yaml`.

## Implementation

### 1. Create context injection script

```python
# scripts/inject_context.py
"""Inject governance context for file reads."""

import sys
import yaml
from pathlib import Path

def get_context_for_file(file_path: str) -> str | None:
    """Get governance context for a file from relationships.yaml."""
    relationships_path = Path("scripts/relationships.yaml")
    if not relationships_path.exists():
        return None

    with open(relationships_path) as f:
        data = yaml.safe_load(f)

    # Check governance entries
    for entry in data.get("governance", []):
        if entry.get("source") == file_path:
            adrs = entry.get("adrs", [])
            context = entry.get("context", "")
            if adrs or context:
                lines = ["# Governance Context"]
                if adrs:
                    lines.append(f"# ADRs: {', '.join(f'ADR-{n:04d}' for n in adrs)}")
                if context:
                    for line in context.strip().split('\n'):
                        lines.append(f"# {line}")
                return '\n'.join(lines)

    return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        context = get_context_for_file(sys.argv[1])
        if context:
            print(context)
```

### 2. Configure Claude Code hook

In `.claude/settings.json` or user settings:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read",
        "command": "python scripts/inject_context.py \"$TOOL_INPUT_file_path\""
      }
    ]
  }
}
```

**AMBIGUITY:** Need to verify exact hook format and capabilities. Claude Code hooks documentation should be consulted.

### 3. Alternative: CLAUDE.md injection

If hooks don't support this pattern, alternative approach:
- Script that updates per-directory CLAUDE.md files with governance context
- Run as part of CI or git hooks
- Less dynamic but more reliable

```python
# scripts/inject_claude_md_context.py
"""Update CLAUDE.md files with governance context."""

def update_claude_md_for_directory(dir_path: Path):
    """Add governance context section to directory's CLAUDE.md."""
    # Find all governed files in this directory
    # Generate context section
    # Append/update in CLAUDE.md
```

### 4. Per-access injection for long sessions

For long Claude Code sessions where session-start injection isn't enough:
- Hook fires on each file read
- Context appears in tool output
- Claude sees governance context when it matters

## Test Plan

### Unit Tests
```python
# tests/unit/test_context_injection.py

def test_get_context_for_governed_file():
    """Governed files return context with ADRs"""

def test_get_context_for_ungoverned_file():
    """Ungoverned files return None"""

def test_context_format():
    """Context is formatted as comments"""

def test_multiple_adrs():
    """Files governed by multiple ADRs list all"""
```

### Integration Tests
```python
def test_hook_integration():
    """Hook fires and injects context on file read"""
    # AMBIGUITY: May need manual testing if hooks hard to automate

def test_claude_md_injection():
    """CLAUDE.md files updated with governance context"""
```

## Acceptance Criteria

- [ ] `inject_context.py` returns context for governed files
- [ ] Context includes ADR references and description
- [ ] Hook configuration documented
- [ ] Alternative CLAUDE.md approach implemented as fallback
- [ ] Unit tests pass
- [ ] Manual verification that context appears in Claude Code

## Files to Create/Modify

- `scripts/inject_context.py` - New: context injection logic
- `.claude/settings.json` - Hook configuration
- `scripts/inject_claude_md_context.py` - New: CLAUDE.md updater (fallback)
- `tests/unit/test_context_injection.py` - New test file
- `CLAUDE.md` - Document the feature

## Ambiguities

1. **Hook capabilities**: Need to verify Claude Code hook system supports this pattern. The exact hook format (`PostToolUse`, `Read` matcher, etc.) may differ from documented.

2. **Output format**: How does hook output appear to Claude? Is it appended to tool result? Shown separately? Need to test.

3. **Performance**: Will running Python script on every file read add noticeable latency? May need caching.

4. **Long sessions**: If hooks don't work, CLAUDE.md approach provides less dynamic but reliable alternative. Trade-off: stale context vs no context.

5. **User opt-in**: Should this be opt-in or opt-out? Relates to Plan #218 (configurable weight).
