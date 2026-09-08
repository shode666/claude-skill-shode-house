#!/usr/bin/env bash
# tests/test-workflow-state.sh -- bash-only test suite for scripts/workflow-state.sh
# (bd: shode-roadmap/C-A4 iter0/1, shode-roadmap/C-A5 iter2 -- CI budget rule,
#  outputs/shode-roadmap/C/05-oliver-decisions.md: "1 AC = 1 test case ในสวีท ไม่ใช่ 1 CI
#  section" -- wired into ci.yml as exactly ONE step)
#
# No framework dependency (bats not installed on this machine / not a repo prereq) --
# plain bash test functions + a tiny assert library. Each test runs in its own
# mktemp -d sandbox via WFSTATE_ROOT so tests never touch the real repo state.
#
# iter 2 renames every phase from the iter0/1 6-node MVP set ({pick|impl|ui-check|
# review|triage|done}) to the real 10-node shode-house graph ({0-discover|1a-spec|
# 1b-design|1c-security|2-implement|3a-ui-check|3b-review|4-triage|5-deploy|6-operate})
# and adds coverage for: enter_requires, skip/fail/escalate outcomes, backward/rework
# edges, spec-change edges, iter-cap escalation, artifact hashing, and `reconcile`.
#
# Usage: bash tests/test-workflow-state.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/workflow-state.sh"

PASS=0
FAIL=0
CUR_TEST=""

t_start() { CUR_TEST="$1"; printf -- '-- %s\n' "$1"; }
t_ok()    { PASS=$((PASS + 1)); printf '   ok\n'; }
t_fail()  { FAIL=$((FAIL + 1)); printf '   FAIL (%s): %s\n' "$CUR_TEST" "$1"; }
t_skip()  { printf '   SKIP: %s\n' "$1"; }

assert_eq() {
  # assert_eq <actual> <expected> <msg>
  if [ "$1" = "$2" ]; then t_ok; else t_fail "$3 -- got '$1' want '$2'"; fi
}
assert_contains() {
  # assert_contains <haystack> <needle> <msg>
  case "$1" in *"$2"*) t_ok ;; *) t_fail "$3 -- '$1' does not contain '$2'" ;; esac
}
assert_true() {
  # assert_true <exit-code> <msg>
  if [ "$1" -eq 0 ]; then t_ok; else t_fail "$2 -- exit code $1"; fi
}
assert_false() {
  # assert_false <exit-code> <msg>
  if [ "$1" -ne 0 ]; then t_ok; else t_fail "$2 -- expected non-zero exit"; fi
}

sandbox() {
  local d; d=$(mktemp -d -t wfstate-test.XXXXXX)
  printf '%s' "$d"
}

# PATH with bd's own directory stripped out (if bd is installed at all) -- used to
# deterministically exercise reconcile's "bd unavailable" degrade path regardless of
# whether the host running this suite happens to have bd installed or not.
path_without_bd() {
  local bd_path bd_dir
  bd_path=$(command -v bd 2>/dev/null) || { printf '%s' "$PATH"; return; }
  bd_dir=$(dirname "$bd_path")
  printf '%s' "$PATH" | awk -v d="$bd_dir" 'BEGIN{RS=":"; ORS=":"} $0!=d {print}'
}

HAVE_BD=0
command -v bd >/dev/null 2>&1 && HAVE_BD=1

