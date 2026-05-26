#!/usr/bin/env bash
# publish-v3.1.0.sh — commit + push + tag v3.1.0 from real macOS terminal
# Cowork sandbox can't run git commit/push (file permission on .git/index.lock).
# Run this from regular terminal: `bash scripts/publish-v3.1.0.sh`
#
# Idempotent: safe to re-run if any step fails.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="3.1.0"
TAG="v${VERSION}"
BRANCH="main"

echo "==> shode-house v${VERSION} publish"
echo "    repo: $(git remote get-url origin)"
echo "    branch: $(git branch --show-current)"
echo ""

# 1. Clean stale lock files from sandbox
echo "==> Step 1: clean stale .git/index.lock (if present)"
rm -f .git/index.lock
echo "    ok"
echo ""

# 2. Sanity — run check-index first
echo "==> Step 2: scripts/check-index.sh (must pass)"
if ! bash scripts/check-index.sh > /dev/null 2>&1; then
  echo "    ✗ check-index.sh FAILED — fix invariants before publishing"
  bash scripts/check-index.sh
  exit 1
fi
echo "    ✓ all invariants pass"
echo ""

# 3. Rebuild .plugin (idempotent)
echo "==> Step 3: rebuild shode-house-${TAG}.plugin"
bash scripts/build-plugin.sh
echo ""

# 4. Stage everything (in case user added more)
echo "==> Step 4: stage all changes"
git add -A
echo ""
echo "Staged changes summary:"
git diff --cached --stat | tail -3
echo ""

# 5. Commit (skip if nothing staged)
if git diff --cached --quiet; then
  echo "==> Step 5: nothing to commit (already committed?). Skipping."
else
  echo "==> Step 5: commit v${VERSION}"
  git commit -m "v${VERSION} — Skill Craft Refactor (9arm-inspired)

Major refactor focused on skill quality + lazy-load + token saving.
Keep v3.0 org structure (19 agents in 7 teams) intact.

Highlights:
- Meeting god-skill split: 1316 -> 180 lines thin entry-point + Recite
  Discipline Card + index. 7 new lazy-load skills under
  skills/discipline/. 86% token reduction for entry context.
- Bucket folder lifecycle: workflow/ops/ui/style/discipline/
  in-progress/deprecated. CLAUDE.md repo invariants enforce
  index integrity via scripts/check-index.sh.
- Command consolidation:
  - /init merges /setup-project via --quick flag
  - /design-system merges /spec-only via --stop --estimate
  - 8 -> 6 active + 2 deprecated alias (remove in v3.2)
- 9arm-inspired skill craft applied to all 10 functional skills:
  - 4-section description format [WHAT/AUDIENCE/WHEN/TRIGGER]
  - When-NOT + Required-inputs refuse-without gates (5 heavy skills)
  - Skill composition pointers for textual handoff (5 skills)
- DRY review-checklist skill: /implement Phase 3b + /review reference
  one source-of-truth instead of duplicating Chris 7-dim + Quinn matrix.
- CLAUDE.md repo invariants including Cowork validator constraints
  (<= 200 chars ASCII description hard cap learned from v2.5.1).
- scripts/{list,check,build,publish}-* dev-loop tooling.

Cowork validator fix (matching v2.5.1 pattern):
- plugin.json description: 146 chars ASCII (was 586 + Thai + em-dash)
- marketplace.json plugins[0].description: 73 chars ASCII (was 400+)
- check-index.sh now enforces these caps automatically.

Stats v3.1:
- Skills: 18 (10 functional + 7 split discipline + 1 review-checklist)
- Commands: 6 active + 2 deprecated alias
- Largest SKILL.md: 272 lines (was 1316 for meeting)
- 9arm patterns adopted: 7/7

Inspired by: github.com/thananon/9arm-skills"
fi
echo ""

# 6. Push branch
echo "==> Step 6: push ${BRANCH}"
git push origin "${BRANCH}"
echo ""

# 7. Create annotated tag (skip if exists)
echo "==> Step 7: create tag ${TAG}"
if git tag -l "${TAG}" | grep -q "${TAG}"; then
  echo "    tag ${TAG} already exists locally — skipping creation"
else
  git tag -a "${TAG}" -m "v${VERSION} — Skill Craft Refactor (9arm-inspired)

See CHANGELOG.md for full details.
Inspired by: github.com/thananon/9arm-skills"
  echo "    ✓ tag ${TAG} created"
fi
echo ""

# 8. Push tag
echo "==> Step 8: push tag ${TAG}"
git push origin "${TAG}"
echo ""

echo "==> ✓ v${VERSION} published"
echo "    GitHub: $(git remote get-url origin | sed 's/\\.git$//' )/releases/tag/${TAG}"
echo ""
echo "    Cowork install:"
echo "      /plugin marketplace update shode-house"
echo "      /plugin install shode-house@shode-house"
echo ""
echo "    Or drag-drop: ${REPO_ROOT}/shode-house-${TAG}.plugin"
