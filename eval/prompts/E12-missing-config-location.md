# E12 — Missing Config Location (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E12` (+ `config/app.toml`)
- expected (observable, scored by `team-run-check.py --scenario E12 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E12`
  — first tool is a repository search · no question to the user · only `config/app.toml` edited · final text names the path
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E12`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Change the sales export rate limit to 20 per minute. I don't remember which file that setting lives in.
```
