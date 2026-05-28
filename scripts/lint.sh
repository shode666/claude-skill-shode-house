#!/usr/bin/env bash
# lint.sh — comprehensive pre-publish gate (8 checks)
# Run automatically by scripts/publish-*.sh. Exits non-zero on any failure.
#
# Catches bugs that check-index.sh doesn't:
# - YAML parse errors in frontmatter (e.g., argument-hint: [a | b] [c] [d] → 3 flow sequences)
# - Stale path references after bucket migration
# - SKILL name vs folder mismatch
# - Cross-skill refs pointing to non-existent skills
# - Zip vs disk staleness
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

red()   { printf "\033[0;31m%s\033[0m\n" "$*"; }
green() { printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[0;33m%s\033[0m\n" "$*"; }

FAIL=0

echo "==============================================================="
echo "  shode-house lint — pre-publish gate (8 checks)"
echo "==============================================================="
echo ""

# [1/8] JSON syntax
echo "[1/8] JSON syntax"
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  if python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
    green "  ✓ $f"
  else
    red "  ✗ $f — INVALID JSON"
    python3 -c "import json; json.load(open('$f'))" 2>&1 | tail -2
    FAIL=1
  fi
done
echo ""

# [2/8] SKILL.md YAML + name + description
echo "[2/8] SKILL.md frontmatter (YAML + name + description string)"
bad=0
for f in $(find skills -name "SKILL.md" 2>/dev/null | sort); do
  if ! python3 -c "
import yaml, sys
content = open('$f').read()
if not content.startswith('---'):
    print('  ✗ $f: missing frontmatter'); sys.exit(1)
parts = content.split('---', 2)
try:
    fm = yaml.safe_load(parts[1])
    assert 'name' in fm, 'name missing'
    assert 'description' in fm, 'description missing'
    assert isinstance(fm['description'], str), f\"description type={type(fm['description']).__name__}, must be str\"
except Exception as e:
    print(f'  ✗ $f: {e}'); sys.exit(1)
" 2>&1; then
    bad=1; FAIL=1
  fi
done
if [ $bad -eq 0 ]; then
  count=$(find skills -name "SKILL.md" | wc -l)
  green "  ✓ ${count}/${count} SKILL.md valid"
fi
echo ""

# [3/8] Command .md frontmatter (description + string argument-hint)
echo "[3/8] Command .md frontmatter (YAML + description + string argument-hint)"
bad=0
for f in commands/*.md; do
  if ! python3 -c "
import yaml, sys
fm = yaml.safe_load(open('$f').read().split('---', 2)[1])
assert isinstance(fm.get('description', ''), str), 'description not string'
if 'argument-hint' in fm:
    assert isinstance(fm['argument-hint'], str), f\"argument-hint type={type(fm['argument-hint']).__name__}, must be str (quote it!)\"
" 2>&1 | grep -v '^$' >&2; then
    :
  fi
  python3 -c "
import yaml
fm = yaml.safe_load(open('$f').read().split('---', 2)[1])
assert isinstance(fm.get('description', ''), str)
if 'argument-hint' in fm:
    assert isinstance(fm['argument-hint'], str), 'list-type argument-hint'
" 2>/dev/null || { red "  ✗ $f — quote argument-hint as string"; bad=1; FAIL=1; }
done
if [ $bad -eq 0 ]; then
  count=$(ls commands/*.md | wc -l)
  green "  ✓ ${count}/${count} commands valid"
fi
echo ""

# [4/8] Agent .md frontmatter (name + description)
echo "[4/8] Agent .md frontmatter (YAML + name + description)"
bad=0
for f in agents/*.md; do
  python3 -c "
import yaml
fm = yaml.safe_load(open('$f').read().split('---', 2)[1])
assert 'name' in fm and 'description' in fm
" 2>/dev/null || { red "  ✗ $f"; bad=1; FAIL=1; }
done
if [ $bad -eq 0 ]; then
  count=$(ls agents/*.md | wc -l)
  green "  ✓ ${count}/${count} agents valid"
fi
echo ""

# [5/8] SKILL name == folder name
echo "[5/8] SKILL frontmatter 'name' matches folder name"
bad=0
for f in $(find skills -name "SKILL.md"); do
  folder=$(basename "$(dirname "$f")")
  fm_name=$(python3 -c "import yaml; print(yaml.safe_load(open('$f').read().split('---', 2)[1])['name'])" 2>/dev/null)
  [ "$folder" = "$fm_name" ] || { red "  ✗ folder='$folder' frontmatter name='$fm_name' in $f"; bad=1; FAIL=1; }
done
[ $bad -eq 0 ] && green "  ✓ all SKILL names match folder"
echo ""

# [6/8] Skill cross-refs in commands+README+CLAUDE resolve
echo "[6/8] Skill cross-references resolve (commands + README + CLAUDE)"
python3 <<'PYEOF' || FAIL=1
import re, os, glob, sys
refs_files = glob.glob('commands/*.md') + ['README.md', 'CLAUDE.md']
skill_dirs = {os.path.basename(os.path.dirname(p)) for p in glob.glob('skills/*/*/SKILL.md')}
referenced = set()
for f in refs_files:
    if not os.path.exists(f): continue
    content = open(f).read()
    for m in re.finditer(r'`(meeting|dev-gate|automate-test|diagnose|incident|slo|secure|ui-test|web-q|caveman|review-checklist|shode-house-[a-z]+)`', content):
        referenced.add(m.group(1))
missing = referenced - skill_dirs
if missing:
    print(f"  \033[0;31m✗ Referenced but missing: {missing}\033[0m")
    sys.exit(1)
print(f"  \033[0;32m✓ {len(referenced)} skills referenced, all resolve\033[0m")
PYEOF
echo ""

# [7/8] Path refs in README+CLAUDE resolve (CHANGELOG skipped — history doc)
echo "[7/8] Path refs in README+CLAUDE resolve (CHANGELOG skipped)"
python3 <<'PYEOF' || FAIL=1
import re, os, sys
ok = True
for f in ['README.md', 'CLAUDE.md']:
    if not os.path.exists(f): continue
    paths = re.findall(r'`(skills/[a-z\-/]+(?:/SKILL\.md)?|scripts/[a-z\-]+\.sh|commands/[a-z\-]+\.md|agents/[a-z\-]+\.md)`', open(f).read())
    for p in set(paths):
        if not os.path.exists(p):
            print(f"  \033[0;31m✗ {f}: broken {p!r}\033[0m")
            ok = False
if not ok: sys.exit(1)
print("  \033[0;32m✓ All path references resolve\033[0m")
PYEOF
echo ""

# [8/8] check-index.sh (Cowork constraints + skill size + bucket discipline)
echo "[8/8] CLAUDE.md invariants (size + Cowork caps + bucket lifecycle)"
if bash scripts/check-index.sh > /tmp/check-index.out 2>&1; then
  green "  ✓ all invariants pass"
else
  red "  ✗ check-index.sh FAILED:"
  tail -20 /tmp/check-index.out | sed 's/^/    /'
  FAIL=1
fi
echo ""

echo "==============================================================="
if [ "$FAIL" -eq 0 ]; then
  green "  ✅ ALL 8 LINT CHECKS PASS — safe to publish"
  exit 0
else
  red "  ❌ LINT FAILED — fix issues before publish"
  exit 1
fi
