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
# Exit codes -- exit 2 is the ONLY code that blocks (Claude Code docs, quoted in
# 02-sara-adr-1a.md Sec "REQUIRED-BEFORE B"); exit 1 is a NON-BLOCKING pass-through and
# must never be used here (would silently defeat the guard -- a correctness bug, not a
# security one, but treated as equally forbidden by the Hook Charter).
#   2 = DENY (state/journal write blocked)
#   0 = ALLOW, or fail-OPEN (Hook Charter Sec 7 fail matrix: unparsable input / missing
#       jq / no path field never blocks -- blocking every Write in a project that never
#       opted into shode-house, or bricking a session over a missing dependency, is worse
#       than the guard occasionally missing a case that the journal-replay net (Stop /
#       SessionStart torn-write check) still catches)
#
# Deps: bash + jq (ADR-C3 -- no python3 on the hot path). Reads only stdin + files under
# "$CLAUDE_PROJECT_DIR/.shode-house/"; writes only "$CLAUDE_PROJECT_DIR/.shode-house/state/.degraded"
# (Hook Charter Sec 6 item 1: least privilege, no fixed /tmp path -- AC-S6).

set -u -o pipefail

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

# 4) Read stdin ONCE. jq -r with `//` chains file_path first, notebook_path second
#    (defense-in-depth: matcher is Write|Edit only today, but a future NotebookEdit
#    matcher would reuse this same script unmodified).
input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' 2>/dev/null)
rc=$?
[ "$rc" -eq 0 ] || exit 0   # malformed JSON on stdin -- fail open, never block on input we can't parse
[ -n "$path" ] || exit 0    # this tool_input shape has no path field -- nothing to compare

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
groot_dir=$(cd "$proj/.shode-house" 2>/dev/null && pwd -P) || exit 0
lreal=$(printf '%s' "$real" | tr '[:upper:]' '[:lower:]')
lroot=$(printf '%s' "$groot_dir" | tr '[:upper:]' '[:lower:]')

case "$lreal" in
  "$lroot"/state|"$lroot"/state/*|"$lroot"/journal|"$lroot"/journal/*)
    deny "$real" ;;
esac

exit 0
