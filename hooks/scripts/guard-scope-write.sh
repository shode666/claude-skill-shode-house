#!/usr/bin/env bash
# guard-scope-write.sh -- PreToolUse Write|Edit|Bash guard (bd: shode-house-5cs.4, L2)
#
# THE PLATFORM ADAPTER: this script is the one place in the repo allowed to name a
# platform (scripts/scope-check.sh, the core, never does -- see that script's own "bind
# design" header comment, invariant grep-enforced by the maintainer suite test-scope-check.sh). It reads
# this host's own PreToolUse identity fields (`agent_id`, `agent_type`) and normalizes
# them into the core's platform-neutral vocabulary before ever calling scope-check.sh:
#   agent_id (PreToolUse)   -> instance_id (core)
#   agent_type (PreToolUse) -> role (core) -- recorded verbatim, never used to derive a
#                               label
#   (this adapter's own identity) -> platform (core) -- the one literal platform-name
#                               string that belongs in THIS file, set below at its single
#                               call site (`PLATFORM_NAME`)
#
# Turns scripts/scope-check.sh's manifest from advisory (nothing ever called it) into
# enforced. Two independent jobs, dispatched on `tool_name`:
#
#   1. Write|Edit -> scope-check the target path against the scope manifest of whichever
#      bd is currently active, resolved from `.shode-house/state` (workflow-state.sh owns
#      that directory; this script only ever reads it, never writes it -- L0 probe
#      confirmed Write/Edit's own tool_input carries no bd/task field at all). Sub-cases:
#        a. subagent (PreToolUse `agent_id` present), resolved to exactly one bound label
#           in exactly one active bd -- run the ordinary ownership check under that label.
#        b. main session (`agent_id` absent), OR a subagent whose instance_id is unbound
#           in the one active bd it could resolve to, OR a subagent whose instance_id
#           resolves ambiguously across active bds (bound in zero or more than one) --
#           ALL THREE are "outsiders" and get the IDENTICAL policy (bd: shode-house-5cs.4
#           iter 1, "C2"; the user ruling calls this "the outsider policy"): a write inside
#           ANY active bd's declared owns/allowed_roots/shared_files is DENIED (otherwise a
#           subagent's scope lock is trivially bypassable by simply never binding, or by
#           writing from the main session instead); a write outside every active bd's
#           declared scope is ALLOWED + one audit log line (this is what keeps a reviewer
#           writing under outputs/ -- which no manifest ever claims -- working with zero
#           friction, even though it never bound anywhere).
#
#   2. Bash -- recognise the bind-on-claim command `scripts/scope-check.sh <bd> <label>
#      --bind` and perform the REAL write scope-check.sh's own `cmd_bind` cannot (it has
#      no instance_id -- see that script's own "bind design" header comment). This is the
#      "hook sees both agent_id/agent_type and the Bash command in one payload" trick from
#      Part 2 of the brief.
#
#      Recognition is a STRICT, fully-anchored canonical shape ONLY -- never a substring
#      match for "--bind" (that would make the binding control plane a new
#      command-parsing attack surface: a compound command like
#      `scripts/scope-check.sh bd Dave#1 --bind && fetch-something evil.example` must NOT
#      be treated as "yes, this is a legitimate bind" just because part of the string
#      resembles one).
#      Defense in depth, in order:
#        (i)  narrow scope: only even look at commands mentioning BOTH "scope-check.sh"
#             and "--bind" as literal substrings (`case` glob, not a shape check) -- this
#             is purely a cheap pre-filter so this guard never touches unrelated Bash
#             calls, not the security boundary itself.
#        (ii) reject OUTRIGHT (exit 2, deny the whole Bash call) if the command contains
#             ANY of: `;` `&&` `||` `|` `$(` a backtick, or a redirect (`>` / `<`)
#             anywhere in the string. This check runs BEFORE shape parsing and is
#             unconditional for anything that passed (i).
#        (iii) only what survives (i)+(ii) is matched against a fully `^...$`-anchored
#             bash regex with narrow character classes for both the bd-id and the label
#             tokens -- classes that structurally exclude every char rejected in (ii), so
#             a crafted compound string cannot match this pattern even if (ii) somehow
#             missed it (belt + suspenders, not a substitute for (ii)).
#      A command that mentions scope-check.sh/--bind but fails (ii) is DENIED. A command
#      that fails (iii) alone (mentions both tokens, no forbidden metachar, just doesn't
#      match the canonical shape -- e.g. wrong arg order) is left to run un-molested: it
#      is not recognised as a bind attempt, and scope-check.sh's own `cmd_bind` (inert, no
#      side effect) or a usage error is all that executes.
#
#   3. ux path set (W8; ADR iter 5 5.7 V1.2 + addendum-1 X8), Write|Edit|NotebookEdit only,
#      when `agent_type` is exactly "shode-house:design". Applies with OR without an
#      engagement (.shode-house/state), because an injected designer is a risk in any
#      project. On the canonical path (same canon_and_check_write_target as job 1, so a
#      symlink leaf is refused, traversal/dot-slash are normalised, a ".." that removes a
#      symlink is refused, ancestors are resolved physically and a path whose existing
#      parent cannot be found or entered is refused) it DENIES:
#        - any path not under outputs/ or design-system/        (reason token ux-path-outside)
#        - an extension not in the runner's E2 data list
#          .md .json .png .jpg .svg .txt .log (exact, as DATA_EXTENSIONS)  (ux-ext)
#        - a manifest, lockfile or tool-config basename (erratum 3 1.10 rule 3, UD R65 F8;
#          closed list in ux_path_check, e.g. design-system/package.json)  (ux-config)
#        - a path segment under outputs/ containing "design-run-order"   (ux-order)
#        - a path segment under outputs/ equal to "design-run"           (ux-design-run-output)
#      (the last three case-insensitive through _scope_fold_deny: ASCII, the long s, the
#      Kelvin sign, the Latin ligatures and the sharp s that APFS folds to ASCII letters,
#      plus the platform's Unicode lower-casing; see _casefold.sh). Deny messages are
#      static and never echo the path.
#
#   4. git directories (UD U6), Write|Edit|NotebookEdit only, for EVERY caller (main
#      session, any subagent) and with OR without an engagement: a write that lands in
#      `.git`, `.git/**`, or a git dir that a `.git` file points to (worktree, submodule,
#      --separate-git-dir, plus its commondir) is DENIED (reason token git-dir). Judged on
#      the lexical path AND on the physical path the kernel writes to (leaf and intermediate
#      symlinks followed, `..` resolved physically, trailing "/" and "/." dropped) and on
#      the physical path of the lexical one, folded through _scope_fold_deny; a pointed git
#      dir is also matched by directory identity (-ef), so any spelling the filesystem
#      treats as that directory (case, Unicode normalisation) is denied too. The physical
#      path follows at most 40 symlinks in total. The git CLI (a Bash call) is not judged. Same status as job
#      3: only where hooks execute, so the host's own permissions.deny is the control that
#      holds without hooks.
#      Status: accident prevention, and protection against an injected designer, ONLY WHERE
#      HOOKS EXECUTE. It is not a control in the generated tree, in Cowork until the user's
#      manual check, or in any session with `disableAllHooks: true`; it never stops a
#      hostile repository, and it fails open without jq. The design runner's own tree check
#      is the control that holds without hooks.
#
#   Before jobs 1, 3 and 4, a Write|Edit|NotebookEdit path that holds a line break or another
#   control character (U+0000-U+001F, U+007F-U+009F) is DENIED (reason token
#   path-control-char): a shell reading of it can differ from the name the filesystem opens
#   (Sentinel pre-release r5 S5-2).
#
# WHERE THIS RUNS: only where hooks execute -- Claude Code with this plugin's
# hooks/hooks.json loaded, not switched off by `disableAllHooks`, and registered with the
# plugin root quoted. Defence in depth, not a guarantee.
#
# Exit codes -- exit 2 is the ONLY code that blocks (same Hook Charter convention as
# guard-state-write.sh): 2 = DENY, 0 = ALLOW or fail-OPEN. This guard fails OPEN on:
# missing jq, a missing hooks/scripts/_casefold.sh, empty stdin, no active bd found
# at all, or scope-check.sh returning
# NO_MANIFEST (2) -- a bug in OUR OWN tooling, or a manifest that genuinely does not exist
# yet, must never brick every write in every project (same reasoning as
# guard-state-write.sh's own jq-prereq fallback). It does NOT fail open on an unbound or
# ambiguously-bound instance_id (bd: shode-house-5cs.4 iter 1, "C2" closed that hole -- see
# the outsider policy above), and, as of iter 2 ("C3"), does NOT fail open on scope-check.sh
# returning 64 (a CORRUPT or old-shape manifest) EITHER -- a manifest that exists but cannot
# be read is a materially different failure than one that was never recorded, and gets a
# distinguishable DENY + audit line instead of being silently indistinguishable from a
# clean ALLOW. Nor does it fail open on any other exit code of scope-check.sh that is not one
# of its documented results for the call (a crash, a signal, 126/127: UD R88, Sentinel final
# FU-F1) -- see scope_check_rc_deny.
# This guard also fails CLOSED on a Write/Edit target that is (or is reached
# through) a symlink (iter 2, "H1") -- see canon_and_check_write_target -- and on a Bash
# command that mentions a fixed control-plane path regardless of read/write intent (iter 2,
# "C5", user ruling "option A") -- see the top of handle_bash -- and on a scope phase (the
# outsider and ownership evaluation) that runs past its time budget (F7-2, UD U20) -- see
# scope_budget_left.
# Hook Charter Sec 7 exception, for this guard and guard-state-write.sh only (the two write
# guards, a security boundary; UD U19, Chris pre-release r6 NF6-1, Sentinel r6 FU6-1):
# NON-EMPTY stdin that jq cannot parse or evaluate is DENIED (exit 2, reason
# "malformed/unsupported hook input"), with or without an engagement, for every tool call
# this guard receives. jq rejects input the host can still act on -- a lone UTF-16
# surrogate escape such as \ud800 anywhere in the JSON, even in the file content -- and a
# jq built without regex support fails the path test in handle_write_edit; either used to
# exit 0 here and let a .git or scope write through. One check, deny_unjudgeable_input,
# serves every read of the hook input whose failure would end the judgement: the dispatch
# read (tool_name), the Write/Edit/NotebookEdit path read, and the Bash command read (a
# tool_input that is not an object fails there: Chris r7 F3, Sentinel r7 F7-3). The other
# reads of the hook input (.agent_id, .agent_type) run only after the dispatch read has
# parsed the input as an object, and a top-level read of an object cannot fail. Empty stdin
# still exits 0. Every other hook keeps the matrix (malformed input never blocks there).
#
# Deps: bash (>= 4, for [[ =~ ]] and BASH_REMATCH) + jq (ADR-C3 -- no python3 on the hot
# path; jq itself is prereq-checked below, never assumed).

