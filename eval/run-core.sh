#!/usr/bin/env bash
# Core matrix: live runs of the core scenarios, sequential, every run kept. This script records; it does not judge.
# The set follows the plugin major (eval/core-set.sh): 3.x = E01 from golden.json + E02..E15, E10b, E1c from
# eval/scenarios/core-3.17.json (frozen); 4.x = all 17 from eval/scenarios/core-4.0/core-4.0.json (its own freeze).
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
#          · 4 stopped: redaction failed (fail-closed) · 129/130/143 interrupted (HUP/INT/TERM)
# redact : (UD U23 OD-2 A+) umask 077 for everything this batch writes (dirs 0700, files 0600). After run_one, the
#          derived files of the run (tools-seen.txt, score.txt, score.json, meta.json) are redacted in place,
#          atomically, by eval/redact_derived.py (eval/evidence_redact.py rules); run.jsonl stays byte-exact (its
#          sha256 is recorded in <run>/redaction.json and checked) and local-only, as do run.files/run.diff/run.stderr.
#          run_one's console output is buffered in <out>/.redact-pending.out and printed only after redaction; the
#          SUMMARY.tsv row and every line built from run text pass through the redactor first. Any redaction failure
#          stops the batch with exit 4: no further run, no row, no summary line.
# isolate: run_one runs as a background job whose stdout/stderr is the buffer and which holds no other descriptor of
#          the runner (no console, no log.txt): nothing it starts (claude, the model's commands, git, the scorer) can
#          write past the redactor through an inherited descriptor (Sentinel final F3). That is all it covers: a process
#          of the same user can still open /dev/tty, or write a file under the out-dir by its path. The runner waits for
#          it; FIRST_ROUTE / SECONDS_TAKEN are read back from the run's meta.json after the redaction.
# interrupt: <out>/.redact-pending names the run in flight from before run_one until its redaction has succeeded.
#          INT/TERM/HUP, to the runner or to its whole process group -> the run in flight is stopped (the job and its
#          direct children get TERM), best-effort redaction of that run, a "NOT final" line on the console (straight
#          into log.txt when the console is already gone: SIGPIPE is ignored), exit 129/130/143, marker kept. The
#          next invocation with the same out-dir (also after a kill -9) redacts that run again before anything else,
#          clears the marker and prints the redacted buffered output; no SUMMARY row is backfilled (as for any crash, a
#          complete run is then "kept", an incomplete one re-runs into <id>.retry<n>). A run dir without
#          redaction.json, or named in .redact-pending, is not final: never read or paste from it.
# All run/score/evidence logic is eval/run-lib.sh `run_one` (frozen), reused as is. run_one has no hook for the
# fixture script, so the one call it makes to scripts/eval-fixture.sh is redirected below to
# scripts/eval-fixture-core.sh (which itself calls the frozen script, then adds the scenario's assets).
umask 077   # before any file or directory of the batch exists (OD-2 A+): raw and derived evidence stay owner-only
. "$(dirname "${BASH_SOURCE[0]}")/run-lib.sh"
. "$(dirname "${BASH_SOURCE[0]}")/core-set.sh"
[ -z "${PROBE_FILE:-}" ] || die "PROBE_FILE is for eval/run-probes.sh, not the core matrix"
core_set "$REPO" || die "no core scenario set for this plugin version (eval/core-set.sh)"
MODEL="${1:-sonnet}"
OUT="${2:-$REPO/outputs/eval-$CORE_LABEL/core/$MODEL-$(date -u +%Y%m%dT%H%M%SZ)}"
GOLDEN="$CORE_E01"; CORE="$CORE_FILE"
CORE_IDS_IN="$(python3 -c 'import json,sys;print(" ".join(s["id"] for s in json.load(open(sys.argv[1],encoding="utf-8"))["scenarios"] if s.get("kind")=="core"))' "$CORE")" || die "cannot read $CORE"
case " $CORE_IDS_IN " in *" E01 "*) ALL_IDS="$CORE_IDS_IN" ;; *) ALL_IDS="E01 $CORE_IDS_IN" ;; esac
IDS="${CORE_IDS:-all}"; [ "$IDS" = all ] && IDS="$ALL_IDS"
for ID in $IDS; do
  case " $ALL_IDS " in *" $ID "*) ;; *) die "$ID is not a core scenario (known: $ALL_IDS)" ;; esac
done
for FZ in $CORE_FREEZE; do
  bash "$REPO/$FZ" >/dev/null 2>&1 || [ "${ALLOW_UNFROZEN:-0}" = 1 ] \
    || die "frozen files changed (bash $FZ); set ALLOW_UNFROZEN=1 only for dry runs"
