#!/usr/bin/env bash
# side-effect.sh -- Milestone D (bd: shode-roadmap/C-D1): side-effect ledger
# (ROADMAP-runtime-10.md, section 8.3 -- Atomic Checkpoint + Journal / Side-effect Ledger).
#
# Tracks side-effecting operations that are dangerous to repeat: deploy, migration,
# send, publish, delete, external API mutation. Every recorded entry is keyed by an
# idempotency_key supplied by the caller -- asking with the SAME key a second time must
# tell the caller "already done", not silently let them fire the operation again.
#
#   side-effect.sh check  <bd-id> <idempotency-key>
#   side-effect.sh record <bd-id> <operation> <idempotency-key> <status> [<detail>]
#
# `check` is the gate a caller runs BEFORE performing the real side effect. `record` is
# what the caller runs AFTER performing it (or attempting it), to persist the result.
#
# exit codes:
#   check:
#     0  NOT_DONE      -- no record for this key, or a record exists but status != completed
#                          (safe to proceed)
#     1  ALREADY_DONE  -- a record for this key exists with status=completed -- DO NOT REPEAT
#     64 usage/dependency error
#   record:
#     0  RECORDED      -- new/updated record written, OR an idempotent no-op re-record of an
#                          already-completed key with the identical status (not an error --
#                          this is exactly the "asked twice with the same key" case; the
#                          ledger is unchanged, nothing is repeated)
#     1  DENY          -- refused: either (a) this key was already used for a DIFFERENT
#                          operation (ledger integrity -- a key must mean one operation), or
#                          (b) an attempt to change an already-completed record to a
#                          different, non-completed status (completed is a one-way door;
#                          if a NEW attempt is needed, use a NEW idempotency_key)
#     64 usage/dependency error
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as scripts/workflow-state.sh and scripts/scope-check.sh. This script
#   never creates that top-level dir itself.
#
# Deps: bash + jq (ADR-C3 precedent -- no python3 in the hot path).
#
# Ledger location: $ROOT/.shode-house/side-effects/<bd-id with / -> -->.json
#   { "<idempotency_key>": {"operation": "...", "status": "...", "detail": "...", "ts": "..."} }
# One JSON object per bd (not JSONL) so a `check` is a single-key jq lookup, not a scan.
#
# ROOT can be overridden with SIDEEFFECT_ROOT (used by the test suite to run inside an
# isolated tmp dir instead of the real repo cwd -- mirrors WFSTATE_ROOT / SCOPECHECK_ROOT).

set -u -o pipefail

ROOT="${SIDEEFFECT_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
LEDGER_DIR="$SHODE_DIR/side-effects"

log_err() { printf 'side-effect.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

encode_bd()    { printf '%s' "$1" | sed 's#/#--#g'; }
ledger_file()  { printf '%s/%s.json' "$LEDGER_DIR" "$(encode_bd "$1")"; }

timestamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ---- read the ledger file, or "{}" if it doesn't exist yet (a bd with no side effects
# recorded yet is not an error -- distinct from a corrupt file, which IS an error).
read_ledger() {
  local lf="$1"
  if [ ! -f "$lf" ]; then printf '{}'; return; fi
  jq empty "$lf" >/dev/null 2>&1 || die "ledger $lf is not valid JSON (this is a bug or manual tampering -- do not repair by hand-guessing, restore from journal/vcs)"
  cat "$lf"
}

usage() {
  cat >&2 <<'EOF'
usage: side-effect.sh check  <bd-id> <idempotency-key>
       side-effect.sh record <bd-id> <operation> <idempotency-key> <status> [<detail>]
exit (check):  0 NOT_DONE | 1 ALREADY_DONE | 64 usage/dep error
exit (record): 0 RECORDED (incl. idempotent no-op re-record) | 1 DENY | 64 usage/dep error
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

# =============================================================================
# check -- the pre-flight gate a caller runs BEFORE performing the real side effect
# =============================================================================
cmd_check() {
  local bd="$1" key="$2"
  engagement_active || exit 0

  local lf; lf=$(ledger_file "$bd")
  local ledger; ledger=$(read_ledger "$lf")

  local status; status=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].status // "NONE"')
  if [ "$status" = "completed" ]; then
    local op ts; op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // "?"')
    ts=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].ts // "?"')
    printf 'ALREADY_DONE: idempotency_key "%s" recorded as completed (operation="%s" at %s) -- do not repeat\n' "$key" "$op" "$ts"
    exit 1
  fi
  if [ "$status" = "NONE" ]; then
    printf 'NOT_DONE: idempotency_key "%s" has no record for bd "%s" -- safe to proceed\n' "$key" "$bd"
  else
    printf 'NOT_DONE: idempotency_key "%s" recorded but status="%s" (not completed) -- safe to (re)attempt\n' "$key" "$status"
  fi
  exit 0
}

