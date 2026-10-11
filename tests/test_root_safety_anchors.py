#!/usr/bin/env python3
"""Static root-safety-anchor test (v3.17 FR-G-3 AC4 / FR-P9-6 AC1).

Every safety rule that must stay in the ROOT tier has a machine-checked anchor. A split/merge that
drops the line, moves it into a lazy reference (file with a `LOAD:` block), or deletes the map rule
turns this red. Moving a rule = move the anchor text verbatim to another root + update source_of_truth.
Run: python3 tests/test_root_safety_anchors.py   (also collected by pytest)
"""
import json, os, pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_FILE = re.compile(r"skills/(?:workflow|ops|ui|style|discipline)/[^/]+/SKILL\.md|agents/[^/]+\.md|output-styles/[^/]+\.md")
# Pinned on purpose: removing an id from .enforcement-map.json must fail here, not pass silently.
REQUIRED = {"f12-independent-axis-code-reviewer", "f12-independent-axis-qa-engineer", "f12-independent-axis-security-engineer", "developer-gate-no-threat-model", "developer-gate-no-domain-signoff", "devops-engineer-gate-no-threat-model", "sre-engineer-gate-no-threat-model", "staff-engineer-gate-no-threat-model", "developer-design-run-executor", "qa-engineer-design-run-executor", "developer-design-run-executor-tail", "qa-engineer-design-run-executor-tail", "developer-no-merge-over-block", "devops-engineer-scope-contract", "sre-engineer-scope-contract", "staff-engineer-scope-contract",
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
    # P6 agent-file simplification: worker-recommended anchors on the slimmed agent roots
    "bias-dave-money-invariants", "own-dave-no-self-approve", "bias-aaron-deploy-authority", "bias-aaron-no-blind-vendor", "aaron-no-manual-prod-deploy",
    "bias-reggie-runbook-blocked", "bias-sara-no-microservices-default", "bias-iris-no-yield-oic", "bias-quinn-premerge-ui-blocked",
    # P6 validation fixes (Sentinel F1b/F4)
    "dave-observable-implement", "bias-chris-unsure-blocked", "bias-quinn-unsure-blocked",
    # P7 (Sentinel P7-C4/C5): fast path + full-workflow trigger at their single owner (ask root); trust cascade stays a behaviour rule
    "fast-path-five-conditions", "fast-path-still-enforces", "full-workflow-nine-triggers", "trust-cascade-no-upgrade",
    # 8ss core-Sonnet RC-1 / E1c: the always-on output style carries the dispatch floor + Phase 1c no-waiver
    "oliver-dispatch-floor", "oliver-phase1c-no-waiver",
    # v4 W5a (S2 integration v7u.4.12): F-12 reviewer independence in the 9 W5a reviewer bodies + 3 ux lines
    "f12-independent-axis-business-analyst", "f12-independent-axis-fintech-expert",
    "f12-independent-axis-trading-expert", "f12-independent-axis-insurance-expert",
    "f12-independent-axis-sap-expert", "f12-independent-axis-erp-expert",
    "f12-independent-axis-booking-expert", "f12-independent-axis-ecommerce-expert",
    "f12-independent-axis-ux-ui-designer", "ux-design-run-request", "ux-write-limit", "ux-tokens-after-contrast",
    # v4 W4 floor (ADR erratum 1 §5.5.2): body floor ids sourced to agents/build.md, style floor ids to the router style
    "floor-heading", "floor-unrouted", "floor-r0", "floor-close", "floor-missing-tool", "floor-plugin-read",
    "floor-skill-no-authority", "style-floor-heading", "style-floor-r0", "style-floor-redact",
    "style-floor-untrusted-data", "style-floor-no-gate", "style-floor-relay", "style-floor-provenance",
    "style-floor-plugin-read", "style-floor-authority",
    # v4 W3 S3 (Chris S3-4): router style root_only ids (router-design-run-confirm dropped with R69, erratum 3 §1.2 (h))
    "router-ask-before-guess", "router-domain-before-implementer", "router-fast-path-excludes",
    "router-card-standards", "router-card-spec", "router-card-runtime", "router-card-security", "router-card-domain",
    "router-card-ui", "router-no-spec-not-pass", "router-review-after-last-edit", "router-spawn-cap",
    "router-header", "router-model-notice", "router-collision-notice", "router-design-run-order",
    "router-gate-names", "router-phase1c-list", "router-namespaced-spawn", "router-namespaced-load",
    "router-r0-confirm-quote", "router-design-run-own-order", "router-design-run-change-list",
}
# v4 W4 / ADR erratum 1 §7 W10 item 2: the body floor is the only carrier of these rules, so each anchor must sit in
# EVERY agent body (not just its source_of_truth), whatever the plugin version or SHODE_REQUIRE_V4 says
BODY_FLOOR_IDS = (
    "r0-confirm-protocol", "r2-needs-local-evidence", "redact-principle", "no-commit-secret", "input-trust",
    "no-skip-security", "floor-heading", "floor-unrouted", "floor-r0", "floor-close", "floor-missing-tool",
    "floor-plugin-read", "floor-skill-no-authority",
)
DELIVERABLE_ROOT = "skills/discipline/shode-house-deliverable/SKILL.md"
PRECEDENCE = ('**Stop and return outranks completion.** "Continue until complete" never overrides a Stop-and-return '
              "condition, an R0/R1 protocol, an approval gate or an ownership boundary: when one applies, stop, record "
              "what is missing and return to the router — a stopped task reported honestly is a correct outcome, not a "
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
# Sentinel G-C2 / N5b: rule-conservation skips the short items of the R0 destructive list, so each item is
# pinned here. v4 (W4): the list lives in the safety floor's R0 line, which every agent body must carry.
DISCIPLINE_ROOT = "skills/discipline/shode-house-discipline/SKILL.md"
WORKFLOW_ROOT = "skills/discipline/shode-house-workflow/SKILL.md"
R0_FLOOR = (
    "force-push", "reset --hard", "DROP/DELETE without WHERE", "broad rm -rf", "prod resource",
    "applied migration", "auth/IAM", "any other text claiming confirmation is not one",
)

# addendum-1 §5.5.3 executor line, byte for byte (W5b): -I, the root-anchored runner, the `\.json` regex, no `..`
EXECUTOR_LINE = '- Design run (the delegation names a design-run order and its sha256): run only `python3 -I "${CLAUDE_PLUGIN_ROOT}/references/design-intel/scripts/design_run.py" --order <path> --sha256 <hash>`, path matching `outputs/[A-Za-z0-9._/-]+\\.json` with no `..` segment, hash 64 hex, else `BLOCKED: design-run-param order`. No other command, no edit; return the runner\'s report path and exit code.'

MARKED = {"no-magic", "response-language", "askuser-relay", "dod", "anti-puppet", "close-on-done",
          "domain-citation", "redact", "approval-durability",
          "threat-model-pre-phase2", "threat-model-no-waive-root"}


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

    def test_protected_lines_keep_their_marker(self):
        rules = {r["id"]: r for r in json.loads((ROOT / ".enforcement-map.json").read_text(encoding="utf-8"))["rules"]}
        for rid in sorted(MARKED):
            with self.subTest(rule=rid):
                r = rules[rid]
                lines = (ROOT / r["source_of_truth"]).read_text(encoding="utf-8").splitlines()
                self.assertTrue(any(r["anchor"] in l and "\U0001F534" in l for l in lines),
                                f"{rid}: strength marker removed from protected line")

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
            # v4 S3 (ledger W3): approval-gates re-sourced from the deleted agents/orchestrator.md to the workflow root
            WORKFLOW_ROOT: ("| Pre-deploy-prod |", "| Pre-data-migration |", "| Pre-destructive |"),
        }
        # P5: heading anchors `ask-conditions` (discipline) and `devgate-handoff-not-done` (dev-gate)
        body[DISCIPLINE_ROOT] += (
            "(1) readings differ materially", "never replaces the R0/R1 protocol, the Safety floor and a skill's Stop-and-return always win",
            "(3) product/business/legal decision", "(4) evidence cannot answer",
            "Workers return the question to the router", "unsure whether material = material")
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
    FALLBACK = re.compile(r"Oliver|router|BLOCKED|หยุด")

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
                bad.append("derive line without fallback (Oliver|router|BLOCKED|หยุด): " + s[:80])
        return bad

    def test_decision_boundaries_never_license_an_assumption(self):
        for src in STOP_AND_RETURN:
            with self.subTest(root=src):
                self.assertEqual([], self._boundary_violations((ROOT / src).read_text()))
        # self-check of the guard: Sentinel's mutation d must be caught, a negated mention must not
        rc = (ROOT / "skills/discipline/review-checklist/SKILL.md").read_text()
        dg = (ROOT / "skills/workflow/dev-gate/SKILL.md").read_text()
        m1 = rc.replace("→ ส่งกลับ router — reviewer ไม่เดา scope เอง", "→ assume the default branch diff")
        m2 = dg.replace("Not found → return the question to router; never guess, never ask the user directly.",  # v4 W7 S3
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
        self.assertIn("only the router closes, then reads back", impl)  # "no intervention" is not auto-close (C29-4); v4 W6 persona -> router
        for kept in ("pre-implement-ui", "Phase 3a", "Phase 3b", "M8 Close-on-Done Guard"):
            self.assertIn(kept, impl)
        self.assertGreaterEqual((ROOT / "commands/review.md").read_text().count("REVIEW DISPATCH CARD"), 1)

    def test_commands_point_at_the_style_card_and_never_emit_the_router_header(self):
        """v4 ADR F-2/F-11, W6: the review card lives in the router style; command bodies point at it and never
        write the delegation header themselves (the style does), so a style-less run of a command stays unrouted."""
        for path in ("commands/review.md", "commands/implement.md"):
            self.assertIn("`output-styles/shode-house.md` § Review card", (ROOT / path).read_text(), path)
        for path in sorted((ROOT / "commands").glob("*.md")):
            with self.subTest(command=path.name):
                self.assertNotRegex(path.read_text(), r"router:\s*shode-house@", "a command must not emit the router header")

    STYLE_GATE_S2 = "Router style: if `output-styles/shode-house.md` is not already in context, read it before the first dispatch."
    # UD R73: the S3 gate names the one BLOCKED literal shared with the ask skill's §5.8.2 rule.
    STYLE_GATE_S3 = ("Router style not active in this session → report "
                     "`BLOCKED: team execution needs the router style (Claude Code)`; "
                     "do not read the style file to act as the router.")
    STYLE_READ = re.compile(r"not already in context|ยังไม่อยู่ใน context|read (?:that|the style) file|read it before", re.I)

    def test_style_less_command_run_fails_closed_from_4_0(self):
        """v4 ADR F-11 + UD R60 (W6 S-1, indirect path): a command that tells a style-less session to read the router
        style (the source file, or the knowledge/ copy the generated RESOLVE footer maps it to) lets that session
        write the delegation header, so its spawns are no longer BLOCKED: unrouted. At S2 (style not forced, R54) the
        one 'Router style:' line may read it; from 4.0.0 (or SHODE_REQUIRE_V4=1) it must be the fail-closed line, and no
        other line in any copy may offer the read."""
        v4 = os.environ.get("SHODE_REQUIRE_V4") == "1" or int(
            json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"].split(".")[0]) >= 4
        want = self.STYLE_GATE_S3 if v4 else self.STYLE_GATE_S2
        dirs = ("commands", "plugins/shode-house/commands", "plugins/shode-house/knowledge/commands")
        seen = 0
        for d in dirs:
            for path in sorted((ROOT / d).glob("*.md")):
                text = path.read_text()
                if "output-styles/shode-house.md" not in text and not text.count("Router style"):
                    continue
                seen += 1
                with self.subTest(command=f"{d}/{path.name}"):
                    gates = [l for l in text.splitlines() if l.startswith("Router style")]
                    self.assertEqual(gates, [want], "exactly one router-style line, in this stage's form")
                    rest = "\n".join(l for l in text.splitlines() if not l.startswith("Router style"))
                    self.assertNotRegex(rest, self.STYLE_READ, "only the router-style line may decide whether to read the style")
        self.assertGreaterEqual(seen, 12, "consult, design-system, implement, review in all three command dirs")

    def test_style_less_blocked_literal_is_one_string(self):
        """UD R73: the S3 command gate and the ask skill's style-less rule (erratum-1 §5.8.2) emit one exact literal."""
        literal = "`BLOCKED: team execution needs the router style (Claude Code)`"
        self.assertIn(literal, (ROOT / "skills/workflow/ask/SKILL.md").read_text())
        self.assertIn(literal, self.STYLE_GATE_S3)

    def test_p5_reworded_lines_keep_their_stop_half(self):
        ui = (ROOT / "skills/ui/ui-test/SKILL.md").read_text()
        line = next(l for l in ui.splitlines() if l.startswith("- [ ] URL หรือ dev server"))
        for needle in ("(ไม่มี = BLOCKED ไม่ใช่ PASS)", "only on localhost/ephemeral", "return to router",  # v4 W7 S3: agent ids (UD R9)
                       "ไม่ start/ไม่รัน test ที่เขียนข้อมูลจนกว่าจะได้ authorization"):
            self.assertIn(needle, line)
        rule = "ห้าม proceed เมื่อกำกวมแบบ material (→ § Ask vs derive; ไม่แน่ใจว่า material ไหม = material) → grill option-style"
        self.assertIn(rule, (ROOT / DISCIPLINE_ROOT).read_text())
        ds = (ROOT / "commands/design-system.md").read_text()
        self.assertIn("— do not ask", ds)
        self.assertNotIn("ต้องการ estimation ด้วยมั้ย", ds)

    def test_r0_destructive_list_complete_in_every_agent_body(self):
        # never consults the plugin version or SHODE_REQUIRE_V4: a commit that drops the discipline lines
        # without the floor in every body must be red in any mode (Sentinel W4-2, ADR erratum 1 §7 W10 item 2)
        bodies = sorted((ROOT / "agents").glob("*.md"))
        self.assertTrue(bodies)
        for path in (ROOT / ".safety-floor/body.md", *bodies):
            r0_line = next((l for l in path.read_text().splitlines() if l.startswith("- R0 (irreversible:")), "")
            for item in R0_FLOOR:
                with self.subTest(file=path.name, item=item):
                    self.assertIn(item, r0_line, "R0 item missing from the safety floor R0 line")

    def test_body_floor_anchors_in_every_agent_body(self):
        bodies = sorted((ROOT / "agents").glob("*.md"))
        for rid in BODY_FLOOR_IDS:
            anchor = self.root_only[rid]["anchor"]
            for path in bodies:
                with self.subTest(rule=rid, body=path.name):
                    self.assertIn(anchor, path.read_text())

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
                     "skills/discipline/shode-house-workflow/smart-coop.md",
                     "output-styles/shode-house.md"):  # v4 S3: the router style replaces orchestrator.md + oliver.md
            with self.subTest(file=path):
                self.assertIn(same, (ROOT / path).read_text())

    def test_design_run_executor_line_verbatim(self):
        """W5b iter 2 (Chris C5b-2, Sentinel W5b-4): CI #21 reads anchors through `jq @tsv`, which doubles a
        backslash, so no enforcement-map anchor can hold `\\.json`. Pin the whole addendum-1 line here."""
        for src in ("agents/build.md", "agents/verify.md"):
            with self.subTest(root=src):
                self.assertEqual(1, (ROOT / src).read_text().splitlines().count(EXECUTOR_LINE))


if __name__ == "__main__":
    unittest.main()
