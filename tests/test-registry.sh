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
# bd: shode-house-5cs.2 -- route.sh used to silently default absent .capability to
# "production-code" (Dave); that hid mis-routed/malformed requests. It must now be a
# loud error, same `die` shape as the unknown-capability check.
t_start "route.sh: missing 'capability' key is a hard error (no more silent default to production-code)"
D=$(sandbox)
echo '{}' > "$D/req.json"
err=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_false "$rc" "absent capability should fail, not silently resolve"
assert_contains "$err" "missing 'capability'" "error should name the problem"
rm -rf "$D"

t_start "route.sh: null 'capability' value is a hard error (same as absent)"
D=$(sandbox)
echo '{"capability":null}' > "$D/req.json"
err=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_false "$rc" "null capability should fail"
assert_contains "$err" "missing 'capability'" "null capability should be treated as missing"
rm -rf "$D"

t_start "route.sh: empty-string 'capability' value is a hard error (same as absent)"
D=$(sandbox)
echo '{"capability":""}' > "$D/req.json"
err=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_false "$rc" "empty-string capability should fail"
assert_contains "$err" "missing 'capability'" "empty-string capability should be treated as missing"
rm -rf "$D"

t_start "route.sh: explicit capability (no default needed) still resolves primary=developer"
D=$(sandbox)
echo '{"capability":"production-code"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "explicit production-code capability should resolve"
primary=$(printf '%s' "$out" | jq -r '.primary')
assert_eq "$primary" "developer" "production-code -> developer"
required_n=$(printf '%s' "$out" | jq '.required | length')
assert_eq "$required_n" "0" "no trigger matched -> required[] empty"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "route.sh: payment/kyc tags -> require fintech-expert, phases include 1b-design + 3b-review"
D=$(sandbox)
echo '{"capability":"production-code","tags":["payment","kyc"]}' > "$D/req.json"
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
echo '{"capability":"production-code","pii":true}' > "$D/req.json"
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
echo '{"capability":"production-code","frontend":true}' > "$D/req.json"
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
echo '{"capability":"production-code","pii":true,"frontend":true,"tags":["cart"]}' > "$D/req.json"
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
# bd: shode-house-5cs.2 -- text matching used to be raw substring (jq contains()),
# which false-positived on (1) fragments inside unrelated words and (2) generic
# English words used as bare single keywords. These are the three reproductions from
# the bug report, run through `text` with an explicit capability (route.sh no longer
# defaults capability -- see the missing-capability tests above).
t_start "regression: 'please fix this bug' no longer requires trading-expert (fix-inside-fix false positive)"
D=$(sandbox)
echo '{"capability":"production-code","text":"please fix this bug"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "should still resolve"
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'fix' alone must not route to trading-expert any more -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression: 'update the security policy doc' no longer requires insurance-expert (bare 'policy' false positive)"
D=$(sandbox)
echo '{"capability":"production-code","text":"update the security policy doc"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "should still resolve"
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *insurance-expert*) t_fail "'policy' alone must not route to insurance-expert any more -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression: 'refactor the stock ticker prefix helper' no longer requires erp-expert or trading-expert (substring-fragment + bare-word false positives)"
D=$(sandbox)
echo '{"capability":"production-code","text":"refactor the stock ticker prefix helper"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1); rc=$?
assert_true "$rc" "should still resolve"
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in
  *erp-expert*)     t_fail "'stock' alone must not route to erp-expert any more -- got $req" ;;
  *trading-expert*) t_fail "'fix' inside 'prefix' must not route to trading-expert -- got $req" ;;
  *)                t_ok ;;
esac
req_n=$(printf '%s' "$out" | jq '.required | length')
assert_eq "$req_n" "0" "this text should not require any domain expert"
rm -rf "$D"

