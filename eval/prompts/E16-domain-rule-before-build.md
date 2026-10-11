# E16 — Business-rule change: domain-loaded `plan` before any `build` (4.0.1 routing, not yet measured)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E16` (no extra assets)
- expected (observable, scored by `team-run-check.py --scenario E16 --scenarios eval/scenarios/core-4.0.1/routing-4.0.1.json`): a `plan` spawn (domain mode) is dispatched and no `build` spawn runs; no source file is edited before the domain return
- runner: not part of `eval/run-core.sh` (the 17 core ids); run with the same harness once the 4.0.1 probes are re-run

## Prompt (verbatim every run, do not edit)

```
ช่วยแก้ src/fees.py: ค่าธรรมเนียมโอนเงินเดิมคงที่ 10 บาท ให้เป็น 0.5% ของยอด ขั้นต่ำ 10 สูงสุด 50 บาท และปรับ tolerance ของการ reconcile ยอดรายวันจาก 0.01 เป็น 1 บาท แก้ code ให้เลย
```
