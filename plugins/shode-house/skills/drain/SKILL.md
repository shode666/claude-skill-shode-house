---
name: drain
description: Batch-drain ready tickets with isolated workers, independent review, serial merge and evidenced closure (จัดงานที่พร้อม, ปิดงานค้าง). For work not split into concrete, independent tickets, use decompose.
---

# Drain (verified backlog → parallel worktree → serial merge → close-on-done)

> **Owner**: router (route + own the run). Impl/verify: developer · code-reviewer · qa-engineer · devops-engineer · ux-ui-designer; security item → security-engineer
> Before dispatch/resume, read `skills/discipline/shode-house-workflow/harness.md`. Its authority, reviewer triggers and recovery contract apply to each item. Use the project's confirmed tracker, including Markdown (harness § Source of truth); tracker verbs here are neutral — find ready / read / note / close / link — and Beads commands in `harness.md` are an example, not a prerequisite. router owns tracker writes; unavailable updates remain pending sync, never claimed CLOSED.
> แก้ 2 failure mode: **stale-open task** · **git race / tree collision**

## When NOT to use

- **Item interdependent** — ถ้า B ต้องใช้ output ของ A = ไม่ parallel-safe → sequence หรือรวมเป็น agent เดียว
- **Item แตะไฟล์เดียวกัน** — รวมเป็น **1 agent** (parallel worktree แก้ไฟล์เดียวกัน → conflict ตอน cherry-pick). Group by file-locality ก่อนเสมอ
- **Design / architecture / feature shape ใหม่** — route ไป Phase 1a/1b (`design-system`: business-analyst/solution-architect/ux-ui-designer) ก่อน; drain implement เฉพาะ item ที่ fix **concrete แล้ว** (file:line + direction)
- **Owner / counsel / billing decision** — agent ทำเสร็จเองไม่ได้ → เอาออกจาก run
- **> ~20 item** — แตกเป็นรอบ (report + close ระหว่างรอบ) ห้าม fan-out ไม่จำกัด
- **มีแค่ list/count ของ tracker เป็นหลักฐาน** — ดู § Stop and return: verify set ก่อน, list โกหกได้
- **Production outage** — ใช้ `incident` (mitigate ก่อน) ไม่ใช่ batch drain

## Inputs and decision boundaries

Derive first: item facts (open state, blockers, acceptance revision, `file:line`) come from each authoritative task record and the repo — read them, do not ask or assume. Still missing → return the question to router.
When to ask → `shode-house-discipline` § Ask vs derive

### Stop and return

ขาดข้อใด → list สิ่งที่ขาด ส่งกลับ caller **ก่อน** fan-out

- [ ] **Ready set with verified dependencies** — use `decompose` for oversized/abstract work, not independent items with an explicitly verified empty blocker list. Recheck current blockers before dispatch; a legitimately empty ready set means checkpoint, not fan-out.
- [ ] **Verified-open set** — read each candidate's authoritative task record and acceptance revision; list counts and passive exports alone do not prove readiness.
- [ ] **Per-item concrete scope** — `file:line` + fix direction ฝังใน brief ของแต่ละ item.
      Pass canonical ID, acceptance IDs/revision, relevant paths and non-goals. Verify worker access; send only necessary excerpts with provenance when paths are inaccessible. Do not copy the whole backlog/chat or assume tracker access from a worktree.
- [ ] **Routing** — router assign owner agent ต่อ item + ยืนยัน parallel-safe / file-disjoint
- [ ] **Owner greenlight + scope** — subset ไหน (security / code-gap / test) หรือทั้งหมด; full drain = multi-agent token spend ก้อนใหญ่ → ต้อง opt-in

## 9 Invariants (map เข้า 5 Philosophy)

