---
name: loop-ladder
description: Reference (lazy-load) ของ `diagnose` — 10 วิธีสร้าง feedback loop เรียงตามลำดับ. โหลดเมื่อวิธี 1-3 ใน SKILL.md ไม่สำเร็จ หรือ loop ยังช้า/flaky/ไม่ deterministic
---

```lazy-load-contract
LOAD: skills/workflow/diagnose/loop-ladder.md
WHEN: feedback_loop_method_1_3_failed=true OR loop_slow_flaky_or_nondeterministic=true
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

## ลับ loop / bug ที่ไม่ deterministic

**ลับ loop ให้คม** (treat the loop as a product) — ได้ loop แล้วยังไม่พอ:
- เร็วขึ้นได้ไหม (cache setup, ข้าม init ที่ไม่เกี่ยว, แคบ scope ของ test)
- signal คมขึ้นได้ไหม (assert **อาการที่ user บอก** ไม่ใช่ "ไม่ crash")
- deterministic ขึ้นได้ไหม (pin เวลา, seed RNG, isolate filesystem, freeze network)
> loop 30 วินาทีที่ flaky แทบไม่ต่างจากไม่มี loop; loop 2 วินาทีที่ deterministic = superpower

**Bug ที่ไม่ deterministic**: เป้าหมายไม่ใช่ repro สะอาด แต่คือ **ดัน reproduction rate ให้สูงพอจะ debug** — ยิง trigger 100× · parallelise · stress · แคบ timing window · แทรก sleep. flake 50% debug ได้, 1% ไม่ได้
