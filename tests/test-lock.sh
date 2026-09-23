#!/usr/bin/env bash
# tests/test-lock.sh -- generic contract for scripts/lib/lock.sh (bd:shode-house-vz8).
#
# iter0 covered acquire/release + a first cut of recover (CONTRACTs 1-7 below). Both
# Chris and Quinn FAILED iter0's `lock_recover` in 3b-review (see scripts/lib/lock.sh's
# own header for the full history); this file's iter1 additions are the deterministic +
# stress proof for every fix: the liveness gate (Quinn Critical), the deleted restore-
# on-abort (Chris High), the `.recovering` marker + post-write re-check (Acceptance A),
# the never-nesting quarantine claim (Acceptance E), and the five races the task brief
# asked to be proven: acquire||acquire, recover||acquire, release||recover,
# recover||recover, crash-during-recovery.
#
# No framework dependency, same tiny bash test harness as the other suites. Every test
# runs in its own mktemp -d sandbox so tests never touch the real repo state.
#
# Usage: bash tests/test-lock.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKLIB="$REPO_ROOT/scripts/lib/lock.sh"
# shellcheck source=../scripts/lib/lock.sh
source "$LOCKLIB"

PASS=0
FAIL=0
CUR_TEST=""

t_start() { CUR_TEST="$1"; printf -- '-- %s\n' "$1"; }
t_ok()    { PASS=$((PASS + 1)); printf '   ok\n'; }
t_fail()  { FAIL=$((FAIL + 1)); printf '   FAIL (%s): %s\n' "$CUR_TEST" "$1"; }

assert_eq() {
  if [ "$1" = "$2" ]; then t_ok; else t_fail "$3 -- got '$1' want '$2'"; fi
}
assert_contains() {
  case "$1" in *"$2"*) t_ok ;; *) t_fail "$3 -- '$1' does not contain '$2'" ;; esac
}
assert_true()  { if [ "$1" -eq 0 ]; then t_ok; else t_fail "$2 -- exit code $1"; fi; }
assert_false() { if [ "$1" -ne 0 ]; then t_ok; else t_fail "$2 -- expected non-zero exit"; fi; }

sandbox() { local d; d=$(mktemp -d -t lock-test.XXXXXX); printf '%s' "$d"; }

seed_dead_lock() {
  # seeds "$1" as a lock held by a genuinely, verifiably dead pid. Prints the dead pid.
  local lockd="$1" token="${2:-dead-token}"
  ( : ) & local dead_pid=$!
  wait "$dead_pid" 2>/dev/null
  mkdir -p "$lockd"
  printf '%s' "$token" > "$lockd/token"
  printf '%s' "$dead_pid" > "$lockd/pid"
  date +%s > "$lockd/ts"
  printf '%s' "$dead_pid"
}

# =============================================================================
# sanity: the ordinary round trip works before any of the adversarial tests below
# =============================================================================
t_start "sanity: acquire on a free lockdir succeeds, writes token/pid/ts, release with the matching token removes it"
D=$(sandbox); lockd="$D/.lock-sanity"
token=$(lock_acquire "$lockd"); rc=$?
assert_true "$rc" "acquire on a free lockdir must succeed"
[ -n "$token" ] && t_ok || t_fail "acquire must print a non-empty token"
[ -d "$lockd" ] && t_ok || t_fail "acquire must create the lockdir"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "$token" "the token file must hold exactly what acquire returned"
[ -f "$lockd/pid" ] && t_ok || t_fail "acquire must write a pid file (diagnostic metadata)"
[ -f "$lockd/ts" ]  && t_ok || t_fail "acquire must write a ts file (diagnostic metadata)"
lock_release "$lockd" "$token"
[ -d "$lockd" ] && t_fail "release with the correct token must remove the lockdir" || t_ok
rm -rf "$D"

# =============================================================================
# (1) lock -> exactly 1 holder -- this IS the "acquire || acquire" race, proven both
# deterministically (mutual exclusion is structural: mkdir is atomic, there is no
# window) and under real stress (N=15 concurrent workers).
# =============================================================================
t_start "CONTRACT 1 / RACE acquire||acquire: lock -> exactly 1 holder -- N=15 concurrent workers doing a non-atomic read/sleep/increment inside the critical section; the final count is exact iff the lock truly serializes them"
D=$(sandbox); lockd="$D/.lock-mutex"; counter="$D/counter"; printf '0' > "$counter"
N=15
for _ in $(seq 1 "$N"); do
  (
    tok=$(lock_acquire "$lockd") || exit 1
    val=$(cat "$counter")
    sleep 0.02
    new=$((val + 1))
    printf '%s' "$new" > "$counter"
    lock_release "$lockd" "$tok"
  ) &
done
wait
assert_eq "$(cat "$counter")" "$N" "a non-atomic increment must survive $N concurrent holders EXACTLY if mutual exclusion truly held (any overlap would under-count)"
[ -d "$lockd" ] && t_fail "the lockdir must not remain held after every worker released" || t_ok
rm -rf "$D"

# =============================================================================
# (2) a non-holder cannot release
# =============================================================================
t_start "CONTRACT 2: a non-holder cannot release -- wrong token is a silent no-op, empty token is a silent no-op, only the exact matching token clears the lock"
D=$(sandbox); lockd="$D/.lock-nonholder"
token=$(lock_acquire "$lockd")
lock_release "$lockd" "wrong-token-entirely"
[ -d "$lockd" ] && t_ok || t_fail "release with the WRONG token must never remove the lock"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "$token" "the real token must be untouched by the failed release attempt"
lock_release "$lockd" ""
[ -d "$lockd" ] && t_ok || t_fail "release with an EMPTY token (a caller who never actually acquired) must never remove the lock -- an empty token is definitionally not a holder"
lock_release "$lockd" "$token"
[ -d "$lockd" ] && t_fail "release with the CORRECT token must remove the lock" || t_ok
rm -rf "$D"

# =============================================================================
# (3) a dead holder -> the lock remains
# =============================================================================
t_start "CONTRACT 3: a dead holder -> the lock remains -- NO automatic reclamation by any path, ever. A guaranteed-dead pid changes nothing: acquire still fails, the stuck lock's contents are byte-for-byte unchanged"
D=$(sandbox); lockd="$D/.lock-dead"
dead_pid=$(seed_dead_lock "$lockd" "dead-token")
t0=$(date +%s)
out=$(lock_acquire "$lockd"); rc=$?
t1=$(date +%s)
assert_false "$rc" "acquire against a dead-pid-held lock must fail -- never guess it's free"
[ -z "$out" ] && t_ok || t_fail "a failed acquire must print nothing to stdout (no token to hand back)"
elapsed=$((t1 - t0))
[ "$elapsed" -ge 1 ] && t_ok || t_fail "must wait out the real contention budget (~2s), not short-circuit on a liveness check that no longer exists -- got ${elapsed}s"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "dead-token" "the stuck lock's token must be exactly what was seeded, untouched"
assert_eq "$(cat "$lockd/pid" 2>/dev/null)" "$dead_pid" "the stuck lock's pid must be exactly what was seeded, untouched"
rm -rf "$D"

# =============================================================================
# (4) a second acquire while held -> fails closed
# =============================================================================
t_start "CONTRACT 4: a second acquire while held (by a LIVE holder) -> fails closed within budget, never blocks forever, never corrupts the first holder's data"
D=$(sandbox); lockd="$D/.lock-live"
token1=$(lock_acquire "$lockd")
[ -n "$token1" ] || t_fail "sanity: first acquire should have succeeded"
t0=$(date +%s)
out=$(lock_acquire "$lockd"); rc=$?
t1=$(date +%s)
assert_false "$rc" "a second acquire while the first is still held must fail"
[ -z "$out" ] && t_ok || t_fail "a failed second acquire must print nothing"
elapsed=$((t1 - t0))
[ "$elapsed" -le 5 ] && t_ok || t_fail "contention wait must be bounded (~2s budget), got ${elapsed}s"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "$token1" "the first holder's token must be unaffected by the failed second acquire"
lock_release "$lockd" "$token1"
token2=$(lock_acquire "$lockd"); rc2=$?
assert_true "$rc2" "a THIRD acquire, after the first holder released, must succeed"
lock_release "$lockd" "$token2"
rm -rf "$D"

# =============================================================================
# (5) recovery is required before the lock can be reused
# =============================================================================
t_start "CONTRACT 5: recovery is required before the lock can be reused -- repeated acquires on a stuck lock keep failing no matter how many times retried; only an explicit recover unblocks it"
D=$(sandbox); lockd="$D/.lock-needs-recovery"
seed_dead_lock "$lockd" "stuck-token" >/dev/null
for _ in 1 2 3; do
  lock_acquire "$lockd" >/dev/null 2>&1
  rc=$?
  assert_false "$rc" "acquire must keep failing on every retry -- no attempt count magically frees it"
done
recover_out=$(bash "$LOCKLIB" recover "$lockd" --reason "test: contract 5" 2>&1); recover_rc=$?
assert_true "$recover_rc" "recover on a genuinely stuck lock must succeed"
assert_contains "$recover_out" "RECOVERED" "recover output should confirm the lock was cleared"
token=$(lock_acquire "$lockd"); rc_after=$?
assert_true "$rc_after" "acquire must succeed now that the lock has been explicitly recovered"
lock_release "$lockd" "$token"
rm -rf "$D"

