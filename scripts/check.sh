#!/usr/bin/env bash
# One-command validation - runs all CI checks locally
# Usage: ./check [--quick]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

QUICK=false
if [[ "$1" == "--quick" ]]; then
    QUICK=true
fi

echo "========================================"
echo "Running local validation checks"
echo "========================================"
echo ""

FAILED=0

# 1. Pytest
echo -e "${YELLOW}[1/6] Running pytest...${NC}"
if pytest tests/ -q --tb=short; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    FAILED=1
fi
echo ""

# 2. Mypy
echo -e "${YELLOW}[2/6] Running mypy...${NC}"
if python -m mypy --strict --ignore-missing-imports --exclude '__pycache__' --no-namespace-packages src/config.py src/world/*.py src/agents/*.py run.py 2>/dev/null; then
    echo -e "${GREEN}✓ Type check passed${NC}"
else
    echo -e "${RED}✗ Type check failed${NC}"
    FAILED=1
fi
echo ""

# 3. Doc-coupling (respects meta-process.yaml strict_doc_coupling setting)
echo -e "${YELLOW}[3/6] Checking doc-code coupling...${NC}"
STRICT_FLAG="--strict"
if python scripts/meta_config.py --get enforcement.strict_doc_coupling 2>/dev/null | grep -qi "false"; then
    STRICT_FLAG=""
fi
if python scripts/check_doc_coupling.py $STRICT_FLAG --weight-aware 2>/dev/null; then
    echo -e "${GREEN}✓ Doc-coupling passed${NC}"
else
    echo -e "${RED}✗ Doc-coupling failed${NC}"
    echo "  Run: python scripts/check_doc_coupling.py --suggest"
    FAILED=1
fi
echo ""

# 4. Plan status sync (with stale plan advisory)
echo -e "${YELLOW}[4/6] Checking plan status sync...${NC}"
if python scripts/sync_plan_status.py --check --warn-stale 14 2>/dev/null; then
    echo -e "${GREEN}✓ Plan status in sync${NC}"
else
    echo -e "${RED}✗ Plan status out of sync${NC}"
    echo "  Run: python scripts/sync_plan_status.py --sync"
    FAILED=1
fi
echo ""

# 5. Meta-process self-test (files + links only, skip slow install test)
echo -e "${YELLOW}[5/6] Running meta-process self-test...${NC}"
if [[ -f "meta-process/scripts/self_test.py" ]]; then
    if python meta-process/scripts/self_test.py --files --links; then
        echo -e "${GREEN}✓ Meta-process self-test passed${NC}"
    else
        echo -e "${RED}✗ Meta-process self-test failed${NC}"
        FAILED=1
    fi
else
    echo -e "${YELLOW}  Skipped (meta-process/scripts/self_test.py not found)${NC}"
fi

# 6. Stale local branch advisory
echo -e "${YELLOW}[6/6] Checking for stale local branches...${NC}"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
STALE_BRANCHES=$(git branch --format='%(refname:short)' | grep -v "^main$" | grep -v "^${CURRENT_BRANCH}$" || true)
if [[ -n "$STALE_BRANCHES" ]]; then
    BRANCH_COUNT=$(echo "$STALE_BRANCHES" | wc -l | tr -d ' ')
    echo -e "${YELLOW}  ⚠ ${BRANCH_COUNT} local branch(es) besides main:${NC}"
    echo "$STALE_BRANCHES" | while read -r branch; do
        LAST_COMMIT=$(git log "$branch" -1 --format="%cr" 2>/dev/null || echo "unknown")
        echo "    - $branch ($LAST_COMMIT)"
    done
    echo -e "${YELLOW}  Run: make branches to check remote status, or delete with: git branch -D <name>${NC}"
else
    echo -e "${GREEN}✓ No stale local branches${NC}"
fi
echo ""

# Advisory: Gap freshness check (non-blocking)
GAPS_FILE="docs/architecture/gaps/GAPS_SUMMARY.yaml"
if [[ -f "$GAPS_FILE" ]]; then
    REFRESHED=$(grep 'refreshed:' "$GAPS_FILE" | head -1 | sed 's/.*refreshed: *//')
    if [[ -n "$REFRESHED" ]]; then
        REFRESH_EPOCH=$(date -d "$REFRESHED" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        DAYS_SINCE=$(( (NOW_EPOCH - REFRESH_EPOCH) / 86400 ))
        if [[ $DAYS_SINCE -gt 30 ]]; then
            echo -e "${YELLOW}⚠ GAPS_SUMMARY.yaml last refreshed ${DAYS_SINCE} days ago (${REFRESHED}). Consider re-running gap analysis.${NC}"
            echo ""
        fi
    fi
fi

# Summary
echo "========================================"
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All checks passed! Ready to push.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix issues before pushing.${NC}"
    exit 1
fi
