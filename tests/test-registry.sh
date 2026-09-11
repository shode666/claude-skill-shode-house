#!/usr/bin/env bash
# tests/test-registry.sh -- bash-only test suite for Milestone B (bd: shode-roadmap/C-B1)
# scripts/route.sh + scripts/policy-check.sh + references/registry/*.json
#
# No framework dependency (same style as tests/test-workflow-state.sh) -- plain
# bash test functions + a tiny assert library. Fixture request.json / bd
# artifact dirs are written to a mktemp sandbox per test, never touching the
# real repo state. Wired into ci.yml as exactly ONE step (CLAUDE.md rule:
# "เพิ่ม step ใหม่ได้ไม่เกิน 1 step สำหรับ Milestone B ทั้งก้อน").
#
# Usage: bash tests/test-registry.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROUTE="$REPO_ROOT/scripts/route.sh"
POLICY="$REPO_ROOT/scripts/policy-check.sh"
WFSTATE="$REPO_ROOT/scripts/workflow-state.sh"
CAPS="$REPO_ROOT/references/registry/capabilities.json"
ROUTES="$REPO_ROOT/references/registry/routes.json"
TRANSITIONS="$REPO_ROOT/references/state-machine/transitions.json"

PASS=0
FAIL=0
CUR_TEST=""

t_start() { CUR_TEST="$1"; printf -- '-- %s\n' "$1"; }
t_ok()    { PASS=$((PASS + 1)); printf '   ok\n'; }
t_fail()  { FAIL=$((FAIL + 1)); printf '   FAIL (%s): %s\n' "$CUR_TEST" "$1"; }

assert_eq() {
  if [ "$1" = "$2" ]; then t_ok; else t_fail "$3 -- got '$1' want '$2'"; fi
}
assert_contains() {
  case "$1" in *"$2"*) t_ok ;; *) t_fail "$3 -- '$1' does not contain '$2'" ;; esac
}
assert_true()  { if [ "$1" -eq 0 ]; then t_ok; else t_fail "$2 -- exit code $1"; fi; }
assert_false() { if [ "$1" -ne 0 ]; then t_ok; else t_fail "$2 -- expected non-zero exit"; fi; }

sandbox() { mktemp -d -t registry-test.XXXXXX; }

# PATH with bd's own directory stripped out (if bd is installed at all) -- used to
# deterministically exercise policy-check.sh's "bd unavailable" degrade path regardless
# of whether the host running this suite happens to have bd installed or not (same
# technique as tests/test-workflow-state.sh's path_without_bd()).
path_without_bd() {
  local bd_path bd_dir
  bd_path=$(command -v bd 2>/dev/null) || { printf '%s' "$PATH"; return; }
  bd_dir=$(dirname "$bd_path")
  printf '%s' "$PATH" | awk -v d="$bd_dir" 'BEGIN{RS=":"; ORS=":"} $0!=d {print}'
}
HAVE_BD=0
command -v bd >/dev/null 2>&1 && HAVE_BD=1

# ---------------------------------------------------------------------------
t_start "registries: capabilities.json + routes.json are valid JSON with non-empty tables"
jq empty "$CAPS" >/dev/null 2>&1; assert_true "$?" "capabilities.json must parse as JSON"
jq empty "$ROUTES" >/dev/null 2>&1; assert_true "$?" "routes.json must parse as JSON"
n=$(jq '.capabilities | length' "$CAPS"); [ "$n" -gt 0 ] && t_ok || t_fail "capabilities table should be non-empty"
n=$(jq '.routes | length' "$ROUTES"); [ "$n" -gt 0 ] && t_ok || t_fail "routes table should be non-empty"

