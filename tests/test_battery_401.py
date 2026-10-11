"""4.0.1 routing-probe battery (eval/scenarios/battery-4.0.1/, eval/run-battery-4.0.1.sh): P01..P47 mapped to the 6 types, additive to the
frozen baseline. No model is called: the derivation, the freeze, the mapping and the runner wiring are proved offline (the runner against
tests/fake_claude.py). NOTHING here is a measurement of a model."""
import hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "eval/scenarios/battery-4.0.1"
GOLDEN = json.loads((ROOT / "eval/scenarios/golden.json").read_text(encoding="utf-8"))["scenarios"]
PROBES = [s for s in GOLDEN if s.get("kind") == "probe"]
BATTERY = json.loads((D / "battery-4.0.1.json").read_text(encoding="utf-8"))
SCEN = {s["id"]: s for s in BATTERY["scenarios"]}
TYPES = {"plan", "build", "verify", "operate", "secure", "design"}
RETIRED = {"product-manager", "business-analyst", "solution-architect", "staff-engineer", "developer", "ux-ui-designer", "code-reviewer",
           "qa-engineer", "security-engineer", "devops-engineer", "sre-engineer", "orchestrator", "fintech-expert", "erp-expert",
           "sap-expert", "trading-expert", "insurance-expert", "booking-expert", "ecommerce-expert", "*-expert"}
EVAL_ENV = ("CLAUDE_BIN", "PLUGIN_REF", "BASE_REF", "ARM_SCOPE", "PROBE_FILE", "PROBE_IDS", "REPEATS", "MAX_RETRY", "ALLOW_UNFROZEN",
            "PROBE_BLOCK_SPAWN", "RUN_TIMEOUT_S", "MAX_BUDGET_USD", "FREEZE_ROOT", "CHECK_ROOT", "FAKE_MODE", "FAKE_INFRA_ON", "FAKE_SKILL", "FAKE_PLAN_MODEL", "FAKE_PLAN_DOMAIN",
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_NAMESPACE", "GIT_PREFIX")


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in EVAL_ENV}
    env.update(extra)
    return env


def derive(root, **env):
    return subprocess.run(["bash", str(root / "eval/scenarios/battery-4.0.1/check-freeze.sh"), *env.pop("args", [])], capture_output=True,
                          text=True, env=clean_env(**env))


