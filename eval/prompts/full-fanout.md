# full-fanout

- command: `synthetic`
- agents ที่คาดว่าจะถูกเรียก: *
- target token reduction: 15%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
(synthetic) วัด context เมื่อทั้ง 19 agent ถูก dispatch
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] ไม่ต้องรัน runtime — ใช้ scripts/context-budget.py เป็นตัวแทน

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/full-fanout/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