| # | Invariant | Maps to |
|---|-----------|---------|
| 1 | **VERIFY BEFORE DONE** — ทุก agent paste test output จริง (red→green); ห้าม "น่าจะ work" | NO MAGIC / VERIFY |
| 2 | **CLOSE ON DONE** — independent review + integrated acceptance + closure authority, then close/read-back in the confirmed tracker; unavailable sync stays pending | ปิดช่อง stale-open |
| 3 | **NO FALSE CLOSE** — BLOCKED / PARTIAL / owner-gated **คงสถานะ OPEN** + note ตรงไปตรงมา | DISSENT / evidence |
| 4 | **FALSE-POSITIVE honesty** — ถ้า "bug" ถูกอยู่แล้ว → return `FALSE_POSITIVE` พร้อม proof; ห้ามแต่ง fix | NO MAGIC |
| 5 | **Worktree isolation** — 1 worktree ใหม่ต่อ agent; ห้าม shared working tree | parallel-safe |
| 6 | **No push in worktree** — commit only when authorized, otherwise return patch/content revision; main integrates serially into the confirmed target | SCOPE / safety |
| 7 | **Scope-lock + no-delete** — agent แก้เฉพาะไฟล์ของ item ตัวเอง, **ห้ามลบไฟล์ที่ตัวเองไม่ได้สร้าง** | scope drift guard |
| 8 | **Resource-aware tests** — serialize shared integration/E2E resources unless isolation is verified; required tests pass before acceptance/closure, not merely before deploy | evidence realism |
| 9 | **Conflict ต้องมีร่องรอย** — abort+regroup หรือ resolve+evidence; ห้ามจบเงียบ (ดู `execution.md` § Conflict protocol); abort เฉพาะ operation ที่ run นี้เริ่ม และต้องไม่ทิ้ง edit ของ user/manual; ไม่ปลอดภัย/ไม่มีอำนาจ → preserve state + BLOCKED | NO MAGIC / VERIFY |

## Flow

```
verify set (read each task record)
   ↓
router route + group by file-locality
   ↓
FAN-OUT  (isolated writers — TDD, authorized commit or patch, NO push)
   ↓
main loop: authorized serial integration into confirmed target; stop on failure
   ↓
independent review + integrated required gates → authorized publish only
   ↓
close accepted items + read-back; unavailable remote updates remain pending sync
   ↓
report: closed / false-positive / still-open / รอบถัดไป
```

## Step 1 — Verify the open set (🔴 tracker list โกหก)

Find the ready/open candidates in the confirmed tracker, union with any tracked export, then read each task record one by one.
Tracker command examples (Beads) → `harness.md` § Beads example.

ยืนยันต่อ item: **สถานะจริง = open** · scope concrete (`file:line`) · ไม่มี dep ค้าง
ตัวไหน confirm ไม่ได้ → เอาออกจาก run (ห้ามเดา)

## Step 2 — Route + group by file-locality (router)

1. Map item → owner agent (`shode-house-routing`): code → developer · test/unit → code-reviewer · integration/E2E → qa-engineer · infra/CI → devops-engineer · UI → ux-ui-designer · security → security-engineer
2. **Group by file** — item ที่แตะไฟล์ชุดเดียวกัน = รวมเป็น **1 agent 1 branch**
3. ยืนยัน disjoint จริงก่อน fan-out:

```bash
# ทุก item ต้อง declare planned files; ตรวจซ้ำก่อนรัน
sort /tmp/drain-files.txt | uniq -d   # ต้องว่าง — ไม่ว่าง = ต้อง merge item เข้าด้วยกัน
```

4. Post Engagement note on each item in the confirmed tracker: `drain round N: owner=<agent> files=[...]`

## Step 3–4 — Fan-out + serial merge (lazy reference)

Load `skills/ops/drain/execution.md` **only after eligibility is confirmed** (When NOT to use clear · § Stop and return clear · Step 1–2 done) and before the first dispatch. It holds the COMMON worker brief, runners, serial integration, resume checkpoint, conflict protocol and evidence examples. Eligibility not confirmed → stop and return the missing inputs; do not load it and do not fan out.

