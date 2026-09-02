---
name: drain
description: |
  [WHAT] Drain backlog ที่ verified แล้ว N item — 1 worktree-isolated agent ต่อ item (TDD, no push) → serial cherry-pick เข้า trunk → ปิด bd ทุก item พร้อม evidence.
  [WHEN] หลังมี routing plan (Oliver) AND item ถูก code-verify ว่า independent + concrete.
  [TRIGGER] /shode-house:drain, "drain backlog", "จัดงานที่พร้อม", "batch fix", "ปิด bd ที่เหลือ", "clear the ready set".
---

# Drain (verified backlog → parallel worktree → serial merge → close-on-done)

> **Owner**: Oliver (route + own the run). Impl/verify: Dave · Chris · Quinn · Aaron · Uma; security item → Sentinel
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

- [ ] **Ready set ที่มี edge จริง** — ถ้า backlog ยังเป็นก้อนใหญ่/ไม่มี blocking edge → แตกด้วย **`decompose` skill** ก่อน อย่ามานั่ง verify independence เองที่นี่
- [ ] **Verified-open set** — union ของ `bd list` + tracked export id **แล้ว confirm ทีละตัวด้วย `bd show`** (อ่านได้เชื่อถือได้ตัวเดียว). ห้าม seed run จาก `bd list` count ดิบ
- [ ] **Per-item concrete scope** — `file:line` + fix direction ฝังใน brief ของแต่ละ item.
      🔴 worktree agent **รัน `bd` ไม่ได้** (Dolt DB ไม่ได้อยู่ใน worktree) → AC ต้องอยู่ใน prompt ทั้งหมด
- [ ] **Routing** — Oliver assign owner agent ต่อ item + ยืนยัน parallel-safe / file-disjoint
- [ ] **Owner greenlight + scope** — subset ไหน (security / code-gap / test) หรือทั้งหมด; full drain = multi-agent token spend ก้อนใหญ่ → ต้อง opt-in

ขาดข้อใด → list สิ่งที่ขาด ส่งกลับ caller **ก่อน** fan-out

## 9 Invariants (map เข้า 5 Philosophy)

| # | Invariant | Maps to |
|---|-----------|---------|
| 1 | **VERIFY BEFORE DONE** — ทุก agent paste test output จริง (red→green); ห้าม "น่าจะ work" | NO MAGIC / VERIFY |
| 2 | **CLOSE ON DONE** — item ที่ land แล้ว → `bd close` **พร้อม evidence** (commit sha + test line) + `bd show` re-confirm | ปิดช่อง stale-open |
| 3 | **NO FALSE CLOSE** — BLOCKED / PARTIAL / owner-gated **คงสถานะ OPEN** + note ตรงไปตรงมา | DISSENT / evidence |
| 4 | **FALSE-POSITIVE honesty** — ถ้า "bug" ถูกอยู่แล้ว → return `FALSE_POSITIVE` พร้อม proof; ห้ามแต่ง fix | NO MAGIC |
| 5 | **Worktree isolation** — 1 worktree ใหม่ต่อ agent; ห้าม shared working tree | parallel-safe |
| 6 | **No push in worktree** — agent commit บน `fix/<id>`; main loop merge serial (ไม่มี push-race) | SCOPE / safety |
| 7 | **Scope-lock + no-delete** — agent แก้เฉพาะไฟล์ของ item ตัวเอง, **ห้ามลบไฟล์ที่ตัวเองไม่ได้สร้าง** | scope drift guard |
| 8 | **Unit test เท่านั้นตอน parallel** — ห้าม fan-out Testcontainers/Playwright (resource blow-up); integration test ที่ต้องรัน → **ระบุชื่อ** ให้รันก่อน deploy | evidence realism |
| 9 | **Conflict ต้องมีร่องรอย** — abort+regroup หรือ resolve+evidence; ห้ามจบเงียบ (ดู § Conflict protocol) | NO MAGIC / VERIFY |

## Flow