# The first command also turns off the shell options that SHELLOPTS in the environment can turn
# on, that loosened a verdict, and that script code can undo (UD R89): errexit (a failing
# command ended the run with its own exit code, 1 for a failing test or 5 for jq on input it
# cannot parse, which the host treats as non-blocking), keyword (an assignment-shaped argument
# went into a command's environment instead of its arguments), noglob (the scan of the state
# directory found no file) and xtrace (bash expands PS4 in this shell before each traced
# command, so an arithmetic PS4 such as $((tool_name=0)) changed the variables the verdict
# branches on: Sentinel env XT-1). noexec and onecmd act before this command and cannot be
# undone here, and a PS4 is still expanded once, at the trace of this command itself, so a
# command substitution in it runs once (an assignment in it to a variable the ENV-R line below
# resets is undone there, UD R90): with the variables of that line, they are control of the
# hook's environment, disclosed as equal to disableAllHooks. verbose, which only adds denies, is
# left alone (UD R89, D1 of R88); posix, which only added denies too, is turned off as a side
# effect of the ENV-R line's unset of POSIXLY_CORRECT (UD R90).
set -u -o pipefail +o errexit +o noglob +o keyword +o xtrace
# Byte semantics for every path comparison in this hook and in scope-check.sh, which it
# runs (Sentinel W8 r3 FU-R3a; see hooks/scripts/_casefold.sh).
export LC_ALL=C
# Ordinary variables of the hook's environment that bash or jq read and that loosened this
# check are cleared here, as in the state guard and scope-check.sh (UD R88, Sentinel final
# ENV-R): jq sources $HOME/.jq, which can redefine a jq builtin (every deny became an allow);
# bash 4.2 and later stop at a FUNCNEST nesting limit (exit 1, which the host treats as
# non-blocking); bash 5 times out every read of piped data under a TMOUT below one tick (a
# collision check read nothing). Nothing here reads HOME, and no git command runs. What acts
# before this line (BASH_ENV, SHELLOPTS noexec or onecmd, a PS4 command substitution at the
# trace of the first command, exported functions, the bash and jq that PATH finds, DYLD_* or
# LD_PRELOAD) cannot be cleared by script code: that is control of the hook's environment,
# disclosed as equal to disableAllHooks. BASHOPTS is disclosed with it (UD R86), but no shopt
# option it can turn on changed a verdict (one that did would be turned off here).
# The shell-behaviour variables that the environment, or an assignment in that one PS4
# expansion, can set are reset here too (UD R90, Dave xt1 XT-2): GLOBIGNORE (bash 5.2 and 5.3: a
# PS4 ${GLOBIGNORE:=*} made every glob return nothing, so the active-bd scan found no state file and
# collisions were allowed), EXECIGNORE (bash 5: command -v no longer found jq, the missing-jq
# fail-open), CDPATH, POSIXLY_CORRECT and BASH_COMPAT, and IFS is set back to space, tab and
# newline. Unsetting POSIXLY_CORRECT also turns posix mode off, and unsetting GLOBIGNORE turns
# dotglob off; this script uses neither.
unset TMOUT FUNCNEST GLOBIGNORE EXECIGNORE CDPATH POSIXLY_CORRECT BASH_COMPAT; IFS=$' \t\n'; export HOME=/dev/null
# The hook's own clock, for the scope-phase budget (F7-2, see scope_budget_left). bash 3.2
# uses SECONDS, and scope_budget_left reads it as the time since the start. bash takes
# SECONDS from the environment (a negative value there turned the scope-phase budget off, a
# large one denied at once), so it is reset here, at the clock's start (Sentinel U20 F8-2).
# The other clocks only take differences of SECONDS (job 4 here, _sc_over in scope-check.sh),
# which an inherited value cannot move, even across the wrap at the top of its range. bash 5
# ignores an EPOCHREALTIME from the environment.
SECONDS=0
if [ "${BASH_VERSINFO[0]}" -ge 5 ]; then _hook_t0=${EPOCHREALTIME/./}; else _hook_t0=""; fi

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
SCOPE_CHECK="$REPO_ROOT/scripts/scope-check.sh"

# The one literal platform-name string in this repo (bd: shode-house-5cs.4 iter 1, "C1")
# -- this script IS the adapter for it, so naming it here is correct and expected; the
# core (scope-check.sh) must never contain this literal (grep-enforced by
# the maintainer suite test-scope-check.sh).
PLATFORM_NAME="claude"

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
state_dir="$proj/.shode-house/state"
scope_dir="$proj/.shode-house/scope"
degraded="$state_dir/.degraded"
audit_log_file="$state_dir/.scope-audit.log"

# 1) Engagement guard. Without .shode-house/state only the ux path set (job 3) and the git
#    directory rule (job 4) run. In that "ux_only" mode the guard reads stdin and parses it
#    with jq (never a raw-JSON substring match, Hook Charter Sec 6 item 8); any tool call
#    that is not a Write/Edit/NotebookEdit exits 0 silently, and a missing jq fails open
#    silently (there is no state dir to record .degraded in).
ux_only=0
if [ ! -e "$state_dir" ]; then
  command -v jq >/dev/null 2>&1 || exit 0
  ux_only=1
fi

# 2) jq prereq -- fail OPEN + degrade LOUDLY (ADR-C3/C8, same pattern as
#    guard-state-write.sh's own fallback).
if ! command -v jq >/dev/null 2>&1; then
  printf '%s guard-scope-write.sh: jq missing on PATH -- guard running fail-open (scope writes are NOT protected)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$degraded" 2>/dev/null
  exit 0
fi

# 3) The shared case fold. It ships next to this file; when it cannot be loaded the
#    install is broken, and the guard fails OPEN like a missing jq (it must not brick every
#    write), recorded in .degraded when the project has an engagement.
# shellcheck source=_casefold.sh
if ! . "$SELF_DIR/_casefold.sh" 2>/dev/null; then
  [ "$ux_only" -eq 1 ] || printf '%s guard-scope-write.sh: _casefold.sh missing next to the hook -- guard running fail-open (scope, ux and .git writes are NOT protected)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$degraded" 2>/dev/null
  exit 0
fi
_scope_folded=""   # set by _scope_fold / _scope_fold_deny (_casefold.sh)
_scope_rel=""      # set by _scope_strip_root (_casefold.sh)

encode_bd() { printf '%s' "$1" | sed 's#/#--#g'; }

# deny_unjudgeable_input <jq-status> -- the one check for hook input that jq cannot parse or
# evaluate (the Hook Charter Sec 7 exception in the header): returns when the status is 0,
# exits 0 when stdin was empty (nothing to judge), and otherwise DENIES with a static
# message that never echoes the payload.
deny_unjudgeable_input() {
  [ "$1" -eq 0 ] && return 0
  [ -n "$input" ] || exit 0
  printf 'shode-house: DENY (malformed/unsupported hook input) -- jq could not parse or evaluate this hook input (malformed JSON, an escape jq rejects such as a lone UTF-16 surrogate, a tool_input that is not an object, or a jq built without regex support), so the scope, designer and git-directory checks cannot judge it; this write guard refuses instead of allowing (scope guard; applies only where hooks execute)\n' >&2
  exit 2
}

# F7-2 (UD U20, Sentinel r7 F7-2): the time budget of the scope phase -- the outsider and
# ownership evaluation: finding the active bds, looking up bindings, and every scope-check.sh
# call. Its cost grows with the manifests (scope-check.sh's own budget note), and a hook cut
# off by the 5 s timeout lets the write through (job 4's premise, below), so the phase ends
# by _SCOPE_MAX_MS after the hook started, allowed or DENIED. Before each step the guard
# takes what is left: nothing left -> DENY (scope_budget_deny, static message, exit 2);
# otherwise each scope-check.sh call gets it as SCOPECHECK_BUDGET_MS and denies itself when
# its own clock passes it. An ordinary write spends 0.1-0.2 s here. bash 5: microsecond
# clock, so the phase ends at about 3 s. bash 3.2 has whole seconds only: SECONDS steps at
# each wall-clock second, so it reads 1 as little as a moment after the start and can lag
# the real time by up to 1 s. So 1 s is held back: a step starts only while SECONDS is 0 or 1,
# a call gets 2000 or 1000 ms and stops within 3 or 2 s of its own start (scope-check.sh
# counts its own whole seconds the same way), and the phase ends between about 1 s and about
# 4 s after the hook starts (Chris U20 L-1: an aligned run measured 3.85 s; an early end
# is a deny, never an allow). Job 4 runs first, under its own budget.
_SCOPE_MAX_MS=3000
_scope_ms_left=0
# scope_budget_left -- sets _scope_ms_left (ms) and returns 0 while time is left, 1 otherwise.
scope_budget_left() {
  if [ -n "$_hook_t0" ]; then
    _scope_ms_left=$(( _SCOPE_MAX_MS - (${EPOCHREALTIME/./} - _hook_t0) / 1000 ))
  else
    _scope_ms_left=$(( (_SCOPE_MAX_MS / 1000 - 1 - SECONDS) * 1000 ))
  fi
  [ "$_scope_ms_left" -gt 0 ]
}
scope_budget_deny() {
  printf 'shode-house: DENY (scope-budget) -- the scope check of this write ran past its time budget (the scope phase of a hook call ends 3 seconds after the hook starts), so it is refused rather than allowed: a check cut off by the 5 s hook timeout would let the write through (scope guard; applies only where hooks execute)\n' >&2
  exit 2
}

