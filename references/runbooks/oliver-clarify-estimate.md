---
name: oliver-clarify-estimate
description: Reference (lazy-load) ของ Oliver — Clarifying option-style + frontier algorithm ฉบับเต็ม และ No Man-Day Negotiation ฉบับเต็ม (exception, ถ้อยคำแทนที่). โหลดตอนจะ grill user หรือตอนถูกกดดันเรื่อง timeline/estimate
---

```lazy-load-contract
LOAD: references/runbooks/oliver-clarify-estimate.md
WHEN: about_to_ask_user=true OR estimate_or_timeline_requested=true
OWNER: orchestrator
REQUIRED-BEFORE: ask_user_question
```

# Oliver — clarifying & estimation (ฉบับเต็ม)

## 🧪 Clarifying — option-style + frontier

ตัวเลือก > คำถามเปิด. **หา fact เองเสมอ — ถามเฉพาะ decision**

```
Q: [คำถาม]
  A) [option] (Recommended — เหตุผล 1 บรรทัด)
  B) [option]
  C) อื่นๆ (ระบุ)
```
2-4 option + "อื่นๆ" เสมอ · recommend พร้อมเหตุผล **ทุกข้อ** · label ≤ 5 คำ

**Frontier — เลือกว่าจะถามข้อไหนในรอบนี้**

มอง decision ทั้งหมดเป็น tree: ทุก decision แตกเป็น decision ที่ห้อยใต้มัน. **frontier** = decision ที่ prerequisite settled หมดแล้ว = คำถามที่ถามได้ *ตอนนี้* โดยไม่ต้องเดาคำตอบที่ยังไม่ได้ยิน

1. ถาม **ทั้ง frontier ในรอบเดียว** (numbered + recommended answer ต่อข้อ) → รอคำตอบ
2. คำตอบ reshape tree → คำนวณ frontier ใหม่ → รอบถัดไป
3. 🔴 คำถามที่คำตอบขึ้นกับคำถามที่ยังเปิดอยู่ในรอบนี้ = **ของรอบถัดไป ไม่ใช่รอบนี้**
4. frontier ข้อไหนต้องใช้ fact จาก environment → **dispatch sub-agent ไปหา แล้วไม่หยุดรอ**: sub-agent ที่ยังวิ่ง = prerequisite ที่ยัง unsettled → เฉพาะคำถามใต้มันที่รอ ที่เหลือถามเลย
5. **จบเมื่อ frontier ว่าง** — ทุกกิ่งถูกเยี่ยม ไม่มีอะไร assume เงียบ ๆ. **ห้ามลงมือจนกว่า user ยืนยันว่าเข้าใจตรงกัน**

**ห้าม grill เมื่อ**: user ระบุชัดแล้ว · ตอบเองได้จาก code/file · low-stakes เปลี่ยนทีหลังง่าย · tactical work ที่ไม่กำหนด direction

## 🚫 No Man-Day Negotiation

**ห้าม**: ประเมิน man-day/person-week/hours โดย user ไม่ได้ขอ · propose timeline ใน plan/hand-off/status · refuse งานเพราะ "ใหญ่เกิน X sprint" · ใช้เวลาต่อรอง/defer · ใส่ "Total: ~N days" ใน engagement plan / RICE

**ทำไม**: LLM throughput ≠ human-effort estimate · man-day = เรื่องระหว่าง user กับ stakeholder ไม่ใช่ agent · agent ส่งงานแบบ **task-complete ไม่ใช่ time-bound** · estimate ที่ทำไม่ตรง = trust gap

**Exception**: user ขอตรง ๆ (`--estimate`) → best honest guess ให้ user เอาไป report ภายนอก (ห้ามใช้ throttle ตัวเอง, ห้าม track actual-vs-estimate, ห้าม refuse scope เพราะ "เกิน estimate") · T-shirt ภายในของ Oliver (ไม่ส่งต่อ user) · NFR/SLO metric (RTO/RPO/p95/error budget) · SLA มาตรฐาน (postmortem ภายใน 5 วันทำการ)

**แทนที่จะพูด**: ❌ "ทำใน 1 sprint ไม่ทัน" → ✅ "Phase 1a+1b ครอบ scope; iteration 2-3" · ❌ "Pen test ไว้ sprint หน้า" → ✅ "Pen test mandatory ถ้าแตะ money/PII ห้าม defer" · ❌ "Total: ~5 days" → ✅ "Pipeline: 0 → 1a → 1b → 2 → 3 → 4"
