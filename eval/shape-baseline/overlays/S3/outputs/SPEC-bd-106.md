# SPEC bd-106 — format_duration

## Scope
เพิ่มฟังก์ชัน `format_duration(seconds)` ในไฟล์ใหม่ `src/durationfmt.py` แปลงจำนวนวินาทีเป็นข้อความสั้น เช่น `1h30m`
ไม่แตะ module อื่น ไม่มี UI ไม่มี API ไม่มีข้อมูลส่วนบุคคล/การเงิน/การยืนยันตัวตน

## Acceptance criteria
- AC-1 `format_duration(5400)` คืน `"1h30m"`; หน่วยที่ใช้คือ `h` `m` `s` เรียงจากใหญ่ไปเล็ก ไม่มีช่องว่าง
- AC-2 `format_duration(0)` คืน `"0s"`
- AC-3 หน่วยที่มีค่าเป็นศูนย์ไม่แสดง: `3600` → `"1h"`, `3661` → `"1h1m1s"`, `59` → `"59s"`
- AC-4 ค่าติดลบ หรือค่าที่ไม่ใช่ `int` (รวมถึง `bool`, `float`, `str`, `None`) → `ValueError`
- AC-5 ไม่มีหน่วยวัน: ตั้งแต่ 86400 วินาทีขึ้นไปใช้ชั่วโมงสะสม เช่น `90000` → `"25h"`
- AC-6 มี unit test ใน `tests/` ครอบคลุม AC-1 ถึง AC-5 และ test เดิมของ project ยังผ่าน

## Out of scope
การ parse ข้อความกลับเป็นวินาที · localisation · หน่วยที่เล็กกว่าวินาที

## Status
approved (phase-1a signed off) — พร้อม implement