# ---- canon_and_check_write_target: bd: shode-house-5cs.4 iter 2, "C1" (Chris) + H1
# (Quinn). Chris reproduced traversal (".shode-house/../src/payment/evil.ts"), dot-slash
# ("src/./payment/evil2.ts") and case (macOS APFS default case-insensitive,
# "SRC/PAYMENT/evil3.ts") all silently ALLOWing into a path that physically collides with
# an active agent's owns/allowed_roots -- because handle_write_edit's old `rel` computation
# only stripped a literal "$proj/" prefix, no lexical normalize, no physical/symlink
# resolve, no case-fold. This reuses hooks/scripts/guard-state-write.sh's own lexnorm +
# physical-resolve + case-fold approach (that file's header explains why the lexical pass
# MUST run before any existence check), rather than inventing a second technique.
#
# Additionally closes Quinn's H1: a symlink LEAF (the write's own file_path resolves to an
# EXISTING symlink, e.g. one self-amended inside an agent's own allowed_roots that actually
# points at a different agent's exclusively-owned file) is REFUSED outright, not silently
# resolved-and-matched -- physical-resolve (phase B below) only ever follows symlinks in the
# path's ANCESTOR directories (that is what `cd ... && pwd -P` does), never the final
# component itself, and trying to chase a possibly-multi-hop leaf symlink ourselves would
# just add a second TOCTOU window between "resolve" and "the real Write actually happens".
# Refusing is the safe, simple answer; resolving cleverly is not required to close H1.
#
# Prints the canonical, project-relative, case-folded path on stdout and returns 0, OR
# prints nothing and returns 1 if the write target is (or is reached only through) a
# symlink, or cannot be resolved physically (W8 iter 4: a ".." that removes a symlink, or
# no existing parent directory within 64 levels) -- the caller must treat return 1 as an
# unconditional DENY, never a fail-open.
canon_and_check_write_target() {
  local file_path="$1" abs dir rest depth=0 real_dir real groot

  if [ -L "$file_path" ]; then
    return 1
  fi

  case "$file_path" in
    /*) abs="$file_path" ;;
    *)  abs="$proj/$file_path" ;;
  esac
  # W8 iter 4 (Sentinel N2): lexnorm below drops "x/.." before anything is resolved, but the
  # kernel resolves "x" first. When "x" is a symlink, "x/.." is the parent of its TARGET, so
  # the guard would judge a different path than the one written. Refuse that form.
  case "/$abs/" in
    */../*) _scope_dotdot_pops_symlink "$abs" && return 1 ;;
  esac
  abs=$(_scope_lexnorm "$abs")

  # W8 iter 2 (Sentinel B1): the raw-path test above is not enough. `[ -L "x/" ]` and
  # `[ -L "x/." ]` follow the link, so a trailing "/", "/.", "//" or "/./" hid a symlink
  # leaf until lexnorm stripped the suffix. Test the NORMALISED leaf again, here.
  if [ -L "$abs" ]; then
    return 1
  fi

  dir=$(dirname "$abs"); rest=$(basename "$abs")
  while [ ! -d "$dir" ] && [ "$dir" != "/" ] && [ "$depth" -lt 64 ]; do
    # A component that is not a directory but IS a symlink (dangling, or pointing at a
    # file) cannot be resolved by `pwd -P` below; refuse it instead of re-appending it
    # unresolved. Symlinked ancestors that are directories are resolved physically.
    if [ -L "$dir" ]; then
      return 1
    fi
    rest="$(basename "$dir")/$rest"
    dir=$(dirname "$dir")
    depth=$((depth + 1))
  done
  # W8 iter 4 (Sentinel N1): fail closed. The walk can stop on a prefix that still does not
  # exist (more than 64 not-yet-existing components), and `cd` can fail; using the lexical
  # prefix as if it were physical would leave a symlinked ancestor above it unresolved.
  [ -d "$dir" ] || return 1
  real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || return 1
  real="$real_dir/$rest"

  groot=$(cd "$proj" 2>/dev/null && pwd -P) || groot="$proj"
  # Router R78 / Sentinel pre-release r2 F-1: the project root spelled in another case (or
  # any spelling the filesystem treats as the same directory) is still the project root,
  # so the manifest rule and the outsider policy below see a project-relative path.
  _scope_strip_root "$real" "$groot"; real=$_scope_rel
  # NOTE: deliberately NOT case-folded here (unlike an earlier version of this function) --
  # this "rel" value flows into DENY messages and the audit log (see handle_write_edit /
  # apply_outsider_policy), and folding it here would permanently lowercase "README.md" to
  # "readme.md" everywhere an operator reads it. The case-insensitivity guarantee (T4) does
  # NOT depend on this -- it lives in scripts/scope-check.sh's path_matches(), which folds
  # BOTH the candidate and the manifest pattern at comparison time, on every filesystem,
  # every single call. This function only needs to return a lexically-normalized,
  # physically-resolved (symlink-ancestor-free), real-cased, project-relative path.
  printf '%s' "$real"
  return 0
}

_scope_lexnorm() {
  local p="$1" seg out="" oldifs="$IFS" had_noglob=0
  # Chris W8 r3 S1: restore the caller's noglob state, as _scope_dotdot_pops_symlink does.
  case $- in *f*) had_noglob=1 ;; esac
  IFS=/
  set -f
  # shellcheck disable=SC2086
  set -- $p
  [ "$had_noglob" -eq 1 ] || set +f
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

# _scope_dotdot_pops_symlink <abs> -- returns 0 when a ".." segment of <abs> removes a
# component that is a symlink (tested on the lexical prefix, before lexnorm), else 1.
# A ".." that removes a real directory is safe: the remaining prefix is still resolved
# physically by canon_and_check_write_target afterwards.
_scope_dotdot_pops_symlink() {
  local p="$1" seg acc="" oldifs="$IFS" had_noglob=0
  case $- in *f*) had_noglob=1 ;; esac
  IFS=/
  set -f
  # shellcheck disable=SC2086
  set -- $p
  [ "$had_noglob" -eq 1 ] || set +f
  IFS="$oldifs"
  for seg in "$@"; do
    case "$seg" in
      ""|".") ;;
      "..") [ -n "$acc" ] && [ -L "$acc" ] && return 0; acc="${acc%/*}" ;;
      *)    acc="$acc/$seg" ;;
    esac
  done
  return 1
}

# =============================================================================
# Job 4 (UD U6): git directories. This runs on every Write in every project, so parent
# paths are taken with parameter expansion, never with dirname/basename processes.
# =============================================================================

# _git_up <abs> -- sets _git_parent_dir to the parent of an absolute path ("/" for a
# top-level entry). A variable, not stdout, so no subshell is spawned per ancestor.
_git_up() {
  _git_parent_dir="${1%/*}"
  [ -n "$_git_parent_dir" ] || _git_parent_dir=/
}

# Bounds of job 4. One resolution follows at most _GIT_MAX_LINKS symlinks IN TOTAL (Linux
# MAXSYMLINKS; the macOS kernel stops at 32), however they nest (Chris pre-release r3 R3-1),
# and at most _GIT_MAX_NEW not-yet-existing directory levels above the file (the file is not a
# level: the same bound as job 1's walk; Chris r4 R4-5). A lookup is a stat of the whole path
# string resolved so far: past PATH_MAX bytes that stat fails (ENAMETOOLONG) and would read
# as "does not exist", while the kernel, which walks one component at a time, still follows
# a symlink there (Sentinel pre-release r4 R4-1). The smallest PATH_MAX of the supported
# hosts (macOS 1024 with its NUL, Linux 4096) bounds every lookup, so no lookup is longer
# than _GIT_MAX_PATH bytes; a longer one is refused.
_GIT_MAX_LINKS=40
_GIT_MAX_NEW=64
_GIT_MAX_PATH=1023
# The work budget of ONE job-4 check (round 5: Chris r4 R4-2/R4-3, Sentinel r4 R4-T). The
# hook has 5 s (hooks/hooks.json), and a hook cut off by the timeout lets the write through,
# so every check must end, allowed or denied, well inside it. Above any limit the check
# stops at once and denies (fail closed):
#   _GIT_MAX_STEPS     path steps: components read by the resolver (both readings; a link
#                      target's components are charged when queued), ancestors probed
#                      for a .git entry, and directory-identity comparisons (e);
#   _GIT_MAX_POINTERS  .git files or .git symlinks read (each one costs process starts);
#   _GIT_MAX_MS        wall time of the check (bash 5: microsecond clock; bash 3.2 has
#                      whole seconds only, so it stops between 2 and 3 s).
#   _GIT_MAX_LINE      bytes of the one line read from a .git file or a commondir file:
#                      "gitdir: " (8), a value no longer than a lookup (_GIT_MAX_PATH) and
#                      32 bytes for a CR and trailing blanks. The read itself stops one byte
#                      past it, so a longer line (or a huge file) is refused without being
#                      read in full or trimmed (Sentinel pre-release r5 S5-1, FU5-3).
# An ordinary write takes a few dozen steps and 0-3 pointer files. The limits leave room for
# paths of the longest length a lookup may have. The slowest input constructed so far takes
# about 1.4 s as a whole-hook call on macOS (16 .git files naming 96 non-ASCII upper-case
# git dirs, whose case folds are not charged: Chris r5 R5-4); the 2 s clock bounds it. The
# hook suite times the other known adversarial shapes as whole-hook calls.
_GIT_MAX_STEPS=4096
_GIT_MAX_POINTERS=16
_GIT_MAX_MS=2000
_GIT_MAX_LINE=1063

# _git_budget_start -- starts the budget of one job-4 check (steps, pointer files, clock).
_git_budget_start() {
  _git_steps=0; _git_ptrs=0; _git_why=""
  if [ "${BASH_VERSINFO[0]}" -ge 5 ]; then
    _git_clock=us; _git_t0=${EPOCHREALTIME/./}
  else
    _git_clock=s; _git_t0=$SECONDS
  fi
}

# _git_time_up -- returns 0 (and sets _git_why=time) once the check has run past _GIT_MAX_MS.
_git_time_up() {
  if [ "$_git_clock" = us ]; then
    [ $(( ${EPOCHREALTIME/./} - _git_t0 )) -gt $(( _GIT_MAX_MS * 1000 )) ] || return 1
  else
    [ $(( SECONDS - _git_t0 )) -gt $(( _GIT_MAX_MS / 1000 )) ] || return 1
  fi
  _git_why="time"
}

# _git_step [n] -- charges n (default 1) path steps; returns 1 (and sets _git_why) when the
# budget is spent. The clock is read each time the count passes a multiple of 64.
_git_step() {
  local old="$_git_steps"
  _git_steps=$(( old + ${1:-1} ))
  [ "$_git_steps" -le "$_GIT_MAX_STEPS" ] || { _git_why=steps; return 1; }
  [ $(( old >> 6 )) -eq $(( _git_steps >> 6 )) ] || ! _git_time_up
}

# _git_physical_target <abs> -- sets _git_phys to the physical, normalised path that a write
# to <abs> lands on, resolved the way the kernel resolves a path (and `mkdir -p` then open()
# for the part that does not exist yet). One queue of pending components, read left to
# right:
#   - ""  and "." are dropped (so a trailing "/" or "/." is too: a host may drop them);
#   - ".." removes the last component of the path resolved so far, which never contains
#     a symlink, so it is the parent of a link's TARGET, not of the link (Sentinel
#     pre-release B1 / r2 B1-R);
#   - a name that is a symlink (the leaf too, dangling or not) is replaced by its target,
#     read byte for byte (a target may end in a newline: Chris r4 R4-1): the target's
#     components go to the FRONT of the queue (an absolute target restarts from "/");
#     every link followed counts against ONE limit for the whole resolution;
#   - a name that does not exist starts the not-yet-existing tail; until a ".." brings
#     the walk back, nothing below it is looked up.
# The queue is the function's positional parameters: each path or link target is split at
# "/" once, and a link's components are put in front with one `set --`, which copies the
# queue. The work is linear in the components read, plus one queue copy per link followed
# (at most _GIT_MAX_LINKS); both are charged to the job-4 budget (the components read, and
# the queue length after each link), so a link whose target names other links many times
# over (r3 R3-1 fan-out) or a long target placed in front (r4 R4-3) cannot multiply it.
# Called in the current shell (no subshell), so the budget carries over between readings.
# Returns 1 (the caller denies: fail closed; _git_why says why) when the target cannot be
# established: more than _GIT_MAX_LINKS symlinks followed (a loop, a long chain, or a
# fan-out), a link that cannot be read or is empty, more than _GIT_MAX_NEW not-yet-existing
# levels, a lookup longer than _GIT_MAX_PATH bytes, or an existing directory that cannot be
# searched (its entries cannot be looked up) -- or when the budget is spent.
_git_physical_target() {
  local cur="" c nxt t links=0 new=0 rc=0 n=0 queued oldifs="$IFS" had_noglob=0
  _git_phys=""; _git_why=unresolved
  case $- in *f*) had_noglob=1 ;; esac
  set -f
  IFS=/
  # shellcheck disable=SC2086
  set -- $1
  IFS="$oldifs"
  _git_step "$#" || rc=1
  while [ "$rc" -eq 0 ] && [ "$#" -gt 0 ]; do
    c="$1"; shift
    n=$((n + 1))
    if [ $((n & 63)) -eq 0 ] && _git_time_up; then rc=1; break; fi
    case "$c" in
      ""|.) continue ;;
      ..)
        cur="${cur%/*}"
        [ "$new" -eq 0 ] || new=$((new - 1))
        continue ;;
    esac
    nxt="$cur/$c"
    if [ "$new" -gt 0 ]; then
      # inside the not-yet-existing tail: nothing below a missing name can exist; "new"
      # missing names are now directory levels above this one
      [ "$new" -le "$_GIT_MAX_NEW" ] || { rc=1; break; }
      new=$((new + 1)); cur="$nxt"; continue
    fi
    [ "${#nxt}" -le "$_GIT_MAX_PATH" ] || { rc=1; break; }
    if [ -L "$nxt" ]; then
      links=$((links + 1)); [ "$links" -le "$_GIT_MAX_LINKS" ] || { rc=1; break; }
      # byte-exact: $(...) strips trailing newlines, so a sentinel byte follows the target
      t=$(readlink -n "$nxt" && printf x) || { rc=1; break; }
      t="${t%x}"
      [ -n "$t" ] || { rc=1; break; }
      case "$t" in /*) cur="" ;; esac
      # the target's components go in front of what is left of the queue
      queued=$#
      IFS=/
      # shellcheck disable=SC2086
      set -- $t "$@"
      IFS="$oldifs"
      # every component queued will be read: charge the target's now, so the queue (and
      # the copy the next link makes of it) never outgrows the budget
      _git_step $(( $# - queued )) || { rc=1; break; }
      continue
    fi
    if [ ! -e "$nxt" ]; then
      # a missing name, unless the directory cannot be searched (then it is unknown)
      if [ -d "${cur:-/}" ] && [ ! -x "${cur:-/}" ]; then rc=1; break; fi
      new=1
    fi
    cur="$nxt"
  done
  [ "$had_noglob" -eq 1 ] || set +f
  [ "$rc" -eq 0 ] || return 1
  _git_why=""
  _git_phys="${cur:-/}"
}

# _git_pointer_values <value> -- prints (one per line) the value of a "gitdir:" or
# "commondir" line the way git reads it, with trailing CR/LF removed (a pointer file written
# on Windows ends in CRLF, and `read` keeps the CR: Chris pre-release C2), and, when it
# differs, with every trailing blank removed too (Sentinel pre-release FU-3). An extra
# candidate can only add a deny. The value is at most _GIT_MAX_LINE bytes (the caller's read
# is bounded), and each trim is a fixed number of expansions: the shortest suffix that starts
# at the last character to keep is removed, then that character is put back by length (r5
# S5-1: "${v##*[![:space:]]}", like a loop that removes one character at a time, is
# quadratic in the characters removed).
_git_pointer_values() {
  local v="$1" w h crlf=$'\r\n'
  h="${v%[!"$crlf"]*}"
  if [ "$h" = "$v" ]; then v=""; else v="${v:0:${#h}+1}"; fi
  [ -n "$v" ] || return 0
  printf '%s\n' "$v"
  h="${v%[![:space:]]*}"
  if [ "$h" = "$v" ]; then w=""; else w="${v:0:${#h}+1}"; fi
  [ -n "$w" ] && [ "$w" != "$v" ] && printf '%s\n' "$w"
  return 0
}

# _git_pointer_dir <base> <value> -- prints the physical dir a pointer value names
# (relative values are relative to <base>), or its normalised spelling when it does not
# exist.
_git_pointer_dir() {
  local g="$2" r
  case "$g" in /*) : ;; *) g="$1/$g" ;; esac
  if [ -d "$g" ] && r=$(cd -P "$g" 2>/dev/null && pwd -P); then
    printf '%s\n' "$r"
  else
    _scope_lexnorm "$g"; printf '\n'
  fi
}

# _git_pointed_dirs <physical-dir>... -- for each argument and each of its ancestors A,
# collects in the array _git_gdirs the git dir that "A/.git" names when it is a FILE
# ("gitdir: X", relative to A: worktree, submodule, --separate-git-dir), that dir's
# "commondir" (a worktree's main git dir), and the physical target of "A/.git" when it is a
# symlink. A plain ".git" directory needs no entry: the component rule already covers it.
# An ancestor already walked from an earlier argument ends that argument's walk (the rest
# was walked too). Runs in the current shell and charges the job-4 budget: one step per
# ancestor probed, one pointer per .git file or symlink read. Returns 1 (_git_why set) when
# the budget is spent, when an existing ancestor is too long for its ".git" to be looked
# up (R4-1: the probe would read as "absent"), or when a .git or commondir line is longer
# than _GIT_MAX_LINE bytes (r5 S5-1; see _git_read_line).
_git_pointed_dirs() {
  local a s line gv g c cv walked=""
  _git_gdirs=()
  for s in "$@"; do
    a="$s"
    while :; do
      [ -z "$walked" ] || case "$walked" in *$'\n'"${a%/}/"*) break ;; esac
      _git_step || return 1
      if [ $(( ${#a} + 5 )) -gt "$_GIT_MAX_PATH" ]; then
        [ -e "$a" ] && { _git_why=unresolved; return 1; }
      elif [ -L "$a/.git" ] && [ -d "$a/.git" ]; then
        _git_pointer_read || return 1
        g=$(cd -P "$a/.git" 2>/dev/null && pwd -P) && _git_gdirs+=("$g")
      elif [ -f "$a/.git" ]; then
        _git_pointer_read || return 1
        _git_read_line "$a/.git" || return 1
        line=$_git_line
        case "$line" in
          "gitdir: "?*)
            while IFS= read -r gv; do
              g=$(_git_pointer_dir "$a" "$gv")
              _git_gdirs+=("$g")
              if [ -f "$g/commondir" ]; then
                _git_read_line "$g/commondir" || return 1
                c=$_git_line
                while IFS= read -r cv; do
                  _git_gdirs+=("$(_git_pointer_dir "$g" "$cv")")
                done < <(_git_pointer_values "$c")
              fi
            done < <(_git_pointer_values "${line#gitdir: }")
            ;;
        esac
      fi
      [ "$a" = / ] && break
      _git_up "$a"; a="$_git_parent_dir"
    done
    walked="$walked"$'\n'"${s%/}/"
  done
  return 0
}

# _git_read_line <file> -- sets _git_line to the first line of <file> (a .git file or a
# commondir), reading at most _GIT_MAX_LINE + 2 bytes. The read ends at the first NUL byte
# (-d ''), as git's own reading of the file does (a C string), or after _GIT_MAX_LINE + 2
# bytes (-n), and the line is what precedes the first LF. With LF as the delimiter instead,
# bash 4 and later would skip NUL bytes without counting them and read a file of NULs to its
# end. Returns 1 (_git_why=line: the caller denies) when the line is not ended within
# _GIT_MAX_LINE bytes. A file that cannot be read reads as empty (git cannot read it either).
# NEW-1 (Sentinel pre-release r6): git takes the WHOLE file as the value, removing only
# trailing CR/LF, so "gitdir: st<LF>ore" names the dir "st<LF>ore", not "st". Such a file is
# not emulated: when anything but CR and LF follows the first LF, or the read stopped after
# the first LF without reaching the end of the file (at a NUL byte, or at the read bound),
# this returns 1 with _git_why=multiline and the caller denies. Every pointer git writes is
# one line (and may end in LF or CRLF), so this refuses only hand-made files.
# R82 (UD U21; Chris U21 L-2): git reads the file only up to its first NUL byte, and trims
# CR/LF only at the real end of the file, so for "gitdir: st<CR><NUL>x" it uses "st<CR>",
# while _git_pointer_values drops that CR and compares "st". So a read that stopped at a NUL
# byte with no LF before it, whose text ends in a CR or a blank, also returns 1 with
# _git_why=multiline (deny; git is not emulated). git writes no NUL byte, so this too refuses
# only hand-made files.
_git_read_line() {
  local raw rc crlf=$'\r\n'
  _git_line=""
  [ -r "$1" ] || return 0
  IFS= read -r -d '' -n "$(( _GIT_MAX_LINE + 2 ))" _git_line < "$1" 2>/dev/null; rc=$?
  raw=$_git_line
  _git_line="${_git_line%%$'\n'*}"
  [ "${#_git_line}" -le "$_GIT_MAX_LINE" ] || { _git_why=line; return 1; }
  case "$raw" in
    *$'\n'*)
      raw=${raw#*$'\n'}
      if [ -n "${raw//["$crlf"]/}" ] || [ "$rc" -eq 0 ]; then _git_why=multiline; return 1; fi ;;
    *$'\r'|*[[:blank:]])
      # no LF: rc 0 here means the read stopped at a NUL byte (a read that reached the bound
      # has already stopped above, with reason line)
      if [ "$rc" -eq 0 ]; then _git_why=multiline; return 1; fi ;;
  esac
  return 0
}

# _git_pointer_read -- charges one pointer file; returns 1 (_git_why set) above the limit.
_git_pointer_read() {
  _git_ptrs=$((_git_ptrs + 1))
  [ "$_git_ptrs" -le "$_GIT_MAX_POINTERS" ] || { _git_why=pointers; return 1; }
  ! _git_time_up
}

# git_dir_check <file_path> -- job 4. Exits 2 when the write would land in a git dir, or when
# that cannot be established within the job-4 budget; returns 0 otherwise.
git_dir_check() {
  local file_path="$1" abs lex real real2="" llex lreal lreal2="" parent parent2="" g lg proj_phys a seen
  _git_budget_start
  case "$file_path" in
    /*) abs="$file_path" ;;
    *)  abs="$proj/$file_path" ;;
  esac
  # (a) the lexical reading (a host that normalises ".." before the filesystem call): a
  #     ".git" component after the fold
  lex=$(_scope_lexnorm "$abs"); _scope_fold_deny "$lex"; llex=$_scope_folded
  case "/$llex/" in */.git/*) git_dir_deny ;; esac
  # (b) the physical reading (what the kernel does); fail closed when it is unknown
  _git_physical_target "$abs" || git_dir_deny "$_git_why"
  real=$_git_phys
  _scope_fold_deny "$real"; lreal=$_scope_folded
  case "/$lreal/" in */.git/*) git_dir_deny ;; esac
  # (b2) the physical reading of the lexical path: what a host that normalises ".." first
  #      then writes. It differs from (b) only when the path has a ".." segment, e.g.
  #      "lnk/../gl/config" with lnk a symlink elsewhere and gl a symlink to .git
  #      (Sentinel pre-release B1).
  case "/$abs/" in
    */../*)
      _git_physical_target "$lex" || git_dir_deny "$_git_why"
      real2=$_git_phys
      if [ "$real2" = "$real" ]; then
        real2=""
      else
        _scope_fold_deny "$real2"; lreal2=$_scope_folded
        case "/$lreal2/" in */.git/*) git_dir_deny ;; esac
      fi
      ;;
  esac
  # (c) an existing leaf that is another name of the sibling .git (any filesystem alias)
  _git_up "$real"; parent="$_git_parent_dir"
  if [ -e "$parent/.git" ] && [ "$real" -ef "$parent/.git" ]; then git_dir_deny; fi
  if [ -n "$real2" ]; then
    _git_up "$real2"; parent2="$_git_parent_dir"
    if [ -e "$parent2/.git" ] && [ "$real2" -ef "$parent2/.git" ]; then git_dir_deny; fi
  fi
  # (d) a git dir named by a .git file or symlink above the target or above the project,
  #     compared with every reading
  proj_phys=$(cd -P "$proj" 2>/dev/null && pwd -P) || proj_phys="$proj"
  _git_pointed_dirs "$parent" "$proj_phys" ${parent2:+"$parent2"} || git_dir_deny "$_git_why"
  seen=$'\n'
  for g in ${_git_gdirs[@]+"${_git_gdirs[@]}"}; do
    [ -n "$g" ] && [ "$g" != / ] || continue
    # each git dir once: decoy .git files that all name one dir cost one comparison
    case "$seen" in *$'\n'"$g"$'\n'*) continue ;; esac
    seen="$seen$g"$'\n'
    _scope_fold_deny "$g"; lg=$_scope_folded
    case "$lreal/" in "$lg"/*) git_dir_deny ;; esac
    case "$llex/" in "$lg"/*) git_dir_deny ;; esac
    if [ -n "$lreal2" ]; then
      case "$lreal2/" in "$lg"/*) git_dir_deny ;; esac
    fi
    # (e) identity, not spelling: a name the filesystem treats as the same directory but
    #     the string compare above does not (APFS Unicode normalisation, e.g. an NFD
    #     spelling of an NFC git dir path: Sentinel pre-release r3 B3). Every ancestor is
    #     compared (an alias may sit at another depth: a bind mount, a firmlink); each
    #     comparison is charged to the budget (Chris r4 R4-2).
    if [ -d "$g" ]; then
      for a in "$real" ${real2:+"$real2"}; do
        while [ -n "$a" ] && [ "$a" != / ]; do
          _git_step || git_dir_deny "$_git_why"
          [ "$a" -ef "$g" ] && git_dir_deny
          _git_up "$a"; a="$_git_parent_dir"
        done
      done
    fi
  done
  return 0
}

# git_dir_deny [unresolved|steps|pointers|time|line] -- static message (never echoes the path),
# exit 2.
git_dir_deny() {
  local why=""
  case "${1:-}" in
    unresolved) why=' (and a target that cannot be resolved physically -- more than 40 symlinks followed in one path, a symlink that cannot be read, more than 64 new directory levels, a path longer than 1023 bytes, or a parent that cannot be entered -- is refused, because it cannot be shown to lie outside one)' ;;
    steps)    why=' (and a write whose git-directory check exceeds its work budget -- more than 4096 path steps: components read, .git entries probed and directory comparisons -- is refused, because a check cut off by the 5 s hook timeout would let the write through)' ;;
    pointers) why=' (and a write whose git-directory check exceeds its work budget -- more than 16 .git files or .git symlinks on the paths checked -- is refused, because a check cut off by the 5 s hook timeout would let the write through)' ;;
    time)     why=' (and a write whose git-directory check exceeds its work budget -- more than 2 seconds -- is refused, because a check cut off by the 5 s hook timeout would let the write through)' ;;
    line)     why=' (and a write whose git-directory check meets a .git file or a commondir file whose first line is longer than 1063 bytes, or that cannot be read within that bound, is refused, because the git dir it names cannot be established)' ;;
    multiline) why=' (and a write whose git-directory check meets a .git file or a commondir file with more than one line, or with a CR or a blank right before its first NUL byte -- git reads the whole file up to its first NUL byte as the path of the git dir, line breaks included, and every pointer git writes is one line without NUL bytes -- is refused, because the git dir it names cannot be established)' ;;
  esac
  printf 'shode-house: DENY (git-dir) -- Write/Edit/NotebookEdit into a git directory (.git, .git/**, or the git dir that a .git file points to: worktree, submodule, separate git dir) is never allowed%s; use the git CLI instead (git config, git commit, ...). This guard applies only where hooks execute; a host permissions.deny rule is the protection that holds without hooks\n' "$why" >&2
  exit 2
}

audit_log() {
  # $1=message -- least-privilege write target, same convention as guard-state-write.sh's
  # own ".degraded" (writes only under "$proj/.shode-house/state/", no fixed /tmp path).
  printf '%s guard-scope-write.sh: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$audit_log_file" 2>/dev/null || true
}

# ---- resolve_in_progress_bds: every bd currently tracked whose OWN current_phase status
# is "in_progress" (workflow-state.sh's own definition of "actively being worked on" --
# see that script's cmd_advance). One bd_id per line on stdout; empty if none. Returns 3 when
# the scope-phase budget runs out (F7-2): the caller denies.
resolve_in_progress_bds() {
  local f bd cur status
  for f in "$state_dir"/*.json; do
    [ -e "$f" ] || continue
    scope_budget_left || return 3
    bd=$(jq -r '.bd_id // empty' "$f" 2>/dev/null) || continue
    cur=$(jq -r '.current_phase // empty' "$f" 2>/dev/null) || continue
    [ -n "$bd" ] && [ -n "$cur" ] || continue
    status=$(jq -r --arg p "$cur" '.phases[$p].status // empty' "$f" 2>/dev/null)
    [ "$status" = "in_progress" ] && printf '%s\n' "$bd"
  done
  return 0
}

# =============================================================================
# Bash tool_name -- bind-on-claim recognition (Part 2 + Part 3's security constraint)
# =============================================================================
handle_bash() {
  local input="$1" command
  command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
  deny_unjudgeable_input "$?"   # a tool_input that is not an object (Chris r7 F3, Sentinel r7 F7-3)
  [ -n "$command" ] || exit 0

  # C5 (bash control-plane guard, user ruling "option A" -- bd: shode-house-5cs.4 iter 2):
  # checked FIRST, applying to every Bash command, not just bind attempts -- Write/Edit
  # stay hook-enforced everywhere (see handle_write_edit); every OTHER shell write is
  # deliberately ADVISORY ONLY (the user explicitly rejected building a general
  # write-target parser for Bash -- that is the arms race the ruling calls out by name).
  # This is the ONE narrow exception: deny-if-mentioned over a tiny FIXED path set (the
  # control-plane's own state/journal/scope-manifest storage), regardless of whether the
  # command reads or writes -- not a smarter parser, just a stricter, hard-coded reject
  # list. Never echoes $command back (reflected-injection rule) -- the deny message is
  # 100% static.
  # UD U22 H1 (external review): the list used to need a "/" after each root, so a command that
  # named a root itself passed: "rm -rf .shode-house/state", "mv .shode-house/journal x", a root
  # at the end of the string or before a space, quote, ";", ")" or newline,
  # "./.shode-house//state", "/abs/proj/.shode-house/state". The match now runs on a copy of the
  # command with every line break turned into a space, every run of "/" (and of spaces) squeezed
  # to one and every "/./" dropped, ASCII case ignored
  # (the Write/Edit side folds case too, HT3), and DENIES when it holds
  #   (a) ".shode-house/state", ".shode-house/journal" or ".shode-house/scope" followed by
  #       anything at all -- a look-alike such as ".shode-house/statefoo" is denied too (fail
  #       closed; no sanctioned child of .shode-house starts with these names), or
  #   (b) the parent itself: ".shode-house", ".shode-house/" or ".shode-house/." followed by
  #       the end of a line or by any character that cannot continue a path (not a letter,
  #       digit, ".", "_", "-" or "/"). The parent holds all three roots, so "rm -rf .shode-house",
  #       "mv .shode-house x" or ".shode-house/*" removes or detaches them as surely as naming a
  #       root. Children such as .shode-house/config.yaml, approval/ or side-effects/ and
  #       names such as .shode-house-backup stay allowed.
  #   (c) a ".." segment anywhere after ".shode-house/" (U22 iter 2, Sentinel S2 / Chris M1;
  #       widened in iter 3, Sentinel S7 / Chris N1 / Bella N1): ".shode-house/approval/../state",
  #       "chmod -R 0 .shode-house/approval/..", ".shode-house/a+b/../state",
  #       "'.shode-house/a b/../state'" reach a root through a child. ".." is a spelling of the
  #       path like "//" and "/./", so it is denied whatever the child names hold (any byte:
  #       space, quote, "+", "@", ",", ":", "=", "%", "~", non-ASCII, a line break) and whatever
  #       follows it -- ".shode-house/approval/../config.yaml" too. A ".." segment is two dots
  #       with no letter, digit, ".", "_" or "-" on either side, so it is also seen after a space,
  #       quote or backslash ("cd .shode-house/approval && rm -rf ../state", ".shode-house/a/'..'/x",
  #       ".shode-house/a/\../x"). Fail closed, like the look-alikes in (a): a command that names
  #       ".shode-house/<child>" and ALSO uses ".." after it for something else ("cat
  #       .shode-house/config.yaml && cd ..", "... src/../x") is denied too. A name that only
  #       contains dots (".shode-house/a..b", ".shode-house/approval/..x", "...") is not a ".." segment and
  #       stays allowed. Line breaks are turned into spaces before the match, so a name or a
  #       command split over lines is judged as one line.
  # Still deny-if-mentioned over the same fixed names, not a parser: a name spliced with quotes,
  # globs or variables (".sho''de-house/state", ".shode-house/st*", "$D/state") is not seen,
  # nor are the two dots of ".." themselves spliced (".shode-house/a/.''./state", "./.\./"),
  # a ".." reached through a glob, a brace (".shode-house/a/.{.,x}/state") or a variable, a ".."
  # written BEFORE the mention that runs after a "cd" in the same command (for example a function
  # body, a trap or a loop: "trap 'chmod -R 0 ..' EXIT; cd .shode-house/approval"), a symlink
  # planted under .shode-house/ ("ln -s .. .shode-house/approval/l"), or a ".." in a later,
  # separate Bash call after "cd" -- the same ceiling as before (references/scope-lock.md
  # "Enforcement ceiling").
  # Cost: the case pre-filter below needs no process; only a command that holds "hode-house"
  # in any ASCII case starts the one linear pipeline (pure-bash substitution is quadratic on a
  # large command and could run into the 5 s hook timeout, which lets the call through). A
  # pipeline status other than "grep matched" or "grep read everything and found nothing" is a
  # DENY: the check could not judge the command.
  case "$command" in
    *[Hh][Oo][Dd][Ee]-[Hh][Oo][Uu][Ss][Ee]*)
      printf '%s\n' "$command" | tr -s '/\n' '/ ' | sed -e ':a' -e 's#/\./#/#g' -e 'ta' \
        | grep -iqE '\.shode-house/(state|journal|scope)|\.shode-house(/\.?)?([^A-Za-z0-9._/-]|$)|\.shode-house/(.*[^A-Za-z0-9._-])?\.\.([^A-Za-z0-9._-]|$)'
      _c5_status="${PIPESTATUS[*]}"
      if [ "$_c5_status" != "0 0 0 1" ]; then
        printf 'shode-house: DENY -- Bash command mentions a control-plane path (.shode-house/state, .shode-house/journal, or .shode-house/scope -- the scope manifest/binding store -- with or without a trailing slash, or the .shode-house directory itself, which holds all three, or a ".." path segment anywhere after ".shode-house/" in the same command). These fixed paths are hard-denied via Bash regardless of read/write intent; every other shell write stays ADVISORY-ONLY (not tool-enforced) by design -- see references/scope-lock.md "Enforcement ceiling". Use scripts/workflow-state.sh / scripts/scope-check.sh instead (both take the shared lock and are the only sanctioned mutators of these paths); to put the directory name into a file such as .gitignore, use the Edit tool.\n' >&2
        exit 2
      fi
      ;;
  esac

  # (i) cheap pre-filter -- only even look further at commands that mention both tokens.
  case "$command" in
    *'scope-check.sh'*'--bind'*) : ;;
    *) exit 0 ;;
  esac

  # (ii) unconditional metachar reject, BEFORE any shape parsing -- this is the actual
  # security boundary (see header comment). bd: shode-house-5cs.4 iter 2, "C2" (Chris) --
  # newline/tab/CR added to this list: POSIX [[:space:]] (used by the OLD version of the
  # anchored regex below) matches those too, so a MULTI-LINE command was being recognised
  # as "the exact canonical shape" the header comment claims is enforced, and reached
  # cmd_bind_record for real. A control plane's answer to a parser bug is a STRICTER
  # canonical shape, never a smarter parser (user ruling, same C2) -- so this also rejects
  # outright on ANY embedded newline, before shape parsing, as an explicit second layer
  # (belt + suspenders on top of the literal-space-only regex in (iii)).
  case "$command" in
    *';'*|*'&&'*|*'||'*|*'|'*|*'$('*|*'`'*|*'>'*|*'<'*|*$'\n'*|*$'\t'*|*$'\r'*)
      printf 'shode-house: bind command rejected -- contains a forbidden shell metacharacter (one of ; && || | $( a backtick, a redirect, or an embedded newline/tab/CR). The binding control plane only ever accepts the exact canonical shape: scripts/scope-check.sh <bd-id> <label> --bind\n' >&2
      exit 2
      ;;
  esac

  # (iii) fully-anchored canonical shape, narrow character classes on both tokens.
  # bd: shode-house-5cs.4 iter 2, "C2": the separator is now LITERAL ASCII SPACE ([ ]+),
  # never POSIX [[:space:]]+ -- [[:space:]] matches \n/\t/\v/\f/\r too, which is exactly
  # what let a multi-line command slip through as "canonical" before this fix. A single
  # literal space is the only separator a real single-line invocation of this command
  # would ever contain.
  local bind_re='^scripts/scope-check\.sh[ ]+([A-Za-z0-9][A-Za-z0-9._/-]*)[ ]+([A-Za-z0-9][A-Za-z0-9._#-]*)[ ]+--bind$'
  if [[ ! "$command" =~ $bind_re ]]; then
    # mentions both tokens, no forbidden metachar, but not the exact canonical shape --
    # not recognised as a bind attempt. Let it run un-molested (harmless: scope-check.sh's
    # own cmd_bind is inert, or a plain usage error fires).
    exit 0
  fi
  local bd="${BASH_REMATCH[1]}" label="${BASH_REMATCH[2]}"

  local agent_id role
  agent_id=$(printf '%s' "$input" | jq -r '.agent_id // empty' 2>/dev/null)
  if [ -z "$agent_id" ]; then
    printf 'shode-house: bind attempted from a context with no agent_id -- only a subagent has one (PreToolUse omits agent_id for the main session), so the main session cannot bind\n' >&2
    exit 2
  fi
  # agent_type -> role: normalized verbatim, recorded but never used to derive the label
  # (core's rule -- see scope-check.sh's own "bind design" header). L0 probe documents
  # agent_type as present in subagent contexts but does not guarantee every harness
  # version always sets it -- fall back to a literal "unknown" rather than binding with an
  # empty role.
  role=$(printf '%s' "$input" | jq -r '.agent_type // empty' 2>/dev/null)
  [ -n "$role" ] || role="unknown"

  local out rc
  out=$(SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$bd" "$agent_id" "$role" "$label" "$PLATFORM_NAME" --bind-record 2>&1); rc=$?
  if [ "$rc" -eq 0 ]; then
    exit 0
  fi
  printf 'shode-house: %s\n' "$out" >&2
  exit 2
}

# =============================================================================
# Write|Edit tool_name -- scope-check the target path
# =============================================================================
# AGENT-TYPE BRANCHES (SEC-1/SEC-2, v4.0.1): the one greppable list of every `agent_type` value this hook branches on. A roster
# change updates this list and the constant below in the same commit; the maintainer roster test (CI gate #27) reads the `agent-type-branch:`
# lines, asserts each is `shode-house:<id>` of a live agents/<id>.md, that the constant equals the ux entry, and that no other
# `shode-house:<id>` literal is compared in hooks/scripts. A stale value would switch the ux path set OFF without a log line.
#   agent-type-branch: shode-house:design
UX_AGENT_TYPE="shode-house:design"

# ---- ux_path_check <rel>: job 3 (see header). <rel> is canon_and_check_write_target's
# output: project-relative and real-cased, or absolute when the target lies outside the
# project. Exits 2 on a deny; returns 0 when the path is in the ux path set.
ux_path_check() {
  local rel="$1" lrel seg rest
  case "$rel" in
    outputs/?*|design-system/?*) : ;;
    *)
      printf 'shode-house: DENY (ux-path-outside) -- the design agent may write only under outputs/ or design-system/ (scope guard, ux path set; applies only where hooks execute)\n' >&2
      exit 2 ;;
  esac
  case "$rel" in
    *.md|*.json|*.png|*.jpg|*.svg|*.txt|*.log) : ;;
    *)
      printf 'shode-house: DENY (ux-ext) -- the design agent may write only data files (.md .json .png .jpg .svg .txt .log) under outputs/ or design-system/ (scope guard, ux path set; applies only where hooks execute)\n' >&2
      exit 2 ;;
  esac
  # W8 iter 4 (Sentinel N3) and pre-release B2: APFS folds U+017F (long s) to "s", U+212A
  # (Kelvin sign) to "k" and the ligatures / sharp s to their ASCII spelling, so
  # "deſign-run" IS "design-run" and "tsconﬁg.json" IS "tsconfig.json" on disk.
  # _scope_fold_deny maps them, then ASCII (hooks/scripts/_casefold.sh has the list).
  _scope_fold_deny "$rel"; lrel=$_scope_folded
  # Rule 3 (erratum 3 1.10, UD R65 F8): the ux body never creates or edits a manifest,
  # lockfile or tool config. Closed list for 4.0.0, compared on the folded basename; adding
  # a name is a guard change with a test. Other lockfiles (pnpm-lock.yaml, yarn.lock,
  # bun.lockb, bun.lock) already fail the extension rule above.
  case "${lrel##*/}" in
    package.json|composer.json|deno.json|project.json|\
    package-lock.json|npm-shrinkwrap.json|\
    tsconfig.json|tsconfig.*.json|jsconfig.json|jsconfig.*.json|*.config.json|\
    .*)
      printf 'shode-house: DENY (ux-config) -- the design agent never creates or edits a manifest, lockfile or tool config (package.json, composer.json, deno.json, project.json, package-lock.json, npm-shrinkwrap.json, tsconfig*.json, jsconfig*.json, *.config.json, or any name starting with a dot) (scope guard, ux path set; applies only where hooks execute)\n' >&2
      exit 2 ;;
  esac
  case "$lrel" in
    outputs/*)
      rest="${lrel#outputs/}"
      while [ -n "$rest" ]; do
        seg="${rest%%/*}"
        case "$seg" in
          *design-run-order*)
            printf 'shode-house: DENY (ux-order) -- a design-run order is written only by the router; the design agent never writes one (scope guard, ux path set; applies only where hooks execute)\n' >&2
            exit 2 ;;
          design-run)
            printf 'shode-house: DENY (ux-design-run-output) -- outputs/<task>/design-run/ is written only by the design runner (scope guard, ux path set; applies only where hooks execute)\n' >&2
            exit 2 ;;
        esac
        case "$rest" in */*) rest="${rest#*/}" ;; *) rest="" ;; esac
      done
      ;;
  esac
  return 0
}