class DerivationTest(unittest.TestCase):
    def test_freeze_and_derivation_are_green_and_the_old_freezes_are_untouched(self):
        for script in ("eval/scenarios/battery-4.0.1/check-freeze.sh", "eval/check-freeze.sh", "eval/scenarios/core-4.0/check-freeze.sh",
                       "eval/shape-baseline/check-freeze.sh", "eval/scenarios/core-4.0.1/check-freeze.sh"):
            r = subprocess.run(["bash", str(ROOT / script)], capture_output=True, text=True, env=clean_env())
            self.assertEqual(0, r.returncode, script + r.stdout + r.stderr)
        manifest = (D / "FREEZE.sha256").read_text(encoding="utf-8")
        for f in ("battery-4.0.1.json", "README.md", "check-freeze.sh", "check-domain.py"):
            self.assertIn(f"eval/scenarios/battery-4.0.1/{f}", manifest)
        self.assertIn("eval/run-battery-4.0.1.sh", manifest)
        old = (ROOT / "eval/FREEZE.sha256").read_text(encoding="utf-8")
        for pinned in ("eval/scenarios/golden.json", "eval/run-lib.sh", "eval/run-probes.sh", "eval/prompts/probes/P01.md"):
            self.assertIn(pinned, old)
        self.assertNotIn("battery-4.0.1", old)       # the old manifest was not extended: the baseline stays what it was

    def test_same_47_probes_prompts_and_scorer_fields_as_the_baseline(self):
        self.assertEqual([f"P{n:02d}" for n in range(1, 48)], [s["id"] for s in BATTERY["scenarios"]])
        self.assertEqual([s["id"] for s in PROBES], [s["id"] for s in BATTERY["scenarios"]])
        self.assertEqual(hash_file(ROOT / "eval/scenarios/golden.json"), BATTERY["derived_from"]["eval/scenarios/golden.json"])
        for old in PROBES:
            new = SCEN[old["id"]]
            for key in ("kind", "class", "desc", "prompt", "max_turns", "source", "related", "fixture_flags", "not_applicable"):
                self.assertEqual(old.get(key), new.get(key), f'{old["id"]}.{key}')
            self.assertEqual("eval/prompts/probes/" + old["id"] + ".md", new["prompt"])
            for key in ("skills", "must_not_load", "max_skills", "max_spawns"):
                self.assertEqual(old["expected"].get(key), new["expected"].get(key), f'{old["id"]}.expected.{key}')
        self.assertEqual("P21", next(i for i, s in SCEN.items() if s.get("not_applicable")))

    def test_expected_names_only_live_types_and_no_retired_id(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib
        trc = importlib.import_module("team-run-check")
        for ident, s in SCEN.items():
            exp = s["expected"]
            self.assertFalse(set(exp) - trc.EXPECTED_FIELDS, ident)
            routes = [r[6:] for r in exp.get("route_any", []) if r.startswith("agent:")]
            self.assertLessEqual(set(routes) | set(exp.get("must_not_dispatch", [])), TYPES, ident)
            self.assertFalse(set(exp.get("must_not_dispatch", [])) & set(routes), f"{ident}: a type is required and forbidden")
            self.assertLessEqual(len(routes), 1, ident)
            for name in list(exp.get("must_not_dispatch", [])) + routes:
                self.assertNotIn(name, RETIRED, ident)

    def test_every_applicable_probe_can_fail_for_a_positive_reason(self):
        for ident, s in SCEN.items():
            exp = s["expected"]
            if s.get("not_applicable"):
                continue
            if ident in ("P38", "P39"):       # validator ruling 09 B: answered directly or by one owner
                self.assertTrue(exp.get("max_spawns") == 1 and exp.get("must_not_dispatch"), ident)
            else:
                self.assertTrue(exp.get("route_any") or exp.get("max_spawns") == 0, ident)

    def test_type_mode_and_domain_fields_cover_every_probe(self):
        for ident, s in SCEN.items():
            self.assertIn(s["type_4_0_1"], TYPES | {"-"}, ident)
            self.assertTrue(s["mode_4_0_1"], ident)
            routed = [r[6:] for r in s["expected"].get("route_any", []) if r.startswith("agent:")]
            self.assertEqual(routed[0] if routed else "-", s["type_4_0_1"], ident)
        self.assertEqual({"P15": "fintech", "P23": "trading", "P24": "insurance", "P42": "erp", "P43": "sap", "P44": "booking", "P45": "ecommerce"},
                         {i: s["domain_4_0_1"] for i, s in SCEN.items() if "domain_4_0_1" in s})
        self.assertEqual({"opus": ["fintech", "sap", "trading", "insurance"], "default": ["erp", "booking", "ecommerce"]}, BATTERY["domain_tier"])

    def test_the_mapping_of_the_probes_that_change_shape(self):
        e = lambda i: SCEN[i]["expected"]
        self.assertEqual((["skill:incident", "agent:operate"], ["build"]), (e("P03")["route_any"], e("P03")["must_not_dispatch"]))
        self.assertEqual((["agent:plan"], []), (e("P15")["route_any"], e("P15")["must_not_dispatch"]))   # the six other experts are plan too
        self.assertEqual(["agent:build"], e("P41")["route_any"])                   # staff-grade brief
        self.assertEqual(["plan"], e("P41")["must_not_dispatch"])                  # developer == build: dropped
        self.assertTrue(any("developer" in d for d in SCEN["P41"]["dropped_4_0_1"]))
        self.assertEqual(["agent:plan"], e("P40")["route_any"])
        self.assertEqual(["build"], e("P40")["must_not_dispatch"])
        self.assertEqual([], e("P10")["must_not_dispatch"])                        # orchestrator is the router, not a spawn
        self.assertEqual(["plan"], e("P46")["must_not_dispatch"])                  # build alone, no domain or discovery spawn
        self.assertEqual(["plan"], e("P20")["must_not_dispatch"])
        self.assertEqual(["operate"], e("P38")["must_not_dispatch"])
        self.assertEqual(["build", "verify"], e("P39")["must_not_dispatch"])
        self.assertEqual(["skill:dev-gate", "agent:build"], e("P01")["route_any"])
        self.assertEqual("-", SCEN["P02"]["type_4_0_1"])                           # skill-only route


def hash_file(p):
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


class FreezeTamperTest(unittest.TestCase):
    """The new manifest fails on any change, a missing file and a battery that is not the stated derivation."""
    def tree(self):
        tmp = Path(tempfile.mkdtemp(prefix="shode-battery.")).resolve()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for rel in ("eval/scenarios/golden.json", "eval/run-battery-4.0.1.sh", *(f"eval/scenarios/battery-4.0.1/{n}" for n in
                    ("battery-4.0.1.json", "README.md", "check-freeze.sh", "check-domain.py", "FREEZE.sha256"))):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, tmp / rel)
        return tmp

    def test_green_changed_missing_unlisted_and_bad_derivation(self):
        t = self.tree()
        r = derive(t)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("battery-4.0.1 freeze OK: 5 files, derivation OK", r.stdout)
        runner = t / "eval/run-battery-4.0.1.sh"
        runner.write_text(runner.read_text() + "\n# tampered\n")
        r = derive(t)
        self.assertEqual(1, r.returncode)
        self.assertIn("CHANGED eval/run-battery-4.0.1.sh", r.stdout)
        shutil.copy2(ROOT / "eval/run-battery-4.0.1.sh", runner)
        (t / "eval/scenarios/battery-4.0.1/check-domain.py").unlink()
        self.assertIn("MISSING eval/scenarios/battery-4.0.1/check-domain.py", derive(t).stdout)
        shutil.copy2(D / "check-domain.py", t / "eval/scenarios/battery-4.0.1/check-domain.py")
        golden = t / "eval/scenarios/golden.json"
        golden.write_text(golden.read_text().replace("trig-tdd", "trig-tdd2", 1))
        r = derive(t)
        self.assertEqual(1, r.returncode)
        self.assertIn("DERIVATION", r.stdout)
        shutil.copy2(ROOT / "eval/scenarios/golden.json", golden)
        manifest = t / "eval/scenarios/battery-4.0.1/FREEZE.sha256"
        manifest.write_text("".join(manifest.read_text().splitlines(True)[1:]))
        self.assertIn("UNLISTED eval/scenarios/battery-4.0.1/battery-4.0.1.json", derive(t).stdout)

    def test_a_battery_edited_by_hand_is_caught_even_if_the_manifest_is_regenerated_from_it(self):
        t = self.tree()
        b = t / "eval/scenarios/battery-4.0.1/battery-4.0.1.json"
        b.write_text(b.read_text().replace('"agent:operate"', '"agent:build"', 1))
        manifest = t / "eval/scenarios/battery-4.0.1/FREEZE.sha256"
        lines = []
        for line in manifest.read_text().splitlines():
            sha, rel = line.split("  ", 1)
            lines.append(f"{hash_file(t / rel)}  {rel}")
        manifest.write_text("\n".join(lines) + "\n")
        r = derive(t)
        self.assertEqual(1, r.returncode)
        self.assertEqual("DERIVATION battery-4.0.1.json is not the stated rule applied to the frozen golden.json", r.stdout.strip())


