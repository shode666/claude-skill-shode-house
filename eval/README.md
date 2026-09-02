# Eval harness — v3.13 release gate

## สถานะ
- ✅ **scenarios.json** — 12 benchmark scenario + target reduction ต่อตัว (รัน 5 รอบ รายงาน median + p90)
- ✅ **usage-record.schema.json** — schema ของ record ต่อ agent invocation (5 token type + tool metric)
- ✅ **static baseline** — `.baseline-3.12.1.json` (วัดจาก tag v3.12.1)
- ⛔ **runtime baseline ยังไม่ได้รัน** — ต้องใช้ Claude Code จริงรัน 12 scenario × 5 รอบ บน tag `v3.12.1`
  แล้วเขียนผลลง `eval/baseline/3.12.1/<scenario>/<agent>.json` ตาม schema

## ทำไม runtime baseline ถึงเป็น blocker ของ Phase B
ถ้าไม่มี behavioral + usage baseline ก่อนย้าย topology จะแยกไม่ออกว่า accuracy/token ที่เปลี่ยน
มาจากการ refactor หรือ noise ของการรันแต่ละครั้ง — v3.13 ทั้ง release วัดผลไม่ได้

## วิธีรัน (manual จนกว่าจะมี runner)
1. `git checkout v3.12.1`
2. รันแต่ละ scenario ด้วย fixture/model/reasoning setting เดิม 5 รอบ
3. เก็บ usage จาก runtime (input/cache_read/cache_write/output + duration) ลงตาม schema
4. `outputs/token-usage/<run-id>/summary.json` = aggregate ต่อ run
5. ทำซ้ำบน branch ของ 3.13 แล้วเทียบ median/p90 ต่อ scenario
