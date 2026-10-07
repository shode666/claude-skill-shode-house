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
# into ci.yml as exactly ONE step (milestone constraint: this milestone may add no more than 1
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
t_skip()  { printf '   SKIP: %s\n' "$1"; }

# The Shift_JIS locale's own name on this host, or empty: macOS lists "ja_JP.SJIS", glibc
# the normalised "ja_JP.sjis" (Chris pre-release C8). No -q / head under pipefail.
SJIS_LOCALE=$(locale -a 2>/dev/null | grep -ix 'ja_jp\.sjis' | sed -n 1p)

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

# wd <seconds> <command...> -- the suite's watchdog: the command runs in its own process
# group, and at the deadline the WHOLE group is killed (status 142), so no child outlives it
# holding the $(...) pipe (Chris U21 I-3). Same helper as in test-hooks.sh.
wd() {
  perl -e '
    my $t = shift; my $pid = fork; defined $pid or exit 126;
    if ($pid == 0) { setpgrp(0, 0); exec { $ARGV[0] } @ARGV; exit 127 }
    setpgrp($pid, $pid);
    $SIG{ALRM} = sub { kill "KILL", -$pid; waitpid($pid, 0); exit 142 };
    alarm $t; waitpid($pid, 0); alarm 0;
    exit(($? & 127) ? 128 + ($? & 127) : $? >> 8)' "$@"
}

# sc_tree <dir> [<case-fold helper>] -- a scratch copy of the tree for scope-check.sh: the
# script, its lock library and (when given) a case-fold helper, at the paths the script
# always loads them from. No variable of the environment chooses code scope-check.sh sources
# (UD U21; Chris U21 I-2), so a test that needs another helper runs such a copy. Prints the
# copy's scope-check.sh.
sc_tree() {
  mkdir -p "$1/scripts/lib" "$1/hooks/scripts"
  cp -p "$SCRIPT" "$1/scripts/scope-check.sh"; cp -p "$REPO_ROOT/scripts/lib/lock.sh" "$1/scripts/lib/lock.sh"
  if [ -n "${2:-}" ]; then cp "$2" "$1/hooks/scripts/_casefold.sh"; fi
  printf '%s' "$1/scripts/scope-check.sh"
}

write_manifest() {
  # $1=root $2=bd-id-filename(already encoded) $3=heredoc content on stdin
  mkdir -p "$1/.shode-house/scope"
  cat > "$1/.shode-house/scope/$2.json"
}

