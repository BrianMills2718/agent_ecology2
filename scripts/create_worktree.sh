#!/bin/bash
# Create a worktree with mandatory claiming
# Usage: ./scripts/create_worktree.sh
#
# This script enforces the coordination protocol:
# 1. Prompts for task description and plan number
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
        else
            read -p "Continue creating worktree anyway? (y/N): " PR_RESPONSE
            if [[ ! "$PR_RESPONSE" =~ ^[Yy]$ ]]; then
                echo "Aborting. Merge existing PRs first."
                exit 0
            fi
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

# Get task description
read -p "Task description (required): " TASK
if [ -z "$TASK" ]; then
    echo -e "${RED}Error: Task description is required${NC}"
    exit 1
fi

# Get plan number (optional)
read -p "Plan number (or press Enter for none): " PLAN

# Generate branch name
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

# Confirm before proceeding
echo ""
echo -e "${YELLOW}Will create:${NC}"
echo "  Task: $TASK"
[ -n "$PLAN" ] && echo "  Plan: #$PLAN"
echo "  Branch: $BRANCH"
echo "  Worktree: worktrees/$BRANCH"
echo ""
read -p "Proceed? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-Y}

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Claim the work first (before creating worktree)
echo ""
echo -e "${GREEN}Claiming work...${NC}"
if [ -n "$PLAN" ]; then
    python scripts/check_claims.py --claim --task "$TASK" --plan "$PLAN"
else
    python scripts/check_claims.py --claim --task "$TASK"
fi

# Create the worktree
echo ""
echo -e "${GREEN}Creating worktree...${NC}"
mkdir -p worktrees
git fetch origin
git worktree add "worktrees/$BRANCH" -b "$BRANCH" origin/main

# Create session marker (Plan #52: prevents premature worktree removal)
# The marker contains the creation timestamp - safe_worktree_remove.py checks
# if it's recent (< 24h) and blocks removal if so
echo "$(date -Iseconds)" > "worktrees/$BRANCH/.claude_session"
echo -e "${GREEN}Created session marker${NC}"

# Set up shared references symlink (docs/references -> shared folder)
SHARED_REF="/home/brian/projects/shared_references"
WT_REF="worktrees/$BRANCH/docs/references"
if [ -d "$SHARED_REF" ]; then
    rm -rf "$WT_REF" 2>/dev/null || true
    ln -sf "$SHARED_REF" "$WT_REF"
    echo -e "${GREEN}Linked docs/references -> shared folder${NC}"
fi

echo ""
echo -e "${GREEN}=== Success ===${NC}"
echo ""
echo "Worktree created at: worktrees/$BRANCH"
echo "Based on: latest origin/main"
echo ""
echo "Next steps:"
echo "  cd worktrees/$BRANCH && claude"
echo ""
echo "When done:"
echo "  make release                    # Release claim (validates tests)"
echo "  make pr-ready                   # Rebase and push"
echo "  make pr                         # Create PR"
echo "  git worktree remove worktrees/$BRANCH"
