---
name: review-checklist
description: |
  [WHAT] Code review discipline — Chris 7-dim checklist + Quinn integration/E2E/contract/load/a11y matrix + Sentinel security + Domain Expert validation + severity grading + bd-native report format. DRY source-of-truth สำหรับ /implement Phase 3b และ /review.
  [AUDIENCE] Chris (7-dim primary) + Quinn (integration/E2E/security scan) + Sentinel (CSP/SAST/abuse) + Domain Experts (Felix/Iris/Sam/Tara/Elena/Brooke/Emma).
  [WHEN] Phase 3b ใน /implement pipeline; ทุก call ของ /review; ก่อน merge gate; หลัง bug fix.
  [TRIGGER] /shode-house:review-checklist, "code review", "review", "7-dim", "Chris review", "Quinn integration test", "security scan", "domain validate", "REVIEW report format".
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
- [ ] **Spec source ระบุได้** (🆕 v3.12) — หาตามลำดับ: bd-id/issue ref ใน commit message → path ที่ user ส่ง → `outputs/SPEC-<bd-id>.md` / `outputs/<bd-id>/` → ถามผู้ใช้. ไม่มี spec จริง ๆ → Spec axis รายงาน **"no spec available"** ห้าม pass เงียบ
- [ ] **Static analysis tool พร้อม** (lint/SAST configured — Chris ใช้ Bash จริง, ไม่ใช่ "ดู visually")
- [ ] **Tracker available** (bd active หรือ Jira key — finding ต้อง track, ไม่ใช่ chat message)
- [ ] **Severity scale agreed** (project ใช้ 🔴/🟠/🟡/🔵/💡 default — ห้าม "minor/major" loose)

---

## Chris — 7 Dimensions = **Standards axis** (รัน parallel เป็น 7 pass)

> ตอบคำถามเดียว: *code เขียนถูกหลักไหม*. คำถาม *code ทำตรงกับที่ spec ขอไหม* = § Spec Axis ด้านล่าง (คนละ sub-agent)

ทุกมิติ output: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low / 💡 Suggestion

### 1. Correctness — **internal behavior เท่านั้น** (v3.12)
> requirement conformity (ตรง spec/AC ไหม) = งานของ **Spec axis** ห้ามตรวจซ้ำที่นี่ — อ่าน diff สองรอบ + finding ซ้ำ
- Invariant ของ module ไม่ถูกทำลาย (state machine, ordering, idempotency)
- Edge case (null/empty/boundary/overflow/unicode)
- Error path (catch + re-throw + meaningful message)
- Concurrent: race / deadlock / lost update
- Idempotency (retry-safe)

### 2. Security (OWASP Top 10 + lang-specific)
- Injection (SQL/NoSQL/cmd/LDAP/XPath)
- Broken auth + session
- Sensitive data (PII/PCI/secret)
- XXE / SSRF / deserialization
- Broken access (BOLA/IDOR/missing authz check)
- Misconfig (default password, exposed admin, verbose error)
- XSS (stored/reflected/DOM) + CSP bypass
- Vulnerable component (audit dep)
- Logging gap (audit trail missing)
- SSRF / open redirect

→ 🔴 Security Critical/High = **block merge** เสมอ (no exception)

### 3. SOLID & Design
- SRP — class/function ทำสิ่งเดียว
- OCP — extend ผ่าน interface
- LSP — subtype substitutable
- ISP — interface เล็ก
- DIP — depend on abstraction
- Cohesion สูง / coupling ต่ำ
- DRY (แต่ไม่ over-DRY = WET tolerable)

### 4. Performance
- N+1 query
- Time/space complexity (Big-O)
- Memory allocation (loop alloc, leak)
- DB index utilization
- Cache strategy (TTL, invalidation)
- Async/await + thread pool sizing
- Cold start / startup time

### 5. Maintainability
- File size ≤ 300 lines (function ≤ 30; cyclomatic ≤ 10)
- Naming descriptive (intent revealing)
- Comment "why" ไม่ใช่ "what" (code อ่านได้แล้ว)
- Magic number → constant
- Test as documentation
- Tech debt label (TODO/FIXME/HACK) มี ticket

### 6. Testing
- Unit coverage ≥ project threshold (Chris baseline ratchet)
- Mutation kill ≥ 70% (Stryker/PIT/mutmut)
- Property-based test (Hypothesis/fast-check) สำหรับ invariant
- Test doubles ถูก: stub/fake/mock/spy ตามจุด
- ห้าม mock business logic (mock เฉพาะ external: DB/API/clock)
- ห้าม `time.sleep` (fake time/freeze)

