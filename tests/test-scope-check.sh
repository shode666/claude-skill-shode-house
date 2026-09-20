#!/usr/bin/env bash
# tests/test-scope-check.sh -- bash-only test suite for Milestone E (bd: shode-roadmap/C-E1)
# scripts/scope-check.sh + references/scope/{manifest.schema.json,example.manifest.json}
#
# Extended for L2 enforcement integrity (bd: shode-house-5cs.4, iter 0): fail-closed
# unclaimed-path handling (exit 4 NEEDS_AMENDMENT vs exit 1 DENY, split on the requesting
# agent's own allowed_roots[]), atomic self-amend (--amend, owns-only, never
# allowed_roots), and the 7 bind-on-claim rules (--bind-record / --bind / --main-check).
# Reference schema/example files under references/scope/ are intentionally UNCHANGED by
# this bd (outside its declared Files boundary -- see outputs/shode-house-5cs/25-dave-L2-implement.md
# "Open questions") -- scope-check.sh never schema-validates against them at runtime
# (`jq empty` for syntax only), so this is a doc-drift gap, not a functional one.
#
# No framework dependency (same style as tests/test-workflow-state.sh + tests/test-registry.sh)
# -- plain bash test functions + a tiny assert library. Each test runs inside a
# mktemp -d sandbox via SCOPECHECK_ROOT so tests never touch the real repo state. Wired
# into ci.yml as exactly ONE step (CLAUDE.md rule: this milestone may add no more than 1
# CI step total; this bd extends the SAME step, no new ci.yml step needed).
#
# Usage: bash tests/test-scope-check.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/scope-check.sh"
SCHEMA="$REPO_ROOT/references/scope/manifest.schema.json"
EXAMPLE="$REPO_ROOT/references/scope/example.manifest.json"

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
assert_rc()    { if [ "$1" -eq "$2" ]; then t_ok; else t_fail "$3 -- exit code $1, want $2"; fi; }

sandbox() { local d; d=$(mktemp -d -t scopecheck-test.XXXXXX); printf '%s' "$d"; }

write_manifest() {
  # $1=root $2=bd-id-filename(already encoded) $3=heredoc content on stdin
  mkdir -p "$1/.shode-house/scope"
  cat > "$1/.shode-house/scope/$2.json"
}

# ---------------------------------------------------------------------------
t_start "schema + example: both are valid JSON, example validates against the schema's basic shape"
jq empty "$SCHEMA" >/dev/null 2>&1; assert_true "$?" "manifest.schema.json must parse as JSON"
jq empty "$EXAMPLE" >/dev/null 2>&1; assert_true "$?" "example.manifest.json must parse as JSON"
sv=$(jq -r '.schema_version' "$EXAMPLE"); assert_eq "$sv" "1" "example schema_version should be 1"
n_agents=$(jq '.agents | length' "$EXAMPLE"); [ "$n_agents" -gt 0 ] && t_ok || t_fail "example should declare at least one agent"
n_shared=$(jq '.shared_files | length' "$EXAMPLE"); [ "$n_shared" -gt 0 ] && t_ok || t_fail "example should declare shared_files (SS7.2)"
modes=$(jq -r '.shared_files[].mode' "$EXAMPLE" | sort -u | tr '\n' ',')
for m in exclusive append-only merge-owner generated; do
  case ",$modes" in *",$m,"*) t_ok ;; *) t_fail "example.manifest.json should demonstrate mode '$m' -- got: $modes" ;; esac
done
coupled=$(jq -r '.shared_files["ci.yml", ".github/workflows/ci.yml"]?.coupled_with[]? // empty' "$EXAMPLE" 2>/dev/null | grep -c golden.json)
[ "${coupled:-0}" -ge 1 ] && t_ok || t_fail "example should demonstrate coupled_with (ac632a3 incident: ci.yml <-> golden.json)"

