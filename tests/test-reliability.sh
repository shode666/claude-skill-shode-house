#!/usr/bin/env bash
# tests/test-reliability.sh -- Milestone D (bd: shode-roadmap/C-D1): retry/rework/resume
# separation (scripts/workflow-state.sh), side-effect ledger (scripts/side-effect.sh),
# approval scope + invalidation (scripts/approval.sh). ROADMAP-runtime-10.md Phase 6 /
# 8.3 / 9. Same CI budget rule as every prior milestone (outputs/shode-roadmap/C/
# 05-oliver-decisions.md: "1 AC = 1 test case ในสวีท ไม่ใช่ 1 CI section") -- this is the
# ONE step Milestone D adds to ci.yml, covering all three new scripts in one file.
#
# No framework dependency, same tiny bash test harness as tests/test-workflow-state.sh /
# tests/test-scope-check.sh. Every test runs in its own mktemp -d sandbox via
# WFSTATE_ROOT / SIDEEFFECT_ROOT / APPROVAL_ROOT so tests never touch the real repo state.
#
# Usage: bash tests/test-reliability.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WF="$REPO_ROOT/scripts/workflow-state.sh"
SE="$REPO_ROOT/scripts/side-effect.sh"
AP="$REPO_ROOT/scripts/approval.sh"

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
assert_true() {
  if [ "$1" -eq 0 ]; then t_ok; else t_fail "$2 -- exit code $1"; fi
}
assert_false() {
  if [ "$1" -ne 0 ]; then t_ok; else t_fail "$2 -- expected non-zero exit"; fi
}

sandbox() { local d; d=$(mktemp -d -t reliability-test.XXXXXX); printf '%s' "$d"; }

walk_to_4triage() {
  # $1 = bd-id -- fast-forward through the happy path to 4-triage, same sequence
  # test-workflow-state.sh's own "loop-1" test already exercises and asserts.
  local bd="$1"
  "$WF" advance "$bd" 1a-spec     >/dev/null 2>&1
  "$WF" advance "$bd" 1b-design   >/dev/null 2>&1
  "$WF" advance "$bd" 1c-security >/dev/null 2>&1
  "$WF" advance "$bd" 2-implement >/dev/null 2>&1
  "$WF" advance "$bd" 3a-ui-check >/dev/null 2>&1
  "$WF" advance "$bd" 3b-review   >/dev/null 2>&1
  "$WF" advance "$bd" 4-triage    >/dev/null 2>&1
}

# =============================================================================
# (1) error taxonomy -- references/state-machine/errors.json
# =============================================================================
t_start "errors.json: valid JSON, all 9 taxonomy classes present, each policy field-complete"
ERRJ="$REPO_ROOT/references/state-machine/errors.json"
jq empty "$ERRJ" >/dev/null 2>&1; assert_true "$?" "errors.json must be valid JSON"
for c in TRANSIENT USER_INPUT_REQUIRED POLICY_VIOLATION DEPENDENCY_FAILED TOOL_FAILURE \
         AGENT_FAILURE INVALID_STATE IRREVERSIBLE_PARTIAL VERIFICATION_FAILED; do
  jq -e --arg c "$c" '.policies | has($c)' "$ERRJ" >/dev/null 2>&1
  assert_true "$?" "errors.json must declare policy for class '$c'"
  jq -e --arg c "$c" '.policies[$c] | has("retry") and has("rework") and has("halt") and has("escalate") and has("reason")' "$ERRJ" >/dev/null 2>&1
  assert_true "$?" "errors.json policy for '$c' must have retry/rework/halt/escalate/reason (no omitted key)"
done
assert_eq "$(jq -r '.policies.TRANSIENT.retry' "$ERRJ")" "2" "TRANSIENT retry cap must be 2 (given in the brief)"
assert_eq "$(jq -r '.policies.VERIFICATION_FAILED.rework' "$ERRJ")" "true" "VERIFICATION_FAILED rework must be true (given)"
assert_eq "$(jq -r '.policies.INVALID_STATE.halt' "$ERRJ")" "true" "INVALID_STATE halt must be true (given)"
assert_eq "$(jq -r '.policies.USER_INPUT_REQUIRED.escalate' "$ERRJ")" "user" "USER_INPUT_REQUIRED escalate must be 'user' (given)"

# =============================================================================
# (2) retry / rework / resume -- scripts/workflow-state.sh
# =============================================================================

t_start "retry: unknown error class is rejected loudly (closed-world enum)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init ret-1 >/dev/null 2>&1
err=$("$WF" retry ret-1 NOT_A_REAL_CLASS 2>&1); rc=$?
assert_false "$rc" "retry with an unknown class must fail"
assert_contains "$err" "unknown error class" "rejection reason should name the problem"
rm -rf "$D"

t_start "retry: TRANSIENT does NOT move current_phase and does NOT bump iter (retry != transition)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init ret-2 >/dev/null 2>&1
out=$("$WF" retry ret-2 TRANSIENT 2>&1); rc=$?
assert_true "$rc" "first TRANSIENT retry (within cap 2) should succeed"
sf="$D/.shode-house/state/ret-2.json"
assert_eq "$(jq -r '.current_phase' "$sf")" "0-discover" "retry must not move current_phase"
assert_eq "$(jq -r '.iter' "$sf")" "0" "retry must not bump iter"
assert_eq "$(jq -r '.phases["0-discover"].status' "$sf")" "in_progress" "retry must not change the phase's status"
rm -rf "$D"

t_start "retry: cap enforced from errors.json policy (TRANSIENT=2) -- 3rd attempt rejected"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init ret-3 >/dev/null 2>&1
"$WF" retry ret-3 TRANSIENT >/dev/null 2>&1
"$WF" retry ret-3 TRANSIENT >/dev/null 2>&1
err=$("$WF" retry ret-3 TRANSIENT 2>&1); rc=$?
assert_false "$rc" "3rd TRANSIENT retry must be rejected once the cap (2) is reached"
assert_contains "$err" "retry cap" "rejection reason should name the cap"
sf="$D/.shode-house/state/ret-3.json"
assert_eq "$(jq -r '.phases["0-discover"].retry_count' "$sf")" "2" "retry_count must stay at 2 after the rejected 3rd attempt (state untouched by a reject)"
rm -rf "$D"

t_start "retry: a class with retry=false in policy (VERIFICATION_FAILED) is refused outright, not silently capped at 0"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init ret-4 >/dev/null 2>&1
err=$("$WF" retry ret-4 VERIFICATION_FAILED 2>&1); rc=$?
assert_false "$rc" "VERIFICATION_FAILED must not be retryable"
assert_contains "$err" "not retryable" "rejection reason should say the class is not retryable"
rm -rf "$D"

t_start "rework: class=code/perf/security routes to 2-implement per output-styles/oliver.md section 5 triage table (mutation target: editing rework-routing.json's 'code' route must turn this red)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init rew-code >/dev/null 2>&1
walk_to_4triage rew-code
out=$("$WF" rework rew-code code 2>&1); rc=$?
assert_true "$rc" "rework class=code should succeed (4-triage -> 2-implement is a declared edge)"
sf="$D/.shode-house/state/rew-code.json"
assert_eq "$(jq -r '.current_phase' "$sf")" "2-implement" "rework class=code must route to 2-implement, not any other phase"
assert_eq "$(jq -r '.phases["4-triage"].status' "$sf")" "failed" "the phase reworked away from must end status=failed (result was wrong), not passed"
rm -rf "$D"

t_start "rework: class=ui/design routes to 1b-design (positive control, distinct target from the code/perf/security case above)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init rew-ui >/dev/null 2>&1
walk_to_4triage rew-ui
out=$("$WF" rework rew-ui ui 2>&1); rc=$?
assert_true "$rc" "rework class=ui should succeed (4-triage -> 1b-design is a declared edge)"
sf="$D/.shode-house/state/rew-ui.json"
assert_eq "$(jq -r '.current_phase' "$sf")" "1b-design" "rework class=ui must route to 1b-design, not 2-implement"
rm -rf "$D"

t_start "rework: class=spec/ac/regulation routes to 1a-spec (reuses the existing spec-change edge -- third distinct target)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init rew-spec >/dev/null 2>&1
walk_to_4triage rew-spec
out=$("$WF" rework rew-spec regulation 2>&1); rc=$?
assert_true "$rc" "rework class=regulation should succeed (4-triage -> 1a-spec spec-change edge)"
sf="$D/.shode-house/state/rew-spec.json"
assert_eq "$(jq -r '.current_phase' "$sf")" "1a-spec" "rework class=regulation must route to 1a-spec"
rm -rf "$D"

t_start "rework: unknown triage class is rejected loudly, state untouched"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init rew-bad >/dev/null 2>&1
sf="$D/.shode-house/state/rew-bad.json"
before_sha=$(shasum "$sf")
err=$("$WF" rework rew-bad not-a-real-class 2>&1); rc=$?
assert_false "$rc" "rework with an unknown class must fail"
assert_contains "$err" "unknown triage class" "rejection reason should name the problem"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "state must be untouched by a rejected rework (unknown class)"
rm -rf "$D"

t_start "rework: iter bumps by exactly 1 per rework call (each target phase is a revisit), and still respects the existing iter>3 escalation cap"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init rew-iter >/dev/null 2>&1
walk_to_4triage rew-iter
sf="$D/.shode-house/state/rew-iter.json"
assert_eq "$(jq -r '.iter' "$sf")" "0" "iter must be 0 right after the pure-forward walk to 4-triage (sanity baseline, same invariant as test-workflow-state.sh's loop-1 test)"

# rework #1: 4-triage -> 2-implement. 2-implement was already visited (status=passed
# from the forward walk) -- a revisit into a non-pending phase bumps iter by 1, same
# rule cmd_advance already applies to every transition (not special-cased for rework).
"$WF" rework rew-iter code >/dev/null 2>&1
assert_eq "$(jq -r '.iter' "$sf")" "1" "iter should be exactly 1 after the first rework loop (0 -> 1, +1)"
assert_eq "$(jq -r '.current_phase' "$sf")" "2-implement" "rework must have landed on 2-implement"

# walk back to 4-triage via the backend-only-bypass edge (2-implement -> 3b-review,
# already legal per transitions.json and exercised by test-workflow-state.sh's own
# rew-2 test) -- every hop here revisits an already-passed/failed phase, so iter keeps
# climbing by 1 each hop; this is not special to rework, just the pre-existing rule.
"$WF" advance rew-iter 3b-review >/dev/null 2>&1   # iter 1 -> 2 (3b-review was visited)
"$WF" advance rew-iter 4-triage  >/dev/null 2>&1   # iter 2 -> 3 (4-triage was visited -- left status=failed by rework #1)
assert_eq "$(jq -r '.iter' "$sf")" "3" "iter should be 3 once back at 4-triage for a second rework attempt"

# rework #2: the PRE-transition iter (3) is checked against the cap ('iter>3', not
# '>=') so this call is still allowed -- and bumps iter to 4 same as rework #1 did.
out=$("$WF" rework rew-iter code 2>&1); rc=$?
assert_true "$rc" "a rework call made while iter=3 (not yet over the cap) must still be allowed"
assert_eq "$(jq -r '.iter' "$sf")" "4" "iter should be 4 after this second rework loop (3 -> 4, +1)"