# ---------------------------------------------------------------------------
t_start "route.sh: rejects missing arg / missing file / invalid JSON (fails loud, not silent)"
"$ROUTE" >/dev/null 2>&1; assert_false "$?" "no arg should fail"
"$ROUTE" /no/such/file.json >/dev/null 2>&1; assert_false "$?" "missing file should fail"
D=$(sandbox)
echo 'not json' > "$D/bad.json"
"$ROUTE" "$D/bad.json" >/dev/null 2>&1; assert_false "$?" "invalid JSON should fail"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: unknown capability is rejected (no guessing an owner)"
D=$(sandbox)
echo '{"capability":"not-a-real-capability"}' > "$D/req.json"
err=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_false "$rc" "unknown capability should fail"
assert_contains "$err" "unknown capability" "error should name the problem"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: default capability (no 'capability' key) resolves primary=developer"
D=$(sandbox)
echo '{}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "empty request should still resolve"
primary=$(printf '%s' "$out" | jq -r '.primary')
assert_eq "$primary" "developer" "default capability should be production-code -> developer"
required_n=$(printf '%s' "$out" | jq '.required | length')
assert_eq "$required_n" "0" "no trigger matched -> required[] empty"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: payment/kyc tags -> require fintech-expert, phases include 1b-design + 3b-review"
D=$(sandbox)
echo '{"tags":["payment","kyc"]}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "payment/kyc request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "fintech-expert" "payment+kyc should require fintech-expert"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "1b-design" "domain trigger should include 1b-design"
assert_contains "$phases" "3b-review" "domain trigger should include 3b-review"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: pii=true -> require security-engineer, phases include 1c-security + 3b-review"
D=$(sandbox)
echo '{"pii":true}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "pii request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "security-engineer" "pii=true should require security-engineer"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "1c-security" "pii trigger should include 1c-security"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: frontend=true -> require ux-ui-designer, phases include 1b-design + 3a-ui-check"
D=$(sandbox)
echo '{"frontend":true}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "frontend request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "ux-ui-designer" "frontend=true should require ux-ui-designer"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "3a-ui-check" "frontend trigger should include 3a-ui-check"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: multiple triggers at once (pii + frontend + ecommerce tag) aggregate + dedupe"
D=$(sandbox)
echo '{"pii":true,"frontend":true,"tags":["cart"]}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "combined request should resolve"
req_n=$(printf '%s' "$out" | jq '.required | length')
assert_eq "$req_n" "3" "should require exactly 3 distinct agents (security, ux, ecommerce)"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "ecommerce-expert" "cart tag should require ecommerce-expert"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: primary is excluded from required[] even if a matched route names it"
D=$(sandbox)
echo '{"capability":"fintech-domain","tags":["payment"]}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1)
primary=$(printf '%s' "$out" | jq -r '.primary')
assert_eq "$primary" "fintech-expert" "capability fintech-domain -> primary fintech-expert"
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *fintech-expert*) t_fail "primary must not also appear in required[]" ;; *) t_ok ;; esac
rm -rf "$D"

# ---------------------------------------------------------------------------
# MUTATION (a): remove a route rule -> resolver must stop returning that agent
t_start "MUTATION (a): deleting the frontend route from routes.json makes the resolver stop requiring ux-ui-designer"
D=$(sandbox)
echo '{"frontend":true}' > "$D/req.json"
before_out=$("$ROUTE" "$D/req.json" 2>&1)
before_req=$(printf '%s' "$before_out" | jq -c '.required')
assert_contains "$before_req" "ux-ui-designer" "sanity: baseline still requires ux-ui-designer"

BACKUP=$(mktemp -t routes-backup.XXXXXX)
cp "$ROUTES" "$BACKUP"
tmp=$(mktemp)
jq 'del(.routes[] | select(.id == "frontend"))' "$ROUTES" > "$tmp" && mv "$tmp" "$ROUTES"

mutated_out=$("$ROUTE" "$D/req.json" 2>&1)
mutated_req=$(printf '%s' "$mutated_out" | jq -c '.required')
case "$mutated_req" in
  *ux-ui-designer*) t_fail "mutation should have removed ux-ui-designer from required[] but it is still there -- resolver did not react to the missing rule (test would go red)" ;;
  *) t_ok ;;
esac

mv "$BACKUP" "$ROUTES"
restored_out=$("$ROUTE" "$D/req.json" 2>&1)
restored_req=$(printf '%s' "$restored_out" | jq -c '.required')
assert_contains "$restored_req" "ux-ui-designer" "restore: routes.json back to original, ux-ui-designer required again"
rm -rf "$D"

# ---------------------------------------------------------------------------
# C-A6 iter0: routes.json and transitions.json used to speak two different phase
# vocabularies (phase_1a/1b/3b vs 1a-spec/1b-design/3b-review). transitions.json is the
# single source of truth (CLAUDE.md 'Repo'); this test locks that in going forward.
t_start "phase-vocab: every phase id used in routes.json's phases[] exists in transitions.json's states[] (no drift between the two registries)"
unknown=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  jq -e --arg p "$p" '.states | index($p) != null' "$TRANSITIONS" >/dev/null 2>&1 \
    || unknown="${unknown}${unknown:+,}$p"
done < <(jq -r '.routes[].phases[]' "$ROUTES" | sort -u)
[ -z "$unknown" ] && t_ok || t_fail "phase id(s) in routes.json not found in transitions.json states[]: $unknown"

