"""Mutation tests of migration validation, not LLM behavior assertions."""
import copy
import ast
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rule_migrations", ROOT / "scripts/rule-migrations.py")
migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrations)


class InstructionLinesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load the actual pure parser without executing the CLI's git gate.
        tree = ast.parse((ROOT / "scripts/rule-conservation.py").read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "instruction_lines")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "rule-conservation.py", "exec"), namespace)
        cls.parse = staticmethod(namespace["instruction_lines"])

    def test_metadata_excluded_but_body_rules_preserved(self):
        self.assertEqual(["ห้าม remove knowledge", "---", "final rule"], self.parse(
            "---\ndescription: ห้าม metadata trigger\n---\nห้าม remove knowledge\n---\nfinal rule\n"))

    def test_plain_markdown_preserved(self):
        self.assertEqual(["# Rules", "ห้าม delete"], self.parse("# Rules\nห้าม delete\n"))

    def test_empty_source(self):
        self.assertEqual([], self.parse(""))

    def test_unterminated_metadata_fails_closed(self):
        with self.assertRaises(ValueError):
            self.parse("---\ndescription: missing delimiter\nห้าม hide rule")


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / ".rule-migrations.json").read_text())

    def check_mutation(self, data=None, missing_text=None):
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path == ROOT / ".rule-migrations.json":
                return json.dumps(data) if data is not None else original(path, *args, **kwargs)
            text = original(path, *args, **kwargs)
            return text.replace(missing_text, "REMOVED") if missing_text else text
        with patch.object(Path, "read_text", read):
            with self.assertRaises(ValueError):
                migrations.load(ROOT)

    def test_current_migrations_validate(self):
        self.assertEqual(350, len(migrations.load(ROOT)))  # v4.0.1 agent consolidation 18 -> 6 (shode-house-jni): +39 = retired-role list/persona/identity lines reworded to the 6 type names (34 vs the 4.0.0 base HEAD, 8 vs the pinned baseline-3.17, some in both) -- the 311 existing entries were re-pointed (replacement + requires) from the 18 deleted agent files and the 20 renamed runbooks to the files that hold the rule now, count unchanged; final fix-up (UD R90): +1 rewording trace (agents/fintech-expert.md money-movement R0 line, Sentinel W10b I-2); v4.0.0 switch W10b (shode-house-v7u.4.44): +142 = W3 S3 replay +73 (orchestrator.md 34 / oliver.md 39, ledger W3 s3_replay_entries) + W4 floor move +6 + W7 S3 +6 + S3 coverage +47 (persona -> agent id fragments credited only through the deleted orchestrator.md / oliver.md copies, the R72 Map-mode block 4 fragments x 2 sources, the R57 harness line, the ask R0 pointer) + rewording trace +10 (A16(b) table #19 #20 #37 #50 #52 #54, R57 review-checklist/intake/spec-axis x2); fix_existing re-pointed: W3 [3..6], W4 G6 (requires now `shode-house:ui-test`), W7 3; v4 W6 commands: +1 (workflow-root 3b reviewer line reworded to English; its persona-token credit in commands/implement.md is gone after the agent-id rename); v4 W5b bodies (S2 integration 2, v7u.4.25): +26 (8 bodies thinned to lazy references, persona -> agent id; outputs/shode-house-v7u/ledger/W5b.json rule_migrations.new_entries) and 13 fix_existing re-pointed; v4 S2 fix-up v7u.4.21 (UD R55, Chris C14-1): -73 S3-only orchestrator.md (34) / oliver.md (39) retirement entries moved back to the S3 replay (outputs/shode-house-v7u/ledger/W3.json rule_migrations.s3_replay_entries; replayed with fix_existing[3..6] in the switch commit); v4 S2 integration v7u.4.12: +93 W3 router (persona renames, Thai->English router rewrite, S3 orchestrator/oliver retirement fragments) +32 W5a bodies (thinning to lazy references, persona -> agent id); 8ss fast-path decision 2026-09-21: +1 (ask fast-path floor = Dave alone; Chris from Bounded tier up); v3.17 merge: +3 historical notes of the retired team-entry skill; P4: +9 decompose thin-router rewordings; P5: +14 decision-boundary rewordings and byte payments; 8ss.29: +5 completion-contract payments; P6: +30 agent-file bias/persona rewordings; P6 integration: +1 dev-gate checklist re-alignment; P7: +8 ceremony (5 greeting lines incl. one pre-P5 spelling, 2 duplicate narration/load-trigger lines) and trust-label-internal rewording; P10: +7 (1 duplicate evidence example pair (PG) x 2 source spellings: discipline root and the pre-merge evidence skill; 1 restated Universal Rules bullet; 2 restated evidence-protocol lines x 2 source spellings) removed/shortened in the discipline root to pay the CI #16 preload debt (GRACE 600 -> 0) while keeping the Node overturned-assumption example pair

    def test_each_replacement_anchor_is_required(self):
        for item in self.data["migrations"]:
            for anchor in item["requires"]:
                # Source can wrap a phrase across lines; remove its first token
                # everywhere so whitespace normalization cannot conceal removal.
                with self.subTest(anchor=anchor):
                    self.check_mutation(missing_text=anchor.split()[0])

    def test_duplicates_fail(self):
        self.data["migrations"].append(copy.deepcopy(self.data["migrations"][0]))
        self.check_mutation(data=self.data)

    def test_empty_anchor_fails(self):
        self.data["migrations"][0]["requires"] = [""]
        self.check_mutation(data=self.data)

    def test_target_outside_repo_fails(self):
        self.data["migrations"][0]["replacement"] = "../not-a-rule.md"
        self.check_mutation(data=self.data)


if __name__ == "__main__":
    unittest.main()
