#!/usr/bin/env bash
# session-start.sh -- SessionStart hook (bd: shode-roadmap/C-A7; ADR-C2 event 1, ADR-C8)
#
# SessionStart cannot block (02-sara-adr-1a.md Sec "REQUIRED-BEFORE B" table) -- this
# script only ever exits 0. Its job is entirely advisory/preparatory:
#   1. Engagement guard (only act when this project has .shode-house/state/)
#   2. jq prereq check -> write .degraded LOUDLY if missing (ADR-C3), never block startup
#   3. Canary stamp (.hooks-alive) -- availability signal only, NOT an integrity proof
#      (S1 in 08-sentinel-threat-model-hooks.md -- anyone can `touch` a plain file; this
#      is accepted and documented, not a security control)
#   4. Read-only torn-write scan (see hooks/scripts/_lib.sh shode_torn_write_scan) across
#      every bd currently tracked. See that file's header for why this is reimplemented
#      read-only here instead of shelling out to `workflow-state.sh resume`.
#
# Output contract: normally 100% silent (0 byte context cost per session -- 02-sara-adr-1a.md
# Sec 1 NFR "Context budget impact: 0 byte preload ... โผล่เฉพาะ systemMessage ตอน
# violation"). On a problem, prints ONE line of JSON with a `systemMessage` field --
# Claude Code surfaces that to the user without blocking SessionStart.
#
# Deps: bash + jq (jq itself is prereq-checked below, not assumed).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks/scripts/_lib.sh
. "$SELF_DIR/_lib.sh"

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
shode_dir="$proj/.shode-house"
state_dir="$shode_dir/state"

# 1) Engagement guard -- same convention as scripts/workflow-state.sh / scripts/scope-check.sh:
#    a project that never ran /init pays zero cost, zero side effect.
[ -d "$state_dir" ] || exit 0

canary="$state_dir/.hooks-alive"
degraded="$state_dir/.degraded"

# 2) jq prereq (ADR-C3: bash+jq only, jq is a NEW end-user dependency this milestone
#    introduces). Missing jq degrades the WHOLE enforcement layer (guard-state-write.sh
#    also fails open without it) -- announce it loudly instead of leaving correctness to
#    silently vanish (ADR-C8 layer 1: the canary/.degraded pair IS the announcement
#    channel the discipline-layer prompt is meant to read; wiring that read is Bella/Sara
#    follow-up per 02-sara-adr-1a.md Sec 8 ADR-C7 hand-off, out of this task's scope).
if ! command -v jq >/dev/null 2>&1; then
  printf '%s session-start.sh: jq not found on PATH -- state/journal enforcement DEGRADED (install: brew install jq / apt install jq)\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$degraded" 2>/dev/null
  printf '{"systemMessage":"shode-house: state enforcement DEGRADED (jq not found on PATH) -- guard hooks fall back to advisory-only; run workflow-state.sh manually before every phase transition until jq is installed"}\n'
  exit 0
fi

# 3) Canary stamp -- written on every successful SessionStart run, jq present or not
#    (moved above the jq branch's exit so both paths stamp it -- a fresh timestamp here
#    means "SessionStart ran this session", independent of whether jq is present).
date -u +%Y-%m-%dT%H:%M:%SZ > "$canary" 2>/dev/null

# 4) Torn-write scan (read-only, see hooks/scripts/_lib.sh).
torn_list=$(shode_torn_write_scan "$shode_dir")

if [ -n "$torn_list" ]; then
  printf '%s session-start.sh: torn write suspected for: %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$torn_list" >> "$degraded" 2>/dev/null
  esc=$(shode_json_escape "$torn_list")
  printf '{"systemMessage":"shode-house: TORN WRITE suspected on [%s] -- journal shows an accepted transition state.json never picked up (crash between journal-append and atomic rename, ADR-C5). Run `workflow-state.sh resume <bd>` before trusting current_phase; do not continue automatically."}\n' "$esc"
fi

exit 0
