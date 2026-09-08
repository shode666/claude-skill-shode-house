#!/usr/bin/env bash
# scope-check.sh -- Milestone E (bd: shode-roadmap/C-E1): scope manifest + shared-file
# strategy + optimistic conflict check (ROADMAP-runtime-10.md SS7.1-7.3).
#
# usage:
#   scope-check.sh <bd-id> <agent> <path>                 # 7.1+7.2 ownership check
#   scope-check.sh <bd-id> <agent> <path> --snapshot       # 7.3 record base sha (+ any
#                                                           #   declared coupled_with paths)
#   scope-check.sh <bd-id> <agent> <path> --verify         # 7.3 compare recorded base sha
#                                                           #   vs current sha on disk
#
# exit codes (kept distinct on purpose -- the brief asks for "อนุญาต / ปฏิเสธเพราะเป็นของ
# agent อื่น / ไม่มี manifest" as three DIFFERENT signals a caller can branch on):
#   0   ALLOW       -- path resolves to the requesting agent under the manifest's rules,
#                      or --verify found no drift since the last --snapshot
#   1   DENY        -- path is owned by a different agent, or a shared_files strategy
#                      forbids this agent from writing it directly (exclusive/merge-owner
#                      not-owner, or generated -- nobody hand-writes a generated file)
#   2   NO_MANIFEST -- .shode-house/ exists but no scope manifest has been recorded for
#                      this bd-id yet (or --snapshot/--verify called before any manifest
#                      exists) -- distinct from ALLOW: there is no lock in place at all
#   3   CONFLICT    -- (--verify only) current sha256 differs from the sha recorded at
#                      --snapshot time, on the checked path or any of its declared
#                      coupled_with paths -- re-evaluate, do not blind-overwrite
#   64  usage/dependency error (missing jq/shasum, missing required arg, corrupt JSON) --
#       deliberately NOT one of 0-3 so a caller can't mistake a broken invocation for a
#       real ALLOW/DENY/NO_MANIFEST/CONFLICT verdict
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as scripts/workflow-state.sh (see that script's own header comment).
#   This script never creates that top-level dir itself.
#
# Deps: bash + jq + shasum (ADR-C3 precedent from workflow-state.sh -- no python3 in the
# hot path).
#
# Manifest location (this reference dir is the SCHEMA + EXAMPLE only, not the live data):
#   $ROOT/.shode-house/scope/<bd-id with / -> -->.json
# Schema:  references/scope/manifest.schema.json
# Example: references/scope/example.manifest.json
# Narrative index + relationship to references/scope-lock.md: references/scope/README.md
#
# Token/context rule for this milestone's brief: this script is read by shell/CI only.
# It is never `Read` into an agent context, and no agents/** file or preloaded skill
# points at it or at references/scope/** (that would cost tokens on every run for a
# capability agents invoke through Bash, not through reading).
#
# ROOT can be overridden with SCOPECHECK_ROOT (used by the test suite to run inside an
# isolated tmp dir instead of the real repo cwd -- mirrors WFSTATE_ROOT).

set -u -o pipefail

ROOT="${SCOPECHECK_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
SCOPE_DIR="$SHODE_DIR/scope"

log_err() { printf 'scope-check.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

encode_bd()     { printf '%s' "$1" | sed 's#/#--#g'; }
manifest_file() { printf '%s/%s.json' "$SCOPE_DIR" "$(encode_bd "$1")"; }

# ---- pattern matching: shell case-pattern, same dialect as the Scope Contract's
# "Files:" field (references/scope-lock.md). `*` already matches across '/' here since
# this is string-level `case` matching, not a filesystem glob -- so `src/orders/**`
# behaves identically to `src/orders/*` (both mean "any suffix"); no globstar shell
# option needs to be set.
path_matches() {
  case "$1" in
    $2) return 0 ;;
    *)  return 1 ;;
  esac
}

sha256_of() {
  local f="$1"
  if [ -f "$f" ]; then
    shasum -a 256 "$f" 2>/dev/null | awk '{print $1}'
  else
    printf 'ABSENT'
  fi
}

# ---- NOTE: this is intentionally NOT a "return the manifest path via stdout" helper
# function called through command substitution (`mf=$(require_manifest ...)`). An `exit`
# inside a command-substitution subshell only kills the subshell, not this script -- and
# any printf meant for the real user would get captured into the variable instead of
# reaching stdout. Every cmd_* below inlines this check directly in its own shell instead.
check_manifest_or_bail() {
  # $1=bd $2=mf -- exits 2 (printing NO_MANIFEST) if missing, dies (64) if corrupt,
  # otherwise returns 0 silently so the caller continues in its own shell.
  local bd="$1" mf="$2"
  if [ ! -f "$mf" ]; then
    printf 'NO_MANIFEST: no scope manifest recorded for bd "%s" (expected %s) -- no lock in place, proceed with caution\n' "$bd" "$mf"
    exit 2
  fi
  jq empty "$mf" >/dev/null 2>&1 || die "manifest $mf is not valid JSON"
}