# now iter=4 (over the cap of 3) -- ANY further advance (rework or plain) must be
# blocked until explicitly escalated, proving rework respects the pre-existing cap
# rather than a separate, weaker one of its own.
err2=$("$WF" advance rew-iter 3b-review 2>&1); rc2=$?
assert_false "$rc2" "a further advance must be blocked once iter has exceeded the cap (3) -- must escalate first, same rule cmd_advance already enforces"
assert_contains "$err2" "iter>3 requires escalated transition first" "rejection reason should name the iter-cap rule"
err3=$("$WF" rework rew-iter code 2>&1); rc3=$?
assert_false "$rc3" "a 3rd rework attempt must also be blocked once iter has exceeded the cap -- rework is not exempt from the cap"
assert_contains "$err3" "iter>3 requires escalated transition first" "the rework-triggered rejection reason should name the same iter-cap rule (not a different/weaker error)"
rm -rf "$D"

t_start "resume: clean (non-torn) state reports the correct next step and does not error"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init res-1 >/dev/null 2>&1
out=$("$WF" resume res-1 2>&1); rc=$?
assert_true "$rc" "resume on a clean freshly-inited state should succeed"
assert_contains "$out" "current_phase=0-discover" "resume should report the current phase"
assert_contains "$out" "next step:" "resume should report a next-step hint"
rm -rf "$D"

t_start "resume: TORN WRITE (journal ahead of state, crash-injected) is detected and reported, exit non-zero, NOT walked past silently"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init res-torn >/dev/null 2>&1
WFSTATE_CRASH_BEFORE_RENAME=1 "$WF" advance res-torn 1a-spec >/dev/null 2>&1
sf="$D/.shode-house/state/res-torn.json"
before_sha=$(shasum "$sf")
out=$("$WF" resume res-torn 2>&1); rc=$?
assert_false "$rc" "resume must exit non-zero on a torn write, never proceed as if nothing happened"
assert_contains "$out" "TORN WRITE DETECTED" "resume must name the torn-write condition explicitly"
assert_contains "$out" "0-discover" "the torn-write report should name the phase involved"
after_sha=$(shasum "$sf")
assert_eq "$after_sha" "$before_sha" "resume must never mutate state.json when it detects a torn write (read-only diagnosis)"
rm -rf "$D"

t_start "resume: artifact drift on an already-approved phase is detected and reported, exit non-zero"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export WFSTATE_ROOT="$D"
"$WF" init res-drift >/dev/null 2>&1
printf 'v1' > "$D/outputs/a.md"
sf="$D/.shode-house/state/res-drift.json"
tmp=$(mktemp); jq '.phases["0-discover"].artifacts = ["outputs/a.md"] | .phases["0-discover"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
"$WF" advance res-drift 1a-spec >/dev/null 2>&1
printf 'v2 tampered' > "$D/outputs/a.md"
out=$("$WF" resume res-drift 2>&1); rc=$?
assert_false "$rc" "resume must exit non-zero when an approved phase's artifact has drifted since"
assert_contains "$out" "ARTIFACT DRIFT" "resume should name the artifact-drift condition explicitly"
assert_contains "$out" "outputs/a.md" "the drift report should name the specific path"
rm -rf "$D"

t_start "journal: retry / rework / resume each write a DISTINCT op tag -- never collapse into the same event as each other or as a plain transition (task requirement)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
"$WF" init jop-1 >/dev/null 2>&1
walk_to_4triage jop-1
"$WF" retry jop-1 TRANSIENT >/dev/null 2>&1
"$WF" rework jop-1 code >/dev/null 2>&1
"$WF" resume jop-1 >/dev/null 2>&1
jf="$D/.shode-house/journal/jop-1.jsonl"
ops=$(jq -r '.op' "$jf" | sort -u | tr '\n' ',')
assert_contains "$ops" "init," "journal must contain an init-tagged line"
assert_contains "$ops" "transition," "journal must contain transition-tagged lines (the plain advance() calls)"
assert_contains "$ops" "retry," "journal must contain a retry-tagged line"
assert_contains "$ops" "rework," "journal must contain a rework-tagged line"
assert_contains "$ops" "resume," "journal must contain a resume-tagged line"
n_distinct=$(jq -r '.op' "$jf" | sort -u | wc -l | tr -d ' ')
[ "$n_distinct" -ge 5 ] && t_ok || t_fail "expected >= 5 distinct op tags (init/transition/retry/rework/resume), got $n_distinct"
rm -rf "$D"

# =============================================================================
# (3) side-effect ledger -- scripts/side-effect.sh
# =============================================================================

t_start "side-effect: check on a never-seen key -> NOT_DONE, exit 0"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
out=$("$SE" check bd-se-1 KEY-A 2>&1); rc=$?
assert_true "$rc" "check on an unseen key should exit 0 (safe to proceed)"
assert_contains "$out" "NOT_DONE" "output should say NOT_DONE"
rm -rf "$D"

t_start "side-effect: record completed, then check the SAME idempotency_key again -> ALREADY_DONE, exit 1 (must not repeat)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-2 deploy KEY-B completed "prod deploy v3" >/dev/null 2>&1
out=$("$SE" check bd-se-2 KEY-B 2>&1); rc=$?
assert_false "$rc" "check must exit non-zero once the key is recorded completed"
assert_contains "$out" "ALREADY_DONE" "output should say ALREADY_DONE"
rm -rf "$D"

t_start "side-effect: recording the SAME completed key/op/status a 2nd time is an idempotent no-op -- ledger content unchanged, not treated as a repeat action"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-3 deploy KEY-C completed "first" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-se-3.json"
before=$(jq -c '.["KEY-C"]' "$lf")
out=$("$SE" record bd-se-3 deploy KEY-C completed "second attempt, ignored the check gate" 2>&1); rc=$?
assert_true "$rc" "re-recording the identical completed status must exit 0 (idempotent no-op, not an error)"
assert_contains "$out" "no-op" "output should say this was a no-op"
after=$(jq -c '.["KEY-C"]' "$lf")
assert_eq "$after" "$before" "the ledger record itself (including original detail/ts) must be unchanged by the duplicate call -- proves the second attempt was NOT executed/recorded as a new action"
rm -rf "$D"

t_start "side-effect: reusing a completed key for a DIFFERENT operation is denied (ledger integrity)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-4 deploy KEY-D completed "deploy" >/dev/null 2>&1
err=$("$SE" record bd-se-4 migration KEY-D completed "different op, same key" 2>&1); rc=$?
assert_false "$rc" "reusing a key across two different operations must be denied"
assert_contains "$err" "DENY" "output should say DENY"
rm -rf "$D"

t_start "side-effect: CLOSED ENUM -- record() itself refuses an unrecognized <status> argument (e.g. the retired legacy 'in_progress' convenience) BEFORE writing anything, exit 64 -- bd:shode-house-5cs.3 iter5"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
out=$("$SE" record bd-se-5 migration KEY-E in_progress "started" 2>&1); rc=$?
assert_eq "$rc" "64" "record must refuse an unrecognized status argument (usage error), not silently write it"
assert_contains "$out" "not a recognized value" "output should explain the status was rejected"
lf="$D/.shode-house/side-effects/bd-se-5.json"
assert_eq "$([ -e "$lf" ] && echo exists || echo missing)" "missing" "no ledger file must be created for a rejected record() call"
rm -rf "$D"

t_start "side-effect: status=failed is a legitimate, NON-ambiguous terminal state -- check reports NOT_DONE (safe to retry), distinct from pending's UNKNOWN -- bd:shode-house-5cs.3 iter5"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-5b migration KEY-E failed "external API rejected the request before any side effect occurred" >/dev/null 2>&1
out=$("$SE" check bd-se-5b KEY-E 2>&1); rc=$?
assert_true "$rc" "check should be NOT_DONE (exit 0) while status=failed -- a confirmed failure is safe to retry"
assert_contains "$out" "NOT_DONE" "output should say NOT_DONE"
case "$out" in
  *"UNKNOWN"*|*"RECONCILE_REQUIRED"*) t_fail "a confirmed 'failed' status must never read as the ambiguous pending/UNKNOWN verdict -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: reserve() on a key whose existing status is 'failed' is ALLOWED to proceed (a confirmed failure is a legitimate retry starting point, not a reconciliation hazard) -- bd:shode-house-5cs.3 iter5"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-5c migration KEY-E failed "first attempt confirmed did not run" >/dev/null 2>&1
out=$("$SE" reserve bd-se-5c migration KEY-E "retry attempt" 2>&1); rc=$?
assert_true "$rc" "reserve on a failed key must succeed (exit 0 RESERVED), not be denied or reconcile-blocked"
assert_contains "$out" "RESERVED" "output should say RESERVED"
lf="$D/.shode-house/side-effects/bd-se-5c.json"
assert_eq "$(jq -r '.["KEY-E"].status' "$lf")" "pending" "the retry must overwrite the failed record with a fresh pending one"
rm -rf "$D"

# =============================================================================
# (3b) side-effect ledger reserve/pending + UNKNOWN reconcile -- bd:shode-house-5cs.3
# =============================================================================

t_start "side-effect: reserve writes status=pending BEFORE the effect, exit 0 RESERVED"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
out=$("$SE" reserve bd-se-6 deploy KEY-F "about to deploy" 2>&1); rc=$?
assert_true "$rc" "reserve on a fresh key should exit 0"
assert_contains "$out" "RESERVED" "output should say RESERVED"
lf="$D/.shode-house/side-effects/bd-se-6.json"
assert_eq "$(jq -r '.["KEY-F"].status' "$lf")" "pending" "ledger must record status=pending after reserve"
rm -rf "$D"

t_start "side-effect: check on a pending (reserved-but-not-recorded) key -> UNKNOWN, exit 2, NEVER 'safe to proceed' or 'safe to (re)attempt'"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" reserve bd-se-7 deploy KEY-G "about to deploy" >/dev/null 2>&1
out=$("$SE" check bd-se-7 KEY-G 2>&1); rc=$?
assert_eq "$rc" "2" "check on a pending key must exit 2 (a distinct code, not 0 or 1)"
assert_contains "$out" "UNKNOWN" "output should say UNKNOWN"
assert_contains "$out" "RECONCILE_REQUIRED" "output should say RECONCILE_REQUIRED"
case "$out" in
  *"safe to proceed"*|*"safe to (re)attempt"*)
    t_fail "pending-key verdict text must NEVER contain 'safe to proceed' or 'safe to (re)attempt' -- got: $out" ;;
  *) t_ok ;;
esac
assert_contains "$out" "SAME idempotency_key" "verdict should tell the caller the correct move: retry with the SAME key if idempotent, else verify external state"
rm -rf "$D"

t_start "side-effect: reserve on an already-completed key is DENIED (completed is a one-way door, cannot re-reserve)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-8 deploy KEY-H completed "done" >/dev/null 2>&1
err=$("$SE" reserve bd-se-8 deploy KEY-H "try again" 2>&1); rc=$?
assert_false "$rc" "reserve on an already-completed key must be denied"
assert_contains "$err" "DENY" "output should say DENY"
rm -rf "$D"