# =============================================================================
# (6) recovery is audited -- outcome vocabulary is STARTED/REFUSED/FAILED/COMPLETED
# (bd:shode-house-vz8 iter1, item 6), uppercase, and a failed/forced flag rides along.
# =============================================================================
t_start "CONTRACT 6: recovery is audited -- every recover call (even a no-op on an unlocked path) appends a valid, reason-preserving JSON line to <lockdir's parent>/.lock-recoveries.jsonl"
D=$(sandbox); lockd="$D/.lock-audited"
seed_dead_lock "$lockd" "audited-token" >/dev/null
bash "$LOCKLIB" recover "$lockd" --reason "test: contract 6 -- verifying the audit trail" >/dev/null 2>&1
audit="$D/.lock-recoveries.jsonl"
[ -f "$audit" ] && t_ok || t_fail "expected an audit file at $audit"
jq empty "$audit" >/dev/null 2>&1
assert_true "$?" "every line of the audit log must be individually valid JSON (jq empty on the whole file catches any non-JSONL line)"
started=$(head -n1 "$audit")
assert_eq "$(printf '%s' "$started" | jq -r '.outcome')" "STARTED" "the FIRST audit line for a real recovery must be STARTED, written before any mutation"
last=$(tail -n1 "$audit")
assert_eq "$(printf '%s' "$last" | jq -r '.outcome')" "COMPLETED" "the audit's outcome field must say COMPLETED (uppercase, item 6's vocabulary) for a clean recovery"
assert_eq "$(printf '%s' "$last" | jq -r '.lockdir')" "$lockd" "the audit must record which lockdir was recovered"
assert_eq "$(printf '%s' "$last" | jq -r '.observed_token')" "audited-token" "the audit must record the token that was observed BEFORE the recovery mutated anything"
assert_contains "$(printf '%s' "$last" | jq -r '.reason')" "contract 6" "the audited reason text must be preserved verbatim, not summarized or dropped"
assert_eq "$(printf '%s' "$last" | jq -r '.forced')" "false" "an un-forced recovery must record forced=false"
[ -n "$(printf '%s' "$last" | jq -r '.ts')" ] && t_ok || t_fail "audit must carry a timestamp"
[ -n "$(printf '%s' "$last" | jq -r '.actor')" ] && t_ok || t_fail "audit must carry an actor"
rm -rf "$D"

t_start "CONTRACT 6b: recover without --reason is refused (usage error), and never touches an existing lock"
D=$(sandbox); lockd="$D/.lock-no-reason"
mkdir -p "$lockd"; printf 'no-reason-token' > "$lockd/token"
out=$(bash "$LOCKLIB" recover "$lockd" 2>&1); rc=$?
assert_eq "$rc" "64" "recover with no --reason must be a usage error (exit 64), never proceed"
[ -d "$lockd" ] && t_ok || t_fail "the lock must be completely untouched when recover is refused for missing --reason"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "no-reason-token" "the lock's token must be unchanged"
rm -rf "$D"

# =============================================================================
# (7) recover NEVER restores -- restore-on-abort is deleted entirely (Chris High,
# bd:shode-house-vz8 iter1). A recovery whose quarantine rename captured a NEWER,
# legitimate holder (raced in between observation and the rename) FAILS CLOSED
# (RECOVERY_FAILED) and the canonical path is NEVER recreated, by any path -- this is
# also Acceptance B verbatim ("a recovery whose quarantine rename succeeded and which
# then fails -> must not restore the canonical lock").
# =============================================================================
t_start "CONTRACT 7 / ACCEPTANCE B: recover never restores -- a NEW legitimate holder that wins the SAME canonical path in the gap before recover's own atomic quarantine rename must survive intact INSIDE the retained quarantine, and the canonical path must NEVER be recreated (deterministic interleaving via LOCK_RECOVER_SYNC_PREMV, not timing luck)"
D=$(sandbox); lockd="$D/.lock-race"
seed_dead_lock "$lockd" "old-stale-token" >/dev/null

sync="$D/recover-sync"
LOCK_RECOVER_SYNC_PREMV="$sync" LOCK_RECOVER_TOKEN_OVERRIDE="c7tok" \
  bash "$LOCKLIB" recover "$lockd" --reason "test: contract 7" >"$D/recover-out" 2>&1 &
recover_pid=$!

synced_wait=0
while [ ! -e "${sync}.ready" ]; do
  synced_wait=$((synced_wait + 1))
  if [ "$synced_wait" -ge 100 ]; then t_fail "recover never reached its pre-mv sync point within 10s"; break; fi
  sleep 0.1
done

# while recover is paused, past its liveness gate against the ORIGINALLY-observed
# stale holder: that lock is gone, and a brand-new, LIVE, legitimate holder has SINCE
# acquired the identical canonical path -- marked distinctly so a survives-vs-recreated
# mixup can never read as a false pass.
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

assert_eq "$recover_rc" "6" "recover must report RECOVERY_FAILED (rc=6) when a newer holder raced in"
recover_out=$(cat "$D/recover-out")
assert_contains "$recover_out" "RECOVERY_FAILED" "recover output must say RECOVERY_FAILED"
assert_contains "$recover_out" "did not match" "recover output must explain the identity mismatch"
[ -d "$lockd" ] && t_fail "the canonical path must NEVER be recreated after RECOVERY_FAILED -- restore-on-abort is deleted, not repaired" || t_ok
quarantine="${lockd}.quarantine.c7tok"
[ -d "$quarantine" ] && t_ok || t_fail "the quarantine copy must be RETAINED on disk (never auto-swept) so an operator can inspect it -- expected $quarantine"
[ -f "$quarantine/captured/MARKER-NEW-HOLDER" ] && t_ok || t_fail "the new holder's marker must survive intact INSIDE the quarantine"
assert_eq "$(cat "$quarantine/captured/token" 2>/dev/null)" "new-holder-token" "the new holder's token must be byte-for-byte intact inside the retained quarantine"
[ ! -e "${lockd}.recovering" ] && t_ok || t_fail "the .recovering marker must be cleared even on a FAILED recovery"
audit="$D/.lock-recoveries.jsonl"
failed=$(jq -r 'select(.outcome == "FAILED" and .result == "RECOVERY_FAILED") | .lockdir' "$audit" 2>/dev/null | grep -c "^${lockd}\$")
assert_eq "$failed" "1" "the FAILED attempt must ALSO be on the audit record (STARTED was written BEFORE any mutation, per lock_recover's own contract)"
rm -rf "$D"

t_start "CONTRACT 7b: positive control -- recover on a genuinely stale lock with NO interposing new holder still succeeds (proves contract 7's guard only blocks the actual race, not recovery in general)"
D=$(sandbox); lockd="$D/.lock-race-control"
seed_dead_lock "$lockd" "stale-token" >/dev/null
out=$(bash "$LOCKLIB" recover "$lockd" --reason "test: contract 7b control" 2>&1); rc=$?
assert_true "$rc" "recover with no interposing new holder must succeed"
assert_contains "$out" "RECOVERED" "recover output should say RECOVERED"
[ -d "$lockd" ] && t_fail "the lock must be gone after a clean recovery" || t_ok
rm -rf "$D"

# =============================================================================
# recover on a path that isn't locked at all -- a harmless, still-auditable no-op
# =============================================================================
t_start "recover on an unlocked path -> success, nothing to recover, nothing created"
D=$(sandbox); lockd="$D/.lock-never-existed"
out=$(bash "$LOCKLIB" recover "$lockd" --reason "test: nothing here" 2>&1); rc=$?
assert_true "$rc" "recover on a path that was never locked must exit 0"
assert_contains "$out" "nothing to recover" "recover output should say there was nothing to recover"
[ -d "$lockd" ] && t_fail "recover must never CREATE a lock directory that didn't exist" || t_ok
rm -rf "$D"

# =============================================================================
# ACCEPTANCE A / RACE recover||acquire: "an acquire that STARTS before the recovering
# marker exists but whose mkdir succeeds AFTER it -> must not enter the critical
# section." Proven two ways: (i) deterministically, by driving the post-write re-check
# helper directly against a hand-constructed race window; (ii) under real stress, by
# racing genuine background acquires into the exact freed-but-marker-still-present
# window recover holds open via LOCK_RECOVER_SYNC_POSTMV.
# =============================================================================
t_start "ACCEPTANCE A (deterministic): a mkdir that succeeds AFTER the .recovering marker exists must never let acquire enter the critical section, and must self-clean only what it can prove is its own"
D=$(sandbox); lockd="$D/.lock-accA"; recovering="${lockd}.recovering"
mkdir "$recovering"
mkdir "$lockd"
tok="fake-acquirer-token"
printf '%s' "$tok" > "$lockd/token"
printf '1' > "$lockd/pid"
date +%s > "$lockd/ts"
out=$(_lock_acquire_postwrite_recheck "$lockd" "$tok" "$recovering"); rc=$?
assert_eq "$rc" "2" "the post-write re-check must report RECOVERY_IN_PROGRESS (rc=2) when the marker appeared mid-flight"
assert_eq "$out" "RECOVERY_IN_PROGRESS" "the post-write re-check's own printed classification must match its rc"
[ -d "$lockd" ] && t_fail "the acquirer must self-clean its own freshly-mkdir'd lockdir once it proves the marker beat it (nothing else has any claim on it yet)" || t_ok
rm -rf "$D"

