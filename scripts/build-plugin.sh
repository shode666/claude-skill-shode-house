#!/usr/bin/env bash
# build-plugin.sh — zip shippable bits into shode-house-v<VERSION>.plugin
# Reads version from .claude-plugin/plugin.json
# Excludes: in-progress/, deprecated/, outputs/, *.plugin (prior versions), .git, .DS_Store
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

VERSION=$(grep -oE '"version":[[:space:]]*"[^"]+"' .claude-plugin/plugin.json | head -1 | sed -E 's/.*"([^"]+)"$/\1/')
[ -n "$VERSION" ] || { echo "ERROR: cannot read version from plugin.json"; exit 1; }

OUT="shode-house-v${VERSION}.plugin"

echo "Building $OUT (version $VERSION) ..."

# Clean prior build of same version
rm -f "$OUT"

zip -r "$OUT" \
  .claude-plugin/ \
  agents/ \
  commands/ \
  skills/workflow/ skills/ops/ skills/ui/ skills/style/ skills/discipline/ \
  references/ \
  docs/ \
  README.md CHANGELOG.md CLAUDE.md \
  -x "*.DS_Store" \
  -x "outputs/*" \
  -x "skills/in-progress/*" \
  -x "skills/deprecated/*" \
  -x "**/.git/*" \
  > /tmp/build-plugin.log 2>&1

SIZE=$(du -h "$OUT" | cut -f1)
COUNT=$(unzip -l "$OUT" | tail -1 | awk '{print $2}')
echo "Built: $OUT ($SIZE, $COUNT files)"
