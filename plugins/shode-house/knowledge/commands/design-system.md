---
description: "[shode-house] Smart Spec pipeline (Phase 1a business-analyst + solution-architect parallel; Phase 1b ux-ui-designer + domain conditional). Flags: --stop = หยุดที่ spec ไม่ suggest implement (proposal mode); --estimate = เพิ่ม T-shirt sizing step"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash, Skill, AskUserQuestion
argument-hint: "[bd-id | system description] [--stop] [--estimate]"
---

> 🗺️ **ก่อนเริ่ม — งานนี้ใหญ่เกิน 1 spec ไหม?** ถ้า user มาด้วยไอเดียก้อนใหญ่ที่ยังมองไม่เห็นทาง (ตอบไม่ได้ว่า "เสร็จ" หน้าตายังไง / มี decision ต้องตัดก่อนถึงจะ spec ได้) → **หยุด แล้วทำ Map ก่อน** (`skills/discipline/shode-house-workflow/wayfinding.md`). command นี้สมมติว่ารูปงานนิ่งแล้ว — ใช้กับ fog จะได้ spec ที่เขียนจากการเดา

📝 **Spec phase** สำหรับ: **$ARGUMENTS**

Router style not active in this session → report `BLOCKED: team execution needs the router style (Claude Code)`; do not read the style file to act as the router.

> v3.1: รวม `/spec-only` เข้ามาเป็น `--stop --estimate` flags. Pipeline = parallel foundation (business-analyst + solution-architect) → conditional sequential expand (ux-ui-designer + domain) → optional estimation → optional stop.

## Flag parsing (router step 0)

```bash
STOP=false
ESTIMATE=false
ARGS=$(echo "$ARGUMENTS" | sed -E 's/--stop|--estimate//g' | xargs)

[[ "$ARGUMENTS" == *--stop* ]] && STOP=true
[[ "$ARGUMENTS" == *--estimate* ]] && ESTIMATE=true

# `--stop` without `--estimate` → no estimation (No Man-Day default); say in the summary that `--estimate` adds it — do not ask
```

| Flag combo | Mode | Use case |
|---|---|---|
| (none) | spec → suggest /implement | normal feature design |
| `--estimate` | spec + estimation → suggest /implement | when user explicit ขอ effort for external report |
| `--stop` | spec → STOP (no implement suggest) | review-only / docs |
| `--stop --estimate` | spec + estimation → STOP + summary | **proposal / quotation** (replaces /spec-only) |

## Step 0 — Triage (router)

- Pick task in the confirmed tracker (read `<id>` ถ้ามี argument) หรือ create ใหม่ (feature, high priority) — harness contract; Markdown fallback
- Trigger detection:
  - **frontend trigger**? (touch UI/component/page/view/email/dashboard) → ux-ui-designer เข้า Phase 1b
  - **business-rule trigger**? (money/policy/matching/booking/inventory/regulation) → matching domain type เข้า Phase 1b
  - Pure infra/CLI/library? → skip 1b ทั้งคู่
- Present relevant roster; reuse existing scope authorization. Ask only for unresolved scope/authority; report effort only when requested.

## Step 1 — Phase 1a Foundation (business-analyst ∥ solution-architect — TRUE parallel)

Record the Phase 1a plan in the checkpoint (flags `stop=$STOP estimate=$ESTIMATE`; roster `shode-house:business-analyst` +
`shode-house:solution-architect`, parallel, independent scope; light cross-read at end, no mid-checkpoint), then dispatch
each per `output-styles/shode-house.md` § Delegation

### business-analyst draft (parallel กับ solution-architect)
- BRD: objective, scope, stakeholder + RACI
- User Stories + AC (Given-When-Then)
- As-is / To-be process (Mermaid)
- Event Storming (ถ้า complex domain)
- RTM (BR → FR → test)
- Assumption + open questions

### solution-architect draft (parallel กับ business-analyst)
- C4 Context + Container
- Tech stack + เหตุผล
- NFR table
- ADR candidates (3-5)
- Threat model (STRIDE)
- DR/BCP (RTO/RPO)
- Risk register

### Light cross-read (NOT cross-feedback round — ลด token)
- business-analyst check: FR ขัด ADR ของ solution-architect ไหม → ping resolve
- solution-architect check: ADR support FR ครบไหม → ping resolve
- (1 pass สั้น ๆ, ไม่ใช่ multi-round Coop)

### Sign-off + task note (compact)
Post as a task note in the confirmed tracker:
```
## Phase 1a — Foundation (business-analyst + solution-architect)

### BRD (business-analyst)
- FR: [count]; Story: [count]; AC: [count]
- Key risk: [1-2 line]
- Open Q: [list]

### ADR (solution-architect)
- Tech stack: [stack]
- ADR-N decisions: [list IDs + 1-line each]
- NFR p95: [target]
- Threat model: [top 3]

### Cross-validation
- FR-N ↔ ADR-M: aligned ✅
- (any unresolved → mark and escalate)
```