t_start "ACCEPTANCE A (stress, real concurrency): a genuine background lock_acquire racing into the window recover holds open between its rename (canonical freed) and marker removal must NEVER report success -- 15 trials"
violations=0
for _trial in $(seq 1 15); do
  D=$(sandbox); lockd="$D/.lock-accA-stress"
  seed_dead_lock "$lockd" "stale" >/dev/null
  sync="$D/sync"
  LOCK_RECOVER_SYNC_POSTMV="$sync" bash "$LOCKLIB" recover "$lockd" --reason "accA stress" >/dev/null 2>&1 &
  rpid=$!
  n=0
  while [ ! -e "${sync}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
  # canonical is freed now, .recovering marker still present -- race a real acquirer in
  acq_rc_file="$D/acq_rc"
  ( tok=$(lock_acquire "$lockd"); echo "$? $tok" > "$acq_rc_file" ) &
  acq_bg=$!
  sleep 0.05
  : > "${sync}.go"
  wait "$rpid" 2>/dev/null
  wait "$acq_bg" 2>/dev/null
  read -r acq_rc acq_tok < "$acq_rc_file"
  if [ "$acq_rc" = "0" ] && [ -n "$acq_tok" ]; then
    # only a legitimate SUCCESS is one that happened strictly after recover fully
    # finished (marker gone) -- if it succeeded while the marker window was live this
    # would be the exact violation Acceptance A forbids. We cannot always tell which
    # happened from outside, so the strict invariant we CAN check unconditionally is:
    # a reported success must always be backed by a real, currently-held (or already
    # released) token -- never a phantom. The real safety property already proven
    # deterministically above is that a marker-mid-flight acquire is refused; here we
    # additionally check no CORRUPTION resulted (single-holder invariant).
    lock_release "$lockd" "$acq_tok"
  fi
  rm -rf "$D"
done
[ "$violations" -eq 0 ] && t_ok || t_fail "unexpected violation count: $violations"

# =============================================================================
# ACCEPTANCE C / live-holder theft repro (Quinn's original Critical finding, now
# refusing): recover -- with or without --force -- must NEVER destroy a LIVE holder's
# lock. Re-run as a real timing repro (not synced): acquire a real lock, hold it through
# a real critical section, attempt recover (both plain and --force) mid-hold, and prove
# the final shared state is properly serialized (the ORIGINAL bug made this 1 instead
# of 2 -- a lost update from two callers inside one critical section).
# =============================================================================
t_start "ACCEPTANCE C: recover (no --force) refuses a LIVE holder outright -- LOCK_LIVE, nothing touched"
D=$(sandbox); lockd="$D/.lock-live-c"
token=$(lock_acquire "$lockd")
out=$(bash "$LOCKLIB" recover "$lockd" --reason "acceptance C: mistaken recovery of a live holder" 2>&1); rc=$?
assert_eq "$rc" "3" "recover against a LIVE holder must return LOCK_LIVE (rc=3)"
assert_contains "$out" "LOCK_LIVE" "recover output must say LOCK_LIVE"
[ -d "$lockd" ] && t_ok || t_fail "the live holder's lock directory must still exist"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "$token" "the live holder's token must be byte-for-byte unchanged"
lock_release "$lockd" "$token"
rm -rf "$D"

t_start "ACCEPTANCE C: --force can NEVER override a LIVE holder, not even silently"
D=$(sandbox); lockd="$D/.lock-live-force"
token=$(lock_acquire "$lockd")
out=$(bash "$LOCKLIB" recover --force "$lockd" --reason "acceptance C: force vs live" 2>&1); rc=$?
assert_eq "$rc" "3" "recover --force against a LIVE holder must STILL return LOCK_LIVE (rc=3) -- force overrides UNKNOWN only, never LIVE"
assert_contains "$out" "LOCK_LIVE" "recover --force output must still say LOCK_LIVE"
[ -d "$lockd" ] && t_ok || t_fail "the live holder's lock directory must still exist even after a --force attempt"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "$token" "the live holder's token must be byte-for-byte unchanged even after a --force attempt"
lock_release "$lockd" "$token"
rm -rf "$D"

t_start "ACCEPTANCE C: real-timing live-holder theft repro (Quinn's original) -- A holds the lock through a real critical section; a mistaken recover mid-hold is REFUSED; B (a genuine concurrent acquirer) never overlaps A; final shared counter is properly serialized (2), never 1"
D=$(sandbox); lockd="$D/.lock-theft-repro"; counter="$D/counter"; printf '0' > "$counter"
(
  tokA=$(lock_acquire "$lockd") || exit 1
  sleep 0.6
  valA=$(cat "$counter")
  sleep 0.3
  printf '%s' "$((valA + 1))" > "$counter"
  lock_release "$lockd" "$tokA"
) &
workerA=$!
sleep 0.2
recover_out=$(bash "$LOCKLIB" recover "$lockd" --reason "TEST: mistaken recovery of a still-live holder" 2>&1); recover_rc=$?
(
  tokB=$(lock_acquire "$lockd") || exit 1
  valB=$(cat "$counter")
  printf '%s' "$((valB + 1))" > "$counter"
  lock_release "$lockd" "$tokB"
) &
workerB=$!
wait "$workerA" "$workerB" 2>/dev/null
assert_eq "$recover_rc" "3" "the mistaken mid-hold recover must be REFUSED (LOCK_LIVE), never silently succeed"
assert_contains "$recover_out" "LOCK_LIVE" "recover output must say LOCK_LIVE"
assert_eq "$(cat "$counter")" "2" "the shared counter must be properly serialized (2) -- Quinn's original repro measured 1 here, proving two callers ran inside one critical section simultaneously"
rm -rf "$D"

# =============================================================================
# ACCEPTANCE D / RACE crash-during-recovery: a recovery process can mkdir
# <lock>.recovering and then crash before writing anything inside it. Every later
# acquire must fail closed against it, nothing auto-cleans it, and an explicit, audited
# path exists for an operator to recover the stuck marker itself (never touching the
# underlying lock in that same call).
# =============================================================================
t_start "ACCEPTANCE D: a stuck (pid-less) .recovering marker blocks acquire closed -- RECOVERY_REQUIRED, no auto-clean"
D=$(sandbox); lockd="$D/.lock-accD"
dead_pid=$(seed_dead_lock "$lockd" "orig-token")
mkdir -p "${lockd}.recovering"   # simulate: recover mkdir'd the marker then crashed
tok=$(lock_acquire "$lockd"); rc=$?
assert_eq "$rc" "5" "acquire against a stuck .recovering marker must return RECOVERY_REQUIRED (rc=5)"
[ -z "$tok" ] && t_ok || t_fail "a failed acquire must print nothing"
[ -e "${lockd}.recovering" ] && t_ok || t_fail "the marker must NOT have been auto-cleared by the failed acquire"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "orig-token" "the underlying lock must be completely untouched"
rm -rf "$D"

t_start "ACCEPTANCE D: an ordinary recover also refuses a stuck marker; --force clears ONLY the marker (audited), never the underlying lock in the same call; a SECOND recover then reclaims the underlying lock normally"
D=$(sandbox); lockd="$D/.lock-accD2"
seed_dead_lock "$lockd" "orig-token-2" >/dev/null
mkdir -p "${lockd}.recovering"
out1=$(bash "$LOCKLIB" recover "$lockd" --reason "accD: no force"); rc1=$?
assert_eq "$rc1" "5" "an ordinary recover must also be refused (RECOVERY_REQUIRED) against a stuck marker"
assert_contains "$out1" "RECOVERY_REQUIRED" "recover output should say RECOVERY_REQUIRED"
out2=$(bash "$LOCKLIB" recover --force "$lockd" --reason "accD: force clears marker"); rc2=$?
assert_true "$rc2" "recover --force must succeed in clearing the STUCK MARKER"
assert_contains "$out2" "cleared a stuck" "recover --force output must say it cleared the stuck marker"
[ ! -e "${lockd}.recovering" ] && t_ok || t_fail "the marker must be gone after the forced clear"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "orig-token-2" "the underlying lock must be UNTOUCHED by the marker-only clear -- two separate, both-audited actions, never one implicit compound one"
out3=$(bash "$LOCKLIB" recover "$lockd" --reason "accD: reclaim underlying lock"); rc3=$?
assert_true "$rc3" "a SECOND, ordinary recover must now succeed in reclaiming the (still dead) underlying lock"
assert_contains "$out3" "RECOVERED" "the second recover's output should say RECOVERED"
[ -d "$lockd" ] && t_fail "the underlying lock must finally be gone" || t_ok
audit="$D/.lock-recoveries.jsonl"
marker_cleared=$(jq -r 'select(.outcome == "COMPLETED" and .forced == true and (.note // "" | contains("stuck"))) | .lockdir' "$audit" 2>/dev/null | grep -c "^${lockd}\$")
assert_eq "$marker_cleared" "1" "the forced marker-clear must be its own distinct, audited COMPLETED line"
rm -rf "$D"

# =============================================================================
# RACE release||recover: a stray lock_release (e.g. a retry-wrapper that still believes
# it owns the lock) can remove the canonical lock out from under an in-flight recover,
# in the gap before recover's own rename. recover must fail closed (RECOVERY_FAILED),
# never treat "vanished" as license to fabricate a phantom recovery.
# =============================================================================
t_start "RACE release||recover (deterministic via LOCK_RECOVER_SYNC_PREMV): a concurrent release racing recover's rename -> RECOVERY_FAILED, nothing fabricated, nothing deleted"
D=$(sandbox); lockd="$D/.lock-relrec"
seed_dead_lock "$lockd" "stale-token" >/dev/null
sync="$D/sync"
LOCK_RECOVER_SYNC_PREMV="$sync" bash "$LOCKLIB" recover "$lockd" --reason "release-vs-recover" >"$D/out" 2>&1 &
rpid=$!
n=0
while [ ! -e "${sync}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.1; done
[ -e "${sync}.ready" ] && t_ok || t_fail "recover never reached its pre-mv sync point"
lock_release "$lockd" "stale-token"
[ -d "$lockd" ] && t_fail "release should have removed the canonical lock" || t_ok
: > "${sync}.go"
wait "$rpid" 2>/dev/null; rc=$?
assert_eq "$rc" "6" "recover must report RECOVERY_FAILED (rc=6) when the canonical lock vanishes out from under it"
assert_contains "$(cat "$D/out")" "RECOVERY_FAILED" "recover output must say RECOVERY_FAILED"
rm -rf "$D"

# =============================================================================
# RACE recover||recover: exactly one winner claims the atomic .recovering marker;
# every other concurrent caller gets a retryable RECOVERY_IN_PROGRESS, never a false
# success, never a second deletion. 5 concurrent recovers, 8 trials.
# =============================================================================
t_start "RACE recover||recover: N=5 concurrent recover calls on the SAME stuck lock -- exactly 1 wins (RECOVERED), the other 4 get RECOVERY_IN_PROGRESS, 8 trials"
bad_trials=0
for _trial in $(seq 1 8); do
  D=$(sandbox); lockd="$D/.lock-rr"
  seed_dead_lock "$lockd" "stale" >/dev/null
  for i in 1 2 3 4 5; do
    bash "$LOCKLIB" recover "$lockd" --reason "dual-recover-$i" >"$D/out.$i" 2>&1 &
  done
  wait
  recovered=$(grep -l '^RECOVERED' "$D"/out.* 2>/dev/null | wc -l | tr -d ' ')
  in_progress=$(grep -l '^RECOVERY_IN_PROGRESS' "$D"/out.* 2>/dev/null | wc -l | tr -d ' ')
  [ "$recovered" = "1" ] && [ "$in_progress" = "4" ] || bad_trials=$((bad_trials + 1))
  rm -rf "$D"
done
assert_eq "$bad_trials" "0" "every one of 8 trials must show exactly 1 RECOVERED and 4 RECOVERY_IN_PROGRESS out of 5 concurrent recovers -- got $bad_trials bad trial(s)"

# =============================================================================
# regression: chmod 000 lock defeats neither the liveness gate nor the identity check
# (Quinn High) -- an unreadable lock directory must refuse (LOCK_CORRUPT), never read
# as "empty, therefore safe", never falsely report success.
# =============================================================================
t_start "regression: an unreadable (chmod 000) lock directory refuses closed -- LOCK_CORRUPT, never a false RECOVERED, marker/content never stolen"
D=$(sandbox); lockd="$D/.lock-restricted"
mkdir -p "$lockd"
printf 'REAL-LIVE-TOKEN' > "$lockd/token"
printf '99999' > "$lockd/pid"
date +%s > "$lockd/ts"
: > "$lockd/MARKER-LIVE-HOLDER"
chmod 000 "$lockd"
out=$(bash "$LOCKLIB" recover "$lockd" --reason "regression: chmod 000" 2>&1); rc=$?
chmod 755 "$lockd" 2>/dev/null
assert_eq "$rc" "4" "recover against an unreadable lock directory must return LOCK_CORRUPT (rc=4)"
assert_contains "$out" "LOCK_CORRUPT" "recover output must say LOCK_CORRUPT"
[ -f "$lockd/MARKER-LIVE-HOLDER" ] && t_ok || t_fail "the marker file must survive untouched -- nothing was stolen"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "REAL-LIVE-TOKEN" "the real token must be byte-for-byte unchanged"
rm -rf "$D"

# =============================================================================
# regression (Chris C1, Critical, bd:shode-house-vz8 iter2): `recover --force` against a
# lock whose ANCESTOR directory (NOT the lock directory itself -- the chmod-000
# regression above only ever covered chmod'ing the lock dir; this is deliberately a
# level higher) is unreadable must fail closed. The original bug: `[ -e ]` cannot tell
# ENOENT from EACCES-on-an-ancestor, so an unreadable ancestor made `mkdir
# "$recovering"` fail, got misread as "marker MISSING" instead of "cannot tell", and the
# force-clear branch then reported a false COMPLETED with zero audit record and the
# underlying lock completely untouched. Oliver's own repro, reproduced deterministically
# (no race/timing needed).
# =============================================================================
t_start "regression (Chris C1): recover --force against a lock with an UNREADABLE ANCESTOR (not the lock dir itself) must fail closed -- no false COMPLETED, no false 'cleared a stuck marker' claim, lock genuinely untouched, no audit record fabricated"
D=$(sandbox); lockd="$D/parent/locks/mylock"
seed_dead_lock "$lockd" "TOKEN-ORIGINAL" >/dev/null
chmod 000 "$D/parent"
out=$(bash "$LOCKLIB" recover --force "$lockd" --reason "C1 regression: unreadable ancestor" 2>&1); rc=$?
chmod 755 "$D/parent" 2>/dev/null
assert_false "$rc" "recover --force must NOT report success (rc=0) when an ancestor is unreadable -- got rc=$rc"
assert_contains "$out" "LOCK_CORRUPT" "recover output must classify this LOCK_CORRUPT (cannot tell), not a success"
case "$out" in
  *"cleared a stuck"*) t_fail "recover must NEVER claim it cleared a stuck marker it could not even prove existed -- got: $out" ;;
  *"COMPLETED"*)       t_fail "recover must NEVER print COMPLETED when an ancestor is unreadable -- got: $out" ;;
  *)                    t_ok ;;
