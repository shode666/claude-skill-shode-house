---
name: intake
description: Reference (lazy-load) ของ `review-checklist` — เงื่อนไขที่ต้องมีก่อนเริ่ม review (required inputs) + กรณีที่ไม่ควร review. โหลดตอนรับงาน review ครั้งแรกของ bd นั้น
---

```lazy-load-contract
LOAD: skills/discipline/review-checklist/intake.md
WHEN: review_request_received=true AND scope_or_spec_unconfirmed=true
OWNER: code-reviewer
REQUIRED-BEFORE: review_start
```

# Review intake

## Required inputs — refuse without

- [ ] **ขอบเขต diff ถูก pin มาแล้ว** — caller (Oliver/`/review`) ต้องส่ง **fixed point + diff command ที่รันได้จริง** มาให้ ไม่ใช่ให้ reviewer เดาเอง
      วิธี resolve (fallback ladder สำหรับ path/snippet/non-git) = `commands/review.md` § Scope resolution · reviewer ตรวจแค่ว่า diff ไม่ว่างและ ref resolve ได้
- [ ] **Spec source ระบุได้** — หาตามลำดับ: bd-id/issue ref ใน commit message → path ที่ user ส่ง → `outputs/SPEC-<bd-id>.md` / `outputs/<bd-id>/` → ถามผู้ใช้
      ไม่มี spec จริง ๆ → Spec axis รายงาน **"no spec available"** ห้าม pass เงียบ
- [ ] **Static analysis tool พร้อม** (lint/SAST configured — Chris ใช้ Bash จริง ไม่ใช่ "ดู visually")
- [ ] **Tracker available** (bd active หรือ Jira key — finding ต้อง track ไม่ใช่ chat message)
- [ ] **Severity scale agreed** (project ใช้ 🔴/🟠/🟡/🔵/💡 default — ห้าม "minor/major" loose)

## When NOT to use

- **Spike / throwaway script** — review overhead ไม่คุ้ม
- **Generated code** (codegen output, ORM model auto-generated) — review template ไม่ใช่ instance
- **Pure doc/markdown change** — Bella/Uma review เนื้อหา ไม่ใช่ review-checklist
- **Production hot-fix P0** ที่ต้อง ship ทันที — รันเฉพาะ 🔴 Critical (Security + Correctness); defer มิติอื่นเป็น follow-up ที่ track ไว้
