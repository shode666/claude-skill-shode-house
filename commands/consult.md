---
description: ปรึกษาด่วน — route ไปหา agent ที่เหมาะที่สุด (ไม่รัน pipeline เต็ม)
allowed-tools: Task, Read, Grep, Glob
argument-hint: [question or topic]
---

คำถาม: **$ARGUMENTS**

## Routing

ส่งไป agent **ตัวเดียว** ที่เหมาะ:

| ลักษณะคำถาม | Agent |
|------------|-------|
| Architecture, tech stack, ADR, threat model | Sara |
| Requirement, user story, BRD, Event Storming | Bella |
| Payment, ledger, banking, KYC/AML | Felix |
| GL, AR/AP, inventory, MRP, payroll | Elena |
| Trading, OMS, matching, FIX | Tara |
| Insurance, policy, claim, actuarial | Iris |
| Booking, reservation, yield | Brooke |
| E-commerce, cart, promo, marketplace | Emma |
| Code quality, SOLID, unit test | Chris |
| Integration/E2E/pen test | Quinn |
| Docker, CI/CD, deploy, obs | Aaron |
| 2+ agents / ไม่ชัด | Oliver |

## Process

1. วิเคราะห์ intent
2. บอก user → agent ไหน + เหตุผลสั้น
3. เรียก agent (Task tool)
4. Present คำตอบ

## ⚠️ Rules

- 1 agent ถ้าคำถามเดียวตอบได้
- Design ใหญ่ → แนะนำ `/design-system`
- Review ไฟล์ → แนะนำ `/review`
- ภาษาไทย
