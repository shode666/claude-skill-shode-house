---
description: "[shode-house] Smart Spec pipeline (Phase 1a Bella + Sara parallel; Phase 1b Uma + Domain conditional) — v2.8 Smart Coop"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: [bd-id | system description]
---

📝 **Spec phase** สำหรับ: **$ARGUMENTS**

> v2.8 Smart Coop: parallel foundation (Bella + Sara) → conditional sequential expand (Uma + Domain). Replaces v2.7 4-way Coop (40% leaner token, no redundant cross-read overhead)

## Step 0 — Triage (Oliver)

- Pick bd issue (`bd show <id>` ถ้า มี argument) หรือสร้างใหม่ (`bd create -t feature -p1 "..."`)
- Trigger detection:
  - **frontend trigger**? (touch UI/component/page/view/email/dashboard) → Uma เข้า Phase 1b
  - **business-rule trigger**? (money/policy/matching/booking/inventory/regulation) → Domain Expert เข้า Phase 1b
  - Pure infra/CLI/library? → skip 1b ทั้งคู่
- Present roster + estimated effort → user approve

## Step 1 — Phase 1a Foundation (Bella ∥ Sara — TRUE parallel)

Oliver kickoff broadcast:
```
[Oliver|state:1a|bd:42] Phase 1a start
- Roster: Bella + Sara (parallel, independent scope)
- bd: bd-42
- Budget: [T-shirt]
- Light cross-read at end (no mid-checkpoint)
```

### Bella draft (parallel กับ Sara)
- BRD: objective, scope, stakeholder + RACI
- User Stories + AC (Given-When-Then)
- As-is / To-be process (Mermaid)
- Event Storming (ถ้า complex domain)
- RTM (BR → FR → test)
- Assumption + open questions

### Sara draft (parallel กับ Bella)
- C4 Context + Container
- Tech stack + เหตุผล
- NFR table
- ADR candidates (3-5)
- Threat model (STRIDE)
- DR/BCP (RTO/RPO)
- Risk register

### Light cross-read (NOT cross-feedback round — ลด token)
- Bella check: FR ขัด ADR ของ Sara ไหม → ping resolve
- Sara check: ADR support FR ครบไหม → ping resolve
- (1 pass สั้น ๆ, ไม่ใช่ multi-round Coop)

### Sign-off + bd notes (compact)
```bash
bd update <id> --notes "$(cat <<EOF
## Phase 1a — Foundation (Bella + Sara)

### BRD (Bella)
- FR: [count]; Story: [count]; AC: [count]
- Key risk: [1-2 line]
- Open Q: [list]

### ADR (Sara)
- Tech stack: [stack]
- ADR-N decisions: [list IDs + 1-line each]
- NFR p95: [target]
- Threat model: [top 3]

### Cross-validation
- FR-N ↔ ADR-M: aligned ✅
- (any unresolved → mark and escalate)
EOF
)"
```

⏸️ **Gate: pre-spec-expand** — Bella+Sara sign-off + no unresolved conflict → unlock Phase 1b

## Step 2 — Phase 1b Conditional Expand (Sequential — read 1a baseline)

### Uma (ถ้า frontend trigger)
Uma reads `bd show <id>` (Phase 1a notes) → produces:
- Persona + JTBD + journey map (ถ้า new domain) — link Bella research
- IA + user flow (happy + edge + error) — Mermaid
- Wireframe low-fi → mid-fi (Figma frame link + frame ID)
- Design tokens (W3C DTCG primitive → semantic → component) → `tokens.json`
- a11y checklist (WCAG 2.1/2.2 AA)
- Component state inventory: default/hover/active/focus/disabled/loading/error/empty
- **Baseline screenshot** ของ current UI (สำหรับ Phase 3a diff)
- **Acceptance criteria จาก UX angle** (Uma's own AC ที่ Phase 3a verify)
- Hand-off bundle to Dave

### Domain Expert (ถ้า business-rule trigger)
Domain reads `bd show <id>` (Phase 1a notes) → produces:
- Schema + ER diagram (ถ้า data change)
- State machine / lifecycle (ถ้า workflow change)
- Business rule + edge case
- Compliance note **with Domain Evidence Protocol citation** (e.g., "PCI-DSS v4.0 Req 3.5.1")
- ถ้า rule ขัด BRD ของ Bella → ping resolve ก่อน sign-off

### Bundle → outputs/SPEC-<bd-id>.md
```markdown
# SPEC: bd-<id> — [feature]

## 1. Business (Bella, from 1a)
[FR + Stories + AC + Process + RTM compact]

## 2. Architecture (Sara, from 1a)
[Stack + ADR + NFR + Threat + DR + Risk compact]

## 3. UX/UI (Uma, from 1b) — conditional
[Persona + Flow + Wireframe + Tokens + a11y + State Inventory + Baseline + Uma's AC]

## 4. Domain (Felix/Iris/Tara/Elena/Sam/Brooke/Emma, from 1b) — conditional
[Schema + Lifecycle + Business Rule + Compliance + Citations]

## 5. Sign-off
- Bella: ✅
- Sara: ✅
- Uma: ✅ (or N/A)
- [Domain]: ✅ (or N/A)
- Oliver gate pre-spec-expand: ✅
```

## Step 3 — Phase 1b Exit Gate (Oliver)

```
⏸️ Gate: pre-implement-ui (ถ้า frontend)
✅ Uma artifact: Figma frame link + tokens.json + a11y checklist + state inventory
✅ Uma's AC documented
✅ Domain (ถ้า trigger): regulation cite + business rule signed
✅ outputs/SPEC-<bd-id>.md saved
→ Unlock Phase 2 — call `/implement bd-<id>`
```

Next: `/implement bd-<id>` (Phase 2)

## ⚠️ Rules

1. 🔴 v2.8 — **Phase 1a parallel เท่านั้น** (ห้าม Bella → Sara serialize; ห้าม mid-checkpoint cross-read หนัก)
2. 🔴 v2.8 — **Phase 1b sequential เท่านั้น** (Uma + Domain ต้องอ่าน 1a sign-off ก่อน start)
3. 🔴 v2.8 — **บังคับ Uma's own AC** ใน 1b (Phase 3a Uma POST จะ verify AC นี้)
4. 🔴 v2.8 — **บังคับ baseline screenshot** ใน 1b (สำหรับ visual diff Phase 3a)
5. ห้าม skip Uma ถ้า touch frontend (pre-implement-ui gate block)
6. ห้าม skip Domain ถ้า touch business rule (regulation/money rule risk)
7. ห้าม implement code (ใช้ `/implement`)
8. ภาษาไทย
