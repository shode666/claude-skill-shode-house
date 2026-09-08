#!/usr/bin/env bash
# workflow-state.sh -- Milestone A phase-graph + reconciliation (bd: shode-roadmap/C-A5, iter 2)
#
# Builds on the iter-0/1 tracer bullet (bd: shode-roadmap/C-A4) -- see
# outputs/shode-roadmap/C/09-dave-workflow-state.md for that history. This iteration:
#   1. Expands the 6-node MVP graph to the real 10-node shode-house phase set, driven
#      entirely by references/state-machine/transitions.json (states/conditional_phases/
#      enter_requires/transitions) -- no phase or edge name is hardcoded in this script.
#   2. Adds `reconcile <bd-id>` (ROADMAP-runtime-10.md SS2.2, 6 checks).
#
#   workflow-state.sh init <bd-id>
#   workflow-state.sh validate <bd-id>
#   workflow-state.sh advance <bd-id> <phase> [<outcome>]
#   workflow-state.sh reconcile <bd-id>
#
# <outcome> (advance's 3rd, optional arg; default "passed") is the ending status the
# *current* phase (the transition's `from`) receives once this call is accepted:
#   passed    -- default; clean forward move
#   skipped   -- only legal when `from` is in transitions.json's conditional_phases
#   failed    -- for backward/rework edges (e.g. 3b-review -review-fail-> 2-implement)
#   escalated -- special self-transition, see the cmd_advance comment below; not a
#                graph edge, does not need an entry in transitions.json's "transitions"
#
# Deps: bash + jq + shasum (ADR-C3 -- no python3 in the hot path; shasum already used by
# tests/test-workflow-state.sh in iter0, so it's an established, CI-verified dependency).
#
# Engagement guard: every command is a no-op (exit 0, silent, no side effect) unless
# "$ROOT/.shode-house" already exists. This script never creates that top-level dir --
# it is assumed created by a separate bootstrap step (/init rule 11, out of this task's
# scope). This is intentional so an unrelated repo that never opted into shode-house
# workflow-state is never touched.
#
# bd is an OPTIONAL MIRROR, not a dependency (outputs/shode-roadmap/C/05-oliver-decisions.md
# #6 / ADR-C6): `reconcile`'s bd-dependent checks (1 and 2) are SKIPPED -- loudly, with a
# printed reason -- when `bd` is not on PATH or there is no active bd workspace. They are
# never silently treated as PASS, and a missing bd never crashes the script.
#
# ROOT can be overridden with WFSTATE_ROOT (used by the test suite to run inside an
# isolated tmp dir instead of the real repo cwd).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${WFSTATE_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
STATE_DIR="$SHODE_DIR/state"
JOURNAL_DIR="$SHODE_DIR/journal"
TRANSITIONS="${WFSTATE_TRANSITIONS:-$SELF_DIR/../references/state-machine/transitions.json}"

# 9-value phase-status enum -- outputs/shode-roadmap/C/05-oliver-decisions.md #4
STATUS_ENUM="pending ready in_progress blocked conditional_pass passed failed skipped escalated"
# statuses a phase may be advanced *away from* (FR-201 rule 2, simplified for this
# tracer bullet -- see "sing thi cong-jai mai tham" in the hand-off artifact)
FROM_ELIGIBLE="in_progress passed conditional_pass"
# outcomes advance()'s optional 3rd arg accepts -- see header comment above
OUTCOME_ENUM="passed skipped failed escalated"
# iter cap before a phase must be escalated instead of retried again (Oliver decision #4 /
# smart-coop.md "iter > 3 -> escalate")
ITER_CAP=3

