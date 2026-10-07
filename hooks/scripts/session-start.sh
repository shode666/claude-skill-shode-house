#!/usr/bin/env bash
# session-start.sh -- SessionStart hook (bd: shode-roadmap/C-A7; ADR-C2 event 1, ADR-C8;
# enforcement status: UD U23 item 2, shode-house-v7u.4.48)
#
# SessionStart cannot block (02-sara-adr-1a.md Sec "REQUIRED-BEFORE B" table) -- this
# script only ever exits 0. Its job is advisory/preparatory:
#   1. Enforcement status, in EVERY project (the .git and designer rules of the scope guard
#      run with or without an engagement): ENFORCED only when every prerequisite of the two
#      write guards is ready, ADVISORY-ONLY otherwise, naming the first one that is not.
#      Prerequisites, in the order the guards meet them:
#        a. jq on PATH                         -- missing: both guards fail OPEN (Hook Charter
#                                                 Sec 7, unchanged)
#        b. hooks/scripts/_casefold.sh loads   -- missing: both guards fail OPEN
#        c. jq RUNS the kind of program the    -- not executable, crashing or built without
#           guards run (JSON input, a regex       regex support: the guards cannot judge hook
#           test, the guards' HOME=/dev/null      input and DENY it (UD U19)
#           and LC_ALL=C) ...
#           ... and answers within              -- slower, or hanging: a guard call can run past
#           JQ_PROBE_LIMIT (0.25 s)               the 5 s hook timeout, which lets the call
#                                                 through (Sentinel final F4; see below)
#        d. macOS only (or a platform that     -- not runnable: the scope check refuses a
#           cannot be determined): /usr/bin/perl  non-ASCII path whose collision check needs
#           with Unicode::Normalize, through the  NFC (F-6, UD U12)
#           guards' own _scope_nfc_batch_deny
#      The guards' verdict logic is not touched here; this only reports it. Every message
#      is a static string (no environment value and no path is echoed). Every probe and the
#      torn-write scan below run under a watchdog that kills their whole process group, so
#      the hook ends inside its 10 s timeout (hooks/hooks.json): jq 2 x 0.25 s + NFC 2 s +
#      torn scan 5 s.
#   2. Engagement-only (.shode-house/state exists; a project that never ran /init gets the
#      status line and nothing else -- no file is written there):
#      - .degraded gets a line when the status is ADVISORY-ONLY (ADR-C3/C8)
#      - canary stamp (.hooks-alive) -- availability signal only, NOT an integrity proof
#        (S1 in 08-sentinel-threat-model-hooks.md -- anyone can `touch` a plain file)
#      - read-only torn-write scan (hooks/scripts/_lib.sh shode_torn_write_scan) when jq
#        runs. See that file's header for why this is not `workflow-state.sh resume`.
#
# Output contract: exactly ONE line of JSON on stdout, every session: `systemMessage` (shown
# to the user) and `hookSpecificOutput.additionalContext` (added to the model's context)
# carry the same text -- the status line, plus the torn-write warning when there is one.
#
# Deps: bash; jq, _casefold.sh and (macOS) /usr/bin/perl are what this script CHECKS.

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks/scripts/_lib.sh
. "$SELF_DIR/_lib.sh"

# The guards clear EXECIGNORE before their own `command -v jq` (UD R90/R91); do the same so
# the status reports what the guards will see.
unset EXECIGNORE

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
shode_dir="$proj/.shode-house"
state_dir="$shode_dir/state"
canary="$state_dir/.hooks-alive"
degraded="$state_dir/.degraded"
engaged=0
[ -d "$state_dir" ] && engaged=1

# run_bounded <seconds> <command or function> [args...] -- runs the command in its own process
# group (set -m) with a watchdog that SIGKILLs that whole group after <seconds>; stdout passes
# through. Killing the group, not one pid, matters: a jq wrapper that forks (runs jq or a
# sleep as a child instead of exec) would otherwise keep the $(...) pipe open after its own
# pid is killed (Chris final Info). As soon as the command ends, the watchdog's group (its sleep
# included) and the command's own group are killed: a jq wrapper that leaves a background
# child holding stdout would otherwise keep the $(...) pipe open after the command itself
# ended (Sentinel final-2 N2), so nothing outlives the call. Returns the command's status,
# 137 when the watchdog killed it. A sleep without fractions falls back to whole seconds
# (1 s); no sleep at all means no watchdog and never an early kill.
run_bounded() {
  local limit="$1"; shift
  (
    set -m
    "$@" &
    cpid=$!
    ( { sleep "$limit" 2>/dev/null || sleep 1 2>/dev/null; } || exit 0
      kill -9 -- -"$cpid" ) >/dev/null 2>&1 &
    wpid=$!
    wait "$cpid"; rc=$?
    kill -9 -- -"$wpid" 2>/dev/null
    kill -9 -- -"$cpid" 2>/dev/null
    exit "$rc"
  ) 2>/dev/null
}

