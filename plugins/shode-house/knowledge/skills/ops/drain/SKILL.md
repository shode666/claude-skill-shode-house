---
name: drain
description: Deliver a verified set of independent, concrete, ready tasks using isolated workers, bounded concurrency, independent review, serial integration and evidence-backed closure. Not for interdependent or still-abstract work, new design decisions, or a production outage.
---

# Drain (verified backlog → parallel worktree → serial merge → close-on-done)

> **Owner**: Oliver (route + own the run). Impl/verify: Dave · Chris · Quinn · Aaron · Uma; security item → Sentinel
> Before dispatch/resume, read `skills/discipline/shode-house-workflow/harness.md`. Its authority, reviewer triggers and recovery contract apply to each item. Use the confirmed tracker, including Markdown; Beads commands below are examples, not prerequisites. Oliver owns tracker writes; unavailable updates remain pending sync, never claimed CLOSED.
> Skill นี้แก้ **2 failure mode ที่วัดได้จริง**: (1) **stale-open bd** — งานเสร็จ แต่ไม่มีใครปิด (2) **git race / tree collision** ตอน agent หลายตัวแตะ trunk พร้อมกัน

## When NOT to use

- **Item interdependent** — ถ้า B ต้องใช้ output ของ A = ไม่ parallel-safe → sequence หรือรวมเป็น agent เดียว
- **Item แตะไฟล์เดียวกัน** — รวมเป็น **1 agent** (parallel worktree แก้ไฟล์เดียวกัน → conflict ตอน cherry-pick). Group by file-locality ก่อนเสมอ
- **Design / architecture / feature shape ใหม่** — route ไป Phase 1a/1b (`design-system`: Bella/Sara/Uma) ก่อน; drain implement เฉพาะ item ที่ fix **concrete แล้ว** (file:line + direction)
- **Owner / counsel / billing decision** — agent ทำเสร็จเองไม่ได้ → เอาออกจาก run
- **> ~20 item** — แตกเป็นรอบ (report + close ระหว่างรอบ) ห้าม fan-out ไม่จำกัด
- **มีแค่ `bd list` เป็นหลักฐาน** — ดู § Required inputs: verify set ก่อน, `bd list` โกหกได้
- **Production outage** — ใช้ `incident` (mitigate ก่อน) ไม่ใช่ batch drain

## Required inputs — refuse without

- [ ] **Ready set with verified dependencies** — use `decompose` for oversized/abstract work, not independent items with an explicitly verified empty blocker list. Recheck current blockers before dispatch; a legitimately empty ready set means checkpoint, not fan-out.
- [ ] **Verified-open set** — read each candidate's authoritative task record and acceptance revision; list counts and passive exports alone do not prove readiness.
- [ ] **Per-item concrete scope** — `file:line` + fix direction ฝังใน brief ของแต่ละ item.
      Pass canonical ID, acceptance IDs/revision, relevant paths and non-goals. Verify worker access; send only necessary excerpts with provenance when paths are inaccessible. Do not copy the whole backlog/chat or assume tracker access from a worktree.
- [ ] **Routing** — Oliver assign owner agent ต่อ item + ยืนยัน parallel-safe / file-disjoint
- [ ] **Owner greenlight + scope** — subset ไหน (security / code-gap / test) หรือทั้งหมด; full drain = multi-agent token spend ก้อนใหญ่ → ต้อง opt-in

ขาดข้อใด → list สิ่งที่ขาด ส่งกลับ caller **ก่อน** fan-out

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
| 9 | **Conflict ต้องมีร่องรอย** — abort+regroup หรือ resolve+evidence; ห้ามจบเงียบ (ดู § Conflict protocol) | NO MAGIC / VERIFY |

## Flow

