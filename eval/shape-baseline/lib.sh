#!/usr/bin/env bash
# Shared launch helper for eval/shape-baseline (protocol shape-baseline-v1). Sourced, never executed.
# The fixed run conditions of the protocol live HERE and nowhere else, so every arm gets the same ones:
#   - user settings are NOT loaded (--setting-sources project,local) and no MCP server (--strict-mcp-config):
#     the user's installed plugins (incl. any installed shode-house) are not in the session
#   - the arm is the ONLY non-builtin plugin, loaded with --plugin-dir from a clean export
#   - permissions: acceptEdits inside the fixture, Bash sandboxed (no write outside the fixture, no network),
#     Read allowed on the arm's own plugin directory, nothing else pre-allowed; whatever would prompt is denied
#   - a silent hook records the fixture's working tree at each spawn start/return and after every Bash/Edit/Write
#     call of the main session and of every spawn (attribution of file changes to the thread that made them)
set -u
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0

SB_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
MAIN_MODEL="${MAIN_MODEL:-sonnet}"
EFFORT="${EFFORT:-medium}"

sb_die() { echo "!! $*" >&2; exit 3; }
sb_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# sb_settings <out.json> <snap.jsonl> [plugin-dir]
sb_settings() {
  python3 - "$1" "$2" "${3:-}" "$SB_HERE/hook-snap.py" <<'PY'
import json, sys
out, snap, plugin, hook = sys.argv[1:5]
allow = ["Bash", "Skill", "Agent", "Task"]
if plugin:
    allow.insert(0, f"Read(/{plugin}/**)")   # //abs/path form: plugin is absolute
cmd = f"SHAPE_SNAP_FILE='{snap}' python3 '{hook}'"
pre = [{"matcher": "Task|Agent", "hooks": [{"type": "command", "command": cmd}]}]
post = [{"matcher": "Task|Agent|Bash|Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": cmd}]}]
json.dump({
    "permissions": {"allow": allow, "deny": ["WebFetch", "WebSearch"]},
    "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False},
    "hooks": {"PreToolUse": pre, "PostToolUse": post},
}, open(out, "x", encoding="utf-8"), indent=1)
PY
}

# sb_launch <cwd> <out-dir> <prompt-file> <session-uuid> <max-turns> <budget-usd> <timeout-s> [extra claude args...]
# writes <out>/raw/run.jsonl, run.stderr; returns the CLI exit code
sb_launch() {
  local cwd="$1" out="$2" prompt="$3" sid="$4" turns="$5" budget="$6" timeout_s="$7"; shift 7
  local rc=0 pid dog
  mkdir -p "$out/raw"
  ( cd "$cwd" && exec env -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ID \
      -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_HOST_SESSION_ID -u CLAUDE_EFFORT -u CLAUDE_PID -u CLAUDECODE \
      -u CLAUDE_CODE_SUBAGENT_MODEL -u CLAUDE_CODE_ENTRYPOINT \
      "$CLAUDE_BIN" -p "$(cat "$prompt")" --session-id "$sid" --model "$MAIN_MODEL" --effort "$EFFORT" \
      --setting-sources project,local --strict-mcp-config --permission-mode acceptEdits \
      --max-turns "$turns" --max-budget-usd "$budget" --output-format stream-json --verbose "$@" \
      > "$out/raw/run.jsonl" 2> "$out/raw/run.stderr" < /dev/null ) &
  pid=$!
  ( sleep "$timeout_s" && echo "watchdog: ${timeout_s}s exceeded, killing $pid" >> "$out/raw/run.stderr" && kill "$pid" 2>/dev/null ) > /dev/null 2>&1 &
  dog=$!
  wait "$pid" || rc=$?
  pkill -P "$dog" 2>/dev/null; kill "$dog" 2>/dev/null; wait "$dog" 2>/dev/null
  return "$rc"
}

# sb_collect_transcript <cwd> <session-uuid> <out-dir>: read-only copy of the session transcript + sub-agent files
sb_collect_transcript() {
  local cwd="$1" sid="$2" out="$3" slug base
  slug="$(printf '%s' "$(cd "$cwd" && pwd -P)" | sed 's/[^A-Za-z0-9]/-/g')"
  base="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/$slug"
  mkdir -p "$out/raw/transcript"
  if [ -f "$base/$sid.jsonl" ]; then
    cp "$base/$sid.jsonl" "$out/raw/transcript/main.jsonl"
    [ -d "$base/$sid/subagents" ] && cp -R "$base/$sid/subagents" "$out/raw/transcript/subagents"
    echo "$base/$sid.jsonl" > "$out/raw/transcript/SOURCE"
  else
    echo "!! transcript not found: $base/$sid.jsonl" >&2; return 1
  fi
  if [ -d "$base/memory" ] && [ -n "$(ls -A "$base/memory" 2>/dev/null)" ]; then
    ls -la "$base/memory" > "$out/raw/transcript/AUTO-MEMORY-NOT-EMPTY"
  fi
}
