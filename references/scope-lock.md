# Scope Contract — Pre-implement Gate (v2.4.1)

> Lazy-load reference. ไม่อยู่ใน main context. Agent load เมื่อต้อง post scope ก่อน implement
> Why: failure-modes/001 (edit-validation-contradiction) + realworld pain — agent over-scope / misinterpret / overlap

## เมื่อใดต้อง post Scope Contract

ก่อน **implement / refactor / scaffold / fix bug / migration / config change** — agent ที่ทำงานจริง (Dave/Chris/Quinn/Aaron/domain experts) บันทึก scope และตรวจ ownership/authorization ก่อน edit; reuse scope ที่อนุญาตแล้ว ไม่บังคับขอ confirm ซ้ำหรือรอ silence-as-approval

ไม่ต้อง post: research / read-only analysis / answer question / clarification

## Template

```
[<agent>|state:scope|task:<id>] Scope contract
- IN:    <≤3 bullets — สิ่งที่จะทำในรอบนี้>
- OUT:   <≤3 bullets — สิ่งที่ไม่ทำ (กัน scope creep)>
- Files: <paths ที่จะแก้ — agent อื่นห้าม touch จนกว่าจะปิด>
- Stop:  <criteria ที่ทำให้ task เสร็จ>
- Echo:  "เข้าใจว่า X เพราะ Y → จะทำ Z" (1 บรรทัด — confirm understanding)
```

## Field rules

**IN/OUT** — กัน scope creep
- IN ≤ 3 bullets, ระบุ outcome ไม่ใช่ activity ("POST /payments/create endpoint" ไม่ใช่ "เขียน code")
- OUT ระบุสิ่งที่ user/Oliver อาจ assume ว่าทำแต่ไม่ทำในรอบนี้ (กัน "ทำเพิ่มนิดนึง")

**Files** — coordinated ownership, not a filesystem lock
- ระบุ paths ที่จะ Write/Edit (read-only ไม่ต้อง list)
- Glob pattern OK ถ้าชัดเจน (`src/payment/**`)
- ระหว่างที่ contract นี้ active → agent อื่นที่ Files overlap → **block + wait**
- file นอก Files → พัก write ของไฟล์นั้นเพื่อตรวจ ownership และบันทึก amendment; ถ้ายังอยู่ใน outcome/authority เดิมไม่ต้องขอ user อนุมัติซ้ำ

**Stop** — กัน agent ทำเรื่อยเปื่อย
- ทดสอบได้ ("smoke test pass + Chris approve") ไม่ใช่ subjective ("ดีพอ")
- ถ้าทดสอบไม่ได้ = task ยังไม่ scope พอ → re-design

**Echo** — กัน misinterpretation
- 1 บรรทัด, ภาษาคน: "เข้าใจว่า user ขอ X เพราะ Y → จะทำ Z, ไม่ทำ W"
- ถ้า Echo ผิด = user reject ที่นี่ก่อนเริ่ม work = save token

## Flow

```
1. Oliver มอบ task → agent ทำ research/clarify ถ้ายังกำกวม
2. agent post Scope Contract
3. Oliver scan active contracts:
   a. Files overlap กับ active agent อื่น? → BLOCK, agent wait
   b. ไม่ overlap → ผ่าน
4. Verify existing authorization covers this scope. If not, obtain explicit approval before editing. AFK/silence never grants approval; approved unchanged scope does not need repeated confirmation.
5. Agent implement (เฉพาะ Files ที่ประกาศ)
6. agent post "scope closed" → ปล่อย file ownership
```

## ตัวอย่าง

### ตัวอย่างที่ 1 — parallel ทำงานได้
```
[Dave#1|state:scope|task:bd-15] Scope contract
- IN: implement POST /payments/create endpoint
- OUT: refactor existing /payments/list, add UI form
- Files: src/payment/create_handler.py, tests/payment/test_create.py
- Stop: smoke test pass + Chris approve
- Echo: เข้าใจว่าเพิ่ม endpoint ใหม่ไม่แก้ของเดิม → จะทำ POST handler + integration test

[Dave#2|state:scope|task:bd-16] Scope contract
- IN: implement POST /payments/refund endpoint
- OUT: ไม่แตะ /create
- Files: src/payment/refund_handler.py, tests/payment/test_refund.py
- Stop: smoke test pass + Chris approve
- Echo: เข้าใจว่า refund แยก endpoint ไม่รวมกับ create → จะทำ POST handler + test
```
→ Files ไม่ overlap → parallel ได้

