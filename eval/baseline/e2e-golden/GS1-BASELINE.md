# GS1-reference-refund — E2E baseline (N=3)

**plugin** shode-house 3.14.0-dev @ `6f0b16d`+ (REVIEW DISPATCH CARD) · **runner** Claude Code CLI 2.1.263, `claude -p … --dangerously-skip-permissions`, unattended · **fixture** shode666/shode-house-example-refund @ `69c3c8c` · **date** 2026-09-08

| run | bd | verdict | Routing | Spec | Security | Evidence | Anti-puppet | bd | tokens | wall |
|---|---|---|---|---|---|---|---|---|---:|---|
| 4 | ftx | PASS | 5/5 card ✓ (seq) | PASS | PASS | PASS | PASS | CLOSED | 1,876,223 | 12.0 min |
| 5 | t4n | PASS | 5/5 card ✓ (seq) | PASS | PASS | PASS | PASS | CLOSED | 1,767,454 | 11.1 min |
| 6 | 0rf | PASS | 5/5 card ✓ (seq) | PASS | PASS | PASS | PASS | CLOSED | 1,984,149 | 10.9 min |

**behavior**: 5/5 critical dimension PASS ใน 3/3 run → baseline ตั้งได้ · **cost** total_effective_tokens median **1,876,223** · p90 **1,984,149** · min 1,767,454

## Regression gate (release ถัดไปเทียบกับตารางนี้)
- behavior: ทุก run ต้อง PASS ทุก critical dimension (0 tolerance)
- cost: median ≤ 1,932,510 (+3%) · p90 ≤ 2,083,356 (+5%) — เกิน = ไม่ promote จนกว่าจะอธิบายได้

## รอบก่อน baseline (เก็บเป็น evidence, ไม่นับ)
- run-1 (ue3): 3/5 spawn, ไม่มี Bella/Sentinel → Routing+Security FAIL → นำไปสู่ B3 REVIEW DISPATCH CARD
- run-2 (769): 5/5 แต่ card ไม่ถึง runtime (plugin cache 3.14.0 ค้าง) · bd OPEN by design → golden แก้ให้รับ OPEN+verdict
- run-3 (igz): 4/5 ไม่มี Sentinel, card ยังไม่ถึง runtime → root cause = `plugin install` ไม่ refresh cache version เดิม

## known gap (ไม่ block baseline)
- ~~reviewer 5 ตัว spawn คนละ message (`parallel=False`)~~ → **false alarm** (2026-09-08, scorer iter14): Agent tool ของ Claude Code launch async (`async_launched` คืนใน ~2 s) — 5 spawn ห่างกัน 6–7 s แล้ววิ่งซ้อนกันจริง (execution window ทับซ้อน). scorer นิยาม `parallel` ใหม่จาก window overlap (`concurrency: overlap|sequential`); card เปลี่ยนถ้อยคำจาก "ONE message" เป็น "ติดกันก่อนรอผลตัวใด". ค่า `parallel=False` ใน run-4..6 score.json เป็นของ scorer เวอร์ชันเก่า — re-score ได้เมื่อ transcript ยังอยู่
- Felix finding แปรผันข้าม run (run-3 เจอ I-1 isolation level ที่ run อื่นไม่เจอ) — reviewer variance, ยังไม่วัดเป็น dimension
