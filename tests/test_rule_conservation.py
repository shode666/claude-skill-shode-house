"""Negative tests for scripts/rule-conservation.py (v3.17 FR-G-1 / ADR-9.1).

Every case builds a throwaway git repo and runs the real CLI in it, so the git plumbing
(--base, --no-renames, deleted paths) is exercised, not mocked. stdlib + git only.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rule-conservation.py"

RULE = "Reviewers never approve a deliverable they produced themselves during this release cycle."
ANCHOR = "never approve a deliverable"
FILLER = "Collect the symptom timeline before proposing any hypothesis about the outage."
SKILL = "skills/workflow/alpha/SKILL.md"
OTHER = "skills/ops/beta/SKILL.md"
REF = "skills/workflow/alpha/detail.md"
LAZY = "<!-- lazy-load-contract -->\nLOAD: skills/workflow/alpha/detail.md\n\n"

# Gate switches of the caller (`SHODE_REQUIRE_V4=1 make validate`, CI) must not reach a fixture repo: the script
# reads SHODE_REQUIRE_V4 itself; RULE_BASE / CI / GITHUB_ACTIONS steer the gate around it. GIT_* variables that
# locate a repository (set by git when a hook runs) would point the fixture's git at the caller's repository.
# Config isolation the caller chose (GIT_CONFIG_GLOBAL / GIT_CONFIG_NOSYSTEM, HOME, XDG_CONFIG_HOME) is kept.
GATE_ENV = ("SHODE_REQUIRE_V4", "RULE_BASE", "CI", "GITHUB_ACTIONS")
GIT_REPO_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX")


def fixture_env():
    """The caller's environment minus every gate switch and repository-locating git variable (hermetic fixture)."""
    return {k: v for k, v in os.environ.items() if k not in GATE_ENV + GIT_REPO_ENV}


def doc(*lines, tools=None, raw_fm=None):
    """raw_fm: frontmatter lines written as given (no JSON encoding), e.g. a YAML plain-scalar `tools:` line."""
    fm = raw_fm if raw_fm is not None else f"tools: {json.dumps(tools)}\n" if tools is not None else ""
    return "---\nname: x\ndescription: metadata is not a rule\n" + fm + "---\n# Title\n\n" + "\n".join(lines) + "\n"


class Repo:
    def __init__(self, files):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.git("init", "-q")
        self.write(files)
        self.base = self.commit("base")

    def close(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ("git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false") + args,
            cwd=self.root, check=True, capture_output=True, text=True, env=fixture_env()).stdout.strip()

    def write(self, files):
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run(self, *args):
        r = subprocess.run((sys.executable, str(SCRIPT)) + args, cwd=self.root, capture_output=True, text=True,
                           env=fixture_env())
        return r.returncode, r.stdout + r.stderr


