---
description: "[shode-house] Implement (developer) + UI Check (ux-ui-designer) + review axes + Triage — Smart Coop Phase 2-4"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash, Skill, AskUserQuestion
argument-hint: "[bd-id]"
---

Implement: **$ARGUMENTS** (bd-id หรือ feature description)

Use the harness's confirmed record homes, available tools and verification tier.
The full pipeline below applies when that tier requires it; retain triggered experts
and their knowledge. Reuse approved design and implementation authority. Beads,
shell and UI-tool examples are not prerequisites or permission to commit/deploy.

Router style not active in this session → report `BLOCKED: team execution needs the router style (Claude Code)`; do not read the style file to act as the router.

## Completion

Implement the authorized scope; continue until the changed behaviour is implemented and affected validation passes. Resolve ordinary implementation details from repository evidence; ask only per `shode-house-discipline` § Ask vs derive;
continue-until · stop-when · validation scope → `shode-house-deliverable` § Completion; finishing without intervention is not closing: only the router closes, then reads back (Rule 10).

## Pipeline (Phase 2 → 3a → 3b → 4)

### 0. UI Precondition Check (router — 🔴 auto-trigger)

ก่อน delegate ไป developer — the router ตรวจ:

**🔴 Auto-trigger Phase 3a detection (บังคับ Bash check)**:
```bash
# Detect frontend trigger จาก spec scope (developer's planned Files):
echo "$DEV_PLANNED_FILES" | grep -qE "\.(vue|tsx|jsx|svelte|html|css|scss|sass|less)$|/(frontend|components|pages|views|app)/" \
  && export FRONTEND_TRIGGER=1 \
  || export FRONTEND_TRIGGER=0
```