# JQ_PROBE_LIMIT -- the longest one jq run may take for ENFORCED (Sentinel final F4). Derived
# from the guards' jq calls per hook call (counted with a counting jq shim, d=0):
#   Bash, a bind command    11 in a row, no time check between them (scope guard 4:
#                           tool_name, command, agent_id, agent_type; scope-check.sh
#                           --bind-record 7); any other Bash call 2
#   Write/Edit/NotebookEdit scope guard: 4 before its scope phase (tool_name, file_path,
#                           agent_type, agent_id), then 3 per state file and the scope-check
#                           calls, all inside the 3 s scope budget that DENIES when spent; a
#                           step already running when it is spent adds up to ~3 more
#                           state guard: 1
# Worst case per call d: bind 11 d; Write about 3 s + 3-4 d. The hook timeout is 5 s and a
# hook cut off by it lets the call through. Measured with a jq shim sleeping 0.25 s per call:
# bind 3.0 s, Write <= 1.9 s (bash 3.2) and <= 3.6 s (bash 5.3), state guard 0.3 s, so at
# least 1.4 s of margin. An ordinary jq run takes about 10-20 ms. A slower jq that still passes keeps the
# guards inside the timeout but can make a Write run out of its scope budget (a DENY, never
# an allow).
JQ_PROBE_LIMIT=0.25

# jq_probe_run -- the guards' kind of jq program: JSON input, the guards' control-character
# regex class, under the guards' HOME=/dev/null and LC_ALL=C. Prints "true" when jq works.
# Called only through run_bounded, so the exports stay in that background job's own shell.
# They are exports, not a "LC_ALL=C jq" prefix: Homebrew bash 5.3 measured a SIGSEGV in a
# set -m background job in about 1 of 12 fresh runs with that prefix form; with the export
# form 0 of 1200 fresh session-start runs (bash 5.3 and 3.2, real jq and a 0.1 s wrapper).
jq_probe_run() {
  export HOME=/dev/null LC_ALL=C
  jq -r '.p | test("[\u0000-\u001f\u007f-\u009f]") | tostring' <<<'{"p":"a\u0001b"}' 2>/dev/null
}

# probe_jq -- 0 when jq answers correctly within JQ_PROBE_LIMIT; 2 when it was still running
# at the limit (slow or hanging) twice in a row; 1 for any other failure. The one retry is for
# a cold start: the first run of a program after it was installed or after a reboot can take
# longer on macOS (here a new jq wrapper with a 0.1 s sleep took over 0.25 s on its first
# run and about 0.12 s after), and the guards run jq warm.
probe_jq() {
  local out rc
  for _ in 1 2; do
    out=$(run_bounded "$JQ_PROBE_LIMIT" jq_probe_run); rc=$?
    [ "$rc" -eq 137 ] || break
  done
  [ "$rc" -eq 137 ] && return 2
  [ "$rc" -eq 0 ] && [ "$out" = "true" ]
}

# probe_nfc -- 0 when the guards' own NFC normaliser gives the right bytes for a known NFD
# sample (Chris final Info: not only that perl ran). U+0065 U+0301 must come back as U+00E9
# on macOS, or where the platform cannot be determined (both use the normaliser); elsewhere
# the candidate is passed through unchanged and no process starts.
probe_nfc() {
  local LC_ALL=C out want
  out=$(run_bounded 2 _scope_nfc_batch_deny $'e\xcc\x81' </dev/null | tr '\000' '|') || return 1
  if _scope_is_macos; then want=$'C\xc3\xa9|E|'; else want=$'Ce\xcc\x81|E|'; fi
  [ "$out" = "$want" ]
}

# torn_ids_shown <comma-joined list> -- the bd ids of the torn-write scan come from the
# project's own state files and reach the model's context (additionalContext), so each id is
# shown only when it is 1-64 bytes of [A-Za-z0-9._/:-]; any other id is replaced by a static
# placeholder. At most TORN_IDS_MAX ids are listed, then "+N more" (Sentinel final I1).
# Splitting copies the rest of the list at each step, so its cost grows with the square of
# the list: only the first TORN_RAW_MAX bytes are read (Sentinel final-2 N1: 200 crafted torn
# pairs took SessionStart past its 10 s timeout). A longer list ends in "+more (...)": the id
# cut at that boundary is not shown and the rest is not counted.
TORN_IDS_MAX=10
TORN_RAW_MAX=4096
torn_ids_shown() {
  local LC_ALL=C rest="$1" id shown="" n=0 cut=0
  if [ "${#rest}" -gt "$TORN_RAW_MAX" ]; then
    cut=1; rest="${rest:0:$TORN_RAW_MAX}"
    case "$rest" in *', '*) rest="${rest%, *}" ;; esac   # drop the id cut at the boundary
  fi
  while [ -n "$rest" ]; do
    case "$rest" in
      *', '*) id="${rest%%, *}"; rest="${rest#*, }" ;;
      *) id="$rest"; rest="" ;;
    esac
    n=$((n + 1))
    if [ "$n" -gt "$TORN_IDS_MAX" ]; then
      [ "$cut" -eq 0 ] || break   # not counted when the list was cut
      continue
    fi
    case "$id" in
      ''|*[!A-Za-z0-9._/:-]*) id='(id not shown: characters outside A-Z a-z 0-9 . _ / : -)' ;;
      *) [ "${#id}" -le 64 ] || id='(id not shown: longer than 64 characters)' ;;
    esac
    shown="$shown${shown:+, }$id"
  done
  if [ "$cut" -eq 1 ]; then
    shown="$shown${shown:+, }+more (the list is longer than $TORN_RAW_MAX bytes; the rest is not counted)"
  elif [ "$n" -gt "$TORN_IDS_MAX" ]; then
    shown="$shown, +$((n - TORN_IDS_MAX)) more"
  fi
  printf '%s' "$shown"
}