class RuleConservationTest(unittest.TestCase):
    def repo(self, files):
        repo = Repo(files)
        self.addCleanup(repo.close)
        return repo

    def assert_lost(self, result, *needles):
        rc, out = result
        self.assertEqual(1, rc, out)
        self.assertNotIn("Traceback", out)
        for needle in needles:
            self.assertIn(needle, out)

    def assert_ok(self, result):
        rc, out = result
        self.assertEqual(0, rc, out)
        self.assertIn("  ok ", out)

    # AC1 -- --base: a committed loss must still be seen (B1)
    def test_committed_loss_needs_base(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), SKILL)            # dirty tree, default HEAD
        repo.commit("drop rule")
        rc, out = repo.run()                            # clean tree vs HEAD: nothing to compare
        self.assertEqual(0, rc, out)
        self.assertIn("no skill/agent file changed", out)
        self.assert_lost(repo.run("--base", repo.base), SKILL, "deliverable")

    def test_unknown_base_fails_closed(self):
        repo = self.repo({SKILL: doc(RULE)})
        rc, out = repo.run("--base", "no-such-ref")
        self.assertEqual(2, rc, out)
        self.assertNotIn("Traceback", out)

    # AC1 / Q2 -- rename detection must not hide the old path
    def test_renamed_skill_is_checked(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.git("mv", "skills/workflow/alpha", "skills/deprecated")
        repo.commit("git mv to deprecated")
        self.assertEqual("skills/deprecated/SKILL.md",          # proof that plain diff hides the old path
                         repo.git("diff", "--name-only", repo.base))
        self.assert_lost(repo.run("--base", repo.base), SKILL, "[file deleted]")

    def test_deprecated_and_in_progress_cannot_hold_a_rule(self):
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER), "skills/deprecated/old/SKILL.md": doc(RULE),
                    "skills/in-progress/new/SKILL.md": doc(RULE), "README.md": RULE})
        self.assert_lost(repo.run(), SKILL)

    # AC2 -- deleted file: no crash, rules must live elsewhere (B2)
    def test_deleted_skill_without_destination(self):
        repo = self.repo({SKILL: doc(RULE, FILLER), OTHER: doc(FILLER)})
        (repo.root / SKILL).unlink()
        repo.commit("delete skill")
        self.assert_lost(repo.run("--base", repo.base), SKILL, "[file deleted]", "deliverable")

    def test_deleted_skill_with_rules_merged_elsewhere_passes(self):
        repo = self.repo({SKILL: doc(RULE), OTHER: doc(FILLER)})
        (repo.root / SKILL).unlink()
        repo.write({OTHER: doc(FILLER, "- " + RULE)})
        repo.commit("merge alpha into beta")
        self.assert_ok(repo.run("--base", repo.base))

    # AC3 -- every shipped bucket, reference files and agents (old scope = discipline SKILL.md only)
    def test_all_buckets_references_and_agents_are_in_scope(self):
        paths = [f"skills/{b}/s/SKILL.md" for b in ("workflow", "ops", "ui", "style", "discipline")]
        paths += ["skills/ops/s/runbook.md", "agents/developer.md"]
        for path in paths:
            with self.subTest(path=path):
                repo = self.repo({path: doc(RULE, FILLER)})
                repo.write({path: doc(FILLER)})
                self.assert_lost(repo.run(), path)

    def test_unshipped_and_non_rule_files_are_out_of_scope(self):
        files = {"skills/deprecated/s/SKILL.md": doc(RULE), "skills/in-progress/s/SKILL.md": doc(RULE),
                 "docs/notes.md": doc(RULE)}
        repo = self.repo(files)
        repo.write({path: doc(FILLER) for path in files})
        self.assert_ok(repo.run())

    # AC4 / S7 -- protection does not come from the marker
    def test_unmarked_english_rule_is_protected(self):
        self.assertNotIn("🔴", RULE)
        self.assertNotIn("ห้าม", RULE)
        repo = self.repo({SKILL: doc(RULE, FILLER)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), "deliverable")

    def test_marker_removed_then_line_deleted(self):
        marked = "- 🔴 ห้าม approve deliverable ของตัวเอง reviewer ต้องเป็นคนอื่นเสมอ independent"
        repo = self.repo({SKILL: doc(marked, FILLER)})
        repo.write({SKILL: doc(marked.replace("🔴 ห้าม", "do not"), FILLER)})
        repo.commit("downgrade marker")
        self.assert_ok(repo.run("--base", repo.base))   # rewording alone keeps the rule
        repo.write({SKILL: doc(FILLER)})
        repo.commit("delete the now-unmarked line")
        self.assert_lost(repo.run("--base", repo.base), SKILL)

    def test_noise_bounds(self):
        """Headings, quotes, table rules, short lines, unmarked fenced examples and pointers are not rules."""
        noise = ["## A heading that is long enough to look like a rule line", "> quoted commentary that is long enough to count",
                 "|------|------|------|------|------|", "short line", "```", "example output inside a fenced block only",
                 "```", "See the detailed procedure in skills/workflow/alpha/detail.md before acting"]
        repo = self.repo({SKILL: doc(FILLER, *noise)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_ok(repo.run())

    def test_marked_line_inside_fence_is_still_a_rule(self):
        repo = self.repo({SKILL: doc(FILLER, "```", "🔴 ห้าม deploy production without rollback plan approved", "```")})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), "rollback")

    # AC4 / S3 -- tier: a root-only rule may not sink into a lazy reference
    def tier_repo(self, enforcement_map=True):
        files = {SKILL: doc(RULE, FILLER), REF: LAZY + "# Detail\n"}
        if enforcement_map:
            files[".enforcement-map.json"] = json.dumps({"version": 1, "rules": [
                {"id": "reviewer-independence", "root_only": True, "anchor": ANCHOR, "source_of_truth": SKILL},
                {"id": "unrelated", "anchor": "symptom timeline", "source_of_truth": SKILL}]})
        repo = self.repo(files)
        repo.write({SKILL: doc(FILLER), REF: LAZY + "# Detail\n\n" + RULE + "\n"})
        repo.commit("move rule root -> lazy reference")
        return repo

    def test_root_only_rule_moved_to_lazy_reference_fails(self):
        repo = self.tier_repo()
        self.assert_lost(repo.run("--base", repo.base), "root tier", ANCHOR)

    def test_root_only_rule_moved_to_another_root_passes(self):
        repo = self.tier_repo()
        repo.write({"agents/reviewer.md": doc(RULE)})
        self.assert_ok(repo.run("--base", repo.base))

    def test_skill_md_carrying_load_block_is_not_root_tier(self):
        repo = self.tier_repo()
        repo.write({OTHER: LAZY + RULE + "\n"})
        self.assert_lost(repo.run("--base", repo.base), "root tier")

    def test_absent_root_only_list_is_not_an_error(self):
        repo = self.tier_repo(enforcement_map=False)
        self.assert_ok(repo.run("--base", repo.base))   # ordinary rule: a reference may hold it
        self.assert_lost(repo.run("--base", repo.base, "--root-only", ANCHOR), "root tier")

    # .rule-migrations.json semantics preserved
    def migration_repo(self, fragment):
        new = "Producers hand the artifact to an independent gatekeeper who alone signs the verdict."
        repo = self.repo({SKILL: doc(RULE, FILLER), ".rule-migrations.json": json.dumps({"migrations": [{
            "source": SKILL, "old_fragment": fragment, "replacement": SKILL,
            "requires": ["independent gatekeeper"], "reason": "reworded"}]})})
        repo.write({SKILL: doc(new, FILLER)})
        return repo

    def test_exact_migration_exempts_the_fragment(self):
        rc, out = self.migration_repo(RULE).run()
        self.assertEqual(0, rc, out)
        self.assertIn("migrated " + SKILL, out)

    def test_inexact_migration_does_not_exempt(self):
        self.assert_lost(self.migration_repo(RULE[:-1]).run(), "deliverable")

    def test_broken_migration_target_exits_2_with_message(self):
        repo = self.migration_repo(RULE)
        entry = json.loads((repo.root / ".rule-migrations.json").read_text())
        entry["migrations"][0]["replacement"] = "skills/workflow/gone/SKILL.md"
        repo.write({".rule-migrations.json": json.dumps(entry)})
        rc, out = repo.run()
        self.assertEqual(2, rc, out)
        self.assertNotIn("Traceback", out)
        self.assertIn(".rule-migrations.json invalid", out)
        self.assertIn("skills/workflow/gone/SKILL.md", out)
        self.assertIn(SKILL, out)

    def test_migration_never_waives_root_tier(self):
        repo = self.migration_repo(RULE)
        self.assert_lost(repo.run("--root-only", ANCHOR), "root tier")

    # v4 ADR §5.10 / A5 (W1): output styles -- wired now, required from 4.0.0 by data (plugin.json major)
    STYLE = "output-styles/router.md"

    def style_repo(self, version=None):
        files = {self.STYLE: doc(RULE, FILLER)}
        if version:
            files[".claude-plugin/plugin.json"] = json.dumps({"name": "p", "version": version})
        repo = self.repo(files)
        repo.write({self.STYLE: doc(FILLER)})
        return repo

    def test_style_rule_loss_is_wired_but_not_required_in_3x(self):
        repo = self.style_repo("3.17.2")
        self.assert_ok(repo.run())                                  # 3.x: style not in the checked scope
        self.assert_lost(repo.run("--with-styles"), self.STYLE)     # wired: the flag turns it on

    def test_style_rule_loss_is_required_from_4_0_0(self):
        self.assert_lost(self.style_repo("4.0.0").run(), self.STYLE, "deliverable")

    def test_style_scope_env_switch(self):
        repo = self.style_repo("3.17.2")
        r = subprocess.run((sys.executable, str(SCRIPT)), cwd=repo.root, capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "SHODE_REQUIRE_V4": "1"})
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn(self.STYLE, r.stdout)

    def agent_to_style_repo(self, tools):
        agent = "agents/router-old.md"
        repo = self.repo({agent: doc(RULE, FILLER, tools=tools), ".enforcement-map.json": json.dumps({
            "version": 1, "rules": [{"id": "reviewer-independence", "root_only": True, "anchor": ANCHOR,
                                     "source_of_truth": agent}]})})
        (repo.root / agent).unlink()
        repo.write({self.STYLE: doc("- " + RULE, FILLER)})
        repo.commit("agent retired, rule moved to the always-on style")
        return repo

    def test_root_only_rule_moved_from_main_session_agent_to_style_stays_root_tier(self):
        for spawn in ("Task", "Agent"):     # main session = the base version's tools: holds Task or Agent
            with self.subTest(spawn=spawn):
                self.assert_ok(self.agent_to_style_repo(["Read", spawn, "Skill"]).run("--base", "HEAD~1"))

    def test_root_only_rule_moved_from_subagent_to_style_is_red(self):
        """Chris W1 M1: a style reaches the main session only -- a subagent rule parked there left its audience."""
        for tools in (["Read", "Bash", "Skill"], None):    # no Task/Agent, or no tools: line at all
            with self.subTest(tools=tools):
                self.assert_lost(self.agent_to_style_repo(tools).run("--base", "HEAD~1"),
                                 "root tier", "styles and Task/Agent agents reach the main session only", ANCHOR)

    def test_real_bias_chris_rule_moved_into_the_style_is_red(self):
        """Chris W1 M1 mutation on the real files: code-reviewer's no-PASS-without-evidence line -> the style."""
        emap = json.loads((ROOT / ".enforcement-map.json").read_text())
        rule = next(r for r in emap["rules"] if r["id"] == "bias-chris-no-pass-without-evidence")
        agent = rule["source_of_truth"]
        style = sorted((ROOT / "output-styles").glob("*.md"))[0].relative_to(ROOT).as_posix()
        body, style_text = (ROOT / agent).read_text(), (ROOT / style).read_text()
        line = next(l for l in body.splitlines() if rule["anchor"] in l)
        repo = self.repo({agent: body, style: style_text, ".enforcement-map.json": json.dumps(emap)})
        repo.write({agent: body.replace(line + "\n", ""), style: style_text + "\n" + line + "\n"})
        self.assert_lost(repo.run("--with-styles"), agent, "root tier", rule["anchor"])
        repo.write({agent: body.replace(line + "\n", "") + "\n" + line.replace("- ", "* ", 1) + "\n",
                    style: style_text})
        self.assert_ok(repo.run("--with-styles"))    # control: kept in the body (reformatted) = conserved

    def subagent_to_router_repo(self, router_tools, raw_fm=None):
        """A subagent's root-only rule moved into an agent body whose CURRENT tools: decide its audience."""
        sub, router = "agents/reviewer.md", "agents/router.md"
        repo = self.repo({sub: doc(RULE, FILLER, tools=["Read", "Skill"]),
                          router: doc(FILLER, tools=router_tools, raw_fm=raw_fm), ".enforcement-map.json": json.dumps({
                              "version": 1, "rules": [{"id": "reviewer-independence", "root_only": True,
                                                       "anchor": ANCHOR, "source_of_truth": sub}]})})
        repo.write({sub: doc(FILLER, tools=["Read", "Skill"]),
                    router: doc(FILLER, "- " + RULE, tools=router_tools, raw_fm=raw_fm)})
        return repo

    def test_root_only_rule_moved_from_subagent_into_main_session_agent_is_red(self):
        """Chris W1 r2 R2-1: an agent whose tools: hold Task/Agent runs as the main session, like the style."""
        for spawn in ("Task", "Agent"):
            with self.subTest(spawn=spawn):
                self.assert_lost(self.subagent_to_router_repo(["Read", spawn, "Skill"]).run(),
                                 "agents/reviewer.md", "root tier", "subagent-visible SKILL.md/agent", "styles and Task/Agent agents reach the main session only", ANCHOR)

    def test_root_only_rule_moved_into_agent_with_unreadable_tools_is_red(self):
        """Fail closed on the credit side: a tools: line that is not a JSON list earns no subagent credit."""
        self.assert_lost(self.subagent_to_router_repo("Read, Task").run(), "root tier", ANCHOR)

    def test_root_only_rule_moved_into_agent_with_raw_comma_tools_line_is_red(self):
        """Chris W1 follow-up C-1: the YAML plain-scalar line `tools: Read, Task` (written raw, not JSON-encoded)
        reaches the unreadable branch and earns no subagent credit."""
        for raw in ("tools: Read, Task\n", "tools: Read, Bash, Skill\n"):
            with self.subTest(raw=raw):
                self.assert_lost(self.subagent_to_router_repo(None, raw_fm=raw).run(), "root tier", ANCHOR)

    def test_duplicate_or_variant_tools_key_earns_no_credit(self):
        """Sentinel W1 follow-up F5: a second tools key in any spelling, or a variant spelling, is unreadable."""
        for raw in ('tools: ["Read", "Skill"]\ntools: ["Read", "Task", "Skill"]\n',
                    'tools: ["Read", "Skill"]\n"tools": ["Task"]\n', 'tools: ["Read", "Skill"]\n  tools: ["Task"]\n',
                    'tools : ["Read", "Skill"]\n', '"tools": ["Read", "Skill"]\n', '  tools: ["Read", "Skill"]\n'):
            with self.subTest(raw=raw):
                self.assert_lost(self.subagent_to_router_repo(None, raw_fm=raw).run(), "root tier", ANCHOR)
        self.assert_ok(self.subagent_to_router_repo(None, raw_fm='tools: ["Read", "Skill"]\n').run())   # control

    def test_parameterised_spawn_tool_is_a_spawn_tool(self):
        """F5: `Agent(worker)` / `Task(*)` spawn like Task/Agent, so the agent is a main-session body."""
        for spawn in ("Agent(worker)", "Task(*)", "Task(code-reviewer)"):
            with self.subTest(spawn=spawn):
                self.assert_lost(self.subagent_to_router_repo(["Read", spawn, "Skill"]).run(), "root tier", ANCHOR)

    def test_spawn_tools_is_the_one_parser_of_both_callers(self):
        """C-3: main_session() and subagent_visible() read tools: through spawn_tools(); unreadable fails closed
        in each caller's direction (no main-session credit, no subagent credit)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc_c3", SCRIPT)
        rc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rc)
        head = "---\nname: x\n"
        cases = {"no tools": (head + "---\n", rc.NO_TOOLS, False, True),
                 "subagent": (head + 'tools: ["Read"]\n---\n', set(), False, True),
                 "router": (head + 'tools: ["Read", "Task"]\n---\n', {"Task"}, True, False),
                 "param": (head + 'tools: ["Agent(worker)"]\n---\n', {"Agent(worker)"}, True, False),
                 "comma": (head + "tools: Read, Task\n---\n", None, False, False),
                 "duplicate": (head + 'tools: ["Read"]\ntools: ["Task"]\n---\n', None, False, False),
                 "variant": (head + 'tools : ["Read"]\n---\n', None, False, False),
                 "non-string": (head + 'tools: ["Read", 1]\n---\n', None, False, False),
                 "no frontmatter": ("# x\n", None, False, False)}
        for why, (text, spawn, main, sub) in cases.items():
            with self.subTest(why=why):
                self.assertEqual(spawn, rc.spawn_tools(text))
                self.assertEqual(main, rc.main_session("agents/a.md", text))
                self.assertEqual(sub, rc.subagent_visible("agents/a.md", text))

    def test_root_only_rule_moved_between_subagents_stays_conserved(self):
        self.assert_ok(self.subagent_to_router_repo(["Read", "Bash", "Skill"]).run())   # control
        self.assert_ok(self.subagent_to_router_repo(None).run())                        # no tools: line

    def test_real_bias_chris_rule_moved_into_the_router_agent_is_red(self):
        """Chris W1 r2 mutation r2 on the real files: code-reviewer line -> the main-session router body."""
        emap = json.loads((ROOT / ".enforcement-map.json").read_text())
        rule = next(r for r in emap["rules"] if r["id"] == "bias-chris-no-pass-without-evidence")
        agent = rule["source_of_truth"]
        body = (ROOT / agent).read_text()
        line = next(l for l in body.splitlines() if rule["anchor"] in l)
        router = doc(FILLER, tools=["Read", "Write", "Edit", "Glob", "Grep", "Task", "Bash", "Skill"])
        repo = self.repo({agent: body, "agents/orchestrator.md": router, ".enforcement-map.json": json.dumps(emap)})
        repo.write({agent: body.replace(line + "\n", ""), "agents/orchestrator.md": router + "\n" + line + "\n"})
        self.assert_lost(repo.run(), agent, "root tier", rule["anchor"])

    def test_root_only_rule_without_anchor_exits_2_with_message(self):
        """Chris W1 r2 L-4: a null/missing/blank anchor is a map error (rc 2), never a traceback or a silent skip."""
        for bad in ({"anchor": None}, {}, {"anchor": "  "}, {"anchor": 7}):
            with self.subTest(entry=bad):
                repo = self.tier_repo()
                emap = json.loads((repo.root / ".enforcement-map.json").read_text())
                emap["rules"].append(dict({"id": "ghost-rule", "root_only": True, "source_of_truth": SKILL}, **bad))
                repo.write({".enforcement-map.json": json.dumps(emap)})
                rc, out = repo.run("--base", repo.base)
                self.assertEqual(2, rc, out)
                self.assertNotIn("Traceback", out)
                self.assertIn("ghost-rule", out)

    def test_floor_marker_lines_are_not_rules(self):
        markers = ["<!-- floor:begin -->", "<!-- floor:end -->", "<!-- floor:style:begin -->", "<!-- floor:style:end -->"]
        repo = self.repo({SKILL: doc(FILLER, *markers)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_ok(repo.run())

    def test_marker_grammar_is_floor_py_grammar(self):
        """The skip list is exactly scripts/floor.py's markers (W4), nothing broader."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("rc", SCRIPT)
        rc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rc)
        floor = ROOT / "scripts/floor.py"
        if floor.is_file():
            spec = importlib.util.spec_from_file_location("floor", floor)
            fl = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fl)
            for kind in fl.KINDS:
                self.assertTrue(rc.MARKER.match(kind.begin) and rc.MARKER.match(kind.end), kind)
        for not_marker in ("<!-- floor:begin generated -->", "  <!-- floor:end -->x", "<!-- Why: realworld pain -->"):
            self.assertFalse(rc.MARKER.match(not_marker.strip()), not_marker)

    def test_rule_inside_other_html_comment_is_still_a_rule(self):
        """Chris W1 M2: a body is raw markdown, so any comment other than a floor marker is live prompt text."""
        commented = "<!-- 🔴 Never run git push --force on main without explicit user confirmation -->"
        repo = self.repo({SKILL: doc(commented, FILLER)})
        repo.write({SKILL: doc(FILLER)})
        self.assert_lost(repo.run(), SKILL, "push --force")

    def test_simulate_delete_of_a_bad_path_exits_2(self):
        """Chris W1 Low 5: a typo, an absolute path or an out-of-scope file is an error, not '0 fragment(s)'."""
        repo = self.repo({SKILL: doc(RULE, FILLER), self.STYLE: doc(FILLER)})
        for bad in ("skills/workflow/alpah/SKILL.md", str(repo.root / SKILL), "../" + SKILL, "docs/x.md",
                    self.STYLE):                                     # a style without --with-styles
            with self.subTest(path=bad):
                rc, out = repo.run("--simulate-delete", bad, "--dry-run")
                self.assertEqual(2, rc, out)
                self.assertIn("--simulate-delete", out)
                self.assertNotIn("Traceback", out)
        rc, out = repo.run("--with-styles", "--simulate-delete", self.STYLE, "--dry-run")
        self.assertEqual(0, rc, out)

    def test_simulated_delete_dry_run_counts_and_exits_zero(self):
        repo = self.repo({SKILL: doc(RULE, FILLER), OTHER: doc("- " + FILLER)})
        rc, out = repo.run("--simulate-delete", SKILL, "--dry-run")
        self.assertEqual(0, rc, out)
        self.assertIn("[file deleted]", out)                         # the file is still on disk: simulated
        self.assertIn("dry-run vs HEAD: 1 fragment(s)", out)         # FILLER lives on in OTHER, RULE does not
        self.assertTrue((repo.root / SKILL).is_file())
        self.assert_lost(repo.run("--simulate-delete", SKILL), "deliverable")   # without --dry-run: red


if __name__ == "__main__":
    unittest.main()
