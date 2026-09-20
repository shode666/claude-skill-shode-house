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
assert_contains "$err" "LOCK_BUSY" "error should explain lock contention with the machine-readable class (bd:shode-house-vz8 iter1 -- advance now does a small bounded retry on LOCK_BUSY, so this must still surface after retry is exhausted, never the old generic 'another writer in progress')"
[ "$elapsed" -le 10 ] && t_ok || t_fail "lock wait should be bounded (WFSTATE_LOCK_MAX_ATTEMPTS attempts of the ~2s budget each, plus small jitter), got ${elapsed}s"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be untouched when the lock could not be acquired"
rm -rf "$D"

# ---------------------------------------------------------------------------
# NO automatic stale-lock reclamation -- bd:shode-house-vz8 (user ruling on
# bd:shode-house-5cs.7's THREE successive reap patches, each of which narrowed the
# "reaper destroys a NEW legitimate holder's lock" race without closing it). Automatic
# reclamation is removed entirely, in the shared scripts/lib/lock.sh this file now
# sources. A dead holder's lock stays stuck BY DESIGN; the only way to clear one is the
# explicit, audited `scripts/lib/lock.sh recover <lockdir> --reason "..."`.
t_start "NO AUTO-REAP: a dead-pid holder's lock is NEVER reclaimed automatically -- advance fails closed (waits the real contention budget, not near-instant), state and the lock dir are both untouched"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init dead-1 >/dev/null 2>&1
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
lockd="$D/.shode-house/state/.lock-dead-1"
mkdir -p "$lockd"
printf 'dead-holder-token' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
sf="$D/.shode-house/state/dead-1.json"
before_sha=$(shasum "$sf")
t0=$(date +%s)
out=$("$SCRIPT" advance dead-1 1a-spec 2>&1); rc=$?
t1=$(date +%s)
assert_false "$rc" "advance against a dead-pid-held lock must FAIL (never silently reap and proceed)"
assert_contains "$out" "RECOVERY_REQUIRED" "the failure must explain lock contention with the machine-readable class (bd:shode-house-vz8 iter1 -- a dead-pid-held lock classifies as RECOVERY_REQUIRED and is never retried)"
elapsed=$((t1 - t0))
[ "$elapsed" -ge 1 ] && t_ok || t_fail "must wait out the real contention budget (~2s), not return near-instant the way the old auto-reap did -- got ${elapsed}s"
[ -d "$lockd" ] && t_ok || t_fail "the dead-pid lock directory must still exist -- NEVER auto-removed"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "dead-holder-token" "the stuck lock's token must be byte-for-byte unchanged"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be completely untouched when the lock could not be acquired"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "STALE LOCK + CONCURRENT RETRY-WORKERS: N=10 concurrent advance calls racing a permanently-stuck dead-pid lock all fail CLOSED -- 0 successes, state untouched, lock dir byte-identical (bd:shode-house-5cs.7's broken shape reproduced: this used to lose writes / duplicate journal seq via the buggy reap; now it cleanly refuses instead of corrupting)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/tmp-out"
export WFSTATE_ROOT="$D"
"$SCRIPT" init dead-2 >/dev/null 2>&1
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
lockd="$D/.shode-house/state/.lock-dead-2"
mkdir -p "$lockd"
printf 'dead-holder-token-2' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
sf="$D/.shode-house/state/dead-2.json"
before_sha=$(shasum "$sf")
for i in $(seq 1 10); do
  ( "$SCRIPT" advance dead-2 1a-spec >/dev/null 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
rc0_count=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
assert_eq "$rc0_count" "0" "not one of the 10 concurrent retry-workers may succeed against a stuck lock -- got $rc0_count rc=0"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be byte-identical after 10 concurrent workers all failed to acquire"
jf="$D/.shode-house/journal/dead-2.jsonl"
jcount=$(wc -l < "$jf" | tr -d ' ')
assert_eq "$jcount" "1" "the journal must hold ONLY the init line -- none of the 10 concurrent workers may have appended a transition (this is exactly what a duplicate-seq corruption used to look like: journal writes from callers that should never have proceeded)"
assert_eq "$(tail -n1 "$jf" | jq -r '.op')" "init" "the one journal line must still be the init entry, not a transition from a worker that should have failed to acquire"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "dead-holder-token-2" "the stuck lock's token must survive 10 concurrent contenders unchanged"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "RECOVERY REQUIRED BEFORE REUSE: the SAME stuck lock that just failed 10 concurrent advances becomes usable again ONLY after an explicit, audited scripts/lib/lock.sh recover -- and that recovery is on the record"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init dead-3 >/dev/null 2>&1
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
lockd="$D/.shode-house/state/.lock-dead-3"
mkdir -p "$lockd"
printf 'dead-holder-token-3' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
"$SCRIPT" advance dead-3 1a-spec >/dev/null 2>&1; rc_pre=$?
assert_false "$rc_pre" "sanity: advance still fails before recovery"
recover_out=$(bash "$REPO_ROOT/scripts/lib/lock.sh" recover "$lockd" --reason "bd:shode-house-vz8 test -- confirmed-dead crash, no live holder" 2>&1); recover_rc=$?
assert_true "$recover_rc" "recover on a genuinely stuck lock (no newer holder raced in) must succeed"
assert_contains "$recover_out" "RECOVERED" "recover output should confirm the lock was cleared"
[ -d "$lockd" ] && t_fail "the lock directory must be GONE after a successful recover" || t_ok
audit="$D/.shode-house/state/.lock-recoveries.jsonl"
[ -f "$audit" ] && t_ok || t_fail "recovery must be audited -- expected $audit"
jq empty "$audit" >/dev/null 2>&1
assert_true "$?" "every line of the recovery audit log must be valid JSON"
completed_lines=$(jq -r 'select(.outcome == "COMPLETED") | .lockdir' "$audit" 2>/dev/null | grep -c "^${lockd}\$")
assert_eq "$completed_lines" "1" "the audit log must record exactly one COMPLETED recovery of this lockdir (bd:shode-house-vz8 iter1 -- outcome vocabulary is STARTED/REFUSED/FAILED/COMPLETED, uppercase)"
out_post=$("$SCRIPT" advance dead-3 1a-spec 2>&1); rc_post=$?
assert_true "$rc_post" "advance must succeed now that the stuck lock has been explicitly recovered"
sf="$D/.shode-house/state/dead-3.json"
assert_eq "$(jq -r '.current_phase' "$sf")" "1a-spec" "post-recovery advance should land cleanly"
rm -rf "$D"

# ---------------------------------------------------------------------------
# bd:shode-house-vz8 iter1 (Chris High + user protocol) -- restore-on-abort is DELETED
# entirely, not repaired: once the quarantine rename succeeds, the canonical path is
# never touched again and NEVER restored, even when the captured identity turns out to
# be a legitimately newer holder. A later mismatch is RECOVERY_FAILED, the quarantine
# stays on disk for an operator to inspect, and the audit records FAILED -- see
# scripts/lib/lock.sh's own header for the full rationale (the old restore-on-abort was
# ITSELF an unclosed TOCTOU: `mv` onto an existing directory silently nests instead of
# failing).
t_start "RECOVER NEVER RESTORES: recovery targets a lock it already observed as stale -- if a NEW legitimate holder acquires the SAME canonical path in the gap before recover's own atomic quarantine rename, recover must FAIL CLOSED (RECOVERY_FAILED) and must NEVER restore/recreate the canonical path (deterministic interleaving via LOCK_RECOVER_SYNC_PREMV, not timing luck)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init dead-4 >/dev/null 2>&1
lockd="$D/.shode-house/state/.lock-dead-4"
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
mkdir -p "$lockd"
printf 'dead-holder-token-4' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"

sync="$D/recover-sync"
LOCK_RECOVER_SYNC_PREMV="$sync" LOCK_RECOVER_TOKEN_OVERRIDE="detvz8" \
  bash "$REPO_ROOT/scripts/lib/lock.sh" recover "$lockd" --reason "racing recover test" >"$D/recover-out" 2>&1 &
recover_pid=$!

synced_wait=0
while [ ! -e "${sync}.ready" ]; do
  synced_wait=$((synced_wait + 1))
  if [ "$synced_wait" -ge 100 ]; then t_fail "recover never reached its pre-mv sync point within 10s"; break; fi
  sleep 0.1
done

# While recover is paused mid-decision (liveness gate already passed against the
# ORIGINALLY-observed dead-4 holder): a NEW, LIVE, legitimate holder wins the SAME
# canonical path -- marked distinctly so a survives-vs-recreated mixup can never read
# as a false pass.
rm -rf "$lockd"
sleep 30 & new_holder_pid=$!
mkdir -p "$lockd"
printf 'new-holder-token' > "$lockd/token"
printf '%s' "$new_holder_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
: > "$lockd/MARKER-NEW-HOLDER"

: > "${sync}.go"
wait "$recover_pid" 2>/dev/null; recover_rc=$?
kill "$new_holder_pid" 2>/dev/null

assert_eq "$recover_rc" "6" "recover must report RECOVERY_FAILED (rc=6) when a newer holder raced in, not silently succeed and never restore"
recover_out=$(cat "$D/recover-out")
assert_contains "$recover_out" "RECOVERY_FAILED" "recover output must say RECOVERY_FAILED"
assert_contains "$recover_out" "did not match" "recover output must explain the identity mismatch (a newer holder was captured)"
# The new holder's directory was swept into quarantine by recover's mv and is GONE
# from the canonical path -- this is the accepted, explicit tradeoff of deleting
# restore-on-abort (a later failure never recreates the canonical lock, by any path).
[ -d "$lockd" ] && t_fail "the canonical path must NOT be restored/recreated after a RECOVERY_FAILED -- restore-on-abort is deleted entirely" || t_ok
quarantine="${lockd}.quarantine.detvz8"
[ -d "$quarantine" ] && t_ok || t_fail "the quarantine copy must be RETAINED on disk (never auto-swept) so an operator can inspect it -- expected $quarantine"
[ -f "$quarantine/captured/MARKER-NEW-HOLDER" ] && t_ok || t_fail "the new holder's marker must survive intact INSIDE the quarantine (not lost, not silently discarded) -- proves it was captured, not corrupted"
assert_eq "$(cat "$quarantine/captured/token" 2>/dev/null)" "new-holder-token" "the new holder's token must be byte-for-byte intact inside the retained quarantine copy"
[ ! -e "${lockd}.recovering" ] && t_ok || t_fail "the .recovering marker must be cleared even on a FAILED recovery (never left stuck by this file's own failure path)"
audit="$D/.shode-house/state/.lock-recoveries.jsonl"
failed_lines=$(jq -r 'select(.outcome == "FAILED" and .result == "RECOVERY_FAILED") | .lockdir' "$audit" 2>/dev/null | grep -c "^${lockd}\$")
assert_eq "$failed_lines" "1" "the failed recovery attempt must ALSO be on the audit record, not just successful ones"
rm -rf "$quarantine" "$D"

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
# C-A6 iter0: enter_requires is now populated on all 10 states (previously only
# 2-implement). Each of the 6 newly-populated gates below (1b-design, 1c-security,
# 3a-ui-check, 4-triage, 5-deploy, 6-operate) gets its own negative test here --
# the shared "loop-1" happy-path test (all edges walked with default outcome=passed)
# already serves as every one of these gates' POSITIVE control. Same technique for
# all 6: walk to right before the gate, then make the exact forward call with
# outcome=failed instead of the default passed -- the target phase's enter_requires
# only allows the predecessor to end in [passed] (or [passed,skipped]), so this must
# be rejected. (Mutation target: deleting any one of these 6 keys from
# transitions.json's enter_requires must turn its matching test below red.)

t_start "enter_requires: entering 1b-design is blocked when 1a-spec ends outcome=failed instead of passed (pre-spec-expand gate)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-1b >/dev/null 2>&1
"$SCRIPT" advance gate-1b 1a-spec >/dev/null 2>&1
sf="$D/.shode-house/state/gate-1b.json"
before_sha=$(shasum "$sf")
err=$("$SCRIPT" advance gate-1b 1b-design failed 2>&1); rc=$?
assert_false "$rc" "1a-spec ending failed must not be allowed into 1b-design"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "1a-spec" "rejection reason should name the specific unmet requirement"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be untouched by a blocked enter_requires attempt"
rm -rf "$D"

t_start "enter_requires: entering 1c-security is blocked when 1b-design ends outcome=failed (not passed/skipped)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-1c >/dev/null 2>&1
"$SCRIPT" advance gate-1c 1a-spec   >/dev/null 2>&1
"$SCRIPT" advance gate-1c 1b-design >/dev/null 2>&1
err=$("$SCRIPT" advance gate-1c 1c-security failed 2>&1); rc=$?
assert_false "$rc" "1b-design ending failed must not be allowed into 1c-security"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "1b-design" "rejection reason should name the specific unmet requirement"
rm -rf "$D"

t_start "enter_requires: entering 3a-ui-check is blocked when 2-implement ends outcome=failed (pre-ui-check gate)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-3a >/dev/null 2>&1
"$SCRIPT" advance gate-3a 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance gate-3a 1b-design   >/dev/null 2>&1
"$SCRIPT" advance gate-3a 1c-security >/dev/null 2>&1
"$SCRIPT" advance gate-3a 2-implement >/dev/null 2>&1
err=$("$SCRIPT" advance gate-3a 3a-ui-check failed 2>&1); rc=$?
assert_false "$rc" "2-implement ending failed must not be allowed into 3a-ui-check"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "2-implement" "rejection reason should name the specific unmet requirement"
rm -rf "$D"

t_start "enter_requires: entering 4-triage is blocked when 3b-review ends outcome=failed instead of passed"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-4t >/dev/null 2>&1
"$SCRIPT" advance gate-4t 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance gate-4t 1b-design   >/dev/null 2>&1
"$SCRIPT" advance gate-4t 1c-security >/dev/null 2>&1
"$SCRIPT" advance gate-4t 2-implement >/dev/null 2>&1
"$SCRIPT" advance gate-4t 3a-ui-check >/dev/null 2>&1
"$SCRIPT" advance gate-4t 3b-review   >/dev/null 2>&1
err=$("$SCRIPT" advance gate-4t 4-triage failed 2>&1); rc=$?
assert_false "$rc" "3b-review ending failed must not be allowed into 4-triage"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "3b-review" "rejection reason should name the specific unmet requirement"
rm -rf "$D"

t_start "enter_requires: entering 5-deploy is blocked when 4-triage ends outcome=failed instead of passed (pre-loop-exit gate)"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-5d >/dev/null 2>&1
"$SCRIPT" advance gate-5d 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance gate-5d 1b-design   >/dev/null 2>&1
"$SCRIPT" advance gate-5d 1c-security >/dev/null 2>&1
"$SCRIPT" advance gate-5d 2-implement >/dev/null 2>&1
"$SCRIPT" advance gate-5d 3a-ui-check >/dev/null 2>&1
"$SCRIPT" advance gate-5d 3b-review   >/dev/null 2>&1
"$SCRIPT" advance gate-5d 4-triage    >/dev/null 2>&1
err=$("$SCRIPT" advance gate-5d 5-deploy failed 2>&1); rc=$?
assert_false "$rc" "4-triage ending failed must not be allowed into 5-deploy"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "4-triage" "rejection reason should name the specific unmet requirement"
rm -rf "$D"

t_start "enter_requires: entering 6-operate is blocked when 5-deploy ends outcome=failed instead of passed"
D=$(sandbox); mkdir -p "$D/.shode-house"
export WFSTATE_ROOT="$D"
"$SCRIPT" init gate-6o >/dev/null 2>&1
"$SCRIPT" advance gate-6o 1a-spec     >/dev/null 2>&1
"$SCRIPT" advance gate-6o 1b-design   >/dev/null 2>&1
"$SCRIPT" advance gate-6o 1c-security >/dev/null 2>&1
"$SCRIPT" advance gate-6o 2-implement >/dev/null 2>&1
"$SCRIPT" advance gate-6o 3a-ui-check >/dev/null 2>&1
"$SCRIPT" advance gate-6o 3b-review   >/dev/null 2>&1
"$SCRIPT" advance gate-6o 4-triage    >/dev/null 2>&1
"$SCRIPT" advance gate-6o 5-deploy    >/dev/null 2>&1
err=$("$SCRIPT" advance gate-6o 6-operate failed 2>&1); rc=$?
assert_false "$rc" "5-deploy ending failed must not be allowed into 6-operate"
assert_contains "$err" "enter_requires" "rejection reason should mention enter_requires"
assert_contains "$err" "5-deploy" "rejection reason should name the specific unmet requirement"
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
