#!/usr/bin/env python3
"""Static root-safety-anchor test (v3.17 FR-G-3 AC4 / FR-P9-6 AC1).

Every safety rule that must stay in the ROOT tier has a machine-checked anchor. A split/merge that
drops the line, moves it into a lazy reference (file with a `LOAD:` block), or deletes the map rule
turns this red. Moving a rule = move the anchor text verbatim to another root + update source_of_truth.
Run: python3 tests/test_root_safety_anchors.py   (also collected by pytest)
"""
import json, pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_FILE = re.compile(r"skills/(?:workflow|ops|ui|style|discipline)/[^/]+/SKILL\.md|agents/[^/]+\.md|output-styles/[^/]+\.md")
# Pinned on purpose: removing an id from .enforcement-map.json must fail here, not pass silently.
REQUIRED = {
    "threat-model-trigger", "approval-durability", "approval-gates", "afk-no-waive",
    "lazy-negligent-carveout", "drain-isolation", "drain-independent-review", "a11y-root",
    "secure-data-classification-stop", "review-fixed-point", "reviewer-independence",
    "authority-precedence", "input-trust", "drift-detection", "redact-principle",
}


class RootSafetyAnchorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rules = json.loads((ROOT / ".enforcement-map.json").read_text())["rules"]
        cls.root_only = {r["id"]: r for r in rules if r.get("root_only") is True}

    def test_required_root_only_rules_present(self):
        self.assertEqual(set(), REQUIRED - set(self.root_only))

    def test_each_anchor_lives_in_a_root_file(self):
        for rid, rule in self.root_only.items():
            with self.subTest(rule=rid):
                src, anchor = rule["source_of_truth"], rule.get("anchor", "")
                self.assertRegex(src, ROOT_FILE, "root_only rule must point at a shipped SKILL.md / agent / output style")
                self.assertTrue(ROOT_FILE.fullmatch(src))
                self.assertGreaterEqual(len(anchor), 12)
                text = (ROOT / src).read_text()
                self.assertIsNone(re.search(r"^LOAD:", text, re.M), f"{src} is a lazy reference")
                self.assertIn(anchor, text)


if __name__ == "__main__":
    unittest.main()
