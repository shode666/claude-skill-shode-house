#!/usr/bin/env bash
# side-effect.sh -- Milestone D (bd: shode-roadmap/C-D1): side-effect ledger
# (ROADMAP-runtime-10.md, section 8.3 -- Atomic Checkpoint + Journal / Side-effect Ledger).
#
# Tracks side-effecting operations that are dangerous to repeat: deploy, migration,
# send, publish, delete, external API mutation. Every recorded entry is keyed by an
# idempotency_key supplied by the caller -- asking with the SAME key a second time must
# tell the caller "already done", not silently let them fire the operation again.
#
#   side-effect.sh check   <bd-id> <idempotency-key>
#   side-effect.sh reserve <bd-id> <operation> <idempotency-key> [<detail>]
#   side-effect.sh record  <bd-id> <operation> <idempotency-key> <status> [<detail>]
#
# `check` is the gate a caller runs BEFORE performing the real side effect. `reserve` is
# what the caller runs BEFORE performing the real side effect too, but AFTER `check` --
# it writes status=pending so a crash between "effect performed" and "record completed"
# is never misreported as "safe to proceed" (bd:shode-house-5cs.3 -- the crash window:
# check -> effect succeeds -> crash before record -> next session's check must NOT say
# NOT_DONE, or the effect gets repeated). `record` is what the caller runs AFTER
# performing the effect (or attempting it), to persist the final result -- it is also
# how a `reserve`d (pending) key gets finalized to completed/failed/whatever the real
# outcome was; no special-casing needed there, `record` already overwrites any non-
# completed existing status.
#
# Full flow: check (must be NOT_DONE) -> reserve (status=pending) -> perform the real
# effect -> record (status=completed). If the caller crashes after reserve but before
# record, the NEXT session's `check` finds status=pending and returns UNKNOWN --
# never NOT_DONE, never "safe to proceed". The caller's correct move on UNKNOWN: verify
# the external system's actual state first, OR -- only if the external operation is
# itself idempotent -- retry using the SAME idempotency_key and then `record` the
# outcome. This script cannot decide which; it only refuses to lie about safety.
#
# A caller never needs, and must never get, a SECOND successful `reserve` on the same
# key (bd:shode-house-5cs.3 iter2). `reserve` on a key that is already pending -- whether
# the second call is a concurrent racer that lost the race, or this same caller retrying
# after its own crash -- returns the SAME CLASS of answer `check` gives for a pending key:
# UNKNOWN/RECONCILE_REQUIRED, exit 2, never a RESERVED-flavored success. The crash-retry
# path is: check -> UNKNOWN -> operator verifies the external system -> `record` the
# real outcome directly (not a second `reserve`).
#
# exit codes:
#   check:
#     0  NOT_DONE            -- no record for this key, or a record exists with
#                                status="failed" (a confirmed, safe-to-retry outcome --
#                                see "status is a CLOSED enum" below) -- safe to (re)attempt
#     1  ALREADY_DONE        -- a record for this key exists with status=completed --
#                                DO NOT REPEAT
#     2  UNKNOWN / RECONCILE_REQUIRED -- a `reserve`d record exists (status=pending) with
#                                no completed record yet -- NEVER "safe to proceed" or
#                                "safe to (re)attempt": the effect may have already
#                                happened. Verify external state first, or retry with the
#                                SAME idempotency_key only if the external op is idempotent.
#     64 usage/dependency error
#   reserve:
#     0  RESERVED            -- new pending record written BEFORE the caller performs the
#                                effect (this is the FIRST reservation for this key -- see
#                                exit 2 below for what every subsequent reserve on the same
#                                key gets instead)
#     1  DENY                -- refused: either (a) this key was already used for a
#                                DIFFERENT operation (ledger integrity, same rule as
#                                `record`), or (b) the key is already completed (one-way
#                                door -- a completed effect cannot be re-reserved; use a
#                                NEW idempotency_key for a new attempt)
#     2  UNKNOWN / RECONCILE_REQUIRED -- this key is ALREADY pending: a prior `reserve`
#                                for the SAME operation got there first (a concurrent
#                                racer that won, or this same caller's own earlier
#                                reserve before it crashed). Same class of answer `check`
#                                gives for pending -- NEVER a RESERVED-flavored success,
#                                NEVER safe to read as permission to fire the effect. The
#                                ledger is left untouched (bd:shode-house-5cs.3 iter2).
#     64 usage/dependency error
#   record:
#     0  RECORDED      -- new/updated record written (including finalizing a `reserve`d
#                          pending key to completed), OR an idempotent no-op re-record of an
#                          already-completed key with the identical status (not an error --
#                          this is exactly the "asked twice with the same key" case; the
#                          ledger is unchanged, nothing is repeated)
#     1  DENY          -- refused: either (a) this key was already used for a DIFFERENT
#                          operation (ledger integrity -- a key must mean one operation), or
#                          (b) an attempt to change an already-completed record to a
#                          different, non-completed status (completed is a one-way door;
#                          if a NEW attempt is needed, use a NEW idempotency_key)
#     64 usage/dependency error
#
#   0 with **no stdout at all** -- .shode-house/ is missing entirely: engagement guard,
#   same convention as scripts/workflow-state.sh and scripts/scope-check.sh. This script
#   never creates that top-level dir itself.
#
# Deps: bash + jq (ADR-C3 precedent -- no python3 in the hot path).
#
# Ledger location: $ROOT/.shode-house/side-effects/<bd-id with / -> -->.json
#   { "<idempotency_key>": {"operation": "...", "idempotency_key": "...", "status": "...",
#                            "detail": "...", "ts": "..."} }
# One JSON object per bd (not JSONL) so a `check` is a single-key jq lookup, not a scan.
#
# status is a CLOSED, finite enum -- exactly {"pending", "completed", "failed"}. Nothing
# else is a legitimate status value. A ledger entry whose status is anything outside this
# set is CORRUPTION, and validate_ledger_or_die() below fails the WHOLE ledger read closed
# (exit 64) -- it never falls through to NOT_DONE/"safe to (re)attempt" for that bd's
# ledger (bd:shode-house-5cs.3 iter5; see that iteration's paragraph further down for why
# the previous "anything else = NOT_DONE" tolerance was itself the bug, not a feature --
# it made a one-character corruption of "completed" indistinguishable, BY CONSTRUCTION,
# from a legitimate unfamiliar status).
#   "pending"   -- written ONLY by `reserve`, before the real effect runs. Ambiguous by
#                  design: the effect may or may not have run yet. `check`/`reserve` on a
#                  pending key -> UNKNOWN/RECONCILE_REQUIRED, never a safe verdict.
#   "completed" -- written ONLY by `record`. One-way door: once completed, only an
#                  idempotent no-op re-record of the SAME status is accepted; changing it
#                  to anything else is DENY. A completed record must ALSO carry the
#                  PROVING FIELDS below -- a record claiming completed without them is
#                  corruption too, not a legitimately-terminated one.
#   "failed"    -- written ONLY by `record`, when the caller has CONFIRMED the effect did
#                  NOT happen (an ordinary, expected outcome -- e.g. the external API
#                  rejected the request before any side effect occurred). Unlike
#                  "pending", this is NOT ambiguous: `check` on a failed key returns
#                  NOT_DONE ("safe to (re)attempt"), and `reserve` on a failed key is
#                  allowed to proceed (overwrites it with a fresh pending record) -- a
#                  confirmed failure is a legitimate retry starting point, not a
#                  reconciliation hazard.
# `record` validates its caller-supplied <status> argument against this exact enum BEFORE
# touching the ledger -- an unrecognized value is refused (usage error, exit 64), never
# silently written (see cmd_record below).
#
# PROVING FIELDS for status="completed" (bd:shode-house-5cs.3 iter5, per the user's ledger
# invariant list -- "a completed record must contain the fields required to prove
# completion"): the record's own `idempotency_key` field must be present, a string, and
# EQUAL to the entry's own outer ledger key (self-consistency -- catches a record whose
# claimed key drifted from the key it is actually filed under); and `detail` must be
# present and a NON-EMPTY string (a completed claim must carry a human-readable statement
# of what was done/verified -- an empty detail is not proof of anything, just a bare
# claim). Both fields are already written by every real `record`/`reserve` call in this
# script -- this only rejects a record that is MISSING or has corrupted either one.
#
# Old-shape ledgers (written before `reserve`/the closed enum existed) remain readable IF
# AND ONLY IF every status value they contain is already one of the three above AND every
# completed entry already carries its proving fields -- true for every real completed
# record this script has ever written (idempotency_key + non-empty detail were always
# included, going back to the very first version). MIGRATION NOTE: no ledger file in this
# repo currently contains any status value outside {pending, completed, failed} -- verified
# by grep across the repo, there is no real caller of this script anywhere except the test
# suite. The one value this closes off that used to be TOLERATED is "in_progress" (used
# only as this file's own documentation example and in tests of the now-removed tolerant
# branch, never written by any real caller) -- it is superseded by "pending" (the reserve-
# protocol's own in-flight state) and by "failed" (a confirmed-safe-to-retry terminal
# state); a ledger entry that still says "in_progress" is now treated the same as any other
# unrecognized status: corruption, fail closed. If a real deployment ever has a ledger with
# a genuinely legitimate historical status outside this enum, this script will refuse to
# read it (exit 64) rather than silently reinterpreting it -- an operator must hand-migrate
# that entry to pending/completed/failed first; this script will not widen the enum on its
# own to make the refusal disappear.
#
# ROOT can be overridden with SIDEEFFECT_ROOT (used by the test suite to run inside an
# isolated tmp dir instead of the real repo cwd -- mirrors WFSTATE_ROOT / SCOPECHECK_ROOT).
#
# iter 1 (bd:shode-house-5cs.3 rework, per Chris/Quinn 3b-review FAIL) -- two plumbing
# fixes underneath the reserve/pending/UNKNOWN design above, which stays as-is:
#   1. FAIL CLOSED on a corrupt/truncated/empty/unreadable ledger. Previously read_ledger()
#      called die() from INSIDE a `$(...)` command substitution at all three call sites --
#      `exit 64` only kills the subshell, the caller never sees it, so `ledger` silently
#      became "" and every downstream read treated the key as "never existed" (fail-OPEN,
#      "safe to (re)attempt", for a possibly-already-completed dangerous effect -- the
#      exact bug class this whole ledger exists to prevent). Fixed the same way
#      approval.sh's cmd_verify already does it correctly: `jq empty ... || die ...` is
#      now called DIRECTLY in the caller's own shell (validate_ledger_or_die(), never
#      through `$(...)`), before read_ledger() is ever invoked. A ledger that exists but
#      is 0 bytes is now also treated as corruption (not "no record yet") -- `jq empty` on
#      empty stdin is itself "valid" per jq, which is how reserve/record used to be able to
#      silently overwrite a corrupted ledger with a near-empty file (empty ledger var ->
#      jq update-filter on empty stdin emits no output, exit 0 -> the write-side `jq empty
#      "$tmp"` guard also passed on that same empty-is-valid technicality). Both write
#      sites now also reject an empty $tmp file outright, not just an invalid one.
#   2. Locking. `reserve`/`record` were unprotected read-modify-write (read whole ledger,
#      merge in a shell var, atomic-rename the result) with no mutual exclusion --
#      concurrent writers for the SAME bd raced on stale in-memory snapshots and silently
#      dropped each other's keys. Both `reserve` and `record` now: acquire the lock, set
#      an EXIT trap that releases it AND removes any `.tmp.*` file this call created but
#      never got to `mv` (crash mid-write no longer orphans a tmp file -- bd:shode-house-
#      5cs.3 iter1 F3), sweep any `.tmp.*` orphaned by a PRIOR crashed call for this bd
#      (same hygiene workflow-state.sh does), then do the read -> merge -> write critical
#      section. Lock mechanics themselves now live in scripts/lib/lock.sh (bd:shode-house-
#      vz8 -- see that file's header for why: this lock used to be a byte-near-identical
#      copy in three files, and the "stale holder reap" logic each copy carried was where
#      every measured defect actually lived, not in mkdir).
#
# iter 2 (bd:shode-house-5cs.3 rework, Oliver ruling on iter1 open question #1 -- this
# IS the finding Quinn originally raised, not a new design change): the lock fix above
# stopped the ledger from LOSING writes, but every racing caller still got a RESERVED-
# flavored exit 0 -- including the literal text "perform the effect now" -- even though
# only one of them actually holds the pending record. `reserve` on a key that is already
# `pending` now returns the SAME CLASS of answer `check` gives for pending: UNKNOWN /
# RECONCILE_REQUIRED, exit 2, ledger left untouched. This is correct for both callers it
# can encounter: a crash-retry (must reconcile via `check` + `record`, never re-`reserve`)
# and a concurrent racer (must not fire the effect at all). Reserve on a key already
# `completed` is UNCHANGED (still DENY, exit 1) -- completed was never the gap.
#
# iter 3 (bd:shode-house-5cs.7 -- 40-way concurrency measured 38 rc=0 but only 34 keys
# persisted: a live lock's directory was getting deleted out from under it by this
# file's own copy of a "reap a dead-pid holder" step). iter 4 (bd:shode-house-vz8, this
# change): that whole class of defect is now closed by removing automatic stale-lock
# reclamation ENTIRELY, not by patching the reap logic a fourth time -- see
# scripts/lib/lock.sh's header for the full rationale and the exact race three
# successive patches each narrowed without closing. A dead holder now leaves its lock
# stuck by design; the only way to clear it is the explicit, audited
# `scripts/lib/lock.sh recover <lockdir> --reason "..."` command.
#
# iter 5 (bd:shode-house-5cs.3, this change -- Oliver's direct repro + Quinn's L3L4-final
# P0): a ONE-CHARACTER corruption of the literal status string "completed" (case,
# trailing/leading whitespace, an appended suffix) was still valid JSON, still
# `type=="string"` -- validate_ledger_or_die's shape check had nothing to catch it on --
# and landed on the header's own "anything else = NOT_DONE" tolerance, so an
# ALREADY-EXECUTED dangerous effect read back as "safe to (re)attempt", exit 0. Root cause
# (Quinn): that tolerance made a corrupted "completed" indistinguishable BY CONSTRUCTION
# from a legitimate unfamiliar status -- no shape-check tweak can close that gap, only
# closing the open vocabulary can. Fix: status is now the closed enum documented above
# ({pending, completed, failed}); validate_ledger_or_die asserts membership in that enum
# for every entry (not just that status is *some* string), so ANY value outside it --
# including every single-character corruption of "completed", the retired legacy
# "in_progress" convenience, and any other unfamiliar string -- fails the WHOLE ledger
# read closed (exit 64), never NOT_DONE. Also added: the completed-record proving-fields
# check (idempotency_key self-match + non-empty detail) on the same validator, and an
# up-front enum check on `record`'s caller-supplied <status> argument so a bad value is
# refused before it is ever written, not just before it is later read back.

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Overridable for the same reason workflow-state.sh's WFSTATE_LOCK_LIB is -- a mutated
# COPY of this script moved outside scripts/ would otherwise fail to find its sibling.
SIDEEFFECT_LOCK_LIB="${SIDEEFFECT_LOCK_LIB:-$SELF_DIR/lib/lock.sh}"
# shellcheck source=lib/lock.sh
source "$SIDEEFFECT_LOCK_LIB"