t_start "side-effect: reserve reusing a key already used for a DIFFERENT operation is denied (same ledger-integrity rule as record)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" reserve bd-se-9 deploy KEY-I "first" >/dev/null 2>&1
err=$("$SE" reserve bd-se-9 migration KEY-I "different op, same key" 2>&1); rc=$?
assert_false "$rc" "reserve with a mismatched operation on an existing key must be denied"
assert_contains "$err" "DENY" "output should say DENY"
rm -rf "$D"

t_start "side-effect: record can finalize a reserve()d pending key straight to completed (the normal, non-crash path)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" reserve bd-se-10 deploy KEY-J "about to deploy" >/dev/null 2>&1
out=$("$SE" record bd-se-10 deploy KEY-J completed "deploy finished normally" 2>&1); rc=$?
assert_true "$rc" "record completed on a pending key should succeed"
assert_contains "$out" "RECORDED" "output should say RECORDED"
out2=$("$SE" check bd-se-10 KEY-J 2>&1); rc2=$?
assert_false "$rc2" "check after finalizing must no longer be exit 0"
assert_eq "$rc2" "1" "check after finalizing must be exit 1 ALREADY_DONE, not the pending exit 2"
assert_contains "$out2" "ALREADY_DONE" "output should say ALREADY_DONE"
rm -rf "$D"

t_start "side-effect: BACKWARD COMPAT -- an old-shape ledger fixture (written before reserve/the closed enum existed) using only enum-valid statuses is still read correctly -- bd:shode-house-5cs.3 iter5 migration policy"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
lf="$D/.shode-house/side-effects/bd-se-old.json"
cat > "$lf" <<'JSON'
{
  "OLD-COMPLETED": {"operation": "deploy", "idempotency_key": "OLD-COMPLETED", "status": "completed", "detail": "pre-reserve era", "ts": "2025-01-01T00:00:00Z"},
  "OLD-FAILED": {"operation": "migration", "idempotency_key": "OLD-FAILED", "status": "failed", "detail": "pre-reserve era, confirmed did not run", "ts": "2025-01-01T00:00:00Z"}
}
JSON
out1=$("$SE" check bd-se-old OLD-COMPLETED 2>&1); rc1=$?
assert_false "$rc1" "old-shape completed record must still deny (exit 1 ALREADY_DONE)"
assert_contains "$out1" "ALREADY_DONE" "old-shape completed record should still say ALREADY_DONE"
out2=$("$SE" check bd-se-old OLD-FAILED 2>&1); rc2=$?
assert_true "$rc2" "old-shape failed record must still be NOT_DONE (exit 0), unaffected by the closed-enum addition"
assert_contains "$out2" "NOT_DONE" "old-shape failed record should still say NOT_DONE"
rm -rf "$D"

t_start "side-effect: MIGRATION -- an old-shape ledger containing the now-RETIRED legacy 'in_progress' convenience (never written by any real caller anywhere in this repo -- only this file's own former documentation example) now fails closed (exit 64), not NOT_DONE -- an explicit, stated policy decision, not silent enum-widening -- bd:shode-house-5cs.3 iter5"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
lf="$D/.shode-house/side-effects/bd-se-old-retired.json"
cat > "$lf" <<'JSON'
{
  "OLD-INPROGRESS": {"operation": "migration", "idempotency_key": "OLD-INPROGRESS", "status": "in_progress", "detail": "pre-reserve era", "ts": "2025-01-01T00:00:00Z"}
}
JSON
out=$("$SE" check bd-se-old-retired OLD-INPROGRESS 2>&1); rc=$?
assert_eq "$rc" "64" "an old ledger entry using the retired 'in_progress' status must fail closed, never fall back to NOT_DONE"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' for a status outside the closed enum -- got: $out" ;;
  *) t_ok ;;
esac
assert_contains "$out" "closed enum" "the die() reason should name the closed-enum policy"
rm -rf "$D"

t_start "CRASH INJECTION: kill -9 the caller process between reserve and record -- check reports UNKNOWN (not NOT_DONE), and only an explicit reconcile record can move it to completed (proves the effect is never silently treated as repeatable)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
(
  "$SE" reserve bd-crash deploy KEY-CRASH "about to deploy" >/dev/null 2>&1
  sleep 3
  "$SE" record bd-crash deploy KEY-CRASH completed "deploy done" >/dev/null 2>&1
) &
bgpid=$!
sleep 0.4
kill -9 "$bgpid" 2>/dev/null
wait "$bgpid" 2>/dev/null
out=$("$SE" check bd-crash KEY-CRASH 2>&1); rc=$?
assert_eq "$rc" "2" "after the kill, check must report the pending/UNKNOWN state (exit 2), not NOT_DONE"
assert_contains "$out" "UNKNOWN" "post-crash check should say UNKNOWN"
assert_contains "$out" "RECONCILE_REQUIRED" "post-crash check should say RECONCILE_REQUIRED"
case "$out" in
  *"safe to proceed"*) t_fail "post-crash check must never say 'safe to proceed' -- that would repeat the effect -- got: $out" ;;
  *) t_ok ;;
esac
# reconcile: caller verifies externally the deploy DID happen, then records completed directly
"$SE" record bd-crash deploy KEY-CRASH completed "reconciled: verified via external status check, effect had in fact completed before the kill" >/dev/null 2>&1
out2=$("$SE" check bd-crash KEY-CRASH 2>&1); rc2=$?
assert_false "$rc2" "after explicit reconcile, check must be non-zero (ALREADY_DONE)"
assert_eq "$rc2" "1" "after explicit reconcile, check must be exactly exit 1 ALREADY_DONE"
assert_contains "$out2" "ALREADY_DONE" "output should say ALREADY_DONE after reconcile"
# and the killed background record (queued behind the sleep) must never have landed a
# SECOND completed write on top -- ledger content for this key traces to the reconcile
# call only, not two competing writers.
lf="$D/.shode-house/side-effects/bd-crash.json"
assert_contains "$(jq -r '.["KEY-CRASH"].detail' "$lf")" "reconciled" "the ledger's final detail must be the reconcile call's, proving the killed background record never executed (it was killed before reaching its own record step)"
rm -rf "$D"

# =============================================================================
# (3c) side-effect ledger: FAIL CLOSED on a corrupt ledger -- bd:shode-house-5cs.3 iter1
# F1 (Chris/Quinn 3b-review: die() inside $(...) was swallowed, corrupted ledger used to
# fail OPEN with "safe to (re)attempt", exit 0)
# =============================================================================

t_start "side-effect: check on a CORRUPTED (truncated, not-JSON) ledger FAILS CLOSED (exit 64), never 'safe to (re)attempt' -- bd:shode-house-5cs.3 F1"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
printf 'not valid json at all {{{' > "$D/.shode-house/side-effects/bd-corrupt-a.json"
out=$("$SE" check bd-corrupt-a KEY-T 2>&1); rc=$?
assert_eq "$rc" "64" "check on a corrupted ledger must exit 64 (usage/dependency error class), not 0"
case "$out" in
  *"safe to"*) t_fail "corrupted-ledger check output must NEVER contain 'safe to ...' -- got: $out" ;;
  *) t_ok ;;
esac
assert_contains "$out" "not valid JSON" "the die() reason should name the actual problem"
rm -rf "$D"

t_start "side-effect: check on an EMPTY (0-byte) ledger file FAILS CLOSED (exit 64) -- jq empty on empty stdin is itself 'valid', this is the loophole F1 also closes"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
: > "$D/.shode-house/side-effects/bd-empty-a.json"
out=$("$SE" check bd-empty-a KEY-T 2>&1); rc=$?
assert_eq "$rc" "64" "check on a 0-byte ledger must exit 64, not treat it as 'no record yet'"
assert_contains "$out" "EMPTY" "the die() reason should name the empty-file condition"
rm -rf "$D"

t_start "side-effect: a PREVIOUSLY-COMPLETED key whose ledger file then gets corrupted (bit-rot/torn-write) must FAIL CLOSED, not report NOT_DONE for an already-executed dangerous effect -- the worst-case scenario F1 exists to prevent"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-corrupt-worst deploy KEY-GOOD completed "important record" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-corrupt-worst.json"
printf 'CORRUPTED-BYTES-MID-FILE' > "$lf"
out=$("$SE" check bd-corrupt-worst KEY-GOOD 2>&1); rc=$?
assert_eq "$rc" "64" "check on a corrupted ledger for a previously-completed key must fail closed (exit 64), never say NOT_DONE"
case "$out" in
  *"safe to"*) t_fail "must never say 'safe to ...' for a corrupted ledger that may hold a completed record -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: reserve/record on a CORRUPTED ledger must FAIL CLOSED too, and must NEVER silently replace the corrupted file with a near-empty one (the old jq-empty-stdin-is-valid loophole)"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
lf="$D/.shode-house/side-effects/bd-corrupt-b.json"
printf 'not valid json at all {{{' > "$lf"
before_bytes=$(wc -c < "$lf" | tr -d ' ')
out=$("$SE" reserve bd-corrupt-b deploy KEY-R "d" 2>&1); rc=$?
assert_eq "$rc" "64" "reserve on a corrupted ledger must exit 64, never RESERVED"
after_bytes=$(wc -c < "$lf" | tr -d ' ')
assert_eq "$after_bytes" "$before_bytes" "the corrupted ledger file must be left BYTE-IDENTICAL after a failed reserve -- must never be silently overwritten with a near-empty file"
rm -rf "$D"

# =============================================================================
# (3c-2) side-effect ledger: FAIL CLOSED on a syntactically-VALID-but-WRONG-SHAPE
# ledger, and on a non-regular-file at the ledger path -- bd:shode-house-5cs.3 iter2,
# Quinn P0 1b/1c (reproduced the exact original worst case: a previously-completed
# key reads back as "safe to (re)attempt"/"safe to proceed", exit 0). validate_ledger_
# or_die() must assert the SHAPE it requires (top-level object, per-key record object
# with string operation/status/ts), not just JSON well-formedness -- and must treat
# "exists but not a regular file" as corruption, not "no record yet".
# =============================================================================

