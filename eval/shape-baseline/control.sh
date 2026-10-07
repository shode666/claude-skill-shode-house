#!/usr/bin/env bash
# Control run: measures the HOST part of a spawn's static prefix, per tool-list signature.
#   bash eval/shape-baseline/control.sh <new-out-dir> <work-dir> [plugin-dir]
# Six "null" agents (one-line body; with/without Bash x the three model settings v3.17.2 uses) are spawned once each.
#   without plugin-dir -> H      = host system prompt + tool definitions + environment
#   with plugin-dir    -> H + M  = the same plus what the plugin adds to EVERY spawn (skill listing etc.)
# metrics.py reads the first API call of each null spawn from the transcript.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
out="${1:?out dir}"; work="${2:?work dir}"; plugin="${3:-}"
[ -e "$out" ] && sb_die "refuse: $out exists"
mkdir -p "$out/raw" "$work"; out="$(cd "$out" && pwd -P)"
cwd="$(mktemp -d "$work/ctl.XXXXXX")"; ( cd "$cwd" && git init -q && echo control > README.md && git add -A && git -c user.email=eval@local -c user.name=eval commit -qm init )
cat > "$out/agents.json" <<'JSON'
{"null-bash-main": {"description": "control", "prompt": "Reply with the single word OK.", "tools": ["Read","Write","Edit","Grep","Glob","Bash","Skill"]},
 "null-nobash-main": {"description": "control", "prompt": "Reply with the single word OK.", "tools": ["Read","Write","Edit","Grep","Glob","WebSearch","WebFetch","Skill"]},
 "null-bash-opus": {"description": "control", "prompt": "Reply with the single word OK.", "model": "opus", "tools": ["Read","Write","Edit","Grep","Glob","Bash","Skill"]},
 "null-nobash-opus": {"description": "control", "prompt": "Reply with the single word OK.", "model": "opus", "tools": ["Read","Write","Edit","Grep","Glob","WebSearch","WebFetch","Skill"]},
 "null-bash-fable": {"description": "control", "prompt": "Reply with the single word OK.", "model": "claude-fable-5", "tools": ["Read","Write","Edit","Grep","Glob","Bash","WebSearch","Skill"]},
 "null-nobash-fable": {"description": "control", "prompt": "Reply with the single word OK.", "model": "claude-fable-5", "tools": ["Read","Write","Edit","Grep","Glob","WebSearch","WebFetch","Skill"]}}
JSON
cat > "$out/prompt.txt" <<'TXT'
Harness control run, not a task. Spawn each of these six sub-agent types exactly once (all six in one message), each with exactly this prompt: "Reply with the single word OK. Do not use any tool." Do not pass a model parameter. Types: null-bash-main, null-nobash-main, null-bash-opus, null-nobash-opus, null-bash-fable, null-nobash-fable. Do not read files, do not load skills. When all six have returned, reply with the single word DONE.
TXT
sid="$(python3 -c 'import uuid;print(uuid.uuid4())')"
sb_settings "$out/raw/settings.json" "$out/raw/snap.jsonl" "$plugin"
args=(--settings "$out/raw/settings.json" --agents "$out/agents.json")
[ -n "$plugin" ] && args+=(--plugin-dir "$plugin")
start="$(sb_utc)"
sb_launch "$cwd" "$out" "$out/prompt.txt" "$sid" 14 4 600 "${args[@]}"; rc=$?
sb_collect_transcript "$cwd" "$sid" "$out"
printf '{"kind":"control","with_plugin":%s,"start":"%s","end":"%s","claude_exit":%s,"main_model":"%s","effort":"%s"}\n' \
  "$([ -n "$plugin" ] && echo true || echo false)" "$start" "$(sb_utc)" "$rc" "$MAIN_MODEL" "$EFFORT" > "$out/meta.json"
printf '{"plugin_dir":"%s","session":"%s","fixture":"%s"}\n' "$plugin" "$sid" "$cwd" > "$out/raw/local.json"
echo "control done rc=$rc -> $out"