ROOT="${SIDEEFFECT_ROOT:-$PWD}"
SHODE_DIR="$ROOT/.shode-house"
LEDGER_DIR="$SHODE_DIR/side-effects"

log_err() { printf 'side-effect.sh: %s\n' "$*" >&2; }
die()     { log_err "$*"; exit 64; }

engagement_active() { [ -d "$SHODE_DIR" ]; }

encode_bd()    { printf '%s' "$1" | sed 's#/#--#g'; }
ledger_file()  { printf '%s/%s.json' "$LEDGER_DIR" "$(encode_bd "$1")"; }
lock_dir()     { printf '%s/.lock-%s' "$LEDGER_DIR" "$(encode_bd "$1")"; }

timestamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ---- lock mechanics (mkdir-based, no automatic stale-lock reclamation) now live in
# scripts/lib/lock.sh (bd:shode-house-vz8, sourced above) -- see that file's header for
# the acquire/release/recover contract cmd_reserve/cmd_record rely on below.
#
# ---- sideeffect_acquire_lock <bd> <caller-label> (bd:shode-house-vz8 iter1) -- retry
# belongs to CALLER semantics, not to scripts/lib/lock.sh (user ruling): reserve/record
# retry ONLY on LOCK_BUSY (ordinary contention) -- RECOVERY_IN_PROGRESS is treated as an
# immediate STOP here, not retried, because an in-flight operator recovery on a side-
# effect ledger's lock is exactly the kind of ambiguity this file's own pending/UNKNOWN
# reconciliation concept exists for (see emit_reconcile_required above) -- narrower than
# workflow-state.sh's own helper on purpose, per the user's per-consumer ruling.
# LOCK_CORRUPT / RECOVERY_REQUIRED are always an immediate STOP, never retried. MUST be
# called directly in the caller's own shell, never through `$(...)` -- same reason
# validate_ledger_or_die() below is: die()'s exit only kills a command-substitution
# subshell, the caller never sees it.
SIDEEFFECT_LOCK_MAX_ATTEMPTS="${SIDEEFFECT_LOCK_MAX_ATTEMPTS:-2}"
SIDEEFFECT_LOCK_TOKEN=""
sideeffect_acquire_lock() {
  local bd="$1" label="$2" lockd; lockd=$(lock_dir "$bd")
  local attempt=0 tok rc
  while :; do
    attempt=$((attempt + 1))
    tok=$(lock_acquire "$lockd"); rc=$?
    [ "$rc" -eq 0 ] && { SIDEEFFECT_LOCK_TOKEN="$tok"; return 0; }
    [ "$rc" -eq 1 ] || break   # only LOCK_BUSY is retryable here
    [ "$attempt" -ge "$SIDEEFFECT_LOCK_MAX_ATTEMPTS" ] && break
    sleep "0.$((RANDOM % 4 + 1))"
  done
  case "$rc" in
    1) die "$label: could not acquire lock for bd '$bd' after $attempt attempt(s) -- LOCK_BUSY (ordinary contention exhausted bounded retry) (${lockd})" ;;
    2) die "$label: could not acquire lock for bd '$bd' -- RECOVERY_IN_PROGRESS (an operator recovery is running; not retried by reserve/record) (${lockd})" ;;
    4) die "$label: could not acquire lock for bd '$bd' -- LOCK_CORRUPT (lock directory cannot be read -- permission problem?) (${lockd})" ;;
    5) die "$label: could not acquire lock for bd '$bd' -- RECOVERY_REQUIRED (this lock looks crash-stuck; an operator must run 'scripts/lib/lock.sh recover') (${lockd})" ;;
    *) die "$label: could not acquire lock for bd '$bd' -- unexpected lock_acquire rc=$rc (${lockd})" ;;
  esac
}

