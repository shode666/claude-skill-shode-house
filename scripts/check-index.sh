#!/usr/bin/env bash
# check-index.sh — enforce CLAUDE.md invariants
# - Every shippable skill must be in plugin.json
# - No in-progress/ or deprecated/ skill in plugin.json
# - No SKILL.md > 300 lines (except thin-entry exception list)
# - Every SKILL.md description must have 4-section markers
# Exits non-zero on violation. Use as pre-commit / CI gate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PLUGIN_JSON=".claude-plugin/plugin.json"
README="README.md"
FAIL=0
SHIPPABLE_BUCKETS=("workflow" "ops" "ui" "style" "discipline")
EXCLUDED_BUCKETS=("in-progress" "deprecated")
THIN_ENTRY_EXCEPTIONS=("meeting")  # may exceed 300 lines if explicitly entry-point
MAX_LINES=300

red()   { printf "\033[0;31m%s\033[0m\n" "$*"; }
green() { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[0;33m%s\033[0m\n" "$*"; }

echo "== 1. Skill size limits (≤ ${MAX_LINES} lines) =="
for f in skills/*/*/SKILL.md; do
  [ -f "$f" ] || continue
  name=$(basename "$(dirname "$f")")
  lines=$(wc -l < "$f")
  if (( lines > MAX_LINES )); then
    if [[ " ${THIN_ENTRY_EXCEPTIONS[*]} " == *" ${name} "* ]]; then
      yellow "  ~ $f: $lines lines (thin-entry exception)"
    else
      red "  ✗ $f: $lines lines > $MAX_LINES — split required"
      FAIL=1
    fi
  else
    green "  ✓ $f: $lines lines"
  fi
done

echo ""
echo "== 2. Excluded buckets not in plugin.json =="
for bucket in "${EXCLUDED_BUCKETS[@]}"; do
  [ -d "skills/$bucket" ] || continue
  for f in skills/$bucket/*/SKILL.md; do
    [ -f "$f" ] || continue
    name=$(basename "$(dirname "$f")")
    if grep -q "\"$name\"" "$PLUGIN_JSON" 2>/dev/null; then
      red "  ✗ '$name' in $bucket/ but listed in $PLUGIN_JSON"
      FAIL=1
    else
      green "  ✓ '$name' in $bucket/ correctly excluded"
    fi
  done
done

echo ""
echo "== 3. Shippable bucket paths listed in plugin.json skills array =="
# v3.1 schema: skills = array of bucket PATHS (string paths); plugin loader auto-discovers
# each <bucket>/<skill-name>/SKILL.md one level deep within listed paths
for bucket in "${SHIPPABLE_BUCKETS[@]}"; do
  [ -d "skills/$bucket" ] || continue
  if grep -qE "\"\\./skills/$bucket/?\"" "$PLUGIN_JSON" 2>/dev/null; then
    skill_count=$(find "skills/$bucket" -name "SKILL.md" | wc -l)
    green "  ✓ '$bucket/' bucket path listed (auto-discovers $skill_count skills)"
  else
    red "  ✗ '$bucket/' bucket path NOT in $PLUGIN_JSON skills array — skills won't load"
    FAIL=1
  fi
done

echo ""
echo "== 4. Cowork validator constraints (description length + ASCII) =="
# History: v2.5.1 + v3.1.0 both failed Cowork "Plugin validation failed" because
# description was too long + non-ASCII. Cowork validator stricter than JSON schema.
# Hard caps: plugin.json description ≤ 200, marketplace plugins[].description ≤ 100, ASCII only.
python3 - <<'PYEOF' || FAIL=1
import json, sys

def check(label, text, limit):
    errs = []
    if len(text) > limit:
        errs.append(f"length {len(text)} > {limit}")
    if not all(ord(c) < 128 for c in text):
        non_ascii = sorted(set(c for c in text if ord(c) >= 128))
        errs.append(f"non-ASCII chars present: {non_ascii}")
    # Specifically forbid em-dash + Thai (most common offenders)
    if '—' in text or '–' in text:
        errs.append("em-dash/en-dash forbidden (use '-' or ':')")
    if any('฀' <= c <= '๿' for c in text):
        errs.append("Thai characters forbidden (move detail to README.md)")
    if errs:
        print(f"\033[0;31m  ✗ {label}: {'; '.join(errs)}\033[0m")
        return 1
    print(f"\033[0;32m  ✓ {label}: {len(text)} chars ASCII (≤ {limit})\033[0m")
    return 0

fail = 0
try:
    p = json.load(open('.claude-plugin/plugin.json'))
    fail += check("plugin.json description", p.get('description', ''), 200)
except Exception as e:
    print(f"\033[0;31m  ✗ plugin.json: {e}\033[0m")
    fail = 1

try:
    m = json.load(open('.claude-plugin/marketplace.json'))
    fail += check("marketplace.json description (top)", m.get('description', ''), 200)
    for i, pl in enumerate(m.get('plugins', [])):
        fail += check(f"marketplace.json plugins[{i}].description", pl.get('description', ''), 100)
except Exception as e:
    print(f"\033[0;31m  ✗ marketplace.json: {e}\033[0m")
    fail = 1

sys.exit(fail)
PYEOF

echo ""
echo "== 5. SKILL.md description format check (4-section: WHAT/AUDIENCE/WHEN/TRIGGER) =="
for f in skills/*/*/SKILL.md; do
  [ -f "$f" ] || continue
  # Extract description block (lines between 'description:' and next top-level YAML key)
  desc=$(awk '/^description:/{flag=1; next} flag && /^[a-z_]+:/{exit} flag' "$f")
  for marker in "WHAT" "AUDIENCE" "WHEN" "TRIGGER"; do
    if ! echo "$desc" | grep -qE "\[${marker}\]"; then
      yellow "  ~ $f: missing [$marker] marker"
    fi
  done
done

echo ""
if [ "$FAIL" -eq 0 ]; then
  green "== All invariants pass =="
else
  red "== Invariants FAILED =="
  exit 1
fi
