# E05 — UI Change (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E05` (frozen `--with-ui`: `web/refund-history.*`, rows dated relative to the build day; `FIXTURE_TODAY` pins it)
- expected (observable, scored by `team-run-check.py --scenario E05 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E05`
  — UI verification reached (ui-test skill, Uma or Quinn) · backend/Java untouched · no migration/API/incident skill
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E05`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
หน้า web/refund-history.html เพิ่มตัวเลือก "180 วัน" ใน filter ช่วงเวลา แล้วให้ตารางกรองตามช่วงที่เลือกจริง ๆ ด้วย ตอนนี้เลือกแล้วไม่มีอะไรเปลี่ยน
```
