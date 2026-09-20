#!/usr/bin/env bash
# guard-scope-write.sh -- PreToolUse Write|Edit|Bash guard (bd: shode-house-5cs.4, L2)
#
# THE PLATFORM ADAPTER: this script is the one place in the repo allowed to name a
# platform (scripts/scope-check.sh, the core, never does -- see that script's own "bind
# design" header comment, invariant grep-enforced by tests/test-scope-check.sh). It reads
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
# Exit codes -- exit 2 is the ONLY code that blocks (same Hook Charter convention as
# guard-state-write.sh): 2 = DENY, 0 = ALLOW or fail-OPEN. This guard fails OPEN on:
# missing jq, malformed stdin JSON, no active bd found at all, or scope-check.sh returning
# NO_MANIFEST (2) -- a bug in OUR OWN tooling, or a manifest that genuinely does not exist
# yet, must never brick every write in every project (same reasoning as
# guard-state-write.sh's own jq-prereq fallback). It does NOT fail open on an unbound or
# ambiguously-bound instance_id (bd: shode-house-5cs.4 iter 1, "C2" closed that hole -- see
# the outsider policy above), and, as of iter 2 ("C3"), does NOT fail open on scope-check.sh
# returning 64 (a CORRUPT or old-shape manifest) EITHER -- a manifest that exists but cannot
# be read is a materially different failure than one that was never recorded, and gets a
# distinguishable DENY + audit line instead of being silently indistinguishable from a
# clean ALLOW. This guard also fails CLOSED on a Write/Edit target that is (or is reached
# through) a symlink (iter 2, "H1") -- see canon_and_check_write_target -- and on a Bash
# command that mentions a fixed control-plane path regardless of read/write intent (iter 2,
# "C5", user ruling "option A") -- see the top of handle_bash.
#
# Deps: bash (>= 4, for [[ =~ ]] and BASH_REMATCH) + jq (ADR-C3 -- no python3 on the hot
# path; jq itself is prereq-checked below, never assumed).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SELF_DIR/../.." && pwd)"
SCOPE_CHECK="$REPO_ROOT/scripts/scope-check.sh"

# The one literal platform-name string in this repo (bd: shode-house-5cs.4 iter 1, "C1")
# -- this script IS the adapter for it, so naming it here is correct and expected; the
# core (scope-check.sh) must never contain this literal (grep-enforced by
# tests/test-scope-check.sh).
PLATFORM_NAME="claude"

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
state_dir="$proj/.shode-house/state"
scope_dir="$proj/.shode-house/scope"
degraded="$state_dir/.degraded"
audit_log_file="$state_dir/.scope-audit.log"

# 1) Engagement guard -- pure bash, FIRST statement that can exit, before stdin/jq is
#    ever touched (same convention as guard-state-write.sh / scripts/scope-check.sh).
[ -e "$state_dir" ] || exit 0

# 2) jq prereq -- fail OPEN + degrade LOUDLY (ADR-C3/C8, same pattern as
#    guard-state-write.sh's own fallback).
if ! command -v jq >/dev/null 2>&1; then
  printf '%s guard-scope-write.sh: jq missing on PATH -- guard running fail-open (scope writes are NOT protected)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$degraded" 2>/dev/null
  exit 0
fi