# ---------------------------------------------------------------------------
# word-boundary mechanism, isolated from the disambiguation feature above: keywords
# that were NOT renamed (auth/trade/promo) must still refuse to match as a fragment
# inside a longer unrelated word.
t_start "word-boundary: 'author' does not falsely match keyword 'auth' as a substring fragment"
D=$(sandbox)
echo '{"capability":"production-code","text":"update the author bio"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1)
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *security-engineer*) t_fail "'author' must not match keyword 'auth' -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "word-boundary: 'trader' does not falsely match keyword 'trade' as a substring fragment"
D=$(sandbox)
echo '{"capability":"production-code","text":"the trader left early"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1)
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trader' must not match keyword 'trade' -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "word-boundary: 'promotion' does not falsely match keyword 'promo' as a substring fragment"
D=$(sandbox)
echo '{"capability":"production-code","text":"we discussed the promotion timeline"}' > "$D/req.json"
out=$("$ROUTE" "$D/req.json" 2>&1)
req=$(printf '%s' "$out" | jq -c '.required')
case "$req" in *ecommerce-expert*) t_fail "'promotion' must not match keyword 'promo' -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

# ---------------------------------------------------------------------------
# true positives via `text` (not `tags`) per route id -- every route that SHOULD
# still match, still matches, including its Thai keyword(s) where it has any. Thai
# has no ASCII word boundary to tokenize on, so these keywords stay substring-matched
# by design (see route.sh header + routes.json _comment) -- these fixtures prove that
# path is exercised and green, not just theorized.
t_start "true-positive text: domain-fintech EN keyword 'payment'"
D=$(sandbox)
echo '{"capability":"production-code","text":"process the payment now"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "fintech-expert" "'payment' should still require fintech-expert"
rm -rf "$D"

t_start "true-positive text: domain-fintech Thai keywords เงิน + ธนาคาร (no ASCII word boundary, substring by design)"
D=$(sandbox)
echo '{"capability":"production-code","text":"โอนเงินผ่านธนาคาร"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "fintech-expert" "Thai เงิน/ธนาคาร text should still require fintech-expert"
rm -rf "$D"

t_start "true-positive text: domain-erp disambiguated AND-phrase 'inventory stock' (both words present -> match)"
D=$(sandbox)
echo '{"capability":"production-code","text":"check inventory stock levels"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "erp-expert" "'inventory stock' (both words) should require erp-expert"
rm -rf "$D"

t_start "true-positive text: domain-erp Thai keyword บัญชี (substring by design)"
D=$(sandbox)
echo '{"capability":"production-code","text":"ปรับปรุงบัญชีลูกค้า"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "erp-expert" "Thai บัญชี text should still require erp-expert"
rm -rf "$D"

t_start "true-positive text: domain-sap EN keyword 'sap'"
D=$(sandbox)
echo '{"capability":"production-code","text":"upgrade our sap landscape"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "sap-expert" "'sap' should still require sap-expert"
rm -rf "$D"

t_start "true-positive text: domain-trading disambiguated AND-phrase 'fix protocol' (both words present -> match)"
D=$(sandbox)
echo '{"capability":"production-code","text":"implement the fix protocol adapter for market data"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "'fix protocol' (both words) should require trading-expert"
rm -rf "$D"

t_start "true-positive text: domain-trading disambiguated AND-phrase 'trading order' (both words present -> match)"
D=$(sandbox)
echo '{"capability":"production-code","text":"submit the trading order now"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "'trading order' (both words) should require trading-expert"
rm -rf "$D"

t_start "true-positive text: domain-insurance disambiguated AND-phrase 'insurance policy' (both words present -> match)"
D=$(sandbox)
echo '{"capability":"production-code","text":"review the insurance policy terms"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "'insurance policy' (both words) should require insurance-expert"
rm -rf "$D"

t_start "true-positive text: domain-insurance disambiguated AND-phrase 'insurance claim' (both words present -> match)"
D=$(sandbox)
echo '{"capability":"production-code","text":"process the insurance claim"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "'insurance claim' (both words) should require insurance-expert"
rm -rf "$D"

t_start "true-positive text: domain-insurance Thai keyword ประกัน (substring by design)"
D=$(sandbox)
echo '{"capability":"production-code","text":"ซื้อประกันภัยรถยนต์"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "Thai ประกัน text should still require insurance-expert"
rm -rf "$D"

t_start "true-positive text: domain-booking EN keyword 'yield'"
D=$(sandbox)
echo '{"capability":"production-code","text":"manage yield strategy"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "booking-expert" "'yield' should still require booking-expert"
rm -rf "$D"