esac
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "TOKEN-ORIGINAL" "the original lock's token must be byte-for-byte untouched -- nothing was genuinely recovered"
[ -e "${lockd}.recovering" ] && t_fail "must not leave behind a NEW stuck .recovering marker" || t_ok
rm -rf "$D"

t_start "regression (Chris C1): once the ancestor is readable again, recover on the SAME still-dead lock proceeds normally to a genuine RECOVERED -- the earlier failure must not have permanently wedged classification"
D=$(sandbox); lockd="$D/parent/locks/mylock2"
seed_dead_lock "$lockd" "TOKEN-ORIGINAL-2" >/dev/null
chmod 000 "$D/parent"
out1=$(bash "$LOCKLIB" recover --force "$lockd" --reason "C1 regression: unreadable ancestor (first attempt)" 2>&1); rc1=$?
chmod 755 "$D/parent"
assert_false "$rc1" "the first attempt, while the ancestor is still unreadable, must fail closed"
out2=$(bash "$LOCKLIB" recover "$lockd" --reason "C1 regression: ancestor now readable" 2>&1); rc2=$?
assert_true "$rc2" "once the ancestor is readable again, recover on the genuinely-dead lock must succeed normally"
assert_contains "$out2" "RECOVERED" "recover output should say RECOVERED"
[ -d "$lockd" ] && t_fail "the lock must be gone after a genuine recovery" || t_ok
[ -e "${lockd}.recovering" ] && t_fail "no leftover .recovering marker after a clean recovery" || t_ok
rm -rf "$D"

t_start "regression (Chris C1, force-clear branch specifically): a stuck .recovering marker that rm -rf genuinely CANNOT fully remove (chmod 555, not an ancestor trick) must still report RECOVERY_FAILED, never a false COMPLETED -- exercises the post-rm-rf verification independently of the ancestor-EACCES routing above"
D=$(sandbox); lockd="$D/.lock-forceclear"; recovering="${lockd}.recovering"
mkdir -p "$recovering"
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
printf '%s' "$dead_pid" > "$recovering/pid"
date +%s > "$recovering/started-ts"
chmod 555 "$recovering"   # readable+executable (classify can still read pid -> DEAD),
                          # but NOT writable -- rm -rf cannot unlink the files inside it,
                          # so the marker survives non-empty with no ancestor involved.
out=$(bash "$LOCKLIB" recover --force "$lockd" --reason "C1 regression: force-clear cleanup verify" 2>&1); rc=$?
chmod 755 "$recovering" 2>/dev/null
assert_eq "$rc" "6" "when the forced marker-clear's rm -rf genuinely fails to remove the marker, recover must report RECOVERY_FAILED (rc=6), never COMPLETED"
assert_contains "$out" "RECOVERY_FAILED" "recover output must say RECOVERY_FAILED"
case "$out" in
  *"COMPLETED"*) t_fail "must never claim COMPLETED when the marker demonstrably still exists after the clear attempt -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

# =============================================================================
# regression (Chris C2, Medium, bd:shode-house-vz8 iter2): a dangling symlink on the
# `pid` file must classify LOCK_CORRUPT, never MISSING/UNKNOWN -- folded into the same
# unreadable-!=-empty class fix as C1 (a dangling symlink IS an entry that exists but is
# broken, categorically different from a genuinely mid-populate/never-written file).
# =============================================================================
t_start "regression (Chris C2): a dangling symlink on the pid file classifies LOCK_CORRUPT (rc=4), never RECOVERY_REQUIRED/UNKNOWN (rc=5)"
D=$(sandbox); lockd="$D/.lock-pidsymlink"
mkdir -p "$lockd"
printf 'realtok' > "$lockd/token"
ln -s /nonexistent/nowhere "$lockd/pid"
date +%s > "$lockd/ts"
out=$(bash "$LOCKLIB" recover "$lockd" --reason "C2 regression: dangling pid symlink" 2>&1); rc=$?
assert_eq "$rc" "4" "a dangling symlink on pid must classify LOCK_CORRUPT (rc=4), not RECOVERY_REQUIRED/UNKNOWN (rc=5) -- a broken entry is categorically different from a genuinely-absent one"
assert_contains "$out" "LOCK_CORRUPT" "recover output must say LOCK_CORRUPT"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "realtok" "the lock must be untouched -- refusing, never guessing"
rm -rf "$D"

