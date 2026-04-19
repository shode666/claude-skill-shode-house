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
