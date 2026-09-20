#!/usr/bin/env bash
# scope-check.sh -- Milestone E (bd: shode-roadmap/C-E1): scope manifest + shared-file
# strategy + optimistic conflict check (ROADMAP-runtime-10.md SS7.1-7.3). L2 enforcement
# integrity (bd: shode-house-5cs.4, iter 0 + iter 1): fail-closed unclaimed-path handling +
# allowed_roots/owns split + self-amend + platform-neutral instance_id-to-label binding +
# outsider policy for unbound/ambiguous instances.
#
# usage:
#   scope-check.sh <bd-id> <agent> <path>                       # ownership check
#   scope-check.sh <bd-id> <agent> <path> --snapshot             # 7.3 record base sha
#   scope-check.sh <bd-id> <agent> <path> --verify                # 7.3 compare base sha
#   scope-check.sh <bd-id> <agent> <path> --amend                 # atomic self-amend
#   scope-check.sh <bd-id> <label> --bind                         # agent-facing, inert
#                                                                  # (see "bind design" below)
#   scope-check.sh <bd-id> <path> --main-check                    # main-session scope probe
#
# Internal-only (never typed by an agent; a platform adapter is the only caller):
#   scope-check.sh <bd-id> <instance-id> <role> <label> <platform> --bind-record
#                                                                  # real bind write --
#                                                                  # platform-neutral record
#                                                                  # shape (bd: shode-house-5cs.4
#                                                                  # iter 1, "C1")
#   scope-check.sh <bd-id> <instance-id> --resolve-binding         # resolve instance_id -> label
#                                                                  # through the SAME shape guard
#                                                                  # bind-record uses, so the
#                                                                  # adapter never re-implements
#                                                                  # this lookup itself (bd:
#                                                                  # shode-house-5cs.4 iter 2)
#
# exit codes (kept distinct on purpose -- a caller branches on the number, never parses
# the message text):
#   0   ALLOW           -- path resolves to the requesting agent under the manifest's
#                          rules, or --verify found no drift, or --bind(-record) recorded
#                          (or idempotently confirmed) a binding, or --main-check found no
#                          collision with any active agent's owns/allowed_roots/shared_files
#   1   DENY            -- path is owned by a different agent, a shared_files strategy
#                          forbids this agent from writing it directly, the path is
#                          unclaimed AND outside the requesting agent's allowed_roots
#                          (escalate, never self-amend), a bind request violates one of
#                          the 7 binding rules (Part 2), or a main-session write collides
#                          with an active agent's declared scope
#   2   NO_MANIFEST     -- .shode-house/ exists but no scope manifest has been recorded for
#                          this bd-id yet -- distinct from ALLOW: there is no lock in place
#                          at all (--check/--snapshot/--verify/--amend only; --bind-record
#                          and --bind treat a missing manifest as DENY/"unknown bd" per the
#                          Part 2 binding rules instead, since a bind with nothing to bind
#                          against is a rule violation, not an advisory "no lock yet")
#   3   CONFLICT        -- (--verify only) current sha256 differs from the sha recorded at
#                          --snapshot time, on the checked path or any of its declared
#                          coupled_with paths -- re-evaluate, do not blind-overwrite
#   4   NEEDS_AMENDMENT -- (--check/--amend-eligibility path only) the path is unclaimed but
#                          falls inside the requesting agent's plan-approved allowed_roots --
#                          the printed message always carries the exact `--amend` command to
#                          run; after a successful --amend, re-running the plain check
#                          returns ALLOW
#   64  usage/dependency error (missing jq/shasum, missing required arg, corrupt JSON, or
#       a `bindings` map still in the pre-C1 flat shape -- see "bind design" below) --
#       deliberately NOT one of 0-4 so a caller can't mistake a broken invocation for a
#       real ALLOW/DENY/NO_MANIFEST/CONFLICT/NEEDS_AMENDMENT verdict --
#       includes an exhausted/refused lock acquisition (LOCK_BUSY/RECOVERY_IN_PROGRESS
#       retry exhausted, or an immediate LOCK_CORRUPT/RECOVERY_REQUIRED stop -- see
#       scopecheck_acquire_lock below) for every command that actually mutates the
#       manifest (--amend, --bind-record, --snapshot)
#
# ---- locking rule (bd: shode-house-5cs.8, W1/W2 -- READ THIS BEFORE "fixing" an
# apparent asymmetry) ----
#
# A command takes the shared lock (scripts/lib/lock.sh, bd:shode-house-vz8) IF AND ONLY
# IF it performs a read-modify-write on shared mutable state (the manifest file itself).
# It does NOT take the lock merely because a lock primitive now exists and is convenient
# to reach for. Concretely, in this file:
#   --amend, --bind-record, --snapshot  -- each reads the manifest, computes a new value,
#     and atomically renames a replacement over it. Each holds the lock (via
#     scopecheck_acquire_lock below) across its ENTIRE read-modify-write, start to finish
#     -- never a local/private lock, always scripts/lib/lock.sh (that prohibition is
#     exactly why bd:shode-house-vz8 exists: three independent local copies of "clever"
#     stale-lock reclamation were the actual bug, not mkdir).
#   --check, --verify, --main-check, --bind, --resolve-binding  -- each is a READ ONLY.
#     None of these ever takes the lock, on purpose, by design, permanently -- NOT a gap
#     to "symmetrize" later. --verify in particular only ever compares a previously
#     recorded sha256 against the manifest's current base_sha and the file's current
#     content; it needs an ATOMIC, VALIDATED READ (check_manifest_or_bail's `jq empty`,
#     plus the fact that every writer above replaces the manifest via mktemp+atomic-rename,
#     so any reader always observes either the fully-old or the fully-new manifest, never a
#     torn one) -- it does NOT need mutual exclusion, because it never mutates anything.
# The next person who notices "--amend/--bind-record/--snapshot lock but --verify/--check
# don't" and is tempted to "fix" that inconsistency for symmetry: do not. Locking exists to
# serialize concurrent WRITERS against each other, not to gate every reader just because a
# lock happens to be sitting right there. Adding a lock to a read-only command would only
# slow it down and give it a spurious failure mode (LOCK_BUSY/RECOVERY_REQUIRED) it has no
# actual need to ever hit.
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as scripts/workflow-state.sh (see that script's own header comment).
#   This script never creates that top-level dir itself.
#
# ---- bind design (Part 2 + Part 3 of bd: shode-house-5cs.4's brief; storage shape made
# platform-neutral in iter 1, "C1") ----
#
# This CORE script never names a platform -- no host-product name anywhere in this file
# (grep-enforced by tests/test-scope-check.sh, the invariant C1 exists to protect: see
# that test for the exact forbidden-string list). It knows exactly three identity
# concepts:
#   instance_id -- an opaque, harness-issued string identifying ONE running agent process
#                  (today's one adapter's hook payload calls this `agent_id`; another host
#                  may call it something else -- this script does not care what it is
#                  called upstream)
#   role        -- an opaque, harness-issued TYPE-level name (today's one adapter's hook
#                  payload calls this `agent_type`, e.g. "shode-house:developer") --
#                  recorded verbatim, NEVER used to derive a label. The label stays the
#                  one thing `bind` actually establishes.
#   label       -- the human-facing instance name ("Dave#1") a Scope Contract was written
#                  against -- must already exist in the manifest's agents[] before it can
#                  be bound.
# A `platform` string also travels with every binding record, for forward-compat with
# adapters this repo does not have yet -- but this core treats it as an OPAQUE pass-through
# value: it stores whatever string it is given and never branches on its value or
# hardcodes a known set of platforms. NAMING which platform a given adapter serves is that
# adapter's own job, not the core's -- hooks/scripts/guard-scope-write.sh is today's one
# such adapter; see that script's own header for which literal platform string it passes
# (correctly absent from this file) and how it derives instance_id/role from its own
# harness's identity fields.
#
# Storage layout -- an OBJECT keyed by instance_id (the one key every caller actually has
# on hand), so lookup-by-instance-id stays O(1) regardless of how many instances have
# bound:
#   "bindings": { "<instance_id>": {"platform": "<platform>", "role": "<role>", "label": "<label>"} }
#
# Migration (pre-C1 manifests): the OLD shape stored a bare string value directly --
#   "bindings": { "<instance_id>": "<label>" }
# -- host-specific-shaped (the key was, in that era, only ever populated from one
# particular adapter's identity field) and lossy (no room for role/platform). A manifest
# still in that shape is REJECTED with a clear operator message (exit 64, see
# `bindings_shape_ok_or_die`) the moment any bind-facing command touches it (`--bind`,
# `--bind-record`). Silently reinterpreting a bare string as a label-only record was
# considered and rejected: there is no way to recover the role/platform that were never
# captured under the old shape without guessing, and NO MAGIC forbids guessing -- so this
# picks "cleanly rejected", not "silently misread". Ownership checks that never touch
# `bindings` at all (cmd_check/cmd_amend/cmd_snapshot/cmd_verify) are UNAFFECTED by an
# old-shape manifest and keep working exactly as before -- only the bind-facing commands
# require the new shape.
#
# An agent cannot see its own instance_id (it is injected by the harness, not readable
# from inside the agent's own turn), and this script cannot see which human-facing label
# ("Dave#1") the agent is -- but the PLATFORM ADAPTER receives BOTH the instance_id/role
# AND the literal command text in the SAME payload when the agent runs:
#     scripts/scope-check.sh <bd-id> <label> --bind
# So the split is: this 3-arg, agent-typed shape (cmd_bind) is DELIBERATELY inert -- it has
# no instance_id to act on, so it only ever prints a read-only status line and exits 0 (or
# 2/64 on a bad/missing/old-shape manifest -- see cmd_bind itself). The REAL write
# (recording (instance_id, role, platform) -> label per the 7 rules below) happens in
# cmd_bind_record, a 5-arg internal shape
# (`<bd> <instance-id> <role> <label> <platform> --bind-record`) that only a platform
# adapter ever calls, after it has independently normalized its own harness's identity
# fields into these three generic ones plus its own literal platform string (see
# hooks/scripts/guard-scope-write.sh's own header for the injection-surface reasoning
# behind the strict canonical-shape regex it applies before ever reaching this call). If
# hooks are disabled or never wired, cmd_bind's inertness is harmless: with no hook,
# Write/Edit scope enforcement is off entirely too, so an unrecorded binding changes
# nothing that was actually being enforced.
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
# NOTE (bd: shode-house-5cs.4, iter 0 + iter 1): the live manifest shape below now carries
# two NEW top-level/per-agent fields the schema+example above do not yet declare --
# `agents[].allowed_roots` (plan-approved boundary, Part 1) and top-level `bindings`
# (instance_id -> {platform, role, label} record map, Part 2, reshaped platform-neutral in
# iter 1 "C1" -- see "bind design" above). Those two reference files sit outside this bd's
# declared Files boundary (see outputs/shode-house-5cs/00-oliver-plan.md's track table; the
# follow-up is tracked as bd shode-house-mri) and are not touched by this change --
# scope-check.sh never schema-validates the manifest against manifest.schema.json at
# runtime (only `jq empty` for syntax, see check_manifest_or_bail), so this is a
# documentation-drift gap, not a functional one.
#
# Token/context rule for this milestone's brief: this script is read by shell/CI only.
# It is never `Read` into an agent context, and no agents/** file or preloaded skill
# points at it or at references/scope/** (that would cost tokens on every run for a
# capability agents invoke through Bash, not through reading).
#
# ROOT can be overridden with SCOPECHECK_ROOT (used by the test suite to run inside an
# isolated tmp dir instead of the real repo cwd -- mirrors WFSTATE_ROOT).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Overridable for the same reason workflow-state.sh's WFSTATE_LOCK_LIB is -- a mutated
# COPY of this script moved outside scripts/ would otherwise fail to find its sibling.
SCOPECHECK_LOCK_LIB="${SCOPECHECK_LOCK_LIB:-$SELF_DIR/lib/lock.sh}"
# shellcheck source=lib/lock.sh
source "$SCOPECHECK_LOCK_LIB"

ROOT="${SCOPECHECK_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
SCOPE_DIR="$SHODE_DIR/scope"

log_err() { printf 'scope-check.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

encode_bd()     { printf '%s' "$1" | sed 's#/#--#g'; }
manifest_file() { printf '%s/%s.json' "$SCOPE_DIR" "$(encode_bd "$1")"; }

# ---- canon_path / _lexnorm: same three-phase technique hooks/scripts/guard-state-write.sh
# uses to close T3 (traversal)/T4 (case)/T6 (dot-slash) for .shode-house/{state,journal}/ --
# REUSED here, not reinvented (bd: shode-house-5cs.4 iter 2, "C1"; Chris's review named this
# file's `path_matches` as the same naive-unnormalized-string-compare bug class). Every
# cmd_* entry point that ever calls evaluate_ownership or path_matches canonicalizes its
# `path` argument through this ONCE, at the top, before doing anything else with it
# (messages, manifest writes, matching) -- so a NEEDS_AMENDMENT hint's printed --amend
# command, and what --amend actually persists into owns[], are always the same string a
# later --check will also compare against.
#   phase A (lexnorm, pure string manipulation, no filesystem access): collapse "." and
#     "x/.." segments -- must run BEFORE any existence check, since a component that never
#     actually gets created on disk cannot be `cd`-resolved, so an existence-only walk alone
#     cannot cancel a ".." that only ever exists as text.
#   phase B (physical resolve): `cd` into the deepest EXISTING ancestor and `pwd -P`, which
#     resolves any symlink sitting in that resolvable prefix and (on a case-insensitive
#     filesystem, e.g. APFS default) naturally returns the ON-DISK case for that prefix.
#   phase C (case-fold): lowercase the WHOLE result, both here and (see path_matches below)
#     the manifest pattern it is compared against -- defense-in-depth for a genuinely
#     case-sensitive filesystem too (accepted residual: this can rarely over-block an
#     unrelated same-name-different-case path; same tradeoff guard-state-write.sh accepts).
# Degrades gracefully (lexnorm+case-fold only, no physical resolve) if ROOT or an ancestor
# vanishes mid-check -- never dies, never blocks the caller on a filesystem race.
_lexnorm() {
  local p="$1" seg out="" oldifs="$IFS"
  IFS=/
  set -f
  # shellcheck disable=SC2086
  set -- $p
  set +f
  IFS="$oldifs"
  for seg in "$@"; do
    case "$seg" in
      ""|".") continue ;;
      "..") out="${out%/*}" ;;
      *)     out="$out/$seg" ;;
    esac
  done
  [ -n "$out" ] && printf '%s' "$out" || printf '/'
}

