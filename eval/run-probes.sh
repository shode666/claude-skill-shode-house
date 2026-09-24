#!/usr/bin/env bash
# Routing probes: sequential live runs, every run kept, REPEATS per probe. This script records; it does not judge.
#   bash eval/run-probes.sh [model=sonnet] [out-dir]
#   REPEATS=5                     runs per probe (default 1), round-robin: all ids for r1, then r2, ...
#   PROBE_IDS="P01 P02" | all     default = every kind:"probe" id without `not_applicable` (= all)
#   PLUGIN_REF=baseline-3.17      plugin under test = that git ref (read-only git archive); default = working tree
#   PROBE_FILE=/path/set.json     external scenario set (held-out), never copied into the repo
# layout : <out>/<id>/r<k>/{run.jsonl,run.files,meta.json,score.txt,score.json,tools-seen.txt,prompt.txt,...}
#          <out>/BATCH.json · <out>/SUMMARY.tsv (row per run) · <out>/AGG.tsv (row per probe) · <out>/log.txt
# resume : re-invoke with the SAME out-dir and settings. A run dir whose result is success/error_max_turns is
#          complete: skipped, never overwritten, never retried (a scored FAIL is data). A crashed run (no result)
#          is kept and the slot re-run into the next r<k>.retry<n> (at most MAX_RETRY=1 crash retries per slot).
#          An INFRA error (any other result: 429, credits, error_during_execution, budget) is kept, never scored,
#          does not use up a crash retry, and STOPS the batch at once (exit 5) -- wait for the rate window, then
#          re-invoke the same command. 3 crashes in a row also stop the batch.
#          A new batch refuses an existing directory that is not a matching batch (BATCH.json mismatch).
# guards : PROBE_FILE (held-out) runs only into a git-ignored dir (or outside the repo) -- prompts must not be
#          committable. PLUGIN_REF other than BASE_REF (default baseline-3.17) must pass eval/check-arm-diff.sh.
#          ARM_SCOPE=floor         narrows that check to the dispatch-floor arm (eval/PROBE-GATE-floor.md): only
#          output-styles/oliver.md + its two generated copies may differ. Default (unset) = description-only, as before.
#          The value lands in BATCH.json as arm_diff "<scope>-only:<base>..<after>".
# exit   : 0 = every slot has a scored run (0/1) · 2 = some slot unscorable/incomplete · 3 = refused · 5 = stopped (infra)
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-3.17/probes/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
REPEATS="${REPEATS:-1}"; MAX_RETRY="${MAX_RETRY:-1}"
case "$REPEATS" in ''|*[!0-9]*|0) die "REPEATS must be a positive integer" ;; esac
IDS="${PROBE_IDS:-all}"
ALL_OK="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1],encoding="utf-8"));print(" ".join(s["id"] for s in (d["scenarios"] if isinstance(d,dict) else d) if s.get("kind")=="probe" and not s.get("not_applicable")))' "$SCENARIOS")" || die "cannot read $SCENARIOS"
if [ "$IDS" = all ]; then IDS="$ALL_OK"; fi
for ID in $IDS; do
  case " $ALL_OK " in *" $ID "*) ;; *) die "$ID is not a runnable probe in $SCENARIOS (unknown id or not_applicable)" ;; esac