# ---- find the shared_files key (if any) whose pattern matches $path. Prints the key
# on stdout, or nothing if unmatched. Shared-file strategy is checked BEFORE agents[]
# owns[] -- an explicit strategy always wins over an implicit ownership glob.
find_shared_key() {
  local mf="$1" path="$2" k
  while IFS= read -r k; do
    [ -z "$k" ] && continue
    if path_matches "$path" "$k"; then printf '%s' "$k"; return 0; fi
  done < <(jq -r '.shared_files // {} | keys[]' "$mf")
  return 1
}

# ---- coupled_with paths for a matched shared_files key, one per line (empty if none)
coupled_paths_of() {
  local mf="$1" key="$2"
  jq -r --arg k "$key" '.shared_files[$k].coupled_with[]? // empty' "$mf"
}

# =============================================================================
# 7.1 + 7.2: ownership check
# =============================================================================
cmd_check() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"

  local matched_shared
  matched_shared=$(find_shared_key "$mf" "$path") || matched_shared=""

  if [ -n "$matched_shared" ]; then
    local sf_mode sf_owner
    sf_mode=$(jq -r --arg k "$matched_shared" '.shared_files[$k].mode' "$mf")
    sf_owner=$(jq -r --arg k "$matched_shared" '.shared_files[$k].owner // ""' "$mf")
    case "$sf_mode" in
      exclusive|merge-owner)
        if [ -z "$sf_owner" ]; then
          printf 'DENY: shared_files["%s"] mode=%s has no declared owner (manifest error) -- fail-safe locked, fix the manifest\n' "$matched_shared" "$sf_mode"
          exit 1
        fi
        if [ "$agent" = "$sf_owner" ]; then
          printf 'ALLOW: "%s" matches shared_files["%s"] mode=%s, agent "%s" is the owner\n' "$path" "$matched_shared" "$sf_mode" "$agent"
          exit 0
        fi
        printf 'DENY: "%s" matches shared_files["%s"] mode=%s, owned by "%s" (not "%s") -- ask "%s" to merge your change, do not write directly\n' \
          "$path" "$matched_shared" "$sf_mode" "$sf_owner" "$agent" "$sf_owner"
        exit 1
        ;;
      append-only)
        if jq -e --arg a "$agent" '.agents // [] | any(.agent == $a)' "$mf" >/dev/null 2>&1; then
          printf 'ALLOW: "%s" matches shared_files["%s"] mode=append-only, "%s" is a registered agent for this bd\n' "$path" "$matched_shared" "$agent"
          exit 0
        fi
        printf 'DENY: "%s" matches shared_files["%s"] mode=append-only, but "%s" is not a registered agent for bd "%s"\n' "$path" "$matched_shared" "$agent" "$bd"
        exit 1
        ;;
      generated)
        local regen
        regen=$(jq -r --arg k "$matched_shared" '.shared_files[$k].regenerate_via // "(no regenerate_via declared in manifest)"' "$mf")
        printf 'DENY: "%s" matches shared_files["%s"] mode=generated -- nobody hand-writes this; regenerate via: %s\n' "$path" "$matched_shared" "$regen"
        exit 1
        ;;
      *)
        printf 'DENY: "%s" matches shared_files["%s"] with unknown mode "%s" -- fail-safe locked, fix the manifest\n' "$path" "$matched_shared" "$sf_mode"
        exit 1
        ;;
    esac
  fi

  # not a shared file -- fall through to agents[].owns[] (7.1)
  local ow_agent ow_pattern found_owner=""
  while IFS=$'\t' read -r ow_agent ow_pattern; do
    [ -z "$ow_agent" ] && continue
    if path_matches "$path" "$ow_pattern"; then found_owner="$ow_agent"; break; fi
  done < <(jq -r '.agents[]? | .agent as $a | .owns[]? | [$a, .] | @tsv' "$mf")

  if [ -n "$found_owner" ]; then
    if [ "$found_owner" = "$agent" ]; then
      printf 'ALLOW: "%s" is owned by "%s" (self)\n' "$path" "$agent"
      exit 0
    fi
    printf 'DENY: "%s" is owned by "%s", not "%s"\n' "$path" "$found_owner" "$agent"
    exit 1
  fi

  # unclaimed by any agent and not a shared_files entry -- permissive by design (a
  # manifest only lists paths that are ACTIVELY part of someone's declared work; a file
  # nobody has claimed yet is not a conflict). Flagged distinctly from a bare ALLOW so
  # this is auditable, not silent.
  printf 'ALLOW: "%s" is unclaimed in the manifest for bd "%s" -- no owner declared, proceeding (consider adding it to a Scope Contract)\n' "$path" "$bd"
  exit 0
}

