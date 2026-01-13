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
