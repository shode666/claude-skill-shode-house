---
name: review-checklist
description: Coordinate independent review of an implemented change by code, runtime, spec, security and domain with severity and merge gates, not self-approval.
---

# Review Checklist — core

> 🔴 subagent เห็นเฉพาะแกนตัวเอง — ห้าม agent preload checklist ของ agent อื่น

## When NOT to use

See `intake.md` for content/generated/spike review. Agent instructions and permissions
are not mere docs; urgency alone never waives required review or security gates.

## Inputs and decision boundaries

spec source · configured checks · evidence home · severity scale → หาเองจาก repo/task record (ลำดับ + default → `intake.md`); not found → return to Oliver; when to ask → `shode-house-discipline` § Ask vs derive

### Stop and return

- diff scope ยังไม่ pin (fixed point หรือ supplied content ไม่ครบ) → ส่งกลับ Oliver — reviewer ไม่เดา scope เอง
- spec source ไม่มี = รายงาน "no spec available" ห้าม pass เงียบ

## แกนของการ review — ใครทำอะไร

- **Standards** — Chris → `agents/code-reviewer.md` § 7 มิติ; Correctness = internal behavior/invariant/error-path เท่านั้น
- **Standards / runtime** — Quinn → `agents/qa-engineer.md` § ขอบเขต (integration/E2E/contract/load/a11y/pen)
- **Spec** — Bella → `spec-axis.md`
- **Security depth** (cond.) — Sentinel → `security-sentinel.md` + `secure` skill
- **Domain** (cond.) — domain expert → `domain-validation.md`

## 🔴 Aggregation rule

- **Standards กับ Spec เป็นคนละ sub-agent เสมอ** — context ห้ามปน
- แยกหัวข้อ `## Standards` / `## Spec` · **ห้าม merge หรือ rerank ข้ามแกน** · ปิดท้าย 1 บรรทัด: จำนวน finding + ตัวแย่สุด **ในแต่ละแกน**
- **requirement conformity เป็นของ Spec axis เท่านั้น** — Chris ห้ามตรวจซ้ำ

## Severity Grading (schema เดียวทุกแกน)

- 🔴 **Critical** — security exploit / data loss / prod-breaking / regulation violation → **block merge**
- 🟠 **High** — wrong behavior / perf regression >10% / a11y critical → fix ก่อน merge
- 🟡 **Medium** — code smell/test gap → track P2-P3, fix รอบ bd ถัดไป
- 🔵 **Low** — nitpick/style → defer P4
- 💡 **Suggestion** — refactor opportunity → inform, no block

## 🔴 Gate ที่ทุกแกนต้องผ่าน

1. **Adversary stance** — verify independently: demonstrated defect = FAIL; missing required evidence = BLOCKED/PARTIAL, never PASS. Counter "should be fine" with actual evidence, not assumed failure.
2. **Anti-Puppet** — ห้าม claim PASS โดยไม่ paste tool output (axe / coverage / Semgrep / Pact) · ห้าม "looks good" ต้อง cite `file:line` · ห้าม skip แกนที่ harness tier/trigger กำหนดเพียงเพราะงานเล็ก
3. **Visual verify** — UI changes require actual screenshot/interaction, console and network evidence per `ui-test`. Backend-only API/CLI/library work uses response, behavior and relevant integration evidence, not screenshots. Missing applicable evidence = **BLOCKED**; browser MCP is not required.
4. **Finding ทุกข้อ** ระบุ `file:line` + severity + วิธีแก้ และ track ใน tracker ไม่ใช่ค้างในแชท
5. **Scope is pinned; severity follows impact.** Blockers need violated AC/invariant/security criteria or a demonstrated defect, including unchanged code newly exposed by this change. Unrelated findings retain severity but require separate repair authority. Hypothetical unsupported inputs alone do not justify new iterations.
6. **money/PII/auth** → Domain Expert + Sentinel ลงชื่อก่อน merge
7. **Fixed point** — review scope = `git diff <base>...HEAD` (three-dot = merge-base), pin ก่อน fan-out
8. **Reviewer independence** — no agent approves its own primary deliverable

## 🛑 Stop condition (🔴 objective-based)

Return when scoped axes are complete, the report is in the confirmed evidence home
per `report-format.md`, and no blocking question remains.
ห้ามวน re-read/re-run "เพื่อความมั่นใจ" — depth = checklist ครบ ไม่ใช่จำนวน turn; ยังไม่ครบ → ทำเฉพาะแกนที่ขาด

## 📎 Reference

- รับงานครั้งแรก → `intake.md`
- จะเขียน report / route loop → `report-format.md`
- ตรวจแกน Spec → `spec-axis.md`
- diff แตะ auth/money/PII/crypto → `security-sentinel.md`
- diff แตะ business rule / regulation → `domain-validation.md`
