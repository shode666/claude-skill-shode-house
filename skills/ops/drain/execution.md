---
name: execution
description: Reference (lazy-load) ของ `drain` — fan-out brief/runners, serial integration, resume checkpoint, conflict protocol, evidence examples. โหลดหลัง eligibility ผ่านแล้วเท่านั้น
---

```lazy-load-contract
LOAD: skills/ops/drain/execution.md
WHEN: drain_eligibility_confirmed=true
OWNER: orchestrator
REQUIRED-BEFORE: drain_fan_out
```

# Drain execution — fan-out → serial merge → evidence

> Mechanics only; root `SKILL.md` (eligibility, 9 invariants, review/closure authority, ห้าม) binds every step here.


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
| ต้อง resolve จริง ๆ (owner สั่ง / งานเร่ง) | ทำตาม 4 ข้อล่าง **แล้วบันทึกไว้ใน task record ของทั้งสองฝั่ง** (confirmed tracker) ว่า resolve ด้วยมือ |

**ถ้าต้อง resolve ด้วยมือ (🔴 ห้าม hand-merge เงียบ ๆ)**
1. หา **primary source ของแต่ละ hunk** — อ่าน commit message + task record ของ **ทั้งสองฝั่ง** เข้าใจ intent เดิมก่อนตัดสิน
2. เก็บ intent ทั้งคู่ถ้าเป็นไปได้; ขัดกันจริง → เลือกฝั่งที่ตรงเป้าของ item + **บันทึก trade-off ใน task record**
3. **ห้ามคิด behaviour ใหม่ระหว่าง resolve** — resolve ไม่ใช่ที่สำหรับออกแบบ
4. รัน fast-gate ก่อน commit และ **แนบ diff ของ hunk ที่ resolve เป็น evidence** (per invariant 1)

> **Invariant 9 — Conflict ต้องมีร่องรอย**: safely abort + regroup, resolve + evidence, or preserve state + record BLOCKED with the next owner when neither action is safe/authorized. **ห้ามจบแบบไม่มีใครรู้ว่าเกิดอะไรขึ้น**

## Evidence

```
✅ "[tracker read-back T-142] status=CLOSED reason='FIXED a1b2c3d vitest 12 passed'"
✅ "[Bash: git cherry-pick a1b2c3d] clean, no conflict; [scripts/ci/local.sh] 214 passed"
✅ "[agent fix:T-142] FALSE_POSITIVE — src/pay/round.ts:88 ใช้ Decimal อยู่แล้ว [paste 3 บรรทัด]"
❌ "ปิด task หมดแล้วครับ" (ไม่มี tracker read-back output)
❌ "ทุก item ผ่าน test" (ไม่มี PASS line ต่อ item)
```
