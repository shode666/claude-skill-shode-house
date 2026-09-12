"""Unit tests for scripts/team-run-check.py on synthetic stream-json events (no live run)."""
import importlib.util, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trc", ROOT / "scripts/team-run-check.py")
trc = importlib.util.module_from_spec(spec); spec.loader.exec_module(trc)


def tool(name, inp, parent=None):
    e = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}
    if parent: e["parent_tool_use_id"] = parent
    return e


def spawn(role, parent=None): return tool("Task", {"subagent_type": f"shode-house:{role}"}, parent)
def bash(cmd): return tool("Bash", {"command": cmd})
RESULT = {"type": "result", "subtype": "success", "total_cost_usd": 1.0, "modelUsage": {"m": {"outputTokens": 10}}}


class TeamRunCheckTest(unittest.TestCase):
    def good(self):
        return [spawn("developer"), spawn("code-reviewer"), spawn("qa-engineer"), bash("git remote -v"), RESULT]

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

    def test_missing_expected_role_and_self_review_fail(self):
        events = [spawn("developer"), {"type": "assistant", "message": {"content": [{"type": "text", "text": "I self-reviewed the diff and it passes."}]}}, RESULT]
        checks, _ = trc.analyze(events, expect_roles=["code-reviewer"])
        self.assertFalse(checks["spawned_code-reviewer"][0])
        self.assertFalse(checks["independent_review"][0])


if __name__ == "__main__":
    unittest.main()
