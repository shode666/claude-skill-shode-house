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
- [ ] **Canonical task/evidence home available** — project-selected tracker or Markdown fallback; findings must survive the chat.
- [ ] **Severity scale agreed** (project ใช้ 🔴/🟠/🟡/🔵/💡 default — ห้าม "minor/major" loose)
- [ ] Record `[REVIEW DISPATCH CARD]` in the checkpoint or report before dispatch;
      verify actual assignments against it. See `commands/review.md` § Step 1.

## When NOT to use

- **Spike / throwaway script** — review overhead ไม่คุ้ม
- **Generated code** (codegen output, ORM model auto-generated) — review template ไม่ใช่ instance
- **Pure explanatory docs** — route content review appropriately. Agent instructions,
  executable configuration and permission policy are not merely documentation.
- **Production hot-fix P0** — a reduced emergency review needs explicit authority and
  recorded risk/follow-up. Urgency alone does not waive required security/correctness gates.
