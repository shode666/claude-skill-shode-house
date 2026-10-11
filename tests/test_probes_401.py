"""4.0.1 pre-registered probes (E19 served model, E20 spec-axis seeded violations) and the no-fable-dispatch negative that
replaced the staff-engineer must_not_dispatch. No model is called: synthetic stream-json traces prove the scorer can PASS and
can FAIL, and that the thresholds are pre-registered in the pinned file, the fixture seeds what the file says, and the
fallback is recorded in maintainer docs. NOTHING here is a measurement of a model."""
import json, os, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "eval/scenarios/core-4.0.1"
CHECK = D / "check-probes.py"
PROBES = json.loads((D / "probes-4.0.1.json").read_text(encoding="utf-8"))
FIXTURE = ROOT / "scripts/eval-fixture-core.sh"


def trace(spawns, text, usage=None, subtext=None):
    ev = []
    for i, (t, m) in enumerate(spawns):
        inp = {"subagent_type": f"shode-house:{t}", "prompt": "x"}
        if m:
            inp["model"] = m
        ev.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Task", "input": inp}]}})
        if subtext:
            ev.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": subtext}]}})
    res = {"type": "result", "subtype": "success", "is_error": False, "result": text}
    if usage is not None:
        res["modelUsage"] = {u: {"outputTokens": 1} for u in usage}
    ev.append(res)
    return ev


def rtrace(text, spawns=(("plan", ""),), final="Review complete."):
    """A run whose spec reviewer's OWN spawn result (the tool_result of each spawn) is `text`; the router's final text is `final`."""
    return trace(list(spawns), final, subtext=text)


