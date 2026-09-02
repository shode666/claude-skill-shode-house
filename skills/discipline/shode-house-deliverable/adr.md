---
name: adr
description: Reference (lazy-load) ของ `shode-house-deliverable` — ADR lifecycle + template. โหลดตอนจะ produce/finalize deliverable
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-deliverable/adr.md
WHEN: adr_create_or_edit=true
OWNER: solution-architect
REQUIRED-BEFORE: adr_commit
```

# ADR lifecycle + template

> แยกจาก `SKILL.md` v3.12.1 — 7 agent preload skill นี้ แต่ส่วนนี้ใช้เฉพาะตอนกำลังจะส่งงานจริง

## 📜 ADR Lifecycle (ADR ต้องตายเป็น)

ทุก ADR มี **`Status`** บังคับ: `Proposed` → `Accepted` → (`Deprecated` | `Superseded by ADR-NNN`)

```markdown
# ADR-014: เลือก PostgreSQL เป็น primary store
**Status**: Superseded by ADR-031 (2026-07-30)   **Date**: 2026-02-11   **Owner**: Sara
## Context / Options / Decision / Consequences
```

- เปลี่ยนใจ = **เขียน ADR ใหม่ที่ supersede** ห้ามแก้ ADR เดิมย้อนหลัง (ประวัติการตัดสินใจคือคุณค่าของ ADR)
- ADR ใหม่ต้องอ้าง `Supersedes: ADR-NNN` และ ADR เก่าต้องถูกอัปเดต `Status` ในคอมมิตเดียวกัน — 2 ทิศทางเสมอ
- `outputs/adr/INDEX.md` = ตารางเดียวรวม id / title / status / superseded-by → Sara ดูแล
- ห้าม implement ตาม ADR ที่ยัง `Proposed` — ต้อง `Accepted` ก่อน Phase 2
