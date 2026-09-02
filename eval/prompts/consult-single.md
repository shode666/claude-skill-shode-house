# consult-single

- command: `/consult`
- agents ที่คาดว่าจะถูกเรียก: solution-architect
- target token reduction: 25%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/consult ระบบ order ของเรามี endpoint เดียวรับ 3 หน้าที่ (create/update/cancel) ควรแยกไหม
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] route ไป solution-architect ตัวเดียว ไม่ fan-out
- [ ] ไม่เปิด pipeline เต็ม
- [ ] ตอบภาษาเดียวกับ prompt (ไทย)

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/consult-single/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร

## ผลรอบที่ 1 (baseline 3.12.1, Cowork)

- [x] route ไป solution-architect ตัวเดียว ไม่ fan-out
- [x] ไม่เปิด pipeline เต็ม
- [x] ตอบภาษาเดียวกับ prompt (ไทย)
- [x] **NO MAGIC ทำงานจริง** — Sara ปฏิเสธที่จะ claim เรื่อง endpoint ของ project เพราะไม่มี tool เข้าถึง repo แล้วขอหลักฐานก่อน
- [x] clarifying option-style + frontier — ถาม Q1-Q4 รอบเดียว, recommend ทุกข้อ, ประกาศว่าคำถามรอบถัดไปยังไม่ถาม
- [x] tag prefix + handoff line ถูกรูปแบบ (`[Sara|state:adhoc|bd:none]`, `Sara ▸ user :`)

usage: cache_write 100,598 · cache_read 60,836 · out 545 · effective 101,153 tok (5 turns)