```
verify set (bd show ทีละตัว)
   ↓
Oliver route + group by file-locality
   ↓
FAN-OUT  (worktree agent ต่อ item — TDD, commit บน fix/<id>, NO push)
   ↓
main loop: git cherry-pick <sha> ทีละตัว (serial → ไม่มี race)
   ↓
1 aggregate fast-gate run  →  1 push
   ↓
bd close ทุก item + bd show verify   ← run ยังไม่จบจนกว่าทุก FIXED = CLOSED
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
คุณอยู่ใน ISOLATED git worktree. ทำเฉพาะ item เดียวนี้. ห้ามรัน bd (ใช้ไม่ได้ใน worktree — context ครบอยู่ใน prompt นี้แล้ว)
HARD RULES:
- TDD ถ้าเป็น code: failing unit test ก่อน → fix → green
- รัน UNIT test เท่านั้น (เช่น `pnpm exec vitest run <path>`); ห้าม Testcontainers/integration ตอน parallel — ถ้ามีที่ต้องรันก่อน deploy ให้ระบุชื่อ
- tsc / eslint เฉพาะไฟล์ที่แก้
- จากนั้น: git switch -c fix/<ID> ; git add <files> ; git commit
- ห้าม push. ห้ามแตะไฟล์นอก scope. ห้ามลบไฟล์ที่ตัวเองไม่ได้สร้าง
VERIFY BEFORE DONE: paste บรรทัด PASS จริงของ test
ถ้าเป็น FALSE POSITIVE หรือ BLOCKED → บอกตรง ๆ พร้อม evidence — ห้ามแต่ง fix
Return structured: verdict, branch (fix/<ID>), commit_sha (git rev-parse HEAD), files, test_cmd, test_result, note
```

**Verdict enum**: `FIXED` · `FALSE_POSITIVE` · `PARTIAL` · `BLOCKED`

**Runner A — Workflow tool** (ถ้า host มี): template อยู่ที่ `skills/ops/drain/workflow-template.js`
**Runner B — Task tool** (Claude Code ปกติ): 1 `Task` ต่อ item ใน message เดียว (concurrent), แต่ละตัวสร้าง worktree เอง:

```bash
git worktree add ../$(basename $PWD)-<ID> -b fix/<ID>
```

Runner ไหนก็ตาม: agent **return conclusion + path** ห้าม dump transcript (Handoff Contract, `shode-house-discipline`)

## Step 4 — Serial merge (main loop เท่านั้น — 🔴 ห้ามอยู่ใน fan-out)

```bash
# fast gate ของ target project — ห้าม hardcode; หาให้เจอก่อน
FAST_GATE=$(ls scripts/ci/local.sh 2>/dev/null \
  || (grep -qE '"(test|check)"' package.json 2>/dev/null && echo "npm test") \
  || (test -f Makefile && grep -qE '^(test|check|ci):' Makefile && echo "make test") \
  || (test -f pyproject.toml && echo "pytest") )
[ -z "$FAST_GATE" ] && { echo "ไม่พบ fast gate — ถาม user ว่ารันอะไร ห้ามเดา"; exit 1; }

for sha in $FIXED_SHAS; do git cherry-pick "$sha"; done   # serial → ไม่มี push-race; ไฟล์ disjoint → clean
$FAST_GATE                                                 # 1 aggregate fast-gate run
git push origin main                                       # 1 push
git worktree prune                                         # เก็บกวาด worktree
```

### 🔀 Conflict protocol (เดิมบอกแค่ "จัดกลุ่มใหม่" ไม่ได้บอกว่าจะเอา tree ที่ค้างกลางคันไปไว้ไหน)

cherry-pick conflict = สัญญาณว่า **file-locality grouping ผิด** (Step 2 พลาด) — แต่ก่อนจะจัดกลุ่มใหม่ ต้องจัดการสถานะที่ค้างอยู่ก่อน:

```bash
git cherry-pick --abort     # ✅ ที่นี่ abort ได้ — commit ของ agent ยังอยู่บน fix/<id> ไม่มีอะไรหาย
git status                  # ยืนยันว่า tree สะอาดก่อนไปต่อ
```
> 🔴 `--abort` ปลอดภัย **เฉพาะที่ step นี้** เพราะงานที่ verify แล้วอยู่บน branch `fix/<id>` ครบ — ไม่ใช่การทิ้งงาน
> ถ้าอยู่กลาง rebase/merge ที่ไม่มี branch สำรอง = **ห้าม abort** ต้อง resolve ให้จบ

