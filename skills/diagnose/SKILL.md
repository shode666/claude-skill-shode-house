---
name: diagnose
description: |
  ใช้เมื่อ user รายงาน bug, error, performance issue, "พัง", "ไม่ทำงาน", "ช้า", "ทำไมถึง...", "debug", หรือต้อง root-cause analysis — structured methodology ที่บังคับ reproduce → isolate → fix → prevent ก่อน "ลอง fix ก่อน"
---

# Diagnose (structured debugging)

> Inspired by mattpocock/skills (engineering/diagnose) — adapted for shode-house

> **Owner**: Chris (review) + Quinn (test) + Dave (implement) — เปิด skill นี้เมื่อมี bug/perf

## หลักการ

**No fix without diagnosis** — ห้าม patch โดยไม่เข้าใจ root cause; "ลองเปลี่ยนดู" = anti-pattern

## 4 Steps

### 1. Reproduce (🔴 ห้ามข้าม)

- **Minimal repro** — input น้อยที่สุดที่ trigger bug
- ระบุ: environment, data, user action, expected vs actual
- ถ้า reproduce ไม่ได้ → **STOP** — ขอ stack trace / log / video / steps จาก user
- Flaky bug = treat as bug (ไม่ใช่ "บางครั้ง")

```
Bug: payment คำนวณผิด
Repro:
  - Env: staging
  - Input: amount=99.99, vat=7%, discount=10%
  - Expected: 96.34
  - Actual: 96.33
  - Steps: 1. login → 2. add cart → 3. apply coupon → 4. checkout
```

### 2. Isolate

- **Bisect** — หาจุดที่พัง (git bisect, binary search ใน flow)
- **Hypothesis** — เขียนสมมติฐาน 2-3 ข้อ + วิธีพิสูจน์
- **Eliminate** — ตัด layer ออกทีละชั้น (UI? API? business logic? DB? external?)
- **Add log/print** เฉพาะจุดสงสัย — ลบหลังเสร็จ
- **Diff** — code ก่อน-หลัง / config / data / version

### 3. Fix (เข้าใจก่อนแก้)

- **Root cause** ≠ symptom — ถ้าแก้แล้ว bug อื่นโผล่ = ไม่ใช่ root cause
- **Smallest change** ที่ fix ได้
- **Test ก่อน fix** — เขียน test ที่ fail (red) → fix → green
- **Comment "why"** ถ้า fix ไม่ obvious

### 4. Prevent

- **Regression test** — bug นี้ห้ามกลับมา
- **Update doc** ถ้า docs ทำให้เข้าใจผิด
- **Postmortem** ถ้า production incident (timeline + root cause + action item)
- **Spread learning** — pattern นี้อาจมีจุดอื่น → grep + fix หมด

## Hand-off pattern

```
Diagnose finished →
  - Chris: review fix + write regression unit test
  - Quinn: integration test เผื่อ pattern อื่น
  - Aaron: monitoring/alert ถ้าเป็น infra
  - Domain Expert: ถ้า business rule ผิด
```

## ห้าม

- ห้าม fix โดยไม่ reproduce
- ห้าม "ลองเปลี่ยน" โดยไม่มี hypothesis
- ห้าม ship fix โดยไม่มี regression test
- ห้าม blame engineer (postmortem blameless)
- ห้าม revert โดยไม่เข้าใจว่า revert ทำอะไร
