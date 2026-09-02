# RUNBOOK — runtime baseline + A/B (WS8 / WS10)

สิ่งเดียวที่ปลดล็อก promotion ของ v3.13 · ต้องรันบนเครื่องที่ใช้ Claude Code จริง
(sandbox ของ session ทำแทนไม่ได้ — ไม่มี runtime, ไม่มี ~/.claude)

## เตรียม 1 ครั้ง

```bash
# project ทดสอบที่จะใช้ทุกรอบ (ต้องเป็นตัวเดิมตลอด A/B ไม่งั้นเทียบไม่ได้)
cd <test-project>
claude plugin install shode-house@<path หรือ marketplace>
```

fix ให้เหมือนกันทุกรอบ: **model เดียว · reasoning setting เดียว · project เดียว · session ใหม่ทุกรอบ**

## A — baseline บน v3.12.1  (11 scenario × 5 รอบ = 55 run)

`full-fanout` ไม่ต้องรัน — ใช้ `scripts/context-budget.py` เป็นตัวแทน (synthetic)

```bash
git checkout v3.12.1 && claude plugin install .      # ให้ CLI ใช้ 3.12.1
```

ต่อ 1 run:

```bash
# 1. เปิด session ใหม่ วาง prompt จาก eval/prompts/<scenario>.md แบบ verbatim
# 2. รันจนจบ แล้วติ๊ก behavior assertion ในไฟล์นั้น (accuracy มาก่อน token)
# 3. เก็บ usage
scripts/usage-from-transcript.py --list        # หา transcript ล่าสุด
scripts/usage-from-transcript.py <transcript.jsonl> \
    --scenario <scenario-id> --run-dir eval/baseline/3.12.1 \
    --plugin-version 3.12.1 --model <model-id> --command <command>
```

🔴 **รอบแรกให้เปิด record ที่ได้ดูด้วยตา** แล้วเทียบกับ `/cost` ของ session นั้น
ถ้าเลขไม่ตรง = schema ของ transcript เปลี่ยน ต้องแก้ `usage-from-transcript.py` ก่อนเก็บที่เหลือ

```bash
scripts/usage-report.py eval/baseline/3.12.1      # สรุป + จับ repeated load
```

## B — candidate บน 3.13

```bash
git checkout feat/v3.13-ws7-ws9-ws10 && claude plugin install .
# รัน 11 scenario × 5 รอบ ด้วย prompt ชุดเดิม --run-dir outputs/token-usage/3.13-rc1
scripts/usage-report.py --compare eval/baseline/3.12.1 outputs/token-usage/3.13-rc1
```

## Promotion criteria (WS8 — ห้ามผ่อน)

- [ ] critical invariant pass **100%** — safety R0/R1/R2 · evidence/no-magic · handoff completeness
      · scope drift · spec axis · domain citation · UX evidence · AskUserQuestion relay · close-on-done
      · lazy-load omission
- [ ] general accuracy ลดไม่เกิน **2%** (นับจาก behavior assertion ที่ติ๊กไว้)
- [ ] input context ลดตาม `target_total_token_reduction` ของแต่ละ scenario
- [ ] **ไม่มี fixture ที่ผ่านเพราะ skip action** — ผ่านเพราะไม่ได้ทำ ไม่นับผ่าน
- [ ] regression gate ของ `usage-report.py --compare`: median +3% / p90 +5% ไม่เกิน

ข้อไหน fail = ไม่ promote · แก้แล้วรันซ้ำทั้งชุด ไม่ใช่เฉพาะ scenario ที่ fail

## ต้นทุนคร่าว ๆ

55 run สำหรับ A + 55 run สำหรับ B · scenario ที่ fan-out (implement-*, phase3b-*) กิน token มากสุด
ทำทีละกลุ่มได้ แต่ **ห้ามสลับ model/project กลางทาง**
