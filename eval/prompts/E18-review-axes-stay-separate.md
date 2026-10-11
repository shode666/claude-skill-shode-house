# E18 — Review keeps the axes as separate spawns across shared types (4.0.1 routing, not yet measured)

- kind: `core` · fixture: `scripts/eval-fixture-core.sh --scenario E18` (no extra assets)
- expected: a `verify` spawn (standards) and a `plan` spawn (spec) are both dispatched; the reply keeps the Standards and Spec findings under separate headings
- runner: not part of `eval/run-core.sh`

## Prompt (verbatim every run, do not edit)

```
review การเปลี่ยนแปลงล่าสุดใน src/notification.py ให้หน่อย (retry + backoff) ทั้ง code quality และตรงตาม spec ที่ขอไหม
```
