#!/usr/bin/env bash
# Core scenario set of a checkout, selected by DATA: the major of .claude-plugin/plugin.json `version`
# (bd v7u.4.7 W9 note, router proposal: the 3.17 files stay frozen; the 4.0 set is separate and frozen too).
#   major 3 -> CORE_FILE=eval/scenarios/core-3.17.json (E02..E15, E10b, E1c) + E01 from eval/scenarios/golden.json,
#              both pinned by eval/FREEZE.sha256 (bash eval/check-freeze.sh)
#   4.0.0   -> CORE_FILE=eval/scenarios/core-4.0/core-4.0.json (E01..E15, E10b, E1c in one file), pinned by its own
#              eval/scenarios/core-4.0/FREEZE.sha256 and derived from the 3.17 files (bash eval/scenarios/core-4.0/check-freeze.sh)
#   4.0.1+  -> CORE_FILE=eval/scenarios/core-4.0.1/core-4.0.1.json (the same 17, retired agent ids rewritten to the 6 types), pinned by
#              its own eval/scenarios/core-4.0.1/FREEZE.sha256 and derived from the frozen 4.0 set (bash eval/scenarios/core-4.0.1/check-freeze.sh)
#   any other major, or no readable version -> refused (exit status 3, message on stderr): a new major needs a
#              scenario-set decision, never a silent fallback to an old set.
# Usage (sourced by eval/run-core.sh and eval/run-e01.sh):  . eval/core-set.sh; core_set "$REPO" || exit 3
# Sets CORE_LABEL (3.17 | 4.0 | 4.0.1), CORE_FILE, CORE_E01 (the scenario file holding E01) and CORE_FREEZE (the freeze
# check scripts to run, repo-relative, space separated). `bash eval/core-set.sh [repo]` prints them.
core_set() {
  local repo="$1" major
  # a refusal never leaves a value behind (one from the environment or an earlier call): a caller that went on
  # anyway would read empty names and stop at "cannot read", never score from a stale set (Chris W10a-C6)
  CORE_LABEL="" CORE_FILE="" CORE_E01="" CORE_FREEZE=""
  major="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1], encoding="utf-8"))["version"]; print(int(str(v).split(".")[0]))' \
    "$repo/.claude-plugin/plugin.json" 2>/dev/null)" || { echo "!! core set: no readable version in $repo/.claude-plugin/plugin.json" >&2; return 3; }
  version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$repo/.claude-plugin/plugin.json" 2>/dev/null)"
  case "$major" in
    3) CORE_LABEL=3.17; CORE_FILE="$repo/eval/scenarios/core-3.17.json"; CORE_E01="$repo/eval/scenarios/golden.json"
       CORE_FREEZE="eval/check-freeze.sh" ;;
    4) if [ "$version" = "4.0.0" ]; then
         CORE_LABEL=4.0; CORE_FILE="$repo/eval/scenarios/core-4.0/core-4.0.json"; CORE_E01="$CORE_FILE"
         CORE_FREEZE="eval/check-freeze.sh eval/scenarios/core-4.0/check-freeze.sh"
       else   # 4.0.1 and later 4.x: the 6-type roster (retired 4.0.0 ids rewritten); the 4.0 set stays frozen as history
         CORE_LABEL=4.0.1; CORE_FILE="$repo/eval/scenarios/core-4.0.1/core-4.0.1.json"; CORE_E01="$CORE_FILE"
         CORE_FREEZE="eval/check-freeze.sh eval/scenarios/core-4.0/check-freeze.sh eval/scenarios/core-4.0.1/check-freeze.sh"
       fi ;;
    *) echo "!! core set: plugin major $major has no core scenario set (3 -> core-3.17, 4 -> core-4.0)" >&2; return 3 ;;
  esac
  [ -f "$CORE_FILE" ] || { echo "!! core set: missing $CORE_FILE" >&2; CORE_LABEL="" CORE_FILE="" CORE_E01="" CORE_FREEZE=""; return 3; }
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  core_set "${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}" || exit 3
  printf 'CORE_LABEL=%s\nCORE_FILE=%s\nCORE_E01=%s\nCORE_FREEZE=%s\n' "$CORE_LABEL" "$CORE_FILE" "$CORE_E01" "$CORE_FREEZE"
fi
