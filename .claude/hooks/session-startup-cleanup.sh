#!/bin/bash
# Session Startup Cleanup Hook (Plan #206)
#
# Automatically cleans up orphaned claims and merged worktrees on session start.
# Only runs once per session using a marker file.
#
# Two cleanup passes:
#   1. Orphaned claims: claims where the worktree no longer exists
#   2. Merged worktrees: worktrees whose branches were merged/deleted on remote
#
# This catches worktrees left behind when PRs are merged outside `make finish`
# (e.g., via GitHub UI or `make merge`).
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

# Run cleanup from main repo root (non-blocking)
cd "$MAIN_REPO_ROOT" || exit 0

# 1. Clean orphaned claims (claims where worktree no longer exists)
ORPHANED=$(python scripts/check_claims.py --cleanup-orphaned --dry-run 2>/dev/null | grep -c "Would remove")
if [[ "$ORPHANED" -gt 0 ]]; then
    echo "" >&2
    echo "🧹 Cleaning $ORPHANED orphaned claim(s)..." >&2
    python scripts/check_claims.py --cleanup-orphaned 2>/dev/null
fi

# 2. Clean merged worktrees (worktrees whose branches were merged/deleted on remote)
MERGED=$(python scripts/cleanup_orphaned_worktrees.py 2>/dev/null | grep -c "branch deleted from remote\|branch merged")
if [[ "$MERGED" -gt 0 ]]; then
    echo "" >&2
    echo "🧹 Cleaning $MERGED merged worktree(s)..." >&2
    python scripts/cleanup_orphaned_worktrees.py --auto 2>/dev/null
fi

exit 0
