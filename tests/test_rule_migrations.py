"""Mutation tests of migration validation, not LLM behavior assertions."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rule_migrations", ROOT / "scripts/rule-migrations.py")
migrations = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrations)


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
