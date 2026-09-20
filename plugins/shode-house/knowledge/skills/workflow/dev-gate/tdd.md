# Dev Gate — TDD depth (seams, worked example, scope, anti-patterns)

```lazy-load-contract
LOAD: skills/workflow/dev-gate/tdd.md
WHEN: new_behavior=true OR bug_fix_regression_test=true
OWNER: developer
REQUIRED-BEFORE: first_test_written
```

Root `SKILL.md` rules (invariants, YAGNI ladder, carve-out, red → green → refactor) apply throughout.

### 0.5 🎯 Seams — ตกลงก่อนเขียน test

**seam** = public boundary ที่เราสังเกต behavior ได้โดยไม่เอื้อมเข้าไปข้างใน. test อยู่ที่ seam เท่านั้น ไม่ใช่ที่ internal

🔴 **เขียน test ไม่ได้จนกว่าจะ list seam ที่จะ test แล้ว confirm** (กับ user หรือกับ AC ใน spec). ห้ามมี test ตัวไหนเขียนที่ seam ที่ยังไม่ confirm
> เหตุผล: test ทุกอย่างไม่ได้ — ตกลง seam ล่วงหน้าคือวิธีให้แรงเทสต์ลงที่ critical path + logic ซับซ้อน แทนที่จะกระจายไปทุก edge case
> Coverage follows the adopted target (Gate 8); a percentage alone proves neither sufficient tests nor the right seams.

ถามตรง ๆ ก่อนเริ่ม: *"public interface คืออะไร แล้วจะ test ที่ seam ไหนบ้าง?"*
รูปร่างของ interface เองยังไม่นิ่ง (ลึกแค่ไหน seam อยู่ตรงไหน) → ดู [quality-gates.md](quality-gates.md) (Gate 0 — Deep module)

### 1. 🔴 Red — worked example

```python
def test_calculate_total_with_vat_includes_7_percent():
    cart = Cart(items=[Item(price=Decimal("100"))])
    total = cart.total_with_vat(rate=Decimal("0.07"))
    assert total == Decimal("107.00")
```

### TDD scope
✅ **เหมาะ**: business logic, calc, validation, state machine, parser, algorithm, bug-fix regression
❌ **ไม่เหมาะ**: UI prototype, spike, pure framework integration

### 🚫 3 anti-pattern ที่ทำให้ coverage สูงแต่ test ไร้ค่า

- **Implementation-coupled** — mock collaborator ภายใน / test private method / verify ผ่านช่องข้าง (query DB แทนใช้ interface)
  *สัญญาณ*: refactor แล้ว test แตก ทั้งที่ behavior ไม่เปลี่ยน
- **Tautological** — assertion คำนวณค่าที่คาดหวังด้วยวิธีเดียวกับ code (`expect(add(a,b)).toBe(a+b)` · snapshot ที่ derive มาด้วยมือแบบเดียวกัน · constant assert เท่ากับตัวเอง) → **ผ่านโดยโครงสร้าง ไม่มีวันเถียงกับ code ได้**
  *ทางแก้*: ค่าที่คาดหวังต้องมาจาก **แหล่งอิสระ** — literal ที่รู้ว่าถูก, worked example, ตัวเลขจาก spec
  > นี่คือเหตุผลที่ coverage 80% เขียวตลอดกาลโดยไม่เคยจับ bug อะไรเลย
- **Horizontal slicing** — เขียน test ทั้งชุดก่อน แล้วค่อย implement ทั้งชุด → test ตรวจ behavior **ในจินตนาการ**, ล็อค test structure ก่อนเข้าใจ implementation, และ test จะด้านต่อการเปลี่ยนแปลงจริง
  *ทางแก้*: **vertical slice** — 1 test → 1 implementation → ทำซ้ำ. แต่ละ test คือ **tracer bullet** ที่ตอบสนองสิ่งที่รอบก่อนสอน
