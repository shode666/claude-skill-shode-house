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
    # Sentinel P5 sign-off (P5-C2): every line of a "### Stop and return" + the hand-off evidence A-items
    "devgate-stop-no-acceptance", "devgate-stop-check-unrunnable", "devgate-stop-security-suppress",
    "devgate-handoff-not-done", "devgate-quarantine-not-pass", "devgate-evidence-paste",
    "decompose-interface-contract-owner", "decompose-stop-no-guess", "decompose-no-spec-route",
    "drain-ready-set-verified", "drain-verified-open", "drain-per-item-scope", "drain-routing-owner",
    "drain-owner-greenlight", "drain-stop-before-fanout",
    "secure-architecture-doc-stop", "secure-regulation-scope-stop", "secure-boundary-confirm", "secure-no-assume",
    "review-stop-scope-unpinned", "review-no-spec-no-silent-pass",
    "diagnose-stop-no-symptom", "diagnose-no-guess-root-cause", "ask-conditions",
    # Sentinel P5 real-diff gate F2/F3: R2 needs evidence-of-local; dev-gate stop ACTION half
    "r2-needs-local-evidence", "devgate-stop-list-and-return",
    # 8ss.29 completion contract (Sentinel C29-1/C29-3/C29-5): precedence + stop-when + affected-validation floor
    "stop-over-completion", "completion-stop-when", "completion-no-widen",
    "affected-validation-floor", "affected-validation-required-suites",
    # Sentinel P6-C1/C4 anchor-first: PROTECTED bias lines (14-audit Table 5) + reviewer ownership tables, before P6 edits any agent file
    "standards-axis", "integration-axis", "wcag22",
    "bias-chris-no-pass-without-evidence", "bias-chris-unavailable-blocked", "bias-quinn-missing-blocked",
    "bias-felix-psp-fit", "bias-felix-thai-context", "bias-felix-cite-before-psp",
    "bias-felix-money-r0", "bias-sentinel-low-risk-hold", "bias-sentinel-low-risk-evidence",
    "bias-sentinel-no-should-be-fine", "bias-sentinel-false-positive-evidence", "bias-stan-divergence-needs-doc",
    "bias-tara-no-blind-vendor", "bias-tara-local-alternatives", "bias-tara-cite-before-vendor",
    "bias-oliver-only-oliver-closes", "own-chris-handoff-table", "own-quinn-handoff-table",
    "own-sentinel-not-mine-table", "own-uma-self-routing-table",
}
DELIVERABLE_ROOT = "skills/discipline/shode-house-deliverable/SKILL.md"
PRECEDENCE = ('**Stop and return outranks completion.** "Continue until complete" never overrides a Stop-and-return '
              "condition, an R0/R1 protocol, an approval gate or an ownership boundary: when one applies, stop, record "
              "what is missing and return to Oliver — a stopped task reported honestly is a correct outcome, not a "
              "failure to complete.")