**เลือกทางไหน** — ตัดสินด้วยจำนวน item ที่ต้องรันซ้ำ ไม่ใช่ความรู้สึก:

| สถานการณ์ | ทำ |
|---|---|
| ยัง cherry-pick ไปได้น้อย (≤2 item) | **abort → จัดกลุ่มใหม่ → รันรอบใหม่** (default) |
| conflict ที่ item ท้าย ๆ ของรอบใหญ่ | abort เฉพาะตัวที่ชน → **ปล่อยที่ land แล้วให้อยู่** → เอา item ที่ชนไปรอบถัดไปพร้อมเพื่อนที่แตะไฟล์เดียวกัน |
| ต้อง resolve จริง ๆ (owner สั่ง / งานเร่ง) | ทำตาม 4 ข้อล่าง **แล้วบันทึกไว้ใน bd ของทั้งสองฝั่ง** ว่า resolve ด้วยมือ |

**ถ้าต้อง resolve ด้วยมือ (🔴 ห้าม hand-merge เงียบ ๆ)**
1. หา **primary source ของแต่ละ hunk** — อ่าน commit message + `bd show` ของ **ทั้งสองฝั่ง** เข้าใจ intent เดิมก่อนตัดสิน
2. เก็บ intent ทั้งคู่ถ้าเป็นไปได้; ขัดกันจริง → เลือกฝั่งที่ตรงเป้าของ item + **บันทึก trade-off ใน bd**
3. **ห้ามคิด behaviour ใหม่ระหว่าง resolve** — resolve ไม่ใช่ที่สำหรับออกแบบ
4. รัน fast-gate ก่อน commit และ **แนบ diff ของ hunk ที่ resolve เป็น evidence** (per invariant 1)

> **Invariant 9 — Conflict ต้องมีร่องรอย**: ทุก conflict ที่เกิด ต้องจบด้วยอย่างใดอย่างหนึ่ง — abort + regroup (บันทึกว่ารอบนี้ตัด item ไหนออก) หรือ resolve + evidence. **ห้ามจบแบบไม่มีใครรู้ว่าเกิดอะไรขึ้น**

## Step 5 — Close on done (🔴 anti-puppet — run ยังไม่จบจนกว่าครบ)

```bash
bd close <id> --reason "<verdict> <commit_sha> <test_result>"
bd show <id>    # ต้องอ่านได้ว่า CLOSED — นี่คือหลักฐาน ไม่ใช่คำพูดของ agent
```

| Verdict | Action |
|---------|--------|
| `FIXED` (landed) | `bd close` + evidence + `bd show` confirm CLOSED |
| `FALSE_POSITIVE` | `bd close` เป็น invalid + แนบ proof ว่าโค้ดเดิมถูกอยู่แล้ว |
| `PARTIAL` / `BLOCKED` | **คง OPEN** + `bd update --notes` บอกว่าติดอะไร + owner ถัดไป |

**Drift guard**: run นี้ **ไม่ done** จนกว่าทุก item ที่ `FIXED` แสดง `CLOSED` จาก `bd show` จริง
(ดู `shode-house-drift` § M8 Close-on-Done Guard — ห้าม claim "ปิดแล้ว" โดยไม่ paste output)

## Round cap

- ≤ ~20 item ต่อรอบ; เกิน → แตกรอบ + report ระหว่างรอบ
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
- ห้าม close bd โดยไม่มี commit sha + test result ใน reason
- ห้าม close `PARTIAL` / `BLOCKED` เพื่อให้ตัวเลขสวย
- ห้ามรัน integration/E2E ขนานใน fan-out
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
| Definition of Done | → `shode-house-deliverable` | DoD = bd **CLOSED with evidence** ไม่ใช่ "code merged" |
| ปิดไม่ครบ / อ้างว่าปิดแล้ว | → `shode-house-drift` § M8 | Close-on-Done Guard (anti-puppet บน close step) |
