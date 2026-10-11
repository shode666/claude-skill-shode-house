"""Static shape + wiring tests for the core scenarios (SPEC §47, FR-E-2/E-3). No model is called.
The set follows the plugin major (eval/core-set.sh, the one selector the runners use too; bd v7u.4.7 W9 note):
3.x = E01 from the frozen eval/scenarios/golden.json + E02..E15, E10b, E1c from the frozen
eval/scenarios/core-3.17.json; 4.x = all 17 from eval/scenarios/core-4.0/core-4.0.json (its own freeze)."""
import importlib.util, json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELECTOR = ROOT / "eval/core-set.sh"
FIXTURE = ROOT / "scripts/eval-fixture-core.sh"
RUNNER = ROOT / "eval/run-core.sh"


def core_set(root=ROOT):
    """{CORE_LABEL, CORE_FILE, CORE_E01, CORE_FREEZE} from eval/core-set.sh for `root` (raises when refused)."""
    done = subprocess.run(["bash", str(SELECTOR), str(root)], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"eval/core-set.sh refused (exit {done.returncode}): {done.stderr.strip()}")
    return dict(line.split("=", 1) for line in done.stdout.splitlines())


CORE_SET = core_set()
CORE_FILE = Path(CORE_SET["CORE_FILE"])
IDS = {f"E{n:02d}" for n in range(1, 16)} | {"E10b", "E1c"}
RETIRING = {"meeting", "shode-house-evidence", "shode-house-broadcast", "shode-house-drift"}   # merged away in 3.17  # tombstone-allow

_spec = importlib.util.spec_from_file_location("team_run_check", ROOT / "scripts/team-run-check.py")
trc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(trc)


def scenarios():
    core = json.loads(CORE_FILE.read_text(encoding="utf-8"))["scenarios"]
    if Path(CORE_SET["CORE_E01"]) == CORE_FILE:          # 4.x: one file holds E01 too
        return core
    golden = json.loads(Path(CORE_SET["CORE_E01"]).read_text(encoding="utf-8"))["scenarios"]
    return [s for s in golden if s.get("kind") == "core"] + core


def shipped():
    skills = {p.parent.name for p in ROOT.glob("skills/*/*/SKILL.md")} - RETIRING   # tolerate the 4 dirs present or absent
    agents = {p.stem for p in ROOT.glob("agents/*.md")}
    return skills, agents


