# Part 3 — Role-by-Role Playbook: PM, BA, SA, UX, Dev, QA, DevOps

> ตอนที่ 1-2 เราคุยภาพรวมและเคสจริงไปแล้ว ตอนนี้คือคู่มือลงสนาม — แต่ละ role ใน software house ใช้ AI ยังไงให้ตรงปัญหาที่ตัวเองเจอจริง พร้อม slash command ตัวอย่าง และ metric ที่จะรู้ว่าใช้แล้วได้ผล

แต่ละ role ในตอนนี้มีโครงเดียวกัน:

1. **Pain point** — เจ็บตรงไหน
2. **AI Use Cases** — 3 use case ที่แก้ pain ได้จริง
3. **ตัวอย่าง command + output** — เห็นภาพว่ามาในรูปแบบไหน
4. **Metric** — วัดผลยังไง

---

## 3.1 PM — Project Manager

### Pain Point

- Status กระจัดกระจาย — Jira, PR, CI, QA, Slack thread, เอกสารใน Drive
- Ticket update ไม่ตรงความจริง — "Done" บน Jira ≠ "Done" บนโลก
- Scope creep ที่จับไม่ทัน
- Risk รู้ช้า — มักรู้ตอน stakeholder ถามแล้วตอบไม่ได้
- Report ใช้เวลาเยอะ — ทุกศุกร์เย็นมีคนนั่ง copy-paste 2 ชั่วโมง
- Meeting เยอะเกินจนมนุษย์เริ่มเหมือน bot ที่แพงกว่า

### Use Case PM-1 — Sprint Risk Radar

```text
/sprint-risk PROJECT current
```

AI อ่าน:
- Sprint board
- Blocked tickets / labels
- Comments ล่าสุด 7 วัน (หา keyword: blocked, wait, depend, postpone)
- PR status (open, draft, fail CI)
- QA status
- Dependency ticket จาก link

Output:

```md
## Sprint Risk Radar — Sprint 24

### High Risk

1. **PAY-123 Payment callback**
   - Ticket in progress 6 วัน
   - PR ยังไม่ open
   - Dependency: API spec not confirmed (comment from BA เมื่อวาน)
   - Action: Schedule SA clarification today

2. **CUS-456 Customer profile**
   - PR open แต่ CI failed 3 ครั้ง (timeout บน integration test)
   - Action: Pair กับ senior 1 ครั้ง

### Medium Risk

3. **POL-789 Policy renewal**
   - QA backlog 5 ใบ มี QA assigned 1 คน
   - Action: Rebalance scope หรือดึง QA จากทีมข้าง

### Hidden Work

4 PRs open ไม่ link ticket — ขอให้ dev เพิ่ม link ก่อน sprint review
```

### Use Case PM-2 — Auto Weekly Report

```text
/weekly-report 2026-W19
```

AI generate:

- Completed (จริง — ตรวจ DoD)
- In progress
- Blockers (พร้อม owner + age)
- Scope changes (ticket added mid-sprint)
- Risks (จาก sprint-risk radar)
- Next week plan
- Stakeholder updates ที่ต้องการ

PM ใช้ AI generate draft แล้วแก้ 10% ก่อนส่ง — ลด report time จาก 2 ชั่วโมงเหลือ 20 นาที

### Use Case PM-3 — Scope Creep Detector

```text
/scope-creep current
```

AI ตรวจ:
- Ticket ที่ added หลัง sprint start
- Ticket ที่ไม่มี estimation
- Ticket ที่ไม่ link epic
- Ticket ที่ requirement เปลี่ยนหลัง dev เริ่ม (จาก Jira changelog)
- Ticket ที่ comment ขอเพิ่ม scope

ผล: PM มีหลักฐานชัดเจนตอนคุยกับ PO — ไม่ต้องใช้ความรู้สึก

### Metric

