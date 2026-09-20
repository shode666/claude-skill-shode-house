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
    # v3.17 Sentinel merge gate F1/F2/F4: lines born in (or moved by) the merge are invisible to the old baseline
    "threat-model-no-waive-root", "drift-m3-ready-merge", "evidence-forbidden-phrases", "evidence-cite-before-claim",
    "safety-r0r1r2", "no-magic", "handoff-contract", "close-on-done", "scope-drift", "verify-before-done",
    # v3.17 P4 thin-router: invariants each slimmed root must keep even when no reference loads
    "routing-sole-owner-reroute", "routing-parallel-unknown-sequential",
    "decompose-signed-off-spec", "decompose-record-authority", "decompose-no-remote-tickets",
    "incident-mitigate-first", "incident-blameless", "incident-authority-runbook", "redact", "ux-evidence",
    # Sentinel P4 wave gate X1/X2: authority rules restored to the root tier
    "devgate-security-no-suppress", "drain-conflict-no-discard",
}
# Sentinel G-C2 / N5b: the R0 destructive list is split on the middle dot, so rule-conservation skips
# its short items. Each item is pinned here instead; all 8 must stay in the discipline ROOT.
DISCIPLINE_ROOT = "skills/discipline/shode-house-discipline/SKILL.md"
WORKFLOW_ROOT = "skills/discipline/shode-house-workflow/SKILL.md"
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

    def test_heading_anchors_have_their_body_in_the_same_root(self):
        # Sentinel X3: an anchor on a HEADING only pins the heading; the body could move to a lazy
        # reference with every other gate green. Pin the body lines of each heading-type anchor.
        body = {
            "skills/workflow/dev-gate/SKILL.md": (
                "Trust-boundary validation", "Data-loss handling", "Security control",
                "Accessibility (WCAG", "Regulation/compliance"),
            "skills/workflow/diagnose/SKILL.md": ("`<REDACTED>` แทน secret/token/auth header/PII",),
            DISCIPLINE_ROOT: (
                '"usually"', '"by default"', '"typically"', '"standard practice"', '"best practice"',
                '"should support"', '"น่าจะรองรับ"', '"ปกติแล้ว"', '"in most cases"', '"โดยทั่วไป"'),
            "agents/orchestrator.md": ("| Pre-deploy-prod |", "| Pre-data-migration |", "| Pre-destructive |"),
        }
        for src, needles in body.items():
            lines = (ROOT / src).read_text().splitlines()
            for needle in needles:
                with self.subTest(root=src, body=needle):
                    self.assertTrue(any(needle in l and not l.startswith("#") for l in lines))

    def test_r0_destructive_list_complete_in_discipline_root(self):
        text = (ROOT / DISCIPLINE_ROOT).read_text()
        r0_line = next((l for l in text.splitlines() if l.startswith("**Destructive R0**")), "")
        for item in R0_DESTRUCTIVE:
            with self.subTest(item=item):
                self.assertIn(item, r0_line, "R0 destructive item missing from the discipline root list")

    def test_phase_1c_trigger_list_is_the_same_everywhere(self):
        """Sentinel F3: the canonical 8-item list lives in the workflow root; the matcher and the three
        citing files must cover every item (dropping e.g. "session" from routes.json used to pass silently)."""
        root = (ROOT / WORKFLOW_ROOT).read_text()
        line = next(l for l in root.splitlines() if l.startswith("- **Trigger**: feature touching "))
        items = [i.strip() for i in line.split("feature touching ", 1)[1].split(" / ")]
        self.assertEqual(8, len(items), items)
        rules = {r["id"]: r for r in json.loads((ROOT / "references/registry/routes.json").read_text())["routes"]}
        covered = set(rules["security-money-auth"]["when"]["any"])
        covered |= {k for k, v in rules["security-pii"]["when"].items() if v is True}
        for item in items:
            with self.subTest(item=item):
                key = item.lower().replace(" ", "-")
                # a later, approved narrowing may replace "session" by adjacent phrases ("session token", ...)
                self.assertTrue(key in covered or any(c.startswith(key + " ") for c in covered),
                                f"routes.json does not cover 1c trigger '{item}'")
        same = "/".join(items)
        for path in ("skills/discipline/shode-house-workflow/harness.md",
                     "skills/discipline/shode-house-workflow/smart-coop.md", "agents/orchestrator.md"):
            with self.subTest(file=path):
                self.assertIn(same, (ROOT / path).read_text())


if __name__ == "__main__":
    unittest.main()
