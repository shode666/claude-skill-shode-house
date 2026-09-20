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

- [ ] **Review scope verified** — caller (Oliver/`/review`) ส่ง fixed point + working diff command สำหรับ diff review หรือ accessible full-file/snippet scope สำหรับ non-git review ไม่ให้ reviewer เดาเอง
      วิธี resolve = `commands/review.md` § Scope resolution; ตรวจ ref/diff เมื่อใช้ diff และตรวจ completeness ของ supplied content เมื่อเป็น full-content review
- [ ] **Spec source ระบุได้** — หาตามลำดับ: bd-id/issue ref ใน commit message → path ที่ user ส่ง → `outputs/SPEC-<bd-id>.md` / `outputs/<bd-id>/` → ส่งคำถามที่ยังจำเป็นให้ Oliver ถามผู้ใช้
      ไม่มี spec จริง ๆ → Spec axis รายงาน **"no spec available"** ห้าม pass เงียบ
- [ ] **Required checks identified** — use actual configured tools; missing tooling is a reported verification limit, not permission to install it. Continue supported review, holding only acceptance that requires the missing check.
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
