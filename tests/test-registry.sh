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
CAPS="$REPO_ROOT/references/registry/capabilities.json"
ROUTES="$REPO_ROOT/references/registry/routes.json"

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
t_start "route.sh: payment/kyc tags -> require fintech-expert, phases include phase_1b + phase_3b"
D=$(sandbox)
echo '{"tags":["payment","kyc"]}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "payment/kyc request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "fintech-expert" "payment+kyc should require fintech-expert"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "phase_1b" "domain trigger should include phase_1b"
assert_contains "$phases" "phase_3b" "domain trigger should include phase_3b"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: pii=true -> require security-engineer, phases include phase_1c + phase_3b"
D=$(sandbox)
echo '{"pii":true}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "pii request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "security-engineer" "pii=true should require security-engineer"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "phase_1c" "pii trigger should include phase_1c"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: frontend=true -> require ux-ui-designer, phases include phase_1b + phase_3a"
D=$(sandbox)
echo '{"frontend":true}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "frontend request should resolve"
req=$(printf '%s' "$out" | jq -c '.required')
assert_contains "$req" "ux-ui-designer" "frontend=true should require ux-ui-designer"
phases=$(printf '%s' "$out" | jq -c '.phases')
assert_contains "$phases" "phase_3a" "frontend trigger should include phase_3a"
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
t_start "packaging: make pack ships references/registry/*.json + scripts/route.sh + scripts/policy-check.sh"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "references/registry/capabilities.json" "packed artifact must ship the capability registry"
assert_contains "$listing" "references/registry/routes.json" "packed artifact must ship the route registry"
assert_contains "$listing" "scripts/route.sh" "packed artifact must ship the resolver script"
assert_contains "$listing" "scripts/policy-check.sh" "packed artifact must ship the policy-check script"

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
