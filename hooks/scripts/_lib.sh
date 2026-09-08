#!/usr/bin/env bash
# _lib.sh -- shared helpers for shode-house hook scripts (bd: shode-roadmap/C-A7)
#
# NOT itself referenced by hooks/hooks.json (AC-S9 only constrains what hooks.json
# invokes) -- this file is `source`d by session-start.sh and stop-integrity.sh, never
# executed directly (kept non-executable, mode 644, to make that explicit). Shebang here
# is present only so `shellcheck` can be run on this file standalone (SC2148); it has no
# effect when the file is sourced.
#
# Deps: bash + jq (caller must have already confirmed `command -v jq` before sourcing
# these functions -- neither function here re-checks it).

shode_json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

# shode_torn_write_scan <shode_dir>
#
# Read-only torn-write detection across every bd tracked under
# "<shode_dir>/state/*.json" -- reimplements, in miniature, the exact same shape check
# scripts/workflow-state.sh's cmd_resume() performs (last journal line claims an accepted
# from->to transition that state.json's current_phase never picked up -- ADR-C5's
# documented crash window: journal-append succeeded, the rename to state.json did not).
#
# This is deliberately reimplemented here rather than shelling out to
# `workflow-state.sh resume <bd>`, because resume() acquires the advance lock and appends
# its OWN journal line as a side effect on every call -- calling that automatically from
# every SessionStart/Stop/SubagentStop would turn a passive advisory hook into a second
# writer racing (and spamming the journal of) the real one. This function only READS; the
# authoritative fix stays `workflow-state.sh resume <bd>`, run deliberately.
#
# NOTE (found and fixed during this task's own testing, not merely assumed): comparing
# state.json's `.seq` counter against the journal's last-line `.seq` is NOT a valid
# integrity signal on this codebase -- `cmd_init`/`cmd_resume` append journal lines
# without ever bumping `.seq` on state.json, so the two counters diverge by construction
# on every fresh bd and every resume call, long before anything is actually wrong. The
# shape check below (from/to/result comparison, matching cmd_resume()'s own definition of
# "torn") is what stays true during healthy operation and only fires on a real torn
# write -- verified live against a real `workflow-state.sh init` + a crafted torn journal
# line in this task's own smoke test.
#
# Prints a comma-joined list of affected bd-ids to stdout (empty string if none).
shode_torn_write_scan() {
  local shode_dir="$1" state_dir journal_dir sf bd cur encoded jf
  local last_line last_result last_from last_to torn_list=""
  state_dir="$shode_dir/state"
  journal_dir="$shode_dir/journal"

  for sf in "$state_dir"/*.json; do
    [ -e "$sf" ] || continue
    case "$sf" in *".tmp."*|*".rejected") continue ;;
    esac
    bd=$(jq -r '.bd_id // empty' "$sf" 2>/dev/null) || continue
    cur=$(jq -r '.current_phase // empty' "$sf" 2>/dev/null) || continue
    [ -n "$bd" ] && [ -n "$cur" ] || continue

    encoded=$(printf '%s' "$bd" | sed 's#/#--#g')
    jf="$journal_dir/$encoded.jsonl"
    [ -f "$jf" ] && [ -s "$jf" ] || continue

    last_line=$(tail -n 1 "$jf")
    last_result=$(printf '%s' "$last_line" | jq -r '.result // empty' 2>/dev/null)
    last_from=$(printf '%s' "$last_line" | jq -r '.from // empty' 2>/dev/null)
    last_to=$(printf '%s' "$last_line" | jq -r '.to // empty' 2>/dev/null)

    if [ "$last_result" = "accept" ] && [ "$last_from" = "$cur" ] && \
       [ -n "$last_to" ] && [ "$last_to" != "$cur" ] && [ "$last_to" != "$last_from" ]; then
      torn_list="${torn_list}${torn_list:+, }$bd"
    fi
  done

  printf '%s' "$torn_list"
}
