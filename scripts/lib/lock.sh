#!/usr/bin/env bash
# scripts/lib/lock.sh -- shared mkdir-based lock primitive (bd:shode-house-vz8).
#
# ---- History ----
# Extracted from THREE byte-near-identical copies (scripts/side-effect.sh,
# scripts/workflow-state.sh, scripts/scope-check.sh) after the SAME bootstrap race was
# independently measured in all three (10/20, 7/20, 4-7-3-of-40 lost writes -- see
# tests/test-reliability.sh / tests/test-scope-check.sh for the reproductions). Root
# cause was never `mkdir` -- mkdir is genuinely atomic on POSIX. Every one of the three
# copies tried to be clever about a *held* lock: it read the recorded pid/ts, GUESSED
# the holder had died, and reclaimed the lock on that guess. Three successive fixes
# each narrowed that window without closing it. The only fix that closes it is to stop
# guessing: acquire/release NEVER reclaim a held lock automatically, by any path, ever.
#
# iter0 shipped exactly that (acquire/release only, `recover` an explicit CLI command)
# and passed Chris + Quinn's 3b-review on the acquire/release core, but iter0's
# `lock_recover` had two defects, both found by review (bd:shode-house-vz8):
#   Quinn Critical -- no liveness check at all: a live, never-crashed holder was
#     indistinguishable from a dead one, so `recover` against a lock that merely
#     *looked* stuck (a slow critical section) silently stole it -- proven data
#     corruption via a real, non-synced timing repro.
#   Chris High -- the restore-on-abort step was `[ ! -e "$lockd" ] && mv "$quarantine"
#     "$lockd"`, a second, narrower, non-atomic TOCTOU: `mv` onto an existing directory
#     NESTS instead of failing, silently burying an evicted holder's state inside a
#     third party's lock directory -- reproduced own-run by Chris.
# This file (iter1) is the user's own re-specified protocol for `lock_recover`,
# implemented verbatim, not improved on. `lock_acquire`/`lock_release`'s core mutual
# exclusion is untouched (both reviewers independently confirmed it correct).
#
# ---- Contract ----
#
#   acquire:  atomic mkdir(lockdir); generate a unique holder token; write token/pid/ts.
#             NEVER reaps automatically, by any path, ever -- a crashed holder leaves a
#             stuck lock BY DESIGN (that's what makes release fail-closed).
#   release:  identity-only. token != mine -> no-op. token == mine -> remove the lock.
#             Never liveness-aware -- a non-holder can never release, a dead holder's
#             stale token can never be "helpfully" cleared by someone else.
#   recover:  explicit, audited, human-invoked. See "Recovery protocol" below.
#
# ---- Recovery protocol (bd:shode-house-vz8 iter1, user-specified) ----
#
# Liveness gates REFUSAL, never reclamation. `recover` never decides "this pid looks
# dead, so I will act as that dead process's replacement" the way the old three-copy
# auto-reap did -- it only ever decides "I refuse to touch a lock I cannot prove is
# dead". Concretely, against the CANONICAL lock's recorded holder:
#   LIVE    -> REFUSE (LOCK_LIVE). `--force` can NEVER override this, not even silently.
#   DEAD    -> may proceed to reclaim.
#   UNKNOWN -> REFUSE (RECOVERY_REQUIRED) unless `--force` is given (force overrides
#              UNKNOWN only -- an operator's explicit judgment call, audited as forced).
# "DEAD -> proceed" is NOT auto-reap: nothing reaches `lock_recover` from `lock_acquire`,
# a timeout, or a health check -- only a human (or a script acting on a human's behalf)
# invoking the `recover` CLI ever calls it.
#
# Recovery wins an atomic claim (`<lock>.recovering`, a fresh `mkdir` -- exactly one
# winner) BEFORE it ever inspects or touches the canonical lock. `lock_acquire` PRE-
# checks that marker before its own `mkdir`, and -- this is the part that actually
# closes the race -- RE-CHECKS it (and re-checks its own token is still the one on
# disk) AFTER writing its token. An acquire can BEGIN before the marker exists and have
# its `mkdir` land AFTER the marker appears (recover's `mv` can free the canonical path
# mid-recovery, before the marker is removed); without the post-write re-check that
# acquire would wrongly believe it holds an uncontested lock. On a caught race, acquire
# never enters its critical section and cleans up only what it can prove is its own
# (its own token still on disk = provably not yet swept by a concurrent recover).
#
# The quarantine rename (`<lock>` -> `<lock>.quarantine.<recovery-token>`) is done as
# `mkdir <lock>.quarantine.<token>` (atomic claim, fails closed if it somehow already
# exists -- the destination name embeds this recovery attempt's own unique token, so
# collision is not a realistic TOCTOU target, but the *guarantee* comes from `mkdir`
# itself failing shut, never from a prior `[ -e ]` test) followed by
# `mv <lock> <lock>.quarantine.<token>/captured` -- a rename INTO a directory we just
# atomically proved is empty and exclusively ours, so it can never nest onto anyone
# else's content the way the iter0 restore-on-abort bug did. Once that mv succeeds, the
# canonical path is NEVER touched again and NEVER restored, by any path, even on later
# failure -- restore-on-abort is deleted entirely (it was the second race window, and
# "recreate the canonical lock after conceding it might not be ours" cannot be made
# safe by construction, only by luck). A later step failing after a successful
# quarantine rename is RECOVERY_FAILED: the quarantine stays on disk, the audit records
# FAILED, and an operator inspects it by hand -- fail-closed, strictly simpler than
# trying to repair the rename.
#
# Every metadata read (token/pid/ts, on both the canonical lock and the `.recovering`
# marker) is now FOUR-state (bd:shode-house-vz8 iter5, see "TOCTOU disambiguation" below
# for why a third state stopped being enough): VALID(value) | MISSING (file genuinely
# absent) | ERROR (directory or file exists but is CONFIRMED, stably, the SAME object
# and could not be read -- e.g. `chmod 000`) | AMBIGUOUS (a readability probe failed and
# we could not establish, from evidence, whether that was ordinary churn or a stable
# corrupt object -- see below). ERROR is NEVER collapsed into "" and compared as if it
# were a legitimate empty identity -- that collapse is exactly what let a `chmod 000`
# lock defeat recover's identity check in review. An ERROR read refuses outright
# (LOCK_CORRUPT), unconditionally, `--force` cannot override it either (force only
# overrides a legitimately-read-but-UNKNOWN identity, never "we could not even read
# it"). AMBIGUOUS refuses too (RECOVERY_REQUIRED) -- see the TOCTOU disambiguation note
# below for why it gets its own, stricter outcome instead of being folded into ERROR.
# Force-overridability of AMBIGUOUS is NOT uniform across the file, and that split is
# deliberate (bd:shode-house-vz8 iter5/iter6, Quinn-ruled -- do not "simplify" this back
# to one rule): at the CANONICAL LOCK's liveness gate (lock_recover Step 1/Step 2,
# ~line 949 below) AMBIGUOUS is NEVER `--force`-overridable, same as ERROR/CORRUPT --
# that gate decides whether it is safe to reclaim the underlying resource, and a wrong
# answer there is the duplicate-holder/lost-work class of bug this whole file exists to
# prevent, so any unresolved uncertainty must refuse, full stop. At the `.recovering`
# MARKER level (lock_recover Step 0, ~line 816) AMBIGUOUS instead lands in the SAME
# force-eligible tier as UNKNOWN/DEAD -- that gate only decides whether it is safe to
# retry claiming the RIGHT to recover; forcing it clears a stuck coordination marker and
# explicitly does NOT touch the underlying lock (see that branch's own COMPLETED
# message), so it is bounded by the identical operator judgment call recover already
# relies on for an UNKNOWN/DEAD marker.
#
# ---- TOCTOU disambiguation (bd:shode-house-vz8 iter5 -- classifier redesign, the
# user's own final round for this defect class; see the bd's notes for full history) ----
#
# iter2 (Chris C1) made every existence probe three-state (EXISTS|MISSING|ERROR) instead
# of a bare `[ -e ]`. iter3 (Quinn High) found that the SEPARATE readability probe run
# immediately after (`[ ! -r ]`/`[ ! -x ]`, or a `cat` fallback) is its OWN non-atomic
# syscall -- an ordinary removal landing in the gap between the two made the readability
# probe fail on a now-gone path and misreport CORRUPT for a lock that had simply
# vanished; the iter3 fix re-ran the existence probe ONE more time on failure (MISSING ->
# honest MISSING, still EXISTS -> CORRUPT). iter4 (Quinn High, renewed) found the SAME
# shape one call frame deeper (`_lock_read`'s own copy of the identical pair) AND, while
# re-verifying THAT fix at N=100, found the iter3 disambiguation itself is ALSO just
# another non-atomic probe: at contention dense enough for a DIFFERENT worker's `mkdir`
# to recreate the exact same path between the failed readability probe and the iter3
# re-check, the re-check observes EXISTS (a brand new, legitimate, still-empty holder)
# and iter3's logic reported CORRUPT for it -- 30-53% of runs at N=100, instrumented down
# to the mechanism (`recheck=EXISTS`, only `.`/`..` present, no pid file yet).
#
# The user's ruling for iter5, verbatim in intent: stacking a FOURTH existence-only
# re-check would only narrow this window again, not close it -- "the path exists again"
# is not proof it is the SAME path. What has to change is the EVIDENCE, not the
# vocabulary: a failed probe re-observes immediately; a CHANGED identity, or a state
# transition that clearly happened under us, means LOCK_BUSY (transient churn,
# retryable, same as before); the SAME object remaining stable and still
# unreadable/malformed means LOCK_CORRUPT (non-retryable, same as before); being unable
# to establish whether it changed means fail closed as RECOVERY_REQUIRED, never a guessed
# LOCK_BUSY.
#
# `_lock_disambiguate_unreadable` (below `_lock_fs_identity`'s own header) implements
# this: on a failed readability probe it takes ONE settled pair of observations --
# re-run the existence probe, and if still EXISTS, compare a device:inode identity
# fingerprint (`_lock_fs_identity`, NOT another bare existence test) across a single
# ~50ms settle -- and returns MISSING (honestly gone, both observations agree) |
# CORRUPT (same fingerprint both times, still inaccessible -- confirmed stable) |
# CHANGED (a different fingerprint, or the path became accessible, between the two
# observations -- proceed as if the original probe had simply landed a beat later,
# never guessed CORRUPT for what is ordinary churn) | AMBIGUOUS (a clean fingerprint
# could not be obtained on at least one side -- e.g. `stat` itself failed despite
# EXISTS, a race inside this disambiguation's own two observations -- fails closed,
# callers must map this to RECOVERY_REQUIRED, never to LOCK_BUSY, never treated as
# license to proceed with a destructive reclaim). This is one settle-and-compare, not a
# loop, not a third/fourth existence-only layer -- it is a different KIND of evidence
# (identity, not existence) applied exactly once.
#
# A stuck `.recovering` marker (the recovery process itself crashed after claiming it)
# is a first-class state, not a dead end: `lock_acquire` fails closed against it
# (LOCK_BUSY if the marker's own holder still looks alive -- i.e. RECOVERY_IN_PROGRESS
# -- or RECOVERY_REQUIRED if the marker's holder looks dead/unknown), and NOTHING ever
# auto-clears it -- no acquire path, no timeout. The only way to clear a stuck marker is
# `recover --force` run again against the SAME lock while the marker cannot be claimed:
# that forced call clears ONLY the stuck marker (audited distinctly), and does NOT also
# attempt to reclaim the underlying lock in the same call -- an operator re-runs
# `recover` a second time (force or not, as the underlying holder's own liveness now
# dictates) to actually reclaim it. Two separate, both-audited, both-explicit actions,
# never one implicit compound one.
#
# Result vocabulary -- exactly six, no larger taxonomy (rc, for both `lock_acquire` and
# the `recover` CLI/`lock_recover`):
#   0                     success (ACQUIRED / RECOVERED / nothing-to-do)
#   1  LOCK_BUSY             retryable
#   2  RECOVERY_IN_PROGRESS  retryable, bounded
#   3  LOCK_LIVE              non-retryable
#   4  LOCK_CORRUPT           non-retryable
#   5  RECOVERY_REQUIRED      non-retryable
#   6  RECOVERY_FAILED        non-retryable
#   64                    usage error (never a lock-state code, same convention as before)
# `lock_acquire` only ever returns 0/1/2/4/5 (it never decides LOCK_LIVE or
# RECOVERY_FAILED -- those are recover-only outcomes). Retry policy lives in the THREE
# CALLERS (side-effect.sh, workflow-state.sh; scope-check.sh is a separate, already-
# queued track), never inside this file -- see each consumer's own lock-acquire helper
# for its retry policy. This file only classifies; it never decides to retry.
#
# ---- Disk leak (unchanged in spirit from iter0, narrower than the old auto-reap) ----
# The only quarantine directories this file ever creates are `<lockdir>.quarantine.*`,
# made ONLY inside `lock_recover`, ONLY after the liveness gate has already passed (i.e.
# on an explicit, human-invoked recovery of a lock proven dead or forced past UNKNOWN).
# A successful recovery removes its own quarantine copy and verifies the removal
# actually happened before reporting COMPLETED. A FAILED recovery (mismatch after the
# rename, or a cleanup that provably didn't succeed) leaves the quarantine copy on disk
# ON PURPOSE -- it is already on the audit record (the FAILED line names it), which is
# what an operator needs to go inspect and clear it by hand. No automatic sweep is
# added for this (that would be auto-reclamation wearing a different hat).
#
# ---- Usage ----
#   source into a caller, per lock instance, inside the SAME process that will release
#   it (lock identity is a token string, not a pid):
#     lockd=$(...)
#     token=$(lock_acquire "$lockd"); rc=$?
#     [ "$rc" -eq 0 ] || <caller's own retry/stop policy on rc -- see vocabulary above>
#     trap 'lock_release "'"$lockd"'" "'"$token"'"' EXIT
#     ...critical section...
#
#   operator CLI (the only automatic-reap replacement -- explicit + audited):
#     scripts/lib/lock.sh recover [--force] <lockdir> --reason "<why>"
#
# `lock_acquire` waits up to ~2s (20 * 0.1s, unchanged from iter0 -- ordinary live-
# holder contention behavior is unchanged; the wait budget is deliberately NOT raised,
# see the bd's own ruling: a longer wait would make a crash-stuck lock look like
# ordinary contention and delay the recover signal, and would collide with
# hooks/hooks.json's 5s hook timeouts) then fails loud. It never blocks forever.
#
# Test hooks (no-op unless set -- zero behavior change outside tests):
#   LOCK_RECOVER_SYNC_PREMV  -- makes lock_recover() touch "$X.ready" right after the
#     liveness gate passes (about to claim the quarantine dir + do the mv) and block
#     (bounded, 10s safety valve) until "$X.go" appears. Lets a test force a release,
#     or any other canonical-path mutation, into the gap before the rename.
#   LOCK_RECOVER_SYNC_POSTMV -- touches "$X.ready" right after the mv into quarantine
#     succeeds (canonical path is now free) and blocks until "$X.go" appears, before
#     verify/cleanup/marker-removal. Lets a test force a fresh `lock_acquire` to land in
#     the freed window while the `.recovering` marker is still present.
#   LOCK_RECOVER_TOKEN_OVERRIDE -- when set, used verbatim as this call's recovery
#     token (instead of the normal pid.ts.random.random) so a test can force a
#     deterministic, predictable quarantine-name collision (Acceptance E) without
#     needing to guess an unguessable real token.
#   LOCK_CLASSIFY_HOLDER_SYNC -- makes _lock_classify_holder() touch "$X.ready" right
#     after its existence probe confirms EXISTS and block (bounded, 10s safety valve)
#     until "$X.go" appears, before its separate readability probe. Lets a test force
#     an ordinary removal (lock_release's rm -rf, or lock_recover's quarantine mv) into
#     that TOCTOU window deterministically (bd:shode-house-vz8 iter4).
#   LOCK_RECOVER_STEP1_READABLE_SYNC -- the same shape as LOCK_CLASSIFY_HOLDER_SYNC
#     above, but for lock_recover()'s own Step 1 readability probe on the CANONICAL
#     lock (a separate, duplicate implementation of the same TOCTOU-prone pair, now
#     sharing the same fix via _lock_disambiguate_unreadable).
#   LOCK_DISAMBIGUATE_SYNC -- makes _lock_disambiguate_unreadable() itself (see its own
#     header, bd:shode-house-vz8 iter5) touch "$X.ready" right at its own start (before
#     its first existence probe) and block (bounded, 10s safety valve) until "$X.go"
#     appears. This is a DIFFERENT, deeper window than the two hooks above: those pause
#     BEFORE a readability probe runs; this one pauses AFTER a readability probe has
#     already FAILED, right before the disambiguation's own re-observation -- lets a
#     test force a different worker's `mkdir` to recreate the exact same path strictly
#     inside that gap, deterministically reproducing the exact mechanism Quinn
#     instrumented at N=100 (recheck=EXISTS, freshly recreated, no pid file yet).
#
# Deps: bash + jq (jq only for lock_recover's audit write; lock_acquire/lock_release
# have zero jq dependency, same as iter0). `kill -0` (POSIX) for liveness
# classification -- best-effort and NON-authoritative for mutual exclusion (mkdir
# already is that); it can only ever gate an additional REFUSAL, never a reclamation.
# `ps -o ppid=` used only by lock_acquire's real-caller-pid detection (unchanged from
# iter0) -- degrades gracefully if unavailable, diagnostic metadata only.

