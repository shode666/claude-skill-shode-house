---
name: loop-ladder
description: Reference (lazy-load) ของ `diagnose` — 10 วิธีสร้าง feedback loop เรียงตามลำดับ. โหลดเมื่อวิธี 1-3 ใน SKILL.md ไม่สำเร็จ
---

```lazy-load-contract
LOAD: skills/workflow/diagnose/loop-ladder.md
WHEN: feedback_loop_method_1_3_failed=true
OWNER: developer
REQUIRED-BEFORE: hypothesis_step
```

# Feedback loop ladder — 10 วิธี

> แยกจาก `SKILL.md` v3.12.1 — เป็น reference material ไม่ใช่ invariant ที่ต้องอ่านทุก diagnosis

**วิธีสร้าง เรียงตามลำดับที่ควรลอง**
1. **Failing test** ที่ seam ซึ่งเข้าถึง bug (unit / integration / e2e)
2. **curl / HTTP script** ยิงใส่ dev server
3. **CLI + fixture input** diff stdout กับ snapshot ที่รู้ว่าถูก
4. **Headless browser script** (Playwright) ขับ UI + assert DOM/console/network
5. **Replay captured trace** — เซฟ request/payload/event log จริงลงดิสก์ แล้ว replay ผ่าน code path นั้นแบบโดด ๆ
6. **Throwaway harness** — ยกระบบส่วนน้อยที่สุด (1 service + mock dep) ให้เรียก code path ของ bug ด้วย function เดียว
7. **Property / fuzz loop** — bug แบบ "บางทีก็ผิด" → ยิง 1000 input สุ่มแล้วดู failure mode
8. **Bisect harness** — bug โผล่ระหว่าง 2 สถานะที่รู้ (commit/dataset/version) → automate "boot ที่สถานะ X, เช็ค, ทำซ้ำ" ให้ `git bisect run` ได้
9. **Differential loop** — input เดียวกันผ่าน version เก่า vs ใหม่ (หรือ 2 config) แล้ว diff output
10. **HITL script** — ทางเลือกสุดท้าย ถ้าจำเป็นต้องให้คนคลิก ให้เขียน script ขับ *คน* เพื่อให้ loop ยังมีโครงสร้าง
