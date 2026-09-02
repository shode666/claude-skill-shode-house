---
name: shode-house-workflow
description: |
  [WHAT] Workflow discipline — Phase Contract (Smart Coop) + lifecycle hooks + approval gates + worktree isolation + task tracking + token-saving runtime rules.
  [WHEN] Pipeline kickoff.
  [TRIGGER] /shode-house:workflow, "Phase Contract", "Smart Coop", "lifecycle hook", "approval gate", "worktree".
---

# shode-house — Workflow Discipline

> Oliver owns workflow. Phase Contract บังคับ. Hooks + Gates make pipeline auditable. สำหรับ Drift Defense (M1-M8) ดู `shode-house-drift` skill

---
## 🧵 Task Tracking — tracker = single source of truth ของ status/dep

Default **beads (bd)**:
```bash
bd create "..." -p1 -t feature   # create
bd ready --json                  # next unblocked
bd update <id> --notes "..."     # progress (bd active = notes only, ห้ามเขียน markdown ซ้ำ)
bd close <id> --reason "<sha> <test>"  &&  bd show <id>   # 🔴 M8 close-on-done + paste
```
- **Markdown deliverable** (BRD/ADR/SPEC/REVIEW) อยู่ `outputs/` — **status/dep = tracker เท่านั้น** (ห้าม markdown TODO list)
- abstraction: `tracker.create(title,priority,type,blockedBy?)` · `.ready()` · `.close(id)` · `.link(from,to,type)` — tracker อื่น + คำถามเลือก tracker → `smart-coop.md` § Tracker options

## 🎚️ Engagement Mode (🔴 Oliver เลือกก่อนเริ่ม)

- **AFK** — Oliver delegate ทุก phase + automated gate; user approve เฉพาะ R0 · *งานชัด scope trusted*
- **Interactive** — human approve ทุก hand-off + ทุก phase exit; R2/R1 inform · *งานใหม่/ละเอียดอ่อน/audit*
- **Hybrid** (default แนะนำ) — AFK จนถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้นไป

ทุก mode: **R0 (irreversible) ขออนุญาตเสมอ**

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
- Reference ด้วย ID/ชื่อมาตรฐาน + reuse artifact path — ไม่ paste content
- Oliver: ห้าม re-analyze สิ่งที่ agent อื่นทำแล้ว
- **Lazy load reference**: `references/languages/<lang>.md`, `references/patterns/general.md`, `references/modern-stack.md`

---

## 🔒 Run Durability (3 กฎที่ session ตายแล้วยังกู้ได้)

> Session ของ agent **ไม่ durable** — process ตาย/context เต็ม/user ปิด = state หายหมด. เรากู้ด้วย `bd` ที่มีอยู่แล้ว ไม่ต้องมี engine
> Runtime guarantee ระดับ target project (journal/idempotency/replay) = **Aaron generate** ตาม `references/patterns/durable-agent-runtime.md` — ห้าม ship engine ใน plugin

**1. Run stamp — บันทึกตอน pick bd (ไม่มี = reproduce ไม่ได้)**
```bash
bd update <id> --notes "run: plugin=v<X.Y.Z> model=<agent:model,...> started=<ISO8601> branch=<branch>"
```
postmortem/dispute ที่ไม่รู้ว่ารันด้วย prompt version ไหน = สืบไม่ได้ (มัน**เป็น**ตัวแปรที่เปลี่ยนผลลัพธ์)

**2. Approval durability — approve ผูกกับสิ่งที่เห็น ไม่ใช่ผูกกับเวลา (🔴)**
```bash
bd update <id> --notes "approved: gate=<gate> by=<who> at=<ISO8601> artifact=<path> sha=<git hash-object path>"
```
- artifact เปลี่ยนหลัง approve (sha ไม่ตรง) → **approval เป็นโมฆะ ต้องขอใหม่** ห้ามใช้ของเดิมต่อ
- ก่อนผ่าน gate ใด ๆ: re-hash artifact แล้วเทียบกับ sha ที่บันทึกไว้
- approval ที่อยู่แค่ในบทสนทนา = ไม่นับ (session ตาย = หลักฐานหาย)

