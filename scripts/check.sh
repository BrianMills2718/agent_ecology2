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
echo -e "${YELLOW}[1/5] Running pytest...${NC}"
if pytest tests/ -q --tb=short; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    FAILED=1
fi
echo ""

# 2. Mypy
echo -e "${YELLOW}[2/5] Running mypy...${NC}"
if python -m mypy --strict --ignore-missing-imports --exclude '__pycache__' --no-namespace-packages src/config.py src/world/*.py src/agents/*.py run.py 2>/dev/null; then
    echo -e "${GREEN}✓ Type check passed${NC}"
else
    echo -e "${RED}✗ Type check failed${NC}"
    FAILED=1
fi
echo ""

# 3. Doc-coupling
echo -e "${YELLOW}[3/5] Checking doc-code coupling...${NC}"
if python scripts/check_doc_coupling.py --strict 2>/dev/null; then
    echo -e "${GREEN}✓ Doc-coupling passed${NC}"
else
    echo -e "${RED}✗ Doc-coupling failed${NC}"
    echo "  Run: python scripts/check_doc_coupling.py --suggest"
    FAILED=1
fi
echo ""

# 4. Plan status sync
echo -e "${YELLOW}[4/5] Checking plan status sync...${NC}"
if python scripts/sync_plan_status.py --check 2>/dev/null; then
    echo -e "${GREEN}✓ Plan status in sync${NC}"
else
    echo -e "${RED}✗ Plan status out of sync${NC}"
    echo "  Run: python scripts/sync_plan_status.py --sync"
    FAILED=1
fi
echo ""

# 5. Quick or full claim check
if [[ "$QUICK" == true ]]; then
    echo -e "${YELLOW}[5/5] Skipping claim check (--quick mode)${NC}"
else
    echo -e "${YELLOW}[5/5] Checking for stale claims...${NC}"
    python scripts/check_claims.py --list 2>/dev/null || true
fi
echo ""

# Summary
echo "========================================"
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All checks passed! Ready to push.${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Fix issues before pushing.${NC}"
    exit 1
fi
