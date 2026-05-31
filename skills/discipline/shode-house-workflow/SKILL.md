---
name: shode-house-workflow
description: |
  [WHAT] Workflow discipline — Phase Contract (Smart Coop) + lifecycle hooks + approval gates + worktree isolation + task tracking + token-saving runtime rules.
  [AUDIENCE] Oliver (sole owner); ทุก agent (Phase Contract compliance).
  [WHEN] Pipeline kickoff; phase transition; pre-deploy multi-sig; ทุก hook event.
  [TRIGGER] /shode-house:workflow, "Phase Contract", "Smart Coop", "lifecycle hook", "approval gate", "worktree", "task tracking", "token-saving", "bd issue".
---

# shode-house — Workflow Discipline

> Oliver owns workflow. Phase Contract บังคับ. Hooks + Gates make pipeline auditable. สำหรับ Drift Defense (M1-M7) ดู `shode-house-drift` skill

---
## 🧵 Task Tracking — Pluggable Tracker (default: beads/bd)

**Single source of truth** สำหรับ status/dep — เลือก tracker ตาม project (config ใน Engagement Plan):

| Tracker | Init | Create | Ready | Close |
|---------|------|--------|-------|-------|
| **beads (bd)** default | `bd init` | `bd create "..." -p1 -t feature` | `bd ready --json` | `bd close N` |
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

## 🧭 Routing

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

## 🔁 Workflow Discipline (🔴 Archon-inspired)

### Phase Contract — 🔴 v3.3 PEV Loop per bd (Oliver enforce)

**Single loop: PEV (Plan → Execute → Verify → Triage) per bd** (🔴 v3.3 — sprint outer loop removed)

> ก่อน v3.3 มี outer sprint loop + inner per-issue loop. v3.3 = **single PEV loop per bd** — agent ส่งงาน task-complete, ไม่ time-bound. ห้าม man-day negotiation (per shode-house-discipline). Deploy = continuous per bd ready, ไม่ batched sprint-end.

```
┌─ PEV LOOP per bd issue (Smart Coop — parallel where independent) ─┐
│                                                                    │
│  📍 PICK: bd update <id> --claim                                   │
│     ↓                                                              │
│  📋 PLAN                                                           │
│   Phase 0 🔍 Discovery (Patrick + Domain SME — opt, new initiative)│
│   Phase 1a 🤝 Foundation (Bella ∥ Sara — TRUE parallel)           │
│              BRD + AC ∥ ADR + risk                                 │
│              → bd update --notes (compact ref only)                │
│   Phase 1b 🎨 Conditional Expand (sequential gate after 1a)        │
│              Uma* reads spec → wireframe + tokens + a11y baseline  │
│              Domain* reads spec → regulation cite + business rule  │
│              → outputs/SPEC-<bd-id>.md (integrated)                │
│              ⏸️ Gate pre-implement-ui (Uma sign UI acceptance)      │
│   Phase 1c 🛡 Threat Model (Sentinel — conditional auth/PII/money) │
│     ↓                                                              │
│  💻 EXECUTE                                                        │
│   Phase 2 (Dave — parallel Dave#1/#2 ถ้า independent)              │
│              Scope Contract + code + unit test                     │
│              ⏸️ Gate: lint clean + unit green + smoke pass          │
│     ↓                                                              │
│  ✅ VERIFY (Chris/Quinn adversarial — zero trust Dave)             │
│   Phase 3a 🎨 UI Check (Uma* — sequential gate)                    │
│              Screenshot diff + Claude in Chrome verify             │
│   Phase 3b 🔍 Code Review (Chris ∥ Quinn — TRUE parallel)          │
│              Chris: 7-dim + mutation ≥ 70% + Chrome verify         │
│              Quinn: integration + E2E + contract + load + Chrome   │
│              ⏸️ Gate: 0 Critical/Major + verdict default = FAIL    │
│     ↓                                                              │
│  🚦 TRIAGE (Oliver — loop routing)                                 │
│   Phase 4 Critical/Major → bd create --discovered-from=N           │
│              + loop กลับ phase ตาม finding type:                    │
│                ─ code/perf/security impl → Phase 2 (EXECUTE)       │
│                ─ UI/design adherence → Phase 1b (PLAN expand)      │
│                ─ spec/AC/regulation → Phase 1a (PLAN foundation)   │
│              Minor → bd create P4 + continue                       │
│              Clean → bd close <id>                                 │
│              Max iter 3 → STOP escalate user                       │
│     ↓                                                              │
│  🚀 DEPLOY (Aaron — continuous per bd, or manual gate)             │
│   Phase 5 CI + canary + health + observability                     │
│     ↓                                                              │
│  📡 OPERATE (Reggie — continuous post-deploy)                      │
│   Phase 6 SLO burn watch + incident response                       │
│                                                                    │
│  📚 (No sprint retro — per-bd reflect happens in Phase 4 Triage)   │
└────────────────────────────────────────────────────────────────────┘

* = conditional: Uma เข้า 1b+3a เฉพาะ feature touch user-facing UI; Domain เข้า 1b เฉพาะ touch business rule
```

