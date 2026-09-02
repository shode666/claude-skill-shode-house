# implement-backend

- command: `/implement`
- agents ที่คาดว่าจะถูกเรียก: developer, code-reviewer, qa-engineer, business-analyst
- target token reduction: 15%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/implement bd-101 เพิ่ม endpoint POST /refunds ตาม spec ที่ outputs/SPEC-bd-101.md
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] Dave implement ตาม spec
- [ ] Phase 3b Chris ∥ Quinn
- [ ] Bella ตรวจ Spec axis แยก context จาก Chris
- [ ] ไม่มี Uma (ไม่มี UI)

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/implement-backend/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