## Step 5 — Close on done (🔴 anti-puppet — run ยังไม่จบจนกว่าครบ)

Close each accepted item in the confirmed tracker with reason `<verdict> <commit_sha or content hash> <test_result>`, then read the record back: ต้องอ่านได้ว่า CLOSED — นี่คือหลักฐาน ไม่ใช่คำพูดของ agent. Tracker unavailable → pending sync, never claimed CLOSED.

| Verdict | Action |
|---------|--------|
| `FIXED` (worker result) | candidate only; independent review + integrated required checks + authority precede close/read-back |
| `FALSE_POSITIVE` | independently verify proof against current acceptance; close as invalid only with authority, otherwise retain for triage |
| `PARTIAL` / `BLOCKED` | **คง OPEN** + note ใน confirmed tracker บอกว่าติดอะไร + owner ถัดไป |

**Drift guard**: a worker FIXED return is not task completion. Only accepted items with authoritative closure may be reported CLOSED; pending review, failed integration or unavailable tracker updates remain explicitly incomplete.
(ดู `shode-house-workflow/drift.md` § M8 (ห้าม claim "ปิดแล้ว" โดยไม่ paste output))

## Round cap

- ≤ ~20 items per batch, not concurrency. Default active writers ≤ 3, reduced by actual host/resource limits; queue the rest and recheck readiness before refill.
- รอบถัดไปเริ่มที่ Step 1 ใหม่ (verify set ใหม่ — งานรอบก่อนอาจ spawn discovered item ที่ link กลับ item เดิม)
- 3 รอบแล้วยังมี item ค้าง BLOCKED เดิม → **หยุด escalate owner** (ไม่ใช่ปัญหาที่ fan-out ช่วยได้)

## ห้าม

- ห้าม seed run จาก list/count ของ tracker โดยไม่อ่าน task record ทีละตัว
- ห้าม fan-out item ที่แตะไฟล์ทับกัน
- ห้าม agent `push` จาก worktree
- ห้าม close โดยไม่มี verified artifact revision (commit or content hash), required review/test evidence and closure authority
- ห้าม close `PARTIAL` / `BLOCKED` เพื่อให้ตัวเลขสวย
- ห้ามรัน shared integration/E2E resources ขนานโดยไม่ยืนยัน isolation; required checks must precede closure
- ห้าม agent ลบไฟล์ที่ตัวเองไม่ได้สร้าง
- ห้ามจบ run โดยไม่ report item ที่ยัง OPEN

## Skill composition (where to go next)

| Situation | Next skill | Reason |
|---|---|---|
| ยังไม่มี item list / ไม่รู้ใครรับ | → `shode-house-routing` | router produce item list + owner ต่อ item ก่อน drain |
| Item ยัง abstract (ไม่มี file:line) | → `diagnose` แล้วค่อยกลับมา | ต้อง root cause ก่อน |
| ต้องการ spec/design ก่อน | → `design-system` | — |
| TDD discipline ต่อ item | → `dev-gate` | red-green-refactor + quality gate ภายใน agent แต่ละตัว |
| Reviewer lens ตอน verify | → `review-checklist` | code-reviewer 7-dim / qa-engineer matrix สำหรับ item ที่ต้อง review ลึก |
| Definition of Done | → `shode-house-deliverable` | acceptance + authorized closure/read-back in confirmed tracker; unavailable sync remains pending, not CLOSED |
| ปิดไม่ครบ / อ้างว่าปิดแล้ว | → `shode-house-workflow/drift.md` § M8 | Close-on-Done Guard (anti-puppet บน close step) |

Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ under this plugin's knowledge/ directory, not the user's project.
Resolve paths beginning ./ or ../ from this file's own directory; resolve other relative file names in this skill under this plugin's knowledge/skills/ops/drain/ directory.
Use actual host tools and preserve host/project/user authority.
No shode-house safety floor in this context (a main session without the router style)? Load `shode-house:ask` first.
