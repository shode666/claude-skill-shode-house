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
# Production-bound gates (bd:shode-house-5cs.5) -- gate names matching "pre-deploy*",
# "pre-merge*", "pre-data-migration*", "pre-destructive*", or exactly "production" --
# additionally REFUSE to grant unless the working tree is CLEAN, full stop: `git status
# --porcelain` must be empty. Production-bound gate list is authoritative at
# output-styles/oliver.md:99 (that file is NO-list -- read-only, never edited here; cite
# the line number so the next person does not have to rediscover it) -- it also names
# pre-data-migration and pre-destructive, the two most irreversible gates in the system,
# which the original iter0 pattern (pre-deploy*|pre-merge*|production only) missed.
#
# iter1 (bd:shode-house-5cs.3/.5 rework, per Bella/Oliver 3b-review ruling): the ORIGINAL
# rationale here scoped the check to `git diff --quiet` + `git diff --cached --quiet`
# (tracked-file drift only), deliberately excluding untracked files. Oliver overruled
# that judgment call: for a production-bound gate the requirement is a CLEAN TREE, and a
# brand-new UNTRACKED file (a new migration, a new deploy script) is exactly the kind of
# unreviewed change the gate exists to catch -- it was invisible to both `git diff` and
# `git diff --cached` (neither command sees untracked paths at all), which is the same
# "approval looks valid, tree no longer matches what was approved" failure mode this gate
# exists to close, just triggered by `git status`'s `??` state instead of `M`. `git status
# --porcelain` (no `--ignored`) catches tracked drift (staged + unstaged) AND untracked
# files in one check, while files matched by `.gitignore` are excluded by git's own
# default `--porcelain` behavior -- so gitignored cruft (build output, local scratch
# files) never blocks a grant, only genuinely unreviewed paths do. `.shode-house/approval/`
# (APPROVAL_DIR -- the one directory this exact script ever writes an approval JSON
# into) is also excluded from the check when the entry there is untracked, same
# rationale as `.gitignore`d paths: it is not reviewed content, and without the
# exclusion an approval JSON this very grant is about to write would self-dirty the
# tree for the NEXT grant call in an un-gitignored target project. Non-production
# gates are unaffected -- this check does not run for them at all.
#
# iter2 (bd:shode-house-5cs.5 rework, per Chris 3b-review Critical -- reproduced, Oliver
# confirmed independently): iter1's exclusion above was a BLANKET pathspec
# (":!.shode-house"), which hid the ENTIRE `.shode-house/` subtree -- not just this
# script's own approval JSON, but ANY tracked, modified, real code file someone placed
# under `.shode-house/` too (a "TAMPERED" append to a tracked `.shode-house/deploy.sh`
# was invisible to the check and GRANTed over, including for pre-deploy-prod/
# pre-destructive), AND any brand-new untracked file placed anywhere else under
# `.shode-house/` by something other than this script. The fix does NOT special-case a
# list of filenames -- it derives the exclusion from what `git status --porcelain`'s own
# status code ALREADY tells us (a line's first two characters distinguish tracked drift,
# "M"/"A"/"D"/"R"/"C"/"U" in either column, from untracked, "??"), narrowed to the ONE
# directory this script's own APPROVAL_DIR constant names. ONLY an untracked ("??")
# entry under `.shode-house/approval/` was dropped from the dirty set at this point in
# the file's history -- superseded by iter3 below, which narrows this further to exactly
# one file, not the whole directory. A TRACKED change is NEVER dropped, no matter where
# it lives, including under `.shode-house/`; an untracked file anywhere OUTSIDE
# `.shode-house/approval/` -- whether outside `.shode-house/` entirely (the pre-existing
# "new unreviewed file must DENY" rule, unaffected) or elsewhere inside `.shode-house/`
# (e.g. `.shode-house/state/`, `.shode-house/side-effects/`, or any other subpath) --
# also still blocks. Gitignored paths still never appear in `git status --porcelain`
# output at all (git's own default behavior, no flag needed) -- unaffected either way.
#
# iter3 (bd:shode-house-5cs.5 rework, per Chris 3b-review Critical -- reproduced a THIRD
# time, narrower blast radius each round): iter2's exclusion above was STILL a SET --
# "every untracked entry whose path starts with APPROVAL_DIR" -- so any untracked file
# dropped directly under `.shode-house/approval/` (an arbitrary payload, a stray leftover
# approval JSON for a DIFFERENT bd/gate, a second attacker-planted file sitting beside the
# real one) rode through, exempted by directory MEMBERSHIP alone, not by being the one
# file this exact `grant` invocation is about to write. Narrowing the exempted set again
# would be the same move a third time -- instead the exemption collapses to a SINGLETON:
# compute the one exact relative path this invocation's own `approval_file "$bd" "$gate"`
# resolves to, and drop only a `??` line whose path equals that exact string -- never a
# prefix/directory match. Every other untracked file anywhere under
# `.shode-house/approval/` -- including a leftover/decoy approval JSON for a DIFFERENT
# bd/gate, or a non-JSON file planted beside the real one -- now stays in the dirty set
# and blocks, exactly like anywhere else in the tree. Re-granting the SAME bd/gate a
# second time (updating an existing approval) still succeeds, because that call's own
# target path is, by definition, the one path being exempted -- there is no set left to
# be wrong about.
#
# exit codes:
#   grant:  0 GRANTED | 1 DENY (production-bound gate refused -- working tree is not
#           clean, tracked drift and/or untracked files) | 64 usage/dependency error
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

