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

t_start "side-effect: in_progress status is not treated as done -- check still allows proceeding"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SIDEEFFECT_ROOT="$D"
"$SE" record bd-se-5 migration KEY-E in_progress "started" >/dev/null 2>&1
out=$("$SE" check bd-se-5 KEY-E 2>&1); rc=$?
assert_true "$rc" "check should still be NOT_DONE while status=in_progress"
assert_contains "$out" "NOT_DONE" "output should say NOT_DONE"
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
# references/state-machine/{transitions,errors}.json would resolve to a bogus path --
# point it at the real repo's copies explicitly (same override mechanism the mutated
# script itself already supports, not a special case added for this test).
export WFSTATE_TRANSITIONS="$REPO_ROOT/references/state-machine/transitions.json"
export WFSTATE_ERRORS="$REPO_ROOT/references/state-machine/errors.json"
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
unset WFSTATE_TRANSITIONS WFSTATE_ERRORS
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
pack_out=$(cd "$REPO_ROOT" && make pack-legacy 2>&1); pack_rc=$?
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
