#!/usr/bin/env bash
# approval.sh -- Milestone D (bd: shode-roadmap/C-D1): approval scope + invalidation
# (ROADMAP-runtime-10.md, Phase 9 -- Approval Correctness).
#
# An approval is bound to: the artifact(s) it was granted against (path + sha256 AT
# GRANT TIME), the git commit HEAD was at, the workflow state_version (workflow-state.sh
# state.seq) at grant time, and a declared scope string. `verify` re-derives every one of
# those four right now and compares -- ANY drift is a hard DENY, never a warning that
# still lets the caller through (task requirement: "approval ที่ stale ต้องถูกปฏิเสธ ไม่ใช่
# เตือนแล้วปล่อยผ่าน").
#
#   approval.sh grant  <bd-id> <gate> <scope> <approved-by> <path> [<path>...]
#   approval.sh verify <bd-id> <gate>
#
# `grant`'s <path>... list is deliberately generic, not "spec path" + "artifact path" as
# two separate concepts -- ROADMAP-runtime-10.md Phase 9's four named invalidation
# triggers (code changed, spec changed, artifact changed, dependency changed) are ALL
# just "some path's sha256 no longer matches what was recorded" once you include a
# code-representative path (e.g. the changed source dir's own hash isn't tracked here --
# `git_commit` already covers "code changed" wholesale) and any dependency-contract file
# in the <path> list the caller cares about; this keeps the invalidation logic DATA
# (which paths were declared), not a special-cased branch per trigger name -- same
# discipline the rest of this milestone's scripts follow.
#
# exit codes:
#   grant:  0 GRANTED | 64 usage/dependency error
#   verify: 0 ALLOW (still fresh) | 1 DENY (stale -- reason(s) printed, never a warning)
#           | 2 NO_APPROVAL (nothing granted for this bd/gate yet) | 64 usage/dep error
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as the rest of this milestone's scripts. Never creates that top-level
#   dir itself.
#
# Deps: bash + jq + shasum + git (git only used by `grant`/`verify` to read the current
# HEAD sha -- if $ROOT is not a git repo, git_commit is recorded/compared as "n/a" rather
# than treated as an error, so this script stays usable in a non-git sandbox too; the
# other three invalidation signals -- artifact hash, state_version, and any dependency
# path included in the artifact list -- still fully apply either way).
#
# Approval location: $ROOT/.shode-house/approval/<bd-id with / -> -->--<gate>.json
# Reads workflow state directly at $ROOT/.shode-house/state/<bd-id>.json (.seq field,
# schema_version 2, scripts/workflow-state.sh's own format) rather than shelling out to
# workflow-state.sh -- same "each script is independently invocable, no cross-script
# process dependency" convention scope-check.sh already established. If no state file
# exists yet for this bd, state_version is recorded/compared as "n/a" (that check is then
# simply not gated -- gate readiness itself is workflow-state.sh's/enter_requires's job,
# not this script's).
#
# ROOT can be overridden with APPROVAL_ROOT (mirrors WFSTATE_ROOT / SCOPECHECK_ROOT /
# SIDEEFFECT_ROOT).

set -u -o pipefail

ROOT="${APPROVAL_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
APPROVAL_DIR="$SHODE_DIR/approval"