### 7. Observability
- Structured log (JSON, key fields: req_id, user_id, latency)
- Metric (RED: rate/error/duration หรือ USE: utilization/saturation/error)
- Trace (OpenTelemetry span ที่ critical path)
- Alert ทุก SLO breach (link runbook)
- Audit log สำหรับ R0 action (money/auth/PII access)

---

## 🎯 Spec Axis (🆕 v3.12 — แกนที่ 2, รัน **parallel sub-agent แยกจาก Chris**)

> Chris 7-dim + Quinn 6-axis เป็น **standards ล้วน** — ตอบแค่ "code เขียนถูกหลักไหม" ไม่มีใครตอบ **"code ทำในสิ่งที่ spec ขอหรือเปล่า"**. code ที่ตามมาตรฐานครบแต่ทำผิดเรื่อง = **Standards PASS / Spec FAIL**; รายงานรวมกันเมื่อไหร่ แกนหนึ่งบังอีกแกน — นี่คือช่องที่ Anti-Puppet Gate เดิมเจาะไม่ถึง

**รายงาน 3 อย่าง — quote บรรทัดของ spec ทุก finding**
- **(a) ขาด/ทำครึ่งเดียว** — AC บอก retry 3 ครั้ง โค้ด retry ครั้งเดียว
- **(b) scope creep** — behaviour ใน diff ที่ spec ไม่ได้ขอ (เช่นแอบใส่ caching layer) → Philosophy #4 SCOPE DRIFT
- **(c) ดูเหมือนทำแล้วแต่ผิด** — คำนวณ VAT ก่อนหักส่วนลด ทั้งที่ spec บอกหลัง

**กฎการรัน (🔴)**
1. Spec axis กับ Standards axis (Chris) **รันเป็น sub-agent คนละตัว** — ไม่ให้ context ปนกัน (per Handoff Contract: ส่ง path ของ diff + spec ไม่ส่งเนื้อหา)
2. รายงานแยกหัวข้อ `## Standards` และ `## Spec` — **ห้าม merge หรือ rerank ข้ามแกน** เพราะการแยกแกนมีไว้กันการบังกันเอง
3. ปิดท้าย 1 บรรทัด: จำนวน finding ต่อแกน + ตัวแย่สุด **ในแต่ละแกน** — ห้ามเลือกผู้ชนะข้ามแกน
4. ไม่มี spec → ข้าม Spec axis แล้วเขียน **"no spec available"** ใน report (ไม่ใช่ pass เงียบ ๆ)

**Routing**: finding ของ Spec axis ส่วนใหญ่ route → **Phase 1a** (Bella ∥ Sara revise spec/AC) ไม่ใช่ Phase 2 — ยกเว้นข้อ (c) ที่ spec ถูกแต่ code ผิด → Phase 2

---

## Quinn — Integration Matrix (รัน 6 axes)

### 1. Integration (Testcontainers + real dep)
- Real DB (Postgres/MySQL/Mongo via Testcontainers)
- Real cache (Redis Testcontainers)
- Real queue (Kafka/RabbitMQ Testcontainers)
- ห้าม mock DB/cache/queue ถ้า test integration

### 2. E2E (Playwright/Cypress — critical user journey)
- Critical path 100% coverage (login/checkout/payment/booking)
- Happy + 1 error path ต่อ journey
- Mobile + desktop viewport

### 3. Contract (Pact + Schemathesis)
- Consumer-driven (consumer Pact → provider verify)
- OpenAPI schema fuzz (Schemathesis)
- Pact broker integration (CI gate)

### 4. Load smoke (k6 / Locust / Gatling)
- p95 < SLO (จาก `slo` skill)
- Error rate < 0.1%
- 1-2x peak สำหรับ smoke; nightly = full load

### 5. a11y automation (axe-core)
- WCAG AA — critical violations = 0
- jq filter axe report → bd note ถ้าเจอ
- Storybook addon-a11y per component

### 6. Pen test (OWASP ASVS Level 1-2)
- Automated: ZAP baseline
- Manual: spot check top-OWASP per release
- Sensitive flow (payment/auth) — Sentinel co-review

---

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

## REVIEW Report Format + Loop Routing → `report-format.md` (v3.12)

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
