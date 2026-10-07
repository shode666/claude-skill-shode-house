#!/usr/bin/env bash
# guard-state-write.sh -- PreToolUse Write|Edit guard (bd: shode-roadmap/C-A7)
#
# Denies any Write/Edit tool call whose target resolves under
# "$CLAUDE_PROJECT_DIR/.shode-house/{state,journal}/**". Those files may only be mutated
# by scripts/workflow-state.sh (invoked via Bash: lock -> validate -> journal-append ->
# atomic rename, ADR-C5) -- which never goes through the Write or Edit tool, so this
# guard never needs to special-case "the validator itself".
#
# This REPLACES the spike matcher from commit 441e0fe (`case "$input" in
# *'.shode-house/state/'*)`), which substring-matched the RAW JSON stdin (including the
# `content` field) and was proven at runtime (08-sentinel-threat-model-hooks.md S4) to:
#   - false-positive on any file whose CONTENT mentions the path (T2)
#   - bypass via traversal (T3), case (T4, APFS default case-insensitive), JSON-escaped
#     solidus (T5), and dot-slash (T6)
# Fix: jq-extract the `tool_input.file_path` field ONLY -> canonicalize to a physical,
# symlink-free, absolute path -> case-fold prefix-compare against the guard roots. Never
# substring-match raw JSON again (Hook Charter Sec 6 item 8).
#
# WHERE THIS RUNS: only where hooks execute -- Claude Code with this plugin's
# hooks/hooks.json loaded, not switched off by `disableAllHooks: true`, and registered with
# the plugin root quoted. Not in the generated tree; unconfirmed in Cowork. Defence in
# depth, not a guarantee.
#
# Exit codes -- exit 2 is the ONLY code that blocks (Claude Code docs, quoted in
# 02-sara-adr-1a.md Sec "REQUIRED-BEFORE B"); exit 1 is a NON-BLOCKING pass-through and
# must never be used here (would silently defeat the guard -- a correctness bug, not a
# security one, but treated as equally forbidden by the Hook Charter).
#   2 = DENY (state/journal write blocked)
#   0 = ALLOW, or fail-OPEN (Hook Charter Sec 7 fail matrix: missing jq / empty stdin / no
#       path field never blocks -- blocking every Write in a project that never opted into
#       shode-house, or bricking a session over a missing dependency, is worse than the
#       guard occasionally missing a case that the journal-replay net (Stop / SessionStart
#       torn-write check) still catches)
#   Hook Charter Sec 7 exception, for this guard and guard-scope-write.sh only (the two
#   write guards, a security boundary; UD U19, Chris pre-release r6 NF6-1, Sentinel r6
#   FU6-1): NON-EMPTY stdin that jq cannot parse or evaluate is DENIED (exit 2, reason
#   "malformed/unsupported hook input"), not allowed. jq rejects input the host can still
#   act on -- a lone UTF-16 surrogate escape such as \ud800 anywhere in the JSON, even in the
#   file content -- and a jq built without regex support fails the path test below; either
#   used to exit 0 here and let the write through. Every other hook keeps the matrix.
#
# Deps: bash + jq (ADR-C3 -- no python3 on the hot path). Reads only stdin, files under
# "$CLAUDE_PROJECT_DIR/.shode-house/" and its sibling _casefold.sh; writes only "$CLAUDE_PROJECT_DIR/.shode-house/state/.degraded"
# (Hook Charter Sec 6 item 1: least privilege, no fixed /tmp path -- AC-S6).

