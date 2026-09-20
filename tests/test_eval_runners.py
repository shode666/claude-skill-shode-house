"""Wiring tests for eval/run-e01.sh and eval/run-probes.sh against tests/fake_claude.py.
No model is called. These prove directory refusal, fixture-outside-repo, evidence files,
meta.json fields and scorer exit propagation -- NOT the shape of a real `claude -p` trace."""
import json, os, shutil, stat, subprocess, sys, tempfile, unittest
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
        self.env = dict(os.environ, CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"))
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

    def test_probes_summary_fail_is_data_unscorable_is_exit_2(self):
        out = self.tmp / "probes"
        done = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P03")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)   # P03 FAILs (stub loads diagnose): data
        rows = [r.split("\t") for r in (out / "SUMMARY.tsv").read_text().splitlines()]
        self.assertEqual(rows[0], ["id", "exit", "first_skill", "first_agent", "seconds"])
        self.assertEqual([(r[0], r[1], r[2]) for r in rows[1:]],
                         [("P02", "0", "shode-house:diagnose"), ("P03", "1", "shode-house:diagnose")])
        self.assertIn("max-turns=3", json.loads((out / "P02/meta.json").read_text())["flags"])
        broken = self.run_script("run-probes.sh", "sonnet", str(self.tmp / "p2"), PROBE_IDS="P02", FAKE_MODE="noresult")
        self.assertEqual(broken.returncode, 2)


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
        for s in NEW:
            self.assertFalse(set(s["expected"]) - trc.EXPECTED_FIELDS, s["id"])
            self.assertIn("## Prompt", (ROOT / s["prompt"]).read_text(encoding="utf-8"), s["id"])
            for name in s["expected"].get("skills", []) + s["expected"].get("must_not_load", []):
                self.assertIn(name, skills, f'{s["id"]}: unknown skill {name}')
            for name in s["expected"].get("agents", []):
                self.assertIn(name, agents, f'{s["id"]}: unknown agent {name}')
            for glob in s["expected"].get("must_not_dispatch", []):
                self.assertTrue(any(__import__("fnmatch").fnmatchcase(a, glob) for a in agents), f'{s["id"]}: {glob}')


if __name__ == "__main__":
    unittest.main()
