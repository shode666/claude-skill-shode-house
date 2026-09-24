"""Wiring tests for eval/run-e01.sh and eval/run-probes.sh against tests/fake_claude.py.
No model is called. These prove directory refusal, fixture-outside-repo, evidence files,
meta.json fields and scorer exit propagation -- NOT the shape of a real `claude -p` trace."""
import csv, json, os, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = json.loads((ROOT / "eval/scenarios/golden.json").read_text(encoding="utf-8"))["scenarios"]
NEW = [s for s in GOLDEN if "expected" in s]


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash + git")
class RunnerWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shode-runner-test.")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        stub = self.tmp / "claude"   # wrapper: independent of the tracked exec bit
        stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "t").mkdir()
        self.env = dict(os.environ, CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"), ALLOW_UNFROZEN="1")
        self.env.pop("PLUGIN_REF", None)

    def run_script(self, name, *args, **env):
        return subprocess.run(["bash", str(ROOT / "eval" / name), *args], capture_output=True, text=True,
                              env=dict(self.env, **env), timeout=120)

    def test_e01_scores_writes_evidence_and_refuses_existing_dir(self):
        out = self.tmp / "e01"
        first = self.run_script("run-e01.sh", "sonnet", str(out))
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        for name in ("run.jsonl", "run.files", "meta.json", "score.txt", "score.json", "tools-seen.txt", "prompt.txt"):
            self.assertTrue((out / name).is_file(), name)
        meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
        for key in ("host", "cli_version", "date", "model_id", "plugin_sha", "scenario", "start", "end", "claude_exit"):
            self.assertIn(key, meta)
        self.assertEqual((meta["scenario"], meta["score_exit"]), ("E01", 0))
        self.assertFalse(Path(meta["fixture"]).resolve().is_relative_to(ROOT), "fixture must live outside the repo")
        self.assertEqual((out / "run.files").read_text().strip(), "M src/validators.py")
        self.assertIn("exit=0", (out / "score.txt").read_text())
        before = (out / "run.jsonl").read_bytes()
        second = self.run_script("run-e01.sh", "sonnet", str(out))
        self.assertEqual(second.returncode, 3)
        self.assertEqual((out / "run.jsonl").read_bytes(), before, "existing evidence must not be touched")

    def test_probes_repeats_layout_summary_agg_and_refusal(self):
        out = self.tmp / "probes"
        done = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P03", REPEATS="2")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)   # P03 FAILs (stub loads diagnose): data, not an error
        rows = list(csv.DictReader((out / "SUMMARY.tsv").open(encoding="utf-8"), delimiter="\t"))
        self.assertEqual([(r["id"], r["run"], r["exit"], r["route"], r["channel"], r["terminal"]) for r in rows],
                         [("P02", "r1", "0", "skill:diagnose", "skill", "max_turns"), ("P02", "r2", "0", "skill:diagnose", "skill", "max_turns"),
                          ("P03", "r1", "1", "skill:diagnose", "none", "max_turns"), ("P03", "r2", "1", "skill:diagnose", "none", "max_turns")])
        agg = {r["id"]: r for r in csv.DictReader((out / "AGG.tsv").open(encoding="utf-8"), delimiter="\t")}
        self.assertEqual((agg["P02"]["k_pass/N"], agg["P03"]["k_pass/N"], agg["P02"]["class"], agg["P02"]["mean_distinct_skills"]),
                         ("2/2", "0/2", "description-sensitive", "1.00"))
        meta = json.loads((out / "P02/r1/meta.json").read_text(encoding="utf-8"))
        self.assertIn("max-turns=6", meta["flags"])
        for key in ("scenarios", "prompt_file", "prompt_txt", "scorer", "run_lib", "fixture_script", "probe_settings"):
            self.assertRegex(meta["sha256"][key] or "", r"^[0-9a-f]{64}$", key)
        self.assertIn("plugins", meta["init_sha256"])
        self.assertFalse((out / "P01").exists(), "subset runs only the ids asked for")
        other = self.run_script("run-probes.sh", "opus", str(out), PROBE_IDS="P02")   # same dir, different batch identity
        self.assertEqual(other.returncode, 3, other.stdout + other.stderr)
        na = self.run_script("run-probes.sh", "sonnet", str(self.tmp / "na"), PROBE_IDS="P21")
        self.assertEqual(na.returncode, 3)
        self.assertFalse((self.tmp / "na").exists(), "a not_applicable probe is refused before anything is created")

    def test_probes_resume_after_crash_never_overwrites(self):
        out = self.tmp / "crash"
        crashed = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02", REPEATS="2", FAKE_MODE="noresult")
        self.assertEqual(crashed.returncode, 2)
        before = {p.name: (p / "run.jsonl").read_bytes() for p in (out / "P02").iterdir()}
        self.assertEqual(sorted(before), ["r1", "r2"])   # one attempt per slot per invocation
        resumed = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02", REPEATS="2")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(sorted(p.name for p in (out / "P02").iterdir()), ["r1", "r1.retry1", "r2", "r2.retry1"])
        for name, content in before.items():
            self.assertEqual((out / "P02" / name / "run.jsonl").read_bytes(), content, "incomplete evidence is kept untouched")
        rows = list(csv.DictReader((out / "SUMMARY.tsv").open(encoding="utf-8"), delimiter="\t"))
        self.assertEqual([(r["run"], r["exit"]) for r in rows], [("r1", "2"), ("r1.retry1", "0"), ("r2", "2"), ("r2.retry1", "0")])
        agg = next(csv.DictReader((out / "AGG.tsv").open(encoding="utf-8"), delimiter="\t"))
        self.assertEqual((agg["k_pass/N"], agg["n_unscorable_or_incomplete"]), ("2/2", "2"))
        stamp = {str(p): p.stat().st_mtime_ns for p in out.rglob("run.jsonl")}
        again = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02", REPEATS="2")
        self.assertEqual(again.returncode, 0)
        self.assertEqual({str(p): p.stat().st_mtime_ns for p in out.rglob("run.jsonl")}, stamp, "complete runs are skipped")

    def test_infra_error_stops_the_batch_is_never_scored_and_resume_reruns_the_slot(self):
        out = self.tmp / "infra"
        stopped = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P03 P04", REPEATS="2",
                                  FAKE_MODE="infra", FAKE_INFRA_ON="rollback")   # P03's prompt
        self.assertEqual(stopped.returncode, 5, stopped.stdout + stopped.stderr)
        self.assertIn("BATCH STOPPED: INFRA error at P03 r1", stopped.stdout)
        self.assertEqual(sorted(str(p.relative_to(out)) for p in out.glob("P*/r*")), ["P02/r1", "P03/r1"], "nothing runs after the stop")
        score = json.loads((out / "P03/r1/score.json").read_text(encoding="utf-8"))
        self.assertEqual(score["status"], "INFRA_ERROR")
        rows = {(r["id"], r["run"]): r["exit"] for r in csv.DictReader((out / "SUMMARY.tsv").open(encoding="utf-8"), delimiter="\t")}
        self.assertEqual(rows, {("P02", "r1"): "0", ("P03", "r1"): "infra"})
        kept = (out / "P03/r1/run.jsonl").read_bytes()
        resumed = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P03 P04", REPEATS="2")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual((out / "P03/r1/run.jsonl").read_bytes(), kept, "the infra run stays as evidence")
        agg = {r["id"]: r for r in csv.DictReader((out / "AGG.tsv").open(encoding="utf-8"), delimiter="\t")}
        self.assertEqual((agg["P03"]["k_pass/N"], agg["P03"]["n_unscorable_or_incomplete"], agg["P03"]["uninformative_0_of_N"]), ("0/2", "1", "yes"))
        self.assertEqual((agg["P02"]["k_pass/N"], agg["P02"]["uninformative_0_of_N"]), ("2/2", "no"))
        self.assertTrue((out / "P03/r1.retry1/meta.json").is_file() and (out / "P03/r2/meta.json").is_file())
        twice = self.run_script("run-probes.sh", "sonnet", str(self.tmp / "infra2"), PROBE_IDS="P03", REPEATS="1", FAKE_MODE="infra")
        again = self.run_script("run-probes.sh", "sonnet", str(self.tmp / "infra2"), PROBE_IDS="P03", REPEATS="1", FAKE_MODE="infra")
        self.assertEqual((twice.returncode, again.returncode), (5, 5), "an infra error never uses up the crash-retry budget")
        self.assertTrue((self.tmp / "infra2/P03/r1.retry1").is_dir())

    def test_three_crashes_in_a_row_stop_the_batch(self):
        done = self.run_script("run-probes.sh", "sonnet", str(self.tmp / "c3"), PROBE_IDS="P02 P03 P04 P05", FAKE_MODE="noresult")
        self.assertEqual(done.returncode, 5)
        self.assertFalse((self.tmp / "c3/P05").exists())

    def test_probe_file_is_refused_in_a_tracked_location(self):
        ext = self.tmp / "h.json"
        ext.write_text(json.dumps([{"id": "H01", "kind": "probe", "prompt_text": "x", "expected": {"max_spawns": 0}}]), encoding="utf-8")
        target = ROOT / "eval/baseline/zz-heldout-must-not-exist"
        done = self.run_script("run-probes.sh", "sonnet", str(target), PROBE_FILE=str(ext))
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertIn("git-tracked location", done.stderr)
        self.assertFalse(target.exists())

    def test_probe_file_runs_an_external_set_without_copying_it_into_the_repo(self):
        ext = self.tmp / "heldout"; ext.mkdir()
        (ext / "set.json").write_text(json.dumps({"scenarios": [
            {"id": "H01", "kind": "probe", "class": "held-out", "max_turns": 6, "prompt_text": "อะไรสักอย่างที่ไม่อยู่ใน repo",
             "fixture_flags": ["--with-ui"], "expected": {"route_any": ["skill:diagnose"], "max_skills": 2}},
            {"id": "H02", "kind": "probe", "prompt": "h02.md", "expected": {"route_any": ["skill:incident"]}}]}), encoding="utf-8")
        (ext / "h02.md").write_text("# H02\n\n## Prompt\n\n```\nheld-out two\n```\n", encoding="utf-8")
        before = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout
        out = self.tmp / "held"
        done = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_FILE=str(ext / "set.json"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((out / "H01/r1/prompt.txt").read_text(encoding="utf-8"), "อะไรสักอย่างที่ไม่อยู่ใน repo")
        self.assertEqual((out / "H02/r1/prompt.txt").read_text(encoding="utf-8"), "held-out two")
        fixture = lambda i: Path(json.loads((out / i / "r1/meta.json").read_text())["fixture"]) / "web/refund-history.html"
        self.assertEqual((fixture("H01").is_file(), fixture("H02").is_file()), (True, False), "fixture_flags honoured for external sets")
        agg = {r["id"]: r for r in csv.DictReader((out / "AGG.tsv").open(encoding="utf-8"), delimiter="\t")}
        self.assertEqual((agg["H01"]["k_pass/N"], agg["H01"]["class"], agg["H02"]["k_pass/N"]), ("1/1", "held-out", "0/1"))
        after = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(before, after, "nothing from the external set lands in the repo")

    def test_ui_fixture_flag_only_for_ui_probes(self):
        out = self.tmp / "ui"
        self.assertEqual(self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P07").returncode, 0)
        has_ui = lambda i: (Path(json.loads((out / i / "r1/meta.json").read_text())["fixture"]) / "web/refund-history.html").is_file()
        self.assertEqual((has_ui("P02"), has_ui("P07")), (False, True))


class FreezeTest(unittest.TestCase):
    def check(self, root=None, *args):
        env = dict(os.environ, **({"FREEZE_ROOT": str(root)} if root else {}))
        return subprocess.run(["bash", str(ROOT / "eval/check-freeze.sh"), *args], capture_output=True, text=True, env=env)

    def test_repo_matches_its_freeze_manifest(self):
        done = self.check()
        self.assertEqual(done.returncode, 0, "frozen probe file changed -- see eval/check-freeze.sh header:\n" + done.stdout + done.stderr)

    def test_change_missing_and_unlisted_prompt_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("eval/scenarios/golden.json", "eval/scenarios/core-3.17.json", "scripts/team-run-check.py", "scripts/eval-fixture.sh", "eval/run-lib.sh",
                        "eval/run-probes.sh", "eval/probe-agg.py", "eval/check-freeze.sh", "eval/check-arm-diff.sh",
                        "eval/PROBE-GATE.md", "eval/PROBE-GATE-floor.md", "eval/PROBE-GATE-floor-v2.md", "eval/heldout-3.17.SHA256SUMS", "eval/prompts/probes/P01.md"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, root / rel)
            self.assertEqual(self.check(root).returncode, 1, "no manifest = fail")
            self.assertEqual(self.check(root, "--update").returncode, 0)
            self.assertEqual(self.check(root).returncode, 0)
            with (root / "eval/prompts/probes/P01.md").open("a", encoding="utf-8") as f:
                f.write(" ")
            self.assertIn("CHANGED eval/prompts/probes/P01.md", self.check(root).stdout)
            self.check(root, "--update")
            (root / "eval/prompts/probes/P99.md").write_text("new", encoding="utf-8")
            self.assertIn("UNLISTED", self.check(root).stdout)
            (root / "eval/prompts/probes/P99.md").unlink(); (root / "eval/run-lib.sh").unlink()
            done = self.check(root)
            self.assertEqual((done.returncode, "MISSING eval/run-lib.sh" in done.stdout), (1, True))


@unittest.skipUnless(shutil.which("git"), "needs git")
class ArmDiffTest(unittest.TestCase):
    SKILL = "---\nname: diagnose\ndescription: |\n  [WHAT] old words here\n  [TRIGGER] bug\nallowed-tools: Read\n---\n\n# Body\nrule one\n"

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="shode-armdiff.")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.git("init", "-q"); self.git("config", "user.email", "t@t"); self.git("config", "user.name", "t")
        self.write("skills/workflow/diagnose/SKILL.md", self.SKILL)
        self.write("skills/ops/slo/SKILL.md", self.SKILL.replace("diagnose", "slo"))
        self.write("agents/developer.md", "---\nname: developer\n---\nbody\n")
        self.write(".claude-plugin/plugin.json", '{\n  "name": "x",\n  "version": "1.0.0",\n  "skills": []\n}\n')
        self.write("eval/prompts/probes/P28.md", "# P28\n\n## Prompt\n\n```\nเครื่องผมรันได้ปกติแต่เครื่องเพื่อนพังเป็นบางครั้ง works on my laptop only\n```\n")
        self.write("eval/prompts/probes/P05.md", "# P05\n\n## Prompt\n\n```\nfrozen legacy prompt words here\n```\n")
        self.base = self.commit("base")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True).stdout.strip()

    def write(self, rel, text):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(text, encoding="utf-8")

    def commit(self, msg):
        self.git("add", "-A"); self.git("commit", "-qm", msg)
        return self.git("rev-parse", "HEAD")

    def verdict(self, mutate, *extra):
        self.git("checkout", "-q", "-B", "work", self.base)
        mutate()
        after = self.commit("after")
        p = subprocess.run(["bash", str(ROOT / "eval/check-arm-diff.sh"), self.base, after, *extra], capture_output=True, text=True,
                           env=dict(os.environ, CHECK_ROOT=str(self.root)))
        return p.returncode, p.stdout + p.stderr

    def new_desc(self, text):
        return lambda: self.write("skills/workflow/diagnose/SKILL.md", self.SKILL.replace("  [WHAT] old words here\n  [TRIGGER] bug\n", f"  {text}\n"))

    def test_description_only_change_and_version_bump_pass(self):
        def mutate():
            self.new_desc("Find the cause before patching. Use when behaviour is wrong or slow.")()
            self.write(".claude-plugin/plugin.json", '{\n  "name": "x",\n  "version": "1.1.0",\n  "skills": []\n}\n')
        code, out = self.verdict(mutate)
        self.assertEqual(code, 0, out)
        self.assertIn("changed descriptions: 1", out)
        self.assertIn(self.base, out)

    def test_every_other_change_fails(self):
        cases = {
            "body": lambda: self.write("skills/workflow/diagnose/SKILL.md", self.SKILL + "rule two\n"),
            "other frontmatter key": lambda: self.write("skills/workflow/diagnose/SKILL.md", self.SKILL.replace("allowed-tools: Read", "allowed-tools: Read, Bash")),
            "name": lambda: self.write("skills/workflow/diagnose/SKILL.md", self.SKILL.replace("name: diagnose", "name: debug")),
            "key added": lambda: self.write("skills/workflow/diagnose/SKILL.md", self.SKILL.replace("allowed-tools: Read", "allowed-tools: Read\nmodel: opus")),
            "agent file": lambda: self.write("agents/developer.md", "---\nname: developer\n---\nbody absorbing probe words\n"),
            "output style added": lambda: self.write("output-styles/oliver.md", "x\n"),
            "skill deleted": lambda: (self.root / "skills/ops/slo/SKILL.md").unlink(),
            "skill renamed": lambda: (self.root / "skills/ops/slo").rename(self.root / "skills/ops/slo2"),
            "reference under a skill": lambda: self.write("skills/workflow/diagnose/references/x.md", "x\n"),
            "plugin.json beyond version": lambda: self.write(".claude-plugin/plugin.json", '{\n  "name": "y",\n  "version": "1.0.0",\n  "skills": []\n}\n'),
        }
        for name, mutate in cases.items():
            code, out = self.verdict(mutate)
            self.assertEqual(code, 1, f"{name} must be refused:\n{out}")

    def test_leak_lint_against_public_paraphrases_only_and_external_set(self):
        code, out = self.verdict(self.new_desc("ใช้เมื่อ เครื่องผมรันได้ปกติ แต่ที่อื่นไม่ได้"))
        self.assertEqual(code, 1, out); self.assertIn("LEAK", out); self.assertIn("P28", out)
        code, out = self.verdict(self.new_desc("Use when it works on my machine but not elsewhere."))
        self.assertEqual(code, 1, out); self.assertIn("works on my", out)
        code, out = self.verdict(self.new_desc("frozen legacy prompt words are fine: P05 is not a paraphrase probe"))
        self.assertEqual(code, 0, out)
        held = self.root.parent / (self.root.name + "-held.json")
        self.addCleanup(lambda: held.exists() and held.unlink())
        held.write_text(json.dumps({"scenarios": [{"id": "H01", "prompt_text": "ลูกค้าบ่นว่าหน้าเว็บค้างตอนจ่ายเงิน"}]}), encoding="utf-8")
        clean = self.new_desc("ใช้เมื่อ หน้าเว็บค้างตอนจ่ายเงิน")
        self.assertEqual(self.verdict(clean)[0], 0)
        code, out = self.verdict(clean, str(held))
        self.assertEqual(code, 1, out); self.assertIn("H01", out)

    def test_bad_ref_is_usage_error(self):
        p = subprocess.run(["bash", str(ROOT / "eval/check-arm-diff.sh"), "nope", "HEAD"], capture_output=True, text=True,
                           env=dict(os.environ, CHECK_ROOT=str(self.root)))
        self.assertEqual(p.returncode, 2)