t_start "true-positive text: domain-booking Thai keyword จอง (substring by design)"
D=$(sandbox)
echo '{"capability":"production-code","text":"ลูกค้าต้องการจองห้องพัก"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "booking-expert" "Thai จอง text should still require booking-expert"
rm -rf "$D"

t_start "true-positive text: domain-ecommerce EN keyword 'cart'"
D=$(sandbox)
echo '{"capability":"production-code","text":"add item to cart"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "ecommerce-expert" "'cart' should still require ecommerce-expert"
rm -rf "$D"

t_start "true-positive text: domain-ecommerce Thai keyword ร้านค้า (substring by design)"
D=$(sandbox)
echo '{"capability":"production-code","text":"เปิดร้านค้าออนไลน์"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "ecommerce-expert" "Thai ร้านค้า text should still require ecommerce-expert"
rm -rf "$D"

t_start "true-positive text: security-money-auth EN keyword 'auth' (unrenamed keyword, whole-token still matches)"
D=$(sandbox)
echo '{"capability":"production-code","text":"set up the auth flow for the api"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "'auth' as a whole token should still require security-engineer"
rm -rf "$D"

t_start "true-positive text: domain-trading disambiguated AND-phrase 'trading exchange' (iter1 F4 -- bare 'exchange' narrowed)"
D=$(sandbox)
echo '{"capability":"production-code","text":"connect to the trading exchange feed"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "'trading exchange' (both words, adjacent) should require trading-expert"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter1 F1 (CRITICAL, Chris) -- hyphenated when.any keywords used to be permanently
# unmatchable: scan("[a-z0-9]+") split "file-upload" into "file"+"upload", so the
# literal hyphenated string could never appear in the token array, for any phrasing.
# 3/5 security-money-auth keywords were silently dead. route.sh's tokenizer now keeps a
# hyphen-joined run as one token -- these prove all three are reachable again.
t_start "regression (iter1 F1): 'file-upload' as literal hyphenated text now requires security-engineer"
D=$(sandbox)
echo '{"capability":"production-code","text":"add file-upload endpoint"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "'file-upload' must require security-engineer -- was silently unreachable before iter1 F1"
rm -rf "$D"

t_start "regression (iter1 F1): 'ai-agent' as literal hyphenated text now requires security-engineer"
D=$(sandbox)
echo '{"capability":"production-code","text":"we need to add a ai-agent feature this sprint"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "'ai-agent' must require security-engineer -- was silently unreachable before iter1 F1"
rm -rf "$D"

t_start "regression (iter1 F1): 'external-integration' as literal hyphenated text now requires security-engineer"
D=$(sandbox)
echo '{"capability":"production-code","text":"external-integration with vendor"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "'external-integration' must require security-engineer -- was silently unreachable before iter1 F1"
rm -rf "$D"

t_start "regression (iter1 F1): all three hyphenated keywords together in one sentence (Oliver/Chris repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"add a new external-integration webhook for file-upload with an ai-agent callback"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "combined hyphenated-keyword sentence must require security-engineer"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter1 F2 (HIGH, Chris/Quinn) -- exact-token matching lost the plurals the old
# substring matcher caught for free ("order" is a substring of "orders"). Fixed with a
# conservative trailing-s stem rule applied to a phrase's final word (route.sh
# stem()). These reproduce the exact bug-report sentences and prove the fix without
# reverting to substring matching.
t_start "regression (iter1 F2): 'trading orders page' (plural) still requires trading-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading orders page"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "'trading orders' (plural 'order') must still require trading-expert"
rm -rf "$D"

t_start "regression (iter1 F2): 'insurance claims list' (plural) still requires insurance-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"insurance claims list"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "'insurance claims' (plural 'claim') must still require insurance-expert"
rm -rf "$D"

