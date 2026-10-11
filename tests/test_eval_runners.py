"""Wiring tests for eval/run-e01.sh, eval/run-probes.sh and eval/run-core.sh (incl. its OD-2 A+ redaction) against tests/fake_claude.py.
No model is called. These prove directory refusal, fixture-outside-repo, evidence files,
meta.json fields and scorer exit propagation -- NOT the shape of a real `claude -p` trace."""
import csv, inspect, json, os, re, shutil, stat, subprocess, sys, tempfile, time, unittest, unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = json.loads((ROOT / "eval/scenarios/golden.json").read_text(encoding="utf-8"))["scenarios"]
NEW = [s for s in GOLDEN if "expected" in s]

# Every variable the runners (eval/run-lib.sh, run-e01.sh, run-probes.sh, run-core.sh, core-set.sh), the scripts they
# call (check-freeze.sh, check-arm-diff.sh, scripts/eval-fixture.sh) and the stub (tests/fake_claude.py) read from the
# environment. A caller's value (an exported PLUGIN_REF / BASE_REF from a live eval session) must not steer a fixture
# run: each test sets the ones it needs explicitly. GIT_* variables that locate a repository (set by git when a hook
# runs) would point the runners' and fixtures' git at the caller's repository. Config isolation the caller chose
# (HOME, XDG_CONFIG_HOME, GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM) and TMPDIR are kept.
EVAL_ENV = ("CLAUDE_BIN", "PLUGIN_REF", "BASE_REF", "ARM_SCOPE", "PROBE_FILE", "PROBE_IDS", "REPEATS", "MAX_RETRY",
            "ALLOW_UNFROZEN", "PROBE_BLOCK_SPAWN", "RUN_TIMEOUT_S", "MAX_BUDGET_USD", "CORE_IDS", "CORE_LABEL",
            "CORE_FILE", "CORE_E01", "CORE_FREEZE", "FREEZE_ROOT", "CHECK_ROOT", "FIXTURE_TODAY",
            "FAKE_MODE", "FAKE_INFRA_ON", "FAKE_SKILL", "FAKE_PLAN_MODEL", "FAKE_PLAN_DOMAIN")
GIT_REPO_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX")


def fixture_env(**extra):
    """The caller's environment minus every eval knob and repository-locating git variable, plus `extra` (hermetic)."""
    env = {k: v for k, v in os.environ.items() if k not in EVAL_ENV + GIT_REPO_ENV}
    env.update(extra)
    return env


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash + git")
class RunnerWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shode-runner-test.")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        stub = self.tmp / "claude"   # wrapper: independent of the tracked exec bit
        stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "t").mkdir()
        self.env = fixture_env(CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"), ALLOW_UNFROZEN="1")

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
        before = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, env=fixture_env()).stdout
        out = self.tmp / "held"
        done = self.run_script("run-probes.sh", "sonnet", str(out), PROBE_FILE=str(ext / "set.json"))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((out / "H01/r1/prompt.txt").read_text(encoding="utf-8"), "อะไรสักอย่างที่ไม่อยู่ใน repo")
        self.assertEqual((out / "H02/r1/prompt.txt").read_text(encoding="utf-8"), "held-out two")
        fixture = lambda i: Path(json.loads((out / i / "r1/meta.json").read_text())["fixture"]) / "web/refund-history.html"
        self.assertEqual((fixture("H01").is_file(), fixture("H02").is_file()), (True, False), "fixture_flags honoured for external sets")
        agg = {r["id"]: r for r in csv.DictReader((out / "AGG.tsv").open(encoding="utf-8"), delimiter="\t")}
        self.assertEqual((agg["H01"]["k_pass/N"], agg["H01"]["class"], agg["H02"]["k_pass/N"]), ("1/1", "held-out", "0/1"))
        after = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, env=fixture_env()).stdout
        self.assertEqual(before, after, "nothing from the external set lands in the repo")

    def test_ui_fixture_flag_only_for_ui_probes(self):
        out = self.tmp / "ui"
        self.assertEqual(self.run_script("run-probes.sh", "sonnet", str(out), PROBE_IDS="P02 P07").returncode, 0)
        has_ui = lambda i: (Path(json.loads((out / i / "r1/meta.json").read_text())["fixture"]) / "web/refund-history.html").is_file()
        self.assertEqual((has_ui("P02"), has_ui("P07")), (False, True))


# OD-2 A+ (UD U23): eval/run-core.sh redacts the derived evidence of every run. The planted credentials are built by
# concatenation so no credential-shaped literal sits in this file.
TOKEN = "ghp" + "_" + "Zq9Lm2Np4Rs6Tv8Wx0Yb1Cd3"
DERIVED = ("tools-seen.txt", "score.txt", "score.json", "meta.json")


def sha256_of(path):
    return __import__("hashlib").sha256(Path(path).read_bytes()).hexdigest()


def load_redactor():
    import importlib.util
    spec = importlib.util.spec_from_file_location("redact_derived", ROOT / "eval/redact_derived.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash + git")