**3. Resume protocol — session ตายกลาง pipeline**
```
1. bd show <id>          → อ่าน run stamp + phase ล่าสุดที่ posted
2. Read outputs/<bd-id>/state.json  → phases{} ที่ status=passed
3. ตรวจ artifact ของ phase นั้นมีอยู่จริง (ไฟล์ + sha) — มี notes แต่ไม่มีไฟล์ = ยังไม่เสร็จจริง
4. resume จาก phase แรกที่ยังไม่ passed — ห้ามรัน phase ที่ passed ซ้ำ (เสีย token + ทับ artifact)
5. R0/destructive ที่ทำไปแล้วก่อนตาย → ห้ามทำซ้ำโดยไม่ถาม (ไม่มี idempotency key)
```

**Pointer**: DoD checklist = `shode-house-deliverable` § Definition of Done (single source) — Oliver enforce ก่อนปิด bd: ทุก DoD item ต้องมี evidence path

## 🔁 Workflow Discipline (🔴 Archon-inspired)

### Phase Contract — 🔴 v3.3 PEV Loop per bd (Oliver enforce)

**Single loop: PEV (Plan → Execute → Verify → Triage) per bd** (sprint outer loop removed)

> ก่อน v3.3 มี outer sprint loop + inner per-issue loop. v3.3 = **single PEV loop per bd** — agent ส่งงาน task-complete, ไม่ time-bound. ห้าม man-day negotiation (per shode-house-discipline). Deploy = continuous per bd ready, ไม่ batched sprint-end.

```
PICK bd claim → PLAN 0 Discover* / 1a Bella∥Sara / 1b Uma*+Domain* / 1c Sentinel*
  → EXECUTE 2 Dave → VERIFY 3a Uma* → 3b Chris∥Quinn → TRIAGE 4 Oliver
  → DEPLOY 5 Aaron (continuous per bd) → OPERATE 6 Reggie          (* = conditional)

Triage routing: code/perf/security→2 · UI/design→1b · spec/AC/regulation→1a
Clean → bd close + bd show verify (M8) + bd remember · iter > 3 → STOP escalate user
```
> รายละเอียด pre/post hook ต่อ phase = ตาราง § Lifecycle Hooks ใน `smart-coop.md` (single source)

**Key rules**: ❌ ไม่มี outer sprint loop · ✅ Patrick OKR + Deploy = continuous per-bd · ✅ per-bd reflect ใน Phase 4 Triage

> **Why 1a + 1b แทน 4-way parallel**: Uma + Domain ต้องอ่าน spec ก่อน design/validate → 4-way + cross-read = ~40% redundant token. 1a (Bella ∥ Sara) + 1b (read 1 spec baseline) = quality สูง token ต่ำ
> **Why 3a before 3b**: UI bug ตรวจที่ Uma ก่อน — Chris/Quinn ไม่เสีย effort review code ที่ design ผิด
> **Phase routing precision**: Triage แยก code/UI/spec → loop กลับ phase ที่เหมาะ (1a vs 1b vs 2)

---

## 🤝 Smart Coop Pattern — parallel where independent, sequential gate where dependent

**Smart Coop ≠ everything parallel.** parallel เฉพาะที่ agent **truly independent** (ไม่มี read dependency); sequential gate ที่มี natural dependency

| Phase | Pattern |
|---|---|
| 1a Bella ↔ Sara · 3b Chris ↔ Quinn · Dave#1 ↔ Dave#2 (คนละไฟล์) | **Parallel** |
| 1a → 1b · 2 → 3a · 3a → 3b | **Sequential gate** |

🔴 **จะรัน pipeline จริง → โหลด `smart-coop.md` ก่อน** (อยู่ข้าง SKILL.md นี้): phase pattern ต่อ phase · anti-pattern ที่จะถูก block · `state.json` schema + resume · **Lifecycle Hooks ต่อ phase** · **10 approval gates** · Phase 0 scope-clarify flow · worktree isolation · prompt template
ห้าม orchestrate จากความจำ — เนื้อหาอยู่ในไฟล์แล้ว (NO MAGIC)

## 📚 Reference Files (lazy-load)

| ไฟล์ | โหลดเมื่อ |
|---|---|
| `smart-coop.md` (ข้าง SKILL.md นี้) | จะรัน/ย้าย phase ของ pipeline จริง |
| `wayfinding.md` (ข้าง SKILL.md นี้) | 🆕 งานใหญ่เกิน 1 session **และยังมองไม่เห็นทาง** — Map + decision ticket ก่อนเข้า Phase 0 |
| `references/patterns/durable-agent-runtime.md` | Aaron/Sara generate runner ที่ต้องการ retry/checkpoint/journal |
| `references/languages/<lang>.md` · `references/patterns/general.md` · `references/modern-stack.md` | ตาม stack ที่แตะ |
