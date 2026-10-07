---
name: smart-coop
description: Reference (lazy-load) ของ `shode-house-workflow` — Smart Coop pattern เต็ม, lifecycle hooks, approval gates, state persistence. โหลดเมื่อจะรัน pipeline จริงเท่านั้น
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-workflow/smart-coop.md
WHEN: pipeline_kickoff OR phase_transition
OWNER: router
REQUIRED-BEFORE: phase_dispatch
```

# Smart Coop Pattern — reference เต็ม (lazy-load)

**Contents**

  - [Parallel-vs-Sequential Matrix](#parallel-vs-sequential-matrix)
  - [Phase 1a Pattern (Parallel Foundation)](#phase-1a-pattern-parallel-foundation)
  - [Phase 1b Pattern (Sequential Expand)](#phase-1b-pattern-sequential-expand)
  - [Phase 3a Pattern (Sequential Gate)](#phase-3a-pattern-sequential-gate)
  - [Phase 3b Pattern (Parallel Review)](#phase-3b-pattern-parallel-review)
  - [❌ Anti-pattern (จะถูก block)](#-anti-pattern-จะถูก-block)
  - [✅ Correct pattern](#-correct-pattern)
  - [🗂️ State persistence (pure JSON, no script)](#️-state-persistence-pure-json-no-script)
  - [🪝 Lifecycle conditions (per phase — automation only when authorized)](#-lifecycle-conditions-per-phase--automation-only-when-authorized)
  - [📋 Phase 0 scope-clarification flow (when SME flags ambiguity)](#-phase-0-scope-clarification-flow-when-sme-flags-ambiguity)
  - [📝 Prompt Template Substitution (commands convention)](#-prompt-template-substitution-commands-convention)
  - [Scope Contract enforcement (router)](#scope-contract-enforcement-router)
  - [Loop with Exit (developer/qa-engineer)](#loop-with-exit-developerqa-engineer)
  - [Approval Gates](#approval-gates)
  - [Worktree Isolation (parallel-safe — devops-engineer pattern)](#worktree-isolation-parallel-safe--devops-engineer-pattern)
  - [Workflow as Markdown](#workflow-as-markdown)
- [🧵 Tracker options](#-tracker-options)

> แยกออกจาก `SKILL.md` ใน v3.12: เนื้อหานี้ = 61% ของ skill ทั้งไฟล์ แต่ใช้เฉพาะตอน **รัน pipeline จริง**
> **โหลดไฟล์นี้เมื่อ**: kickoff pipeline · phase transition · ตั้ง approval gate · เขียน/อ่าน `state.json` · devops-engineer ตั้ง lifecycle hook
> Handoff Contract ไม่อยู่ที่นี่ — อยู่ใน `shode-house-discipline` (ทุก agent ต้องรู้ ไม่ใช่แค่ตอนรัน pipeline)

> Applicability: use the harness risk tier and triggered roles. UI-only phases/gates are not applicable to pure backend changes; record why. Parallel means optional concurrency between independent actors, subject to host capacity; separate sequential reviewers are valid. Beads/output paths below are examples within the confirmed record home, not a tracker migration requirement.

**Smart Coop ≠ everything parallel.** parallel เฉพาะที่ agent **truly independent** (ไม่มี read dependency); sequential gate ที่มี natural dependency

| Phase | Pattern |
|---|---|
| 1a business-analyst ↔ solution-architect · 3b code-reviewer ↔ qa-engineer · developer#1 ↔ developer#2 (คนละไฟล์) | **Parallel** |
| 1a → 1b · 2 → 3a · 3a → 3b | **Sequential gate** |

**Key rules**: ❌ ไม่มี outer sprint loop · ✅ product-manager OKR + Deploy = continuous per-bd · ✅ per-bd reflect ใน Phase 4 Triage

> ux-ui-designer/Domain consume one approved baseline. UI gates precede downstream review; failures return to the affected phase. Measure token savings, never assume a fixed percentage.

### Parallel-vs-Sequential Matrix

| สถานการณ์ | Pattern | เหตุผล |
|-----------|---------|--------|
| business-analyst ↔ solution-architect (Phase 1a) | **Parallel** | Different scope (BA vs SA), no read dep, align at end |
| business-analyst+solution-architect → ux-ui-designer (Phase 1a → 1b) | **Sequential gate** | ux-ui-designer needs spec context to design |
| business-analyst+solution-architect → Domain (Phase 1a → 1b) | **Sequential gate** | Domain validates spec, not design from scratch |
| Dev → ux-ui-designer POST (Phase 2 → 3a) | **Sequential gate** | UI bug = halt before deeper review |
| ux-ui-designer POST → code-reviewer+qa-engineer (Phase 3a → 3b) | **Sequential gate** | UI passed first, then code/security |
| code-reviewer ↔ qa-engineer (Phase 3b) | **Parallel** | Different scope (static review vs runtime test) |
| developer#1 ↔ developer#2 (Phase 2) | **Parallel** | Different files, no shared state (Scope Contract enforce) |

### Phase 1a Pattern (Parallel Foundation)
```
1. router kick-off: broadcast roster (business-analyst + solution-architect) + bd-id
2. business-analyst + solution-architect draft parallel (independent scopes)
3. Light cross-read at end (NOT mid-checkpoint — too token-heavy):
   - business-analyst check FR ขัด ADR ไหม
   - solution-architect check ADR support FR ครบไหม
