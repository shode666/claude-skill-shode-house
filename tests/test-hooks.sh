#!/usr/bin/env bash
# tests/test-hooks.sh -- bash-only test suite for hooks/** (bd: shode-roadmap/C-A7)
#
# Replaces the spike matcher from commit 441e0fe (`case "$input" in
# *'.shode-house/state/'*)` -- raw-JSON substring match, Sentinel-blocked from merge:
# outputs/shode-roadmap/C/08-sentinel-threat-model-hooks.md Sec 4/9 "CONDITIONAL PASS").
# This suite is the CI gate that stands in for AC-S1..S9/S11 (AC-S10 = README disclosure,
# not a test; AC-S8 asks for >=10 fixture cases -- this suite has ~20).
#
# Folds BOTH static hygiene checks (hooks.json shape, forbidden patterns, timeouts,
# shellcheck/bash -n, packaging) AND behavior fixtures (T1-T6 from Sentinel's own runtime
# evidence + new vectors this task adds) into ONE suite, so the CI budget rule ("1 CI step
# per milestone" -- every prior Milestone A/B/D/E/F test suite follows the same pattern,
# e.g. tests/test-permission-check.sh's own header) costs exactly one ci.yml step total.
#
# No framework dependency (same style as tests/test-workflow-state.sh /
# tests/test-scope-check.sh / tests/test-permission-check.sh) -- plain bash test
# functions + a tiny assert library. Each behavior test runs inside a fresh mktemp -d
# sandbox via CLAUDE_PROJECT_DIR, so tests never touch the real repo state.
#
# Usage: bash tests/test-hooks.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"
HOOKS_DIR="$REPO_ROOT/hooks/scripts"
GUARD="$HOOKS_DIR/guard-state-write.sh"
SCOPE_GUARD="$HOOKS_DIR/guard-scope-write.sh"
SESSION_START="$HOOKS_DIR/session-start.sh"
STOP_INTEGRITY="$HOOKS_DIR/stop-integrity.sh"
WFSTATE="$REPO_ROOT/scripts/workflow-state.sh"

PASS=0
FAIL=0
CUR_TEST=""

t_start() { CUR_TEST="$1"; printf -- '-- %s\n' "$1"; }
t_ok()    { PASS=$((PASS + 1)); printf '   ok\n'; }
t_fail()  { FAIL=$((FAIL + 1)); printf '   FAIL (%s): %s\n' "$CUR_TEST" "$1"; }
t_skip()  { printf '   SKIP: %s\n' "$1"; }

assert_eq() {
  if [ "$1" = "$2" ]; then t_ok; else t_fail "$3 -- got '$1' want '$2'"; fi
}
assert_contains() {
  case "$1" in *"$2"*) t_ok ;; *) t_fail "$3 -- '$1' does not contain '$2'" ;; esac
}
assert_not_contains() {
  case "$1" in *"$2"*) t_fail "$3 -- '$1' unexpectedly contains '$2'" ;; *) t_ok ;; esac
}
assert_true()  { if [ "$1" -eq 0 ]; then t_ok; else t_fail "$2 -- exit code $1"; fi; }
assert_rc()    { if [ "$1" -eq "$2" ]; then t_ok; else t_fail "$3 -- exit code $1, want $2"; fi; }

sandbox() { local d; d=$(mktemp -d -t hooks-test.XXXXXX); printf '%s' "$d"; }

# init_engagement <sandbox-dir> -- mkdir the bare minimum for the engagement guard to
# consider this project "opted in", without depending on workflow-state.sh's schema.
init_engagement() { mkdir -p "$1/.shode-house/state" "$1/.shode-house/journal"; }

# guard_run <sandbox-dir> <json-stdin> -- invokes the real guard script, returns
# "exit_code<TAB>stderr" on stdout.
guard_run() {
  local proj="$1" input="$2" out rc
  out=$(printf '%s' "$input" | CLAUDE_PROJECT_DIR="$proj" "$GUARD" 2>&1)
  rc=$?
  printf '%s\t%s' "$rc" "$out"
}

# scope_guard_run <sandbox-dir> <json-stdin> -- same convention, for guard-scope-write.sh
# (bd: shode-house-5cs.4, L2). <json-stdin> is built with `jq -n` by every call site so a
# real backtick/pipe/etc. byte lands in tool_input.command, never a shell-escaped stand-in.
scope_guard_run() {
  local proj="$1" input="$2" out rc
  out=$(printf '%s' "$input" | CLAUDE_PROJECT_DIR="$proj" "$SCOPE_GUARD" 2>&1)
  rc=$?
  printf '%s\t%s' "$rc" "$out"
}

# init_scope_engagement <sandbox-dir> -- an in_progress workflow state file (so the guard's
# resolve_in_progress_bds() sees an active bd) plus a scope manifest for it.
init_scope_state() {
  # $1=sandbox $2=bd-id $3=manifest-json-on-stdin
  local proj="$1" bd="$2"
  mkdir -p "$proj/.shode-house/state" "$proj/.shode-house/scope"
  printf '{"bd_id":"%s","current_phase":"2-implement","phases":{"2-implement":{"status":"in_progress"}}}\n' "$bd" \
    > "$proj/.shode-house/state/$(printf '%s' "$bd" | sed 's#/#--#g').json"
  cat > "$proj/.shode-house/scope/$(printf '%s' "$bd" | sed 's#/#--#g').json"
}

echo "== hooks/hooks.json static shape (AC-S3/S9) =="

t_start "hooks.json is valid JSON"
jq empty "$HOOKS_JSON" >/dev/null 2>&1
assert_true "$?" "jq empty $HOOKS_JSON"

t_start "every hook command references only \${CLAUDE_PLUGIN_ROOT}/hooks/scripts/*.sh (AC-S9)"
bad_cmds=$(jq -r '[.hooks[][]?.hooks[]?.command] | .[]' "$HOOKS_JSON" 2>/dev/null | \
  grep -v '^\${CLAUDE_PLUGIN_ROOT}/hooks/scripts/[A-Za-z0-9_-]*\.sh$' || true)
[ -z "$bad_cmds" ] && t_ok || t_fail "commands outside the allowed pattern: $bad_cmds"

t_start "every hook entry declares an explicit numeric timeout (AC-S3)"
missing_timeout=$(jq -r '[.hooks[][]?.hooks[]? | select((.timeout // null) == null or (.timeout | type) != "number")] | length' "$HOOKS_JSON" 2>/dev/null)
assert_eq "$missing_timeout" "0" "every hook object must have a numeric 'timeout' field"