# ---- shared verdict text for a key that is currently `pending` -- used by BOTH `check`
# and `reserve` (bd:shode-house-5cs.3 iter2) so the two commands emit the SAME CLASS of
# answer for the same ledger state: a pending key must never be readable as permission
# to fire the effect, whether the caller asked via `check` or via `reserve`.
emit_reconcile_required() {
  local key="$1" op="$2" ts="$3"
  printf 'UNKNOWN: RECONCILE_REQUIRED -- idempotency_key "%s" was reserved (operation="%s" at %s) but never recorded as completed -- the effect may have already happened. Do not blindly assume either outcome. Verify the external system'"'"'s actual state first, or -- only if "%s" is itself idempotent -- retry using the SAME idempotency_key and then record the outcome.\n' "$key" "$op" "$ts" "$op"
}

# ---- validate the ledger file's JSON well-formedness in the CALLER's own shell --
# called DIRECTLY (never through `$(...)`), so die()'s `exit 64` actually kills the
# process instead of only the subshell (bd:shode-house-5cs.3 iter1 F1 -- this is the
# fix; see the top-of-file comment for the failure mode this closes). A ledger file that
# does not exist yet is not corruption (no side effects recorded for this bd yet); a
# ledger file that EXISTS but is 0 bytes IS treated as corruption -- a real ledger write
# always contains at least "{}", so an empty-but-present file can only mean a torn
# write/disk event, and `jq empty` on empty stdin is itself "valid" per jq, which is
# exactly the loophole that let a corrupted ledger get silently replaced before this fix.
validate_ledger_or_die() {
  local lf="$1"
  # ---- existence: "nothing at this path at all" is the ONLY shape that means "no
  # record yet" (bd:shode-house-5cs.3 iter2, Quinn P0 1c). `[ -f ]` alone cannot
  # distinguish that from "something exists here that is not a regular file" (a
  # directory, or a symlink to a non-regular target) -- both of THOSE are corruption:
  # a directory-shaped path silently swallowed reserve/record writes (mv landed the
  # tmp file NESTED inside instead of replacing it) while every caller was told
  # RESERVED/RECORDED, and `check` read a directory the same as "brand-new, no record
  # yet" for what may have been a previously-completed key. `[ -e ]` false is the only
  # legitimate "doesn't exist yet" case.
  [ -e "$lf" ] || return 0
  if [ ! -f "$lf" ]; then
    die "ledger $lf exists but is NOT A REGULAR FILE (a directory, or a symlink to a non-regular target) -- this is corruption, not \"no record yet\"; FAILING CLOSED for a dangerous side-effect ledger -- restore from journal/vcs, do not hand-edit"
  fi
  if [ ! -s "$lf" ]; then
    die "ledger $lf exists but is EMPTY (0 bytes) -- this is corruption (a real write always contains at least '{}'), not \"no record yet\"; FAILING CLOSED for a dangerous side-effect ledger -- restore from journal/vcs, do not hand-edit"
  fi
  jq empty "$lf" >/dev/null 2>&1 || die "ledger $lf is not valid JSON (this is a bug or manual tampering -- do not repair by hand-guessing, restore from journal/vcs); FAILING CLOSED for a dangerous side-effect ledger"
  # ---- shape, not just syntax (bd:shode-house-5cs.3 iter2, Quinn P0 1b): `jq empty`
  # only proves well-formed JSON -- it says nothing about the top-level value being an
  # OBJECT, or about each entry's value being the {operation,status,ts,...} record
  # shape every real write always produces. A syntactically-valid-but-wrong-shape
  # ledger (a top-level array; a per-key value that is a bare string/number/array
  # instead of a record object) used to sail through this gate, then hit a jq runtime
  # error downstream that resolved to status="" -- which is not the literal "NONE" or
  # "completed"/"pending" this script checks for, so it fell through to the fail-OPEN
  # "safe to (re)attempt"/"safe to proceed" branch for what could be a genuinely
  # completed, already-executed dangerous effect. This is a positive assertion of the
  # shape every real write produces -- reject everything that doesn't match it, rather
  # than a growing blocklist of the specific malformed shapes anyone has tried; any
  # future malformed shape nobody has enumerated yet still fails this the same way.
  #
  # iter5 (bd:shode-house-5cs.3, Oliver repro / Quinn L3L4-final P0): `status` membership
  # in the closed enum {pending, completed, failed} is now asserted HERE, as part of the
  # same positive shape assertion -- not as a separate downstream string comparison. This
  # is what closes the near-miss-corruption hole: a status of "Completed"/"completed "/
  # "COMPLETED"/"completedX"/anything else outside the three literals fails THIS gate
  # (exit 64, whole ledger), it never reaches the completed/pending/else branches in
  # cmd_check that used to treat "anything else" as NOT_DONE/"safe to (re)attempt". A
  # completed entry must ALSO satisfy the proving-fields check (idempotency_key field
  # equals its own outer ledger key; detail is a non-empty string) -- see the top-of-file
  # "PROVING FIELDS" comment for the rationale. Allowing extra FIELDS beyond these stays
  # untouched (the filter never rejects a record for having additional keys) -- only extra
  # SHAPES/values are refused, per the user's "allow extra fields, never allow extra
  # shapes" rule.
  jq -e '
    def is_known_status: . == "pending" or . == "completed" or . == "failed";
    type == "object"
    and (to_entries | all(
      .key as $outer_key
      | .value as $rec
      | ($rec | type) == "object"
        and (($rec.operation // null) | type) == "string"
        and (($rec.status    // null) | type) == "string"
        and ((($rec.status    // "") | is_known_status))
        and (($rec.ts        // null) | type) == "string"
        and (
          ($rec.status != "completed")
          or (
            (($rec.idempotency_key // null) | type) == "string"
            and ($rec.idempotency_key == $outer_key)
            and (($rec.detail // null) | type) == "string"
            and ((($rec.detail // "") | length) > 0)
          )
        )
    ))
  ' "$lf" >/dev/null 2>&1 \
    || die "ledger $lf is syntactically valid JSON but not shaped like a side-effect ledger, OR contains a status value outside the closed enum {pending, completed, failed} (including a near-miss corruption of a valid value -- wrong case, stray whitespace, an appended/prepended character), OR a status=completed record missing its required proving fields (idempotency_key equal to its own ledger key, and a non-empty detail) -- this is corruption (a wrong-shape write, an unrecognized/corrupted status string, an unrelated file swapped onto this path, or manual tampering), not \"no record yet\"; FAILING CLOSED for a dangerous side-effect ledger -- restore from journal/vcs, do not hand-edit. If a genuinely legitimate old status value triggered this, it must be hand-migrated to pending/completed/failed before this script will read the file again -- it will never silently reinterpret an unrecognized status as safe."
}

# ---- read the ledger file, or "{}" if it doesn't exist yet (a bd with no side effects
# recorded yet is not an error -- distinct from a corrupt file, which validate_ledger_or_die
# above must have already caught, directly, before this is ever called).
read_ledger() {
  local lf="$1"
  if [ ! -f "$lf" ]; then printf '{}'; return; fi
  cat "$lf"
}

usage() {
  cat >&2 <<'EOF'
usage: side-effect.sh check   <bd-id> <idempotency-key>
       side-effect.sh reserve <bd-id> <operation> <idempotency-key> [<detail>]
       side-effect.sh record  <bd-id> <operation> <idempotency-key> <status> [<detail>]
exit (check):   0 NOT_DONE | 1 ALREADY_DONE | 2 UNKNOWN/RECONCILE_REQUIRED | 64 usage/dep error
exit (reserve): 0 RESERVED (first reservation only) | 1 DENY | 2 UNKNOWN/RECONCILE_REQUIRED (key already pending) | 64 usage/dep error
exit (record):  0 RECORDED (incl. idempotent no-op re-record) | 1 DENY | 64 usage/dep error
      (0 with NO stdout at all = .shode-house/ missing entirely -- engagement guard off)
EOF
}

# =============================================================================
# check -- the pre-flight gate a caller runs BEFORE performing the real side effect
# =============================================================================
cmd_check() {
  local bd="$1" key="$2"
  engagement_active || exit 0

  local lf; lf=$(ledger_file "$bd")
  validate_ledger_or_die "$lf"
  local ledger; ledger=$(read_ledger "$lf")

  local status; status=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].status // "NONE"')
  if [ "$status" = "completed" ]; then
    local op ts; op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // "?"')
    ts=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].ts // "?"')
    printf 'ALREADY_DONE: idempotency_key "%s" recorded as completed (operation="%s" at %s) -- do not repeat\n' "$key" "$op" "$ts"
    exit 1
  fi
  if [ "$status" = "pending" ]; then
    local op ts; op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // "?"')
    ts=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].ts // "?"')
    emit_reconcile_required "$key" "$op" "$ts"
    exit 2
  fi
  if [ "$status" = "NONE" ]; then
    printf 'NOT_DONE: idempotency_key "%s" has no record for bd "%s" -- safe to proceed\n' "$key" "$bd"
  else
    printf 'NOT_DONE: idempotency_key "%s" recorded but status="%s" (not completed) -- safe to (re)attempt\n' "$key" "$status"
  fi
  exit 0
}

# =============================================================================
# reserve -- what the caller runs BEFORE performing the real side effect, right after
# a NOT_DONE `check`. Writes status=pending so a crash before `record` is detectable.
# =============================================================================
cmd_reserve() {
  local bd="$1" operation="$2" key="$3" detail="${4:-}"
  engagement_active || exit 0

  mkdir -p "$LEDGER_DIR"

  # ---- lock -> validate -> merge -> atomic rename (ADR-C5, workflow-state.sh pattern;
  # bd:shode-house-5cs.3 iter1 F2). Keyed per-bd via the same encode_bd() ledger_file()
  # already uses, so concurrent writers for DIFFERENT bds never contend on each other.
  local lockd; lockd=$(lock_dir "$bd")
  sideeffect_acquire_lock "$bd" "reserve"
  local lock_token="$SIDEEFFECT_LOCK_TOKEN"
  local tmp=""
  # F3: on ANY exit (including die()), remove this call's own orphaned tmp file (no-op
  # if it was already mv'd -- $tmp is cleared right after a successful mv below) AND
  # release the lock. $tmp is intentionally left unexpanded here (single-quoted) so the
  # trap reads its value AT EXIT TIME, not when the trap is installed. $lockd/$lock_token
  # are baked in at trap-install time instead (both are set once and never change).
  trap 'rm -f "$tmp" 2>/dev/null; lock_release "'"$lockd"'" "'"$lock_token"'"' EXIT

  # ---- crash-recovery hygiene: sweep any .tmp.* a PRIOR crashed reserve/record for
  # this bd left behind (safe now -- we hold the lock, no concurrent same-bd writer).
  rm -f "$LEDGER_DIR/.tmp.$(encode_bd "$bd")".* 2>/dev/null || true

  local lf; lf=$(ledger_file "$bd")
  validate_ledger_or_die "$lf"
  local ledger; ledger=$(read_ledger "$lf")

  local existing_op existing_status
  existing_op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // ""')
  existing_status=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].status // ""')

  # ---- same ledger-integrity rule as record: a key must mean exactly ONE operation.
  if [ -n "$existing_op" ] && [ "$existing_op" != "$operation" ]; then
    printf 'DENY: idempotency_key "%s" already used for operation "%s", cannot reserve for "%s" (use a new key per distinct operation)\n' \
      "$key" "$existing_op" "$operation"
    exit 1
  fi

  # ---- completed is a one-way door: a finished effect cannot be re-reserved.
  if [ "$existing_status" = "completed" ]; then
    printf 'DENY: idempotency_key "%s" is already completed -- cannot reserve it again (completed is final; use a new key for a new attempt)\n' "$key"
    exit 1
  fi

  # ---- iter2 (bd:shode-house-5cs.3, Oliver ruling on iter1 open question #1 -- this IS
  # the finding Quinn originally raised): a key that is ALREADY pending must NEVER get a
  # RESERVED-flavored success out of a second `reserve` call -- whether that second call
  # is a concurrent racer that arrived after the winner, or this same caller retrying
  # after its own crash. Both get the SAME CLASS of answer `check` gives for pending:
  # UNKNOWN/RECONCILE_REQUIRED, non-zero exit. No ledger write happens here -- the
  # existing pending record (written by whichever caller actually won) is left as-is.
  if [ "$existing_status" = "pending" ]; then
    local exist_ts; exist_ts=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].ts // "?"')
    emit_reconcile_required "$key" "$existing_op" "$exist_ts"
    exit 2
  fi

  local now; now=$(timestamp)
  tmp=$(mktemp "$LEDGER_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  printf '%s' "$ledger" | jq \
    --arg k "$key" --arg op "$operation" --arg d "$detail" --arg ts "$now" \
    '.[$k] = {operation: $op, idempotency_key: $k, status: "pending", detail: $d, ts: $ts}' \
    > "$tmp"
  # F1 hardening: an EMPTY $tmp must never be treated as "valid" -- `jq empty` on empty
  # stdin is itself valid per jq, which is exactly how a corrupted-ledger read used to
  # turn into a silent whole-ledger wipe. Reject empty OR invalid.
  if [ ! -s "$tmp" ] || ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    tmp=""
    die "reserve: generated ledger failed validation (must be non-empty valid JSON) -- this is a bug, report it"
  fi
  mv "$tmp" "$lf"
  tmp=""   # already landed -- nothing left for the EXIT trap to clean up

  printf 'RESERVED: idempotency_key "%s" operation="%s" status=pending -- perform the effect now, then record the outcome\n' "$key" "$operation"
  exit 0
}

# =============================================================================
# record -- what the caller runs AFTER performing (or attempting) the side effect
# =============================================================================
cmd_record() {
  local bd="$1" operation="$2" key="$3" status="$4" detail="${5:-}"
  engagement_active || exit 0

  # ---- closed status enum (bd:shode-house-5cs.3 iter5): reject an unrecognized <status>
  # argument BEFORE any lock/file work, not just later when it is read back. Fail fast,
  # cheap check, no partial state to unwind. This is a caller/usage error (die -> exit 64),
  # the same class as a missing arg or unknown subcommand -- distinct from the DENY (exit
  # 1) business-rule refusals below, which are about a VALID status conflicting with the
  # ledger's existing state, not about the status literal itself being unrecognized.
  case "$status" in
    pending|completed|failed) ;;
    *) die "record: status \"$status\" is not a recognized value -- must be exactly one of: pending, completed, failed (the ledger's status enum is closed; an unrecognized or corrupted value is refused, never silently written -- see the top-of-file \"status is a CLOSED, finite enum\" comment)" ;;
  esac

  mkdir -p "$LEDGER_DIR"

  # ---- lock -> validate -> merge -> atomic rename (ADR-C5; same pattern as cmd_reserve
  # above, same lock keyed on the same lock_dir -- this is what makes `record` racing
  # `reserve` on the same key safe: bd:shode-house-5cs.3 iter1 F2).
  local lockd; lockd=$(lock_dir "$bd")
  sideeffect_acquire_lock "$bd" "record"
  local lock_token="$SIDEEFFECT_LOCK_TOKEN"
  local tmp=""
  trap 'rm -f "$tmp" 2>/dev/null; lock_release "'"$lockd"'" "'"$lock_token"'"' EXIT

  rm -f "$LEDGER_DIR/.tmp.$(encode_bd "$bd")".* 2>/dev/null || true

  local lf; lf=$(ledger_file "$bd")
  validate_ledger_or_die "$lf"
  local ledger; ledger=$(read_ledger "$lf")

  local existing_op existing_status
  existing_op=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].operation // ""')
  existing_status=$(printf '%s' "$ledger" | jq -r --arg k "$key" '.[$k].status // ""')

  # ---- ledger integrity: a key must mean exactly ONE operation for its whole life.
  if [ -n "$existing_op" ] && [ "$existing_op" != "$operation" ]; then
    printf 'DENY: idempotency_key "%s" already used for operation "%s", cannot reuse for "%s" (use a new key per distinct operation)\n' \
      "$key" "$existing_op" "$operation"
    exit 1
  fi

  # ---- completed is a one-way door (this IS the "ห้ามทำซ้ำ" enforcement point):
  #   - re-recording the SAME status=completed again is an idempotent no-op (exit 0,
  #     ledger unchanged) -- exactly the "asked twice with the same key" case.
  #   - recording any OTHER status once completed is refused outright.
  if [ "$existing_status" = "completed" ]; then
    if [ "$status" = "completed" ]; then
      printf 'RECORDED (no-op): idempotency_key "%s" already completed -- ledger unchanged, side effect NOT repeated\n' "$key"
      exit 0
    fi
    printf 'DENY: idempotency_key "%s" is already completed -- cannot change status to "%s" (completed is final; use a new key for a new attempt)\n' \
      "$key" "$status"
    exit 1
  fi

  local now; now=$(timestamp)
  tmp=$(mktemp "$LEDGER_DIR/.tmp.$(encode_bd "$bd").XXXXXX")
  printf '%s' "$ledger" | jq \
    --arg k "$key" --arg op "$operation" --arg st "$status" --arg d "$detail" --arg ts "$now" \
    '.[$k] = {operation: $op, idempotency_key: $k, status: $st, detail: $d, ts: $ts}' \
    > "$tmp"
  if [ ! -s "$tmp" ] || ! jq empty "$tmp" >/dev/null 2>&1; then
    rm -f "$tmp"
    tmp=""
    die "record: generated ledger failed validation (must be non-empty valid JSON) -- this is a bug, report it"
  fi
  mv "$tmp" "$lf"
  tmp=""

  printf 'RECORDED: idempotency_key "%s" operation="%s" status="%s"\n' "$key" "$operation" "$status"
  exit 0
}

main() {
  command -v jq >/dev/null 2>&1 || die "jq required"

  local cmd="${1:-}"
  [ $# -gt 0 ] && shift
  case "$cmd" in
    check)
      [ $# -eq 2 ] || { usage; die "check: <bd-id> and <idempotency-key> required"; }
      cmd_check "$1" "$2"
      ;;
    reserve)
      [ $# -ge 3 ] || { usage; die "reserve: <bd-id> <operation> <idempotency-key> required"; }
      cmd_reserve "$1" "$2" "$3" "${4:-}"
      ;;
    record)
      [ $# -ge 4 ] || { usage; die "record: <bd-id> <operation> <idempotency-key> <status> required"; }
      cmd_record "$1" "$2" "$3" "$4" "${5:-}"
      ;;
    ""|-h|--help) usage; exit 1 ;;
    *) usage; die "unknown command '$cmd'" ;;
  esac
}

main "$@"
