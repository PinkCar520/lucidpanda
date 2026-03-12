#!/bin/bash

# AlphaSignal Security Check Script
# Run this before committing to ensure no sensitive data is exposed

echo "🔒 Running security checks..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

# Check 1: .env file should not be tracked
echo -n "Checking .env file... "
if git ls-files --error-unmatch .env 2>/dev/null; then
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ .env file is tracked by Git!"
    echo "  Run: git rm --cached .env"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}OK${NC}"
fi

# Check 2: .gitignore should exist
echo -n "Checking .gitignore... "
if [ ! -f .gitignore ]; then
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ .gitignore file missing!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}OK${NC}"
fi

# Check 3: Database files should not be tracked
echo -n "Checking database files... "
if git ls-files | grep -q "\.db$"; then
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ Database files are tracked by Git!"
    echo "  Run: git rm --cached *.db"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}OK${NC}"
fi

# Check 4: Check for hardcoded API keys in code (actual values, not variable names)
echo -n "Checking for hardcoded secrets... "
if git grep -E "(api_key|API_KEY|password|PASSWORD).*=.*['\"][A-Za-z0-9]{20,}" -- '*.py' '*.ts' '*.tsx' '*.js' | grep -v "settings\." | grep -v "process\.env" | grep -v "your_.*_here" 2>/dev/null; then
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ Possible hardcoded API keys found!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}OK${NC}"
fi

# Check 5: .env.example should exist
echo -n "Checking .env.example... "
if [ ! -f .env.example ]; then
    echo -e "${YELLOW}WARNING${NC}"
    echo "  ⚠️  .env.example file missing (recommended)"
else
    echo -e "${GREEN}OK${NC}"
fi

# Check 6: Verify .env is in .gitignore
echo -n "Checking .gitignore rules... "
if [ -f .gitignore ] && grep -q "^\.env$" .gitignore; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "  ❌ .env not properly ignored in .gitignore!"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ All security checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $ISSUES_FOUND security issue(s)!${NC}"
    echo ""
    echo "Please fix the issues above before committing."
    exit 1
fi
