---
name: smart-coop
description: Reference (lazy-load) ของ `shode-house-workflow` — Smart Coop pattern เต็ม, lifecycle hooks, approval gates, state persistence. โหลดเมื่อจะรัน pipeline จริงเท่านั้น
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-workflow/smart-coop.md
WHEN: pipeline_kickoff OR phase_transition
OWNER: orchestrator
REQUIRED-BEFORE: phase_dispatch
```

# Smart Coop Pattern — reference เต็ม (lazy-load)

> แยกออกจาก `SKILL.md` ใน v3.12: เนื้อหานี้ = 61% ของ skill ทั้งไฟล์ แต่ใช้เฉพาะตอน **รัน pipeline จริง**
> Oliver แบกมันทุกครั้งที่ spawn แม้ตอนแค่ triage คำถามสั้นหรือ route `/consult`
> **โหลดไฟล์นี้เมื่อ**: kickoff pipeline · phase transition · ตั้ง approval gate · เขียน/อ่าน `state.json` · Aaron ตั้ง lifecycle hook
> Handoff Contract ไม่อยู่ที่นี่ — อยู่ใน `shode-house-discipline` (ทุก agent ต้องรู้ ไม่ใช่แค่ตอนรัน pipeline)

**Smart Coop ≠ everything parallel.** ใช้ parallel เฉพาะที่ agent **truly independent** (no read dependency); ใช้ sequential gate ที่มี natural dependency

### Parallel-vs-Sequential Matrix

| สถานการณ์ | Pattern | เหตุผล |
|-----------|---------|--------|
| Bella ↔ Sara (Phase 1a) | **Parallel** | Different scope (BA vs SA), no read dep, align at end |
| Bella+Sara → Uma (Phase 1a → 1b) | **Sequential gate** | Uma needs spec context to design |
| Bella+Sara → Domain (Phase 1a → 1b) | **Sequential gate** | Domain validates spec, not design from scratch |
| Dev → Uma POST (Phase 2 → 3a) | **Sequential gate** | UI bug = halt before deeper review |
| Uma POST → Chris+Quinn (Phase 3a → 3b) | **Sequential gate** | UI passed first, then code/security |
| Chris ↔ Quinn (Phase 3b) | **Parallel** | Different scope (static review vs runtime test) |
| Dave#1 ↔ Dave#2 (Phase 2) | **Parallel** | Different files, no shared state (Scope Contract enforce) |

### Phase 1a Pattern (Parallel Foundation)
```
1. Oliver kick-off: broadcast roster (Bella + Sara) + bd-id
2. Bella + Sara draft parallel (independent scopes)
3. Light cross-read at end (NOT mid-checkpoint — too token-heavy):
   - Bella check FR ขัด ADR ไหม
   - Sara check ADR support FR ครบไหม
