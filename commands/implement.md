---
description: "[shode-house] Implement feature code (Dave) + Chris review/unit test + Quinn integration"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: [feature description or spec path]
---

Implement: **$ARGUMENTS**

## Pipeline

### 0. UI Precondition Check (Oliver — 🔴 v2.6.1)

ก่อน delegate ไป Dave — Oliver ตรวจ:

- Feature touch frontend/UI/component/page/view/email/dashboard? → **YES**: บังคับมี Uma artifact (Figma frame link + tokens.json + a11y checklist + state inventory + hand-off bundle)
- Pure backend/API/data pipeline/CLI? → **NO Uma needed**, proceed
- กำกวม? → ask user option-style

**ถ้า frontend แต่ไม่มี Uma artifact**:
```
⏸️ Gate: pre-implement-ui
❌ Feature: [feature name] touches frontend
❌ Missing: Uma artifact (Figma + tokens + a11y)
→ STOP Dave; route to Uma หรือ `/design-system` (Step 3.5)
```

ห้าม Dave bypass — Philosophy 1 (NO MAGIC: ห้ามเดา UI) + Philosophy 4 (no scope drift via "ขอวาด UI เอง")

### 1. Context (Dave)
- อ่าน spec/user stories (ถ้ามี path) — ถ้าไม่มี ถาม user
- อ่าน convention โค้ด existing
- ปรึกษา Sara/Bella/Domain Expert ถ้า spec ไม่ชัด

### 2. Plan
Dave present:
- Files ที่จะแตะ
- Dependencies ใหม่
- Migration plan (ถ้า schema change)
- Open questions

→ user approve

### 3. Implement
- Follow project convention
- Type-safe, error handling, structured logging
- Money → Decimal/integer (ห้าม float)
- Feature flag (ถ้า risky)
- Observability: log + metric (RED) + trace
- Commit: Conventional Commits

### 4. Smoke Test
- Start server + curl happy path
- ยืนยันว่าทำงานได้

### 5. Hand-off → 🔎 Phase 3 Coop Review (🔴 v2.7 parallel)

ทุก reviewer ทำงานพร้อมกัน (ห้าม serialize):
- **Chris** → review 7 มิติ + unit test (business/edge/error/boundary) + mutation kill ≥ 70%
- **Quinn** → integration + E2E (critical path) + contract + load smoke + a11y axe-core
- **Uma** (🔴 v2.7 conditional ถ้า frontend) → visual diff vs Figma + design adherence + a11y WCAG AA manual + component state validation
- **Aaron** → env var / Dockerfile / CI ถ้ามีของใหม่

Output รวม: `outputs/03-coop-review.md` (Coop Review report)

### 6. Phase 4 Loop Decision (Oliver — 🔴 v2.7)

หลัง Coop Review report — Oliver decide:
- **All 3 green (Chris ✅ + Quinn ✅ + Uma ✅)** → unlock Phase 5 Deploy via `pre-loop-exit` gate
- **Code-only finding** (bug/perf/security/test gap) → loop กลับ Step 1-4 (Dave fix)
- **Spec/design finding** (BRD/ADR/UX/Domain wrong) → loop กลับ `/design-system` (Phase 1 re-Coop)
- **Iter ≤ 3** — iter 4 = STOP escalate user

### 7. Domain Validation (conditional)
Sensitive feature → **บังคับ** Domain Expert validate (Phase 3 parallel กับ Chris/Quinn/Uma):
- payment/ledger → Felix
- accounting/inventory → Elena
- trading → Tara
- insurance → Iris
- booking → Brooke
- ecommerce → Emma

## ⚠️ Rules

0. 🔴 v2.6.1 — ถ้า frontend involved → **Uma artifact ต้องมีก่อน Dave start** (pre-implement-ui gate). Bypass = scope drift = STOP. ไม่มี artifact → `/design-system` Step 3.5 หรือ delegate Uma agent
1. ต้องมี spec ก่อน → ถ้าไม่มีรัน `/spec-only` หรือ `/design-system` (= Phase 1 Coop bundle)
2. Chris เขียน unit test + mutation (Dave smoke test ok)
3. Quinn integration/E2E + contract + load + a11y axe สำหรับ critical path
4. 🔴 v2.7 — **Uma joins Coop Review (Step 5)** ถ้า frontend changed (visual diff + design adherence + a11y manual)
5. Domain Expert validation บังคับสำหรับ sensitive (parallel ใน Phase 3)
6. 🔴 v2.7 — ห้าม merge จน Chris + Quinn + Uma* approve (pre-loop-exit gate); review fail → Step 6 Loop Decision
7. ห้าม serialize Coop Review (ห้าม Chris เสร็จก่อนแล้วเริ่ม Quinn) — Phase 3 ทุก reviewer parallel
8. ภาษาไทย; code ตาม convention
