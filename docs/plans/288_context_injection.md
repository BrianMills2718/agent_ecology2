# Plan #288: Context Injection for Edit Operations

**Status:** ✅ Complete
**Created:** 2026-02-04
**Branch:** explore-context-provision

## Gap

**Current:** When editing source files, Claude Code receives governance context only *after* reading files (via PostToolUse hook). This context shows doc references but not actual content. Deprecated/forbidden terms from GLOSSARY and CONCEPTUAL_MODEL are not surfaced. Claude can make edits that violate ADR principles without seeing any warning.

**Target:** Before editing source files, Claude should see:
1. Warnings for deprecated/forbidden terms found in the file
2. Relevant ADR principles that govern the file
3. Key glossary terms extracted from the file
4. Conceptual model sections relevant to the code
5. List of docs to check after editing

**Why:** Context provision is broken - "context exists" ≠ "context is used". The exploration in EXPLORATION_NOTES.md demonstrated that:
- CONCEPTUAL_MODEL says "owner" DOES NOT EXIST but code uses it extensively
- Nothing stops edits that violate ADR principles
- Governance hook only triggers on Read, not Edit
- Hook shows doc references, not actual content

## References Reviewed

- `docs/GLOSSARY.md` - Terminology definitions (494 lines)
- `docs/CONCEPTUAL_MODEL.yaml` - Entity definitions including non_existence
- `scripts/relationships.yaml` - Governance and coupling mappings
- `.claude/hooks/inject-governance-context.sh` - Existing PostToolUse hook
- `meta-process/patterns/27_conceptual-modeling.md` - Pattern for conceptual model usage

## Files Affected

| File | Change |
|------|--------|
| `scripts/extract_relevant_context.py` | New - extracts relevant context from GLOSSARY, CONCEPTUAL_MODEL, ADRs |
| `.claude/hooks/inject-edit-context.sh` | New - PreToolUse hook for Edit that injects context |
| `.claude/hooks/inject-governance-context.sh` | Modified - fix worktree path handling bug |
| `.claude/settings.json` | Modified - register new hook |

## Plan

1. ✅ Create `extract_relevant_context.py`:
   - Parse Python files with AST to extract identifiers/terms
   - Match against GLOSSARY entries
   - Match against CONCEPTUAL_MODEL sections (resources, artifacts, etc.)
   - Extract ADR principles from governance mappings
   - Surface WARNINGS for deprecated/forbidden terms

2. ✅ Create `inject-edit-context.sh` PreToolUse hook:
   - Trigger on Edit tool for Python files in src/
   - Call extraction script
   - Inject context as additionalContext before edit

3. ✅ Fix worktree bug in `inject-governance-context.sh`:
   - sed pattern failed on relative paths starting with `worktrees/`
   - Added case for relative worktree paths

4. ✅ Register hook in `.claude/settings.json`

## Testing

Manual testing completed:
- `python scripts/extract_relevant_context.py src/world/ledger.py` → Shows ADR principles, glossary terms, resource model
- `python scripts/extract_relevant_context.py src/world/artifacts.py` → Shows WARNINGS for "owner" and "credits"
- Hook tested via simulated input

## Acceptance Criteria

- [ ] When editing src/world/ledger.py, Claude sees ADR-0002 principle "Scrip cannot go negative"
- [ ] When editing src/world/artifacts.py, Claude sees WARNING about forbidden term "owner"
- [ ] Worktree paths correctly handled in both hooks

## Notes

This plan emerged from an exploration of the context provision problem. The exploration found that:
1. CLAUDE.md provides process context but not domain context
2. Terminology enforcement is non-existent (code uses "owner" despite CONCEPTUAL_MODEL prohibition)
3. Hooks only inject context after Read, not before Edit
4. The "owner" term is used in code comments 50+ times despite being "forbidden"

The solution focuses on **delivery** of existing context, not creating new documentation.
