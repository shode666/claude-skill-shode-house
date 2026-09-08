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

## ลำดับต่อไป (roadmap Phase B)
1. golden E2E scenario เริ่มจาก main orchestrator (routing → agent → artifact → review → verify → bd CLOSED)
2. behavioral scorer: expected routing · required artifact/evidence exists · forbidden claim ไม่เกิด · security agent ถูกเรียกเมื่อแตะ PII/money · final state CLOSED + evidence
3. หลายรอบต่อ scenario → median/p90 → regression gate ก่อน tag release

## วิธีรัน
→ [`RUNBOOK.md`](RUNBOOK.md) (ต้องใช้ Claude Code/Cowork จริง — sandbox ทำแทนไม่ได้)