t_start "side-effect: check on a ledger that is a syntactically-VALID top-level JSON ARRAY fails closed (exit 64), never falls through to NOT_DONE/safe-to-proceed -- bd:shode-house-5cs.3 Quinn P0 1b"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
printf '["totally", "wrong", "shape", "but", "syntactically", "valid", "json"]' > "$D/.shode-house/side-effects/bd-shape-arr.json"
out=$("$SE" check bd-shape-arr KEY-REAL 2>&1); rc=$?
assert_eq "$rc" "64" "a top-level-array ledger must exit 64, not fall through to a NOT_DONE/safe-to-proceed verdict"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' for a wrong-shape ledger -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: a PREVIOUSLY-COMPLETED key whose ledger gets replaced with a valid-JSON top-level array must fail closed, not read as NOT_DONE -- the exact worst-case scenario, reproduced via the wrong-shape vector"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-shape5 deploy KEY-REAL completed "real prod deploy, already executed" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-shape5.json"
printf '["totally", "wrong", "shape", "but", "syntactically", "valid", "json"]' > "$lf"
out=$("$SE" check bd-shape5 KEY-REAL 2>&1); rc=$?
assert_eq "$rc" "64" "a previously-completed key's ledger, corrupted into a top-level array, must fail closed (exit 64), never NOT_DONE"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' when the underlying record may have been completed -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: check on a ledger whose per-key VALUE is a bare string (not a record object) fails closed (exit 64) -- bd:shode-house-5cs.3 Quinn P0 1b, the wrong-shape-per-value variant"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
printf '{"KEY-REAL": "not-an-object"}' > "$D/.shode-house/side-effects/bd-shape-val.json"
out=$("$SE" check bd-shape-val KEY-REAL 2>&1); rc=$?
assert_eq "$rc" "64" "a bare-string per-key value must exit 64, not fall through to a verdict"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' for a wrong-shape per-key value -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: check on a ledger path that is a DIRECTORY (not a file) treats it as corruption (exit 64), never as 'no record yet' -- bd:shode-house-5cs.3 Quinn P0 1c"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-isdir3 deploy KEY-REAL2 completed "real completed effect" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-isdir3.json"
rm -f "$lf"; mkdir -p "$lf"
out=$("$SE" check bd-isdir3 KEY-REAL2 2>&1); rc=$?
assert_eq "$rc" "64" "a directory-shaped ledger path for a PREVIOUSLY-COMPLETED key must fail closed (exit 64), never read as 'has no record -- safe to proceed'"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' for a directory-shaped ledger path -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: check on a ledger path that is a SYMLINK to a non-regular target (/dev/null) treats it as corruption (exit 64) -- bd:shode-house-5cs.3 Quinn P0 1c"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-symnull2 deploy KEY-REAL3 completed "real completed effect" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-symnull2.json"
rm -f "$lf"; ln -s /dev/null "$lf"
out=$("$SE" check bd-symnull2 KEY-REAL3 2>&1); rc=$?
assert_eq "$rc" "64" "a symlink-to-non-regular ledger path must fail closed (exit 64), never read as 'no record'"
case "$out" in
  *"safe to"*) t_fail "must NEVER say 'safe to ...' for a symlink-to-non-regular ledger path -- got: $out" ;;
  *) t_ok ;;
esac
rm -rf "$D"

t_start "side-effect: reserve against a DIRECTORY-shaped ledger path fails closed (exit 64) BEFORE ever attempting the write -- must never claim RESERVED while silently nesting the tmp file inside the directory instead of replacing it"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects/bd-isdir2.json"; export SIDEEFFECT_ROOT="$D"
out=$("$SE" reserve bd-isdir2 deploy KEY-D3 "important reservation" 2>&1); rc=$?
assert_eq "$rc" "64" "reserve against a directory-shaped ledger path must exit 64, never RESERVED"
case "$out" in
  *"RESERVED"*) t_fail "must NEVER say RESERVED for a directory-shaped ledger path -- got: $out" ;;
  *) t_ok ;;
esac
nested=$(find "$D/.shode-house/side-effects/bd-isdir2.json" -maxdepth 1 -name '.tmp.*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "$nested" "0" "no tmp file should have been nested inside the directory-shaped path -- validate must reject before the write ever starts"
rm -rf "$D"

# =============================================================================
# (3c-3) side-effect ledger: CLOSED STATUS ENUM -- a near-miss corruption of the literal
# "completed", or any other status string outside {pending, completed, failed}, must fail
# closed (exit 64), never fall through to NOT_DONE/"safe to (re)attempt" -- bd:shode-house-
# 5cs.3 iter5 (Oliver's direct repro + Quinn's L3L4-final P0)
# =============================================================================

t_start "side-effect: OLIVER'S REPRO -- a PREVIOUSLY-COMPLETED record whose status string is corrupted by exactly one character/case/whitespace variant of the literal 'completed' fails closed (exit 64) for every variant, never NOT_DONE/'safe to (re)attempt'"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-nearmiss deploy KEY-D completed "real prod deploy, already executed" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-nearmiss.json"
for badstatus in "Completed" "completed " " completed" "COMPLETED" "completedX"; do
  jq --arg s "$badstatus" '.["KEY-D"].status = $s' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
  out=$("$SE" check bd-nearmiss KEY-D 2>&1); rc=$?
  assert_eq "$rc" "64" "status corrupted to [$badstatus] must fail closed (exit 64), not read as NOT_DONE for an already-executed effect"
  case "$out" in
    *"safe to"*) t_fail "must NEVER say 'safe to ...' for status corrupted to [$badstatus] -- got: $out" ;;
    *) t_ok ;;
  esac
  # restore to a clean completed record before the next variant
  jq --arg s "completed" '.["KEY-D"].status = $s' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
done
rm -rf "$D"

t_start "side-effect: an ENTIRELY UNKNOWN status on a FRESH (never-completed) key now fails closed (exit 64) -- deliberate change from the old 'anything else = NOT_DONE' tolerance, which is exactly the tension the closed enum resolves -- bd:shode-house-5cs.3 iter5"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
printf '{"KEY-C":{"operation":"deploy","idempotency_key":"KEY-C","status":"archived-by-external-tool","ts":"2025-01-01T00:00:00Z"}}' > "$D/.shode-house/side-effects/bd-unk.json"
out=$("$SE" check bd-unk KEY-C 2>&1); rc=$?
assert_eq "$rc" "64" "an unrecognized status string must fail closed, even on a key that was never completed"
assert_contains "$out" "closed enum" "the die() reason should name the closed-enum policy"
rm -rf "$D"

t_start "side-effect: PROVING FIELDS -- a status=completed record whose idempotency_key field does NOT match its own outer ledger key is corruption (self-consistency check) -- fails closed (exit 64)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-provkey deploy KEY-A completed "real" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-provkey.json"
jq '.["KEY-A"].idempotency_key = "SOMETHING-ELSE"' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
out=$("$SE" check bd-provkey KEY-A 2>&1); rc=$?
assert_eq "$rc" "64" "a completed record whose idempotency_key field disagrees with its own ledger key must fail closed"
assert_contains "$out" "proving fields" "the die() reason should name the proving-fields requirement"
rm -rf "$D"

t_start "side-effect: PROVING FIELDS -- a status=completed record with idempotency_key deleted entirely (missing proving field) is corruption -- fails closed (exit 64)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-provkey2 deploy KEY-A completed "real" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-provkey2.json"
jq 'del(.["KEY-A"].idempotency_key)' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
out=$("$SE" check bd-provkey2 KEY-A 2>&1); rc=$?
assert_eq "$rc" "64" "a completed record missing idempotency_key entirely must fail closed"
rm -rf "$D"

t_start "side-effect: PROVING FIELDS -- a status=completed record with detail deleted entirely (no evidence of what was verified/executed) is corruption -- fails closed (exit 64)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-nodetail2 deploy KEY-B completed "real" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-nodetail2.json"
jq 'del(.["KEY-B"].detail)' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
out=$("$SE" check bd-nodetail2 KEY-B 2>&1); rc=$?
assert_eq "$rc" "64" "a completed record missing detail entirely must fail closed"
rm -rf "$D"

t_start "side-effect: PROVING FIELDS -- a status=completed record with an EMPTY-STRING detail (present, but not proof of anything) is corruption -- fails closed (exit 64)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-emptydetail deploy KEY-B completed "" >/dev/null 2>&1
out=$("$SE" check bd-emptydetail KEY-B 2>&1); rc=$?
assert_eq "$rc" "64" "a completed record with an empty detail must fail closed, not read as ALREADY_DONE"
rm -rf "$D"

t_start "side-effect: FIELD OF WRONG TYPE (new proving-field surface) -- idempotency_key is a NUMBER on an otherwise-completed record -- fails closed (exit 64)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-wtkey deploy KEY-A completed "real" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-wtkey.json"
jq '.["KEY-A"].idempotency_key = 12345' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
out=$("$SE" check bd-wtkey KEY-A 2>&1); rc=$?
assert_eq "$rc" "64" "a numeric idempotency_key on a completed record must fail closed"
rm -rf "$D"

t_start "side-effect: allow-extra-FIELDS still holds under the closed enum -- an unrelated extra field on a valid completed record does NOT trip the enum/proving-fields check"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-extra deploy KEY-A completed "real" >/dev/null 2>&1
lf="$D/.shode-house/side-effects/bd-extra.json"
jq '.["KEY-A"].some_future_field = "anything"' "$lf" > "$lf.tmp" && mv "$lf.tmp" "$lf"
out=$("$SE" check bd-extra KEY-A 2>&1); rc=$?
assert_eq "$rc" "1" "an unrelated extra field must not be rejected, and should still read as ALREADY_DONE -- allow extra FIELDS, never allow extra SHAPES"
rm -rf "$D"

# =============================================================================
# (3d) side-effect ledger: locking -- bd:shode-house-5cs.3 iter1 F2 (Chris/Quinn
# 3b-review: no mutual exclusion on the read-modify-write path in reserve/record)
# =============================================================================

t_start "CONCURRENCY: N=20 parallel reserve calls, 20 DISTINCT keys, same bd -- ALL 20 must persist in the ledger (no lost writes)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
for i in $(seq 1 20); do
  "$SE" reserve bd-conc-distinct deploy "KEY-$i" "concurrent" >/dev/null 2>&1 &
done
wait
lf="$D/.shode-house/side-effects/bd-conc-distinct.json"
n=$(jq 'keys | length' "$lf" 2>/dev/null)
assert_eq "$n" "20" "all 20 concurrently-reserved DISTINCT keys must be present in the ledger after the lock fix (was 1/20 before)"
rm -rf "$D"

t_start "CONCURRENCY: N=20 parallel reserve calls, ALL on the SAME never-before-seen key -- exactly ONE caller may be told to proceed (exit 0 RESERVED), every other caller gets the reconcile verdict (exit 2 UNKNOWN/RECONCILE_REQUIRED, never RESERVED), ledger holds exactly one consistent pending record"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/tmp-out"; export SIDEEFFECT_ROOT="$D"
for i in $(seq 1 20); do
  ( "$SE" reserve bd-conc-same deploy KEY-SAME "caller $i" >"$D/tmp-out/out-$i" 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
winners=$(grep -l '^RESERVED: ' "$D"/tmp-out/out-* 2>/dev/null | wc -l | tr -d ' ')
reconciled=$(grep -l 'RECONCILE_REQUIRED' "$D"/tmp-out/out-* 2>/dev/null | wc -l | tr -d ' ')
rc0=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
rc2=$(cat "$D"/tmp-out/rc-* | grep -c '^2$')
assert_eq "$winners" "1" "exactly one caller must be told to proceed (RESERVED) -- got $winners"
assert_eq "$reconciled" "19" "the other 19 must all get the reconcile verdict (RECONCILE_REQUIRED), never a RESERVED success -- got $reconciled"
assert_eq "$rc0" "1" "exactly one caller must exit 0 -- got $rc0"
assert_eq "$rc2" "19" "the other 19 callers must all exit 2 (non-zero, never RESERVED-flavored success) -- got $rc2"
for f in "$D"/tmp-out/out-*; do
  case "$(cat "$f")" in
    *"perform the effect now"*"RECONCILE"*) t_fail "a single output must never contain BOTH 'perform the effect now' and RECONCILE_REQUIRED -- $f" ;;
    *) t_ok ;;
  esac
