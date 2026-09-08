#!/usr/bin/env bash
# tests/test-permission-check.sh -- bash-only test suite for Milestone F (bd: shode-roadmap/C-F1)
# scripts/permission-check.sh + references/security/{tool-profiles,delegation,trust-levels}.json
#
# Same harness style as tests/test-scope-check.sh (no framework; PERMCHECK_ROOT sandbox via
# mktemp -d). Wired into ci.yml as exactly ONE step (CLAUDE.md rule: this milestone may add
# no more than 1 CI step total), so the registry drift checks live HERE, not as extra steps.
#
# The drift block is the teeth of Milestone F: tool-profiles.json `tools` arrays must equal
# each agents/<name>.md `tools:` frontmatter verbatim, tool_grants must be derivable from
# those arrays, and delegation can_spawn must be non-empty iff the frontmatter has Task.
# A profile that flatters or shortchanges any agent goes red without any human reading it.
#
# Usage: bash tests/test-permission-check.sh

set -u -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/permission-check.sh"
PROFILES="$REPO_ROOT/references/security/tool-profiles.json"
DELEGATION="$REPO_ROOT/references/security/delegation.json"
TRUST="$REPO_ROOT/references/security/trust-levels.json"

PASS=0
FAIL=0
CUR_TEST=""

t_start() { CUR_TEST="$1"; printf -- '-- %s\n' "$1"; }
t_ok()    { PASS=$((PASS + 1)); printf '   ok\n'; }
t_fail()  { FAIL=$((FAIL + 1)); printf '   FAIL (%s): %s\n' "$CUR_TEST" "$1"; }

assert_rc()       { if [ "$1" -eq "$2" ]; then t_ok; else t_fail "$3 -- exit code $1, want $2"; fi; }
assert_contains() { case "$1" in *"$2"*) t_ok ;; *) t_fail "$3 -- '$1' does not contain '$2'" ;; esac; }
assert_empty()    { if [ -z "$1" ]; then t_ok; else t_fail "$2 -- expected no stdout, got '$1'"; fi; }
assert_eq()       { if [ "$1" = "$2" ]; then t_ok; else t_fail "$3 -- got '$1' want '$2'"; fi; }

SANDBOX="$(mktemp -d -t permcheck-test.XXXXXX)"
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/engaged/.shode-house" "$SANDBOX/bare"

run_pc() { # engagement active
  PERMCHECK_ROOT="$SANDBOX/engaged" bash "$SCRIPT" "$@"
}

# =============================================================================
# 0. registries are valid JSON
# =============================================================================
t_start "registries are valid JSON"
rc=0; jq empty "$PROFILES" "$DELEGATION" "$TRUST" || rc=$?
assert_rc "$rc" 0 "jq empty on the three registries"

# =============================================================================
# 1. engagement guard: no .shode-house/ -> exit 0, NO stdout (workflow-state.sh rule)
# =============================================================================
t_start "engagement guard: silent no-op without .shode-house/"
out=$(PERMCHECK_ROOT="$SANDBOX/bare" bash "$SCRIPT" developer deploy_prod); rc=$?
assert_rc "$rc" 0 "guard exit code"
assert_empty "$out" "guard stdout"

# =============================================================================
# 2. tool-grant layer
# =============================================================================
t_start "ALLOW: developer run_commands (Bash in frontmatter)"
out=$(run_pc developer run_commands); rc=$?
assert_rc "$rc" 0 "exit"
assert_contains "$out" "ALLOW" "verdict"

t_start "DENY: business-analyst run_commands (no Bash grant)"
out=$(run_pc business-analyst run_commands); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "DENY" "verdict"

t_start "DENY: developer network (no WebSearch/WebFetch grant)"
out=$(run_pc developer network); rc=$?
assert_rc "$rc" 1 "exit"

# =============================================================================
# 3. policy layer -- write_code / deploy / deploy_prod
# =============================================================================
t_start "ALLOW: developer write_code"
out=$(run_pc developer write_code); rc=$?
assert_rc "$rc" 0 "exit"