done
"$REPO/eval/check-freeze.sh" >/dev/null 2>&1; FREEZE_RC=$?
[ "$FREEZE_RC" = 0 ] || [ "${ALLOW_UNFROZEN:-0}" = 1 ] || die "frozen files changed (bash eval/check-freeze.sh); set ALLOW_UNFROZEN=1 only for dry runs"
if [ -n "${PROBE_FILE:-}" ]; then   # held-out prompts end up in prompt.txt / run.jsonl / BATCH.json: keep them uncommittable
  OUT_PARENT="$(mkdir -p "$(dirname "$OUT")" && cd "$(dirname "$OUT")" && pwd -P)" || die "cannot resolve $OUT"
  case "$OUT_PARENT/" in
    "$REPO"/*) git -C "$REPO" check-ignore -q "$OUT_PARENT/$(basename "$OUT")" \
      || die "refuse: PROBE_FILE run into a git-tracked location ($OUT). Use outputs/heldout-3.17/runs/<arm>/ (git-ignored)" ;;
  esac
fi
preflight
BASE_REF="${BASE_REF:-baseline-3.17}"; ARM_DIFF="not-applicable"
case "${ARM_SCOPE:-description}" in description|floor) ;; *) die "ARM_SCOPE must be description (default) or floor" ;; esac
if [ -n "${PLUGIN_REF:-}" ]; then
  BASE_SHA="$(git -C "$REPO" rev-parse --verify "$BASE_REF^{commit}" 2>/dev/null)" || die "BASE_REF $BASE_REF not found (needed to check the arm diff)"
  if [ "$BASE_SHA" = "$PLUGIN_SHA" ]; then ARM_DIFF="baseline:$BASE_SHA"
  else
    ARM_SCOPE="${ARM_SCOPE:-description}" bash "$REPO/eval/check-arm-diff.sh" "$BASE_SHA" "$PLUGIN_SHA" || die "refuse: $PLUGIN_REF differs from $BASE_REF by more than ARM_SCOPE=${ARM_SCOPE:-description} allows (eval/check-arm-diff.sh)"
    ARM_DIFF="${ARM_SCOPE:-description}-only:$BASE_SHA..$PLUGIN_SHA"
  fi
fi

BATCH="$(python3 - "$SCENARIOS" <<PY
import hashlib, json, sys
print(json.dumps({"model": "$MODEL", "plugin_ref": "${PLUGIN_REF:-WORKTREE}", "plugin_sha": "$PLUGIN_SHA",
  "plugin_dirty": "$PLUGIN_DIRTY" == "true", "scenarios": sys.argv[1],
  "scenarios_sha256": hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(), "cli_version": "$CLI_VERSION",
  "spawn_block": "${PROBE_BLOCK_SPAWN:-1}", "frozen": $FREEZE_RC == 0, "arm_diff": "$ARM_DIFF"}, sort_keys=True))
PY
)" || die "cannot build batch identity"
if [ -e "$OUT" ]; then
  [ -f "$OUT/BATCH.json" ] || die "refuse: $OUT exists and is not a probe batch (no BATCH.json)"
  [ "$(cat "$OUT/BATCH.json")" = "$BATCH" ] || die "refuse: $OUT belongs to a different batch (model/plugin/scenarios/CLI differ); use a new directory"
  echo "== resuming batch $OUT"
else
  mkdir -p "$OUT" || die "cannot create $OUT"
  printf '%s\n' "$BATCH" > "$OUT/BATCH.json"
fi
OUT="$(cd "$OUT" && pwd -P)"
exec > >(tee -a "$OUT/log.txt") 2>&1
echo "== $(utc) batch model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} repeats=$REPEATS ids: $IDS"

K=1; STOP=""; CRASH_STREAK=0
while [ "$K" -le "$REPEATS" ] && [ -z "$STOP" ]; do
  for ID in $IDS; do
    SLOT="$OUT/$ID/r$K"; DONE=""; CRASHES=0; TARGET=""; N=0
    while [ "$N" -le 50 ]; do
      if [ "$N" = 0 ]; then CAND="$SLOT"; else CAND="$SLOT.retry$N"; fi
      case "$(run_state "$CAND")" in
        complete) DONE="$CAND"; break ;;
        absent) TARGET="$CAND"; break ;;
        incomplete) CRASHES=$((CRASHES + 1)) ;;
        infra:*) ;;   # kept, not scored, does not count against MAX_RETRY
      esac
      N=$((N + 1))
    done
    if [ -n "$DONE" ]; then echo "-- skip $ID r$K (complete: $DONE)"; continue; fi
    if [ -z "$TARGET" ] || [ "$CRASHES" -gt "$MAX_RETRY" ]; then echo "-- $ID r$K: crashed $CRASHES time(s), retries exhausted; left as is"; continue; fi
    mkdir -p "$OUT/$ID"
    run_one "$ID" "$MODEL" "$TARGET" || true
    case "$(run_state "$TARGET")" in
      infra:*) STOP="INFRA error at $ID r$K ($(run_state "$TARGET"); see $TARGET/run.stderr and the result event). This is rate limit / credits / execution failure, not behaviour: the run is kept, not scored, and the slot will be re-run. Wait for the limit to reset, then re-invoke the SAME command."; break ;;
      incomplete|absent) CRASH_STREAK=$((CRASH_STREAK + 1))
        if [ "$CRASH_STREAK" -ge 3 ]; then STOP="3 runs in a row ended without a result event (last: $TARGET). Check claude login/network, then re-invoke the SAME command."; break; fi ;;
      complete) CRASH_STREAK=0 ;;
    esac
  done
  K=$((K + 1))
done

python3 "$REPO/eval/probe-agg.py" "$OUT"
echo "--- AGG.tsv ($OUT)"; cat "$OUT/AGG.tsv"
MISSING="$(python3 - "$OUT" "$REPEATS" $IDS <<'PY'
import csv, sys
out, repeats, ids = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
rows = list(csv.DictReader(open(out + "/SUMMARY.tsv", encoding="utf-8"), delimiter="\t"))
ok = {(r["id"], r["run"].split(".")[0]) for r in rows if r["exit"] in ("0", "1")}
print(sum(1 for i in ids for k in range(1, repeats + 1) if (i, f"r{k}") not in ok))
PY
)"
if [ -n "$STOP" ]; then echo "!! BATCH STOPPED: $STOP"; echo "SUMMARY probes STOPPED slots_without_scored_run=$MISSING dir=$OUT"; exit 5; fi
echo "SUMMARY probes model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} slots=$(( $(echo $IDS | wc -w) * REPEATS )) slots_without_scored_run=$MISSING dir=$OUT"
[ "$MISSING" = 0 ] || exit 2
exit 0
