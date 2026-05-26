#!/usr/bin/env bash
# list-skills.sh — show every SKILL.md with line count + bucket + description first line
# Usage: ./scripts/list-skills.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

printf "%-12s  %-30s  %5s  %s\n" "BUCKET" "SKILL" "LINES" "DESCRIPTION"
printf "%-12s  %-30s  %5s  %s\n" "------" "-----" "-----" "-----------"

for f in skills/*/*/SKILL.md skills/*/SKILL.md; do
  [ -f "$f" ] || continue
  bucket=$(echo "$f" | awk -F/ '{ if (NF==4) print $2; else print "(root)" }')
  name=$(echo "$f" | awk -F/ '{ if (NF==4) print $3; else print $2 }')
  lines=$(wc -l < "$f")
  desc=$(awk '/^description:/{flag=1; sub(/^description:[[:space:]]*\|?[[:space:]]*/,""); if(length($0)) print; next} flag && /^[[:space:]]+[^[:space:]]/{sub(/^[[:space:]]+/,""); print; exit} flag && /^[^[:space:]]/{exit}' "$f" | head -c 80)
  printf "%-12s  %-30s  %5d  %s\n" "$bucket" "$name" "$lines" "$desc"
done
