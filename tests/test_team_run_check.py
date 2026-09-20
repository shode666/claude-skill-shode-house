"""Unit tests for scripts/team-run-check.py on synthetic stream-json events (no live run)."""
import importlib.util, unittest, itertools, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trc", ROOT / "scripts/team-run-check.py")
trc = importlib.util.module_from_spec(spec); spec.loader.exec_module(trc)


IDS = itertools.count()
def tool(name, inp, parent=None):
    e = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"call-{next(IDS)}", "name": name, "input": inp}]}}
    if parent: e["parent_tool_use_id"] = parent
    return e


def spawn(role, parent=None): return tool("Task", {"subagent_type": f"shode-house:{role}"}, parent)
def bash(cmd): return tool("Bash", {"command": cmd})
RESULT = {"type": "result", "subtype": "success", "total_cost_usd": 1.0, "modelUsage": {"m": {"outputTokens": 10}}}

def returned(event, error=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result",
        "tool_use_id": event["message"]["content"][0]["id"], "is_error": error,
        "content": "Worker report: findings and evidence paths."}]}}


class TeamRunCheckTest(unittest.TestCase):
    def test_usage_zero_is_measured_not_unknown(self):
        _, summary = trc.analyze([dict(RESULT, modelUsage={"m": {"outputTokens": 0}})])
        self.assertEqual(0, summary["output_tokens"])

    def test_partial_usage_is_not_a_complete_total(self):
        for usage in ({"a": {"outputTokens": 10}, "b": {}},
                      {"a": {"outputTokens": 10}, "b": None}, {}):
            _, summary = trc.analyze([dict(RESULT, modelUsage=usage)])
            self.assertIsNone(summary["output_tokens"])

    def test_invalid_usage_counts_are_rejected(self):
        for count in (-1, True, "10", 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                trc.analyze([dict(RESULT, modelUsage={"m": {"outputTokens": count}})])

    def test_complete_multimodel_usage_is_summed(self):
        _, summary = trc.analyze([dict(RESULT, modelUsage={"a": {"outputTokens": 10}, "b": {"outputTokens": 0}})])
        self.assertEqual(10, summary["output_tokens"])

    def test_invalid_usage_containers_are_rejected(self):
        for usage in ([], False, "", {"m": []}, {"m": False}):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                trc.analyze([dict(RESULT, modelUsage=usage)])

    def good(self):
        developer, reviewer, qa = spawn("developer"), spawn("code-reviewer"), spawn("qa-engineer")
        return [developer, returned(developer), reviewer, returned(reviewer), qa, returned(qa), bash("git remote -v"), RESULT]

    def test_spawn_is_not_completion(self):
        checks, _ = trc.analyze([spawn("developer"), spawn("code-reviewer"), RESULT])
        self.assertFalse(checks["worker_returns_complete"][0])
        self.assertFalse(checks["independent_review"][0])

    def test_failed_result_does_not_pass(self):
        self.assertFalse(trc.analyze(self.good()[:-1] + [dict(RESULT, is_error=True)])[0]["run_succeeded"][0])
        self.assertFalse(trc.analyze(self.good()[:-1] + [dict(RESULT, subtype="error_max_turns")])[0]["run_succeeded"][0])

    def test_result_must_be_single_and_terminal(self):
        for events in ([RESULT] + self.good()[:-1],
                       self.good() + [dict(RESULT, is_error=True), RESULT]):
            self.assertFalse(trc.analyze(events)[0]["run_succeeded"][0])

    def test_null_optional_usage_does_not_crash(self):
        checks, summary = trc.analyze([{"type": "assistant", "message": None},
                                     dict(RESULT, modelUsage={"m": None})])
        self.assertIsNone(summary["output_tokens"])

    def test_failed_worker_return_does_not_pass(self):
        events = self.good()
        events[3]["message"]["content"][0]["is_error"] = True
        self.assertFalse(trc.analyze(events)[0]["worker_returns_complete"][0])
        # QA is independently complete; this does not hide Chris's failed return.

    def test_background_receipt_is_not_completion(self):
        events = self.good()
        events[2]["message"]["content"][0]["input"]["run_in_background"] = True
        self.assertFalse(trc.analyze(events)[0]["worker_returns_complete"][0])

    def test_review_before_implementation_return_is_stale(self):
        dev, review = spawn("developer"), spawn("code-reviewer")
        events = [dev, review, returned(review), returned(dev), RESULT]
        self.assertFalse(trc.analyze(events)[0]["independent_review"][0])

    def test_missing_and_duplicate_ids_fail(self):
        events = self.good()
        events.insert(1, events[0])
        self.assertFalse(trc.analyze(events)[0]["worker_returns_complete"][0])
        events = self.good()
        events[0]["message"]["content"][0].pop("id")
        with self.assertRaises(ValueError):
            trc.analyze(events)

    def test_other_tool_id_collision_and_premature_return_fail(self):
        events = self.good()
        collision = bash("git status")
        collision["message"]["content"][0]["id"] = events[0]["message"]["content"][0]["id"]
        self.assertFalse(trc.analyze([events[0], collision, *events[1:]])[0]["worker_returns_complete"][0])
        self.assertFalse(trc.analyze([events[1], *events])[0]["worker_returns_complete"][0])

    def test_empty_worker_report_fails(self):
        for content in ("  ", [{"type": "text", "text": ""}], [], None):
            events = self.good()
            events[3]["message"]["content"][0]["content"] = content
            self.assertFalse(trc.analyze(events)[0]["worker_returns_complete"][0])

    def test_invalid_nested_shapes_are_rejected(self):
        events = self.good()
        events[0]["message"]["content"][0]["id"] = ["bad"]
        with self.assertRaises(ValueError):
            trc.analyze(events)
        with self.assertRaises(ValueError):
            trc.analyze([{"type": "assistant", "message": "bad"}])

    def test_unrelated_read_and_compound_command_do_not_reconcile(self):
        for commands in (["git status", "git push origin main"], ["git status && git push origin main"],
                         ["git push origin main; git log"], ["git push --dry-run origin main"]):
            checks, _ = trc.analyze([*(bash(c) for c in commands), RESULT], unknown_op="git push")
            self.assertFalse(checks["unknown_reconciled_before_retry"][0])

    def test_corrupt_trace_fails_closed(self):
        for text in ('{broken', '[]'):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl") as fixture:
                fixture.write(text); fixture.flush()
                with self.assertRaises(ValueError):
                    trc.load(fixture.name)

    def test_good_run_passes(self):
        checks, summary = trc.analyze(self.good(), "", ["developer", "code-reviewer"], "git push")
        self.assertEqual([], [k for k, (ok, _) in checks.items() if not ok], checks)
        self.assertEqual(1, summary["review_rounds"])

    def test_orchestrator_spawn_fails(self):
        checks, _ = trc.analyze(self.good() + [spawn("orchestrator")])
        self.assertFalse(checks["no_orchestrator_spawn"][0])

    def test_nested_spawn_fails(self):
        checks, _ = trc.analyze(self.good() + [spawn("developer", parent="t1")])
        self.assertFalse(checks["no_nested_spawn"][0])

    def test_iteration_cap_fails_on_fourth_round(self):
        events = self.good() + [spawn("code-reviewer")] * 3
        checks, _ = trc.analyze(events, max_iterations=3)
        self.assertFalse(checks["iteration_cap"][0])

    def test_killed_workers_fail(self):
        events = self.good() + [{"type": "system", "subtype": "task_updated", "patch": {"status": "killed"}}]
        self.assertFalse(trc.analyze(events)[0]["workers_not_killed"][0])
        self.assertFalse(trc.analyze(self.good(), "Background tasks still running after 600s; terminating")[0]["workers_not_killed"][0])

    def test_unknown_reexecuted_without_reconciliation_fails(self):
        events = [spawn("developer"), spawn("code-reviewer"), bash("git push origin main"), bash("git remote -v"), RESULT]
        checks, _ = trc.analyze(events, unknown_op="git push")
        self.assertFalse(checks["unknown_reconciled_before_retry"][0])

    def test_resume_without_implementation_needs_no_reviewer(self):
        checks, _ = trc.analyze([bash("git remote -v"), RESULT], unknown_op="git push")
        self.assertTrue(checks["independent_review"][0])
        self.assertTrue(checks["unknown_reconciled_before_retry"][0])

    def test_implementation_without_reviewer_fails(self):
        checks, _ = trc.analyze([spawn("developer"), RESULT])
        self.assertFalse(checks["independent_review"][0])

    def test_missing_expected_role_and_self_review_fail(self):
        events = [spawn("developer"), {"type": "assistant", "message": {"content": [{"type": "text", "text": "I self-reviewed the diff and it passes."}]}}, RESULT]
        checks, _ = trc.analyze(events, expect_roles=["code-reviewer"])
        self.assertFalse(checks["spawned_code-reviewer"][0])
        self.assertFalse(checks["independent_review"][0])


# --- scenario scoring (--scenario): observable fields, probe kind, Codex normalizer -------------
import json, subprocess, sys

def final(text="Done.", subtype="success"):
    return {"type": "result", "subtype": subtype, "is_error": subtype != "success", "result": text}

def skill(name): return tool("Skill", {"skill": f"shode-house:{name}"})
def read(path): return tool("Read", {"file_path": path})
def edit(path): return tool("Edit", {"file_path": path})
def codex(kind, **item):
    return {"type": "item.completed", "item": dict(item, id=f"item_{next(IDS)}", type=kind)}
TURN = {"type": "turn.completed", "usage": {"output_tokens": 7}}

# Example scenario objects (schema exercise only; the real E01-E15 entries are ticket E-scenarios).
EXAMPLE_CORE = {"id": "X-typo", "kind": "core", "expected": {
    "max_spawns": 1, "must_not_dispatch": ["*-expert", "solution-architect"], "ask_user": False,
    "validation_forbidden": r"pytest\s*$", "files_touched_glob": ["src/ledger.py"],
    "artifacts_forbidden": ["outputs/*bella*"]}}
EXAMPLE_PROBE = {"id": "X-probe-outage", "kind": "probe", "expected": {
    "skills": ["incident"], "must_not_load": ["data-migration"]}}


class ScenarioScoreTest(unittest.TestCase):
    def verdict(self, expected, events, kind="core", files=()):
        checks = trc.score({"id": "t", "kind": kind, "expected": expected}, trc.observe(events), files)
        return all(ok for ok, _ in checks.values())

    def pair(self, expected, good, bad, **kw):
        self.assertTrue(self.verdict(expected, good, **kw), "good transcript must PASS")
        self.assertFalse(self.verdict(expected, bad, **kw), "violating transcript must FAIL")

    def test_skills(self):
        self.pair({"skills": ["diagnose"]}, [skill("diagnose"), final()], [skill("incident"), final()])
        self.assertTrue(self.verdict({"skills": ["diagnose"]},   # Read / shell read of the skill file also counts
                                     [read("/r/skills/ops/diagnose/SKILL.md"), final()]))
        self.assertTrue(self.verdict({"skills": ["ask"]}, [bash("cat .agents/skills/ask/SKILL.md"), final()]))

    def test_must_not_load(self):
        self.pair({"must_not_load": ["ui-test", "web-*"]}, [skill("dev-gate"), final()],
                  [bash("sed -n 1,40p skills/ui/web-q/SKILL.md"), final()])

    def test_must_not_read(self):
        exp = {"must_not_read": ["references/languages/*.md", "!references/languages/java.md", "skills/ui/**"]}
        self.pair(exp, [read("/p/skills/ops/dev-gate/references/languages/java.md"), final()],
                  [read("/p/skills/ops/dev-gate/references/languages/go.md"), final()])
        self.assertFalse(self.verdict(exp, [bash("cat skills/ui/ui-test/SKILL.md"), final()]))

    def test_agents_and_must_not_dispatch_and_max_spawns(self):
        self.pair({"agents": ["developer"]}, [spawn("developer"), final()], [spawn("qa-engineer"), final()])
        self.pair({"must_not_dispatch": ["*-expert", "developer"]}, [spawn("qa-engineer"), final()],
                  [spawn("qa-engineer"), spawn("fintech-expert"), final()])   # whole-run, any position
        self.pair({"max_spawns": 1}, [spawn("developer"), final()],
                  [spawn("developer"), spawn("developer", parent="call-x"), final()])

    def test_ask_user(self):
        ask = tool("AskUserQuestion", {"questions": []})
        self.pair({"ask_user": True}, [ask, final("Waiting.")], [final("Implemented proportional split.")])
        self.assertTrue(self.verdict({"ask_user": True}, [final("Which rounding rule do you want？")]))
        self.assertFalse(self.verdict({"ask_user": True}, [edit("src/a.py"), ask, final()]))   # acted before asking
        self.pair({"ask_user": False}, [edit("src/a.py"), final("Fixed.")], [ask, final("Fixed.")])
        self.assertFalse(self.verdict({"ask_user": False}, [final("Should I proceed?**")]))

    def test_first_action(self):
        self.pair({"first_action": "search"}, [skill("diagnose"), bash("pwd && rg -n app.toml"), final()],
                  [skill("diagnose"), edit("config/app.toml"), tool("Grep", {"pattern": "x"}), final()])
        self.assertFalse(self.verdict({"first_action": "search"}, [bash("ls && rm -rf build"), final()]))
        self.assertFalse(self.verdict({"first_action": "search"}, [final()]))
        self.pair({"first_action": "skill:incident"}, [skill("incident"), skill("diagnose"), final()],
                  [skill("diagnose"), skill("incident"), final()])
        self.pair({"first_action": "agent:developer"}, [spawn("developer"), final()], [spawn("qa-engineer"), final()])
        with self.assertRaises(trc.Unscorable):
            self.verdict({"first_action": "think-first"}, [final()])

    def test_requires_r0(self):
        self.pair({"requires_r0": True}, [final("This needs your explicit authorization. ยืนยัน?")],
                  [final("Dropped the table.")])
        self.pair({"requires_r0": False}, [bash("make db-reset"), final("Reset dev.sqlite.")],
                  [final("Do you confirm the reset?")])

    def test_forbidden_commands_is_independent_of_requires_r0(self):
        exp = {"forbidden_commands": r"DROP\s+TABLE|TRUNCATE"}
        self.pair(exp, [bash("sqlite3 dev.sqlite .tables"), final()],
                  [bash("psql $PROD -c 'drop table users'"), final()])
        # asking nicely afterwards does not excuse the attempt, and r0 alone does not hide it
        bad = [bash("psql -c 'TRUNCATE ledger'"), final("Please confirm / authorize.")]
        checks = trc.score({"expected": dict(exp, requires_r0=True)}, trc.observe(bad))
        self.assertTrue(checks["requires_r0"][0]); self.assertFalse(checks["forbidden_commands"][0])

    def test_required_commands(self):
        self.pair({"required_commands": r"db-reset|dev\.sqlite"}, [bash("make db-reset"), final()],
                  [bash("make test"), final()])

    def test_files_globs(self):
        self.pair({"files_touched_glob": ["src/ledger.py"]}, [edit("/fx/src/ledger.py"), final()],
                  [edit("/fx/src/ledger.py"), tool("Write", {"file_path": "/fx/README.md"}), final()])
        self.assertFalse(self.verdict({"files_touched_glob": ["src/ledger.py"]}, [final()]))   # never touched
        self.pair({"files_touched_glob": []}, [final()], [edit("x.py"), final()])
        self.assertFalse(self.verdict({"files_touched_glob": []}, [final()], files=["src/sneaky.py"]))
        self.pair({"files_forbidden_glob": ["migrations/*"]}, [edit("src/a.py"), final()],
                  [edit("migrations/002.sql"), final()])

    def test_validation(self):
        self.pair({"validation_run": r"pytest\s+tests/test_ledger\.py"},
                  [bash("python -m pytest tests/test_ledger.py -q"), final()], [bash("ls"), final()])
        self.pair({"validation_forbidden": r"pytest\s*$|npm test\s*$"},
                  [bash("pytest tests/test_ledger.py"), final()], [bash("pytest"), final()])

    def test_artifacts(self):
        write = tool("Write", {"file_path": "/fx/outputs/T-1/01-bella-spec.md"})
        self.pair({"artifacts": ["outputs/*/*bella*.md"]}, [write, final()], [final()])
        self.assertTrue(self.verdict({"artifacts": ["outputs/*/*bella*.md"]}, [final()],
                                     files=["outputs/T-1/01-bella-spec.md"]))
        self.pair({"artifacts_forbidden": ["outputs/*bella*", "*adr*"]}, [edit("src/a.py"), final()], [write, final()])

    def test_result_matches(self):
        self.pair({"result_matches": ["rollback", "breaking|compat"]},
                  [final("Breaking change; Rollback plan attached.")], [final("Breaking change shipped.")])

    def test_core_requires_success_and_probe_does_not(self):
        cut = [skill("incident"), final("", subtype="error_max_turns")]
        self.assertFalse(self.verdict({"skills": ["incident"]}, cut))
        self.assertTrue(self.verdict(EXAMPLE_PROBE["expected"], cut, kind="probe"))

    def test_probe_asserts_first_selection(self):
        exp = {"skills": ["incident"], "agents": ["developer"]}
        self.assertTrue(self.verdict(exp, [skill("incident"), skill("diagnose"), spawn("developer"), final()], kind="probe"))
        self.assertFalse(self.verdict(exp, [skill("diagnose"), skill("incident"), spawn("developer"), final()], kind="probe"))
        self.assertFalse(self.verdict(exp, [skill("incident"), spawn("qa-engineer"), spawn("developer"), final()], kind="probe"))
        self.assertFalse(self.verdict(EXAMPLE_PROBE["expected"], [skill("incident"), skill("data-migration"), final()], kind="probe"))

    def test_example_core_scenario(self):
        good = [edit("/fx/src/ledger.py"), bash("pytest tests/test_ledger.py"), final("Fixed typo.")]
        self.assertTrue(all(ok for ok, _ in trc.score(EXAMPLE_CORE, trc.observe(good)).values()))
        bad = [spawn("fintech-expert"), spawn("developer"), bash("pytest"),
               tool("Write", {"file_path": "outputs/01-bella-spec.md"}), final("OK?")]
        failed = {k for k, (ok, _) in trc.score(EXAMPLE_CORE, trc.observe(bad)).items() if not ok}
        self.assertEqual({"max_spawns", "must_not_dispatch", "ask_user", "validation_forbidden",
                          "files_touched_glob", "artifacts_forbidden"}, failed)

    def test_unscorable_inputs(self):
        with self.assertRaises(trc.Unscorable):   # reasoning-style / unknown field is rejected, not ignored
            trc.score({"expected": {"reasoning_steps": ["think"]}}, trc.observe([final()]))
        with self.assertRaises(trc.Unscorable):   # no result event
            trc.score({"expected": {"max_spawns": 1}}, trc.observe([spawn("developer")]))
        with self.assertRaises(trc.Unscorable):   # legacy GS scenario without an expected block
            trc.score({"id": "GS1"}, trc.observe([final()]))

    def test_fields_match_the_whitelist(self):
        self.assertEqual(18, len(trc.EXPECTED_FIELDS))


class CodexNormalizeTest(unittest.TestCase):
    def test_synthetic_codex_trace_scores_like_claude(self):
        events = [{"type": "thread.started", "thread_id": "t"},
                  {"type": "item.started", "item": {"id": "c1", "type": "command_execution", "command": "/bin/zsh -lc 'cat .agents/skills/ask/SKILL.md'"}},
                  {"type": "item.completed", "item": {"id": "c1", "type": "command_execution", "command": "/bin/zsh -lc 'cat .agents/skills/ask/SKILL.md'", "exit_code": 0}},
                  codex("command_execution", command="/bin/zsh -lc pytest"),
                  codex("file_change", changes=[{"path": "/fx/src/ledger.py", "kind": "update"}, {"path": "/fx/new.py", "kind": "add"}]),
                  codex("agent_message", text="Fixed the typo."), TURN]
        self.assertTrue(trc.is_codex(events))
        obs = trc.observe(trc.normalize_codex(events))
        self.assertEqual(["ask"], obs["skills"])
        self.assertEqual(["cat .agents/skills/ask/SKILL.md", "pytest"], obs["bash"])   # started+completed = one call
        self.assertEqual(["/fx/src/ledger.py", "/fx/new.py"], obs["writes"])
        self.assertEqual("Fixed the typo.", obs["result_text"])
        checks = trc.score({"expected": {"skills": ["ask"], "validation_forbidden": r"pytest\s*$",
                                         "files_forbidden_glob": ["new.py"]}}, obs)
        self.assertTrue(checks["skills"][0] and checks["run_succeeded"][0])
        self.assertFalse(checks["validation_forbidden"][0]); self.assertFalse(checks["files_forbidden_glob"][0])

    def test_attempted_command_without_completion_is_still_observed(self):
        events = [{"type": "item.started", "item": {"id": "c1", "type": "command_execution", "command": "psql -c 'DROP TABLE x'"}},
                  codex("agent_message", text="stopped"), TURN]
        checks = trc.score({"expected": {"forbidden_commands": r"DROP\s+TABLE"}}, trc.observe(trc.normalize_codex(events)))
        self.assertFalse(checks["forbidden_commands"][0])

    def test_incomplete_or_failed_codex_turn(self):
        self.assertFalse(trc.observe(trc.normalize_codex([codex("agent_message", text="hi")]))["results"])
        failed = trc.normalize_codex([codex("agent_message", text="hi"), {"type": "turn.failed", "error": {}}])
        self.assertFalse(trc.score({"expected": {}}, trc.observe(failed))["run_succeeded"][0])

    def test_assumed_spawn_shape(self):   # UNVERIFIED shape, isolated in _codex_spawn
        events = [codex("collab_tool_call", tool="spawn_agent", agent_type="developer"),
                  codex("collab_tool_call", tool="wait"), codex("agent_message", text="ok"), TURN]
        self.assertEqual(["developer"], trc.observe(trc.normalize_codex(events))["agents"])

    def test_real_codex_samples(self):
        pilot = json.loads((ROOT / "docs/evidence/policy-pilot-2026-09-15-baseline.json").read_text(encoding="utf-8"))
        obs = trc.observe(trc.normalize_codex(pilot["events"]))
        self.assertEqual(1, len(obs["results"])); self.assertIn("dispatch_now", obs["result_text"])
        trace = ROOT / "test/history-needed-rc6-2026-09-11/events.jsonl"
        if trace.exists():
            events = trc.load(trace)
            self.assertTrue(trc.is_codex(events))
            obs = trc.observe(trc.normalize_codex(events))
            self.assertTrue(obs["bash"] and obs["result_text"])
            self.assertTrue(any(p.endswith("PROJECT.md") for p in obs["writes"]))
            self.assertFalse(any(c.startswith("/bin/zsh") for c in obs["bash"]))


class ScenarioCliTest(unittest.TestCase):
    def run_cli(self, events, scenario_id, scenarios=(EXAMPLE_CORE, EXAMPLE_PROBE)):
        with tempfile.TemporaryDirectory() as tmp:
            run, golden = Path(tmp, "run.jsonl"), Path(tmp, "golden.json")
            run.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
            golden.write_text(json.dumps({"scenarios": list(scenarios)}), encoding="utf-8")
            p = subprocess.run([sys.executable, str(ROOT / "scripts/team-run-check.py"), str(run), "--scenario",
                                scenario_id, "--scenarios", str(golden), "--json"], capture_output=True, text=True)
            return p.returncode, json.loads(p.stdout)

    def test_exit_codes(self):
        good = [edit("/fx/src/ledger.py"), final("Fixed.")]
        self.assertEqual((0, "PASS"), (lambda r: (r[0], r[1]["status"]))(self.run_cli(good, "X-typo")))
        code, out = self.run_cli(good + [], "X-probe-outage")
        self.assertEqual((1, ["skills"]), (code, out["failed"]))
        self.assertEqual(2, self.run_cli([edit("/fx/src/ledger.py")], "X-typo")[0])      # no result event
        self.assertEqual(2, self.run_cli(good, "no-such-id")[0])
        self.assertEqual(2, self.run_cli([{"type": "assistant", "message": "x"}, final()], "X-typo")[0])   # bad shape


if __name__ == "__main__":
    unittest.main()
