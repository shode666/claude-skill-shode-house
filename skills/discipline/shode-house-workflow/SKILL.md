---
name: shode-house-workflow
description: |
  [WHAT] Workflow discipline — Phase Contract (Smart Coop) + lifecycle hooks + approval gates + worktree isolation + task tracking + token-saving runtime rules.
  [AUDIENCE] Oliver (sole owner); ทุก agent (Phase Contract compliance).
  [WHEN] Pipeline kickoff; phase transition; pre-deploy multi-sig; ทุก hook event.
  [TRIGGER] /shode-house:workflow, "Phase Contract", "Smart Coop", "lifecycle hook", "approval gate", "worktree", "task tracking", "token-saving", "bd issue".
---

# shode-house — Workflow Discipline

> Oliver owns workflow. Phase Contract บังคับ. Hooks + Gates make pipeline auditable. สำหรับ Drift Defense (M1-M8) ดู `shode-house-drift` skill

---
## 🧵 Task Tracking — Pluggable Tracker (default: beads/bd)

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

## 🎚️ Engagement Mode (🔴 Oliver เลือกก่อนเริ่ม — ย้ายมาจาก `shode-house-discipline` v3.10)

| Mode | Behavior | When |
|------|----------|------|
| **AFK** (Auto) | Oliver delegate ทุก phase + automated gate. User approve เฉพาะ R0 | งานชัด, trusted scope |
| **Interactive** (Supervised) | Human approve ทุก hand-off + ดู agent output ก่อน next | งานใหม่/ละเอียดอ่อน, learning, audit |
| **Hybrid** (Recommended default) | AFK ถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้น | งานทั่วไป — balance speed + safety |

**Mode bind R0/R1/R2**:
- AFK: R2 auto, R1 inform-only, R0 ขออนุญาต
- Interactive: R2/R1 inform, R0 ขออนุญาต + ทุก phase exit ขออนุมัติ
- Hybrid: AFK rule ก่อน deploy phase → switch Interactive ตั้งแต่ deploy

---

## 🚦 Phase orchestration — ห้าม (🔴 Oliver enforce, ย้ายมาจาก discipline v3.10)

- 🔴 ห้าม serialize Phase 1a (Bella → Sara รอคิว); ห้าม parallel Phase 1b (Uma/Domain ต้องอ่าน 1a spec ก่อน design/validate)
- 🔴 ห้าม skip Phase 3a Uma POST gate. Dave → Chris+Quinn ตรงเลย โดยไม่ผ่าน Uma = UI bug ลึกค่อย rework
- 🔴 ห้าม serialize Phase 3b (Chris → Quinn รอคิว); parallel เท่านั้น (different scope)
- 🔴 ห้าม skip Phase 4 Triage routing. Review fail → loop ไป phase ที่ตรง finding (code→2, UI→1b, spec→1a); ห้าม "ผ่านครึ่ง ๆ" ข้ามไป Deploy
- 🔴 ห้าม close Phase 3 (3a/3b) ก่อน post review report. **bd active → `bd update <id> --notes` ONLY** (ห้ามเขียน markdown ซ้ำ). **No bd → `outputs/REVIEW-<feature>.md`** (markdown fallback). ใช้ template structure จาก "REVIEW Report Format" section
- 🔴 ห้ามเขียน review เป็น markdown ถ้ามี bd. bd = single source of truth; markdown = audit redundancy + drift risk

---

## 🔧 Token-saving (🔴 runtime)

- `Grep`/`Glob` (targeted) > `Read` ทั้งไฟล์
- `Read` with `offset`/`limit` > full
- `mcp__context7__get-library-docs` > `WebFetch`
- `WebSearch` > `WebFetch` (link first)
- Reference by ID/standard name ไม่ paste content
- Domain expert: focus scope, generic ส่ง Sara/Dave
- Reuse artifact path ไม่ paste content
- Oliver: ห้าม re-analyze สิ่งที่ agent อื่นทำแล้ว
- **Lazy load reference**: `references/languages/<lang>.md`, `references/patterns/general.md`, `references/modern-stack.md`

---

## ✅ Definition of Done (🔴 verifiable — Oliver enforce ห้ามปิด task)

> DoD checklist (verifiable, Anti-Puppet, per-owner) = **`shode-house-deliverable` skill § Definition of Done** (single source). Oliver enforce ก่อนปิด bd: ทุก DoD item ต้องมี evidence path — ห้ามปิดถ้าขาด

## 🔁 Workflow Discipline (🔴 Archon-inspired)

### Phase Contract — 🔴 v3.3 PEV Loop per bd (Oliver enforce)

**Single loop: PEV (Plan → Execute → Verify → Triage) per bd** (🔴 v3.3 — sprint outer loop removed)

> ก่อน v3.3 มี outer sprint loop + inner per-issue loop. v3.3 = **single PEV loop per bd** — agent ส่งงาน task-complete, ไม่ time-bound. ห้าม man-day negotiation (per shode-house-discipline). Deploy = continuous per bd ready, ไม่ batched sprint-end.

```
PICK bd claim → PLAN 0 Discover* / 1a Bella∥Sara / 1b Uma*+Domain* / 1c Sentinel*
  → EXECUTE 2 Dave → VERIFY 3a Uma* → 3b Chris∥Quinn → TRIAGE 4 Oliver
  → DEPLOY 5 Aaron (continuous per bd) → OPERATE 6 Reggie          (* = conditional)

Triage routing: code/perf/security→2 · UI/design→1b · spec/AC/regulation→1a
Clean → bd close + bd show verify (M8) + bd remember · iter > 3 → STOP escalate user
```
> รายละเอียด pre/post hook ต่อ phase = ตาราง § Lifecycle Hooks ด้านล่าง (single source)