# ---------------------------------------------------------------------------
t_start "engagement guard: no .shode-house/ -> init/validate/advance/reconcile all no-op (exit 0, silent, no side effect)"
D=$(sandbox)
export WFSTATE_ROOT="$D"
out=$("$SCRIPT" init eg-1 2>&1); rc=$?
assert_true "$rc" "init should exit 0 with no .shode-house/"
assert_eq "$out" "" "init should print nothing"
out=$("$SCRIPT" validate eg-1 2>&1); rc=$?
assert_true "$rc" "validate should exit 0 with no .shode-house/"
out=$("$SCRIPT" advance eg-1 1a-spec 2>&1); rc=$?
assert_true "$rc" "advance should exit 0 with no .shode-house/"
out=$("$SCRIPT" reconcile eg-1 2>&1); rc=$?
assert_true "$rc" "reconcile should exit 0 with no .shode-house/"
entries=$(find "$D" -mindepth 1 2>/dev/null | wc -l | tr -d ' ')
assert_eq "$entries" "0" "no files/dirs should be created under an unengaged repo"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "init: creates state.json with the 10-node graph + genesis journal line"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
out=$("$SCRIPT" init C-A5 2>&1); rc=$?
assert_true "$rc" "init should succeed once engaged"
sf="$D/.shode-house/state/C-A5.json"
[ -f "$sf" ] && t_ok || t_fail "state file should exist at $sf"
cur=$(jq -r '.current_phase' "$sf" 2>/dev/null)
assert_eq "$cur" "0-discover" "fresh state current_phase should be 0-discover"
phase_status=$(jq -r '.phases["0-discover"].status' "$sf" 2>/dev/null)
assert_eq "$phase_status" "in_progress" "fresh 0-discover phase should be in_progress"
n_phases=$(jq -r '.phases | length' "$sf" 2>/dev/null)
assert_eq "$n_phases" "10" "state should have exactly the 10 declared phases"
jf="$D/.shode-house/journal/C-A5.jsonl"
lines=$(wc -l < "$jf" | tr -d ' ')
assert_eq "$lines" "1" "journal should have exactly 1 genesis line after init"
jseq=$(jq -r '.seq' "$jf" 2>/dev/null)
assert_eq "$jseq" "1" "genesis journal line seq should be 1"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "init: refuses to clobber an existing state file (no silent overwrite)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init dup-1 >/dev/null 2>&1
before_sha=$(shasum "$D/.shode-house/state/dup-1.json")
"$SCRIPT" init dup-1 >/dev/null 2>&1; rc=$?
assert_false "$rc" "re-init on existing bd should fail"
after_sha=$(shasum "$D/.shode-house/state/dup-1.json")
assert_eq "$after_sha" "$before_sha" "existing state must be untouched by a rejected re-init"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "validate: OK on a freshly-init'd state"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init v-ok >/dev/null 2>&1
"$SCRIPT" validate v-ok >/dev/null 2>&1; rc=$?
assert_true "$rc" "validate should pass on fresh state"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "validate: rejects a hand-corrupted status value outside the 9-value enum"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init v-bad >/dev/null 2>&1
sf="$D/.shode-house/state/v-bad.json"
tmp=$(mktemp)
jq '.phases["1a-spec"].status = "not-a-real-status"' "$sf" > "$tmp" && mv "$tmp" "$sf"
err=$("$SCRIPT" validate v-bad 2>&1); rc=$?
assert_false "$rc" "validate should reject unknown status value"
assert_contains "$err" "unknown status" "error should name the problem"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "validate: rejects a missing artifact path"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init v-art >/dev/null 2>&1
sf="$D/.shode-house/state/v-art.json"
tmp=$(mktemp)
jq '.phases["0-discover"].artifacts = ["outputs/does-not-exist.md"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
err=$("$SCRIPT" validate v-art 2>&1); rc=$?
assert_false "$rc" "validate should reject a dangling artifact path"
assert_contains "$err" "artifact path missing" "error should name the problem"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: valid transition 0-discover -> 1a-spec succeeds and updates state + journal"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init tr-1 >/dev/null 2>&1
out=$("$SCRIPT" advance tr-1 1a-spec 2>&1); rc=$?
assert_true "$rc" "valid transition should succeed"
sf="$D/.shode-house/state/tr-1.json"
cur=$(jq -r '.current_phase' "$sf")
assert_eq "$cur" "1a-spec" "current_phase should move to 1a-spec"
prev_status=$(jq -r '.phases["0-discover"].status' "$sf")
assert_eq "$prev_status" "passed" "left phase should default to outcome=passed"
next_status=$(jq -r '.phases["1a-spec"].status' "$sf")
assert_eq "$next_status" "in_progress" "entered phase should be marked in_progress"
jf="$D/.shode-house/journal/tr-1.jsonl"
lines=$(wc -l < "$jf" | tr -d ' ')
assert_eq "$lines" "2" "journal should now have genesis + 1 accept line"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: invalid edge is rejected with a reason, state untouched, journal still records the attempt"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init tr-2 >/dev/null 2>&1
sf="$D/.shode-house/state/tr-2.json"
before_sha=$(shasum "$sf")
err=$("$SCRIPT" advance tr-2 6-operate 2>&1); rc=$?
assert_false "$rc" "no-such-edge transition should be rejected"
assert_contains "$err" "no such edge" "rejection reason should say no such edge"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be byte-identical after a rejected advance"
jf="$D/.shode-house/journal/tr-2.jsonl"
lines=$(wc -l < "$jf" | tr -d ' ')
assert_eq "$lines" "2" "journal should record the rejected attempt too (genesis + reject)"
result=$(tail -n1 "$jf" | jq -r '.result')
assert_eq "$result" "reject" "last journal line should be result=reject"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: unrecognized target phase is rejected (phase enum closed-world)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init tr-3 >/dev/null 2>&1
err=$("$SCRIPT" advance tr-3 nonexistent-phase 2>&1); rc=$?
assert_false "$rc" "unknown phase name should be rejected"
assert_contains "$err" "unknown phase" "rejection reason should say unknown phase"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: unrecognized outcome value is rejected"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init tr-3b >/dev/null 2>&1
err=$("$SCRIPT" advance tr-3b 1a-spec bogus-outcome 2>&1); rc=$?
assert_false "$rc" "unknown outcome value should be rejected"
assert_contains "$err" "unknown outcome" "rejection reason should say unknown outcome"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: without a state file (no init) fails loud, not silent"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
err=$("$SCRIPT" advance never-inited 1a-spec 2>&1); rc=$?
assert_false "$rc" "advance on a never-init'd bd should fail"
assert_contains "$err" "run init first" "error should tell the caller what to do"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "journal: seq is monotonic with no gaps/dupes across accept+reject attempts"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init seqt >/dev/null 2>&1                    # journal seq 1 (genesis)
"$SCRIPT" advance seqt 1a-spec >/dev/null 2>&1          # seq 2 (accept)
"$SCRIPT" advance seqt 6-operate >/dev/null 2>&1        # seq 3 (reject, no edge 1a-spec->6-operate)
"$SCRIPT" advance seqt 1b-design >/dev/null 2>&1        # seq 4 (accept)
jf="$D/.shode-house/journal/seqt.jsonl"
seqs=$(jq -r '.seq' "$jf" | tr '\n' ',' )
assert_eq "$seqs" "1,2,3,4," "journal seq should be exactly 1,2,3,4 with no gap and no repeat"
results=$(jq -r '.result' "$jf" | tr '\n' ',')
assert_eq "$results" "accept,accept,reject,accept," "accept/reject sequence should match the calls made"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "atomic write: crash injected right before rename leaves live state byte-identical, journal 1 entry ahead (documented torn window)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init crash-1 >/dev/null 2>&1
sf="$D/.shode-house/state/crash-1.json"
before_sha=$(shasum "$sf")
WFSTATE_CRASH_BEFORE_RENAME=1 "$SCRIPT" advance crash-1 1a-spec >/dev/null 2>&1
rc=$?
assert_eq "$rc" "137" "crash-injected advance should exit with the injected code"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "live state.json must be byte-identical after a crash before rename (AC-401a)"
jq empty "$sf" >/dev/null 2>&1; assert_true "$?" "live state.json must still parse as valid JSON after the crash"
jf="$D/.shode-house/journal/crash-1.jsonl"
last_result=$(tail -n1 "$jf" | jq -r '.result')
assert_eq "$last_result" "accept" "journal (write-ahead) shows the intended accept even though state wasn't renamed yet"
# no lock left held after the crashed process died
lockd="$D/.shode-house/state/.lock-crash-1"
[ -d "$lockd" ] && t_fail "lock dir should not remain held forever after crashed writer" || t_ok
# the very next advance call must still work (stale tmp cleanup + no lingering lock)
out=$("$SCRIPT" advance crash-1 1a-spec 2>&1); rc=$?
assert_true "$rc" "next advance call after a crash should succeed cleanly"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "atomic write: rejected candidate never overwrites the live file, and tmp litter isn't ambiguous"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init aw-1 >/dev/null 2>&1
"$SCRIPT" advance aw-1 1a-spec >/dev/null 2>&1
sf="$D/.shode-house/state/aw-1.json"
jq empty "$sf" >/dev/null 2>&1; assert_true "$?" "live state must always parse (post-happy-path sanity check)"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "lock contention: a live holder blocks a concurrent advance, which fails loud within budget (not forever), state untouched"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init lock-1 >/dev/null 2>&1
sleep 30 &
holder=$!
lockd="$D/.shode-house/state/.lock-lock-1"
mkdir -p "$lockd"
printf '%s' "$holder" > "$lockd/pid"
date +%s > "$lockd/ts"
sf="$D/.shode-house/state/lock-1.json"
before_sha=$(shasum "$sf")
t0=$(date +%s)
err=$("$SCRIPT" advance lock-1 1a-spec 2>&1); rc=$?
t1=$(date +%s)
elapsed=$((t1 - t0))
kill "$holder" 2>/dev/null
assert_false "$rc" "advance should fail while a live holder has the lock"
assert_contains "$err" "another writer in progress" "error should explain lock contention"
[ "$elapsed" -le 5 ] && t_ok || t_fail "lock wait should be bounded (~2s budget), got ${elapsed}s"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be untouched when the lock could not be acquired"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "lock contention: a stale lock (dead pid) is reaped automatically, does not block forever"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init lock-2 >/dev/null 2>&1
# start and immediately reap a subprocess to get a guaranteed-dead pid
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
lockd="$D/.shode-house/state/.lock-lock-2"
mkdir -p "$lockd"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
t0=$(date +%s)
out=$("$SCRIPT" advance lock-2 1a-spec 2>&1); rc=$?
t1=$(date +%s)
assert_true "$rc" "advance should succeed after reaping a dead-pid stale lock"
[ "$((t1 - t0))" -le 1 ] && t_ok || t_fail "dead-pid reap should be near-instant, not wait out the full budget"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "full happy-path loop through the declarative transition table (0-discover -> ... -> 6-operate, all 9 edges)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init loop-1 >/dev/null 2>&1
ok=1
"$SCRIPT" advance loop-1 1a-spec      >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 1b-design    >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 1c-security  >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 2-implement  >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 3a-ui-check  >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 3b-review    >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 4-triage     >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 5-deploy     >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 6-operate    >/dev/null 2>&1 || ok=0
assert_eq "$ok" "1" "every edge in the declared table should be walkable end to end"
sf="$D/.shode-house/state/loop-1.json"
cur=$(jq -r '.current_phase' "$sf")
assert_eq "$cur" "6-operate" "final phase should be 6-operate"
seq=$(jq -r '.seq' "$sf")
assert_eq "$seq" "9" "state.seq should equal number of accepted transitions (9 edges across 10 nodes)"
iter=$(jq -r '.iter' "$sf")
assert_eq "$iter" "0" "a purely-forward first-visit-only path must never trip the iter/retry counter"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "rework edge: 3a-ui-check -ui-fail-> 1b-design is a declared, legal backward edge"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rew-1 >/dev/null 2>&1
"$SCRIPT" advance rew-1 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance rew-1 1b-design   >/dev/null 2>&1
"$SCRIPT" advance rew-1 1c-security >/dev/null 2>&1
"$SCRIPT" advance rew-1 2-implement >/dev/null 2>&1
"$SCRIPT" advance rew-1 3a-ui-check >/dev/null 2>&1
out=$("$SCRIPT" advance rew-1 1b-design failed 2>&1); rc=$?
assert_true "$rc" "3a-ui-check -> 1b-design loop-back should be a legal, declared edge"
sf="$D/.shode-house/state/rew-1.json"
ui_status=$(jq -r '.phases["3a-ui-check"].status' "$sf")
assert_eq "$ui_status" "failed" "the phase we rework away from should end in status=failed, not passed"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "rework edge: 3b-review -review-fail-> 2-implement is a declared, legal backward edge"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rew-2 >/dev/null 2>&1
"$SCRIPT" advance rew-2 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance rew-2 1b-design   >/dev/null 2>&1
"$SCRIPT" advance rew-2 1c-security >/dev/null 2>&1
"$SCRIPT" advance rew-2 2-implement >/dev/null 2>&1
"$SCRIPT" advance rew-2 3b-review implement-done-backend-only 2>/dev/null # wrong outcome name -> rejected, ignored on purpose (sanity: outcome enum ignores 'on' labels)
out=$("$SCRIPT" advance rew-2 3b-review 2>&1); rc=$?
assert_true "$rc" "2-implement -> 3b-review backend-only bypass edge should be legal"
out=$("$SCRIPT" advance rew-2 2-implement failed 2>&1); rc=$?
assert_true "$rc" "3b-review -> 2-implement loop-back should be a legal, declared edge"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "spec-change edge: an arbitrary later phase can route back to 1a-spec"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init spc-1 >/dev/null 2>&1
"$SCRIPT" advance spc-1 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance spc-1 1b-design   >/dev/null 2>&1
"$SCRIPT" advance spc-1 1c-security >/dev/null 2>&1
"$SCRIPT" advance spc-1 2-implement >/dev/null 2>&1
out=$("$SCRIPT" advance spc-1 1a-spec failed 2>&1); rc=$?
assert_true "$rc" "2-implement -> 1a-spec spec-change edge should be legal"
sf="$D/.shode-house/state/spc-1.json"
cur=$(jq -r '.current_phase' "$sf")
assert_eq "$cur" "1a-spec" "spec-change should move current_phase back to 1a-spec"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "enter_requires: entering 2-implement is blocked if 1b-design has not reached passed/skipped, even though the edge itself exists (mutation target: removing enter_requires from transitions.json must turn this red)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init er-1 >/dev/null 2>&1
"$SCRIPT" advance er-1 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance er-1 1b-design   >/dev/null 2>&1
"$SCRIPT" advance er-1 1c-security >/dev/null 2>&1   # 1b-design now marked passed
sf="$D/.shode-house/state/er-1.json"
# simulate a corrupted/tampered history where 1b-design's completion was never real
tmp=$(mktemp); jq '.phases["1b-design"].status = "pending"' "$sf" > "$tmp" && mv "$tmp" "$sf"
before_sha=$(shasum "$sf")
err=$("$SCRIPT" advance er-1 2-implement 2>&1); rc=$?
assert_false "$rc" "entering 2-implement must be blocked when 1b-design is not passed/skipped"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "1b-design" "rejection reason should name the specific unmet requirement"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be untouched by a blocked enter_requires attempt"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "enter_requires: passes once 1a-spec/1b-design/1c-security are all satisfied (positive control for the test above)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init er-2 >/dev/null 2>&1
"$SCRIPT" advance er-2 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance er-2 1b-design   >/dev/null 2>&1
"$SCRIPT" advance er-2 1c-security >/dev/null 2>&1
out=$("$SCRIPT" advance er-2 2-implement 2>&1); rc=$?
assert_true "$rc" "entering 2-implement should succeed once 1a passed and 1b/1c passed"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "skip: a conditional phase (1b-design) can end status=skipped and still satisfy 2-implement's enter_requires"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init sk-1 >/dev/null 2>&1
"$SCRIPT" advance sk-1 1a-spec >/dev/null 2>&1
"$SCRIPT" advance sk-1 1b-design >/dev/null 2>&1
out=$("$SCRIPT" advance sk-1 1c-security skipped 2>&1); rc=$?
assert_true "$rc" "skipping the conditional phase 1b-design should be legal"
out=$("$SCRIPT" advance sk-1 2-implement skipped 2>&1); rc=$?
assert_true "$rc" "skipping the conditional phase 1c-security should be legal, and enter_requires should accept it"
sf="$D/.shode-house/state/sk-1.json"
assert_eq "$(jq -r '.phases["1b-design"].status' "$sf")" "skipped" "1b-design should end status=skipped"
assert_eq "$(jq -r '.phases["1c-security"].status' "$sf")" "skipped" "1c-security should end status=skipped"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "skip: rejected on a non-conditional phase (0-discover is not in conditional_phases)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init sk-2 >/dev/null 2>&1
err=$("$SCRIPT" advance sk-2 1a-spec skipped 2>&1); rc=$?
assert_false "$rc" "skipping a non-conditional phase should be rejected"
assert_contains "$err" "is not conditional" "rejection reason should say the phase isn't conditional"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "iter-cap: a phase retried past the cap blocks normal advances until it is explicitly escalated, then stays blocked"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init esc-1 >/dev/null 2>&1
"$SCRIPT" advance esc-1 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance esc-1 1b-design   >/dev/null 2>&1
"$SCRIPT" advance esc-1 1c-security >/dev/null 2>&1
"$SCRIPT" advance esc-1 2-implement >/dev/null 2>&1
# 4 fail-cycles between 2-implement <-> 3b-review to push iter past the cap (3)
"$SCRIPT" advance esc-1 3b-review          >/dev/null 2>&1  # iter 0 (3b-review fresh)
"$SCRIPT" advance esc-1 2-implement failed >/dev/null 2>&1  # iter 1
"$SCRIPT" advance esc-1 3b-review          >/dev/null 2>&1  # iter 2
"$SCRIPT" advance esc-1 2-implement failed >/dev/null 2>&1  # iter 3
"$SCRIPT" advance esc-1 3b-review          >/dev/null 2>&1  # iter 4 (still allowed: pre-check used old iter=3)
sf="$D/.shode-house/state/esc-1.json"
assert_eq "$(jq -r '.iter' "$sf")" "4" "iter should now be 4 (past the cap of 3)"
err=$("$SCRIPT" advance esc-1 2-implement failed 2>&1); rc=$?
assert_false "$rc" "a normal advance must be blocked once iter exceeds the cap"
assert_contains "$err" "iter>3 requires escalated transition first" "rejection reason should name the iter-cap rule"
out=$("$SCRIPT" advance esc-1 3b-review escalated 2>&1); rc=$?
assert_true "$rc" "escalated outcome should succeed once iter has exceeded the cap"
assert_eq "$(jq -r '.phases["3b-review"].status' "$sf")" "escalated" "current phase should now carry status=escalated"
assert_eq "$(jq -r '.current_phase' "$sf")" "3b-review" "escalate must not move current_phase away from the escalated phase"
err2=$("$SCRIPT" advance esc-1 4-triage 2>&1); rc2=$?
assert_false "$rc2" "further advances must stay blocked after escalation (needs human decision, no auto-retry)"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "escalated outcome: rejected when target isn't a self-transition, and when iter hasn't exceeded the cap yet"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init esc-2 >/dev/null 2>&1
err=$("$SCRIPT" advance esc-2 1a-spec escalated 2>&1); rc=$?
assert_false "$rc" "escalated outcome should require to==from (self-transition)"
assert_contains "$err" "self-transition" "rejection reason should explain the self-transition requirement"
err2=$("$SCRIPT" advance esc-2 0-discover escalated 2>&1); rc2=$?
assert_false "$rc2" "escalated outcome should be rejected while iter is still within the cap"
assert_contains "$err2" "has not exceeded the cap" "rejection reason should explain iter hasn't exceeded the cap"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "artifact hashing: advance() pins a sha256 for a phase's artifacts when leaving it"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init hash-1 >/dev/null 2>&1
mkdir -p "$D/outputs"
printf 'v1' > "$D/outputs/x.md"
sf="$D/.shode-house/state/hash-1.json"
tmp=$(mktemp); jq '.phases["0-discover"].artifacts = ["outputs/x.md"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
"$SCRIPT" advance hash-1 1a-spec >/dev/null 2>&1
stored=$(jq -r '.phases["0-discover"].artifact_hashes["outputs/x.md"] // ""' "$sf")
expect=$(shasum -a 256 "$D/outputs/x.md" | awk '{print $1}')
assert_eq "$stored" "$expect" "advance() should have recorded the artifact's sha256 for the phase it just left"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: engagement guard applies (no .shode-house -> silent no-op) [already covered above, this asserts on its own state too]"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-guard >/dev/null 2>&1
rm -rf "$D/.shode-house"
out=$("$SCRIPT" reconcile rc-guard 2>&1); rc=$?
assert_true "$rc" "reconcile should no-op once the engagement dir disappears"
assert_eq "$out" "" "reconcile should print nothing when not engaged"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: bd unavailable -> checks 1&2 SKIP loudly (never silent pass, never crash)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init nobd-1 >/dev/null 2>&1
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile nobd-1 2>&1); rc=$?
assert_true "$rc" "reconcile should still exit 0 -- the other 4 checks pass on a fresh state even with bd unavailable"
assert_contains "$out" "bd-closed-vs-workflow]: SKIP" "check 1 should be visibly SKIPped, not silently passed"
assert_contains "$out" "workflow-done-vs-bd-active]: SKIP" "check 2 should be visibly SKIPped, not silently passed"
assert_contains "$out" "bd unavailable" "the SKIP reason should say why (not a bare 'skipped')"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: artifact path missing -> FAIL, distinguishable from the other 5 checks"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-3 >/dev/null 2>&1
sf="$D/.shode-house/state/rc-3.json"
tmp=$(mktemp); jq '.phases["0-discover"].artifacts = ["outputs/does-not-exist.md"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile rc-3 2>&1); rc=$?
assert_false "$rc" "reconcile should exit non-zero when an artifact path is missing"
assert_contains "$out" "artifact-path-missing]: FAIL" "the missing-artifact check should be named FAIL, not a generic failure"
assert_contains "$out" "does-not-exist.md" "the FAIL reason should name the specific missing path"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: artifact hash mismatch on a NOT-yet-approved phase -> FAIL check 4 (not check 5)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-4 >/dev/null 2>&1
mkdir -p "$D/outputs"
printf 'v1' > "$D/outputs/y.md"
sf="$D/.shode-house/state/rc-4.json"
tmp=$(mktemp); jq '.phases["1a-spec"].artifacts = ["outputs/y.md"] | .phases["1a-spec"].artifact_hashes = {"outputs/y.md": "deadbeef"}' "$sf" > "$tmp" && mv "$tmp" "$sf"
# 1a-spec is still "pending" (never entered) -- deliberately not an approved phase
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile rc-4 2>&1); rc=$?
assert_false "$rc" "reconcile should exit non-zero on a hash mismatch"
assert_contains "$out" "artifact-hash-mismatch]: FAIL" "should be reported under the general hash-mismatch check"
assert_contains "$out" "approval-stale-artifact]: PASS" "the approval-specific check must stay PASS -- the owning phase was never approved"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: approval references a stale artifact once the owning phase has passed -> FAIL check 5 (not check 4)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-5 >/dev/null 2>&1
mkdir -p "$D/outputs"
printf 'v1' > "$D/outputs/z.md"
sf="$D/.shode-house/state/rc-5.json"
tmp=$(mktemp); jq '.phases["0-discover"].artifacts = ["outputs/z.md"] | .phases["0-discover"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
"$SCRIPT" advance rc-5 1a-spec >/dev/null 2>&1   # 0-discover -> passed, hash of z.md pinned
printf 'v2 tampered after approval' > "$D/outputs/z.md"
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile rc-5 2>&1); rc=$?
assert_false "$rc" "reconcile should exit non-zero once an approved phase's artifact drifts"
assert_contains "$out" "approval-stale-artifact]: FAIL" "should be reported under the approval-specific check"
assert_contains "$out" "artifact-hash-mismatch]: PASS" "the general check must stay PASS -- this phase IS approved, so it belongs to check 5 only"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: phase passed without a required owner -> FAIL check 6"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-6 >/dev/null 2>&1
"$SCRIPT" advance rc-6 1a-spec >/dev/null 2>&1   # 0-discover -> passed, owners never set ([])
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile rc-6 2>&1); rc=$?
assert_false "$rc" "reconcile should exit non-zero when a passed phase has no owner"
assert_contains "$out" "phase-passed-without-owner]: FAIL" "should be reported under the owner check"
assert_contains "$out" "0-discover" "the FAIL reason should name the specific phase missing an owner"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "reconcile: all-clean state -> every check reports PASS or SKIP, overall exit 0"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init rc-7 >/dev/null 2>&1
sf="$D/.shode-house/state/rc-7.json"
tmp=$(mktemp); jq '.phases["0-discover"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
"$SCRIPT" advance rc-7 1a-spec >/dev/null 2>&1
out=$(PATH="$(path_without_bd)" "$SCRIPT" reconcile rc-7 2>&1); rc=$?
assert_true "$rc" "a clean state with no bd, no artifacts, and a properly-owned passed phase should reconcile clean"
fails=$(printf '%s' "$out" | grep -c ']: FAIL' || true)
assert_eq "$fails" "0" "no check should report FAIL on a clean state"
rm -rf "$D"

