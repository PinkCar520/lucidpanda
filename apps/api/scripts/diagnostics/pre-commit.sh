#!/bin/bash

# Git pre-commit hook
# Automatically runs security checks before each commit
# To install: cp scripts/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

echo "🔍 Running pre-commit security checks..."
echo ""

# Run the security check script
./scripts/security-check.sh

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Commit blocked due to security issues!"
    echo "Please fix the issues above and try again."
    echo ""
    echo "To bypass this check (NOT RECOMMENDED):"
    echo "  git commit --no-verify"
    exit 1
fi

echo ""
echo "✅ Security checks passed. Proceeding with commit..."
exit 0