4. Sign-off → note on the task record (compact)
```

### Phase 1b Pattern (Sequential Expand)
```
1. router detect: frontend trigger? business-rule trigger?
2. ux-ui-designer (if frontend): read spec → wireframe + tokens + a11y + baseline screenshot
3. Domain (if business rule): read spec → regulation cite + business rule + compliance gap
4. Sign-off → outputs/SPEC-<bd-id>.md integrated
```

### Phase 3a Pattern (Sequential Gate)
```
1. ux-ui-designer read developer's PR + own Phase 1b baseline
2. Screenshot diff (Chromatic/Percy) + manual visual review
3. Verify own accept criteria + a11y manual (keyboard, screen reader, focus)
4. Verdict: PASS → Phase 3b unlocks; FAIL → triage to affected owner/phase (code→developer, design→ux-ui-designer, spec→business-analyst)
```

### Phase 3b Pattern (Parallel Review)
```
1. router kick-off: code-reviewer + qa-engineer parallel (ux-ui-designer POST already passed)
2. code-reviewer: 7-dim review + unit test gaps + mutation kill verify
3. qa-engineer: integration + E2E + contract + load smoke + a11y axe automation
4. Sign-off → outputs/REVIEW-<bd-id>.md (code-reviewer finding + qa-engineer finding merged)
```

### ❌ Anti-pattern (จะถูก block)
- ❌ Phase 1a solution-architect คัดลอกข้อสรุป business-analyst แทนทำ architecture analysis ของตน; sequential คนละ context ทำได้
- ❌ Phase 1b ux-ui-designer start ก่อน 1a sign-off — ux-ui-designer เดา spec
- ❌ Skip ux-ui-designer POST for changed UI; pure backend records Phase 3a not-applicable and proceeds to its required reviews
- ❌ Phase 3b qa-engineer ใช้ verdict code-reviewer แทน integration evidence ของตน; sequential คนละ reviewer ทำได้
- ❌ developer#1 + developer#2 แตะ file เดียวกัน — ต้อง Scope Contract enforce

### ✅ Correct pattern
- ✅ Phase 1a: business-analyst+solution-architect start same kickoff, end with light cross-read (no mid-checkpoint)
- ✅ Phase 1b: ux-ui-designer+Domain read same 1a baseline (1 spec, not 2-3 drafts) → ลด token
- ✅ Phase 3a: ux-ui-designer POST = explicit gate; FAIL = loop ก่อน code-reviewer/qa-engineer เริ่ม
- ✅ Phase 3b: code-reviewer+qa-engineer truly parallel (no order dep)

### 🗂️ State persistence (pure JSON, no script)
router maintain checkpoint ใน canonical record ของ project ตาม `harness.md`; ไม่สร้าง state อีกชุดหากมี record ที่ครอบคลุมอยู่แล้ว. JSON ต่อไปนี้เป็นทางเลือก ไม่ใช่ runner prerequisite.
**Required meaning**: task ID, engagement/scope, current phase/iteration, phase status/owners/artifacts/revisions, findings, open questions, approvals, UNKNOWN operations และ next action. Markdown/Jira links ใช้แทน JSON fields ได้
**Phase status enum**: `pending | in_progress | conditional_pass | passed | failed | skipped`
**router bootstrap**: อ่าน current record + artifact revisions ก่อน resume; unresolved at the third review/fix iteration → checkpoint and escalate. ห้าม advance เมื่อ required evidence/owner ขาด. `conditional_pass` ไม่ปลด blocker ที่ยัง unresolved. Prompt check ไม่ใช่ deterministic runtime enforcement

### 🪝 Lifecycle conditions (per phase — automation only when authorized)

แต่ละ phase มี pre/post hook สำหรับ automated check:

### 📋 Phase 0 scope-clarification flow (when SME flags ambiguity)

When Domain SME (fintech-expert/insurance-expert/sap-expert/trading-expert/erp-expert/booking-expert/ecommerce-expert) flags scope gap in Phase 0:
1. product-manager state CONDITIONAL PASS (not full PASS) — list clarification questions verbatim from SME
2. **router user-question relay** (G10 — explicit packaging, ห้าม invisible):
   - router create `outputs/<bd>/05-router-user-clarify.md`
   - Format: friendly preamble + numbered questions + grouping by SME + explicit "USER ACTION REQUIRED"
   - 🔴 **subagent เรียก `AskUserQuestion` ไม่ได้** (Claude Code: tool นี้ยังไม่รองรับ agent ที่ spawn ผ่าน Task) —
     Any specialist needing user input returns a question bundle to the router, which remains the main session; never spawn a router subagent:
     ```
     subagent  → return { questions[], options[], recommended } + path ของไฟล์ clarify
     main session (command) → เรียก AskUserQuestion (≤ 4 ข้อ) หรือ post markdown + สรุปในแชท (> 4 ข้อ)
                            → เขียนคำตอบกลับ tracker (task note) แล้วส่ง path ให้ subagent รอบถัดไป
     ```
     The router uses the main session's actual popup tool when available, otherwise Markdown. Host limits determine question batch size; the Claude example is not a portable API.
3. **Block Phase 1a** until user response (M2 classify = `quest`, NOT M5 — no spec exists yet)
4. **Clarification round cap** (G11 — max 2 rounds):
   - Round 1: initial SME questions to user
   - Round 2: ถ้า user answer still ambiguous → re-package + ask narrower
   - Round 3 (= 3rd attempt) → **STOP, escalate user**: "scope ambiguity not resolvable via clarification — recommend (a) defer feature, (b) descope, or (c) workshop session"
5. User response → product-manager re-issue Phase 0 final → business-analyst incorporate into BRD scope
6. Then Phase 1a kickoff

ห้าม proceed Phase 1a โดย product-manager guess scope answer เอง (sycophancy + anchoring risk).
ห้าม router relay raw SME questions ลอย ๆ โดยไม่ package — user เห็น noise (G10).
ห้ามวนถาม > 2 rounds — escalate user เลือก descope/workshop (G11).

**Grouped by phase (v3.3 PEV loop per bd)**:

| Phase | Actor | Pre-hook | Post-hook |
|-------|-------|----------|-----------|
| **Pick bd** | router | ready (unblocked) task exists in the confirmed tracker | task claimed in the tracker |
| **Phase 0 Discover** (opt — new initiative) | product-manager + Domain SME (dispatched separately, no product-manager role-play) | opportunity flagged | OKR + RICE + kill criteria → `outputs/opportunity-<feature>.md`. **Conditional PASS** if Domain SME flags scope ambiguity → escalate user clarify, block Phase 1a (per § Phase 0 scope-clarify flow) |
| **Phase 1a Foundation** | business-analyst ∥ solution-architect | bd issue context + CLAUDE.md loaded | BRD + ADR drafts done, light cross-read pass, task note posted |
| **Phase 1b Expand** | ux-ui-designer + Domain (conditional) | 1a sign-off + frontend/business-rule trigger detected | ux-ui-designer: wireframe + tokens + a11y baseline; Domain: regulation cite + rule. Integrated `outputs/SPEC-<bd-id>.md` saved |
| **Phase 1c Threat Model** (conditional) | security-engineer | auth/session/PII/money/external integration/webhook/file upload/AI agent trigger (canonical list → SKILL.md § Phase 1c; "low risk" ไม่ waive) | STRIDE + abuse case + security AC injected to 1a |
| **Phase 2 Implement** | developer | Scope Contract posted, verified write isolation; UI artifact required only for UI work | lint + type + unit pass, smoke green, Scope Contract closed |
| **Phase 3a UI Check** | ux-ui-designer (conditional) | implement done + frontend changed | screenshot diff approved + a11y manual + visual evidence (ladder) + ux-ui-designer own AC verified → PASS/FAIL verdict |
| **Phase 3b Code Review** | Selected reviewers per harness tier + triggered experts, independent | Phase 3a passed for UI or explicitly not applicable; no PASS without evidence | code-reviewer: invariants/test quality; qa-engineer when applicable: integration/contract and relevant E2E/load; UI evidence only for UI. Record findings with revision in confirmed evidence home |
| **Phase 4 Triage** | router | Applicable review reports ready; UI N/A recorded for backend | Route findings to affected phase. Close only after required acceptance and closure authority; read back confirmed tracker, otherwise pending sync. At third unresolved review/fix iteration checkpoint and stop; retain per-task lesson |
| **Phase 5 Deploy** | devops-engineer (continuous per bd) | approval gate + rollback plan ready | health check + observability live |
| **Phase 6 Operate** | sre-engineer | service in production | SLO burn watched, incident response per runbook |

These lifecycle hooks describe pre/post conditions, not mandatory executable hooks.
Use existing project/host verification and record the evidence. devops-engineer adds automation
only when it is part of the authorized project work, never to make the plugin usable.
Do not claim deterministic enforcement merely because a condition is written here.

### 📝 Prompt Template Substitution (commands convention)

Illustrative notation only; this plugin does not supply a template interpreter.
Static (host): `{{PROJECT_NAME}}` `{{STACK}}` `{{DOMAIN}}` `{{TRACKER}}` `{{ENV}}` `{{ENGAGEMENT_ID}}` `{{USER}}` `{{DATE}}` `{{BRANCH}}`
Shell eval (sandbox, per iteration): `` {{!`git rev-parse HEAD`}} `` · `` {{!`<tracker: next ready task id>`}} ``
> ใช้เฉพาะที่จำเป็น — over-template = อ่านยาก

### Scope Contract enforcement (router)

**ก่อน implement / refactor / scaffold / fix / migration** — agent ที่ทำงานจริงต้องบันทึก Scope Contract (IN / OUT / Files / Stop / Echo). ตรวจสิทธิ์และ file ownership ก่อน edit; scope ที่อนุมัติแล้วใช้ต่อได้โดยไม่ต้องขอ scope ซ้ำ แต่ R0 ทุกครั้งยังต้องได้ confirm ของ user สำหรับ action นั้นตรง ๆ. Scope/authority ใหม่ต้องขอยืนยันชัดเจน ความเงียบไม่ใช่ approval

The router enforces it at 3 points:
1. **Pre-implement** — agent post contract → router scan: Files overlap กับ active contract อื่น? → overlap = BLOCK, รอ agent คนแรกปิด
2. **During implement** — amend/check ownership before adding files; only new scope/authority needs user decision
3. **Post-implement** — agent post `state:scope-closed` → router ปลด file ownership → agent ถัดไปทำต่อได้

**Active contracts** (durable checkpoint; reconcile on resume; notes are not locks). Reconcile missing ownership/scope before overlapping writes; unresolved authority → user. Use tested isolation or serialization; printed contracts enforce no locks. Template, examples and amendment flow → `references/scope-lock.md`.

### Loop with Exit (developer/qa-engineer)

Use the harness's three review→fix iteration cap; this reference grants no separate
five-attempt allowance. Each retry requires a changed hypothesis or new evidence.
At the cap with unresolved findings, preserve artifacts/evidence, record BLOCKED or
PARTIAL with next owner and options, and stop. Passing tests do not override unresolved
acceptance or approval gates.

### Approval Gates
Before R0 (irreversible) → bullet check + ask for approval. The 12-row gate table (single source) → `shode-house-workflow/SKILL.md` § Approval Gates; the router checks each gate before the hand-off.
Format example:
```
⏸️ Gate: pre-deploy-prod
✅ Tests: pass (unit 234/234, integration 45/45, E2E 12/12)
✅ Security: 0 critical CVE
✅ Migration: dry-run ok
✅ Rollback: revert + flag-off
→ approve deploy prod? (Y/N)
```

### Worktree Isolation (parallel-safe — devops-engineer pattern)
```bash
git worktree add ../$(PROJECT)-$(feat) -b $(feat)
```
Use case: parallel developer, hotfix-while-feature, A/B. **Batch backlog (N item อิสระ)** → load `shode-house:drain` (fan-out worktree + serial cherry-pick + close-on-done)
> Makefile pattern → `agents/devops-engineer.md`

### Workflow as Markdown
`commands/*.md` = workflow templates (Markdown แทน YAML, Claude-native, ไม่ต้อง host server)

---

---

## 🧵 Tracker options

**Single source of truth** สำหรับ status/dep — เลือก tracker ตาม project (config ใน Engagement Plan):

| Tracker | Init | Create | Ready | Close |
|---------|------|--------|-------|-------|
| **Beads** if selected | (existing) | see `harness.md` § Beads example | same | same: close + read-back |
| **GitHub Issues** | (gh authed) | `gh issue create -t "..." -l p1` | `gh issue list -l "ready"` | `gh issue close N` |
| **Linear** | (linear auth) | `linear issue create -t "..."` | `linear issue list --state Todo` | `linear issue update --state Done` |
| **Jira** | (atlassian MCP) | `mcp jira create ...` | JQL ready query | transition to Done |
| **Asana** | (asana auth) | `asana task create ...` | section query | task complete |

**Tracker selection**: reuse user-confirmed homes; ask only on first use if still unknown. Do not select/install a new tracker by default. Example choices:
```
Q: Tracker?
A) Markdown — fallback for all concerns when no existing tool is chosen
B) GitHub Issues — repo-bound, free, public/team
C) Linear — modern UI, paid (best for product team)
D) Jira — enterprise, complex, paid
E) Asana — task-focused, paid (cross-functional)
```

**Universal abstraction** (business-analyst/router use):
- `tracker.create(title, priority, type, blockedBy?)` — issue creation
- `tracker.ready()` — next unblocked tasks
- `tracker.close(id)` — done
- `tracker.link(from, to, type)` — dep (blocks/related/parent-child/discovered-from)

Status/dependencies, specs and evidence use the confirmed homes; Markdown may own any concern. Keep one authoritative copy and links elsewhere. Beads/Redmine/other trackers remain valid explicit choices

---