set -u -o pipefail

_lock_log() { printf 'lock.sh: %s\n' "$*" >&2; }

# ---- three-state existence probe (bd:shode-house-vz8 iter2, Chris Critical C1): EXISTS
# | MISSING | ERROR. Unlike a bare `[ -e ]` (which cannot distinguish ENOENT from
# EACCES-on-an-ancestor -- both just make the test return false), this walks the path
# top-down, one component at a time, confirming each ancestor's search (x) permission
# BEFORE testing the component beneath it -- so a `[ -e ]` false at any given level is
# unambiguous: it can only mean "this component itself does not exist", never "an
# ancestor above it could not be traversed" (that case is caught, and returns ERROR, at
# the PRIOR iteration, before we ever get this deep). This needs NO permission on the
# target itself (matching real stat() semantics: only ancestor search bits matter to
# resolve a path) -- ERROR here means "an ancestor directory could not be traversed",
# never "the target itself happens to be unreadable" (that remains a SEPARATE case,
# handled by the `[ -r ]`/`[ -x ]` checks in _lock_read and _lock_classify_holder below
# -- see _lock_disambiguate_unreadable's own header for how those checks disambiguate
# a race against this probe, bd:shode-house-vz8 iter5). `[ -L ]` alongside
# `[ -e ]` at the final
# component so a dangling symlink is reported EXISTS (the link entry itself resolves
# fine, even though `-e` alone would follow it to a target that isn't there) -- letting
# those same downstream readability checks correctly catch it as unreadable/corrupt
# rather than this probe silently swallowing it as MISSING (Chris C2).
#
# Deliberately built from ONLY bash builtins (`[`, parameter expansion, `read <<<`) --
# no forked subprocess (no `ls`/`stat`/`dirname`/`basename`). This is a genuinely hot
# path: _lock_read and _lock_classify_holder call it on every metadata read, including
# inside _lock_classify_holder's settle-wait retry loop, across every concurrent
# acquire/recover in this file's own stress suites (tests/test-lock.sh's N=15/N=5x8/N=15
# trials). An earlier version of this probe shelled out to `ls -ld` per call and was
# observed to flake THAT suite under concurrent load purely from fork/exec pressure
# (transient errors unrelated to any real permission problem) -- unacceptable for a
# concurrency primitive's own hot path. Same disambiguation GOAL as _lock_pid_liveness's
# kill -0 ESRCH-vs-EPERM text-matching below, achieved here without paying its fork
# cost.
_lock_exists_or_error() {
  local path="$1"
  case "$path" in
    /*) : ;;
    *) path="$PWD/$path" ;;
  esac
  # bd:shode-house-vz8 F1 (Chris iter2 review): a bash here-string (`<<<`) feeds `read`
  # a single line, and plain `read` stops at the FIRST newline byte regardless of
  # `IFS` -- a path component containing a literal embedded newline (legal in a POSIX
  # filename; only `/` and NUL are forbidden) silently truncated everything after it,
  # so the walk never reached the real remaining components and misreported an
  # EXISTING (possibly LIVE) lock as MISSING. Pure parameter-expansion split instead --
  # no `read`, no here-string, so no line-oriented consumption of any kind; still zero
  # forked subprocesses (see header comment above), same fork-free requirement as
  # before.
  local -a parts=()
  local rest="$path"
  while [[ "$rest" == */* ]]; do
    parts+=("${rest%%/*}")
    rest="${rest#*/}"
  done
  parts+=("$rest")
  local last=$(( ${#parts[@]} - 1 ))
  local i comp accum=''
  for i in "${!parts[@]}"; do
    comp="${parts[$i]}"
    [ -n "$comp" ] || continue
    accum="$accum/$comp"
    if [ ! -e "$accum" ] && [ ! -L "$accum" ]; then
      printf 'MISSING'; return
    fi
    if [ "$i" -lt "$last" ] && [ ! -x "$accum" ]; then
      printf 'ERROR'; return
    fi
  done
  printf 'EXISTS'
}

# ---- portable filesystem identity fingerprint (device:inode:ctime_ns), used ONLY by the
# disambiguation below to tell "the SAME object, still there" apart from "a DIFFERENT
# object that happens to occupy the same path now" (bd:shode-house-vz8 iter5). This
# DOES fork (`stat`) -- unlike `_lock_exists_or_error` above, it is called ONLY from
# the already-rare disambiguation path (a readability probe has already failed), never
# on the hot acquire/release path, so the fork-avoidance requirement documented on
# `_lock_exists_or_error`'s own header does not apply here. stat's identity fields
# (device+inode plus ctime_ns) need no permission on the target itself, only search
# permission on its ancestors (same as `_lock_exists_or_error`) -- so this still works
# against a directory that is itself `chmod 000`. Uses Python's os.lstat so we can use
# nanosecond ctime and still fingerprint dangling symlinks (important for the explicit
# dangling-pid corruption checks), which also disambiguates inode-reuse-on-recreate
# filesystems. Prints "" (and returns nonzero) if identity cannot be read -- e.g. Python
# unavailable, or the path vanished again in
# the instant between the caller's own existence probe and this call -- callers must
# treat that as "no identity obtained", NEVER as a match against anything.
_lock_fs_identity() {
  local path="$1" out
  out=$(python3 - "$path" <<'PY' 2>/dev/null
import os, sys
p = sys.argv[1]
try:
    st = os.lstat(p)
    ctime_ns = getattr(st, "st_ctime_ns", int(st.st_ctime * 1_000_000_000))
    print(f"{st.st_dev}:{st.st_ino}:{ctime_ns}")
except Exception:
    sys.exit(1)
PY
  ) && { printf '%s' "$out"; return 0; }
  printf ''
  return 1
}

# ---- is $path accessible RIGHT NOW -- the exact same shape of test every call site
# below already runs once (`[ -r ] && [ -x ]` for a directory, `[ -r ]` alone for a
# file); factored out so the disambiguation below can re-run it a second time without
# duplicating its exact form.
_lock_is_now_accessible() {
  local path="$1"
  if [ -d "$path" ]; then
    [ -r "$path" ] && [ -x "$path" ]
  else
    [ -r "$path" ]
  fi
}

# ---- disambiguates a failed readability/traversability probe (`[ ! -r ]`/`[ ! -x ]`,
# or a failed `cat`) using EVIDENCE of identity/state change, not another bare
# existence probe (bd:shode-house-vz8 iter5 -- classifier redesign, the user's own
# final round for this defect class; full history in the file header's own "TOCTOU
# disambiguation" section above -- iter3 added one existence-only re-check, iter4
# found the same pattern one call frame deeper AND found that iter3's own re-check is
# itself just another non-atomic existence probe, reproducibly misfiring 30-53% of
# runs at N=100 when a DIFFERENT worker's `mkdir` recreates the exact same path inside
# that re-check's own gap). Prints exactly one of:
#   MISSING    -- both observations agree the path is genuinely, honestly gone
#   CORRUPT    -- the SAME object (matching device:inode fingerprint), confirmed
#                 stable across two observations, still inaccessible -- an integrity
#                 problem, never guessed for ordinary churn
#   CHANGED    -- clear evidence a state transition happened under us: a DIFFERENT
#                 fingerprint now occupies the path, or it became accessible between
#                 the two observations -- ordinary contention; callers must proceed as
#                 if the original probe had simply landed a beat later, NEVER return
#                 CORRUPT for this case
#   AMBIGUOUS  -- a clean identity fingerprint could not be obtained on at least one
#                 side (`stat` itself failed despite an existence probe saying
#                 EXISTS -- a race inside this disambiguation's own two
#                 observations) -- fails closed; callers MUST map this to
#                 RECOVERY_REQUIRED, NEVER to LOCK_BUSY, and NEVER treat it as
#                 license to proceed with a destructive reclaim (unlike UNKNOWN
#                 elsewhere in this file, AMBIGUOUS is not `--force`-overridable)
# Exactly ONE settle pause (bounded, ~50ms, same order of magnitude as the
# pid-missing settle-wait in `_lock_classify_holder` below) between the two
# observations -- a single before/after comparison, not a loop, not a third or
# fourth existence-only layer stacked on the ones before it. Ancestor-unresolvable
# (`ERROR` from `_lock_exists_or_error`) stays CORRUPT at both observation points,
# unchanged from iter3/iter4 -- that direction of the invariant must never flip: an
# ancestor that cannot be resolved is NEVER reported as MISSING or CHANGED.
#
# Shared by every call site that needs this disambiguation: `_lock_read` below (both
# its `[ ! -r ]` probe and its `cat` fallback), `_lock_classify_holder` further below,
# and `lock_recover`'s own duplicate `[ ! -r ] || [ ! -x ]` check on the canonical
# lock.
_lock_disambiguate_unreadable() {
  local path="$1"
  if [ -n "${LOCK_DISAMBIGUATE_SYNC:-}" ]; then
    : > "${LOCK_DISAMBIGUATE_SYNC}.ready"
    local synced0=0
    while [ ! -e "${LOCK_DISAMBIGUATE_SYNC}.go" ]; do
      synced0=$((synced0 + 1)); [ "$synced0" -ge 100 ] && break
      sleep 0.1
    done
  fi
  case "$(_lock_exists_or_error "$path")" in
    MISSING) printf 'MISSING'; return ;;
    ERROR)   printf 'CORRUPT'; return ;;
  esac
  local id1; id1=$(_lock_fs_identity "$path")
  if _lock_is_now_accessible "$path"; then
    printf 'CHANGED'; return
  fi
  sleep 0.05
  case "$(_lock_exists_or_error "$path")" in
    MISSING) printf 'MISSING'; return ;;
    ERROR)   printf 'CORRUPT'; return ;;
  esac
  if _lock_is_now_accessible "$path"; then
    printf 'CHANGED'; return
  fi
  local id2; id2=$(_lock_fs_identity "$path")
  if [ -z "$id1" ] || [ -z "$id2" ]; then
    printf 'AMBIGUOUS'; return
  fi
  if [ "$id1" != "$id2" ]; then
    printf 'CHANGED'; return
  fi
  printf 'CORRUPT'
}

