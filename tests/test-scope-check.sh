#!/usr/bin/env bash
# tests/test-scope-check.sh -- bash-only test suite for Milestone E (bd: shode-roadmap/C-E1)
# scripts/scope-check.sh + references/scope/{manifest.schema.json,example.manifest.json}
#
# No framework dependency (same style as tests/test-workflow-state.sh + tests/test-registry.sh)
# -- plain bash test functions + a tiny assert library. Each test runs inside a
# mktemp -d sandbox via SCOPECHECK_ROOT so tests never touch the real repo state. Wired
# into ci.yml as exactly ONE step (CLAUDE.md rule: this milestone may add no more than 1
# CI step total).
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
t_start "ownership (SS7.1): 3 real cases -- own path ALLOW, other agent's path DENY, unclaimed path ALLOW"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-1" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-1",
  "agents": [
    {"agent": "Dave#1", "owns": ["src/orders/**"]},
    {"agent": "Dave#2", "owns": ["src/payments/**"]}
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

out=$("$SCRIPT" bd-1 Dave#1 README.md 2>&1); rc=$?
assert_rc "$rc" 0 "unclaimed path should ALLOW (permissive-by-design)"
assert_contains "$out" "unclaimed" "unclaimed path should be flagged as such, not a bare silent ALLOW"
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
pack_out=$(cd "$REPO_ROOT" && make pack-legacy 2>&1); pack_rc=$?
assert_true "$pack_rc" "make pack should build successfully -- output: $pack_out"
[ -f "$plugin" ] && t_ok || t_fail "expected artifact not found at $plugin"
listing=$(unzip -l "$plugin" 2>/dev/null)
assert_contains "$listing" "references/scope/manifest.schema.json" "packed artifact must ship the manifest schema"
assert_contains "$listing" "references/scope/example.manifest.json" "packed artifact must ship the example manifest"
assert_contains "$listing" "scripts/scope-check.sh" "packed artifact must ship scope-check.sh"

printf '\n== %d passed, %d failed ==\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
