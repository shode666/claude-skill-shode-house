---
name: shode-house-workflow
description: Coordinate multi-phase delivery with phase gates, recorded approvals, run recovery and drift detection, governing how work proceeds, not who owns it.
---

# shode-house — Workflow Discipline

เริ่ม/resume engagement หรือก่อน delegate ครั้งแรก: อ่าน `harness.md` ข้างไฟล์นี้
เพื่อยืนยัน source of truth, host tools, owner, checkpoint และการ reconcile UNKNOWN

> Oliver owns workflow. Phase Contract บังคับ. Hooks + Gates make pipeline auditable. สำหรับ Drift Defense (M1-M8) ดู `shode-house-drift` skill

---
## 🧵 Task Tracking — tracker = single source of truth ของ status/dep

เลือก source of truth ตาม project ที่ user ยืนยัน (ดู `harness.md`); ไม่มีของเดิมใช้ Markdown ได้ทุก concern. ตัวอย่างต่อไปนี้สำหรับ project ที่เลือก **beads (bd)** เท่านั้น:
```bash
bd create "..." -p1 -t feature   # create
bd ready --json                  # next unblocked
bd update <id> --notes "..."     # Beads example: progress + link to the confirmed evidence home
bd close <id> --reason "<sha> <test>"  &&  bd show <id>   # 🔴 M8 close-on-done + paste
```
- **Markdown deliverable** (BRD/ADR/SPEC/REVIEW) อยู่ตำแหน่งที่ project เลือก; status/dep อยู่ canonical record เดียว ซึ่งอาจเป็น Markdown ได้
- abstraction: `tracker.create(title,priority,type,blockedBy?)` · `.ready()` · `.close(id)` · `.link(from,to,type)` — tracker อื่น + คำถามเลือก tracker → `smart-coop.md` § Tracker options

## 🎚️ Engagement Mode (🔴 Oliver เลือกก่อนเริ่ม)

- **AFK** — proceed through applicable phases within recorded scope/authority; unattended mode does not waive deployment, external-write or business-policy approval. Missing authority becomes a checkpointed blocker.
- **Interactive** — human approve ทุก hand-off + ทุก phase exit; R2/R1 inform · *งานใหม่/ละเอียดอ่อน/audit*
- **Hybrid** (default แนะนำ) — AFK จนถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้นไป

ทุก mode: **R0 (irreversible) ขออนุญาตเสมอ**

## 🚦 Phase orchestration — ห้าม (🔴 Oliver enforce, ย้ายมาจาก discipline v3.10)

- Phase 1a Bella/Sara ใช้ independent context; parallel เมื่อ host รองรับและไม่มี dependency มิฉะนั้น sequential ได้. Phase 1b Uma/Domain ต้องอ่าน 1a spec ที่รวมแล้วก่อน design/validate
- UI changed → ห้าม skip Phase 3a Uma POST gate. Pure backend → บันทึก not-applicable พร้อม diff evidence แล้วเข้า 3b ได้
- Phase 3b Chris/Quinn ตรวจคนละ scope และ verdict อิสระ; parallel เมื่อทำได้ หรือ sequential คนละ context โดยห้ามคัดลอก verdict กัน
- 🔴 ห้าม skip Phase 4 Triage routing. Review fail → loop ไป phase ที่ตรง finding (code→2, UI→1b, spec→1a); ห้าม "ผ่านครึ่ง ๆ" ข้ามไป Deploy
- ห้าม close Phase 3 (3a/3b) ก่อน review report อยู่ใน evidence home ที่ project ยืนยัน; task record เก็บ link ไม่ copy ซ้ำ. ใช้ REVIEW Report Format

---

## 🔧 Token-saving (🔴 runtime)

- Search source code narrowly and read relevant context. Selected role/skill instructions must still be read completely as required; do not truncate safety rules to save tokens.
- Use available documentation tools and primary sources; tool names are host-specific. A search snippet or link alone is not verified evidence.
- Reuse accessible artifact paths and matching revisions; provide necessary excerpts when the receiver cannot access them.
- Oliver reuses specialist analysis, but must check returned artifacts, conflicting findings and stale evidence against acceptance; avoiding duplicate work never means blind trust.
- **Lazy load reference**: `references/languages/<lang>.md`, `references/patterns/general.md`, `references/modern-stack.md`

---

## 🔒 Run Durability (3 กฎที่ session ตายแล้วยังกู้ได้)

> Sessions are not durable. Use the confirmed project record per `harness.md`, not a second required JSON/SESSION-STATE store. Project runtime engineering is separate authorized work, not a plugin prerequisite.

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
1. Read the current canonical checkpoint: run stamp, phase, owners, outstanding gates.
2. Verify referenced artifacts/revisions; records without artifacts do not prove completion.
3. Reuse passed evidence only for matching scope/content/environment; recheck changed dependencies.
4. Reconcile UNKNOWN external operations from intent, stable key and authoritative receipts.
5. Never repeat an uncertain effect merely because the user says yes; unresolved outcome remains blocked per harness.md.
```

**Pointer**: DoD checklist = `shode-house-deliverable/definition-of-done.md` § Definition of Done (single source) — Oliver enforce ก่อนปิด bd: ทุก DoD item ต้องมี evidence path

## 🔁 Workflow Discipline (🔴 Archon-inspired)

### Phase Contract — 🔴 v3.3 PEV Loop per bd (Oliver enforce)

**Single loop: PEV (Plan → Execute → Verify → Triage) per bd** (sprint outer loop removed)

> Task-complete, not time-bound; ห้าม man-day negotiation. Deploy only when ready and authorized, not batched by sprint.

```
PICK bd claim → PLAN 0 Discover* / 1a Bella∥Sara / 1b Uma*+Domain* / 1c Sentinel*
  → EXECUTE 2 Dave → VERIFY 3a Uma* → 3b Chris∥Quinn → TRIAGE 4 Oliver
  → DEPLOY 5 Aaron (continuous per bd) → OPERATE 6 Reggie          (* = conditional)

Triage routing: code/perf/security→2 · UI/design→1b · spec/AC/regulation→1a
Clean + closure authority → tracker close + read-back (M8); unresolved at third review/fix iteration → STOP, checkpoint and escalate
```
> รายละเอียด pre/post hook ต่อ phase = ตาราง § Lifecycle Hooks ใน `smart-coop.md` (single source)

**Key rules**: ❌ ไม่มี outer sprint loop · ✅ Patrick OKR + Deploy = continuous per-bd · ✅ per-bd reflect ใน Phase 4 Triage

> Uma/Domain consume one approved baseline. UI gates precede downstream review; failures return to the affected phase. Measure token savings, never assume a fixed percentage.

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
