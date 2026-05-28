#!/usr/bin/env bash
# setup-precommit.sh — install pre-commit hook for shode-house contributors
# One-time setup. Run after fresh clone.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> shode-house — pre-commit setup"
echo ""

# 1. Verify pre-commit installed
if ! command -v pre-commit > /dev/null 2>&1; then
  echo "  pre-commit not found. Installing..."
  if command -v brew > /dev/null 2>&1; then
    brew install pre-commit
  elif command -v pip > /dev/null 2>&1; then
    pip install pre-commit
  else
    echo "  ✗ Neither brew nor pip found. Install manually: https://pre-commit.com/#install"
    exit 1
  fi
fi
echo "  ✓ pre-commit: $(pre-commit --version)"

# 2. Install git hook
echo ""
echo "==> Installing git pre-commit hook"
pre-commit install
echo "  ✓ hook installed (.git/hooks/pre-commit)"

# 3. Run all hooks once to verify clean state
echo ""
echo "==> Running pre-commit on all files (first pass)"
if pre-commit run --all-files; then
  echo ""
  echo "  ✅ All hooks pass — repo is clean"
else
  echo ""
  echo "  ⚠ Some hooks reported issues. Review output above + fix before next commit."
  echo "    Re-run: pre-commit run --all-files"
  exit 1
fi

echo ""
echo "==> Setup complete"
echo ""
echo "Now every 'git commit' will run:"
echo "  - check-yaml / check-json / EOF + whitespace fixers"
echo "  - gitleaks (secret scan)"
echo "  - yamllint"
echo "  - shellcheck (scripts/*.sh)"
echo "  - shode-house lint.sh (8 plugin-specific checks)"
echo ""
echo "To bypass (NOT recommended): git commit --no-verify"
echo "Better: fix the issue or document in bd why it's intentional"