| Metric | Target |
|---|---|
| Report preparation time | -70% |
| Blocker detection time | จากรายสัปดาห์ → รายวัน |
| Sprint planning time | -30% |
| Scope creep visibility | เพิ่มขึ้น (วัดจากจำนวน scope change ที่ flag ก่อน mid-sprint) |

---

## 3.2 BA — Business Analyst

### Pain Point

- Meeting note เยอะเกินกว่าจะอ่านซ้ำ
- Requirement conflict ในเอกสารเดียวกันเอง
- Acceptance criteria ไม่ครบ
- Edge case หลุด
- BRD ↔ Jira ticket ไม่ sync
- ลูกค้าพูด 1 อย่าง เอกสารตีความได้ 4 อย่าง ตามธรรมเนียมโบราณของงาน software

### Use Case BA-1 — Meeting to BRD

```text
/transcript-to-brd meeting-2026-05-09
```

Input: meeting transcript (จาก Otter / Fathom / Read.ai หรือ manual note)

Output: BRD draft ที่มีโครงครบ

- Business objective
- In-scope / out-of-scope (สำคัญ — ลด scope creep)
- User roles
- Functional requirement
- Non-functional requirement
- Main flow / alternative flow / exception flow
- Validation rules
- Open question (สำคัญที่สุด — บอกชัดว่าอะไรยังไม่ชัด)

### Use Case BA-2 — Requirement Conflict Checker

```text
/brd-review BRD-2026-001
```

AI ตรวจ:
- Rule ขัดกันใน document เดียว
- Field ใช้คำไม่ตรงกัน (เช่น "customer category" ใน section 3, "customer type" ใน section 7)
- Role permission ที่ขัดกัน
- Flow ไม่มี error case
- Mismatch กับ BRD เก่าที่ระบุไว้ใน reference

Output ตัวอย่าง:

```text
Conflict found:
- Section 3 บอก branch manager approve ได้
- Section 5 บอก only regional manager approve ได้
→ ต้อง clarify

Inconsistent terminology:
- Section 3 ใช้ "customer category"
- Section 7 ใช้ "customer type"
- Data dictionary ใช้ "customer_segment"
→ เลือก 1 แล้วใช้ตลอดเอกสาร

Missing:
- Permission matrix
- Data retention rule
- Error message mapping
- Migration strategy
```

### Use Case BA-3 — Story Generator

```text
/create-stories BRD-PAYMENT-EXPORT
```

Output (Jira-ready):
- Epic: Payment Export
- User stories (ตาม INVEST principle)
- Acceptance criteria (Given-When-Then)
- Definition of Done
- QA notes
- Dev notes
- Out-of-scope clarification

BA review draft แล้ว push ขึ้น Jira ผ่าน MCP

### Metric

| Metric | Target |
|---|---|
| BRD draft time | -40% |
| Missing acceptance criteria | -50% |
| Rework จาก requirement gap | -30% |
| BA → QA handoff time | -30% |

---

## 3.3 SA — System Analyst / Solution Architect

### Pain Point

- ต้องอ่านหลายระบบใน 1 feature
- Impact analysis ใช้เวลาวันละ-สัปดาห์
- Legacy knowledge อยู่ในหัวคน 2-3 คน (ที่กำลังจะเกษียณ)
- Architecture decision ไม่ถูกบันทึกอย่างเป็นทางการ
- Dev ถามซ้ำเรื่อง pattern ทุกอาทิตย์

### Use Case SA-1 — Impact Analysis

```text
/impact-analysis PAY-123
```

AI ค้นจาก:
- Code grep cross-repo
- API catalog (OpenAPI)
- DB schema
- Batch job catalog
- Report SQL
- Test scope
- Past incidents
- ADR เก่า

Output:

- Affected service
- Affected table
- Affected API
- Affected batch
- Affected report
- Risk + likelihood
- Recommended test scope
- Migration consideration

(เห็นตัวอย่างเต็มใน Part 2 Case 9)

### Use Case SA-2 — ADR Generator

```text
/create-adr "Use event-driven callback for payment status update"
```