4. Sign-off → bd update <id> --notes (compact)
```

### Phase 1b Pattern (Sequential Expand)
```
1. Oliver detect: frontend trigger? business-rule trigger?
2. Uma (if frontend): read spec → wireframe + tokens + a11y + baseline screenshot
3. Domain (if business rule): read spec → regulation cite + business rule + compliance gap
4. Sign-off → outputs/SPEC-<bd-id>.md integrated
```

### Phase 3a Pattern (Sequential Gate)
```
1. Uma read Dave's PR + own Phase 1b baseline
2. Screenshot diff (Chromatic/Percy) + manual visual review
3. Verify own accept criteria + a11y manual (keyboard, screen reader, focus)
4. Verdict: PASS → Phase 3b unlocks; FAIL → loop Phase 2 (Dave fix)
```

### Phase 3b Pattern (Parallel Review)
```
1. Oliver kick-off: Chris + Quinn parallel (Uma POST already passed)
2. Chris: 7-dim review + unit test gaps + mutation kill verify
3. Quinn: integration + E2E + contract + load smoke + a11y axe automation
4. Sign-off → outputs/REVIEW-<bd-id>.md (Chris finding + Quinn finding merged)
```

### ❌ Anti-pattern (จะถูก block)
- ❌ Phase 1a serialize (Bella เสร็จก่อนแล้วโยน Sara) — ขัด parallel
- ❌ Phase 1b Uma start ก่อน 1a sign-off — Uma เดา spec
- ❌ Phase 3a skip — Dave → Chris+Quinn ตรงไม่ผ่าน Uma → UI bug ลึก
- ❌ Phase 3b serialize Chris → Quinn — ขัด parallel
- ❌ Dave#1 + Dave#2 แตะ file เดียวกัน — ต้อง Scope Contract enforce

### ✅ Correct pattern
- ✅ Phase 1a: Bella+Sara start same kickoff, end with light cross-read (no mid-checkpoint)
- ✅ Phase 1b: Uma+Domain read same 1a baseline (1 spec, not 2-3 drafts) → ลด token
- ✅ Phase 3a: Uma POST = explicit gate; FAIL = loop ก่อน Chris/Quinn เริ่ม
- ✅ Phase 3b: Chris+Quinn truly parallel (no order dep)

### 🗂️ State persistence (pure JSON, no script)
Agent maintain state ใน `outputs/<bd-id>/state.json` via Read/Write tools.
**Required**: `schema_version, bd_id, engagement{name,mode,started_at,domain[]}, current_phase, iter, phases{<phase>:{status,owners[],artifacts[]}}, handoff_log[], findings{critical,high,medium,low}, open_questions[]`
**Phase status enum**: `pending | in_progress | conditional_pass | passed | failed | skipped`
**Oliver bootstrap**: Read state.json (resume) or Write new; ถ้า `iter > 3` escalate; Edit on phase transition; ห้าม advance ถ้า prev status ≠ passed/conditional_pass หรือ missing artifacts/owners. Gate = Oliver discipline (verify schema on Read; self-check before advance).

### 🪝 Lifecycle Hooks (per phase — Aaron auto-trigger)

แต่ละ phase มี pre/post hook สำหรับ automated check:

### 📋 Phase 0 scope-clarification flow (when SME flags ambiguity)

When Domain SME (Felix/Iris/Sam/Tara/Elena/Brooke/Emma) flags scope gap in Phase 0:
1. Patrick state CONDITIONAL PASS (not full PASS) — list clarification questions verbatim from SME
2. **Oliver user-question relay** (G10 — explicit packaging, ห้าม invisible):
   - Oliver create `outputs/<bd>/05-oliver-user-clarify.md`
   - Format: friendly preamble + numbered questions + grouping by SME + explicit "USER ACTION REQUIRED"
   - 🔴 **subagent เรียก `AskUserQuestion` ไม่ได้** (Claude Code: tool นี้ยังไม่รองรับ agent ที่ spawn ผ่าน Task) —
     Oliver-as-subagent จึง **return question bundle** ขึ้นไป ไม่เปิด popup เอง:
     ```
     subagent  → return { questions[], options[], recommended } + path ของไฟล์ clarify
     main session (command) → เรียก AskUserQuestion (≤ 4 ข้อ) หรือ post markdown + สรุปในแชท (> 4 ข้อ)
                            → เขียนคำตอบกลับ tracker (bd update --notes) แล้วส่ง path ให้ subagent รอบถัดไป
     ```
     Oliver ที่ยึด main session ผ่าน `output-styles/oliver.md` = main context เรียก popup ได้ปกติ
3. **Block Phase 1a** until user response (M2 classify = `quest`, NOT M5 — no spec exists yet)
4. **Clarification round cap** (G11 — max 2 rounds):
   - Round 1: initial SME questions to user
   - Round 2: ถ้า user answer still ambiguous → re-package + ask narrower
   - Round 3 (= 3rd attempt) → **STOP, escalate user**: "scope ambiguity not resolvable via clarification — recommend (a) defer feature, (b) descope, or (c) workshop session"
5. User response → Patrick re-issue Phase 0 final → Bella incorporate into BRD scope
6. Then Phase 1a kickoff

ห้าม proceed Phase 1a โดย Patrick guess scope answer เอง (sycophancy + anchoring risk).
ห้าม Oliver relay raw SME questions ลอย ๆ โดยไม่ package — user เห็น noise (G10).
ห้ามวนถาม > 2 rounds — escalate user เลือก descope/workshop (G11).

**Grouped by phase (🔴 v3.3 PEV loop per bd)**:

| Phase | Actor | Pre-hook | Post-hook |
|-------|-------|----------|-----------|
| **Pick bd** | Oliver | `bd ready --json` not empty | `bd update <id> --claim` posted |
| **Phase 0 Discover** (opt — new initiative) | Patrick + Domain SME (dispatched separately, no Patrick role-play) | opportunity flagged | OKR + RICE + kill criteria → `outputs/opportunity-<feature>.md`. **Conditional PASS** if Domain SME flags scope ambiguity → escalate user clarify, block Phase 1a (per § Phase 0 scope-clarify flow) |
| **Phase 1a Foundation** | Bella ∥ Sara | bd issue context + CLAUDE.md loaded | BRD + ADR drafts done, light cross-read pass, `bd update <id> --notes` posted |
| **Phase 1b Expand** | Uma + Domain (conditional) | 1a sign-off + frontend/business-rule trigger detected | Uma: wireframe + tokens + a11y baseline; Domain: regulation cite + rule. Integrated `outputs/SPEC-<bd-id>.md` saved |
| **Phase 1c Threat Model** (conditional) | Sentinel | auth/PII/money/external trigger | STRIDE + abuse case + security AC injected to 1a |
| **Phase 2 Implement** | Dave | UI artifact verified (pre-implement-ui), Scope Contract posted, worktree | lint + type + unit pass, smoke green, Scope Contract closed |
| **Phase 3a UI Check** | Uma (conditional) | implement done + frontend changed | screenshot diff approved + a11y manual + visual evidence (ladder) + Uma own AC verified → PASS/FAIL verdict |
| **Phase 3b Code Review** | Chris ∥ Quinn | Phase 3a passed (no order between Chris/Quinn); **adversarial — verdict default FAIL** | Chris: 7-dim + mutation kill ≥ 70% + visual evidence (ladder); Quinn: E2E + contract + load + axe + visual evidence (ladder); merged `outputs/REVIEW-<bd-id>.md` |
| **Phase 4 Triage** | Oliver | 3a + 3b reports ready | route loop (Phase 1a/1b/2 by finding type) ∥ Clean → `bd close <id> --reason "<verdict> <sha> <test>"` + `bd show <id>` re-confirm CLOSED (🔴 M8 Close-on-Done — paste output) ∥ iter > 3 → escalate user. Per-bd reflect `bd remember <lesson>` |
| **Phase 5 Deploy** | Aaron (continuous per bd) | approval gate + rollback plan ready | health check + observability live |
| **Phase 6 Operate** | Reggie | service in production | SLO burn watched, incident response per runbook |

Aaron implements hooks via Makefile/CI — agent ไม่ต้อง manual

### 📝 Prompt Template Substitution (commands convention)

Static (host): `{{PROJECT_NAME}}` `{{STACK}}` `{{DOMAIN}}` `{{TRACKER}}` `{{ENV}}` `{{ENGAGEMENT_ID}}` `{{USER}}` `{{DATE}}` `{{BRANCH}}`
Shell eval (sandbox, per iteration): `` {{!`git rev-parse HEAD`}} `` · `` {{!`bd ready --json | jq '.[0].id'`}} ``
> ใช้เฉพาะที่จำเป็น — over-template = อ่านยาก

### Loop with Exit (🔴 Dave/Quinn)
```
loop (max 5):
  do → test
  pass → exit | fail+max → escalate Sara | else → fix root cause + retry
