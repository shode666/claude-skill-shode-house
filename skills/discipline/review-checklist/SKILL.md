---
name: review-checklist
description: |
  [WHAT] Code review discipline — Chris 7-dim checklist + Quinn integration/E2E/contract/load/a11y matrix + Sentinel security + Domain Expert validation + severity grading + bd-native report format. DRY source-of-truth สำหรับ /implement Phase 3b และ /review.
  [WHEN] Phase 3b ใน /implement pipeline.
  [TRIGGER] /shode-house:review-checklist, "code review", "review", "7-dim", "Chris review", "Quinn integration test".
---

# Review Checklist (v3.1 DRY source-of-truth)

> v3.1 refactor: เดิม `/implement` Phase 3b และ `/review` มี checklist ของตัวเอง — duplicate logic. v3.1 รวมเป็น skill เดียว, ทั้ง 2 command อ้างที่นี่
> **Owners**: Chris (primary 7-dim) + Quinn (integration matrix) + Sentinel (security depth) + Domain Expert (regulation/business rule)

---

## When NOT to use

- **Spike / throwaway script** — review overhead ไม่คุ้ม
- **Generated code** (codegen output, ORM model auto-generated) — review template, ไม่ใช่ instance
- **Pure doc/markdown change** — Bella/Uma review เนื้อหา, ไม่ใช่ review-checklist
- **Production hot-fix P0** ที่ต้อง ship ทันที — รัน checklist เฉพาะ 🔴 Critical (Security + Correctness); defer มิติอื่นเป็น follow-up

## Required inputs — refuse without

- [ ] **ขอบเขต diff ถูก pin มาแล้ว** — caller (Oliver/`/review`) ต้องส่ง **fixed point + diff command ที่รันได้จริง** มาให้ ไม่ใช่ให้ reviewer เดาเอง
      วิธี resolve (มี fallback ladder สำหรับ path/snippet/non-git) = `commands/review.md` § Scope resolution · reviewer ตรวจแค่ว่า diff ไม่ว่างและ ref resolve ได้
- [ ] **Spec source ระบุได้** — หาตามลำดับ: bd-id/issue ref ใน commit message → path ที่ user ส่ง → `outputs/SPEC-<bd-id>.md` / `outputs/<bd-id>/` → ถามผู้ใช้. ไม่มี spec จริง ๆ → Spec axis รายงาน **"no spec available"** ห้าม pass เงียบ
- [ ] **Static analysis tool พร้อม** (lint/SAST configured — Chris ใช้ Bash จริง, ไม่ใช่ "ดู visually")
- [ ] **Tracker available** (bd active หรือ Jira key — finding ต้อง track, ไม่ใช่ chat message)
- [ ] **Severity scale agreed** (project ใช้ 🔴/🟠/🟡/🔵/💡 default — ห้าม "minor/major" loose)

---

## แกนของการ review — ใครทำอะไร (orchestration core)

| แกน | เจ้าของ | รายละเอียดอยู่ที่ |
|---|---|---|
| **Standards** — code เขียนถูกหลักไหม | Chris | `agents/code-reviewer.md` § 7 มิติ (Correctness = internal behavior/invariant/error-path เท่านั้น) |
| **Standards / runtime** — พฤติกรรมจริงตอนรัน | Quinn | `agents/qa-engineer.md` § ขอบเขต (integration/E2E/contract/load/a11y/pen) |
| **Spec** — code ทำตรงกับที่ spec ขอไหม | Bella | `spec-axis.md` (ไฟล์ข้าง SKILL.md นี้) |
| Security depth (conditional) | Sentinel | `secure` skill |
| Domain validation (conditional) | Domain expert | `report-format.md` § Domain routing |

🔴 **Standards กับ Spec เป็นคนละ sub-agent เสมอ** — context ห้ามปน · aggregate แยกหัวข้อ `## Standards` / `## Spec` · **ห้าม merge หรือ rerank ข้ามแกน** · ปิดท้าย 1 บรรทัด: จำนวน finding + ตัวแย่สุด **ในแต่ละแกน**
🔴 requirement conformity เป็นของ **Spec axis เท่านั้น** — Chris ห้ามตรวจซ้ำ (อ่าน diff สองรอบ + finding ซ้ำ)
ทุกแกน apply: § Severity Grading · § Anti-Puppet Gate · § Mandatory Visual Verify · report format ใน `report-format.md`

## Sentinel — Security Depth (conditional, when secure skill triggered)

