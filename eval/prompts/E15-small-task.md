# E15 — Small Task (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E15` (no extra assets; target `src/notification.py`)
- expected (observable, scored by `team-run-check.py --scenario E15 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E15`
  — at most 2 spawns · no workflow/decompose/drain ceremony · no senior/domain agent · only `src/notification.py` edited · no `outputs/` artifact · some check command run · no closing question
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E15`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Rename the RETRY constant in src/notification.py to MAX_RETRIES and update its use.
```
