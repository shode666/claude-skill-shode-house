---
name: reporting
description: Reference (lazy-load) ของ `shode-house-discipline` — ตัวอย่าง report เต็ม, สิ่งที่ห้าม/ห้ามตัดในรายงาน, risk template, ตัวอย่าง tag prefix. โหลดเมื่อกำลังจะเขียนรายงานยาวหรือไม่แน่ใจว่าอะไรตัดได้
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-discipline/reporting.md
WHEN: report_length_exceeds_return_format=true OR risk_statement_required=true
OWNER: orchestrator
REQUIRED-BEFORE: report_to_user
```

# Report & risk conventions

## ✍️ Work deep, report short

**ทำละเอียด ≠ พูดเยอะ.** ความละเอียดอยู่ใน artifact file + tool output ที่ paste ไม่ใช่ในคำบรรยาย

| ต้องยาว (ไม่จำกัด) | ต้องสั้น (บังคับ) |
|---|---|
| artifact file ที่เขียนลง `outputs/` | ข้อความที่ส่งกลับ orchestrator/user |
| tool output ที่ paste เป็นหลักฐาน | คำอธิบายสิ่งที่กำลังจะทำ |
| code + test ที่เขียนจริง | สรุปสิ่งที่เพิ่งทำเสร็จ |

**ห้าม**: preamble ("ผมจะเริ่มด้วย…") · narrate ทุก tool call · เล่าซ้ำสิ่งที่อยู่ใน artifact แล้ว · restate คำถาม user · สรุปปิดท้ายที่ไม่มีข้อมูลใหม่
**ตัดคำบรรยายได้ ห้ามตัด**: evidence · security finding · ตัวเลข · dissent · สิ่งที่ทำไม่สำเร็จ
เกินไปอีกขั้น (long loop / broadcast) → โหลด `caveman` skill

## 🏷️ Tag prefix — ตัวอย่าง

```
[Dave|state:phase-2|bd:42]
[Uma|state:adhoc|bd:none]
Dave ▸ Chris : payment service implement เสร็จ พร้อม review (bd:42)
```
ไม่มี bd → `bd:none` · ไม่มี phase → `state:adhoc`

## ⚠️ Risk Template

```
Risk: [what] | Likelihood: L/M/H | Impact: L/M/H | Mitigation: [concrete] | Owner: [agent]
```
ใช้ทุกครั้งที่เสนอ R0/R1 action, dissent, หรือ trade-off ที่ user ต้องตัดสินใจ
