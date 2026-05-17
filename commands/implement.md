---
description: "[shode-house] Implement (Dave) + UI Check (Uma) + Code Review (Chris ∥ Quinn) + Triage — v2.8 Smart Coop Phase 2-4"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: [bd-id]
---

Implement: **$ARGUMENTS** (bd-id หรือ feature description)

## Pipeline (Phase 2 → 3a → 3b → 4)

### 0. UI Precondition Check (Oliver — 🔴 v2.6.1)

ก่อน delegate ไป Dave — Oliver ตรวจ:
- bd issue มี SPEC-<bd-id>.md ที่ Phase 1b ส่งมาไหม?
- Feature touch frontend? → บังคับมี Uma artifact (Figma + tokens + a11y + baseline + Uma's AC)
- ไม่มี Uma artifact + frontend = **STOP**, route to `/design-system` Phase 1b
- Pure backend? → proceed without Uma

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

### 4. Smoke Test (Dave)

- Start server + curl happy path
- Lint + type + unit pass
- `bd update <id> --notes "Phase 2 done: smoke ok, files: [...]"`

⏸️ **Gate: pre-ui-check** — lint clean + unit green + smoke pass → unlock Phase 3a

### 5. UI Check (Uma — Phase 3a, conditional — sequential gate 🔴 v2.8)

ถ้า frontend changed:
- Uma reads Dave's PR + Phase 1b baseline + Uma's own AC
- Screenshot ตอนนี้ vs baseline (Chromatic/Percy หรือ manual)
- Manual a11y: keyboard, screen reader (VoiceOver/NVDA spot check), focus order, reduced motion, contrast
- Component state validation: ตรวจ default/hover/active/focus/disabled/loading/error/empty ครบไหม
- Content design: microcopy, error message, empty state copy ตรง spec
- Verdict: **PASS** → unlock Phase 3b ∥ **FAIL** → loop Phase 2 (Dave fix) หรือ Phase 1b (Uma redesign baseline)

```bash
# Uma post finding:
bd update <id> --notes "Phase 3a Uma POST: PASS (visual diff 0.05%, a11y 0 critical, AC 7/7)"
# หรือ
bd update <id> --notes "Phase 3a Uma POST: FAIL — visual diff 2.3% (button spacing off-spec), loop Phase 2"
```

⏸️ **Gate: pre-code-review** — Uma POST PASS → unlock Phase 3b. ถ้า pure backend skip Phase 3a → ผ่าน gate อัตโนมัติ

### 6. Code Review (Chris ∥ Quinn — Phase 3b, TRUE parallel 🔴 v2.8)

Chris + Quinn ทำงานพร้อมกัน (no order, different scope):

**Chris (7-dim + unit + mutation)**:
- Correctness / Security (OWASP) / SOLID / Performance / Maintainability / Testing / Observability
- Unit test gap + mutation kill rate ≥ 70%
- Property-based test (Hypothesis/fast-check) for invariant
- Critical/High → block

**Quinn (integration + E2E + contract + load + a11y axe)**:
- Integration (Testcontainers + real DB/cache)
- E2E (Playwright user journey, critical path 100%)
- Contract (Pact + Schemathesis)
- Load smoke (k6 — p95 < SLO, error < 0.1%)
- a11y axe automation (WCAG AA critical=0)
- Pen test (OWASP ASVS)

**Domain Expert validate** (conditional — parallel กับ Chris+Quinn):
- payment/ledger → Felix (regulation cite verify, money rule)
- accounting/inventory → Elena
- trading → Tara
- insurance → Iris
- booking → Brooke
- ecommerce → Emma
- SAP → Sam

Output: `outputs/REVIEW-<bd-id>.md` (Chris finding + Quinn finding + Domain finding merged)

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

⏸️ **Gate: pre-loop-exit** — clean + iter ≤ 3 → queue for Phase 5 (sprint-end deploy)

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
