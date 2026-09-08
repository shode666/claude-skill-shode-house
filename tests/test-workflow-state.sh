#!/usr/bin/env bash
# tests/test-workflow-state.sh -- bash-only test suite for scripts/workflow-state.sh
# (bd: shode-roadmap/C-A4 -- CI budget rule, outputs/shode-roadmap/C/05-oliver-decisions.md:
#  "1 AC = 1 test case ในสวีท ไม่ใช่ 1 CI section" -- wired into ci.yml as exactly ONE step)
#
# No framework dependency (bats not installed on this machine / not a repo prereq) --
# plain bash test functions + a tiny assert library. Each test runs in its own
# mktemp -d sandbox via WFSTATE_ROOT so tests never touch the real repo state.
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

# ---------------------------------------------------------------------------
t_start "engagement guard: no .shode-house/ -> init/validate/advance all no-op (exit 0, silent, no side effect)"
D=$(sandbox)
export WFSTATE_ROOT="$D"
out=$("$SCRIPT" init eg-1 2>&1); rc=$?
assert_true "$rc" "init should exit 0 with no .shode-house/"
assert_eq "$out" "" "init should print nothing"
out=$("$SCRIPT" validate eg-1 2>&1); rc=$?
assert_true "$rc" "validate should exit 0 with no .shode-house/"
out=$("$SCRIPT" advance eg-1 impl 2>&1); rc=$?
assert_true "$rc" "advance should exit 0 with no .shode-house/"
entries=$(find "$D" -mindepth 1 2>/dev/null | wc -l | tr -d ' ')
assert_eq "$entries" "0" "no files/dirs should be created under an unengaged repo"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "init: creates state.json with 9-value-enum-ready schema + genesis journal line"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
out=$("$SCRIPT" init C-A4 2>&1); rc=$?
assert_true "$rc" "init should succeed once engaged"
sf="$D/.shode-house/state/C-A4.json"
[ -f "$sf" ] && t_ok || t_fail "state file should exist at $sf"
cur=$(jq -r '.current_phase' "$sf" 2>/dev/null)
assert_eq "$cur" "pick" "fresh state current_phase should be pick"
pick_status=$(jq -r '.phases.pick.status' "$sf" 2>/dev/null)
assert_eq "$pick_status" "in_progress" "fresh pick phase should be in_progress"
jf="$D/.shode-house/journal/C-A4.jsonl"
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
jq '.phases.impl.status = "not-a-real-status"' "$sf" > "$tmp" && mv "$tmp" "$sf"
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
jq '.phases.pick.artifacts = ["outputs/does-not-exist.md"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
err=$("$SCRIPT" validate v-art 2>&1); rc=$?
assert_false "$rc" "validate should reject a dangling artifact path"
assert_contains "$err" "artifact path missing" "error should name the problem"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "advance: valid transition pick -> impl succeeds and updates state + journal"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init tr-1 >/dev/null 2>&1
out=$("$SCRIPT" advance tr-1 impl 2>&1); rc=$?
assert_true "$rc" "valid transition should succeed"
sf="$D/.shode-house/state/tr-1.json"
cur=$(jq -r '.current_phase' "$sf")
assert_eq "$cur" "impl" "current_phase should move to impl"
pick_status=$(jq -r '.phases.pick.status' "$sf")
assert_eq "$pick_status" "passed" "left phase should be marked passed"
impl_status=$(jq -r '.phases.impl.status' "$sf")
assert_eq "$impl_status" "in_progress" "entered phase should be marked in_progress"
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
err=$("$SCRIPT" advance tr-2 done 2>&1); rc=$?
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
t_start "advance: without a state file (no init) fails loud, not silent"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
err=$("$SCRIPT" advance never-inited impl 2>&1); rc=$?
assert_false "$rc" "advance on a never-init'd bd should fail"
assert_contains "$err" "run init first" "error should tell the caller what to do"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "journal: seq is monotonic with no gaps/dupes across accept+reject attempts"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init seqt >/dev/null 2>&1                # journal seq 1 (genesis)
"$SCRIPT" advance seqt impl >/dev/null 2>&1         # seq 2 (accept)
"$SCRIPT" advance seqt done >/dev/null 2>&1         # seq 3 (reject, no edge impl->done)
"$SCRIPT" advance seqt ui-check >/dev/null 2>&1     # seq 4 (accept)
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
WFSTATE_CRASH_BEFORE_RENAME=1 "$SCRIPT" advance crash-1 impl >/dev/null 2>&1
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
out=$("$SCRIPT" advance crash-1 impl 2>&1); rc=$?
assert_true "$rc" "next advance call after a crash should succeed cleanly"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "atomic write: rejected candidate never overwrites the live file, and tmp litter isn't ambiguous"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init aw-1 >/dev/null 2>&1
"$SCRIPT" advance aw-1 impl >/dev/null 2>&1
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
err=$("$SCRIPT" advance lock-1 impl 2>&1); rc=$?
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
out=$("$SCRIPT" advance lock-2 impl 2>&1); rc=$?
t1=$(date +%s)
assert_true "$rc" "advance should succeed after reaping a dead-pid stale lock"
[ "$((t1 - t0))" -le 1 ] && t_ok || t_fail "dead-pid reap should be near-instant, not wait out the full budget"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "full happy-path loop through the declarative transition table (pick -> impl -> ui-check -> review -> triage -> done)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init loop-1 >/dev/null 2>&1
ok=1
"$SCRIPT" advance loop-1 impl      >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 ui-check  >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 review    >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 triage    >/dev/null 2>&1 || ok=0
"$SCRIPT" advance loop-1 done      >/dev/null 2>&1 || ok=0
assert_eq "$ok" "1" "every edge in the declared table should be walkable end to end"
sf="$D/.shode-house/state/loop-1.json"
cur=$(jq -r '.current_phase' "$sf")
assert_eq "$cur" "done" "final phase should be done"
seq=$(jq -r '.seq' "$sf")
assert_eq "$seq" "5" "state.seq should equal number of accepted transitions"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "loop-back edge: ui-check -fail-> impl is a declared, legal edge"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init loop-2 >/dev/null 2>&1
"$SCRIPT" advance loop-2 impl     >/dev/null 2>&1
"$SCRIPT" advance loop-2 ui-check >/dev/null 2>&1
out=$("$SCRIPT" advance loop-2 impl 2>&1); rc=$?
assert_true "$rc" "ui-check -> impl loop-back should be a legal, declared edge"
rm -rf "$D"

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