- ถ้า `FRONTEND_TRIGGER=1`:
  - task มี SPEC-<bd-id>.md ที่ Phase 1b ส่งมาไหม?
  - มี ux-ui-designer artifact (Figma + tokens + a11y + baseline + ux-ui-designer's AC) ครบไหม?
  - ไม่มี = **STOP**, route to `/design-system` Phase 1b
  - **🔴 บังคับ invoke ux-ui-designer POST (Phase 3a) ก่อน Phase 3b reviewers** — ห้าม router "decide skip เพราะ minor change"; auto-detected = auto-required
- ถ้า `FRONTEND_TRIGGER=0` (pure backend/API/data/CLI): proceed without ux-ui-designer; Phase 3a skip ผ่าน gate อัตโนมัติ

**Detection หลังจาก developer Phase 2 done** (re-check ก่อน Step 5):
```bash
# TASK_BASE = verified revision recorded before this task; include current task edits
git diff --name-only "$TASK_BASE" --
```

Inspect the successful output for the frontend patterns above. A missing base or
failed diff is unresolved detection, never evidence that frontend was unchanged.
Also inspect task-owned untracked files. In a dirty checkout, attribute changes to
this task using its recorded scope; do not count unrelated user edits as developer's work.

ถ้า frontend detected แต่ Phase 1b ไม่มี ux-ui-designer artifact = developer touch UI โดยไม่ผ่าน design = scope drift = STOP + escalate

### 1. Context (developer)

- Read the task in the confirmed tracker + `outputs/SPEC-<bd-id>.md`
- ปรึกษา solution-architect/business-analyst/domain ถ้า spec ไม่ชัด — กลับ Phase 1a/1b

### 2. Plan (developer present)

- Files ที่จะแตะ (Scope Contract format: IN/OUT/Files/Stop/Echo)
- Dependencies ใหม่
- Migration plan (ถ้า schema change)
- Open questions
- → the router ตรวจเทียบสิทธิ์กับ scope เดิม; ถ้า user สั่ง implement แล้วให้ดำเนินต่อ ไม่ขออนุมัติ file plan ซ้ำ ขอ user เฉพาะ policy, scope ใหม่ หรือผลกระทบที่ยังไม่อนุญาต

### 3. Implement (developer — Phase 2)

- Follow project convention + ux-ui-designer's wireframe + design tokens (ห้าม hardcode)
- Money → Decimal/integer (ห้าม float)
- Parallel developer#1/#2 ถ้า truly independent files (Scope Contract enforce no overlap)
- Commit only when authorized; if committing, use Conventional Commits + task ref (`feat(...): ... [bd:42]`). Otherwise record the source revision and uncommitted diff/artifact evidence.

### 4. Smoke Test (developer) — 🔴 screenshot mandatory ถ้า frontend

- Start server + curl happy path → paste 200
- Lint + type + unit pass → paste output
- **🔴 ถ้า frontend changed (touch *.vue/*.tsx/*.jsx/*.svelte/*.html/css/scss/components/pages/views/frontend/)**:
  ```bash
  # MUST capture screenshot:
  pnpm exec playwright screenshot --viewport-size=1440,900 http://localhost:3000/<route> tests/visual/<feature>-after.png
  pnpm exec playwright screenshot --viewport-size=375,812 http://localhost:3000/<route> tests/visual/<feature>-mobile-after.png
  ls -lh tests/visual/<feature>-*.png    # paste paths
  ```
  ห้าม hand-off ux-ui-designer POST ถ้าไม่ paste screenshot path — ux-ui-designer มี baseline แล้ว ต้องการ "after" เพื่อ diff
- Task note: "Phase 2 done: smoke ok, files: [...], screenshot: [paths ถ้า frontend]"

⏸️ **Gate: pre-ui-check** — lint clean + unit green + smoke pass + screenshot evidence (ถ้า frontend) → unlock Phase 3a

### 5. UI Check (ux-ui-designer — Phase 3a, sequential gate 🔴 auto-trigger)

**🔴 Auto-trigger** (จาก Step 0 detection): ถ้า frontend changed (git diff match `.vue/.tsx/.jsx/.svelte/.html/.css/.scss` หรือ `frontend/components/pages/views/`) = **MANDATORY**. ห้าม router/ux-ui-designer "skip เพราะ minor"

ux-ui-designer เข้า Phase 3a ทำตาม `references/runbooks/ux-ui-designer-phase-3a.md` § Process (11 steps). ux-ui-designer has no Bash: each tool step is a design-run request (catalogue template + typed params) that the router runs per the design-run order in `output-styles/shode-house.md` § Delegation:
1. Read context (task + SPEC-id)
2. App reachable at a loopback URL (Playwright `webServer` templates start it; otherwise the router asks developer or devops-engineer)
3. Capture current screenshot (`ui-capture` / `ui-screenshot`)
4. Visual diff (`visual-diff`; Chromatic is not in the catalogue)
5. Design adherence (Grep hardcoded color + off-grid spacing, read-only)
6. a11y axe (`axe-scan` report: violations by id/impact)
7. a11y manual (keyboard + screen reader + paste observations)
8. Contrast verify (`contrast-pair`)
9. Component state (`state-tests`)
10. Content design (manual paste vs spec)
11. AC verification (bullet per AC + evidence path)

**🔴 Anti-Puppet UX/UI (บังคับ — `shode-house-deliverable` § Anti-Puppet Rule)**: ห้าม claim PASS โดยไม่ paste tool output. Verdict format: `references/runbooks/ux-ui-designer-phase-3a.md` § Verdict format

Verdict:
- **PASS** → task note "Phase 3a ux-ui-designer POST PASS — evidence: [visual-diff run id, axe report path, AC bullets]" → unlock Phase 3b
- **FAIL** → task note "Phase 3a FAIL — [specific issues + paths]" → Triage routing:
  - Implementation gap (developer ทำผิด wireframe) → loop Phase 2
  - Design baseline ผิด (ux-ui-designer's own AC ไม่ถูก) → loop Phase 1b

⏸️ **Gate: pre-code-review** — ux-ui-designer POST PASS → unlock Phase 3b. Pure backend (no frontend trigger) skip Phase 3a → ผ่าน gate อัตโนมัติ

### 6. Code Review (Phase 3b — review axes, one fresh spawn each)

> Method = `shode-house:review-checklist` (`Skill` tool — อยู่ใน allowed-tools แล้ว). Axis plan = `output-styles/shode-house.md` § Review card:
> record it as the `[REVIEW DISPATCH CARD]`, then dispatch every DISPATCH axis only after the developer has returned;
> spec is always DISPATCH; runtime, security and domain rules → `commands/review.md` § Step 1 (rules 1-2)

Kickoff: pin fixed point ก่อน fan-out (`skills/discipline/review-checklist/intake.md`); method per axis = the 6 Kickoff lines of
`commands/review.md` § Step 1 (standards, runtime, security, domain, ui, spec). Here: runtime
(`shode-house:qa-engineer`, Integration/E2E/Contract/Load/a11y/Pen) is DISPATCH when review.md rule 1 says so — harness
risk tier, process/network/storage boundary or project requirements; ui reuses the Phase 3a verdict when it covers the
current revision and is dispatched again only if UI files changed after 3a.
Spec axis (`shode-house:business-analyst`) — sub-agent แยก ห้ามรวม context กับ standards: (a) requirement ที่ขาด/ทำครึ่ง (b) scope creep (c) implement ผิด
— `skills/discipline/review-checklist/spec-axis.md`; input = diff range ที่ pin ไว้ + `outputs/SPEC-<bd-id>.md` (ส่ง path ไม่ส่งเนื้อหา);
ไม่มี spec → `BLOCKED: no-spec` ("no spec available") พร้อม sources ที่ตรวจแล้ว = missing acceptance ที่ router relay ให้ user ห้าม pass เงียบ

🔴 **aggregate ห้าม merge/rerank ข้ามแกน** — รายงานแยกหัวข้อ `## Standards` / `## Spec` + ปิดท้าย 1 บรรทัดบอกจำนวน finding และตัวแย่สุด **ในแต่ละแกน**

**ทุกคน apply**:
- Severity grading (🔴/🟠/🟡/🔵/💡) — see `review-checklist` § Severity Grading
- bd-native primary, markdown fallback — see `skills/discipline/review-checklist/report-format.md`
- Loop routing recommendation — see `skills/discipline/review-checklist/report-format.md` § Loop Routing
- Anti-Puppet gate (paste tool output, no "should be fine") — see `review-checklist` § Gate ที่ทุกแกนต้องผ่าน

Output: task notes OR `outputs/REVIEW-<bd-id>.md` (consolidated)

### 7. Triage (router — Phase 4)

```bash
# router decides loop routing:
if any critical/major:
  create bug task linked discovered-from <id>   # confirmed tracker; Markdown fallback
  # Route loop:
  if finding_type in [code, perf, security_impl, test_coverage]:
    → Phase 2 (developer fix)
  elif finding_type in [ui, design_adherence, visual_diff, a11y_manual]:
    → Phase 1b (ux-ui-designer redesign baseline)
  elif finding_type in [spec, ac, regulation, business_rule]:
    → Phase 1a (business-analyst ∥ solution-architect revise)
elif any minor:
  create low-priority task (defer P4 backlog)
  → close <id>, reason "minor deferred <source_revision_and_diff_evidence> <test_result>" # when closure authorized
else: # clean
  close <id>, reason "clean <source_revision_and_diff_evidence> <test_result>" # when closure authorized

# 🔴 M8 Close-on-Done Guard (บังคับหลังทุก close):
read back <id>   # ต้องอ่านได้ว่า CLOSED แล้ว paste output — ห้าม claim "ปิดแล้ว" ลอย ๆ

if iter > 3:
  STOP — broadcast "[router] bd-<id> exceeded iter 3 — escalating user"
```

⏸️ **Gate: pre-loop-exit** — clean + iter ≤ 3 → Phase 5 (continuous per-bd deploy or user manual batch — v3.3 no sprint)

## ⚠️ Rules

0. 🔴 frontend involved → ux-ui-designer artifact ต้องมีก่อน developer start (pre-implement-ui)
1. ต้องมี SPEC-<bd-id>.md → ถ้าไม่มีรัน `/design-system bd-<id>` ก่อน
2. 🔴 **Phase 3a ux-ui-designer POST = sequential gate** ก่อน Phase 3b. Phase 3b reviewers ห้าม start ถ้า ux-ui-designer ยังไม่ approve
3. **Phase 3b reviewers คนละ reviewer context** (fresh spawn per axis) — parallel เมื่อทำได้; sequential ได้แต่ห้ามใช้ self-review แทน independent verdict
4. 🔴 **Phase 4 Triage routing precise** (code→2, UI→1b, spec→1a) — ห้าม "ผ่านครึ่ง ๆ" ข้าม deploy
5. 🔴 Loop iter ≤ 3 ต่อ task; > 3 → escalate user
6. code-reviewer เขียน unit test + mutation (developer smoke แล้วเสร็จ)
7. qa-engineer integration/E2E + contract + load + a11y axe สำหรับ critical path
8. domain type validation บังคับสำหรับ sensitive (parallel ใน Phase 3b)
9. ห้าม merge จน Phase 3a + 3b ผ่าน + Phase 4 clean (pre-loop-exit gate)
10. 🔴 **Close-on-Done (M8)**: เมื่อ closure อยู่ใน authority ให้บันทึก verdict + source revision/diff evidence + test result แล้ว read back สถานะจริง. Commit/merge เป็นเงื่อนไขเฉพาะเมื่อ acceptance ต้องการและได้รับ authorization; ห้ามสร้าง commit เพื่อให้ template ครบ
11. Batch หลาย bd อิสระในรอบเดียว → ใช้ `shode-house:drain` skill (worktree fan-out + serial cherry-pick + close-on-done) ไม่ใช่ /implement ซ้ำ ๆ
12. ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim
