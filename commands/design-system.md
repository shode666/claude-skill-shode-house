---
description: "[shode-house] Smart Spec pipeline (Phase 1a Bella + Sara parallel; Phase 1b Uma + Domain conditional). Flags: --stop = หยุดที่ spec ไม่ suggest implement (proposal mode); --estimate = เพิ่ม T-shirt sizing step"
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[bd-id | system description] [--stop] [--estimate]"
---

📝 **Spec phase** สำหรับ: **$ARGUMENTS**

> v3.1: รวม `/spec-only` เข้ามาเป็น `--stop --estimate` flags. Pipeline = parallel foundation (Bella + Sara) → conditional sequential expand (Uma + Domain) → optional estimation → optional stop.

## Flag parsing (Oliver step 0)

```bash
STOP=false
ESTIMATE=false
ARGS=$(echo "$ARGUMENTS" | sed -E 's/--stop|--estimate//g' | xargs)

[[ "$ARGUMENTS" == *--stop* ]] && STOP=true
[[ "$ARGUMENTS" == *--estimate* ]] && ESTIMATE=true

# Sanity: --stop มักไปคู่กับ --estimate (proposal mode ต้องการ effort number)
# ถ้า --stop ไม่มี --estimate → ถาม user 1 ครั้ง: "proposal mode ต้องการ estimation ด้วยมั้ย?"
```

| Flag combo | Mode | Use case |
|---|---|---|
| (none) | spec → suggest /implement | normal feature design |
| `--estimate` | spec + estimation → suggest /implement | when user explicit ขอ effort for external report |
| `--stop` | spec → STOP (no implement suggest) | review-only / docs |
| `--stop --estimate` | spec + estimation → STOP + summary | **proposal / quotation** (replaces /spec-only) |

## Step 0 — Triage (Oliver)

- Pick bd issue (`bd show <id>` ถ้ามี argument) หรือสร้างใหม่ (`bd create -t feature -p1 "..."`)
- Trigger detection:
  - **frontend trigger**? (touch UI/component/page/view/email/dashboard) → Uma เข้า Phase 1b
  - **business-rule trigger**? (money/policy/matching/booking/inventory/regulation) → Domain Expert เข้า Phase 1b
  - Pure infra/CLI/library? → skip 1b ทั้งคู่
- Present roster + estimated effort → user approve

## Step 1 — Phase 1a Foundation (Bella ∥ Sara — TRUE parallel)

Oliver kickoff broadcast:
```
[Oliver|state:1a|bd:42] Phase 1a start (flags: stop=$STOP estimate=$ESTIMATE)
- Roster: Bella + Sara (parallel, independent scope)
- bd: bd-42
- Budget: [T-shirt]
- Light cross-read at end (no mid-checkpoint)
```

### Bella draft (parallel กับ Sara)
- BRD: objective, scope, stakeholder + RACI
- User Stories + AC (Given-When-Then)
- As-is / To-be process (Mermaid)
- Event Storming (ถ้า complex domain)
- RTM (BR → FR → test)
- Assumption + open questions

### Sara draft (parallel กับ Bella)
- C4 Context + Container
- Tech stack + เหตุผล
- NFR table
- ADR candidates (3-5)
- Threat model (STRIDE)
- DR/BCP (RTO/RPO)
- Risk register

### Light cross-read (NOT cross-feedback round — ลด token)
- Bella check: FR ขัด ADR ของ Sara ไหม → ping resolve
- Sara check: ADR support FR ครบไหม → ping resolve
- (1 pass สั้น ๆ, ไม่ใช่ multi-round Coop)

### Sign-off + bd notes (compact)
```bash
bd update <id> --notes "$(cat <<EOF
## Phase 1a — Foundation (Bella + Sara)

### BRD (Bella)
- FR: [count]; Story: [count]; AC: [count]
- Key risk: [1-2 line]
- Open Q: [list]

### ADR (Sara)
- Tech stack: [stack]
- ADR-N decisions: [list IDs + 1-line each]
- NFR p95: [target]
- Threat model: [top 3]

### Cross-validation
- FR-N ↔ ADR-M: aligned ✅
- (any unresolved → mark and escalate)
EOF
)"
```

⏸️ **Gate: pre-spec-expand** — Bella+Sara sign-off + no unresolved conflict → unlock Phase 1b

## Step 2 — Phase 1b Conditional Expand (Sequential — read 1a baseline)

