#!/usr/bin/env bash
# collision-scan.sh -- F-10 collision detection hook, registration wrapper (W8; ADR iter 5
# 5.7, addendum-1 X6). Registered in hooks/hooks.json on SessionStart and on PreToolUse for
# the spawn tool and Skill, with the plugin root quoted.
#
# This wrapper exists for the documented fail-open when python3 is missing or cannot start.
# A bare `python3 "<root>/hooks/scripts/collision-scan.py"` registration exits 127 from the
# host shell when python3 is absent; this wrapper instead exits 0 with a stderr note, so
# the session proceeds WITHOUT shadowing detection and says so. Everything else is in
# collision-scan.py (stdlib only, no shell, no network, no writes).
#
# WHERE THIS RUNS: only where hooks execute -- Claude Code with this plugin's
# hooks/hooks.json loaded and not switched off by `disableAllHooks: true` (a project can
# set that, and then no plugin hook runs at all). Not in the generated tree; unconfirmed in
# Cowork. Detection and accident prevention, defence in depth -- not a guarantee.
#
# `python3 -I -S`: isolated mode, so PYTHON* environment variables, the user site directory
# and the current directory never reach the interpreter; -S skips the `site` import (the
# scanner is stdlib-only; measured 67 ms -> 15 ms per call on the maintainer's machine).
# Which python3 runs is still the host shell's PATH lookup (a residual for the README
# security note).

set -u

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  printf 'shode-house: collision-scan skipped -- python3 not found on PATH; project files that shadow a shode-house: skill, command or style are NOT detected this session (fail-open)\n' >&2
  exit 0
fi

# Not `exec`: Python reports its own start failures with exit 2 (a missing or unreadable
# collision-scan.py, an interpreter that rejects -I), and 2 is the PreToolUse deny code.
# The scanner signals a deny with 3, a code Python never uses on its own; only 3 becomes 2.
# Every other non-zero code is a start failure or crash: warn and fail open (Sentinel W8 F3,
# UD R63). stdin, stdout and stderr pass straight through to the child.
python3 -I -S "$SELF_DIR/collision-scan.py"
rc=$?
case "$rc" in
  0) exit 0 ;;
  3) exit 2 ;;
  *)
    printf 'shode-house: collision-scan skipped -- python3 could not run the scanner (exit %s); project files that shadow a shode-house: skill, command or style are NOT detected for this call (fail-open)\n' "$rc" >&2
    exit 0 ;;
esac
