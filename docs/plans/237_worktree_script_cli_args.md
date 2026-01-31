# Plan 237: Non-Interactive Worktree Creation

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** None (but blocks Claude Code from using meta-process properly)

---

## Gap

**Current:**
- `scripts/create_worktree.sh` is fully interactive (uses `read -p` prompts)
- Claude Code cannot provide interactive input to scripts
- This forces Claude Code to either bypass the meta-process or ask humans to run commands

**Target:**
- Script accepts command-line arguments as alternative to interactive prompts
- Interactive mode preserved for humans who prefer it
- Claude Code can create worktrees non-interactively while respecting the claim system

**Why High:**
- Claude Code cannot follow the meta-process without this fix
- Current state forces workarounds that defeat the purpose of coordination
- Blocks proper multi-CC coordination

---

## References Reviewed

- `scripts/create_worktree.sh` - Current interactive-only implementation
- `Makefile:worktree` target - Calls the script directly
- `.claude/hooks/block-worktree-remove.sh` - Blocks direct `git worktree add`

---

## Files Affected

- `scripts/create_worktree.sh` (modify) - Add CLI argument parsing

---

## Plan

### Changes Required

Add argument parsing at the top of `create_worktree.sh`:

```bash
#!/bin/bash
# Create a worktree with mandatory claiming
# Usage:
#   ./scripts/create_worktree.sh                    # Interactive mode
#   ./scripts/create_worktree.sh --branch NAME --task "description" [--plan N]  # Non-interactive

set -e

# Parse arguments
BRANCH=""
TASK=""
PLAN=""
INTERACTIVE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH="$2"
            INTERACTIVE=false
            shift 2
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        --plan)
            PLAN="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--branch NAME --task DESC] [--plan N]"
            echo ""
            echo "Options:"
            echo "  --branch NAME   Branch name (required for non-interactive)"
            echo "  --task DESC     Task description (required for non-interactive)"
            echo "  --plan N        Plan number (optional)"
            echo ""
            echo "Without arguments, runs in interactive mode."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate non-interactive mode has required args
if [ "$INTERACTIVE" = false ]; then
    if [ -z "$BRANCH" ] || [ -z "$TASK" ]; then
        echo "Error: --branch and --task are required for non-interactive mode"
        exit 1
    fi
fi
```

Then wrap each `read -p` block in an `if [ "$INTERACTIVE" = true ]` check:

```bash
# Example for task prompt
if [ "$INTERACTIVE" = true ]; then
    read -p "Task description (required): " TASK
    if [ -z "$TASK" ]; then
        echo -e "${RED}Error: Task description is required${NC}"
        exit 1
    fi
fi
```

### Steps

1. Add argument parsing block at top of script
2. Add `--help` option
3. Wrap each interactive prompt in `if [ "$INTERACTIVE" = true ]`
4. Update Makefile to pass through arguments: `make worktree BRANCH=x TASK="y" PLAN=z`
5. Test both interactive and non-interactive modes

---

## Required Tests

| Test | What It Verifies |
|------|------------------|
| Manual: `make worktree` | Interactive mode still works |
| Manual: `./scripts/create_worktree.sh --branch test-cli --task "Test task"` | Non-interactive works |
| Manual: `./scripts/create_worktree.sh --branch test-cli --task "Test" --plan 237` | Plan argument works |
| Manual: `./scripts/create_worktree.sh --branch test-cli` | Fails without --task |

---

## Verification

- [ ] Interactive mode works unchanged for humans
- [ ] Non-interactive mode creates worktree + claim correctly
- [ ] `--help` shows usage
- [ ] Missing required args in non-interactive mode fails with clear error
- [ ] Makefile passes arguments through correctly

---

## Notes

This is a meta-process fix that unblocks Claude Code from properly participating in the coordination system. Without this, Claude Code must either:
1. Ask humans to run interactive commands (breaks autonomy)
2. Bypass the meta-process (defeats coordination purpose)

Neither is acceptable for a well-functioning multi-CC environment.
