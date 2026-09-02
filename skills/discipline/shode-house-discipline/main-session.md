---
name: main-session
description: Reference (lazy-load) ของ `shode-house-discipline` — กฎที่ใช้ได้เฉพาะ main session ที่คุยกับ user ตรง ๆ (Recite Card, clarifying option-style, no man-day negotiation). Subagent ไม่ต้องโหลด
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-discipline/main-session.md
WHEN: is_main_session=true AND user_facing_response=true
OWNER: orchestrator
REQUIRED-BEFORE: first_response
```

# Main-session policy

> 🔴 ใช้กับ **main session เท่านั้น** — subagent เกิดใน context ว่างและไม่มี first response กับ user
> subagent ที่โหลดไฟล์นี้ = เปลือง token เปล่า

## 🎯 Recite Discipline Card

Card ตัวจริงอยู่ที่ output-style `oliver.md` §1 — main session ผลิต first response จึง recite จากที่นั่น **verbatim ห้าม paraphrase**
Subagent ทำแทนด้วยการ **บังคับใช้ 5 Philosophy จริง ๆ** ไม่ใช่ recite ใส่ delegation return

## 🧪 Clarifying — option-style (🔴 ห้ามเดา → ห้ามทำ)

กำกวม → **ห้ามเดา ห้ามทำต่อ**. ตอบเองได้จาก code/file → อ่านเอง อย่าถาม

ต้องถาม user จริง:
- **option-style** 2-4 option + "อื่นๆ" · recommend ตัวแรกพร้อมเหตุผล
- **batch รอบเดียว** — ห้ามถามทีละข้อ
- ถามเฉพาะข้อที่ **คำตอบเปลี่ยนสิ่งที่จะทำ** (frontier rule) — ข้อที่ตอบยังไงก็ทำเหมือนเดิม = ไม่ต้องถาม
- Format เต็ม + frontier algorithm → `references/runbooks/oliver-clarify-estimate.md`

**AskUserQuestion relay** — subagent เรียก `AskUserQuestion` ไม่ได้ (main-session only). Subagent ต้อง return question bundle → main session เปิด popup แทน → ส่งคำตอบกลับ. เต็ม → `shode-house-workflow/smart-coop.md`
Agent ที่ไม่ใช่ Oliver/Bella/Patrick/Sara: กำกวม = ส่งกลับ Oliver ไม่ใช่ถาม user เอง (M7)

## 🚫 No Man-Day Negotiation (🔴)

**ห้ามประเมิน man-day / person-week / hours / timeline โดย user ไม่ได้ขอ** และห้ามใช้เวลาเป็นเหตุผลต่อรองหรือ defer scope
Agent ส่งงานแบบ **task-complete ไม่ใช่ time-bound**

- exception / T-shirt sizing / ถ้อยคำแทนที่ → `references/runbooks/oliver-clarify-estimate.md` · `agents/product-manager.md` § No Man-Day
- Metric ที่ **ไม่ใช่ estimate** และใช้ได้ปกติ: NFR/SLO (RTO/RPO/p95/error budget) · SLA มาตรฐาน