t_start "regression (iter1 F2): 'update inventory stocks report' (plural, Quinn repro) still requires erp-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"update inventory stocks report"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "erp-expert" "'inventory stocks' (plural 'stock') must still require erp-expert"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter1 F3 (HIGH, Chris/Quinn/Bella) -- iter0's AND-phrase semantics ("both words
# present anywhere in text") was too loose and reintroduced the exact false-positive
# shape this bd exists to close. route.sh now requires the phrase's words to appear as
# an ADJACENT run, in order. These two negative fixtures are Oliver's own reproductions
# -- neither must route to trading-expert any more.
t_start "regression (iter1 F3): 'let's fix this per our meeting protocol' does NOT require trading-expert (non-adjacent 'fix'...'protocol')"
D=$(sandbox)
echo "{\"capability\":\"production-code\",\"text\":\"let's fix this per our meeting protocol\"}" > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "non-adjacent 'fix'...'protocol' must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter1 F3): 'in order to speed up trading of assets' does NOT require trading-expert (non-adjacent 'order'/'trading', wrong order)"
D=$(sandbox)
echo '{"capability":"production-code","text":"in order to speed up trading of assets"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "non-adjacent/reordered 'order'...'trading' must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter2 D1 (HIGH, Chris) -- iter1 F3's ADJACENT-run check operated on the *filtered*
# token array, and scan() silently drops every non-alnum character including sentence-
# terminating punctuation, so two words either side of a full stop sat at adjacent array
# indices with nothing to tell that apart from true same-clause adjacency. One negative
# fixture per AND-phrase (6 phrases, 3 routes) -- the words are genuinely present in the
# text, in order, but split across a sentence/clause boundary, so none of these must
# match.
t_start "regression (iter2 D1): cross-sentence 'fix protocol' does NOT require trading-expert (Oliver/Chris repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"Please fix. Protocol docs are outdated."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'fix.' + 'Protocol' across a sentence boundary must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): cross-sentence 'trading order' does NOT require trading-expert (Chris repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"We do a lot of trading. Order form is attached separately."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trading.' + 'Order' across a sentence boundary must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): cross-sentence 'trading exchange' does NOT require trading-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"We handle a lot of trading. Exchange fees are listed separately."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trading.' + 'Exchange' across a sentence boundary must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): cross-sentence 'inventory stock' does NOT require erp-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"We manage the inventory. Stock levels are tracked separately."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *erp-expert*) t_fail "'inventory.' + 'Stock' across a sentence boundary must not route to erp-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): cross-sentence 'insurance policy' does NOT require insurance-expert"
D=$(sandbox)
echo '{"capability":"production-code","text":"Please check the insurance. Policy documents are attached separately."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *insurance-expert*) t_fail "'insurance.' + 'Policy' across a sentence boundary must not route to insurance-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): cross-sentence 'insurance claim' does NOT require insurance-expert (comma variant, Chris/Quinn repro shape)"
D=$(sandbox)
echo '{"capability":"production-code","text":"We handle the insurance, claim forms are attached separately in another paragraph."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *insurance-expert*) t_fail "'insurance,' + 'claim' across a comma clause boundary must not route to insurance-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D1): true-positive AND-phrases still fire when punctuation is present elsewhere in the sentence (sentinel does not over-block)"
D=$(sandbox)
echo '{"capability":"production-code","text":"Team, please submit the trading order now."}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a comma elsewhere in the sentence must not block an otherwise-adjacent phrase match"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter2 D2 (HIGH, Quinn) -- iter1 F2's plural-stem rule stripped a trailing 's' from any
# word of length > 3, so the real, unrelated English word "saps" (drains/exhausts)
# stemmed down to "sap" and collided with the 3-char keyword "sap". The length floor was
# raised to > 4; every when.any keyword in the registry was checked for the same
# collision shape (see 18-dave-L1-implement-iter2.md) -- "sap"/"saps" is the only
# confirmed real-word collision found ("kyc","mrp","btp","pms" are also 3-char keywords
# but none of "kycs"/"mrps"/"btps"/"pmss" collided with a distinct real word).
t_start "regression (iter2 D2): 'this refactor saps my energy' does NOT require sap-expert (Quinn repro -- 'saps' stemmed to 'sap')"
D=$(sandbox)
echo '{"capability":"production-code","text":"this refactor saps my energy"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *sap-expert*) t_fail "'saps' must not stem-match the unrelated keyword 'sap' -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter2 D2): the plural rule still works for the cases it was added for -- 'trading orders'/'insurance claims'/'inventory stocks' unaffected by the raised threshold"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading orders page"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "'trading orders' must still require trading-expert after the D2 threshold raise"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter2 D3 (HIGH, Quinn) -- iter1 F1's hyphen-preserving tokenizer fixed hyphenated
# single keywords (file-upload, ai-agent, external-integration) but, as a side effect,
# made a hyphenated spelling of a two-word PHRASE keyword permanently unmatchable: the
# text "trading-order" tokenized to ONE token "trading-order" that equals neither
# "trading" nor "order", so phrase_match could never fire. One positive fixture per
# AND-phrase (6 phrases, 3 routes), each written with a hyphen instead of a space --
# these are Quinn's own exact reproductions plus the delegation's named 'fix protocol'
# case. Both the hyphen and space spellings must resolve to the same required agent.
t_start "regression (iter2 D3): hyphenated 'FIX-protocol' text requires trading-expert (delegation repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"we rolled out FIX-protocol support"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "hyphenated 'FIX-protocol' must require trading-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated 'trading-order' text requires trading-expert (delegation repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading-order gateway"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "hyphenated 'trading-order' must require trading-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated 'trading-exchange' text requires trading-expert (Quinn repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"connect to the trading-exchange feed"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "hyphenated 'trading-exchange' must require trading-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated 'inventory-stock' text requires erp-expert (Quinn repro, delegation repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"check inventory-stock levels"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "erp-expert" "hyphenated 'inventory-stock' must require erp-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated 'insurance-policy' text requires insurance-expert (delegation repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"insurance-policy renewal"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "hyphenated 'insurance-policy' must require insurance-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated 'insurance-claim' text requires insurance-expert (Quinn repro)"
D=$(sandbox)
echo '{"capability":"production-code","text":"process the insurance-claim form"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "insurance-expert" "hyphenated 'insurance-claim' must require insurance-expert same as the space form"
rm -rf "$D"

t_start "regression (iter2 D3): hyphenated single KEYWORD matching is NOT regressed by the phrase-tokens split (F1 still green under D3's fix)"
D=$(sandbox)
echo '{"capability":"production-code","text":"add a new external-integration webhook for file-upload with an ai-agent callback"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "security-engineer" "F1's hyphenated single-keyword combined repro must still require security-engineer"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter3 (HIGH x2, Quinn iter2 re-review Findings C + D) -- iter2 D1's sentinel list
# ([.!?,;\n]) both over-applied (a bare newline mid-phrase was treated as an
# unconditional hard clause break, Finding C -- a genuine soft line-wrap false
# negative) and under-applied (colon and em-dash were never in the list, Finding D --
# a false positive, same class/blast-radius as the original D1 bug). Fixed by replacing
# the blacklist with a positive rule. iter3b (bd: shode-house-5cs.2, Oliver-measured
# regression against the user's own authoritative spec, which iter3's brief predated):
# iter3's positive rule required EXACTLY ONE separator CHARACTER, which wrongly rejected
# an ordinary whitespace RUN of 2+ (double space after a period, wrapped/indented text,
# aligned columns) as if it were a multi-character punctuation break. Corrected: two
# phrase words are adjacent iff the gap is EITHER a run of one-or-more WHITESPACE
# characters (any length, any mix of space/tab/newline) OR exactly one ASCII hyphen with
# no whitespace beside it (see route.sh's $items/phrase_match comment for the full
# mechanism). These are Oliver's three reproductions plus the delegation-required
# two-space/three-space/mixed-whitespace-run fixtures.
t_start "regression (iter3 Finding C): mid-phrase line-wrap DOES require trading-expert (Oliver repro -- iter2 D1 wrongly treated a soft wrap as a hard sentence break)"
D=$(sandbox)
jq -n '{capability:"production-code", text:"process the trading\norder now"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a mid-phrase newline (soft line-wrap) must still require trading-expert"
rm -rf "$D"

t_start "regression (iter3 Finding C): mid-phrase TAB-separated phrase DOES require trading-expert (delegation-required fixture)"
D=$(sandbox)
jq -n '{capability:"production-code", text:"process the trading\torder now"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a single tab between phrase words must still require trading-expert"
rm -rf "$D"

t_start "regression (iter3 Finding D): em-dash-separated clause does NOT require trading-expert (Oliver/Quinn repro -- iter2 D1's blacklist never covered '--')"
D=$(sandbox)
echo '{"capability":"production-code","text":"we are done trading -- order the coffee for the retro"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trading -- order' (em-dash clause break) must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter3 Finding D): colon-separated clause does NOT require trading-expert (Quinn repro shape -- iter2 D1's blacklist never covered ':')"
D=$(sandbox)
echo '{"capability":"production-code","text":"Meeting notes -- trading: order of business is confirmed"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trading: order' (colon clause break) must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter3): single-space phrase still requires trading-expert (baseline -- the positive rule must not over-block the common case)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading order flow"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a plain single-space 'trading order' must still require trading-expert"
rm -rf "$D"

t_start "regression (iter3b, corrects iter3's own regression): TWO-space separation DOES require trading-expert (Oliver repro -- iter3 wrongly rejected a plain double-space run)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading  order flow"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a double-space 'trading  order' (a whitespace RUN, not a punctuation break) must require trading-expert"
rm -rf "$D"

t_start "regression (iter3b): THREE-space separation DOES require trading-expert (Oliver repro -- aligned-column / wrapped-and-indented prose)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading   order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a triple-space 'trading   order' must require trading-expert same as any other whitespace run"
rm -rf "$D"

t_start "regression (iter3b, delegation-required): MIXED space+tab whitespace run DOES require trading-expert"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading \torder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a space+tab whitespace run is still whitespace-only -- must require trading-expert"
rm -rf "$D"

t_start "regression (iter3b, delegation-required): MIXED space+newline whitespace run DOES require trading-expert"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading \norder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a space+newline whitespace run is still whitespace-only -- must require trading-expert"
rm -rf "$D"

t_start "regression (iter3b): hyphen WITH adjacent whitespace does NOT require trading-expert ('trading - order' is neither a pure whitespace run nor a bare hyphen)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading - order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
case "$req" in *trading-expert*) t_fail "'trading - order' (hyphen with whitespace on both sides) must not route to trading-expert -- got $req" ;; *) t_ok ;; esac
rm -rf "$D"

