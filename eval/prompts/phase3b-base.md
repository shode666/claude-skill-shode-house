# phase3b-base

- command: `/implement`
- agents ที่คาดว่าจะถูกเรียก: code-reviewer, qa-engineer, business-analyst
- target token reduction: 20%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/review รีวิว diff ตั้งแต่ commit abc1234 ของ service notification
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] pin fixed point ก่อน fan-out
- [ ] Chris standards + Quinn runtime + Bella spec แยกกัน
- [ ] aggregate แยกหัวข้อ Standards / Spec ห้าม merge

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/phase3b-base/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
