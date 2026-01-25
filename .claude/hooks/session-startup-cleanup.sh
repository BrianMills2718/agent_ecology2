#!/bin/bash
# Session Startup Cleanup Hook (Plan #206)
#
# Automatically cleans up orphaned claims on session start.
# Only runs once per session using a marker file.
#
# This removes claims where the worktree no longer exists,
# which is safe because if the worktree is gone, the work is abandoned.
#
# Exit codes:
#   0 - Always allow (this is just cleanup, not blocking)
#
# Configuration:
#   Controlled by hooks.session_cleanup in meta-process.yaml

# Check if hook is enabled via config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/check-hook-enabled.sh"
if ! is_hook_enabled "session_cleanup"; then
    exit 0  # Hook disabled in config
fi

# Get the main repo root
MAIN_REPO_ROOT=$(git worktree list 2>/dev/null | head -1 | awk '{print $1}')
if [[ -z "$MAIN_REPO_ROOT" ]]; then
    exit 0  # Not in a git repo
fi

# Session marker - unique per port or PID
SESSION_ID="${CLAUDE_CODE_SSE_PORT:-$$}"
MARKER_FILE="/tmp/claude-cleanup-run-$SESSION_ID"

# Check if already ran this session
if [[ -f "$MARKER_FILE" ]]; then
    # Check if marker is less than 1 hour old (sessions can be long)
    if [[ $(find "$MARKER_FILE" -mmin -60 2>/dev/null) ]]; then
        exit 0  # Already ran recently
    fi
fi

# Create marker file first to prevent race conditions
touch "$MARKER_FILE"

# Run orphaned claim cleanup (non-blocking)
# Use --dry-run first to check, then actually clean if there's something
cd "$MAIN_REPO_ROOT" || exit 0

ORPHANED=$(python scripts/check_claims.py --cleanup-orphaned --dry-run 2>/dev/null | grep -c "Would remove")
if [[ "$ORPHANED" -gt 0 ]]; then
    echo "" >&2
    echo "╔════════════════════════════════════════════════════════════╗" >&2
    echo "║  🧹 Session startup cleanup found $ORPHANED orphaned claim(s)     ║" >&2
    echo "╠════════════════════════════════════════════════════════════╣" >&2
    echo "║  Running: python scripts/check_claims.py --cleanup-orphaned ║" >&2
    echo "╚════════════════════════════════════════════════════════════╝" >&2
    echo "" >&2

    # Actually run the cleanup
    python scripts/check_claims.py --cleanup-orphaned 2>/dev/null
fi

exit 0