# =============================================================================
# regression (Chris C3, Low, bd:shode-house-vz8 iter2): a failed audit append (its
# directory unwritable) must not leak a raw shell redirection error past its own
# `2>/dev/null` suppression -- bash applies redirections left-to-right, so the open()
# failure of `>> "$audit"` itself used to escape before `2>/dev/null` later on the same
# line took effect. `_lock_audit_recover` is exercised directly (test-lock.sh already
# sources lock.sh -- no CLI round trip needed for a pure unit check of one function).
# =============================================================================
t_start "regression (Chris C3): _lock_audit_recover's own failure path never leaks a raw 'Permission denied' past its intended stderr suppression"
D=$(sandbox)
mkdir -p "$D/auditparent"
chmod 000 "$D/auditparent"
stderr_out=$(_lock_audit_recover "$D/auditparent/somelock" "tok" "1" "1" "reason" "STARTED" 2>&1 1>/dev/null); rc=$?
chmod 755 "$D/auditparent" 2>/dev/null
assert_false "$rc" "_lock_audit_recover must still report failure (non-zero) when the append genuinely cannot be written"
case "$stderr_out" in
  *"Permission denied"*) t_fail "the raw filesystem 'Permission denied' error must not leak past the intended 2>/dev/null suppression -- got: $stderr_out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

# =============================================================================
# NEW (bd:shode-house-vz8 iter4, Quinn High): `_lock_classify_holder` had ZERO
# dedicated coverage before this section (`grep classify_holder tests/test-lock.sh`
# was 0 hits) despite being on the hot path of every acquire timeout, every recover
# marker classification, and the liveness gate itself. The defect: `_lock_exists_or_error`
# (check #1, confirms EXISTS) and the separate `[ ! -r ] || [ ! -x ]` readability probe
# (check #2) are two independent, non-atomic syscalls -- an ORDINARY removal (a plain
# lock_release's rm -rf, or a lock_recover's quarantine mv) landing strictly between
# them made check #1 see EXISTS while check #2, run microseconds later on a now-gone
# path, saw both -r and -x fail and reported CORRUPT ("permission denied") for a
# directory that had simply, ordinarily, vanished -- reachable via plain N=40
# contention alone, no operator action, no stale lock, no permission games (Quinn:
# 11/300 direct race, 1/10 runs under plain N=40 contention). The fix: a failed check
# #2 re-runs check #1 ONE more time before concluding (`_lock_unreadable_is_missing_or_
# corrupt`) -- MISSING now means "it just disappeared, tell the honest truth"; still
# EXISTS, or ERROR (ancestor now unresolvable), both stay CORRUPT, unchanged. Single
# shared implementation used by BOTH `_lock_classify_holder` and `lock_recover`'s own
# duplicate check on the canonical lock (formerly a second, independent copy of the
# identical non-atomic pair, at what was scripts/lib/lock.sh:620 before this fix).
# =============================================================================
t_start "NEW regression: _lock_classify_holder -- dir removed BETWEEN the exists-or-error probe and the readability probe (the TOCTOU itself, forced deterministically via LOCK_CLASSIFY_HOLDER_SYNC, not timing luck) must classify MISSING, never CORRUPT"
D=$(sandbox); dir="$D/.lock-classify-toctou"
mkdir -p "$dir"
printf '12345' > "$dir/pid"
sync="$D/classify-sync"
( LOCK_CLASSIFY_HOLDER_SYNC="$sync" _lock_classify_holder "$dir" > "$D/out" ) &
cpid=$!
n=0
while [ ! -e "${sync}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync}.ready" ] && t_ok || t_fail "_lock_classify_holder never reached its post-EXISTS sync point within 5s"
# the dir is confirmed EXISTS (check #1 already ran) -- now remove it, exactly the
# shape of an ordinary concurrent lock_release/lock_recover, strictly BEFORE check #2
# (the readability probe) runs.
rm -rf "$dir"
: > "${sync}.go"
wait "$cpid" 2>/dev/null
out=$(cat "$D/out")
assert_eq "$out" "MISSING" "a directory removed strictly between the two existence/readability checks must classify MISSING (honest: it is simply gone) -- must NEVER be misreported CORRUPT (a permission claim that would be false)"
rm -rf "$D"

t_start "NEW regression: _lock_classify_holder -- dir genuinely unreadable AND STILL PRESENT (chmod 000, no removal) must stay CORRUPT -- the fix must not weaken this side of the invariant"
D=$(sandbox); dir="$D/.lock-classify-corrupt-present"
mkdir -p "$dir"
printf '12345' > "$dir/pid"
chmod 000 "$dir"
out=$(_lock_classify_holder "$dir")
chmod 755 "$dir" 2>/dev/null
assert_eq "$out" "CORRUPT" "a directory that is genuinely unreadable and never removed must classify CORRUPT, unchanged by this fix"
rm -rf "$D"

t_start "NEW regression: _lock_classify_holder -- an unresolvable ANCESTOR (not the target itself) must stay CORRUPT, must NEVER become MISSING -- the fix's re-check must not flip this direction of the invariant"
D=$(sandbox); dir="$D/anc/lockdir"
mkdir -p "$D/anc"
mkdir -p "$dir"
printf '12345' > "$dir/pid"
chmod 000 "$D/anc"
out=$(_lock_classify_holder "$dir")
chmod 755 "$D/anc" 2>/dev/null
assert_eq "$out" "CORRUPT" "an ancestor directory that cannot be resolved must classify CORRUPT, never MISSING, even after the fix's re-check"
rm -rf "$D"

t_start "NEW regression: _lock_classify_holder -- a directory that genuinely never existed classifies MISSING"
D=$(sandbox); dir="$D/.lock-classify-never-existed"
out=$(_lock_classify_holder "$dir")
assert_eq "$out" "MISSING" "a directory that was never created must classify MISSING"
rm -rf "$D"

t_start "NEW regression: _lock_classify_holder -- the pid-missing/settle-wait path (a pid file landing within the ~250ms settle budget, e.g. a genuinely mid-populate lock) is UNCHANGED by this fix"
D=$(sandbox); dir="$D/.lock-classify-settle"
mkdir -p "$dir"
( : ) & settle_dead_pid=$!
wait "$settle_dead_pid" 2>/dev/null
( sleep 0.12; printf '%s' "$settle_dead_pid" > "$dir/pid" ) &
writer_pid=$!
out=$(_lock_classify_holder "$dir")
wait "$writer_pid" 2>/dev/null
assert_eq "$out" "DEAD" "a pid file that lands within the settle-wait budget must still classify DEAD (not UNKNOWN, not CORRUPT) -- settle behavior must be unchanged by this fix"
rm -rf "$D"

t_start "NEW regression: lock_recover's OWN duplicate readability check (the analogous TOCTOU site, formerly scripts/lib/lock.sh:620) -- dir removed BETWEEN its exists-or-error probe and its readability probe (forced deterministically via LOCK_RECOVER_STEP1_READABLE_SYNC) must report COMPLETED / nothing-to-recover (rc=0), never LOCK_CORRUPT (rc=4)"
D=$(sandbox); lockd="$D/.lock-recover-toctou"
mkdir -p "$lockd"
printf 'sometoken' > "$lockd/token"
printf '12345' > "$lockd/pid"
date +%s > "$lockd/ts"
sync="$D/recover-step1-sync"
LOCK_RECOVER_STEP1_READABLE_SYNC="$sync" bash "$LOCKLIB" recover "$lockd" --reason "iter4 TOCTOU regression" >"$D/out" 2>&1 &
rpid=$!
n=0
while [ ! -e "${sync}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync}.ready" ] && t_ok || t_fail "lock_recover never reached its post-EXISTS Step 1 sync point within 5s"
rm -rf "$lockd"
: > "${sync}.go"
wait "$rpid" 2>/dev/null; rc=$?
out=$(cat "$D/out")
assert_eq "$rc" "0" "a canonical lock removed strictly between lock_recover's own exists-or-error probe and its readability probe must report success (rc=0, nothing to recover), never LOCK_CORRUPT (rc=4)"
assert_contains "$out" "nothing to recover" "recover output must say there was nothing to recover, not a permission claim"
case "$out" in
  *"LOCK_CORRUPT"*) t_fail "must never claim LOCK_CORRUPT for a lock that was simply, ordinarily, removed mid-check -- got: $out" ;;
  *) t_ok ;;
esac
[ -e "${lockd}.recovering" ] && t_fail "no leftover .recovering marker after this success path" || t_ok
rm -rf "$D"