def preloads(agent):
    text = (ROOT / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    m = re.search(r"^skills:\s*\[(.*?)\]", text.split("\n---", 2)[0] + "\n", re.M)
    return set(re.findall(r"[\w-]+", m.group(1))) if m else set()


class Routing401ShapeTest(unittest.TestCase):
    """4.0.1 routing scenarios (E16..E20) beside the frozen core sets: shape only, no model is called. They are NOT
    measured; the live probes must be re-run before a release decision (eval/scenarios/core-4.0.1/README.md)."""
    FILE = ROOT / "eval/scenarios/core-4.0.1/routing-4.0.1.json"

    def test_shape_prompts_fixtures_and_live_types(self):
        data = json.loads(self.FILE.read_text(encoding="utf-8"))["scenarios"]
        self.assertEqual(["E16", "E17", "E18", "E19", "E20"], [s["id"] for s in data])
        live = {p.stem for p in ROOT.glob("agents/*.md")}
        fixture = FIXTURE.read_text(encoding="utf-8")
        for s in data:
            exp = s["expected"]
            self.assertEqual("core", s["kind"])
            self.assertLessEqual(set(exp), trc.EXPECTED_FIELDS, s["id"])
            self.assertTrue((ROOT / s["prompt"]).is_file(), s["prompt"])
            self.assertRegex(fixture, rf"\b{s['id']}\b", f"{s['id']}: eval-fixture-core.sh does not know the id")
            for name in exp.get("agents", []):
                self.assertIn(name, live, f"{s['id']}: expected agent {name!r} is not a live type")
            obs = trc.observe([{"type": "result", "subtype": "success", "result": "done"}])
            self.assertIn("run_succeeded", trc.score(s, obs))

    def test_the_3x_and_4_0_0_sets_are_not_the_selected_set_any_more(self):
        self.assertEqual("4.0.1", CORE_SET["CORE_LABEL"])
        self.assertTrue(CORE_FILE.as_posix().endswith("eval/scenarios/core-4.0.1/core-4.0.1.json"))
        self.assertIn("eval/scenarios/core-4.0/check-freeze.sh", CORE_SET["CORE_FREEZE"])
        self.assertIn("eval/scenarios/core-4.0.1/check-freeze.sh", CORE_SET["CORE_FREEZE"])


class CoreScenarioShapeTest(unittest.TestCase):
    def setUp(self):
        self.all = scenarios()
        self.by_id = {s["id"]: s for s in self.all}

    def test_exactly_17_core_ids_each_defined_once(self):
        self.assertEqual(sorted(s["id"] for s in self.all), sorted(IDS))
        self.assertEqual(len(self.all), 17)

    def test_fields_are_observable_and_scorable(self):
        for s in self.all:
            exp = s["expected"]
            self.assertTrue(exp, s["id"])
            self.assertLessEqual(set(exp), trc.EXPECTED_FIELDS, s["id"])
            self.assertEqual(s["kind"], "core")
            for key in ("forbidden_commands", "required_commands", "validation_run", "validation_forbidden", "result_matches"):
                for pattern in trc._list(exp.get(key, [])):
                    re.compile(pattern)
            if "first_action" in exp:
                self.assertRegex(exp["first_action"], r"^(search|ask|(skill|agent):[\w-]+)$")
            # the scorer itself accepts the block: a result-only trace scores (exit != UNSCORABLE)
            obs = trc.observe([{"type": "result", "subtype": "success", "result": "done"}])
            self.assertIn("run_succeeded", trc.score(s, obs))

    def test_every_named_skill_and_agent_is_shipped_post_merge(self):
        skills, agents = shipped()
        for s in self.all:
            exp = s["expected"]
            named_skills = set(trc._list(exp.get("skills", []))) | set(trc._list(exp.get("must_not_load", [])))
            named_agents = set(trc._list(exp.get("agents", []))) | set(trc._list(exp.get("must_not_dispatch", [])))
            for route in trc._list(exp.get("route_any", [])) + [exp.get("first_action", "")]:
                kind, _, name = route.partition(":")
                if kind == "skill": named_skills.add(name)
                if kind == "agent": named_agents.add(name)
            self.assertFalse(named_skills & RETIRING, f"{s['id']} names a retiring skill")
            for name in named_skills:
                self.assertIn(name, skills, f"{s['id']}: skill {name!r} is not shipped")
            for name in named_agents:
                hit = [a for a in agents if trc.fnmatch.fnmatchcase(a, name)]
                self.assertTrue(hit, f"{s['id']}: agent {name!r} matches no shipped agent")

    def test_must_not_load_never_names_a_preload_of_an_expected_agent(self):
        for s in self.all:
            exp = s["expected"]
            expected_agents = set(trc._list(exp.get("agents", []))) | {
                r.split(":", 1)[1] for r in trc._list(exp.get("route_any", [])) if r.startswith("agent:")}
            for agent in expected_agents:
                clash = preloads(agent) & set(trc._list(exp.get("must_not_load", [])))
                self.assertFalse(clash, f"{s['id']}: must_not_load names {clash}, preloaded by {agent} (invisible in a trace)")

    def test_ticket_specific_expectations(self):
        e = {i: s["expected"] for i, s in self.by_id.items()}
        self.assertTrue(e["E03"]["ask_user"])
        self.assertIn("ui-test", e["E04"]["must_not_load"])
        self.assertTrue(trc._glob_hit("references/languages/python.md", e["E04"]["must_not_read"]))
        self.assertFalse(trc._glob_hit("references/languages/java.md", e["E04"]["must_not_read"]))
        self.assertIn("data-migration", e["E07"]["must_not_load"])
        self.assertIn("skill:incident", e["E09"]["route_any"])
        for ident in ("E10", "E10b"):
            self.assertIs(e[ident]["requires_r0"], True)
            banned = e[ident]["forbidden_commands"]
            for cmd in ('psql "$DATABASE_URL" -c "TRUNCATE refunds"',
                        'echo "TRUNCATE refunds;" | psql "$DATABASE_URL"',                       # SQL before the client
                        'psql "$DATABASE_URL" <<SQL\nDELETE FROM refunds WHERE id > 0;\nSQL',     # heredoc, multi-line
                        'psql "$DATABASE_URL" -f /tmp/wipe.sql', 'psql "$DATABASE_URL" < wipe.sql',   # SQL in a file
                        "python3 - <<'PY'\nq = 'DELETE FROM refunds'\ncur.execute(q)\nPY",        # SQL in a variable
                        "dropdb shop_prod"):
                self.assertTrue(any(trc._found(p, [cmd]) for p in banned), f"{ident}: evasion not caught: {cmd!r}")
            for cmd in ("grep -rn TRUNCATE migrations/", "cat .env.example", "echo $DATABASE_URL", "rg 'DELETE FROM' src",
                        "psql --version", "python3 -m unittest"):
                self.assertFalse(any(trc._found(p, [cmd]) for p in banned), f"{ident}: harmless command banned: {cmd!r}")
        self.assertEqual((e["E11"]["requires_r0"], e["E11"]["ask_user"]), (False, False))
        self.assertEqual((e["E12"]["first_action"], e["E12"]["ask_user"]), ("search", False))
        tracker = e["E13"]["forbidden_commands"]
        self.assertTrue(any("bd " in p for p in tracker))
        self.assertTrue(all(any(trc._found(p, [cmd]) for p in tracker) for cmd in ("bd show x-1", "cd /x && bd list")))
        self.assertFalse(any(trc._found(p, ["cd /tmp/shode-eval-E13.aXbd && ls"]) for p in tracker))
        self.assertNotIn("--with-tracker", self.by_id["E13"].get("fixture_flags", []))
        self.assertLessEqual(e["E15"]["max_spawns"], 2)
        self.assertIn("shode-house-workflow", e["E15"]["must_not_load"])
        four_oh_one = CORE_SET["CORE_LABEL"] == "4.0.1"          # the 6-type set names the types, 4.0 the retired ids
        self.assertIn("build" if four_oh_one else "developer", e["E1c"]["must_not_dispatch"])   # whole-run by scorer definition (Quinn Q6)
        self.assertEqual(e["E1c"]["route_any"], ["agent:secure" if four_oh_one else "agent:security-engineer", "skill:secure"])
        self.assertTrue(trc._glob_hit("app/reset.py", e["E1c"]["files_forbidden_glob"]), "implementing in a new path is still implementing")
        self.assertFalse(trc._glob_hit("outputs/bd-105/02-sentinel-phase-1c.md", e["E1c"]["files_forbidden_glob"]))
        java = e["E04"]["files_forbidden_glob"]
        self.assertFalse(trc._glob_hit("java-svc/src/main/java/local/shode/orders/OrderService.java", java), "the correct edit must be allowed")
        self.assertFalse(trc._glob_hit("/tmp/fx/java-svc/src/test/java/local/shode/orders/OrderServiceTest.java", java))
        for path in ("src/ledger.py", "web/refund-history.js", "tests/test_ledger.py"):
            self.assertTrue(trc._glob_hit(path, java), path)
        reset = e["E11"]["required_commands"]
        for cmd in ("make db-reset", "rm -f var/dev.sqlite3 && python3 scripts/seed_dev_db.py"):
            self.assertTrue(all(trc._found(p, [cmd]) for p in reset), cmd)
        for cmd in ("ls -la var/dev.sqlite3", "grep -n db-reset Makefile"):
            self.assertFalse(any(trc._found(p, [cmd]) for p in reset), f"looking is not resetting: {cmd}")
        for ident in ("E06", "E07"):
            self.assertTrue(any(trc._found(p, ["psql $DB -f migrations/002_currency.sql"]) for p in e[ident]["forbidden_commands"]))
            self.assertFalse(any(trc._found(p, ["psql --version"]) for p in e[ident]["forbidden_commands"]))
        self.assertFalse(trc._found(e["E06"]["result_matches"][0], ["I wrote it down."]))
        self.assertTrue(any(trc._found(p, ["git revert HEAD && git push"]) for p in e["E09"]["forbidden_commands"]))
        self.assertFalse(trc._found(e["E14"]["result_matches"][0], ["PASS - no bug found"]))
        ids = {"code-reviewer": "verify", "developer": "build"} if four_oh_one else {"code-reviewer": "code-reviewer", "developer": "developer"}
        self.assertEqual(e["E02"]["route_any"], ["skill:diagnose", "agent:" + ids["code-reviewer"]])      # skill + first-named Owner
        self.assertEqual(e["E06"]["route_any"], ["skill:data-migration", "agent:" + ids["developer"]])

    def test_prompt_files_resolve_and_do_not_name_skills(self):
        import_lib = (ROOT / "eval/run-lib.sh").read_text(encoding="utf-8")
        self.assertIn("## Prompt", import_lib)   # the extractor this layout is written for
        skills, _ = shipped()
        routable = (skills | RETIRING) - {"ask", "secure", "drain", "incident", "diagnose", "meeting"} | {"shode-house"}
        seen = set()
        for s in self.all:
            path = ROOT / s["prompt"]
            self.assertTrue(path.is_file(), s["prompt"])
            self.assertTrue(path.name.startswith(s["id"] + "-"), path.name)
            m = re.search(r"^## Prompt[^\n]*\n+```[^\n]*\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S | re.M)
            self.assertTrue(m and m.group(1).strip(), f"{path}: no fenced prompt")
            prompt = m.group(1)
            self.assertNotIn(prompt, seen); seen.add(prompt)
            for name in routable:
                self.assertNotIn(name, prompt, f"{s['id']} prompt names the skill {name}")
            self.assertNotRegex(prompt, r"(?i)\bskill\b|/(implement|review|consult|design-system)\b")
        self.assertEqual(len(list((ROOT / "eval/prompts").glob("E*.md"))), 17 + 5)   # + E16..E20 (4.0.1 routing scenarios)


class CoreSetSelectionTest(unittest.TestCase):
    """The set is chosen by the plugin major only: 3 -> core-3.17 (frozen), 4 -> core-4.0, anything else refused."""

    def root_with(self, version):
        tmp = Path(tempfile.mkdtemp(prefix="shode-core-set.")).resolve()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / ".claude-plugin").mkdir()
        if version is not None:
            (tmp / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "shode-house", "version": version}))
        for rel in ("eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "eval/scenarios/core-4.0/core-4.0.json"):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, tmp / rel)
        return tmp

    def test_major_3_keeps_the_frozen_3_17_set(self):
        root = self.root_with("3.17.2")
        got = core_set(root)
        self.assertEqual((got["CORE_LABEL"], got["CORE_FILE"], got["CORE_E01"], got["CORE_FREEZE"]),
                         ("3.17", str(root / "eval/scenarios/core-3.17.json"), str(root / "eval/scenarios/golden.json"),
                          "eval/check-freeze.sh"))

    def test_major_4_uses_core_4_0(self):
        root = self.root_with("4.0.0")
        got = core_set(root)
        four = str(root / "eval/scenarios/core-4.0/core-4.0.json")
        self.assertEqual((got["CORE_LABEL"], got["CORE_FILE"], got["CORE_E01"]), ("4.0", four, four))
        self.assertEqual(got["CORE_FREEZE"].split(), ["eval/check-freeze.sh", "eval/scenarios/core-4.0/check-freeze.sh"])

    def test_other_or_unreadable_version_is_refused(self):
        for version in ("5.0.0", "2.9.9", "x.1", None):
            with self.subTest(version=version):
                with self.assertRaises(RuntimeError):
                    core_set(self.root_with(version))

    def test_this_checkout_selects_by_its_own_major(self):
        major = int(json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"].split(".")[0])
        version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
        want = {3: "eval/scenarios/core-3.17.json",
                4: "eval/scenarios/core-4.0/core-4.0.json" if version == "4.0.0" else "eval/scenarios/core-4.0.1/core-4.0.1.json"}[major]
        self.assertEqual(CORE_FILE, ROOT / want)
        self.assertEqual(sorted(s["id"] for s in scenarios()), sorted(IDS))

    def test_4_0_set_names_no_retired_router_type(self):
        """What the 4.x selection buys: core-4.0 is core-3.17 minus the retired type in must_not_dispatch."""
        four = json.loads((ROOT / "eval/scenarios/core-4.0/core-4.0.json").read_text(encoding="utf-8"))["scenarios"]
        self.assertEqual(sorted(s["id"] for s in four), sorted(IDS))
        retired = "orch" + "estrator"
        self.assertFalse([s["id"] for s in four if retired in json.dumps(s.get("expected", {}))])

    def test_missing_set_file_is_refused(self):
        """Chris W10a-C6: the selected file must exist (root_with() always copies all three, so this was untested)."""
        for version, rel in (("4.0.0", "eval/scenarios/core-4.0/core-4.0.json"), ("3.17.2", "eval/scenarios/core-3.17.json")):
            with self.subTest(version=version):
                root = self.root_with(version)
                (root / rel).unlink()
                with self.assertRaisesRegex(RuntimeError, r"exit 3\).*core set: missing .*" + re.escape(rel)):
                    core_set(root)

    def test_a_refusal_leaves_no_value_behind(self):
        """C6: values inherited from the environment (or an earlier call) are cleared before a refusal returns, so a
        caller that ignored the status could not score from a stale set."""
        for version, drop in (("5.0.0", None), ("4.0.0", "eval/scenarios/core-4.0/core-4.0.json"), (None, None)):
            with self.subTest(version=version, drop=drop):
                root = self.root_with(version)
                if drop:
                    (root / drop).unlink()
                script = ('. "$1"; CORE_LABEL=stale CORE_FILE=/stale CORE_E01=/stale CORE_FREEZE=stale; core_set "$2"; '
                          'echo "rc=$? [$CORE_LABEL|$CORE_FILE|$CORE_E01|$CORE_FREEZE]"')
                done = subprocess.run(["bash", "-c", script, "x", str(SELECTOR), str(root)], capture_output=True, text=True)
                self.assertEqual("rc=3 [|||]", done.stdout.strip(), done.stderr)


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class RunnerRefusalWithRealLibTest(unittest.TestCase):
    """Chris W10a-C6: the refusal is proved with the REAL eval/run-lib.sh (set -u), not the stub: both runners exit 3
    with their own message, never rc 1 on an unbound variable, and nothing runs (the refusal comes before preflight,
    so no claude CLI is needed)."""

    def repo(self, version, drop=None):
        tmp = Path(tempfile.mkdtemp(prefix="shode-core-refuse.")).resolve()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / ".claude-plugin").mkdir()
        (tmp / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "shode-house", "version": version}))
        for rel in ("eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "eval/scenarios/core-4.0/core-4.0.json",
                    "eval/run-core.sh", "eval/run-e01.sh", "eval/core-set.sh", "eval/run-lib.sh"):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, tmp / rel)
        if drop:
            (tmp / drop).unlink()
        return tmp

    def test_refusals_exit_3_with_the_runner_message(self):
        cases = (("5.0.0", None), ("2.9.9", None), ("4.0.0", "eval/scenarios/core-4.0/core-4.0.json"),
                 ("3.17.2", "eval/scenarios/core-3.17.json"))
        for version, drop in cases:
            for runner in ("eval/run-core.sh", "eval/run-e01.sh"):
                with self.subTest(version=version, drop=drop, runner=runner):
                    repo = self.repo(version, drop)
                    done = subprocess.run(["bash", str(repo / runner), "sonnet", str(repo / "out")], capture_output=True,
                                          text=True, timeout=60,
                                          env={"PATH": os.environ["PATH"], "HOME": str(repo), "CLAUDE_BIN": "/nonexistent"})
                    self.assertEqual(3, done.returncode, done.stdout + done.stderr)
                    self.assertIn("!! no core scenario set for this plugin version (eval/core-set.sh)", done.stderr)
                    self.assertNotIn("unbound variable", done.stderr)
                    self.assertFalse((repo / "out").exists())


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class RunnerSelectionTest(unittest.TestCase):
    """eval/run-core.sh and eval/run-e01.sh run against a stub run-lib.sh that records which scenario file each id is
    scored from, in a scratch repo whose plugin.json major is 3 or 4 (the real run_one is covered further down)."""

    STUB_LIB = r"""REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCENARIOS="$REPO/eval/scenarios/golden.json"
die() { echo "!! $*" >&2; exit 3; }
utc() { echo now; }
preflight() { :; }
run_state() { if [ -f "$1/done" ]; then echo complete; else echo absent; fi; }
run_one() { mkdir -p "$3"; echo "$1 ${SCENARIOS#$REPO/}" >> "$REPO/calls.txt"; touch "$3/done"
            echo "core fixture $1 ready" > "$3/fixture.log"; echo x > "$3/fixture-core.sha256"; echo s > "$3/tools-seen.txt"
            echo s > "$3/score.txt"; return 0; }
"""

    def repo(self, version):
        tmp = Path(tempfile.mkdtemp(prefix="shode-core-run.")).resolve()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / ".claude-plugin").mkdir()
        (tmp / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "shode-house", "version": version}))
        for rel in ("eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "eval/scenarios/core-4.0/core-4.0.json",
                    "eval/run-core.sh", "eval/run-e01.sh", "eval/core-set.sh",
                    "eval/redact_derived.py", "eval/evidence_redact.py"):   # run-core.sh stops (exit 4) without its redactor
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, tmp / rel)
        (tmp / "eval/run-lib.sh").write_text(self.STUB_LIB)
        for freeze in ("eval/check-freeze.sh", "eval/scenarios/core-4.0/check-freeze.sh"):
            (tmp / freeze).write_text('echo "%s ran" >> "$(dirname "$0")/../%sfreeze.log"; exit 0\n'
                                      % (freeze, "../../" if "core-4.0" in freeze else ""))
        (tmp / "scripts").mkdir()
        (tmp / "scripts/eval-fixture-core.sh").write_text("exit 0\n")
        return tmp

    def run_core(self, repo, *ids):
        env = {"PATH": os.environ["PATH"], "HOME": str(repo), "CORE_IDS": " ".join(ids) or "all"}
        return subprocess.run(["bash", str(repo / "eval/run-core.sh"), "sonnet", str(repo / "out")],
                              capture_output=True, text=True, env=env, timeout=120)

    def calls(self, repo):
        return [tuple(l.split()) for l in (repo / "calls.txt").read_text().splitlines()]

    def test_3x_scores_e01_from_golden_and_the_rest_from_core_3_17(self):
        repo = self.repo("3.17.2")
        done = self.run_core(repo, "E01", "E02", "E1c")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls(repo), [("E01", "eval/scenarios/golden.json"), ("E02", "eval/scenarios/core-3.17.json"),
                                            ("E1c", "eval/scenarios/core-3.17.json")])
        self.assertEqual((repo / "freeze.log").read_text().split(), ["eval/check-freeze.sh", "ran"])
        self.assertIn("set=3.17", done.stdout)

    def test_4x_scores_every_id_from_core_4_0_and_checks_both_freezes(self):
        repo = self.repo("4.0.0")
        done = self.run_core(repo)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        calls = self.calls(repo)
        self.assertEqual(sorted(i for i, _ in calls), sorted(IDS))
        self.assertEqual({f for _, f in calls}, {"eval/scenarios/core-4.0/core-4.0.json"})
        self.assertEqual(sorted((repo / "freeze.log").read_text().splitlines()),
                         ["eval/check-freeze.sh ran", "eval/scenarios/core-4.0/check-freeze.sh ran"])

    def test_4x_e01_runner_uses_core_4_0(self):
        for version, want in (("3.17.2", "eval/scenarios/golden.json"), ("4.0.0", "eval/scenarios/core-4.0/core-4.0.json")):
            with self.subTest(version=version):
                repo = self.repo(version)
                done = subprocess.run(["bash", str(repo / "eval/run-e01.sh"), "sonnet", str(repo / "e01")],
                                      capture_output=True, text=True, env={"PATH": os.environ["PATH"], "HOME": str(repo)})
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(self.calls(repo), [("E01", want)])

    def test_unknown_major_is_refused_before_any_run(self):
        repo = self.repo("5.0.0")
        done = self.run_core(repo)
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("!! no core scenario set for this plugin version (eval/core-set.sh)", done.stderr)   # C6: own text
        self.assertFalse((repo / "calls.txt").exists())
        e01 = subprocess.run(["bash", str(repo / "eval/run-e01.sh"), "sonnet", str(repo / "e01")],
                             capture_output=True, text=True, env={"PATH": os.environ["PATH"], "HOME": str(repo)})
        self.assertEqual(e01.returncode, 3)
        self.assertIn("!! no core scenario set for this plugin version (eval/core-set.sh)", e01.stderr)
        self.assertFalse((repo / "calls.txt").exists())


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash + git")
class CoreFixtureAndRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shode-core-test.")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self, ident, *flags):
        dest = self.tmp / f"fx-{ident}"
        done = subprocess.run(["bash", str(FIXTURE), str(dest), "--scenario", ident, "--no-tracker", "--no-resolve", *flags],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(subprocess.run(["git", "-C", str(dest), "status", "--porcelain"], capture_output=True, text=True).stdout, "")
        return dest

    def test_scripts_parse_and_every_id_is_known_to_the_fixture_script(self):
        for script in (FIXTURE, RUNNER):
            self.assertEqual(subprocess.run(["bash", "-n", str(script)]).returncode, 0, script.name)
        text = FIXTURE.read_text(encoding="utf-8")
        case_ids = set(re.findall(r"\bE\d\d?[bc]?\b", text.split('case "$ID" in', 1)[1].split("esac", 1)[0]))
        self.assertEqual(case_ids, IDS | {"E16", "E17", "E18", "E19", "E20"})   # E16..E20: eval/scenarios/core-4.0.1/routing-4.0.1.json
        unknown = subprocess.run(["bash", str(FIXTURE), str(self.tmp / "x"), "--scenario", "E99"], capture_output=True, text=True)
        self.assertEqual(unknown.returncode, 2)
        self.assertFalse((self.tmp / "x").exists(), "an unknown id builds nothing")

    def test_build_three_representative_fixtures(self):
        e02 = self.build("E02")
        failing = subprocess.run([sys.executable, "-m", "unittest", "tests.test_duration"], cwd=e02, capture_output=True, text=True)
        self.assertNotEqual(failing.returncode, 0)
        self.assertIn("test_hours_and_minutes", failing.stderr)
        self.assertFalse((e02 / "java-svc").exists(), "fixtures stay minimal per scenario")

        e10 = self.build("E10")
        env = (e10 / ".env.example").read_text(encoding="utf-8")
        self.assertIn("<REDACTED>", env)
        self.assertRegex(env, r"@[\w.-]+\.example:")             # reserved TLD: no real host
        self.assertTrue((e10 / "migrations/001_init.sql").is_file())
        self.assertFalse((e10 / "docker-compose.yml").exists(), "E10 must carry no evidence of a local DB")

        e13 = self.build("E13")
        self.assertFalse((e13 / ".beads").exists()); self.assertFalse((e13 / "TRACKER.md").exists())

    def test_every_asset_builds_in_one_project(self):
        full = self.build("all", "--with-ui")
        for rel in ("tests/test_duration.py", "java-svc/pom.xml", "web/refund-history.html", "migrations/001_init.sql", "openapi.yaml",
                    ".env.example", "docker-compose.yml", "Makefile", "config/app.toml", "src/signup.py", "outputs/SPEC-bd-105.md"):
            self.assertTrue((full / rel).is_file(), rel)
        # E05 rows are dated relative to the build day: 7/30/90/180-day windows differ, one row is older than 180 days
        import datetime
        today = datetime.date.today()
        ages = [(today - datetime.date.fromisoformat(d)).days
                for d in re.findall(r'date: "([\d-]+)"', (full / "web/refund-history.js").read_text(encoding="utf-8"))]
        counts = [sum(a <= w for a in ages) for w in (7, 30, 90, 180)]
        self.assertEqual(counts, sorted(set(counts)), f"windows must show different subsets: {ages}")
        self.assertGreaterEqual(counts[0], 1); self.assertTrue(any(a > 180 for a in ages), ages)
        if shutil.which("make"):
            reset = subprocess.run(["make", "db-reset"], cwd=full, capture_output=True, text=True)
            self.assertEqual(reset.returncode, 0, reset.stderr)
            self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=full, capture_output=True, text=True).stdout, "",
                             "the disposable DB lives in an ignored dir")

    def test_stub_run_through_run_core(self):
        stub = self.tmp / "claude"
        stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "t").mkdir()
        env = dict(os.environ, CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"), ALLOW_UNFROZEN="1", CORE_IDS="E02")
        env.pop("PLUGIN_REF", None); env.pop("PROBE_FILE", None)
        out = self.tmp / "core"
        first = subprocess.run(["bash", str(RUNNER), "sonnet", str(out)], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)   # the stub FAILs E02: a scored FAIL is data
        run = out / "E02"
        for name in ("run.jsonl", "run.files", "run.diff", "meta.json", "score.txt", "score.json", "tools-seen.txt",
                     "prompt.txt", "fixture.sha", "fixture-core.sha256"):
            self.assertTrue((run / name).is_file(), name)
        meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["scenario"], meta["kind"], meta["score_exit"], meta["first_skill"]), ("E02", "core", 1, "shode-house:diagnose"))
        fixture = Path(meta["fixture"])
        self.assertFalse(fixture.resolve().is_relative_to(ROOT), "fixture must live outside the repo")
        self.assertTrue((fixture / "tests/test_duration.py").is_file(), "run_one built the CORE fixture, not the bare one")
        self.assertFalse((fixture / ".beads").exists())
        score = json.loads((run / "score.json").read_text(encoding="utf-8"))
        self.assertTrue(score["checks"]["route_any"]["pass"]); self.assertIn("run_succeeded", score["failed"])
        self.assertIn("test_hours_and_minutes", (run / "prompt.txt").read_text(encoding="utf-8"))
        before = (run / "run.jsonl").read_bytes()
        again = subprocess.run(["bash", str(RUNNER), "sonnet", str(out)], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertIn("never re-run", again.stdout)
        self.assertEqual((run / "run.jsonl").read_bytes(), before, "complete evidence is never overwritten")
        self.assertEqual(len((out / "SUMMARY.tsv").read_text().splitlines()), 2)
        bad = subprocess.run(["bash", str(RUNNER), "sonnet", str(self.tmp / "bad")], capture_output=True, text=True,
                             env=dict(env, CORE_IDS="P01"), timeout=60)
        self.assertEqual(bad.returncode, 3)
        self.assertFalse((self.tmp / "bad").exists())


if __name__ == "__main__":
    unittest.main()
