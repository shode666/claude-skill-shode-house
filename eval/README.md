# Eval harness — release gate

## สถานะ (v3.13.0)
- ✅ **scenarios.json** — 12 benchmark scenario + target reduction ต่อตัว (design: รัน 5 รอบ รายงาน median + p90)
- ✅ **usage-record.schema.json** — schema ของ record ต่อ agent invocation (5 token type + tool metric)
- ✅ **static baseline** — `.baseline-3.12.1.json` (วัดจาก tag v3.12.1)
- ✅ **runtime A/B v3.12.1 vs v3.13.0** — รันแล้ว 9 agent บน Cowork → [`results/3.13-rc1/`](results/3.13-rc1/)
  - [`COMPARE.md`](results/3.13-rc1/COMPARE.md) — ctx0 ลดทุก agent, รวม −8.2% (target 10–25% เดิม **ไม่ผ่าน** — assumption ผิด)
  - [`BEHAVIOR.md`](results/3.13-rc1/BEHAVIOR.md) — invariant 8 ข้อผ่าน 100% ทั้งสองฝั่ง, ไม่มี regression
- ⛔ **ยังไม่มี**: 5 รอบต่อ scenario (ตอนนี้ 1 run/agent) · E2E ผ่าน command จริง (`/implement`, `/review`) · scorer แบบ machine-verifiable · regression gate ใน CI

## ข้อจำกัดที่ต้องอ่านก่อนอ้างตัวเลข
- 1 run ต่อ agent → ข้อสรุปที่ปลอดภัยคือ "ไม่มี regression" ไม่ใช่ "ดีขึ้น"
- วัดที่ระดับ agent เดี่ยว ไม่ใช่ pipeline — Spec-axis dispatch และ AskUserQuestion relay **ยังไม่เคยถูกทดสอบ end-to-end**
- ctx0 รวม harness ของ Cowork (system prompt + tool list) ซึ่งคงที่ระหว่าง A/B → สัดส่วนที่ plugin ประหยัดได้ดูเล็กกว่า static byte

## E2E golden scenarios + scorer (Phase B — 3.14.0 in progress)
- `eval/scenarios/golden.json` — GS1..GS5 (refund reference · implement-backend · spec-gap catch · AskUserQuestion relay · phase3b-sensitive) — expected routing / artifacts / evidence / forbidden phrases / security triggers / relay / end_state
- `scripts/eval-scorer.py <session-dir> --scenario GSn --outputs-dir <fixture project> --out <run-dir>` — stdlib, python ≥3.9; อ่าน `main.jsonl` + `subagents/` (schema จริงของ Claude Code: Agent tool_use ↔ `agent-*.meta.json.toolUseId`); 7 dimension อิสระ (Routing · Spec fidelity · Security trigger · Evidence · Anti-puppet · bd end_state · Cost); exit 0 PASS / 1 FAIL / 2 UNSCORABLE — ไม่มีวันเดาว่า PASS เมื่อ input หาย
- `scripts/transcript-trim.py <session-dir> <out-dir>` — สำเนาโครงอย่างเดียว (string ≤ 80 chars) สำหรับสร้าง fixture โดยไม่หลุดเนื้อหา project; **Evidence/Anti-puppet ต้อง score บน transcript เต็มเท่านั้น**
- fixtures: `eval/fixtures/transcripts/<case>/` (7 case) + `eval/fixtures/outputs-root/` · tests: `tests/test_eval_scorer.py` (38, AC-1..8)
- 🔴 known limit (accepted, ไม่ patch ต่อ): Evidence/Anti-puppet ใช้ phrase list ไม่ใช่ LLM — negation/sequencing เช่น "done ยังไม่ได้ทำ", "ตรวจแล้วค่อย…" ยัง false-positive (3/10 ใน adversarial set) → scorer quote บรรทัดที่จับได้เสมอ ให้คนตัดสินก่อนถือเป็น regression
- ยังไม่ได้รัน: GS1–5 × 3 รอบบน Claude Code จริง (ต้อง maintainer) → baseline `eval/baseline/e2e-golden/` → regression gate

## ลำดับต่อไป
1. รัน 5 scenario × 3 บน Claude Code จริง → score → baseline
2. regression gate ใน CI (เทียบ baseline: behavior 5 dim 100% PASS, cost median +3%/p90 +5%)

## วิธีรัน
→ [`RUNBOOK.md`](RUNBOOK.md) (ต้องใช้ Claude Code/Cowork จริง — sandbox ทำแทนไม่ได้)