### ตัวอย่างที่ 2 — block ที่ overlap
```
[Dave#3|state:scope|task:bd-17] Scope contract
- Files: src/payment/create_handler.py  ← overlap Dave#1
```
→ Oliver: BLOCK Dave#3, รอ Dave#1 ปิด task ก่อน

### ตัวอย่างที่ 3 — Echo จับ misinterpretation
User: "เพิ่ม validation ตรง edit ราคา"
```
[Dave|state:scope] Scope contract
- IN: เพิ่ม validation `price > 0` ที่ POST /products/:id/price
- ...
- Echo: เข้าใจว่า user ขอ validate ค่าราคา > 0 → จะทำ validation ตรง backend
```
User: "ไม่ใช่ ผมหมายถึง validate ที่ frontend form"
→ Re-scope ก่อนเริ่ม code = save token จากการ implement ผิด

## Enforcement

- Oliver = enforcer หลัก (ดู `agents/orchestrator.md` § Scope Contract Enforcement)
- ทุก implementing agent (Dave/Chris/Quinn/Aaron/domain expert) ต้อง compliance
- ขัด rule = block + Oliver แจ้ง user

## Catches (จาก realworld painpoint)

| Painpoint | จับโดย field |
|-----------|--------------|
| Scope creep — refactor เกินที่ขอ | IN/OUT |
| Misinterpretation — ทำผิดทิศ | Echo |
| Pace mismatch — task เล็ก response ใหญ่ | IN/OUT bullets เป็น implicit S/M/L |
| Token waste — ทำผิดต้องทำใหม่ | Echo + IN ดักก่อน implement |
| Agent overlap — 2 agent แก้ file เดียวกัน | Files |
| Agent ทำเรื่อยเปื่อย ไม่จบ | Stop |

## Anti-puppet

- ห้าม implement โดยไม่โพสต์ Scope Contract → treated as scope drift = block
- โพสต์ Scope Contract แต่ทำเกิน scope → block + re-scope
- "Files" ที่ระบุไม่ครบ → พัก affected write แล้ว reconcile inventory/ownership ตาม Scope Amendment; ไม่หยุดงานอิสระที่ได้รับ authority แล้ว

## ถ้า scope ต้องเปลี่ยนระหว่างทาง

agent พักเฉพาะ affected write แล้วบันทึก **Scope Amendment**:
```
[<agent>|state:scope-amend|task:<id>] Scope amendment
- Reason: <พบว่าต้องแก้ไฟล์เพิ่ม / requirement เปลี่ยน>
- Add IN/OUT/Files: <delta>
- Echo: <understand>
```
ถ้า amendment เป็นรายละเอียดภายใน outcome/authority เดิมและไม่ชน active ownership ให้บันทึกแล้วทำต่อ ถ้าขยาย outcome/authority หรือชน ownership ให้พักเฉพาะงานที่ขึ้นต่อ decision นั้นและขอการตัดสินที่ขาด

## ถ้า scope ปิด (task done)

```
[<agent>|state:scope-closed|task:<id>] Scope closed
- Files ปล่อย: <list>
- Stop criteria met: <evidence>
```
→ Oliver ปลด file ownership → agent อื่นต่อได้

## Script-checkable enforcement (🆕 bd: shode-house-5cs.4, L2)

Applicability: this section documents the separate repository script runtime, only
for projects that explicitly adopted it and have verified its hooks are active.
The distributed instruction-only plugin supplies neither these scripts nor hooks;
it must not claim this enforcement or install the runtime implicitly. Without it,
use the harness's scoped ownership, serialized writes and honest enforcement limits.