⏸️ **Gate: pre-spec-expand** — business-analyst + solution-architect sign-off + no unresolved conflict → unlock Phase 1b

## Step 2 — Phase 1b Conditional Expand (Sequential — read 1a baseline)

### ux-ui-designer (ถ้า frontend trigger)
ux-ui-designer reads the task (Phase 1a notes) → produces:
- Persona + JTBD + journey map (ถ้า new domain) — link business-analyst research
- IA + user flow (happy + edge + error) — Mermaid
- Wireframe low-fi → mid-fi (Figma frame link + frame ID)
- Design tokens (W3C DTCG primitive → semantic → component) → `tokens.json`
- a11y checklist (WCAG 2.1 AA + 2.2 AA — SC ของ 2.2 ที่ axe จับไม่ได้: ดู `agents/ux-ui-designer.md` § 5. Accessibility; ไม่มีองค์ประกอบนั้น = เขียน `N/A: <SC>`)
- Component state inventory: default/hover/active/focus/disabled/loading/error/empty
- **Baseline screenshot** ของ current UI (สำหรับ Phase 3a diff)
- **Acceptance criteria จาก UX angle** (ux-ui-designer's own AC ที่ Phase 3a verify)
- Hand-off bundle to developer

### Domain type (ถ้า business-rule trigger)
The domain type reads the task (Phase 1a notes) → produces:
- Schema + ER diagram (ถ้า data change)
- State machine / lifecycle (ถ้า workflow change)
- Business rule + edge case
- Compliance note **with Domain Evidence Protocol citation** (e.g., "PCI-DSS v4.0 Req 3.5.1")
- ถ้า rule ขัด BRD ของ business-analyst → ping resolve ก่อน sign-off

### Bundle → outputs/SPEC-<bd-id>.md
```markdown
# SPEC: bd-<id> — [feature]

## 1. Business (business-analyst, from 1a)
[FR + Stories + AC + Process + RTM compact]

## 2. Architecture (solution-architect, from 1a)
[Stack + ADR + NFR + Threat + DR + Risk compact]

## 3. UX/UI (ux-ui-designer, from 1b) — conditional
[Persona + Flow + Wireframe + Tokens + a11y + State Inventory + Baseline + ux-ui-designer's AC]

## 4. Domain (fintech/insurance/trading/erp/sap/booking/ecommerce-expert, from 1b) — conditional
[Schema + Lifecycle + Business Rule + Compliance + Citations]

## 5. Sign-off
- business-analyst: ✅
- solution-architect: ✅
- ux-ui-designer: ✅ (or N/A)
- [domain type]: ✅ (or N/A)
- router gate pre-spec-expand: ✅
```

## Step 3 — Phase Est (router + solution-architect — ถ้า `--estimate`)

T-shirt size (XS/S/M/L/XL) ต่อ module:
- Foundation (setup, infra)
- Per business module
- Integration
- QA

Task note:
```
## Estimation
| Module | T-shirt | Confidence | Note |
|---|---|---|---|
| Foundation | M | high | infra + auth |
| <Business-1> | L | medium | <reason> |
| QA pyramid | M | high | unit + integration + E2E |
| Integration | S | high | 2 external API |
**Total**: XL · **Confidence**: medium · **Risk drivers**: <top 3>
```

→ `outputs/04-estimation.md`

## Step 3.5 — Decompose (router + business-analyst — 🆕 v3.12, conditional)

**เข้าเมื่อ**: T-shirt รวม = **XL** · spec ครอบมากกว่า 1 module/service · หรือ AC เยอะจน 1 pipeline run ไม่จบ
**ข้ามเมื่อ**: S/M ที่ 1 bd จบได้ (แตกแล้วจ่ายค่า coordination ฟรี ๆ)

> เดิม pipeline สรุปว่างานเป็น XL มี 4 module แล้ว **เดินออกไปเป็น bd ใบเดียว** ให้ `/implement` รันรวด —
> `shode-house-routing` เขียนกฎ "XL → split into smaller bd" ไว้ แต่ไม่มี step ไหนทำจริง. Step นี้คือ step นั้น

```
โหลด `shode-house:decompose` skill → แตกจาก AC (ไม่ใช่จาก layer) → เช็คขนาด → wire blocking edge (create-then-wire 2 pass)
→ find ready tasks — verify (ต้องได้ ≥ 1 ใบ) → paste output
```
Output: ชุด bd ที่มี edge + `parent-child` กลับไปหา bd เดิม (เป็น epic) — **แทนที่จะออกไปใบเดียว**

## Step 4 — Exit Gate (router)

### If `--stop` (proposal mode)

Generate `outputs/00-proposal-summary.md`:
- Business objective (business-analyst)
- Solution overview (solution-architect C4 + ADR top 3)
- Tech headline
- Effort ballpark (จาก Estimation; ถ้าไม่มี --estimate → ตอบ "estimation not requested, add --estimate to include")
- Assumption + risk
- Next step

```
⏸️ /design-system --stop completed
✅ outputs/SPEC-<bd-id>.md
✅ outputs/00-proposal-summary.md
✅ outputs/04-estimation.md (ถ้า --estimate)

ห้าม auto-suggest /implement (proposal mode).
ถ้า user สั่ง proceed/implement ภายหลัง → the router ดำเนินต่อใน scope ที่อนุญาต ไม่ต้องให้ user พิมพ์ command เอง
```

### If no `--stop` (normal flow)

```
⏸️ Gate: pre-implement-ui (ถ้า frontend)
✅ ux-ui-designer artifact: Figma frame link + tokens.json + a11y checklist + state inventory
✅ ux-ui-designer's AC documented
✅ Domain (ถ้า trigger): regulation cite + business rule signed
✅ outputs/SPEC-<bd-id>.md saved
→ Unlock Phase 2 — frontier ใบเดียว: `/implement bd-<id>` · frontier หลายใบ concrete + file-disjoint: `drain`
```

### 🔄 Conversation-flow auto-handoff (router M2 classifier)

หลัง spec done ตรวจ authority ก่อน: ถ้าคำขอเดิมอนุญาต implementation แล้วให้ดำเนินต่อใน scope เดิม ตัวอย่างด้านล่างใช้กับ design-only engagement ที่ยังขาด implementation authority; the router suggests /implement และ **classify user response** ตาม drift M2:

```
the router asks: "spec ready (bd-<id>). พร้อม implement, รัน /implement bd-<id> ต่อ?"

User responses → M2 classify:
  "ลุยต่อ" / "เริ่ม implement" / "ok ทำต่อเลย" / "yes" / "ต่อ"
    → M2 = approve + next-phase
    → router auto-invokes /implement bd-<id> (no manual command typing)

  "ขอดู spec ก่อน" / "เดี๋ยว" / "wait" / "หยุดไว้"
    → M2 = status
    → router: pause; show SPEC path; wait for user

  "เปลี่ยน X" / "แก้ AC" / "redo spec"
    → M2 = spec-change
    → router: reopen bd-<id> Phase 1a (business-analyst/solution-architect revise per drift M5)

  "skip ux-ui-designer" / "ไม่ต้อง Phase 3a"
    → M2 = approve + scope-modify
    → Apply explicit user scope/authority over plugin conventions; record the omitted review and its acceptance implications
    → Keep any host/project requirement that still applies; do not claim omitted UX checks passed
```

**Why this pattern**:
- ไม่เพิ่ม command/flag (3-flag rule preserved)
- User approval gate ยังอยู่ (consent = "ลุยต่อ" message)
- Low token (1 message vs 2 command invocations)
- router M2 ตัวเดิม (drift skill — ไม่ขยาย agent prompt)

**Anti-pattern (ห้าม)**:
- ❌ router invokes `/implement` โดยไม่มี authorization ครอบ implementation; reuse authorization ที่มีอยู่แล้ว ไม่ถามซ้ำ
- ❌ ตีความ silence = approve → ต้องมี explicit affirmative message
- ❌ Add `--continue` flag → ขัด 3-flag rule

## ⚠️ Rules

1. **Phase 1a independent business-analyst/solution-architect** — parallel เมื่อ host รองรับ; sequential ได้โดยรักษา scope/context แยกแล้ว cross-read ตอนรวมผล
2. 🔴 **Phase 1b sequential เท่านั้น** (ux-ui-designer + domain ต้องอ่าน 1a sign-off ก่อน start)
3. 🔴 **บังคับ ux-ui-designer's own AC** ใน 1b (Phase 3a ux-ui-designer POST จะ verify AC นี้)
4. 🔴 **บังคับ baseline screenshot** ใน 1b (สำหรับ visual diff Phase 3a)
5. ห้าม skip ux-ui-designer ถ้า touch frontend (pre-implement-ui gate block)
6. ห้าม skip domain ถ้า touch business rule (regulation/money rule risk)
7. ห้าม implement code (ใช้ `/implement` หลัง spec)
8. v3.1 — **`--stop` ต้องระบุ output destination** (default outputs/; proposal → CC ให้ product-manager review)
9. ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim

## Skill composition

- After spec → `/implement bd-<id>` (normal) หรือ STOP (`--stop`)
- After estimation (user explicit ขอ) → ส่งต่อ product-manager สำหรับ opportunity sizing + user external report
- เมื่อ Domain Evidence cite → invoke `shode-house:secure` skill ถ้า touch PII / payment / auth
- v3.1 merged `/spec-only` เข้ามาเป็น `--stop --estimate` flags (alias เก่ายัง work ผ่าน v3.x)
