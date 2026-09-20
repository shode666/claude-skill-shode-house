#!/usr/bin/env bash
# Shared helpers for eval/run-e01.sh and eval/run-probes.sh (3.17 live scenario runs).
# Sourced, never executed. Rules this file encodes (RUNBOOK "v3.17 core matrix"):
#   - one NEW directory per run; an existing target is refused, evidence is never truncated
#   - the fixture project is created under $TMPDIR, never inside the plugin repo
#   - every run that starts is kept and scored (exit 0 PASS / 1 FAIL / 2 UNSCORABLE); a FAIL is never retried
#   - the runner builds and records; it does not judge (verdicts come from scripts/team-run-check.py only)
#   - do not edit these scripts while a run is in progress
# Env overrides: CLAUDE_BIN (default claude) · PLUGIN_REF (git ref to test instead of the working
#   tree, extracted read-only with `git archive`) · RUN_TIMEOUT_S · MAX_BUDGET_USD · PROBE_BLOCK_SPAWN=0 ·
#   PROBE_FILE (external scenarios JSON, e.g. a held-out set outside the repo; prompts = inline `prompt_text`
#   or `prompt` paths relative to that file; nothing is copied into the repo)

set -u
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
if [ -n "${PROBE_FILE:-}" ]; then
  [ -f "$PROBE_FILE" ] || { echo "!! PROBE_FILE not found: $PROBE_FILE" >&2; exit 3; }
  SCENARIOS="$(cd "$(dirname "$PROBE_FILE")" && pwd -P)/$(basename "$PROBE_FILE")"
else
  SCENARIOS="$REPO/eval/scenarios/golden.json"
fi
PROMPT_BASE="$(dirname "$SCENARIOS")"; [ -n "${PROBE_FILE:-}" ] || PROMPT_BASE="$REPO"
TMPROOT="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
PLUGIN_DIR="" PLUGIN_SHA="" PLUGIN_DIRTY="" CLI_VERSION="" CLI_HELP=""

die() { echo "!! $*" >&2; exit 3; }
utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

