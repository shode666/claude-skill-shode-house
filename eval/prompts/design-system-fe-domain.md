# design-system-fe-domain

- command: `/design-system`
- agents ที่คาดว่าจะถูกเรียก: business-analyst, solution-architect, ux-ui-designer, fintech-expert
- target token reduction: 15%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/design-system หน้า checkout ใหม่ รับบัตรเครดิต + PromptPay ต้องมี 3-D Secure และเก็บ audit ตาม PCI-DSS
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] Phase 1a Bella + Sara
- [ ] Phase 1b Uma + Felix (money trigger)
- [ ] Felix cite standard พร้อม version/clause หรือ mark เป็น general guidance
- [ ] Uma ระบุ WCAG 2.2 SC ที่เกี่ยวข้อง

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/design-system-fe-domain/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