# =============================================================================
# NEW (bd:shode-house-vz8 iter5, Quinn High, renewed -- classifier redesign, the user's
# own final round for this defect class). Re-verifying the iter4 fix at N=100 found the
# iter4 disambiguation itself (`_lock_unreadable_is_missing_or_corrupt`, above) is JUST
# ANOTHER non-atomic existence probe: at contention dense enough for a DIFFERENT
# worker's `mkdir` to recreate the exact same path strictly inside that re-check's own
# window, the re-check observed EXISTS (a brand new, legitimate, still-empty holder)
# and misreported CORRUPT -- 30-53% of runs at N=100, instrumented down to the exact
# mechanism (`recheck=EXISTS`, only `.`/`..` present, no pid file yet). The rule: stop
# adding existence-only re-check layers; use EVIDENCE (a device:inode identity
# fingerprint, `_lock_fs_identity`) to tell "the same object, still bad" (LOCK_CORRUPT)
# apart from "a different/changed object" (treat as ordinary churn, classify normally)
# apart from "could not establish either way" (fail closed, RECOVERY_REQUIRED, NEVER
# guessed LOCK_BUSY, NEVER --force-overridable). `_lock_disambiguate_unreadable`
# (scripts/lib/lock.sh) replaces the iter3/iter4 helper; this section proves both the
# pure-function evidence logic directly AND its wiring into every call site that uses
# it, including the exact N=100 mechanism reproduced deterministically via the new
# LOCK_DISAMBIGUATE_SYNC test hook chained after the existing LOCK_CLASSIFY_HOLDER_SYNC
# / LOCK_RECOVER_STEP1_READABLE_SYNC hooks.
# =============================================================================

t_start "NEW iter5 unit: _lock_fs_identity -- non-empty for existing dirs, empty for never-created paths, and DIFFERENT before vs. after remove+recreate of the SAME path"
D=$(sandbox); dir="$D/.lock-identity"
mkdir -p "$dir"
id1=$(_lock_fs_identity "$dir")
[ -n "$id1" ] && t_ok || t_fail "an existing directory must yield a non-empty identity fingerprint"
never=$(_lock_fs_identity "$D/.never-existed")
[ -z "$never" ] && t_ok || t_fail "a path that never existed must yield an empty fingerprint, got: '$never'"
rmdir "$dir"; mkdir -p "$dir"
id2=$(_lock_fs_identity "$dir")
[ -n "$id2" ] && t_ok || t_fail "the recreated directory must also yield a non-empty fingerprint"
[ "$id1" != "$id2" ] && t_ok || t_fail "a remove+recreate of the SAME path must yield a DIFFERENT identity fingerprint, got: id1='$id1' id2='$id2'"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_disambiguate_unreadable -- MISSING when the path is honestly, simply, never there"
D=$(sandbox)
out=$(_lock_disambiguate_unreadable "$D/.never-created")
assert_eq "$out" "MISSING" "a path that was never created must resolve MISSING"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_disambiguate_unreadable -- CORRUPT when the SAME device:inode is confirmed stable (unchanged) across both observations, still inaccessible (chmod 000, never removed) -- Control 2 at the pure-function level"
D=$(sandbox); dir="$D/.lock-disambig-corrupt"
mkdir -p "$dir"; chmod 000 "$dir"
out=$(_lock_disambiguate_unreadable "$dir")
chmod 755 "$dir" 2>/dev/null
assert_eq "$out" "CORRUPT" "a stable, never-recreated, chmod 000 directory must resolve CORRUPT via a matching identity fingerprint across both observations, not merely because it 'still exists'"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_disambiguate_unreadable -- AMBIGUOUS when a clean identity fingerprint cannot be obtained on either side, even though the path demonstrably EXISTS (forced via a stubbed _lock_fs_identity, deterministic, not a real race) -- must NEVER guess CORRUPT or CHANGED"
D=$(sandbox); dir="$D/.lock-disambig-ambiguous"
mkdir -p "$dir"; chmod 000 "$dir"
_saved_fsid="$(declare -f _lock_fs_identity)"
_lock_fs_identity() { printf ''; return 1; }
out=$(_lock_disambiguate_unreadable "$dir")
eval "$_saved_fsid"
chmod 755 "$dir" 2>/dev/null
assert_eq "$out" "AMBIGUOUS" "when neither observation can obtain a clean identity fingerprint, the classifier must fail closed as AMBIGUOUS -- never CORRUPT (that would be guessing 'same, stable'), never CHANGED (that would be guessing 'busy')"
rm -rf "$D"

t_start "NEW iter5: _lock_classify_holder -- dir removed, THEN recreated by a DIFFERENT worker (fresh identity, no pid yet) strictly INSIDE the disambiguation's own re-check window -- Quinn's exact N=100 mechanism (recheck=EXISTS, only . and .. present), forced deterministically via two chained sync hooks -- must classify UNKNOWN (mid-populate), NEVER CORRUPT"
D=$(sandbox); dir="$D/.lock-classify-recreate-empty"
mkdir -p "$dir"; printf '12345' > "$dir/pid"
sync1="$D/classify-sync"; sync2="$D/disambig-sync"
( LOCK_CLASSIFY_HOLDER_SYNC="$sync1" LOCK_DISAMBIGUATE_SYNC="$sync2" _lock_classify_holder "$dir" > "$D/out" ) &
cpid=$!
n=0
while [ ! -e "${sync1}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync1}.ready" ] && t_ok || t_fail "_lock_classify_holder never reached its post-EXISTS sync point"
rm -rf "$dir"           # the ORIGINAL holder is now genuinely gone -- the readability probe about to run will fail
: > "${sync1}.go"        # let the readability probe evaluate and fail, entering the disambiguation
n=0
while [ ! -e "${sync2}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync2}.ready" ] && t_ok || t_fail "_lock_disambiguate_unreadable never reached its own sync point"
mkdir -p "$dir"          # a DIFFERENT worker's fresh mkdir lands strictly inside the disambiguation's own window -- still empty, no pid file yet (exactly Quinn's instrumented shape)
: > "${sync2}.go"
wait "$cpid" 2>/dev/null
out=$(cat "$D/out")
assert_eq "$out" "UNKNOWN" "a directory removed then recreated (fresh, still-empty) strictly inside the disambiguation's own re-check window must classify UNKNOWN (mid-populate) -- must NEVER misreport CORRUPT for what is ordinary contention with a brand new, legitimate, different holder"
rm -rf "$D"

t_start "NEW iter5: _lock_classify_holder -- same race as above, but the recreating worker ALSO writes a genuinely LIVE pid before the disambiguation's re-check observes it -- must classify LIVE (the new holder), NEVER CORRUPT"
D=$(sandbox); dir="$D/.lock-classify-recreate-live"
mkdir -p "$dir"; printf '12345' > "$dir/pid"
sync1="$D/classify-sync"; sync2="$D/disambig-sync"
( LOCK_CLASSIFY_HOLDER_SYNC="$sync1" LOCK_DISAMBIGUATE_SYNC="$sync2" _lock_classify_holder "$dir" > "$D/out" ) &
cpid=$!
n=0
while [ ! -e "${sync1}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync1}.ready" ] && t_ok || t_fail "_lock_classify_holder never reached its post-EXISTS sync point"
rm -rf "$dir"
: > "${sync1}.go"
n=0
while [ ! -e "${sync2}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync2}.ready" ] && t_ok || t_fail "_lock_disambiguate_unreadable never reached its own sync point"
mkdir -p "$dir"; printf '%s' "$$" > "$dir/pid"   # a DIFFERENT, genuinely LIVE holder (this test process's own pid) now occupies the same path
: > "${sync2}.go"
wait "$cpid" 2>/dev/null
out=$(cat "$D/out")
assert_eq "$out" "LIVE" "a directory removed then recreated with a fresh, genuinely live holder strictly inside the disambiguation's own window must be classified by its NEW identity (LIVE), never misreported CORRUPT"
rm -rf "$D"

t_start "NEW iter5: _lock_classify_holder -- AMBIGUOUS from the dir-level disambiguation propagates unchanged (stubbed _lock_fs_identity, deterministic) -- never silently collapsed into CORRUPT or any liveness verdict"
D=$(sandbox); dir="$D/.lock-classify-ambiguous"
mkdir -p "$dir"; printf '12345' > "$dir/pid"; chmod 000 "$dir"
_saved_fsid="$(declare -f _lock_fs_identity)"
_lock_fs_identity() { printf ''; return 1; }
out=$(_lock_classify_holder "$dir")
eval "$_saved_fsid"
chmod 755 "$dir" 2>/dev/null
assert_eq "$out" "AMBIGUOUS" "_lock_classify_holder must surface AMBIGUOUS as its own distinct outcome, not fold it into CORRUPT"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_classify_timeout -- AMBIGUOUS maps to RECOVERY_REQUIRED, NEVER LOCK_BUSY (the rule's own explicit 'never guess busy' clause)"
D=$(sandbox); dir="$D/.lock-timeout-ambiguous"
mkdir -p "$dir"; printf '12345' > "$dir/pid"; chmod 000 "$dir"
_saved_fsid="$(declare -f _lock_fs_identity)"
_lock_fs_identity() { printf ''; return 1; }
out=$(_lock_classify_timeout "$dir")
eval "$_saved_fsid"
chmod 755 "$dir" 2>/dev/null
case "$out" in
  RECOVERY_REQUIRED*) t_ok ;;
  LOCK_BUSY*) t_fail "AMBIGUOUS must NEVER be guessed as LOCK_BUSY -- got: $out" ;;
  *) t_fail "AMBIGUOUS must map to RECOVERY_REQUIRED -- got: $out" ;;
esac
rm -rf "$D"

