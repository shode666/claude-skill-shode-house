---
name: spec-axis
description: Reference (lazy-load) ของ `review-checklist` — แกน Spec: เทียบ diff กับ spec. โหลดโดย reviewer ที่รับแกนนี้ (Bella) เท่านั้น
---

```lazy-load-contract
LOAD: skills/discipline/review-checklist/spec-axis.md
WHEN: review_axis=spec
OWNER: business-analyst
REQUIRED-BEFORE: spec_axis_verdict
```

# Spec Axis — reference

> แยกจาก `SKILL.md` v3.12.1: Chris/Quinn/Sentinel preload `review-checklist` แต่ **ไม่ได้ทำแกนนี้** จึงแบกไว้เปล่า ๆ ×3

> Chris 7-dim + Quinn 6-axis เป็น **standards ล้วน** — ตอบแค่ "code เขียนถูกหลักไหม" ไม่มีใครตอบ **"code ทำในสิ่งที่ spec ขอหรือเปล่า"**. code ที่ตามมาตรฐานครบแต่ทำผิดเรื่อง = **Standards PASS / Spec FAIL**; รายงานรวมกันเมื่อไหร่ แกนหนึ่งบังอีกแกน — นี่คือช่องที่ Anti-Puppet Gate เดิมเจาะไม่ถึง

**รายงาน 3 อย่าง — quote บรรทัดของ spec ทุก finding**
- **(a) ขาด/ทำครึ่งเดียว** — AC บอก retry 3 ครั้ง โค้ด retry ครั้งเดียว
- **(b) scope creep** — behaviour ใน diff ที่ spec ไม่ได้ขอ (เช่นแอบใส่ caching layer) → Philosophy #4 SCOPE DRIFT
- **(c) ดูเหมือนทำแล้วแต่ผิด** — คำนวณ VAT ก่อนหักส่วนลด ทั้งที่ spec บอกหลัง

**กฎการรัน (🔴)**
1. Spec axis กับ Standards axis (Chris) **รันเป็น sub-agent คนละตัว** — ไม่ให้ context ปนกัน (per Handoff Contract: ส่ง path ของ diff + spec ไม่ส่งเนื้อหา)
2. รายงานแยกหัวข้อ `## Standards` และ `## Spec` — **ห้าม merge หรือ rerank ข้ามแกน** เพราะการแยกแกนมีไว้กันการบังกันเอง
3. ปิดท้าย 1 บรรทัด: จำนวน finding ต่อแกน + ตัวแย่สุด **ในแต่ละแกน** — ห้ามเลือกผู้ชนะข้ามแกน
4. ไม่มี spec → ข้าม Spec axis แล้วเขียน **"no spec available"** ใน report (ไม่ใช่ pass เงียบ ๆ)

**Routing**: finding ของ Spec axis ส่วนใหญ่ route → **Phase 1a** (Bella ∥ Sara revise spec/AC) ไม่ใช่ Phase 2 — ยกเว้นข้อ (c) ที่ spec ถูกแต่ code ผิด → Phase 2

---
