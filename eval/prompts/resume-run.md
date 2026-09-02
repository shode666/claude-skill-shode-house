# resume-run

- command: `/implement`
- agents ที่คาดว่าจะถูกเรียก: orchestrator, developer
- target token reduction: 10%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/implement ทำต่อจาก bd-103 ที่ค้างอยู่ รอบที่แล้ว Phase 2 เสร็จแล้วแต่ยังไม่ได้ review
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] อ่าน run stamp / resume protocol
- [ ] ไม่ทำ Phase 2 ซ้ำ
- [ ] M1 ingress guard: bd show ก่อนตอบ

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/resume-run/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
