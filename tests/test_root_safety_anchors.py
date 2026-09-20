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
    # v3.17 Sentinel G-C1 (anchor-first, before the 24->20 merge touches any root)
    "approval-void-on-change", "approval-rehash-before-gate", "approval-chat-not-counted",
    "threat-model-no-waive", "threat-model-pre-phase2",
    "no-commit-secret", "no-skip-security", "money-precision", "reviewer-risk-tier", "r0-confirm-protocol",
    "drift-m2-classifier", "drift-m4-feedback", "drift-m5-spec-change", "drift-m7-direct-block",
}
# Sentinel G-C2 / N5b: the R0 destructive list is split on the middle dot, so rule-conservation skips
# its short items. Each item is pinned here instead; all 8 must stay in the discipline ROOT.
DISCIPLINE_ROOT = "skills/discipline/shode-house-discipline/SKILL.md"
R0_DESTRUCTIVE = (
    "git push --force", "git reset --hard", "DROP TABLE", "DELETE without WHERE", "rm -rf",
    "delete prod resource", "edit migration ที่ apply prod", "modify auth/IAM",
)


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

    def test_r0_destructive_list_complete_in_discipline_root(self):
        text = (ROOT / DISCIPLINE_ROOT).read_text()
        r0_line = next((l for l in text.splitlines() if l.startswith("**Destructive R0**")), "")
        for item in R0_DESTRUCTIVE:
            with self.subTest(item=item):
                self.assertIn(item, r0_line, "R0 destructive item missing from the discipline root list")


if __name__ == "__main__":
    unittest.main()
