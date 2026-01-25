#!/bin/bash
# Warn if Claude Code session is running from inside a worktree
# This causes problems because:
#   1. If the worktree is deleted, the shell CWD becomes invalid
#   2. CC can't run 'make finish' from inside its own worktree
#   3. Session becomes stuck, requiring user intervention
#
# The correct workflow is:
#   - Start Claude from main repo
#   - Use worktrees as PATHS for file isolation, not as working directories
#   - Edit files using absolute paths: worktrees/plan-X/path/to/file
#
# Exit codes:
#   0 - Always allow (this is a warning, not a block)
#
# Configuration:
#   Controlled by hooks.warn_worktree_cwd in meta-process.yaml

# Check if hook is enabled via config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/check-hook-enabled.sh"
if ! is_hook_enabled "warn_worktree_cwd"; then
    exit 0  # Hook disabled in config
fi

# Only run once per session (check for marker)
MARKER_FILE="/tmp/.claude-worktree-warning-$$"
if [[ -f "$MARKER_FILE" ]]; then
    exit 0
fi

# Get current working directory
CWD=$(pwd 2>/dev/null || echo "")

# Check if CWD is inside a worktree
if [[ "$CWD" == */worktrees/* ]]; then
    # Create marker so we only warn once
    touch "$MARKER_FILE"

    # Extract main directory
    MAIN_DIR=$(echo "$CWD" | sed 's|/worktrees/.*||')
    WORKTREE_NAME=$(basename "$CWD")

    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "⚠️  WARNING: Running from inside a worktree" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "" >&2
    echo "Your session CWD: $CWD" >&2
    echo "" >&2
    echo "This can cause problems:" >&2
    echo "  • If this worktree is deleted, your shell will break" >&2
    echo "  • You can't run 'make finish' from here (hooks will block)" >&2
    echo "  • You'll need user intervention to complete your work" >&2
    echo "" >&2
    echo "RECOMMENDED: Start Claude sessions from main repo instead:" >&2
    echo "  cd $MAIN_DIR" >&2
    echo "  claude" >&2
    echo "" >&2
    echo "Then edit files using paths:" >&2
    echo "  worktrees/$WORKTREE_NAME/path/to/file" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
fi

# Always allow - this is just a warning
exit 0