# ---- four-state read (bd:shode-house-vz8 iter5, was three-state through iter4):
# VALID(value) | MISSING | ERROR | AMBIGUOUS. Never collapses ERROR/AMBIGUOUS into "".
# Sets globals (bash has no multi-return) -- callers must consume immediately, before
# any other _lock_read call clobbers them. `depth` is internal-only (bounded retry
# guard, never passed by an external caller): on CHANGED evidence (see
# _lock_disambiguate_unreadable's own header) this makes exactly ONE further read
# attempt -- a normal read, now that evidence shows it is safe to trust one, not
# another probe layer -- and if THAT attempt also needs disambiguation, gives up as
# AMBIGUOUS rather than retrying indefinitely.
_LOCK_READ_STATE=""
_LOCK_READ_VALUE=""
_lock_read() {
  local path="$1" depth="${2:-0}"
  case "$(_lock_exists_or_error "$path")" in
    MISSING) _LOCK_READ_STATE="MISSING"; _LOCK_READ_VALUE=""; return ;;
    ERROR)   _LOCK_READ_STATE="ERROR";   _LOCK_READ_VALUE=""; return ;;
  esac
  if [ ! -r "$path" ]; then
    # bd:shode-house-vz8 iter5: see _lock_disambiguate_unreadable's own header -- this
    # probe is a SEPARATE, non-atomic syscall from the exists-or-error probe just
    # above; an ordinary removal of $path (its parent lockdir being rm -rf'd by a
    # concurrent release, mid-walk) landing strictly between the two must not be
    # reported as ERROR (-> CORRUPT, one level up in _lock_classify_holder) for a file
    # that has simply, ordinarily, stopped existing -- and a DIFFERENT object landing
    # on the same path in that gap must not be reported as ERROR either.
    case "$(_lock_disambiguate_unreadable "$path")" in
      MISSING)   _LOCK_READ_STATE="MISSING";   _LOCK_READ_VALUE=""; return ;;
      CORRUPT)   _LOCK_READ_STATE="ERROR";     _LOCK_READ_VALUE=""; return ;;
      AMBIGUOUS) _LOCK_READ_STATE="AMBIGUOUS"; _LOCK_READ_VALUE=""; return ;;
      CHANGED)
        if [ "$depth" -ge 1 ]; then
          _LOCK_READ_STATE="AMBIGUOUS"; _LOCK_READ_VALUE=""; return
        fi
        _lock_read "$path" 1
        return
        ;;
    esac
  fi
  local val
  if val=$(cat "$path" 2>/dev/null); then
    _LOCK_READ_STATE="VALID"; _LOCK_READ_VALUE="$val"
    return
  fi
  # same disambiguation for the narrower window between the -r check just above and
  # this cat -- a removal, or a different object appearing, landing there must not be
  # reported ERROR either.
  case "$(_lock_disambiguate_unreadable "$path")" in
    MISSING)   _LOCK_READ_STATE="MISSING";   _LOCK_READ_VALUE="" ;;
    CORRUPT)   _LOCK_READ_STATE="ERROR";     _LOCK_READ_VALUE="" ;;
    AMBIGUOUS) _LOCK_READ_STATE="AMBIGUOUS"; _LOCK_READ_VALUE="" ;;
    CHANGED)
      if [ "$depth" -ge 1 ]; then
        _LOCK_READ_STATE="AMBIGUOUS"; _LOCK_READ_VALUE=""
      else
        _lock_read "$path" 1
      fi
      ;;
  esac
}