t_start "regression (iter3b): bare hyphenated 'trading-order' spelling still requires trading-expert (D3 baseline not regressed by the iter3b rewrite)"
D=$(sandbox)
echo '{"capability":"production-code","text":"trading-order flow"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a single ASCII hyphen with no whitespace beside it must still require trading-expert"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter3c (bd: shode-house-5cs.2, Chris+Quinn iter3b re-review, both axes independently) --
# iter3b's own "whitespace" half of the positive rule was STILL an enumerated list of
# exactly three characters ("[ \t\n]", space/tab/LF), so CR, VT, FF, and every non-ASCII
# whitespace codepoint fell through to the single-char "." alternative and broke adjacency
# -- same enumeration-completeness failure this bd has hit in every prior iteration (iter1
# missing colon, iter2 missing CR/VT/FF in the D1 blacklist, iter3 "exactly one character"
# rejecting a bare 2+ run), just relocated to a new spot each time. Fixed by matching a
# whitespace character CLASS ("[[:space:]]", Oniguruma POSIX class) instead of a list, so a
# whitespace character nobody has thought to name is still classified correctly by
# construction. This is a full walk of the whitespace family Oliver's ruling put in scope
# (POSIX/ASCII control whitespace plus the Unicode `White_Space` property) -- every member
# below MUST join two phrase words exactly like a plain ASCII space does; this is the test
# that stops the class from silently shrinking back to a list in a future iteration.
t_start "iter3c whitespace-family: bare CR (\\r) joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading\rorder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "bare CR between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: CRLF (\\r\\n, Windows line ending) joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading\r\norder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "CRLF between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: CRLF blank-line paragraph break (\\r\\n\\r\\n) joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading\r\n\r\norder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "a CRLF blank-line break between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: vertical tab (\\u000b) joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"tradingorder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "vertical tab between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: form feed (\\u000c) joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"tradingorder"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "form feed between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: NBSP (\\u00a0, common copy-paste-from-web artifact) joins two phrase words (Oliver ruling: Unicode whitespace counts)"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "NBSP between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: ideographic space (\\u3000, arrives with CJK text) joins two phrase words (Oliver ruling: Unicode whitespace counts)"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading　order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "ideographic space between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: Unicode line separator U+2028 joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "U+2028 line separator between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