handle_write_edit() {
  local input="$1" file_path rel agent_type is_ux=0
  # A path holding a line break or another control character is refused before any shell
  # reading of it (Sentinel pre-release r5 S5-2): $(...) drops every trailing newline, so the
  # jobs below would judge "x" while the host opens "x<LF>" (for example a symlink named so,
  # into .git). jq itself tests the decoded string, and prints "C" for such a path or "P"
  # and the path otherwise; only jq's own final newline is then dropped.
  file_path=$(printf '%s' "$input" | jq -r '(.tool_input.file_path // .tool_input.notebook_path // empty)
    | if type == "string" and test("[\u0000-\u001f\u007f-\u009f]") then "C" else "P" + tostring end' 2>/dev/null)
  deny_unjudgeable_input "$?"   # a non-object tool_input, or a jq without regex support
  case "$file_path" in
    C)
      printf 'shode-house: DENY (path-control-char) -- a Write/Edit/NotebookEdit path that contains a line break (LF, CR) or another control character (U+0000-U+001F, U+007F-U+009F) is never allowed: a shell reading of it can differ from the name the filesystem opens, so the scope, designer and git-directory checks cannot judge it (scope guard; applies only where hooks execute)\n' >&2
      exit 2 ;;
    P?*) file_path="${file_path#P}" ;;
    *) exit 0 ;;
  esac
  # job 4 (UD U6) first: every caller, with or without an engagement.
  git_dir_check "$file_path"
  agent_type=$(printf '%s' "$input" | jq -r '.agent_type // empty' 2>/dev/null)
  [ "$agent_type" = "$UX_AGENT_TYPE" ] && is_ux=1
  # ux_only (no engagement): after job 4, nothing but the ux path set is enforced.
  if [ "$ux_only" -eq 1 ] && [ "$is_ux" -eq 0 ]; then
    exit 0
  fi

  # project-relative, same convention scope manifests are authored in (references/scope-lock.md
  # "Files:" field / manifest owns[]/allowed_roots[] patterns are always project-relative) --
  # AND lexically-normalized + physically-resolved + case-folded (bd: shode-house-5cs.4
  # iter 2, "C1"), never a raw "$proj/" prefix-strip. A symlink LEAF is refused outright
  # (Quinn's H1), fail-closed, before any ownership matching is even attempted.
  rel=$(canon_and_check_write_target "$file_path")
  if [ $? -ne 0 ]; then
    printf 'shode-house: DENY -- write target "%s" is (or is reached through) a symlink, or cannot be resolved physically; this guard refuses to resolve through a leaf symlink rather than risk matching the wrong physical file (bd: shode-house-5cs.4 iter 2, "H1")\n' "$file_path" >&2
    exit 2
  fi

  if [ "$is_ux" -eq 1 ]; then
    ux_path_check "$rel"
  fi
  [ "$ux_only" -eq 1 ] && exit 0

  # ---- Bella finding 6 (bd: shode-house-5cs.4) / W3 (bd: shode-house-5cs.8): a
  # Write/Edit whose canonicalized target IS the scope manifest or its binding store
  # (the same file -- `.bindings` lives INSIDE the per-bd manifest JSON, see
  # scripts/scope-check.sh's own "bind design" header) is DENIED outright, regardless of
  # ownership. Same spirit as hooks/scripts/guard-state-write.sh's dedicated protection
  # of .shode-house/{state,journal}/** (that file's own header comment), same
  # canonicalization technique this file ALREADY applies above via
  # canon_and_check_write_target/C1 -- reused, not reinvented, so traversal/dot-slash/
  # case are all already closed by the time $rel reaches this comparison, and a symlink
  # LEAF is refused even earlier by the check just above this one.
  #
  # Checked BEFORE any ownership resolution, on purpose: today, WITHOUT this rule, the
  # manifest is only DENY-by-construction because its own path happens not to sit inside
  # any agent's declared owns[]/allowed_roots[] -- an accident of manifest CONTENT, not
  # an enforced rule. A misconfigured (or maliciously widened) allowed_roots pattern that
  # DOES cover ".shode-house/scope/**" would, without this check, let an agent
  # NEEDS_AMENDMENT/self-amend its way into OWNING the manifest file, then Write it
  # directly -- bypassing scripts/scope-check.sh's own shared lock (bd:shode-house-vz8),
  # atomic-rename, and validation entirely. This check makes the protection unconditional
  # on manifest content: this path is denied regardless of what any agent's
  # owns[]/allowed_roots[] happens to say about it.
  # Case-folded comparison ONLY (never bakes the fold into $rel itself -- same convention
  # canon_and_check_write_target's own header explains: $rel flows into DENY messages and
  # the audit log verbatim, real-cased, everywhere else in this file).
  # W8 iter 4 (Sentinel N3 class): the shared fold maps the long s and the Kelvin sign, as
  # in ux_path_check -- APFS folds ".ſhode-houſe/ſcope" to ".shode-house/scope".
  local mg_lrel
  _scope_fold_deny "$rel"; mg_lrel=$_scope_folded
  case "$mg_lrel" in
    .shode-house/scope|.shode-house/scope/*)
      printf 'shode-house: DENY -- direct write to the scope manifest/binding store (.shode-house/scope/**) is never allowed via Write/Edit, regardless of ownership -- these paths are recorded/mutated ONLY by scripts/scope-check.sh (--amend, --bind, --bind-record), which takes the shared lock (bd:shode-house-vz8) and validates every write; denied outright even if this exact path happens to appear in some agent'"'"'s own owns[]/allowed_roots[]. resolved_path=%s\n' "$rel" >&2
      exit 2
      ;;
  esac

  local agent_id
  agent_id=$(printf '%s' "$input" | jq -r '.agent_id // empty' 2>/dev/null)

  local candidates
  candidates=$(resolve_in_progress_bds) || scope_budget_deny
  [ -n "$candidates" ] || exit 0   # nothing active anywhere -- nothing to enforce

  if [ -z "$agent_id" ]; then
    handle_main_session "$rel" "$candidates"
    return
  fi
  handle_subagent "$agent_id" "$rel" "$candidates"
}

# ---- scope_check_rc_deny: an exit code of scope-check.sh that is not one of its documented
# results for the call -- a crash, a signal (128+n), 126/127, or an error that ends it some
# other way -- is a DENY on every path here, never an allow (UD R88, Sentinel final FU-F1;
# before, the outsider policy read anything but 1 and 64 as "no collision", and the subagent
# path had `*) exit 0`). The message is static apart from the number, the bd id and the
# guard's own context text.
#   $1=rc $2=bd $3=the documented codes of the call $4=context $5=rel
scope_check_rc_deny() {
  printf 'shode-house: DENY -- scope-check.sh ended with exit code %s for bd "%s", which is not one of its results for this check (%s): it crashed, was killed or failed in a way it does not report, so this write cannot be judged -- failing CLOSED rather than allowing it (%s)\n' "$1" "$2" "$3" "$4" >&2
  audit_log "scope-check DENY (unexpected exit $1, NOT a clean allow) -- bd \"$2\" ($4): $5"
  exit 2
}

# ---- apply_outsider_policy: THE single policy for every write this guard cannot resolve
# to exactly one bound (bd, label) pair -- main session (no agent_id at all), an unbound
# instance_id in the one active bd it could resolve to, or an instance_id bound
# ambiguously (zero or more than one) across simultaneously-active bds (bd:
# shode-house-5cs.4 iter 1, "C2" -- the user ruling calls this "the outsider policy",
# explicitly identical for all three cases): a write inside ANY of the given candidate
# bds' declared owns/allowed_roots/shared_files is DENIED; a write outside every one of
# them is ALLOWED + one audit log line. Never fails open on a path actually inside active
# scope -- that was the C2 hole (an agent evading scope simply by never binding).
#   $1=rel (project-relative path)  $2=candidates (one bd-id per line, checked against ALL
#   of them, same "any collision anywhere DENIES" rule as the pre-C2 main-session policy)
#   $3=context (free text -- ONLY affects the DENY stderr suffix and the ALLOW audit-log
#   line, never the verdict itself)
apply_outsider_policy() {
  local rel="$1" candidates="$2" context="$3" bd out rc
  while IFS= read -r bd; do
    [ -z "$bd" ] && continue
    scope_budget_left || scope_budget_deny
    out=$(SCOPECHECK_BUDGET_MS="$_scope_ms_left" SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$bd" "$rel" --main-check 2>&1); rc=$?
    if [ "$rc" -eq 1 ]; then
      printf 'shode-house: %s (outsider policy: %s)\n' "$out" "$context" >&2
      exit 2
    fi
    if [ "$rc" -eq 64 ]; then
      # bd: shode-house-5cs.4 iter 2, "C3" (Chris + Quinn H2): a corrupt/unreadable
      # manifest used to fall into the same catch-all as a genuinely missing one and ALLOW
      # silently -- indistinguishable in the audit log from a real "nothing collided" pass.
      # This bd's whole purpose is fail-CLOSED without bricking writes, and "we could not
      # even read whether this collides" is not the same claim as "we checked and it does
      # not collide" -- treat it as if it collided (DENY) and log a message an operator can
      # actually tell apart from a clean ALLOW.
      printf 'shode-house: DENY -- scope manifest for bd "%s" is corrupt/unreadable (scope-check.sh exit 64) -- failing CLOSED rather than silently allowing a write whose collision with that bd'"'"'s active scope could not be checked (outsider policy: %s). Ask the router to repair or regenerate the manifest.\n' "$bd" "$context" >&2
      audit_log "outsider policy DENY (corrupt-manifest, NOT a clean allow) -- bd \"$bd\" manifest unreadable, failing closed for: $rel"
      exit 2
    fi
    # Only 0 means "no collision with this bd" (FU-F1): any other code denies.
    [ "$rc" -eq 0 ] || scope_check_rc_deny "$rc" "$bd" "0 no collision, 1 collision, 64 unreadable manifest" "outsider policy: $context" "$rel"
  done <<<"$candidates"
  audit_log "outsider policy ALLOW ($context) -- write outside all active scope (checked $(printf '%s' "$candidates" | grep -c .) active bd(s)): $rel"
  exit 0
}

# ---- main session: Part 3's "NOT blanket-exempt" rule -- one case of the outsider policy.
handle_main_session() {
  local rel="$1" candidates="$2"
  apply_outsider_policy "$rel" "$candidates" "main session (no agent_id)"
}

# ---- subagent: resolve which bd's manifest applies (via its agent_id binding when more
# than one bd is simultaneously in_progress), then which label it is bound to, then the
# ordinary ownership check under that label. An instance_id that cannot be resolved to
# exactly one bound label -- because it never bound anywhere, or because it is bound
# ambiguously across more than one active bd -- is an "outsider" (C2) and gets the
# identical policy the main session gets, checked against every candidate bd, NOT just the
# one it happened to be ambiguous in.
handle_subagent() {
  local agent_id="$1" rel="$2" candidates="$3"
  local n_candidates resolved="" bd mf match_count=0

  n_candidates=$(printf '%s\n' "$candidates" | grep -c .)
  if [ "$n_candidates" -eq 1 ]; then
    resolved=$(printf '%s' "$candidates" | head -1)
  else
    while IFS= read -r bd; do
      [ -z "$bd" ] && continue
      scope_budget_left || scope_budget_deny
      mf="$scope_dir/$(encode_bd "$bd").json"
      [ -f "$mf" ] || continue
      if jq -e --arg a "$agent_id" '.bindings // {} | has($a)' "$mf" >/dev/null 2>&1; then
        resolved="$bd"; match_count=$((match_count + 1))
      fi
    done <<<"$candidates"
    if [ "$match_count" -ne 1 ]; then
      # genuinely ambiguous (0 or >1 bd manifests already know this instance_id) -- cannot
      # safely resolve which single manifest+label applies. C2: this is NOT a fail-open --
      # apply the outsider policy against every candidate, exactly like the main session.
      apply_outsider_policy "$rel" "$candidates" \
        "instance_id bound in $match_count of $n_candidates active bd(s) -- ambiguous, cannot resolve a single label"
      return
    fi
  fi

  mf="$scope_dir/$(encode_bd "$resolved").json"
  [ -f "$mf" ] || exit 0   # no manifest for the resolved bd -- nothing to enforce

  # bd: shode-house-5cs.4 iter 2 -- resolve the label through scope-check.sh's own
  # --resolve-binding instead of this file reading `.bindings[$a].label` directly. Bella's
  # review found the direct-jq-read version bypassed bindings_shape_ok_or_die entirely: an
  # old-shape `.bindings[$a]` is a bare STRING, `.label` on a string is a jq type error, the
  # `2>/dev/null` here swallowed it, and an empty $label silently misrouted a legitimately-
  # bound subagent into the outsider policy -- DENYing its own file writes with a generic
  # "not bound" message instead of the clear exit-64 explanation. Routing through the core
  # means there is exactly ONE shape guard, applied uniformly, not two (one real, one
  # accidentally bypassable).
  local rb_out rb_rc label=""
  scope_budget_left || scope_budget_deny
  rb_out=$(SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$resolved" "$agent_id" --resolve-binding 2>&1); rb_rc=$?
  case "$rb_rc" in
    0) label="${rb_out#BOUND: }" ;;
    1) : ;;   # NOT_BOUND -- fall through to the outsider-policy branch below, unchanged
    2) exit 0 ;;   # NO_MANIFEST -- manifest vanished between the `[ -f "$mf" ]` check above and now; fail open, our own tooling race
    64)
      # C3: corrupt/old-shape manifest -- fail CLOSED, not open, and say so distinguishably
      # (this is the exact stranding bug Bella traced: previously this surfaced as a
      # misleading generic outsider-policy DENY with no mention of exit 64 at all).
      printf 'shode-house: DENY -- scope manifest for bd "%s" cannot be read for binding resolution (scope-check.sh exit 64: %s) -- failing CLOSED rather than guessing whether instance_id "%s" is bound. Ask the router to repair or regenerate the manifest (see scope-check.sh --resolve-binding output above for the exact cause).\n' "$resolved" "$rb_out" "$agent_id" >&2
      audit_log "subagent binding-resolution DENY (corrupt/old-shape manifest, NOT an outsider) -- bd \"$resolved\" agent_id \"$agent_id\": $rel"
      exit 2
      ;;
    *) scope_check_rc_deny "$rb_rc" "$resolved" "0 bound, 1 not bound, 2 no manifest, 64 unreadable manifest" "subagent binding resolution" "$rel" ;;   # FU-F1
  esac

  if [ -z "$label" ]; then
    # C2: an instance_id that has never bound in the one bd it resolved to is ALSO an
    # outsider -- not an automatic DENY (that would brick a reviewer writing under
    # outputs/, which no manifest claims) and not a fail-open either. Apply the identical
    # outsider policy, scoped to just this one resolved bd (the only candidate it could
    # possibly mean).
    apply_outsider_policy "$rel" "$resolved" \
      "instance_id not bound to any label for bd \"$resolved\" yet -- run scripts/scope-check.sh $resolved <your-label> --bind first"
    return
  fi

  local out rc
  scope_budget_left || scope_budget_deny
  out=$(SCOPECHECK_BUDGET_MS="$_scope_ms_left" SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$resolved" "$label" "$rel" 2>&1); rc=$?
  case "$rc" in
    0) exit 0 ;;
    1|4) printf 'shode-house: %s\n' "$out" >&2; exit 2 ;;
    2) exit 0 ;;   # NO_MANIFEST -- our own tooling race, fail open
    64)
      # C3: corrupt manifest at ownership-check time -- fail CLOSED with a distinguishable
      # audit line, same policy as apply_outsider_policy's own rc=64 branch above.
      printf 'shode-house: DENY -- scope manifest for bd "%s" is corrupt/unreadable (scope-check.sh exit 64: %s) -- failing CLOSED rather than silently allowing a write whose ownership could not be checked. Ask the router to repair or regenerate the manifest.\n' "$resolved" "$out" >&2
      audit_log "subagent ownership-check DENY (corrupt-manifest, NOT a clean allow) -- bd \"$resolved\" label \"$label\": $rel"
      exit 2
      ;;
    *) scope_check_rc_deny "$rc" "$resolved" "0 allow, 1 or 4 deny, 2 no manifest, 64 unreadable manifest" "subagent ownership check" "$rel" ;;   # FU-F1
  esac
}

# =============================================================================
# dispatch
# =============================================================================
input=$(cat)
# One jq call decides the branch, so a call that is not judged exits after a single parse
# (Chris W8 S2). Without an engagement every Write/Edit/NotebookEdit is now judged too: job 4
# applies to every caller (UD U6); job 3 still applies to the designer only.
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // "" | tostring' 2>/dev/null)
deny_unjudgeable_input "$?"   # malformed JSON, a lone surrogate escape, a non-object payload

case "$tool_name" in
  Bash)                    [ "$ux_only" -eq 1 ] && exit 0   # no engagement: only job 3 runs
                           handle_bash "$input" ;;
  Write|Edit|NotebookEdit) handle_write_edit "$input" ;;   # L1 (Quinn/Bella): NotebookEdit
                           # was covered by neither hooks.json's matcher nor this dispatch
                           # -- handle_write_edit already reads .tool_input.notebook_path
                           # as a fallback, so no further change is needed there.
  *)                       exit 0 ;;
esac
