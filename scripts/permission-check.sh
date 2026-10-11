#!/usr/bin/env bash
# permission-check.sh -- Milestone F runtime least-privilege check (bd: shode-roadmap/C-F1,
# ROADMAP-runtime-10.md SS 11.1 tool profiles + SS 11.3 delegation + SS 11.2/SS 12 trust).
#
# usage:
#   permission-check.sh <agent> <action> [target]
#
# actions:
#   write_files | run_commands | network      tool-grant layer (facts from agents/*.md
#                                             `tools:` frontmatter, mirrored in
#                                             references/security/tool-profiles.json --
#                                             CI asserts the mirror cannot drift)
#   write_code | deploy | deploy_prod         policy layer (least-privilege caps narrower
#                                             than the tool grants). A policy "true" is
#                                             honored ONLY if the prerequisite tool grant
#                                             is also true (write_code needs write_files;
#                                             deploy/deploy_prod need run_commands) --
#                                             a typo in the policy JSON can never widen
#                                             access beyond what the platform granted.
#   spawn <target-agent>                      delegation layer (references/security/
#                                             delegation.json -- anti recursive fan-out)
#   claim_trust <path>:<level>                trust cascade guard (references/security/
#                                             trust-levels.json): DENY when the declared
#                                             level outranks the path's class -- the
#                                             machine-checkable half of "agent output
#                                             cannot elevate the trust of its source"
#
# claim_trust path classes (F-13, W8): every class in trust-levels.json names its root.
#   root "plugin"  -- the shipped directories (agents/ skills/ output-styles/ references/
#                     scripts/ hooks/). Matched against the path relative to the PLUGIN
#                     root, taken from CLAUDE_PLUGIN_ROOT and resolved physically. The same
#                     relative path under the project root is NOT in the class. An unset,
#                     empty, relative or nonexistent CLAUDE_PLUGIN_ROOT puts no path in a
#                     plugin class (it falls to the default, `untrusted`); there is never a
#                     fallback to $PWD or to the project root.
#   root "project" -- matched against the path relative to the project root (ROOT).
#   A class without a valid root is a corrupt registry (exit 64), never a default.
# The path is lexically normalised (no `..` escape) and its existing ancestors resolved
# physically; a symlink leaf is in no class at all (default `untrusted`).
#
# exit codes (distinct on purpose -- the brief asks for allow / deny / unknown-agent as
# different signals a caller can branch on, same philosophy as scope-check.sh):
#   0   ALLOW
#   1   DENY      -- known agent, known action, answer is no (deny-by-default: a policy
#                    key missing from the profile is a DENY, never a silent allow)
#   2   UNKNOWN   -- agent / action / spawn-target / trust level not in the registries;
#                    distinct from DENY so a caller can tell a typo from a real refusal
#   64  usage/dependency error (missing jq, missing arg, corrupt JSON) -- deliberately
#       NOT 0-2 so a broken invocation can't be mistaken for a verdict
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as scripts/workflow-state.sh + scripts/scope-check.sh. This script
#   never creates that dir itself.
#
# Deps: bash + jq only (ADR-C3 precedent -- no python3 on the hot path).
#
# Token/context rule (C-F1 brief, hard requirement): this script and the three JSON
# registries it reads are consumed by shell/CI only. They are NEVER `Read` into an agent
# context, and no agents/** file or preloaded skill points at them.
#
# ROOT overridable with PERMCHECK_ROOT (test sandbox, mirrors SCOPECHECK_ROOT); registry
# paths overridable with PERMCHECK_PROFILES / PERMCHECK_DELEGATION / PERMCHECK_TRUST
# (mutation testing points these at doctored copies instead of editing shipped files).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${PERMCHECK_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
PROFILES="${PERMCHECK_PROFILES:-$SELF_DIR/../references/security/tool-profiles.json}"
DELEGATION="${PERMCHECK_DELEGATION:-$SELF_DIR/../references/security/delegation.json}"
TRUST="${PERMCHECK_TRUST:-$SELF_DIR/../references/security/trust-levels.json}"

