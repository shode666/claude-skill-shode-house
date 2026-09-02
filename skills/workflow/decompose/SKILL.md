---
name: decompose
description: |
  [WHAT] แตกงานก้อนใหญ่ที่ **spec นิ่งแล้ว** เป็น leaf task ที่ลงมือได้ — tracer bullet (ตัดทะลุทุก layer) + blocking edge ประกาศตอนสร้าง + create-then-wire 2 pass + เกณฑ์ "เล็กพอหรือยัง".
  [WHEN] หลัง spec/BRD นิ่ง (Phase 1a sign-off).
  [TRIGGER] /shode-house:decompose, "แตกงาน", "แตก epic", "split", "ซอยงาน", "epic".
---

# Decompose (epic → leaf task ที่ลงมือได้)

> **Owner**: Bella (จาก user story) + Oliver (จาก XL triage). Co-pilot: Sara (interface contract), Patrick (ลำดับตาม outcome), Quinn (test slice)
> แก้ปัญหาที่วัดได้: `shode-house-routing` เขียนไว้ว่า **"XL = cross-service/cross-domain → split into smaller bd"** แต่ **ไม่มี step ไหนในทั้ง pipeline ที่ทำ split จริง** — เป็นกฎที่ไม่มีใครรัน

## When NOT to use

- **ยังมีหมอก** — ยังตอบไม่ได้ว่า "เสร็จ" หน้าตายังไง หรือมี decision ค้างที่ต้องตัดก่อน → **`shode-house-workflow/wayfinding.md` (Map mode)** ก่อน. แตกหมอกเป็น task = ซอยสิ่งที่ยังไม่รู้ว่าคืออะไร
- **งานเล็กอยู่แล้ว** — 1 bd จบใน pipeline เดียว (S/M) → อย่าแตก แตกแล้วจ่ายค่า coordination ฟรี ๆ
- **แตกเพื่อให้ดูมีความคืบหน้า** — leaf ที่ merge แล้ว user ไม่ได้อะไรเลย = แตกผิด (ดู § Tracer bullet)
- **backlog ที่ verified + concrete แล้ว** → ไป `drain` เลย ไม่ต้องแตกซ้ำ

## Required inputs — refuse without

- [ ] **Spec หรือ BRD ที่ sign-off แล้ว** (Phase 1a) — แตกจาก AC/FR ไม่ใช่จากชื่อ feature
- [ ] **Outcome ของก้อนใหญ่** 1-2 บรรทัด — ใช้ตัดสินว่า leaf ไหน "อยู่ในทาง" (ขาดข้อนี้ = แตกได้ แต่เรียงลำดับไม่ได้)
- [ ] **Tracker เขียนได้** (`bd` หรืออื่น) + สิทธิ์สร้าง dep — leaf ที่ไม่มี edge = drain แยกไม่ออกว่าอันไหน independent
- [ ] **Interface contract** ถ้าข้าม service/module (Sara กำหนดก่อน — ดู § Chunk)

ขาดข้อใด → list สิ่งที่ขาด แล้วหยุด ห้ามเดา

## 🎯 Tracer bullet — เกณฑ์เดียวที่ตัดสินว่าแตกถูกหรือผิด

**leaf 1 ใบ = ตัดทะลุทุก layer แล้วส่งของที่ verify ได้จริง** — บาง แต่ครบตั้งแต่ต้นจนจบ

```
✅ ถูก (vertical)                        ❌ ผิด (horizontal)
"ผู้ใช้ขอคืนเงิน 1 รายการได้"            "สร้าง DB schema ทั้งหมด"
  DB + API + UI + test ครบสำหรับเคสนี้      "ทำ API ทุก endpoint"
  merge แล้วมีคนใช้ได้จริง                 "ต่อ UI ทั้งหมด"
                                          merge 2 ใบแรกแล้วยังไม่มีอะไรใช้ได้
```

