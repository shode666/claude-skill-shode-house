#!/usr/bin/env bash
# 4.0.1 routing-probe battery runner: the P01..P47 prompts mapped to the 6 types (eval/scenarios/battery-4.0.1/). A copy of the
# run-probes.sh logic under a new name; eval/run-probes.sh, eval/run-lib.sh, eval/scenarios/golden.json and every file pinned in
# eval/FREEZE.sha256 stay untouched (they are the 3.17 / 4.0.0 baseline). This script records; it does not judge.
#   bash eval/run-battery-4.0.1.sh [model=sonnet] [out-dir]
#   REPEATS=5                     runs per probe (default 5 = the N of the P01..P47 baseline), round-robin: all ids for r1, then r2, ...
#   PROBE_IDS="P01 P02" | all     default = every probe without `not_applicable` (46; P21 is refused)
#   PLUGIN_REF=<git ref>          plugin under test = that git ref (read-only git archive); default = working tree
#                                 (no arm-diff guard: this battery compares nothing by itself; compare AGG.tsv with the baseline's)
#   PROBE_FILE is not supported (the battery is the pinned file, not an external set)
# layout : <out>/<id>/r<k>/{run.jsonl,run.files,meta.json,score.txt,score.json,tools-seen.txt,prompt.txt,...}; the 7 domain probes also
#          get domain-check.txt (check-domain.py: which domain reference the plan spawn names, requested model tier)
#          <out>/BATCH.json . <out>/SUMMARY.tsv . <out>/AGG.tsv . <out>/log.txt
# resume : as run-probes.sh (same SAME-out-dir rule, crash retry, infra stop, exit codes 0/2/3/5)
# guards : refuses to start unless the old freeze (bash eval/check-freeze.sh) AND the battery freeze
#          (bash eval/scenarios/battery-4.0.1/check-freeze.sh) are green; ALLOW_UNFROZEN=1 only for dry runs.
# owner-only: umask 077 before anything exists (dirs 0700, files 0600); a symlinked out-dir is refused; an existing out-dir is locked
#          down before any run (eval/redact_derived.py lockdown, as eval/run-core.sh): every dir 0700, every file 0600, or exit 4 with
#          nothing changed (symlink / special / hard-linked / foreign entry).
# redact : as eval/run-core.sh, after each run the derived files (tools-seen.txt score.txt score.json meta.json, domain-check.txt),
#          the buffered console output of the run, SUMMARY.tsv and AGG.tsv are redacted in place (eval/redact_derived.py); run.jsonl
#          stays byte-exact (sha256 in redaction.json). Redaction failure = exit 4, no further run. <out>/.redact-pending names the
#          run in flight: the next invocation seals it before anything else. run_one (frozen run-lib.sh) is wrapped, not edited; the
#          descriptor isolation and signal traps of run-core.sh are not replicated (foreground loop).
# exit   : 0 = every slot has a scored run (0/1) . 2 = some slot unscorable/incomplete . 3 = refused . 4 = redaction failed or the
#          out-dir cannot be made owner-only . 5 = stopped (infra)
umask 077   # before any file or directory of the batch exists (SEC-13): raw and derived evidence stay owner-only
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
# run-lib.sh picks golden.json; this runner scores the 4.0.1 battery (prompt paths are repo-relative, as in golden.json)
[ -z "${PROBE_FILE:-}" ] || die "PROBE_FILE is not supported by the 4.0.1 battery runner (use eval/run-probes.sh for an external set)"
BATTERY_DIR="$REPO/eval/scenarios/battery-4.0.1"
SCENARIOS="$BATTERY_DIR/battery-4.0.1.json"; PROMPT_BASE="$REPO"
[ -f "$SCENARIOS" ] || die "missing $SCENARIOS"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-4.0.1/battery/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
REPEATS="${REPEATS:-5}"; MAX_RETRY="${MAX_RETRY:-1}"
case "$REPEATS" in ''|*[!0-9]*|0) die "REPEATS must be a positive integer" ;; esac
IDS="${PROBE_IDS:-all}"
ALL_OK="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1],encoding="utf-8"));print(" ".join(s["id"] for s in (d["scenarios"] if isinstance(d,dict) else d) if s.get("kind")=="probe" and not s.get("not_applicable")))' "$SCENARIOS")" || die "cannot read $SCENARIOS"
if [ "$IDS" = all ]; then IDS="$ALL_OK"; fi
for ID in $IDS; do
  case " $ALL_OK " in *" $ID "*) ;; *) die "$ID is not a runnable probe in $SCENARIOS (unknown id or not_applicable)" ;; esac
done
"$REPO/eval/check-freeze.sh" >/dev/null 2>&1; FREEZE_RC=$?
bash "$BATTERY_DIR/check-freeze.sh" >/dev/null 2>&1 || FREEZE_RC=1
[ "$FREEZE_RC" = 0 ] || [ "${ALLOW_UNFROZEN:-0}" = 1 ] || die "frozen files changed (bash eval/check-freeze.sh; bash eval/scenarios/battery-4.0.1/check-freeze.sh); set ALLOW_UNFROZEN=1 only for dry runs"
preflight
ARM_DIFF="not-applicable"
REDACT="$REPO/eval/redact_derived.py"
redact_fail() { echo "!! STOPPED: redaction failed ($*). Fail-closed: no further run." >&2
                echo "!! Nothing under the out-dir is final; fix the redactor and re-invoke the same command." >&2; exit 4; }
[ -f "$REDACT" ] && [ -f "$REPO/eval/evidence_redact.py" ] || redact_fail "missing eval/redact_derived.py or eval/evidence_redact.py"
python3 "$REDACT" selftest || redact_fail "selftest"