ข้างบนคือ **prose protocol** (chat message + Oliver อ่านเอง) — ชั้นที่ **script บังคับจริง**
อยู่ที่ `scripts/scope-check.sh` (per-bd manifest `.shode-house/scope/<bd-id>.json`) +
`hooks/scripts/guard-scope-write.sh` (PreToolUse บน `Write|Edit|Bash`). ความสัมพันธ์กับ
`references/scope/README.md` เดิมไม่เปลี่ยน (prose ↔ script คนละชั้น ประกอบกัน ไม่ทับกัน)

- **Fail-closed unclaimed path**: path ที่ไม่มีใครประกาศ owns[] → **ไม่ ALLOW เงียบๆ อีกต่อไป**
  — ถ้าอยู่ใน `allowed_roots[]` ของ agent ที่ขอ (plan-approved boundary ตอน Scope Contract)
  → exit 4 `NEEDS_AMENDMENT` พร้อมคำสั่ง `--amend` ที่ต้องรันเป๊ะๆ; ถ้าอยู่นอก `allowed_roots[]`
  → exit 1 `DENY`, escalate ให้ Oliver, **ห้าม self-amend ข้ามขอบเขตที่ plan อนุมัติไว้**
- **`--amend`**: atomic (lock + validate + atomic-rename เหมือน `workflow-state.sh`), เติมได้
  เฉพาะ `owns[]` — **ห้ามเติม `allowed_roots[]`** (self-amend ≠ self-expand)
- **bind-on-claim**: agent เห็นเฉพาะ label ของตัวเอง (`Dave#1`) ไม่เห็น instance id ที่ harness
  สุ่มให้ตอน subagent spawn — agent รัน `scripts/scope-check.sh <bd> <label> --bind` เป็นก้าวแรก,
  hook (`guard-scope-write.sh`, ADAPTER ของ platform นี้) เห็นทั้ง identity fields ของ harness
  และคำสั่ง Bash พร้อมกัน จึงเป็นคนบันทึกจริง (7 กติกา ระบุด้วย instance_id + label เท่านั้น,
  role/platform เป็น metadata ที่บันทึกไว้เฉยๆ ไม่เข้ากติกา: first-bind-wins, label ต้องมีอยู่ใน
  แมนิเฟสต์แล้ว, idempotent ถ้า instance_id เดิม+label เดิม, DENY ถ้า instance_id เดิมขอ label อื่น
  หรือ label ถูกจองแล้วโดย instance_id อื่น) — recognize เฉพาะ **canonical shape เป๊ะๆ** เท่านั้น
  (ห้าม substring match `--bind`, reject ทันทีถ้ามี `; && || | $( ` \` ` หรือ redirect ปนอยู่ที่ไหน
  ก็ตามในคำสั่ง)
- **Binding record เป็น platform-neutral** (🆕 bd: shode-house-5cs.4 iter 1, "C1") — `scripts/
  scope-check.sh` (core) **ห้ามเอ่ยชื่อ platform ใดๆ เลย** (grep-enforced test) รู้จักแค่
  `instance_id` / `role` / `label`; เก็บ `bindings` เป็น object keyed by `instance_id` →
  `{"platform": ..., "role": ..., "label": ...}` (lookup O(1)) แทน flat map เดิมที่ผูกกับรูปแบบ
  ของ platform หนึ่งเดียว — การตั้งชื่อ platform (`"claude"` วันนี้) เป็นหน้าที่ของ ADAPTER
  (`hooks/scripts/guard-scope-write.sh`) เท่านั้น ซึ่งอ่าน harness identity fields ของตัวเองแล้ว
  normalize ก่อนส่งให้ core. แมนิเฟสต์รุ่นเก่า (`bindings` เป็น flat string) ถูก **reject ชัดเจน**
  (exit 64 พร้อมคำแนะนำ) ทันทีที่คำสั่งฝั่ง bind แตะเข้าไป — ไม่ misread เงียบๆ; ownership check ที่
  ไม่แตะ `bindings` เลย (`--check`/`--amend`/`--snapshot`/`--verify`) ยังใช้แมนิเฟสต์รุ่นเก่าได้ปกติ