log_err() { printf 'permission-check.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

usage() {
  cat >&2 <<'EOF'
usage: permission-check.sh <agent> <action> [target]
  actions: write_files | run_commands | network | write_code | deploy | deploy_prod
           spawn <target-agent> | claim_trust <path>:<level>
exit: 0 ALLOW | 1 DENY | 2 UNKNOWN (agent/action/target/level not in registry) | 64 usage/dep
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

allow()   { printf 'ALLOW: %s\n' "$1"; exit 0; }
deny()    { printf 'DENY: %s\n' "$1"; exit 1; }
unknown() { printf 'UNKNOWN: %s\n' "$1"; exit 2; }

# NOTE: jq's `//` treats false the same as null, so `.x // "null"` would silently turn an
# explicit `false` into "null" and misreport a deliberate deny as a missing entry. Use
# has() so true / false / absent stay three distinct answers.
profile_flag() {
  # $1=agent $2=layer(tool_grants|policy) $3=key -> echoes true|false|null
  jq -r --arg a "$1" --arg l "$2" --arg k "$3" \
    '(.profiles[$a][$l] // {}) | if has($k) then (.[$k] | tostring) else "null" end' "$PROFILES"
}

require_known_agent() {
  local agent="$1"
  if ! jq -e --arg a "$agent" '.profiles | has($a)' "$PROFILES" >/dev/null; then
    unknown "agent \"$agent\" is not in references/security/tool-profiles.json -- not a registered agent type (typo? new type not yet profiled? a retired id, see skills/discipline/shode-house-routing/ownership.md Formerly?)"
  fi
}

check_grant() {
  # tool-grant layer: platform facts
  local agent="$1" key="$2" v
  v=$(profile_flag "$agent" tool_grants "$key")
  case "$v" in
    true)  allow "\"$agent\" has the $key tool grant ($(jq -r --arg a "$agent" '.profiles[$a].source' "$PROFILES") tools frontmatter)" ;;
    false) deny  "\"$agent\" has no $key tool grant -- the platform does not give it the required tool ($(jq -r --arg a "$agent" '.profiles[$a].source' "$PROFILES"))" ;;
    *)     deny  "\"$agent\" profile has no tool_grants.$key entry -- deny-by-default (fix tool-profiles.json if this is wrong)" ;;
  esac
}

check_policy() {
  # policy layer: least-privilege cap, honored only on top of its tool prerequisite
  local agent="$1" key="$2" prereq="$3" pv gv
  gv=$(profile_flag "$agent" tool_grants "$prereq")
  if [ "$gv" != "true" ]; then
    deny "\"$agent\" lacks the $prereq tool grant that $key requires -- platform layer already forbids this, regardless of policy"
  fi
  pv=$(profile_flag "$agent" policy "$key")
  case "$pv" in
    true)  allow "\"$agent\" policy grants $key (least-privilege cap in tool-profiles.json, prerequisite $prereq grant present)" ;;
    false) deny  "\"$agent\" policy forbids $key -- least privilege per capability ownership (references/registry/capabilities.json); tool grant alone does not confer this right" ;;
    *)     deny  "\"$agent\" profile has no policy.$key entry -- deny-by-default (fix tool-profiles.json if this is wrong)" ;;
  esac
}

check_spawn() {
  local agent="$1" target="$2" cs
  [ -n "$target" ] || { usage; die "spawn requires a target agent"; }
  # target must itself be a registered agent -- spawning a nonexistent agent is a typo,
  # not a grantable right
  if ! jq -e --arg a "$target" '.profiles | has($a)' "$PROFILES" >/dev/null; then
    unknown "spawn target \"$target\" is not a registered agent in tool-profiles.json"
  fi
  cs=$(jq -r --arg a "$agent" '.delegation[$a].can_spawn // "null" | if type == "array" then join(",") else . end' "$DELEGATION")
  case "$cs" in
    '*')   allow "\"$agent\" can_spawn \"*\" (delegation.json -- backed by the Task tool grant in its frontmatter)" ;;
    null)  deny  "\"$agent\" has no delegation entry -- deny-by-default, no spawn rights" ;;
    "")    deny  "\"$agent\" can_spawn [] -- no Task tool in its frontmatter; only the main session (the router output style, not a registered agent) delegates (anti recursive fan-out, ROADMAP SS 11.3)" ;;
    *)
      case ",$cs," in
        *",$target,"*) allow "\"$agent\" can_spawn explicitly lists \"$target\" (delegation.json)" ;;
        *)             deny  "\"$agent\" can_spawn [$cs] does not include \"$target\" (delegation.json -- anti recursive fan-out)" ;;
      esac
      ;;
  esac
}