### Uma (ถ้า frontend trigger)
Uma reads `bd show <id>` (Phase 1a notes) → produces:
- Persona + JTBD + journey map (ถ้า new domain) — link Bella research
- IA + user flow (happy + edge + error) — Mermaid
- Wireframe low-fi → mid-fi (Figma frame link + frame ID)
- Design tokens (W3C DTCG primitive → semantic → component) → `tokens.json`
- a11y checklist (WCAG 2.1/2.2 AA)
- Component state inventory: default/hover/active/focus/disabled/loading/error/empty
- **Baseline screenshot** ของ current UI (สำหรับ Phase 3a diff)
- **Acceptance criteria จาก UX angle** (Uma's own AC ที่ Phase 3a verify)
- Hand-off bundle to Dave

### Domain Expert (ถ้า business-rule trigger)
Domain reads `bd show <id>` (Phase 1a notes) → produces:
- Schema + ER diagram (ถ้า data change)
- State machine / lifecycle (ถ้า workflow change)
- Business rule + edge case
- Compliance note **with Domain Evidence Protocol citation** (e.g., "PCI-DSS v4.0 Req 3.5.1")
- ถ้า rule ขัด BRD ของ Bella → ping resolve ก่อน sign-off

### Bundle → outputs/SPEC-<bd-id>.md
```markdown
# SPEC: bd-<id> — [feature]

## 1. Business (Bella, from 1a)
[FR + Stories + AC + Process + RTM compact]

## 2. Architecture (Sara, from 1a)
[Stack + ADR + NFR + Threat + DR + Risk compact]

## 3. UX/UI (Uma, from 1b) — conditional
[Persona + Flow + Wireframe + Tokens + a11y + State Inventory + Baseline + Uma's AC]

## 4. Domain (Felix/Iris/Tara/Elena/Sam/Brooke/Emma, from 1b) — conditional
[Schema + Lifecycle + Business Rule + Compliance + Citations]

## 5. Sign-off
- Bella: ✅
- Sara: ✅
- Uma: ✅ (or N/A)
- [Domain]: ✅ (or N/A)
- Oliver gate pre-spec-expand: ✅
```

## Step 3 — Phase Est (Oliver + Sara — ถ้า `--estimate`)

T-shirt size (XS/S/M/L/XL) ต่อ module:
- Foundation (setup, infra)
- Per business module
- Integration
- QA

```bash
bd update <id> --notes "
## Estimation
| Module | T-shirt | Confidence | Note |
|---|---|---|---|
| Foundation | M | high | infra + auth |
| <Business-1> | L | medium | <reason> |
| QA pyramid | M | high | unit + integration + E2E |
| Integration | S | high | 2 external API |
**Total**: XL · **Confidence**: medium · **Risk drivers**: <top 3>
"
```

→ `outputs/04-estimation.md`

## Step 4 — Exit Gate (Oliver)

### If `--stop` (proposal mode)

Generate `outputs/00-proposal-summary.md`:
- Business objective (Bella)
- Solution overview (Sara C4 + ADR top 3)
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
ถ้า user สั่ง proceed → user ต้องเรียก /implement bd-<id> เอง
```

### If no `--stop` (normal flow)

```
⏸️ Gate: pre-implement-ui (ถ้า frontend)
✅ Uma artifact: Figma frame link + tokens.json + a11y checklist + state inventory
✅ Uma's AC documented
✅ Domain (ถ้า trigger): regulation cite + business rule signed
✅ outputs/SPEC-<bd-id>.md saved
→ Unlock Phase 2 — call /implement bd-<id>
```

### 🔄 Conversation-flow auto-handoff (🆕 v3.2 — Oliver M2 classifier)

หลัง spec done, Oliver suggest /implement และ **classify user response** ตาม drift M2:

```
Oliver: "spec ready (bd-<id>). พร้อม implement, รัน /implement bd-<id> ต่อ?"

User responses → M2 classify:
  "ลุยต่อ" / "เริ่ม implement" / "ok ทำต่อเลย" / "yes" / "ต่อ"
    → M2 = approve + next-phase
    → Oliver auto-invoke /implement bd-<id> (no manual command typing)

  "ขอดู spec ก่อน" / "เดี๋ยว" / "wait" / "หยุดไว้"
    → M2 = status
    → Oliver: pause; show SPEC path; wait for user

  "เปลี่ยน X" / "แก้ AC" / "redo spec"
    → M2 = spec-change
    → Oliver: reopen bd-<id> Phase 1a (Bella/Sara revise per drift M5)

  "skip Uma" / "ไม่ต้อง Phase 3a"
    → M2 = approve + scope-modify
    → ❌ Oliver REJECT: pre-implement-ui gate mandatory if frontend trigger (per implement.md Step 0)
    → Re-explain + wait for valid response
```

**Why this pattern**:
- ไม่เพิ่ม command/flag (CLAUDE.md 3-flag rule preserved)
- User approval gate ยังอยู่ (consent = "ลุยต่อ" message)
- Low token (1 message vs 2 command invocations)
- Oliver M2 ตัวเดิม (drift skill — ไม่ขยาย agent prompt)

**Anti-pattern (ห้าม)**:
- ❌ Oliver auto-invoke `/implement` โดยไม่รอ user response → bypass approval gate
- ❌ ตีความ silence = approve → ต้องมี explicit affirmative message
- ❌ Add `--continue` flag → ขัด 3-flag rule

## ⚠️ Rules

1. 🔴 v2.8 — **Phase 1a parallel เท่านั้น** (ห้าม Bella → Sara serialize; ห้าม mid-checkpoint cross-read หนัก)
2. 🔴 v2.8 — **Phase 1b sequential เท่านั้น** (Uma + Domain ต้องอ่าน 1a sign-off ก่อน start)
3. 🔴 v2.8 — **บังคับ Uma's own AC** ใน 1b (Phase 3a Uma POST จะ verify AC นี้)
4. 🔴 v2.8 — **บังคับ baseline screenshot** ใน 1b (สำหรับ visual diff Phase 3a)
5. ห้าม skip Uma ถ้า touch frontend (pre-implement-ui gate block)
6. ห้าม skip Domain ถ้า touch business rule (regulation/money rule risk)
7. ห้าม implement code (ใช้ `/implement` หลัง spec)
8. 🔴 v3.1 — **`--stop` ต้องระบุ output destination** (default outputs/; proposal → CC ให้ Patrick review)
9. ภาษาไทย

## Skill composition

- After spec → `/implement bd-<id>` (normal) หรือ STOP (`--stop`)
- After estimation (user explicit ขอ) → ส่งต่อ Patrick (PM) สำหรับ opportunity sizing + user external report
- เมื่อ Domain Evidence cite → invoke `secure` skill ถ้า touch PII / payment / auth
- v3.1 merged `/spec-only` เข้ามาเป็น `--stop --estimate` flags (alias เก่ายัง work ผ่าน v3.x)