BATCH="$(python3 - "$SCENARIOS" <<PY
import hashlib, json, sys
print(json.dumps({"model": "$MODEL", "plugin_ref": "${PLUGIN_REF:-WORKTREE}", "plugin_sha": "$PLUGIN_SHA",
  "plugin_dirty": "$PLUGIN_DIRTY" == "true", "scenarios": sys.argv[1],
  "scenarios_sha256": hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(), "cli_version": "$CLI_VERSION",
  "spawn_block": "${PROBE_BLOCK_SPAWN:-1}", "frozen": $FREEZE_RC == 0, "arm_diff": "$ARM_DIFF", "battery": "4.0.1"}, sort_keys=True))
PY
)" || die "cannot build batch identity"
[ ! -L "$OUT" ] || die "refuse: $OUT is a symlink"
if [ -e "$OUT" ]; then
  [ -f "$OUT/BATCH.json" ] || die "refuse: $OUT exists and is not a probe batch (no BATCH.json)"
  [ "$(cat "$OUT/BATCH.json")" = "$BATCH" ] || die "refuse: $OUT belongs to a different batch (model/plugin/scenarios/CLI differ); use a new directory"
  echo "== resuming batch $OUT"
else
  mkdir -p "$OUT" || die "cannot create $OUT"
  printf '%s\n' "$BATCH" > "$OUT/BATCH.json"
fi
OUT="$(cd "$OUT" && pwd -P)"
# a batch begun before umask 077 (or touched by hand): every dir -> 0700, every file -> 0600 before any run; a symlink / special /
# hard-linked / foreign entry refuses the batch with nothing changed
python3 "$REDACT" lockdown "$OUT" || { echo "!! STOPPED: the out-dir cannot be made owner-only (reason above). Nothing ran." >&2
  echo "!! Inspect it by hand (ls -laR), or start a NEW out-dir." >&2; exit 4; }
exec > >(tee -a "$OUT/log.txt") 2>&1
PENDING="$OUT/.redact-pending"; PENDOUT="$OUT/.redact-pending.out"
# seal_run <run-dir>: redact the derived files of the run, its domain-check.txt and the buffered console output (prints nothing)
seal_run() {
  python3 "$REDACT" seal "$1" || return 1
  [ ! -e "$1/domain-check.txt" ] || python3 "$REDACT" file "$1/domain-check.txt" || return 1
  [ ! -e "$PENDOUT" ] || python3 "$REDACT" file "$PENDOUT"
}
flush() { [ ! -e "$PENDOUT" ] || { cat "$PENDOUT" && rm -f "$PENDOUT"; }; }
if [ -f "$PENDING" ]; then   # an earlier invocation stopped between run_one and the end of its redaction
  P0="$(head -n 1 "$PENDING")"
  printf '%s\n' "$P0" | grep -Eq '^P[0-9]+/r[0-9]+(\.retry[0-9]+)?$' || redact_fail "unreadable $PENDING"
  echo "== resume: $P0 was interrupted before its redaction finished; redacting it again before anything else"
  seal_run "$OUT/$P0" || redact_fail "$P0"
  rm -f "$PENDING"
fi
if [ -e "$PENDOUT" ]; then python3 "$REDACT" file "$PENDOUT" || redact_fail "$PENDOUT"; echo "== resume: console output of the interrupted run (redacted):"; flush; fi
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
    printf '%s\n' "$ID/$(basename "$TARGET")" > "$PENDING.tmp" && mv -f "$PENDING.tmp" "$PENDING" || redact_fail "cannot write $PENDING"
    run_one "$ID" "$MODEL" "$TARGET" > "$PENDOUT" 2>&1 || true   # console output held back until it is redacted
    if [ -f "$TARGET/run.jsonl" ] && [ -n "$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(next((s.get("domain_4_0_1","") for s in d["scenarios"] if s["id"]==sys.argv[2]),""))' "$SCENARIOS" "$ID")" ]; then
      python3 "$BATTERY_DIR/check-domain.py" "$ID" "$TARGET/run.jsonl" > "$TARGET/domain-check.txt" 2>&1; echo "exit=$?" >> "$TARGET/domain-check.txt"
    fi
    seal_run "$TARGET" || redact_fail "$TARGET"
    rm -f "$PENDING"; flush
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
python3 "$REDACT" file "$OUT/SUMMARY.tsv" && python3 "$REDACT" file "$OUT/AGG.tsv" || redact_fail "SUMMARY.tsv / AGG.tsv"
echo "--- AGG.tsv ($OUT)"; cat "$OUT/AGG.tsv"
MISSING="$(python3 - "$OUT" "$REPEATS" $IDS <<'PY'
import csv, sys
out, repeats, ids = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
rows = list(csv.DictReader(open(out + "/SUMMARY.tsv", encoding="utf-8"), delimiter="\t"))
ok = {(r["id"], r["run"].split(".")[0]) for r in rows if r["exit"] in ("0", "1")}
print(sum(1 for i in ids for k in range(1, repeats + 1) if (i, f"r{k}") not in ok))
PY
)"
if [ -n "$STOP" ]; then echo "!! BATCH STOPPED: $STOP"; echo "SUMMARY battery-4.0.1 STOPPED slots_without_scored_run=$MISSING dir=$OUT"; exit 5; fi
echo "SUMMARY battery-4.0.1 model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} slots=$(( $(echo $IDS | wc -w) * REPEATS )) slots_without_scored_run=$MISSING dir=$OUT"
[ "$MISSING" = 0 ] || exit 2
exit 0