```
verify set (bd show ทีละตัว)
   ↓
Oliver route + group by file-locality
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

## Step 1 — Verify the open set (🔴 `bd list` โกหก)

```bash
bd list --json | jq -r '.[].id' > /tmp/drain-list.txt
# union กับ tracked export ถ้ามี แล้ว confirm ทีละตัว:
while read -r id; do bd show "$id"; done < /tmp/drain-list.txt
```

ยืนยันต่อ item: **สถานะจริง = open** · scope concrete (`file:line`) · ไม่มี dep ค้าง
ตัวไหน confirm ไม่ได้ → เอาออกจาก run (ห้ามเดา)

## Step 2 — Route + group by file-locality (Oliver)

1. Map item → owner agent (`shode-house-routing`): code → Dave · test/unit → Chris · integration/E2E → Quinn · infra/CI → Aaron · UI → Uma · security → Sentinel
2. **Group by file** — item ที่แตะไฟล์ชุดเดียวกัน = รวมเป็น **1 agent 1 branch**
3. ยืนยัน disjoint จริงก่อน fan-out:

```bash
# ทุก item ต้อง declare planned files; ตรวจซ้ำก่อนรัน
sort /tmp/drain-files.txt | uniq -d   # ต้องว่าง — ไม่ว่าง = ต้อง merge item เข้าด้วยกัน
```

4. Post Engagement note: `bd update <id> --notes "drain round N: owner=<agent> files=[...]"`

## Step 3 — Fan-out (worktree agent ต่อ item)

**COMMON brief** (ฝังในทุก agent prompt — sub-agent เกิดใน context ว่าง):

```
ทำเฉพาะ assigned item ใน verified isolated workspace. Oliver owns tracker writes. Load role/prerequisites and accessible acceptance/evidence; return questions when inputs are missing.
HARD RULES:
- TDD ถ้าเป็น code: failing unit test ก่อน → fix → green
- Run targeted project tests; serialize shared integration/E2E resources. Outstanding required tests block acceptance until run.
- tsc / eslint เฉพาะไฟล์ที่แก้
- Use assigned branch; commit only if authorized, otherwise return a patch/content revision. Do not blindly create a second branch.
- ห้าม push. ห้ามแตะไฟล์นอก scope. ห้ามลบไฟล์ที่ตัวเองไม่ได้สร้าง
VERIFY BEFORE DONE: paste บรรทัด PASS จริงของ test
ถ้าเป็น FALSE POSITIVE หรือ BLOCKED → บอกตรง ๆ พร้อม evidence — ห้ามแต่ง fix
Return structured: verdict, assigned branch, source revision, commit_sha if created OR patch path + content hash, files, test_cmd, test_result, outstanding checks and questions. Never use an unchanged HEAD SHA as proof of an uncommitted fix.
```

**Verdict enum**: `FIXED` · `FALSE_POSITIVE` · `PARTIAL` · `BLOCKED`

**Runner A — optional host-specific example**: `skills/ops/drain/workflow-template.js`; not a prerequisite. Verify host APIs/isolation before adoption, and supply only one capacity-limited ready wave.
**Runner B — native host delegation**: use actual host tools within its active-worker limit. Oliver provisions isolated workspaces; no invented Task API. This example requires branch-creation authority and a validated unused destination:

```bash
git worktree add ../$(basename $PWD)-<ID> -b fix/<ID>
```

Runner ไหนก็ตาม: agent **return conclusion + path** ห้าม dump transcript (Handoff Contract, `shode-house-discipline`)

## Step 4 — Serial merge (main loop เท่านั้น — 🔴 ห้ามอยู่ใน fan-out)

1. Confirm target branch/revision, clean integration workspace, ownership and commit authority; never assume `main`.
2. Validate worker diff/patch and source revision. Dispatch independent reviewers and triggered experts per harness tier. FIXED is not review PASS.
3. Record source commit/patch hash and target base before each serial integration. If target changed, inspect affected dependencies and invalidate stale evidence.
4. Stop at the first conflict or failed gate; preserve prior integrations and worker branches. Do not publish or continue the remaining picks.
5. Run verified project-required checks on the integrated revision; filename presence alone does not identify a valid gate.
6. Push only to the confirmed destination with explicit authority. Record intent/receipt; timeout is UNKNOWN and requires reconciliation before retry. No automatic push or cleanup.

### Resume checkpoint

Per item record canonical ID, acceptance revision, worker/branch, patch or commit hash,
review/evidence revision, integration target/result, required checks, closure and
external-operation status. Resume from current records and actual Git/tracker state.
Do not reapply an integrated commit or repeat push/closure after a lost response.
Unresolved outcomes remain blocked; unchanged integrated work is reused. Context
reduction must retain unresolved findings and operation keys.

### 🔀 Conflict protocol (เดิมบอกแค่ "จัดกลุ่มใหม่" ไม่ได้บอกว่าจะเอา tree ที่ค้างกลางคันไปไว้ไหน)

cherry-pick conflict = สัญญาณว่า **file-locality grouping ผิด** (Step 2 พลาด) — แต่ก่อนจะจัดกลุ่มใหม่ ต้องจัดการสถานะที่ค้างอยู่ก่อน:

```bash
git cherry-pick --abort     # ✅ ที่นี่ abort ได้ — commit ของ agent ยังอยู่บน fix/<id> ไม่มีอะไรหาย
git status                  # ยืนยันว่า tree สะอาดก่อนไปต่อ
```
> Abort only the integration operation started by this run after verifying its pre-state and that no later user/manual edits would be discarded. Worker branches alone do not protect integration-side edits. Unknown or pre-existing merge/rebase state: preserve it and report the blocker; do not blindly abort or force a resolution.

**เลือกทางไหน** — ตัดสินด้วยจำนวน item ที่ต้องรันซ้ำ ไม่ใช่ความรู้สึก:

| สถานการณ์ | ทำ |
|---|---|
| ยัง cherry-pick ไปได้น้อย (≤2 item) | preserve completed integrations; safely abort only this run's conflicting operation, regroup/recheck affected items only |
| conflict ที่ item ท้าย ๆ ของรอบใหญ่ | abort เฉพาะตัวที่ชน → **ปล่อยที่ land แล้วให้อยู่** → เอา item ที่ชนไปรอบถัดไปพร้อมเพื่อนที่แตะไฟล์เดียวกัน |
| ต้อง resolve จริง ๆ (owner สั่ง / งานเร่ง) | ทำตาม 4 ข้อล่าง **แล้วบันทึกไว้ใน bd ของทั้งสองฝั่ง** ว่า resolve ด้วยมือ |

**ถ้าต้อง resolve ด้วยมือ (🔴 ห้าม hand-merge เงียบ ๆ)**
1. หา **primary source ของแต่ละ hunk** — อ่าน commit message + `bd show` ของ **ทั้งสองฝั่ง** เข้าใจ intent เดิมก่อนตัดสิน
2. เก็บ intent ทั้งคู่ถ้าเป็นไปได้; ขัดกันจริง → เลือกฝั่งที่ตรงเป้าของ item + **บันทึก trade-off ใน bd**
3. **ห้ามคิด behaviour ใหม่ระหว่าง resolve** — resolve ไม่ใช่ที่สำหรับออกแบบ
4. รัน fast-gate ก่อน commit และ **แนบ diff ของ hunk ที่ resolve เป็น evidence** (per invariant 1)

> **Invariant 9 — Conflict ต้องมีร่องรอย**: safely abort + regroup, resolve + evidence, or preserve state + record BLOCKED with the next owner when neither action is safe/authorized. **ห้ามจบแบบไม่มีใครรู้ว่าเกิดอะไรขึ้น**

## Step 5 — Close on done (🔴 anti-puppet — run ยังไม่จบจนกว่าครบ)

```bash
bd close <id> --reason "<verdict> <commit_sha> <test_result>"
bd show <id>    # ต้องอ่านได้ว่า CLOSED — นี่คือหลักฐาน ไม่ใช่คำพูดของ agent
```

| Verdict | Action |
|---------|--------|
| `FIXED` (worker result) | candidate only; independent review + integrated required checks + authority precede close/read-back |
| `FALSE_POSITIVE` | independently verify proof against current acceptance; close as invalid only with authority, otherwise retain for triage |
| `PARTIAL` / `BLOCKED` | **คง OPEN** + `bd update --notes` บอกว่าติดอะไร + owner ถัดไป |

**Drift guard**: a worker FIXED return is not task completion. Only accepted items with authoritative closure may be reported CLOSED; pending review, failed integration or unavailable tracker updates remain explicitly incomplete.
(ดู `shode-house-workflow/drift.md` § M8 (ห้าม claim "ปิดแล้ว" โดยไม่ paste output))

## Round cap

- ≤ ~20 items per batch, not concurrency. Default active writers ≤ 3, reduced by actual host/resource limits; queue the rest and recheck readiness before refill.
- รอบถัดไปเริ่มที่ Step 1 ใหม่ (verify set ใหม่ — งานรอบก่อนอาจ spawn `--discovered-from` item)
- 3 รอบแล้วยังมี item ค้าง BLOCKED เดิม → **หยุด escalate owner** (ไม่ใช่ปัญหาที่ fan-out ช่วยได้)

## Evidence

```
✅ "[bd show bd-142] status=CLOSED reason='FIXED a1b2c3d vitest 12 passed'"
✅ "[Bash: git cherry-pick a1b2c3d] clean, no conflict; [scripts/ci/local.sh] 214 passed"
✅ "[agent fix:bd-142] FALSE_POSITIVE — src/pay/round.ts:88 ใช้ Decimal อยู่แล้ว [paste 3 บรรทัด]"
❌ "ปิด bd หมดแล้วครับ" (ไม่มี bd show output)
❌ "ทุก item ผ่าน test" (ไม่มี PASS line ต่อ item)
```

## ห้าม

- ห้าม seed run จาก `bd list` count โดยไม่ `bd show` ทีละตัว
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
| ยังไม่มี item list / ไม่รู้ใครรับ | → `shode-house-routing` | Oliver produce item list + owner ต่อ item ก่อน drain |
| Item ยัง abstract (ไม่มี file:line) | → `diagnose` แล้วค่อยกลับมา | ต้อง root cause ก่อน; drain implement เฉพาะ fix ที่ concrete |
| ต้องการ spec/design ก่อน | → `design-system` | drain ไม่ใช่ที่ออกแบบ feature |
| TDD discipline ต่อ item | → `dev-gate` | red-green-refactor + quality gate ภายใน agent แต่ละตัว |
| Reviewer lens ตอน verify | → `review-checklist` | Chris 7-dim / Quinn matrix สำหรับ item ที่ต้อง review ลึก |
| Definition of Done | → `shode-house-deliverable` | acceptance + authorized closure/read-back in confirmed tracker; unavailable sync remains pending, not CLOSED |
| ปิดไม่ครบ / อ้างว่าปิดแล้ว | → `shode-house-workflow/drift.md` § M8 | Close-on-Done Guard (anti-puppet บน close step) |