Output (ตาม MADR template):
- Context
- Decision
- Alternatives considered (พร้อม pros/cons)
- Consequences
- Rollback plan
- Links (relevant ticket, PR, RFC)

ADR ที่ AI generate ไม่ได้ "ตัดสินใจ" — มันรวบ context และ rationale ให้ SA แก้น้อย ๆ ก่อน publish

### Use Case SA-3 — Architecture Review Bot

ก่อน PR merge AI ตรวจ:
- Layer violation (controller → repository ตรง = warn)
- Dependency direction (domain layer ต้องไม่รู้ infrastructure)
- Transaction boundary
- Database access pattern (raw SQL vs repository)
- API contract drift (เทียบกับ OpenAPI baseline)

ตัวที่ยืนยัน final ยังคงเป็น **ArchUnit / dependency-cruiser / structurizr** — ที่ deterministic — แต่ AI ช่วยอธิบายเหตุผลเป็นภาษาคน

### Metric

| Metric | Target |
|---|---|
| Impact analysis time | -50% |
| Architecture review comment ซ้ำ | -40% |
| ADR coverage | +70% |
| Production issue จาก impact หลุด | ลดลง |

---

## 3.4 UX/UI Designer

### Pain Point

- Dev ไม่ใช้ component ที่มีในระบบ
- Requirement ไม่ชัด ต้อง ping 5 ครั้ง
- Design handoff ขาด detail (state, validation, copy)
- Accessibility ถูกเช็คท้ายสุด — เจอตอนใกล้ release
- Design system drift — มี Button 5 แบบใน production

### Use Case UX-1 — Requirement to Wireframe Checklist

AI ไม่ได้แทน designer — แต่ช่วยสร้าง checklist ก่อน design จริง

```text
/ux-brief CUS-456
```

Output:
- User goal (จาก BRD)
- Main task ที่ user ต้องทำได้
- Screen list ที่ต้อง design
- Form fields + validation
- State ที่ต้องครอบ (loading, empty, error, success)
- Error message (จาก style guide)
- Accessibility note ตาม WCAG 2.2

Designer ใช้ checklist นี้เป็นจุดเริ่ม ไม่ลืม state ใดเลย

### Use Case UX-2 — Component Reuse Advisor

```text
/find-components "customer search with filter and status badge"
```

AI query Storybook + component catalog (MCP):

Output:
- Existing components ที่ตรงกับ requirement
- Usage example (link ไป Storybook)
- Design token ที่ใช้
- Accessibility note
- Variants ที่มีอยู่แล้ว

ลด "ออกแบบใหม่" ที่จริงแล้วมีของเดิมอยู่แล้ว 70%

### Use Case UX-3 — Handoff Generator

จาก Figma + Jira:
- Screen behavior
- Validation rule
- Edge state
- Responsive rule (breakpoint)
- Copy text (with i18n key)
- Component mapping (Figma layer → @company/ui component)

Dev ได้ handoff doc ที่ "ไม่ต้องถาม designer ทุกชั่วโมง"

### Metric

| Metric | Target |
|---|---|
| Design handoff clarification | -40% |
| Component reuse | +50% |
| Accessibility issue caught early | +60% |
| UI inconsistency | ลดลง |

---

## 3.5 Developer

### Pain Point

- อ่าน ticket ไม่ครบ (เพราะติดงานอื่น)
- Context หายระหว่าง task
- Boilerplate เยอะ
- AI generate ผิด pattern
- Review ยาว
- Test ไม่ครบ
- Fix CI น่าเบื่อเหมือนชดใช้กรรมชาติที่แล้ว

### Use Case DEV-1 — From Ticket to Plan

```text
/from-ticket PAY-123
```

AI:
1. อ่าน ticket จาก Jira
2. อ่าน BRD ที่ link
3. อ่าน acceptance criteria
4. อ่าน OpenAPI spec ของ service ที่เกี่ยวข้อง
5. อ่าน DB schema
6. อ่าน past incident ที่ tag module นี้

Output:

