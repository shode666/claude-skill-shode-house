# E01 — Simple Local Fix (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture.sh --no-tracker --no-resolve` (commit "validators + targeted tests")
- expected (observable, scored by `team-run-check.py --scenario E01`): see `eval/scenarios/golden.json` id `E01`
  — edit `src/validators.py` only · targeted test · no architecture/domain agent · no `outputs/` artifact · no closing question
- runner: `bash eval/run-e01.sh [model]`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Fix typo in error message.
```
