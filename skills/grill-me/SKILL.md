---
name: grill-me
description: |
  ใช้เมื่อ user สั่ง "grill me", "ถามให้ครบ", "clarify", "อย่ารีบ implement", "ขุด requirement", "ขอตอบเป็นตัวเลือก", หรือเริ่ม task ใหม่ที่ requirement กำกวม — บังคับ option-style A/B/C/D ตาม shode-house discipline ก่อนเริ่มทำ
---

# Grill Me (option-style clarifying)

> Inspired by mattpocock/skills (productivity/grill-me) — adapted for shode-house

## หลักการ

**ห้ามเดา → ห้ามทำ** ก่อน confirm ทุก ambiguity
- คำถามเปิด = bad UX (user ต้องคิดเอง)
- ตัวเลือก = good UX (เลือกง่าย, batch ได้)

## รูปแบบ (🔴 บังคับ)

```
Q1: [คำถาม]
  A) [option 1] (Recommended — เหตุผลสั้น)
  B) [option 2]
  C) [option 3]
  D) อื่นๆ (ระบุ)

Q2: [คำถามถัดไป]
  ...
```

กติกา:
- 2-4 options + "อื่นๆ" เสมอ
- Recommend ตัวแรก + ใส่ "(Recommended)" + เหตุผล 1 บรรทัด
- Label ≤ 5 คำ + คำอธิบาย 1 บรรทัด
- Batch 3-7 คำถามครั้งเดียว → ลด round-trip
- User ตอบ A/1 → accept

## เมื่อไหร่ Grill

- Requirement กำกวม ("อยากได้ระบบ XX")
- Decision tree branching (architecture/tech/process)
- Ambiguous bug report ("มันพัง")
- New project bootstrap (stack/scope/scale)
- ข้อสงสัยที่ทำต่อไม่ได้ถ้าไม่รู้

## เมื่อไหร่ ไม่ Grill

- User ระบุชัดอยู่แล้ว
- คำถามที่ตอบเองได้จาก context (อ่าน file/code ดูได้)
- Low-stakes (ทำผิดเปลี่ยนได้ง่าย)
- Tactical work ที่ไม่กำหนด direction

## Grill Patterns

### Stack Decision
```
Q: Backend framework?
  A) FastAPI (Recommended — type hint + async + OpenAPI)
  B) Django (batteries included, ORM ดี)
  C) NestJS (TypeScript)
  D) Spring Boot (JVM)
```

### Scope Decision
```
Q: รวม authentication?
  A) ใช่ (built-in)
  B) ไม่ — assume มี SSO อยู่แล้ว
  C) optional (config flag)
```

### Severity / Priority
```
Q: Severity?
  A) 🔴 Critical (block prod / security / money)
  B) 🟠 High (visible bug, data loss risk)
  C) 🟡 Medium (workaround มี)
  D) 🔵 Low (UX nitpick)
```

## Hand-off

Bella/Sara/Sam/Uma/Felix... ทุก agent ที่ถาม clarifying ใช้ pattern นี้ — Oliver ตรวจ

## ห้าม

- ห้ามถามคำถามเปิดถ้ามี discrete options
- ห้ามถามทีละข้อถ้า batch ได้
- ห้ามไม่มี Recommended (user ต้องเดาเอง = grill ที่แย่กว่าไม่ grill)
- ห้ามถาม > 7 ข้อรอบเดียว (overwhelming)
- ห้าม proceed ถ้า user "skip" คำถามสำคัญ → ถามใหม่ + อธิบายว่าทำไมต้องตอบ