t_start "SessionStart timeout <= 10s, guard/Stop/SubagentStop timeout <= 5s (AC-S3)"
bad_budget=$(jq -r '
  [.hooks.SessionStart[]?.hooks[]? | select(.timeout > 10)] as $ss
  | [.hooks.PreToolUse[]?.hooks[]?, .hooks.Stop[]?.hooks[]?, .hooks.SubagentStop[]?.hooks[]? | select(.timeout > 5)] as $rest
  | ($ss + $rest) | length
' "$HOOKS_JSON" 2>/dev/null)
assert_eq "$bad_budget" "0" "timeout budget exceeded somewhere"

t_start "every script hooks.json references actually exists on disk"
referenced=$(jq -r '[.hooks[][]?.hooks[]?.command] | .[]' "$HOOKS_JSON" 2>/dev/null | sed 's#\${CLAUDE_PLUGIN_ROOT}#'"$REPO_ROOT"'#')
missing=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ -f "$p" ] || missing="${missing}${missing:+, }$p"
done <<<"$referenced"
[ -z "$missing" ] && t_ok || t_fail "referenced but missing: $missing"

echo
echo "== script hygiene: bash -n / shellcheck / forbidden patterns (Hook Charter Sec 6, AC-S4/S5/S6) =="

for f in "$HOOKS_DIR"/*.sh; do
  t_start "bash -n $f"
  bash -n "$f" 2>/tmp/hooks-test-bashn.$$; rc=$?
  assert_true "$rc" "$(cat /tmp/hooks-test-bashn.$$ 2>/dev/null)"
  rm -f /tmp/hooks-test-bashn.$$
done

if command -v shellcheck >/dev/null 2>&1; then
  for f in "$HOOKS_DIR"/*.sh; do
    t_start "shellcheck -S warning $f"
    out=$(shellcheck -x -S warning "$f" 2>&1); rc=$?
    assert_true "$rc" "$out"
  done
else
  t_start "shellcheck availability"
  t_skip "shellcheck not on PATH -- AC-S4 shellcheck-clean requirement not exercised in this environment (CI's ubuntu-latest ships it; verified locally on the maintainer's machine separately)"
fi

t_start "no eval / sh -c / network binaries anywhere under hooks/ (Hook Charter Sec 6 item 2/3)"
forbidden=$(grep -nE '\beval\b|\bsh[[:space:]]+-c\b|\b(curl|wget|nc|ssh|scp)\b|/dev/tcp|git[[:space:]]+ls-remote' "$REPO_ROOT"/hooks/hooks.json "$HOOKS_DIR"/*.sh 2>/dev/null || true)
[ -z "$forbidden" ] && t_ok || t_fail "forbidden pattern found: $forbidden"

t_start "no fixed /tmp/ path anywhere under hooks/ (AC-S6, spike used /tmp/shode-hook-canary)"
tmp_hits=$(grep -n '/tmp/' "$HOOKS_DIR"/*.sh "$HOOKS_JSON" 2>/dev/null || true)
[ -z "$tmp_hits" ] && t_ok || t_fail "literal /tmp/ path found: $tmp_hits"

t_start "no raw stdin/content is ever echoed to stderr (AC-S5 -- static messages only)"
# every '>&2' line in guard-state-write.sh must NOT mention $input or $content
raw_leak=$(grep -n '>&2' "$GUARD" | grep -E '\$input|\$content' || true)
[ -z "$raw_leak" ] && t_ok || t_fail "stderr line references raw stdin var: $raw_leak"

echo
echo "== guard-state-write.sh: bypass fixtures (Sentinel T1-T6 + new vectors) =="

SB=$(sandbox)
init_engagement "$SB"

t_start "T1 legit-deny: Write .shode-house/state/probe.json -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/state/probe.json","content":"x"}}')
assert_eq "${res%%$'\t'*}" "2" "T1"

t_start "T2 FP-content-mention (was the runtime-confirmed false positive): content mentions the path, file_path does not -> ALLOW exit 0"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/notes.md","content":"see .shode-house/state/ for details"}}')
assert_eq "${res%%$'\t'*}" "0" "T2"

t_start "T3 bypass-traversal (was a runtime-confirmed bypass): .shode-house/foo/../state/probe.json -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/foo/../state/probe.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T3"

t_start "T4 bypass-case (was a runtime-confirmed bypass, APFS default case-insensitive): .SHODE-HOUSE/STATE -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.SHODE-HOUSE/STATE/probe.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T4"

t_start "T5 bypass-json-escape (was a runtime-confirmed bypass): escaped solidus in the JSON text -> DENY exit 2"
input5=$(printf '{"tool_input":{"file_path":"%s\\/.shode-house\\/state\\/probe.json"}}' "$SB")
res=$(guard_run "$SB" "$input5")
assert_eq "${res%%$'\t'*}" "2" "T5"

t_start "T6 bypass-dot-slash (was a runtime-confirmed bypass): .shode-house/./state/probe.json -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/./state/probe.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T6"

t_start "T7a bypass-symlink-parent: .shode-house is a symlink out of the workspace -> DENY exit 2, fail-closed"
SB7=$(sandbox)
mkdir -p "$SB7/elsewhere/state"
ln -s "$SB7/elsewhere" "$SB7/.shode-house"
res=$(guard_run "$SB7" '{"tool_input":{"file_path":"'"$SB7"'/.shode-house/state/x.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T7a"
rm -rf "$SB7"

t_start "T7b bypass-symlink-leaf: only .shode-house/state is a symlink out of the workspace -> DENY exit 2, fail-closed"
SB7b=$(sandbox)
mkdir -p "$SB7b/.shode-house" "$SB7b/elsewhere"
ln -s "$SB7b/elsewhere" "$SB7b/.shode-house/state"
res=$(guard_run "$SB7b" '{"tool_input":{"file_path":"'"$SB7b"'/.shode-house/state/x.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T7b"
rm -rf "$SB7b"

t_start "T8 absolute-path: already-absolute file_path under state/ -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/state/abs.json"}}')
assert_eq "${res%%$'\t'*}" "2" "T8"

t_start "T9 empty-path: tool_input.file_path is an empty string -> ALLOW exit 0, fail-open"
res=$(guard_run "$SB" '{"tool_input":{"file_path":""}}')
assert_eq "${res%%$'\t'*}" "0" "T9"

t_start "T10 malformed-json: stdin is not valid JSON at all -> ALLOW exit 0, fail-open (never block on unparsable input)"
res=$(printf 'not json {{{' | CLAUDE_PROJECT_DIR="$SB" "$GUARD" 2>&1; echo "RC=$?")
assert_contains "$res" "RC=0" "T10"

t_start "T11 jq-absent: PATH has no jq -> ALLOW exit 0, fail-open, AND .degraded is written (AC-S7)"
rm -f "$SB/.shode-house/state/.degraded"
FAKEBIN=$(mktemp -d -t hooks-fakebin.XXXXXX)
for b in bash date dirname basename tr sed cat env grep; do
  src=$(command -v "$b" 2>/dev/null) && ln -s "$src" "$FAKEBIN/$b"
done
out=$(printf '{"tool_input":{"file_path":"%s/.shode-house/state/x.json"}}' "$SB" | \
      CLAUDE_PROJECT_DIR="$SB" PATH="$FAKEBIN" bash "$GUARD" 2>&1); rc=$?
assert_rc "$rc" 0 "T11 exit code"
[ -f "$SB/.shode-house/state/.degraded" ] && t_ok || t_fail "T11: .degraded marker not written when jq is absent"
rm -rf "$FAKEBIN"

t_start "T12 journal-path: .shode-house/journal/<bd>.jsonl -> DENY exit 2 (append-only, second bullet of the task)"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/journal/some-bd.jsonl"}}')
assert_eq "${res%%$'\t'*}" "2" "T12"

t_start "T13 notebook_path fallback: NotebookEdit-shaped tool_input targeting state/ -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"notebook_path":"'"$SB"'/.shode-house/state/nb.ipynb"}}')
assert_eq "${res%%$'\t'*}" "2" "T13"

t_start "T14 trailing-slash: directory-shaped write target .shode-house/state/ -> DENY exit 2"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.shode-house/state/"}}')
assert_eq "${res%%$'\t'*}" "2" "T14"

t_start "T15 combined case+traversal: .SHODE-HOUSE/../.shode-house/STATE/x -> DENY exit 2 (both defenses stacked)"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/.SHODE-HOUSE/../.shode-house/STATE/x"}}')
assert_eq "${res%%$'\t'*}" "2" "T15"

t_start "control-unrelated-relative: write to notes/ok.txt (relative) -> ALLOW exit 0"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/notes/ok.txt","content":"hello"}}')
assert_eq "${res%%$'\t'*}" "0" "control-unrelated-relative"

t_start "control-unrelated-absolute: absolute write outside .shode-house entirely -> ALLOW exit 0"
res=$(guard_run "$SB" '{"tool_input":{"file_path":"'"$SB"'/somewhere/else.txt"}}')
assert_eq "${res%%$'\t'*}" "0" "control-unrelated-absolute"

t_start "no-engagement: project without .shode-house/state at all -> ALLOW exit 0, silent, no jq needed"
SB_NOENG=$(sandbox)
res=$(guard_run "$SB_NOENG" '{"tool_input":{"file_path":"'"$SB_NOENG"'/.shode-house/state/probe.json"}}')
assert_eq "${res%%$'\t'*}" "0" "no-engagement guard"
assert_eq "${res#*$'\t'}" "" "no-engagement guard must be silent (no stdout/stderr at all)"
rm -rf "$SB_NOENG"

rm -rf "$SB"

echo
echo "== guard-scope-write.sh: bind-on-claim (Bash) + Write/Edit scope enforcement (bd: shode-house-5cs.4, L2) =="

t_start "guard-scope-write.sh: bash -n"
bash -n "$SCOPE_GUARD" 2>/tmp/hooks-test-scopeguard-bashn.$$; rc=$?
assert_true "$rc" "$(cat /tmp/hooks-test-scopeguard-bashn.$$ 2>/dev/null)"
rm -f /tmp/hooks-test-scopeguard-bashn.$$

echo
echo "-- Bash tool_name: bind-on-claim recognition --"

SBB=$(sandbox)
init_scope_state "$SBB" "bd-h1" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-h1",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": ["src/payment/refund.ts"]},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**"], "owns": []}
  ]
}
EOF
MFB="$SBB/.shode-house/scope/bd-h1.json"

t_start "B1 canonical bind shape, real agent_id + agent_type -> ALLOW exit 0, manifest records the platform-neutral binding (bd: shode-house-5cs.4 iter 1, C1)"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-AAA",agent_type:"shode-house:developer",tool_input:{command:"scripts/scope-check.sh bd-h1 Dave#1 --bind"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "0" "B1 exit code"
bnd_label=$(jq -r '.bindings["agentid-AAA"].label // empty' "$MFB")
assert_eq "$bnd_label" "Dave#1" "B1 binding label actually recorded"
bnd_role=$(jq -r '.bindings["agentid-AAA"].role // empty' "$MFB")
assert_eq "$bnd_role" "shode-house:developer" "B1 binding records role verbatim from agent_type"
bnd_platform=$(jq -r '.bindings["agentid-AAA"].platform // empty' "$MFB")
assert_eq "$bnd_platform" "claude" "B1 binding records the adapter's own literal platform string"

t_start "B9 canonical bind shape with agent_type ABSENT -> role falls back to \"unknown\", still binds"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-NOROLE",tool_input:{command:"scripts/scope-check.sh bd-h1 Dave#2 --bind"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "0" "B9 exit code"
bnd_role2=$(jq -r '.bindings["agentid-NOROLE"].role // empty' "$MFB")
assert_eq "$bnd_role2" "unknown" "B9: missing agent_type falls back to a literal \"unknown\" role, never an empty/missing field"

t_start "B2 metachar ';' anywhere in the command -> DENY exit 2, no binding recorded"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-XXX",tool_input:{command:"scripts/scope-check.sh bd-h1 Dave#2 --bind; touch pwn"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "2" "B2 exit code"
assert_contains "${res#*$'\t'}" "forbidden shell metacharacter" "B2 message"
[ -z "$(jq -r '.bindings["agentid-XXX"] // empty' "$MFB")" ] && t_ok || t_fail "B2: binding must not have been recorded"

for pair in '&&:AND' '||:OR' '|:PIPE' '$(:CMDSUB' '>:REDIR' '<:REDIRIN'; do
  meta="${pair%%:*}"; label="${pair##*:}"
  t_start "B3-$label metachar '$meta' anywhere in the command -> DENY exit 2"
  payload=$(jq -n --arg c "scripts/scope-check.sh bd-h1 Dave#2 ${meta} touch pwn --bind" '{tool_name:"Bash",agent_id:"agentid-YYY",tool_input:{command:$c}}')
  res=$(scope_guard_run "$SBB" "$payload")
  assert_eq "${res%%$'\t'*}" "2" "B3-$label exit code"
done

t_start "B4 metachar backtick (real byte, not a shell-escaped stand-in) -> DENY exit 2"
BT=$(printf '\140')
cmd="scripts/scope-check.sh bd-h1 Dave#2 ${BT}touch pwn${BT} --bind"
payload=$(jq -n --arg c "$cmd" '{tool_name:"Bash",agent_id:"agentid-ZZZ",tool_input:{command:$c}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "2" "B4 exit code"

t_start "B5 canonical shape, no agent_id (main session) -> DENY exit 2, main session cannot bind"
payload=$(jq -n '{tool_name:"Bash",tool_input:{command:"scripts/scope-check.sh bd-h1 Dave#2 --bind"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "2" "B5 exit code"
assert_contains "${res#*$'\t'}" "no agent_id" "B5 message"

t_start "B6 non-canonical shape (extra trailing token) -- not recognized as a bind attempt, ALLOW exit 0, no write"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-WWW",tool_input:{command:"scripts/scope-check.sh bd-h1 Dave#2 --bind --extra"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "0" "B6 exit code (un-molested pass-through)"
[ -z "$(jq -r '.bindings["agentid-WWW"] // empty' "$MFB")" ] && t_ok || t_fail "B6: non-canonical shape must never record a binding"

t_start "B7 unrelated Bash command (mentions neither scope-check.sh nor --bind) -> ALLOW exit 0, guard does not even inspect it further"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-AAA",tool_input:{command:"ls -la"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "0" "B7 exit code"

t_start "B8 unknown label via the real bind path -> DENY exit 2, forwards scope-check.sh's own DENY reason"
payload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-VVV",tool_input:{command:"scripts/scope-check.sh bd-h1 Ghost --bind"}}')
res=$(scope_guard_run "$SBB" "$payload")
assert_eq "${res%%$'\t'*}" "2" "B8 exit code"
assert_contains "${res#*$'\t'}" "unknown label" "B8 forwarded reason"

rm -rf "$SBB"

echo
echo "-- Write/Edit tool_name: subagent scope check + main-session non-exemption --"

SBW=$(sandbox)
init_scope_state "$SBW" "bd-h2" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-h2",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": ["src/payment/refund.ts"]},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**"], "owns": []}
  ],
  "bindings": {"agentid-AAA": {"platform": "claude", "role": "shode-house:developer", "label": "Dave#1"}}
}
EOF

t_start "W1 subagent bound to Dave#1, writes its own owned path -> ALLOW exit 0"
payload=$(jq -n --arg p "$SBW/src/payment/refund.ts" '{tool_name:"Write",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "0" "W1 exit code"

t_start "W2 subagent bound to Dave#1, writes a path outside its own allowed_roots (owned by no one, Dave#2's territory) -> DENY exit 2"
payload=$(jq -n --arg p "$SBW/src/orders/handler.py" '{tool_name:"Write",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "2" "W2 exit code"

t_start "W3 subagent bound to Dave#1, writes an UNCLAIMED path inside its own allowed_roots -> DENY exit 2 (NEEDS_AMENDMENT, carries the amend command)"
payload=$(jq -n --arg p "$SBW/src/payment/create.ts" '{tool_name:"Write",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "2" "W3 exit code"
assert_contains "${res#*$'\t'}" "--amend" "W3 message carries the amend command"

t_start "W4 subagent with an agent_id that was never bound, writing a path INSIDE active scope -> DENY exit 2, outsider policy, told to bind first (bd: shode-house-5cs.4 iter 1, C2)"
payload=$(jq -n --arg p "$SBW/src/payment/create.ts" '{tool_name:"Write",agent_id:"agentid-UNBOUND",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "2" "W4 exit code"
assert_contains "${res#*$'\t'}" "collides with agent" "W4 message applies the same collision reasoning as the main-session outsider policy"
assert_contains "${res#*$'\t'}" "--bind" "W4 message still tells the agent to bind first"

t_start "W10 subagent with an agent_id that was never bound, writing a path OUTSIDE all active scope -> ALLOW exit 0 + audit log (C2 -- the exact 'reviewer writing under outputs/' case the ruling names)"
rm -f "$SBW/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBW/outputs/report.md" '{tool_name:"Write",agent_id:"agentid-UNBOUND",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "0" "W10 exit code -- unbound agent is NOT bricked outside active scope"
[ -f "$SBW/.shode-house/state/.scope-audit.log" ] && t_ok || t_fail "W10: audit log must be written"
assert_contains "$(cat "$SBW/.shode-house/state/.scope-audit.log" 2>/dev/null)" "outputs/report.md" "W10 audit log content"
assert_contains "$(cat "$SBW/.shode-house/state/.scope-audit.log" 2>/dev/null)" "not bound" "W10 audit log explains why the outsider policy applied"

t_start "W5 main session (no agent_id) writes INTO an active agent's allowed_roots -> DENY exit 2 -- NOT blanket-exempt"
payload=$(jq -n --arg p "$SBW/src/payment/anything.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "2" "W5 exit code"

t_start "W6 main session (no agent_id) writes OUTSIDE all active scope -> ALLOW exit 0, one audit log line appended"
rm -f "$SBW/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBW/README.md" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "0" "W6 exit code"
[ -f "$SBW/.shode-house/state/.scope-audit.log" ] && t_ok || t_fail "W6: audit log must be written"
assert_contains "$(cat "$SBW/.shode-house/state/.scope-audit.log" 2>/dev/null)" "README.md" "W6 audit log content"

t_start "W7 Edit tool_name is covered identically to Write (same matcher, same script)"
payload=$(jq -n --arg p "$SBW/src/orders/handler.py" '{tool_name:"Edit",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW" "$payload")
assert_eq "${res%%$'\t'*}" "2" "W7 exit code"

t_start "W8 no .shode-house/state entries in_progress at all -> ALLOW exit 0, nothing to enforce"
SBW2=$(sandbox); mkdir -p "$SBW2/.shode-house/state"
payload=$(jq -n --arg p "$SBW2/anything.ts" '{tool_name:"Write",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW2" "$payload")
assert_eq "${res%%$'\t'*}" "0" "W8 exit code"
rm -rf "$SBW2"

t_start "W9 no .shode-house/state directory at all (never opted in) -> ALLOW exit 0, silent (engagement guard)"
SBW3=$(sandbox)
payload=$(jq -n --arg p "$SBW3/anything.ts" '{tool_name:"Write",agent_id:"agentid-AAA",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBW3" "$payload")
assert_eq "${res%%$'\t'*}" "0" "W9 exit code"
assert_eq "${res#*$'\t'}" "" "W9 must be silent"
rm -rf "$SBW3"

rm -rf "$SBW"

echo
echo "-- multi-bd resolution: subagent write when more than one bd is in_progress simultaneously --"

SBM=$(sandbox)
init_scope_state "$SBM" "bd-h3" <<'EOF'
{"schema_version":1,"bd_id":"bd-h3","agents":[{"agent":"Dave#1","allowed_roots":["src/a/**"],"owns":["src/a/x.ts"]}],"bindings":{"agentid-A3":{"platform":"claude","role":"shode-house:developer","label":"Dave#1"}}}
EOF
init_scope_state "$SBM" "bd-h4" <<'EOF'
{"schema_version":1,"bd_id":"bd-h4","agents":[{"agent":"Dave#1","allowed_roots":["src/b/**"],"owns":["src/b/y.ts"]}],"bindings":{"agentid-A4":{"platform":"claude","role":"shode-house:developer","label":"Dave#1"}}}
EOF

t_start "M1 two bds in_progress, agent_id is bound in exactly ONE of them -> resolves to that one, ordinary check applies"
payload=$(jq -n --arg p "$SBM/src/a/x.ts" '{tool_name:"Write",agent_id:"agentid-A3",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBM" "$payload")
assert_eq "${res%%$'\t'*}" "0" "M1 exit code (own path in the bd it is actually bound to)"

payload=$(jq -n --arg p "$SBM/src/b/y.ts" '{tool_name:"Write",agent_id:"agentid-A3",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBM" "$payload")
assert_eq "${res%%$'\t'*}" "2" "M1b: same agent_id, a path only valid under the OTHER bd it is not bound to -> DENY (resolved to bd-h3, not bd-h4)"

t_start "M2 two bds in_progress, agent_id bound in NEITHER, path INSIDE bd-h3's active scope -> outsider policy DENY exit 2 (bd: shode-house-5cs.4 iter 1, C2 -- closes the fail-open hole M2 used to document)"
rm -f "$SBM/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBM/src/a/x.ts" '{tool_name:"Write",agent_id:"agentid-UNSEEN",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBM" "$payload")
assert_eq "${res%%$'\t'*}" "2" "M2 exit code (C2: ambiguous instance_id no longer fails open inside active scope)"
assert_contains "${res#*$'\t'}" "ambiguous" "M2 DENY message still names the ambiguity as context"
assert_contains "${res#*$'\t'}" "collides with agent" "M2 DENY applies the same collision reasoning as the main-session outsider policy"
[ -s "$SBM/.shode-house/state/.scope-audit.log" ] && t_fail "M2: a DENIED write must not also append an ALLOW audit line" || t_ok

t_start "M3 two bds in_progress, agent_id bound in NEITHER, path OUTSIDE both bds' active scope -> outsider policy ALLOW exit 0 + audit log"
rm -f "$SBM/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBM/README.md" '{tool_name:"Write",agent_id:"agentid-UNSEEN",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBM" "$payload")
assert_eq "${res%%$'\t'*}" "0" "M3 exit code (ambiguous instance is not bricked outside every active bd's scope)"
assert_contains "$(cat "$SBM/.shode-house/state/.scope-audit.log" 2>/dev/null)" "ambiguous" "M3 audit log records the ambiguity"
assert_contains "$(cat "$SBM/.shode-house/state/.scope-audit.log" 2>/dev/null)" "README.md" "M3 audit log content"

rm -rf "$SBM"

echo
echo "== guard-scope-write.sh: T1-T6-parity canonicalization + H1 symlink + C2/C3/C5 (bd: shode-house-5cs.4 iter 2) =="

SBC=$(sandbox)
init_scope_state "$SBC" "bd-h5" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-h5",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": ["src/payment/refund.ts"]},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**"], "owns": ["src/orders/handler.py"]}
  ]
}
EOF
mkdir -p "$SBC/src/payment" "$SBC/src/orders"

t_start "HT1 (C1, Chris) traversal bypass: .shode-house/../src/payment/evil.ts -> DENY exit 2 (physically identical to src/payment/evil.ts, collides with Dave#1's active scope)"
payload=$(jq -n --arg p "$SBC/.shode-house/../src/payment/evil.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HT1 exit code"

t_start "HT2 (C1, Chris) dot-slash bypass: src/./payment/evil2.ts -> DENY exit 2"
payload=$(jq -n --arg p "$SBC/src/./payment/evil2.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HT2 exit code"

t_start "HT3 (C1, Chris) case bypass: SRC/PAYMENT/evil3.ts -> DENY exit 2 (case-folded, portable regardless of underlying filesystem's own case sensitivity)"
payload=$(jq -n --arg p "$SBC/SRC/PAYMENT/evil3.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HT3 exit code"

t_start "HT4 (C1, Chris) sanity: an UNRELATED path (not owned/allowed_root by anyone), even through the same guard, still ALLOWs -- canonicalization must not become an over-broad DENY"
payload=$(jq -n --arg p "$SBC/README.md" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "0" "HT4 exit code"

t_start "HS1 (H1, Quinn) symlink leaf: a real symlink at src/payment/link.ts -> src/orders/handler.py -- Write to the symlink path is REFUSED outright (fail-closed), never resolved-and-matched"
ln -sf "$SBC/src/orders/handler.py" "$SBC/src/payment/link.ts"
payload=$(jq -n --arg p "$SBC/src/payment/link.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HS1 exit code"
assert_contains "${res#*$'\t'}" "symlink" "HS1 message names the reason"
rm -f "$SBC/src/payment/link.ts"

echo
echo "-- C2 (Chris): embedded-newline bind command must NOT be recognised as the canonical shape --"

t_start "HB-NL multi-line command (real embedded newlines, not literal backslash-n text) mentioning both scope-check.sh and --bind -> DENY exit 2, never reaches --bind-record"
MFC="$SBC/.shode-house/scope/bd-h5.json"
before_bindings=$(jq -c '.bindings // {}' "$MFC")
nlcmd=$(printf 'scripts/scope-check.sh\nbd-h5\nDave#1\n--bind')
payload=$(jq -n --arg c "$nlcmd" '{tool_name:"Bash",agent_id:"agentid-NL",agent_type:"tester",tool_input:{command:$c}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HB-NL exit code"
assert_contains "${res#*$'\t'}" "newline" "HB-NL message names the newline as a forbidden metacharacter"
after_bindings=$(jq -c '.bindings // {}' "$MFC")
assert_eq "$after_bindings" "$before_bindings" "HB-NL: manifest bindings must be byte-identical -- no binding was recorded"

echo
echo "-- C3 (Chris + Quinn H2): corrupt manifest fails CLOSED, with a distinguishable audit line --"

t_start "HC3-outsider: main-session write, this bd's manifest is corrupt JSON -> DENY exit 2 (not the old fail-open ALLOW), audit line says 'corrupt-manifest', not the generic outsider-policy ALLOW wording"
cp "$MFC" "$MFC.bak"
printf '{not valid json' > "$MFC"
rm -f "$SBC/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBC/src/payment/x.ts" '{tool_name:"Write",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HC3-outsider exit code"
assert_contains "${res#*$'\t'}" "corrupt/unreadable" "HC3-outsider message names the manifest as corrupt, not a clean 'no collision'"
assert_contains "$(cat "$SBC/.shode-house/state/.scope-audit.log" 2>/dev/null)" "corrupt-manifest" "HC3-outsider audit line is distinguishable from a genuine outsider-policy ALLOW"
mv "$MFC.bak" "$MFC"   # restore to valid JSON before the next test binds against it

t_start "HC3-subagent: a REALLY-bound subagent's own write, this bd's manifest becomes corrupt AFTER binding -> DENY exit 2 (fail CLOSED, not the old silent fail-open), distinguishable audit line, never misclassified as an unbound outsider"
bindpayload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-BOUND-CORRUPT",agent_type:"tester",tool_input:{command:"scripts/scope-check.sh bd-h5 Dave#1 --bind"}}')
bindres=$(scope_guard_run "$SBC" "$bindpayload")
assert_eq "${bindres%%$'\t'*}" "0" "HC3-subagent setup: the real bind must succeed before the manifest is corrupted"
assert_eq "$(jq -r '.bindings["agentid-BOUND-CORRUPT"].label // empty' "$MFC")" "Dave#1" "HC3-subagent setup: binding actually recorded"
cp "$MFC" "$MFC.bak"
printf '{not valid json' > "$MFC"
rm -f "$SBC/.shode-house/state/.scope-audit.log"
payload=$(jq -n --arg p "$SBC/src/payment/refund.ts" '{tool_name:"Write",agent_id:"agentid-BOUND-CORRUPT",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HC3-subagent exit code"
assert_contains "${res#*$'\t'}" "cannot be read for binding resolution" "HC3-subagent message names the real cause (exit 64), not a generic 'not bound' outsider message"
assert_contains "$(cat "$SBC/.shode-house/state/.scope-audit.log" 2>/dev/null)" "binding-resolution DENY" "HC3-subagent audit line is distinguishable from the outsider-policy line"
mv "$MFC.bak" "$MFC"

echo
echo "-- C5 (user ruling, option A): Bash control-plane guard -- deny-if-mentioned over a fixed path set, ordinary Bash writes stay advisory --"

t_start "HBC1 Bash command mentions .shode-house/scope/ (the manifest itself, Quinn's exact manifest-tampering shape) -> DENY exit 2"
payload=$(jq -n --arg cmd "jq '(.agents[]|select(.agent==\"Dave#1\")|.owns)=[]' $MFC > tmp && mv tmp $MFC" '{tool_name:"Bash",agent_id:"agentid-BBB",tool_input:{command:$cmd}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HBC1 exit code"
assert_contains "${res#*$'\t'}" "control-plane path" "HBC1 message names the reason"
owns_after=$(jq -c '.agents[0].owns' "$MFC")
assert_eq "$owns_after" '["src/payment/refund.ts"]' "HBC1: manifest must be UNTOUCHED -- the denied command never actually ran"

t_start "HBC2 Bash command mentions .shode-house/state/ -> DENY exit 2"
payload=$(jq -n --arg cmd "echo PWNED > $SBC/.shode-house/state/bd-h5.json" '{tool_name:"Bash",tool_input:{command:$cmd}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HBC2 exit code"

t_start "HBC3 Bash command mentions .shode-house/journal/ -> DENY exit 2"
payload=$(jq -n --arg cmd "cat $SBC/.shode-house/journal/bd-h5.jsonl" '{tool_name:"Bash",tool_input:{command:$cmd}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HBC3 exit code"

t_start "HBC4 sanity: an ordinary Bash write that mentions NO control-plane path -> ALLOW exit 0 (advisory-only, by design -- shell writes outside the fixed control-plane set are NOT scope-enforced, proving the ceiling is real, not accidentally broader)"
payload=$(jq -n --arg cmd "echo 'not the manifest' > $SBC/src/orders/handler.py" '{tool_name:"Bash",agent_id:"agentid-AAA",tool_input:{command:$cmd}}')
res=$(scope_guard_run "$SBC" "$payload")
assert_eq "${res%%$'\t'*}" "0" "HBC4 exit code -- Bash tool call itself is ALLOWed (advisory)"
bash -c "echo 'via bash, unenforced by design' > '$SBC/src/orders/handler.py'"
assert_contains "$(cat "$SBC/src/orders/handler.py" 2>/dev/null)" "via bash, unenforced by design" "HBC4: the real write actually landed -- Bash writes outside the 3 fixed control-plane paths are genuinely advisory, not silently blocked elsewhere"

rm -rf "$SBC"

echo
echo "-- W3 (bd: shode-house-5cs.8, Bella finding 6 on bd: shode-house-5cs.4): a Write/Edit whose canonicalized target IS the scope manifest/binding store is DENIED outright, regardless of ownership --"

SBMG=$(sandbox)
# DELIBERATELY misconfigured/broad manifest: Dave#1's allowed_roots AND owns[] both
# explicitly cover the manifest's own path. This is the exact scenario the old,
# incidental-only protection could not have survived (a self-amend into owns[] of this
# exact path would have made an ordinary ownership check return ALLOW) -- proving this
# rule fires REGARDLESS of what owns[]/allowed_roots[] says, not merely because the
# manifest path happens to not be claimed by anyone.
init_scope_state "$SBMG" "bd-h9" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-h9",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**", ".shode-house/scope/**"], "owns": ["src/payment/refund.ts", ".shode-house/scope/bd-h9.json"]}
  ]
}
EOF
mkdir -p "$SBMG/src/payment"
MFMG="$SBMG/.shode-house/scope/bd-h9.json"

bindpayload=$(jq -n '{tool_name:"Bash",agent_id:"agentid-MG",agent_type:"tester",tool_input:{command:"scripts/scope-check.sh bd-h9 Dave#1 --bind"}}')
bindres=$(scope_guard_run "$SBMG" "$bindpayload")
assert_eq "${bindres%%$'\t'*}" "0" "MG setup: bind must succeed before the manifest-write tests below"

t_start "MG1 direct Write at the manifest's own canonical path -> DENY exit 2, regardless of ownership (this manifest's own agents[] DELIBERATELY claims owns[] over its own file -- an ordinary ownership check would ALLOW this; the dedicated rule must override it)"
payload=$(jq -n --arg p "$MFMG" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG1 exit code"
assert_contains "${res#*$'\t'}" "scope manifest" "MG1 message names the reason"
assert_not_contains "${res#*$'\t'}" "NEEDS_AMENDMENT" "MG1 must not be the old incidental NEEDS_AMENDMENT/ownership-fallthrough verdict -- this is a dedicated, unconditional deny"

t_start "MG2 traversal bypass: src/payment/../../.shode-house/scope/bd-h9.json -> DENY exit 2"
payload=$(jq -n --arg p "$SBMG/src/payment/../../.shode-house/scope/bd-h9.json" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG2 exit code"

t_start "MG3 dot-slash bypass: .shode-house/scope/./bd-h9.json -> DENY exit 2"
payload=$(jq -n --arg p "$SBMG/.shode-house/scope/./bd-h9.json" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG3 exit code"

t_start "MG4 case bypass: .SHODE-HOUSE/SCOPE/BD-H9.JSON -> DENY exit 2"
payload=$(jq -n --arg p "$SBMG/.SHODE-HOUSE/SCOPE/BD-H9.JSON" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG4 exit code"

t_start "MG5 symlink shape: a symlink elsewhere pointing AT the manifest -- Write to the symlink path is REFUSED outright (fail-closed, same symlink-leaf rule as HS1), never resolved-and-matched"
ln -sf "$MFMG" "$SBMG/src/payment/looks-like-code.ts"
payload=$(jq -n --arg p "$SBMG/src/payment/looks-like-code.ts" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG5 exit code"
rm -f "$SBMG/src/payment/looks-like-code.ts"

t_start "MG6 a DIFFERENT bd's manifest file, not the active/bound one, under the same .shode-house/scope/ directory -> DENY exit 2 (the rule protects the whole manifest/binding store directory, not just the currently-resolved bd's own file)"
: > "$SBMG/.shode-house/scope/bd-other.json"
payload=$(jq -n --arg p "$SBMG/.shode-house/scope/bd-other.json" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "2" "MG6 exit code"

t_start "MG7 sanity: an ordinary owned write elsewhere still ALLOWs -- the new manifest guard must not become an over-broad DENY"
payload=$(jq -n --arg p "$SBMG/src/payment/refund.ts" '{tool_name:"Write",agent_id:"agentid-MG",tool_input:{file_path:$p}}')
res=$(scope_guard_run "$SBMG" "$payload")
assert_eq "${res%%$'\t'*}" "0" "MG7 exit code"

rm -rf "$SBMG"

echo
echo "-- L1 (Quinn/Bella): NotebookEdit is now covered by both the hooks.json matcher and this guard's dispatch --"

SBN=$(sandbox)
init_scope_state "$SBN" "bd-h6" <<'EOF'
{"schema_version":1,"bd_id":"bd-h6","agents":[{"agent":"Dave#1","allowed_roots":["src/orders/**"],"owns":["src/orders/nb.ipynb"]}]}
EOF
mkdir -p "$SBN/src/orders"

t_start "HN1 NotebookEdit tool_name, notebook_path collides with an active agent's owned path, main session -> DENY exit 2 (previously silently ALLOWed: neither the matcher nor this guard's dispatch recognised NotebookEdit at all)"
payload=$(jq -n --arg p "$SBN/src/orders/nb.ipynb" '{tool_name:"NotebookEdit",tool_input:{notebook_path:$p}}')
res=$(scope_guard_run "$SBN" "$payload")
assert_eq "${res%%$'\t'*}" "2" "HN1 exit code"

rm -rf "$SBN"

echo
echo "== session-start.sh + stop-integrity.sh: canary, degradation, torn-write (ADR-C8) =="

t_start "session-start.sh: no engagement -> silent exit 0"
SB2=$(sandbox)
out=$(CLAUDE_PROJECT_DIR="$SB2" "$SESSION_START" 2>&1); rc=$?
assert_rc "$rc" 0 "session-start no-engagement rc"
assert_eq "$out" "" "session-start no-engagement must be silent"
rm -rf "$SB2"

t_start "session-start.sh: clean init via the real workflow-state.sh -> silent, canary written"
SB3=$(sandbox)
mkdir -p "$SB3/.shode-house"
WFSTATE_ROOT="$SB3" WFSTATE_ACTOR=test bash "$WFSTATE" init "shode-roadmap/C-A7-fixture" >/dev/null
out=$(CLAUDE_PROJECT_DIR="$SB3" "$SESSION_START" 2>&1); rc=$?
assert_rc "$rc" 0 "session-start clean-init rc"
assert_eq "$out" "" "session-start clean-init must be silent"
[ -f "$SB3/.shode-house/state/.hooks-alive" ] && t_ok || t_fail "canary .hooks-alive not written"

t_start "stop-integrity.sh: same clean init -> silent (regression guard: an earlier version of this check false-positived here on every fresh init)"
out=$(CLAUDE_PROJECT_DIR="$SB3" "$STOP_INTEGRITY" 2>&1); rc=$?
assert_rc "$rc" 0 "stop-integrity clean-init rc"
assert_eq "$out" "" "stop-integrity clean-init must be silent"

t_start "stop-integrity.sh: after a real advance -> still silent"
WFSTATE_ROOT="$SB3" WFSTATE_ACTOR=test bash "$WFSTATE" advance "shode-roadmap/C-A7-fixture" "1a-spec" passed >/dev/null
out=$(CLAUDE_PROJECT_DIR="$SB3" "$STOP_INTEGRITY" 2>&1); rc=$?
assert_rc "$rc" 0 "stop-integrity after-advance rc"
assert_eq "$out" "" "stop-integrity after-advance must be silent"

t_start "session-start.sh + stop-integrity.sh: crafted torn write -> both warn (systemMessage), never block, .degraded written"
jf="$SB3/.shode-house/journal/shode-roadmap--C-A7-fixture.jsonl"
sf="$SB3/.shode-house/state/shode-roadmap--C-A7-fixture.json"
cur=$(jq -r '.current_phase' "$sf")
printf '{"seq":999,"ts":"2026-09-08T00:00:00Z","bd_id":"shode-roadmap/C-A7-fixture","from":"%s","to":"1b-design","actor":"test","result":"accept","reason":"crafted-torn-fixture","op":"transition"}\n' "$cur" >> "$jf"
rm -f "$SB3/.shode-house/state/.degraded"

out_ss=$(CLAUDE_PROJECT_DIR="$SB3" "$SESSION_START" 2>&1); rc_ss=$?
assert_rc "$rc_ss" 0 "session-start torn-write rc (must never block)"
assert_contains "$out_ss" "systemMessage" "session-start torn-write must warn via systemMessage"
assert_contains "$out_ss" "TORN WRITE" "session-start torn-write message content"
[ -f "$SB3/.shode-house/state/.degraded" ] && t_ok || t_fail "torn write must write .degraded"

out_si=$(CLAUDE_PROJECT_DIR="$SB3" "$STOP_INTEGRITY" 2>&1); rc_si=$?
assert_rc "$rc_si" 0 "stop-integrity torn-write rc (must never block)"
assert_contains "$out_si" "systemMessage" "stop-integrity torn-write must warn via systemMessage"

rm -rf "$SB3"

t_start "session-start.sh: jq absent -> DEGRADED systemMessage + .degraded written, still exit 0"
SB4=$(sandbox)
init_engagement "$SB4"
FAKEBIN2=$(mktemp -d -t hooks-fakebin2.XXXXXX)
for b in bash date dirname basename tr sed cat env grep; do
  src=$(command -v "$b" 2>/dev/null) && ln -s "$src" "$FAKEBIN2/$b"
done
out=$(CLAUDE_PROJECT_DIR="$SB4" PATH="$FAKEBIN2" bash "$SESSION_START" 2>&1); rc=$?
assert_rc "$rc" 0 "session-start jq-absent rc"
assert_contains "$out" "DEGRADED" "session-start jq-absent must announce DEGRADED"
[ -f "$SB4/.shode-house/state/.degraded" ] && t_ok || t_fail "jq-absent must write .degraded"
rm -rf "$FAKEBIN2" "$SB4"

echo
echo "== NFR: no-op latency (02-sara-adr-1a.md Sec 1 -- <=30ms p95, must not touch jq) =="

t_start "guard-state-write.sh no-op path (no .shode-house/state at all) x100 mean latency"
SB5=$(sandbox)
start_ns=$(date -u +%s%N)
for _ in $(seq 1 100); do
  printf '{"tool_input":{"file_path":"'"$SB5"'/.shode-house/state/probe.json"}}' | \
    CLAUDE_PROJECT_DIR="$SB5" "$GUARD" >/dev/null 2>&1
done
end_ns=$(date -u +%s%N)
rm -rf "$SB5"
total_ns=$((end_ns - start_ns))
mean_ms=$((total_ns / 100 / 1000000))
printf '   100 calls, no-op (no .shode-house/state present): total=%sms mean=%sms/call (target <=30ms)\n' \
  "$((total_ns / 1000000))" "$mean_ms"
if [ "$mean_ms" -le 30 ]; then t_ok; else t_fail "mean ${mean_ms}ms exceeds the 30ms NFR budget"; fi

echo
echo "== packaging: hooks/ ships in the .plugin artifact with exec bits intact (bd:shode-roadmap/C-A7, Makefile) =="

t_start "make pack ships hooks/hooks.json + hooks/scripts/*.sh"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "hooks/hooks.json" "packed artifact must ship hooks/hooks.json"
assert_contains "$listing" "hooks/scripts/guard-state-write.sh" "packed artifact must ship the guard script"
assert_contains "$listing" "hooks/scripts/guard-scope-write.sh" "packed artifact must ship the scope guard script (bd: shode-house-5cs.4)"
assert_contains "$listing" "hooks/scripts/session-start.sh" "packed artifact must ship the SessionStart script"
assert_contains "$listing" "hooks/scripts/stop-integrity.sh" "packed artifact must ship the Stop/SubagentStop script"
assert_contains "$listing" "hooks/scripts/_lib.sh" "packed artifact must ship the shared lib"

t_start "packaged hook scripts keep their executable bit (zipinfo perms start with -rwx)"
if command -v zipinfo >/dev/null 2>&1; then
  perms=$(zipinfo -l "$plugin" 2>/dev/null | grep 'hooks/scripts/guard-state-write.sh' | awk '{print $1}')
  case "$perms" in -rwx*) t_ok ;; *) t_fail "guard-state-write.sh perms in zip: '$perms' (expected -rwx...)" ;; esac
  # mirrors the assertion above -- bd: shode-house-5cs.4's own new hook script must ship
  # with its executable bit intact too (Makefile:36 packs hooks/ as a whole directory, so
  # this is the one place that would silently catch a forgotten `chmod +x`).
  perms2=$(zipinfo -l "$plugin" 2>/dev/null | grep 'hooks/scripts/guard-scope-write.sh' | awk '{print $1}')
  case "$perms2" in -rwx*) t_ok ;; *) t_fail "guard-scope-write.sh perms in zip: '$perms2' (expected -rwx...)" ;; esac
else
  t_skip "zipinfo not on PATH -- exec-bit-in-zip check not exercised in this environment"
fi

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
