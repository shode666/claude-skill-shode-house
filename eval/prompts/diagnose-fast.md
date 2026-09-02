# diagnose-fast

- command: `diagnose`
- agents ที่คาดว่าจะถูกเรียก: developer
- target token reduction: 25%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
payment webhook ตอบ 200 แต่ order ไม่ถูก update ตั้งแต่เมื่อวาน
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] reproduce ก่อน fix
- [ ] redact ก่อน paste log
- [ ] ranked falsifiable hypotheses
- [ ] ไม่ patch โดยไม่มี root cause

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/diagnose-fast/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
