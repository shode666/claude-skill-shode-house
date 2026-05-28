#!/usr/bin/env bash
# publish.sh — version-agnostic publish script (commit + push + tag)
# Reads VERSION from .claude-plugin/plugin.json automatically.
# Cowork sandbox can't run git commit/push — run from real macOS terminal.
#
# Idempotent: safe to re-run if any step fails.
# Replaces: publish-v3.1.0.sh (deprecated — kept for reference)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION=$(grep -oE '"version":[[:space:]]*"[^"]+"' .claude-plugin/plugin.json | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
[ -n "$VERSION" ] || { echo "ERROR: cannot read version from plugin.json"; exit 1; }
TAG="v${VERSION}"
BRANCH="${BRANCH:-main}"

echo "==> shode-house ${TAG} publish"
echo "    repo:    $(git remote get-url origin)"
echo "    branch:  $(git branch --show-current)"
echo "    version: ${VERSION} (from plugin.json)"
echo ""

# Step 1: Clean stale lock files from sandbox
echo "==> Step 1: clean stale .git/index.lock (if present)"
rm -f .git/index.lock
echo "    ok"
echo ""

# Step 2: Comprehensive lint (8 checks) — block publish if fail
echo "==> Step 2: scripts/lint.sh (8 pre-publish checks)"
if ! bash scripts/lint.sh; then
  echo ""
  echo "    ✗ LINT FAILED — fix issues above before publishing"
  exit 1
fi
echo ""

# Step 3: Rebuild .plugin (idempotent)
echo "==> Step 3: rebuild shode-house-${TAG}.plugin"
bash scripts/build-plugin.sh
echo ""

# Step 4: Stage everything
echo "==> Step 4: stage all changes"
git add -A
echo ""
echo "Staged changes summary:"
git diff --cached --stat | tail -3
echo ""

# Step 5: Commit (skip if nothing staged)
if git diff --cached --quiet; then
  echo "==> Step 5: nothing to commit (already committed?). Skipping."
else
  # Extract latest CHANGELOG entry for this version as commit body
  COMMIT_BODY=$(awk -v ver="${VERSION}" '
    $0 ~ "^## \\[" ver "\\]" {flag=1; next}
    /^## \[/ && flag {exit}
    flag {print}
  ' CHANGELOG.md | head -50)

  echo "==> Step 5: commit ${TAG}"
  git commit -m "${TAG} — see CHANGELOG.md

${COMMIT_BODY}

See full CHANGELOG.md for details."
fi
echo ""

# Step 6: Push branch
echo "==> Step 6: push ${BRANCH}"
git push origin "${BRANCH}"
echo ""

# Step 7: Create annotated tag (skip if exists)
echo "==> Step 7: create tag ${TAG}"
if git tag -l "${TAG}" | grep -q "${TAG}"; then
  echo "    tag ${TAG} already exists locally — skipping creation"
else
  git tag -a "${TAG}" -m "${TAG} — see CHANGELOG.md for details"
  echo "    ✓ tag ${TAG} created"
fi
echo ""

# Step 8: Push tag
echo "==> Step 8: push tag ${TAG}"
git push origin "${TAG}"
echo ""

echo "==> ✓ ${TAG} published"
echo "    GitHub: $(git remote get-url origin | sed 's/\.git$//')/releases/tag/${TAG}"
echo ""
echo "    Cowork install/update:"
echo "      /plugin marketplace update shode-house"
echo "      /plugin install shode-house@shode-house"
echo ""
echo "    Or drag-drop: ${REPO_ROOT}/shode-house-${TAG}.plugin"
