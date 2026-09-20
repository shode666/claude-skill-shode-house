"""Structural routing regression, not behavioral or host-parity proof.

Role inventory comes from the frozen 3.15 baseline; the entrypoint must route to
every retained role and every declared prerequisite must exist in shipped buckets.
Mutation cases prove that missing knowledge cannot silently pass this check.
"""
import importlib.util
import json
from pathlib import Path
import re
import unittest
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inventory", ROOT / "tests/test_team_package.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def entry_errors(entry, contents):
    errors = []
    baseline = inventory.required_paths()
    roles = sorted(p for p in baseline if p.startswith("agents/") and p.endswith(".md"))
    skills = {Path(p).parent.name: p for p in contents if p.endswith("/SKILL.md")}
    for role in roles:
        if not re.search(r"\|\s*" + re.escape(Path(role).name) + r"\s*\|", entry):
            errors.append("unrouted: " + role)
        body = contents.get(role, "")
        if not body.strip():
            errors.append("missing role: " + role)
            continue
        match = re.search(r"^skills:\s*(\[.*\])$", body, re.M)
        if not match:
            errors.append("missing prerequisites: " + role)
            continue
        for name in json.loads(match.group(1)):
            path = skills.get(name)
            if not path or not contents[path].strip():
                errors.append("missing prerequisite: " + role + ": " + name)
    # Validate the new entry's literal relative resource pointers.
    for relative in re.findall(r"`(\.\./[^`]+\.md)`", entry):
        path = (ROOT / "skills/workflow/ask" / relative).resolve()
        try:
            key = str(path.relative_to(ROOT))
        except ValueError:
            errors.append("escaped plugin root: " + relative)
            continue
        if key not in contents:
            errors.append("broken entry reference: " + relative)
    return errors