preflight() {
  command -v "$CLAUDE_BIN" >/dev/null 2>&1 || die "claude CLI not found: $CLAUDE_BIN (set CLAUDE_BIN)"
  command -v python3 >/dev/null 2>&1 || die "python3 not found"
  command -v git >/dev/null 2>&1 || die "git not found"
  case "$TMPROOT/" in "$REPO"/*) die "TMPDIR ($TMPROOT) is inside the plugin repo" ;; esac
  CLI_VERSION="$("$CLAUDE_BIN" --version 2>/dev/null | head -1)"
  CLI_HELP="$("$CLAUDE_BIN" --help 2>/dev/null || true)"
  if [ -n "${PLUGIN_REF:-}" ]; then
    PLUGIN_SHA="$(git -C "$REPO" rev-parse --verify "$PLUGIN_REF^{commit}")" || die "bad PLUGIN_REF=$PLUGIN_REF"
    PLUGIN_DIR="$(mktemp -d "$TMPROOT/shode-plugin.XXXXXX")" || die "mktemp failed"
    git -C "$REPO" archive "$PLUGIN_SHA" | tar -x -C "$PLUGIN_DIR" || die "git archive $PLUGIN_REF failed"
    PLUGIN_DIRTY=false
  else
    PLUGIN_DIR="$REPO"
    PLUGIN_SHA="$(git -C "$REPO" rev-parse HEAD)"
    if [ -n "$(git -C "$REPO" status --porcelain -- agents commands skills hooks references output-styles .claude-plugin)" ]
    then PLUGIN_DIRTY=true; else PLUGIN_DIRTY=false; fi
  fi
  [ -f "$PLUGIN_DIR/.claude-plugin/plugin.json" ] || die "no .claude-plugin/plugin.json under $PLUGIN_DIR"
}

cli_has() { printf '%s' "$CLI_HELP" | grep -q -- "$1"; }

# scenario_field <id> <key> [default]   (top-level scenario keys: kind, prompt, max_turns)
scenario_field() {
  python3 - "$SCENARIOS" "$1" "$2" "${3:-}" <<'PY'
import json, sys
path, ident, key, default = sys.argv[1:5]
data = json.load(open(path, encoding="utf-8"))
for s in (data["scenarios"] if isinstance(data, dict) else data):   # {"scenarios": [...]} or a bare list
    if s.get("id") == ident:
        value = s.get(key, default)
        print(" ".join(map(str, value)) if isinstance(value, list) else value); break
else:
    sys.exit(f"scenario {ident} not found")
PY
}

# extract_prompt <prompt.md> <out.txt>: first fenced block after the "## Prompt" heading, verbatim
extract_prompt() {
  python3 - "$1" "$2" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"^## Prompt[^\n]*\n+```[^\n]*\n(.*?)\n```", text, re.S | re.M)
if not m or not m.group(1).strip():
    sys.exit(f"{sys.argv[1]}: no fenced block under '## Prompt'")
open(sys.argv[2], "x", encoding="utf-8").write(m.group(1))
PY
}

# write_prompt <id> <out.txt>: inline `prompt_text`, else the fenced block of the scenario's `prompt` file
write_prompt() {
  local rel
  if [ "$(scenario_field "$1" prompt_text __none__)" != __none__ ]; then
    python3 - "$SCENARIOS" "$1" "$2" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
text = next(s["prompt_text"] for s in (data["scenarios"] if isinstance(data, dict) else data) if s.get("id") == sys.argv[2])
if not isinstance(text, str) or not text.strip():
    sys.exit("empty prompt_text")
open(sys.argv[3], "x", encoding="utf-8").write(text)
PY
    return $?
  fi
  rel="$(scenario_field "$1" prompt)" || return 1
  [ -f "$PROMPT_BASE/$rel" ] || { echo "!! $1: prompt file missing: $PROMPT_BASE/$rel" >&2; return 1; }
  PROMPT_FILE="$PROMPT_BASE/$rel"
  extract_prompt "$PROMPT_FILE" "$2"
}

# run_state <run-dir> -> complete | infra:<subtype> | incomplete | absent
#   complete   = last result is success / error_max_turns: behaviour evidence, never re-run, never overwritten
#   infra:...  = any other result (error_during_execution, 429, credits, budget, success+is_error): NOT behaviour,
#                kept as evidence, never scored as PASS/FAIL, the slot is re-run after the operator resumes
#   incomplete = no result event (crash / kill)
run_state() {
  python3 - "$1" <<'PY'
import json, os, sys
path = os.path.join(sys.argv[1], "run.jsonl")
if not os.path.isdir(sys.argv[1]):
    print("absent"); sys.exit()
last = None
try:
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("type") == "result" and not e.get("parent_tool_use_id"):
            last = e
except OSError:
    pass
if last is None:
    print("incomplete")
elif last.get("subtype") not in ("success", "error_max_turns") or (last.get("subtype") == "success" and last.get("is_error")):
    print(f"infra:{last.get('subtype')}")
else:
    print("complete")
PY
}

# run_one <scenario-id> <model> <new-out-dir> -> scorer exit code (0/1/2); 3 = refused before start
run_one() {
  local id="$1" model="$2" out="$3"
  local kind turns budget timeout_s fix start end t0 rc=0 score_rc pid dog fxflags
  PROMPT_FILE=""
  [ -e "$out" ] && { echo "!! refuse: $out already exists (one new directory per run)" >&2; return 3; }
  kind="$(scenario_field "$id" kind core)" || return 3
  [ "$(scenario_field "$id" not_applicable __no__)" = __no__ ] \
    || { echo "!! $id is not_applicable: not run" >&2; return 3; }
  fxflags="$(scenario_field "$id" fixture_flags "")"
  if [ "$kind" = probe ]; then
    turns="$(scenario_field "$id" max_turns 6)"; budget="${MAX_BUDGET_USD:-1}"; timeout_s="${RUN_TIMEOUT_S:-600}"
  else
    turns="$(scenario_field "$id" max_turns 30)"; budget="${MAX_BUDGET_USD:-5}"; timeout_s="${RUN_TIMEOUT_S:-1800}"
  fi
  mkdir -p "$out" || return 3
  out="$(cd "$out" && pwd -P)"
  write_prompt "$id" "$out/prompt.txt" || return 3

  fix="$(mktemp -d "$TMPROOT/shode-eval-$id.XXXXXX")" || return 3
  case "$fix/" in "$REPO"/*) echo "!! fixture inside plugin repo: $fix" >&2; return 3 ;; esac
  # shellcheck disable=SC2086  # fxflags: whitelisted words from the scenario (e.g. --with-ui)
  bash "$REPO/scripts/eval-fixture.sh" "$fix" --no-tracker --no-resolve $fxflags > "$out/fixture.log" 2>&1 \
    || { echo "!! $id: fixture build failed, see $out/fixture.log" >&2; return 3; }
  git -C "$fix" rev-parse HEAD > "$out/fixture.sha"

  local args=(-p "$(cat "$out/prompt.txt")" --plugin-dir "$PLUGIN_DIR" --model "$model" --max-turns "$turns"
              --output-format stream-json --verbose --dangerously-skip-permissions)
  local flags="max-turns=$turns${fxflags:+ fixture:$fxflags}"
  if cli_has '--max-budget-usd'; then args+=(--max-budget-usd "$budget"); flags="$flags max-budget-usd=$budget"; fi
  if [ "$kind" = probe ] && [ "${PROBE_BLOCK_SPAWN:-1}" = 1 ] && cli_has '--settings'; then
    # A probe only needs the dispatch DECISION. The tool_use stays in the trace (the scorer counts
    # attempted spawns); the hook denies execution so no opus subagent runs to completion.
    cat > "$out/probe-settings.json" <<'JSON'
{"hooks": {"PreToolUse": [{"matcher": "Task|Agent", "hooks": [{"type": "command",
  "command": "echo 'routing probe: dispatch recorded, not executed. Stop here and answer briefly.' >&2; exit 2"}]}]}}
JSON
    args+=(--settings "$out/probe-settings.json"); flags="$flags spawn-blocked"
  fi

  start="$(utc)"; t0=$(date +%s)
  echo "== $start $id model=$model kind=$kind $flags -> $out"
  ( cd "$fix" && exec "$CLAUDE_BIN" "${args[@]}" > "$out/run.jsonl" 2> "$out/run.stderr" < /dev/null ) &
  pid=$!
  ( sleep "$timeout_s" && echo "watchdog: ${timeout_s}s exceeded, killing $pid" >> "$out/run.stderr" && kill "$pid" 2>/dev/null ) > /dev/null 2>&1 &
  dog=$!
  wait "$pid" || rc=$?
  pkill -P "$dog" 2>/dev/null; kill "$dog" 2>/dev/null; wait "$dog" 2>/dev/null
  end="$(utc)"

  git -C "$fix" status --porcelain -uall > "$out/run.files" 2>&1
  git -C "$fix" diff > "$out/run.diff" 2>&1
  tools_seen "$out/run.jsonl" > "$out/tools-seen.txt" 2>&1

  python3 "$REPO/scripts/team-run-check.py" "$out/run.jsonl" --scenario "$id" --scenarios "$SCENARIOS" \
      --files "$out/run.files" --json > "$out/score.json" 2>&1
  python3 "$REPO/scripts/team-run-check.py" "$out/run.jsonl" --scenario "$id" --scenarios "$SCENARIOS" \
      --files "$out/run.files" > "$out/score.txt" 2>&1
  score_rc=$?
  echo "exit=$score_rc" >> "$out/score.txt"

  SECONDS_TAKEN=$(( $(date +%s) - t0 ))
  M_ID="$id" M_KIND="$kind" M_CLI="$CLI_VERSION" M_START="$start" M_END="$end" M_SECONDS="$SECONDS_TAKEN" \
  M_MODEL="$model" M_SHA="$PLUGIN_SHA" M_REF="${PLUGIN_REF:-WORKTREE}" M_DIRTY="$PLUGIN_DIRTY" \
  M_HARNESS="$(git -C "$REPO" rev-parse HEAD)" M_FLAGS="$flags" M_RC="$rc" M_SCORE="$score_rc" M_FIX="$fix" \
  M_STATE="$(run_state "$out")" M_SCENARIOS="$SCENARIOS" M_PROMPT_FILE="$PROMPT_FILE" M_REPO="$REPO" M_CLASS="$(scenario_field "$id" class "")" \
  python3 - "$out" <<'PY'
import hashlib, json, os, platform, sys
out, env = sys.argv[1], os.environ


def sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


def sha_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


init_hash = {}
model_id, first_skill, first_agent, route, cost = None, "", "", "", None
try:
    for line in open(out + "/run.jsonl", encoding="utf-8"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "system" and e.get("subtype") == "init" and not model_id:
            model_id = e.get("model")
            for key in ("skills", "agents", "slash_commands", "tools", "mcp_servers"):
                if isinstance(e.get(key), list):
                    init_hash[key] = sha_obj(sorted(map(str, e[key])) if all(isinstance(v, str) for v in e[key]) else e[key])
            if isinstance(e.get("plugins"), list):   # path differs per PLUGIN_REF extraction: hash identity only
                init_hash["plugins"] = sha_obj(sorted(f"{p.get('name')}@{p.get('version')}|{p.get('source')}"
                                                      for p in e["plugins"] if isinstance(p, dict)))
        if e.get("type") == "result":
            cost = e.get("total_cost_usd", cost)
        for c in ((e.get("message") or {}).get("content") or []) if e.get("type") == "assistant" else []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                inp = c.get("input") if isinstance(c.get("input"), dict) else {}
                if c.get("name") == "Skill" and not first_skill:
                    first_skill = str(inp.get("skill") or inp.get("command") or "?")
                    route = route or "skill:" + first_skill.split(":")[-1]
                if c.get("name") in ("Task", "Agent") and not first_agent:
                    first_agent = str(inp.get("subagent_type") or "?")
                    route = route or "agent:" + first_agent.split(":")[-1]
except OSError:
    pass
meta = {
    "scenario": env["M_ID"], "kind": env["M_KIND"], "host": "claude-code", "cli_version": env["M_CLI"],
    "date": env["M_START"], "start": env["M_START"], "end": env["M_END"], "seconds": int(env["M_SECONDS"]),
    "model": env["M_MODEL"], "model_id": model_id, "plugin_sha": env["M_SHA"], "plugin_ref": env["M_REF"],
    "plugin_dirty": env["M_DIRTY"] == "true", "harness_sha": env["M_HARNESS"], "flags": env["M_FLAGS"],
    "claude_exit": int(env["M_RC"]), "score_exit": int(env["M_SCORE"]), "cost_usd": cost,
    "route": route, "first_skill": first_skill, "first_agent": first_agent, "fixture": env["M_FIX"],
    "machine": platform.platform(), "class": env["M_CLASS"], "run_state": env["M_STATE"],
    "sha256": {
        "scenarios": sha(env["M_SCENARIOS"]), "prompt_file": sha(env["M_PROMPT_FILE"]) if env["M_PROMPT_FILE"] else None,
        "prompt_txt": sha(out + "/prompt.txt"), "scorer": sha(env["M_REPO"] + "/scripts/team-run-check.py"),
        "run_lib": sha(env["M_REPO"] + "/eval/run-lib.sh"), "fixture_script": sha(env["M_REPO"] + "/scripts/eval-fixture.sh"),
        "probe_settings": sha(out + "/probe-settings.json"), "freeze_manifest": sha(env["M_REPO"] + "/eval/FREEZE.sha256"),
    },
    "init_sha256": init_hash,
}
try:   # report-only descriptors from the scorer (not a verdict of the runner)
    info = json.load(open(out + "/score.json", encoding="utf-8"))
    meta.update({k: info.get(k) for k in ("channel", "terminal", "distinct_skills", "routes")})
except (OSError, ValueError):
    pass
json.dump(meta, open(out + "/meta.json", "x", encoding="utf-8"), indent=1, ensure_ascii=False)
PY
  FIRST_SKILL="$(python3 -c 'import json,sys;m=json.load(open(sys.argv[1]));print(m["first_skill"] or "-")' "$out/meta.json" 2>/dev/null || echo '?')"
  FIRST_ROUTE="$(python3 -c 'import json,sys;m=json.load(open(sys.argv[1]));print(m["route"] or "-")' "$out/meta.json" 2>/dev/null || echo '?')"
  FIRST_AGENT="$(python3 -c 'import json,sys;m=json.load(open(sys.argv[1]));print(m["first_agent"] or "-")' "$out/meta.json" 2>/dev/null || echo '?')"
  local verdict; case "$score_rc" in 0) verdict=PASS ;; 1) verdict=FAIL ;; 2) verdict=UNSCORABLE ;; *) verdict="ERR$score_rc" ;; esac
  echo "== $end $id $verdict (score exit=$score_rc, claude exit=$rc, ${SECONDS_TAKEN}s, first skill=$FIRST_SKILL, first agent=$FIRST_AGENT)"
  return "$score_rc"
}

# tools_seen <run.jsonl>: tool names + first Skill/Task/Agent input. Live 2026-09-20 (CLI 2.1.269):
# Skill input = {"skill","args"}; the spawn tool is `Agent` {"description","subagent_type","prompt"}.
tools_seen() {
  python3 - "$1" <<'PY'
import collections, json, sys
names, first, init, bad, types = collections.Counter(), {}, None, 0, collections.Counter()
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
    except ValueError:
        bad += 1; continue
    if not isinstance(e, dict):
        bad += 1; continue
    types[f"{e.get('type')}/{e.get('subtype')}" if e.get("subtype") else str(e.get("type"))] += 1
    if e.get("type") == "system" and e.get("subtype") == "init" and init is None:
        init = e
    if e.get("type") != "assistant":
        continue
    for c in (e.get("message") or {}).get("content") or []:
        if isinstance(c, dict) and c.get("type") == "tool_use":
            name = str(c.get("name"))
            names[name] += 1
            if name not in first:
                inp = c.get("input")
                first[name] = {k: (v if len(str(v)) <= 300 else str(v)[:300] + "...") for k, v in inp.items()} \
                    if isinstance(inp, dict) else inp
print("# event types:", dict(types), "| non-JSON lines:", bad)
print("# distinct tool names (count):")
for name, n in names.most_common():
    print(f"{name}\t{n}")
for name in ("Skill", "Task", "Agent"):
    print(f"# first {name} tool_use input:", json.dumps(first.get(name), ensure_ascii=False) if name in first else "NOT SEEN")
other = [n for n in first if "skill" in n.lower() and n != "Skill"]
print("# other skill-like tool names:", other or "none")
if init is not None:
    for key in ("model", "claude_code_version", "plugins", "skills", "agents", "slash_commands"):
        if key in init:
            value = init[key]
            if isinstance(value, list):
                value = [v for v in value if "shode" in json.dumps(v)] or f"{len(value)} entries, none mention shode-house"
            print(f"# init.{key}:", json.dumps(value, ensure_ascii=False))
else:
    print("# no system/init event seen")
PY
}
