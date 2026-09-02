# phase3b-sensitive

- command: `/implement`
- agents ที่คาดว่าจะถูกเรียก: code-reviewer, qa-engineer, business-analyst, security-engineer, fintech-expert
- target token reduction: 20%

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้ระหว่าง A/B)

```
/review รีวิว diff ตั้งแต่ commit def5678 — แก้ ledger posting + เก็บเลขบัตรบางส่วน
```

## Behavior assertions (ตรวจก่อนดูตัวเลข — accuracy มาก่อน token)

- [ ] Sentinel เข้า (auth/money/PII trigger)
- [ ] Felix validate business rule
- [ ] ห้าม merge โดยไม่มีลายเซ็น domain + security

## บันทึกผล

1 record = 1 agent invocation → `<run-dir>/phase3b-sensitive/<agent>-<n>.json` ตาม `eval/usage-record.schema.json`
assertion ที่ fail = **promotion blocker** ไม่ว่า token จะลดเท่าไร