class TeamEntryTest(unittest.TestCase):
    def test_routing_dedup_retains_owner_and_phase_tables(self):
        path = "skills/discipline/shode-house-routing/SKILL.md"
        old = subprocess.check_output(["git", "show", "v3.16.2:" + path], cwd=ROOT, text=True)
        current = (ROOT / path).read_text()
        # These tables assign responsibility; shortening handoff examples must
        # not remove an owner, phase, or domain route.
        for start, end in (
            ("### Domain Selection", "## ⚖️ Conflict Resolution"),
            ("### Single-owner capability matrix", "## 🤝 Handoff Broadcast Protocol"),
            ("## 📋 RACI per Phase", "### Adversarial relation"),
        ):
            section = old[old.index(start):old.index(end)]
            rows = [line for line in section.splitlines() if line.startswith("|") or " → " in line]
            self.assertTrue(rows)
            for row in rows:
                self.assertIn(row, current)
        link = "../shode-house-discipline/handoff.md"
        self.assertIn("(" + link + ")", current)
        self.assertTrue(((ROOT / path).parent / link).resolve().is_file())

    def test_language_matrix_retains_released_rows(self):
        old = subprocess.check_output(["git", "show", "v3.16.2:skills/workflow/dev-gate/SKILL.md"], cwd=ROOT, text=True)
        section = old[old.index("### Per-language tool matrix"):old.index("### Gate 1: Format")]
        reference = (ROOT / "skills/workflow/dev-gate/tool-matrix.md").read_text()
        rows = [line for line in section.splitlines() if line.startswith("|")]
        self.assertEqual(10, len(rows))
        for row in rows:
            self.assertIn(row, reference)
        core = (ROOT / "skills/workflow/dev-gate/SKILL.md").read_text()
        self.assertIn("[tool-matrix.md](tool-matrix.md)", core)
        self.assertNotIn(rows[0], core)

    def test_full_diagnosis_reference_preserves_released_instructions(self):
        old = subprocess.check_output(["git", "show", "v3.16.2:skills/workflow/diagnose/SKILL.md"], cwd=ROOT, text=True)
        start = old.index("### 2. Reproduce + Minimise")
        end = old.index("### 4. Fix + Regression test")
        reference = (ROOT / "skills/workflow/diagnose/full-investigation.md").read_text()
        self.assertIn(old[start:end].strip(), reference)
        core = (ROOT / "skills/workflow/diagnose/SKILL.md").read_text()
        self.assertIn("[full-investigation.md](full-investigation.md)", core)
        self.assertNotIn(old[start:end].strip(), core)

    # --- v3.17 P4 thin-router: text moved out of a root must still exist verbatim somewhere loadable ---
    @staticmethod
    def _baseline_body_lines(path, tag="baseline-3.17"):
        old = subprocess.check_output(["git", "show", tag + ":" + path], cwd=ROOT, text=True)
        return [line for line in old.split("---", 2)[2].splitlines() if line.strip()]

    # T-tracker-neutral (8ss.52): the only wording change allowed on a pinned baseline line.
    TRACKER_NEUTRAL = (("log เป็น bd discovered", "log เป็น discovered task"), ("ไม่มี bd id", "ไม่มี task id"),
                       ("bd track", "ticket"), ("bd issue", "ticket"))

    @classmethod
    def _neutral(cls, line):
        for old, new in cls.TRACKER_NEUTRAL:
            line = line.replace(old, new)
        return line.strip()

    @classmethod
    def _skill_lines(cls, skill_dir, names=None):
        """Stripped-line SET (not substring): a lost line that is a substring of another still fails."""
        return {line.strip() for line in cls._skill_text(skill_dir, names).splitlines()}

    @staticmethod
    def _skill_text(skill_dir, names=None):
        files = sorted((ROOT / skill_dir).glob("*.md")) if names is None else [ROOT / skill_dir / n for n in names]
        return "\n".join(p.read_text() for p in files)

    def test_dev_gate_router_keeps_every_baseline_line(self):
        d = "skills/workflow/dev-gate"
        lines = self._skill_lines(d)
        dropped = {  # history notes (no rule) + cross-refs re-pointed at the new files + headings of relocated pointer blocks
            "# Dev Gate (TDD + Quality Gates) — v3.0 merged",
            "> Merged from v2 skills: `tdd` + `code-quality` — ลด context, รวม dev-time discipline",
            "> ทุกครั้งที่ตัด (ขั้น 1) หรือใช้ทางลัด → mark ด้วย `shortcut(bd:N):` comment (ดู Gate 3) เพื่อให้ debt harvest เก็บได้",
            "รูปร่างของ interface เองยังไม่นิ่ง (ลึกแค่ไหน seam อยู่ตรงไหน) → ดู § Gate 0 § Deep module",
            "### Per-language tool matrix",
            "## Pre-commit integration (when authorized)",
            "## Hand-off",  # now "## Hand-off + completion boundary"
            # P6 integration: checklist re-aligned with the 11-gate table (the source of truth); the prefix must survive
            '- [ ] **Quality gate ผ่านครบ 11** (Gate 0-10, ดู Part 2): YAGNI · format · lint · type · complexity ≤10 · naming · test · coverage ≥ threshold · doc/comment "why" · security · observability',
            # P5 (8ss.28) byte payment: illustrative hand-off chain, owned by the workflow root (no rule)
            "Dave  ▸ Chris   : impl + smoke (dev-gate passed)",
            "Chris ▸ Quinn   : 7-dim + unit quality vs adopted targets",
        }
        p5 = {  # P5 (8ss.28): whole baseline line -> the whole line that replaces it (must exist verbatim)
            "## Required inputs — refuse without": "## Inputs and decision boundaries",
            'ก่อน hand-off Phase 2 → 3, confirm ทุก checklist. ถ้าขาด **list สิ่งที่ขาด แล้วหยุด** — ห้าม claim "done":':
                "ขาดข้อใด → **list สิ่งที่ขาด แล้วหยุด** ส่งกลับ Oliver:",
            "| Test pass แต่ยังไม่มี CI gate | → `automate-test` | Pyramid ratio + CI threshold + contract test (dev-gate = per-task; automate-test = project-wide) |":
                "| Test pass แต่ยังไม่มี CI gate | → `automate-test` | Pyramid ratio + CI threshold + contract test |",
            "| Code touches frontend | → `ui-test` | E2E + visual + a11y automation (dev-gate ไม่ครอบ visual) |":
                "| Code touches frontend | → `ui-test` | E2E + visual + a11y automation |",
            "| Hand-off Phase 2 → 3b review | → `review-checklist` skill | Chris 7-dim + Quinn integration matrix (used by /implement Phase 3b + /review)":
                "| Hand-off Phase 2 → 3b review | → `review-checklist` skill | Chris 7-dim + Quinn integration matrix",
        }
        missing = [l for l in self._baseline_body_lines(d + "/SKILL.md")
                   if self._neutral(l) not in lines and l not in dropped and p5.get(l) not in lines]
        self.assertEqual([], missing)
        self.assertIn('### Hand-off evidence (Phase 2 → 3) — ขาดข้อใด = ยังไม่ done, ห้าม claim "done"', lines)
        self.assertIn("### Stop and return", lines)
        core = (ROOT / d / "SKILL.md").read_text()
        for ref in ("tdd.md", "quality-gates.md"):
            self.assertIn("[%s](%s)" % (ref, ref), core)
        self.assertIn("`shortcut(bd:N):` comment", core)
        self.assertIn("**Quality gate ผ่านครบ 11** (Gate 0-10, ดู Part 2): architecture · format", core)

    def test_ui_test_router_keeps_every_baseline_line(self):
        d = "skills/ui/ui-test"
        lines = self._skill_lines(d, ["SKILL.md", "automation-patterns.md"])
        # P5 CH-1 (8ss.28): the one reworded baseline line; its BLOCKED-not-PASS half must survive on the SAME line
        url = "- [ ] URL หรือ dev server ที่เปิดได้จริง (ไม่มี = BLOCKED ไม่ใช่ PASS)"
        new_url = [l for l in lines if l.startswith("- [ ] URL หรือ dev server ที่เปิดได้จริง — ")]
        self.assertEqual(1, len(new_url))
        self.assertIn("(ไม่มี = BLOCKED ไม่ใช่ PASS)", new_url[0])
        self.assertIn("จนกว่าจะได้ authorization", new_url[0])
        self.assertEqual([], [l for l in self._baseline_body_lines(d + "/SKILL.md")
                              if self._neutral(l) not in lines and l != url])
        self.assertIn("automation-patterns.md", (ROOT / d / "SKILL.md").read_text())

    def test_drain_router_keeps_invariants_in_root_and_moved_blocks_in_execution(self):
        d = "skills/ops/drain"
        core, execution = (ROOT / d / "SKILL.md").read_text(), (ROOT / d / "execution.md").read_text()
        baseline = self._baseline_body_lines(d + "/SKILL.md")
        for anchor in ("**Worktree isolation** — 1 worktree ใหม่ต่อ agent",
                       "independent review + integrated acceptance + closure authority"):
            self.assertIn(anchor, core)
            self.assertNotIn(anchor, execution)
        self.assertIn("execution.md", core)
        moved = (  # sample of blocks moved verbatim (tracker-neutral rewordings are covered by rule-conservation)
            "**COMMON brief** (ฝังในทุก agent prompt — sub-agent เกิดใน context ว่าง):",
            "4. Stop at the first conflict or failed gate; preserve prior integrations and worker branches. Do not publish or continue the remaining picks.",
            "3. **ห้ามคิด behaviour ใหม่ระหว่าง resolve** — resolve ไม่ใช่ที่สำหรับออกแบบ",
            "Do not reapply an integrated commit or repeat push/closure after a lost response.",
            next(l for l in baseline if l.startswith("> Abort only the integration operation started by this run")),
        )
        for line in moved:
            self.assertIn(line, baseline)
            self.assertIn(line, execution)
            self.assertNotIn(line, core)

    def test_routing_roster_and_team_tables_live_in_ownership_reference(self):
        d = "skills/discipline/shode-house-routing"
        old = subprocess.check_output(["git", "show", "baseline-3.17:" + d + "/SKILL.md"], cwd=ROOT, text=True)
        ownership = self._skill_lines(d, ["ownership.md"])
        for start, end in (("## 👥 ทีม (19 agents", "## 💯 Universal Quality"),
                           ("## 👥 Team Structure", "### Single-owner capability matrix")):
            rows = [l for l in old[old.index(start):old.index(end)].splitlines() if l.startswith(("|", "- **"))]
            self.assertGreaterEqual(len(rows), 2)
            for row in rows:
                self.assertIn(row.strip(), ownership)
        core = (ROOT / d / "SKILL.md").read_text()
        for ref in ("ownership.md", "orchestration.md"):
            self.assertIn(ref, core)

    def test_routing_router_keeps_every_post_merge_line(self):
        # Chris C1: rule-conservation does not protect table rows (capability matrix, RACI, conflict table).
        d = "skills/discipline/shode-house-routing"
        lines = self._skill_lines(d, ["SKILL.md", "ownership.md", "orchestration.md"])
        repointed = ("- **XL** = cross-service / cross-domain → ",  # "`bd` examples below" -> orchestration.md
                     "> Interim owner = ไม่มี dedicated agent ตอนนี้ (YAGNI)",  # "ด้านบน" -> ownership.md § Add agent
                     "**Pattern**: ")  # P7 FR-P7-5: printing the trust label is no longer mandatory; citing the source still is
        missing = [l for l in self._baseline_body_lines(d + "/SKILL.md", "baseline-3.17-m")
                   if l.strip() not in lines and not l.startswith(repointed)]
        self.assertEqual([], missing)
        core = (ROOT / d / "SKILL.md").read_text()
        for prefix in repointed:
            self.assertIn(prefix, core)
        # P7 FR-P7-5 / P7-C5: the label is internal, the behaviour is not
        self.assertIn("claim ต้อง cite source เสมอ", core)
        self.assertIn("ห้าม upgrade trust ของ chain", core)

    def test_diagnose_loop_sharpening_moved_verbatim_and_safety_stays_in_root(self):
        d = "skills/workflow/diagnose"
        old = subprocess.check_output(["git", "show", "baseline-3.17:" + d + "/SKILL.md"], cwd=ROOT, text=True)
        start = old.index("**ลับ loop ให้คม**")
        block = old[start:old.index("\n\n", start)]
        self.assertGreaterEqual(block.count("\n"), 3)
        core = (ROOT / d / "SKILL.md").read_text()
        self.assertIn(block, (ROOT / d / "loop-ladder.md").read_text())
        self.assertNotIn("**ลับ loop ให้คม**", core)
        self.assertIn("`loop-ladder.md`", core)
        self.assertRegex(core, r"(?m)^## .*Redact ก่อน paste")
        self.assertIn("→ `incident` ก่อน", core)

    def test_decompose_root_keeps_its_gates(self):
        path = "skills/workflow/decompose/SKILL.md"
        old = subprocess.check_output(["git", "show", "baseline-3.17:" + path], cwd=ROOT, text=True)
        core = (ROOT / path).read_text()
        for text in ("**Spec หรือ BRD ที่ sign-off แล้ว**",
                     "**Confirmed record location and write authority**",
                     "Planning does not authorize creating remote tickets",
                     "**leaf 1 ใบ = outcome ที่ verify ได้จริง ผ่านเฉพาะ layer ที่เกี่ยวข้อง**",
                     "ขาดข้อใด → list สิ่งที่ขาด แล้วหยุด ห้ามเดา"):
            self.assertIn(text, old)
            self.assertIn(text, core)
        self.assertLess(len(core.encode()), len(old.encode()))

    def test_incident_has_exactly_one_postmortem_template(self):
        d = ROOT / "skills/ops/incident"
        headers = [l for p in sorted(d.glob("*.md")) for l in p.read_text().splitlines() if l.startswith("# Postmortem:")]
        self.assertEqual(1, len(headers))

    @classmethod
    def setUpClass(cls):
        cls.contents = {
            str(p.relative_to(ROOT)): p.read_text()
            for base in [ROOT / "agents", *[ROOT / "skills" / b for b in inventory.BUCKETS]]
            for p in base.rglob("*.md")
        }
        cls.entry = cls.contents["skills/workflow/ask/SKILL.md"]

    def test_all_baseline_roles_and_prerequisites_reachable(self):
        self.assertEqual([], entry_errors(self.entry, self.contents))

    def test_missing_domain_route_is_detected(self):
        mutated = self.entry.replace("| fintech-expert.md |", "| absent.md |")
        self.assertIn("unrouted: agents/fintech-expert.md", entry_errors(mutated, self.contents))

    def test_missing_domain_knowledge_is_detected(self):
        mutated = dict(self.contents)
        mutated["agents/booking-expert.md"] = ""
        self.assertIn("missing role: agents/booking-expert.md", entry_errors(self.entry, mutated))

    def test_missing_prerequisite_is_detected(self):
        mutated = dict(self.contents)
        mutated.pop("skills/discipline/domain-core/SKILL.md")
        self.assertTrue(any("missing prerequisite:" in e for e in entry_errors(self.entry, mutated)))

    HARNESS_INVARIANTS = (
        "Iteration cap: three review",
        "no user channel exists",
        "mark the task BLOCKED",
        "Do not decide business policy, widen scope or add",
        "Amending an acceptance criterion is the requirements owner's call",
        "never end the\nturn with workers still running",
        "Verification depth follows risk, not habit",
        "nothing\nremoves a triggered role",
        "A blocking finding (Critical/High) must name the recorded acceptance criterion",
        "append a three-line retro to the checkpoint",
    )

    def harness_missing(self, text):
        return [f for f in self.HARNESS_INVARIANTS if f not in text]

    def test_harness_unattended_invariants_present(self):
        harness = self.contents["skills/discipline/shode-house-workflow/harness.md"]
        self.assertEqual([], self.harness_missing(harness))

    def test_harness_invariant_removal_is_detected(self):
        harness = self.contents["skills/discipline/shode-house-workflow/harness.md"]
        start = harness.index("Iteration cap:")
        mutated = harness[:start] + harness[harness.index("\n\n", start) + 2:]
        self.assertTrue(self.harness_missing(mutated))

    def test_broken_entry_reference_is_detected(self):
        mutated = self.entry.replace("engineering-loop.md", "does-not-exist.md")
        self.assertTrue(any("broken entry reference:" in e for e in entry_errors(mutated, self.contents)))


if __name__ == "__main__":
    unittest.main()
