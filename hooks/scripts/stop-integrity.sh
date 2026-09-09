#!/usr/bin/env bash
# stop-integrity.sh -- Stop / SubagentStop hook (bd: shode-roadmap/C-A7; ADR-C2 event 4)
#
# WARN-ONLY in this milestone, by explicit ADR decision (02-sara-adr-1a.md Sec 3
# ADR-C2 event 4): "การ block Stop บังคับให้ Claude ทำงานต่อ เสี่ยง infinite loop; จะยกเป็น
# block ได้ต่อเมื่อยืนยัน loop-guard semantics ของ Stop hook จากเอกสาร/ทดลองก่อน" (Open
# Question 3, still unresolved) -- so this script NEVER exits non-zero and NEVER emits a
# blocking `decision`. It only ever adds an advisory `systemMessage`, then always exits 0.
#
# What "integrity check" means here (ADR-C2 event 4's own wording is "ตรวจ state hash
# ตรงกับ journal entry ล่าสุด"): this reuses the exact SAME torn-write shape check
# session-start.sh runs (hooks/scripts/_lib.sh shode_torn_write_scan) -- last journal line
# claims an accepted from->to transition that state.json's current_phase never picked up.
# Stop/SubagentStop fires far more often than SessionStart (every turn, not just once per
# session), so running the same check here catches drift that happens mid-session instead
# of only at the next session's start.
#
# An EARLIER version of this script compared state.json's `.seq` counter against the
# journal's last-line `.seq` directly, on the theory that the two should always match.
# That was WRONG and caught live during this task's own testing: `workflow-state.sh
# init`/`resume` append journal lines without ever bumping state.json's `.seq`, so the two
# counters diverge by construction on every fresh bd -- a seq-equality check would have
# warned on every single Stop for a bd that just ran `init` and nothing else, which is not
# an integrity problem at all. See hooks/scripts/_lib.sh's shode_torn_write_scan comment
# for the corrected signal and the live evidence that it does NOT false-positive on a
# clean init.
#
# Deps: bash + jq. Read-only: never writes state/journal/canary. Writes `.degraded` only
# on an actual finding (mirrors session-start.sh's own convention so the two hooks'
# findings both land in the one file an operator/agent would check).

set -u -o pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks/scripts/_lib.sh
. "$SELF_DIR/_lib.sh"

proj="${CLAUDE_PROJECT_DIR:-$PWD}"
shode_dir="$proj/.shode-house"
state_dir="$shode_dir/state"

# Engagement guard -- pure bash first (same convention as every other script in this
# suite). Fires on both Stop and SubagentStop, same script, same behavior for each.
[ -d "$state_dir" ] || exit 0

# jq missing -- session-start.sh already announced DEGRADED for this session; do not
# re-announce here, just skip silently (still exit 0, never blocks).
command -v jq >/dev/null 2>&1 || exit 0

torn_list=$(shode_torn_write_scan "$shode_dir")

if [ -n "$torn_list" ]; then
  esc=$(shode_json_escape "$torn_list")
  printf '{"systemMessage":"shode-house: TORN WRITE suspected on [%s] (warn-only, ADR-C2 -- not blocking): journal shows an accepted transition state.json never picked up. Run `workflow-state.sh resume <bd>` before trusting current_phase."}\n' "$esc"
fi

exit 0
