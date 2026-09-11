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
pack_out=$(cd "$REPO_ROOT" && make pack-legacy 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "hooks/hooks.json" "packed artifact must ship hooks/hooks.json"
assert_contains "$listing" "hooks/scripts/guard-state-write.sh" "packed artifact must ship the guard script"
assert_contains "$listing" "hooks/scripts/session-start.sh" "packed artifact must ship the SessionStart script"
assert_contains "$listing" "hooks/scripts/stop-integrity.sh" "packed artifact must ship the Stop/SubagentStop script"
assert_contains "$listing" "hooks/scripts/_lib.sh" "packed artifact must ship the shared lib"

t_start "packaged hook scripts keep their executable bit (zipinfo perms start with -rwx)"
if command -v zipinfo >/dev/null 2>&1; then
  perms=$(zipinfo -l "$plugin" 2>/dev/null | grep 'hooks/scripts/guard-state-write.sh' | awk '{print $1}')
  case "$perms" in -rwx*) t_ok ;; *) t_fail "guard-state-write.sh perms in zip: '$perms' (expected -rwx...)" ;; esac
else
  t_skip "zipinfo not on PATH -- exec-bit-in-zip check not exercised in this environment"
fi

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
