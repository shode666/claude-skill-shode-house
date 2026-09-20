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

> Applicability: use the harness risk tier and triggered roles. UI-only phases/gates are not applicable to pure backend changes; record why. Parallel means optional concurrency between independent actors, subject to host capacity; separate sequential reviewers are valid. Beads/output paths below are examples within the confirmed record home, not a tracker migration requirement.

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
4. Verdict: PASS → Phase 3b unlocks; FAIL → triage to affected owner/phase (code→Dave, design→Uma, spec→Bella)
```

### Phase 3b Pattern (Parallel Review)
```
1. Oliver kick-off: Chris + Quinn parallel (Uma POST already passed)
2. Chris: 7-dim review + unit test gaps + mutation kill verify
3. Quinn: integration + E2E + contract + load smoke + a11y axe automation
4. Sign-off → outputs/REVIEW-<bd-id>.md (Chris finding + Quinn finding merged)
```

### ❌ Anti-pattern (จะถูก block)
- ❌ Phase 1a Sara คัดลอกข้อสรุป Bella แทนทำ architecture analysis ของตน; sequential คนละ context ทำได้
- ❌ Phase 1b Uma start ก่อน 1a sign-off — Uma เดา spec
- ❌ Skip Uma POST for changed UI; pure backend records Phase 3a not-applicable and proceeds to its required reviews
- ❌ Phase 3b Quinn ใช้ verdict Chris แทน integration evidence ของตน; sequential คนละ reviewer ทำได้
- ❌ Dave#1 + Dave#2 แตะ file เดียวกัน — ต้อง Scope Contract enforce

### ✅ Correct pattern
- ✅ Phase 1a: Bella+Sara start same kickoff, end with light cross-read (no mid-checkpoint)
- ✅ Phase 1b: Uma+Domain read same 1a baseline (1 spec, not 2-3 drafts) → ลด token
- ✅ Phase 3a: Uma POST = explicit gate; FAIL = loop ก่อน Chris/Quinn เริ่ม
- ✅ Phase 3b: Chris+Quinn truly parallel (no order dep)

### 🗂️ State persistence (pure JSON, no script)
Oliver maintain checkpoint ใน canonical record ของ project ตาม `harness.md`; ไม่สร้าง state อีกชุดหากมี record ที่ครอบคลุมอยู่แล้ว. JSON ต่อไปนี้เป็นทางเลือก ไม่ใช่ runner prerequisite.
**Required meaning**: task ID, engagement/scope, current phase/iteration, phase status/owners/artifacts/revisions, findings, open questions, approvals, UNKNOWN operations และ next action. Markdown/Jira links ใช้แทน JSON fields ได้
**Phase status enum**: `pending | in_progress | conditional_pass | passed | failed | skipped`
**Oliver bootstrap**: อ่าน current record + artifact revisions ก่อน resume; unresolved at the third review/fix iteration → checkpoint and escalate. ห้าม advance เมื่อ required evidence/owner ขาด. `conditional_pass` ไม่ปลด blocker ที่ยัง unresolved. Prompt check ไม่ใช่ deterministic runtime enforcement

### 🪝 Lifecycle conditions (per phase — automation only when authorized)

แต่ละ phase มี pre/post hook สำหรับ automated check:

### 📋 Phase 0 scope-clarification flow (when SME flags ambiguity)

When Domain SME (Felix/Iris/Sam/Tara/Elena/Brooke/Emma) flags scope gap in Phase 0:
1. Patrick state CONDITIONAL PASS (not full PASS) — list clarification questions verbatim from SME
2. **Oliver user-question relay** (G10 — explicit packaging, ห้าม invisible):
   - Oliver create `outputs/<bd>/05-oliver-user-clarify.md`
   - Format: friendly preamble + numbered questions + grouping by SME + explicit "USER ACTION REQUIRED"
   - 🔴 **subagent เรียก `AskUserQuestion` ไม่ได้** (Claude Code: tool นี้ยังไม่รองรับ agent ที่ spawn ผ่าน Task) —
     Any specialist needing user input returns a question bundle to Oliver, who remains the main session; never spawn an Oliver subagent:
     ```
     subagent  → return { questions[], options[], recommended } + path ของไฟล์ clarify
     main session (command) → เรียก AskUserQuestion (≤ 4 ข้อ) หรือ post markdown + สรุปในแชท (> 4 ข้อ)
                            → เขียนคำตอบกลับ tracker (bd update --notes) แล้วส่ง path ให้ subagent รอบถัดไป
     ```
     Oliver uses the main session's actual popup tool when available, otherwise Markdown. Host limits determine question batch size; the Claude example is not a portable API.
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
| **Phase 1c Threat Model** (conditional) | Sentinel | auth/session/PII/money/external integration/webhook/file upload/AI agent trigger (canonical list → SKILL.md § Phase 1c; "low risk" ไม่ waive) | STRIDE + abuse case + security AC injected to 1a |
| **Phase 2 Implement** | Dave | Scope Contract posted, verified write isolation; UI artifact required only for UI work | lint + type + unit pass, smoke green, Scope Contract closed |
| **Phase 3a UI Check** | Uma (conditional) | implement done + frontend changed | screenshot diff approved + a11y manual + visual evidence (ladder) + Uma own AC verified → PASS/FAIL verdict |
| **Phase 3b Code Review** | Selected reviewers per harness tier + triggered experts, independent | Phase 3a passed for UI or explicitly not applicable; no PASS without evidence | Chris: invariants/test quality; Quinn when applicable: integration/contract and relevant E2E/load; UI evidence only for UI. Record findings with revision in confirmed evidence home |
| **Phase 4 Triage** | Oliver | Applicable review reports ready; UI N/A recorded for backend | Route findings to affected phase. Close only after required acceptance and closure authority; read back confirmed tracker, otherwise pending sync. At third unresolved review/fix iteration checkpoint and stop; retain per-task lesson |
| **Phase 5 Deploy** | Aaron (continuous per bd) | approval gate + rollback plan ready | health check + observability live |
| **Phase 6 Operate** | Reggie | service in production | SLO burn watched, incident response per runbook |

These lifecycle hooks describe pre/post conditions, not mandatory executable hooks.
Use existing project/host verification and record the evidence. Aaron adds automation
only when it is part of the authorized project work, never to make the plugin usable.
Do not claim deterministic enforcement merely because a condition is written here.

### 📝 Prompt Template Substitution (commands convention)

Illustrative notation only; this plugin does not supply a template interpreter.
Static (host): `{{PROJECT_NAME}}` `{{STACK}}` `{{DOMAIN}}` `{{TRACKER}}` `{{ENV}}` `{{ENGAGEMENT_ID}}` `{{USER}}` `{{DATE}}` `{{BRANCH}}`
Shell eval (sandbox, per iteration): `` {{!`git rev-parse HEAD`}} `` · `` {{!`bd ready --json | jq '.[0].id'`}} ``
> ใช้เฉพาะที่จำเป็น — over-template = อ่านยาก

### Loop with Exit (Dave/Quinn)

Use the harness's three review→fix iteration cap; this reference grants no separate
five-attempt allowance. Each retry requires a changed hypothesis or new evidence.
At the cap with unresolved findings, preserve artifacts/evidence, record BLOCKED or
PARTIAL with next owner and options, and stop. Passing tests do not override unresolved
acceptance or approval gates.

### Approval Gates (⏸️ Oliver)
ก่อน R0 (irreversible) → bullet check + ขอ approve
**10 standard (🔴 phase-aligned)**: **pre-spec-expand** (🔴 Phase 1a → 1b: Bella+Sara sign-off ก่อน Uma/Domain expand), **pre-implement-ui** (🔴 Phase 1b → 2: Uma artifact ครบก่อน Dave start frontend), **pre-ui-check** (🔴 Phase 2 → 3a: lint clean + unit green + smoke pass ก่อน Uma POST), **pre-code-review** (🔴 Phase 3a → 3b: Uma POST PASS for changed UI, or recorded UI not-applicable for backend, before selected reviewers start), pre-merge, **pre-merge-ui** (🔴 Playwright/visual/axe evidence ก่อน merge UI change), **pre-loop-exit** (🔴 Phase 4 → 5: Triage clean + iter ≤ 3 → unlock Deploy), pre-deploy-staging/uat/prod, pre-data-migration, pre-destructive
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
| **beads (bd)** if selected | `bd init` | `bd create "..." -p1 -t feature` | `bd ready --json` | `bd close N --reason "<sha> <test>"` + `bd show N` |
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

**Universal abstraction** (Bella/Oliver use):
- `tracker.create(title, priority, type, blockedBy?)` — issue creation
- `tracker.ready()` — next unblocked tasks
- `tracker.close(id)` — done
- `tracker.link(from, to, type)` — dep (blocks/related/parent-child/discovered-from)

Status/dependencies, specs and evidence use the confirmed homes; Markdown may own any concern. Keep one authoritative copy and links elsewhere. Beads/Redmine/other trackers remain valid explicit choices

---
