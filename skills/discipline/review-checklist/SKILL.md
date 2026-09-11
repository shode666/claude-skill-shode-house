---
name: review-checklist
description: |
  [WHAT] Review orchestration core — ใครตรวจแกนไหน + severity + aggregation + gate ที่ห้ามข้าม; รายละเอียดแต่ละแกนอยู่ที่เจ้าของแกน.
  [WHEN] Phase 3b ใน /implement และ /review.
  [TRIGGER] /shode-house:review-checklist, "code review", "review", "7-dim", "Chris review", "Quinn integration test".
---

# Review Checklist — core

> 🔴 subagent เห็นเฉพาะแกนตัวเอง — ห้าม agent preload checklist ของ agent อื่น

## When NOT to use

Spike/throwaway · generated code · pure doc change · P0 hot-fix (รันเฉพาะ 🔴 Critical แล้ว track ที่เหลือ) → รายละเอียด `intake.md`

## Required inputs — refuse without

diff scope ที่ pin แล้ว (หรือ full-file/snippet scope) · spec source (ไม่มี = รายงาน "no spec available" ห้าม pass เงียบ) · applicable static analysis tool · authorized report destination, not mandatory tracker · severity scale → checklist เต็ม `intake.md`

## แกนของการ review — ใครทำอะไร

- **Standards** (code ถูกหลักไหม) — Chris → `agents/code-reviewer.md` § 7 มิติ; Correctness = internal behavior/invariant/error-path เท่านั้น
- **Standards / runtime** (พฤติกรรมตอนรัน) — Quinn → `agents/qa-engineer.md` § ขอบเขต (integration/E2E/contract/load/a11y/pen)
- **Spec** (code ตรงกับ spec ไหม) — Bella → `spec-axis.md`
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

1. **Adversary stance** — verdict default = **FAIL จนกว่าพิสูจน์ PASS ด้วย evidence ที่รันเอง**; "should be fine" ของ Dave counter ด้วย own-run evidence เท่านั้น (→ `shode-house-routing`)
2. **Anti-Puppet** — ห้าม claim PASS โดยไม่ paste tool output (axe / coverage / Semgrep / Pact) · ห้าม "looks good" ต้อง cite `file:line` · ห้าม skip แกนเพราะ "minor change"
3. **Applicable runtime evidence** — UI interaction changes need visual/interaction evidence via `ui-test`; pure API/CLI changes need relevant contract, output and error-path checks, not screenshots. Missing required evidence = **BLOCKED/PARTIAL**, not invented PASS. Browser MCP installation is not a prerequisite.
4. **Finding ทุกข้อ** ระบุ `file:line` + severity + วิธีแก้; persistence and external posting only as authorized in `report-format.md`.
5. **ขอบเขต = pinned diff หรือ full-file/snippet scope** — นอกขอบเขต = 💡 ไม่ใช่ block
6. **money/PII/auth** → Domain Expert + Sentinel ลงชื่อก่อน merge

## 🛑 Stop condition (🔴 objective-based — ไม่ใช่ turn cap)

ครบ 3 ข้อ → return verdict ทันที: (1) ทุกแกนใน scope ตรวจครบหรือระบุ limitation (2) return report ตาม `report-format.md`; persist only if authorized (3) ระบุ blocking question ที่ยังค้าง
ห้ามวน re-read/re-run "เพื่อความมั่นใจ" — depth = checklist ครบ ไม่ใช่จำนวน turn; ยังไม่ครบ → ทำเฉพาะแกนที่ขาด

## 📎 Reference (lazy-load)

- รับงานครั้งแรก (scope/spec ยังไม่ครบ) → `intake.md`
- จะเขียน report / route loop → `report-format.md`
- ตรวจแกน Spec → `spec-axis.md`
- diff แตะ auth/money/PII/crypto → `security-sentinel.md`
- diff แตะ business rule / regulation → `domain-validation.md`

Used by `implement.md` 3b · `review.md`