horizontal slicing เป็น anti-pattern เดียวกับที่ `dev-gate` ห้ามในระดับ test — ที่นี่คือระดับ backlog: **ล็อคโครงสร้างก่อนเข้าใจงาน แล้วรู้ตัวตอนใบสุดท้าย**

**Test ว่าเป็น tracer bullet จริงไหม**: ถ้า merge ใบนี้ใบเดียวแล้วหยุดโครงการทันที — **มีใครได้อะไรไหม?** ไม่มี = ยังไม่ใช่ leaf ที่ถูก

## 📏 เล็กพอหรือยัง

INVEST ของ Bella มี "Small" แต่ไม่มีตัวเลข — ที่นี่ให้เกณฑ์ที่ตรวจได้:

- [ ] **1 leaf = 1 pipeline run** (Phase 2 → 3a → 3b → 4) จบใน session เดียวของ Dave
- [ ] **AC ≤ ~5 ข้อ** — เกินนั้นมักมีมากกว่า 1 behavior ปนอยู่
- [ ] **แตะ module/service เดียว** — ข้าม service = ต้องมี interface contract ก่อน (§ Chunk)
- [ ] **verify ได้ด้วยตัวมันเอง** — มี test/หลักฐานที่บอกว่า "ใบนี้เสร็จ" โดยไม่ต้องรอใบอื่น
- [ ] **describe ได้ใน 1 ประโยคที่มีกริยาของผู้ใช้** — เขียนเป็นชื่อ layer (`"schema"`, `"refactor service"`) = สัญญาณ horizontal

ยังไม่ผ่าน 2 ข้อขึ้นไป → แตกต่อ. **แตกได้ ≤ 2 ชั้น** (epic → leaf); ลึกกว่านั้นแปลว่า outcome กว้างเกิน → กลับไปคุย scope กับ Patrick

## 🔗 Blocking edge — ประกาศตอนสร้าง ไม่ใช่ค่อยไปเดาทีหลัง

🔴 ทุกใบต้องประกาศ dep ของตัวเอง **ตอนสร้าง**. leaf ที่ไม่มี edge = `drain` ต้องมานั่ง verify เองว่าใบไหน independent (ซึ่งเป็นงานที่ไม่ควรต้องทำ)

**create-then-wire — 2 pass เสมอ** (issue ต้องมี id ก่อนถึงอ้างกันได้):

```bash
# pass 1 — สร้างให้ครบก่อน เก็บ id
bd create "ผู้ใช้ขอคืนเงิน 1 รายการได้" -t feature -p1      # → 41
bd create "แสดงสถานะคำขอคืนเงินในหน้าประวัติ" -t feature -p2  # → 42
bd create "ผู้ดูแลอนุมัติคำขอคืนเงิน" -t feature -p2         # → 43

# pass 2 — ค่อย wire
bd link 41 42 blocks        # 42 รอ 41
bd link 41 43 blocks
bd link <epic> 41 parent-child
bd ready --json             # ✅ frontier คำนวณเอง: ควรเห็น 41 ใบเดียว
```

**เกณฑ์ edge**: ใส่ `blocks` เฉพาะ **dep จริง** (ใบหลังใช้ output/interface ของใบแรก) — ห้ามใส่เพราะ "อยากให้ทำก่อน" นั่นคือ **ลำดับความสำคัญ** ใช้ `-p` ไม่ใช่ edge
edge ปลอมทำให้ `bd ready` ว่างทั้งที่งานทำขนานได้ → `drain` fan-out ไม่ได้

**Verify หลัง wire (🔴 ห้ามข้าม)**: `bd ready --json` ต้องคืน **อย่างน้อย 1 ใบ**. ว่าง = มี cycle หรือ edge ปลอม → แก้ก่อนส่งต่อ

## 🧩 Chunk — เมื่อต้องข้าม service/module