**Key rules**: ❌ ไม่มี outer sprint loop (ไม่มี /sprint, Pre-Sprint, Sprint Close, retro bracket) · ✅ Patrick OKR review + Deploy = continuous per-bd · ✅ per-bd reflect ใน Phase 4 Triage · ✅ ห้าม propose timeline/man-day (per `shode-house-discipline` § No Man-Day Negotiation)

> **Why 1a + 1b แทน 4-way parallel**: Uma + Domain ต้องอ่าน spec ก่อน design/validate → 4-way + cross-read = ~40% redundant token. 1a (Bella ∥ Sara) + 1b (read 1 spec baseline) = quality สูง token ต่ำ
> **Why 3a before 3b**: UI bug ตรวจที่ Uma ก่อน — Chris/Quinn ไม่เสีย effort review code ที่ design ผิด
> **Phase routing precision**: Triage แยก code/UI/spec → loop กลับ phase ที่เหมาะ (1a vs 1b vs 2)

---

## 🤝 Smart Coop Pattern (🔴 parallel where independent, sequential gate where dependent)

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

### 🤝 Handoff Contract (🔴 v3.8 — artifact-passing, ห้ามส่งเนื้อหาผ่าน prose)

> **Why**: sub-agent เกิดใน context ว่าง — เห็นแค่ agent body + delegation message + CLAUDE.md. เนื้อหาที่ orchestrator ส่งเป็น prose = **lossy channel** ("game of telephone"). ทุก phase artifact จึงต้องอยู่ใน **ไฟล์** และ delegation ส่ง **path**

**บังคับทุก Task delegate**:
```
1. Producer เขียน artifact ลงไฟล์ก่อน hand-off  → outputs/<bd-id>/<NN>-<agent>-<phase>.md
2. Delegation message ส่ง PATH ไม่ส่งเนื้อหา     → "อ่าน outputs/bd-42/08-bella-phase1a.md"
3. Consumer Read ไฟล์เอง                        → ห้ามพึ่งสรุปใน delegation message
4. Producer return = structured conclusion เท่านั้น → verdict + artifact path + open questions
   (ห้าม dump transcript / full content กลับ orchestrator)
5. Oliver synthesize จาก conclusion + path      → ห้าม rehydrate worker's full trace
```

**ห้าม** (จะถูก block):
- ❌ Oliver paste BRD/ADR/REVIEW content ลง delegation prompt — ส่ง path
- ❌ Agent claim "ตาม spec ที่ได้รับมา" โดยไม่ Read ไฟล์ spec จริง (= NO MAGIC violation)
- ❌ Sub-agent return markdown ยาวกลับ Oliver แทนที่จะเขียนไฟล์ + return path

**Bootstrap gap**: sub-agent ไม่เห็น conversation history → delegation message ต้องมี **bd-id + artifact paths + phase + iter** เสมอ ไม่งั้น consumer เริ่มงานแบบไม่มี state

### 🗂️ State persistence (pure JSON, no script)
Agent maintain state ใน `outputs/<bd-id>/state.json` via Read/Write tools.
**Required**: `schema_version, bd_id, engagement{name,mode,started_at,domain[]}, current_phase, iter, phases{<phase>:{status,owners[],artifacts[]}}, handoff_log[], findings{critical,high,medium,low}, open_questions[]`
**Phase status enum**: `pending | in_progress | conditional_pass | passed | failed | skipped`
**Oliver bootstrap**: Read state.json (resume) or Write new; ถ้า `iter > 3` escalate; Edit on phase transition; ห้าม advance ถ้า prev status ≠ passed/conditional_pass หรือ missing artifacts/owners. Gate = Oliver discipline (verify schema on Read; self-check before advance).

### 🪝 Lifecycle Hooks (per phase — Aaron auto-trigger)

แต่ละ phase มี pre/post hook สำหรับ automated check:

### 📋 Phase 0 scope-clarification flow (🔴 v3.3 — when SME flags ambiguity)

When Domain SME (Felix/Iris/Sam/Tara/Elena/Brooke/Emma) flags scope gap in Phase 0:
1. Patrick state CONDITIONAL PASS (not full PASS) — list clarification questions verbatim from SME
2. **Oliver user-question relay** (G10 — explicit packaging, ห้าม invisible):
   - Oliver create `outputs/<bd>/05-oliver-user-clarify.md`
   - Format: friendly preamble + numbered questions + grouping by SME + explicit "USER ACTION REQUIRED"
   - Use AskUserQuestion tool ถ้า ≤ 4 questions; ถ้า > 4 → markdown file + chat summary
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
| **Phase 3a UI Check** | Uma (conditional) | implement done + frontend changed | screenshot diff approved + a11y manual + Claude in Chrome verify + Uma own AC verified → PASS/FAIL verdict |
| **Phase 3b Code Review** | Chris ∥ Quinn | Phase 3a passed (no order between Chris/Quinn); **adversarial — verdict default FAIL** | Chris: 7-dim + mutation kill ≥ 70% + Chrome verify; Quinn: E2E + contract + load + axe + Chrome verify; merged `outputs/REVIEW-<bd-id>.md` |
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

## 📚 Reference Files (lazy-load)