- SAST (Semgrep/CodeQL) — full repo
- SCA (Trivy/Grype/npm audit) — dep + container
- Secret scan (gitleaks/truffleHog) — commit history + current
- CSP / Trusted Types policy review
- Abuse case validation (จาก `secure` skill threat model)
- Pen test (OWASP ASVS, ถ้า PCI/HIPAA scope)

---

## Domain Expert — Conditional Validation

changed code แตะ keyword ของ domain ไหน → **domain expert ตัวนั้นต้อง validate parallel กับ Chris+Quinn** (money/regulation = ห้าม merge โดยไม่มีลายเซ็น)
ตาราง keyword → expert (payment/ledger→Felix · policy/claim→Iris · SAP/ABAP→Sam · order/matching→Tara · accounting/inventory→Elena · booking/yield→Brooke · cart/promotion→Emma) → **`report-format.md` § Domain routing**

## Severity Grading (consistent)

| Severity | Meaning | Action |
|---|---|---|
| 🔴 **Critical** | Security exploit / data loss / production-breaking / regulation violation | **Block merge**, immediate fix |
| 🟠 **High** | Wrong behavior / perf regression > 10% / a11y critical | Fix before merge |
| 🟡 **Medium** | Code smell / minor inefficiency / test gap | Track P2-P3, fix in next bd iter |
| 🔵 **Low** | Nitpick / style / could-be-better | Optional, defer P4 backlog |
| 💡 **Suggestion** | Refactor opportunity / pattern improvement | Inform, no block |

---

## REVIEW Report Format + Loop Routing → `report-format.md`

เขียน report เมื่อไหร่ → อ่าน **`report-format.md`** (ไฟล์ข้าง SKILL.md นี้): bd-native template · markdown fallback · storage rule (ห้ามเขียนซ้ำ 2 ที่) · ตาราง Loop Routing ต่อชนิด finding
เป็น output template = reference ที่ใช้ตอนท้าย ไม่ต้องแบกไว้ตลอด (preload budget, CI #16)

## Anti-Puppet Gate

- ห้าม claim "PASS" โดยไม่ paste tool output (jq axe / coverage report / Semgrep finding / Pact verification)
- ห้าม "should be fine" / "looks good" — verbatim cite line numbers
- ห้าม skip 7-dim เพราะ "minor change" — minor = bypass ก็ minor effort
- ห้าม domain skip ถ้า code touches money/regulation/PII

## 🔴 Adversary Stance

verdict default = **FAIL จนกว่าจะพิสูจน์ PASS ด้วย evidence ที่รันเอง** · zero trust ต่อคำอ้างของ Dave · Dave push back "should be fine" → counter ด้วย own-run evidence เท่านั้น
ตารางเต็ม (ใครเชื่อใครได้แค่ไหน) → `shode-house-routing` § Adversarial RACI

## 🌐 Mandatory Visual Verify

Frontend/API/observable ถูกแตะ → **ต้องมี visual/interaction evidence ก่อน PASS**: screenshot path จริง · console error (หรือยืนยันว่าไม่มี) · network status ของ request หลัก
🔴 บังคับ *หลักฐาน* ไม่ใช่บังคับ *tool ตัวใดตัวหนึ่ง* — plugin ไม่ได้จัดหา browser MCP (`.mcp.json` มีแค่ Context7) และชื่อ tool ต่างกันตาม config ผู้ใช้
**tool ladder + วิธีเก็บหลักฐานแต่ละทาง → `ui-test` skill § Visual evidence ladder** (Chris/Quinn โหลดตอนแตะ frontend อยู่แล้ว) · ทำไม่ได้ทุกทาง = **BLOCKED ไม่ใช่ PASS**

## กฎที่ต้องทำ (positive form — v3.12)

- **verdict ทุกข้อมี evidence ที่รันเอง** (command + output ที่ paste) — verdict default = FAIL จนกว่าจะพิสูจน์ PASS
- **finding ทุกข้อระบุ file:line + severity + วิธีแก้** และถูก track ใน tracker ไม่ใช่ค้างในแชท
- **UI change → paste visual/interaction evidence ตาม ladder** (Playwright screenshot + console + network; axe สำหรับ a11y) ก่อนให้ผ่าน
- **money/PII/auth → Domain Expert + Sentinel ต้องลงชื่อ** ก่อน merge
- **ขอบเขต review = diff จาก fixed point ที่ pin ไว้** — นอกขอบเขตนั้นบันทึกเป็น 💡 Suggestion ไม่ใช่ block

## Used by

- `commands/implement.md` Phase 3b (Chris ∥ Quinn parallel pass)
- `commands/review.md` (standalone ad-hoc review)
- Both commands invoke this skill — DRY source-of-truth
