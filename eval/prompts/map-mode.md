# map-mode

- command: `wayfinding`
- agents ที่คาดว่าจะถูกเรียก: orchestrator, product-manager
- target token reduction: 10%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
อยากทำระบบ loyalty ทั้งระบบ ยังไม่รู้จะเริ่มตรงไหน มีทั้ง earn/burn/tier/partner
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] Oliver เข้า Map mode ไม่ใช่ /design-system ตรง ๆ
- [ ] โหลด wayfinding.md
- [ ] สร้าง decision ticket + fog of war + out of scope

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/map-mode/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