casefold_ok=0
# shellcheck source=hooks/scripts/_casefold.sh
. "$SELF_DIR/_casefold.sh" 2>/dev/null && casefold_ok=1

status=ENFORCED
reason=""
jq_runs=0
jq_probe_rc=1
if ! command -v jq >/dev/null 2>&1; then
  status=ADVISORY-ONLY
  reason='jq not found on PATH -- the Write/Edit scope and state guards are NOT enforced: they let every write through (fail-open), and the .git and designer path rules are off too. Install jq (brew install jq / apt install jq) and start a new session.'
elif [ "$casefold_ok" -eq 0 ]; then
  status=ADVISORY-ONLY
  reason='hooks/scripts/_casefold.sh is missing next to the hooks (broken install) -- the Write/Edit scope and state guards are NOT enforced: they let every write through (fail-open). Reinstall the plugin and start a new session.'
else
  probe_jq; jq_probe_rc=$?
fi
if [ "$status" = ENFORCED ] && [ "$jq_probe_rc" -eq 2 ]; then
  status=ADVISORY-ONLY
  reason='jq is on PATH but did not answer a test run within 0.25 s (too slow, or hanging) -- the Write/Edit scope and state guards are NOT enforced: they call jq many times per tool call (up to 11 in a row with no time check, on a Bash bind), so a guard call can run past the 5 s hook timeout, which lets the call through, or refuse a write whose scope check runs out of time. Repair or reinstall jq (or relieve the load on this machine) and start a new session.'
elif [ "$status" = ENFORCED ] && [ "$jq_probe_rc" -ne 0 ]; then
  status=ADVISORY-ONLY
  reason='jq is on PATH but failed a test run (not executable, crashing, or built without regex support) -- the Write/Edit scope and state guards are NOT enforced as designed: they cannot judge hook input, so they refuse every Write, Edit and NotebookEdit (the scope guard also every Bash call) until jq runs. Repair or reinstall jq and start a new session.'
elif [ "$status" = ENFORCED ]; then
  jq_runs=1
  if ! probe_nfc; then
    status=ADVISORY-ONLY
    reason='/usr/bin/perl with Unicode::Normalize did not run (needed on macOS for the Unicode NFC collision check) -- the Write/Edit scope guard is NOT enforced as designed for non-ASCII paths: such a write that needs the collision check is refused. ASCII paths are still judged.'
  fi
fi

if [ "$status" = ENFORCED ]; then
  msg='shode-house hooks: ENFORCED -- jq runs and every guard prerequisite is present, so the Write/Edit/NotebookEdit scope, state and .git guards judge writes where hooks execute (defence in depth, not a guarantee).'
else
  msg="shode-house hooks: ADVISORY-ONLY -- $reason"
fi

if [ "$engaged" -eq 1 ]; then
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if [ "$status" != ENFORCED ]; then
    printf '%s session-start.sh: %s\n' "$ts" "$msg" > "$degraded" 2>/dev/null
  fi
  printf '%s\n' "$ts" > "$canary" 2>/dev/null
  if [ "$jq_runs" -eq 1 ]; then
    # The bd ids come from the project's own state files: torn_ids_shown lets through only
    # ids of [A-Za-z0-9._/:-]{1,64}, at most TORN_IDS_MAX of them (no quote, backslash,
    # space or control character reaches the JSON or the model's context). The scan runs
    # jq per state file, so it is bounded too (5 s); a scan cut off says so.
    torn_raw=$(run_bounded 5 shode_torn_write_scan "$shode_dir"); torn_rc=$?
    torn_list=$(torn_ids_shown "$torn_raw")
    if [ "$torn_rc" -eq 137 ]; then
      printf '%s session-start.sh: torn-write scan cut off after 5 s\n' "$ts" >> "$degraded" 2>/dev/null
      msg="$msg shode-house: the torn-write check did not finish within 5 s (slow jq or many state files), so a torn write is not ruled out -- run \`workflow-state.sh resume <bd>\` for a bd whose session ended abnormally before trusting current_phase."
    elif [ -n "$torn_list" ]; then
      printf '%s session-start.sh: torn write suspected for: %s\n' "$ts" "$torn_list" >> "$degraded" 2>/dev/null
      msg="$msg shode-house: TORN WRITE suspected on [$torn_list] -- journal shows an accepted transition state.json never picked up (crash between journal-append and atomic rename, ADR-C5). Run \`workflow-state.sh resume <bd>\` before trusting current_phase; do not continue automatically."
    fi
  fi
fi

# msg holds only static text and the filtered torn list.
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg" "$msg"
exit 0