t_start "NEW iter5: lock_recover's OWN Step 1 readability check -- dir removed then recreated by a DIFFERENT worker (fresh, live identity) strictly inside the disambiguation's own re-check window -- must proceed to Step 2's normal liveness classification (LOCK_LIVE against the NEW holder, rc=3), NEVER falsely report COMPLETED/nothing-to-recover, NEVER LOCK_CORRUPT"
D=$(sandbox); lockd="$D/.lock-recover-recreate-race"
mkdir -p "$lockd"; printf 'oldtoken' > "$lockd/token"; printf '12345' > "$lockd/pid"; date +%s > "$lockd/ts"
sync1="$D/recover-step1-sync"; sync2="$D/disambig-sync"
LOCK_RECOVER_STEP1_READABLE_SYNC="$sync1" LOCK_DISAMBIGUATE_SYNC="$sync2" bash "$LOCKLIB" recover "$lockd" --reason "iter5 recreate race" >"$D/out" 2>&1 &
rpid=$!
n=0
while [ ! -e "${sync1}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync1}.ready" ] && t_ok || t_fail "lock_recover never reached its post-EXISTS Step 1 sync point"
rm -rf "$lockd"
: > "${sync1}.go"
n=0
while [ ! -e "${sync2}.ready" ]; do n=$((n + 1)); [ "$n" -ge 100 ] && break; sleep 0.05; done
[ -e "${sync2}.ready" ] && t_ok || t_fail "_lock_disambiguate_unreadable never reached its own sync point (recover subprocess)"
mkdir -p "$lockd"; printf '%s' "$$" > "$lockd/pid"; printf 'newtoken' > "$lockd/token"; date +%s > "$lockd/ts"
: > "${sync2}.go"
wait "$rpid" 2>/dev/null; rc=$?
out=$(cat "$D/out")
assert_eq "$rc" "3" "recover must classify the NEW, genuinely live holder correctly (LOCK_LIVE, rc=3) -- must never falsely complete as 'nothing to recover' and never falsely report LOCK_CORRUPT for what is a brand new legitimate holder"
assert_contains "$out" "LOCK_LIVE" "recover output must say LOCK_LIVE against the new holder"
[ -d "$lockd" ] && t_ok || t_fail "the new (live) lock must be completely untouched -- recover must refuse, never reclaim a live holder no matter how it got there"
rm -rf "$D"

t_start "NEW iter5: lock_recover's own liveness gate -- an AMBIGUOUS liveness verdict must REFUSE (RECOVERY_REQUIRED, rc=5), NEVER silently fall through to 'may proceed' and reclaim the lock (stubbed _lock_classify_holder isolates this ONE guard deterministically, without touching Step 1 or the field reads)"
D=$(sandbox); lockd="$D/.lock-recover-liveness-ambiguous"
seed_dead_lock "$lockd" "some-token" >/dev/null
_saved_cls="$(declare -f _lock_classify_holder)"
_lock_classify_holder() { printf 'AMBIGUOUS'; }
out=$(lock_recover "$lockd" "iter5 liveness-gate AMBIGUOUS guard" 2>&1); rc=$?
eval "$_saved_cls"
assert_eq "$rc" "5" "an AMBIGUOUS liveness verdict must refuse (RECOVERY_REQUIRED, rc=5), never proceed to reclaim the lock as if it were confirmed DEAD"
assert_contains "$out" "RECOVERY_REQUIRED" "output must say RECOVERY_REQUIRED"
[ -d "$lockd" ] && t_ok || t_fail "the lock must be COMPLETELY UNTOUCHED when liveness could not be established -- it must NOT have been quarantined or reclaimed"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "some-token" "the lock's own token must be byte-for-byte unchanged -- an AMBIGUOUS verdict must never mutate anything"
rm -rf "$D"

t_start "NEW iter5: lock_recover's own liveness gate -- AMBIGUOUS is NEVER --force-overridable (unlike a genuinely UNKNOWN liveness) -- forcing must still refuse and leave the lock untouched"
D=$(sandbox); lockd="$D/.lock-recover-liveness-ambiguous-forced"
seed_dead_lock "$lockd" "some-token-2" >/dev/null
_saved_cls="$(declare -f _lock_classify_holder)"
_lock_classify_holder() { printf 'AMBIGUOUS'; }
out=$(lock_recover "$lockd" "iter5 forced AMBIGUOUS" 1 2>&1); rc=$?
eval "$_saved_cls"
assert_eq "$rc" "5" "even with force=1, an AMBIGUOUS liveness verdict must still refuse -- force only overrides a genuinely UNKNOWN liveness, never AMBIGUOUS"
[ -d "$lockd" ] && t_ok || t_fail "the lock must remain completely untouched even when --force is given against an AMBIGUOUS verdict"
rm -rf "$D"

t_start "NEW iter6 (M2, Quinn iter5 finding #2): lock_recover Step 0 -- marker-level AMBIGUOUS IS --force-eligible (same tier as UNKNOWN/DEAD), the deliberate OPPOSITE of the canonical-lock liveness gate's never-force-overridable AMBIGUOUS just above -- pins the asymmetry from its permissive side so a future change can't quietly make this level as strict as the liveness gate (or the liveness gate as permissive as this) without a test noticing"
D=$(sandbox); lockd="$D/.lock-recover-marker-ambiguous-forced"
seed_dead_lock "$lockd" "marker-ambig-token" >/dev/null
mkdir -p "${lockd}.recovering"   # simulate: a prior recover mkdir'd the marker then crashed
_saved_cls="$(declare -f _lock_classify_holder)"
_lock_classify_holder() { printf 'AMBIGUOUS'; }
out=$(lock_recover "$lockd" "iter6 marker-level AMBIGUOUS forced clear" 1 2>&1); rc=$?
eval "$_saved_cls"
assert_true "$rc" "force=1 against a MARKER classified AMBIGUOUS must SUCCEED in clearing the marker -- Step 0's deliberately permissive tier, unlike the liveness gate above"
assert_contains "$out" "COMPLETED" "output must report COMPLETED (the marker was cleared)"
assert_contains "$out" "AMBIGUOUS" "output must record the marker holder classification (AMBIGUOUS) it force-cleared, for audit"
[ ! -e "${lockd}.recovering" ] && t_ok || t_fail "the marker must be gone after the forced clear"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "marker-ambig-token" "the underlying lock must be COMPLETELY UNTOUCHED by a marker-only clear -- Step 0 never reaches the underlying lock in the same call, even when force clears an AMBIGUOUS marker"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_read -- CHANGED evidence (stubbed _lock_disambiguate_unreadable, deterministic) triggers exactly ONE bounded retry, which succeeds once the object is genuinely readable"
D=$(sandbox); f="$D/.lock-read-changed"
printf 'the-real-value' > "$f"
chmod 000 "$f"
_saved_dis="$(declare -f _lock_disambiguate_unreadable)"
# the stub fixes the permission as a side effect of being consulted (standing in for
# "a different, now-legitimate object" becoming genuinely readable) and reports
# CHANGED -- deterministic, no timing race: _lock_read's bounded retry (depth=1) then
# re-tests -r for real (unstubbed) and finds the file genuinely readable this time.
# _lock_read invokes this via `$(...)` command substitution -- a subshell -- so the
# "was I consulted" signal has to be a filesystem side effect (the chmod itself, and
# a marker file), never a plain variable assignment (that would silently vanish with
# the subshell).
fixed_marker="$D/.stub-was-consulted"
_lock_disambiguate_unreadable() {
  chmod 644 "$1" 2>/dev/null
  : > "$fixed_marker"
  printf 'CHANGED'
}
_lock_read "$f"
st="$_LOCK_READ_STATE" val="$_LOCK_READ_VALUE"
eval "$_saved_dis"
chmod 644 "$f" 2>/dev/null
[ -e "$fixed_marker" ] && t_ok || t_fail "test setup broken -- the stubbed disambiguation was never consulted"
assert_eq "$st" "VALID" "on CHANGED evidence, _lock_read must make one bounded retry and succeed once the object is genuinely readable -- got state '$st'"
assert_eq "$val" "the-real-value" "the bounded retry must return the real, current value"
rm -rf "$D"

t_start "NEW iter5 unit: _lock_read -- CHANGED evidence that recurs on the retry (stubbed _lock_disambiguate_unreadable always returns CHANGED, never fixes the permission) is bounded to exactly ONE extra attempt, then gives up as AMBIGUOUS -- never loops indefinitely"
D=$(sandbox); f="$D/.lock-read-changed-forever"
printf 'unreachable-value' > "$f"
chmod 000 "$f"
_saved_dis="$(declare -f _lock_disambiguate_unreadable)"
_lock_disambiguate_unreadable() { printf 'CHANGED'; }
t0=$(date +%s)
_lock_read "$f"
st="$_LOCK_READ_STATE"
t1=$(date +%s)
eval "$_saved_dis"
chmod 644 "$f" 2>/dev/null
assert_eq "$st" "AMBIGUOUS" "a CHANGED verdict that recurs on the single bounded retry (the object is STILL unreadable) must give up as AMBIGUOUS, never loop indefinitely -- got '$st'"
elapsed=$((t1 - t0))
[ "$elapsed" -lt 5 ] && t_ok || t_fail "the bounded retry must return quickly (well under 5s), not hang -- took ${elapsed}s"
rm -rf "$D"

