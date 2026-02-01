#!/bin/bash
# Create a worktree with mandatory claiming
# Usage:
#   ./scripts/create_worktree.sh                                    # Interactive mode
#   ./scripts/create_worktree.sh --branch NAME --task "desc"        # Non-interactive
#   ./scripts/create_worktree.sh --branch NAME --task "desc" --plan N  # With plan
#
# This script enforces the coordination protocol:
# 1. Prompts for task description and plan number (or accepts via args)
# 2. Claims the work in .claude/active-work.yaml
# 3. Creates the worktree based on latest origin/main
#
# This ensures all CC instances can see what others are working on.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Create a git worktree with mandatory work claiming."
            echo ""
            echo "Options:"
            echo "  --branch NAME   Branch name (required for non-interactive mode)"
            echo "  --task DESC     Task description (required for non-interactive mode)"
            echo "  --plan N        Plan number (optional)"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Without arguments, runs in interactive mode with prompts."
            echo ""
            echo "Examples:"
            echo "  $0                                          # Interactive"
            echo "  $0 --branch fix-bug --task 'Fix the bug'    # Non-interactive"
            echo "  $0 --branch plan-237-cli --task 'Implement Plan 237' --plan 237"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Validate non-interactive mode has required args
if [ "$INTERACTIVE" = false ]; then
    if [ -z "$BRANCH" ]; then
        echo -e "${RED}Error: --branch is required for non-interactive mode${NC}"
        exit 1
    fi
    if [ -z "$TASK" ]; then
        echo -e "${RED}Error: --task is required for non-interactive mode${NC}"
        exit 1
    fi
fi

echo "=== Create Worktree with Claim ==="
echo ""

# Check for existing claims
echo "Current claims:"
python scripts/check_claims.py --list
echo ""

# Plan #136: Check for YOUR open PRs (ones matching your claims)
# Configurable via WARN_OPEN_PRS: warn (default), block, none
WARN_OPEN_PRS=${WARN_OPEN_PRS:-warn}

if [ "$WARN_OPEN_PRS" != "none" ]; then
    # Get list of your claimed branch names
    CLAIMED_BRANCHES=$(python scripts/check_claims.py --list 2>/dev/null | grep -E "^\s+plan-" | awk '{print $1}' || echo "")

    # Check if any of your claimed branches have open PRs
    YOUR_PRS=""
    if [ -n "$CLAIMED_BRANCHES" ]; then
        for branch in $CLAIMED_BRANCHES; do
            PR_INFO=$(gh pr list --state open --head "$branch" --json number,title,headRefName 2>/dev/null || echo "")
            if [ -n "$PR_INFO" ] && [ "$PR_INFO" != "[]" ]; then
                PR_NUM=$(echo "$PR_INFO" | grep -o '"number":[0-9]*' | grep -o '[0-9]*')
                PR_TITLE=$(echo "$PR_INFO" | grep -o '"title":"[^"]*"' | sed 's/"title":"//;s/"$//')
                YOUR_PRS="${YOUR_PRS}  - #${PR_NUM}: ${PR_TITLE} (${branch})\n"
            fi
        done
    fi

    if [ -n "$YOUR_PRS" ]; then
        echo -e "${YELLOW}======================================================================${NC}"
        echo -e "${YELLOW}!! WARNING: YOU HAVE OPEN PRs THAT SHOULD BE MERGED FIRST${NC}"
        echo -e "${YELLOW}======================================================================${NC}"
        echo ""
        echo -e "$YOUR_PRS"
        echo ""
        echo "Merge with: make finish BRANCH=<branch> PR=<number>"
        echo ""

        if [ "$WARN_OPEN_PRS" = "block" ]; then
            echo -e "${RED}BLOCKED: WARN_OPEN_PRS=block prevents creating new worktrees${NC}"
            echo "Set WARN_OPEN_PRS=warn or WARN_OPEN_PRS=none to override"
            exit 1
        elif [ "$INTERACTIVE" = true ]; then
            read -p "Continue creating worktree anyway? (y/N): " PR_RESPONSE
            if [[ ! "$PR_RESPONSE" =~ ^[Yy]$ ]]; then
                echo "Aborting. Merge existing PRs first."
                exit 0
            fi
            echo ""
        else
            echo -e "${YELLOW}Non-interactive mode: continuing despite open PRs${NC}"
            echo ""
        fi
    fi
fi

# Also warn if overall PR queue is deep (original check)
OPEN_PRS=$(gh pr list --state open 2>/dev/null | wc -l || echo "0")
if [ "$OPEN_PRS" -gt 5 ]; then
    echo -e "${YELLOW}Note: $OPEN_PRS total open PRs in repository${NC}"
    echo ""
fi

# Get task description (interactive only)
if [ "$INTERACTIVE" = true ]; then
    read -p "Task description (required): " TASK
    if [ -z "$TASK" ]; then
        echo -e "${RED}Error: Task description is required${NC}"
        exit 1
    fi
fi

# Get plan number (interactive only, already set if non-interactive)
if [ "$INTERACTIVE" = true ]; then
    read -p "Plan number (or press Enter for none): " PLAN
fi

# Generate branch name (interactive only, already set if non-interactive)
if [ "$INTERACTIVE" = true ]; then
    if [ -n "$PLAN" ]; then
        # Suggest branch name based on plan
        PLAN_FILE=$(ls docs/plans/${PLAN}_*.md 2>/dev/null | head -1)
        if [ -n "$PLAN_FILE" ]; then
            SUGGESTED=$(basename "$PLAN_FILE" .md | sed 's/^[0-9]*_/plan-'$PLAN'-/')
            read -p "Branch name [$SUGGESTED]: " BRANCH
            BRANCH=${BRANCH:-$SUGGESTED}
        else
            read -p "Branch name (e.g., plan-$PLAN-feature): " BRANCH
        fi
    else
        read -p "Branch name (e.g., fix-something): " BRANCH
    fi

    if [ -z "$BRANCH" ]; then
        echo -e "${RED}Error: Branch name is required${NC}"
        exit 1
    fi
