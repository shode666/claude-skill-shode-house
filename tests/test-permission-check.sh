#!/usr/bin/env bash
# tests/test-permission-check.sh -- bash-only test suite for Milestone F (bd: shode-roadmap/C-F1)
# scripts/permission-check.sh + references/security/{tool-profiles,delegation,trust-levels}.json
#
# Same harness style as tests/test-scope-check.sh (no framework; PERMCHECK_ROOT sandbox via
# mktemp -d). Wired into ci.yml as exactly ONE step (milestone constraint: this milestone may add
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
t_start "UNKNOWN: orchestrator is retired (W8) -- no profile, so it is not a registered agent (exit 2, never an ALLOW)"
out=$(run_pc orchestrator spawn developer); rc=$?
assert_rc "$rc" 2 "exit"
assert_contains "$out" "UNKNOWN" "verdict"

t_start "DENY: developer spawn code-reviewer (no Task tool -- anti recursive fan-out)"
out=$(run_pc developer spawn code-reviewer); rc=$?
assert_rc "$rc" 1 "exit"
assert_contains "$out" "fan-out" "reason names the rule"
assert_contains "$out" "main session" "reason names the only dispatcher (the router in the main session)"

t_start "DENY: no registered agent may spawn (every profile x spawn developer)"
bad=""
for a in $(jq -r '.profiles | keys[]' "$PROFILES"); do
  run_pc "$a" spawn developer >/dev/null; rc=$?
  [ "$rc" -eq 1 ] || bad="$bad $a(rc=$rc)"
done
assert_eq "$bad" "" "agents that may spawn"

t_start "UNKNOWN: developer spawn nonexistent agent"
out=$(run_pc developer spawn mechanical-helper); rc=$?
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
# 5b. F-13 plugin-rooted trust classes (W8; ADR iter 5 F-13 + V5, SAC-24)
#     Shipped-directory classes (agents/ skills/ output-styles/ references/ scripts/
#     hooks/) are canonical only under the PLUGIN root (CLAUDE_PLUGIN_ROOT, resolved
#     physically). The same relative path under the project root is `untrusted`. An unset,
#     empty, relative or missing plugin root makes those paths `untrusted` -- never a
#     fallback to $PWD or to the project root.
# =============================================================================
PLUG="$SANDBOX/plugin root"          # contains a space on purpose
PRJ="$SANDBOX/engaged"
mkdir -p "$PLUG/agents" "$PLUG/references" "$PLUG/skills/workflow/x" "$PLUG/hooks" \
         "$PRJ/references" "$PRJ/agents-real" "$SANDBOX/outside"