```
- Binary: pass = pass (ห้าม "เกือบ pass")
- Max iter ≠ keep trying → re-design

### Approval Gates (⏸️ Oliver)
ก่อน R0 (irreversible) → bullet check + ขอ approve
**10 standard (🔴 phase-aligned)**: **pre-spec-expand** (🔴 Phase 1a → 1b: Bella+Sara sign-off ก่อน Uma/Domain expand), **pre-implement-ui** (🔴 Phase 1b → 2: Uma artifact ครบก่อน Dave start frontend), **pre-ui-check** (🔴 Phase 2 → 3a: lint clean + unit green + smoke pass ก่อน Uma POST), **pre-code-review** (🔴 Phase 3a → 3b: Uma POST PASS ก่อน Chris+Quinn เริ่ม), pre-merge, **pre-merge-ui** (🔴 Playwright/visual/axe evidence ก่อน merge UI change), **pre-loop-exit** (🔴 Phase 4 → 5: Triage clean + iter ≤ 3 → unlock Deploy), pre-deploy-staging/uat/prod, pre-data-migration, pre-destructive
> ดู Oliver agent file สำหรับ full table + format

### Worktree Isolation (parallel-safe — Aaron pattern)
```bash
git worktree add ../$(PROJECT)-$(feat) -b $(feat)
```
Use case: parallel Dave, hotfix-while-feature, A/B. **Batch backlog (N item อิสระ)** → `drain` skill (fan-out worktree + serial cherry-pick + close-on-done)
> ดู Aaron agent file สำหรับ Makefile pattern

### Workflow as Markdown
`commands/*.md` = workflow templates (Markdown แทน YAML, Claude-native, ไม่ต้อง host server)

---

---

## 🧵 Tracker options

**Single source of truth** สำหรับ status/dep — เลือก tracker ตาม project (config ใน Engagement Plan):

| Tracker | Init | Create | Ready | Close |
|---------|------|--------|-------|-------|
| **beads (bd)** default | `bd init` | `bd create "..." -p1 -t feature` | `bd ready --json` | `bd close N --reason "<sha> <test>"` + `bd show N` |
| **GitHub Issues** | (gh authed) | `gh issue create -t "..." -l p1` | `gh issue list -l "ready"` | `gh issue close N` |
| **Linear** | (linear auth) | `linear issue create -t "..."` | `linear issue list --state Todo` | `linear issue update --state Done` |
| **Jira** | (atlassian MCP) | `mcp jira create ...` | JQL ready query | transition to Done |
| **Asana** | (asana auth) | `asana task create ...` | section query | task complete |

**Tracker selection** (Engagement Plan Phase 2 — option-style):
```
Q: Tracker?
A) beads (bd) — local, fast, AFK-friendly (Recommended for solo/small)
B) GitHub Issues — repo-bound, free, public/team
C) Linear — modern UI, paid (best for product team)
D) Jira — enterprise, complex, paid
E) Asana — task-focused, paid (cross-functional)
```

**Universal abstraction** (Bella/Oliver use):
- `tracker.create(title, priority, type, blockedBy?)` — issue creation
- `tracker.ready()` — next unblocked tasks
- `tracker.close(id)` — done
- `tracker.link(from, to, type)` — dep (blocks/related/parent-child/discovered-from)

**Markdown deliverable** (BRD/ADR/spec) อยู่ `outputs/` — แต่ **status/dep = tracker เท่านั้น** (ห้าม markdown TODO list)

---
