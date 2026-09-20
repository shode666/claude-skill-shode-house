# E08 — API Breaking Change (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E08` (+ `openapi.yaml`)
- expected (observable, scored by `team-run-check.py --scenario E08 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E08`
  — api-contract skill or solution-architect route · final text carries a compatibility/breaking-change analysis
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E08`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
ใน openapi.yaml อยากเปลี่ยน response ของ refund: field amount (number) เปลี่ยนชื่อเป็น amount_minor แบบ integer หน่วยสตางค์ แล้วตัด status ออกไปเลย mobile app รุ่นเก่ายังเรียก endpoint นี้อยู่นะ ช่วยจัดการให้หน่อย
```