done
lf="$D/.shode-house/side-effects/bd-conc-same.json"
n=$(jq 'keys | length' "$lf" 2>/dev/null)
assert_eq "$n" "1" "the ledger must hold exactly one consistent record for the shared key, not a torn/duplicated write"
assert_eq "$(jq -r '.["KEY-SAME"].status' "$lf")" "pending" "the single record must be status=pending"
rm -rf "$D"

t_start "side-effect: SEQUENTIAL re-reserve on an already-pending key gets the reconcile verdict (exit 2, UNKNOWN/RECONCILE_REQUIRED), never a second RESERVED success -- bd:shode-house-5cs.3 iter2 (Oliver ruling on iter1 open question #1)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
out1=$("$SE" reserve bd-se-reseq deploy KEY-SEQ "first" 2>&1); rc1=$?
assert_true "$rc1" "the FIRST reserve on a fresh key must exit 0 RESERVED"
assert_contains "$out1" "RESERVED" "first reserve output should say RESERVED"
out2=$("$SE" reserve bd-se-reseq deploy KEY-SEQ "second" 2>&1); rc2=$?
assert_eq "$rc2" "2" "a SECOND sequential reserve on the same still-pending key must exit 2, not 0 or 1"
assert_contains "$out2" "UNKNOWN" "second reserve output should say UNKNOWN"
assert_contains "$out2" "RECONCILE_REQUIRED" "second reserve output should say RECONCILE_REQUIRED"
case "$out2" in
  *"RESERVED"*) t_fail "a re-reserve on a pending key must NEVER contain the word RESERVED -- got: $out2" ;;
  *) t_ok ;;
esac
case "$out2" in
  *"perform the effect now"*) t_fail "a re-reserve on a pending key must NEVER say 'perform the effect now' -- got: $out2" ;;
  *) t_ok ;;
esac
lf="$D/.shode-house/side-effects/bd-se-reseq.json"
assert_eq "$(jq -r '.["KEY-SEQ"].detail' "$lf")" "first" "the ledger record must be UNCHANGED by the rejected second reserve (still the first caller's detail)"
rm -rf "$D"

t_start "side-effect: happy path end-to-end -- reserve -> effect -> record completed; check afterward is ALREADY_DONE, and a caller never needed a second successful reserve"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
out=$("$SE" reserve bd-se-happy deploy KEY-HAPPY "about to deploy" 2>&1); rc=$?
assert_true "$rc" "reserve should succeed (exit 0)"
assert_contains "$out" "perform the effect now" "reserve output should tell the caller to perform the effect now"
# ... caller performs the real effect here ...
out2=$("$SE" record bd-se-happy deploy KEY-HAPPY completed "deploy finished" 2>&1); rc2=$?
assert_true "$rc2" "record completed should succeed"
out3=$("$SE" check bd-se-happy KEY-HAPPY 2>&1); rc3=$?
assert_eq "$rc3" "1" "check after the happy path must be exit 1 ALREADY_DONE"
assert_contains "$out3" "ALREADY_DONE" "check output should say ALREADY_DONE"
rm -rf "$D"

t_start "side-effect: happy path with crash -- reserve -> crash -> check -> UNKNOWN -> operator verifies -> record completed (the crash-retry caller never calls reserve a second time)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" reserve bd-se-happy-crash deploy KEY-HC "about to deploy" >/dev/null 2>&1
# simulate the crash: caller dies here, before record
out=$("$SE" check bd-se-happy-crash KEY-HC 2>&1); rc=$?
assert_eq "$rc" "2" "post-crash check must be UNKNOWN/RECONCILE_REQUIRED, exit 2"
assert_contains "$out" "RECONCILE_REQUIRED" "post-crash check should say RECONCILE_REQUIRED"
# operator verifies externally the effect did complete, then records directly (no second reserve)
out2=$("$SE" record bd-se-happy-crash deploy KEY-HC completed "reconciled: verified externally" 2>&1); rc2=$?
assert_true "$rc2" "reconcile record should succeed"
out3=$("$SE" check bd-se-happy-crash KEY-HC 2>&1); rc3=$?
assert_eq "$rc3" "1" "check after reconcile must be exit 1 ALREADY_DONE"
rm -rf "$D"

t_start "CONCURRENCY: record(completed) racing reserve() on the SAME already-reserved key, 30 trials -- completed must NEVER be silently reverted back to pending (was 15/30 before the lock fix)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
lost=0
for t in $(seq 1 30); do
  k="KEY-LU-$t"
  "$SE" reserve bd-conc-lu deploy "$k" "initial" >/dev/null 2>&1
  ( "$SE" record bd-conc-lu deploy "$k" completed "finalized" >/dev/null 2>&1 ) &
  ( "$SE" reserve bd-conc-lu deploy "$k" "racing-reserve" >/dev/null 2>&1 ) &
  wait
  st=$(jq -r --arg k "$k" '.[$k].status' "$D/.shode-house/side-effects/bd-conc-lu.json")
  [ "$st" != "completed" ] && lost=$((lost + 1))
done
assert_eq "$lost" "0" "0 of 30 trials should lose the completed write to a racing reserve after the lock fix"
rm -rf "$D"

# =============================================================================
# (3e) side-effect ledger: orphaned .tmp.* cleanup -- bd:shode-house-5cs.3 iter1 F3
# =============================================================================