def trace(spawns, final="ok"):
    ev = []
    for i, (t, model, prompt) in enumerate(spawns):
        inp = {"subagent_type": f"shode-house:{t}", "description": "d", "prompt": prompt}
        if model:
            inp["model"] = model
        ev.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Task", "input": inp}]}})
    ev.append({"type": "result", "subtype": "error_max_turns", "is_error": True, "result": final})
    return ev


class DomainCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_check(self, ident, events):
        p = Path(self.tmp.name) / "t.jsonl"
        p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(D / "check-domain.py"), ident, str(p)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_opus_domains_need_the_reference_and_the_opus_request(self):
        for ident, dom in (("P15", "fintech"), ("P23", "trading"), ("P24", "insurance"), ("P43", "sap")):
            ref = f"load references/domain/{dom}.md"
            self.assertEqual(0, self.run_check(ident, trace([("plan", "opus", ref)]))[0], ident)
            rc, out = self.run_check(ident, trace([("plan", "", ref)]))
            self.assertEqual(1, rc, ident)
            self.assertIn("opus domain", out)
            self.assertEqual(1, self.run_check(ident, trace([("plan", "opus", "no reference named")]))[0], ident)
            self.assertEqual(1, self.run_check(ident, trace([("plan", "opus", ref + " and references/domain/erp.md")]))[0], ident)

    def test_default_domains_run_at_the_type_default_unless_a_high_stakes_reason_is_recorded(self):
        for ident, dom in (("P42", "erp"), ("P44", "booking"), ("P45", "ecommerce")):
            ref = f"load references/domain/{dom}.md"
            self.assertEqual(0, self.run_check(ident, trace([("plan", "", ref)]))[0], ident)
            self.assertEqual(0, self.run_check(ident, trace([("plan", "sonnet", ref)]))[0], ident)
            rc, out = self.run_check(ident, trace([("plan", "opus", ref)]))
            self.assertEqual(1, rc, ident)
            self.assertIn("without a recorded high-stakes reason", out)
            self.assertEqual(0, self.run_check(ident, trace([("plan", "opus", ref + "; model opus because high-stakes: money movement")]))[0], ident)

    def test_a_negated_high_stakes_is_not_a_recorded_reason(self):
        """Standards suggestion: "not high-stakes" / "no high-stakes reason" must not license an opus request on a default domain."""
        ref = "load references/domain/erp.md"
        for text in ("this is not high-stakes", "no high-stakes reason", "non-high-stakes work", "it isn't high-stakes", "without a high-stakes reason",
                     "never high-stakes", "NOT High-Stakes", "this is routine.\nnot high-stakes"):
            rc, out = self.run_check("P42", trace([("plan", "opus", f"{ref}; model opus. {text}")]))
            self.assertEqual(1, rc, text + out)
            self.assertIn("without a recorded high-stakes reason", out, text)
        for text in ("because high-stakes: money movement", "High-Stakes period close", "not trivial; high-stakes", "not high-stakes at first, but high-stakes now"):
            rc, out = self.run_check("P42", trace([("plan", "opus", f"{ref}; model opus {text}")]))
            self.assertEqual(0, rc, text + out)

    def test_no_plan_spawn_wrong_type_and_non_domain_probes(self):
        self.assertEqual(1, self.run_check("P15", trace([]))[0])
        self.assertEqual(1, self.run_check("P15", trace([("build", "opus", "references/domain/fintech.md")]))[0])
        rc, out = self.run_check("P02", trace([("plan", "opus", "x")]))
        self.assertEqual(2, rc, out)
        self.assertIn("not a domain probe", out)


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash + git")
class RunnerWiringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="shode-battery-run.")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        stub = self.tmp / "claude"
        stub.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{ROOT}/tests/fake_claude.py" "$@"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.tmp / "t").mkdir()
        self.env = clean_env(CLAUDE_BIN=str(stub), TMPDIR=str(self.tmp / "t"))

    def run_battery(self, *args, **env):
        return subprocess.run(["bash", str(ROOT / "eval/run-battery-4.0.1.sh"), *args], capture_output=True, text=True,
                              env=dict(self.env, **env), timeout=170)

    def test_runner_scores_the_battery_records_the_batch_and_the_domain_check(self):
        out = self.tmp / "b"
        done = self.run_battery("sonnet", str(out), PROBE_IDS="P02 P03 P15", REPEATS="2")
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)      # a FAIL is data, not an error
        rows = {}
        for line in (out / "SUMMARY.tsv").read_text().splitlines()[1:]:
            c = line.split("\t")
            rows[(c[0], c[1])] = c[2]
        self.assertEqual({("P02", "r1"): "0", ("P02", "r2"): "0", ("P03", "r1"): "1", ("P03", "r2"): "1", ("P15", "r1"): "1", ("P15", "r2"): "1"}, rows)
        batch = json.loads((out / "BATCH.json").read_text())
        self.assertEqual("4.0.1", batch["battery"])
        self.assertTrue(batch["frozen"])
        self.assertTrue(batch["scenarios"].endswith("eval/scenarios/battery-4.0.1/battery-4.0.1.json"))
        meta = json.loads((out / "P02/r1/meta.json").read_text())
        self.assertEqual(hash_file(D / "battery-4.0.1.json"), meta["sha256"]["scenarios"])
        self.assertEqual(hash_file(ROOT / "eval/prompts/probes/P02.md"), meta["sha256"]["prompt_file"])
        self.assertIn("max-turns=6", meta["flags"])
        dom = (out / "P15/r1/domain-check.txt").read_text()
        self.assertIn("FAIL P15: no plan spawn", dom)
        self.assertTrue(dom.rstrip().endswith("exit=1"))
        self.assertFalse((out / "P02/r1/domain-check.txt").exists(), "only the 7 domain probes get the domain check")
        self.assertIn("SUMMARY battery-4.0.1", done.stdout)

    def test_default_n_is_5_the_baselines_and_the_model_default_is_sonnet(self):
        text = (ROOT / "eval/run-battery-4.0.1.sh").read_text()
        self.assertIn('REPEATS="${REPEATS:-5}"', text)
        self.assertIn('MODEL="${1:-sonnet}"', text)
        out = self.tmp / "n5"
        done = self.run_battery("sonnet", str(out), PROBE_IDS="P02")
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertEqual([f"r{k}" for k in range(1, 6)], sorted(p.name for p in (out / "P02").iterdir()))

    def test_refusals_not_applicable_probe_file_unfrozen_and_foreign_batch(self):
        na = self.run_battery("sonnet", str(self.tmp / "na"), PROBE_IDS="P21")
        self.assertEqual(3, na.returncode)
        self.assertFalse((self.tmp / "na").exists())
        pf = self.run_battery("sonnet", str(self.tmp / "pf"), PROBE_FILE=str(ROOT / "eval/scenarios/golden.json"))
        self.assertEqual(3, pf.returncode)
        self.assertIn("PROBE_FILE is not supported", pf.stderr)
        empty = self.tmp / "emptyroot"
        empty.mkdir()
        red = self.run_battery("sonnet", str(self.tmp / "red"), PROBE_IDS="P02", REPEATS="1", FREEZE_ROOT=str(empty))
        self.assertEqual(3, red.returncode, red.stdout + red.stderr)
        self.assertFalse((self.tmp / "red").exists(), "a red freeze refuses before anything is created")
        out = self.tmp / "same"
        self.assertEqual(0, self.run_battery("sonnet", str(out), PROBE_IDS="P02", REPEATS="1").returncode)
        self.assertEqual(3, self.run_battery("opus", str(out), PROBE_IDS="P02", REPEATS="1").returncode)

    def freeze_root(self, name):
        """A FREEZE_ROOT holding every file either freeze check reads, copied from the real tree: both checks are green on it."""
        root = self.tmp / name
        old = [l.split("  ", 1)[1] for l in (ROOT / "eval/FREEZE.sha256").read_text(encoding="utf-8").splitlines() if l.strip()]
        new = [l.split("  ", 1)[1] for l in (D / "FREEZE.sha256").read_text(encoding="utf-8").splitlines() if l.strip()]
        for rel in old + new + ["eval/FREEZE.sha256", "eval/scenarios/golden.json"]:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, root / rel)
        return root

    def test_each_freeze_guard_alone_refuses_the_start_and_a_green_root_does_not(self):
        """Standards F2: the runner needs BOTH the old freeze and the battery freeze green. Dropping either check must be noticed."""
        green = self.freeze_root("fz-green")
        ok = self.run_battery("sonnet", str(self.tmp / "ok"), PROBE_IDS="P02", REPEATS="1", FREEZE_ROOT=str(green))
        self.assertEqual(0, ok.returncode, "control: with both freezes green the runner starts\n" + ok.stdout + ok.stderr)
        for name, victim, expect in (("old-only-red", "eval/prompts/probes/P01.md", "eval/check-freeze.sh"),
                                     ("battery-only-red", "eval/scenarios/battery-4.0.1/README.md", "battery-4.0.1/check-freeze.sh")):
            root = self.freeze_root("fz-" + name)
            (root / victim).write_text((root / victim).read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")
            old_rc = subprocess.run(["bash", str(ROOT / "eval/check-freeze.sh")], capture_output=True, text=True, env=clean_env(FREEZE_ROOT=str(root))).returncode
            new_rc = subprocess.run(["bash", str(D / "check-freeze.sh")], capture_output=True, text=True, env=clean_env(FREEZE_ROOT=str(root))).returncode
            self.assertEqual((1, 0) if name == "old-only-red" else (0, 1), (old_rc, new_rc), name + ": exactly one freeze is red")
            r = self.run_battery("sonnet", str(self.tmp / name), PROBE_IDS="P02", REPEATS="1", FREEZE_ROOT=str(root))
            self.assertEqual(3, r.returncode, name + r.stdout + r.stderr)
            self.assertIn("frozen files changed", r.stderr, name)
            self.assertFalse((self.tmp / name).exists(), name + ": a red freeze refuses before anything is created")

    def all_modes(self, out, label=""):
        self.assertEqual(0o700, stat.S_IMODE(out.stat().st_mode), label + " out-dir")
        for path in out.rglob("*"):
            want = 0o700 if path.is_dir() else 0o600
            self.assertEqual(want, stat.S_IMODE(path.lstat().st_mode), label + str(path.relative_to(out)))

    def umask0(self, *args, **env):
        return subprocess.run(["bash", "-c", 'umask 000; exec bash "$0" "$@"', str(ROOT / "eval/run-battery-4.0.1.sh"), *args],
                              capture_output=True, text=True, env=dict(self.env, **env), timeout=170)

    def test_runner_is_owner_only_under_a_permissive_umask_and_redacts_derived_evidence(self):
        """SEC-13: dirs 0700 and files 0600 come from the runner itself; derived evidence is redacted, run.jsonl is byte-exact."""
        token = "ghp" + "_" + "Zq9Lm2Np4Rs6Tv8Wx0Yb1Cd3"
        out = self.tmp / "deep" / "b"
        done = self.umask0("sonnet", str(out), PROBE_IDS="P02 P15", REPEATS="1", FAKE_SKILL="diagnose --token " + token,
                           FAKE_PLAN_MODEL="sonnet-" + token)       # the domain check prints the requested model of the plan spawn
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertEqual(0o700, stat.S_IMODE(out.parent.stat().st_mode), "the parent the runner created")
        self.all_modes(out)
        self.assertEqual([], [p.name for p in out.rglob(".redact*")], "no marker, buffer or temporary file left behind")
        for pid in ("P02", "P15"):
            run = out / pid / "r1"
            raw = (run / "run.jsonl").read_bytes()
            self.assertIn(token.encode(), raw, "run.jsonl is the raw trace: byte-exact, never redacted")
            record = json.loads((run / "redaction.json").read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), record["run_jsonl_sha256"])
            for name in ("tools-seen.txt", "score.txt", "score.json", "meta.json"):
                self.assertNotIn(token, (run / name).read_text(encoding="utf-8"), pid + "/" + name)
        self.assertIn("<REDACTED>", (out / "P02/r1/tools-seen.txt").read_text(encoding="utf-8"))
        self.assertIn("<REDACTED>", (out / "P15/r1/domain-check.txt").read_text(encoding="utf-8"), "the planted model reached domain-check.txt and was redacted")
        self.assertIn(token, (out / "P15/r1/run.jsonl").read_text(encoding="utf-8"))
        for name in ("SUMMARY.tsv", "AGG.tsv", "log.txt", "P15/r1/domain-check.txt", "BATCH.json"):
            self.assertNotIn(token, (out / name).read_text(encoding="utf-8"), name)
        self.assertNotIn(token, done.stdout + done.stderr)

    TOKEN = "ghp" + "_" + "Zq9Lm2Np4Rs6Tv8Wx0Yb1Cd3"

    def shim(self):
        """A python3 first on PATH that fails `redact_derived.py <SHIM_FAIL>` (selftest / seal) and runs everything else for real."""
        d = self.tmp / "shim"
        d.mkdir(exist_ok=True)
        (d / "python3").write_text(f'#!/bin/sh\ncase "$1" in */redact_derived.py) [ "$2" = "${{SHIM_FAIL:-}}" ] && {{ echo "shim: $2 failed" >&2; exit 1; }} ;; esac\n'
                                   f'exec "{sys.executable}" "$@"\n')
        (d / "python3").chmod(0o700)
        return dict(PATH=str(d) + os.pathsep + os.environ.get("PATH", ""))

    def test_an_interrupted_batch_is_resealed_before_any_run_and_its_console_output_is_redacted_and_flushed(self):
        """Standards M1 (a): .redact-pending + .redact-pending.out left by a killed invocation are sealed first, then the batch goes on."""
        out = self.tmp / "resume"
        env = dict(PROBE_IDS="P02", FAKE_SKILL="diagnose --token " + self.TOKEN)
        self.assertEqual(0, self.run_battery("sonnet", str(out), REPEATS="1", **env).returncode)
        run = out / "P02/r1"
        for name in ("score.txt", "tools-seen.txt"):          # what a kill between run_one and its seal leaves behind
            with open(run / name, "a", encoding="utf-8") as f:
                f.write("\nleaked " + self.TOKEN + "\n")
        (out / ".redact-pending").write_text("P02/r1\n", encoding="utf-8")
        (out / ".redact-pending.out").write_text("INTERRUPTED-CONSOLE-LINE token=" + self.TOKEN + "\n", encoding="utf-8")
        for name in (".redact-pending", ".redact-pending.out"):
            os.chmod(out / name, 0o600)
        again = self.run_battery("sonnet", str(out), REPEATS="2", **env)
        self.assertEqual(0, again.returncode, again.stdout + again.stderr)
        text = again.stdout + again.stderr
        self.assertIn("== resume: P02/r1 was interrupted", text)
        self.assertLess(text.index("== resume: P02/r1 was interrupted"), text.index("== resume: console output"), "seal first, then flush")
        self.assertLess(text.index("== resume: console output"), text.index(" batch model="), "before the batch (and so any run) starts")
        self.assertIn("INTERRUPTED-CONSOLE-LINE", text, "the interrupted run's console output is flushed, not lost")
        self.assertTrue((out / "P02/r2/run.jsonl").exists(), "the batch went on")
        for name in ("score.txt", "tools-seen.txt"):
            self.assertNotIn(self.TOKEN, (run / name).read_text(encoding="utf-8"), name)
        for name in ("log.txt", "SUMMARY.tsv", "AGG.tsv"):
            self.assertNotIn(self.TOKEN, (out / name).read_text(encoding="utf-8"), name)
        self.assertNotIn(self.TOKEN, text)
        self.assertIn("INTERRUPTED-CONSOLE-LINE", (out / "log.txt").read_text(encoding="utf-8"))
        self.assertEqual([], [p.name for p in out.rglob(".redact*")], "marker and buffer are gone")
        # a buffer with no marker (killed after the seal, before the flush) is redacted and flushed too
        (out / ".redact-pending.out").write_text("LONE-BUFFER-LINE " + self.TOKEN + "\n", encoding="utf-8")
        os.chmod(out / ".redact-pending.out", 0o600)
        lone = self.run_battery("sonnet", str(out), REPEATS="2", **env)
        self.assertEqual(0, lone.returncode, lone.stdout + lone.stderr)
        self.assertIn("LONE-BUFFER-LINE", lone.stdout + lone.stderr)
        self.assertNotIn(self.TOKEN, lone.stdout + lone.stderr + (out / "log.txt").read_text(encoding="utf-8"))
        self.assertFalse((out / ".redact-pending.out").exists())

    def test_a_bad_or_hostile_marker_stops_the_batch_with_exit_4_and_nothing_runs_or_is_sealed(self):
        """Standards M1 (b): the marker is validated before it is used as a path."""
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "score.txt").write_text("keep " + self.TOKEN + "\n", encoding="utf-8")
        env = dict(PROBE_IDS="P02", FAKE_SKILL="diagnose --token " + self.TOKEN)
        for n, marker in enumerate(("../outside", "P02/../../outside", "P02/r1/../../../outside", "", "P02/r1 extra", "/etc", "P02/r1.retry", "p02/r1")):
            out = self.tmp / f"bad{n}"
            self.assertEqual(0, self.run_battery("sonnet", str(out), REPEATS="1", **env).returncode)
            (out / ".redact-pending").write_text(marker + "\n", encoding="utf-8")
            os.chmod(out / ".redact-pending", 0o600)
            r = self.run_battery("sonnet", str(out), REPEATS="2", **env)
            self.assertEqual(4, r.returncode, repr(marker) + r.stdout + r.stderr)
            self.assertIn("unreadable", r.stdout + r.stderr, repr(marker))
            self.assertFalse((out / "P02/r2").exists(), repr(marker) + ": nothing ran")
            self.assertTrue((out / ".redact-pending").exists(), repr(marker) + ": the marker is kept for the operator")
            self.assertIn(self.TOKEN, (outside / "score.txt").read_text(encoding="utf-8"), repr(marker) + ": nothing outside the batch was touched")

    def test_a_failing_redactor_stops_the_batch_with_exit_4_and_no_further_run(self):
        """Standards M1 (c): selftest failure, seal failure after a run, seal failure on resume are all fail-closed."""
        shim = self.shim()
        env = dict(PROBE_IDS="P02 P03", FAKE_SKILL="diagnose --token " + self.TOKEN)
        # selftest fails: refused before the out-dir exists
        st = self.run_battery("sonnet", str(self.tmp / "st"), REPEATS="1", SHIM_FAIL="selftest", **shim, **env)
        self.assertEqual(4, st.returncode, st.stdout + st.stderr)
        self.assertIn("redaction failed (selftest)", st.stderr)
        self.assertFalse((self.tmp / "st").exists())
        # seal fails after the first run: the marker names it, the second probe never starts
        out = self.tmp / "sealfail"
        sf = self.run_battery("sonnet", str(out), REPEATS="1", SHIM_FAIL="seal", **shim, **env)
        self.assertEqual(4, sf.returncode, sf.stdout + sf.stderr)
        self.assertIn("redaction failed", sf.stdout + sf.stderr)
        self.assertEqual("P02/r1\n", (out / ".redact-pending").read_text(encoding="utf-8"), "the in-flight run is named before it runs")
        self.assertTrue((out / "P02/r1/run.jsonl").exists())
        self.assertFalse((out / "P03").exists(), "no further run")
        self.assertNotIn(self.TOKEN, sf.stdout + sf.stderr, "the buffered console output was never printed")
        # the redactor still fails on the next invocation: the pending run is not skipped, nothing new runs
        again = self.run_battery("sonnet", str(out), REPEATS="1", SHIM_FAIL="seal", **shim, **env)
        self.assertEqual(4, again.returncode, again.stdout + again.stderr)
        self.assertTrue((out / ".redact-pending").exists())
        self.assertFalse((out / "P03").exists())
        self.assertNotIn(self.TOKEN, again.stdout + again.stderr)
        # a buffered console output that cannot be redacted is never flushed either
        (out / ".redact-pending.out").write_text("BUFFER " + self.TOKEN + "\n", encoding="utf-8")
        os.chmod(out / ".redact-pending.out", 0o600)
        (out / ".redact-pending").unlink()
        buf = self.run_battery("sonnet", str(out), REPEATS="1", SHIM_FAIL="file", **shim, **env)
        self.assertEqual(4, buf.returncode, buf.stdout + buf.stderr)
        self.assertNotIn(self.TOKEN, buf.stdout + buf.stderr)
        (out / ".redact-pending").write_text("P02/r1\n", encoding="utf-8")
        os.chmod(out / ".redact-pending", 0o600)
        # redactor fixed: the pending run is sealed first and the batch completes
        fixed = self.run_battery("sonnet", str(out), REPEATS="1", **shim, **env)
        self.assertEqual(0, fixed.returncode, fixed.stdout + fixed.stderr)
        self.assertNotIn(self.TOKEN, (out / "P02/r1/score.txt").read_text(encoding="utf-8") + (out / "log.txt").read_text(encoding="utf-8") + fixed.stdout + fixed.stderr)
        self.assertTrue((out / "P03/r1/run.jsonl").exists())
        self.assertFalse((out / ".redact-pending").exists())

    def test_resume_of_a_loose_outdir_is_tightened_and_a_symlink_or_symlinked_outdir_is_refused(self):
        out = self.tmp / "loose"
        args = ("sonnet", str(out))
        env = dict(PROBE_IDS="P02", REPEATS="1")
        self.assertEqual(0, self.run_battery(*args, **env).returncode)
        raw = out / "P02/r1/run.jsonl"
        want = hashlib.sha256(raw.read_bytes()).hexdigest()
        for root, dirs, files in os.walk(out):          # a batch begun before umask 077 / touched by hand
            for n in dirs:
                os.chmod(os.path.join(root, n), 0o777)
            for n in files:
                os.chmod(os.path.join(root, n), 0o666)
        os.chmod(out, 0o755)
        again = self.run_battery(*args, **env)
        self.assertEqual(0, again.returncode, again.stdout + again.stderr)
        self.all_modes(out, "tightened: ")
        self.assertEqual(want, hashlib.sha256(raw.read_bytes()).hexdigest(), "the lockdown never rewrites evidence")
        # a symlink inside the out-dir refuses the batch (exit 4), nothing is changed and nothing runs
        outside = self.tmp / "outside.txt"
        outside.write_text("x")
        os.chmod(outside, 0o644)
        os.symlink(outside, out / "evil")
        os.chmod(out / "P02", 0o755)
        before = sorted((str(p.relative_to(out)), stat.S_IMODE(p.lstat().st_mode)) for p in out.rglob("*"))
        refused = self.run_battery(*args, **dict(env, REPEATS="2"))
        self.assertEqual(4, refused.returncode, refused.stdout + refused.stderr)
        self.assertIn("owner-only", refused.stderr)
        self.assertEqual(before, sorted((str(p.relative_to(out)), stat.S_IMODE(p.lstat().st_mode)) for p in out.rglob("*")), "nothing changed")
        self.assertEqual(0o644, stat.S_IMODE(outside.stat().st_mode), "the link target was not chmod-ed")
        self.assertFalse((out / "P02/r2").exists(), "nothing ran")
        # a symlinked out-dir itself
        link = self.tmp / "linked"
        os.symlink(self.tmp / "same-target", link)
        (self.tmp / "same-target").mkdir()
        sym = self.run_battery("sonnet", str(link), **env)
        self.assertEqual(3, sym.returncode, sym.stdout + sym.stderr)
        self.assertIn("symlink", sym.stderr)
        self.assertEqual([], list((self.tmp / "same-target").iterdir()))

    def test_umask_077_is_set_before_the_library_is_sourced_and_the_frozen_library_is_wrapped_not_edited(self):
        text = (ROOT / "eval/run-battery-4.0.1.sh").read_text(encoding="utf-8")
        self.assertLess(text.index("\numask 077"), text.index('. "$(dirname'))
        self.assertIn('python3 "$REDACT" lockdown "$OUT"', text)
        self.assertNotIn("umask", (ROOT / "eval/run-lib.sh").read_text(encoding="utf-8"))
        self.assertIn("eval/run-lib.sh", (ROOT / "eval/FREEZE.sha256").read_text(encoding="utf-8"))

    def test_the_baseline_runner_and_library_still_use_the_baseline_battery(self):
        text = (ROOT / "eval/run-lib.sh").read_text()
        self.assertIn('SCENARIOS="$REPO/eval/scenarios/golden.json"', text)
        self.assertNotIn("battery", text)
        self.assertNotIn("battery", (ROOT / "eval/run-probes.sh").read_text())


class WiringAndDocsTest(unittest.TestCase):
    def test_ci_gate_27_and_agents_md_list_the_battery_freeze(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("bash eval/scenarios/battery-4.0.1/check-freeze.sh", ci)
        self.assertIn("W9 battery-4.0.1 freeze: eval/scenarios/battery-4.0.1/check-freeze.sh missing -- NOT CHECKED", ci)
        self.assertIn("test_battery_401", ci)
        agents = " ".join((ROOT / "AGENTS.md").read_text().split())
        self.assertIn("`eval/scenarios/battery-4.0.1/check-freeze.sh`", agents)
        self.assertIn("test_battery_401", agents)

    def test_runbook_states_same_prompt_model_and_n_and_the_old_battery_is_the_baseline(self):
        text = " ".join((ROOT / "eval/RUNBOOK.md").read_text().split())
        self.assertIn("Same prompt, same model, same N as the baseline", text)
        self.assertIn("historical baseline", text)
        self.assertIn("eval/run-battery-4.0.1.sh", text)
        readme = " ".join((D / "README.md").read_text().split())
        self.assertIn("Same prompt, model and N as the baseline", readme)
        self.assertIn("historical baseline", readme)


if __name__ == "__main__":
    unittest.main()