: > "$PLUG/agents/developer.md"; : > "$PLUG/references/x.md"; : > "$PLUG/skills/workflow/x/SKILL.md"
: > "$PLUG/hooks/h.sh"; : > "$PLUG/README.md"; : > "$PRJ/references/x.md"; : > "$PRJ/notes.md"
run_pcp() { CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" "$@"; }
run_pc_noroot() { env -u CLAUDE_PLUGIN_ROOT PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" "$@"; }

t_start "F-13 ALLOW: a file under the plugin root claims canonical (plugin root set, path with a space)"
out=$(run_pcp developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 0 "exit"
for p in "$PLUG/references/x.md" "$PLUG/skills/workflow/x/SKILL.md" "$PLUG/hooks/h.sh"; do
  out=$(run_pcp developer claim_trust "$p:canonical"); rc=$?
  assert_rc "$rc" 0 "canonical under the plugin root: $p"
done

t_start "trust-class-project-shadow: references/x.md under the PROJECT root -> DENY canonical, class untrusted (relative and absolute)"
out=$(run_pcp developer claim_trust "references/x.md:canonical"); rc=$?
assert_rc "$rc" 1 "relative project path"
assert_contains "$out" '"untrusted"' "class named"
out=$(run_pcp developer claim_trust "$PRJ/references/x.md:canonical"); rc=$?
assert_rc "$rc" 1 "absolute project path"
out=$(run_pcp developer claim_trust "agents/developer.md:operational"); rc=$?
assert_rc "$rc" 1 "a project agents/ file cannot claim operational either"
out=$(run_pcp developer claim_trust "references/x.md:untrusted"); rc=$?
assert_rc "$rc" 0 "no elevation is fine"

t_start "plugin-root-unset: CLAUDE_PLUGIN_ROOT unset -> even a real plugin file is untrusted (no \$PWD fallback)"
out=$(run_pc_noroot developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "unset root"
assert_contains "$out" '"untrusted"' "class named"
out=$(cd "$PLUG" && env -u CLAUDE_PLUGIN_ROOT PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "unset root, cwd = plugin root"

t_start "plugin-root-unset: empty, relative and nonexistent CLAUDE_PLUGIN_ROOT -> untrusted"
out=$(CLAUDE_PLUGIN_ROOT="" PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "empty root"
out=$(cd "$SANDBOX" && CLAUDE_PLUGIN_ROOT="plugin root" PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "relative root (would resolve against \$PWD)"
out=$(CLAUDE_PLUGIN_ROOT="$SANDBOX/no-such-root" PERMCHECK_ROOT="$PRJ" bash "$SCRIPT" developer claim_trust "$PLUG/agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "nonexistent root"

t_start "plugin-root-unset: project root == plugin root and the root unset -> agents/ is untrusted, not canonical"
mkdir -p "$PLUG/.shode-house"
out=$(env -u CLAUDE_PLUGIN_ROOT PERMCHECK_ROOT="$PLUG" bash "$SCRIPT" developer claim_trust "agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 1 "no fallback to the project root"
out=$(CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PLUG" bash "$SCRIPT" developer claim_trust "agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 0 "with the root set, the plugin's own checkout is canonical"
rm -rf "$PLUG/.shode-house"

t_start "F-13 traversal: a path that normalises out of the plugin root is not canonical"
out=$(run_pcp developer claim_trust "$PLUG/agents/../../outside/x.md:canonical"); rc=$?
assert_rc "$rc" 1 "absolute traversal"
out=$(run_pcp developer claim_trust "agents/../../../etc/passwd:canonical"); rc=$?
assert_rc "$rc" 1 "relative traversal"
out=$(run_pc developer claim_trust "agents/../outputs/x.md:canonical"); rc=$?
assert_rc "$rc" 1 "relative traversal into outputs/ -> generated"
out=$(run_pcp developer claim_trust "$PLUG/agents/no-such-dir/../../../engaged/notes.md:canonical"); rc=$?
assert_rc "$rc" 1 "traversal through a nonexistent component (physical resolution alone cannot see it)"

t_start "F-13 symlink leaf inside the plugin root pointing at a project file -> not canonical"
ln -sf "$PRJ/notes.md" "$PLUG/references/link.md"
out=$(run_pcp developer claim_trust "$PLUG/references/link.md:canonical"); rc=$?
assert_rc "$rc" 1 "leaf symlink"
rm -f "$PLUG/references/link.md"

t_start "F-13 symlinked ancestor: a project dir that is a symlink INTO the plugin root resolves physically -> canonical"
ln -s "$PLUG/agents" "$PRJ/agents"
out=$(run_pcp developer claim_trust "agents/developer.md:canonical"); rc=$?
assert_rc "$rc" 0 "physical resolution"
rm -f "$PRJ/agents"

t_start "F-13 a plugin-root file outside every shipped class -> untrusted"
out=$(run_pcp developer claim_trust "$PLUG/README.md:canonical"); rc=$?
assert_rc "$rc" 1 "unclassified plugin file"

t_start "F-13 project-rooted classes unchanged: outputs/ generated, .shode-house/ operational, CLAUDE.md canonical"
out=$(run_pcp developer claim_trust "outputs/x.md:generated"); rc=$?
assert_rc "$rc" 0 "outputs"
out=$(run_pcp developer claim_trust "outputs/x.md:external"); rc=$?
assert_rc "$rc" 1 "outputs cannot be raised"
out=$(run_pcp developer claim_trust ".shode-house/notes:operational"); rc=$?
assert_rc "$rc" 0 ".shode-house"
out=$(run_pcp developer claim_trust "CLAUDE.md:canonical"); rc=$?
assert_rc "$rc" 0 "project CLAUDE.md"

t_start "F-13 registry: every path class names its root, and the shipped directories are plugin-rooted"
bad=$(jq -r '[.path_classes[] | select((.root // "") as $r | ($r != "plugin" and $r != "project"))] | length' "$TRUST")
assert_eq "$bad" "0" "classes without a valid root"
pr=$(jq -r '[.path_classes[] | select(.root == "plugin") | .pattern] | sort | join(",")' "$TRUST")
assert_eq "$pr" "agents/*,hooks/*,output-styles/*,references/*,scripts/*,skills/*" "plugin-rooted classes"
pc=$(jq -r '[.path_classes[] | select(.trust == "canonical" and .root == "project") | .pattern] | join(",")' "$TRUST")
assert_eq "$pc" "CLAUDE.md" "the only project-rooted canonical class"

t_start "F-13 mutation: a class without a root fails closed (exit 64), never defaults to the project root"
doctored_trust="$SANDBOX/doctored-trust.json"
jq '(.path_classes[] | select(.pattern == "references/*")) |= del(.root)' "$TRUST" > "$doctored_trust"
out=$(CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PRJ" PERMCHECK_TRUST="$doctored_trust" bash "$SCRIPT" developer claim_trust "references/x.md:canonical" 2>&1); rc=$?
assert_rc "$rc" 64 "missing root"

t_start "F-13 corrupt registry is detected up front (Chris W8 F2): a rootless class appended AFTER every real class -> exit 64 even for a path an earlier class matches"
doctored_trust2="$SANDBOX/doctored-trust-2.json"
jq '.path_classes += [{"pattern":"zz/*","trust":"canonical"}]' "$TRUST" > "$doctored_trust2"
out=$(CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PRJ" PERMCHECK_TRUST="$doctored_trust2" bash "$SCRIPT" developer claim_trust "outputs/a.md:generated" 2>&1); rc=$?
assert_rc "$rc" 64 "earlier-matching path, corrupt later class"
assert_contains "$out" "corrupt registry" "names the cause"
jq '.path_classes += [{"pattern":"zz/*","trust":"canonical","root":"elsewhere"}]' "$TRUST" > "$doctored_trust2"
out=$(CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PRJ" PERMCHECK_TRUST="$doctored_trust2" bash "$SCRIPT" developer claim_trust "outputs/a.md:generated" 2>&1); rc=$?
assert_rc "$rc" 64 "an invalid root value"
jq '.path_classes = {}' "$TRUST" > "$doctored_trust2"
out=$(CLAUDE_PLUGIN_ROOT="$PLUG" PERMCHECK_ROOT="$PRJ" PERMCHECK_TRUST="$doctored_trust2" bash "$SCRIPT" developer claim_trust "outputs/a.md:generated" 2>&1); rc=$?
assert_rc "$rc" 64 "path_classes not an array"
out=$(run_pcp developer claim_trust "outputs/a.md:generated"); rc=$?
assert_rc "$rc" 0 "control: the shipped registry passes the up-front check"

t_start "lexnorm restores the caller's noglob state (Chris W8 S3)"
out=$(bash -c 'eval "$(sed -n "/^lexnorm() {/,/^}/p" "$1")"; set -f; lexnorm "/a/./b/../c" >/dev/null; case $- in *f*) echo kept ;; *) echo lost ;; esac; set +f; lexnorm "/a" >/dev/null; case $- in *f*) echo set ;; *) echo off ;; esac' _ "$SCRIPT")
assert_eq "$out" "kept"$'\n'"off" "set -f kept when the caller had it, globbing left on otherwise"

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

# Retired agent types (W8, ADR iter 5 7: `orchestrator` out of profiles and registry; the
# router is the main session's output style and is not a registered agent). The 4.0.0 switch
# (W10b) deleted their files; they are excluded from the drift comparison below and must have
# no profile, no delegation entry and no agents/<name>.md file.
RETIRED_AGENTS="orchestrator"
is_retired() { case " $RETIRED_AGENTS " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

t_start "retired agents have no agents/<name>.md file (Chris W8 F4: the exclusion cannot outlive the file)"
bad=""
for a in $RETIRED_AGENTS; do
  [ -e "$REPO_ROOT/agents/$a.md" ] && bad="$bad $a"
done
assert_eq "$bad" "" "retired agent file still present"

t_start "retired agents have no profile and no delegation entry"
bad=""
for a in $RETIRED_AGENTS; do
  jq -e --arg a "$a" '.profiles | has($a)' "$PROFILES" >/dev/null && bad="$bad profile:$a"
  jq -e --arg a "$a" '.delegation | has($a)' "$DELEGATION" >/dev/null && bad="$bad delegation:$a"
done
assert_eq "$bad" "" "retired agents still registered"

t_start "drift: every live agents/*.md has a profile and vice versa (18/18 both ways)"
agents_fs=$(for f in "$REPO_ROOT"/agents/*.md; do a=$(basename "$f" .md); is_retired "$a" || printf '%s\n' "$a"; done | sort)
assert_eq "$(printf '%s\n' "$agents_fs" | grep -c .)" "18" "live agent count"
agents_pf=$(jq -r '.profiles | keys[]' "$PROFILES" | sort)
assert_eq "$agents_pf" "$agents_fs" "profile keys vs agents/ filenames"
agents_dl=$(jq -r '.delegation | keys[]' "$DELEGATION" | sort)
assert_eq "$agents_dl" "$agents_fs" "delegation keys vs agents/ filenames"

t_start "drift: profile tools arrays equal frontmatter verbatim"
bad=""
for f in "$REPO_ROOT"/agents/*.md; do
  a=$(basename "$f" .md)
  is_retired "$a" && continue
  fm=$(frontmatter_tools "$f" | jq -c 'sort')
  pf=$(jq -c --arg a "$a" '.profiles[$a].tools | sort' "$PROFILES")
  [ "$fm" = "$pf" ] || bad="$bad $a"
done
assert_eq "$bad" "" "agents whose profile tools drifted from frontmatter"

t_start "drift: tool_grants derivable from tools (Write/Edit, Bash, Task, WebSearch/WebFetch)"
bad=""
for f in "$REPO_ROOT"/agents/*.md; do
  a=$(basename "$f" .md)
  is_retired "$a" && continue
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
  is_retired "$a" && continue
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
