#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}       Antigravity Hub • Production APK Builder     ${NC}"
echo -e "${BLUE}====================================================${NC}\n"

# ---------------------------------------------------------
# Step 1: Run Full Test Suite (Backend + Mobile)
# ---------------------------------------------------------
echo -e "${YELLOW}Phase 1: Running Automated Pre-Build Test Validations...${NC}"
"${SCRIPT_DIR}/run_tests.sh"
TEST_STATUS=$?

if [ $TEST_STATUS -ne 0 ]; then
    echo -e "\n${RED}❌ Pre-build tests failed! Refusing to build APK.${NC}"
    exit 1
fi

echo -e "\n${GREEN}✓ All tests passed! Proceeding to Gradle APK compilation.${NC}\n"

# ---------------------------------------------------------
# Step 2: Compile Release APK with Gradle
# ---------------------------------------------------------
echo -e "${YELLOW}Phase 2: Compiling Android Release APK via Gradle...${NC}"
cd "${SCRIPT_DIR}/mobile/android"

./gradlew assembleRelease

APK_OUTPUT="${SCRIPT_DIR}/mobile/android/app/build/outputs/apk/release/app-release.apk"

if [ ! -f "$APK_OUTPUT" ]; then
    echo -e "\n${RED}❌ Error: Gradle finished but release APK was not found at:${NC}"
    echo "  $APK_OUTPUT"
    exit 1
fi

# ---------------------------------------------------------
# Step 3: Copy to Root AntigravityHub.apk & Calculate Checksum
# ---------------------------------------------------------
echo -e "\n${YELLOW}Phase 3: Deploying APK to project root...${NC}"
DEST_APK="${SCRIPT_DIR}/AntigravityHub.apk"
cp "$APK_OUTPUT" "$DEST_APK"

FILE_SIZE=$(du -h "$DEST_APK" | cut -f1)
SHA256=$(sha256sum "$DEST_APK" | cut -d' ' -f1)

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}  ✓ BUILD SUCCESSFUL!${NC}"
echo -e "${GREEN}  Output:    ${DEST_APK}${NC}"
echo -e "${GREEN}  Size:      ${FILE_SIZE}${NC}"
echo -e "${GREEN}  SHA-256:   ${SHA256}${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "${BLUE}Tip: Your phone can download this APK directly over LAN at:${NC}"
echo -e "${BLUE}     http://<YOUR_PC_IP>:8765/download${NC}\n"

exit 0