# P5-C2: anchors that must sit INSIDE the root's "### Stop and return" (under "## Inputs and decision boundaries").
STOP_AND_RETURN = {
    "skills/workflow/dev-gate/SKILL.md": (
        "devgate-stop-list-and-return", "devgate-stop-no-acceptance", "devgate-stop-check-unrunnable",
        "devgate-stop-security-suppress"),
    "skills/workflow/decompose/SKILL.md": (
        "decompose-signed-off-spec", "decompose-record-authority", "decompose-interface-contract-owner",
        "decompose-stop-no-guess", "decompose-no-spec-route"),
    "skills/ops/drain/SKILL.md": (
        "drain-ready-set-verified", "drain-verified-open", "drain-per-item-scope", "drain-routing-owner",
        "drain-owner-greenlight", "drain-stop-before-fanout"),
    "skills/ops/secure/SKILL.md": (
        "secure-architecture-doc-stop", "secure-data-classification-stop", "secure-boundary-confirm",
        "secure-regulation-scope-stop", "secure-no-assume"),
    "skills/discipline/review-checklist/SKILL.md": ("review-stop-scope-unpinned", "review-no-spec-no-silent-pass"),
    "skills/workflow/diagnose/SKILL.md": ("diagnose-stop-no-symptom", "diagnose-no-guess-root-cause"),
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
        # P5: heading anchors `ask-conditions` (discipline) and `devgate-handoff-not-done` (dev-gate)
        body[DISCIPLINE_ROOT] += (
            "(1) readings differ materially", "never replaces the R0/R1 protocol, § Safety and a skill's Stop-and-return always win",
            "(3) product/business/legal decision", "(4) evidence cannot answer",
            "Workers return the question to Oliver", "unsure whether material = material")
        body["skills/workflow/dev-gate/SKILL.md"] += (
            "tracked quarantine does not satisfy a missing required test",
            "**Evidence paste**: command + output ใน hand-off", "**Test runs locally** (red phase)",
            "**Quality gate ผ่านครบ 11**")
        for src, needles in body.items():
            lines = (ROOT / src).read_text().splitlines()
            for needle in needles:
                with self.subTest(root=src, body=needle):
                    self.assertTrue(any(needle in l and not l.startswith("#") for l in lines))

    @staticmethod
    def _stop_and_return(text):
        """Body of "### Stop and return" inside "## Inputs and decision boundaries" ("" when absent)."""
        section = re.search(r"(?ms)^## Inputs and decision boundaries\n(.*?)(?=^## |\Z)", text)
        sub = re.search(r"(?ms)^### Stop and return\n(.*?)(?=^### |\Z)", section.group(1)) if section else None
        return sub.group(1).strip() if sub else ""

    def test_stop_and_return_holds_every_stop_anchor(self):
        # P5-C2: a stop that drifts out of the subsection (or an emptied subsection) must turn red.
        for src, ids in STOP_AND_RETURN.items():
            text = (ROOT / src).read_text()
            self.assertNotRegex(text, r"(?m)^## .*refuse without", src)
            stop = self._stop_and_return(text)
            self.assertTrue(stop, src + ": '### Stop and return' missing or empty")
            for rid in ids:
                with self.subTest(root=src, rule=rid):
                    self.assertIn(self.root_only[rid]["anchor"], stop)
            self.assertIn("`shode-house-discipline` § Ask vs derive", text)

    # Sentinel F3 (mutation d): a stop/derive line rewritten into "assume the default" passed every gate.
    FORBIDDEN = re.compile(r"(?i)\bassume\b|สมมติ(?!เอง)|\bdefault to\b")
    NEGATION = re.compile(r"(?i)\bnever\b|ห้าม|\bdo not\b|ไม่")
    FALLBACK = re.compile(r"Oliver|BLOCKED|หยุด")

    @classmethod
    def _boundary_violations(cls, text):
        section = re.search(r"(?ms)^## Inputs and decision boundaries\n(.*?)(?=^## |\Z)", text)
        if not section:
            return ["section missing"]
        bad, body = [], section.group(1)
        for line in body.splitlines():
            for clause in re.split(r"→|;|—|\. ", line):  # negation must sit in the SAME clause, before the word
                hit = cls.FORBIDDEN.search(clause)
                if hit and not cls.NEGATION.search(clause[:hit.start()]):
                    bad.append("assumption wording: " + clause.strip())
        derive = body.split("### Stop and return", 1)[0].splitlines()
        for n, line in enumerate(derive):
            s = line.strip()
            if not s or s.startswith("#") or re.fullmatch(r"(- )?When to ask → `shode-house-discipline` § Ask vs derive", s):
                continue
            if s.endswith(":") and any(l.strip().startswith("- ") for l in derive[n + 1:]):
                continue  # lead-in of a derive list: each item below carries its own fallback
            if not cls.FALLBACK.search(s):
                bad.append("derive line without fallback (Oliver|BLOCKED|หยุด): " + s[:80])
        return bad

    def test_decision_boundaries_never_license_an_assumption(self):
        for src in STOP_AND_RETURN:
            with self.subTest(root=src):
                self.assertEqual([], self._boundary_violations((ROOT / src).read_text()))
        # self-check of the guard: Sentinel's mutation d must be caught, a negated mention must not
        rc = (ROOT / "skills/discipline/review-checklist/SKILL.md").read_text()
        dg = (ROOT / "skills/workflow/dev-gate/SKILL.md").read_text()
        m1 = rc.replace("→ ส่งกลับ Oliver — reviewer ไม่เดา scope เอง", "→ assume the default branch diff")
        m2 = dg.replace("Not found → return the question to Oliver; never guess, never ask the user directly.",
                        "Not found → assume the project default.")
        self.assertNotEqual(rc, m1)
        self.assertNotEqual(dg, m2)
        self.assertTrue(self._boundary_violations(m1))
        self.assertTrue(self._boundary_violations(m2))

    def test_completion_contract_precedence_sits_above_continue_until(self):
        text = (ROOT / DELIVERABLE_ROOT).read_text()
        section = re.search(r"(?ms)^## Completion\n(.*?)(?=^## |\Z)", text).group(1)
        self.assertEqual(1, text.count(PRECEDENCE), "precedence sentence must appear verbatim exactly once")
        self.assertIn(PRECEDENCE, section)
        order = [section.index(PRECEDENCE), section.index("Continue inside the authorized scope until"),
                 section.index("Stop when:"), section.index("Affected validation = floor")]
        self.assertEqual(sorted(order), order, "precedence > continue-until > stop-when > validation")
        for case in ("shared libraries", "build tooling", "public contracts", "database schema",
                     "deployment configuration", "security boundaries", "cross-module behaviour"):
            self.assertIn(case, section)
        self.assertNotRegex(section, r"(?i)skip (the )?full suite|affected only|only affected")
        # owner-by-pointer, no copy (C29-1): the two callers cite the section and do not restate the sentence
        for path in ("skills/workflow/dev-gate/SKILL.md", "commands/implement.md"):
            caller = (ROOT / path).read_text()
            self.assertRegex(caller, r"(?m)^## Completion$", path)
            self.assertIn("`shode-house-deliverable` § Completion", caller)
            self.assertNotIn("outranks completion", caller)
        self.assertIn("Complete = no open § Stop and return condition", (ROOT / "skills/workflow/dev-gate/SKILL.md").read_text())
        impl = (ROOT / "commands/implement.md").read_text()
        self.assertIn("only Oliver closes, then reads back", impl)  # "no intervention" is not auto-close (C29-4)
        for kept in ("pre-implement-ui", "Phase 3a", "Phase 3b", "M8 Close-on-Done Guard"):
            self.assertIn(kept, impl)
        self.assertGreaterEqual((ROOT / "commands/review.md").read_text().count("REVIEW DISPATCH CARD"), 1)

    def test_p5_reworded_lines_keep_their_stop_half(self):
        ui = (ROOT / "skills/ui/ui-test/SKILL.md").read_text()
        line = next(l for l in ui.splitlines() if l.startswith("- [ ] URL หรือ dev server"))
        for needle in ("(ไม่มี = BLOCKED ไม่ใช่ PASS)", "only on localhost/ephemeral", "return to Oliver",
                       "ไม่ start/ไม่รัน test ที่เขียนข้อมูลจนกว่าจะได้ authorization"):
            self.assertIn(needle, line)
        rule = "ห้าม proceed เมื่อกำกวมแบบ material (→ § Ask vs derive; ไม่แน่ใจว่า material ไหม = material) → grill option-style"
        self.assertIn(rule, (ROOT / DISCIPLINE_ROOT).read_text())
        ds = (ROOT / "commands/design-system.md").read_text()
        self.assertIn("— do not ask", ds)
        self.assertNotIn("ต้องการ estimation ด้วยมั้ย", ds)

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