class ScenarioDataTest(unittest.TestCase):
    def test_ids_prompts_and_names_resolve(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib
        trc = importlib.import_module("team-run-check")
        ids = [s["id"] for s in NEW]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"E01"} | {f"P{n:02d}" for n in range(1, 16)} <= set(ids))
        skills = {p.parent.name for p in ROOT.glob("skills/*/*/SKILL.md")}
        agents = {p.stem for p in ROOT.glob("agents/*.md")}
        workflow_ops_ui = {p.parent.name for g in ("workflow", "ops", "ui") for p in ROOT.glob(f"skills/{g}/*/SKILL.md")}
        for s in NEW:
            self.assertFalse(set(s["expected"]) - trc.EXPECTED_FIELDS, s["id"])
            self.assertIn("## Prompt", (ROOT / s["prompt"]).read_text(encoding="utf-8"), s["id"])
            for name in s["expected"].get("skills", []) + s["expected"].get("must_not_load", []):
                self.assertIn(name, skills, f'{s["id"]}: unknown skill {name}')
            routes = s["expected"].get("route_any", [])
            exp = s["expected"]
            if routes:   # a probe that can hardly fail measures nothing
                self.assertLessEqual(len(routes), 2, f'{s["id"]}: accept-list too wide')
                self.assertLessEqual(sum(r.startswith("agent:") for r in routes), 1, s["id"])
            if s.get("kind") == "probe" and not s.get("not_applicable"):
                self.assertIn(s.get("class"), ("description-sensitive", "control-agent-table", "negative"), s["id"])
                # every probe can FAIL for a positive reason (no vacuous PASS on "nothing happened") ...
                # exception (validator ruling 09 §B): P38/P39 may be answered directly OR by one legitimate owner
                # (docs / UX copy), so they keep max_spawns 1 + must_not_dispatch and no required route.
                if s["id"] not in ("P38", "P39"):
                    self.assertTrue(routes or exp.get("max_spawns") == 0, f'{s["id"]}: needs route_any or max_spawns 0')
                else:
                    self.assertTrue(exp.get("max_spawns") == 1 and exp.get("must_not_dispatch"), s["id"])
                # ... and for over-triggering: all unrelated workflow/ops/ui skills are forbidden loads
                target = {r[6:] for r in routes if r.startswith("skill:")}
                unrelated = workflow_ops_ui - target - set(s.get("related", [])) - {"ask", "meeting"}
                self.assertFalse(unrelated - set(exp.get("must_not_load", [])), f'{s["id"]}: must_not_load misses {unrelated - set(exp.get("must_not_load", []))}')
                if s["class"] != "negative":
                    self.assertEqual(exp.get("max_skills"), 2, s["id"])
                    self.assertLessEqual(len(s.get("related", [])), 1, f'{s["id"]}: at most one allowed co-load')
            for name in [r[6:] for r in routes if r.startswith("skill:")]:
                self.assertIn(name, skills, f'{s["id"]}: unknown skill {name}')
            for name in s["expected"].get("agents", []) + [r[6:] for r in routes if r.startswith("agent:")]:
                self.assertIn(name, agents, f'{s["id"]}: unknown agent {name}')
            for glob in s["expected"].get("must_not_dispatch", []):
                self.assertTrue(any(__import__("fnmatch").fnmatchcase(a, glob) for a in agents), f'{s["id"]}: {glob}')


if __name__ == "__main__":
    unittest.main()
