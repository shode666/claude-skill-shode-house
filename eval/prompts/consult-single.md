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