class CoreRedactionLiveLibTest(unittest.TestCase):
    """The real run-core.sh + frozen run-lib.sh + frozen scorer against tests/fake_claude.py, with a credential in the
    first Skill input (it reaches tools-seen.txt, meta.json, the SUMMARY route and the console line of run_one)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shode-redact-live.")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        stub = self.tmp / "claude"
        stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "t").mkdir()
        self.env = fixture_env(CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"), ALLOW_UNFROZEN="1", CORE_IDS="E02",
                               FAKE_SKILL="diagnose --token " + TOKEN)

    def test_derived_redacted_raw_byte_exact_verdict_unchanged_owner_only(self):
        out = self.tmp / "core"
        # a permissive caller umask: owner-only modes must come from run-core.sh itself
        done = subprocess.run(["bash", "-c", 'umask 000; exec bash "$0" sonnet "$1"', str(ROOT / "eval/run-core.sh"), str(out)],
                              capture_output=True, text=True, env=self.env, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        run = out / "E02"
        raw = (run / "run.jsonl").read_bytes()
        self.assertIn(TOKEN.encode(), raw, "run.jsonl is the raw trace: byte-exact, never redacted")
        record = json.loads((run / "redaction.json").read_text(encoding="utf-8"))
        self.assertEqual(record["run_jsonl_sha256"], sha256_of(run / "run.jsonl"))
        self.assertEqual(record["derived"]["tools-seen.txt"], "redacted")
        for path in [run / n for n in DERIVED] + [out / "SUMMARY.tsv", out / "log.txt", run / "redaction.json"]:
            self.assertNotIn(TOKEN, path.read_text(encoding="utf-8"), path.name)
        self.assertNotIn(TOKEN, done.stdout + done.stderr)
        self.assertIn("<REDACTED>", (run / "tools-seen.txt").read_text(encoding="utf-8"))
        rows = list(csv.DictReader((out / "SUMMARY.tsv").open(encoding="utf-8"), delimiter="\t"))
        self.assertEqual(len(rows), 1)
        self.assertIn("<REDACTED>", rows[0]["route"])
        # the verdict: the frozen scorer re-run on the raw trace agrees with the redacted score.json and the row
        sel = dict(l.split("=", 1) for l in subprocess.run(["bash", str(ROOT / "eval/core-set.sh"), str(ROOT)],
                   capture_output=True, text=True, check=True, env=fixture_env()).stdout.splitlines())
        again = subprocess.run([sys.executable, str(ROOT / "scripts/team-run-check.py"), str(run / "run.jsonl"), "--scenario", "E02",
                                "--scenarios", sel["CORE_FILE"], "--files", str(run / "run.files"), "--json"],
                               capture_output=True, text=True, env=fixture_env())
        self.assertEqual(json.loads((run / "score.json").read_text(encoding="utf-8"))["status"], json.loads(again.stdout)["status"])
        self.assertEqual((rows[0]["exit"], rows[0]["verdict"]), (str(again.returncode), {0: "PASS", 1: "FAIL"}[again.returncode]))
        self.assertIn(f"exit={again.returncode}", (run / "score.txt").read_text(encoding="utf-8"))
        self.assertEqual(sha256_of(run / "run.jsonl"), record["run_jsonl_sha256"], "the scorer re-run did not touch it")
        # owner-only, everything the batch wrote; no marker, buffer or temporary file left behind
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        for path in out.rglob("*"):
            want = 0o700 if path.is_dir() else 0o600
            self.assertEqual(stat.S_IMODE(path.lstat().st_mode), want, str(path.relative_to(out)))
        self.assertEqual([p.name for p in out.rglob(".redact*")], [])

    def test_claude_holds_no_runner_descriptor_so_nothing_reaches_the_console_past_the_redactor(self):
        """Sentinel final F3: the console + log.txt was fd 3 of the runner, inherited by run_one's whole tree; a fake
        claude that writes a token to every descriptor above 2 it holds now finds none (bash 3.2 also leaked a saved
        copy of the console at a higher number when fd 3 was only closed for the call)."""
        report = self.tmp / "fds.txt"
        stub = self.tmp / "claude"
        stub.write_text(f"""#!/bin/sh
case " $* " in *" -p "*) "{sys.executable}" -c '
import os, sys
held = []
for fd in range(3, 1024):
    try:
        os.fstat(fd)
    except OSError:
        continue
    held.append(fd)
    try:
        os.write(fd, ("fd%d " % fd + sys.argv[2] + chr(10)).encode())
    except OSError:
        pass
open(sys.argv[1], "a").write(" ".join(map(str, held)) + chr(10))
' "{report}" "{TOKEN}" ;; esac
exec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"
""")
        env = dict(self.env, FAKE_SKILL="diagnose")
        out = self.tmp / "core-fd"
        done = subprocess.run(["bash", str(ROOT / "eval/run-core.sh"), "sonnet", str(out)],
                              capture_output=True, text=True, env=env, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(report.read_text().splitlines(), [""], "claude held a descriptor above 2: " + report.read_text())
        for path in [out / "log.txt", out / "SUMMARY.tsv"] + [out / "E02" / n for n in DERIVED]:
            self.assertNotIn(TOKEN, path.read_text(encoding="utf-8"), path.name)
        self.assertNotIn(TOKEN, done.stdout + done.stderr)


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class CoreRedactionControlTest(unittest.TestCase):
    """run-core.sh against a stub run-lib.sh whose run_one writes a credential into the raw trace, every derived file,
    FIRST_ROUTE and its console line, and can then signal the runner between that write and the redaction."""

    STUB_LIB = r"""REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCENARIOS="$REPO/eval/scenarios/golden.json"
