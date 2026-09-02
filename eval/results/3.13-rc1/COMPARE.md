# A/B — v3.12.1 vs v3.13.0 (Cowork, pass 1)

metric = **ctx0** = `cache_write + cache_read` ของ **turn แรก** ของ subagent
= context ตั้งต้นจริง (system + tool list + agent body + preload skills)

ทำไมใช้ตัวนี้: `cache_write` รวมทั้ง run แปรตามจำนวน turn (Sara ฝั่ง B ใช้ 11 turn เทียบกับ
5 turn ฝั่ง A ทำให้ยอดรวมดู "เพิ่ม" ทั้งที่ context ตั้งต้นลดลง) ส่วน ctx0 นิ่งมาก --
วัด agent เดียวกันสองครั้งในฝั่ง A ต่างกัน < 0.1% (เช่น Uma 30,970 vs 30,986)

| agent | A (3.12.1) | B (3.13.0) | delta | % |
|---|---:|---:|---:|---:|
| security-engineer | 29,534 | 26,516 | -3,018 | -10.2% |
| qa-engineer | 35,346 | 32,334 | -3,012 | -8.5% |
| code-reviewer | 33,602 | 30,616 | -2,986 | -8.9% |
| solution-architect | 30,418 | 27,588 | -2,830 | -9.3% |
| ux-ui-designer | 30,986 | 28,234 | -2,752 | -8.9% |
| business-analyst | 29,892 | 27,178 | -2,714 | -9.1% |
| developer | 33,490 | 30,809 | -2,681 | -8.0% |
| orchestrator | 39,551 | 37,172 | -2,379 | -6.0% |
| fintech-expert | 25,806 | 24,539 | -1,267 | -4.9% |
| **รวม 9 agent** | **288,625** | **264,986** | **-23,639** | **-8.2%** |

**ลดลงทุก agent ไม่มีข้อยกเว้น** เฉลี่ย -8.2%

หนักสุดที่ Oliver (39,551 -> 37,172) เพราะ body ถูกแตกไป runbook; เบาสุดที่ Felix
(-4.9%) เพราะ domain-core ที่เพิ่มเข้า preload ไปหักล้างส่วนที่ถอดออกจาก body บางส่วน

## เทียบกับ static prediction

static byte (`scripts/context-budget.py`) บอกว่า agent+preload ลด 16-30% แต่ ctx0 จริง
ลดแค่ 5-9% -- ต่างกันเพราะ **ctx0 รวม harness ของ Cowork** (system prompt + tool list ทั้งชุด)
ซึ่งไม่เปลี่ยนระหว่าง A/B ส่วนของ shode-house จึงเป็นเศษเสี้ยวของก้อนนั้น
=> byte ที่ประหยัดได้จริงตรงกับที่ static วัด แต่ **สัดส่วนต่อ context ทั้งหมดเล็กกว่าที่แผนคาดไว้**

## Promotion criteria (WS8)

- [x] critical invariant pass 100% -- ดู BEHAVIOR.md
- [x] general accuracy ไม่ลด (ดีขึ้นด้วยซ้ำ 2 จุด)
- [ ] input context ลดตาม target ต่อ scenario -- **ไม่ผ่านตามตัวเลขที่ตั้งไว้**
      target เดิม 10-25% ต่อ scenario วัดจาก byte ของ plugin; ctx0 จริงลด 5-9%
      target ถูกตั้งบนสมมติฐานว่า plugin คือทั้ง context ซึ่งไม่จริงใน Cowork
- [x] ไม่มี fixture ที่ผ่านเพราะ skip action