done
preflight
REDACT="$REPO/eval/redact_derived.py"
redact_fail() { echo "!! STOPPED: redaction failed ($*). Fail-closed: no further run, no SUMMARY row, no summary line." >&2
                echo "!! Nothing under the out-dir is final; fix the redactor and re-invoke the same command." >&2; exit 4; }
[ -f "$REDACT" ] && [ -f "$REPO/eval/evidence_redact.py" ] || redact_fail "missing eval/redact_derived.py or eval/evidence_redact.py"
python3 "$REDACT" selftest || redact_fail "selftest"

CORE_ID=""
# The bash on PATH, by path: run_one runs as a job (see "isolate"), and bash 3.2 runs `command bash ...` in a function of
# a job with exec and no fork, so the job itself would become the fixture script and run_one would end there with 0.
BASH_BIN="$(type -P bash)" || BASH_BIN="$BASH"
bash() {   # only run_one's fixture build is redirected; every other `bash` call is untouched
  if [ "${1:-}" = "$REPO/scripts/eval-fixture.sh" ] && [ -n "$CORE_ID" ]; then
    shift; "$BASH_BIN" "$REPO/scripts/eval-fixture-core.sh" --scenario "$CORE_ID" "$@"
  else
    "$BASH_BIN" "$@"
  fi
}

mkdir -p "$OUT" || die "cannot create $OUT"
OUT="$(cd "$OUT" && pwd -P)"
[ -f "$OUT/SUMMARY.tsv" ] || [ -z "$(ls -A "$OUT")" ] || die "refuse: $OUT exists and is not a core batch (no SUMMARY.tsv)"
[ -f "$OUT/SUMMARY.tsv" ] || printf 'id\trun\tmodel\tverdict\texit\tstate\troute\tseconds\tdir\n' > "$OUT/SUMMARY.tsv"
chmod 700 "$OUT" && chmod 600 "$OUT/SUMMARY.tsv" || die "cannot restrict $OUT to its owner"   # a batch begun before umask 077
[ ! -e "$OUT/log.txt" ] || chmod 600 "$OUT/log.txt" || die "cannot restrict $OUT/log.txt to its owner"
exec > >(tee -a "$OUT/log.txt") 2>&1   # the console + log; run_one's job never holds it (see "isolate")
echo "== $(utc) core batch set=$CORE_LABEL ($CORE) model=$MODEL plugin=${PLUGIN_REF:-WORKTREE}@${PLUGIN_SHA:0:7} ids: $IDS"

