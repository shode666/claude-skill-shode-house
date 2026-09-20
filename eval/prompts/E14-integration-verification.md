# E14 — Integration Verification (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E14` (+ `src/signup.py` calling validators + notification)
- expected (observable, scored by `team-run-check.py --scenario E14 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E14`
  — qa-engineer dispatched · own execution evidence · `src/` not edited · final text reports the cross-module defect
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E14`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Dave just added src/signup.py (register -> require_email -> notification.send). He says he tried it by hand and it works. Please verify the integration between those three modules actually holds. There is no real SMTP server on this machine.
```