canon_path() {
  local raw="$1" root_phys abs dir rest depth=0 real_dir real
  case "$raw" in
    /*) abs="$raw" ;;
    *)  abs="$ROOT/$raw" ;;
  esac
  abs=$(_lexnorm "$abs")

  dir=$(dirname "$abs"); rest=$(basename "$abs")
  while [ ! -d "$dir" ] && [ "$dir" != "/" ] && [ "$depth" -lt 64 ]; do
    rest="$(basename "$dir")/$rest"
    dir=$(dirname "$dir")
    depth=$((depth + 1))
  done
  real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || real_dir="$dir"
  real="$real_dir/$rest"

  root_phys=$(cd "$ROOT" 2>/dev/null && pwd -P) || root_phys="$ROOT"
  case "$real" in
    "$root_phys"/*) real="${real#"$root_phys"/}" ;;
    "$root_phys")   real="." ;;
  esac
  # NOTE: case-fold (phase C) is deliberately NOT applied here -- it happens once, at
  # comparison time, inside path_matches() below. Folding the string this function RETURNS
  # would permanently lowercase every path used in a DENY/ALLOW message, an --amend
  # command hint, and an audit-log line -- so an operator reading "readme.md" in a log
  # could never tell it was really "README.md" on disk. Case is still fully closed as a
  # bypass vector (path_matches folds BOTH the candidate and the manifest pattern before
  # every single comparison, on every filesystem, not just a case-insensitive one) -- this
  # function only ever needs to return the real, on-disk-cased (for whatever prefix
  # physically exists) path for display purposes.
  printf '%s' "$real"
}

# ---- pattern matching: shell case-pattern, same dialect as the Scope Contract's
# "Files:" field (references/scope-lock.md). `*` already matches across '/' here since
# this is string-level `case` matching, not a filesystem glob -- so `src/orders/**`
# behaves identically to `src/orders/*` (both mean "any suffix"); no globstar shell
# option needs to be set. Both sides case-folded HERE (not baked into canon_path's return
# value -- see that function's own note) so a canon_path'd candidate always compares
# correctly against a manifest pattern authored in whatever case the Scope Contract
# happened to be typed in, on ANY filesystem (not just a case-insensitive one).
path_matches() {
  local candidate pattern
  candidate=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  pattern=$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')
  # $pattern is DELIBERATELY unquoted below: it is meant to be matched as a shell glob
  # (the manifest's "src/orders/**" pattern dialect), not a literal string. Pre-existing
  # design, unchanged by this bd.
  # shellcheck disable=SC2254
  case "$candidate" in
    $pattern) return 0 ;;
    *)        return 1 ;;
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

# ---- bindings_shape_ok_or_die: $1=mf. Every bind-facing command (cmd_bind,
# cmd_bind_record) calls this before touching `.bindings` at all. Dies (64) with a clear
# operator message if the manifest's bindings map is still in the pre-C1 flat shape
# (bare string value per instance_id) instead of the platform-neutral record shape (object
# value per instance_id) -- see the "bind design" header comment's "Migration" paragraph
# for why this is a clean reject, not a silent reinterpretation. An empty/absent bindings
# map, or one whose first entry is already an object, is fine -- returns silently.
bindings_shape_ok_or_die() {
  local mf="$1" first_type
  first_type=$(jq -r '(.bindings // {}) | to_entries | if length > 0 then (.[0].value | type) else "empty" end' "$mf" 2>/dev/null)
  case "$first_type" in
    object|empty) return 0 ;;
    string)
      die "manifest $mf has a \`bindings\` map in the pre-C1 flat shape (\"<instance_id>\": \"<label>\") -- this version of scope-check.sh only reads the platform-neutral record shape (\"<instance_id>\": {\"platform\": ..., \"role\": ..., \"label\": ...}). Ask Oliver to regenerate this bd's scope manifest under a fresh Scope Contract (fresh binds), or hand-migrate every bindings entry to the object form before retrying."
      ;;
    *) die "manifest $mf has a \`bindings\` map with an unrecognised value shape ($first_type)" ;;
  esac
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

# ---- lock mechanics (mkdir-based, no automatic stale-lock reclamation) now live in
# scripts/lib/lock.sh (bd:shode-house-vz8, sourced above via SELF_DIR). This file used
# to carry its own copy that reaped a lock whose holder pid looked dead by doing a
# plain `rm -rf` on the canonical lock path the moment it observed that -- the SAME
# bootstrap race bd:shode-house-5cs.7 had already found (and only partially closed,
# three times over) in scripts/side-effect.sh / scripts/workflow-state.sh's copies:
# under real concurrency a holder's release and its own process exit happen back-to-
# back, so a waiter that cached the outgoing holder's pid a moment earlier judges it
# "dead" right as some OTHER waiter's fresh mkdir has just landed, and reclaims that
# fresh waiter's lock instead -- this is exactly the shape Quinn measured as concurrent
# `--amend` on DIFFERENT paths losing 4, 7 and 3 writes out of 40 (every caller still
# got ALLOW/exit 0; the manifest write itself was what got clobbered by two callers
# simultaneously believing they held the same lock). bd:shode-house-vz8 closes this by
# removing automatic reclamation entirely -- see scripts/lib/lock.sh's header for the
# full acquire/release/recover contract this file's cmd_amend/cmd_bind_record/cmd_snapshot
# now use.

# ---- scopecheck_acquire_lock <bd> <caller-label> <lockdir> (bd:shode-house-5cs.8, W2) --
# adopts lock.sh's result vocabulary. This file used to call `lock_acquire` directly and
# treat ANY non-zero return the same way (a single generic "another writer in progress"
# die, no retry at all) -- deliberately left inconsistent with scripts/side-effect.sh's
# sideeffect_acquire_lock / scripts/workflow-state.sh's wfstate_acquire_lock while
# lock.sh itself was still being reworked (bd:shode-house-vz8). Now matches their shape:
# retry belongs to the CALLER (lock.sh's own header says so explicitly), never inside
# lock.sh. Retryable, bounded, with small jitter: LOCK_BUSY (1, ordinary contention) and
# RECOVERY_IN_PROGRESS (2, an operator recovery is running but expected to finish soon) --
# this matches workflow-state.sh's own shape (both codes retryable), which is also the
# exact retry set this bd's own delegation named for --amend/--snapshot. Never
# "non-zero == retryable": every other rc (4 LOCK_CORRUPT, 5 RECOVERY_REQUIRED, or any
# future/unforeseen value) is an immediate, non-retried STOP -- only a human running
# `scripts/lib/lock.sh recover` can resolve those; retrying cannot. On success, sets
# SCOPECHECK_LOCK_TOKEN and returns 0. MUST be called directly in the caller's own shell,
# never through `$(...)` -- die()'s `exit 64` only kills a command-substitution subshell,
# the caller would never actually see it (same reason noted in both sibling files).
#
# Retry-then-re-validate (this bd's own per-consumer ruling for --amend, applied uniformly
# to every RMW command here): once this function returns 0, the caller re-reads and
# re-evaluates whatever it needs FRESH, under the now-held lock -- it never acts on a
# pre-lock read that may have gone stale during a retry. cmd_amend already does exactly
# this (its own TOCTOU-close re-evaluate_ownership call, unchanged by this edit); cmd_snapshot
# is restructured (see below) to do all of its manifest reads AFTER this call succeeds, for
# the identical reason.
SCOPECHECK_LOCK_MAX_ATTEMPTS="${SCOPECHECK_LOCK_MAX_ATTEMPTS:-2}"
SCOPECHECK_LOCK_TOKEN=""
scopecheck_acquire_lock() {
  local bd="$1" label="$2" lockd="$3"
  local attempt=0 tok rc
  while :; do
    attempt=$((attempt + 1))
    tok=$(lock_acquire "$lockd"); rc=$?
    [ "$rc" -eq 0 ] && { SCOPECHECK_LOCK_TOKEN="$tok"; return 0; }
    case "$rc" in
      1|2) : ;;   # LOCK_BUSY | RECOVERY_IN_PROGRESS -- retryable, bounded
      *) break ;; # LOCK_CORRUPT / RECOVERY_REQUIRED / anything else -- STOP, never retry
    esac
    [ "$attempt" -ge "$SCOPECHECK_LOCK_MAX_ATTEMPTS" ] && break
    sleep "0.$((RANDOM % 4 + 1))"
  done
  case "$rc" in
    1) die "$label: could not acquire lock for '$bd' after $attempt attempt(s) -- LOCK_BUSY (ordinary contention exhausted bounded retry) (${lockd})" ;;
    2) die "$label: could not acquire lock for '$bd' after $attempt attempt(s) -- RECOVERY_IN_PROGRESS (an operator recovery is still running) (${lockd})" ;;
    4) die "$label: could not acquire lock for '$bd' -- LOCK_CORRUPT (lock directory cannot be read -- permission problem?) (${lockd})" ;;
    5) die "$label: could not acquire lock for '$bd' -- RECOVERY_REQUIRED (this lock looks crash-stuck; an operator must run 'scripts/lib/lock.sh recover') (${lockd})" ;;
    *) die "$label: could not acquire lock for '$bd' -- unexpected lock_acquire rc=$rc (${lockd})" ;;
  esac
}

# =============================================================================
# ownership evaluation -- shared by cmd_check (prints + exits) and cmd_amend (needs the
# verdict WITHOUT exiting, to decide whether an amendment is even eligible). Sets
# EVAL_CODE (0 ALLOW | 1 DENY | 4 NEEDS_AMENDMENT) and EVAL_MSG (one line, no trailing
# newline). Never touches the manifest.
# =============================================================================
EVAL_CODE=1
EVAL_MSG=""

evaluate_ownership() {
  local bd="$1" mf="$2" agent="$3" path="$4"
  EVAL_CODE=1
  EVAL_MSG=""

  local matched_shared
  matched_shared=$(find_shared_key "$mf" "$path") || matched_shared=""

  if [ -n "$matched_shared" ]; then
    local sf_mode sf_owner
    sf_mode=$(jq -r --arg k "$matched_shared" '.shared_files[$k].mode' "$mf")
    sf_owner=$(jq -r --arg k "$matched_shared" '.shared_files[$k].owner // ""' "$mf")
    case "$sf_mode" in
      exclusive|merge-owner)
        if [ -z "$sf_owner" ]; then
          EVAL_MSG=$(printf 'DENY: shared_files["%s"] mode=%s has no declared owner (manifest error) -- fail-safe locked, fix the manifest' "$matched_shared" "$sf_mode")
          return
        fi
        if [ "$agent" = "$sf_owner" ]; then
          EVAL_CODE=0
          EVAL_MSG=$(printf 'ALLOW: "%s" matches shared_files["%s"] mode=%s, agent "%s" is the owner' "$path" "$matched_shared" "$sf_mode" "$agent")
          return
        fi
        EVAL_MSG=$(printf 'DENY: "%s" matches shared_files["%s"] mode=%s, owned by "%s" (not "%s") -- ask "%s" to merge your change, do not write directly' "$path" "$matched_shared" "$sf_mode" "$sf_owner" "$agent" "$sf_owner")
        return
        ;;
      append-only)
        if jq -e --arg a "$agent" '.agents // [] | any(.agent == $a)' "$mf" >/dev/null 2>&1; then
          EVAL_CODE=0
          EVAL_MSG=$(printf 'ALLOW: "%s" matches shared_files["%s"] mode=append-only, "%s" is a registered agent for this bd' "$path" "$matched_shared" "$agent")
          return
        fi
        EVAL_MSG=$(printf 'DENY: "%s" matches shared_files["%s"] mode=append-only, but "%s" is not a registered agent for bd "%s"' "$path" "$matched_shared" "$agent" "$bd")
        return
        ;;
      generated)
        local regen
        regen=$(jq -r --arg k "$matched_shared" '.shared_files[$k].regenerate_via // "(no regenerate_via declared in manifest)"' "$mf")
        EVAL_MSG=$(printf 'DENY: "%s" matches shared_files["%s"] mode=generated -- nobody hand-writes this; regenerate via: %s' "$path" "$matched_shared" "$regen")
        return
        ;;
      *)
        EVAL_MSG=$(printf 'DENY: "%s" matches shared_files["%s"] with unknown mode "%s" -- fail-safe locked, fix the manifest' "$path" "$matched_shared" "$sf_mode")
        return
        ;;
    esac
  fi

  # not a shared file -- fall through to agents[].owns[]
  local ow_agent ow_pattern found_owner=""
  while IFS=$'\t' read -r ow_agent ow_pattern; do
    [ -z "$ow_agent" ] && continue
    if path_matches "$path" "$ow_pattern"; then found_owner="$ow_agent"; break; fi
  done < <(jq -r '.agents[]? | .agent as $a | .owns[]? | [$a, .] | @tsv' "$mf")

  if [ -n "$found_owner" ]; then
    if [ "$found_owner" = "$agent" ]; then
      EVAL_CODE=0
      EVAL_MSG=$(printf 'ALLOW: "%s" is owned by "%s" (self)' "$path" "$agent")
      return
    fi
    EVAL_MSG=$(printf 'DENY: "%s" is owned by "%s", not "%s"' "$path" "$found_owner" "$agent")
    return
  fi

  # unclaimed by any agent and not a shared_files entry -- v2 (bd: shode-house-5cs.4):
  # FAIL-CLOSED by default now. Check the requesting agent's own plan-approved
  # allowed_roots[] (declared once, at Scope Contract time, and never expandable by
  # --amend itself -- see cmd_amend). Inside -> NEEDS_AMENDMENT (self-amend path exists).
  # Outside (or agent has no allowed_roots / isn't even registered in the manifest at
  # all) -> DENY, escalate, never self-amend.
  local ar_pattern matched_root=""
  while IFS= read -r ar_pattern; do
    [ -z "$ar_pattern" ] && continue
    if path_matches "$path" "$ar_pattern"; then matched_root="$ar_pattern"; break; fi
  done < <(jq -r --arg a "$agent" '.agents[]? | select(.agent == $a) | .allowed_roots[]? // empty' "$mf")

  if [ -n "$matched_root" ]; then
    EVAL_CODE=4
    EVAL_MSG=$(printf 'NEEDS_AMENDMENT: "%s" is unclaimed but falls inside agent "%s"'"'"'s plan-approved allowed_roots ("%s") for bd "%s" -- run: scope-check.sh %s %s %s --amend' \
      "$path" "$agent" "$ar_pattern" "$bd" "$bd" "$agent" "$path")
    return
  fi

  EVAL_MSG=$(printf 'DENY: "%s" is unclaimed and outside agent "%s"'"'"'s allowed_roots for bd "%s" -- escalate to Oliver for a scope amendment, never self-amend outside your plan-approved boundary' "$path" "$agent" "$bd")
}

# =============================================================================
# 7.1 + 7.2 + Part 1 (fail-closed unclaimed path): ownership check
# =============================================================================
cmd_check() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0
  path=$(canon_path "$path")

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"

  evaluate_ownership "$bd" "$mf" "$agent" "$path"
  printf '%s\n' "$EVAL_MSG"
  exit "$EVAL_CODE"
}

# =============================================================================
# Part 1: atomic self-amend -- ONLY legal when the plain check above would return
# NEEDS_AMENDMENT for this exact (agent, path). Adds the path to owns[] ONLY, never to
# allowed_roots[] (self-amend must not become self-expand). Same
# lock/validate/atomic-rename discipline as the rest of this repo (workflow-state.sh).
# =============================================================================
cmd_amend() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0
  path=$(canon_path "$path")

  # bd: shode-house-5cs.4 iter 2, "M2" (Quinn) -- owns[] is matched by path_matches, the
  # SAME glob-capable function allowed_roots[] uses. A crafted --amend whose <path> token
  # is itself a literal glob (e.g. "src/payment/**") would otherwise be accepted verbatim
  # once it string-matches the agent's own allowed_roots pattern, collapsing a per-file
  # self-amend into a one-shot root-wide owns[] grant. owns[] is only ever meant to record
  # CONCRETE files an agent actually touched -- reject outright before eligibility is even
  # evaluated, so no crafted path can ride through on a coincidental allowed_roots match.
  case "$path" in
    *'*'*|*'?'*|*'['*|*']'*)
      printf 'DENY: cannot amend "%s" for agent "%s" -- owns[] only accepts concrete file paths, never glob metacharacters (one of * ? [ ]) -- self-amend claims exactly the file you touched, not a pattern\n' "$path" "$agent"
      exit 1
      ;;
  esac

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"

  evaluate_ownership "$bd" "$mf" "$agent" "$path"
  case "$EVAL_CODE" in
    0)
      printf 'ALLOW: "%s" is already owned by "%s" -- nothing to amend\n' "$path" "$agent"
      exit 0
      ;;
    4)
      : # eligible -- inside allowed_roots and currently unclaimed, proceed
      ;;
    *)
      printf 'DENY: cannot amend "%s" for agent "%s" -- %s\n' "$path" "$agent" "$EVAL_MSG"
      exit 1
      ;;
  esac

  mkdir -p "$SCOPE_DIR"
  local lockd; lockd="$SCOPE_DIR/.lock-$(encode_bd "$bd")"
  scopecheck_acquire_lock "$bd" "amend" "$lockd"
  local lock_token="$SCOPECHECK_LOCK_TOKEN"
  trap 'lock_release "'"$lockd"'" "'"$lock_token"'"' EXIT

  # re-evaluate under the lock -- someone else may have amended/claimed this exact path
  # between the unlocked pre-check above and acquiring the lock (TOCTOU close).
  evaluate_ownership "$bd" "$mf" "$agent" "$path"
  if [ "$EVAL_CODE" != 4 ]; then
    printf 'DENY: cannot amend "%s" for agent "%s" -- state changed since the pre-check (%s)\n' "$path" "$agent" "$EVAL_MSG"
    exit 1
  fi

  local tmp; tmp=$(mktemp "$SCOPE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  jq --arg a "$agent" --arg p "$path" \
    '(.agents |= map(if .agent == $a then (.owns = ((.owns // []) + [$p] | unique)) else . end))' \
    "$mf" > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "amend: generated manifest failed JSON validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$mf"
  printf 'ALLOW: amended -- "%s" added to agent "%s"'"'"'s owns[] for bd "%s" (allowed_roots unchanged); re-check will now ALLOW\n' "$path" "$agent" "$bd"
  exit 0
}

# =============================================================================
# Part 2: bind-on-claim
#
# cmd_bind: the exact 3-arg shape an agent types itself (`<bd> <label> --bind`).
# Deliberately inert -- see the "bind design" header comment for why. Always exit 0.
# =============================================================================
cmd_bind() {
  local bd="$1" label="$2"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  if [ ! -f "$mf" ]; then
    printf 'NO_MANIFEST: no scope manifest recorded for bd "%s" -- nothing to bind against\n' "$bd"
    exit 2
  fi
  jq empty "$mf" >/dev/null 2>&1 || die "manifest $mf is not valid JSON"
  bindings_shape_ok_or_die "$mf"

  local bound_instance
  bound_instance=$(jq -r --arg l "$label" '.bindings // {} | to_entries[] | select(.value.label == $l) | .key' "$mf" 2>/dev/null | head -1)
  if [ -n "$bound_instance" ]; then
    printf 'INFO: label "%s" for bd "%s" is bound (recorded by a platform adapter, not by this direct invocation -- it has no instance_id to act on)\n' "$label" "$bd"
  else
    printf 'INFO: label "%s" for bd "%s" is not yet bound -- the platform adapter records the real (instance_id, role, platform) -> label binding when it observes this exact command shape; this direct invocation cannot know its own instance_id\n' "$label" "$bd"
  fi
  exit 0
}

# =============================================================================
# cmd_bind_record: the REAL write. Internal-only
# (`<bd> <instance-id> <role> <label> <platform> --bind-record`), called by a platform
# adapter (hooks/scripts/guard-scope-write.sh today) with a real instance_id/role it
# parsed out of its own harness's identity fields, and its own literal platform string.
# Implements the 7 binding rules verbatim (user ruling, bd: shode-house-5cs.4) -- STATED IN
# TERMS OF instance_id AND label ONLY; role/platform are recorded metadata, never part of
# the rule evaluation itself (do not derive the label from the role):
#   first-bind-wins per instance_id
#   instance label unique per bd
#   label must already exist in the manifest
#   unknown bd or unknown label                 -> DENY
#   same instance_id -> same label               -> idempotent ALLOW
#   same instance_id -> a different label        -> DENY
#   a different instance_id -> a bound label      -> DENY
# =============================================================================
cmd_bind_record() {
  local bd="$1" instance_id="$2" role="$3" label="$4" platform="$5"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  if [ ! -f "$mf" ]; then
    printf 'DENY: unknown bd "%s" -- no scope manifest recorded, nothing to bind against\n' "$bd"
    exit 1
  fi
  jq empty "$mf" >/dev/null 2>&1 || die "manifest $mf is not valid JSON"

  if ! jq -e --arg l "$label" '.agents[]? | select(.agent == $l)' "$mf" >/dev/null 2>&1; then
    printf 'DENY: unknown label "%s" for bd "%s" -- label must already exist in the manifest'"'"'s agents[] before it can be bound\n' "$label" "$bd"
    exit 1
  fi

  bindings_shape_ok_or_die "$mf"

  mkdir -p "$SCOPE_DIR"
  local lockd; lockd="$SCOPE_DIR/.lock-$(encode_bd "$bd")"
  scopecheck_acquire_lock "$bd" "bind-record" "$lockd"
  local lock_token="$SCOPECHECK_LOCK_TOKEN"
  trap 'lock_release "'"$lockd"'" "'"$lock_token"'"' EXIT

  local existing_label
  existing_label=$(jq -r --arg a "$instance_id" '.bindings[$a].label // empty' "$mf" 2>/dev/null)

  if [ -n "$existing_label" ]; then
    if [ "$existing_label" = "$label" ]; then
      printf 'ALLOW: already bound to "%s" for bd "%s" (idempotent -- same instance_id, same label)\n' "$label" "$bd"
      exit 0
    fi
    printf 'DENY: this instance_id is already bound to "%s" for bd "%s" -- cannot rebind the same instance_id to a different label ("%s" requested)\n' "$existing_label" "$bd" "$label"
    exit 1
  fi

  local bound_by
  bound_by=$(jq -r --arg l "$label" '.bindings // {} | to_entries[] | select(.value.label == $l) | .key' "$mf" 2>/dev/null | head -1)
  if [ -n "$bound_by" ]; then
    printf 'DENY: label "%s" for bd "%s" is already bound to a different instance_id -- an instance label may be bound to exactly one instance_id at a time\n' "$label" "$bd"
    exit 1
  fi

  local tmp; tmp=$(mktemp "$SCOPE_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  jq --arg a "$instance_id" --arg r "$role" --arg l "$label" --arg p "$platform" \
    '(.bindings //= {}) | .bindings[$a] = {"platform": $p, "role": $r, "label": $l}' \
    "$mf" > "$tmp"
  if ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    die "bind-record: generated manifest failed JSON validate (this is a bug -- report it)"
  fi
  mv "$tmp" "$mf"
  printf 'ALLOW: bound label "%s" for bd "%s" (first-bind)\n' "$label" "$bd"
  exit 0
}

# =============================================================================
# cmd_resolve_binding: internal-only (`<bd> <instance-id> --resolve-binding`), adapter-only
# caller. bd: shode-house-5cs.4 iter 2 -- Bella's review found the adapter
# (hooks/scripts/guard-scope-write.sh) was reading `.bindings[$a].label` DIRECTLY with its
# own inline jq, bypassing bindings_shape_ok_or_die entirely -- against an old-shape
# manifest that read a bare STRING (not an object), so `.label` was a jq type error the
# adapter's own `2>/dev/null` silently swallowed, misclassifying a legitimately-bound
# subagent as an "outsider" and denying its own writes with a misleading generic message
# instead of the clear exit-64 explanation this shape guard exists to give. Fix: the
# adapter no longer re-implements this lookup at all -- it calls this command, which runs
# the SAME bindings_shape_ok_or_die every bind-facing command already runs, so there is
# exactly one shape guard, not two (one real, one accidentally bypassed).
# Prints "BOUND: <label>" + exit 0 if resolved, "NOT_BOUND: ..." + exit 1 if the manifest is
# well-shaped but this instance_id has no entry, "NO_MANIFEST: ..." + exit 2 if no manifest
# exists for this bd at all, or dies (64, via bindings_shape_ok_or_die) if the manifest's
# `bindings` map is corrupt or still the pre-C1 flat shape -- the caller (the adapter) is
# expected to treat 64 as fail-CLOSED per C3, not fail-open like it used to.
# =============================================================================
cmd_resolve_binding() {
  local bd="$1" instance_id="$2"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  if [ ! -f "$mf" ]; then
    printf 'NO_MANIFEST: no scope manifest recorded for bd "%s"\n' "$bd"
    exit 2
  fi
  jq empty "$mf" >/dev/null 2>&1 || die "manifest $mf is not valid JSON"
  bindings_shape_ok_or_die "$mf"

  local label
  label=$(jq -r --arg a "$instance_id" '.bindings[$a].label // empty' "$mf" 2>/dev/null)
  if [ -n "$label" ]; then
    printf 'BOUND: %s\n' "$label"
    exit 0
  fi
  printf 'NOT_BOUND: instance_id "%s" has no binding recorded for bd "%s"\n' "$instance_id" "$bd"
  exit 1
}

# =============================================================================
# Part 3: main-session scope probe. Main session has no agent_id (L0 probe finding), so
# it cannot be resolved to a label the way a subagent write can. Instead: does this path
# collide with ANY currently-declared active scope surface (any agent's owns[] or
# allowed_roots[], or any shared_files[] key) for this bd? Exit 0 ALLOW (including when
# there is no manifest at all -- nothing to enforce) | exit 1 DENY (collision found).
# =============================================================================
cmd_main_check() {
  local bd="$1" path="$2"
  engagement_active || exit 0
  path=$(canon_path "$path")

  local mf; mf=$(manifest_file "$bd")
  if [ ! -f "$mf" ]; then
    printf 'ALLOW: no scope manifest recorded for bd "%s" -- nothing to enforce against a main-session write\n' "$bd"
    exit 0
  fi
  jq empty "$mf" >/dev/null 2>&1 || die "manifest $mf is not valid JSON"

  local matched_shared
  matched_shared=$(find_shared_key "$mf" "$path") || matched_shared=""
  if [ -n "$matched_shared" ]; then
    printf 'DENY: main-session write to "%s" collides with active shared_files["%s"] for bd "%s" -- this path is under active scope lock, the write must come from the owning agent, not the main session\n' "$path" "$matched_shared" "$bd"
    exit 1
  fi

  local ag pat
  while IFS=$'\t' read -r ag pat; do
    [ -z "$ag" ] && continue
    if path_matches "$path" "$pat"; then
      printf 'DENY: main-session write to "%s" collides with agent "%s"'"'"'s active scope (pattern "%s") for bd "%s" -- otherwise a subagent'"'"'s scope lock is trivially bypassed by writing from the main session\n' "$path" "$ag" "$pat" "$bd"
      exit 1
    fi
  done < <(jq -r '.agents[]? | .agent as $a | ((.owns[]? , .allowed_roots[]?)) | [$a, .] | @tsv' "$mf")

  printf 'ALLOW: main-session write to "%s" does not collide with any active agent'"'"'s owns/allowed_roots/shared_files for bd "%s"\n' "$path" "$bd"
  exit 0
}

# =============================================================================
# 7.3: optimistic conflict check -- snapshot. bd:shode-house-5cs.8 (W1): this is a
# read-modify-write on shared mutable state -- .base_sha[agent][path] in the SAME
# manifest --amend/--bind-record mutate -- and must hold the shared lock across its
# ENTIRE read-modify-write, exactly like those two, never a local lock (see this file's
# own "locking rule" header comment). Before this fix, cmd_snapshot took NO lock at all:
# two concurrent --snapshot calls on DIFFERENT paths could each read the manifest, compute
# their own updated copy, and atomic-rename over each other -- the exact same class of lost
# write bd:shode-house-vz8 already closed for --amend (Quinn measured 4, 7, and 3 of 40
# amend writes lost this way; every caller still returned ALLOW/exit 0). Every manifest
# READ this command needs (matched_shared/coupled_paths_of, then the actual base_sha
# merge) now happens AFTER the lock is held -- not before -- so a caller that had to retry
# past LOCK_BUSY/RECOVERY_IN_PROGRESS never acts on a pre-retry read that may have gone
# stale (same "re-read and re-validate" rule cmd_amend's own TOCTOU-close re-check already
# follows).
# =============================================================================
cmd_snapshot() {
  local bd="$1" agent="$2" path="$3"
  engagement_active || exit 0

  local mf; mf=$(manifest_file "$bd")
  check_manifest_or_bail "$bd" "$mf"
  mkdir -p "$SCOPE_DIR"

  local lockd; lockd="$SCOPE_DIR/.lock-$(encode_bd "$bd")"
  scopecheck_acquire_lock "$bd" "snapshot" "$lockd"
  local lock_token="$SCOPECHECK_LOCK_TOKEN"
  trap 'lock_release "'"$lockd"'" "'"$lock_token"'"' EXIT

  # ---- everything below reads $mf fresh, now that the lock is actually held (post any
  # retry) -- never a value computed before scopecheck_acquire_lock returned.
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
# 7.3: optimistic conflict check -- verify. bd:shode-house-5cs.8 (W1): stays
# DELIBERATELY lock-free -- READ-ONLY, never mutates .base_sha or anything else in the
# manifest, so it never needs mutual exclusion (see this file's own "locking rule" header
# comment for why "a command takes the lock iff it has a read-modify-write" means this
# one specifically does NOT, on purpose, permanently -- not a gap to close for symmetry
# with --amend/--bind-record/--snapshot). What it DOES need, and already has: an ATOMIC,
# VALIDATED read. Validated: check_manifest_or_bail's `jq empty` below rejects a corrupt
# manifest outright, the same gate every other command uses. Atomic: every writer of
# this manifest (--amend/--bind-record/--snapshot, all three now under the shared lock)
# replaces it via mktemp + atomic `mv`, never an in-place edit -- so any reader opening
# $mf at any instant, including one racing a concurrent --snapshot, always observes
# either the fully-old or the fully-new manifest content, never a torn half-write. No
# additional locking, buffering, or retry is needed to make that true; it already falls
# out of every writer's own atomic-rename discipline.
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
usage: scope-check.sh <bd-id> <agent> <path>                # ownership check
       scope-check.sh <bd-id> <agent> <path> --snapshot      # 7.3 record base sha
       scope-check.sh <bd-id> <agent> <path> --verify        # 7.3 optimistic conflict check
       scope-check.sh <bd-id> <agent> <path> --amend         # atomic self-amend (owns only)
       scope-check.sh <bd-id> <label> --bind                 # agent-facing bind shape (inert)
       scope-check.sh <bd-id> <path> --main-check            # main-session scope probe
       scope-check.sh <bd-id> <instance-id> <role> <label> <platform> --bind-record
                                                              # internal -- adapter-only
       scope-check.sh <bd-id> <instance-id> --resolve-binding
                                                              # internal -- adapter-only
exit: 0 ALLOW | 1 DENY | 2 NO_MANIFEST | 3 CONFLICT (--verify only) |
      4 NEEDS_AMENDMENT (--check/--amend only) | 64 usage/dep error (incl. a `bindings`
      map still in the pre-C1 flat shape -- see scope-check.sh's own "bind design" header)
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

main() {
  command -v jq >/dev/null 2>&1 || die "jq required"
  command -v shasum >/dev/null 2>&1 || die "shasum required"

  local bd="${1:-}"
  [ -n "$bd" ] || { usage; die "bd-id is required"; }

  # ---- 3-arg-with-flag-in-position-3 shapes (bd + one token + flag) -- both reuse the
  # SAME positional skeleton as the 4-arg shapes below (bd, X, flag), just one token
  # shorter, since neither --bind nor --main-check has a separate "agent" concept.
  if [ "${3:-}" = "--bind" ] && [ $# -eq 3 ]; then
    local label="${2:-}"
    [ -n "$label" ] || { usage; die "--bind: <label> required"; }
    cmd_bind "$bd" "$label"
    return
  fi
  if [ "${3:-}" = "--main-check" ] && [ $# -eq 3 ]; then
    local mc_path="${2:-}"
    [ -n "$mc_path" ] || { usage; die "--main-check: <path> required"; }
    cmd_main_check "$bd" "$mc_path"
    return
  fi
  if [ "${3:-}" = "--resolve-binding" ] && [ $# -eq 3 ]; then
    local rb_instance="${2:-}"
    [ -n "$rb_instance" ] || { usage; die "--resolve-binding: <instance-id> required"; }
    cmd_resolve_binding "$bd" "$rb_instance"
    return
  fi

  # ---- 6-token internal-only shape: bd, instance-id, role, label, platform, flag.
  # Distinct arity from every agent-typed shape above/below on purpose -- an adapter is
  # the only caller (see scope-check.sh's own "bind design" header + hooks/scripts/
  # guard-scope-write.sh).
  if [ "${6:-}" = "--bind-record" ] && [ $# -eq 6 ]; then
    local instance_id="${2:-}" role="${3:-}" bind_label="${4:-}" platform="${5:-}"
    if [ -z "$instance_id" ] || [ -z "$role" ] || [ -z "$bind_label" ] || [ -z "$platform" ]; then
      usage; die "--bind-record: <instance-id> <role> <label> <platform> all required"
    fi
    cmd_bind_record "$bd" "$instance_id" "$role" "$bind_label" "$platform"
    return
  fi

  local agent="${2:-}" path="${3:-}" flag="${4:-}"
  if [ -z "$agent" ] || [ -z "$path" ]; then
    usage; die "bd-id, agent, and path are all required"
  fi

  case "$flag" in
    "")              cmd_check "$bd" "$agent" "$path" ;;
    "--snapshot")    cmd_snapshot "$bd" "$agent" "$path" ;;
    "--verify")      cmd_verify "$bd" "$agent" "$path" ;;
    "--amend")       cmd_amend "$bd" "$agent" "$path" ;;
    *) usage; die "unknown flag '$flag'" ;;
  esac
}

main "$@"