# ---------------------------------------------------------------------------
# MUTATION (c): corrupt one route's phase id into a value not in transitions.json's
# states[] -> the drift test above must go red (proves it actually checks membership,
# not just "is non-empty").
t_start "MUTATION (c): a bogus phase id injected into routes.json makes the phase-vocab drift test fail"
BACKUP=$(mktemp -t routes-backup2.XXXXXX)
cp "$ROUTES" "$BACKUP"
tmp=$(mktemp)
jq '(.routes[] | select(.id == "frontend") | .phases) |= (. + ["phase_bogus_drift"])' "$ROUTES" > "$tmp" && mv "$tmp" "$ROUTES"

mutated_unknown=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  jq -e --arg p "$p" '.states | index($p) != null' "$TRANSITIONS" >/dev/null 2>&1 \
    || mutated_unknown="${mutated_unknown}${mutated_unknown:+,}$p"
done < <(jq -r '.routes[].phases[]' "$ROUTES" | sort -u)
case "$mutated_unknown" in
  *phase_bogus_drift*) t_ok ;;
  *) t_fail "injecting an unknown phase id should have made the drift check fail but it reported unknown='$mutated_unknown' -- the check did not react to the injected drift (test would stay green, gate not proven to enforce)" ;;
esac

mv "$BACKUP" "$ROUTES"
restored_unknown=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  jq -e --arg p "$p" '.states | index($p) != null' "$TRANSITIONS" >/dev/null 2>&1 \
    || restored_unknown="${restored_unknown}${restored_unknown:+,}$p"
done < <(jq -r '.routes[].phases[]' "$ROUTES" | sort -u)
[ -z "$restored_unknown" ] && t_ok || t_fail "restore: routes.json back to original, drift check should be clean again"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: rejects missing arg / missing enforcement map"
"$POLICY" >/dev/null 2>&1; assert_false "$?" "no arg should fail"
POLICYCHECK_MAP=/no/such/map.json "$POLICY" some-bd >/dev/null 2>&1
assert_false "$?" "missing enforcement map should fail"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: every rule in .enforcement-map.json gets exactly one PASS/FAIL/SKIP line, none silently omitted"
n_rules=$(jq '.rules | length' "$REPO_ROOT/.enforcement-map.json")
out=$("$POLICY" no-such-bd-anywhere 2>&1)
n_lines=$(printf '%s\n' "$out" | grep -cE '^(PASS|FAIL|SKIP) ')
assert_eq "$n_lines" "$n_rules" "one verdict line per rule in the enforcement map"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: no bd artifact dir -> anti-puppet + redact report SKIP, never a silent PASS"
out=$("$POLICY" no-such-bd-anywhere 2>&1)
assert_contains "$out" "SKIP anti-puppet" "no artifact -> anti-puppet must be SKIP not PASS"
assert_contains "$out" "SKIP redact" "no artifact -> redact must be SKIP not PASS"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: clean bd artifact (real evidence, no placeholder/secret) -> anti-puppet + redact PASS"
D=$(sandbox)
mkdir -p "$D/outputs/clean-bd"
cat > "$D/outputs/clean-bd/01-dave-impl.md" <<'EOF'
## Verify
$ pnpm test
5 passed
EOF
out=$(POLICYCHECK_ROOT="$D" "$POLICY" clean-bd 2>&1); rc=$?
assert_true "$rc" "clean bd should exit 0 (no FAIL)"
assert_contains "$out" "PASS anti-puppet" "clean artifact should PASS anti-puppet"
assert_contains "$out" "PASS redact" "clean artifact with no secret should PASS redact"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: placeholder without OPEN QUESTION -> anti-puppet FAILs, exit code non-zero"
D=$(sandbox)
mkdir -p "$D/outputs/placeholder-bd"
cat > "$D/outputs/placeholder-bd/01-dave-impl.md" <<'EOF'
## Config
Endpoint: TBD
EOF
out=$(POLICYCHECK_ROOT="$D" "$POLICY" placeholder-bd 2>&1); rc=$?
assert_false "$rc" "a FAIL rule should make policy-check.sh exit non-zero"
assert_contains "$out" "FAIL anti-puppet" "TBD without OPEN QUESTION should FAIL anti-puppet"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "policy-check.sh: unredacted secret-shaped token -> redact FAILs"
D=$(sandbox)
mkdir -p "$D/outputs/secret-bd"
cat > "$D/outputs/secret-bd/01-dave-impl.md" <<'EOF'
## Config
API key: sk-abcdefghijklmnop1234567890
EOF
out=$(POLICYCHECK_ROOT="$D" "$POLICY" secret-bd 2>&1); rc=$?
assert_false "$rc" "unredacted secret should make policy-check.sh exit non-zero"
assert_contains "$out" "FAIL redact" "unredacted sk- token should FAIL redact"
rm -rf "$D"

