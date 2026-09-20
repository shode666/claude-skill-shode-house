"""Conditional extraction must not make full-path accounting artificially cheap."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContextBudgetTest(unittest.TestCase):
    def test_full_diagnosis_counts_required_extracted_investigation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/context-budget.py"), "--json"],
            check=True, capture_output=True, text=True,
        )
        scenarios = json.loads(result.stdout)["scenarios"]
        root = ROOT / "skills/workflow/diagnose"
        expected = sum((root / name).stat().st_size for name in
                       ("SKILL.md", "full-investigation.md", "loop-ladder.md"))
        self.assertEqual(scenarios["diagnose-full"]["lazy_refs"], expected)
        self.assertEqual(scenarios["diagnose-fast"]["lazy_refs"],
                         (root / "SKILL.md").stat().st_size)


if __name__ == "__main__":
    unittest.main()
