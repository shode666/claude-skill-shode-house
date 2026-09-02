# diagnose-full

- command: `diagnose`
- agents ที่คาดว่าจะถูกเรียก: developer, qa-engineer
- target token reduction: 10%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
p95 ของ /search ขึ้นจาก 180ms เป็น 1.2s หลัง deploy เมื่อวาน หา root cause
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] สร้าง feedback loop ก่อน (วิธี 1-3)
- [ ] ไม่สำเร็จ → โหลด loop-ladder.md
- [ ] Quinn ยืนยันด้วย test

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/diagnose-full/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