# The first command also turns off the shell options that SHELLOPTS in the environment can turn
# on, that loosened a verdict, and that script code can undo (UD R89): errexit (a failing
# command ended the run with its own exit code, 1 for a failing test or 5 for jq on input it
# cannot parse, which the host treats as non-blocking), keyword (an assignment-shaped argument
# went into a command's environment instead of its arguments), noglob (in the scope guard,
# the scan of the state directory found no file; this guard has no glob, and it is turned off
# here so the three scripts follow one rule) and xtrace (bash expands PS4 in this shell before
# each traced command, so an arithmetic PS4 such as $((path=0)) changed the path this guard
# matches: Sentinel env XT-1). noexec and onecmd act before this command and cannot be undone
# here, and a PS4 is still expanded once, at the trace of this command itself, so a command
# substitution in it runs once (an assignment in it to a variable the ENV-R line further down
# resets is undone there, UD R90): with the variables of that line, they are control of the
# hook's environment, disclosed as equal to disableAllHooks. verbose, which only adds denies, is
# left alone (UD R89, D1 of R88); posix, which only added denies too, is turned off as a side
# effect of the ENV-R line's unset of POSIXLY_CORRECT (UD R90).
set -u -o pipefail +o errexit +o noglob +o keyword +o xtrace

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
state_dir="$proj/.shode-house/state"
journal_dir="$proj/.shode-house/journal"
degraded="$state_dir/.degraded"

deny() {
  # Static message + exactly one extracted-and-canonicalized field (the resolved path).
  # Hook Charter Sec 6 item 4: never echo raw stdin/content back into stderr -- the deny
  # reason flows back into the calling agent's context, so echoing untrusted content here
  # would be a reflected-injection channel, not just a leak.
  printf 'shode-house: direct write to .shode-house/{state,journal} denied -- use workflow-state.sh (init/advance/retry/rework/resume) via Bash instead. resolved_path=%s\n' "$1" >&2
  exit 2
}

# 1) Engagement guard -- pure bash, FIRST statement that can exit, before stdin/jq is
#    ever touched (NFR: no-op path <=30ms p95, MUST NOT invoke jq -- 02-sara-adr-1a.md
#    Sec 1; ADR-C2). A project that never ran /init (no .shode-house/state/) pays ~0ms.
[ -e "$state_dir" ] || exit 0

# 2) Symlink refuse -- fail CLOSED (Hook Charter Sec 7 table: "guard dir เป็น symlink ->
#    fail-closed" -- this is always a tamper signal, never legitimate config; threat T-c,
#    08-sentinel-threat-model-hooks.md Sec 3). Checked on the parent AND both leaves: a
#    clone that replaces .shode-house itself, or just .shode-house/state, or just
#    .shode-house/journal, with a symlink pointing out of the workspace must all deny.
if [ -L "$proj/.shode-house" ] || [ -L "$state_dir" ] || [ -L "$journal_dir" ]; then
  printf 'shode-house: .shode-house/{,state,journal} is a symlink -- refusing (tamper signal, AC-S6)\n' >&2
  exit 2
fi

# 2b) ENV-R. Ordinary variables of the hook's environment that bash or jq read and that
# loosened this check are cleared here, as in the scope guard and scope-check.sh (UD R88,
# Sentinel final ENV-R): jq sources $HOME/.jq, which can redefine a jq builtin (every deny of this guard
# became an allow); bash 4.2 and later stop at a FUNCNEST nesting limit (exit 1, which the host
# treats as non-blocking). TMOUT is cleared too, so the three scripts follow one rule. Nothing
# here reads HOME. What acts before this line (BASH_ENV, SHELLOPTS noexec or onecmd, a PS4
# command substitution at the trace of the first command, exported functions, the bash and jq
# that PATH finds, DYLD_* or LD_PRELOAD) cannot be cleared by script code: that is control of
# the hook's environment, disclosed as equal to disableAllHooks. BASHOPTS is disclosed with it
# (UD R86), but no shopt option it can turn on changed a verdict (one that did would be turned
# off in code). The shell-behaviour variables that the environment, or an assignment in that one
# PS4 expansion, can set are reset here too, as in the scope guard and scope-check.sh (UD R90,
# Dave xt1 XT-2): GLOBIGNORE, EXECIGNORE, CDPATH, POSIXLY_CORRECT and BASH_COMPAT, and IFS is set
# back to space, tab and newline. Unsetting POSIXLY_CORRECT also turns posix mode off, and
# unsetting GLOBIGNORE turns dotglob off; this script uses neither. This line runs before step 3
# (UD R91), so an EXECIGNORE set by the environment or by that PS4 can no longer hide jq from the
# jq check; it is builtins only, so the engagement no-op path above stays fork-free. A PATH
# without jq is still the missing-jq fail-open of step 3, unchanged.
unset TMOUT FUNCNEST GLOBIGNORE EXECIGNORE CDPATH POSIXLY_CORRECT BASH_COMPAT; IFS=$' \t\n'; export HOME=/dev/null

