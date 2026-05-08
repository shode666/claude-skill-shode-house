# Scope Contract — Pre-implement Gate (v2.4.1)

> Lazy-load reference. ไม่อยู่ใน main context. Agent load เมื่อต้อง post scope ก่อน implement
> Why: failure-modes/001 (edit-validation-contradiction) + realworld pain — agent over-scope / misinterpret / overlap

## เมื่อใดต้อง post Scope Contract

ก่อน **implement / refactor / scaffold / fix bug / migration / config change** — agent ที่ทำงานจริง (Dave/Chris/Quinn/Aaron/domain experts) ต้องโพสต์ scope contract แล้วรอ confirm/auto-pass ก่อนเริ่ม edit จริง

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

**Files** — กัน agent overlap (file ownership lock)
- ระบุ paths ที่จะ Write/Edit (read-only ไม่ต้อง list)
- Glob pattern OK ถ้าชัดเจน (`src/payment/**`)
- ระหว่างที่ contract นี้ active → agent อื่นที่ Files overlap → **block + wait**
- แตะ file นอก Files = scope drift = stop + re-scope

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
4. User confirm/reject (Interactive mode) หรือ auto-pass (AFK mode after no objection)
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
- "Files" ที่ระบุไม่ครบ (แตะ file ที่ไม่ list) → scope drift = stop

## ถ้า scope ต้องเปลี่ยนระหว่างทาง

agent ต้อง stop + post **Scope Amendment**:
```
[<agent>|state:scope-amend|task:<id>] Scope amendment
- Reason: <พบว่าต้องแก้ไฟล์เพิ่ม / requirement เปลี่ยน>
- Add IN/OUT/Files: <delta>
- Echo: <understand>
```
รอ confirm → ทำต่อ

## ถ้า scope ปิด (task done)

```
[<agent>|state:scope-closed|task:<id>] Scope closed
- Files ปล่อย: <list>
- Stop criteria met: <evidence>
```
→ Oliver ปลด file ownership → agent อื่นต่อได้
