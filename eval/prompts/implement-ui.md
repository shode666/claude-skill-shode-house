# implement-ui

- command: `/implement`
- agents ที่คาดว่าจะถูกเรียก: developer, ux-ui-designer, code-reviewer, qa-engineer, business-analyst
- target token reduction: 15%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/implement bd-102 ทำหน้า refund history ตาม wireframe ที่ Uma ส่งไว้
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] pre-implement-ui gate: ต้องมี Uma artifact ก่อน
- [ ] Phase 3a Uma verify + paste visual evidence
- [ ] ทำ Playwright ไม่ได้ = BLOCKED ไม่ใช่ PASS

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/implement-ui/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
