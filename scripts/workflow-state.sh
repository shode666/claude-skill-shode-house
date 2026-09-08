#!/usr/bin/env bash
# workflow-state.sh -- Milestone A tracer bullet (bd: shode-roadmap/C-A4)
#
# 3 commands only (deliberately not the full Bella FR-1xx..FR-5xx surface -- see
# outputs/shode-roadmap/C/09-dave-workflow-state.md "sing thi cong-jai mai tham"):
#
#   workflow-state.sh init <bd-id>
#   workflow-state.sh validate <bd-id>
#   workflow-state.sh advance <bd-id> <phase>
#
# Deps: bash + jq only (ADR-C3 -- no python3 in the hot path). Requires jq >= 1.6-ish
# (uses --argjson, index()).
#
# Engagement guard: every command is a no-op (exit 0, silent, no side effect) unless
# "$ROOT/.shode-house" already exists. This script never creates that top-level dir --
# it is assumed created by a separate bootstrap step (/init rule 11, out of this task's
# scope). This is intentional so an unrelated repo that never opted into shode-house
# workflow-state is never touched.
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

is_known_status() {
  case " $STATUS_ENUM " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

from_status_eligible() {
  case " $FROM_ELIGIBLE " in *" $1 "*) return 0 ;; *) return 1 ;; esac
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
       workflow-state.sh advance <bd-id> <phase>
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
  jq -n --arg bd "$bd" --arg now "$now" '
    {
      schema_version: 1,
      bd_id: $bd,
      current_phase: "pick",
      seq: 0,
      iter: 0,
      phases: {
        "pick":      {status: "in_progress", owners: [], artifacts: []},
        "impl":      {status: "pending",     owners: [], artifacts: []},
        "ui-check":  {status: "pending",     owners: [], artifacts: []},
        "review":    {status: "pending",     owners: [], artifacts: []},
        "triage":    {status: "pending",     owners: [], artifacts: []},
        "done":      {status: "pending",     owners: [], artifacts: []}
      },
      updated_at: $now
    }' > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "init: generated state failed schema validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$sf"

  local jf; jf=$(journal_file "$bd")
  [ -f "$jf" ] || : > "$jf"
  append_journal "$bd" 1 "$now" "null" "pick" "${WFSTATE_ACTOR:-${USER:-unknown}}" "accept" "init"

  printf 'init: created %s (current_phase=pick)\n' "$sf"
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
  local bd="${1:-}" to="${2:-}"
  if [ -z "$bd" ] || [ -z "$to" ]; then
    usage; die "advance: <bd-id> and <phase> required"
  fi
  engagement_active || exit 0

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
  if ! is_known_phase "$to"; then
    ok=0; reason="unknown phase '$to' (not in transitions.json states)"
  elif ! edge_exists "$from" "$to"; then
    ok=0; reason="no such edge '$from' -> '$to'"
  elif ! from_status_eligible "$from_status"; then
    ok=0; reason="prev status '$from_status' for phase '$from' not eligible (need one of: $FROM_ELIGIBLE)"
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
  append_journal "$bd" "$jseq" "$now" "$from" "$to" "$actor" "accept" "ok"

  # test-only crash injection hook (never set outside the test suite)
  if [ "${WFSTATE_CRASH_BEFORE_RENAME:-0}" = "1" ]; then
    exit 137
  fi

  local tmp; tmp=$(mktemp "$STATE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  jq \
    --arg to "$to" --arg from "$from" --arg now "$now" \
    --argjson seq "$((seq + 1))" --argjson iter "$((iter + 1))" '
    .current_phase = $to
    | .seq = $seq
    | .iter = $iter
    | .phases[$from].status = "passed"
    | .phases[$to].status = "in_progress"
    | .updated_at = $now
  ' "$sf" > "$tmp"

  if ! jq empty "$tmp" >/dev/null 2>&1; then
    mv "$tmp" "$tmp.rejected"
    die "advance: generated state failed schema validate -- old state kept intact, bad candidate at $tmp.rejected"
  fi
  mv "$tmp" "$sf"

  printf 'advance: %s -> %s (seq=%s)\n' "$from" "$to" "$((seq + 1))"
}

main() {
  local cmd="${1:-}"
  [ $# -gt 0 ] && shift
  case "$cmd" in
    init)     cmd_init "$@" ;;
    validate) cmd_validate "$@" ;;
    advance)  cmd_advance "$@" ;;
    ""|-h|--help) usage; exit 1 ;;
    *) usage; die "unknown command '$cmd'" ;;
  esac
}

main "$@"
