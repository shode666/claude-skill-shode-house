---
name: tdd
description: |
  ใช้เมื่อ user สั่ง "TDD", "test first", "เขียน test ก่อน", "red-green-refactor", หรือเริ่ม implement business logic ใหม่ที่ต้องการ confidence + safety net — บังคับ red→green→refactor cycle, ห้าม code ก่อน test
---

# Test-Driven Development (red → green → refactor)

> Inspired by mattpocock/skills (engineering/tdd) — adapted for shode-house

> **Owner**: Chris (test design) + Dave (implement). เปิด skill นี้เมื่อทำ business logic หลัก, money calc, state machine, algorithm

## หลักการ (🔴)

**No production code without failing test first**

- Test = spec ที่ executable
- Test ที่ pass ตอนแรก = ไม่ได้ test อะไร
- Refactor ปลอดภัยเพราะ test ครอบ → ไม่มี test = ห้าม refactor

## Cycle

### 1. 🔴 Red — เขียน test ที่ fail

- Test เล็กที่สุด — 1 behavior
- Naming: `should_<behavior>_when_<condition>` หรือ G-W-T
- Run test → ต้อง fail (ถ้า pass = test ผิด หรือ behavior มีอยู่แล้ว)
- Fail ด้วย reason ที่ถูก (compile error ไม่นับ — ต้องเป็น assertion fail)

```python
def test_calculate_total_with_vat_includes_7_percent():
    # Given
    cart = Cart(items=[Item(price=Decimal("100"))])
    # When
    total = cart.total_with_vat(rate=Decimal("0.07"))
    # Then
    assert total == Decimal("107.00")
```

### 2. 🟢 Green — เขียน code น้อยที่สุดที่ pass

- **Simplest thing that works** — แม้จะ "โง่" (return hardcoded ก็ได้)
- ห้าม anticipate future requirement (YAGNI)
- Run test → ต้อง pass
- ห้าม refactor ตอนนี้ — แยก step

### 3. 🔵 Refactor — clean up

- Test ยัง pass — รัน every change
- Remove duplication, improve naming, extract function
- ทำ code ดี + readable
- ห้ามเพิ่ม behavior ใหม่ — refactor = no new test

## ขนาด Test

- **เร็ว** (< 100ms): unit test logic
- **กลาง** (100ms-1s): integration กับ DB/cache (Quinn)
- **ช้า** (> 1s): E2E (Quinn)

TDD focus: **fast unit tests** — slow tests กระทบ flow

## Test First สำหรับอะไร

✅ **เหมาะ**:
- Business logic, calc, validation
- State machine
- Parser, formatter
- Algorithm (sort, search, match)
- Bug fix (regression test ก่อน fix)

❌ **ไม่เหมาะ**:
- UI prototype (visual feedback ดีกว่า)
- Spike (throwaway code)
- Pure framework integration (test framework แทน)

## Hand-off

Dave ทำ TDD แล้ว → Chris review test cases (edge case ครบ?) + add property-based test ถ้า invariant สำคัญ

## ห้าม

- ห้ามเขียน code ก่อน test (TDD core rule)
- ห้าม commit test ที่ยัง fail (ใช้ skip/xfail แทน + bd issue)
- ห้าม refactor พร้อม add behavior — แยก commit
- ห้าม mock business logic — mock เฉพาะ external (DB/API/clock)
- ห้ามใช้ time.sleep ใน test → fake time / freeze
- ห้าม shared state ระหว่าง test