t_start "DENY: business-analyst write_code (SS 11.1 write_code: false)"
out=$(run_pc business-analyst write_code); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "least privilege" "reason names the principle"

t_start "ALLOW: devops-engineer deploy_prod (SS 11.1 deploy_prod: true)"
out=$(run_pc devops-engineer deploy_prod); rc=$?
assert_rc "$rc" 0 "exit"

t_start "DENY: developer deploy_prod (SS 11.1 deploy_prod: false)"
out=$(run_pc developer deploy_prod); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "DENY" "verdict"

t_start "DENY: sre-engineer deploy (deploy capability owner is devops-engineer only)"
out=$(run_pc sre-engineer deploy); rc=$?
assert_rc "$rc" 1 "exit"

t_start "DENY: policy true cannot override missing tool prerequisite"
# doctored profiles: give product-manager deploy_prod=true in policy -- it has no Bash
# grant, so the prerequisite check must still DENY (policy typo can never widen access)
doctored="$SANDBOX/doctored-profiles.json"
jq '.profiles["product-manager"].policy.deploy_prod = true' "$PROFILES" > "$doctored"
out=$(PERMCHECK_ROOT="$SANDBOX/engaged" PERMCHECK_PROFILES="$doctored" bash "$SCRIPT" product-manager deploy_prod); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "run_commands" "reason names the missing prerequisite"

# =============================================================================
# 4. delegation layer -- spawn
# =============================================================================
t_start "ALLOW: orchestrator spawn developer (can_spawn '*')"
out=$(run_pc orchestrator spawn developer); rc=$?
assert_rc "$rc" 0 "exit"

t_start "DENY: developer spawn code-reviewer (no Task tool -- anti recursive fan-out)"
out=$(run_pc developer spawn code-reviewer); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "fan-out" "reason names the rule"

t_start "UNKNOWN: orchestrator spawn nonexistent agent"
out=$(run_pc orchestrator spawn mechanical-helper); rc=$?
assert_rc "$rc" 2 "exit"
assert_contains "$out" "UNKNOWN" "verdict"

# =============================================================================
# 5. trust cascade -- claim_trust
# =============================================================================
t_start "ALLOW: developer claim_trust outputs/x.md:generated (equal to class)"
out=$(run_pc developer claim_trust "outputs/x.md:generated"); rc=$?
assert_rc "$rc" 0 "exit"

t_start "DENY: developer claim_trust outputs/x.md:canonical (elevation of own output)"
out=$(run_pc developer claim_trust "outputs/x.md:canonical"); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "elevate" "reason names the cascade rule"

t_start "DENY: qa-engineer claim_trust README.md:external (unclassified defaults to untrusted)"
out=$(run_pc qa-engineer claim_trust "README.md:external"); rc=$?
assert_rc "$rc" 1 "exit"

t_start "ALLOW: security-engineer claim_trust src/notes.log:untrusted (no elevation)"
out=$(run_pc security-engineer claim_trust "src/notes.log:untrusted"); rc=$?
assert_rc "$rc" 0 "exit"

t_start "UNKNOWN: bogus trust level"
out=$(run_pc developer claim_trust "outputs/x.md:sacred"); rc=$?
assert_rc "$rc" 2 "exit"

# =============================================================================
# 6. unknown agent / unknown action / usage errors
# =============================================================================
t_start "UNKNOWN: agent not in registry (exit 2, distinct from DENY)"
out=$(run_pc evil-agent deploy_prod); rc=$?
assert_rc "$rc" 2 "exit"
assert_contains "$out" "UNKNOWN" "verdict"

t_start "UNKNOWN: unsupported action"
out=$(run_pc developer teleport); rc=$?
assert_rc "$rc" 2 "exit"

t_start "usage error: missing action -> exit 64"
out=$(run_pc developer 2>/dev/null); rc=$?
assert_rc "$rc" 64 "exit"