# ---------------------------------------------------------------------------
# This suite's own copy of wd (Chris final I-5): the same self-test as test-hooks.sh, so a
# regression in this copy (killing only the command, not its group) is caught here too.
t_start "watchdog (Chris U21 I-3, final I-5): this suite's wd kills the command's whole process group -- a command whose children hold the output pipe for 6 s ends at its 1 s deadline with status 142, and the capture returns within 4 s; a command that ends in time keeps its status and output"
wd_t0=$(date +%s)
wd_out=$(wd 1 bash -c 'sleep 6 & sleep 6; echo late'); wd_rc=$?
wd_t1=$(date +%s)
assert_eq "$wd_rc" 142 "status at the deadline"
[ $((wd_t1 - wd_t0)) -le 4 ] && t_ok || t_fail "the capture took $((wd_t1 - wd_t0)) s: a child outlived the watchdog"
assert_eq "$wd_out" "" "no output after the deadline"
wd_out=$(wd 5 bash -c 'echo in-time; exit 3'); wd_rc=$?
assert_eq "$wd_rc:$wd_out" "3:in-time" "a command that ends in time"

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
t_start "NF2 (router R74, bd: shode-house-v7u.4.34): path_matches uses the shared fold -- long s, Kelvin sign (under LC_ALL=C too), a multibyte locale, Thai patterns"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-fold" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-fold",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["docs/**"], "owns": ["docs/a.md"]},
    {"agent": "Dave#2", "allowed_roots": ["src/orders/**", "src/kernel/**", "src/*sales/**", "src/ไทย/**"], "owns": ["src/orders/**"]}
  ]
}
EOF
mkdir -p "$D/src/orders"
nf2_ls=$(printf '\305\277'); nf2_kv=$(printf '\342\204\252')
out=$("$SCRIPT" bd-fold "${nf2_ls}rc/orders/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "<U+017F>rc/orders/x.ts collides with Dave#2's src/orders/** (APFS writes src/orders/x.ts)"
out=$("$SCRIPT" bd-fold Dave#1 "src/order${nf2_ls}/x.ts" 2>&1); rc=$?
assert_rc "$rc" 1 "src/order<U+017F>/x.ts is Dave#2's file, not Dave#1's"
assert_contains "$out" "Dave#2" "the long-s DENY names the real owner"
out=$(env LC_ALL=C "$SCRIPT" bd-fold "src/${nf2_kv}ernel/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "Kelvin sign under LC_ALL=C (macOS tr folds it only in a UTF-8 locale)"
out=$("$SCRIPT" bd-fold "src/ไทย/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "a Thai allowed_roots pattern still matches its own path byte for byte"
out=$("$SCRIPT" bd-fold "src/ไท/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "a different Thai name does not match (no over-match)"
out=$("$SCRIPT" bd-fold "docs/b.md" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "control: plain ASCII collision unchanged"
jq '.agents[1].allowed_roots += ["src/files/**", "src/strasse/**"]' "$D/.shode-house/scope/bd-fold.json" > "$D/m.tmp" && mv -f "$D/m.tmp" "$D/.shode-house/scope/bd-fold.json"
# Sentinel pre-release B2: the ligatures and the sharp s are part of the deterministic fold.
out=$("$SCRIPT" bd-fold "src/$(printf '\357\254\201')les/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "src/<U+FB01>les/x.ts collides with src/files/** (APFS writes src/files/x.ts)"
out=$("$SCRIPT" bd-fold "src/stra$(printf '\303\237')e/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "src/stra<U+00DF>e/x.ts collides with src/strasse/**"
out=$("$SCRIPT" bd-fold "src/STRA$(printf '\341\272\236')E/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "src/STRA<U+1E9E>E/x.ts collides with src/strasse/**"
if [ -n "$SJIS_LOCALE" ]; then
  out=$(env LC_ALL="$SJIS_LOCALE" "$SCRIPT" bd-fold "src/$(printf '\343\201\202')sales/x.ts" --main-check 2>&1); rc=$?
  assert_rc "$rc" 1 "LC_ALL=$SJIS_LOCALE: src/<U+3042>sales/x.ts still matches src/*sales/** (the last byte of U+3042 must not swallow the s)"
else
  t_skip "no Shift_JIS locale (ja_JP.SJIS / ja_JP.sjis) installed -- SJIS case not exercised here"
fi
rm -rf "$D"

# Router R78 (amends R77): a match that DENIES an outsider uses the deny-side fold, which
# adds the platform's Unicode lower-casing (U+00DC -> U+00FC on macOS, where APFS treats the
# two spellings as one directory); a match that GRANTS keeps the deterministic fold.
t_start "R78: an outsider collision uses the deny-side fold (src/<U+00DC>ber/x.ts collides with Dave#1's src/über/**; docs/<U+00E4>rger.md with the shared key docs/<U+00C4>rger.md), an owner grant does not"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-r78" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-r78",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/über/**"], "owns": ["src/über/**"]},
    {"agent": "Dave#2", "allowed_roots": ["src/**", "docs/**"], "owns": []}
  ],
  "shared_files": {"docs/Ärger.md": {"mode": "exclusive", "owner": "Dave#1"},
                   "shared/Ärger.md": {"mode": "exclusive", "owner": "Dave#1"}}
}
EOF
r78_U=$(printf 'src/\303\234ber/x.ts'); r78_ae=$(printf 'docs/\303\244rger.md'); r78_sh=$(printf 'shared/\303\244rger.md')
out=$("$SCRIPT" bd-r78 Dave#1 "src/über/x.ts" 2>&1); rc=$?
assert_rc "$rc" 0 "control: the owner's own spelling is granted"
out=$("$SCRIPT" bd-r78 "lib/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "control: a path outside every pattern does not collide"
for r78_loc in C en_US.UTF-8; do
  out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 Dave#1 "$r78_U" 2>&1); rc=$?
  assert_rc "$rc" 1 "LC_ALL=$r78_loc: the owner's pattern does NOT grant src/<U+00DC>ber/x.ts (the grant side keeps the deterministic fold)"
  out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 Dave#1 "$r78_ae" 2>&1); rc=$?
  assert_rc "$rc" 1 "LC_ALL=$r78_loc: a shared key matched only through the deny-side fold never grants its owner"
done
if [ "$(printf '\303\234' | env LC_ALL=en_US.UTF-8 tr '[:upper:]' '[:lower:]' 2>/dev/null)" = "$(printf '\303\274')" ]; then
  for r78_loc in C en_US.UTF-8; do
    out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 "$r78_U" --main-check 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r78_loc: main session src/<U+00DC>ber/x.ts collides with src/über/**"
    assert_contains "$out" 'agent "Dave#1"' "LC_ALL=$r78_loc: the main-session collision is Dave#1's src/über/** (listed before Dave#2's src/**)"
    out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 "$r78_sh" --main-check 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r78_loc: main session shared/<U+00E4>rger.md collides with the shared key shared/<U+00C4>rger.md (no agent pattern covers shared/)"
    assert_contains "$out" 'shared_files' "LC_ALL=$r78_loc: the collision names the shared key"
    out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 Dave#2 "$r78_U" 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r78_loc: Dave#2 src/<U+00DC>ber/x.ts is Dave#1's file (was NEEDS_AMENDMENT 4 under R77)"
    assert_contains "$out" 'owned by "Dave#1"' "the R78 DENY names the real owner"
    out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 "$r78_ae" --main-check 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r78_loc: main session docs/<U+00E4>rger.md collides with the shared key docs/<U+00C4>rger.md"
    out=$(env LC_ALL="$r78_loc" "$SCRIPT" bd-r78 Dave#2 "$r78_ae" 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r78_loc: Dave#2 docs/<U+00E4>rger.md is refused by the exclusive shared key (was NEEDS_AMENDMENT 4)"
  done
  out=$("$SCRIPT" bd-r78 Dave#2 "$r78_U" --amend 2>&1); rc=$?
  assert_rc "$rc" 1 "Dave#2 cannot self-amend src/<U+00DC>ber/x.ts into its owns[]"
  [ "$(jq -r '.agents[1].owns | length' "$D/.shode-house/scope/bd-r78.json")" = 0 ] && t_ok || t_fail "the refused amend changed the manifest"
else
  t_skip "this platform's tr does not lower U+00DC (byte-based tr): the deny-side fold equals the deterministic fold here"
fi
rm -rf "$D"

# Chris pre-release r3 R3-3: the two candidate-fold memos (D5) must stay separate. Here another
# agent's pattern is listed FIRST, so path_matches_deny folds the candidate (and fills its
# memo) before the owner's own pattern is matched with path_matches. A shared memo would hand
# the deny-side fold to the grant side and grant src/<U+00DC>ber/x.ts to its owner.
t_start "R78 / R3-3: another agent listed before the owner -- the deny-fold memo never reaches the owner's grant: Dave#1 src/<U+00DC>ber/x.ts -> 1 (not ALLOW self)"
if [ "$(printf '\303\234' | env LC_ALL=en_US.UTF-8 tr '[:upper:]' '[:lower:]' 2>/dev/null)" = "$(printf '\303\274')" ]; then
  D=$(sandbox); export SCOPECHECK_ROOT="$D"
  write_manifest "$D" "bd-r33" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-r33",
  "agents": [
    {"agent": "B", "allowed_roots": ["lib/**"], "owns": ["lib/**"]},
    {"agent": "Dave#1", "allowed_roots": ["src/über/**"], "owns": ["src/über/**"]}
  ]
}
EOF
  for r33_loc in C en_US.UTF-8; do
    out=$(env LC_ALL="$r33_loc" "$SCRIPT" bd-r33 Dave#1 "$(printf 'src/\303\234ber/x.ts')" 2>&1); rc=$?
    assert_rc "$rc" 1 "LC_ALL=$r33_loc: Dave#1 is not granted src/<U+00DC>ber/x.ts after a deny-side match against B's lib/**"
    case "$out" in *"(self)"*) t_fail "LC_ALL=$r33_loc: a self grant was reported: $out" ;; *) t_ok ;; esac
  done
  out=$("$SCRIPT" bd-r33 Dave#1 "src/über/x.ts" 2>&1); rc=$?
  assert_rc "$rc" 0 "control: Dave#1's own spelling is granted with B listed first"
  rm -rf "$D"
else
  t_skip "this platform's tr does not lower U+00DC (byte-based tr): both folds are equal here, so a shared memo cannot widen a grant"
fi

# F-6 (UD U12, Sentinel pre-release r3): on macOS an outsider collision ALSO compares the
# Unicode NFC spelling (deny side only), because APFS treats canonically equivalent spellings
# as one name: the NFD "src/u<U+0308>ber/x.ts" IS src/über/x.ts there, and so is a Thai name
# with its marks typed in another order. Never on the grant side (R77/R78), and never off
# macOS: Linux keeps the spellings apart, so its behaviour must not change. Each block runs
# twice: natively, and as on Linux (the non-macOS branch). The platform signal is the
# kernel's name from /usr/bin/uname (or /bin/uname), never $OSTYPE (Sentinel r7 F7-4), so the
# Linux pass runs a scratch copy of the tree (sc_tree) whose case-fold helper names a stand-in
# uname that prints the given name.
# f6_mklib <dir> <uname output, empty = no uname at all> -- writes <dir>/_casefold.sh and a
# tree copy under <dir>/tree whose scope-check.sh loads it (<dir>/tree/scripts/scope-check.sh).
f6_mklib() {
  mkdir -p "$1"
  sed -e "s#/usr/bin/uname#$1/uname#g" -e "s#/bin/uname#$1/uname#g" "$REPO_ROOT/hooks/scripts/_casefold.sh" > "$1/_casefold.sh"
  if [ -n "$2" ]; then printf '#!/bin/sh\necho %s\n' "$2" > "$1/uname"; chmod 755 "$1/uname"; fi
  sc_tree "$1/tree" "$1/_casefold.sh" >/dev/null
}
f6_lin=$(mktemp -d -t scope-uname-lin.XXXXXX); f6_mklib "$f6_lin" Linux
f6_mac_lib=$(mktemp -d -t scope-uname-mac.XXXXXX); f6_mklib "$f6_mac_lib" Darwin
f6_unk=$(mktemp -d -t scope-uname-unk.XXXXXX); f6_mklib "$f6_unk" ""
t_start "F7-4 premise: the stand-in helper copies replace every uname path (and only those lines differ from the real helper)"
for f6_l in "$f6_lin" "$f6_mac_lib" "$f6_unk"; do
  [ "$(grep -c '/usr/bin/uname\|[^a-z]/bin/uname' "$f6_l/_casefold.sh")" = 0 ] && [ "$(grep -c "$f6_l/uname" "$f6_l/_casefold.sh")" -ge 2 ] && t_ok || t_fail "$f6_l: uname paths not replaced"
done
f6_nfd_u=$(printf 'src/u\314\210ber/x.ts'); f6_nfd_uu=$(printf 'src/U\314\210ber/x.ts'); f6_nfd_a=$(printf 'docs/A\314\210rger.md')
f6_nfc_n=$(printf 'nfd/\303\274ber/x.ts'); f6_th_swap=$(printf 'th/\340\270\227\340\271\210\340\270\270\340\270\207/x.md')
f6_th_other=$(printf 'th/\340\271\204\340\270\227\340\270\242/x.md'); f6_bad=$(printf 'zz/\377.ts'); f6_bad_src=$(printf 'src/\377.ts')
for f6_os in native linux; do
  # fresh manifests per pass: a refused or accepted --amend in one pass never reaches the next
  f6_D=$(sandbox)
  write_manifest "$f6_D" "bd-f6m" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-f6m",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/über/**"], "owns": ["src/über/**", "nfd/über/**", "th/ทุ่ง/**", "docs/design-run-order*"]},
    {"agent": "Dave#2", "allowed_roots": ["lib/**"], "owns": []}
  ],
  "shared_files": {"docs/Ärger.md": {"mode": "exclusive", "owner": "Dave#1"}}
}
EOF
  write_manifest "$f6_D" "bd-f6s" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-f6s",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/über/**"], "owns": ["src/über/**", "docs/design-run-order*"]},
    {"agent": "Dave#2", "allowed_roots": ["src/**", "docs/**"], "owns": []}
  ],
  "shared_files": {"docs/Ärger.md": {"mode": "exclusive", "owner": "Dave#1"}}
}
EOF
  if [ "$f6_os" = native ]; then f6_baselib="$REPO_ROOT/hooks/scripts/_casefold.sh" f6_sc="$SCRIPT"; else f6_baselib="$f6_lin/_casefold.sh" f6_sc="$f6_lin/tree/scripts/scope-check.sh"; fi
  case "$f6_os:$OSTYPE" in native:darwin*) f6_mac=1 ;; *) f6_mac=0 ;; esac
  if [ "$f6_mac" -eq 1 ]; then f6_hit=1 f6_amend=1; else f6_hit=0 f6_amend=4; fi
  export SCOPECHECK_ROOT="$f6_D"
  t_start "F-6 [$f6_os] main session: NFD src/u<U+0308>ber/x.ts and src/U<U+0308>ber/x.ts vs src/über/**, NFD docs/A<U+0308>rger.md vs the shared key docs/Ärger.md, NFC nfd/über/x.ts vs the NFD pattern nfd/u<U+0308>ber/**, Thai th/<marks swapped>/x.md vs th/<U+0E17 U+0E38 U+0E48 U+0E07>/** -> $f6_hit (1 = DENY on macOS, 0 = unchanged elsewhere)"
  for f6_p in "$f6_nfd_u" "$f6_nfd_uu" "$f6_nfd_a" "$f6_nfc_n" "$f6_th_swap"; do
    out=$("$f6_sc" bd-f6m "$f6_p" --main-check 2>&1); rc=$?
    assert_rc "$rc" "$f6_hit" "[$f6_os] main session $(printf '%q' "$f6_p")"
    if [ "$f6_mac" -eq 1 ]; then assert_contains "$out" "DENY: main-session write" "[$f6_os] $(printf '%q' "$f6_p") is a collision"; fi
  done
  t_start "F-6 [$f6_os] controls: a different Thai name th/<U+0E44 U+0E17 U+0E22>/x.md, an unrelated non-ASCII zz/<U+00FC>.ts and zz/x.ts -> 0; the owner's own spelling src/über/x.ts -> 1 (a collision, as before)"
  for f6_p in "$f6_th_other" "$(printf 'zz/\303\274.ts')" zz/x.ts; do
    out=$("$f6_sc" bd-f6m "$f6_p" --main-check 2>&1); rc=$?
    assert_rc "$rc" 0 "[$f6_os] control $(printf '%q' "$f6_p")"
  done
  out=$("$f6_sc" bd-f6m "src/über/x.ts" --main-check 2>&1); rc=$?
  assert_rc "$rc" 1 "[$f6_os] src/über/x.ts collides"
  # Chris r7 F2 (UD U20): the NFC compare only ADDS denies. The raw NFD spelling
  # docs/design-run-order<U+0301>.md matches Dave#1's docs/design-run-order*; its NFC form ends
  # in ...orde<U+0155>.md and does not, so an NFC compare that REPLACED the raw one would allow it.
  t_start "F-6 [$f6_os] NFC only adds denies (Chris r7 F2): main session NFD docs/design-run-order<U+0301>.md vs Dave#1's docs/design-run-order* -> 1; Dave#2 (docs/** in its allowed_roots) the same path -> 1, owned by Dave#1, never NEEDS_AMENDMENT"
  f6_dro=$(printf 'docs/design-run-order\314\201.md')
  if [ "$f6_mac" -eq 1 ]; then
    f6_dro_nfc=$(printf '' | bash -c '. "$1"; _scope_os=Darwin; _scope_nfc_batch_deny "$2"' _ "$REPO_ROOT/hooks/scripts/_casefold.sh" "$f6_dro" | LC_ALL=C tr '\0' '|')
    case "$f6_dro_nfc" in
      "C$(printf 'docs/design-run-orde\305\225.md')|E|") t_ok ;;
      *) t_fail "[$f6_os] premise: the NFC form of the fixture is docs/design-run-orde<U+0155>.md, got $(printf '%q' "$f6_dro_nfc")" ;;
    esac
  fi
  out=$("$f6_sc" bd-f6m "$f6_dro" --main-check 2>&1); rc=$?
  assert_rc "$rc" 1 "[$f6_os] main session $(printf '%q' "$f6_dro")"
  assert_contains "$out" 'pattern "docs/design-run-order*"' "[$f6_os] the collision names the raw pattern"
  out=$("$f6_sc" bd-f6s Dave#2 "$f6_dro" 2>&1); rc=$?
  assert_rc "$rc" 1 "[$f6_os] Dave#2 $(printf '%q' "$f6_dro")"
  assert_contains "$out" 'owned by "Dave#1"' "[$f6_os] Dave#2: the deny names the owner"
  t_start "F-6 [$f6_os] a non-ASCII path that cannot be normalised (zz/<0xFF>.ts, not UTF-8; outside every pattern) -> DENY with the NFC message on macOS; 0 elsewhere (no normalisation)"
  out=$("$f6_sc" bd-f6m "$f6_bad" --main-check 2>&1); rc=$?
  if [ "$f6_mac" -eq 1 ]; then
    assert_rc "$rc" 1 "[$f6_os] main session zz/<0xFF>.ts"
    assert_contains "$out" "could not be Unicode-normalised (NFC)" "[$f6_os] the deny names the normalisation failure"
    out=$("$f6_sc" bd-f6s Dave#2 "$f6_bad_src" 2>&1); rc=$?
    assert_rc "$rc" 1 "[$f6_os] Dave#2 src/<0xFF>.ts (inside its allowed_roots) is denied, not NEEDS_AMENDMENT"
    assert_contains "$out" "could not be Unicode-normalised (NFC)" "[$f6_os] the subagent deny names the normalisation failure"
  else
    assert_rc "$rc" 0 "[$f6_os] main session zz/<0xFF>.ts (no normalisation)"
    out=$("$f6_sc" bd-f6s Dave#2 "$f6_bad_src" 2>&1); rc=$?
    assert_rc "$rc" 4 "[$f6_os] Dave#2 src/<0xFF>.ts (no normalisation): NEEDS_AMENDMENT as before"
  fi
  t_start "F-6 [$f6_os] subagent outsider: Dave#2 NFD src/u<U+0308>ber/x.ts and NFD docs/A<U+0308>rger.md -> $f6_amend (1 = Dave#1's file on macOS; 4 = NEEDS_AMENDMENT as before elsewhere)"
  for f6_p in "$f6_nfd_u" "$f6_nfd_a"; do
    out=$("$f6_sc" bd-f6s Dave#2 "$f6_p" 2>&1); rc=$?
    assert_rc "$rc" "$f6_amend" "[$f6_os] Dave#2 $(printf '%q' "$f6_p")"
  done
  if [ "$f6_mac" -eq 1 ]; then
    out=$("$f6_sc" bd-f6s Dave#2 "$f6_nfd_u" 2>&1)
    assert_contains "$out" 'owned by "Dave#1"' "[$f6_os] the deny names the real owner"
    out=$("$f6_sc" bd-f6s Dave#2 "$f6_nfd_u" --amend 2>&1); rc=$?
    assert_rc "$rc" 1 "[$f6_os] Dave#2 cannot self-amend the NFD spelling of Dave#1's file"
    [ "$(jq -r '.agents[1].owns | length' "$f6_D/.shode-house/scope/bd-f6s.json")" = 0 ] && t_ok || t_fail "[$f6_os] the refused amend changed the manifest"
  fi
  # The grant side never normalises (R77/R78; UD U12 "never for owner/grant matching"): the
  # owner's NFD spelling of its own pattern, and the NFD spelling of a shared key it owns, are
  # NOT granted -- a grant through NFC would turn both into ALLOW.
  t_start "F-6 [$f6_os] grant side: Dave#1 NFD src/u<U+0308>ber/x.ts and NFD docs/A<U+0308>rger.md -> 1 (not ALLOW: owner matching keeps the deterministic fold); Dave#1 src/über/x.ts and docs/Ärger.md -> 0"
  for f6_p in "$f6_nfd_u" "$f6_nfd_a"; do
    out=$("$f6_sc" bd-f6s Dave#1 "$f6_p" 2>&1); rc=$?
    assert_rc "$rc" 1 "[$f6_os] Dave#1 $(printf '%q' "$f6_p") is not granted"
    case "$out" in ALLOW*) t_fail "[$f6_os] Dave#1 $(printf '%q' "$f6_p") was granted: $out" ;; *) t_ok ;; esac
  done
  for f6_p in "src/über/x.ts" "docs/Ärger.md"; do
    out=$("$f6_sc" bd-f6s Dave#1 "$f6_p" 2>&1); rc=$?
    assert_rc "$rc" 0 "[$f6_os] control: Dave#1 $f6_p"
  done
  # F7-1 (UD U20, Sentinel r7 F7-1, Chris r7 F1): ONE normaliser process per check, however many
  # non-ASCII patterns the check compares. The perl calls are counted through a tree copy
  # (sc_tree) whose case-fold helper calls a counting wrapper in place of /usr/bin/perl, which
  # runs the real one.
  if [ "$f6_mac" -eq 1 ]; then f6_one=1; else f6_one=0; fi
  t_start "F7-1 [$f6_os] one normaliser process per check: a manifest with 60 non-ASCII owns entries -- main session NFD miss, NFD collision, subagent non-ASCII ownership check -> $f6_one perl call each (1 on macOS, 0 elsewhere), verdicts unchanged; an ASCII candidate -> 0 perl calls"
  f6_lib=$(mktemp -d -t scope-nfc-lib.XXXXXX)
  sed "s#/usr/bin/perl -T #$f6_lib/perl -T #" "$f6_baselib" > "$f6_lib/_casefold.sh"
  [ "$(grep -c "perl -T " "$f6_lib/_casefold.sh")" = 1 ] && [ "$(grep -c "$f6_lib/perl -T " "$f6_lib/_casefold.sh")" = 1 ] && t_ok || t_fail "[$f6_os] the counting copy must replace the one perl call"
  printf '#!/bin/sh\nprintf x >> "%s/count"\nexec /usr/bin/perl "$@"\n' "$f6_lib" > "$f6_lib/perl"; chmod 755 "$f6_lib/perl"
  f6_csc=$(sc_tree "$f6_lib/tree" "$f6_lib/_casefold.sh")
  jq -n '{schema_version:1, bd_id:"bd-f6n", agents:[
    {agent:"Dave#3", allowed_roots:["n3/**"], owns:[range(60) | "n3/f\(.)-\u00fcber.ts"]},
    {agent:"Dave#1", allowed_roots:["src/\u00fcber/**"], owns:["src/\u00fcber/**"]},
    {agent:"Dave#2", allowed_roots:["lib/**"], owns:[]}]}' > "$f6_D/.shode-house/scope/bd-f6n.json"
  for f6_case in "$(printf 'zz/u\314\210.ts')|--main-check|0|$f6_one" "$f6_nfd_u|--main-check|$f6_hit|$f6_one" \
                 "$(printf 'lib/\303\274.ts')|Dave#2|4|$f6_one" "zz/x.ts|--main-check|0|0"; do
    IFS='|' read -r f6_p f6_who f6_want f6_calls <<EOF
$f6_case
EOF
    : > "$f6_lib/count"
    if [ "$f6_who" = --main-check ]; then
      out=$("$f6_csc" bd-f6n "$f6_p" --main-check 2>&1); rc=$?
    else
      out=$("$f6_csc" bd-f6n "$f6_who" "$f6_p" 2>&1); rc=$?
    fi
    assert_rc "$rc" "$f6_want" "[$f6_os] $f6_who $(printf '%q' "$f6_p")"
    assert_eq "$(wc -c < "$f6_lib/count" | tr -d ' ')" "$f6_calls" "[$f6_os] $f6_who $(printf '%q' "$f6_p"): perl calls"
  done
  rm -rf "$f6_lib" "$f6_D"
done

# F7-4 (Sentinel r7): the platform signal is the kernel's name (uname(2) through /usr/bin/uname
# or /bin/uname), never $OSTYPE or any other variable the hook's environment can set. A
# platform that cannot be determined counts as macOS (fail closed: the NFC compare runs, and a
# path it cannot normalise is denied).
f74_D=$(sandbox); export SCOPECHECK_ROOT="$f74_D"
write_manifest "$f74_D" "bd-f74" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-f74",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/über/**"], "owns": ["src/über/**", "src/ä/**", "src/ö/**"]}
  ]
}
EOF
case "$OSTYPE" in darwin*) f74_want=1 f74_other=linux-gnu f74_un=Linux ;; *) f74_want=0 f74_other=darwin23 f74_un=Darwin ;; esac
t_start "F7-4: OSTYPE=$f74_other, _scope_os=Linux, _scope_os=Darwin, UNAME_s=$f74_un or UNAME_SYSNAME=$f74_un (macOS's uname prints these in place of the kernel's name; Sentinel U21 F7-4-R) in the environment never changes the platform -- main session NFD src/u<U+0308>ber/x.ts -> $f74_want, as natively ($([ "$f74_want" = 1 ] && echo macOS || echo not macOS)); premise: bash takes OSTYPE from the environment"
[ "$(env OSTYPE="$f74_other" bash -c 'printf %s "$OSTYPE"')" = "$f74_other" ] && t_ok || t_fail "premise: bash did not take OSTYPE from the environment, so this test proves nothing"
out=$("$SCRIPT" bd-f74 "$f6_nfd_u" --main-check 2>&1); rc=$?
assert_rc "$rc" "$f74_want" "native"
for f74_e in "OSTYPE=$f74_other" "_scope_os=Linux" "_scope_os=Darwin" "UNAME_s=$f74_un" "UNAME_SYSNAME=$f74_un"; do
  out=$(env "$f74_e" "$SCRIPT" bd-f74 "$f6_nfd_u" --main-check 2>&1); rc=$?
  assert_rc "$rc" "$f74_want" "$f74_e in the environment"
done
t_start "F7-4: no uname at /usr/bin or /bin -> the platform counts as macOS (fail closed): NFD src/u<U+0308>ber/x.ts -> 1 on every host (the NFC collision, or the normalisation deny); a stand-in uname that says Darwin -> 1, one that says Linux -> 0"
out=$("$f6_unk/tree/scripts/scope-check.sh" bd-f74 "$f6_nfd_u" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "no uname"
out=$("$f6_mac_lib/tree/scripts/scope-check.sh" bd-f74 "$f6_nfd_u" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "uname says Darwin"
out=$("$f6_lin/tree/scripts/scope-check.sh" bd-f74 "$f6_nfd_u" --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "uname says Linux"
t_start "F7-4: uname runs at most once per scope-check process, and never for an ASCII path: a non-ASCII main-session check (three non-ASCII patterns) -> 1 uname call; an ASCII path -> 0"
f74_cl=$(mktemp -d -t scope-uname-cnt.XXXXXX)
sed -e "s#/usr/bin/uname#$f74_cl/uname#g" -e "s#/bin/uname#$f74_cl/uname#g" "$REPO_ROOT/hooks/scripts/_casefold.sh" > "$f74_cl/_casefold.sh"
f74_real=$(command -v uname)   # an absolute path: the helper runs uname with an empty environment
printf '#!/bin/sh\nprintf x >> "%s/count"\nexec %s "$@"\n' "$f74_cl" "$f74_real" > "$f74_cl/uname"; chmod 755 "$f74_cl/uname"
f74_csc=$(sc_tree "$f74_cl/tree" "$f74_cl/_casefold.sh")
: > "$f74_cl/count"; "$f74_csc" bd-f74 "$(printf 'zz/u\314\210.ts')" --main-check >/dev/null 2>&1
assert_eq "$(wc -c < "$f74_cl/count" | tr -d ' ')" 1 "non-ASCII path: uname calls"
: > "$f74_cl/count"; "$f74_csc" bd-f74 zz/x.ts --main-check >/dev/null 2>&1
assert_eq "$(wc -c < "$f74_cl/count" | tr -d ' ')" 0 "ASCII path: uname calls"
rm -rf "$f74_cl" "$f74_D"

# Sentinel U20 F8-1, Chris U20 N-1: jq -r writes a JSON "\u0000" in a shared_files key as a raw
# NUL byte; inside the helper's NUL-terminated records that forged records (a second "C", an
# "N" out of step) and could cancel the F-6 deny. The helper drops every line that holds a NUL
# (the string then counts as a collision), and the reader takes the records only in the
# helper's order. Owner Dave#1 owns src/ü/**; a NUL-poisoned manifest must give exactly the
# verdict of the same manifest without the poison (on macOS: DENY for the NFD spelling).
t_start "F8-1/N-1: a NUL in a manifest string (shared_files keys x/ü<NUL>Czz/zz, src/u<U+0308>/**<NUL>Nzzz, src/ü/**<NUL>Nzzz, docs/é<NUL>Cnothing; an owns entry and an allowed_roots entry of Dave#7) never changes a verdict: main session and Dave#9 (src/** in its allowed_roots) writing NFD src/u<U+0308>/a.ts -> the unpoisoned verdict (macOS: 1, DENY)"
n1_D=$(sandbox); export SCOPECHECK_ROOT="$n1_D"
n1_mk() {   # <bd> <shared_files json> <Dave#7 owns json> <Dave#7 roots json>
  mkdir -p "$n1_D/.shode-house/scope"
  printf '{"schema_version":1,"bd_id":"%s","shared_files":%s,"agents":[{"agent":"Dave#1","allowed_roots":["src/\\u00fc/**"],"owns":["src/\\u00fc/**"]},{"agent":"Dave#7","allowed_roots":%s,"owns":%s},{"agent":"Dave#9","allowed_roots":["src/**"],"owns":[]}]}\n' \
    "$1" "$2" "$4" "$3" > "$n1_D/.shode-house/scope/$1.json"
  jq empty "$n1_D/.shode-house/scope/$1.json" 2>/dev/null && t_ok || t_fail "fixture $1 is not valid JSON"
}
n1_mk bd-n1c '{}' '[]' '["lib/**"]'
n1_mk bd-n1a '{"x/ü\u0000Czz/zz":{"mode":"exclusive","owner":"Dave#1"}}' '[]' '["lib/**"]'
n1_mk bd-n1b '{"src/u\u0308/**\u0000Nzzz":{"mode":"exclusive","owner":"Dave#1"},"src/ü/**\u0000Nzzz":{"mode":"exclusive","owner":"Dave#1"},"docs/é\u0000Cnothing":{"mode":"exclusive","owner":"Dave#1"}}' '[]' '["lib/**"]'
n1_mk bd-n1d '{}' '["q/ü\u0000Czz/zz", "src/ü/**\u0000Nzzz"]' '["lib/ü\u0000Cq/**", "lib/**"]'
[ "$(jq -r '.shared_files | keys[]' "$n1_D/.shode-house/scope/bd-n1a.json" | LC_ALL=C tr -d '\n' | LC_ALL=C tr '\0' '|')" = "x/$(printf '\303\274')|Czz/zz" ] && t_ok || t_fail "premise: jq -r does not write the NUL raw here, so the fixture proves nothing"
n1_p=$(printf 'src/u\314\210/a.ts')
n1_cm=$("$SCRIPT" bd-n1c "$n1_p" --main-check >/dev/null 2>&1; echo $?)
n1_c9=$("$SCRIPT" bd-n1c Dave#9 "$n1_p" >/dev/null 2>&1; echo $?)
case "$OSTYPE" in
  darwin*) assert_eq "$n1_cm:$n1_c9" "1:1" "premise: on macOS the unpoisoned manifest denies the NFD spelling (main session, Dave#9)" ;;
esac
for n1_b in bd-n1a bd-n1b bd-n1d; do
  out=$("$SCRIPT" "$n1_b" "$n1_p" --main-check 2>&1); rc=$?
  assert_rc "$rc" "$n1_cm" "$n1_b: main session $(printf '%q' "$n1_p")"
  out=$("$SCRIPT" "$n1_b" Dave#9 "$n1_p" 2>&1); rc=$?
  assert_rc "$rc" "$n1_c9" "$n1_b: Dave#9 $(printf '%q' "$n1_p")"
  case "$OSTYPE" in darwin*) assert_contains "$out" 'DENY: ' "$n1_b: Dave#9: a deny (a poisoned string that is not in the batch counts as a collision)" ;; esac
done

# The reader of the helper's records (nfc_batch_load) takes them only in the helper's order: one
# C, then R/N pairs, then E, then nothing. Any other stream is a failure (deny with the NFC
# message). Stand-in helpers that write such streams; the stand-in uname says Darwin, so this
# runs on every host.
t_start "F8-1/N-1: nfc_batch_load accepts only C, R/N pairs, E -- a second C, an R without N, an N without R, a record after E, or a stream without C -> DENY with the NFC message; the well-formed stream -> the normal verdict (0)"
write_manifest "$n1_D" "bd-n1s" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-n1s",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/a/**"], "owns": ["src/a/**"]}
  ]
}
EOF
n1_zp=$(printf 'zz/u\314\210.ts')
for n1_s in 'C%s\0E\0|0' 'C%s\0Cforged\0E\0|1' 'C%s\0Rq/x\0E\0|1' 'C%s\0Nq/x\0E\0|1' 'C%s\0E\0Rq/x\0Nq/x\0|1' 'C%s\0Rq/x\0Nq/x\0Rq/y\0Nq/y\0E\0|0' 'Rq/x\0Nq/x\0E\0|1' 'C%s\0E\0E\0|1'; do
  n1_fmt=${n1_s%|*}; n1_want=${n1_s##*|}
  n1_lib=$(mktemp -d -t scope-nb-stream.XXXXXX)
  { cat "$f6_mac_lib/_casefold.sh"; printf '_scope_nfc_batch_deny() { cat >/dev/null; printf %q "$1"; }\n' "$n1_fmt"; } > "$n1_lib/_casefold.sh"
  out=$("$(sc_tree "$n1_lib/tree" "$n1_lib/_casefold.sh")" bd-n1s "$n1_zp" --main-check 2>&1); rc=$?
  assert_rc "$rc" "$n1_want" "stream $n1_fmt"
  [ "$n1_want" = 1 ] && assert_contains "$out" "could not be Unicode-normalised (NFC)" "stream $n1_fmt: the deny is the NFC message"
  rm -rf "$n1_lib"
done
rm -rf "$n1_D"

# Chris U20 D7: the batch splits a shared_files key on newlines, as find_shared_key's line read
# does, so each part is normalised and found. Without the split, the non-ASCII second part of
# "x/y.md<LF>sk/über/**" would be missing from the batch and count as a collision for every
# non-ASCII write (over-deny).
t_start "D7: a shared_files key holding a newline (x/y.md<LF>sk/über/**) is two patterns -- main session NFD zz/u<U+0308>.ts -> 0 (not an over-deny); x/y.md -> 1; NFD sk/u<U+0308>ber/x.ts -> 1 on macOS (NFC collision with the second part), 0 elsewhere"
d7_D=$(sandbox); export SCOPECHECK_ROOT="$d7_D"
mkdir -p "$d7_D/.shode-house/scope"
printf '{"schema_version":1,"bd_id":"bd-d7","shared_files":{"x/y.md\\nsk/\\u00fcber/**":{"mode":"exclusive","owner":"Dave#1"}},"agents":[{"agent":"Dave#1","allowed_roots":["src/a/**"],"owns":["src/a/**"]}]}\n' > "$d7_D/.shode-house/scope/bd-d7.json"
out=$("$SCRIPT" bd-d7 "$(printf 'zz/u\314\210.ts')" --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "NFD zz/u<U+0308>.ts"
out=$("$SCRIPT" bd-d7 x/y.md --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "x/y.md (the first part)"
case "$OSTYPE" in darwin*) d7_want=1 ;; *) d7_want=0 ;; esac
out=$("$SCRIPT" bd-d7 "$(printf 'sk/u\314\210ber/x.ts')" --main-check 2>&1); rc=$?
assert_rc "$rc" "$d7_want" "NFD sk/u<U+0308>ber/x.ts (the second part)"
rm -rf "$d7_D"
rm -rf "$f6_lin" "$f6_mac_lib" "$f6_unk"

# F7-2 (UD U20, Sentinel r7 F7-2): the time budget of an evaluation. SCOPECHECK_BUDGET_MS can only
# shorten it (the scope guard passes what is left of its scope phase); 0 = no time left, so the
# first manifest entry compared is over budget: a deterministic stand-in for a check that ran
# out of time. Over budget -> DENY (exit 1) with a static message that never names the path.
t_start "F7-2: SCOPECHECK_BUDGET_MS=0 -> a main-session check, a subagent check (own pattern, allowed_roots, a shared key) and --amend each DENY with the static (scope-budget) message, the path never echoed, the manifest unchanged; without it the same calls give their normal verdicts"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-bud" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-bud",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/**"], "owns": ["src/a/**"]},
    {"agent": "Dave#2", "allowed_roots": ["lib/**"], "owns": []}
  ],
  "shared_files": {"docs/shared.md": {"mode": "exclusive", "owner": "Dave#1"}}
}
EOF
bud_before=$(shasum -a 256 "$D/.shode-house/scope/bd-bud.json")
for bud_case in "zz/budget-probe.ts|--main-check|0" "src/a/budget-probe.ts|Dave#1|0" "lib/budget-probe.ts|Dave#2|4" "docs/shared.md|Dave#1|0"; do
  IFS='|' read -r bud_p bud_who bud_want <<EOF
$bud_case
EOF
  if [ "$bud_who" = --main-check ]; then bud_args=(bd-bud "$bud_p" --main-check); else bud_args=(bd-bud "$bud_who" "$bud_p"); fi
  out=$(SCOPECHECK_BUDGET_MS=0 "$SCRIPT" "${bud_args[@]}" 2>&1); rc=$?
  assert_rc "$rc" 1 "budget 0: $bud_who $bud_p"
  assert_contains "$out" "(scope-budget)" "budget 0: $bud_who $bud_p: the budget reason"
  assert_not_contains "$out" "$bud_p" "budget 0: $bud_who $bud_p: the path is never echoed"
  out=$("$SCRIPT" "${bud_args[@]}" 2>&1); rc=$?
  assert_rc "$rc" "$bud_want" "control, no budget variable: $bud_who $bud_p"
done
out=$(SCOPECHECK_BUDGET_MS=0 "$SCRIPT" bd-bud Dave#2 lib/new.ts --amend 2>&1); rc=$?
assert_rc "$rc" 1 "budget 0: --amend is refused"
assert_contains "$out" "(scope-budget)" "budget 0: --amend names the budget"
assert_eq "$(shasum -a 256 "$D/.shode-house/scope/bd-bud.json")" "$bud_before" "budget 0: the manifest is unchanged"

t_start "F7-2: SCOPECHECK_BUDGET_MS can only shorten the budget -- values that are not plain decimal milliseconds ('abc', '-1', '1.5', '1e3', ' 5'), a 7-digit number, and values above 3000 are ignored; '2000' and '02000' (no octal reading) are valid shorter budgets -> the normal verdict; --snapshot and --verify run no evaluation and are not affected by a budget of 0"
for bud_v in abc -1 1.5 1e3 ' 5' 1000000 5000 2000 02000; do
  out=$(SCOPECHECK_BUDGET_MS="$bud_v" "$SCRIPT" bd-bud zz/x.ts --main-check 2>&1); rc=$?
  assert_rc "$rc" 0 "SCOPECHECK_BUDGET_MS='$bud_v': main session zz/x.ts"
done
mkdir -p "$D/src/a"; printf 'v1\n' > "$D/src/a/s.ts"
out=$(SCOPECHECK_BUDGET_MS=0 "$SCRIPT" bd-bud Dave#1 src/a/s.ts --snapshot 2>&1); rc=$?
assert_rc "$rc" 0 "budget 0: --snapshot"
out=$(SCOPECHECK_BUDGET_MS=0 "$SCRIPT" bd-bud Dave#1 src/a/s.ts --verify 2>&1); rc=$?
assert_rc "$rc" 0 "budget 0: --verify"
rm -rf "$D"

# Chris U20 N-2: the bash 3.2 clock of the budget (whole seconds) pinned on any bash. The two
# budget functions are taken from the script and run with the whole-second clock forced;
# assigning SECONDS sets the counter. A budget of B ms stops once MORE than B/1000 whole
# seconds have passed: never sooner than the budget's whole seconds, so an ordinary check is
# not cut short at the next second tick.
t_start "N-2: the whole-second budget clock (bash 3.2) -- budget 1000: 1 s passed -> not over, 2 s -> over; budget 2000: 2 s -> not over, 3 s -> over; budget 999: 1 s -> over; budget 0 -> over at once; with SCOPECHECK_BUDGET_MS unset, _sc_budget_start picks the 3000 ms default and this bash's clock"
sc_fn() { ( eval "$(sed -n -e '/^SC_MAX_MS=/p' -e '/^_sc_budget_start() {/,/^}/p' -e '/^_sc_over() {/,/^}/p' "$SCRIPT")"; eval "$1" ) 2>&1; }
assert_eq "$(sc_fn 'for c in 1000:1 1000:2 2000:2 2000:3 999:0 999:1 0:0; do _sc_clock=s; _sc_ms=${c%:*}; SECONDS=0; _sc_t0=$SECONDS; SECONDS=${c#*:}; if _sc_over; then echo "$c:over"; else echo "$c:ok"; fi; done')" \
  "1000:1:ok"$'\n'"1000:2:over"$'\n'"2000:2:ok"$'\n'"2000:3:over"$'\n'"999:0:ok"$'\n'"999:1:over"$'\n'"0:0:over" "whole-second edges"
sc_want=s; [ "${BASH_VERSINFO[0]}" -ge 5 ] && sc_want=us
assert_eq "$(sc_fn 'unset SCOPECHECK_BUDGET_MS; _sc_budget_start; echo "$_sc_ms:$_sc_clock"')" "3000:$sc_want" "default budget and clock"

# Sentinel U20 F8-2 (regression pin): bash takes SECONDS from the environment. scope-check.sh's
# bash 3.2 clock only takes the difference of two SECONDS readings, which an inherited value
# cannot move, even one that wraps past the top of its range while it counts (the 64-bit
# difference wraps back). 4000 upper-case entries cost far more than the 1000 ms budget given.
t_start "F8-2: SECONDS=9223372036854775806 or -100000 in the environment, SCOPECHECK_BUDGET_MS=1000, 4000 upper-case owns entries before the match -> main session zz/x.ts is DENIED (scope-budget), each in <= 4000 ms"
f82_D=$(sandbox); export SCOPECHECK_ROOT="$f82_D"
mkdir -p "$f82_D/.shode-house/scope"
jq -n '{schema_version:1, bd_id:"bd-f82", agents:[{agent:"Dave#3", allowed_roots:["src/d3/**"], owns:[range(4000) | "src/D3/F\(.).ts"]}]}' > "$f82_D/.shode-house/scope/bd-f82.json"
for f82_s in 9223372036854775806 -100000; do
  f82_t0=$(date -u +%s%N)
  out=$(wd 30 env SECONDS="$f82_s" SCOPECHECK_BUDGET_MS=1000 "$SCRIPT" bd-f82 zz/x.ts --main-check 2>&1); rc=$?
  f82_ms=$(( ($(date -u +%s%N) - f82_t0) / 1000000 ))
  printf '   SECONDS=%s: rc=%s %s ms\n' "$f82_s" "$rc" "$f82_ms"
  assert_rc "$rc" 1 "SECONDS=$f82_s: zz/x.ts"
  assert_contains "$out" "(scope-budget)" "SECONDS=$f82_s: the budget reason"
  [ "$f82_ms" -le 4000 ] && t_ok || t_fail "SECONDS=$f82_s: took $f82_ms ms (ceiling 4000 ms)"
done
rm -rf "$f82_D"

# Router R78 / Sentinel pre-release r2 F-1: the project root spelled in another case is still
# the project root. A byte-exact prefix strip left such a path absolute, so it matched no
# manifest pattern ("outside the project") and the main session passed the outsider policy.
t_start "F-1: an absolute path whose project-root prefix is spelled in another case is stripped (case-insensitive volume) and matched; a different directory on a case-sensitive volume is not"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-f1" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-f1",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["src/orders/**"], "owns": ["src/orders/**"]}
  ]
}
EOF
mkdir -p "$D/src/orders"
f1_phys=$(cd "$D" && pwd -P)
f1_up="${f1_phys%/*}/$(printf '%s' "${f1_phys##*/}" | tr 'a-z' 'A-Z')"
if [ -n "$f1_phys" ] && [ "$f1_up" != "$f1_phys" ] && [ -d "$f1_up" ] && [ "$f1_up" -ef "$f1_phys" ]; then
  out=$("$SCRIPT" bd-f1 "$f1_up/src/orders/x.ts" --main-check 2>&1); rc=$?
  assert_rc "$rc" 1 "main session <ROOT-IN-UPPER-CASE>/src/orders/x.ts collides with Dave#1's src/orders/**"
  assert_contains "$out" '"src/orders/x.ts"' "the path is reported project-relative"
  out=$("$SCRIPT" bd-f1 Dave#1 "$f1_up/src/orders/x.ts" 2>&1); rc=$?
  assert_rc "$rc" 0 "the owner writing through the upper-case root is granted its own file"
  out=$("$SCRIPT" bd-f1 "$f1_up/docs/x.md" --main-check 2>&1); rc=$?
  assert_rc "$rc" 0 "control: an unclaimed file through the upper-case root does not collide"
else
  t_skip "case-sensitive volume: the upper-case spelling of the sandbox is another directory here"
fi
# A case-sensitive volume keeps "Proj" and "proj" apart: the root must not be stripped from
# a directory that only folds to it.
F1CS=$(sandbox)
mkdir -p "$F1CS/proj/.shode-house/scope" "$F1CS/Proj/src/orders"
if [ ! "$F1CS/Proj" -ef "$F1CS/proj" ]; then
  cp -f "$D/.shode-house/scope/bd-f1.json" "$F1CS/proj/.shode-house/scope/bd-f1.json"
  out=$(SCOPECHECK_ROOT="$F1CS/proj" "$SCRIPT" bd-f1 Dave#1 "$F1CS/Proj/src/orders/x.ts" 2>&1); rc=$?
  assert_rc "$rc" 1 "case-sensitive volume: Proj/src/orders/x.ts is outside the project proj, never granted as src/orders/x.ts"
else
  t_skip "case-insensitive volume: Proj and proj are one directory here"
fi
rm -rf "$D" "$F1CS"

# Chris pre-release C7: the PATTERN side is folded too (a Scope Contract typed in any case).
t_start "NF2: a manifest pattern authored in upper case or with a long s (SRC/Orders/**, docs/<U+017F>pec.md) matches the lower-case path"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-pat" <<'EOF'
{
  "schema_version": 1,
  "bd_id": "bd-pat",
  "agents": [
    {"agent": "Dave#1", "allowed_roots": ["SRC/Orders/**"], "owns": ["SRC/Orders/**", "docs/ſpec.md"]}
  ]
}
EOF
out=$("$SCRIPT" bd-pat "src/orders/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "src/orders/x.ts collides with SRC/Orders/**"
out=$("$SCRIPT" bd-pat "docs/spec.md" --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "docs/spec.md collides with docs/<U+017F>pec.md"
out=$("$SCRIPT" bd-pat "src/other/x.ts" --main-check 2>&1); rc=$?
assert_rc "$rc" 0 "control: src/other/x.ts matches nothing"
rm -rf "$D"

# ---------------------------------------------------------------------------
t_start "NF2: a missing case-fold helper is a dependency error (exit 64), never a silent match miss"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
mkdir -p "$D/.shode-house/scope"
out=$("$(sc_tree "$D/tree")" bd-x "src/x.ts" --main-check 2>&1); rc=$?   # a tree copy without the helper
assert_rc "$rc" 64 "missing helper -> 64"
assert_contains "$out" "case-fold helper not found" "message names the missing helper"
rm -rf "$D"

# ---------------------------------------------------------------------------
# UD U21 (Chris U21 I-2, Sentinel U21): no variable of the environment chooses code this script
# sources, or lengthens a check. SCOPECHECK_CASEFOLD_LIB and SCOPECHECK_LOCK_LIB used to name the
# helper and the lock library (a file that ends with exit 0 then turned a deny into an allow);
# SCOPECHECK_LOCK_MAX_ATTEMPTS could raise the bounded lock retry, and lock.sh's test hooks
# (LOCK_*_SYNC) could pause a lock wait for up to 10 s, which the 5 s hook timeout turns into
# an allow. A variable may only shorten a budget (SCOPECHECK_BUDGET_MS) or add a deny; the one
# exception, SCOPECHECK_ROOT, names the project, not code (UD R86).
t_start "environment overrides (UD U21): SCOPECHECK_CASEFOLD_LIB or SCOPECHECK_LOCK_LIB naming a file that ends with exit 0 never runs -- the main session's src/a/x.ts against Dave#1's src/a/** stays 1"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-eo" <<'EOF'
{"schema_version": 1, "bd_id": "bd-eo", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/a/**"], "owns": ["src/a/**"]}]}
EOF
printf 'printf x >> "%s/ran"\nexit 0\n' "$D" > "$D/evil.sh"
out=$("$SCRIPT" bd-eo src/a/x.ts --main-check 2>&1); rc=$?
assert_rc "$rc" 1 "premise: without the variable"
for eo_v in SCOPECHECK_CASEFOLD_LIB SCOPECHECK_LOCK_LIB; do
  out=$(env "$eo_v=$D/evil.sh" "$SCRIPT" bd-eo src/a/x.ts --main-check 2>&1); rc=$?
  assert_rc "$rc" 1 "$eo_v=<a file ending in exit 0>"
  [ ! -e "$D/ran" ] && t_ok || t_fail "$eo_v: the named file was run"
  rm -f "$D/ran"
done
rm -rf "$D"

t_start "environment overrides (UD U21): with the lock held, SCOPECHECK_LOCK_MAX_ATTEMPTS=4 and every LOCK_*_SYNC test hook of lock.sh in the environment, --amend still gives up after 2 attempts (exit 64, LOCK_BUSY) and no test hook runs (no .ready file is touched)"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-eol" <<'EOF'
{"schema_version": 1, "bd_id": "bd-eol", "agents": [{"agent": "Dave#1", "allowed_roots": ["src/w2/**"], "owns": []}]}
EOF
mkdir -p "$D/.shode-house/scope/.lock-bd-eol" "$D/sync"
eol_env=(SCOPECHECK_LOCK_MAX_ATTEMPTS=4)
for eol_h in LOCK_CLASSIFY_HOLDER_SYNC LOCK_DISAMBIGUATE_SYNC LOCK_RECOVER_MARKER_SETTLE_SYNC LOCK_RECOVER_STEP1_READABLE_SYNC LOCK_RECOVER_SYNC_PREMV LOCK_RECOVER_SYNC_POSTMV; do
  eol_env+=("$eol_h=$D/sync/$eol_h"); : > "$D/sync/$eol_h.go"   # a hook that runs touches .ready and finds .go at once
done
out=$(wd 30 env "${eol_env[@]}" "$SCRIPT" bd-eol Dave#1 src/w2/x.ts --amend 2>&1); rc=$?
assert_rc "$rc" 64 "lock held: exit 64"
assert_contains "$out" "after 2 attempt(s) -- LOCK_BUSY" "the bounded retry stays at 2 attempts"
assert_eq "$(cd "$D/sync" && ls | grep -c '\.ready$')" "0" "no lock.sh test hook ran"
rm -rf "$D"

# UD R88 (Sentinel final ENV-R): ordinary variables of the environment that bash or jq read and
# that turned a deny into an allow (or a check into an error): HOME (jq sources $HOME/.jq, which
# can redefine a builtin -- here keys, so the shared_files collision was missed), FUNCNEST
# (bash >= 4.2: a low limit ended a check early, exit 0 for a collision) and TMOUT (bash 5: a
# value below one tick timed out every read of piped data, so a collision was missed). The
# script clears them at its start; on bash 3.2 the FUNCNEST and TMOUT rows are regression rows.
# UD R89: the shell options errexit, keyword, noglob and xtrace (Sentinel env XT-1: an arithmetic
# PS4 is expanded in the script's own shell before each traced command and can assign a variable
# a check reads), which SHELLOPTS can turn on, are turned off on the script's first command.
# noglob changes no CLI result: a regression row here. UD R90 (Dave xt1 XT-2): that one PS4
# expansion at the trace of the first command can also assign a variable with ${NAME:=value} or
# $((NAME=n)), and the environment can set some of them directly, so the ENV-R line also resets
# GLOBIGNORE, EXECIGNORE (bash 5: jq was not found), CDPATH, POSIXLY_CORRECT, BASH_COMPAT and
# IFS: one row per variable through PS4, and the environment rows for the ones bash takes from
# the environment; rows that no bash here turns red are regression rows. A value list entry may
# hold several NAME=value assignments separated by '|'. Never a PS4 with a command substitution
# here: it runs in every traced shell, children included, and recurses.
t_start "environment (UD R88, Sentinel final ENV-R): HOME naming a directory whose .jq redefines jq builtins, FUNCNEST=1/2/3, TMOUT=0.000001, the shell options errexit, keyword and noglob through SHELLOPTS (UD R89) and SHELLOPTS=xtrace with an arithmetic PS4 \$((tool_name=0)), \$((path=0)) or \$((rc=0,rb_rc=0)) (Sentinel env XT-1), and GLOBIGNORE, EXECIGNORE, CDPATH, POSIXLY_CORRECT, BASH_COMPAT and IFS set through such a PS4 or the environment (UD R90) never change a result -- --main-check docs/shared.md (shared_files) 1, --main-check src/a/x.ts (Dave#1's) 1, Dave#2 on src/a/x.ts 1, --main-check zz/ok.ts 0, Dave#2 on its own src/b/ok.ts 0"
D=$(sandbox); export SCOPECHECK_ROOT="$D"
write_manifest "$D" "bd-ev" <<'MF'
{"schema_version": 1, "bd_id": "bd-ev", "shared_files": {"docs/shared.md": {"strategy": "sequential", "owner_order": ["Dave#1"]}},
 "agents": [{"agent": "Dave#1", "allowed_roots": ["src/a/**"], "owns": ["src/a/**"]}, {"agent": "Dave#2", "allowed_roots": ["src/b/**"], "owns": ["src/b/**"]}]}
MF
mkdir -p "$D/jh"; printf 'def tostring: "Read";\ndef keys: [];\n' > "$D/jh/.jq"
assert_eq "$(HOME="$D/jh" jq -c -n '{a: 1} | keys')" "[]" "premise: this jq sources \$HOME/.jq, and a definition there replaces a builtin"
ev_rc() {   # <NAME=value[|NAME=value...]> <scope-check.sh args...> -> its exit code
  local ev_a; IFS='|' read -r -a ev_a <<<"$1"
  wd 30 env "${ev_a[@]}" "$SCRIPT" "${@:2}" >/dev/null 2>&1; printf '%s' "$?"
}
for ev_e in "HOME=$D/jh" FUNCNEST=1 FUNCNEST=2 FUNCNEST=3 TMOUT=0.000001 SHELLOPTS=errexit SHELLOPTS=keyword SHELLOPTS=noglob \
    'SHELLOPTS=xtrace|PS4=$((tool_name=0))' 'SHELLOPTS=xtrace|PS4=$((path=0))' 'SHELLOPTS=xtrace|PS4=$((rc=0,rb_rc=0))' \
    'SHELLOPTS=xtrace|PS4=${GLOBIGNORE:=*}' 'SHELLOPTS=xtrace|PS4=${EXECIGNORE:=*}' 'SHELLOPTS=xtrace|PS4=${CDPATH:=/}' CDPATH=/ \
    'SHELLOPTS=xtrace|PS4=${POSIXLY_CORRECT:=1}' POSIXLY_CORRECT=1 'SHELLOPTS=xtrace|PS4=${BASH_COMPAT:=31}' BASH_COMPAT=31 \
    'SHELLOPTS=xtrace|PS4=$((IFS=0))'; do
  ev_n=${ev_e%%=*}; [ "$ev_n" = HOME ] && ev_n="HOME=<.jq>" || ev_n=$ev_e
  assert_eq "$(ev_rc "$ev_e" bd-ev docs/shared.md --main-check)" 1 "$ev_n: --main-check docs/shared.md"
  assert_eq "$(ev_rc "$ev_e" bd-ev src/a/x.ts --main-check)" 1 "$ev_n: --main-check src/a/x.ts"
  assert_eq "$(ev_rc "$ev_e" bd-ev Dave#2 src/a/x.ts)" 1 "$ev_n: Dave#2 on src/a/x.ts"
  assert_eq "$(ev_rc "$ev_e" bd-ev zz/ok.ts --main-check)" 0 "$ev_n: --main-check zz/ok.ts"
  assert_eq "$(ev_rc "$ev_e" bd-ev Dave#2 src/b/ok.ts)" 0 "$ev_n: Dave#2 on src/b/ok.ts"
done
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
