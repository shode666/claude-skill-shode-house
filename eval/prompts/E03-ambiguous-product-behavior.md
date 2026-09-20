# E03 — Ambiguous Product Behavior (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E03` (no extra assets; target `src/report.py`)
- expected (observable, scored by `team-run-check.py --scenario E03 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E03`
  — asks (question in the final text or AskUserQuestion) · writes nothing · developer not dispatched
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E03`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
ลูกค้าบ่นว่า export ยอดขายใน src/report.py ได้ข้อมูลเก่าปนมาด้วย ช่วยแก้ให้ตัดข้อมูลเก่าออกที
```
