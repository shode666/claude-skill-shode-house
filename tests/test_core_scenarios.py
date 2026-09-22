"""Static shape + wiring tests for the v3.17 core scenarios (SPEC §47, FR-E-2/E-3). No model is called.
E01 lives in the frozen eval/scenarios/golden.json; E02..E15 + E10b + E1c in eval/scenarios/core-3.17.json."""
import importlib.util, json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE_FILE = ROOT / "eval/scenarios/core-3.17.json"
FIXTURE = ROOT / "scripts/eval-fixture-core.sh"
RUNNER = ROOT / "eval/run-core.sh"
IDS = {f"E{n:02d}" for n in range(1, 16)} | {"E10b", "E1c"}
RETIRING = {"meeting", "shode-house-evidence", "shode-house-broadcast", "shode-house-drift"}   # merged away in 3.17  # tombstone-allow

_spec = importlib.util.spec_from_file_location("team_run_check", ROOT / "scripts/team-run-check.py")
trc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(trc)


def scenarios():
    golden = json.loads((ROOT / "eval/scenarios/golden.json").read_text(encoding="utf-8"))["scenarios"]
    core = json.loads(CORE_FILE.read_text(encoding="utf-8"))["scenarios"]
    return [s for s in golden if s.get("kind") == "core"] + core


def shipped():
    skills = {p.parent.name for p in ROOT.glob("skills/*/*/SKILL.md")} - RETIRING   # tolerate the 4 dirs present or absent
    agents = {p.stem for p in ROOT.glob("agents/*.md")}
    return skills, agents


def preloads(agent):
    text = (ROOT / "agents" / f"{agent}.md").read_text(encoding="utf-8")
    m = re.search(r"^skills:\s*\[(.*?)\]", text.split("\n---", 2)[0] + "\n", re.M)
    return set(re.findall(r"[\w-]+", m.group(1))) if m else set()


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
        self.assertIn("developer", e["E1c"]["must_not_dispatch"])   # whole-run by scorer definition (Quinn Q6)
        self.assertEqual(e["E1c"]["route_any"], ["agent:security-engineer", "skill:secure"])
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
        self.assertEqual(e["E02"]["route_any"], ["skill:diagnose", "agent:code-reviewer"])      # skill + first-named Owner
        self.assertEqual(e["E06"]["route_any"], ["skill:data-migration", "agent:developer"])

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
        self.assertEqual(len(list((ROOT / "eval/prompts").glob("E*.md"))), 17)


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
        self.assertEqual(case_ids, IDS)
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