t_start "iter3c whitespace-family: Unicode paragraph separator U+2029 joins two phrase words"
D=$(sandbox)
jq -n '{capability:"production-code", text:"trading order"}' > "$D/req.json"
req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required')
assert_contains "$req" "trading-expert" "U+2029 paragraph separator between two phrase words must require trading-expert -- got $req"
rm -rf "$D"

# ---------------------------------------------------------------------------
# iter1 F5 (structural guard, Chris's suggestion) -- the test above that DOES catch F1:
# every when.any keyword across routes.json, wrapped in a neutral carrier sentence,
# must resolve its route's required agent. This is dynamic (reads routes.json itself),
# so it automatically covers any future keyword too, not just the ones fixed today.
t_start "structural: EVERY when.any keyword in routes.json has at least one true-positive fixture (would have caught iter1 F1 directly)"
struct_fail=""
while IFS=$'\t' read -r route_id agent item; do
  [ -z "$item" ] && continue
  D=$(sandbox)
  jq -n --arg t "please handle this $item" '{capability:"production-code", text:$t}' > "$D/req.json"
  req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required // empty')
  case "$req" in
    *"$agent"*) : ;;
    *) struct_fail="${struct_fail}${struct_fail:+; }route=$route_id item='$item' agent=$agent got=$req" ;;
  esac
  rm -rf "$D"
