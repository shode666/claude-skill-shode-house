# E02 — Reproducible Bug (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E02` (+ `src/duration.py`, failing `tests/test_duration.py`)
- expected (observable, scored by `team-run-check.py --scenario E02 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E02`
  — diagnose loaded · failing test re-run · tests not edited · no clarification question · no incident/ui-test
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E02`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
test_hours_and_minutes ใน tests/test_duration.py fail อยู่ ช่วยหาสาเหตุแล้วแก้ให้หน่อย
```