**Key change v3.3**:
- ❌ ไม่มี outer sprint loop (drop /sprint command + Pre-Sprint + Sprint Close + retro bracket)
- ✅ Patrick OKR review = continuous (per-bd contribution, ไม่ bracket)
- ✅ Deploy = per bd ready (continuous) หรือ manual batch (optional ตาม user)
- ✅ Per-bd reflect ใน Phase 4 Triage (ไม่มี Sprint Retro)
- ✅ ห้าม agent propose timeline / man-day (per shode-house-discipline § No Man-Day Negotiation)

> **Why 1a + 1b แทน Coop 4-way parallel** (v2.8 over v2.7): Bella → Sara มี natural alignment (BRD informs ADR), Uma + Domain ต้องอ่าน spec ก่อน design/validate ฉะนั้น 4-way parallel + cross-read = ~40% redundant token. 1a (Bella ∥ Sara) + 1b (Uma + Domain sequential, read 1 spec baseline) = ได้ quality สูง ลด token

> **Why 3a before 3b** (v2.8 over v2.7): UI bug ตรวจที่ Uma ก่อน — Chris/Quinn ไม่เสีย effort review code ที่ design ผิด. Chris+Quinn ทำงาน parallel ตามเดิม (different scope: static review vs runtime test)

> **Phase routing precision** (v2.8 over v2.7): Triage แยก code/UI/spec → loop กลับ phase ที่เหมาะ (1a vs 1b vs 2) ไม่ใช่แค่ "Phase 1 หรือ Phase 2"

---

## 🤝 Smart Coop Pattern (🔴 v2.8 — parallel where independent, sequential gate where dependent)

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
2. Bella + Sara draft pผ่ารallel (independent scopes)
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

### 🪝 Lifecycle Hooks (per phase — Aaron auto-trigger)

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
| **Phase 4 Triage** | Oliver | 3a + 3b reports ready | route loop (Phase 1a/1b/2 by finding type) ∥ Clean → `bd close <id>` ∥ iter > 3 → escalate user. Per-bd reflect captured in `bd remember <lesson>` (no sprint retro) |
| **Phase 5 Deploy** | Aaron (continuous per bd) | approval gate + rollback plan ready | health check + observability live |
| **Phase 6 Operate** | Reggie | service in production | SLO burn watched, incident response per runbook |

Aaron implements hooks via Makefile/CI — agent ไม่ต้อง manual

### 📝 Prompt Template Substitution (commands convention)

Slash commands รองรับ placeholder + shell eval:

**Static substitution** (host-side):
- `{{PROJECT_NAME}}` `{{STACK}}` `{{DOMAIN}}` `{{TRACKER}}` `{{ENV}}`
- `{{ENGAGEMENT_ID}}` `{{USER}}` `{{DATE}}` `{{BRANCH}}`

**Shell eval** (sandbox-side, per iteration):
- `` {{!`git rev-parse HEAD`}} `` — current commit
- `` {{!`bd ready --json | jq '.[0].id'`}} `` — next task
- `` {{!`docker compose ps --format json`}} `` — runtime state

**Example** (`commands/implement.md`):
```
[Dave] รับงาน {{!`bd ready --json | jq -r '.[0].title'`}}
context: {{ENGAGEMENT_ID}} on {{BRANCH}}
```

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
**10 standard (🔴 v2.8 phase-aligned)**: **pre-spec-expand** (🔴 v2.8 — Phase 1a → 1b: Bella+Sara sign-off ก่อน Uma/Domain expand), **pre-implement-ui** (🔴 v2.6.1 — Phase 1b → 2: Uma artifact ครบก่อน Dave start frontend), **pre-ui-check** (🔴 v2.8 — Phase 2 → 3a: lint clean + unit green + smoke pass ก่อน Uma POST), **pre-code-review** (🔴 v2.8 — Phase 3a → 3b: Uma POST PASS ก่อน Chris+Quinn เริ่ม), pre-merge, **pre-merge-ui** (🔴 v2.4 — Playwright/visual/axe evidence ก่อน merge UI change), **pre-loop-exit** (🔴 v2.7 — Phase 4 → 5: Triage clean + iter ≤ 3 → unlock Deploy), pre-deploy-staging/uat/prod, pre-data-migration, pre-destructive
> ดู Oliver agent file สำหรับ full table + format

### Worktree Isolation (parallel-safe — Aaron pattern)
```bash
git worktree add ../$(PROJECT)-$(feat) -b $(feat)
```
Use case: parallel Dave, hotfix-while-feature, A/B
> ดู Aaron agent file สำหรับ Makefile pattern

### Workflow as Markdown
`commands/*.md` = workflow templates (Markdown แทน YAML, Claude-native, ไม่ต้อง host server)

---

## 📚 Reference Files (lazy-load)
