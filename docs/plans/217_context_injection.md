# Plan 217: Context Injection for Claude Code

**Status:** Complete
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

Inject relevant context when Claude Code reads governed files. Use Claude Code's PostToolUse hook system to inject `additionalContext` after file reads.

## Implementation (Completed)

### 1. Python script for governance context lookup

Created `scripts/get_governance_context.py`:
- Reads `relationships.yaml` governance section
- Looks up ADR titles from the `adrs` section
- Returns JSON-escaped string with governance context
- Outputs nothing for ungoverned files (clean exit)

### 2. Bash hook for PostToolUse

Created `.claude/hooks/inject-governance-context.sh`:
- Reads JSON input from stdin (tool_input.file_path)
- Normalizes file paths for worktrees
- Runs Python script to get governance context
- Outputs JSON with `hookSpecificOutput.additionalContext`
- Handles edge cases (invalid JSON, missing script, etc.)

### 3. Hook configuration

Added to `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/inject-governance-context.sh",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

### 4. Meta-process configuration

Added to `meta-process.yaml`:
```yaml
hooks:
  inject_governance_context: true  # Can disable if needed
```

## Example Output

When reading `src/world/contracts.py`:
```
This file is governed by ADR-0001 (Everything is an artifact), ADR-0003 (Contracts can do anything). Governance context: Permission checks are the hot path - keep them fast.
Contracts return decisions; kernel applies state changes.
```

## Test Plan (Completed)

### Unit Tests - `tests/unit/test_context_injection.py`
- `test_governed_file_returns_context` - contracts.py returns context
- `test_governed_file_ledger` - ledger.py returns ADR-0001/0002 context
- `test_ungoverned_file_returns_none` - README.md returns None
- `test_nonexistent_file_returns_none` - graceful handling
- `test_context_includes_adr_titles` - titles included

### Integration Tests
- `test_hook_outputs_valid_json_for_governed_file` - valid JSON output
- `test_hook_silent_for_ungoverned_file` - no output
- `test_hook_silent_for_missing_file_path` - graceful handling
- `test_hook_silent_for_invalid_json` - graceful handling

### Configuration Tests
- `test_hook_config_exists` - meta-process.yaml has setting
- `test_hook_enabled_by_default` - enabled by default
- `test_read_hook_configured` - settings.json configured

## Acceptance Criteria

- [x] `get_governance_context.py` returns context for governed files
- [x] Context includes ADR references and titles
- [x] Hook configuration in `.claude/settings.json`
- [x] Configurable via `meta-process.yaml`
- [x] Unit tests pass (12 tests)
- [x] Manual verification that context appears in Claude Code

## Files Created/Modified

- `scripts/get_governance_context.py` - New: context lookup logic
- `.claude/hooks/inject-governance-context.sh` - New: PostToolUse hook
- `.claude/settings.json` - Updated: added Read hook
- `meta-process.yaml` - Updated: added `inject_governance_context` config
- `tests/unit/test_context_injection.py` - New: 12 tests

## Resolved Ambiguities

1. **Hook capabilities**: PostToolUse hooks can inject `additionalContext` via JSON output with `hookSpecificOutput.hookEventName` and `hookSpecificOutput.additionalContext`.

2. **Output format**: Context appears as additional output shown to Claude after the tool result.

3. **Performance**: Python script runs quickly (~50ms). Hook timeout set to 3000ms for safety.

4. **User opt-in**: Configurable via `meta-process.yaml` - enabled by default but can be disabled.