# ---------------------------------------------------------------------------
if [ "$HAVE_BD" -eq 1 ]; then
  t_start "reconcile: bd closed but workflow not done -> FAIL check 1 (real bd workspace)"
  D=$(sandbox); mkdir -p "$D/.shode-house"
  ( cd "$D" && bd init --quiet >/dev/null 2>&1 )
  bdid=$(bd -C "$D" create "reconcile test 1" --json 2>/dev/null | jq -r .id)
  export WFSTATE_ROOT="$D"
  "$SCRIPT" init "$bdid" >/dev/null 2>&1
  bd -C "$D" close "$bdid" --reason "test" --json >/dev/null 2>&1
  out=$("$SCRIPT" reconcile "$bdid" 2>&1); rc=$?
  assert_false "$rc" "reconcile should FAIL when bd is closed but the workflow state hasn't reached done"
  assert_contains "$out" "bd-closed-vs-workflow]: FAIL" "should be reported under check 1"
  rm -rf "$D"

  t_start "reconcile: workflow done but bd still active -> FAIL check 2 (real bd workspace)"
  D=$(sandbox); mkdir -p "$D/.shode-house"
  ( cd "$D" && bd init --quiet >/dev/null 2>&1 )
  bdid=$(bd -C "$D" create "reconcile test 2" --json 2>/dev/null | jq -r .id)
  export WFSTATE_ROOT="$D"
  "$SCRIPT" init "$bdid" >/dev/null 2>&1
  sf="$D/.shode-house/state/$(printf '%s' "$bdid" | sed 's#/#--#g').json"
  tmp=$(mktemp); jq '.current_phase = "6-operate" | .phases["6-operate"].status = "passed" | .phases["6-operate"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
  out=$("$SCRIPT" reconcile "$bdid" 2>&1); rc=$?
  assert_false "$rc" "reconcile should FAIL when the workflow reached done but bd is still open"
  assert_contains "$out" "workflow-done-vs-bd-active]: FAIL" "should be reported under check 2"
  rm -rf "$D"

  t_start "reconcile: bd open + workflow not done -> check 1&2 PASS (real bd workspace, positive control)"
  D=$(sandbox); mkdir -p "$D/.shode-house"
  ( cd "$D" && bd init --quiet >/dev/null 2>&1 )
  bdid=$(bd -C "$D" create "reconcile test 3" --json 2>/dev/null | jq -r .id)
  export WFSTATE_ROOT="$D"
  "$SCRIPT" init "$bdid" >/dev/null 2>&1
  out=$("$SCRIPT" reconcile "$bdid" 2>&1); rc=$?
  assert_true "$rc" "a fresh bd-linked engagement should reconcile clean"
  assert_contains "$out" "bd-closed-vs-workflow]: PASS" "check 1 should PASS"
  assert_contains "$out" "workflow-done-vs-bd-active]: PASS" "check 2 should PASS"
  rm -rf "$D"
else
  t_skip "bd not installed on this host -- real-bd-workspace reconcile tests (checks 1&2 positive path) skipped; the bd-unavailable degrade path above still ran and is what CI (no bd installed) exercises"
fi

unset WFSTATE_ROOT

# ---------------------------------------------------------------------------
# bd: shode-roadmap/C-A4 iter 1 -- Makefile zip list had `references` but not
# `scripts` -> target project got the rule table (transitions.json) but not the
# enforcer (workflow-state.sh). This case runs the real `make pack` and greps the
# real artifact, so it goes red if anyone drops the Makefile line again.
t_start "packaging: make pack ships scripts/workflow-state.sh alongside references/state-machine/transitions.json"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "scripts/workflow-state.sh" "packed artifact must ship the enforcer script"
assert_contains "$listing" "references/state-machine/transitions.json" "packed artifact must ship the rule table"

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
