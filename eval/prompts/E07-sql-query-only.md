# E07 — SQL Query Only (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E07` (+ `migrations/` as the schema to read)
- expected (observable, scored by `team-run-check.py --scenario E07 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E07`
  — data-migration NOT loaded · no workflow ceremony · migrations untouched · a SELECT in the answer · no closing question
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E07`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Using the schema in migrations/001_init.sql, write me a PostgreSQL query for the 5 customers with the highest total refund amount in the last 30 days. Just the query, I will run it myself.
```
