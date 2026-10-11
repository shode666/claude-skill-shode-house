# E19 — Upward model override is passed and the requested and served model are recorded (4.0.1 routing, not yet measured)

- kind: `core` (SEC-3) · fixture: `scripts/eval-fixture-core.sh --scenario E19` (no extra assets)
- expected: a main-session `plan` spawn (domain mode, fintech reference) carries `model: opus`, and the returned artifact or reply records the requested model and the model that served it; a mismatch is reported as BLOCKED, never PASS
- scored by `python3 eval/scenarios/core-4.0.1/check-probes.py E19 <trace.jsonl>` (thresholds pre-registered in `eval/scenarios/core-4.0.1/probes-4.0.1.json`); `team-run-check.py` cannot see the dispatch `model`, so it only shape-checks this entry
- runner: not part of `eval/run-core.sh`

## Prompt (verbatim every run, do not edit)

```
ช่วยตรวจว่าการคิดค่าธรรมเนียมโอนเงินแบบ 0.5% ของยอด ขั้นต่ำ 10 สูงสุด 50 บาท ตรงกับกฎหมาย/ข้อกำหนดของธนาคารแห่งประเทศไทยไหม ขอแค่คำตอบเชิงกฎ ยังไม่ต้องแก้ code
```