# ---- best-effort, READ-ONLY liveness classification of a pid. Prints LIVE | DEAD |
# UNKNOWN. Never authoritative for mutual exclusion -- only ever used to gate a
# REFUSAL (recover) or a retry-classification (acquire's own timeout diagnostic),
# never to justify a reclamation. `kill -0` returning nonzero is ambiguous between
# ESRCH (no such process -- genuinely dead) and EPERM (process exists, owned by
# someone else -- very much alive); best-effort text-match on stderr disambiguates,
# defaulting to the SAFER answer (LIVE) whenever that distinction can't be made.
_lock_pid_liveness() {
  local pid="$1"
  if [ -z "$pid" ]; then printf 'UNKNOWN'; return; fi
  case "$pid" in *[!0-9]*) printf 'UNKNOWN'; return ;; esac
  local err rc
  err=$(kill -0 "$pid" 2>&1); rc=$?
  if [ "$rc" -eq 0 ]; then printf 'LIVE'; return; fi
  case "$err" in
    *"not permitted"*|*"Operation not permitted"*) printf 'LIVE'; return ;;
  esac
  printf 'DEAD'
}

# ---- classify a lock-shaped directory (canonical lockdir OR a `.recovering` marker --
# both are just "a directory with a pid file" at this level). Prints one of:
#   MISSING    -- the directory does not exist at all
#   CORRUPT    -- confirmed, stably, either not readable/traversable itself, or its
#                 pid file exists but could not be read (permission denied) -- NEVER
#                 folded into UNKNOWN
#   AMBIGUOUS  -- (bd:shode-house-vz8 iter5) a readability probe failed and it could
#                 not be established whether that was ordinary churn or a stable
#                 corrupt object -- see `_lock_disambiguate_unreadable`'s own header.
#                 Fails closed like CORRUPT, but is a DISTINCT outcome: callers must
#                 map it to RECOVERY_REQUIRED, never LOCK_BUSY, and it is NEVER
#                 `--force`-overridable (unlike UNKNOWN below)
#   UNKNOWN    -- directory is readable but the pid file is absent (mid-populate, or a
#                 tokenless crash-between-mkdir-and-write lock)
#   LIVE       -- recorded pid appears to be running
#   DEAD       -- recorded pid definitively does not exist
_lock_classify_holder() {
  local dir="$1"
  case "$(_lock_exists_or_error "$dir")" in
    MISSING) printf 'MISSING'; return ;;
    ERROR)   printf 'CORRUPT'; return ;;   # ancestor unresolvable -- cannot tell, never MISSING
  esac
  # ---- test hook: pause here, between the existence probe above (dir confirmed
  # EXISTS) and the readability probe below -- lets a test force an ORDINARY removal
  # (a plain lock_release, or a lock_recover's quarantine mv) into the TOCTOU window
  # deterministically (bd:shode-house-vz8 iter4), instead of racing for it. No-op
  # unless set -- zero behavior change outside tests, same convention as the
  # LOCK_RECOVER_SYNC_* hooks above. ----
  if [ -n "${LOCK_CLASSIFY_HOLDER_SYNC:-}" ]; then
    : > "${LOCK_CLASSIFY_HOLDER_SYNC}.ready"
    local synced=0
    while [ ! -e "${LOCK_CLASSIFY_HOLDER_SYNC}.go" ]; do
      synced=$((synced + 1)); [ "$synced" -ge 100 ] && break
      sleep 0.1
    done
  fi
  if [ ! -r "$dir" ] || [ ! -x "$dir" ]; then
    case "$(_lock_disambiguate_unreadable "$dir")" in
      MISSING)   printf 'MISSING'; return ;;
      CORRUPT)   printf 'CORRUPT'; return ;;
      AMBIGUOUS) printf 'AMBIGUOUS'; return ;;
      CHANGED)
        # bd:shode-house-vz8 iter5 (Quinn High, renewed -- the N=100 finding): evidence
        # shows a DIFFERENT object now legitimately occupies $dir (or it simply became
        # accessible again) -- fall through and classify it normally below, exactly as
        # if the readability probe above had landed a beat later and simply succeeded.
        # Never return CORRUPT for this case.
        : ;;
    esac
  fi
  _lock_read "$dir/pid"
  if [ "$_LOCK_READ_STATE" = "MISSING" ]; then
    # A missing pid file is ambiguous: genuinely mid-populate (mkdir just landed,
    # about to write pid within microseconds) vs. a process that crashed before ever
    # writing it. Settle briefly (bounded, ~250ms) before concluding UNKNOWN -- this is
    # a usability smoothing for the ordinary race, never a safety difference: UNKNOWN
    # still REFUSES by default either way (lock_recover's liveness gate, and
    # lock_acquire's marker-timeout classification, both treat UNKNOWN as non-live).
    local i=0
    while [ "$i" -lt 5 ] && [ "$_LOCK_READ_STATE" = "MISSING" ]; do
      sleep 0.05
      _lock_read "$dir/pid"
      i=$((i + 1))
    done
  fi
  case "$_LOCK_READ_STATE" in
    ERROR)     printf 'CORRUPT';   return ;;
    AMBIGUOUS) printf 'AMBIGUOUS'; return ;;
    MISSING)   printf 'UNKNOWN';   return ;;
  esac
  _lock_pid_liveness "$_LOCK_READ_VALUE"
}

