---
name: source-validation
description: Reference (lazy-load) ของ `domain-core` — ตัวอย่าง citation ที่ผ่าน/ไม่ผ่าน + วิธีตรวจว่า source เป็น primary จริง + stale-knowledge handling. โหลดเมื่อกำลังจะ cite regulation/standard จริง
---

```lazy-load-contract
LOAD: skills/discipline/domain-core/source-validation.md
WHEN: domain_claim_about in {regulation,standard,protocol,tax_rule}
OWNER: fintech-expert
REQUIRED-BEFORE: domain_claim_stated
```

# Source validation

## ✅ ผ่าน

```
"PCI-DSS v4.0 Req 3.5.1 (effective Mar 2024) — PAN ต้องอ่านไม่ได้เมื่อเก็บ;
 มาตรฐานรับหลายวิธี (truncation / tokenization / hashing / strong cryptography)
 ไม่ได้บังคับ encryption อย่างเดียว"
```
🔴 ตัวอย่างนี้สอน **รูปแบบการ cite** เท่านั้น — ห้าม reuse ข้อความเป็น requirement จริง
(v3.12: ถ้อยคำเดิม "store PAN encrypted at rest" แคบกว่ามาตรฐานจริง — นี่คือเหตุผลที่ต้องเปิด clause เอง)

## ❌ ไม่ผ่าน

- "ตาม PCI-DSS ต้อง encrypt PAN" — ไม่มี version ไม่มี clause
- "BOT requirement บอกว่า…" — ไม่มีเลขหนังสือเวียน
- "IFRS 17 ใช้ measurement model นี้" — ไม่มี paragraph
- "ปกติ regulator จะ…" — ปกติ ≠ clause

## Primary หรือไม่ — เช็ค 4 ข้อ

1. **ผู้ออกคือเจ้าของกฎเอง** (regulator / standard body) ไม่ใช่ blog, vendor whitepaper, consultant summary
2. **มี version + วันที่บังคับใช้** และตรงกับ scope ของ project (ประเทศ / ปีบัญชี / card scheme)
3. **อ้างถึงระดับ clause/paragraph ได้** ไม่ใช่ระดับ "มาตรฐานบอกว่า"
4. **ยังไม่ถูก supersede** — ตรวจว่ามี amendment/errata ใหม่กว่าไหม

ผ่านไม่ครบ 4 ข้อ = ยังเป็น **general guidance** ต้อง mark ตาม `domain-core` § citation contract

## Stale knowledge

Regulation เปลี่ยนบ่อยกว่า training cutoff — claim ที่เกี่ยวกับ **rate, threshold, deadline, effective date** ให้ถือว่า stale เสมอจนกว่าจะเปิด source ปีปัจจุบัน
หา primary source ไม่ได้ในเวลาที่มี → เขียนเป็น **OPEN QUESTION พร้อมชื่อคนที่ต้องยืนยัน** ไม่ใช่เดาแล้วส่งต่อ
