---
description: "[shode-house] Implement (Dave) + UI Check (Uma) + Code Review (Chris ∥ Quinn) + Triage — v2.8 Smart Coop Phase 2-4"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[bd-id]"
---

Implement: **$ARGUMENTS** (bd-id หรือ feature description)

## Pipeline (Phase 2 → 3a → 3b → 4)

### 0. UI Precondition Check (Oliver — 🔴 v2.6.1 + v2.8.1 auto-trigger)

ก่อน delegate ไป Dave — Oliver ตรวจ:

**🔴 v2.8.1 — Auto-trigger Phase 3a detection (บังคับ Bash check)**:
```bash
# Detect frontend trigger จาก spec scope (Dave's planned Files):
echo "$DAVE_PLANNED_FILES" | grep -qE "\.(vue|tsx|jsx|svelte|html|css|scss|sass|less)$|/(frontend|components|pages|views|app)/" \
  && export FRONTEND_TRIGGER=1 \
  || export FRONTEND_TRIGGER=0
```

- ถ้า `FRONTEND_TRIGGER=1`:
  - bd issue มี SPEC-<bd-id>.md ที่ Phase 1b ส่งมาไหม?
  - มี Uma artifact (Figma + tokens + a11y + baseline + Uma's AC) ครบไหม?
  - ไม่มี = **STOP**, route to `/design-system` Phase 1b
  - **🔴 v2.8.1 — บังคับ invoke Uma POST (Phase 3a) ก่อน Chris+Quinn** — ห้าม Oliver "decide skip เพราะ minor change"; auto-detected = auto-required
- ถ้า `FRONTEND_TRIGGER=0` (pure backend/API/data/CLI): proceed without Uma; Phase 3a skip ผ่าน gate อัตโนมัติ

**Detection หลังจาก Dave Phase 2 done** (re-check ก่อน Step 5):
```bash
# git diff ของ Dave's commit → frontend triggered ไหม
git diff --name-only HEAD~1 HEAD | grep -qE "\.(vue|tsx|jsx|svelte|html|css|scss|sass|less)$|/(frontend|components|pages|views|app)/" \
  && echo "FRONTEND CHANGED — Phase 3a Uma POST MANDATORY" \
  || echo "no frontend — skip Phase 3a"
```

ถ้า frontend detected แต่ Phase 1b ไม่มี Uma artifact = Dave touch UI โดยไม่ผ่าน design = scope drift = STOP + escalate

### 1. Context (Dave)

- `bd show <id>` + read `outputs/SPEC-<bd-id>.md`
- Identify section relevant (BRD section + ADR section + Uma's AC + Domain rule)
- Read convention code existing (`Glob` + `Grep` similar pattern)
- ปรึกษา Sara/Bella/Domain ถ้า spec ไม่ชัด — กลับ Phase 1a/1b

### 2. Plan (Dave present)

- Files ที่จะแตะ (Scope Contract format: IN/OUT/Files/Stop/Echo)
- Dependencies ใหม่
- Migration plan (ถ้า schema change)
- Open questions
- → user approve

### 3. Implement (Dave — Phase 2)

- Follow project convention + Uma's wireframe + design tokens (ห้าม hardcode)
- Type-safe, error handling, structured logging
- Money → Decimal/integer (ห้าม float)
- Feature flag (ถ้า risky)
- Observability: log + metric (RED) + trace
- Parallel Dave#1/#2 ถ้า truly independent files (Scope Contract enforce no overlap)
- Commit: Conventional Commits + bd ref (`feat(...): ... [bd:42]`)

### 4. Smoke Test (Dave) — 🔴 v2.8.1 screenshot mandatory ถ้า frontend

- Start server + curl happy path → paste 200
- Lint + type + unit pass → paste output
- **🔴 v2.8.1 — ถ้า frontend changed (touch *.vue/*.tsx/*.jsx/*.svelte/*.html/css/scss/components/pages/views/frontend/)**:
  ```bash
  # MUST capture screenshot:
  pnpm exec playwright screenshot --viewport-size=1440,900 http://localhost:3000/<route> tests/visual/<feature>-after.png
  pnpm exec playwright screenshot --viewport-size=375,812 http://localhost:3000/<route> tests/visual/<feature>-mobile-after.png
  ls -lh tests/visual/<feature>-*.png    # paste paths
  ```
  ห้าม hand-off Uma POST ถ้าไม่ paste screenshot path — Uma มี baseline แล้ว ต้องการ "after" เพื่อ diff
- `bd update <id> --notes "Phase 2 done: smoke ok, files: [...], screenshot: [paths ถ้า frontend]"`

⏸️ **Gate: pre-ui-check** — lint clean + unit green + smoke pass + screenshot evidence (ถ้า frontend) → unlock Phase 3a

### 5. UI Check (Uma — Phase 3a, sequential gate 🔴 v2.8 + v2.8.1 auto-trigger)

**🔴 v2.8.1 — Auto-trigger** (จาก Step 0 detection): ถ้า frontend changed (git diff match `.vue/.tsx/.jsx/.svelte/.html/.css/.scss` หรือ `frontend/components/pages/views/`) = **MANDATORY**. ห้าม Oliver/Uma "skip เพราะ minor"

Uma เข้า Phase 3a ทำตาม **mandatory Bash invocation pattern** ใน `agents/ux-ui-designer.md` Phase 3a Process (11 steps):
1. Read context (bd show + SPEC-id)
2. Spin up app (docker compose / make dev + curl /health)
3. Capture current screenshot (Playwright Bash)
4. Visual diff (Chromatic / pixel diff Bash)
5. Design adherence (rg hardcoded color + off-grid spacing Bash)
6. a11y axe (axe-cli Bash + jq violations)
7. a11y manual (keyboard + screen reader + paste observations)
8. Contrast verify (wcag-contrast-checker Bash)
9. Component state (Playwright tests/states/ Bash)
10. Content design (manual paste vs spec)
11. AC verification (bullet per AC + evidence path)

**🔴 v2.8.1 — Anti-Puppet UX/UI (meeting skill บังคับ)**: ห้าม claim PASS โดยไม่ paste tool output. Verdict format ดู `agents/ux-ui-designer.md`

Verdict:
- **PASS** → `bd update <id> --notes "Phase 3a Uma POST PASS — evidence: [Chromatic build/N, axe report path, AC bullets]"` → unlock Phase 3b
- **FAIL** → `bd update <id> --notes "Phase 3a FAIL — [specific issues + paths]"` → Triage routing:
  - Implementation gap (Dave ทำผิด wireframe) → loop Phase 2
  - Design baseline ผิด (Uma's own AC ไม่ถูก) → loop Phase 1b

⏸️ **Gate: pre-code-review** — Uma POST PASS → unlock Phase 3b. Pure backend (no frontend trigger) skip Phase 3a → ผ่าน gate อัตโนมัติ

### 6. Code Review (Chris ∥ Quinn — Phase 3b, TRUE parallel 🔴 v2.8)

> 🔴 **v3.1**: ใช้ `review-checklist` skill เป็น source-of-truth. Phase นี้ = invoke skill + ส่ง parallel ไปยัง 3 axes

Chris + Quinn (+ optional Sentinel/Domain Expert) ทำงาน parallel ผ่าน **`review-checklist` skill**:

```bash
[Oliver|state:3b|bd:42] Phase 3b kickoff
- Chris  → 7-dim (Correctness/Security/SOLID/Perf/Maintain/Test/Observ) — see review-checklist § Chris
- Quinn  → integration matrix (6 axes: Integration/E2E/Contract/Load/a11y/Pen) — see review-checklist § Quinn
- Sentinel (conditional, if security trigger) → SAST/SCA/CSP/abuse — see review-checklist § Sentinel
- Domain (conditional, if code touches sensitive area) → see review-checklist § Domain Expert
```

**ทุกคน apply**:
- Severity grading (🔴/🟠/🟡/🔵/💡) — see `review-checklist` § Severity Grading
- bd-native primary, markdown fallback — see `review-checklist` § REVIEW Report Format
- Loop routing recommendation — see `review-checklist` § Loop Routing Recommendation
- Anti-Puppet gate (paste tool output, no "should be fine") — see `review-checklist` § Anti-Puppet Gate

Output: bd notes OR `outputs/REVIEW-<bd-id>.md` (consolidated)

### 7. Triage (Oliver — Phase 4)

```bash
# Oliver decide loop routing:
if any critical/major:
  bd create -t bug --discovered-from=<id> "..."
  # Route loop:
  if finding_type in [code, perf, security_impl, test_coverage]:
    → Phase 2 (Dave fix)
  elif finding_type in [ui, design_adherence, visual_diff, a11y_manual]:
    → Phase 1b (Uma redesign baseline)
  elif finding_type in [spec, ac, regulation, business_rule]:
    → Phase 1a (Bella ∥ Sara revise)
elif any minor:
  bd create -p4 "..." (defer P4 backlog)
  → bd close <id>
else: # clean
  bd close <id>

if iter > 3:
  STOP — broadcast "[Oliver] bd-<id> exceeded iter 3 — escalating user"
```

⏸️ **Gate: pre-loop-exit** — clean + iter ≤ 3 → Phase 5 (continuous per-bd deploy or user manual batch — v3.3 no sprint)

## ⚠️ Rules

0. 🔴 v2.6.1 — frontend involved → Uma artifact ต้องมีก่อน Dave start (pre-implement-ui)
1. ต้องมี SPEC-<bd-id>.md → ถ้าไม่มีรัน `/design-system bd-<id>` ก่อน
2. 🔴 v2.8 — **Phase 3a Uma POST = sequential gate** ก่อน Phase 3b. Chris+Quinn ห้าม start ถ้า Uma ยังไม่ approve
3. 🔴 v2.8 — **Phase 3b Chris ∥ Quinn parallel เท่านั้น** (ห้าม Chris → Quinn serialize)
4. 🔴 v2.8 — **Phase 4 Triage routing precise** (code→2, UI→1b, spec→1a) — ห้าม "ผ่านครึ่ง ๆ" ข้าม deploy
5. 🔴 v2.8 — Loop iter ≤ 3 ต่อ bd issue; > 3 → escalate user
6. Chris เขียน unit test + mutation (Dave smoke แล้วเสร็จ)
7. Quinn integration/E2E + contract + load + a11y axe สำหรับ critical path
8. Domain Expert validation บังคับสำหรับ sensitive (parallel ใน Phase 3b)
9. ห้าม merge จน Phase 3a + 3b ผ่าน + Phase 4 clean (pre-loop-exit gate)
10. ภาษาไทย; code ตาม convention