done < <(jq -r '.routes[] | .id as $id | .require[0] as $agent | .when.any[]? | [$id, $agent, .] | @tsv' "$ROUTES")
[ -z "$struct_fail" ] && t_ok || t_fail "keyword(s) with no true-positive fixture: $struct_fail"

# ---------------------------------------------------------------------------
# iter2 D3 extension of F5 -- same dynamic sweep, but for every multi-word (space-
# containing) when.any item, ALSO try a hyphenated spelling of that phrase (spaces
# replaced with hyphens) in the carrier sentence and assert it still resolves to the
# route's required agent. This is what would have caught D3 directly (single-word items
# are skipped -- a hyphenated single keyword like "file-upload" already IS the item, no
# separate hyphenated variant to construct), and it automatically covers any future
# multi-word keyword too, not just today's six.
t_start "structural: EVERY multi-word when.any phrase in routes.json ALSO matches its hyphenated spelling (would have caught iter2 D3 directly)"
struct_fail=""
while IFS=$'\t' read -r route_id agent item; do
  [ -z "$item" ] && continue
  case "$item" in *" "*) : ;; *) continue ;; esac
  hyphenated=$(printf '%s' "$item" | tr ' ' '-')
  D=$(sandbox)
  jq -n --arg t "please handle this $hyphenated" '{capability:"production-code", text:$t}' > "$D/req.json"
  req=$(printf '%s' "$("$ROUTE" "$D/req.json" 2>&1)" | jq -c '.required // empty')
  case "$req" in
    *"$agent"*) : ;;
    *) struct_fail="${struct_fail}${struct_fail:+; }route=$route_id item='$item' hyphenated='$hyphenated' agent=$agent got=$req" ;;
  esac
  rm -rf "$D"
done < <(jq -r '.routes[] | .id as $id | .require[0] as $agent | .when.any[]? | [$id, $agent, .] | @tsv' "$ROUTES")
[ -z "$struct_fail" ] && t_ok || t_fail "hyphenated phrase spelling(s) with no true-positive fixture: $struct_fail"

# ---------------------------------------------------------------------------
# MUTATION (a): remove a route rule -> resolver must stop returning that agent
t_start "MUTATION (a): deleting the frontend route from routes.json makes the resolver stop requiring ux-ui-designer"
D=$(sandbox)
echo '{"capability":"production-code","frontend":true}' > "$D/req.json"
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
