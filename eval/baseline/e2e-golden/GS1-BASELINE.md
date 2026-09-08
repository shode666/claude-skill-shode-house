# GS1-reference-refund — E2E baseline (N=3)

**plugin** shode-house 3.14.0-dev @ `6f0b16d`+ (REVIEW DISPATCH CARD) · **runner** Claude Code CLI 2.1.263, `claude -p … --dangerously-skip-permissions`, unattended · **fixture** shode666/shode-house-example-refund @ `69c3c8c` · **date** 2026-09-08 (re-scored 2026-09-08, bd:shode-roadmap/C-C2 R-1 — see § Cost metric correction below)

| run | bd | verdict | Routing | Spec | Security | Evidence | Anti-puppet | bd | tokens | wall |
|---|---|---|---|---|---|---|---|---|---:|---|
| 4 | ftx | PASS | 5/5 card ✓ (overlap) | PASS | PASS | PASS | PASS | CLOSED | 717,757 | 12.0 min |
| 5 | t4n | PASS | 5/5 card ✓ (overlap) | PASS | PASS | PASS | PASS | CLOSED | 670,972 | 11.1 min |
| 6 | 0rf | PASS | 5/5 card ✓ (overlap) | PASS | PASS | PASS | PASS | CLOSED | 727,503 | 10.9 min |

**behavior**: 5/5 critical dimension PASS ใน 3/3 run → baseline ตั้งได้ · **cost** total_effective_tokens median **717,757** · p90 **727,503** · min 670,972

## 🔴 Cost metric correction (2026-09-08, bd:shode-roadmap/C-C2 R-1)

ตัวเลข tokens ในตารางข้างบนเป็นค่า **แก้แล้ว** (re-scored จาก transcript เดิม บนเครื่องเดิม, ไม่ได้รัน E2E ใหม่) —
ตัวเลขเดิมของ run-4/5/6 คือ 1,876,223 / 1,767,454 / 1,984,149 ซึ่ง **inflate ~2.6-2.7x**

**สาเหตุ**: `eval-scorer.py::cost_dimension` (เดิม) รวม `message.usage` ต่อ JSONL row แต่ Claude Code CLI 2.1.263
เขียน assistant message ที่มีหลาย content block เป็นหลาย row ที่แชร์ `message.usage`/`message.id` เดียวกัน — scorer
เดิมนับก้อนเดียวกันซ้ำสูงสุด 5 ครั้ง. Fix: dedupe ด้วย `message.id` (**last-wins**, scoped ต่อไฟล์ — main +
แต่ละ `subagents/*.jsonl` แยกกัน) ใน `scripts/eval-scorer.py::cost_dimension`.

ทำไมต้อง **last-wins** ไม่ใช่ first-wins: ใน main transcript ทุก duplicate row เหมือนกัน byte-ต่อ-byte (pick
order ไม่สำคัญ) แต่ใน **subagent transcript** `output_tokens` ไต่ขึ้นข้าม duplicate-id group จริง (streaming
usage snapshot — CLI เขียน snapshot ของ usage ระหว่างที่ content กำลัง stream ลง disk, row สุดท้ายของ
message.id นั้นถึงจะมี output_tokens ตัวจริง/สุดท้าย) — วัดได้ 50/64 message.id บน run-4 qa-engineer subagent
เดียว. First-wins จะนับ output ต่ำกว่าจริงเงียบ ๆ ทุก subagent. ตัวเลขที่ dedupe แบบ last-wins ได้ตรงกับตัวเลข
per-agent ใน `outputs/shode-roadmap/C/11-stan-token-audit.md` §1 เป๊ะทุกตัว (MAIN 74,358 + Quinn 172,520 +
Bella 80,942 + Sentinel 89,078 + Chris 162,187 + Felix 138,672 = 717,757).

ค่าเดิม (inflated) เก็บไว้ใน `score.json` ทุกไฟล์ ที่ `cost.cost_legacy_inflated` + `cost.cost_legacy_note` —
ไม่ลบทิ้ง เพื่อ trace ย้อนได้ว่าเปลี่ยนเพราะอะไร. รายละเอียดเต็ม: `outputs/shode-roadmap/C/12-dave-scorer-dedupe.md`

## Regression gate (release ถัดไปเทียบกับตารางนี้)
- behavior: ทุก run ต้อง PASS ทุก critical dimension (0 tolerance)
- cost: median ≤ 789,533 (+10%) · p90 ≤ 814,803 (+12%) — เกิน = ไม่ promote จนกว่าจะอธิบายได้
  (ค่าเก่า ±3%/±5% ตั้งบน gate metric ที่ผิด — **ทิ้ง ไม่ใช้อ้างอิงอีก**; เหตุผลค่าใหม่ + N=3 caveat →
  `outputs/shode-roadmap/C/12-dave-scorer-dedupe.md` §4)

## รอบก่อน baseline (เก็บเป็น evidence, ไม่นับ — ค่า token เดิม ไม่ได้ re-score เพราะไม่ใช่ baseline run)
- run-1 (ue3): 3/5 spawn, ไม่มี Bella/Sentinel → Routing+Security FAIL → นำไปสู่ B3 REVIEW DISPATCH CARD
- run-2 (769): 5/5 แต่ card ไม่ถึง runtime (plugin cache 3.14.0 ค้าง) · bd OPEN by design → golden แก้ให้รับ OPEN+verdict
- run-3 (igz): 4/5 ไม่มี Sentinel, card ยังไม่ถึง runtime → root cause = `plugin install` ไม่ refresh cache version เดิม

## known gap (ไม่ block baseline)
- ~~reviewer 5 ตัว spawn คนละ message (`parallel=False`)~~ → **resolved by this re-score** (scorer iter14, already
  landed before R-1): Agent tool ของ Claude Code launch async (`async_launched` คืนใน ~2 s) — 5 spawn ห่างกัน
  6–7 s แล้ววิ่งซ้อนกันจริง (execution window ทับซ้อน). scorer นิยาม `parallel` ใหม่จาก window overlap
  (`concurrency: overlap|sequential`); ค่า `parallel=True(overlap)` ในตารางบน + score.json ทุกไฟล์คือผลจาก
  re-score รอบนี้แล้ว (เดิมเขียนไว้ว่า `parallel=False` เพราะ score.json ตอนนั้นมาจาก scorer เวอร์ชันเก่า)
- Felix finding แปรผันข้าม run (run-3 เจอ I-1 isolation level ที่ run อื่นไม่เจอ) — reviewer variance, ยังไม่วัดเป็น dimension
- **🔴 durability gap** (ยังไม่แก้ — ให้ Oliver ตัดสิน): `score.json` ถูก commit แต่ raw transcript (`main.jsonl` +
  `subagents/*.jsonl`, ~2.5-2.8MB/run ดิบ, ~0.7MB/run gzip) อยู่นอก repo ที่ `~/.claude/projects/...` เท่านั้น —
  ไม่มีใครนอกเครื่องนี้ (รวม CI) re-score ย้อนหลังได้ถ้าต้อง dedupe fix รอบหน้า. ข้อเสนอ + trade-off →
  `outputs/shode-roadmap/C/12-dave-scorer-dedupe.md` §5
