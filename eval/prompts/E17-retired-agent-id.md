# E17 — A retired 4.0.0 agent id named by the user (4.0.1 routing, not yet measured)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E17` (no extra assets)
- expected: the router answers from `skills/discipline/shode-house-routing/ownership.md` § Formerly and dispatches `build`; no spawn of `developer`, `code-reviewer` or `qa-engineer` (neither namespaced nor bare)
- runner: not part of `eval/run-core.sh`

## Prompt (verbatim every run, do not edit)

```
ช่วยเรียก agent developer ให้เพิ่มฟังก์ชัน retry ใน src/notification.py หน่อย
```
