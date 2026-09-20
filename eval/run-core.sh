#!/usr/bin/env bash
# v3.17 core matrix: live runs of the core scenarios (E01 from golden.json, E02..E15 + E10b + E1c from
# eval/scenarios/core-3.17.json), sequential, every run kept. This script records; it does not judge.
#   bash eval/run-core.sh [model=sonnet] [out-dir]          (run on the Mac, from anywhere)
#   CORE_IDS="E02 E10b" | all     default all (17 ids)
#   CLAUDE_BIN / PLUGIN_REF / RUN_TIMEOUT_S / MAX_BUDGET_USD: as in eval/run-lib.sh
# layout : <out>/<id>/{run.jsonl,run.files,run.diff,meta.json,score.txt,score.json,tools-seen.txt,prompt.txt,
#          fixture.log,fixture.sha,fixture-core.sha256} · <out>/SUMMARY.tsv (append-only, row per run) · <out>/log.txt
# resume : re-invoke with the SAME out-dir. A complete run (success / error_max_turns) is skipped: never overwritten,
#          never retried (a scored FAIL is data). A crashed run (no result) is kept and the id re-run into
#          <id>.retry<n>. An INFRA result (429, credits, budget, error_during_execution) is kept, never counted,
#          and stops the batch (exit 5): wait, then re-invoke the same command.
# exit   : 0 every id has a scored run (PASS or FAIL) · 2 some id unscorable/incomplete · 3 refused · 5 stopped (infra)
# All run/score/evidence logic is eval/run-lib.sh `run_one` (frozen), reused as is. run_one has no hook for the
# fixture script, so the one call it makes to scripts/eval-fixture.sh is redirected below to
# scripts/eval-fixture-core.sh (which itself calls the frozen script, then adds the scenario's assets).
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
[ -z "${PROBE_FILE:-}" ] || die "PROBE_FILE is for eval/run-probes.sh, not the core matrix"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-3.17/core/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
GOLDEN="$SCENARIOS"; CORE="$REPO/eval/scenarios/core-3.17.json"
[ -f "$CORE" ] || die "missing $CORE"
ALL_IDS="E01 $(python3 -c 'import json,sys;print(" ".join(s["id"] for s in json.load(open(sys.argv[1],encoding="utf-8"))["scenarios"] if s.get("kind")=="core"))' "$CORE")" || die "cannot read $CORE"
IDS="${CORE_IDS:-all}"; [ "$IDS" = all ] && IDS="$ALL_IDS"
for ID in $IDS; do
  case " $ALL_IDS " in *" $ID "*) ;; *) die "$ID is not a core scenario (known: $ALL_IDS)" ;; esac
done
"$REPO/eval/check-freeze.sh" >/dev/null 2>&1 || [ "${ALLOW_UNFROZEN:-0}" = 1 ] \
  || die "frozen files changed (bash eval/check-freeze.sh); set ALLOW_UNFROZEN=1 only for dry runs"
preflight

CORE_ID=""
bash() {   # only run_one's fixture build is redirected; every other `bash` call is untouched
  if [ "${1:-}" = "$REPO/scripts/eval-fixture.sh" ] && [ -n "$CORE_ID" ]; then
    shift; command bash "$REPO/scripts/eval-fixture-core.sh" --scenario "$CORE_ID" "$@"
  else
    command bash "$@"
  fi
}

mkdir -p "$OUT" || die "cannot create $OUT"
OUT="$(cd "$OUT" && pwd -P)"
[ -f "$OUT/SUMMARY.tsv" ] || [ -z "$(ls -A "$OUT")" ] || die "refuse: $OUT exists and is not a core batch (no SUMMARY.tsv)"
[ -f "$OUT/SUMMARY.tsv" ] || printf 'id\trun\tmodel\tverdict\texit\tstate\troute\tseconds\tdir\n' > "$OUT/SUMMARY.tsv"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "== $(utc) core batch model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} ids: $IDS"

UNSCORED=0
for ID in $IDS; do
  TARGET=""; DONE=""; N=0
  while [ "$N" -le 20 ]; do
    if [ "$N" = 0 ]; then CAND="$OUT/$ID"; else CAND="$OUT/$ID.retry$N"; fi
    case "$(run_state "$CAND")" in
      complete) DONE="$CAND"; break ;;
      absent) TARGET="$CAND"; break ;;
    esac
    N=$((N + 1))
  done
  if [ -n "$DONE" ]; then echo "== $ID kept: $DONE is complete (never re-run)"; continue; fi
  [ -n "$TARGET" ] || die "$ID: too many incomplete attempts under $OUT"
  if [ "$ID" = E01 ]; then SCENARIOS="$GOLDEN"; else SCENARIOS="$CORE"; fi
  CORE_ID="$ID"
  run_one "$ID" "$MODEL" "$TARGET"; RC=$?
  CORE_ID=""
  [ "$RC" = 3 ] && die "$ID refused before start"
  [ "$ID" = E01 ] || grep -q "^core fixture $ID ready" "$TARGET/fixture.log" || die "$ID: core fixture was not built (redirect missed)"
  [ -e "$TARGET/fixture-core.sha256" ] || python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' \
    "$REPO/scripts/eval-fixture-core.sh" > "$TARGET/fixture-core.sha256"
  STATE="$(run_state "$TARGET")"
  case "$RC" in 0) VERDICT=PASS ;; 1) VERDICT=FAIL ;; *) VERDICT=UNSCORABLE ;; esac
  case "$STATE" in complete) ;; *) VERDICT="NOT_COUNTED" ;; esac
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$ID" "$(basename "$TARGET")" "$MODEL" "$VERDICT" "$RC" "$STATE" \
    "${FIRST_ROUTE:--}" "${SECONDS_TAKEN:-0}" "$TARGET" >> "$OUT/SUMMARY.tsv"
  case "$STATE" in
    infra:*) echo "!! $ID ended with $STATE: infrastructure, not behaviour. Batch stopped; re-invoke the same command later."; exit 5 ;;
  esac
  { [ "$STATE" = complete ] && [ "$RC" -le 1 ]; } || UNSCORED=$((UNSCORED + 1))
done
echo "== $(utc) core batch done: unscored=$UNSCORED summary=$OUT/SUMMARY.tsv"
[ "$UNSCORED" = 0 ] || exit 2
exit 0