t_start "side-effect: reserve killed AFTER mktemp but BEFORE mv leaves no orphaned .tmp.* file behind on the NEXT reserve call for the same bd (crash-recovery sweep)"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
# simulate an orphaned tmp file the way a killed-mid-write reserve would leave one
touch "$D/.shode-house/side-effects/.tmp.bd-orphan.XXXXXX-fake"
"$SE" reserve bd-orphan deploy KEY-Z "d" >/dev/null 2>&1
remaining=$(find "$D/.shode-house/side-effects" -maxdepth 1 -name '.tmp.bd-orphan.*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "$remaining" "0" "a subsequent reserve call must sweep away orphaned .tmp.* files left by a prior crash for the same bd"
rm -rf "$D"

# =============================================================================
# (3f) side-effect ledger: NO automatic stale-lock reclamation -- bd:shode-house-vz8
# (user ruling on bd:shode-house-5cs.7's THREE successive reap patches, each of which
# narrowed the "reaper destroys a NEW legitimate holder's lock" race without closing
# it -- 40-way concurrency had measured 38 rc=0 callers but only 34 persisted keys
# under the last of those patches). The fix is not a fourth patch: automatic
# reclamation is removed entirely, in the shared scripts/lib/lock.sh every consumer
# now uses. A dead holder's lock stays stuck BY DESIGN; the only way to clear one is
# the explicit, audited `scripts/lib/lock.sh recover <lockdir> --reason "..."`.
# =============================================================================

t_start "NO AUTO-REAP: a dead-pid holder's lock is NEVER reclaimed automatically -- reserve fails closed (not near-instant, not a silent reap), the lock dir is untouched, the ledger stays empty"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
lockd="$D/.shode-house/side-effects/.lock-bd-dead-1"
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
mkdir -p "$lockd"
printf 'dead-holder-token' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
t0=$(date +%s)
out=$("$SE" reserve bd-dead-1 deploy KEY-D "d" 2>&1); rc=$?
t1=$(date +%s)
assert_false "$rc" "reserve against a dead-pid-held lock must FAIL (never silently reap and proceed)"
assert_contains "$out" "RECOVERY_REQUIRED" "the failure must explain lock contention with a machine-readable, retry-vs-stop class (bd:shode-house-vz8 iter1 -- a dead-pid-held lock classifies as RECOVERY_REQUIRED, never the old generic 'another writer in progress' every rc used to collapse into), not report a ledger verdict"
elapsed=$((t1 - t0))
[ "$elapsed" -ge 1 ] && t_ok || t_fail "must wait out the real contention budget (~2s), not return near-instant the way the old auto-reap did -- got ${elapsed}s"
[ -d "$lockd" ] && t_ok || t_fail "the dead-pid lock directory must still exist -- NEVER auto-removed"
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "dead-holder-token" "the stuck lock's token must be byte-for-byte unchanged -- nothing touched it"
lf="$D/.shode-house/side-effects/bd-dead-1.json"
[ -f "$lf" ] && t_fail "no ledger file should have been created -- reserve must fail before ever touching the ledger" || t_ok
rm -rf "$D"

t_start "STALE LOCK + CONCURRENT RETRY-WORKERS: N=10 concurrent reserve calls racing a permanently-stuck dead-pid lock all fail CLOSED -- 0 successes, ledger has ZERO keys, lock dir byte-identical (bd:shode-house-5cs.7's broken shape reproduced: this used to lose/duplicate writes via the buggy reap; now it cleanly refuses instead of corrupting)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/tmp-out"; export SIDEEFFECT_ROOT="$D"
mkdir -p "$D/.shode-house/side-effects"
lockd="$D/.shode-house/side-effects/.lock-bd-dead-2"
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
mkdir -p "$lockd"
printf 'dead-holder-token-2' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
for i in $(seq 1 10); do
  ( "$SE" reserve bd-dead-2 deploy "KEY-RETRY-$i" "retry-worker" >/dev/null 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
rc0_count=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
assert_eq "$rc0_count" "0" "not one of the 10 concurrent retry-workers may succeed against a stuck lock -- got $rc0_count rc=0"
lf="$D/.shode-house/side-effects/bd-dead-2.json"
[ -f "$lf" ] && t_fail "no ledger file should exist -- every worker must have failed before ever writing" || t_ok
assert_eq "$(cat "$lockd/token" 2>/dev/null)" "dead-holder-token-2" "the stuck lock's token must survive 10 concurrent contenders unchanged"
[ -d "$lockd" ] && t_ok || t_fail "the lock directory itself must survive"
rm -rf "$D"

t_start "RECOVERY REQUIRED BEFORE REUSE: the SAME stuck lock that just failed 10 concurrent reserves becomes usable again ONLY after an explicit, audited scripts/lib/lock.sh recover -- and that recovery is on the record"
D=$(sandbox); mkdir -p "$D/.shode-house/side-effects"; export SIDEEFFECT_ROOT="$D"
lockd="$D/.shode-house/side-effects/.lock-bd-dead-3"
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
mkdir -p "$lockd"
printf 'dead-holder-token-3' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
"$SE" reserve bd-dead-3 deploy KEY-PRE "d" >/dev/null 2>&1; rc_pre=$?
assert_false "$rc_pre" "sanity: reserve still fails before recovery"
recover_out=$(bash "$REPO_ROOT/scripts/lib/lock.sh" recover "$lockd" --reason "bd:shode-house-vz8 test -- confirmed-dead crash, no live holder" 2>&1); recover_rc=$?
assert_true "$recover_rc" "recover on a genuinely stuck lock (no newer holder raced in) must succeed"
assert_contains "$recover_out" "RECOVERED" "recover output should confirm the lock was cleared"
[ -d "$lockd" ] && t_fail "the lock directory must be GONE after a successful recover" || t_ok
audit="$D/.shode-house/side-effects/.lock-recoveries.jsonl"
[ -f "$audit" ] && t_ok || t_fail "recovery must be audited -- expected $audit"
jq empty "$audit" >/dev/null 2>&1
assert_true "$?" "every line of the recovery audit log must be valid JSON"
completed_lines=$(jq -r 'select(.outcome == "COMPLETED") | .lockdir' "$audit" 2>/dev/null | grep -c "^${lockd}\$")
assert_eq "$completed_lines" "1" "the audit log must record exactly one COMPLETED recovery of this lockdir (bd:shode-house-vz8 iter1 -- outcome vocabulary is STARTED/REFUSED/FAILED/COMPLETED, uppercase)"
assert_contains "$(cat "$audit")" "confirmed-dead crash" "the audited reason text must be preserved verbatim"
out_post=$("$SE" reserve bd-dead-3 deploy KEY-POST "d" 2>&1); rc_post=$?
assert_true "$rc_post" "reserve must succeed now that the stuck lock has been explicitly recovered"
assert_contains "$out_post" "RESERVED" "post-recovery reserve should proceed normally"
rm -rf "$D"

# =============================================================================
# (3g) side-effect ledger: N-way stress invariant -- bd:shode-house-5cs.7 secondary
# check (deterministic tests above are the primary gate; this is real concurrent
# load, same shape as Oliver's original 40-way measurement: count(callers that
# exited 0) must equal count(keys persisted), exactly, every run).
# =============================================================================

t_start "STRESS INVARIANT: N=40 concurrent reserve calls, 40 DISTINCT keys, same bd -- count(rc=0) MUST equal count(persisted keys), exactly (bd:shode-house-5cs.7 -- Oliver measured 38 rc=0 vs 34 persisted before this fix)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/tmp-out"; export SIDEEFFECT_ROOT="$D"
for i in $(seq 1 40); do
  ( "$SE" reserve bd-stress deploy "KEY-$i" "concurrent" >/dev/null 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
rc0_count=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
lf="$D/.shode-house/side-effects/bd-stress.json"
persisted_count=$(jq 'keys | length' "$lf" 2>/dev/null)
assert_eq "$rc0_count" "$persisted_count" "count(rc=0 reserves) must equal count(persisted keys) -- got rc0=$rc0_count persisted=$persisted_count"
# Informational only, NOT an assertion (the task is explicit: this stress run is a
# secondary check, the deterministic tests above are the primary gate -- a caller
# legitimately fail-closing on lock-wait contention under 40-way load on ONE lock dir
# is correct behavior, not data loss, and how many of the 40 land inside the ~2s
# per-acquire budget is a function of sandbox/CI machine speed, not this fix's
# correctness. The invariant above is what must hold, always, exactly.)
printf '   (informational, not asserted) rc0=%s persisted=%s / 40 attempted\n' "$rc0_count" "$persisted_count"
rm -rf "$D"

# =============================================================================
# (4) approval scope + invalidation -- scripts/approval.sh
# =============================================================================

t_start "approval: verify before any grant -> NO_APPROVAL, exit 2"
D=$(sandbox); mkdir -p "$D/.shode-house"; export APPROVAL_ROOT="$D"
out=$("$AP" verify bd-ap-1 pre-deploy 2>&1); rc=$?
assert_eq "$rc" "2" "verify with nothing granted yet should exit 2 (NO_APPROVAL)"
assert_contains "$out" "NO_APPROVAL" "output should say NO_APPROVAL"
rm -rf "$D"

t_start "approval: grant then verify immediately -> ALLOW (no drift yet)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
printf 'spec v1' > "$D/outputs/SPEC.md"
"$AP" grant bd-ap-2 pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
out=$("$AP" verify bd-ap-2 pre-deploy 2>&1); rc=$?
assert_true "$rc" "verify immediately after grant (no drift) should ALLOW"
assert_contains "$out" "ALLOW" "output should say ALLOW"
rm -rf "$D"

t_start "approval: artifact changed since grant -> DENY (stale, rejected outright -- not a warning)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
printf 'spec v1' > "$D/outputs/SPEC.md"
"$AP" grant bd-ap-3 pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
printf 'spec v2 tampered after approval' > "$D/outputs/SPEC.md"
out=$("$AP" verify bd-ap-3 pre-deploy 2>&1); rc=$?
assert_false "$rc" "verify must exit non-zero once the approved artifact has drifted"
assert_contains "$out" "DENY" "output should say DENY, never just a warning"
assert_contains "$out" "outputs/SPEC.md" "the DENY reason should name the specific drifted path"
rm -rf "$D"

t_start "approval: code changed (git commit moved) since grant -> DENY"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"
git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
"$AP" grant bd-ap-4 pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
printf 'unrelated file' > "$D/outputs/OTHER.md"
git -C "$D" add -A && git -C "$D" commit -q -m v2
out=$("$AP" verify bd-ap-4 pre-deploy 2>&1); rc=$?
assert_false "$rc" "verify must exit non-zero once git HEAD has moved since grant"
assert_contains "$out" "code changed" "the DENY reason should name 'code changed'"
rm -rf "$D"

t_start "approval: state rollback/drift (workflow state_version moved) since grant -> DENY"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"; export WFSTATE_ROOT="$D"
printf 'spec v1' > "$D/outputs/SPEC.md"
"$WF" init bd-ap-5 >/dev/null 2>&1
"$AP" grant bd-ap-5 pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
"$WF" advance bd-ap-5 1a-spec >/dev/null 2>&1
out=$("$AP" verify bd-ap-5 pre-deploy 2>&1); rc=$?
assert_false "$rc" "verify must exit non-zero once workflow state_version has moved since grant"
assert_contains "$out" "state changed" "the DENY reason should name 'state changed'"
rm -rf "$D"

t_start "approval: a stale approval is REJECTED, never a warn-and-pass -- exit code alone (not just message text) proves it blocks"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
printf 'v1' > "$D/outputs/SPEC.md"
"$AP" grant bd-ap-6 pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
printf 'v2' > "$D/outputs/SPEC.md"
"$AP" verify bd-ap-6 pre-deploy >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
  t_fail "a stale approval must not exit 0 under any circumstance -- a caller that only checks exit code (the normal case, e.g. 'approval.sh verify ... && deploy') would proceed"
else
  t_ok
fi
rm -rf "$D"

# =============================================================================
# (4b) approval: production-bound gates require a clean tree -- bd:shode-house-5cs.5
# =============================================================================

t_start "approval: grant on a CLEAN tree for a production-bound gate (pre-deploy) -- ALLOW, positive control"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
out=$("$AP" grant bd-clean1 pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_true "$rc" "grant on a clean tree for a production-bound gate must succeed"
assert_contains "$out" "GRANTED" "output should say GRANTED"
rm -rf "$D"

t_start "approval: grant refused when a TRACKED file has an UNSTAGED edit (git diff not clean) -- production-bound gate (pre-deploy)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'unstaged edit' >> "$D/outputs/SPEC.md"
out=$("$AP" grant bd-dirty1 pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when the tree has an unstaged edit"
assert_eq "$rc" "1" "refusal must be exit 1 DENY, not 64 or some other code"
assert_contains "$out" "DENY" "output should say DENY"
af="$D/.shode-house/approval/bd-dirty1--pre-deploy.json"
[ ! -f "$af" ] && t_ok || t_fail "no approval file should be written when grant is refused"
rm -rf "$D"

t_start "approval: grant refused when a TRACKED file has a STAGED (cached) edit (git diff --cached not clean) -- production-bound gate (pre-deploy)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'staged edit' >> "$D/outputs/SPEC.md"
git -C "$D" add -A
out=$("$AP" grant bd-dirty2 pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when the tree has a staged-but-uncommitted edit"
assert_contains "$out" "DENY" "output should say DENY"
rm -rf "$D"

t_start "approval: gate-name matching covers pre-deploy*, pre-merge*, and exact 'production' -- all refuse on a dirty tree"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'dirty' >> "$D/outputs/SPEC.md"
for gate in pre-deploy-prod pre-merge-fast production; do
  "$AP" grant bd-gates "$gate" scope dave outputs/SPEC.md >/dev/null 2>&1
  rc=$?
  assert_false "$rc" "gate '$gate' must be treated as production-bound and refuse on a dirty tree"
done
rm -rf "$D"

t_start "approval: NON-production gate keeps CURRENT behavior -- grant succeeds even with a dirty tree"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'dirty, but this gate does not care' >> "$D/outputs/SPEC.md"
out=$("$AP" grant bd-nonprod dev-review some-scope dave outputs/SPEC.md 2>&1); rc=$?
assert_true "$rc" "a non-production gate must still GRANT on a dirty tree (regression guard: unaffected behavior)"
assert_contains "$out" "GRANTED" "output should say GRANTED"
rm -rf "$D"

t_start "approval: repo where git is ABSENT ('n/a' path) is not broken by the clean-tree check -- production gate still grants"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
printf 'spec v1' > "$D/outputs/SPEC.md"
out=$("$AP" grant bd-nogit pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_true "$rc" "grant on a production gate in a non-git sandbox must still succeed (git_commit=n/a path preserved)"
assert_contains "$out" "GRANTED" "output should say GRANTED"
assert_contains "$out" "git_commit=n/a" "recorded git_commit should still be n/a when git is absent"
rm -rf "$D"

# =============================================================================
# (4c) approval: gate-list coverage gap -- bd:shode-house-5cs.5 iter1 F4 (Chris/Bella
# 3b-review: pre-data-migration + pre-destructive missing from the authoritative list
# at output-styles/oliver.md:99, the two most irreversible gates in the registry)
# =============================================================================

t_start "approval: pre-data-migration and pre-destructive are now treated as production-bound -- refuse on a dirty tree, same as pre-deploy*/pre-merge*"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'dirty' >> "$D/outputs/SPEC.md"
for gate in pre-data-migration pre-destructive pre-data-migration-users pre-destructive-drop-table; do
  out=$("$AP" grant bd-gates2 "$gate" scope dave outputs/SPEC.md 2>&1); rc=$?
  assert_false "$rc" "gate '$gate' must be treated as production-bound and refuse on a dirty tree (was missing from is_production_gate before this fix)"
  assert_contains "$out" "DENY" "output for gate '$gate' should say DENY"
done
rm -rf "$D"

t_start "approval: pre-data-migration and pre-destructive grant successfully on a CLEAN tree (positive control -- proves the new patterns don't over-block)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
for gate in pre-data-migration pre-destructive; do
  # bd:shode-house-5cs.5 iter3 -- clear any leftover approval JSON from the PRIOR loop
  # iteration first: under the singleton exemption a prior gate's own approval JSON is
  # a DIFFERENT bd/gate's file from this iteration's perspective and would (correctly)
  # count as dirty, which is not what this positive control is testing (each gate
  # granting cleanly on its own, in isolation).
  rm -rf "$D/.shode-house/approval"
  out=$("$AP" grant bd-gates3 "$gate" scope dave outputs/SPEC.md 2>&1); rc=$?
  assert_true "$rc" "gate '$gate' must GRANT on a clean tree"
  assert_contains "$out" "GRANTED" "output for gate '$gate' should say GRANTED"
done
rm -rf "$D"

# =============================================================================
# (4d) approval: untracked-file / gitignore matrix -- bd:shode-house-5cs.5 iter1 F5
# (Oliver ruling overrides iter0: clean tree means git status --porcelain empty,
# gitignored paths excluded)
# =============================================================================

t_start "approval: UNTRACKED file present (tracked tree otherwise clean) -> DENY -- Oliver ruling, a new unreviewed file is exactly the drift a production-bound gate must catch"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'sneaky new file, never committed' > "$D/outputs/SNEAKY-UNTRACKED.md"
out=$("$AP" grant bd-untracked pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when an untracked file is present, even though the TRACKED tree is clean"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" "SNEAKY-UNTRACKED.md" "the DENY reason should surface the untracked path (git status --porcelain output)"
af="$D/.shode-house/approval/bd-untracked--pre-deploy.json"
[ ! -f "$af" ] && t_ok || t_fail "no approval file should be written when grant is refused for an untracked file"
rm -rf "$D"

t_start "approval: RE-GRANTING the SAME bd/gate a second time (updating an existing approval) must NOT self-dirty the tree on its own leftover JSON -- bd:shode-house-5cs.5 iter3, singleton exemption is keyed to THIS call's own exact target path"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
out1=$("$AP" grant bd-self1 pre-deploy scope dave outputs/SPEC.md 2>&1); rc1=$?
assert_true "$rc1" "first grant on a clean tracked tree must succeed"
out2=$("$AP" grant bd-self1 pre-deploy scope2 dave2 outputs/SPEC.md 2>&1); rc2=$?
assert_true "$rc2" "a SECOND grant of the SAME bd/gate, right after the first grant wrote that exact approval JSON, must still succeed (not self-dirtied by its own prior write)"
assert_contains "$out2" "GRANTED" "second grant output should say GRANTED"
rm -rf "$D"

t_start "approval: a DIFFERENT bd/gate's approval JSON left over under .shode-house/approval/ is NOT this invocation's own target file -- must STILL DENY -- bd:shode-house-5cs.5 iter3, Chris Critical (reproduced a third time): the prior APPROVAL_DIR-prefix exemption let ANY untracked file inside the directory ride through, including a leftover approval for a bd/gate that has nothing to do with this grant call"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
out1=$("$AP" grant bd-other pre-merge scope dave outputs/SPEC.md 2>&1); rc1=$?
assert_true "$rc1" "priming grant for a DIFFERENT bd/gate on a clean tree must succeed"
out2=$("$AP" grant bd-target pre-deploy-prod scope dave outputs/SPEC.md 2>&1); rc2=$?
assert_false "$rc2" "a grant for bd-target/pre-deploy-prod must refuse when bd-other/pre-merge's leftover approval JSON is sitting untracked in the same directory -- it is not this invocation's file"
assert_contains "$out2" "DENY" "output should say DENY"
assert_contains "$out2" "bd-other--pre-merge.json" "the DENY reason should surface the OTHER bd/gate's leftover approval JSON path, proving it was actually seen and not exempted by directory membership alone"
af="$D/.shode-house/approval/bd-target--pre-deploy-prod.json"
[ ! -f "$af" ] && t_ok || t_fail "no approval file should be written when grant is refused"
rm -rf "$D"

t_start "approval: an unrelated untracked, non-approval file dropped directly beside the approval JSON inside .shode-house/approval/ (this call's OWN scope boundary) -- must STILL DENY -- bd:shode-house-5cs.5 iter3, Oliver's exact repro (payload.sh next to the approval JSON)"
D=$(sandbox); mkdir -p "$D/.shode-house/approval" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'echo pwned\n' > "$D/.shode-house/approval/payload.sh"
out=$("$AP" grant bd-1 pre-deploy-prod all oliver outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when an unrelated untracked file (not this call's own target) sits directly inside APPROVAL_DIR"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" ".shode-house/approval/payload.sh" "the DENY reason should surface the untracked payload path, proving it was actually seen and not exempted by directory membership alone"
af="$D/.shode-house/approval/bd-1--pre-deploy-prod.json"
[ ! -f "$af" ] && t_ok || t_fail "no approval file should be written when grant is refused"
rm -rf "$D"

t_start "approval: a TRACKED file inside .shode-house/approval/ itself -- must STILL DENY a production-bound grant -- bd:shode-house-5cs.5 iter3: the singleton exemption only ever drops an untracked ('??') line, never a tracked one, so a tracked file inside APPROVAL_DIR is unaffected by the exemption at all and blocks like any other tracked drift"
D=$(sandbox); mkdir -p "$D/.shode-house/approval" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
printf 'not an approval json' > "$D/.shode-house/approval/tracked-thing.txt"
git -C "$D" add -A && git -C "$D" commit -q -m "v1 (a tracked file under .shode-house/approval/ -- against convention, but not prevented)"
printf 'tampered' >> "$D/.shode-house/approval/tracked-thing.txt"
out=$("$AP" grant bd-2 pre-deploy-prod all oliver outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when a tracked file inside APPROVAL_DIR has an unstaged edit"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" ".shode-house/approval/tracked-thing.txt" "the DENY reason should surface the tracked path inside APPROVAL_DIR, proving it was actually seen"
af="$D/.shode-house/approval/bd-2--pre-deploy-prod.json"
[ ! -f "$af" ] && t_ok || t_fail "no approval file should be written when grant is refused"
rm -rf "$D"

t_start "approval: a TRACKED, modified file under .shode-house/ must STILL DENY a production-bound grant -- bd:shode-house-5cs.5 iter2, Chris Critical (reproduced): the prior blanket ':!.shode-house' pathspec exclusion hid a real, tracked, modified file from every production gate, including pre-deploy-prod"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
mkdir -p "$D/.shode-house/sneaky-real-code"
printf 'echo pwned' > "$D/.shode-house/sneaky-real-code/payload.sh"
git -C "$D" add -A && git -C "$D" commit -q -m "v1 (.shode-house tracked -- against convention, but not prevented)"
printf 'echo pwned v2 -- REAL CHANGE' > "$D/.shode-house/sneaky-real-code/payload.sh"
out=$("$AP" grant sneaky-bd pre-deploy-prod scope dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "a tracked, modified file under .shode-house/ must refuse a pre-deploy-prod grant -- must NOT be invisible to the clean-tree check"
assert_eq "$rc" "1" "refusal must be exit 1 DENY"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" ".shode-house/sneaky-real-code/payload.sh" "the DENY reason should surface the tracked path under .shode-house/, proving it was actually seen"
rm -rf "$D"

t_start "approval: an UNTRACKED, non-bookkeeping file nested under .shode-house/ (not this tool's own approval JSON) must STILL DENY a production-bound grant -- only untracked entries git reports as being exactly this tool's own bookkeeping are meant to be excluded, not the whole subtree by path alone"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
mkdir -p "$D/.shode-house/sneaky-real-code"
printf 'echo pwned, never committed' > "$D/.shode-house/sneaky-real-code/new.sh"
out=$("$AP" grant sneaky-bd2 pre-deploy-prod scope dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "a brand-new untracked file under .shode-house/ that is NOT this tool's own approval JSON must still refuse a pre-deploy-prod grant"
assert_contains "$out" "DENY" "output should say DENY"
rm -rf "$D"

t_start "approval: only a .gitignore'd file present (tracked tree clean, no untracked-visible files) -> GRANT -- ignored paths must NOT block"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
printf 'ignored.log\n' > "$D/.gitignore"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'build noise, gitignored' > "$D/ignored.log"
out=$("$AP" grant bd-ignored pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_true "$rc" "grant must succeed when the only dirty-looking path is gitignored"
assert_contains "$out" "GRANTED" "output should say GRANTED"
rm -rf "$D"

# =============================================================================
# (4e) approval: git_head() unborn-repo contract -- bd:shode-house-5cs.5 iter4, Quinn
# 3b-review Medium. In a git repo with ZERO commits, `git rev-parse HEAD` writes its
# best-effort partial resolution ("HEAD") to stdout AND fails non-zero at the same time;
# the un-gated `2>/dev/null || printf 'n/a'` one-liner let that stray stdout leak into the
# same command substitution as the fallback, producing a corrupted two-line
# "HEAD\nn/a" instead of the documented clean "n/a". Confirmed NOT exploitable into a
# false ALLOW (both directions of the non-git <-> zero-commit transition still DENY/skip
# safely) -- this locks in the field's own data contract regardless.
# =============================================================================

t_start "approval: git_head() in a git repo with ZERO commits records the clean sentinel 'n/a' -- not the corrupted 'HEAD\\nn/a'"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"   # no commit at all -- HEAD is unborn
printf 'spec, never committed' > "$D/outputs/SPEC.md"
out=$("$AP" grant bd-unborn pre-spec-expand scope dave outputs/SPEC.md 2>&1); rc=$?
assert_true "$rc" "grant on a non-production gate in an unborn (zero-commit) repo must still succeed"
assert_contains "$out" "git_commit=n/a" "CLI confirmation must show the clean single-line sentinel, not a garbled multi-line one"
af="$D/.shode-house/approval/bd-unborn--pre-spec-expand.json"
stored=$(jq -r '.git_commit' "$af")
assert_eq "$stored" "n/a" "stored git_commit must be the exact clean string 'n/a' (a corrupted value would be 'HEAD\\nn/a' -- jq -r would print two lines, not equal to 'n/a')"
line_count=$(printf '%s' "$stored" | wc -l | tr -d ' ')
assert_eq "$line_count" "0" "stored git_commit must be a single line (0 embedded newlines) -- the old bug embedded a literal newline inside the JSON string value"
rm -rf "$D"

# =============================================================================
# (4f) approval: mainline breakage from the singleton exemption disappears when the
# TARGET PROJECT'S OWN .gitignore contains the runtime dir -- bd:shode-house-5cs.5 iter4,
# per user ruling (Option A): the exemption itself does NOT change. The fix is that a
# gitignored, untracked approval JSON never appears in `git status --porcelain` at all
# (git's own default behavior -- unaffected by this bd's code), so it can never again be
# cited as "dirty" for a LATER, unrelated grant. These tests exercise the UNTOUCHED
# approval.sh exemption logic under a `.gitignore`'d `/.shode-house/`, to lock in that the
# distinction is real and does not silently widen what the exemption itself covers.
# =============================================================================

t_start "approval: WITH '/.shode-house/' in .gitignore -- grant A (bd-100/pre-deploy) then grant B (bd-200/pre-merge, a DIFFERENT bd/gate) both GRANT -- the mainline case this bd exists to fix"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
printf '/.shode-house/\n' > "$D/.gitignore"
git -C "$D" add -A && git -C "$D" commit -q -m v1
out1=$("$AP" grant bd-100 pre-deploy scope dave outputs/SPEC.md 2>&1); rc1=$?
assert_true "$rc1" "grant A must succeed on a clean, .shode-house/-ignoring tree"
assert_contains "$out1" "GRANTED" "grant A output should say GRANTED"
out2=$("$AP" grant bd-200 pre-merge scope dave outputs/SPEC.md 2>&1); rc2=$?
assert_true "$rc2" "grant B (a DIFFERENT bd/gate) must ALSO succeed -- grant A's own approval JSON is untracked AND gitignored, so it never reaches git status --porcelain at all, and is never cited as dirty; this is unrelated to (does not widen) the singleton exemption itself"
assert_contains "$out2" "GRANTED" "grant B output should say GRANTED"
rm -rf "$D"

t_start "approval: WITHOUT the ignore rule (contrast case, same shape) -- grant B for a DIFFERENT bd/gate still DENYs, citing grant A's own leftover approval JSON -- proves the fix above is caused by the ignore rule, not by any change to the exemption's matching logic (already covered by the singleton-exemption test above at 'a DIFFERENT bd/gate's approval JSON left over', re-asserted here bd:shode-house-5cs.5 iter4 for direct side-by-side contrast with the .gitignore'd case immediately above)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1   # deliberately no .gitignore this time
out1=$("$AP" grant bd-100 pre-deploy scope dave outputs/SPEC.md 2>&1); rc1=$?
assert_true "$rc1" "grant A must still succeed (unaffected)"
out2=$("$AP" grant bd-200 pre-merge scope dave outputs/SPEC.md 2>&1); rc2=$?
assert_false "$rc2" "grant B for a DIFFERENT bd/gate must DENY when the runtime dir is NOT gitignored -- proves the mainline fix is specifically the ignore rule, and the singleton exemption never widened to cover a different bd/gate's file"
assert_contains "$out2" "DENY" "grant B output should say DENY"
assert_contains "$out2" "bd-100--pre-deploy.json" "the DENY reason should surface grant A's own leftover approval JSON path"
rm -rf "$D"

t_start "approval: WITH '/.shode-house/' in .gitignore -- a TRACKED, modified file under .shode-house/ still DENYs a production-bound grant -- the ignore rule must not reopen the original Critical (bd:shode-house-5cs.5 iter2)"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
mkdir -p "$D/.shode-house/sneaky-real-code"
printf 'echo pwned' > "$D/.shode-house/sneaky-real-code/payload.sh"
git -C "$D" add -A && git -C "$D" commit -q -m "v1 (deploy.sh tracked BEFORE the ignore rule exists)"
printf '/.shode-house/\n' > "$D/.gitignore"
git -C "$D" add .gitignore && git -C "$D" commit -q -m "add ignore rule after the fact"
printf 'echo pwned v2 -- REAL CHANGE' > "$D/.shode-house/sneaky-real-code/payload.sh"
out=$("$AP" grant sneaky-bd pre-deploy-prod scope dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "a tracked, modified file under a NOW-gitignored .shode-house/ must still refuse a pre-deploy-prod grant -- git reports TRACKED file modifications regardless of .gitignore"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" ".shode-house/sneaky-real-code/payload.sh" "the DENY reason should surface the tracked, modified path even though the directory is now gitignored"
rm -rf "$D"

t_start "approval: WITH '/.shode-house/' in .gitignore -- an unrelated untracked file OUTSIDE .shode-house/ still DENYs -- the ignore rule must not widen beyond the runtime dir"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
printf '/.shode-house/\n' > "$D/.gitignore"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'sneaky new file, never committed' > "$D/outputs/SNEAKY-UNTRACKED.md"
out=$("$AP" grant bd-untracked2 pre-deploy production-deploy dave outputs/SPEC.md 2>&1); rc=$?
assert_false "$rc" "grant must refuse when an untracked file OUTSIDE the ignored runtime dir is present, ignore rule notwithstanding"
assert_contains "$out" "DENY" "output should say DENY"
assert_contains "$out" "SNEAKY-UNTRACKED.md" "the DENY reason should surface the untracked path outside .shode-house/"
rm -rf "$D"

# =============================================================================
# mutation axes (task's VERIFY BEFORE DONE requirement -- run as literal shell mutations
# against a scratch copy of the real scripts, confirm red, then confirm the originals
# stay green (no in-place mutation of the committed files))
# =============================================================================

t_start "MUTATION (a): disabling the retry cap check must turn the cap-enforcement test red"
MUT=$(mktemp -t wf-mut.XXXXXX.sh)
sed 's/\[ "\$cur_count" -ge "\$cap" \]/false/' "$WF" > "$MUT"
chmod +x "$MUT"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"
# the mutated copy lives outside scripts/, so its own SELF_DIR-relative lookup of
# references/state-machine/{transitions,errors}.json AND scripts/lib/lock.sh would
# resolve to a bogus path -- point them at the real repo's copies explicitly (same
# override mechanism the mutated script itself already supports, not a special case
# added for this test; bd:shode-house-vz8 added the lock.sh one).
export WFSTATE_TRANSITIONS="$REPO_ROOT/references/state-machine/transitions.json"
export WFSTATE_ERRORS="$REPO_ROOT/references/state-machine/errors.json"
export WFSTATE_LOCK_LIB="$REPO_ROOT/scripts/lib/lock.sh"
"$MUT" init mut-a >/dev/null 2>&1
"$MUT" retry mut-a TRANSIENT >/dev/null 2>&1
"$MUT" retry mut-a TRANSIENT >/dev/null 2>&1
out=$("$MUT" retry mut-a TRANSIENT 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then
  t_ok   # mutation correctly broke the cap (3rd retry now wrongly allowed) -> confirms the
         # REAL script's own cap-enforcement test above (which asserts rc!=0 here) is the
         # thing actually catching this, i.e. the check is load-bearing
else
  t_fail "mutated script (cap check disabled) should have let the 3rd retry through, but it still rejected -- the sed patch did not land, this mutation check is not proving anything"
fi
unset WFSTATE_TRANSITIONS WFSTATE_ERRORS WFSTATE_LOCK_LIB
rm -rf "$D" "$MUT"

t_start "MUTATION (b): swapping rework-routing.json's 'code' target must turn the routing test red"
MUTROUTE=$(mktemp -t rework-mut.XXXXXX.json)
jq '.routes.code = "1b-design"' "$REPO_ROOT/references/state-machine/rework-routing.json" > "$MUTROUTE"
D=$(sandbox); mkdir -p "$D/.shode-house"; export WFSTATE_ROOT="$D"; export WFSTATE_REWORK_ROUTING="$MUTROUTE"
"$WF" init mut-b >/dev/null 2>&1
walk_to_4triage mut-b
"$WF" rework mut-b code >/dev/null 2>&1
sf="$D/.shode-house/state/mut-b.json"
routed_to=$(jq -r '.current_phase' "$sf")
if [ "$routed_to" = "1b-design" ]; then
  t_ok   # confirms the routing table (not something else) is what decided the target --
         # the real test above ("rework: class=code ... routes to 2-implement") reads
         # the UNMUTATED rework-routing.json and would go red if that file's 'code' row
         # were ever changed to anything other than 2-implement
else
  t_fail "mutated routing table should have sent class=code to 1b-design, got '$routed_to' -- mutation did not take effect, this check is not proving anything"
fi
unset WFSTATE_REWORK_ROUTING
rm -rf "$D" "$MUTROUTE"

t_start "MUTATION (c): letting a stale approval pass verify must turn the invalidation test red"
MUTAP=$(mktemp -t approval-mut.XXXXXX.sh)
sed 's/\[ "\$fail" -eq 1 \]; then/false; then/' "$AP" > "$MUTAP"
chmod +x "$MUTAP"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
printf 'v1' > "$D/outputs/SPEC.md"
"$MUTAP" grant mut-c pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1
printf 'v2 tampered' > "$D/outputs/SPEC.md"
"$MUTAP" verify mut-c pre-deploy >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then
  t_ok   # mutation correctly broke the DENY gate (stale approval now wrongly ALLOWed) ->
         # confirms the real "artifact changed since grant -> DENY" test above (which
         # asserts non-zero exit against the UNMUTATED approval.sh) is load-bearing
else
  t_fail "mutated approval.sh (fail-check disabled) should have let a stale approval verify as ALLOW, but it still denied -- the sed patch did not land, this mutation check is not proving anything"
fi
rm -rf "$D" "$MUTAP"

t_start "MUTATION (d): disabling production-gate name matching must turn the clean-tree-refusal test red"
MUTAP2=$(mktemp -t approval-mut2.XXXXXX.sh)
sed 's/case "\$1" in/case "__never_matches__" in/' "$AP" > "$MUTAP2"
chmod +x "$MUTAP2"
D=$(sandbox); mkdir -p "$D/.shode-house" "$D/outputs"; export APPROVAL_ROOT="$D"
git init -q "$D"; git -C "$D" config user.email "t@t.local"; git -C "$D" config user.name "t"
printf 'spec v1' > "$D/outputs/SPEC.md"
git -C "$D" add -A && git -C "$D" commit -q -m v1
printf 'dirty' >> "$D/outputs/SPEC.md"
"$MUTAP2" grant mut-d pre-deploy production-deploy dave outputs/SPEC.md >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then
  t_ok   # mutation correctly broke is_production_gate (pre-deploy no longer recognized as
         # production-bound) -> GRANTED wrongly succeeded on a dirty tree -> confirms the
         # REAL script's "grant refused ... unstaged edit" / "gate-name matching" tests
         # above (which assert rc!=0 against the UNMUTATED approval.sh) are load-bearing
else
  t_fail "mutated approval.sh (gate-name matching disabled) should have let grant succeed on a dirty tree for gate 'pre-deploy', but it still refused -- the sed patch did not land, this mutation check is not proving anything"
fi
rm -rf "$D" "$MUTAP2"

echo
echo "== revert check: originals are untouched by the mutation tests above (they operated on scratch copies only) =="
jq empty "$WF" >/dev/null 2>&1 || true   # workflow-state.sh is not JSON; syntax-check instead
bash -n "$WF" >/dev/null 2>&1; assert_true "$?" "scripts/workflow-state.sh must still be syntactically valid (untouched by mutation (a))"
bash -n "$AP" >/dev/null 2>&1; assert_true "$?" "scripts/approval.sh must still be syntactically valid (untouched by mutation (c))"
jq empty "$REPO_ROOT/references/state-machine/rework-routing.json" >/dev/null 2>&1
assert_true "$?" "rework-routing.json must still be valid JSON (untouched by mutation (b))"
assert_eq "$(jq -r '.routes.code' "$REPO_ROOT/references/state-machine/rework-routing.json")" "2-implement" \
  "rework-routing.json's real 'code' route must still be 2-implement (mutation (b) only ever touched a scratch copy)"

# =============================================================================
# packaging: make pack ships the two new scripts (same pattern test-workflow-state.sh's
# own packaging test already uses for the Milestone A files)
# =============================================================================
t_start "packaging: make pack ships scripts/side-effect.sh + scripts/approval.sh + the new state-machine data files"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "scripts/side-effect.sh" "packed artifact must ship side-effect.sh"
assert_contains "$listing" "scripts/approval.sh" "packed artifact must ship approval.sh"
assert_contains "$listing" "references/state-machine/errors.json" "packed artifact must ship errors.json"
assert_contains "$listing" "references/state-machine/rework-routing.json" "packed artifact must ship rework-routing.json"

unset WFSTATE_ROOT SIDEEFFECT_ROOT APPROVAL_ROOT WFSTATE_REWORK_ROUTING

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