# 3) jq prereq -- fail OPEN + degrade LOUDLY (ADR-C3/C8; Hook Charter Sec 7: a missing
#    dependency on the guard's own hot path must never brick every Write/Edit in the
#    project -- that would get the plugin uninstalled, which is strictly worse than the
#    advisory-only fallback). SessionStart already writes the primary .degraded
#    announcement; this appends a second, more specific line so the two are
#    distinguishable in the file.
if ! command -v jq >/dev/null 2>&1; then
  printf '%s guard-state-write.sh: jq missing on PATH -- guard running fail-open (state/journal writes are NOT protected)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$degraded" 2>/dev/null
  exit 0
fi

# 3b) Byte semantics and the shared case fold (hooks/scripts/_casefold.sh, which ships next
#     to this file). Loaded only after the engagement guard, so the no-op path stays
#     fork-free. A missing helper is a broken install: fail OPEN + degrade loudly, like jq.
export LC_ALL=C
case "${BASH_SOURCE[0]}" in */*) self_dir="${BASH_SOURCE[0]%/*}" ;; *) self_dir=. ;; esac
# shellcheck source=_casefold.sh
if ! . "$self_dir/_casefold.sh" 2>/dev/null; then
  printf '%s guard-state-write.sh: _casefold.sh missing next to the hook -- guard running fail-open (state/journal writes are NOT protected)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$degraded" 2>/dev/null
  exit 0
fi
_scope_folded=""   # set by _scope_fold / _scope_fold_deny (_casefold.sh)

# 4) Read stdin ONCE. jq -r with `//` chains file_path first, notebook_path second
#    (defense-in-depth: matcher is Write|Edit only today, but a future NotebookEdit
#    matcher would reuse this same script unmodified).
#    A path holding a line break or another control character is refused before any shell
#    reading of it (Sentinel pre-release r5 FU5-2, the S5-2 class): $(...) drops every
#    trailing newline, so this guard would judge "x" while the host opens "x<LF>" (a symlink
#    named so, into state/). jq itself tests the decoded string, and prints "C" for such a
#    path or "P" and the path otherwise; only jq's own final newline is then dropped.
#    Non-empty input that jq cannot parse or evaluate is DENIED (the Hook Charter Sec 7
#    exception in the header): the one check below covers malformed JSON, a lone surrogate
#    escape, a non-object tool_input and a jq without regex support. The message is static
#    and never echoes the payload. Empty stdin still exits 0 (nothing to judge).
input=$(cat)
path=$(printf '%s' "$input" | jq -r '(.tool_input.file_path // .tool_input.notebook_path // empty)
  | if type == "string" and test("[\u0000-\u001f\u007f-\u009f]") then "C" else "P" + tostring end' 2>/dev/null)
rc=$?
if [ "$rc" -ne 0 ]; then
  [ -n "$input" ] || exit 0
  printf 'shode-house: DENY (malformed/unsupported hook input) -- jq could not parse or evaluate this Write/Edit hook input (malformed JSON, an escape jq rejects such as a lone UTF-16 surrogate, a tool_input that is not an object, or a jq built without regex support), so the .shode-house/{state,journal} check cannot judge it; this write guard refuses instead of allowing (state guard)\n' >&2
  exit 2
fi
case "$path" in
  C)
    printf 'shode-house: DENY (path-control-char) -- a Write/Edit path that contains a line break (LF, CR) or another control character (U+0000-U+001F, U+007F-U+009F) is never allowed: a shell reading of it can differ from the name the filesystem opens, so the .shode-house/{state,journal} check cannot judge it (state guard)\n' >&2
    exit 2 ;;
  P?*) path="${path#P}" ;;
  *) exit 0 ;;              # this tool_input shape has no path field -- nothing to compare
esac

# 5) Canonicalize to an absolute, dot-free, symlink-free PHYSICAL path. Two phases, in
#    order -- phase A alone is NOT enough to defeat T3 (see phase A comment for why):
#
#    5a) Pure LEXICAL normalize (no filesystem access): collapse "." and "x/.." segments
#        by string manipulation alone. This must run BEFORE any existence check, because
#        a component that does not exist on disk (e.g. Write into a brand-new "foo/"
#        that is never actually created, only used to smuggle "foo/../state/x") can never
#        be `cd`-resolved -- the OS has nothing to stat through -- so an existence-based
#        walk alone cannot cancel that ".." (confirmed by this milestone's own fixture:
#        `.shode-house/foo/../state/probe.json` slipped through an existence-only version
#        of this canonicalizer as `.../foo/../state/probe.json`, i.e. the literal ".."
#        text survived untouched -- this lexical pass is what closes T3 for good).
#    5b) Existence-based physical resolve: `cd` into the deepest EXISTING ancestor of the
#        now-lexically-clean path and `pwd -P`, which resolves any symlink sitting in that
#        resolvable prefix (T3's traversal text is already gone by now; this phase's job
#        is purely symlinks). Whatever tail does not exist yet is re-appended verbatim,
#        case included, for step 6's fold -- a brand-new file being Written does not exist
#        on disk at PreToolUse time, by definition.
lexnorm() {
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

case "$path" in
  /*) abs="$path" ;;
  *)  abs="$proj/$path" ;;
esac
abs=$(lexnorm "$abs")

dir=$(dirname "$abs")
rest=$(basename "$abs")
depth=0
while [ ! -d "$dir" ] && [ "$dir" != "/" ] && [ "$depth" -lt 64 ]; do
  rest="$(basename "$dir")/$rest"
  dir=$(dirname "$dir")
  depth=$((depth + 1))
done
real_dir=$(cd "$dir" 2>/dev/null && pwd -P) || exit 0   # ancestor vanished mid-check -- fail open
real="$real_dir/$rest"

# 6) Case-insensitive prefix compare against the physical, symlink-resolved guard root
#    (T4: APFS/NTFS default case-insensitive, so a differently-cased path names the SAME
#    file on those filesystems; on a case-sensitive filesystem this can rarely
#    false-positive-deny an unrelated same-name-different-case directory -- accepted
#    residual, R5 in 08-sentinel-threat-model-hooks.md Sec 8, explained in the deny
#    reason above).
#    The fold is the shared deny-side _scope_fold_deny (bd: shode-house-v7u.4.34, router
#    R74 NF1, R77): an ASCII-only `tr` let ".ſhode-houſe/ſtate/x.json" through, which APFS
#    writes into .shode-house/state (U+017F folds to "s"), and ".shode-house/ﬆate/x.json"
#    (U+FB06 folds to "st", Sentinel pre-release B2). Fold and match run under LC_ALL=C
#    (set above).
groot_dir=$(cd "$proj/.shode-house" 2>/dev/null && pwd -P) || exit 0
_scope_fold_deny "$real"; lreal=$_scope_folded
_scope_fold_deny "$groot_dir"; lroot=$_scope_folded

case "$lreal" in
  "$lroot"/state|"$lroot"/state/*|"$lroot"/journal|"$lroot"/journal/*)
    deny "$real" ;;
esac

# 7) Identity, not spelling (Sentinel pre-release r3 F-5, the same approach as router R79
#    and r3 B3): `pwd -P` keeps the spelling it was given, so an NFD spelling of an
#    accented project root (one directory on APFS) never matches the string compare above.
#    Every ancestor of the target that IS the .shode-house directory (`-ef`: same device and
#    inode) has the part below it judged with the same fold. Builtin tests only, no process;
#    an identity match can only add a deny.
a="$real"
while [ -n "$a" ] && [ "$a" != / ]; do
  if [ "$a" -ef "$groot_dir" ]; then
    _scope_fold_deny "${real#"$a"}"
    case "$_scope_folded" in
      /state|/state/*|/journal|/journal/*) deny "$real" ;;
    esac
  fi
  a="${a%/*}"
done

exit 0