# =============================================================================
# 7. registry drift checks -- profiles/delegation must MATCH agents/*.md frontmatter
# =============================================================================
frontmatter_tools() { # $1 = agent file -> the raw JSON array from its `tools:` line
  awk '/^---$/{c++; next} c==1 && /^tools:/ {sub(/^tools:[ \t]*/, ""); print; exit}' "$1"
}

t_start "drift: every agents/*.md has a profile and vice versa (19/19 both ways)"
agents_fs=$(for f in "$REPO_ROOT"/agents/*.md; do basename "$f" .md; done | sort)
agents_pf=$(jq -r '.profiles | keys[]' "$PROFILES" | sort)
assert_eq "$agents_pf" "$agents_fs" "profile keys vs agents/ filenames"
agents_dl=$(jq -r '.delegation | keys[]' "$DELEGATION" | sort)
assert_eq "$agents_dl" "$agents_fs" "delegation keys vs agents/ filenames"

t_start "drift: profile tools arrays equal frontmatter verbatim"
bad=""
for f in "$REPO_ROOT"/agents/*.md; do
  a=$(basename "$f" .md)
  fm=$(frontmatter_tools "$f" | jq -c 'sort')
  pf=$(jq -c --arg a "$a" '.profiles[$a].tools | sort' "$PROFILES")
  [ "$fm" = "$pf" ] || bad="$bad $a"
done
assert_eq "$bad" "" "agents whose profile tools drifted from frontmatter"

t_start "drift: tool_grants derivable from tools (Write/Edit, Bash, Task, WebSearch/WebFetch)"
bad=""
for f in "$REPO_ROOT"/agents/*.md; do
  a=$(basename "$f" .md)
  tools=$(frontmatter_tools "$f")
  for pair in 'write_files:["Write","Edit"]' 'run_commands:["Bash"]' 'spawn:["Task"]' 'network:["WebSearch","WebFetch"]'; do
    key="${pair%%:*}"; markers="${pair#*:}"
    want=$(printf '%s' "$tools" | jq --argjson m "$markers" 'any(.[]; . as $t | $m | index($t) != null)')
    got=$(jq -r --arg a "$a" --arg k "$key" '.profiles[$a].tool_grants[$k]' "$PROFILES")
    [ "$want" = "$got" ] || bad="$bad $a.$key(want=$want,got=$got)"
  done
done
assert_eq "$bad" "" "tool_grants entries that contradict frontmatter"

t_start "drift: can_spawn non-empty iff frontmatter has Task"
bad=""
for f in "$REPO_ROOT"/agents/*.md; do
  a=$(basename "$f" .md)
  has_task=$(frontmatter_tools "$f" | jq 'index("Task") != null')
  spawns=$(jq -r --arg a "$a" '.delegation[$a].can_spawn | if type == "array" then (length > 0) else true end' "$DELEGATION")
  [ "$has_task" = "$spawns" ] || bad="$bad $a(task=$has_task,can_spawn_nonempty=$spawns)"
done
assert_eq "$bad" "" "delegation entries that contradict the Task grant"

t_start "drift: policy never wider than SS 11.1 anchors (deploy_prod true only for devops-engineer)"
extra=$(jq -r '[.profiles | to_entries[] | select(.value.policy.deploy_prod == true) | .key] | join(",")' "$PROFILES")
assert_eq "$extra" "devops-engineer" "deploy_prod=true set"
extra=$(jq -r '[.profiles | to_entries[] | select(.value.policy.deploy == true) | .key] | join(",")' "$PROFILES")
assert_eq "$extra" "devops-engineer" "deploy=true set"

t_start "drift: trust levels enum matches roadmap SS 12 exactly"
lv=$(jq -r '.levels | keys_unsorted | join(",")' "$TRUST")
assert_eq "$lv" "canonical,operational,user,external,untrusted,generated" "level names + order"

# =============================================================================
printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