log_err() { printf 'approval.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

encode_bd()   { printf '%s' "$1" | sed 's#/#--#g'; }
approval_file() { printf '%s/%s--%s.json' "$APPROVAL_DIR" "$(encode_bd "$1")" "$2"; }

timestamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

sha256_of() {
  local f="$1"
  if [ -f "$f" ]; then shasum -a 256 "$f" 2>/dev/null | awk '{print $1}'
  else printf 'ABSENT'; fi
}

git_head() {
  git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf 'n/a'
}

state_version_of() {
  local bd="$1" sf
  sf="$SHODE_DIR/state/$(encode_bd "$bd").json"
  if [ -f "$sf" ] && jq empty "$sf" >/dev/null 2>&1; then
    jq -r '.seq // "n/a"' "$sf"
  else
    printf 'n/a'
  fi
}

usage() {
  cat >&2 <<'EOF'
usage: approval.sh grant  <bd-id> <gate> <scope> <approved-by> <path> [<path>...]
       approval.sh verify <bd-id> <gate>
exit (grant):  0 GRANTED | 64 usage/dep error
exit (verify): 0 ALLOW | 1 DENY (stale) | 2 NO_APPROVAL | 64 usage/dep error
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

# =============================================================================
# grant
# =============================================================================
cmd_grant() {
  local bd="$1" gate="$2" scope="$3" approved_by="$4"
  shift 4
  [ $# -ge 1 ] || die "grant: at least one <path> is required (artifacts the approval is bound to)"

  engagement_active || exit 0
  mkdir -p "$APPROVAL_DIR"

  local af; af=$(approval_file "$bd" "$gate")
  local now; now=$(timestamp)
  local commit; commit=$(git_head)
  local sv; sv=$(state_version_of "$bd")

  local artifacts_json="[]" p h
  for p in "$@"; do
    h=$(sha256_of "$ROOT/$p")
    artifacts_json=$(printf '%s' "$artifacts_json" | jq --arg p "$p" --arg h "$h" '. + [{path:$p, sha:$h}]')
  done

  local tmp; tmp=$(mktemp "$APPROVAL_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  jq -n \
    --arg gate "$gate" --arg scope "$scope" --arg by "$approved_by" \
    --arg commit "$commit" --arg sv "$sv" --arg ts "$now" \
    --argjson artifacts "$artifacts_json" \
    '{gate:$gate, scope:$scope, approved_by:$by, git_commit:$commit, state_version:$sv, artifacts:$artifacts, ts:$ts}' \
    > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "grant: generated approval failed JSON validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$af"

  printf 'GRANTED: gate="%s" scope="%s" by="%s" git_commit=%s state_version=%s artifacts=%s -> %s\n' \
    "$gate" "$scope" "$approved_by" "$commit" "$sv" "$#" "$af"
  exit 0
}

# =============================================================================
# verify
# =============================================================================
cmd_verify() {
  local bd="$1" gate="$2"
  engagement_active || exit 0

  local af; af=$(approval_file "$bd" "$gate")
  if [ ! -f "$af" ]; then
    printf 'NO_APPROVAL: no approval recorded for bd "%s" gate "%s" (expected %s)\n' "$bd" "$gate" "$af"
    exit 2
  fi
  jq empty "$af" >/dev/null 2>&1 || die "verify: $af is not valid JSON"

  local reasons="" fail=0

  # ---- code changed: git_commit drift
  local stored_commit cur_commit
  stored_commit=$(jq -r '.git_commit' "$af")
  cur_commit=$(git_head)
  if [ "$stored_commit" != "n/a" ] && [ "$cur_commit" != "n/a" ] && [ "$stored_commit" != "$cur_commit" ]; then
    reasons="${reasons}${reasons:+; }code changed: git HEAD was $stored_commit at grant time, now $cur_commit"
    fail=1
  fi

  # ---- state rollback (or any drift, either direction -- approval was granted
  # against one specific workflow-state snapshot; any movement since invalidates it)
  local stored_sv cur_sv
  stored_sv=$(jq -r '.state_version' "$af")
  cur_sv=$(state_version_of "$bd")
  if [ "$stored_sv" != "n/a" ] && [ "$cur_sv" != "n/a" ] && [ "$stored_sv" != "$cur_sv" ]; then
    reasons="${reasons}${reasons:+; }state changed: workflow state_version was $stored_sv at grant time, now $cur_sv"
    fail=1
  fi

  # ---- spec / artifact / dependency changed: any recorded path's sha256 drifted.
  # (spec/artifact/dependency are not distinguished here -- whichever paths grant was
  # given ARE the scope of what this approval covers; this is data-driven by design,
  # see the header comment.)
  local drift="" path stored_sha cur_sha
  while IFS=$'\t' read -r path stored_sha; do
    [ -z "$path" ] && continue
    cur_sha=$(sha256_of "$ROOT/$path")
    if [ "$cur_sha" != "$stored_sha" ]; then
      drift="${drift}${drift:+; }$path (was $stored_sha, now $cur_sha)"
      fail=1
    fi
  done < <(jq -r '.artifacts[] | [.path, .sha] | @tsv' "$af")
  [ -n "$drift" ] && reasons="${reasons}${reasons:+; }artifact/spec/dependency changed: $drift"

  if [ "$fail" -eq 1 ]; then
    printf 'DENY: approval for bd "%s" gate "%s" is STALE -- %s\n' "$bd" "$gate" "$reasons"
    exit 1
  fi

  local scope; scope=$(jq -r '.scope' "$af")
  printf 'ALLOW: approval for bd "%s" gate "%s" (scope="%s") is still fresh -- no drift on code/state/artifacts\n' "$bd" "$gate" "$scope"
  exit 0
}

main() {
  command -v jq >/dev/null 2>&1 || die "jq required"
  command -v shasum >/dev/null 2>&1 || die "shasum required"

  local cmd="${1:-}"
  [ $# -gt 0 ] && shift
  case "$cmd" in
    grant)
      [ $# -ge 5 ] || { usage; die "grant: <bd-id> <gate> <scope> <approved-by> <path>... required"; }
      cmd_grant "$@"
      ;;
    verify)
      [ $# -eq 2 ] || { usage; die "verify: <bd-id> <gate> required"; }
      cmd_verify "$1" "$2"
      ;;
    ""|-h|--help) usage; exit 1 ;;
    *) usage; die "unknown command '$cmd'" ;;
  esac
}

main "$@"
