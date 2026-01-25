# Plan #198: Shareable Hook Enhancements

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Claude Code hooks in `.claude/hooks/` are gitignored, so improvements like the CWD safety check in `pending-finish.sh` are local-only and don't benefit other users/sessions.

## Context

The `cd /main && bash .claude/pending-finish.sh` bypass was fixed locally by adding a CWD check to the generated `pending-finish.sh`. But since `.claude/` is gitignored, this fix doesn't propagate to other users.

---

## Solution

Move hook templates/scripts to a tracked location and have the setup script install them:

1. Create `meta-process/hooks/` directory for hook templates
2. Move `enforce-make-merge.sh` template logic there
3. Update `scripts/setup_hooks.sh` to copy/symlink from templates
4. Keep `.claude/hooks/` gitignored but generated from tracked templates

---

## Files Affected

- `meta-process/hooks/claude/enforce-make-merge.sh` (modify) - Add CWD safeguard to pending-finish.sh generation
- `meta-process/install.sh` (modify) - Ensure hooks are installed
- `CLAUDE.md` (modify) - Document hook installation
- `docs/architecture/current/execution_model.md` (modify) - Re-verify (no content changes)
- `docs/architecture/current/agents.md` (modify) - Re-verify (no content changes)
- `docs/architecture/current/artifacts_executor.md` (modify) - Re-verify (no content changes)

---

## Implementation

### 1. Create Template Directory

```
meta-process/
  hooks/
    enforce-make-merge.sh  # Template with CWD check in pending-finish.sh generation
    block-worktree-remove.sh
    protect-main.sh
    ... other hooks
```

### 2. Update Setup Script

```bash
# scripts/setup_hooks.sh
HOOKS_DIR=".claude/hooks"
TEMPLATE_DIR="meta-process/hooks"

mkdir -p "$HOOKS_DIR"
for hook in "$TEMPLATE_DIR"/*.sh; do
    cp "$hook" "$HOOKS_DIR/"
    chmod +x "$HOOKS_DIR/$(basename $hook)"
done
```

### 3. Document Installation

Add to CLAUDE.md Quick Reference:
```
### First-Time Setup
bash scripts/setup_hooks.sh  # Install meta-process hooks
```

---

## Acceptance Criteria

- [ ] Hook templates exist in `meta-process/hooks/`
- [ ] `scripts/setup_hooks.sh` installs from templates
- [ ] CWD safeguard in `pending-finish.sh` is in tracked template
- [ ] Fresh clone + setup gets all hook protections
- [ ] CLAUDE.md documents the setup step

---

## Testing

```bash
# Verify hooks are installed correctly
rm -rf .claude/hooks
bash scripts/setup_hooks.sh
ls -la .claude/hooks/  # Should have all hooks
grep -l "CWD safety check" .claude/hooks/*  # Should find the check
```