PENDING="$OUT/.redact-pending" PENDOUT="$OUT/.redact-pending.out"
# say <text>: a console/log line built from run text, redacted first (a redactor failure stops the batch)
say() { local line; line="$(printf '%s\n' "$*" | python3 "$REDACT" text)" || redact_fail "console line"; printf '%s\n' "$line"; }
# seal <run-dir>: redact the run's derived files and its buffered console output (prints nothing)
seal() { python3 "$REDACT" seal "$1" && { [ ! -e "$PENDOUT" ] || python3 "$REDACT" file "$PENDOUT"; }; }
# flush: print the (already redacted) buffered console output of the last run, then drop the buffer
flush() { [ ! -e "$PENDOUT" ] || { cat "$PENDOUT" && rm -f "$PENDOUT"; }; }
pending_target() {   # the run named in .redact-pending: one plain name, a direct child of $OUT (never a path)
  local name; name="$(head -n 1 "$PENDING")" || return 1
  case "$name" in ""|.|..|*/*) return 1 ;; esac
  printf '%s\n' "$OUT/$name"
}
RUN_PID=""
stop_run() {   # stop the run_one job in flight: frozen first (it starts nothing new), then its children, then itself
  [ -n "$RUN_PID" ] || return 0
  kill -STOP "$RUN_PID" 2>/dev/null; pkill -TERM -P "$RUN_PID" 2>/dev/null
  kill -TERM "$RUN_PID" 2>/dev/null; kill -CONT "$RUN_PID" 2>/dev/null; wait "$RUN_PID" 2>/dev/null; RUN_PID=""
}
# notice <text>: to the console; when that pipe is gone (TERM/HUP to the whole group also ends tee), into log.txt
notice() { printf '%s\n' "$1" 2>/dev/null || printf '%s\n' "$1" >> "$OUT/log.txt"; }
on_signal() {   # $1 name, $2 exit status. Stop the run, redact first, report second (the console may be gone).
  trap - INT TERM HUP; trap '' PIPE   # a write to a dead console must not turn the exit into SIGPIPE (Chris L-A)
  stop_run
  if [ -f "$PENDING" ]; then
    local t; t="$(pending_target)" || t=""
    if [ -n "$t" ] && seal "$t" >/dev/null 2>&1; then
      notice "!! interrupted ($1): $t is NOT final (derived files redacted, no SUMMARY row). Re-invoke the same command to finish."
    else
      notice "!! interrupted ($1): ${t:-the run in flight} is NOT final and its derived files may be UNREDACTED. Re-invoke the same command before reading or pasting anything from it."
    fi
  else
    notice "!! interrupted ($1)"
  fi
  exit "$2"
}
trap 'on_signal HUP 129' HUP; trap 'on_signal INT 130' INT; trap 'on_signal TERM 143' TERM
if [ -f "$PENDING" ]; then   # an earlier invocation stopped between run_one and the end of its redaction
  T0="$(pending_target)" || redact_fail "unreadable $PENDING"
  echo "== resume: $T0 was interrupted before its redaction finished; redacting it again before anything else"
  seal "$T0" || redact_fail "$T0"
  rm -f "$PENDING"
fi
if [ -e "$PENDOUT" ]; then   # buffered console output of an interrupted run: redact (again), then print it
  python3 "$REDACT" file "$PENDOUT" || redact_fail "$PENDOUT"
  echo "== resume: console output of the interrupted run (redacted):"; flush
fi

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
  if [ "$ID" = E01 ]; then SCENARIOS="$GOLDEN"; else SCENARIOS="$CORE"; fi   # 4.x: both are core-4.0.json
  CORE_ID="$ID"
  printf '%s\n' "$(basename "$TARGET")" > "$PENDING.tmp" && mv -f "$PENDING.tmp" "$PENDING" || redact_fail "cannot write $PENDING"
  echo "== $(utc) $ID -> $TARGET (its console output is printed after redaction)"
  RUN_T0=$SECONDS
  run_one "$ID" "$MODEL" "$TARGET" > "$PENDOUT" 2>&1 &   # console output held back until it is redacted ("isolate")
  RUN_PID=$!; wait "$RUN_PID"; RC=$?; RUN_PID=""
  CORE_ID=""
  seal "$TARGET" || redact_fail "$TARGET"
  rm -f "$PENDING"; flush
  # run_one ran in its own job: its route and duration come from the (now redacted) meta.json it wrote
  FIRST_ROUTE="$(python3 -c 'import json,sys;m=json.load(open(sys.argv[1]));print(m.get("route") or "-")' "$TARGET/meta.json" 2>/dev/null || echo '?')"
  SECONDS_TAKEN="$(python3 -c 'import json,sys;print(int(json.load(open(sys.argv[1]))["seconds"]))' "$TARGET/meta.json" 2>/dev/null || echo $((SECONDS - RUN_T0)))"
  [ "$RC" = 3 ] && die "$ID refused before start"
  [ "$ID" = E01 ] || grep -q "^core fixture $ID ready" "$TARGET/fixture.log" || die "$ID: core fixture was not built (redirect missed)"
  [ -e "$TARGET/fixture-core.sha256" ] || python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' \
    "$REPO/scripts/eval-fixture-core.sh" > "$TARGET/fixture-core.sha256"
  STATE="$(run_state "$TARGET")"
  case "$RC" in 0) VERDICT=PASS ;; 1) VERDICT=FAIL ;; *) VERDICT=UNSCORABLE ;; esac
  case "$STATE" in complete) ;; *) VERDICT="NOT_COUNTED" ;; esac
  ROW="$(printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$ID" "$(basename "$TARGET")" "$MODEL" "$VERDICT" "$RC" "$STATE" \
    "${FIRST_ROUTE:--}" "${SECONDS_TAKEN:-0}" "$TARGET" | python3 "$REDACT" text)" || redact_fail "SUMMARY row of $TARGET"
  printf '%s\n' "$ROW" >> "$OUT/SUMMARY.tsv"
  case "$STATE" in
    infra:*) say "!! $ID ended with $STATE: infrastructure, not behaviour. Batch stopped; re-invoke the same command later."; exit 5 ;;
  esac
  { [ "$STATE" = complete ] && [ "$RC" -le 1 ]; } || UNSCORED=$((UNSCORED + 1))
done
echo "== $(utc) core batch done: unscored=$UNSCORED summary=$OUT/SUMMARY.tsv"
[ "$UNSCORED" = 0 ] || exit 2
exit 0
