#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   Antigravity Hub • Pre-Build & Pre-Push Test Suite${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# ---------------------------------------------------------
# 1. Backend Python Unit & Integration Tests
# ---------------------------------------------------------
echo -e "${YELLOW}[1/2] Running Backend Test Suite (Python/FastAPI)...${NC}"
cd "${SCRIPT_DIR}/backend"

if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: backend/.venv not found. Run ./run_backend.sh first to set up virtualenv.${NC}"
    exit 1
fi

PYTHONPATH=. .venv/bin/python -W ignore -m unittest discover tests -v
BACKEND_STATUS=$?

if [ $BACKEND_STATUS -ne 0 ]; then
    echo -e "\n${RED}❌ Backend tests failed! Build / Push aborted.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend tests passed cleanly!${NC}\n"

# ---------------------------------------------------------
# 2. Mobile Client Unit Tests
# ---------------------------------------------------------
echo -e "${YELLOW}[2/2] Running Mobile Test Suite (React Native/Node.js)...${NC}"
cd "${SCRIPT_DIR}/mobile"

node --test tests/*.test.js
MOBILE_STATUS=$?

if [ $MOBILE_STATUS -ne 0 ]; then
    echo -e "\n${RED}❌ Mobile tests failed! Build / Push aborted.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Mobile tests passed cleanly!${NC}\n"

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}  ✓ ALL TESTS PASSED (Backend + Mobile)${NC}"
echo -e "${GREEN}  Safe to push to remote and build release APK!${NC}"
echo -e "${GREEN}====================================================${NC}"
exit 0
