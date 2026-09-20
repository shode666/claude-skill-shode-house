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


if __name__ == "__main__":
    unittest.main()