# lexnorm <abs-path> -- resolve `.`/`..`/empty segments lexically (same technique as
# hooks/scripts/guard-scope-write.sh), so a `..` can never walk a path out of a class.
lexnorm() {
  local p="$1" seg out="" oldifs="$IFS" had_noglob=0
  case $- in *f*) had_noglob=1 ;; esac
  IFS=/
  set -f
  # shellcheck disable=SC2086
  set -- $p
  [ "$had_noglob" -eq 1 ] || set +f   # restore the caller's globbing state (Chris W8 S3)
  IFS="$oldifs"
  for seg in "$@"; do
    case "$seg" in
      ""|".") continue ;;
      "..") out="${out%/*}" ;;
      *)     out="$out/$seg" ;;
    esac
  done
  if [ -n "$out" ]; then printf '%s' "$out"; else printf '/'; fi
}

# physical_path <normalised-abs-path> -- resolve the longest existing ancestor with
# `pwd -P` (follows symlinked ancestors, never the leaf) and re-append the rest.
physical_path() {
  local abs="$1" dir rest depth=0 real_dir
  dir=$(dirname "$abs"); rest=$(basename "$abs")
  while [ ! -d "$dir" ] && [ "$dir" != "/" ] && [ "$depth" -lt 64 ]; do
    rest="$(basename "$dir")/$rest"
    dir=$(dirname "$dir")
    depth=$((depth + 1))
  done
  real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || real_dir="$dir"
  printf '%s/%s' "${real_dir%/}" "$rest"
}