# ---- internal: classify an ORDINARY acquire timeout against the CANONICAL lock (no
# `.recovering` marker involved -- that path is handled separately in lock_acquire).
# Prints "CODE|human text" on one line. Read-only, never mutates, never gates the wait
# itself -- runs strictly AFTER the decision to fail is already made.
_lock_classify_timeout() {
  local lockd="$1"
  local cls; cls=$(_lock_classify_holder "$lockd")
  case "$cls" in
    CORRUPT)   printf 'LOCK_CORRUPT|lock directory exists but is not readable/traversable (permission denied) -- cannot determine who (if anyone) holds it' ;;
    AMBIGUOUS) printf 'RECOVERY_REQUIRED|could not establish whether the lock holder changed (ordinary churn) or is the same stable object during a readability check -- refusing to guess LOCK_BUSY; a human should run `scripts/lib/lock.sh recover` once contention settles (bd:shode-house-vz8 iter5)' ;;
    DEAD)      printf 'RECOVERY_REQUIRED|recorded holder is no longer running -- this lock is very likely crash-stuck; a human should run `scripts/lib/lock.sh recover` (never auto-retry)' ;;
    *)         printf 'LOCK_BUSY|recorded holder appears to still be running, or its identity could not yet be determined (mid-populate) -- ordinary contention, bounded retry is reasonable' ;;
  esac
}

# ---- lock_acquire <lockdir>
# Prints the holder token on stdout and returns 0 on success. Prints nothing on
# failure and returns one of: 1 LOCK_BUSY | 2 RECOVERY_IN_PROGRESS | 4 LOCK_CORRUPT |
# 5 RECOVERY_REQUIRED (never 3 or 6 -- those are recover-only outcomes). Never reaps,
# never guesses -- the only test for "free" is whether `mkdir` itself succeeds.
lock_acquire() {
  local lockd="$1" waited=0
  local recovering="${lockd}.recovering"

  while :; do
    # PRE-CHECK: an in-flight recovery blocks new acquires outright -- do not even
    # attempt mkdir this iteration (see header: this is what the post-write re-check
    # below exists to close the race the pre-check alone cannot).
    # bd:shode-house-vz8 F2 (Chris iter2 review, Low): was a bare `[ -e ]`, the one
    # remaining unmigrated decision point of its kind inside lock_acquire -- now the
    # same three-state probe as everywhere else in this file. EXISTS and ERROR (cannot
    # tell, e.g. an ancestor directory just went EACCES) both fold into the same
    # wait-and-classify branch as a genuine marker; only a confirmed MISSING is
    # permissive enough to attempt mkdir this iteration. "Cannot tell" is never treated
    # as "no recovery in progress".
    if [ "$(_lock_exists_or_error "$recovering")" != "MISSING" ]; then
      waited=$((waited + 1))
      if [ "$waited" -ge 20 ]; then
        local mcls; mcls=$(_lock_classify_holder "$recovering")
        _lock_log "acquire timeout on \"$lockd\" -- .recovering marker present, holder classified $mcls"
        case "$mcls" in
          LIVE)      return 2 ;;   # RECOVERY_IN_PROGRESS
          CORRUPT)   return 4 ;;   # LOCK_CORRUPT
          AMBIGUOUS) return 5 ;;   # bd:vz8 iter5: could not establish changed-vs-stable -> fail closed, same as DEAD|UNKNOWN below (explicit, though * already gave 5)
          *)         return 5 ;;   # DEAD | UNKNOWN | MISSING(race) -> RECOVERY_REQUIRED
        esac
      fi
      sleep 0.1
      continue
    fi

    if mkdir "$lockd" 2>/dev/null; then
      break
    fi
    waited=$((waited + 1))
    if [ "$waited" -ge 20 ]; then
      local cls; cls=$(_lock_classify_timeout "$lockd")
      _lock_log "acquire timeout on \"$lockd\" -- ${cls%%|*}: ${cls#*|}"
      case "$cls" in
        LOCK_CORRUPT*)       return 4 ;;
        RECOVERY_REQUIRED*)  return 5 ;;
        *)                   return 1 ;;   # LOCK_BUSY
      esac
    fi
    sleep 0.1
  done

  # mkdir succeeded -- write metadata. BASHPID (not $$) -- callers may invoke this
  # from inside a background subshell; $$ stays pinned to the top-level shell even
  # inside one, which would make every concurrent subshell mint the "same" token.
  local mypid="${BASHPID:-$$}"
  # Record the REAL long-lived caller's pid, not this subshell's own -- every real
  # caller invokes via `tok=$(lock_acquire ...)`, which forks a subshell that exits
  # within microseconds of returning; `kill -0 $mypid` would report "not running"
  # almost immediately even while the actual holder is still mid-critical-section.
  # `ps -o ppid=` queries the kernel for this subshell's OS-level parent instead
  # (bash's own $PPID is cached at shell-startup, not recomputed per subshell).
  # Best-effort, diagnostic metadata: a degraded value here can only make the
  # liveness-gated REFUSAL in lock_recover less accurate, never break mutual
  # exclusion (mkdir already is that) and never enable a reclamation.
  local ownerpid; ownerpid=$(ps -o ppid= -p "$mypid" 2>/dev/null | tr -d '[:space:]')
  case "$ownerpid" in ''|*[!0-9]*) ownerpid="$mypid" ;; esac
  local token; token="${mypid}.$(date +%s).${RANDOM}.${RANDOM}"
  printf '%s' "$token" > "$lockd/token"
  printf '%s' "$ownerpid" > "$lockd/pid"
  date +%s > "$lockd/ts"

  _lock_acquire_postwrite_recheck "$lockd" "$token" "$recovering" >/dev/null
  local rc=$?
  [ "$rc" -eq 0 ] || return "$rc"

  printf '%s' "$token"
  return 0
}

# ---- internal: the post-write re-check (bd:shode-house-vz8 Acceptance A). Exposed as
# its own function (not inlined into lock_acquire) so tests can drive it directly
# against a manually-constructed race window, without needing sub-millisecond real
# concurrency. Prints OK|LOCK_BUSY|RECOVERY_IN_PROGRESS and returns 0|1|2 to match.
# Enters the critical section (rc=0) ONLY if: no `.recovering` marker exists, AND the
# canonical token is still exactly the one this call itself just wrote. On any other
# outcome, cleans up ONLY what it can prove is its own (its own token still present at
# $lockd/token) -- if a concurrent recover already swept $lockd away entirely, there is
# nothing provably ours left to clean, and that is fine.
_lock_acquire_postwrite_recheck() {
  local lockd="$1" token="$2" recovering="$3"
  # bd:shode-house-vz8 F2 (Chris iter2 review, Low): was a bare `[ -e ]`, the last
  # remaining unmigrated decision point of its kind -- now the same three-state probe.
  # EXISTS and ERROR both fold into the RECOVERY_IN_PROGRESS branch: a call this close
  # to `lock_acquire`'s own write must never treat "cannot tell whether a recovery
  # started" as "no recovery in progress" and hand back OK on that basis.
  if [ "$(_lock_exists_or_error "$recovering")" != "MISSING" ]; then
    if [ "$(cat "$lockd/token" 2>/dev/null)" = "$token" ]; then
      rm -rf "$lockd" 2>/dev/null
    fi
    printf 'RECOVERY_IN_PROGRESS'
    return 2
  fi
  local cur; cur=$(cat "$lockd/token" 2>/dev/null)
  if [ "$cur" != "$token" ]; then
    printf 'LOCK_BUSY'
    return 1
  fi
  printf 'OK'
  return 0
}