# ---------------------------------------------------------------------------
# MUTATION (b): make policy-check.sh skip a rule it currently really checks ->
# the fixture test above must go red
t_start "MUTATION (b): disabling the anti-puppet real check (force it to SKIP) breaks the placeholder-FAIL fixture test"
D=$(sandbox)
mkdir -p "$D/outputs/placeholder-bd2"
cat > "$D/outputs/placeholder-bd2/01-dave-impl.md" <<'EOF'
## Config
Endpoint: TBD
EOF
baseline_out=$(POLICYCHECK_ROOT="$D" "$POLICY" placeholder-bd2 2>&1)
assert_contains "$baseline_out" "FAIL anti-puppet" "sanity: baseline still really checks anti-puppet and FAILs"

BACKUP=$(mktemp -t policy-backup.XXXXXX)
cp "$POLICY" "$BACKUP"
# mutate: force the anti-puppet branch to always SKIP instead of running the real
# placeholder check (simulates "someone quietly turned a real check into a SKIP")
sed -i.bak \
  's/if ! has_artifacts; then$/if true; then report SKIP "$id" "MUTATED: real check disabled"; elif false; then/' \
  "$POLICY"

mutated_out=$(POLICYCHECK_ROOT="$D" bash "$POLICY" placeholder-bd2 2>&1)
case "$mutated_out" in
  *"FAIL anti-puppet"*) t_fail "mutation should have turned anti-puppet into a SKIP but it still FAILs -- mutation did not take effect (test would stay green, gate not proven to enforce)" ;;
  *"SKIP anti-puppet -- MUTATED"*) t_ok ;;
  *) t_fail "mutation produced unexpected output: $mutated_out" ;;
esac

mv "$BACKUP" "$POLICY"
chmod +x "$POLICY"
rm -f "$POLICY.bak"
restored_out=$(POLICYCHECK_ROOT="$D" "$POLICY" placeholder-bd2 2>&1)
assert_contains "$restored_out" "FAIL anti-puppet" "restore: policy-check.sh back to original, real anti-puppet check FAILs again"
rm -rf "$D"

# ---------------------------------------------------------------------------
# C-A6 iter0: policy-check.sh gained two more real (non-SKIP-always) checks now that
# Milestone A's .shode-house/state/<bd>.json exists to read from -- dod (phase passed
# without owner) and close-on-done (workflow reached terminal phase but bd still open).
# These use the real workflow-state.sh binary to build a genuine state.json fixture
# (not a hand-written one) so the test also exercises the actual C-A5/C-A6 integration
# seam between the two scripts, not just policy-check.sh in isolation.
t_start "policy-check.sh: dod SKIP when no Milestone A state exists for this bd (a markdown artifact alone is not enough)"
D=$(sandbox)
mkdir -p "$D/outputs/no-state-bd"
cat > "$D/outputs/no-state-bd/01-dave-impl.md" <<'EOF'
## Verify
$ pnpm test
5 passed
EOF
out=$(POLICYCHECK_ROOT="$D" "$POLICY" no-state-bd 2>&1)
assert_contains "$out" "SKIP dod" "no state.json -> dod must SKIP, never guess PASS"
assert_contains "$out" "SKIP close-on-done" "no state.json -> close-on-done must SKIP, never guess PASS"
rm -rf "$D"

t_start "policy-check.sh: dod FAILs when Milestone A state has a passed phase without an owner"
D=$(sandbox); mkdir -p "$D/.shode-house"
WFSTATE_ROOT="$D" "$WFSTATE" init dod-bd >/dev/null 2>&1
WFSTATE_ROOT="$D" "$WFSTATE" advance dod-bd 1a-spec >/dev/null 2>&1   # 0-discover -> passed, owners never set
out=$(POLICYCHECK_ROOT="$D" "$POLICY" dod-bd 2>&1); rc=$?
assert_false "$rc" "a FAIL rule should make policy-check.sh exit non-zero"
assert_contains "$out" "FAIL dod" "phase passed without owner should FAIL the dod rule"
assert_contains "$out" "0-discover" "FAIL reason should name the specific phase missing an owner"
rm -rf "$D"