class Probe401Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_check(self, ident, traces, *flags):
        paths = []
        for i, ev in enumerate(traces):
            p = Path(self.tmp.name) / f"{ident}-{i}.jsonl"
            p.write_text("\n".join(json.dumps(e) for e in ev) + "\n", encoding="utf-8")
            paths.append(str(p))
        r = subprocess.run([sys.executable, str(CHECK), ident, *paths, *flags], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    # ---- pre-registration -------------------------------------------------------------------------------------------
    def test_thresholds_and_fallback_are_registered_in_the_pinned_file(self):
        self.assertTrue(PROBES["registered"]["before_first_run"])
        self.assertEqual("nothing", PROBES["registered"]["measured_so_far"])
        e19, e20 = PROBES["probes"]["E19"], PROBES["probes"]["E20"]
        self.assertEqual((5, 5, 5), (e19["runs"], e19["min_runs_passing"], e19["min_runs_honoured"]))
        self.assertEqual(0.80, e20["threshold"]["min_catch_rate"])
        self.assertEqual(0.25, e20["threshold"]["max_false_positive_rate"])
        self.assertTrue(e20["threshold"]["catch_rate_not_below_baseline"])
        self.assertIn("spec axis moves from `plan` to `verify`", PROBES["fallback"]["action"])
        manifest = (D / "FREEZE.sha256").read_text(encoding="utf-8")
        for f in ("probes-4.0.1.json", "check-probes.py", "routing-4.0.1.json"):
            self.assertIn(f, manifest, f"{f} is not pinned before the first run")
        for f in ("E19-served-model-override.md", "E20-spec-axis-seeded-violations.md"):       # Standards F5: the instrument's input is pinned too
            self.assertIn(f, manifest, f"{f} is not pinned before the first run")

    def test_the_e19_and_e20_prompts_are_under_the_freeze_check(self):
        import shutil
        tmp = Path(self.tmp.name) / "fz"
        for rel in ("eval/scenarios/core-4.0.1", "eval/scenarios/core-4.0", "eval/prompts"):
            shutil.copytree(ROOT / rel, tmp / rel, ignore=shutil.ignore_patterns("probes", "__pycache__"))
        env = {k: v for k, v in os.environ.items() if k != "FREEZE_ROOT"}
        env["FREEZE_ROOT"] = str(tmp)
        check = lambda: subprocess.run(["bash", str(tmp / "eval/scenarios/core-4.0.1/check-freeze.sh")], capture_output=True, text=True, env=env)
        r = check()
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("freeze OK: 8 files", r.stdout)
        prompt = tmp / "eval/prompts/E20-spec-axis-seeded-violations.md"
        prompt.write_text(prompt.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
        r = check()
        self.assertEqual(1, r.returncode)
        self.assertIn("CHANGED ../../prompts/E20-spec-axis-seeded-violations.md", r.stdout)

    def test_fallback_is_in_maintainer_docs_not_only_in_outputs(self):
        for rel in ("eval/scenarios/core-4.0.1/README.md", "CHANGELOG.md", "README.md"):
            text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
            self.assertRegex(text, r"spec axis moves from `plan` to `verify`|spec axis (moves|would move) to `verify`", rel)

    def test_the_scenarios_use_only_scorer_fields_and_know_the_probe_ids(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("trc", ROOT / "scripts/team-run-check.py")
        trc = importlib.util.module_from_spec(spec); spec.loader.exec_module(trc)
        data = {s["id"]: s for s in json.loads((D / "routing-4.0.1.json").read_text(encoding="utf-8"))["scenarios"]}
        for ident in PROBES["probes"]:
            self.assertIn(ident, data)
            self.assertLessEqual(set(data[ident]["expected"]), trc.EXPECTED_FIELDS)
            self.assertTrue((ROOT / data[ident]["prompt"]).is_file())

    # ---- E19 --------------------------------------------------------------------------------------------------------
    GOOD19 = "requested model: opus; served model: claude-opus-4-1 (per modelUsage)\nrule answer ..."

    def test_e19_passes_when_override_requested_and_served_are_recorded(self):
        good = trace([("plan", "opus")], self.GOOD19, usage=["claude-sonnet-5", "claude-opus-4-1"])
        rc, out = self.run_check("E19", [good] * 5)
        self.assertEqual(0, rc, out)

    def test_e19_fails_without_the_override_without_the_record_or_on_a_silent_mismatch(self):
        good = trace([("plan", "opus")], self.GOOD19, usage=["claude-opus-4-1"])
        no_override = trace([("plan", "")], self.GOOD19, usage=["claude-opus-4-1"])
        no_record = trace([("plan", "opus")], "answer only", usage=["claude-opus-4-1"])
        silent = trace([("plan", "opus")], "requested model: opus; served model: opus", usage=["claude-sonnet-5"])
        for bad in (no_override, no_record, silent):
            rc, out = self.run_check("E19", [good] * 4 + [bad])
            self.assertEqual(1, rc, out)
        honest = trace([("plan", "opus")], "requested model: opus; served model: sonnet. BLOCKED: model mismatch", usage=["claude-sonnet-5"])
        rc, out = self.run_check("E19", [good] * 4 + [honest])
        self.assertEqual(1, rc, out)
        self.assertIn("NOT honoured", out)          # honest BLOCKED, but the host did not honour the override: a failed control

    def test_e19_is_unscorable_without_modelusage_or_with_too_few_runs(self):
        no_usage = trace([("plan", "opus")], self.GOOD19)
        self.assertEqual(2, self.run_check("E19", [no_usage] * 5)[0])
        good = trace([("plan", "opus")], self.GOOD19, usage=["claude-opus-4-1"])
        self.assertEqual(2, self.run_check("E19", [good] * 4)[0])

    # ---- E20 (closed form, U30): only `AC-n: MET|VIOLATED` lines are read; everything else is UNSCORABLE, never a guess ----------
    @staticmethod
    def lines(**verdicts):
        v = {"AC-1": "MET", "AC-2": "VIOLATED", "AC-3": "VIOLATED", "AC-4": "VIOLATED", "AC-5": "MET", "AC-6": "VIOLATED"}
        v.update({k.replace("_", "-"): x for k, x in verdicts.items()})
        return "\n".join(f"{k}: {x}" for k, x in sorted(v.items()))

    CATCH_ALL = "AC-1: MET\nAC-2: VIOLATED\nAC-3: VIOLATED\nAC-4: VIOLATED\nAC-5: MET\nAC-6: VIOLATED"
    CATCH_3 = CATCH_ALL.replace("AC-6: VIOLATED", "AC-6: MET")

    def e20(self, text, runs=5, **kw):
        return self.run_check("E20", [rtrace(text)] * runs)

    def test_e20_the_prompt_asks_for_the_closed_form_and_the_probe_file_registers_only_that(self):
        prompt = (ROOT / "eval/prompts/E20-spec-axis-seeded-violations.md").read_text(encoding="utf-8")
        self.assertIn("`AC-n: MET` หรือ `AC-n: VIOLATED`", prompt.split("## Prompt", 1)[1])
        e20 = PROBES["probes"]["E20"]
        self.assertEqual(r"^(AC-\d+(?:\.\d+)*): (MET|VIOLATED)$", e20["verdict_line_regex"])
        for gone in ("violation_word_regex", "weak_violation_regex", "negated_violation_regex", "cleared_word_regex"):
            self.assertNotIn(gone, e20)
        self.assertIn("human adjudication", e20["verdict_rule"])
        self.assertEqual((0.80, 0.25), (e20["threshold"]["min_catch_rate"], e20["threshold"]["max_false_positive_rate"]))

    def test_e20_is_described_as_a_structured_text_scorer_with_human_adjudication_in_every_doc(self):
        for rel in ("eval/scenarios/core-4.0.1/README.md", "CHANGELOG.md", "README.md"):
            text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
            self.assertIn("structured text scorer", text, rel)
            self.assertIn("human adjudication", text, rel)
            self.assertIn("AC-n: MET", text, rel)
            self.assertIn("UNSCORABLE", text, rel)
            self.assertIn("spec reviewer's own spawn result", text, rel)       # Spec S-10: the docs state the relay rule the scorer applies
            self.assertIn("corroborate", text, rel)

    def test_e20_a_correct_closed_form_run_computes_catch_and_false_positive(self):
        rc, out = self.e20(self.CATCH_ALL)
        self.assertEqual(0, rc, out)
        self.assertIn("catch rate 1.00", out)
        self.assertIn("false-positive rate 0.00", out)
        self.assertIn("AC-2 [seeded] VIOLATED", out)
        self.assertIn("AC-1 [decoy] MET", out)

    def test_e20_passes_at_the_registered_catch_rate_and_fails_below_it(self):
        full = rtrace(self.CATCH_ALL)
        three = rtrace(self.CATCH_3)       # 3 of 4 = 0.75 < 0.80
        rc, out = self.run_check("E20", [three] * 5)
        self.assertEqual(1, rc, out)
        self.assertIn("catch rate 0.75", out)
        self.assertEqual(0, self.run_check("E20", [full] * 4 + [three])[0])       # 19 of 20 = 0.95

    def test_e20_exactly_the_registered_catch_rate_passes(self):
        """Standards F3: 16 of 20 = 0.80 is a PASS (`>=`); one catch fewer is not."""
        full = rtrace(self.CATCH_ALL)
        none = rtrace(self.lines(AC_2="MET", AC_3="MET", AC_4="MET", AC_6="MET"))
        rc, out = self.run_check("E20", [full] * 4 + [none])
        self.assertEqual(0, rc, out)
        self.assertIn("catch rate 0.80", out)
        three = rtrace(self.CATCH_3)
        rc, out = self.run_check("E20", [full] * 3 + [three, none])        # 15 of 20 = 0.75
        self.assertEqual(1, rc, out)
        self.assertIn("catch rate 0.75", out)

    def test_e20_flagging_met_criteria_is_a_false_positive_and_a_baseline_can_fail_the_run(self):
        one_decoy = rtrace(self.CATCH_ALL.replace("AC-5: MET", "AC-5: VIOLATED"))   # 5 of 10 = 0.50 > 0.25
        rc, out = self.run_check("E20", [one_decoy] * 5)
        self.assertEqual(1, rc, out)
        self.assertIn("false-positive rate 0.50", out)
        full = rtrace(self.CATCH_ALL)
        three = rtrace(self.CATCH_3)
        self.assertEqual(0, self.run_check("E20", [full] * 5, "--baseline-rate", "0.95")[0])
        self.assertEqual(1, self.run_check("E20", [full] * 4 + [three], "--baseline-rate", "1.0")[0])

    def test_e20_the_all_met_reviewer_fails_with_zero_catch(self):
        rc, out = self.e20(self.lines(AC_2="MET", AC_3="MET", AC_4="MET", AC_6="MET"))
        self.assertEqual(1, rc, out)
        self.assertIn("catch rate 0.00", out)

    def test_e20_needs_the_spec_spawn_and_forbids_build_and_reads_the_returned_text(self):
        wrong = rtrace(self.CATCH_ALL, spawns=[("verify", "")])
        self.assertEqual(1, self.run_check("E20", [wrong] * 5)[0])
        built = rtrace(self.CATCH_ALL, spawns=[("plan", ""), ("build", "")])
        self.assertEqual(1, self.run_check("E20", [built] * 5)[0])
        relayed = rtrace(self.CATCH_ALL, final="see the review")
        self.assertEqual(0, self.run_check("E20", [relayed] * 5)[0])
        ba = rtrace(self.CATCH_ALL, spawns=[("business-analyst", "")])
        self.assertEqual(0, self.run_check("E20", [ba] * 5, "--spec-agent", "business-analyst")[0])

    def test_e20_a_router_relaying_the_same_verdicts_is_fine_but_a_conflict_is_unscorable(self):
        relay = rtrace(self.CATCH_ALL, final=self.CATCH_ALL)          # reviewer reply + router final text, identical: corroboration
        self.assertEqual(0, self.run_check("E20", [relay] * 5)[0])
        conflict = rtrace(self.CATCH_ALL, final=self.CATCH_ALL.replace("AC-2: VIOLATED", "AC-2: MET"))
        rc, out = self.run_check("E20", [conflict] * 5)
        self.assertEqual(2, rc, out)
        self.assertIn("conflicting verdicts", out)
        reverse = rtrace(self.CATCH_ALL.replace("AC-2: VIOLATED", "AC-2: MET"), final=self.CATCH_ALL)   # the reviewer's word is the one read
        self.assertEqual(2, self.run_check("E20", [reverse] * 5)[0])

    @staticmethod
    def replies_trace(*spawn_replies, final="done"):
        """One main-session spawn per (type, reply): each reply is the tool_result of its own spawn."""
        ev = []
        for i, (kind, reply) in enumerate(spawn_replies):
            ev.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"s{i}", "name": "Task",
                                                                      "input": {"subagent_type": f"shode-house:{kind}", "prompt": "x"}}]}})
            ev.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"s{i}", "content": reply}]}})
        return ev + [{"type": "result", "subtype": "success", "is_error": False, "result": final}]

    def test_e20_only_the_spec_reviewer_types_replies_are_read_not_another_spawns_and_two_replies_that_disagree_are_unscorable(self):
        """Standards L1: spec_replies matches the spawn type, and verdict_lines compares the reviewer's replies with each other."""
        # a non-plan spawn (verify) returns six closed-form lines while the plan reviewer gives prose: the plan reviewer gave no verdict
        other = self.replies_trace(("plan", "I reviewed it; see details."), ("verify", self.CATCH_ALL))
        rc, out = self.run_check("E20", [other] * 5)
        self.assertEqual(2, rc, out)
        self.assertIn("no closed-form", out)
        self.assertNotIn("PASS", out.replace("UNSCORABLE", ""))
        # control: the same spawns with the plan reviewer giving the six lines (verify's prose ignored) scores
        self.assertEqual(0, self.run_check("E20", [self.replies_trace(("plan", self.CATCH_ALL), ("verify", "prose"))] * 5)[0])
        # two plan replies disagree on AC-2 (VIOLATED vs MET): UNSCORABLE, whichever order and whichever is whole
        for first, second in ((self.CATCH_ALL, self.CATCH_ALL.replace("AC-2: VIOLATED", "AC-2: MET")),
                              (self.CATCH_ALL.replace("AC-2: VIOLATED", "AC-2: MET"), self.CATCH_ALL)):
            rc, out = self.run_check("E20", [self.replies_trace(("plan", first), ("plan", second))] * 5)
            self.assertEqual(2, rc, out)
            self.assertIn("AC-2: conflicting verdicts", out)
        # control: two plan replies that agree are fine
        self.assertEqual(0, self.run_check("E20", [self.replies_trace(("plan", self.CATCH_ALL), ("plan", self.CATCH_ALL))] * 5)[0])

    def test_e20_verdicts_come_only_from_the_spec_spawns_own_result_never_from_the_routers_text(self):
        """Standards F1: the router may corroborate, never supply. Both demonstrated cases and their neighbours are UNSCORABLE, never PASS."""
        cases = {
            "prose-only reviewer, router supplies six": rtrace("I reviewed it; see details.", final=self.CATCH_ALL),
            "3-of-6 reviewer, router supplies six": rtrace("AC-1: MET\nAC-2: VIOLATED\nAC-3: VIOLATED", final=self.CATCH_ALL),
            "empty reviewer reply, router supplies six": rtrace("", final=self.CATCH_ALL),
            "no reviewer reply at all, router supplies six": trace([("plan", "")], self.CATCH_ALL),
        }
        for name, ev in cases.items():
            rc, out = self.run_check("E20", [ev] * 5)
            self.assertEqual(2, rc, name + out)
            self.assertNotIn("PASS", out.replace("UNSCORABLE", ""), name)
        rc, out = self.run_check("E20", [cases["3-of-6 reviewer, router supplies six"]] * 5)
        self.assertIn("AC-4: no closed-form line", out)
        rc, out = self.run_check("E20", [cases["no reviewer reply at all, router supplies six"]] * 5)
        self.assertIn("no spec-reviewer reply", out)
        # the final text alone also never completes a run when only 4 of 5 runs are whole
        whole = rtrace(self.CATCH_ALL)
        self.assertEqual(2, self.run_check("E20", [whole] * 4 + [cases["prose-only reviewer, router supplies six"]])[0])

    def test_e20_a_tool_result_of_another_tool_or_a_subagents_internal_result_is_not_the_reviewers_reply(self):
        reviewer_prose = rtrace("I reviewed it; see details.", final="done")
        other_tool = reviewer_prose[:-1] + [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "x"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "r1", "content": self.CATCH_ALL}]}},
        ] + reviewer_prose[-1:]
        rc, out = self.run_check("E20", [other_tool] * 5)
        self.assertEqual(2, rc, out)
        internal = reviewer_prose[:-1] + [
            {"type": "user", "parent_tool_use_id": "t0", "message": {"content": [{"type": "tool_result", "tool_use_id": "t0", "content": self.CATCH_ALL}]}},
        ] + reviewer_prose[-1:]
        rc, out = self.run_check("E20", [internal] * 5)
        self.assertEqual(2, rc, out)
        # a reply given as a list of text blocks is read
        blocks = trace([("plan", "")], "done", subtext=[{"type": "text", "text": self.CATCH_ALL}])
        self.assertEqual(0, self.run_check("E20", [blocks] * 5)[0])

    def test_e20_chris_phrasings_n2_n3_n5_are_unscorable_never_pass(self):
        table = ("| AC | Verdict |\n|---|---|\n| AC-1 | met |\n| AC-2 | VIOLATED |\n| AC-3 | VIOLATED |\n"
                 "| AC-4 | VIOLATED |\n| AC-5 | met |\n| AC-6 | VIOLATED |")
        table_reason = table.replace("| AC-2 | VIOLATED |", "| AC-2 | Fail | rows descending |")
        for name, text in (
            ("N2 polar", "AC-2 violated? no\nAC-3 violated? no\nAC-4 violated? no\nAC-6 violated? no\nAC-1 met\nAC-5 met"),
            ("N2 colon", "AC-2 violated: no\nAC-3 violated: no\nAC-4 violated: no\nAC-6 violated: no\nAC-1 met\nAC-5 met"),
            ("N2 could not find", "I could not find any violation of AC-2, AC-3, AC-4 or AC-6. AC-1 and AC-5 are met."),
            ("N3 table", table), ("N3 table with reason", table_reason),
            ("N5 nothing missing", "AC-1 met\nAC-5 met, nothing missing\nAC-2 violated\nAC-3 violated\nAC-4 violated\nAC-6 violated"),
            ("N5 lowercase id", "ac-1 met\nac-2 violated\nac-3 violated\nac-4 violated\nac-5 met\nac-6 violated"),
            ("N5 thai negation", "AC-2 ไม่พบการละเมิด\nAC-3 ไม่พบการละเมิด\nAC-4 ไม่พบการละเมิด\nAC-6 ไม่พบการละเมิด\nAC-1 ผ่าน\nAC-5 ผ่าน"),
            ("N5 no keyword", "AC-2: output is descending but spec requires ascending\nAC-4: raises an exception instead of a header"),
            ("summary", "Violated: AC-2, AC-3, AC-4, AC-6. Met: AC-1, AC-5."),
        ):
            rc, out = self.e20(text)
            self.assertEqual(2, rc, name + out)
            self.assertIn("UNSCORABLE", out, name)

    def test_e20_only_the_exact_closed_form_line_is_read(self):
        for bad in ("- AC-2: VIOLATED", "**AC-2: VIOLATED**", "`AC-2: VIOLATED`", "AC-2: VIOLATED (rows descending)", "AC-2: violated",
                    "AC-2 : VIOLATED", "AC-2:VIOLATED", "AC-2: VIOLATED."):
            rc, out = self.e20(self.lines().replace("AC-2: VIOLATED", bad))
            self.assertEqual(2, rc, bad + out)
            self.assertIn("AC-2: no closed-form line", out, bad)
        # surrounding whitespace is stripped; prose around the closed-form block is never read, so it cannot change a verdict
        noisy = "Review of audit_export:\n  " + self.CATCH_ALL.replace("\n", "  \n  ") + "\nAC-1 violated? no. AC-5 fails nothing. AC-2 not violated."
        rc, out = self.e20(noisy)
        self.assertEqual(0, rc, out)
        self.assertIn("catch rate 1.00", out)
        self.assertIn("false-positive rate 0.00", out)

    def test_e20_a_missing_duplicate_or_absent_closed_form_is_unscorable(self):
        for name, text in (("missing AC-6", self.CATCH_ALL.rsplit("\n", 1)[0]),
                           ("no lines", "all six criteria are fine except the four seeded ones"),
                           ("empty", ""),
                           ("duplicate same", self.CATCH_ALL + "\nAC-2: VIOLATED"),
                           ("duplicate different", self.CATCH_ALL + "\nAC-2: MET")):
            rc, out = self.e20(text)
            self.assertEqual(2, rc, name + out)
            self.assertIn("UNSCORABLE", out, name)
        rc, out = self.e20(self.CATCH_ALL.rsplit("\n", 1)[0])
        self.assertIn("AC-6: no closed-form line", out)
        rc, out = self.e20(self.CATCH_ALL + "\nAC-2: MET")
        self.assertIn("AC-2: duplicate closed-form line in one reply", out)
        # one unscorable run among five makes the whole probe UNSCORABLE
        good = rtrace(self.CATCH_ALL)
        bad = rtrace("no verdict lines")
        self.assertEqual(2, self.run_check("E20", [good] * 4 + [bad])[0])

    def test_e20_ids_outside_the_six_are_ignored_and_ids_match_whole(self):
        rc, out = self.e20(self.CATCH_ALL + "\nAC-10: VIOLATED\nAC-1.1: VIOLATED")
        self.assertEqual(0, rc, out)
        self.assertIn("false-positive rate 0.00", out)
        # an id outside the six is ignored even when it repeats (a duplicate of an unregistered id is not a duplicate of a criterion)
        rc, out = self.e20(self.CATCH_ALL + "\nAC-10: VIOLATED\nAC-10: MET\nAC-1.1: VIOLATED\nAC-1.1: VIOLATED\nAC-7: VIOLATED\nAC-7: VIOLATED")
        self.assertEqual(0, rc, out)
        self.assertIn("catch rate 1.00", out)

    def test_e20_and_e19_are_unscorable_when_the_trace_count_differs_from_the_registered_runs(self):
        full = rtrace(self.CATCH_ALL)
        self.assertEqual(2, self.run_check("E20", [full] * 6)[0])
        self.assertEqual(2, self.run_check("E20", [full] * 4)[0])
        self.assertIn("exactly 5", self.run_check("E20", [full] * 6)[1])
        good = trace([("plan", "opus")], self.GOOD19, usage=["claude-opus-4-1"])
        silent = trace([("plan", "opus")], "requested model: opus; served model: opus", usage=["claude-sonnet-5"])
        rc, out = self.run_check("E19", [good] * 5 + [silent])          # 5 of 6 must not pass a "5 of 5" rule
        self.assertEqual(2, rc, out)
        self.assertEqual(2, self.run_check("E19", [good] * 4)[0])

    # ---- ordinary-work negative (replaces the staff-engineer must_not_dispatch) --------------------------------------------
    def test_derivation_marks_exactly_the_scenarios_that_lost_the_staff_engineer_negative(self):
        old = json.loads((ROOT / "eval/scenarios/core-4.0/core-4.0.json").read_text(encoding="utf-8"))["scenarios"]
        new = {s["id"]: s for s in json.loads((D / "core-4.0.1.json").read_text(encoding="utf-8"))["scenarios"]}
        lost = {s["id"] for s in old if "staff-engineer" in s.get("expected", {}).get("must_not_dispatch", [])}
        self.assertTrue(lost, "the 4.0 set has staff-engineer negatives")
        self.assertEqual(lost, {i for i, s in new.items() if "no-fable-dispatch" in s.get("post_checks", [])})
        self.assertTrue({"E01", "E07", "E11", "E12", "E15"} <= lost)

    def test_no_fable_dispatch_fails_on_a_fable_request_or_a_fable_served_model(self):
        ok = trace([("build", "")], "done", usage=["claude-sonnet-5"])
        self.assertEqual(0, self.run_check("E01", [ok])[0])
        asked = trace([("build", "fable")], "done", usage=["claude-sonnet-5"])
        self.assertEqual(1, self.run_check("E01", [asked])[0])
        served = trace([("build", "")], "done", usage=["claude-fable-5"])
        self.assertEqual(1, self.run_check("E01", [served])[0])
        self.assertEqual(2, self.run_check("E02", [ok])[0])   # E02 never lost the negative: not a post_check scenario

    # ---- fixture ----------------------------------------------------------------------------------------------------
    def test_e20_fixture_seeds_what_the_probe_file_registers(self):
        dest = Path(self.tmp.name) / "fx"
        r = subprocess.run(["bash", str(FIXTURE), str(dest), "--scenario", "E20", "--no-tracker", "--no-resolve"], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        spec = (dest / "outputs/SPEC-bd-120.md").read_text(encoding="utf-8")
        for ident in list(PROBES["probes"]["E20"]["seeded_violations"]) + list(PROBES["probes"]["E20"]["decoys_met"]):
            self.assertRegex(spec, rf"- {ident} ")
        sys.path.insert(0, str(dest / "src"))
        import importlib
        mod = importlib.import_module("audit_export")
        out = mod.export_csv([{"ts": 1, "actor": "a,b", "action": "x"}, {"ts": 2, "actor": "c", "action": "y"}])
        lines = out.splitlines()
        self.assertEqual("ts,actor,action", lines[0])                  # AC-1 met
        self.assertEqual("2", lines[1].split(",")[0])                  # AC-2 violated (descending)
        self.assertIn("a,b", out)                                      # AC-3 violated (no quoting)
        with self.assertRaises(ValueError):                            # AC-4 violated (raises on empty)
            mod.export_csv([])
        self.assertIn("a-very-long-actor", mod.export_csv([{"ts": 1, "actor": "a-very-long-actor", "action": "x"}]))   # AC-5 met
        mod.export_csv([{"ts": i, "actor": "a", "action": "x"} for i in range(10001)])                                  # AC-6 violated (no limit)
        t = subprocess.run([sys.executable, "-m", "unittest", "tests.test_audit_export"], cwd=dest, capture_output=True, text=True)
        self.assertEqual(0, t.returncode, t.stderr)                    # the seeded change's tests are green
        sys.modules.pop("audit_export", None)
        sys.path.remove(str(dest / "src"))


if __name__ == "__main__":
    unittest.main()
