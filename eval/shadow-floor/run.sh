#!/usr/bin/env bash
# One live shadow-floor run (P2 re-run, UD R26; v7u.14). LIVE MODEL CALL: run only with the user's go-ahead.
#   bash eval/shadow-floor/run.sh <kit-dir> <tier-suffix> <fixture> <n> <out-root>
#   tier-suffix: sonnet | opus | fable-5      fixture: a name in fixtures.json
# Env: CLAUDE_BIN (the claude binary) · CLAUDE_PROJECTS (default $HOME/.claude/projects, where the host writes
#      session transcripts; read only, to copy this run's sub-agent transcript) · MAINMODEL (default sonnet)
# Writes <out-root>/<tier>__<fixture>__<n>/{stream.jsonl,stream.err,subagents/} ; refuses an existing run dir.
# Same flags as W0 round 4: headless, max 3 turns, project+local setting sources only, strict MCP config,
# --plugin-dir <kit>/pw; the session env variables of a parent Claude Code session are dropped.
set -u
kit="${1:?kit dir}"; tier="${2:?tier}"; fx="${3:?fixture}"; n="${4:?n}"; root="${5:?out root}"
: "${CLAUDE_BIN:?CLAUDE_BIN = claude binary}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
read -r project agent mode skill < <(python3 - "$here/fixtures.json" "$fx" "$tier" <<'PY'
import json, sys
spec = json.load(open(sys.argv[1]))
f = next((x for x in spec["fixtures"] if x["name"] == sys.argv[2]), None)
if f is None:
    sys.exit("unknown fixture " + sys.argv[2])
agent = ("nofloor-sonnet" if sys.argv[3] == "control" else "%s-%s" % (f["agent"], sys.argv[3]))
print(f["project"], "pw:" + agent, f["mode"], f["skill"])
PY
)
[ -n "${project:-}" ] && [ -n "${skill:-}" ] || { echo "unknown fixture: $fx" >&2; exit 2; }
out="$root/${tier}__${fx}__${n}"
[ -e "$out" ] && { echo "refuse: $out exists" >&2; exit 2; }
mkdir -p "$out/subagents"
deleg="$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s["delegation"][sys.argv[2]].replace("{SKILL}", sys.argv[3]))' "$here/fixtures.json" "$mode" "$skill")"
prompt="Call the Agent tool exactly once, with subagent_type \"$agent\", description \"probe\", and this prompt verbatim (two lines):
$deleg
After it returns, reply with its final message verbatim and nothing else."
( cd "$kit/$project" && env -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ID \
    -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_HOST_SESSION_ID -u CLAUDE_CODE_ENTRYPOINT \
    "$CLAUDE_BIN" -p "$prompt" --output-format stream-json --verbose --max-turns 3 --model "${MAINMODEL:-sonnet}" \
    --setting-sources project,local --strict-mcp-config --plugin-dir "$kit/pw" < /dev/null \
    > "$out/stream.jsonl" 2> "$out/stream.err" )
rc=$?
sid="$(python3 -c 'import json,sys
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except ValueError: continue
    if e.get("type")=="system" and e.get("subtype")=="init": print(e["session_id"]); break' "$out/stream.jsonl")"
for f in "${CLAUDE_PROJECTS:-$HOME/.claude/projects}"/*/"$sid"/subagents/agent-*.jsonl; do
  [ -f "$f" ] && cp "$f" "$out/subagents/"
done
echo "== $tier $fx $n exit=$rc session=$sid"