# =============================================================================
# 7.3: optimistic conflict check -- snapshot
# =============================================================================
cmd_snapshot() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"
  mkdir -p "$SCOPE_DIR"

  local matched_shared paths_to_snap
  matched_shared=$(find_shared_key "$mf" "$path") || matched_shared=""
  paths_to_snap="$path"
  if [ -n "$matched_shared" ]; then
    while IFS= read -r cp; do
      [ -z "$cp" ] && continue
      paths_to_snap="$paths_to_snap
$cp"
    done < <(coupled_paths_of "$mf" "$matched_shared")
  fi

  local tmp; tmp=$(mktemp "$SCOPE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  cp "$mf" "$tmp"
  local p h
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    h=$(sha256_of "$ROOT/$p")
    jq --arg a "$agent" --arg p "$p" --arg h "$h" \
      '(.base_sha //= {}) | (.base_sha[$a] //= {}) | .base_sha[$a][$p] = $h' \
      "$tmp" > "$tmp.next" && mv "$tmp.next" "$tmp"
  done <<<"$paths_to_snap"

  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "snapshot: generated manifest failed JSON validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$mf"
  printf 'SNAPSHOT: recorded base sha for agent "%s" on: %s\n' "$agent" "$(printf '%s' "$paths_to_snap" | tr '\n' ' ')"
  exit 0
}

# =============================================================================
# 7.3: optimistic conflict check -- verify
# =============================================================================
cmd_verify() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"

  local matched_shared paths_to_check
  matched_shared=$(find_shared_key "$mf" "$path") || matched_shared=""
  paths_to_check="$path"
  if [ -n "$matched_shared" ]; then
    while IFS= read -r cp; do
      [ -z "$cp" ] && continue
      paths_to_check="$paths_to_check
$cp"
    done < <(coupled_paths_of "$mf" "$matched_shared")
  fi

  local p base_h cur_h conflict=0
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    base_h=$(jq -r --arg a "$agent" --arg p "$p" '.base_sha[$a][$p] // "NO_SNAPSHOT"' "$mf" 2>/dev/null)
    cur_h=$(sha256_of "$ROOT/$p")
    if [ "$base_h" = "NO_SNAPSHOT" ]; then
      printf 'CONFLICT: "%s" has no recorded snapshot for agent "%s" -- run --snapshot before --verify\n' "$p" "$agent"
      conflict=1
    elif [ "$base_h" != "$cur_h" ]; then
      printf 'CONFLICT: "%s" changed since snapshot (base=%s current=%s) -- someone else touched it, re-evaluate before write\n' "$p" "$base_h" "$cur_h"
      conflict=1
    fi
  done <<<"$paths_to_check"

  [ "$conflict" -eq 1 ] && exit 3
  printf 'ALLOW: no drift since snapshot for "%s" (agent "%s")\n' "$path" "$agent"
  exit 0
}

usage() {
  cat >&2 <<'EOF'
usage: scope-check.sh <bd-id> <agent> <path>              # 7.1+7.2 ownership check
       scope-check.sh <bd-id> <agent> <path> --snapshot    # 7.3 record base sha
       scope-check.sh <bd-id> <agent> <path> --verify      # 7.3 optimistic conflict check
exit: 0 ALLOW | 1 DENY | 2 NO_MANIFEST | 3 CONFLICT (--verify only) | 64 usage/dep error
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

main() {
  command -v jq >/dev/null 2>&1 || die "jq required"
  command -v shasum >/dev/null 2>&1 || die "shasum required"

  local bd="${1:-}" agent="${2:-}" path="${3:-}" flag="${4:-}"
  if [ -z "$bd" ] || [ -z "$agent" ] || [ -z "$path" ]; then
    usage; die "bd-id, agent, and path are all required"
  fi

  case "$flag" in
    "")           cmd_check "$bd" "$agent" "$path" ;;
    "--snapshot") cmd_snapshot "$bd" "$agent" "$path" ;;
    "--verify")   cmd_verify "$bd" "$agent" "$path" ;;
    *) usage; die "unknown flag '$flag'" ;;
  esac
}

main "$@"