จาก `shode-house-routing` § Pipeline parallel: **Sara กำหนด interface contract ระหว่าง chunk ก่อน** แล้ว downstream chunk จะไม่ block จนกว่า interface จะเปลี่ยน

```
Sara: contract ของ chunk A↔B  →  A กับ B ทำขนานได้ (edge = contract ไม่ใช่ code)
ไม่มี contract              →  B ต้องรอ A เสร็จจริง (serialize, ช้ากว่ามาก)
```
contract เปลี่ยนกลางทาง = **spec change** → bd revision ตาม drift M5 ไม่ใช่แก้เงียบ ๆ

## ✂️ Process

1. **อ่าน spec + outcome** — ถ้าเป็น XL ให้ดู T-shirt ต่อ module จาก `/design-system --estimate` (ถ้ามี) เป็นจุดตั้งต้นของการแบ่ง
2. **ร่าง leaf จาก AC ไม่ใช่จาก layer** — ไล่ user story/AC แล้วถามทีละข้อว่า "ข้อนี้ merge เดี่ยว ๆ แล้วมีคนได้อะไรไหม"
3. **เช็คขนาด** (§ เล็กพอหรือยัง) → ยังใหญ่ก็แตกต่อ (≤ 2 ชั้น)
4. **หา dep จริง** — เขียน edge ลงกระดาษก่อน แล้วถามทุกเส้นว่า "ถ้าไม่มีเส้นนี้ ใบหลังพังตรงไหน" ตอบไม่ได้ = edge ปลอม ตัดทิ้ง
5. **create-then-wire 2 pass** (§ Blocking edge) + `bd link <epic> <leaf> parent-child` ทุกใบ
6. **`bd ready --json` verify** — paste output เป็นหลักฐาน
7. **ส่งต่อ**: frontier 1 ใบ → `/implement bd-<id>` · frontier หลายใบที่ concrete + file-disjoint → `drain`

## 🚫 Anti-pattern

| อาการ | ทำไมผิด | แก้ |
|---|---|---|
| leaf ชื่อเป็น layer (`"ทำ API"`, `"ต่อ DB"`) | horizontal — merge แล้วไม่มีใครได้อะไร | ตั้งชื่อด้วยกริยาของผู้ใช้ |
| แตกก่อนมี spec | ซอยสิ่งที่ยังไม่รู้ว่าคืออะไร | wayfinding (fog) → design-system (spec) → ค่อยแตก |
| ทุกใบ `blocks` กันเป็นสายโซ่ | ส่วนใหญ่เป็น priority ไม่ใช่ dep → drain ทำขนานไม่ได้ | ตัด edge ที่ตอบไม่ได้ว่าพังตรงไหน |
| แตก 4-5 ชั้น | outcome กว้างเกินจะเป็น 1 epic | กลับไปคุย scope กับ Patrick |
| leaf ไม่มี AC | ไม่มีใครรู้ว่าเสร็จเมื่อไหร่ → Anti-Puppet Done | copy AC ที่เกี่ยวจาก spec ลงทุกใบ |

## Skill composition (where to go next)

| สถานการณ์ | ไปไหน | เพราะ |
|---|---|---|
| ยังมีหมอก ตอบไม่ได้ว่าเสร็จหน้าตายังไง | → `shode-house-workflow/wayfinding.md` | Map + decision ticket ก่อน (decompose ต้องการ spec ที่นิ่ง) |
| spec ยังไม่มี | → `/design-system` | Bella ∥ Sara ผลิต BRD + ADR ก่อน |
| แตกเสร็จ มี frontier หลายใบ concrete + file-disjoint | → `drain` | fan-out worktree + serial cherry-pick + close-on-done |
| แตกเสร็จ frontier ใบเดียว | → `/implement bd-<id>` | pipeline ปกติ |
| leaf ข้าม service ยังไม่มี contract | → Sara (`api-contract` skill) | contract คือสิ่งที่ทำให้ chunk ขนานได้ |
