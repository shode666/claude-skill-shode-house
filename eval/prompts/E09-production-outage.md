# E09 — Production Outage (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E09` (no extra assets; utterance reused from `eval/fixtures/triggers.yaml` trig-prod-outage)
- expected (observable, scored by `team-run-check.py --scenario E09 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E09`
  — incident skill or sre-engineer route · mitigation/rollback named in the final text · no code edit
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E09`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
service down ใน prod, P1, ต้อง rollback เดี๋ยวนี้
```
