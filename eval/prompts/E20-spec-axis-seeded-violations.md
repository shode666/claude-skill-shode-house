# E20 — Spec axis catches seeded acceptance-criteria violations (4.0.1 routing, not yet measured)

- kind: `core` (SEC-8) · fixture: `scripts/eval-fixture-core.sh --scenario E20` (asset `auditexport`: `outputs/SPEC-bd-120.md`, `src/audit_export.py`, a green `tests/test_audit_export.py`)
- seeded: 6 acceptance criteria; the implementation violates 4 (AC-2, AC-3, AC-4, AC-6) and meets 2 (AC-1, AC-5, the decoys); the unit tests pass, so only a spec reading finds the 4
- expected: a `plan` spawn (spec axis) reports the violated criteria; scored by `python3 eval/scenarios/core-4.0.1/check-probes.py E20 <trace.jsonl>...` (a structured text scorer: it reads only the closed-form lines `AC-n: MET` / `AC-n: VIOLATED`; a run without one for every criterion is UNSCORABLE and a human adjudicates) against the pre-registered catch-rate threshold in `eval/scenarios/core-4.0.1/probes-4.0.1.json`, with the 4.0.0 `business-analyst` baseline on the same fixture
- runner: not part of `eval/run-core.sh`

## Prompt (verbatim every run, do not edit; revised once before any run, U30: the closed-form answer line was added)

```
ตรวจเฉพาะว่า src/audit_export.py ทำตามสเปก outputs/SPEC-bd-120.md ครบทุกข้อไหม (AC-1 ถึง AC-6) บอกว่าข้อไหนไม่ตรง ยังไม่ต้องแก้ code
ให้ผู้ตรวจตอบทีละข้อ หนึ่งบรรทัดต่อหนึ่งข้อ ครบทั้ง 6 ข้อ ในรูปนี้เท่านั้น: `AC-n: MET` หรือ `AC-n: VIOLATED` (ตัวพิมพ์ใหญ่ ไม่มีอักขระอื่นในบรรทัดนั้น) เหตุผลเขียนในบรรทัดแยก และให้ส่งบรรทัดเหล่านี้กลับมาในคำตอบสุดท้าย
```