```md
## Implementation Plan — PAY-123

### Files to change
1. PaymentCallbackResource.java — add new endpoint
2. PaymentCallbackRequest.java — DTO
3. PaymentCallbackValidator.java — signature verification
4. PaymentService.java — orchestration
5. PaymentRepository.java — idempotency lookup
6. AuditLogger.java — write audit log

### Tests
7. PaymentServiceTest.java — unit
8. PaymentCallbackResourceIT.java — integration
9. payment-callback.contract.yaml — contract test

### Docs
10. OpenAPI spec update
11. ADR draft (ถ้าใช้ retry pattern ใหม่)

### Risks
- Duplicate callback (idempotency key handling)
- Signature mismatch (rotation)
- Race with batch job premium-reconcile

### Estimated complexity: M (3-5 day)
```

Dev ไม่ต้องเริ่มจากศูนย์ — มี plan ที่ขัดเกลาได้ทันที

### Use Case DEV-2 — Scaffold Resource

```text
/scaffold-resource payment-callback --stack dropwizard
```

AI generate ตาม internal template:
- Resource / Controller (HTTP layer only)
- DTO (with validation)
- Service (business logic)
- Repository (DB only)
- Mapper (DTO ↔ entity)
- Unit test (service)
- Integration test (resource)
- OpenAPI spec
- Audit log hook

ทุกไฟล์ตาม coding standard ของบริษัท ไม่ใช่ generic Spring/Dropwizard ที่ AI เห็นบน internet

### Use Case DEV-3 — Self Review Before PR

```text
/review-before-pr
```

AI ตรวจก่อนเปิด PR:
- Code standard
- Missing test
- Security issue (basic SAST + LLM review)
- Unused dependency / import
- Architecture violation
- Unclear naming
- Missing audit log
- PR description suggestion

ผล: PR ที่เปิดมีคุณภาพสูงตั้งแต่ first push — first-pass PR rate เพิ่ม 30-40%

### Metric

| Metric | Target |
|---|---|
| Boilerplate time | -60% |
| First-pass PR rate | +40% |
| Review comment เรื่อง style | -70% |
| CI failure จาก standard | -50% |

---

## 3.6 QA

### Pain Point

- Test case เขียนช้า
- Requirement ไม่ครบ ต้องเดา
- Regression scope ไม่ชัด — รัน 100 case หรือ 500?
- Bug triage ใช้เวลานาน
- Automated test ตามไม่ทัน feature

### Use Case QA-1 — Requirement to Test Matrix

```text
/generate-test-matrix PAY-123
```

Output:

| Requirement | Positive | Negative | Edge | Permission | Regression | Security |
|---|---|---|---|---|---|---|
| Payment callback | valid callback | invalid signature | duplicate callback | unauthorized source | old payment status (BUG-2023) | replay attack |

QA validate business rule ก่อนใช้เป็น test plan

### Use Case QA-2 — Diff to Regression Scope

```text
/regression-scope PR-456
```

AI อ่าน code diff แล้วสรุป:
- Module ที่กระทบ
- API ที่ shape เปลี่ยน (จาก OpenAPI diff)
- Screen ที่กระทบ
- Test เดิมที่ควรรัน
- Test ใหม่ที่ควรเพิ่ม

QA ไม่ต้องรัน "ทุกอย่างเผื่อไว้" — มี scope ที่มีหลักฐาน

### Use Case QA-3 — Bug Triage

```text
/triage-bug BUG-789
```

AI อ่าน:
- Bug report
- Log + screenshot
- Recent PR ที่ touch module เดียวกัน
- Test ที่ pass / fail
- Past incident ใกล้เคียง

Output: probable root cause + suggested reproduce step + recommended owner

### Metric

| Metric | Target |
|---|---|
| Test case drafting | -60% |
| Regression planning | -50% |
| Bug triage time | -40% |
| Defect leakage | ลดลง |

---

## 3.7 DevOps / Platform

### Pain Point