# plugin_root_physical -- the physical plugin root, or return 1 when CLAUDE_PLUGIN_ROOT is
# unset, empty, relative or not a directory (F-13 V5: no fallback of any kind).
plugin_root_physical() {
  local raw
  raw=$(printenv CLAUDE_PLUGIN_ROOT 2>/dev/null) || return 1
  case "$raw" in /*) : ;; *) return 1 ;; esac
  (cd "$raw" 2>/dev/null && pwd -P) || return 1
}

check_claim_trust() {
  local agent="$1" target="$2" path level lrank
  [ -n "$target" ] || { usage; die "claim_trust requires <path>:<level>"; }
  case "$target" in
    *:*) path="${target%:*}"; level="${target##*:}" ;;
    *)   usage; die "claim_trust target must be <path>:<level>, got \"$target\"" ;;
  esac
  [ -n "$path" ] || { usage; die "claim_trust: empty path"; }

  lrank=$(jq -r --arg l "$level" '.levels[$l] // "null"' "$TRUST")
  if [ "$lrank" = "null" ]; then
    unknown "trust level \"$level\" is not one of $(jq -r '.levels | keys_unsorted | join("/")' "$TRUST") (trust-levels.json)"
  fi

  # F-13: one absolute, lexically normalised, physically resolved path; then its place
  # relative to the plugin root and to the project root (see the header).
  local abs phys prel="" rel="" proot groot is_link=0
  case "$path" in
    /*) abs="$path" ;;
    *)  abs="$ROOT/$path" ;;
  esac
  abs=$(lexnorm "$abs")
  [ -L "$abs" ] && is_link=1
  phys=$(physical_path "$abs")
  if [ "$is_link" -eq 0 ]; then
    if proot=$(plugin_root_physical); then
      case "$phys" in "$proot"/*) prel="${phys#"$proot"/}" ;; esac
    fi
    groot=$(cd "$ROOT" 2>/dev/null && pwd -P) || groot="$ROOT"
    case "$phys" in "$groot"/*) rel="${phys#"$groot"/}" ;; esac
  fi
  local shown="${prel:-${rel:-$path}}"

  # A class without a valid root is a corrupt registry. Checked for EVERY class before the
  # loop, so the answer never depends on whether an earlier class matched first (Chris W8 F2).
  jq -e '(.path_classes | type == "array") and all(.path_classes[]; .root == "plugin" or .root == "project")' "$TRUST" >/dev/null 2>&1 \
    || die "trust-levels.json has a path class without a valid root (plugin|project) -- corrupt registry, refusing to guess"

  # first matching path class wins; unclassified content defaults to `untrusted`
  # (SS 11.2: README/issue/web/source comment/log/fixture in a target repo = untrusted)
  local class="" pat tr root cand
  while IFS=$'\t' read -r pat tr root; do
    [ -z "$pat" ] && continue
    case "$root" in
      plugin)  cand="$prel" ;;
      project) cand="$rel" ;;
      *)       die "trust-levels.json path class \"$pat\" has no valid root (plugin|project) -- corrupt registry, refusing to guess" ;;
    esac
    [ -n "$cand" ] || continue
    # unquoted $pat is the point: registry patterns are shell case-globs, same
    # dialect as scope-check.sh path_matches
    # shellcheck disable=SC2254
    case "$cand" in
      $pat) class="$tr"; break ;;
    esac
  done < <(jq -r '.path_classes[] | [.pattern, .trust, (.root // "")] | @tsv' "$TRUST")
  [ -n "$class" ] || class=$(jq -r '.default_class' "$TRUST")
  rel="$shown"

  local crank
  crank=$(jq -r --arg l "$class" '.levels[$l] // "null"' "$TRUST")
  [ "$crank" != "null" ] || die "trust-levels.json path class \"$class\" has no rank (corrupt registry)"

  if [ "$lrank" -gt "$crank" ]; then
    deny "\"$agent\" may not label \"$rel\" as \"$level\" (rank $lrank) -- its class is \"$class\" (rank $crank); trust cascade: an agent cannot elevate the trust of its source or output (ROADMAP SS 12)"
  fi
  allow "\"$agent\" labels \"$rel\" as \"$level\" (<= class \"$class\") -- no elevation"
}

main() {
  # engagement guard FIRST -- before jq/registry checks, so a machine without an active
  # engagement (or without jq) is never blocked by this script (workflow-state.sh rule)
  [ -d "$SHODE_DIR" ] || exit 0

  command -v jq >/dev/null 2>&1 || die "jq required"
  [ -f "$PROFILES" ]   || die "profiles registry not found: $PROFILES"
  [ -f "$DELEGATION" ] || die "delegation registry not found: $DELEGATION"
  [ -f "$TRUST" ]      || die "trust registry not found: $TRUST"
  jq empty "$PROFILES" "$DELEGATION" "$TRUST" 2>/dev/null || die "a security registry is not valid JSON"

  local agent="${1:-}" action="${2:-}" target="${3:-}"
  if [ -z "$agent" ] || [ -z "$action" ]; then
    usage; die "agent and action are required"
  fi

  require_known_agent "$agent"

  case "$action" in
    write_files)   check_grant  "$agent" write_files ;;
    run_commands)  check_grant  "$agent" run_commands ;;
    network)       check_grant  "$agent" network ;;
    write_code)    check_policy "$agent" write_code  write_files ;;
    deploy)        check_policy "$agent" deploy      run_commands ;;
    deploy_prod)   check_policy "$agent" deploy_prod run_commands ;;
    spawn)         check_spawn  "$agent" "$target" ;;
    claim_trust)   check_claim_trust "$agent" "$target" ;;
    *)             unknown "action \"$action\" is not supported (see usage) -- refusing to guess" ;;
  esac
}

main "$@"
