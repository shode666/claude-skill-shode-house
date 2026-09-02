# Baseline A — v3.12.1 (Cowork, pass 1: 1 run/scenario)

harness: Cowork subagent ผ่าน Agent tool · model claude-opus-5 · fixture `~/workspace/shode-eval`
วัดจาก transcript `~/.claude/projects/<session>/subagents/agent-*.jsonl` ของ cloud container

## Context ต่อ agent (cache_write = ขนาด context ที่ถูกสร้างใหม่ = ตัวที่ WS2-6 ไปแตะ)

| scenario | agent | turns | cache_write | cache_read |
|---|---|---:|---:|---:|
| consult-single | solution-architect | 5 | 100,598 | 60,836 |
| design-system-backend | business-analyst | 17 | 109,458 | 446,750 |
| design-system-backend | solution-architect | 11 | 135,650 | 217,114 |
| design-system-fe-domain | ux-ui-designer | 6 | 60,700 | 129,757 |
| design-system-fe-domain | fintech-expert | 16 | 80,187 | 405,417 |
| implement-backend | developer | 51 | 103,003 | 2,250,725 |
| implement-ui | ux-ui-designer | 10 | 135,135 | 197,107 |
| phase3b-base | code-reviewer | 16 | 63,831 | 533,928 |
| phase3b-base | qa-engineer | 15 | 36,667 | 533,719 |
| phase3b-base | business-analyst | 22 | 89,449 | 761,218 |
| phase3b-sensitive | security-engineer | 14 | 139,579 | 350,799 |
| phase3b-sensitive | fintech-expert | 14 | 96,398 | 307,448 |
| diagnose-fast | developer | 12 | 86,605 | 400,099 |
| diagnose-full | qa-engineer | 10 | 64,722 | 315,400 |
| map-mode | orchestrator | 13 | 100,935 | 482,181 |
| resume-run | orchestrator | 12 | 87,892 | 416,572 |

รวม 16 record · cache_write 1,490,809 · cache_read 7,809,070

## 🔴 ข้อจำกัดของตัวเลขชุดนี้ (ต้องอ่านก่อนใช้)

1. **`output_tokens` ใช้ไม่ได้** — รวมได้ 52-8,828 tok ทั้งที่ agent เขียนรายงานยาวหลายพันคำ
   transcript บันทึก usage ไม่ครบทุก turn → ใช้เฉพาะ cache_write / cache_read
2. **cache_write รวม harness ของ Cowork** (system prompt + tool list ทั้งชุด) ซึ่งใหญ่กว่าส่วนของ
   plugin มาก — ค่าสัมบูรณ์จึงไม่ใช่ "ขนาดของ shode-house" แต่ **ผลต่าง A vs B ยังใช้ได้**
   เพราะ harness เท่ากันทั้งสองฝั่ง
3. **1 run/scenario ไม่ใช่ 5** — ยังไม่มี median/p90 ตัวเลขนี้มี noise
4. **main session วัดไม่ได้** — orchestration overhead ของ Oliver ไม่อยู่ในนี้
5. Agent tool รายงาน `subagent_tokens` คนละค่ากับผลรวม transcript (เช่น Sara 37,129 vs 101,153)
   ยังไม่รู้ว่าอันไหนคือ billing จริง — ต้องเลือกให้ตรงกันทั้ง A และ B

## Behavior assertion — ผลรวม

**ผ่านทั้งหมด 11/11 scenario** สิ่งที่พิสูจน์ได้จริง:

- **NO MAGIC** — 5 agent (Sara, Dave, Quinn×2, Felix) ปฏิเสธที่จะ claim เรื่อง code ที่ไม่มีจริง
  แล้วขอหลักฐานก่อน แทนที่จะเดา (`/search`, payment webhook, Postgres ที่อ้างว่า "มีอยู่")
- **frontier clarifying** — Bella/Sara/Oliver/Felix ถามเป็น option-style รอบเดียว recommend ทุกข้อ
  และประกาศชัดว่าคำถามที่ขึ้นกับคำตอบรอบนี้เป็นของรอบถัดไป
- **M1 ingress guard** — Uma/Felix/Sentinel/Oliver ตรวจ bd ก่อนตอบ ไม่มี bd → STOP + route Oliver
- **pre-implement-ui gate** — Uma FAIL 7/9 ข้อ (ไม่มี MASTER.md/tokens/contrast/baseline) → BLOCKED
  ไม่ใช่ PASS และไม่ยอมเริ่ม implement
- **แกน Standards vs Spec แยกจริง** — Bella รายงาน "no spec available" ไม่ pass เงียบ
  และไม่แตะ code quality เลย
- **domain + security เข้าเมื่อแตะ money/PII** — Sentinel + Felix เจอ **full PAN ลง log**
  (`print(f"ledger post card={card}")`) ที่ fixture ฝังไว้ **ทั้งคู่**
- **เจอ bug ที่ผู้เขียน fixture ไม่ได้ตั้งใจฝัง** — `mask_card()` fail-open เมื่อ PAN < 10 หลัก
  (`"*" * negative` = `""` → คืนเลขเกือบเต็มโดยไม่มี mask) Quinn/Sentinel/Felix เจอครบ 3 คน
- **AI persona disclaimer + citation contract** — Felix ขึ้น disclaimer ทุกครั้ง และเมื่อ cite
  PCI-DSS clause ไม่ได้ ก็ mark เป็น "general guidance, not source-verified" ตรงตามกฎ แทนที่จะเดาเลขข้อ
- **Anti-Puppet** — Dave paste ผล pytest/ruff/mypy/curl จริงทั้ง 5 AC; Sentinel paste output
  ของ reproduce เอง; ไม่มีใคร claim PASS ลอย ๆ

## Fixture defect ที่เจอระหว่างรัน (ต้องแก้ก่อนฝั่ง B)

`phase3b-base` prompt ใช้ sha ของ commit notification เอง → `git diff <sha>..HEAD` ได้แต่ ledger
Quinn จับได้และรายงาน scope mismatch (ถูกต้อง) แต่ทำให้ scenario วัดไม่ตรงเจตนา
→ ต้องใช้ sha ของ baseline commit แทน