- Pipeline fail แล้ว dev ไม่รู้แก้ยังไง — มา ping ใน Slack ทุกวัน
- Environment config drift
- Secret หลุด / rotate ไม่ทัน
- Deploy checklist ทำ manual
- Observability ไม่ถูกใช้เต็มที่ — มี dashboard 30 อัน เปิดดู 3

### Use Case OPS-1 — CI Failure Explainer

```text
/explain-ci-failure pipeline-123
```

AI output:
- Failed job + step
- Root cause (จาก log + error pattern)
- File ที่เกี่ยวข้อง
- Suggested fix (พร้อม example)
- Owner (จาก CODEOWNERS)
- Link ไปที่ runbook ถ้ามี

ลด Slack message "ใครรู้บ้าง CI พังเพราะอะไร" ลง 50%

### Use Case OPS-2 — Deployment Risk Check

```text
/release-risk release-2026.05.09
```

AI ตรวจ:
- Failed pipeline ใน release branch
- Unmerged hotfix ที่ควร include
- High-risk PR (ตาม label หรือ size)
- DB migration ที่ต้อง coordinate
- Feature flag ที่ enable พร้อม release
- Rollback plan availability

Output: risk score + checklist ก่อน deploy

### Use Case OPS-3 — Config Drift Detector

```text
/config-drift sit uat prod
```

AI เทียบ config 3 environment:
- Env var ที่ขาดใน environment ใด
- Value ต่างผิดปกติ (เช่น `JWT_EXP=3600` ใน UAT, `JWT_EXP=86400000` ใน PROD — typo เป็น ms กับ s)
- Version mismatch
- Secret format ผิด

จับ config bug ก่อนถึง production

### Metric

| Metric | Target |
|---|---|
| CI troubleshooting time | -40% |
| Release preparation time | -30% |
| Config drift incident | ลดลง |
| Mean time to recovery | ลดลง |

---

## ภาพรวม Role Playbook

ลองสังเกตจะเห็น pattern ซ้ำกันใน 7 role:

1. ทุก role มี **Use Case แบบ "ลด work ซ้ำ"** (report, scaffold, draft) — AI ทำได้เร็วและถูกพอใช้
2. ทุก role มี **Use Case แบบ "ลด context-switching"** (summarize, find, query) — AI ลดเวลาหา
3. ทุก role มี **Use Case แบบ "เพิ่ม coverage"** (checklist, conflict checker, regression scope) — AI จับสิ่งที่คนมองข้าม

แต่ทุก role ก็มีงานที่ AI **ไม่ควร** ทำเอง:
- PM ตัดสินใจเรื่อง scope
- BA ยืนยัน business intent กับลูกค้า
- SA ตัดสินใจ architecture
- Designer ตัดสินใจ UX direction
- Dev ตัดสินใจ trade-off
- QA sign-off release
- DevOps ทำ irreversible action บน production

นี่คือเส้นแบ่งระหว่าง **AI ที่ช่วยงาน** กับ **AI ที่แทนคน** — ซีรีส์นี้ยืนข้างแรกตลอด

---

## สรุป Part 3

ทุก role ใน software house มีงานที่ AI ช่วยได้จริง — แต่ที่สำคัญกว่าคือทุก role ต้องเข้าถึง 3 สิ่ง:

1. **Context** ของบริษัท (handbook + MCP + RAG)
2. **Workflow มาตรฐาน** (slash command + skill)
3. **Metric** ที่วัดว่าใช้แล้วได้ผล

ถ้าขาดข้อใดข้อหนึ่ง AI จะกลายเป็น "เครื่องมือเพิ่มอีกตัว" ที่ทุกคนใช้แบบไม่เป็นระบบ — ซึ่งคือ Part 1 + Part 2 ที่เราเพิ่งคุยกันไป

ใน Part 4 เราจะลงไปดูว่า "context + workflow + metric" ทั้งหมดนี้รวมเป็น **architecture ของ AI Agent Platform** ยังไง — 6 Pillars Framework, MCP layer, Skill design, Plugin distribution, Multi-repo strategy
