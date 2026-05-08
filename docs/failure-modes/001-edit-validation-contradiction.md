# Failure Mode #001 — Edit Screen Validation Contradiction

> Catalog seed entry. ทุก failure ที่ user เจอจริง = 1 file ที่นี่ — feed กลับเข้า rule patch แทนที่จะคาดเดา

## Summary

หน้า edit (price / quantity / status / config / etc.) มี validation ที่ require `input === current_state` (หรือ semantic equivalent) → ทำให้ save ไม่ได้ตลอด: ถ้า input ตรงกับ current = ไม่มีอะไรต้องเปลี่ยน, ถ้าจะเปลี่ยน = input ไม่ตรง = validation block

## Reported by
shode666 — engagement session, May 7, 2026

## Symptom
- User แก้ค่าในหน้า edit → submit → "validation failed"
- ลอง submit ค่าเดิม → pass ทาง validator แต่ไม่มี mutation จริง
- Test pass หมด (เพราะ unit test ใช้ input ที่ตรงกับ state ใน fixture)
- User ยืนยัน feature "แก้ราคา" ใช้งานไม่ได้บน production

## Root cause (4-layer)

1. **Bella (BA)** — AC ระบุ "user แก้ราคาได้" แต่ไม่ได้บังคับ "edit screen ต้องไม่มี gate ที่ทำให้แก้ไม่ได้" → Dave ตีความช่องว่างเอง
2. **Dave (Dev)** — ใส่ defensive validation "เพื่อความปลอดภัย" ที่ปิด valid input space ทั้งหมด, ไม่ trace ว่ายังมี input path ที่ผ่านได้ไหม
3. **Chris (Reviewer)** — review code logic ของ validator (ทำงานถูกตามที่เขียน) ไม่ trace business journey ว่า user เดินผ่าน feature นี้ end-to-end ได้ไหม
4. **Quinn (QA)** — เขียน unit test ของ `validatePrice(input, current)` (assertion ผ่านเมื่อ equal) → tautology test, ไม่ได้ทดสอบ feature contract

## Pattern (เพื่อ detection)

- Validation ที่ทำให้ valid input space เป็น **empty set** หรือ **trivial set** (e.g. input == state)
- Test ที่ assertion ผ่านสำหรับทุก realistic input = ไม่ได้ทดสอบอะไร
- Code ที่ semantic ขัดกับ feature name (e.g. `EditForm` ที่ reject edit, `SaveButton` ที่ block save)
- Defensive validation ที่ Dave ใส่เองโดยไม่มีใน spec/AC

## Mechanism ที่จับ (ปัจจุบัน)

- **Quinn → Mutation Evidence rule** (`agents/qa-engineer.md` § Mutation Evidence, v2.4.1)
  - Test ต้องเปลี่ยน value (`new_value !== current_value`), submit, query backend, assert value changed
  - ห้าม submit `current_value` (no-op = proves nothing)
- **Dave → Scope Contract Echo field** (`references/scope-lock.md`, v2.4.1)
  - Echo บังคับ confirm understanding ก่อน implement → จับ misinterpretation ก่อน code

## Mechanism ที่ยังไม่จับ (เผื่อเจอ regression)

- **Bella → Feature Intent Statement** — ยังไม่ implement, รอ pain ครั้งที่ 2 ใน catalog ก่อนเพิ่ม rule
- **Dave → Defensive Validation Source-required** — ยังไม่ implement, รอ evidence ว่า Mutation Evidence + Scope Echo ไม่พอ

## Related rules

- `agents/qa-engineer.md` § Mutation Evidence (มี provenance comment ลิงก์มาที่นี่)
- `references/scope-lock.md` § Echo field
- `agents/orchestrator.md` § Scope Contract Enforcement

## Status

**Mitigated** by Mutation Evidence (v2.4.1) + Scope Contract Echo (v2.4.1)
**Watching for regression** — ถ้าเจอเคสที่ rule ทั้ง 2 ผ่านแต่ยังพลาด → escalate, อาจต้องเพิ่ม rule ที่ Bella/Dave layer
