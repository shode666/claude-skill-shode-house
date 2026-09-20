# E04 — Java Backend Change (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E04` (+ `java-svc/` Maven module)
- expected (observable, scored by `team-run-check.py --scenario E04 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E04`
  — developer or dev-gate route · only the Java language reference read · no UI skill/agent · Java build/test attempted · Python/web untouched
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E04`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
In java-svc, make OrderService.create() reject a quantity of zero or less with IllegalArgumentException("QUANTITY_INVALID"), and cover it with a unit test.
```