t_start "policy-check.sh: dod PASSes once the passed phase has an owner recorded (positive control)"
D=$(sandbox); mkdir -p "$D/.shode-house"
WFSTATE_ROOT="$D" "$WFSTATE" init dod-ok >/dev/null 2>&1
sf="$D/.shode-house/state/dod-ok.json"
tmp=$(mktemp); jq '.phases["0-discover"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
WFSTATE_ROOT="$D" "$WFSTATE" advance dod-ok 1a-spec >/dev/null 2>&1
out=$(POLICYCHECK_ROOT="$D" "$POLICY" dod-ok 2>&1); rc=$?
assert_true "$rc" "an owned passed phase should not fail policy-check.sh"
assert_contains "$out" "PASS dod" "owner present -> dod PASS"
rm -rf "$D"

t_start "policy-check.sh: close-on-done SKIPs (not a guessed PASS) while workflow hasn't reached the terminal phase yet"
D=$(sandbox); mkdir -p "$D/.shode-house"
WFSTATE_ROOT="$D" "$WFSTATE" init cod-1 >/dev/null 2>&1
out=$(POLICYCHECK_ROOT="$D" "$POLICY" cod-1 2>&1); rc=$?
assert_true "$rc" "SKIP alone should not fail exit code"
assert_contains "$out" "SKIP close-on-done" "workflow not done yet -> SKIP, never guess"
rm -rf "$D"

t_start "policy-check.sh: close-on-done SKIPs loudly when bd is unavailable, even though the workflow reached its terminal phase"
D=$(sandbox); mkdir -p "$D/.shode-house"
WFSTATE_ROOT="$D" "$WFSTATE" init nobd-cod >/dev/null 2>&1
sf="$D/.shode-house/state/nobd-cod.json"
tmp=$(mktemp); jq '.current_phase = "6-operate" | .phases["6-operate"].status = "passed" | .phases["6-operate"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
out=$(PATH="$(path_without_bd)" POLICYCHECK_ROOT="$D" "$POLICY" nobd-cod 2>&1); rc=$?
assert_true "$rc" "bd-unavailable SKIP alone should not fail exit code"
assert_contains "$out" "SKIP close-on-done" "bd unavailable -> SKIP, never a silent PASS"
assert_contains "$out" "bd unavailable" "SKIP reason should say why"
rm -rf "$D"

if [ "$HAVE_BD" -eq 1 ]; then
  t_start "policy-check.sh: close-on-done FAILs when workflow reached done but the real bd is still open, PASSes once closed (real bd workspace)"
  D=$(sandbox); mkdir -p "$D/.shode-house"
  ( cd "$D" && bd init --quiet >/dev/null 2>&1 )
  bdid=$(bd -C "$D" create "policy-check close-on-done test" --json 2>/dev/null | jq -r .id)
  WFSTATE_ROOT="$D" "$WFSTATE" init "$bdid" >/dev/null 2>&1
  sf="$D/.shode-house/state/$(printf '%s' "$bdid" | sed 's#/#--#g').json"
  tmp=$(mktemp); jq '.current_phase = "6-operate" | .phases["6-operate"].status = "passed" | .phases["6-operate"].owners = ["dave"]' "$sf" > "$tmp" && mv "$tmp" "$sf"
  out=$(POLICYCHECK_ROOT="$D" "$POLICY" "$bdid" 2>&1); rc=$?
  assert_false "$rc" "workflow done + bd still open should FAIL close-on-done"
  assert_contains "$out" "FAIL close-on-done" "should be reported as FAIL close-on-done"
  bd -C "$D" close "$bdid" --reason "test done" --json >/dev/null 2>&1
  out2=$(POLICYCHECK_ROOT="$D" "$POLICY" "$bdid" 2>&1); rc2=$?
  assert_true "$rc2" "closing the bd should make policy-check.sh exit 0"
  assert_contains "$out2" "PASS close-on-done" "closing the bd should flip close-on-done to PASS"
  rm -rf "$D"
else
  printf '   SKIP: bd not installed on this host -- close-on-done real-bd-workspace test skipped (the bd-unavailable degrade path above still ran and is what CI, no bd installed, exercises)\n'
fi

# ---------------------------------------------------------------------------
t_start "packaging: make pack ships references/registry/*.json + scripts/route.sh + scripts/policy-check.sh"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack-legacy 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "references/registry/capabilities.json" "packed artifact must ship the capability registry"
assert_contains "$listing" "references/registry/routes.json" "packed artifact must ship the route registry"
assert_contains "$listing" "scripts/route.sh" "packed artifact must ship the resolver script"
assert_contains "$listing" "scripts/policy-check.sh" "packed artifact must ship the policy-check script"

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