# iter4 fix (bd:shode-house-5cs.5, Quinn 3b-review Medium -- confirmed not exploitable
# into a false ALLOW, but violated this field's own documented contract): in a git repo
# with ZERO commits, `git rev-parse HEAD` cannot resolve a ref -- it writes its
# best-effort partial output ("HEAD") to STDOUT, an error to stderr, and exits non-zero,
# all at once. The old one-liner (`git ... 2>/dev/null || printf 'n/a'`) captured BOTH the
# stray stdout AND the `|| printf 'n/a'` fallback into the same "$(...)" call site,
# producing the corrupted two-line sentinel "HEAD\nn/a" instead of the documented clean
# "n/a". Gating the fallback on the command's own exit status (not just piping stderr
# away) makes a failed rev-parse NEVER leak its partial stdout to the caller.
git_head() {
  local out
  if out=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null); then printf '%s' "$out"
  else printf 'n/a'; fi
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
exit (grant):  0 GRANTED | 1 DENY (production-bound gate, tree not clean) | 64 usage/dep error
exit (verify): 0 ALLOW | 1 DENY (stale) | 2 NO_APPROVAL | 64 usage/dep error
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

# production-bound gate names -- authoritative list: output-styles/oliver.md:99
# (pre-spec-expand, pre-implement-ui, pre-ui-check, pre-code-review, pre-merge,
# pre-merge-ui, pre-loop-exit, pre-deploy-*, pre-data-migration, pre-destructive). Only
# the gates that gate an irreversible/production-facing action need the clean-tree check
# below -- pre-data-migration and pre-destructive added iter1 (bd:shode-house-5cs.5
# rework), they are the two most irreversible gates in the registry and were missing.
# See header comment for what this gates and why (clean-tree check, incl. untracked).
is_production_gate() {
  case "$1" in
    pre-deploy*|pre-merge*|pre-data-migration*|pre-destructive*|production) return 0 ;;
    *) return 1 ;;
  esac
}

is_git_repo() {
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# =============================================================================
# grant
# =============================================================================
cmd_grant() {
  local bd="$1" gate="$2" scope="$3" approved_by="$4"
  shift 4
  [ $# -ge 1 ] || die "grant: at least one <path> is required (artifacts the approval is bound to)"

  engagement_active || exit 0

  # ---- production-bound gates: refuse to grant over an unclean tree -- tracked drift
  # (staged or unstaged) OR untracked files, gitignored paths excluded (Oliver ruling,
  # bd:shode-house-5cs.5 iter1 -- see header comment). Skipped entirely if $ROOT is not
  # a git repo (mirrors the existing git_commit="n/a" convention below -- a non-git
  # sandbox/repo must stay usable, this check just can't run there).
  if is_production_gate "$gate" && is_git_repo; then
    # ---- iter3 fix (bd:shode-house-5cs.5, Chris Critical, third round -- see header
    # comment): no directory-prefix exclusion, not even scoped to APPROVAL_DIR. Two
    # scoped porcelain calls, same as iter2 (still the right shape -- Chris's own
    # review called this part "structurally sound"):
    #   (a) everything OUTSIDE ".shode-house/" -- default porcelain, unchanged behavior.
    #   (b) ONLY inside ".shode-house/", with `--untracked-files=all` so a wholly-new
    #       ".shode-house/" directory is walked file-by-file instead of collapsing to a
    #       single "?? .shode-house/" line (git's default directory-collapse behavior
    #       for an entirely-untracked directory) -- without this, a brand-new approval
    #       JSON this very grant is about to have already written under it in an
    #       earlier call would be indistinguishable, by path, from the directory line
    #       itself. `-uall` is scoped to ONLY ".shode-house/" here (bounded, this tool's
    #       own small runtime dir), not the whole repo, so it carries none of the
    #       whole-tree "-uall on a large repo" cost.
    # From (b), drop ONLY the one "??" line whose path equals the EXACT file THIS
    # invocation's own approval_file() call is about to write -- a singleton, not a
    # directory or a filename pattern. Everything else stays in the dirty set: every
    # tracked change ("M"/"A"/"D"/"R"/"C"/"U" in either status column) anywhere --
    # including elsewhere under ".shode-house/" -- is kept, AND every OTHER untracked
    # file anywhere -- whether outside ".shode-house/" entirely, or elsewhere inside it,
    # including a leftover/decoy approval JSON for a DIFFERENT bd/gate sitting right
    # next to this one inside APPROVAL_DIR itself -- still blocks. Only THIS invocation's
    # own single write target is exempt from self-dirtying its own gate.
    local approval_file_rel; approval_file_rel="$(approval_file "$bd" "$gate")"
    approval_file_rel="${approval_file_rel#"$ROOT"/}"
    local outside_shodehouse inside_shodehouse dirty="" line code path
    outside_shodehouse=$(git -C "$ROOT" status --porcelain -- . ':!.shode-house' 2>/dev/null)
    inside_shodehouse=$(git -C "$ROOT" status --porcelain --untracked-files=all -- .shode-house 2>/dev/null)
    dirty="$outside_shodehouse"
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      code="${line:0:2}"
      path="${line:3}"
      case "$code" in
        '??')
          [ "$path" = "$approval_file_rel" ] && continue   # ONLY this exact call's own target file
          ;;
      esac
      dirty="${dirty}${dirty:+$'\n'}${line}"
    done <<< "$inside_shodehouse"
    if [ -n "$dirty" ]; then
      printf 'DENY: refusing to grant gate "%s" for bd "%s" -- working tree is not clean (git status --porcelain is non-empty -- tracked-file drift and/or untracked files; gitignored paths are excluded by git'"'"'s own default behavior); production-bound gates require a clean tree so the approved commit actually reflects what was reviewed. dirty entries:\n%s\n' \
        "$gate" "$bd" "$dirty"
      exit 1
    fi
  fi

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