# ---------------------------------------------------------------------------
t_start "engagement guard: no .shode-house/ -> exit 0, silent, no side effect (check/snapshot/verify)"
D=$(sandbox)
export SCOPECHECK_ROOT="$D"
out=$("$SCRIPT" eg-1 Dave#1 src/foo.py 2>&1); rc=$?
assert_true "$rc" "check should exit 0 with no .shode-house/"
assert_eq "$out" "" "check should print nothing"
out=$("$SCRIPT" eg-1 Dave#1 src/foo.py --snapshot 2>&1); rc=$?
assert_true "$rc" "snapshot should exit 0 with no .shode-house/"
assert_eq "$out" "" "snapshot should print nothing"
out=$("$SCRIPT" eg-1 Dave#1 src/foo.py --verify 2>&1); rc=$?
assert_true "$rc" "verify should exit 0 with no .shode-house/"
assert_eq "$out" "" "verify should print nothing"
[ -e "$D/.shode-house" ] && t_fail "engagement guard must never create .shode-house/ itself" || t_ok
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "usage errors: missing args -> exit 64 (distinct from ALLOW/DENY/NO_MANIFEST/CONFLICT)"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SCOPECHECK_ROOT="$D"
"$SCRIPT" >/dev/null 2>&1; assert_rc "$?" 64 "no args"
"$SCRIPT" bd-1 >/dev/null 2>&1; assert_rc "$?" 64 "only bd-id"
"$SCRIPT" bd-1 Dave#1 >/dev/null 2>&1; assert_rc "$?" 64 "missing path"
"$SCRIPT" bd-1 Dave#1 src/foo.py --bogus-flag >/dev/null 2>&1; assert_rc "$?" 64 "unknown flag"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "NO_MANIFEST: .shode-house/ exists but no manifest recorded for this bd -> exit 2, distinct from ALLOW"
D=$(sandbox); mkdir -p "$D/.shode-house"; export SCOPECHECK_ROOT="$D"
out=$("$SCRIPT" no-such-bd Dave#1 src/foo.py 2>&1); rc=$?
assert_rc "$rc" 2 "no manifest for this bd-id"
assert_contains "$out" "NO_MANIFEST" "message should say NO_MANIFEST"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "ownership (SS7.1): own path ALLOW, other agent's path DENY (bd: shode-house-5cs.4: unclaimed is no longer bare-permissive -- see the dedicated NEEDS_AMENDMENT/DENY section below)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-1" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-1",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/orders/**"], "owns": ["src/orders/**"]},
    {"agent": "Dave#2", "allowed_roots": ["src/payments/**"], "owns": ["src/payments/**"]}
  ]
}
EOF
out=$("$SCRIPT" bd-1 Dave#1 src/orders/handler.py 2>&1); rc=$?
assert_rc "$rc" 0 "own path should ALLOW"
assert_contains "$out" "ALLOW" "own-path message should say ALLOW"

out=$("$SCRIPT" bd-1 Dave#1 src/payments/handler.py 2>&1); rc=$?
assert_rc "$rc" 1 "another agent's owned path should DENY"
assert_contains "$out" "DENY" "cross-owner message should say DENY"
assert_contains "$out" "Dave#2" "DENY message should name the real owner"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "C1 (bd: shode-house-5cs.4 iter 2, Chris): path canonicalization -- traversal/dot-slash/case all resolve to the SAME physical path as the plain form, both for ALLOW (self) and DENY (cross-owner)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-canon" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-canon",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/orders/**"], "owns": ["src/orders/handler.py"]},
    {"agent": "Dave#2", "allowed_roots": ["src/payments/**"], "owns": ["src/payments/handler.py"]}
  ]
}
EOF
mkdir -p "$D/src/orders" "$D/src/payments"
out=$("$SCRIPT" bd-canon Dave#1 '.shode-house/../src/orders/handler.py' 2>&1); rc=$?
assert_rc "$rc" 0 "traversal-obfuscated own path still ALLOWs (physically identical to src/orders/handler.py)"
out=$("$SCRIPT" bd-canon Dave#1 'src/./orders/handler.py' 2>&1); rc=$?
assert_rc "$rc" 0 "dot-slash-obfuscated own path still ALLOWs"
out=$("$SCRIPT" bd-canon Dave#1 'SRC/ORDERS/handler.py' 2>&1); rc=$?
assert_rc "$rc" 0 "case-obfuscated own path still ALLOWs"

out=$("$SCRIPT" bd-canon Dave#1 '.shode-house/../src/payments/handler.py' 2>&1); rc=$?
assert_rc "$rc" 1 "traversal-obfuscated CROSS-owner path still DENYs (Dave#2's file, not Dave#1's)"
assert_contains "$out" "Dave#2" "traversal-obfuscated DENY still names the real owner"
out=$("$SCRIPT" bd-canon Dave#1 'src/./payments/handler.py' 2>&1); rc=$?
assert_rc "$rc" 1 "dot-slash-obfuscated CROSS-owner path still DENYs"
out=$("$SCRIPT" bd-canon Dave#1 'SRC/PAYMENTS/handler.py' 2>&1); rc=$?
assert_rc "$rc" 1 "case-obfuscated CROSS-owner path still DENYs"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "L2 (bd: shode-house-5cs.4) Part 1: unclaimed path split -- NEEDS_AMENDMENT (exit 4) inside allowed_roots, DENY (exit 1) outside"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-8" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-8",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**", "tests/payment/**"], "owns": ["src/payment/refund.ts"]},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**"], "owns": []}
  ]
}
EOF
out=$("$SCRIPT" bd-8 Dave#1 src/payment/create.ts 2>&1); rc=$?
assert_rc "$rc" 4 "unclaimed path inside own allowed_roots -> exit 4 NEEDS_AMENDMENT"
assert_contains "$out" "NEEDS_AMENDMENT" "message should say NEEDS_AMENDMENT"
assert_contains "$out" "scope-check.sh bd-8 Dave#1 src/payment/create.ts --amend" "NEEDS_AMENDMENT message must carry the EXACT amend command to run"

out=$("$SCRIPT" bd-8 Dave#1 README.md 2>&1); rc=$?
assert_rc "$rc" 1 "unclaimed path outside own allowed_roots -> exit 1 DENY, never self-amend"
assert_contains "$out" "DENY" "outside-roots message should say DENY"
assert_contains "$out" "never self-amend" "outside-roots DENY should explicitly say never self-amend"

out=$("$SCRIPT" bd-8 Dave#1 src/orders/handler.py 2>&1); rc=$?
assert_rc "$rc" 1 "unclaimed path inside a DIFFERENT agent's allowed_roots (not the caller's own) -> DENY, not NEEDS_AMENDMENT"

out=$("$SCRIPT" bd-8 UnknownAgent src/payment/x.ts 2>&1); rc=$?
assert_rc "$rc" 1 "agent not even registered in the manifest -> DENY (empty allowed_roots by construction), fail-closed"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "L2 Part 1: --amend end to end -- eligible amends, re-check ALLOWs, owns-only (never allowed_roots), TOCTOU-safe, ineligible amends DENY"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-9" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-9",
  "agents": [{"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": []}]
}
EOF
out=$("$SCRIPT" bd-9 Dave#1 src/payment/create.ts --amend 2>&1); rc=$?
assert_rc "$rc" 0 "eligible amend should succeed"
assert_contains "$out" "ALLOW" "amend success message should say ALLOW"

out=$("$SCRIPT" bd-9 Dave#1 src/payment/create.ts 2>&1); rc=$?
assert_rc "$rc" 0 "re-check after amend must now ALLOW"

roots_after=$(jq -c '.agents[0].allowed_roots' "$D/.shode-house/scope/bd-9.json")
assert_eq "$roots_after" '["src/payment/**"]' "amend must NEVER add to allowed_roots (self-amend != self-expand)"
owns_after=$(jq -c '.agents[0].owns' "$D/.shode-house/scope/bd-9.json")
assert_eq "$owns_after" '["src/payment/create.ts"]' "amend must add the exact path to owns[]"

out=$("$SCRIPT" bd-9 Dave#1 src/payment/create.ts --amend 2>&1); rc=$?
assert_rc "$rc" 0 "re-amending an already-owned path is a harmless no-op, not an error"
assert_contains "$out" "nothing to amend" "re-amend of an already-owned path should say nothing to amend"

out=$("$SCRIPT" bd-9 Dave#1 README.md --amend 2>&1); rc=$?
assert_rc "$rc" 1 "amend outside allowed_roots must DENY, never self-amend outside the plan-approved boundary"

# TOCTOU close: two agents racing to amend the SAME unclaimed-but-eligible path must not
# both succeed -- the second one must see it already claimed (re-evaluated under the lock,
# not just at the pre-check that ran before acquiring it).
write_manifest "$D" "bd-10" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-10",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/shared/**"], "owns": []},
    {"agent": "Dave#2", "allowed_roots": ["src/shared/**"], "owns": []}
  ]
}
EOF
"$SCRIPT" bd-10 Dave#2 src/shared/race.ts --amend >/dev/null 2>&1
out=$("$SCRIPT" bd-10 Dave#1 src/shared/race.ts --amend 2>&1); rc=$?
assert_rc "$rc" 1 "amend must fail once someone else already claimed the exact same path (checked again under the lock, not just at pre-check time)"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "M2 (bd: shode-house-5cs.4 iter 2, Quinn): --amend rejects a literal glob path outright -- owns[] must only ever hold concrete files, never a pattern that would collapse per-file self-amend into a root-wide grant"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-m2" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-m2",
  "agents": [{"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": ["src/payment/refund.ts"]}]
}
EOF
out=$("$SCRIPT" bd-m2 Dave#1 'src/payment/**' --amend 2>&1); rc=$?
assert_rc "$rc" 1 "literal glob path (same text as the agent's own allowed_roots pattern) -- amend must DENY, not silently accept"
assert_contains "$out" "glob metacharacter" "DENY message names the reason"
owns_after=$(jq -c '.agents[0].owns' "$D/.shode-house/scope/bd-m2.json")
assert_eq "$owns_after" '["src/payment/refund.ts"]' "owns[] must be UNCHANGED -- the crafted glob must never be persisted"

for bad in 'src/payment/*.ts' 'src/payment/file?.ts' 'src/payment/[ab].ts'; do
  out=$("$SCRIPT" bd-m2 Dave#1 "$bad" --amend 2>&1); rc=$?
  assert_rc "$rc" 1 "amend of '$bad' (contains a glob metachar) must DENY"
done

out=$("$SCRIPT" bd-m2 Dave#1 'src/payment/create.ts' --amend 2>&1); rc=$?
assert_rc "$rc" 0 "sanity: an ordinary concrete path (no glob metachars) still amends normally"
rm -rf "$D"

# ---------------------------------------------------------------------------
# CONCURRENT --amend on DIFFERENT paths -- bd:shode-house-vz8, reproducing the exact
# shape Quinn originally measured against scope-check.sh's OLD lock (a plain `rm -rf`
# reap on the canonical path the instant it observed the holder's cached pid looked
# dead -- see scripts/lib/lock.sh's header): 40 concurrent --amend calls on 40 DIFFERENT
# unclaimed-but-eligible paths, every caller receiving ALLOW/exit 0, but only 33/36/37
# writes (i.e. 4, 7, or 3 lost) actually persisted in owns[] -- because two callers
# could simultaneously believe they held the manifest lock and clobber each other's
# read-modify-write. The invariant that must hold now, exactly, every run:
# count(callers that exited 0) == count(paths actually present in owns[]).
t_start "CONCURRENCY: N=40 concurrent --amend calls on 40 DIFFERENT unclaimed-but-eligible paths, same bd -- count(rc=0) MUST equal count(paths persisted in owns[]), exactly (bd:shode-house-vz8 -- Quinn originally measured 4, 7, and 3 of 40 writes lost here, every caller still returning ALLOW/exit 0)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"; mkdir -p "$D/tmp-out"
write_manifest "$D" "bd-stress-amend" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-stress-amend",
  "agents": [{"agent": "Dave#1", "allowed_roots": ["src/stress/**"], "owns": []}]
}
EOF
for i in $(seq 1 40); do
  ( "$SCRIPT" bd-stress-amend Dave#1 "src/stress/file-$i.ts" --amend >/dev/null 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
rc0_count=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
mf="$D/.shode-house/scope/bd-stress-amend.json"
jq empty "$mf" >/dev/null 2>&1; assert_true "$?" "manifest must still be valid JSON after 40 concurrent amends"
persisted_count=$(jq -r '.agents[0].owns | length' "$mf" 2>/dev/null)
assert_eq "$rc0_count" "$persisted_count" "count(rc=0 amends) must equal count(paths persisted in owns[]) -- got rc0=$rc0_count persisted=$persisted_count"
# every persisted path must be UNIQUE (jq `unique` in cmd_amend's write means a lost-then-
# reapplied duplicate would silently under-count above without this -- belt and suspenders).
unique_count=$(jq -r '.agents[0].owns | unique | length' "$mf" 2>/dev/null)
assert_eq "$persisted_count" "$unique_count" "owns[] must never contain a duplicate path (jq 'unique' in cmd_amend, plus this proves no torn/duplicated write slipped through)"
printf '   (informational, not asserted) rc0=%s persisted=%s / 40 attempted\n' "$rc0_count" "$persisted_count"
rm -rf "$D"

# ---------------------------------------------------------------------------
# bd:shode-house-5cs.8 (W1) -- --snapshot performed the SAME read-modify-write
# (.base_sha[agent][path]) with NO lock at all until this bd. Same reproduction shape as
# --amend's own concurrency test just above (40 concurrent calls on 40 DIFFERENT paths,
# same bd, same agent), now for --snapshot instead.
t_start "CONCURRENCY (bd:shode-house-5cs.8, W1): N=40 concurrent --snapshot calls on 40 DIFFERENT paths, same bd/agent -- count(rc=0) MUST equal count(paths persisted in base_sha[agent]), exactly"
D=$(sandbox); export SCOPECHECK_ROOT="$D"; mkdir -p "$D/tmp-out" "$D/src/stress"
write_manifest "$D" "bd-stress-snapshot" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-stress-snapshot",
  "agents": [{"agent": "Dave#1", "allowed_roots": [], "owns": []}]
}
EOF
for i in $(seq 1 40); do
  printf 'content-%s' "$i" > "$D/src/stress/file-$i.ts"
done
for i in $(seq 1 40); do
  ( "$SCRIPT" bd-stress-snapshot Dave#1 "src/stress/file-$i.ts" --snapshot >/dev/null 2>&1; echo $? > "$D/tmp-out/rc-$i" ) &
done
wait
rc0_count=$(cat "$D"/tmp-out/rc-* | grep -c '^0$')
mf="$D/.shode-house/scope/bd-stress-snapshot.json"
jq empty "$mf" >/dev/null 2>&1; assert_true "$?" "manifest must still be valid JSON after 40 concurrent snapshots"
persisted_count=$(jq -r '.base_sha["Dave#1"] // {} | length' "$mf" 2>/dev/null)
assert_eq "$rc0_count" "$persisted_count" "count(rc=0 snapshots) must equal count(paths persisted in base_sha[Dave#1]) -- got rc0=$rc0_count persisted=$persisted_count"
printf '   (informational, not asserted) rc0=%s persisted=%s / 40 attempted\n' "$rc0_count" "$persisted_count"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "W1 (bd:shode-house-5cs.8): --verify stays lock-free and still correct -- a manually-held lock directory for this bd must NOT block or slow down --verify (it performs an atomic, validated READ only, and NEVER calls lock_acquire)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-verify-lockfree" <<'EOF'
{"schema_version": 1, "bd_id": "bd-verify-lockfree", "agents": [{"agent": "Dave#1", "allowed_roots": [], "owns": []}]}
EOF
echo "v1" > "$D/ci.yml"
"$SCRIPT" bd-verify-lockfree Dave#1 ci.yml --snapshot >/dev/null 2>&1
lockd="$D/.shode-house/scope/.lock-bd-verify-lockfree"
mkdir -p "$lockd"   # simulate a lock held by some OTHER writer (--amend/--bind-record/--snapshot)
t0=$(date +%s%N)
out=$("$SCRIPT" bd-verify-lockfree Dave#1 ci.yml --verify 2>&1); rc=$?
t1=$(date +%s%N)
elapsed_ms=$(( (t1 - t0) / 1000000 ))
assert_rc "$rc" 0 "verify must succeed even while another writer holds the lock"
assert_contains "$out" "ALLOW" "verify must still report the correct, real verdict (no drift since snapshot)"
[ "$elapsed_ms" -lt 500 ] && t_ok || t_fail "verify took ${elapsed_ms}ms while a lock was held -- it must never attempt lock_acquire's own ~2s wait budget (this is the behavioral proof it stayed lock-free)"
rm -rf "$D"

# ---------------------------------------------------------------------------
# bd:shode-house-5cs.8 (W2) -- scope-check.sh's own RMW commands used to call
# `lock_acquire` directly and die() on ANY non-zero rc with one generic message, no
# retry at all. Now, via scopecheck_acquire_lock, they follow the SAME shape
# scripts/side-effect.sh's sideeffect_acquire_lock / scripts/workflow-state.sh's
# wfstate_acquire_lock already use: LOCK_BUSY(1)/RECOVERY_IN_PROGRESS(2) retry, bounded,
# with jitter; everything else is an immediate, non-retried stop. "Never non-zero ==
# retryable" is asserted directly by W2c/W2d below (RECOVERY_REQUIRED/LOCK_CORRUPT).
echo
echo "-- W2 (bd:shode-house-5cs.8): scope-check.sh adopts lock.sh's LOCK_BUSY/RECOVERY_IN_PROGRESS (retry) vs LOCK_LIVE/LOCK_CORRUPT/RECOVERY_REQUIRED/RECOVERY_FAILED (stop) result vocabulary --"

t_start "W2a LOCK_BUSY: bounded retry actually helps -- a transient holder that clears mid-retry lets --amend SUCCEED on a later attempt, not merely fail loud (never 'wait once, give up')"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-busy" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-busy", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/w2/**"], "owns": []}]}
EOF
lockd="$D/.shode-house/scope/.lock-bd-w2-busy"
mkdir -p "$lockd"   # empty lock dir, no pid/token yet -- classifies UNKNOWN -> LOCK_BUSY at timeout, same as ordinary mid-populate contention
( sleep 2.5; rm -rf "$lockd" ) &
releaser=$!
t0=$(date +%s)
out=$("$SCRIPT" bd-w2-busy Dave#1 src/w2/create.ts --amend 2>&1); rc=$?
t1=$(date +%s)
wait "$releaser" 2>/dev/null
elapsed=$((t1 - t0))
assert_rc "$rc" 0 "amend must SUCCEED once bounded retry crosses the point where the transient holder cleared"
[ "$elapsed" -ge 2 ] && [ "$elapsed" -le 8 ] && t_ok || t_fail "expected the retry to cross past the ~2.5s release point within the bounded attempt budget, got ${elapsed}s"
rm -rf "$D"

t_start "W2b LOCK_BUSY exhausted: a holder that NEVER clears makes --amend fail loud after bounded retry (not forever), manifest byte-identical, exit 64 (scope-check.sh's own usage/dependency-error code, never confused with a 0/1/2/3/4 verdict)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-busy2" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-busy2", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/w2/**"], "owns": []}]}
EOF
lockd="$D/.shode-house/scope/.lock-bd-w2-busy2"
mkdir -p "$lockd"
before_sha=$(shasum "$D/.shode-house/scope/bd-w2-busy2.json")
t0=$(date +%s)
out=$("$SCRIPT" bd-w2-busy2 Dave#1 src/w2/create.ts --amend 2>&1); rc=$?
t1=$(date +%s)
elapsed=$((t1 - t0))
assert_rc "$rc" 64 "exhausted LOCK_BUSY retry must exit 64"
assert_contains "$out" "LOCK_BUSY" "message must name the machine-readable class"
[ "$elapsed" -le 10 ] && t_ok || t_fail "bounded retry must not wait forever -- got ${elapsed}s"
after_sha=$(shasum "$D/.shode-house/scope/bd-w2-busy2.json")
assert_eq "$after_sha" "$before_sha" "manifest must be byte-identical -- an exhausted lock attempt must never touch it"
rm -rf "$lockd"
rm -rf "$D"

t_start "W2c RECOVERY_REQUIRED (dead-pid holder) is NEVER retried -- --amend fails after a SINGLE lock_acquire timeout (~2s), not the doubled budget LOCK_BUSY gets above"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-dead" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-dead", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/w2/**"], "owns": []}]}
EOF
( : ) & dead_pid=$!
wait "$dead_pid" 2>/dev/null
lockd="$D/.shode-house/scope/.lock-bd-w2-dead"
mkdir -p "$lockd"
printf 'dead-holder-token' > "$lockd/token"
printf '%s' "$dead_pid" > "$lockd/pid"
date +%s > "$lockd/ts"
t0=$(date +%s)
out=$("$SCRIPT" bd-w2-dead Dave#1 src/w2/create.ts --amend 2>&1); rc=$?
t1=$(date +%s)
elapsed=$((t1 - t0))
assert_rc "$rc" 64 "dead-pid-held lock (RECOVERY_REQUIRED) must fail, exit 64"
assert_contains "$out" "RECOVERY_REQUIRED" "message must name the class"
[ "$elapsed" -ge 1 ] && [ "$elapsed" -le 5 ] && t_ok || t_fail "must be roughly ONE lock_acquire timeout (~2s), never retried, never near-instant -- got ${elapsed}s"
rm -rf "$D"

t_start "W2d LOCK_CORRUPT (chmod 000, stable & unreadable) is NEVER retried -- --amend fails after a single classification, exit 64, near-instant relative to LOCK_BUSY's doubled budget"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-corrupt" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-corrupt", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/w2/**"], "owns": []}]}
EOF
lockd="$D/.shode-house/scope/.lock-bd-w2-corrupt"
mkdir -p "$lockd"
printf 'x' > "$lockd/pid"
chmod 000 "$lockd"
t0=$(date +%s)
out=$("$SCRIPT" bd-w2-corrupt Dave#1 src/w2/create.ts --amend 2>&1); rc=$?
t1=$(date +%s)
elapsed=$((t1 - t0))
chmod 700 "$lockd"
assert_rc "$rc" 64 "LOCK_CORRUPT must fail, exit 64"
assert_contains "$out" "LOCK_CORRUPT" "message must name the class"
[ "$elapsed" -le 5 ] && t_ok || t_fail "LOCK_CORRUPT must be near-instant, never retried -- got ${elapsed}s"
rm -rf "$D"

t_start "W2e --snapshot also adopts the retry vocabulary (not just --amend): LOCK_BUSY exhausted -> exit 64, base_sha untouched"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-snap-busy" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-snap-busy", "agents": [{"agent": "Dave#1", "allowed_roots": [], "owns": []}]}
EOF
echo "v1" > "$D/f.txt"
lockd="$D/.shode-house/scope/.lock-bd-w2-snap-busy"
mkdir -p "$lockd"
before_sha=$(shasum "$D/.shode-house/scope/bd-w2-snap-busy.json")
out=$("$SCRIPT" bd-w2-snap-busy Dave#1 f.txt --snapshot 2>&1); rc=$?
assert_rc "$rc" 64 "exhausted LOCK_BUSY retry on --snapshot must exit 64, same convention as --amend"
assert_contains "$out" "LOCK_BUSY" "message must name the class"
after_sha=$(shasum "$D/.shode-house/scope/bd-w2-snap-busy.json")
assert_eq "$after_sha" "$before_sha" "manifest (incl. base_sha) must be byte-identical -- an exhausted --snapshot lock attempt must never touch it"
rm -rf "$D"

t_start "W2f --bind-record also adopts the retry vocabulary: LOCK_BUSY exhausted -> exit 64, bindings untouched"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-w2-bind-busy" <<'EOF'
{"schema_version": 1, "bd_id": "bd-w2-bind-busy", "agents": [{"agent": "Dave#1", "allowed_roots": [], "owns": []}]}
EOF
lockd="$D/.shode-house/scope/.lock-bd-w2-bind-busy"
mkdir -p "$lockd"
before_sha=$(shasum "$D/.shode-house/scope/bd-w2-bind-busy.json")
out=$("$SCRIPT" bd-w2-bind-busy inst-1 tester Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 64 "exhausted LOCK_BUSY retry on --bind-record must exit 64, same convention as --amend/--snapshot"
assert_contains "$out" "LOCK_BUSY" "message must name the class"
after_sha=$(shasum "$D/.shode-house/scope/bd-w2-bind-busy.json")
assert_eq "$after_sha" "$before_sha" "manifest (incl. bindings) must be byte-identical -- an exhausted --bind-record lock attempt must never touch it"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "L2 Part 2 (bd: shode-house-5cs.4 iter 1, C1): the 7 bind-on-claim rules under the platform-neutral record shape -- --bind-record <bd> <instance-id> <role> <label> <platform>"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-11" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-11",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": []},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**"], "owns": []}
  ]
}
EOF
out=$("$SCRIPT" no-such-bd agentid-AAA developer Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 1 "rule: unknown bd -> DENY"
assert_contains "$out" "unknown bd" "unknown-bd message should say so"

out=$("$SCRIPT" bd-11 agentid-AAA developer Ghost claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 1 "rule: unknown label -> DENY"
assert_contains "$out" "unknown label" "unknown-label message should say so"

out=$("$SCRIPT" bd-11 agentid-AAA developer Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 0 "rule: first-bind-wins -> ALLOW"
assert_contains "$out" "ALLOW" "first-bind message should say ALLOW"

out=$("$SCRIPT" bd-11 agentid-AAA developer Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 0 "rule: same instance_id -> same label -> idempotent ALLOW"
assert_contains "$out" "idempotent" "idempotent re-bind message should say so"

out=$("$SCRIPT" bd-11 agentid-AAA developer Dave#2 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 1 "rule: same instance_id -> a DIFFERENT label -> DENY"

out=$("$SCRIPT" bd-11 agentid-BBB developer Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 1 "rule: a DIFFERENT instance_id -> an already-bound label -> DENY"
assert_contains "$out" "already bound to a different instance_id" "cross-instance rebind DENY should say so"

out=$("$SCRIPT" bd-11 agentid-BBB developer Dave#2 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 0 "rule: instance label unique per bd -- a DIFFERENT, still-unbound label binds independently -> ALLOW"

bindings=$(jq -c '.bindings' "$D/.shode-house/scope/bd-11.json")
assert_eq "$bindings" '{"agentid-AAA":{"platform":"claude","role":"developer","label":"Dave#1"},"agentid-BBB":{"platform":"claude","role":"developer","label":"Dave#2"}}' \
  "final bindings map should reflect exactly the two successful binds, each carrying platform+role+label"

t_start "L2 Part 2 usage: the 5-arg --bind-record shape rejects a stray 4-arg (pre-C1) invocation as a usage error, never silently reinterpreted"
out=$("$SCRIPT" bd-11 agentid-CCC Dave#1 --bind-record 2>&1); rc=$?
assert_rc "$rc" 64 "old 4-arg shape (bd, instance-id, label, flag) is no longer a recognised invocation -- usage error, not a bind"

t_start "bd: shode-house-5cs.4 iter 2 (Bella): --resolve-binding -- BOUND/NOT_BOUND/NO_MANIFEST, routed through the SAME shape guard bind-record uses (the adapter must never reimplement this lookup itself)"
out=$("$SCRIPT" bd-11 agentid-AAA --resolve-binding 2>&1); rc=$?
assert_rc "$rc" 0 "bound instance_id -> exit 0"
assert_eq "$out" "BOUND: Dave#1" "resolve-binding prints the exact bound label"

out=$("$SCRIPT" bd-11 agentid-CCC --resolve-binding 2>&1); rc=$?
assert_rc "$rc" 1 "unbound instance_id, well-shaped manifest -> exit 1 NOT_BOUND, distinct from ALLOW/DENY/64"
assert_contains "$out" "NOT_BOUND" "message says NOT_BOUND"

out=$("$SCRIPT" no-such-bd agentid-AAA --resolve-binding 2>&1); rc=$?
assert_rc "$rc" 2 "unknown bd -> exit 2 NO_MANIFEST"
assert_contains "$out" "NO_MANIFEST" "message says NO_MANIFEST"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "L2 Part 2: --bind (agent-facing 3-arg shape) is deliberately inert -- always exit 0, never writes bindings"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-12" <<'EOF'
{"schema_version": 1, "bd_id": "bd-12", "agents": [{"agent": "Dave#1", "allowed_roots": [], "owns": []}]}
EOF
out=$("$SCRIPT" bd-12 Dave#1 --bind 2>&1); rc=$?
assert_rc "$rc" 0 "direct --bind (no instance_id available) always exits 0"
bindings_before=$(jq -c '.bindings // {}' "$D/.shode-house/scope/bd-12.json")
assert_eq "$bindings_before" '{}' "direct --bind must never itself write a binding (it has no instance_id to act on)"

out=$("$SCRIPT" no-manifest-bd x --bind 2>&1); rc=$?
assert_rc "$rc" 2 "direct --bind against an unknown bd -> NO_MANIFEST (2), distinct from the DENY/ALLOW verdicts --bind-record uses"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "C1 migration: a manifest whose bindings map is still the pre-C1 flat shape ({instance_id: label}) is CLEANLY REJECTED (exit 64), never silently misread"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-old" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-old",
  "agents": [{"agent": "Dave#1", "allowed_roots": ["src/legacy/**"], "owns": ["src/legacy/x.ts"]}],
  "bindings": {"agentid-ZZZ": "Dave#1"}
}
EOF
out=$("$SCRIPT" bd-old agentid-YYY developer Dave#1 claude --bind-record 2>&1); rc=$?
assert_rc "$rc" 64 "--bind-record against an old-shape manifest -> usage/dep error (64), not a silent write"
assert_contains "$out" "pre-C1 flat shape" "old-shape rejection message names the problem"
assert_contains "$out" "platform-neutral record shape" "old-shape rejection message tells the operator what shape is expected"

out=$("$SCRIPT" bd-old Dave#1 --bind 2>&1); rc=$?
assert_rc "$rc" 64 "direct --bind (read-only probe) against an old-shape manifest also cleanly rejects, never silently reports a stale/misread status"

out=$("$SCRIPT" bd-old agentid-ZZZ --resolve-binding 2>&1); rc=$?
assert_rc "$rc" 64 "--resolve-binding against an old-shape manifest also cleanly rejects (same shape guard as --bind/--bind-record), never silently misreads a bare-string value as a bound label"
assert_contains "$out" "pre-C1 flat shape" "resolve-binding old-shape rejection names the problem, same message bindings_shape_ok_or_die always gives"

# ownership checks that never touch bindings at all are UNAFFECTED by the old shape --
# this is the same manifest, same agent, same request as the very first ownership test in
# this suite (own path -> ALLOW).
out=$("$SCRIPT" bd-old Dave#1 src/legacy/x.ts 2>&1); rc=$?
assert_rc "$rc" 0 "cmd_check never touches bindings -- an old-shape manifest's ownership data is fully readable regardless"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "C1 invariant: scripts/scope-check.sh (the core) never names a platform -- naming a platform is the adapter's job"
platform_hits=$(grep -inE 'claude|codex|antigravity' "$SCRIPT" || true)
[ -z "$platform_hits" ] && t_ok || t_fail "scope-check.sh must contain zero platform-name literals (grep hit: $platform_hits)"

# ---------------------------------------------------------------------------
t_start "L2 Part 3: --main-check -- main-session write collides with active owns/allowed_roots/shared_files -> DENY, otherwise ALLOW"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-13" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-13",
  "agents": [{"agent": "Dave#1", "allowed_roots": ["src/payment/**"], "owns": ["src/payment/refund.ts"]}],
  "shared_files": {"ci.yml": {"mode": "merge-owner", "owner": "Dave#1"}}
}
EOF
out=$("$SCRIPT" bd-13 src/payment/refund.ts --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "main-session write to an OWNED path -> DENY"

out=$("$SCRIPT" bd-13 src/payment/anything-else.ts --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "main-session write inside an agent's allowed_roots (even if unclaimed) -> DENY -- otherwise the scope lock is bypassable from main session"

out=$("$SCRIPT" bd-13 ci.yml --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "main-session write to an active shared_files path -> DENY"

out=$("$SCRIPT" bd-13 README.md --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "main-session write fully outside any active scope surface -> ALLOW"

out=$("$SCRIPT" bd-does-not-exist README.md --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "main-session --main-check against a bd with no manifest at all -> ALLOW, nothing to enforce"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "shared_files strategy (SS7.2): exclusive/merge-owner locks to owner"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-2" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-2",
  "agents": [{"agent": "Dave#1", "owns": []}, {"agent": "Dave#2", "owns": []}],
  "shared_files": {
    "package.json": {"mode": "merge-owner", "owner": "Dave#1"},
    "ci.yml": {"mode": "exclusive", "owner": "Dave#1"}
  }
}
EOF
out=$("$SCRIPT" bd-2 Dave#1 package.json 2>&1); rc=$?
assert_rc "$rc" 0 "merge-owner: owner writes -> ALLOW"
out=$("$SCRIPT" bd-2 Dave#2 package.json 2>&1); rc=$?
assert_rc "$rc" 1 "merge-owner: non-owner writes -> DENY"
assert_contains "$out" "merge-owner" "DENY message should name the strategy"
out=$("$SCRIPT" bd-2 Dave#2 ci.yml 2>&1); rc=$?
assert_rc "$rc" 1 "exclusive: non-owner writes -> DENY"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "shared_files strategy (SS7.2): append-only allows any registered agent, denies unregistered"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-3" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-3",
  "agents": [{"agent": "Dave#1", "owns": []}, {"agent": "Dave#2", "owns": []}],
  "shared_files": {"migrations/index": {"mode": "append-only"}}
}
EOF
out=$("$SCRIPT" bd-3 Dave#1 migrations/index 2>&1); rc=$?
assert_rc "$rc" 0 "append-only: registered agent 1 -> ALLOW"
out=$("$SCRIPT" bd-3 Dave#2 migrations/index 2>&1); rc=$?
assert_rc "$rc" 0 "append-only: registered agent 2 -> ALLOW"
out=$("$SCRIPT" bd-3 Ghost migrations/index 2>&1); rc=$?
assert_rc "$rc" 1 "append-only: unregistered agent -> DENY"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "shared_files strategy (SS7.2): generated always denies + points at regenerate_via"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-4" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-4",
  "agents": [{"agent": "Dave#1", "owns": []}],
  "shared_files": {"dist/**": {"mode": "generated", "regenerate_via": "npm run build"}}
}
EOF
out=$("$SCRIPT" bd-4 Dave#1 dist/bundle.js 2>&1); rc=$?
assert_rc "$rc" 1 "generated file -> DENY even for the manifest's only agent"
assert_contains "$out" "npm run build" "DENY message should surface regenerate_via"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "shared_files strategy: unknown mode value fails safe (DENY), not silently ALLOW"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-5" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-5",
  "agents": [{"agent": "Dave#1", "owns": []}],
  "shared_files": {"weird.txt": {"mode": "yolo"}}
}
EOF
out=$("$SCRIPT" bd-5 Dave#1 weird.txt 2>&1); rc=$?
assert_rc "$rc" 1 "unrecognized mode should fail-safe DENY, never a silent ALLOW"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "optimistic conflict check (SS7.3): snapshot then verify -- no drift ALLOWs, drift CONFLICTs"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-6" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-6",
  "agents": [{"agent": "Dave#1", "owns": ["ci.yml"]}]
}
EOF
echo "version A" > "$D/ci.yml"
out=$("$SCRIPT" bd-6 Dave#1 ci.yml --verify 2>&1); rc=$?
assert_rc "$rc" 3 "verify before any snapshot -> CONFLICT (no baseline recorded)"
assert_contains "$out" "no recorded snapshot" "message should say why: no snapshot yet"

out=$("$SCRIPT" bd-6 Dave#1 ci.yml --snapshot 2>&1); rc=$?
assert_rc "$rc" 0 "snapshot should succeed"
out=$("$SCRIPT" bd-6 Dave#1 ci.yml --verify 2>&1); rc=$?
assert_rc "$rc" 0 "verify right after snapshot, no file change -> ALLOW"

echo "version B (someone else's edit)" > "$D/ci.yml"
out=$("$SCRIPT" bd-6 Dave#1 ci.yml --verify 2>&1); rc=$?
assert_rc "$rc" 3 "file drifted from snapshot -> CONFLICT, re-evaluate before write"
assert_contains "$out" "changed since snapshot" "CONFLICT message should explain drift"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "optimistic conflict check (SS7.3): coupled_with -- the real ac632a3 incident shape"
# ci.yml itself is untouched by the writer, but the file it is semantically coupled to
# (golden.json) drifted underneath it -- exactly what happened across two correctly
# scope-locked agents in commit ac632a3 on this repo (see references/scope/example.manifest.json).
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-7" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-7",
  "agents": [{"agent": "Dave#1", "owns": ["ci.yml"]}, {"agent": "Dave#2", "owns": ["golden.json"]}],
  "shared_files": {"ci.yml": {"mode": "merge-owner", "owner": "Dave#1", "coupled_with": ["golden.json"]}}
}
EOF
echo "ci-v1" > "$D/ci.yml"
echo "golden-v1" > "$D/golden.json"
"$SCRIPT" bd-7 Dave#1 ci.yml --snapshot >/dev/null 2>&1
out=$("$SCRIPT" bd-7 Dave#1 ci.yml --verify 2>&1); rc=$?
assert_rc "$rc" 0 "no drift on either coupled path yet -> ALLOW"

# Dave#2 does exactly what its OWN scope contract allows: edits golden.json (not ci.yml)
echo "golden-v2 (bd_id migrated to null)" > "$D/golden.json"

out=$("$SCRIPT" bd-7 Dave#1 ci.yml --verify 2>&1); rc=$?
assert_rc "$rc" 3 "ci.yml's OWN content is untouched, but its declared coupled_with (golden.json) drifted -> CONFLICT"
assert_contains "$out" "golden.json" "CONFLICT should name the coupled path that actually drifted, not ci.yml"
rm -rf "$D"

# ---------------------------------------------------------------------------
# MUTATION (a): disable the ownership DENY branch -> the cross-owner DENY test must go red
t_start "MUTATION (a): disabling the ownership check makes scope-check.sh ALLOW a path it does not own"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-mut-a" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-mut-a",
  "agents": [
    {"agent": "Dave#1", "owns": ["src/orders/**"]},
    {"agent": "Dave#2", "owns": ["src/payments/**"]}
  ]
}
EOF
baseline_out=$("$SCRIPT" bd-mut-a Dave#1 src/payments/handler.py 2>&1); baseline_rc=$?
assert_rc "$baseline_rc" 1 "sanity: baseline really DENYs a path owned by someone else"
assert_contains "$baseline_out" "DENY" "sanity: baseline message says DENY"

BACKUP=$(mktemp -t scope-check-backup.XXXXXX)
cp "$SCRIPT" "$BACKUP"
# force the "found_owner belongs to someone else" branch to be unreachable -- every
# ownership match now looks like a self-match, i.e. "the ownership check is off"
sed -i.bak 's/if \[ "\$found_owner" = "\$agent" \]; then/if true; then/' "$SCRIPT"

mutated_out=$("$SCRIPT" bd-mut-a Dave#1 src/payments/handler.py 2>&1); mutated_rc=$?
if [ "$mutated_rc" -eq 1 ]; then
  t_fail "mutation should have made scope-check.sh ALLOW a path owned by Dave#2, but it still DENYs -- mutation did not take effect (test would stay green without proving the check runs)"
else
  assert_contains "$mutated_out" "ALLOW" "mutated ownership check should now (wrongly) ALLOW"
fi

mv "$BACKUP" "$SCRIPT"
chmod +x "$SCRIPT"
rm -f "$SCRIPT.bak"
restored_out=$("$SCRIPT" bd-mut-a Dave#1 src/payments/handler.py 2>&1); restored_rc=$?
assert_rc "$restored_rc" 1 "restore: scope-check.sh back to original, DENY again for a path owned by someone else"
rm -rf "$D"

# ---------------------------------------------------------------------------
# MUTATION (b): disable the optimistic sha-drift comparison -> the CONFLICT test must go red
t_start "MUTATION (b): disabling the optimistic sha check makes --verify miss real drift"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-mut-b" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-mut-b",
  "agents": [{"agent": "Dave#1", "owns": ["ci.yml"]}]
}
EOF
echo "v1" > "$D/ci.yml"
"$SCRIPT" bd-mut-b Dave#1 ci.yml --snapshot >/dev/null 2>&1
echo "v2 -- someone else's edit" > "$D/ci.yml"
baseline_out=$("$SCRIPT" bd-mut-b Dave#1 ci.yml --verify 2>&1); baseline_rc=$?
assert_rc "$baseline_rc" 3 "sanity: baseline really CONFLICTs on real drift"

BACKUP=$(mktemp -t scope-check-backup.XXXXXX)
cp "$SCRIPT" "$BACKUP"
# force the sha-mismatch branch to be unreachable -- "the optimistic check is off"
sed -i.bak 's/elif \[ "\$base_h" != "\$cur_h" \]; then/elif false; then/' "$SCRIPT"

mutated_out=$("$SCRIPT" bd-mut-b Dave#1 ci.yml --verify 2>&1); mutated_rc=$?
if [ "$mutated_rc" -eq 3 ]; then
  t_fail "mutation should have made --verify miss the drift (exit 0), but it still reports CONFLICT -- mutation did not take effect"
else
  assert_rc "$mutated_rc" 0 "mutated --verify wrongly reports no conflict"
fi

mv "$BACKUP" "$SCRIPT"
chmod +x "$SCRIPT"
rm -f "$SCRIPT.bak"
restored_out=$("$SCRIPT" bd-mut-b Dave#1 ci.yml --verify 2>&1); restored_rc=$?
assert_rc "$restored_rc" 3 "restore: scope-check.sh back to original, real drift CONFLICTs again"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "packaging: make pack ships references/scope/*.json + scripts/scope-check.sh"
ver=$(jq -r .version "$REPO_ROOT/.claude-plugin/plugin.json" 2>/dev/null)
plugin="$REPO_ROOT/shode-house-v${ver}.plugin"
pack_out=$(cd "$REPO_ROOT" && make pack 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "references/scope/manifest.schema.json" "packed artifact must ship the manifest schema"
assert_contains "$listing" "references/scope/example.manifest.json" "packed artifact must ship the example manifest"
assert_contains "$listing" "scripts/scope-check.sh" "packed artifact must ship scope-check.sh"

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