die() { echo "!! $*" >&2; exit 3; }
utc() { echo now; }
preflight() { :; }
run_state() { if [ ! -d "$1" ]; then echo absent; elif [ -f "$1/done" ]; then echo complete; else echo incomplete; fi; }
run_one() {
  local s; s="$(cat "$REPO/secret")"; mkdir -p "$3"; echo "$1" >> "$REPO/calls.txt"
  printf '{"type": "result", "subtype": "success", "result": "%s"}\n' "$s" > "$3/run.jsonl"
  echo "core fixture $1 ready" > "$3/fixture.log"; echo x > "$3/fixture-core.sha256"
  printf '# first Skill tool_use input: {"skill": "x --token %s"}\n' "$s" > "$3/tools-seen.txt"
  printf '  X check: password=%s\n  RESULT: FAIL check\nexit=1\n' "$s" > "$3/score.txt"
  printf '{\n  "status": "FAIL",\n  "checks": {"c": {"pass": false, "detail": "Authorization: Bearer %s"}}\n}\n' "$s" > "$3/score.json"
  printf '{\n "first_skill": "x --token %s",\n "score_exit": 1\n}\n' "$s" > "$3/meta.json"
  touch "$3/done"; FIRST_ROUTE="skill:x --token $s"; SECONDS_TAKEN=1
  echo "== $1 FAIL (first skill=x --token $s)"
  [ ! -f "$REPO/baddir.$1" ] || { rm -f "$3/score.json"; mkdir "$3/score.json"; }
  if [ -f "$REPO/signal.$1" ]; then local sig; sig="$(cat "$REPO/signal.$1")"; rm -f "$REPO/signal.$1"
    case "$sig" in *-GROUP) kill -s "${sig%-GROUP}" 0 ;; *) kill -s "$sig" $$ ;; esac
    [ ! -f "$REPO/inflight.$1" ] || {   # a run still in flight when the trap fires: a child that records its pid
      /bin/sh -c 'echo $$ > "$1"; exec /bin/sleep 30.77' sh "$REPO/inflight.pid"; echo late > "$3/late"; }; fi
  return 1
}
"""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp(prefix="shode-redact-ctl.")).resolve()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        (self.repo / ".claude-plugin").mkdir()
        (self.repo / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "shode-house", "version": "4.0.0"}))
        for rel in ("eval/scenarios/core-4.0/core-4.0.json", "eval/run-core.sh", "eval/core-set.sh",
                    "eval/redact_derived.py", "eval/evidence_redact.py"):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, self.repo / rel)
        (self.repo / "eval/run-lib.sh").write_text(self.STUB_LIB)
        for freeze in ("eval/check-freeze.sh", "eval/scenarios/core-4.0/check-freeze.sh"):
            (self.repo / freeze).write_text("exit 0\n")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts/eval-fixture-core.sh").write_text("exit 0\n")
        (self.repo / "secret").write_text(TOKEN)
        self.out = self.repo / "out"

    def run_core(self, ids="E02 E03"):
        env = {"PATH": os.environ["PATH"], "HOME": str(self.repo), "CORE_IDS": ids}
        # a session of its own: a signal to the runner's whole process group (kill 0) never reaches this test
        return subprocess.run(["bash", str(self.repo / "eval/run-core.sh"), "sonnet", str(self.out)],
                              capture_output=True, text=True, env=env, timeout=120, start_new_session=True)

    def calls(self):
        p = self.repo / "calls.txt"
        return p.read_text().split() if p.exists() else []

    def rows(self):
        return list(csv.DictReader((self.out / "SUMMARY.tsv").open(encoding="utf-8"), delimiter="\t"))

    def assert_no_token(self, *paths, text=""):
        for path in paths:
            self.assertNotIn(TOKEN, Path(path).read_text(encoding="utf-8"), str(path))
        self.assertNotIn(TOKEN, text)

    def assert_sealed(self, run, raw):
        self.assertEqual((run / "run.jsonl").read_bytes(), raw, "raw trace byte-exact")
        self.assertEqual(json.loads((run / "redaction.json").read_text())["run_jsonl_sha256"], sha256_of(run / "run.jsonl"))
        self.assert_no_token(*[run / n for n in DERIVED])
        self.assertEqual(json.loads((run / "score.json").read_text())["status"], "FAIL", "verdict unchanged")
        self.assertIn("exit=1", (run / "score.txt").read_text())
        self.assertEqual(json.loads((run / "meta.json").read_text())["score_exit"], 1)

    def test_clean_batch_redacts_every_pasteable_output(self):
        done = self.run_core()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls(), ["E02", "E03"])
        for ident in ("E02", "E03"):
            self.assert_sealed(self.out / ident, (self.out / ident / "run.jsonl").read_bytes())
            self.assertIn(TOKEN.encode(), (self.out / ident / "run.jsonl").read_bytes())
        self.assert_no_token(self.out / "SUMMARY.tsv", self.out / "log.txt", text=done.stdout + done.stderr)
        self.assertEqual([(r["id"], r["verdict"], r["exit"]) for r in self.rows()], [("E02", "FAIL", "1"), ("E03", "FAIL", "1")])
        self.assertIn("first skill=x --token <REDACTED>", (self.out / "log.txt").read_text())

    def test_sigterm_between_write_and_redaction_then_resume(self):
        (self.repo / "signal.E02").write_text("TERM")
        stopped = self.run_core()
        self.assertEqual(stopped.returncode, 143, stopped.stdout + stopped.stderr)
        run = self.out / "E02"
        raw = (run / "run.jsonl").read_bytes()
        self.assertIn(TOKEN.encode(), raw)
        self.assertEqual(self.calls(), ["E02"], "nothing runs after the interruption")
        self.assertEqual(self.rows(), [], "an interrupted run is never summarised")
        self.assertTrue((self.out / ".redact-pending").is_file(), "the run stays marked not final")
        self.assertIn("is NOT final", stopped.stdout)
        self.assert_no_token(*[run / n for n in DERIVED], self.out / "log.txt", text=stopped.stdout + stopped.stderr)
        resumed = self.run_core()
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertFalse((self.out / ".redact-pending").exists())
        self.assert_sealed(run, raw)
        self.assertEqual(self.calls(), ["E02", "E03"], "E02 is complete: kept, never re-run")
        self.assert_no_token(self.out / "SUMMARY.tsv", self.out / "log.txt", text=resumed.stdout + resumed.stderr)
        self.assertIn("first skill=x --token <REDACTED>", resumed.stdout, "the buffered console output is printed redacted")

    def test_signal_to_the_whole_process_group_exits_with_its_status_not_sigpipe(self):
        """Chris final L-A: TERM or HUP to the runner's process group (a terminal hangup, kill -TERM -<pgid>) also ends
        the console tee; the notice then hit a dead pipe and SIGPIPE killed the runner (-13). It now exits 143 / 129
        (INT: 130), the run is redacted first, and the notice goes straight into log.txt when the console is gone."""
        for sig, code in (("TERM", 143), ("HUP", 129), ("INT", 130)):
            with self.subTest(sig):
                self.setUp()
                (self.repo / "signal.E02").write_text(sig + "-GROUP")
                stopped = self.run_core()
                self.assertEqual(stopped.returncode, code, stopped.stdout + stopped.stderr)
                run = self.out / "E02"
                raw = (run / "run.jsonl").read_bytes()
                self.assertIn(TOKEN.encode(), raw)
                self.assertEqual(self.calls(), ["E02"], "nothing runs after the interruption")
                self.assertEqual(self.rows(), [], "an interrupted run is never summarised")
                self.assertTrue((self.out / ".redact-pending").is_file(), "the run stays marked not final")
                self.assertIn("is NOT final (derived files redacted", (self.out / "log.txt").read_text())
                self.assert_no_token(*[run / n for n in DERIVED], self.out / "log.txt", self.out / ".redact-pending.out",
                                     text=stopped.stdout + stopped.stderr)
                resumed = self.run_core()
                self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
                self.assert_sealed(run, raw)
                self.assertEqual(self.calls(), ["E02", "E03"])
                self.assert_no_token(self.out / "SUMMARY.tsv", self.out / "log.txt", text=resumed.stdout + resumed.stderr)

    def test_a_signal_to_the_runner_alone_stops_the_run_in_flight(self):
        """Chris final-2 L-C: TERM to the runner pid only (`kill <pid>`, not the group) while run_one's job still runs a
        child. stop_run must stop that child with the job; without it the job keeps running after the runner exits
        (unattended spend up to RUN_TIMEOUT_S). The child records its own pid; only that pid is checked and killed."""
        (self.repo / "signal.E02").write_text("TERM")
        (self.repo / "inflight.E02").write_text("")
        pid_file = self.repo / "inflight.pid"

        def kill_recorded():
            try:
                os.kill(int(pid_file.read_text()), 9)
            except (OSError, ValueError):
                pass
        self.addCleanup(kill_recorded)
        stopped = self.run_core()
        self.assertEqual(stopped.returncode, 143, stopped.stdout + stopped.stderr)
        self.assertIn("is NOT final", stopped.stdout)
        time.sleep(1)
        alive = False
        if pid_file.exists():   # absent: the job was stopped before it started the child
            try:
                os.kill(int(pid_file.read_text()), 0)
                alive = True
            except OSError:
                pass
        self.assertFalse(alive, "the run in flight (a child of run_one) was not stopped")
        self.assertFalse((self.out / "E02/late").exists(), "run_one went on after the interruption")
        self.assertTrue((self.out / ".redact-pending").is_file(), "the run stays marked not final")

    def test_kill_9_between_write_and_redaction_leaves_it_marked_then_resume_redacts(self):
        (self.repo / "signal.E02").write_text("KILL")
        killed = self.run_core()
        self.assertEqual(killed.returncode, -9)
        run = self.out / "E02"
        raw = (run / "run.jsonl").read_bytes()
        self.assertEqual((self.out / ".redact-pending").read_text().strip(), "E02", "no trap ran: the marker says not final")
        self.assertFalse((run / "redaction.json").exists())
        self.assertEqual(self.rows(), [])
        self.assert_no_token(self.out / "log.txt", text=killed.stdout + killed.stderr)   # console output was buffered
        resumed = self.run_core()
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertIn("== resume:", resumed.stdout)
        self.assert_sealed(run, raw)
        self.assertFalse((self.out / ".redact-pending").exists() or (self.out / ".redact-pending.out").exists())
        self.assert_no_token(self.out / "log.txt", self.out / "SUMMARY.tsv", text=resumed.stdout + resumed.stderr)

    def test_sanitizer_failure_mid_batch_stops_fail_closed(self):
        (self.repo / "baddir.E02").write_text("")   # score.json is not a regular file: the seal cannot finish
        done = self.run_core()
        self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
        self.assertIn("STOPPED: redaction failed", done.stdout + done.stderr)   # the batch console is tee'd to log.txt
        self.assertIn("STOPPED: redaction failed", (self.out / "log.txt").read_text())
        self.assertEqual(self.calls(), ["E02"], "no further run")
        self.assertEqual(self.rows(), [], "nothing summarised")
        self.assertNotIn("core batch done", done.stdout)
        self.assertTrue((self.out / ".redact-pending").is_file())
        self.assert_no_token(self.out / "SUMMARY.tsv", self.out / "log.txt", text=done.stdout + done.stderr)

    def test_missing_or_broken_redactor_stops_before_any_run(self):
        for name, breakage in (("missing helper", lambda: (self.repo / "eval/redact_derived.py").unlink()),
                               ("broken rules", lambda: (self.repo / "eval/evidence_redact.py").write_text("raise ImportError('x')\n"))):
            with self.subTest(name):
                self.setUp()
                breakage()
                done = self.run_core()
                self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
                self.assertIn("STOPPED: redaction failed", done.stderr)
                self.assertEqual(self.calls(), [])
                self.assertFalse(self.out.exists(), "stopped before the batch directory exists")


def tree_modes(root):
    """{relative path: (lstat mode bits, is link)} of every entry under root, root itself as "."."""
    root = Path(root)
    out = {".": (stat.S_IMODE(root.lstat().st_mode), False)}
    for path in root.rglob("*"):
        st = path.lstat()
        out[str(path.relative_to(root))] = (stat.S_IMODE(st.st_mode), stat.S_ISLNK(st.st_mode))
    return out


def loosen(root):
    """What a batch begun before umask 077 looks like: dirs 0755, files 0644 (links are left alone)."""
    for path in [Path(root)] + list(Path(root).rglob("*")):
        if not path.is_symlink():
            path.chmod(0o755 if path.is_dir() else 0o644)


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class CoreOutDirLockdownTest(unittest.TestCase):
    """Resume of an existing out-dir (external review, Medium): every entry is tightened to 0700 / 0600 by descriptor
    before any run, or the batch is refused (exit 4) with nothing changed when an entry is a symlink, a special file, a
    hard-linked file, a redaction.json that is not what `seal` writes or a run.jsonl that no longer matches its
    redaction.json. run.jsonl content is never changed."""

    STUB_LIB = CoreRedactionControlTest.STUB_LIB
    setUp = CoreRedactionControlTest.setUp
    run_core = CoreRedactionControlTest.run_core
    calls = CoreRedactionControlTest.calls
    rows = CoreRedactionControlTest.rows

    def old_batch(self):
        """A finished E02 run, then every entry loosened: the state the finding describes."""
        first = self.run_core("E02")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        loosen(self.out)
        run = self.out / "E02"
        self.assertEqual(stat.S_IMODE((run / "run.jsonl").stat().st_mode), 0o644)
        return run, (run / "run.jsonl").read_bytes()

    def assert_refused_untouched(self, done, before, raw, log):
        self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
        self.assertIn("!! out-dir refused: ", done.stderr)
        self.assertIn("STOPPED: the out-dir cannot be made owner-only", done.stderr)
        self.assertNotIn(str(self.out), done.stdout + done.stderr, "static message: no path")
        self.assertNotIn(TOKEN, done.stdout + done.stderr)
        self.assertEqual(self.calls(), ["E02"], "nothing ran")
        self.assertEqual(tree_modes(self.out), before, "refused: no mode changed")
        self.assertEqual((self.out / "E02/run.jsonl").read_bytes(), raw)
        self.assertEqual((self.out / "log.txt").read_bytes(), log, "refused before the console log is opened")

    def test_resume_of_a_loose_batch_tightens_every_entry_and_keeps_run_jsonl(self):
        run, raw = self.old_batch()
        (run / "sub").mkdir()
        (run / "sub/extra.txt").write_text("x")
        loosen(self.out)
        resumed = self.run_core("E02 E03")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.calls(), ["E02", "E03"], "E02 kept, E03 ran")
        for rel, (mode, is_link) in tree_modes(self.out).items():
            self.assertFalse(is_link, rel)
            self.assertEqual(mode, 0o700 if (self.out / rel).is_dir() else 0o600, rel)
        self.assertEqual((run / "run.jsonl").read_bytes(), raw, "raw trace byte-exact")
        self.assertEqual(json.loads((run / "redaction.json").read_text())["run_jsonl_sha256"], sha256_of(run / "run.jsonl"))

    def test_a_symlink_anywhere_refuses_the_batch_and_its_target_is_untouched(self):
        for name, make in (("file link", lambda run, outside: (run / "link.txt").symlink_to(outside / "target.txt")),
                           ("dir link", lambda run, outside: (run / "linkdir").symlink_to(outside)),
                           ("dangling link", lambda run, outside: (run / "gone").symlink_to(outside / "missing")),
                           ("link at the top", lambda run, outside: (self.out / "E09").symlink_to(outside))):
            with self.subTest(name):
                self.setUp()
                outside = self.repo / "outside"
                outside.mkdir()
                (outside / "target.txt").write_text("not evidence")
                outside.chmod(0o755)
                (outside / "target.txt").chmod(0o644)
                run, raw = self.old_batch()
                make(run, outside)
                before, log = tree_modes(self.out), (self.out / "log.txt").read_bytes()
                done = self.run_core("E02 E03")
                self.assert_refused_untouched(done, before, raw, log)
                self.assertIn("symlink", done.stderr)
                self.assertEqual(stat.S_IMODE((outside / "target.txt").stat().st_mode), 0o644, "link target untouched")
                self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o755, "link target untouched")
                self.assertEqual((outside / "target.txt").read_text(), "not evidence")

    def test_special_hard_linked_or_tampered_entries_refuse_the_batch(self):
        def fifo(run):
            os.mkfifo(run / "pipe")

        def hardlink(run):
            os.link(run / "score.txt", self.repo / "score-copy.txt")

        def tamper(run):
            with open(run / "run.jsonl", "ab") as f:
                f.write(b"{}\n")

        def unreadable_file(run):
            (run / "score.txt").chmod(0o000)
            self.addCleanup((run / "score.txt").chmod, 0o600)   # runs before setUp's rmtree (cleanups are LIFO)

        def unreadable_dir(run):
            (run / "d").mkdir()
            (run / "d/inner.txt").write_text("x")
            (run / "d").chmod(0o300)   # write + search, no read: cannot be listed
            self.addCleanup((run / "d").chmod, 0o700)
        cases = [("fifo", fifo, "not a regular file"), ("hard link", hardlink, "hard link"),
                 ("run.jsonl changed", tamper, "does not match the sha256")]
        if os.geteuid() != 0:   # root reads a 0000 file and lists a 0300 directory: "unreadable" needs a non-root user
            cases += [("unreadable file", unreadable_file, "no owner access"),
                      ("unreadable dir", unreadable_dir, "no owner access")]
        for name, make, reason in cases:
            with self.subTest(name):
                self.setUp()
                run, _ = self.old_batch()
                make(run)
                raw = (run / "run.jsonl").read_bytes()
                before, log = tree_modes(self.out), (self.out / "log.txt").read_bytes()
                done = self.run_core("E02 E03")
                self.assert_refused_untouched(done, before, raw, log)
                self.assertIn(reason, done.stderr)

    def test_a_redaction_json_that_is_not_what_seal_writes_refuses_the_batch(self):
        """Every redaction.json is read, with or without a run.jsonl beside it (Sentinel 89 L1/L2). It must be an object
        whose run_jsonl_sha256 is a 64-char lowercase hex sha256 when a run.jsonl is there and null when none is (what
        `seal` writes); anything else refuses the batch in pass 1 with nothing changed and nothing run."""
        def beside(text):   # E02's own redaction.json, next to its run.jsonl
            return lambda run, sha: (run / "redaction.json").write_text(text(sha))

        def orphan(text):   # a run dir with a redaction.json and no run.jsonl
            def make(run, sha):
                (self.out / "E07").mkdir()
                (self.out / "E07/redaction.json").write_text(text(sha))
            return make

        def null_beside_tampered(run, sha):   # Sentinel case A: a null seal does not switch the hash check off
            (run / "redaction.json").write_text('{"run_jsonl_sha256": null}')
            with open(run / "run.jsonl", "ab") as f:
                f.write(b"{}\n")

        def odd_raw(make_raw):   # Chris 91 L-1: a recorded sha beside a run.jsonl that is not a regular file
            def make(run, sha):
                orphan(lambda sha: json.dumps({"run_jsonl_sha256": sha}))(run, sha)
                make_raw(self.out / "E07/run.jsonl")
            return make

        def odd_record(make_record):   # Chris 91 S-1: a redaction.json that is not a regular file is never read
            def make(run, sha):
                (self.out / "E07").mkdir()
                make_record(self.out / "E07/redaction.json")
            return make
        unparsable, invalid, missing = "does not parse", "no valid run_jsonl_sha256", "raw evidence missing"
        not_regular, too_deep = "a redaction.json is a symlink or not a regular file", "nested too deeply"
        cases = [("garbage", beside(lambda sha: "garbage"), unparsable),
                 ("empty object", beside(lambda sha: "{}"), unparsable),
                 ("array", beside(lambda sha: "[]"), unparsable),
                 ("null beside a run.jsonl", null_beside_tampered, invalid),
                 ("short sha", beside(lambda sha: json.dumps({"run_jsonl_sha256": sha[:63]})), invalid),
                 ("uppercase sha", beside(lambda sha: json.dumps({"run_jsonl_sha256": sha.upper()})), invalid),
                 ("non-hex sha", beside(lambda sha: json.dumps({"run_jsonl_sha256": "g" * 64})), invalid),
                 ("number", beside(lambda sha: '{"run_jsonl_sha256": 1}'), invalid),
                 ("unparsable, no run.jsonl", orphan(lambda sha: "garbage"), unparsable),   # Sentinel case B
                 ("sha, no run.jsonl", orphan(lambda sha: json.dumps({"run_jsonl_sha256": sha})), missing),
                 ("sha, run.jsonl is a directory", odd_raw(lambda raw: raw.mkdir()), missing),
                 ("sha, run.jsonl is a FIFO", odd_raw(os.mkfifo), missing),
                 ("redaction.json is a FIFO", odd_record(os.mkfifo), not_regular),
                 ("redaction.json is a directory", odd_record(lambda record: record.mkdir()), not_regular),
                 ("deeply nested redaction.json", orphan(lambda sha: "[" * 100000), too_deep)]   # Chris 91 S-2
        for name, make, reason in cases:
            with self.subTest(name):
                self.setUp()
                run, _ = self.old_batch()
                make(run, sha256_of(run / "run.jsonl"))
                loosen(self.out)
                raw = (run / "run.jsonl").read_bytes()
                before, log = tree_modes(self.out), (self.out / "log.txt").read_bytes()
                done = self.run_core("E02 E03")
                self.assert_refused_untouched(done, before, raw, log)
                self.assertIn(reason, done.stderr)

    def test_a_run_sealed_with_no_run_jsonl_is_accepted(self):
        """`seal` of a run dir that never got a run.jsonl records run_jsonl_sha256 null: a valid seal, tightened, not
        refused."""
        run, raw = self.old_batch()
        empty = self.out / "E07"
        empty.mkdir()
        load_redactor().seal(str(empty))
        self.assertIsNone(json.loads((empty / "redaction.json").read_text())["run_jsonl_sha256"])
        loosen(self.out)
        resumed = self.run_core("E02 E03")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.calls(), ["E02", "E03"], "E02 kept, E03 ran")
        self.assertEqual(stat.S_IMODE((empty / "redaction.json").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(empty.stat().st_mode), 0o700)
        self.assertEqual((run / "run.jsonl").read_bytes(), raw)

    def test_an_entry_swapped_for_a_link_between_check_and_chmod_is_never_followed(self):
        """TOCTOU: pass 1 sees a regular file; then, before pass 2 or between pass 2's lstat and its open, it is replaced
        by a link to a file outside. The chmod is by descriptor opened with O_NOFOLLOW and compared by inode, so the swap
        fails the lockdown and the outside file keeps its mode and content."""
        for when in ("before pass 2", "between lstat and open"):
            with self.subTest(when):
                mod = load_redactor()
                root = Path(tempfile.mkdtemp(prefix="batch.", dir=self.repo))
                (root / "E02").mkdir()
                victim = root / "E02/run.jsonl"
                victim.write_text('{"type": "result"}\n')
                outside = root.parent / (root.name + "-elsewhere")
                outside.write_text("x")
                outside.chmod(0o644)
                loosen(root)
                state = {"pass2": False, "swapped": False}
                real_walk, real_check = mod._walk, mod._check_entry

                def swap():
                    if not state["swapped"]:
                        victim.unlink()
                        victim.symlink_to(outside)
                        state["swapped"] = True

                def walk(dir_fd, seen, tighten):
                    state["pass2"] = tighten
                    if tighten and when == "before pass 2":
                        swap()
                    return real_walk(dir_fd, seen, tighten)

                def check(st):
                    real_check(st)
                    if state["pass2"] and when != "before pass 2" and stat.S_ISREG(st.st_mode):
                        swap()   # the lstat just passed; the name now points elsewhere
                with unittest.mock.patch.object(mod, "_walk", side_effect=walk), \
                        unittest.mock.patch.object(mod, "_check_entry", side_effect=check):
                    with self.assertRaises(mod.LockdownRefused):
                        mod.lockdown(str(root))
                self.assertTrue(state["swapped"])
                self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o644, "never followed")
                self.assertEqual(outside.read_text(), "x")

    def test_an_entry_added_between_the_two_passes_is_refused_and_left_as_it_was(self):
        """An entry created after pass 1 is not one pass 1 recorded, so pass 2 refuses it before opening it. Behaviour
        (stated, not 'nothing changed'): the batch is refused; pass 2 has already set the out-dir to 0700 and may have
        tightened entries sorted before the new one; the new entry keeps its mode; nothing is loosened; nothing outside
        the out-dir changes."""
        mod = load_redactor()
        root = Path(tempfile.mkdtemp(prefix="batch.", dir=self.repo))
        (root / "E02").mkdir()
        (root / "E02/run.jsonl").write_text('{"type": "result"}\n')
        (root / "E02/score.txt").write_text("x")
        outside = root.parent / (root.name + "-elsewhere")
        outside.write_text("x")
        outside.chmod(0o644)
        loosen(root)
        before = tree_modes(root)
        late = root / "E02/run2.txt"   # sorts between run.jsonl and score.txt
        real_walk = mod._walk

        def walk(dir_fd, seen, tighten):
            if tighten and not late.exists():
                late.write_text("added after pass 1")
                late.chmod(0o644)
            return real_walk(dir_fd, seen, tighten)
        with unittest.mock.patch.object(mod, "_walk", side_effect=walk):
            with self.assertRaisesRegex(mod.LockdownRefused, "changed during the permission check"):
                mod.lockdown(str(root))
        self.assertEqual(stat.S_IMODE(late.stat().st_mode), 0o644, "the new entry was refused, not tightened")
        self.assertEqual(late.read_text(), "added after pass 1")
        self.assertEqual(stat.S_IMODE((root / "E02/run.jsonl").stat().st_mode), 0o600, "sorted before it: tightened")
        self.assertEqual(stat.S_IMODE((root / "E02/score.txt").stat().st_mode), 0o644, "sorted after it: untouched")
        after = tree_modes(root)
        for rel, (mode, _) in before.items():
            self.assertEqual(after[rel][0] & ~mode, 0, f"{rel}: never loosened")
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode), 0o644, "outside untouched")
        self.assertEqual(outside.read_text(), "x")


class RedactDerivedUnitTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_redactor()
        self.dir = Path(tempfile.mkdtemp(prefix="shode-redact-unit.")).resolve()
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def leftovers(self):
        return sorted(p.name for p in self.dir.iterdir() if p.name.startswith(".redact-"))

    def test_failed_replacement_leaves_the_original_and_no_partial_file(self):
        target = self.dir / "score.txt"
        original = ("  X c: password=" + TOKEN + "\nexit=1\n").encode()
        for broken in ("replace", "fsync"):
            with self.subTest(broken):
                target.write_bytes(original)
                with unittest.mock.patch.object(self.mod.os, broken, side_effect=OSError("disk full")):
                    with self.assertRaises(OSError):
                        self.mod.redact_file(str(target))
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(self.leftovers(), [])

    def test_success_is_atomic_owner_only_and_keeps_the_verdict(self):
        score = self.dir / "score.json"
        score.write_text(json.dumps({"status": "PASS", "failed": [], "checks": {"a": {"pass": True, "detail": "Bearer " + TOKEN}}},
                                    indent=2), encoding="utf-8")
        score.chmod(0o644)
        self.assertEqual(self.mod.redact_file(str(score)), "redacted")
        data = json.loads(score.read_text(encoding="utf-8"))
        self.assertEqual((data["status"], data["failed"], data["checks"]["a"]["pass"]), ("PASS", [], True))
        self.assertNotIn(TOKEN, score.read_text(encoding="utf-8"))
        self.assertEqual(stat.S_IMODE(score.stat().st_mode), 0o600)
        inode = score.stat().st_ino
        self.assertEqual(self.mod.redact_file(str(score)), "unchanged", "idempotent: a clean file is not rewritten")
        self.assertEqual(score.stat().st_ino, inode)
        self.assertEqual(self.leftovers(), [])

    def test_json_files_are_parsed_never_redacted_as_text(self):
        """Chris final L-B: score.json / meta.json take the JSON branch. As text, `"detail": "secret="` loses its closing
        quote to the redactor (invalid JSON); parsed, the file stays valid and equals redact_tree of the original."""
        er = self.mod
        for name, indent in sorted(er.JSON_INDENT.items()):
            with self.subTest(name):
                original = {"detail": "secret=", "status": "FAIL", "n": 1, "pass": False,
                            "checks": {"c": {"detail": "password=" + TOKEN}}}
                path = self.dir / name
                path.write_text(json.dumps(original, indent=indent) + "\n", encoding="utf-8")
                self.assertEqual(er.redact_file(str(path), name), "redacted")
                text = path.read_text(encoding="utf-8")
                self.assertEqual(json.loads(text), er.redact_tree(original))
                self.assertEqual(text, json.dumps(er.redact_tree(original), indent=indent, ensure_ascii=False) + "\n")
                self.assertNotIn(TOKEN, text)
                as_text = er.redact_text(json.dumps(original, indent=indent).encode()).decode()
                with self.assertRaises(ValueError, msg="control: the text path really corrupts this file"):
                    json.loads(as_text)

    def test_seal_refuses_a_raw_trace_that_changes(self):
        (self.dir / "run.jsonl").write_text('{"type": "result"}\n')
        (self.dir / "score.txt").write_text("password=" + TOKEN + "\n")
        real = self.mod.redact_file

        def tamper(path, name=None):
            with open(self.dir / "run.jsonl", "a") as f:
                f.write("x\n")
            return real(path, name)
        with unittest.mock.patch.object(self.mod, "redact_file", side_effect=tamper):
            with self.assertRaises(self.mod.RedactionError):
                self.mod.seal(str(self.dir))
        self.assertFalse((self.dir / "redaction.json").exists())

    def test_unreadable_or_odd_derived_file_fails(self):
        (self.dir / "tools-seen.txt").symlink_to(self.dir / "elsewhere")
        with self.assertRaises(self.mod.RedactionError):
            self.mod.seal(str(self.dir))
        done = subprocess.run([sys.executable, str(ROOT / "eval/redact_derived.py"), "seal", str(self.dir)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("redaction failed: RedactionError", done.stderr)

    def test_an_entry_owned_by_another_user_is_refused(self):
        """The per-entry owner rule (pass 1, and again on the opened descriptor), without needing a second account."""
        other = os.geteuid() + 1
        for kind in (stat.S_IFREG | 0o644, stat.S_IFDIR | 0o755):
            with self.subTest(oct(kind)):
                st = os.stat_result((kind, 1, 0, 1, other, 0, 0, 0, 0, 0))
                with self.assertRaisesRegex(self.mod.LockdownRefused, "not owned by the user running the batch"):
                    self.mod._check_entry(st)
        self.mod._check_entry(os.stat_result((stat.S_IFREG | 0o644, 1, 0, 1, os.geteuid(), 0, 0, 0, 0, 0)))

    def test_a_tree_nested_past_the_recursion_limit_is_refused_with_no_mode_changed(self):
        """Chris 91 S-2: the walk recurses per directory level; a tree deeper than Python's recursion limit is a static
        LockdownRefused in pass 1 (nothing changed), never a RecursionError traceback. The limit is lowered for the
        test so the tree stays small (60 levels) and fast."""
        root = self.dir / "batch"
        deep = root
        for _ in range(60):
            deep = deep / "d"
        deep.mkdir(parents=True)
        (deep / "run.jsonl").write_text('{"type": "result"}\n')
        loosen(root)
        before = tree_modes(root)
        limit = sys.getrecursionlimit()
        frames = len(inspect.stack(0))
        sys.setrecursionlimit(frames + 40)
        try:
            with self.assertRaisesRegex(self.mod.LockdownRefused, "^the out-dir or a redaction.json in it is nested too deeply$"):
                self.mod.lockdown(str(root))
        finally:
            sys.setrecursionlimit(limit)
        self.assertEqual(tree_modes(root), before, "refused in pass 1: no mode changed")

    def test_an_out_dir_owned_by_another_user_is_refused_with_no_mode_changed(self):
        """Root owner rule: with the effective uid seen as another user's, lockdown refuses at the out-dir itself
        (before pass 1) and changes no mode -- for an empty out-dir too, where no per-entry rule could fire."""
        full = self.dir / "batch"
        (full / "E02").mkdir(parents=True)
        (full / "E02/run.jsonl").write_text('{"type": "result"}\n')
        empty = self.dir / "empty"
        empty.mkdir()
        for root in (full, empty):
            with self.subTest(root.name):
                loosen(root)
                before = tree_modes(root)
                with unittest.mock.patch.object(self.mod.os, "geteuid", return_value=os.geteuid() + 1):
                    with self.assertRaisesRegex(self.mod.LockdownRefused, "the out-dir is not a directory owned"):
                        self.mod.lockdown(str(root))
                self.assertEqual(tree_modes(root), before, "refused: no mode changed")


class ToolsSeenCutTest(unittest.TestCase):
    """Sentinel final F1 + F2 against the FROZEN writer: eval/run-lib.sh `tools_seen` cuts every first-input value
    longer than 300 characters to 300 plus "..." before any redaction, and json.dumps escapes the JSON inside a value.
    Its Python body is run as is (read from run-lib.sh), the output redacted as the seal does, for every cut position."""

    SECRET = "Q7x" + "Z9pLm2Vb8Nc4Rt6Yw1Ks3Hd5Jf0Ga"
    SHAPES = {
        "json password": '{"password": "' + SECRET + '"}',
        "json api_key": '{"api_key":"' + SECRET + '"}',
        "url user:password": "https://user:" + SECRET + "@host/x",
        "postgres url": "postgres://app:" + SECRET + "@db:5432/x",
        "bearer": "Authorization: Bearer " + SECRET,
        "curl -d json": 'curl -d "{\\"password\\":\\"' + SECRET + '\\"}" h',
    }

    @classmethod
    def setUpClass(cls):
        lib = (ROOT / "eval/run-lib.sh").read_text(encoding="utf-8")
        body = re.search(r"^tools_seen\(\) \{\n  python3 - \"\$1\" <<'PY'\n(.*?)\nPY\n\}", lib, re.S | re.M)
        cls.writer = compile(body.group(1), "run-lib.sh:tools_seen", "exec")
        cls.mod = load_redactor()

    def tools_seen(self, path):
        import contextlib, io
        buf, argv = io.StringIO(), sys.argv
        sys.argv = ["-", str(path)]
        try:
            with contextlib.redirect_stdout(buf):
                exec(self.writer, {"__name__": "__main__"})
        finally:
            sys.argv = argv
        return buf.getvalue()

    def leaks(self, text):
        return any(self.SECRET[i:i + 8] in text for i in range(len(self.SECRET) - 7))

    def test_no_cut_position_leaks(self):
        tmp = Path(tempfile.mkdtemp(prefix="shode-tools-seen.")).resolve()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        trace = tmp / "run.jsonl"
        plain_leaks = copied = 0
        for label, shape in self.SHAPES.items():
            for pad in range(300):
                value = "x" * pad + " " + shape + " tail"
                event = {"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": "s", "args": value}}]}}
                trace.write_text(json.dumps(event) + "\n", encoding="utf-8")
                raw = self.tools_seen(trace).encode()
                copied += self.leaks(raw.decode())
                clean = (self.mod.redacted_bytes("tools-seen.txt", raw) or raw).decode()
                self.assertFalse(self.leaks(clean), (label, pad, clean))
                if len(value) > 300:   # the cut marker is kept (or redacted with a value cut to nothing: `"pw": ...`)
                    self.assertRegex(clean, r'(\.\.\.|<REDACTED>)"\}\n', "the cut marker is kept")
                plain_leaks += self.leaks(self.mod.redact_text(raw).decode())
        self.assertGreater(copied, len(self.SHAPES) * 250, "control: the frozen writer copies the credential")
        self.assertGreater(plain_leaks, 0, "control: redacting the line as plain text leaves some cut credentials")

    def test_a_cut_value_is_redacted_up_to_the_cut_and_keeps_its_marker(self):
        """Parsing alone already lets the end-of-string rules see a cut value; the marker is then part of what they
        replace. Redacting up to the cut keeps "..." visible, so a reader still sees the value was cut."""
        er, part = self.mod, self.SECRET[:12]
        for value, want in (('{"password": "' + part + "...", '{"password": <REDACTED>...'),
                            ("https://user:" + part + "...", "https://<REDACTED>..."),
                            ("Authorization: Bearer " + part + "...", "Authorization: <REDACTED>..."),
                            ('{"password": ...', '{"password": <REDACTED>'),       # cut to nothing: the marker goes
                            ("x" * 20 + "...", "x" * 20 + "...")):
            self.assertEqual(er.redact_cut(value), want, value)
            self.assertNotIn(part, er.redact(value))
        self.assertEqual(er.redact('{"password": "' + part + "..."), '{"password": <REDACTED>', "control: plain loses it")

    def test_lines_that_are_not_a_first_input_or_do_not_parse_are_redacted_as_text(self):
        er = self.mod
        text = ("# event types: {'assistant': 1}\n# first Skill tool_use input: NOT SEEN\n"
                "# first Task tool_use input: {broken password=" + self.SECRET + "\n"
                '# init.model: "password=' + self.SECRET + '"\n')
        clean = er.redacted_bytes("tools-seen.txt", text.encode()).decode()
        self.assertFalse(self.leaks(clean))
        self.assertIn("# first Skill tool_use input: NOT SEEN\n", clean)
        self.assertIsNone(er.redacted_bytes("tools-seen.txt", b"# first Agent tool_use input: {\"a\": \"b...\"}\n"),
                          "nothing to redact: the file is not rewritten")


class FreezeTest(unittest.TestCase):
    def check(self, root=None, *args):
        env = fixture_env(**({"FREEZE_ROOT": str(root)} if root else {}))
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
        self.write("agents/build.md", "---\nname: developer\n---\nbody\n")
        self.write(".claude-plugin/plugin.json", '{\n  "name": "x",\n  "version": "1.0.0",\n  "skills": []\n}\n')
        self.write("eval/prompts/probes/P28.md", "# P28\n\n## Prompt\n\n```\nเครื่องผมรันได้ปกติแต่เครื่องเพื่อนพังเป็นบางครั้ง works on my laptop only\n```\n")
        self.write("eval/prompts/probes/P05.md", "# P05\n\n## Prompt\n\n```\nfrozen legacy prompt words here\n```\n")
        self.base = self.commit("base")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=True,
                              env=fixture_env()).stdout.strip()

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
                           env=fixture_env(CHECK_ROOT=str(self.root)))
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
            "agent file": lambda: self.write("agents/build.md", "---\nname: developer\n---\nbody absorbing probe words\n"),
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
                           env=fixture_env(CHECK_ROOT=str(self.root)))
        self.assertEqual(p.returncode, 2)


class HermeticEnvTest(unittest.TestCase):
    # read with a default, but set by the runner itself before use (TMPDIR / HOME: kept on purpose, see EVAL_ENV)
    NOT_KNOBS = {"TMPDIR", "HOME", "DEST", "FIRST_ROUTE", "SECONDS_TAKEN"}
    FILES = ("eval/run-lib.sh", "eval/run-e01.sh", "eval/run-probes.sh", "eval/run-core.sh", "eval/core-set.sh",
             "eval/check-freeze.sh", "eval/check-arm-diff.sh", "scripts/eval-fixture.sh", "tests/fake_claude.py",
             "eval/redact_derived.py")

    def test_every_variable_the_runners_read_is_stripped(self):
        read = set()
        for rel in self.FILES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            read |= set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*):[-=?]", text))
            read |= set(re.findall(r"os\.environ\.get\(\"([A-Z_][A-Z0-9_]*)\"", text))
        self.assertFalse(read - self.NOT_KNOBS - set(EVAL_ENV), "add to EVAL_ENV")

    def test_a_callers_knobs_do_not_reach_a_fixture_run(self):
        junk = {k: "junk-" + k.lower() for k in EVAL_ENV + GIT_REPO_ENV}
        with unittest.mock.patch.dict(os.environ, junk):
            env = fixture_env(CHECK_ROOT="/x")
        self.assertEqual(set(), (set(junk) - {"CHECK_ROOT"}) & set(env))
        self.assertEqual(env["CHECK_ROOT"], "/x")
        for kept in ("HOME", "PATH"):
            if kept in os.environ:
                self.assertEqual(env[kept], os.environ[kept])


OWNERSHIP = ROOT / "skills/discipline/shode-house-routing/ownership.md"


def formerly_ids(retired, text=None):
    """Retired ids the frozen P01..P47 battery may still name: only those listed in ownership.md § Formerly (4.0.0 id column)."""
    text = OWNERSHIP.read_text(encoding="utf-8") if text is None else text
    table = text.split("## Formerly", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
    listed = set()
    for row in table.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if row.startswith("|") and len(cells) >= 2:
            if re.fullmatch(r"[a-z][a-z-]*", cells[1]):
                listed.add(cells[1])
            listed.update(re.findall(r"`([a-z][a-z-]*)`", cells[1]))
    return retired & listed


class ScenarioDataTest(unittest.TestCase):
    def test_retired_ids_in_the_frozen_battery_must_be_in_the_formerly_table(self):
        sys.path.insert(0, str(ROOT / "tests"))
        from test_team_package import RETIRED
        retired = {Path(k).stem for k in RETIRED if k.startswith("agents/")}
        listed = formerly_ids(retired)
        self.assertEqual(retired, listed, "every retired id must have a Formerly row")
        # an id that is neither live nor a Formerly row is rejected; a Formerly row without the id is not accepted
        table = OWNERSHIP.read_text(encoding="utf-8")
        self.assertNotIn("ghost-expert", formerly_ids(retired | {"ghost-expert"}, table))
        self.assertNotIn("fintech-expert", formerly_ids(retired, table.replace("| fintech-expert |", "| gone |")))

    def test_ids_prompts_and_names_resolve(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib
        trc = importlib.import_module("team-run-check")
        ids = [s["id"] for s in NEW]
        self.assertEqual(len(ids), len(set(ids)))
        # E01 is scored from the checkout's core set (eval/core-set.sh, the selector the runners use): at 4.x that is
        # core-4.0's E01, whose must_not_dispatch drops the retired `orchestrator` type; golden.json stays frozen
        sel = dict(l.split("=", 1) for l in subprocess.run(["bash", str(ROOT / "eval/core-set.sh"), str(ROOT)],
                   capture_output=True, text=True, check=True, env=fixture_env()).stdout.splitlines())
        e01 = next(s for s in json.loads(Path(sel["CORE_E01"]).read_text(encoding="utf-8"))["scenarios"] if s["id"] == "E01")
        scenarios = [e01 if s["id"] == "E01" else s for s in NEW]
        self.assertEqual(ids, [s["id"] for s in scenarios])
        self.assertTrue({"E01"} | {f"P{n:02d}" for n in range(1, 16)} <= set(ids))
        skills = {p.parent.name for p in ROOT.glob("skills/*/*/SKILL.md")}
        agents = {p.stem for p in ROOT.glob("agents/*.md")}
        sys.path.insert(0, str(ROOT / "tests"))
        from test_team_package import RETIRED
        retired = formerly_ids({Path(k).stem for k in RETIRED if k.startswith("agents/")})
        workflow_ops_ui = {p.parent.name for g in ("workflow", "ops", "ui") for p in ROOT.glob(f"skills/{g}/*/SKILL.md")}
        for s in scenarios:
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
                # golden.json is the frozen 3.17 probe battery: at 4.0.1 its agent names are the 18 retired 4.0.0 ids
                # (a retired id names a type, not a typo); the strict live-type check of the selected core set (core-4.0.1,
                # E16..E18) is tests/test_core_scenarios.py
                self.assertTrue(name in agents or name in retired, f'{s["id"]}: unknown agent {name} (neither live nor in ownership.md Formerly)')
            for glob in s["expected"].get("must_not_dispatch", []):
                # a retired agent type (tests/test_team_package.py RETIRED, e.g. `orchestrator` at 4.0.0) stays a valid
                # must-not-dispatch name in the frozen 3.17 probe files: it names a type, not a typo
                self.assertTrue(any(__import__("fnmatch").fnmatchcase(a, glob) for a in agents | retired),
                                f'{s["id"]}: {glob}')


if __name__ == "__main__":
    unittest.main()