# =============================================================================
# record -- what the caller runs AFTER performing (or attempting) the side effect
# =============================================================================
cmd_record() {
  local bd="$1" operation="$2" key="$3" status="$4" detail="${5:-}"
  engagement_active || exit 0

  mkdir -p "$LEDGER_DIR"
  local lf; lf=$(ledger_file "$bd")
  local ledger; ledger=$(read_ledger "$lf")

  local existing_op existing_status
  existing_op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // ""')
  existing_status=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].status // ""')

  # ---- ledger integrity: a key must mean exactly ONE operation for its whole life.
  if [ -n "$existing_op" ] && [ "$existing_op" != "$operation" ]; then
    printf 'DENY: idempotency_key "%s" already used for operation "%s", cannot reuse for "%s" (use a new key per distinct operation)\n' \
      "$key" "$existing_op" "$operation"
    exit 1
  fi

  # ---- completed is a one-way door (this IS the "ห้ามทำซ้ำ" enforcement point):
  #   - re-recording the SAME status=completed again is an idempotent no-op (exit 0,
  #     ledger unchanged) -- exactly the "asked twice with the same key" case.
  #   - recording any OTHER status once completed is refused outright.
  if [ "$existing_status" = "completed" ]; then
    if [ "$status" = "completed" ]; then
      printf 'RECORDED (no-op): idempotency_key "%s" already completed -- ledger unchanged, side effect NOT repeated\n' "$key"
      exit 0
    fi
    printf 'DENY: idempotency_key "%s" is already completed -- cannot change status to "%s" (completed is final; use a new key for a new attempt)\n' \
      "$key" "$status"
    exit 1
  fi

  local now; now=$(timestamp)
  local tmp; tmp=$(mktemp "$LEDGER_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  printf '%s' "$ledger" | jq \
    --arg k "$key" --arg op "$operation" --arg st "$status" --arg d "$detail" --arg ts "$now" \
    '.[$k] = {operation: $op, idempotency_key: $k, status: $st, detail: $d, ts: $ts}' \
    > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "record: generated ledger failed JSON validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$lf"

  printf 'RECORDED: idempotency_key "%s" operation="%s" status="%s"\n' "$key" "$operation" "$status"
  exit 0
}

main() {
  command -v jq >/dev/null 2>&1 || die "jq required"

  local cmd="${1:-}"
  [ $# -gt 0 ] && shift
  case "$cmd" in
    check)
      [ $# -eq 2 ] || { usage; die "check: <bd-id> and <idempotency-key> required"; }
      cmd_check "$1" "$2"
      ;;
    record)
      [ $# -ge 4 ] || { usage; die "record: <bd-id> <operation> <idempotency-key> <status> required"; }
      cmd_record "$1" "$2" "$3" "$4" "${5:-}"
      ;;
    ""|-h|--help) usage; exit 1 ;;
    *) usage; die "unknown command '$cmd'" ;;
  esac
}

main "$@"