encode_bd() { printf '%s' "$1" | sed 's#/#--#g'; }

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
# symlink -- the caller must treat return 1 as an unconditional DENY, never a fail-open.
canon_and_check_write_target() {
  local file_path="$1" abs dir rest depth=0 real_dir real groot

  if [ -L "$file_path" ]; then
    return 1
  fi

  case "$file_path" in
    /*) abs="$file_path" ;;
    *)  abs="$proj/$file_path" ;;
  esac
  abs=$(_scope_lexnorm "$abs")

  dir=$(dirname "$abs"); rest=$(basename "$abs")
  while [ ! -d "$dir" ] && [ "$dir" != "/" ] && [ "$depth" -lt 64 ]; do
    rest="$(basename "$dir")/$rest"
    dir=$(dirname "$dir")
    depth=$((depth + 1))
  done
  real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || real_dir="$dir"
  real="$real_dir/$rest"

  groot=$(cd "$proj" 2>/dev/null && pwd -P) || groot="$proj"
  case "$real" in
    "$groot"/*) real="${real#"$groot"/}" ;;
    "$groot")   real="." ;;
  esac
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

audit_log() {
  # $1=message -- least-privilege write target, same convention as guard-state-write.sh's
  # own ".degraded" (writes only under "$proj/.shode-house/state/", no fixed /tmp path).
  printf '%s guard-scope-write.sh: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$audit_log_file" 2>/dev/null || true
}

# ---- resolve_in_progress_bds: every bd currently tracked whose OWN current_phase status
# is "in_progress" (workflow-state.sh's own definition of "actively being worked on" --
# see that script's cmd_advance). One bd_id per line on stdout; empty if none.
resolve_in_progress_bds() {
  local f bd cur status
  for f in "$state_dir"/*.json; do
    [ -e "$f" ] || continue
    bd=$(jq -r '.bd_id // empty' "$f" 2>/dev/null) || continue
    cur=$(jq -r '.current_phase // empty' "$f" 2>/dev/null) || continue
    [ -n "$bd" ] && [ -n "$cur" ] || continue
    status=$(jq -r --arg p "$cur" '.phases[$p].status // empty' "$f" 2>/dev/null)
    [ "$status" = "in_progress" ] && printf '%s\n' "$bd"
  done
}

# =============================================================================
# Bash tool_name -- bind-on-claim recognition (Part 2 + Part 3's security constraint)
# =============================================================================
handle_bash() {
  local input="$1" command
  command=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
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
  case "$command" in
    *'.shode-house/state/'*|*'.shode-house/journal/'*|*'.shode-house/scope/'*)
      printf 'shode-house: DENY -- Bash command mentions a control-plane path (.shode-house/state/, .shode-house/journal/, or .shode-house/scope/ -- the scope manifest/binding store). These three fixed paths are hard-denied via Bash regardless of read/write intent; every other shell write stays ADVISORY-ONLY (not tool-enforced) by design -- see references/scope-lock.md "Enforcement ceiling". Use scripts/workflow-state.sh / scripts/scope-check.sh instead (both take the shared lock and are the only sanctioned mutators of these paths).\n' >&2
      exit 2
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
handle_write_edit() {
  local input="$1" file_path rel
  file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null)
  [ -n "$file_path" ] || exit 0

  # project-relative, same convention scope manifests are authored in (references/scope-lock.md
  # "Files:" field / manifest owns[]/allowed_roots[] patterns are always project-relative) --
  # AND lexically-normalized + physically-resolved + case-folded (bd: shode-house-5cs.4
  # iter 2, "C1"), never a raw "$proj/" prefix-strip. A symlink LEAF is refused outright
  # (Quinn's H1), fail-closed, before any ownership matching is even attempted.
  rel=$(canon_and_check_write_target "$file_path")
  if [ $? -ne 0 ]; then
    printf 'shode-house: DENY -- write target "%s" is (or is reached through) a symlink; this guard refuses to resolve through a leaf symlink rather than risk matching the wrong physical file (bd: shode-house-5cs.4 iter 2, "H1")\n' "$file_path" >&2
    exit 2
  fi

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
  local mg_lrel; mg_lrel=$(printf '%s' "$rel" | tr '[:upper:]' '[:lower:]')
  case "$mg_lrel" in
    .shode-house/scope|.shode-house/scope/*)
      printf 'shode-house: DENY -- direct write to the scope manifest/binding store (.shode-house/scope/**) is never allowed via Write/Edit, regardless of ownership -- these paths are recorded/mutated ONLY by scripts/scope-check.sh (--amend, --bind, --bind-record), which takes the shared lock (bd:shode-house-vz8) and validates every write; denied outright even if this exact path happens to appear in some agent'"'"'s own owns[]/allowed_roots[]. resolved_path=%s\n' "$rel" >&2
      exit 2
      ;;
  esac

  local agent_id
  agent_id=$(printf '%s' "$input" | jq -r '.agent_id // empty' 2>/dev/null)

  local candidates
  candidates=$(resolve_in_progress_bds)
  [ -n "$candidates" ] || exit 0   # nothing active anywhere -- nothing to enforce

  if [ -z "$agent_id" ]; then
    handle_main_session "$rel" "$candidates"
    return
  fi
  handle_subagent "$agent_id" "$rel" "$candidates"
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
    out=$(SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$bd" "$rel" --main-check 2>&1); rc=$?
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
      printf 'shode-house: DENY -- scope manifest for bd "%s" is corrupt/unreadable (scope-check.sh exit 64) -- failing CLOSED rather than silently allowing a write whose collision with that bd'"'"'s active scope could not be checked (outsider policy: %s). Ask Oliver to repair or regenerate the manifest.\n' "$bd" "$context" >&2
      audit_log "outsider policy DENY (corrupt-manifest, NOT a clean allow) -- bd \"$bd\" manifest unreadable, failing closed for: $rel"
      exit 2
    fi
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
  rb_out=$(SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$resolved" "$agent_id" --resolve-binding 2>&1); rb_rc=$?
  case "$rb_rc" in
    0) label="${rb_out#BOUND: }" ;;
    1) : ;;   # NOT_BOUND -- fall through to the outsider-policy branch below, unchanged
    2) exit 0 ;;   # NO_MANIFEST -- manifest vanished between the `[ -f "$mf" ]` check above and now; fail open, our own tooling race
    64)
      # C3: corrupt/old-shape manifest -- fail CLOSED, not open, and say so distinguishably
      # (this is the exact stranding bug Bella traced: previously this surfaced as a
      # misleading generic outsider-policy DENY with no mention of exit 64 at all).
      printf 'shode-house: DENY -- scope manifest for bd "%s" cannot be read for binding resolution (scope-check.sh exit 64: %s) -- failing CLOSED rather than guessing whether instance_id "%s" is bound. Ask Oliver to repair or regenerate the manifest (see scope-check.sh --resolve-binding output above for the exact cause).\n' "$resolved" "$rb_out" "$agent_id" >&2
      audit_log "subagent binding-resolution DENY (corrupt/old-shape manifest, NOT an outsider) -- bd \"$resolved\" agent_id \"$agent_id\": $rel"
      exit 2
      ;;
    *) exit 0 ;;   # residual unforeseen code -- fail open, our own tooling issue
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
  out=$(SCOPECHECK_ROOT="$proj" "$SCOPE_CHECK" "$resolved" "$label" "$rel" 2>&1); rc=$?
  case "$rc" in
    0) exit 0 ;;
    1|4) printf 'shode-house: %s\n' "$out" >&2; exit 2 ;;
    2) exit 0 ;;   # NO_MANIFEST -- our own tooling race, fail open
    64)
      # C3: corrupt manifest at ownership-check time -- fail CLOSED with a distinguishable
      # audit line, same policy as apply_outsider_policy's own rc=64 branch above.
      printf 'shode-house: DENY -- scope manifest for bd "%s" is corrupt/unreadable (scope-check.sh exit 64: %s) -- failing CLOSED rather than silently allowing a write whose ownership could not be checked. Ask Oliver to repair or regenerate the manifest.\n' "$resolved" "$out" >&2
      audit_log "subagent ownership-check DENY (corrupt-manifest, NOT a clean allow) -- bd \"$resolved\" label \"$label\": $rel"
      exit 2
      ;;
    *) exit 0 ;;   # residual unforeseen code -- fail open, our own tooling issue
  esac
}

# =============================================================================
# dispatch
# =============================================================================
input=$(cat)
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)
rc=$?
[ "$rc" -eq 0 ] || exit 0   # malformed JSON on stdin -- fail open, never block on input we can't parse

case "$tool_name" in
  Bash)                    handle_bash "$input" ;;
  Write|Edit|NotebookEdit) handle_write_edit "$input" ;;   # L1 (Quinn/Bella): NotebookEdit
                           # was covered by neither hooks.json's matcher nor this dispatch
                           # -- handle_write_edit already reads .tool_input.notebook_path
                           # as a fallback, so no further change is needed there.
  *)                       exit 0 ;;
esac