# ---- lock_release <lockdir> <token>
# Identity-aware, never liveness-aware. A caller with no token (empty $2) can never
# release anything -- that is definitionally a non-holder, not a special case.
lock_release() {
  local lockd="$1" mine="${2:-}"
  [ -n "$mine" ] || return 0
  [ -d "$lockd" ] || return 0
  local holder=""
  [ -f "$lockd/token" ] && holder=$(cat "$lockd/token" 2>/dev/null)
  [ "$holder" = "$mine" ] || return 0
  rm -rf "$lockd" 2>/dev/null || true
  return 0
}

# ---- internal: append one audit line, BEFORE any mutation for STARTED/REFUSED, and
# gating COMPLETED itself (see lock_recover). outcome in STARTED|REFUSED|FAILED|
# COMPLETED (item 6's vocabulary); result is one of the 6-way rc names when non-empty.
# Returns 0 iff the line was actually appended -- lock_recover treats a nonzero return
# here as itself a reason COMPLETED cannot be claimed (a failed append is never
# swallowed).
_lock_audit_recover() {
  local lockd="$1" token="$2" pid="$3" ts="$4" reason="$5" outcome="$6" result="${7:-}" note="${8:-}" forced="${9:-false}"
  local audit; audit="$(dirname "$lockd")/.lock-recoveries.jsonl"
  local now; now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  local actor="${USER:-${LOGNAME:-unknown}}"
  local forced_json="false"
  [ "$forced" = "true" ] && forced_json="true"
  local line
  line=$(jq -nc \
    --arg ts "$now" --arg actor "$actor" --arg lockdir "$lockd" \
    --arg token "$token" --arg pid "$pid" --arg holder_ts "$ts" \
    --arg reason "$reason" --arg outcome "$outcome" --arg result "$result" --arg note "$note" \
    --argjson forced "$forced_json" \
    '{ts: $ts, actor: $actor, lockdir: $lockdir, observed_token: $token, observed_pid: $pid, observed_ts: $holder_ts, reason: $reason, outcome: $outcome, forced: $forced}
     + (if $result == "" then {} else {result: $result} end)
     + (if $note == "" then {} else {note: $note} end)') || return 1
  # ---- Chris Low C3: bash applies redirections left-to-right, so a FAILED open() of
  # `>> "$audit"` itself (e.g. its directory is unwritable) emits its error to the
  # CURRENT stderr before a later `2>/dev/null` on the same line takes effect -- the
  # intended suppression never applied to failures of the redirection setup itself, only
  # to output from an already-running command. Group the whole attempt under one
  # redirection so `2>/dev/null` covers the open() failure too; `|| return 1` still
  # catches it either way -- this only fixes an unwanted raw error escaping to stderr.
  { printf '%s\n' "$line" >> "$audit"; } 2>/dev/null || return 1
  return 0
}

# ---- internal (Chris Low, "audit-append return code checked inconsistently"): call
# _lock_audit_recover and, if the append itself fails, surface that on stderr instead of
# firing-and-forgetting it. Deliberately does NOT change the caller's return code --
# REFUSED/FAILED outcomes below are already fail-closed (non-zero, non-COMPLETED)
# regardless of whether the forensic audit trail itself could be written; only a
# COMPLETED/RECOVERED outcome's own user-facing result must be GATED on audit success
# (see every "COMPLETED requires audit succeeding" call site below, which checks
# _lock_audit_recover's return code directly and does NOT use this wrapper).
_lock_audit_or_log() {
  local lockd="$1" outcome="$6"
  if ! _lock_audit_recover "$@"; then
    _lock_log "audit append failed (lockdir=\"$lockd\", outcome=$outcome) -- forensic trail has a gap for this decision"
  fi
}

# ---- internal: `lock_recover`'s "the canonical lock is genuinely not there -- nothing
# to recover" success completion. Factored out (bd:shode-house-vz8 iter4) because it now
# has TWO legitimate ways to arrive at a confirmed-MISSING canonical lock: the direct
# exists-or-error probe at the top of Step 1, and the TOCTOU-disambiguated readability
# probe just below it (see `_lock_disambiguate_unreadable`) -- both must emit
# the exact same audited, gated COMPLETED. Prints the same COMPLETED/RECOVERY_FAILED
# text either call site printed before this refactor; returns 0 or 6 to match.
_lock_recover_nothing_to_recover() {
  local lockd="$1" reason="$2" recovering="$3"
  rm -rf "$recovering" 2>/dev/null
  # Chris C1 (Critical): a COMPLETED-emitting branch must gate on the audit append's
  # own return code, same as the force-clear branch and Step 6 -- a "nothing to
  # recover" success is still a success claim.
  if ! _lock_audit_recover "$lockd" "" "" "" "$reason" "COMPLETED" "" "nothing to recover -- lock was not held"; then
    printf 'RECOVERY_FAILED: "%s" was not locked, but the audit append itself failed -- treat as unaudited, investigate .lock-recoveries.jsonl by hand\n' "$lockd"
    return 6
  fi
  printf 'COMPLETED: "%s" is not currently locked -- nothing to recover\n' "$lockd"
  return 0
}

# ---- lock_recover <lockdir> <reason> [force(0|1)]
# Explicit, audited reclaim of a stuck lock. NEVER called by lock_acquire -- the only
# caller is a human (or a script acting on a human's behalf) via the CLI below.
# Returns 0 (recovered, or nothing to recover, or a stuck marker was force-cleared) or
# one of 2 RECOVERY_IN_PROGRESS | 3 LOCK_LIVE | 4 LOCK_CORRUPT | 5 RECOVERY_REQUIRED |
# 6 RECOVERY_FAILED.
lock_recover() {
  local lockd="$1" reason="${2:-}" force="${3:-0}"
  if [ -z "$reason" ]; then
    _lock_log "recover: --reason is required (recovery is an audited command)"
    return 64
  fi

  local recovering="${lockd}.recovering"

  # ---- Step 0: atomically claim the RIGHT to recover -- exactly one winner. ----
  if ! mkdir "$recovering" 2>/dev/null; then
    local mcls; mcls=$(_lock_classify_holder "$recovering")
    case "$mcls" in
      LIVE)
        _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "RECOVERY_IN_PROGRESS" "another recovery of this lock is currently in progress"
        printf 'RECOVERY_IN_PROGRESS: another recovery of "%s" is already in progress -- bounded retry\n' "$lockd"
        return 2
        ;;
      CORRUPT)
        # Chris C1: reached both when the marker itself exists but cannot be read AND
        # when the marker's path cannot even be RESOLVED (an ancestor directory is
        # EACCES) -- _lock_classify_holder's own _lock_exists_or_error probe no longer
        # collapses that second case into MISSING (see its header). Message says
        # "could not be resolved" rather than asserting the marker positively exists,
        # since in the ancestor-EACCES case we genuinely cannot tell either way.
        _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "LOCK_CORRUPT" "the .recovering marker could not be resolved or read (unreadable marker, or an ancestor directory is not accessible)"
        printf 'LOCK_CORRUPT: the ".recovering" marker on "%s" could not be resolved or read (unreadable, or an ancestor directory is not accessible) -- refusing, never treating unreadable as empty\n' "$lockd"
        return 4
        ;;
      *)  # DEAD | UNKNOWN | AMBIGUOUS | MISSING(lost the race just now -- treat like a
          # stuck marker retry). bd:vz8 iter5: AMBIGUOUS falls in here deliberately,
          # same fail-closed/force-eligible tier as UNKNOWN -- an uncertain MARKER
          # (not yet the underlying lock itself) is the same class of "an operator's
          # explicit judgment call" this branch already exists for.
        if [ "$force" = "1" ]; then
          rm -rf "$recovering" 2>/dev/null
          # Chris C1 (Critical): `rm -rf` can silently no-op (e.g. EACCES on an
          # ancestor, or the directory itself being non-empty-but-unremovable) --
          # verify with the same three-state probe used everywhere else in this file,
          # never a bare `[ -e ]`. Both EXISTS (rm genuinely left something behind) and
          # ERROR (cannot even tell) mean "did NOT succeed" -- "cannot tell" is NEVER
          # "must have worked".
          local clear_state; clear_state=$(_lock_exists_or_error "$recovering")
          if [ "$clear_state" != "MISSING" ]; then
            _lock_audit_or_log "$lockd" "" "" "" "$reason" "FAILED" "RECOVERY_FAILED" "forced clear of the stuck .recovering marker did not succeed (post-clear state: $clear_state)" "true"
            printf 'RECOVERY_FAILED: could not clear the stuck ".recovering" marker on "%s"\n' "$lockd"
            return 6
          fi
          # Chris C1 (Critical): COMPLETED must require the audit append itself
          # succeeding, exactly like Step 6's genuine-recovery COMPLETED already does --
          # this was the ONE COMPLETED-emitting branch in the file that did not gate on
          # it, and is exactly how the false-COMPLETED-under-an-unreadable-ancestor bug
          # reported success with zero audit record.
          if ! _lock_audit_recover "$lockd" "" "" "" "$reason" "COMPLETED" "" "forced: cleared a stuck .recovering marker (marker holder was $mcls); the underlying lock itself was NOT touched by this call -- re-run recover to reclaim it" "true"; then
            printf 'RECOVERY_FAILED: cleared the stuck ".recovering" marker on "%s", but the audit append itself failed -- treat as unaudited, investigate .lock-recoveries.jsonl by hand before re-running recover\n' "$lockd"
            return 6
          fi
          printf 'COMPLETED: cleared a stuck ".recovering" marker on "%s" (marker holder was %s) -- re-run recover to reclaim the underlying lock\n' "$lockd" "$mcls"
          return 0
        fi
        _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "RECOVERY_REQUIRED" "a stuck .recovering marker exists (marker holder $mcls) -- re-run with --force to clear the marker itself"
        printf 'RECOVERY_REQUIRED: a stuck ".recovering" marker exists on "%s" (marker holder %s) -- re-run with --force to clear the marker (this does not by itself reclaim the lock)\n' "$lockd" "$mcls"
        return 5
        ;;
    esac
  fi

  # ---- we exclusively own $recovering now. Write pid FIRST, before anything that
  # forks a subprocess (the token below needs `date`) -- this minimizes the window
  # where a concurrent losing recover (or lock_acquire's marker-timeout classifier)
  # observes this marker as pid-less and has to settle-wait (see
  # _lock_classify_holder) instead of seeing LIVE immediately. ----
  local my_pid="${BASHPID:-$$}"
  printf '%s' "$my_pid" > "$recovering/pid"
  # LOCK_RECOVER_TOKEN_OVERRIDE: test-only hook (no-op unless set) so a test can force
  # a deterministic, predictable quarantine-name collision (Acceptance E) without
  # needing to guess an unguessable real token.
  local recovery_token; recovery_token="${LOCK_RECOVER_TOKEN_OVERRIDE:-${my_pid}.$(date +%s).${RANDOM}.${RANDOM}}"
  printf '%s' "$recovery_token" > "$recovering/recovery-token"
  printf '%s' "$reason" > "$recovering/reason"
  date +%s > "$recovering/started-ts"

  _lock_audit_recover "$lockd" "" "" "" "$reason" "STARTED"
  if [ $? -ne 0 ]; then
    rm -rf "$recovering" 2>/dev/null
    printf 'RECOVERY_FAILED: could not write the audit record for "%s" -- refusing to proceed unaudited\n' "$lockd"
    return 6
  fi

  # ---- Step 1: three-state read of the canonical lock (Chris C1: distinguish "not
  # there" from "cannot tell" for the CANONICAL lock's path itself, exactly the same
  # class fix applied to the .recovering marker above). ----
  local lockd_state; lockd_state=$(_lock_exists_or_error "$lockd")
  if [ "$lockd_state" = "ERROR" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "LOCK_CORRUPT" "the lock path could not be resolved -- an ancestor directory is not readable/searchable, never treated as if the lock were absent"
    printf 'LOCK_CORRUPT: "%s" could not be resolved (an ancestor directory is not readable/searchable) -- refusing, never treating unreadable as empty\n' "$lockd"
    return 4
  fi
  if [ "$lockd_state" = "MISSING" ]; then
    _lock_recover_nothing_to_recover "$lockd" "$reason" "$recovering"; return $?
  fi
  # ---- test hook: pause here, between the exists-or-error probe above (canonical
  # lock confirmed EXISTS) and the readability probe below -- lets a test force an
  # ordinary removal into THIS specific TOCTOU window deterministically
  # (bd:shode-house-vz8 iter4), the same shape as LOCK_CLASSIFY_HOLDER_SYNC above but
  # for lock_recover's own Step 1 (this call site never reaches _lock_classify_holder
  # at all when the canonical lock turns out unreadable -- it returns before Step 2).
  # No-op unless set. ----
  if [ -n "${LOCK_RECOVER_STEP1_READABLE_SYNC:-}" ]; then
    : > "${LOCK_RECOVER_STEP1_READABLE_SYNC}.ready"
    local synced3=0
    while [ ! -e "${LOCK_RECOVER_STEP1_READABLE_SYNC}.go" ]; do
      synced3=$((synced3 + 1)); [ "$synced3" -ge 100 ] && break
      sleep 0.1
    done
  fi
  if [ ! -r "$lockd" ] || [ ! -x "$lockd" ]; then
    # bd:shode-house-vz8 iter5 (Quinn High, renewed): this readability probe is a
    # SEPARATE, non-atomic syscall from the exists-or-error probe just above -- an
    # ordinary removal (a concurrent lock_release, or another lock_recover's
    # quarantine mv) landing strictly between the two must not be misreported as
    # LOCK_CORRUPT for a lock that had simply, ordinarily, vanished -- and neither
    # must a DIFFERENT worker's fresh mkdir recreating the same path in that same gap
    # (the exact mechanism Quinn instrumented at N=100 after the iter4 fix -- see
    # `_lock_disambiguate_unreadable`'s own header). Same shared implementation as
    # `_lock_classify_holder`'s identical pair above.
    case "$(_lock_disambiguate_unreadable "$lockd")" in
      MISSING)
        _lock_recover_nothing_to_recover "$lockd" "$reason" "$recovering"; return $?
        ;;
      CHANGED)
        # evidence of a state transition -- fall through to Step 2 below, which
        # classifies $lockd's current, now-accessible state exactly as if this probe
        # had simply landed a beat later and succeeded the first time.
        : ;;
      AMBIGUOUS)
        rm -rf "$recovering" 2>/dev/null
        _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "RECOVERY_REQUIRED" "could not establish whether \"$lockd\" changed identity or is the same stable object while checking readability -- refusing to guess; re-run once contention settles"
        printf 'RECOVERY_REQUIRED: "%s" could not be reliably classified as changed-vs-stable while checking readability (transient churn during the check) -- refusing to guess; re-run once contention settles\n' "$lockd"
        return 5
        ;;
      CORRUPT)
        rm -rf "$recovering" 2>/dev/null
        _lock_audit_or_log "$lockd" "" "" "" "$reason" "REFUSED" "LOCK_CORRUPT" "lock directory exists but is not readable/traversable"
        printf 'LOCK_CORRUPT: "%s" exists but cannot be read (permission denied) -- refusing, never treating unreadable as safe\n' "$lockd"
        return 4
        ;;
    esac
  fi

  # Classify liveness FIRST (this settles briefly on a missing pid file -- see
  # _lock_classify_holder -- so a genuinely mid-populate fresh acquirer isn't
  # misclassified as UNKNOWN purely from reading a fraction of a second too early),
  # THEN take the three individual field reads for audit/verification -- by then any
  # real in-flight write the settle wait was giving a chance to land already has.
  local liveness; liveness=$(_lock_classify_holder "$lockd")

  _lock_read "$lockd/token"; local obs_token_state="$_LOCK_READ_STATE" obs_token="$_LOCK_READ_VALUE"
  _lock_read "$lockd/pid";   local obs_pid_state="$_LOCK_READ_STATE"   obs_pid="$_LOCK_READ_VALUE"
  _lock_read "$lockd/ts";    local obs_ts_state="$_LOCK_READ_STATE"    obs_ts="$_LOCK_READ_VALUE"

  # bd:shode-house-vz8 iter5: an AMBIGUOUS field or liveness verdict is checked BEFORE
  # the ERROR/CORRUPT guard below and returns its OWN distinct rc (RECOVERY_REQUIRED,
  # not LOCK_CORRUPT) -- and, unlike UNKNOWN two blocks down, is NEVER --force-
  # overridable. This guard must exist explicitly: without it, an AMBIGUOUS liveness
  # value would match neither the "LIVE" check nor the "UNKNOWN" check just below and
  # would silently fall through to "may proceed" -- reclaiming (quarantine + mv) a lock
  # whose identity could not even be established. That silent fallthrough is exactly
  # the class of guess this whole iteration exists to close off.
  if [ "$obs_token_state" = "AMBIGUOUS" ] || [ "$obs_pid_state" = "AMBIGUOUS" ] || [ "$obs_ts_state" = "AMBIGUOUS" ] || [ "$liveness" = "AMBIGUOUS" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "REFUSED" "RECOVERY_REQUIRED" "could not establish whether \"$lockd\"'s metadata changed or is the same stable state while reading it -- refusing to guess, --force does NOT override this (unlike a genuinely UNKNOWN liveness)"
    printf 'RECOVERY_REQUIRED: "%s" metadata could not be reliably classified as changed-vs-stable while reading it (transient churn during the read) -- refusing to guess; re-run once contention settles. This is never --force-overridable, unlike a genuinely UNKNOWN liveness.\n' "$lockd"
    return 5
  fi

  if [ "$obs_token_state" = "ERROR" ] || [ "$obs_pid_state" = "ERROR" ] || [ "$obs_ts_state" = "ERROR" ] || [ "$liveness" = "CORRUPT" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "REFUSED" "LOCK_CORRUPT" "one or more lock metadata files could not be read -- an unreadable field is NEVER treated as a matching-empty identity"
    printf 'LOCK_CORRUPT: "%s" metadata could not be fully read -- refusing\n' "$lockd"
    return 4
  fi

  # ---- Step 2: liveness gate -- REFUSAL only, this is never a reclamation input. ----
  if [ "$liveness" = "LIVE" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "REFUSED" "LOCK_LIVE" "recorded holder pid=$obs_pid is alive -- refusing; --force can never override LIVE"
    printf 'LOCK_LIVE: "%s" is held by a LIVE process (pid=%s) -- refusing, --force can never override this\n' "$lockd" "$obs_pid"
    return 3
  fi
  local forced_flag="false"
  if [ "$liveness" = "UNKNOWN" ]; then
    if [ "$force" != "1" ]; then
      rm -rf "$recovering" 2>/dev/null
      _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "REFUSED" "RECOVERY_REQUIRED" "holder liveness could not be determined -- re-run with --force to override UNKNOWN only"
      printf 'RECOVERY_REQUIRED: "%s" holder liveness is UNKNOWN (pid=%s) -- re-run with --force to proceed anyway\n' "$lockd" "${obs_pid:-<none recorded>}"
      return 5
    fi
    forced_flag="true"
  fi
  # liveness == DEAD (or UNKNOWN + --force): may proceed.

  # ---- test hook: pause right before the quarantine claim + mv. ----
  if [ -n "${LOCK_RECOVER_SYNC_PREMV:-}" ]; then
    : > "${LOCK_RECOVER_SYNC_PREMV}.ready"
    local synced=0
    while [ ! -e "${LOCK_RECOVER_SYNC_PREMV}.go" ]; do
      synced=$((synced + 1)); [ "$synced" -ge 100 ] && break
      sleep 0.1
    done
  fi

  # ---- Step 3: atomic quarantine claim -- guaranteed no-nest BY THE OPERATION ITSELF,
  # never by a prior [ -e ] check (that is the exact shape Chris found in iter0). ----
  local quarantine="${lockd}.quarantine.${recovery_token}"
  if ! mkdir "$quarantine" 2>/dev/null; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "FAILED" "RECOVERY_FAILED" "quarantine destination already existed -- refusing to nest or overwrite" "$forced_flag"
    printf 'RECOVERY_FAILED: quarantine destination for "%s" already existed -- refusing (never nests, never overwrites)\n' "$lockd"
    return 6
  fi

  if ! mv "$lockd" "$quarantine/captured" 2>/dev/null; then
    # canonical vanished or changed between our read and this mv (released, or an
    # unrelated process removed it) -- nothing was captured, nothing to delete.
    rm -rf "$quarantine" 2>/dev/null
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "FAILED" "RECOVERY_FAILED" "canonical lock changed before it could be quarantined (released, or raced)" "$forced_flag"
    printf 'RECOVERY_FAILED: "%s" changed before it could be quarantined (released, or raced) -- nothing was deleted\n' "$lockd"
    return 6
  fi

  # ---- Past this point: canonical <lockd> is NEVER touched again, NEVER restored,
  # by any path, even on failure below. ----

  if [ -n "${LOCK_RECOVER_SYNC_POSTMV:-}" ]; then
    : > "${LOCK_RECOVER_SYNC_POSTMV}.ready"
    local synced2=0
    while [ ! -e "${LOCK_RECOVER_SYNC_POSTMV}.go" ]; do
      synced2=$((synced2 + 1)); [ "$synced2" -ge 100 ] && break
      sleep 0.1
    done
  fi

  # ---- Step 4: verify the quarantined identity matches what was observed BEFORE the
  # rename. A mismatch means a different holder legitimately occupied the canonical
  # path in the gap between observation and the mv -- that holder's state is now
  # sitting in $quarantine, untouched, and stays there. RECOVERY_FAILED, never restored.
  _lock_read "$quarantine/captured/token"; local got_state="$_LOCK_READ_STATE" got_token="$_LOCK_READ_VALUE"
  if [ "$got_state" != "VALID" ] || [ "$got_token" != "$obs_token" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "FAILED" "RECOVERY_FAILED" "the quarantined identity did not match what was observed before the rename (a different holder was captured) -- canonical was NOT restored; the captured state is retained at ${quarantine}" "$forced_flag"
    printf 'RECOVERY_FAILED: "%s" -- the quarantined copy'"'"'s identity did not match what was observed (a different holder was captured) -- canonical was NOT restored; inspect %s\n' "$lockd" "$quarantine"
    return 6
  fi

  # ---- Step 5: clean up the quarantine; verify the cleanup actually succeeded. A
  # failed rm -rf is NEVER swallowed into a false COMPLETED -- and (Chris C1 class fix)
  # "cannot tell whether it's gone" (an ancestor going unreadable between Step 3 and
  # here) is verified the same three-state way as the force-clear marker check above,
  # never a bare `[ -e ]` that would silently read EACCES as "must be gone".
  rm -rf "$quarantine" 2>/dev/null
  if [ "$(_lock_exists_or_error "$quarantine")" != "MISSING" ]; then
    rm -rf "$recovering" 2>/dev/null
    _lock_audit_or_log "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "FAILED" "RECOVERY_FAILED" "the lock was cleared, but its quarantine copy at ${quarantine} could not be fully removed" "$forced_flag"
    printf 'RECOVERY_FAILED: "%s" was cleared, but its quarantine copy could not be fully removed -- inspect %s by hand\n' "$lockd" "$quarantine"
    return 6
  fi

  # ---- Step 6: COMPLETED requires ALL of: quarantine cleanup verified gone (above),
  # AND the audit append itself succeeding. ----
  if ! _lock_audit_recover "$lockd" "$obs_token" "$obs_pid" "$obs_ts" "$reason" "COMPLETED" "" "" "$forced_flag"; then
    rm -rf "$recovering" 2>/dev/null
    printf 'RECOVERY_FAILED: "%s" was cleared and its quarantine removed, but the audit append itself failed -- treat as unaudited, investigate .lock-recoveries.jsonl by hand\n' "$lockd"
    return 6
  fi
  rm -rf "$recovering" 2>/dev/null
  if [ "$forced_flag" = "true" ]; then
    printf 'RECOVERED: "%s" cleared (reason: %s) [forced: holder liveness was UNKNOWN]\n' "$lockd" "$reason"
  else
    printf 'RECOVERED: "%s" cleared (reason: %s)\n' "$lockd" "$reason"
  fi
  return 0
}

_lock_usage() {
  cat >&2 <<'EOF'
usage: lock.sh recover [--force] <lockdir> --reason "<why>"
exit: 0 success (RECOVERED / nothing-to-do / stuck-marker-cleared)
      2 RECOVERY_IN_PROGRESS (retryable, bounded) | 3 LOCK_LIVE | 4 LOCK_CORRUPT
      5 RECOVERY_REQUIRED | 6 RECOVERY_FAILED (all four non-retryable)
      64 usage error
--force overrides an UNKNOWN holder identity ONLY -- it can never override a LIVE
holder, and never overrides an unreadable (LOCK_CORRUPT) lock.
EOF
}

_lock_main() {
  command -v jq >/dev/null 2>&1 || { _lock_log "jq required"; exit 64; }
  local cmd="${1:-}"
  case "$cmd" in
    recover)
      shift
      local force=0
      if [ "${1:-}" = "--force" ]; then force=1; shift; fi
      local lockdir="${1:-}"
      shift || true
      local flag="${1:-}" reason="${2:-}"
      if [ -z "$lockdir" ] || [ "$flag" != "--reason" ] || [ -z "$reason" ]; then
        _lock_usage
        _lock_log "recover: [--force] <lockdir> --reason \"<why>\" required"
        exit 64
      fi
      lock_recover "$lockdir" "$reason" "$force"
      exit $?
      ;;
    ""|-h|--help) _lock_usage; exit 1 ;;
    *) _lock_usage; _lock_log "unknown command '$cmd'"; exit 64 ;;
  esac
}

# Only dispatch the CLI when this file is executed directly -- sourcing scripts get
# the functions above with no side effect.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  _lock_main "$@"
fi
