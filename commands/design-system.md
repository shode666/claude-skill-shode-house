---
description: "[shode-house] Full design pipeline (BA → Domain → SA → Oliver summary)"
allowed-tools: Task, Read, Write, Edit, Grep, Glob
argument-hint: [system description]
---

Full design pipeline สำหรับ: **$ARGUMENTS**

## Pipeline (บังคับผ่าน domain expert)

### 0. Triage (Oliver)
- วิเคราะห์ domain → เลือก Domain Expert
- ถ้าไม่ตรง domain ใด → **หยุด** ถาม user
- Present engagement plan → user approve

### 1. Business Analysis (Bella)
- BRD (objective, scope, stakeholder + RACI)
- User Stories + AC (Given-When-Then)
- As-is / To-be process (Mermaid)
- Event Storming (ถ้า complex domain)
- RTM (BR → FR → test)
- Assumption + open questions
- **ปรึกษา Domain Expert** สำหรับ business rule

→ `outputs/01-brd.md`

### 2. Domain Design (Domain Expert)
Expert ที่เลือกใน Step 0:
- Schema + ER diagram
- State machine / lifecycle
- Business rule + edge case
- Compliance note
- ถ้าไม่ใช่ domain ของตัวเอง → ปฏิเสธ + รายงาน Oliver

→ `outputs/02-domain-design.md`

### 3. Architecture (Sara)
- C4 Context + Container
- Tech stack + เหตุผล
- NFR table
- ADR (สำคัญ 3-5 ตัว)
- Threat model (STRIDE)
- DR/BCP (RTO/RPO)
- Risk register
- **Validate กับ Domain Expert** จุดที่เกี่ยวข้อง

→ `outputs/03-architecture.md`

### 3.5. UX/UI Design (Uma) 🔴 v2.6.1 — conditional

**Trigger**: feature touch frontend/UI/component/page/view/email template/dashboard (web/mobile)
**Skip**: pure backend/API/data pipeline/CLI/library (Oliver ตัดสินใจตอน Step 0 Triage, confirm กับ user ถ้ากำกวม)

Uma produce:
- Persona + JTBD + journey map (ถ้า new domain) — link Bella research
- IA + user flow (happy + edge + error) — Mermaid
- Wireframe low-fi → mid-fi (Figma frame link + frame ID)
- Design tokens (W3C DTCG): primitive → semantic → component → `tokens.json`
- a11y checklist (WCAG 2.1/2.2 AA): contrast / keyboard / screen reader / reduced motion
- Component state inventory: default/hover/active/focus/disabled/loading/error/empty
- Hand-off bundle to Dave: Figma link + tokens + spec + a11y note + AC (G-W-T visual)
- **Validate กับ Bella + Sara** — flow ตรง BRD, component สอดคล้อง architecture

→ `outputs/04-ux-ui.md`

### 4. Summary (Oliver)
- Exec summary 1 หน้า
- Link ทุก step
- Next: `/implement` หรือ `/setup-project`
- Risk + open questions

→ `outputs/00-summary.md`

## ⚠️ Rules

1. ห้าม skip domain expert
2. Domain ไม่ fit expert → Oliver หยุดถาม user
3. แต่ละ step save ไฟล์แยก (traceable)
4. ภาษาไทย
5. ห้าม implement code (ใช้ `/implement`)
6. 🔴 v2.6.1 — ถ้า feature มี frontend/UI → **ห้าม skip Step 3.5 Uma**. Pure backend = skip ได้ แต่ต้อง confirm กับ user ก่อน
