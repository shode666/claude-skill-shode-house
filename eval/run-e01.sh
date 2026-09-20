#!/usr/bin/env bash
# E-run-path-gate (FR-E-4): one live E01 run, scored end to end.
#   bash eval/run-e01.sh [model=sonnet] [out-dir]      (run on the Mac, from anywhere)
# default out-dir: outputs/eval-3.17/E01/<model>-<UTC timestamp>/   (must not exist)
# exit = scorer exit: 0 PASS · 1 FAIL · 2 UNSCORABLE · 3 refused before start
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-3.17/E01/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
[ -e "$OUT" ] && die "refuse: $OUT already exists"
preflight
run_one E01 "$MODEL" "$OUT"; RC=$?
[ "$RC" = 3 ] && exit 3
echo "--- tools-seen.txt"; cat "$OUT/tools-seen.txt"
echo "--- score.txt";      cat "$OUT/score.txt"
echo "SUMMARY E01 model=$MODEL score_exit=$RC dir=$OUT"
exit "$RC"
