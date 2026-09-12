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
        self.assertEqual(5, len(migrations.load(ROOT)))

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
