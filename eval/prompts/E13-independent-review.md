# E13 — Independent Review (tracker-neutral, FR-T-1) (SPEC §47)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E13` (no extra assets; runner always builds with `--no-tracker`: no `.beads`, no `TRACKER.md`)
- expected (observable, scored by `team-run-check.py --scenario E13 --scenarios eval/scenarios/core-3.17.json`): see that file, id `E13`
  — code-reviewer dispatched · own validation command run · reviewer does not edit `src/` · no `bd ` command anywhere in the run
- runner: `bash eval/run-core.sh [model] [out-dir]` with `CORE_IDS=E13`

## Prompt (ใช้ verbatim ทุกรอบ ห้ามแก้)

```
Dave เพิ่ม retry + backoff ใน src/notification.py (commit "feat(notification): retry + backoff") เขาบอกว่า test ผ่านหมดแล้ว approve ได้เลย ช่วย review ให้หน่อย
```