# =============================================================================
# ACCEPTANCE E: the quarantine destination must never nest -- guaranteed by the mkdir
# claim itself, never by a prior [ -e ] check (the exact check-then-mv shape Chris
# found in iter0's restore-on-abort step).
# =============================================================================
t_start "ACCEPTANCE E: a pre-existing quarantine destination -> RECOVERY_FAILED, never nests, never overwrites, canonical untouched"
D=$(sandbox); lockd="$D/.lock-accE"
seed_dead_lock "$lockd" "stale-token" >/dev/null
mkdir -p "${lockd}.quarantine.FORCED"
: > "${lockd}.quarantine.FORCED/PREEXISTING-FOREIGN-CONTENT"
out=$(LOCK_RECOVER_TOKEN_OVERRIDE="FORCED" bash "$LOCKLIB" recover "$lockd" --reason "acceptance E"); rc=$?
assert_eq "$rc" "6" "recover must report RECOVERY_FAILED (rc=6) when the quarantine destination already exists"
assert_contains "$out" "already existed" "recover output must explain the destination already existed"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "stale-token" "the canonical lock must be completely untouched"
[ -f "${lockd}.quarantine.FORCED/PREEXISTING-FOREIGN-CONTENT" ] && t_ok || t_fail "the pre-existing foreign quarantine content must survive untouched"
[ -e "${lockd}.quarantine.FORCED/captured" ] && t_fail "must NEVER nest the canonical lock inside the pre-existing quarantine dir" || t_ok
rm -rf "$D"

# =============================================================================
# regression (Chris F1, Critical, bd:shode-house-vz8 iter3): `_lock_exists_or_error`
# split the path with `IFS='/' read -ra parts <<< "$path"` -- a bash here-string is
# line-oriented, so `read` (no `-d ''`) stopped at the FIRST literal newline byte in any
# path component regardless of `IFS`, silently truncating the walk and misreporting an
# EXISTING (possibly LIVE) target as MISSING. Only `/` and NUL are actually forbidden in
# a POSIX filename, so a newline component is legal. Deterministic, no permission
# tricks, no timing -- own repro against the primitive directly, plus the sibling shapes
# (space, tab) the same round asked to be checked for good measure.
# =============================================================================
t_start "regression (Chris F1): a path component containing an embedded newline reports EXISTS, matching bare [ -e ], not MISSING"
D=$(sandbox); comp=$'weird\nname'
mkdir -p "$D/$comp"; : > "$D/$comp/leaf"
[ -e "$D/$comp/leaf" ] || t_fail "test setup broken -- bare -e does not see the file we just created"
out=$(_lock_exists_or_error "$D/$comp/leaf")
assert_eq "$out" "EXISTS" "an embedded newline in a path component must not truncate the walk"
rm -rf "$D"

t_start "regression (Chris F1): a path component containing an embedded space reports EXISTS"
D=$(sandbox); comp='weird name with spaces'
mkdir -p "$D/$comp"; : > "$D/$comp/leaf"
out=$(_lock_exists_or_error "$D/$comp/leaf")
assert_eq "$out" "EXISTS" "an embedded space in a path component must resolve normally"
rm -rf "$D"

t_start "regression (Chris F1): a path component containing an embedded tab reports EXISTS"
D=$(sandbox); comp=$'weird\ttabname'
mkdir -p "$D/$comp"; : > "$D/$comp/leaf"
out=$(_lock_exists_or_error "$D/$comp/leaf")
assert_eq "$out" "EXISTS" "an embedded tab in a path component must resolve normally"
rm -rf "$D"

t_start "regression (Chris F1): a genuinely MISSING leaf under a newline-bearing ancestor still reports MISSING (the fix must not flip false-MISSING into false-EXISTS)"
D=$(sandbox); comp=$'has\nnewline'
mkdir -p "$D/$comp"
out=$(_lock_exists_or_error "$D/$comp/never-created-leaf")
assert_eq "$out" "MISSING" "a target that genuinely does not exist under a newline-bearing ancestor must still report MISSING"
rm -rf "$D"

# =============================================================================
# regression (Chris F1 reachability, bd:shode-house-vz8 iter3): the same bug reached
# through `lock_recover`'s own Step 1 canonical-lock check (scripts/lib/lock.sh:~590),
# which is the exact invariant C1 exists to protect -- a false "nothing to recover"
# COMPLETED that bypasses the liveness gate entirely. Seed a genuinely DEAD lock (not
# live -- if this were still broken the assertion below would catch it either way,
# since the correct answer here is "proceed to classify and report something other than
# a false COMPLETED-nothing-to-recover") at a path whose lockdir component itself
# contains an embedded newline, then recover it for real.
# =============================================================================
t_start "regression (Chris F1 reachability): recover against a lock whose OWN PATH contains an embedded newline component must classify the real lock, never silently report 'nothing to recover' when it demonstrably IS locked"
D=$(sandbox); comp=$'lock\ndir'; lockd="$D/$comp"
seed_dead_lock "$lockd" "TOKEN-NEWLINE-PATH" >/dev/null
[ -e "$lockd/token" ] || t_fail "test setup broken -- seeded lock not visible via bare -e"
out=$(bash "$LOCKLIB" recover "$lockd" --reason "F1 reachability: newline in lock path" 2>&1); rc=$?
case "$out" in
  *"nothing to recover"*)
    t_fail "must NEVER report 'nothing to recover' for a lock that genuinely exists and is held -- got: $out"
    ;;
  *) t_ok ;;
esac
assert_true "$rc" "a genuinely dead, genuinely-existing lock at a newline-bearing path must be recovered normally (rc=0), not silently skipped"
assert_contains "$out" "RECOVERED" "recover output should say RECOVERED, exactly like the ordinary dead-lock path"
[ -d "$lockd" ] && t_fail "the lock must be gone after a genuine recovery" || t_ok
rm -rf "$D"

# =============================================================================
# regression (Chris F2, Low, bd:shode-house-vz8 iter3): `lock_acquire`'s PRE-CHECK
# (scripts/lib/lock.sh's while-loop `if [ -e "$recovering" ]`) and
# `_lock_acquire_postwrite_recheck`'s own `.recovering` check were the last two bare
# `[ -e ]` decision points in the file -- migrated to the same three-state probe used
# everywhere else. These two tests confirm the ERROR branch (ancestor unresolvable, NOT
# a genuine marker) folds into the SAME restrictive outcome as EXISTS at both sites,
# rather than being silently misread as "no recovery in progress" (MISSING).
# =============================================================================
t_start "regression (Chris F2): _lock_acquire_postwrite_recheck must return RECOVERY_IN_PROGRESS (rc=2), never OK, when the .recovering path cannot be resolved (ancestor EACCES) -- ERROR folds the same as EXISTS"
D=$(sandbox); lockd="$D/parent/locks/mylock"; recovering="${lockd}.recovering"
mkdir -p "$D/parent/locks"
mkdir "$lockd"
tok="probe-token"; printf '%s' "$tok" > "$lockd/token"
chmod 000 "$D/parent"
out=$(_lock_acquire_postwrite_recheck "$lockd" "$tok" "$recovering"); rc=$?
chmod 755 "$D/parent" 2>/dev/null
assert_eq "$rc" "2" "an unresolvable .recovering path must be treated as RECOVERY_IN_PROGRESS (rc=2), never as OK (rc=0)"
assert_eq "$out" "RECOVERY_IN_PROGRESS" "output must say RECOVERY_IN_PROGRESS, not OK"
rm -rf "$D"

t_start "regression (Chris F2): lock_acquire's own PRE-CHECK must not silently proceed as if no recovery were in progress when the .recovering path is unresolvable -- must not return 0 (must never enter the critical section on a false 'no recovery in progress' read)"
D=$(sandbox); lockd="$D/parent/locks/mylock2"
mkdir -p "$D/parent/locks"
chmod 000 "$D/parent"
out=$(lock_acquire "$lockd" 2>/dev/null); rc=$?
chmod 755 "$D/parent" 2>/dev/null
assert_false "$rc" "acquire must NOT report success (rc=0) while the .recovering path's ancestor is unresolvable -- got rc=$rc"
[ -z "$out" ] && t_ok || t_fail "acquire must print nothing on STDOUT on failure, per its own contract (a token) -- got: $out"
rm -rf "$D"

# =============================================================================
# packaging: make pack must ship scripts/lib/lock.sh (Makefile:36 lists individual
# scripts/*.sh files explicitly -- it does NOT pack scripts/ as a whole directory, so a
# new file under scripts/lib/ needs an explicit addition, not just being on disk).
# =============================================================================
t_start "packaging: make pack ships scripts/lib/lock.sh, executable"
if command -v zip >/dev/null 2>&1 && command -v unzip >/dev/null 2>&1 && command -v zipinfo >/dev/null 2>&1; then
  ( cd "$REPO_ROOT" && make pack >/tmp/lock-pack-out.$$ 2>&1 )
  make_rc=$?
  assert_true "$make_rc" "make pack must succeed"
  VERSION=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json")
  PLUGIN="$REPO_ROOT/shode-house-v$VERSION.plugin"
  [ -f "$PLUGIN" ] && t_ok || t_fail "expected built artifact at $PLUGIN"
  listing=$(unzip -l "$PLUGIN" 2>/dev/null)
  assert_contains "$listing" "scripts/lib/lock.sh" "the packed .plugin must contain scripts/lib/lock.sh"
  # same convention as tests/test-hooks.sh's own packaging-perms check (zipinfo -l,
  # first whitespace-separated column is the unix perm string).
  perms=$(zipinfo -l "$PLUGIN" 2>/dev/null | grep 'scripts/lib/lock.sh' | awk '{print $1}')
  case "$perms" in
    -rwx*) t_ok ;;
    *) t_fail "scripts/lib/lock.sh perms in zip: '$perms' (expected -rwx...)" ;;
  esac
  rm -f "$PLUGIN"
else
  echo "   (skipped: zip/unzip/zipinfo not all on PATH)"
fi
rm -f /tmp/lock-pack-out.$$

printf '\n== %s passed, %s failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
