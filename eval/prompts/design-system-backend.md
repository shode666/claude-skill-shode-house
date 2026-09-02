# design-system-backend

- command: `/design-system`
- agents ที่คาดว่าจะถูกเรียก: business-analyst, solution-architect
- target token reduction: 15%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/design-system ทำ service เก็บ audit log ของทุก write operation ใน ERP ภายใน ใช้ Postgres ที่มีอยู่
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] Bella + Sara parallel Phase 1a
- [ ] ไม่เรียก Uma (ไม่มี frontend)
- [ ] ไม่เรียก domain expert (ไม่มี money/regulation trigger)
- [ ] clarifying option-style ก่อนลงมือ ไม่เดา

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/design-system-backend/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
