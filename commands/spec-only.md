---
description: "[shode-house] ทำ spec อย่างเดียว (BA + SA + Domain) ไม่ implement — เหมาะกับ proposal/estimation"
allowed-tools: Task, Read, Write, Edit, Grep, Glob
argument-hint: [system description]
---

ทำ spec สำหรับ: **$ARGUMENTS**

## เป้าหมาย
spec สำหรับ proposal/quotation/estimation/onboarding — **ไม่ implement code**

## Pipeline (หยุดที่ spec)

### 0. Triage (Oliver)
- ระบุ domain → เลือก Domain Expert
- Present plan ให้ user approve

### 1. Requirements (Bella)
- BRD (objective, scope, stakeholder, RACI)
- FRD (priority + AC)
- NFR baseline
- User stories + AC
- Process flow as-is/to-be
- Event Storming (ถ้า complex domain)
- RTM
- Risk + assumption

→ `outputs/01-brd.md`

### 2. Domain Spec (Domain Expert)
- ER diagram + state machine
- Business rule + edge case
- Compliance note

→ `outputs/02-domain-spec.md`

### 3. Architecture (Sara)
- C4 Context + Container
- Tech stack (options + chosen + reason)
- ADR (3-5 decision สำคัญ)
- NFR targets
- Threat model (STRIDE)
- DR/BCP target (RTO/RPO)
- Risk register

→ `outputs/03-architecture.md`

### 4. Estimation (Oliver + Sara)
T-shirt size (XS/S/M/L/XL) ต่อ module:
- Foundation (setup, infra)
- Per business module
- Integration
- QA

→ `outputs/04-estimation.md`

### 5. Summary (Oliver)
Exec summary 1 หน้า:
- Business objective
- Solution overview
- Tech headline
- Effort ballpark
- Assumption + risk
- Next step

→ `outputs/00-proposal-summary.md`

## ⚠️ Rules

1. **ห้าม implement code** — spec/diagram/table เท่านั้น
2. ผ่าน Domain Expert สำหรับ domain-specific
3. ภาษาไทย (diagram = Mermaid)
4. ถ้า user proceed → เสนอ `/implement` + `/setup-project`
