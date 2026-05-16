---
description: "[shode-house] Coop Design pipeline (Bella + Sara + Uma + Domain parallel) — v2.7 Coop Workflow Phase 1"
allowed-tools: Task, Read, Write, Edit, Grep, Glob
argument-hint: [system description]
---

🤝 **Coop Design Phase 1** สำหรับ: **$ARGUMENTS**

> Replaces sequential BA → Domain → SA → Uma pattern (pre-v2.7). All design agents work **in parallel + cross-feedback** → produce single integrated bundle.

## Step 0 — Triage (Oliver)

- วิเคราะห์ domain → เลือก Domain Expert (เฉพาะถ้า touch business rule)
- ตรวจ frontend trigger (touch UI/component/page/view/email/dashboard) → เลือก Uma เข้า Coop ไหม
- ถ้าไม่ตรง domain ใด → **หยุด** ถาม user
- Present engagement plan + roster (Bella + Sara + Uma* + Domain*) → user approve

## Step 1 — Coop Kick-off (Oliver broadcast)

```
[Oliver|state:coop-kickoff|phase:1] Coop Design start
- Roster: Bella + Sara + Uma* + [Domain]*
- Shared workspace: outputs/01-coop-design.md
- Budget: [T-shirt size]; mid-checkpoint at 30%, sign-off at 100%
- Cross-feedback: ทุก agent post initial draft → mid-checkpoint cross-read → resolve conflict → sign-off
```

## Step 2 — Parallel Draft (🤝 all agents simultaneously)

ทุกคนเริ่มพร้อมกัน (ห้าม serialize):

### Bella draft (Business Analysis)
- BRD (objective, scope, stakeholder + RACI)
- User Stories + AC (Given-When-Then)
- As-is / To-be process (Mermaid)
- Event Storming (ถ้า complex domain)
- RTM (BR → FR → test)
- Assumption + open questions

### Sara draft (Architecture)
- C4 Context + Container
- Tech stack + เหตุผล
- NFR table
- ADR candidates (สำคัญ 3-5 ตัว)
- Threat model (STRIDE)
- DR/BCP (RTO/RPO)
- Risk register

### Uma draft (UX/UI — conditional ถ้า frontend trigger)
- Persona + JTBD + journey map (ถ้า new domain)
- IA + user flow (happy + edge + error) — Mermaid
- Wireframe low-fi → mid-fi (Figma frame link + frame ID)
- Design tokens (W3C DTCG): primitive → semantic → component → `tokens.json`
- a11y checklist (WCAG 2.1/2.2 AA)
- Component state inventory: default/hover/active/focus/disabled/loading/error/empty
- Hand-off bundle preview (สำหรับ Phase 2 Dave)

### Domain Expert draft (Domain Design — conditional ถ้า business-rule trigger)
- Schema + ER diagram
- State machine / lifecycle
- Business rule + edge case
- Compliance note (with Domain Evidence Protocol citation)
- ถ้าไม่ใช่ domain ของตัวเอง → ปฏิเสธ + รายงาน Oliver

## Step 3 — Mid-Checkpoint (≥30% budget done — Oliver enforce)

ทุก agent post initial draft → cross-read ของกัน 1 pass:

```
[Bella] draft posted (BRD v0.1 — 8 FR, 3 open Q)
[Sara] draft posted (ADR v0.1 — 4 ADR candidates, tech stack TS+PG+Redis)
[Uma] draft posted (wireframe 5 frames, tokens v0.1)
[Felix] draft posted (KYC flow + double-entry CoA — PCI-DSS v4.0 Req 3.5.1 cite)

[Oliver|state:coop-checkpoint|phase:1] all 4 draft posted → cross-read round 1
```

## Step 4 — Cross-Feedback (1-2 round)

ทุก agent identify conflict/gap/coupling กับ draft ของคนอื่น:

```
[Bella → Sara] FR-12 "real-time inventory" vs ADR-02 batch sync → conflict, ขอ resolve
[Sara → Uma] ADR-03 multi-tenant DB → wireframe ต้องมี tenant switcher
[Uma → Bella] wireframe checkout flow มี 6 step; user story บอก 4 step → ขอ confirm
[Felix → Sara] ADR-01 ledger schema ขาด audit trail per PCI-DSS Req 10
```

→ แต่ละ agent **กลับไปแก้ draft** + repost (max 2 round)

## Step 5 — Integration Sign-off (all participants)

ทุก agent post acknowledgment ว่า draft ตัวเอง consistent กับของคนอื่น:

```
[Bella] ✅ BRD v1.0 signed (cross-ref ADR-01..04 + Uma wireframe + Felix rule)
[Sara]  ✅ ADR v1.0 signed (cross-ref BRD FR-1..15 + Uma component lib + Felix schema)
[Uma]   ✅ Wireframe v1.0 + tokens v1.0 signed (cross-ref BRD flow + Sara tenant ADR)
[Felix] ✅ Domain v1.0 signed (cross-ref BRD + ADR-01 schema)
```

## Step 6 — Bundle (Oliver compile)

Oliver รวม draft ทุก agent เป็น single artifact:

→ `outputs/01-coop-design.md` (integrated bundle structure):

```markdown
# Coop Design — [feature]

## 1. Business (Bella)
[BRD + Stories + AC + Process + RTM]

## 2. Architecture (Sara)
[C4 + Stack + NFR + ADR + Threat + DR + Risk]

## 3. UX/UI (Uma) — conditional
[Persona + Flow + Wireframe + Tokens + a11y + State Inventory]

## 4. Domain (Felix/Iris/Tara/Elena/Sam/Brooke/Emma) — conditional
[Schema + Lifecycle + Business Rule + Compliance + Citations]

## 5. Cross-Validation Matrix
| From → To | Reference | Status |
| BRD FR-1 → ADR-02 | tech stack support | ✅ |
| ADR-03 → Wireframe tenant switcher | multi-tenant UI | ✅ |
| Felix rule → BRD FR-7 | KYC step | ✅ |

## 6. Open Questions (escalated to user)
[any unresolved item]

## 7. Sign-off
- Bella: ✅
- Sara: ✅
- Uma: ✅ (or N/A)
- [Domain]: ✅ (or N/A)
- Oliver Coop checkpoint: ✅
```

## Step 7 — Phase 1 Exit Gate (Oliver)

```
⏸️ Gate: pre-coop-design-exit
✅ Roster ack: Bella + Sara + Uma + Felix
✅ Integrated bundle: outputs/01-coop-design.md
✅ Cross-validation matrix complete, no unresolved conflict
✅ Open questions escalated (if any)
→ Unlock Phase 2 (Dave implement)
```

Next: `/implement` (Phase 2) — Dave ใช้ bundle เป็น spec single source of truth

## ⚠️ Rules

1. 🔴 v2.7 — **ห้าม serialize** (ห้าม Bella เสร็จก่อนแล้วโยน Sara). ทุกคน parallel ตั้งแต่ Step 2 Draft
2. 🔴 v2.7 — **บังคับ mid-checkpoint cross-read** (Step 3). ขาด = silo pattern = block
3. 🔴 v2.7 — **บังคับ sign-off ครบทุก roster participant** (Step 5). ขาด ack คนใดคนหนึ่ง = ขัด pre-coop-design-exit gate
4. ห้าม skip domain expert ถ้า touch business rule
5. ห้าม skip Uma ถ้า touch frontend/UI (pre-implement-ui gate)
6. Domain ไม่ fit expert → Oliver หยุดถาม user
7. ห้าม implement code ใน command นี้ (ใช้ `/implement` = Phase 2)
8. ภาษาไทย