fi

# Confirm before proceeding (interactive only)
echo ""
echo -e "${YELLOW}Will create:${NC}"
echo "  Task: $TASK"
[ -n "$PLAN" ] && echo "  Plan: #$PLAN"
echo "  Branch: $BRANCH"
echo "  Worktree: worktrees/$BRANCH"
echo ""

if [ "$INTERACTIVE" = true ]; then
    read -p "Proceed? [Y/n]: " CONFIRM
    CONFIRM=${CONFIRM:-Y}

    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Plan #176: Check for conflicts BEFORE creating worktree
# This prevents partial state (worktree without claim or claim without worktree)
echo ""
echo -e "${GREEN}Checking for conflicts...${NC}"
CONFLICT_ARGS=""
if [ -n "$PLAN" ]; then
    CONFLICT_ARGS="--plan $PLAN"
fi
if ! python scripts/check_claims.py --check-conflict $CONFLICT_ARGS 2>/dev/null; then
    echo -e "${RED}Conflict detected. Another instance is working on this plan/feature.${NC}"
    exit 1
fi

# Create the worktree FIRST
echo ""
echo -e "${GREEN}Creating worktree...${NC}"
mkdir -p worktrees
git fetch origin
git worktree add "worktrees/$BRANCH" -b "$BRANCH" origin/main

# Plan #176: Write atomic claim file to worktree
# Claim is stored IN the worktree, not in central YAML
# Deleting worktree = releasing claim (no orphan possible)
echo ""
echo -e "${GREEN}Creating claim...${NC}"
CLAIM_ARGS="--write-claim-file worktrees/$BRANCH --task \"$TASK\" --id $BRANCH"
if [ -n "$PLAN" ]; then
    CLAIM_ARGS="$CLAIM_ARGS --plan $PLAN"
fi
eval python scripts/check_claims.py $CLAIM_ARGS

# Create session marker (Plan #52: prevents premature worktree removal)
# The marker contains the creation timestamp - safe_worktree_remove.py checks
# if it's recent (< 24h) and blocks removal if so
echo "$(date -Iseconds)" > "worktrees/$BRANCH/.claude_session"
echo -e "${GREEN}Created session marker${NC}"

# Create per-worktree context file for CC to track progress
# This helps CC resume after context compaction and documents decisions
mkdir -p "worktrees/$BRANCH/.claude"
PLAN_REF=""
if [ -n "$PLAN" ]; then
    PLAN_FILE=$(ls docs/plans/${PLAN}_*.md 2>/dev/null | head -1)
    if [ -n "$PLAN_FILE" ]; then
        PLAN_REF="docs/plans/$(basename "$PLAN_FILE")"
    fi
fi

cat > "worktrees/$BRANCH/.claude/CONTEXT.md" << CONTEXT_EOF
# Worktree Context: $BRANCH

## Task
$TASK

## Plan Reference
${PLAN_REF:-None (trivial change)}

## Status
- [ ] Implementation started
- [ ] Tests passing
- [ ] Ready for PR

## Progress Notes
<!-- CC: Update this as you work. Helps resume after context compaction. -->


## Decisions Made
<!-- CC: Document key decisions and why. -->


## Discovered Conflicts
<!-- CC: Record plan-reality mismatches found during implementation. See Pattern 28. -->


## Files Changed
<!-- CC: List files you've modified. -->

CONTEXT_EOF
echo -e "${GREEN}Created .claude/CONTEXT.md for tracking progress${NC}"

# Set up shared references symlink (docs/references -> shared folder)
# Check environment variable, then common locations
SHARED_REF="${SHARED_REFERENCES_DIR:-}"
if [ -z "$SHARED_REF" ]; then
    # Try common locations
    for candidate in "$HOME/projects/shared_references" "$HOME/shared_references" "../shared_references"; do
        if [ -d "$candidate" ]; then
            SHARED_REF="$candidate"
            break
        fi
    done
fi

WT_REF="worktrees/$BRANCH/docs/references"
if [ -n "$SHARED_REF" ] && [ -d "$SHARED_REF" ]; then
    rm -rf "$WT_REF" 2>/dev/null || true
    ln -sf "$SHARED_REF" "$WT_REF"
    echo -e "${GREEN}Linked docs/references -> $SHARED_REF${NC}"
fi

echo ""
echo -e "${GREEN}=== Success ===${NC}"
echo ""
echo "Worktree created at: worktrees/$BRANCH"
echo "Based on: latest origin/main"
echo "Context file: worktrees/$BRANCH/.claude/CONTEXT.md"
echo ""
echo "Workflow (run from main, use worktree as path):"
echo "  # Edit files:"
echo "  worktrees/$BRANCH/src/...          # Use paths from main"
echo ""
echo "  # Commit:"
echo "  git -C worktrees/$BRANCH add -A"
echo "  git -C worktrees/$BRANCH commit -m '[Plan #N] ...'"
echo ""
echo "  # Ship:"
echo "  git -C worktrees/$BRANCH push -u origin $BRANCH"
echo "  gh pr create --head $BRANCH --title '...' --body '...'"
echo "  make finish BRANCH=$BRANCH PR=<number>"