log_err() { printf 'workflow-state.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 1; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

timestamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

encode_bd() { printf '%s' "$1" | sed 's#/#--#g'; }

state_file()   { printf '%s/%s.json'  "$STATE_DIR"   "$(encode_bd "$1")"; }
journal_file() { printf '%s/%s.jsonl' "$JOURNAL_DIR" "$(encode_bd "$1")"; }
lock_dir()     { printf '%s/.lock-%s' "$STATE_DIR"   "$(encode_bd "$1")"; }

is_known_phase() {
  jq -e --arg p "$1" '.states | index($p) != null' "$TRANSITIONS" >/dev/null 2>&1
}

edge_exists() {
  jq -e --arg f "$1" --arg t "$2" \
    '.transitions | any(.from == $f and .to == $t)' "$TRANSITIONS" >/dev/null 2>&1
}

is_conditional_phase() {
  jq -e --arg p "$1" '.conditional_phases // [] | index($p) != null' "$TRANSITIONS" >/dev/null 2>&1
}

is_known_status() {
  case " $STATUS_ENUM " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

from_status_eligible() {
  case " $FROM_ELIGIBLE " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

# ---- enter_requires: generic gate, driven entirely by transitions.json's enter_requires
# object -- this function does not know any phase name. For target phase $to, every
# {required_phase: [allowed_statuses]} entry must be satisfied by the CURRENT state,
# except when required_phase == $from: since $from's status is being set to $outcome as
# part of THIS very call (the from-phase update and the to-phase entry are atomic in one
# advance()), we must check the pending $outcome value there, not the pre-call value --
# otherwise entering phase_2 immediately after phase_1c finally passes would always look
# like phase_1c is still "in_progress" and reject itself. Sets ENTER_REQ_FAIL_REASON on
# failure (bash functions here run in the caller's shell, not a subshell, since the while
# loop is fed via `< <(...)` process substitution -- so this global assignment is visible
# to the caller).
ENTER_REQ_FAIL_REASON=""
enter_requires_check() {
  local sf="$1" to="$2" from="$3" outcome="$4"
  ENTER_REQ_FAIL_REASON=""
  local n; n=$(jq -r --arg to "$to" '.enter_requires[$to] // {} | length' "$TRANSITIONS")
  [ "$n" = "0" ] && return 0
  local phase allowed_csv actual
  while IFS=$'\t' read -r phase allowed_csv; do
    [ -z "$phase" ] && continue
    if [ "$phase" = "$from" ]; then
      actual="$outcome"
    else
      actual=$(jq -r --arg p "$phase" '.phases[$p].status // "pending"' "$sf")
    fi
    case ",$allowed_csv," in
      *",$actual,"*) ;;
      *)
        ENTER_REQ_FAIL_REASON="enter_requires for '$to' failed: phase '$phase' status '$actual' not in allowed [$allowed_csv]"
        return 1
        ;;
    esac
  done < <(jq -r --arg to "$to" '.enter_requires[$to] // {} | to_entries[] | [.key, (.value | join(","))] | @tsv' "$TRANSITIONS")
  [ -n "$ENTER_REQ_FAIL_REASON" ] && return 1
  return 0
}

# ---- artifact hashing: pins a sha256 per artifact path recorded on a phase, at the
# moment that phase's status is set (any outcome). Files that don't (yet) exist on disk
# are skipped here -- that is check 3 (artifact-path-missing)'s job, not this one's.
# Prints a JSON object {"path": "sha256", ...} (or "{}" if no artifacts / none present).
compute_artifact_hashes_json() {
  local sf="$1" phase="$2"
  local paths; paths=$(jq -r --arg p "$phase" '.phases[$p].artifacts[]? // empty' "$sf")
  [ -z "$paths" ] && { printf '{}'; return; }
  local first=1 p fpath h
  printf '{'
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    fpath="$ROOT/$p"
    [ -f "$fpath" ] || continue
    h=$(shasum -a 256 "$fpath" 2>/dev/null | awk '{print $1}')
    [ -z "$h" ] && continue
    [ "$first" -eq 1 ] && first=0 || printf ','
    printf '%s:%s' "$(jq -n --arg s "$p" '$s')" "$(jq -n --arg s "$h" '$s')"
  done <<<"$paths"
  printf '}'
}

# ---- bd: optional mirror, never a dependency (Oliver decision #6 / ADR-C6). Always
# invoked with `-C "$ROOT"` so it resolves the workspace relative to the engagement
# root (which may differ from the process's own cwd -- e.g. under WFSTATE_ROOT in
# tests, or if this script is invoked from a subdirectory in real usage), never by
# accidentally falling back to whatever bd workspace happens to be discoverable from
# the caller's actual shell cwd.
bd_available() {
  command -v bd >/dev/null 2>&1 || return 1
  bd -C "$ROOT" where >/dev/null 2>&1 || return 1
  return 0
}

# ---- lock: mkdir is atomic on POSIX (ADR-C5). Reaps a lock whose holder pid is dead
# or whose age > 600s (stale-crash cleanup folded in here since hooks/SessionStart
# reaping is out of this tracer bullet's scope). Waits up to ~2s otherwise, then fails
# loud (never blocks forever).
acquire_lock() {
  local lockd="$1" waited=0
  while ! mkdir "$lockd" 2>/dev/null; do
    local pid="" ts="" now_epoch age
    [ -f "$lockd/pid" ] && pid=$(cat "$lockd/pid" 2>/dev/null)
    [ -f "$lockd/ts" ]  && ts=$(cat "$lockd/ts" 2>/dev/null)
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      rm -rf "$lockd" 2>/dev/null
      continue
    fi
    if [ -n "$ts" ]; then
      now_epoch=$(date +%s)
      age=$((now_epoch - ts))
      if [ "$age" -gt 600 ]; then
        rm -rf "$lockd" 2>/dev/null
        continue
      fi
    fi
    waited=$((waited + 1))
    [ "$waited" -ge 20 ] && return 1
    sleep 0.1
  done
  printf '%s' "$$" > "$lockd/pid"
  date +%s > "$lockd/ts"
  return 0
}

release_lock() { rm -rf "$1" 2>/dev/null || true; }

next_journal_seq() {
  local jf; jf=$(journal_file "$1")
  [ -f "$jf" ] || { echo 1; return; }
  local last
  last=$(tail -n 1 "$jf" 2>/dev/null | jq -r '.seq // 0' 2>/dev/null)
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  echo $((last + 1))
}

append_journal() {
  local bd="$1" seq="$2" ts="$3" from="$4" to="$5" actor="$6" result="$7" reason="$8"
  local jf; jf=$(journal_file "$bd")
  jq -nc \
    --argjson seq "$seq" --arg ts "$ts" --arg bd "$bd" \
    --arg from "$from" --arg to "$to" --arg actor "$actor" \
    --arg result "$result" --arg reason "$reason" \
    '{seq:$seq, ts:$ts, bd_id:$bd, from:$from, to:$to, actor:$actor, result:$result, reason:$reason}' \
    >> "$jf"
}

usage() {
  cat >&2 <<'EOF'
usage: workflow-state.sh init <bd-id>
       workflow-state.sh validate <bd-id>
       workflow-state.sh advance <bd-id> <phase> [<outcome>]
       workflow-state.sh reconcile <bd-id>
EOF
}

cmd_init() {
  local bd="${1:-}"
  [ -n "$bd" ] || { usage; die "init: <bd-id> required"; }
  engagement_active || exit 0

  mkdir -p "$STATE_DIR" "$JOURNAL_DIR"
  local sf; sf=$(state_file "$bd")
  if [ -f "$sf" ]; then
    die "init: state already exists for '$bd' at $sf -- use advance to move it, not init"
  fi

  local now; now=$(timestamp)
  local tmp; tmp=$(mktemp "$STATE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  # phases{} is built entirely from transitions.json's states[] -- no phase name is
  # hardcoded here. First declared state starts in_progress, every other state pending.
  jq -n --arg bd "$bd" --arg now "$now" --slurpfile tj "$TRANSITIONS" '
    ($tj[0].states) as $states
    | {
        schema_version: 2,
        bd_id: $bd,
        current_phase: $states[0],
        seq: 0,
        iter: 0,
        phases: (reduce $states[] as $s ({};
          . + {($s): {
            status: (if $s == $states[0] then "in_progress" else "pending" end),
            owners: [],
            artifacts: [],
            artifact_hashes: {}
          }}
        )),
        updated_at: $now
      }' > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "init: generated state failed schema validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$sf"

  local jf; jf=$(journal_file "$bd")
  [ -f "$jf" ] || : > "$jf"
  local first_phase; first_phase=$(jq -r '.current_phase' "$sf")
  append_journal "$bd" 1 "$now" "null" "$first_phase" "${WFSTATE_ACTOR:-${USER:-unknown}}" "accept" "init"

  printf 'init: created %s (current_phase=%s)\n' "$sf" "$first_phase"
}

cmd_validate() {
  local bd="${1:-}"
  [ -n "$bd" ] || { usage; die "validate: <bd-id> required"; }
  engagement_active || exit 0

  local sf; sf=$(state_file "$bd")
  [ -f "$sf" ] || die "validate: no state file for '$bd' (run init first)"
  jq empty "$sf" >/dev/null 2>&1 || die "validate: $sf is not valid JSON"

  local errors=0
  jq -e '(.schema_version | type) == "number"' "$sf" >/dev/null 2>&1 \
    || { log_err "validate: missing/invalid schema_version"; errors=1; }

  local file_bd; file_bd=$(jq -r '.bd_id // ""' "$sf")
  [ "$file_bd" = "$bd" ] \
    || { log_err "validate: bd_id mismatch (file has '$file_bd', expected '$bd')"; errors=1; }

  local cur; cur=$(jq -r '.current_phase // ""' "$sf")
  if is_known_phase "$cur"; then :; else
    log_err "validate: current_phase '$cur' is not a known phase"; errors=1
  fi

  while IFS=$'\t' read -r phase status; do
    [ -z "$phase" ] && continue
    if ! is_known_status "$status"; then
      log_err "validate: phase '$phase' has unknown status '$status' (not in 9-value enum)"
      errors=1
    fi
  done < <(jq -r '.phases | to_entries[] | [.key, .value.status] | @tsv' "$sf" 2>/dev/null)

  while IFS= read -r path; do
    [ -z "$path" ] && continue
    [ -e "$ROOT/$path" ] || { log_err "validate: artifact path missing on disk: $path"; errors=1; }
  done < <(jq -r '.phases[].artifacts[]?' "$sf" 2>/dev/null)

  if [ "$errors" -eq 0 ]; then
    printf 'validate: OK (%s) current_phase=%s\n' "$bd" "$cur"
    exit 0
  fi
  exit 1
}

cmd_advance() {
  local bd="${1:-}" to="${2:-}" outcome="${3:-passed}"
  if [ -z "$bd" ] || [ -z "$to" ]; then
    usage; die "advance: <bd-id> and <phase> required"
  fi
  engagement_active || exit 0

  case "$outcome" in
    passed|skipped|failed|escalated) : ;;
    *) usage; die "advance: unknown outcome '$outcome' (must be one of: $OUTCOME_ENUM)" ;;
  esac

  local sf; sf=$(state_file "$bd")
  [ -f "$sf" ] || die "advance: no state file for '$bd' (run init first)"

  local lockd; lockd=$(lock_dir "$bd")
  acquire_lock "$lockd" || die "advance: could not acquire lock for '$bd' -- another writer in progress (${lockd})"
  trap 'release_lock "'"$lockd"'"' EXIT

  # crash-recovery hygiene: a prior crashed advance may have left a tmp state file --
  # never leave ambiguous litter around, but never touch the live state file itself.
  rm -f "$STATE_DIR/.tmp.$(encode_bd "$bd")".* 2>/dev/null || true

  local from seq iter from_status
  from=$(jq -r '.current_phase' "$sf")
  seq=$(jq -r '.seq' "$sf")
  iter=$(jq -r '.iter' "$sf")
  from_status=$(jq -r --arg p "$from" '.phases[$p].status // "unknown"' "$sf")

  local ok=1 reason=""

  # ---- escalated is a SELF-transition (to == from), not a phase-graph edge. It marks
  # the phase currently stuck in a retry loop as escalated -- "needs a human decision,
  # do not auto-retry" (state schema note, outputs/shode-roadmap/C/01-bella-spec-1a.md
  # SS2). It deliberately does not require (or check) transitions.json's edge table:
  # declaring 10 identical self-loop rows there (one per phase) would be pure noise --
  # this action is generic across every phase by construction (to==from), so it is not
  # "an edge outside transitions.json" in the sense the routing table exists to prevent
  # (routing DATA between distinct phases). See outputs/shode-roadmap/C/09-dave-workflow-state.md
  # "iter 2" for the full design-decision writeup.
  if [ "$outcome" = "escalated" ]; then
    if [ "$to" != "$from" ]; then
      ok=0; reason="escalated outcome requires self-transition (to must equal current phase '$from'), got '$to'"
    elif [ "$iter" -le "$ITER_CAP" ]; then
      ok=0; reason="escalated outcome not applicable -- iter=$iter has not exceeded the cap ($ITER_CAP) for phase '$from'"
    elif ! from_status_eligible "$from_status"; then
      ok=0; reason="prev status '$from_status' for phase '$from' not eligible (need one of: $FROM_ELIGIBLE)"
    fi
  else
    if [ "$iter" -gt "$ITER_CAP" ]; then
      ok=0; reason="iter>3 requires escalated transition first"
    elif ! is_known_phase "$to"; then
      ok=0; reason="unknown phase '$to' (not in transitions.json states)"
    elif ! edge_exists "$from" "$to"; then
      ok=0; reason="no such edge '$from' -> '$to'"
    elif ! from_status_eligible "$from_status"; then
      ok=0; reason="prev status '$from_status' for phase '$from' not eligible (need one of: $FROM_ELIGIBLE)"
    elif [ "$outcome" = "skipped" ] && ! is_conditional_phase "$from"; then
      ok=0; reason="phase '$from' is not conditional -- only phases listed in transitions.json's conditional_phases may be skipped"
    elif ! enter_requires_check "$sf" "$to" "$from" "$outcome"; then
      ok=0; reason="$ENTER_REQ_FAIL_REASON"
    fi
  fi

  local jseq now actor
  jseq=$(next_journal_seq "$bd")
  now=$(timestamp)
  actor="${WFSTATE_ACTOR:-${USER:-unknown}}"

  if [ "$ok" -eq 0 ]; then
    append_journal "$bd" "$jseq" "$now" "$from" "$to" "$actor" "reject" "$reason"
    die "advance: REJECTED $from -> $to : $reason"
  fi

  # write-ahead: journal records the accepted transition before the state file is
  # touched (ADR-C5 step 3). On a crash between here and the rename below, the
  # journal is 1 entry ahead of state.json -- that torn window is documented and left
  # for a future replay tool (FR-502, explicitly out of this tracer bullet's scope);
  # what THIS script guarantees is that the live state.json itself is never observed
  # in a partial/mixed state (AC-401a).
  append_journal "$bd" "$jseq" "$now" "$from" "$to" "$actor" "accept" "$outcome"

  # test-only crash injection hook (never set outside the test suite)
  if [ "${WFSTATE_CRASH_BEFORE_RENAME:-0}" = "1" ]; then
    exit 137
  fi

  # iter tracks retries of whatever phase is about to become current: reset to 0 the
  # first time a phase is ever entered (pre-transition status == pending), otherwise
  # increment -- this is what lets "iter > 3" mean "this phase (or the loop it's part
  # of) has been retried more than 3 times", not "9 total transitions have ever
  # happened" (a purely-forward happy path through all 10 phases must NOT trip the cap).
  local to_prev_status new_iter
  if [ "$to" = "$from" ]; then
    new_iter="$iter"
  else
    to_prev_status=$(jq -r --arg t "$to" '.phases[$t].status // "pending"' "$sf")
    if [ "$to_prev_status" = "pending" ]; then
      new_iter=0
    else
      new_iter=$((iter + 1))
    fi
  fi

  local hashes_json; hashes_json=$(compute_artifact_hashes_json "$sf" "$from")

  local tmp; tmp=$(mktemp "$STATE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  if [ "$to" = "$from" ]; then
    jq \
      --arg from "$from" --arg now "$now" \
      --argjson seq "$((seq + 1))" --argjson hashes "$hashes_json" '
      .phases[$from].status = "escalated"
      | .phases[$from].artifact_hashes = ($hashes // {})
      | .seq = $seq
      | .updated_at = $now
    ' "$sf" > "$tmp"
  else
    jq \
      --arg to "$to" --arg from "$from" --arg now "$now" --arg outcome "$outcome" \
      --argjson seq "$((seq + 1))" --argjson iter "$new_iter" --argjson hashes "$hashes_json" '
      .current_phase = $to
      | .seq = $seq
      | .iter = $iter
      | .phases[$from].status = $outcome
      | .phases[$from].artifact_hashes = ($hashes // {})
      | .phases[$to].status = "in_progress"
      | .updated_at = $now
    ' "$sf" > "$tmp"
  fi

  if ! jq empty "$tmp" >/dev/null 2>&1; then
    mv "$tmp" "$tmp.rejected"
    die "advance: generated state failed schema validate -- old state kept intact, bad candidate at $tmp.rejected"
  fi
  mv "$tmp" "$sf"

  if [ "$to" = "$from" ]; then
    printf 'advance: %s escalated (iter=%s)\n' "$from" "$iter"
  else
    printf 'advance: %s -> %s (%s, seq=%s)\n' "$from" "$to" "$outcome" "$((seq + 1))"
  fi
}

# ---- reconcile: ROADMAP-runtime-10.md SS2.2, 6 checks, bd optional (SS header comment).
# Each check prints exactly one "reconcile[<name>]: PASS|FAIL|SKIP -- <reason>" line so a
# caller can grep for which specific case fired; overall exit code is 1 iff any check
# reported FAIL (SKIP never flips it, and is never silent -- it always prints why).
cmd_reconcile() {
  local bd="${1:-}"
  [ -n "$bd" ] || { usage; die "reconcile: <bd-id> required"; }
  engagement_active || exit 0

  local sf; sf=$(state_file "$bd")
  [ -f "$sf" ] || die "reconcile: no state file for '$bd' (run init first)"

  local overall=0
  report() {
    # $1=check-name $2=PASS|FAIL|SKIP $3=reason (optional for PASS)
    printf 'reconcile[%s]: %s%s\n' "$1" "$2" "${3:+ -- $3}"
    [ "$2" = "FAIL" ] && overall=1
  }

  local last_state cur last_status workflow_done
  last_state=$(jq -r '.states[-1]' "$TRANSITIONS")
  cur=$(jq -r '.current_phase' "$sf")
  last_status=$(jq -r --arg p "$last_state" '.phases[$p].status // "pending"' "$sf")
  workflow_done=0
  case "$last_status" in
    passed|conditional_pass) [ "$cur" = "$last_state" ] && workflow_done=1 ;;
  esac

  # ---- checks 1 & 2: bd closed/active vs workflow done -- bd optional mirror
  if bd_available; then
    local bd_json bd_rc
    bd_json=$(bd -C "$ROOT" show "$bd" --json 2>/dev/null); bd_rc=$?
    if [ "$bd_rc" -ne 0 ]; then
      report "bd-closed-vs-workflow" SKIP "bd show '$bd' failed (bd-id not found in tracker) -- bd is an optional mirror, not a dependency"
      report "workflow-done-vs-bd-active" SKIP "bd show '$bd' failed (bd-id not found in tracker) -- bd is an optional mirror, not a dependency"
    else
      local bd_status
      bd_status=$(printf '%s' "$bd_json" | jq -r 'if type=="array" then (.[0].status // "") else (.status // "") end' 2>/dev/null)
      local cur_status; cur_status=$(jq -r --arg p "$cur" '.phases[$p].status // "unknown"' "$sf")
      if [ "$bd_status" = "closed" ] && [ "$workflow_done" -ne 1 ]; then
        report "bd-closed-vs-workflow" FAIL "bd '$bd' is closed but workflow phase '$cur' status is '$cur_status' (not done)"
      else
        report "bd-closed-vs-workflow" PASS ""
      fi
      if [ "$workflow_done" -eq 1 ] && [ "$bd_status" != "closed" ]; then
        report "workflow-done-vs-bd-active" FAIL "workflow reached done (phase='$last_state' status='$last_status') but bd '$bd' is still '$bd_status' (not closed)"
      else
        report "workflow-done-vs-bd-active" PASS ""
      fi
    fi
  else
    report "bd-closed-vs-workflow" SKIP "bd unavailable (not on PATH, or no active bd workspace) -- bd is an optional mirror, not a dependency"
    report "workflow-done-vs-bd-active" SKIP "bd unavailable (not on PATH, or no active bd workspace) -- bd is an optional mirror, not a dependency"
  fi

  # ---- check 3: artifact path missing
  local missing
  missing=$(jq -r '.phases[].artifacts[]? // empty' "$sf" | while IFS= read -r p; do
    [ -e "$ROOT/$p" ] || printf '%s\n' "$p"
  done)
  if [ -n "$missing" ]; then
    report "artifact-path-missing" FAIL "missing on disk: $(printf '%s' "$missing" | tr '\n' ',')"
  else
    report "artifact-path-missing" PASS ""
  fi

  # ---- checks 4 & 5: artifact hash mismatch, partitioned by whether the owning phase
  # has already been approved (passed/conditional_pass). Both compare the sha256
  # recorded on that phase (compute_artifact_hashes_json, written by advance()) against
  # the file's current sha256. Same underlying mechanism, deliberately disjoint scope so
  # the two named failure modes never double-report the same fact under two labels:
  #   4 = general drift on artifacts belonging to a NOT-yet-approved phase
  #   5 = an APPROVED phase's sign-off now references content that has since changed
  # (Dave design decision, iter 2 -- ROADMAP-runtime-10.md SS2.2 names both cases but
  # does not define how they differ; see outputs/shode-roadmap/C/09-dave-workflow-state.md.)
  local hash_fail_4="" hash_fail_5=""
  while IFS=$'\t' read -r phase pstatus; do
    [ -z "$phase" ] && continue
    while IFS=$'\t' read -r path stored_hash; do
      [ -z "$path" ] && continue
      [ -f "$ROOT/$path" ] || continue
      local cur_hash
      cur_hash=$(shasum -a 256 "$ROOT/$path" 2>/dev/null | awk '{print $1}')
      if [ "$cur_hash" != "$stored_hash" ]; then
        case "$pstatus" in
          passed|conditional_pass)
            hash_fail_5="${hash_fail_5}${hash_fail_5:+; }$phase:$path" ;;
          *)
            hash_fail_4="${hash_fail_4}${hash_fail_4:+; }$phase:$path" ;;
        esac
      fi
    done < <(jq -r --arg p "$phase" '.phases[$p].artifact_hashes // {} | to_entries[] | [.key,.value] | @tsv' "$sf")
  done < <(jq -r '.phases | to_entries[] | [.key, .value.status] | @tsv' "$sf")

  if [ -n "$hash_fail_4" ]; then
    report "artifact-hash-mismatch" FAIL "$hash_fail_4"
  else
    report "artifact-hash-mismatch" PASS ""
  fi
  if [ -n "$hash_fail_5" ]; then
    report "approval-stale-artifact" FAIL "$hash_fail_5"
  else
    report "approval-stale-artifact" PASS ""
  fi

  # ---- check 6: phase passed without required owner
  local no_owner
  no_owner=$(jq -r '.phases | to_entries[] | select(.value.status=="passed" or .value.status=="conditional_pass") | select((.value.owners // []) | length == 0) | .key' "$sf")
  if [ -n "$no_owner" ]; then
    report "phase-passed-without-owner" FAIL "phase(s) missing owners: $(printf '%s' "$no_owner" | tr '\n' ',')"
  else
    report "phase-passed-without-owner" PASS ""
  fi

  exit "$overall"
}

main() {
  local cmd="${1:-}"
  [ $# -gt 0 ] && shift
  case "$cmd" in
    init)      cmd_init "$@" ;;
    validate)  cmd_validate "$@" ;;
    advance)   cmd_advance "$@" ;;
    reconcile) cmd_reconcile "$@" ;;
    ""|-h|--help) usage; exit 1 ;;
    *) usage; die "unknown command '$cmd'" ;;
  esac
}

main "$@"