- **Main session ไม่ exempt + outsider policy** (🆕 bd: shode-house-5cs.4 iter 1, "C2") — เขียนจาก
  main session เข้า path ที่อยู่ใน `owns[]`/`allowed_roots[]`/`shared_files[]` ของ agent ที่ active
  อยู่ → DENY เหมือนกัน (ไม่งั้น scope lock ของ subagent หลบผ่าน main session ได้ตรงๆ); เขียนนอก
  ขอบเขตที่ active → ALLOW + audit log 1 บรรทัด — **policy เดียวกันนี้ใช้กับ subagent ที่ resolve
  ไม่ได้ด้วย**: instance_id ที่ไม่เคย bind เลยใน bd ที่ active เพียงอันเดียว หรือ bind แบบกำกวม
  (bound ใน 0 หรือ >1 bd ที่ `in_progress` พร้อมกัน) ถือเป็น "outsider" เหมือน main session ทุก
  ประการ — DENY ถ้า path ชนกับ scope ที่ active อยู่, ALLOW+audit ถ้าไม่ชน. ก่อนหน้านี้ agent ที่ไม่
  bind หรือ bind กำกวม fail OPEN เงียบๆ (ช่องโหว่: agent หลบ scope ได้แค่ไม่ยอม bind) — C2 ปิดช่อง
  นี้โดยไม่ brick agent ที่ legitimate ไม่เคย bind เลย (เช่น reviewer เขียน artifact ใต้ `outputs/`
  ที่ไม่มีแมนิเฟสต์ไหน claim)
- รายละเอียด exit code ทั้งหมด (0/1/2/3/4/64) + ตัวอย่างจริง → header comment ของ
  `scripts/scope-check.sh` เอง (single source of truth)

## Enforcement ceiling (🆕 bd: shode-house-5cs.4 iter 2, "C5" — user ruling "option A")

**ห้าม doc นี้ implied ว่า enforce มากกว่าที่มีจริง** — ceiling ที่แท้จริงคือ:

- **Write/Edit/NotebookEdit tool = hook-enforced เต็ม** (`guard-scope-write.sh`) — path
  canonicalize (lexnorm + physical-resolve + case-fold, ปิด traversal/dot-slash/case, "C1")
  แล้วเทียบกับ manifest ก่อนตัดสิน ALLOW/DENY/NEEDS_AMENDMENT ทุกครั้ง; symlink leaf ที่ target
  เขียนจริงถูก refuse ทันที ไม่พยายาม resolve-แล้ว-match ("H1")
- **Shell write (ผ่าน Bash tool) = ADVISORY เท่านั้น** — **ห้าม claim ว่า scope-enforced**
  ยกเว้น 3 fixed control-plane path: `.shode-house/state/`, `.shode-house/journal/`,
  `.shode-house/scope/` (scope manifest / binding store) ซึ่ง **DENY ทันทีถ้า Bash command
  เอ่ยถึง path พวกนี้** ไม่ว่าจะอ่านหรือเขียน (`deny-if-mentioned` over fixed string set — **ไม่ใช่
  general write-target parser**, ห้าม resolve variable/cwd-trick/shell-indirection — user
  ตัดสินใจแล้วว่านั่นคือ arms race ที่ไม่คุ้ม) — agent อื่นเขียนไฟล์คนอื่นผ่าน `echo >`/`cp`/`sed -i`/
  `tee`/heredoc นอก 3 path นี้ **ยังผ่านได้** (advisory only, by design, ไม่ใช่ bug ที่เหลือ)
- `--bind` canonical shape ยังคง strict shape เดิม (metachar reject + fully-anchored regex);
  iter 2 แก้ separator จาก `[[:space:]]+` (match `\n` ด้วย) เป็น literal space เท่านั้น
  ("C2" — multi-line command เคยหลุดผ่านเป็น "canonical shape เป๊ะๆ" ได้)
- Manifest ที่อ่านไม่ออก (corrupt JSON / เก่ากว่า C1 shape) → **fail-closed พร้อม audit line ที่
  แยกออกจาก ALLOW ปกติได้** ("C3") ไม่ใช่ fail-open เงียบๆ เหมือนเดิม
- `--amend` รับเฉพาะ concrete file path เท่านั้น (มี `* ? [ ]` → DENY ทันที, "M2") กัน
  self-amend กลายเป็น root-wide grant ผ่าน literal glob string
