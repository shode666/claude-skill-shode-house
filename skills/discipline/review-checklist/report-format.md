---
name: report-format
description: Reference (lazy-load) ของ `review-checklist` — REVIEW report template (bd-native + markdown fallback) + Loop Routing table. โหลดตอนจะเขียน report
---

```lazy-load-contract
LOAD: skills/discipline/review-checklist/report-format.md
WHEN: review_report_write=true
OWNER: code-reviewer
REQUIRED-BEFORE: review_report_post
```

# REVIEW Report Format + Loop Routing (reference)

> แยกจาก `SKILL.md` เป็น output template ที่ใช้ตอนท้ายของ review เท่านั้น ไม่ต้องอยู่ใน preload
> `shode-house-evidence` ชี้มาที่นี่ (single source of truth ของ REVIEW format)

## REVIEW Report Format (bd-native primary, markdown fallback)

ใช้ format ใน `shode-house-evidence` (REVIEW Report Format section). สรุป:

### bd notes (≤ 500 chars compact)
```
[Chris|Quinn|Sentinel review bd-42] verdict: FAIL
- 🔴 1: <file:line> <issue>
- 🟠 2: <count + summary>
- 🟡 5: <count, see md fallback>
Coverage: unit 78% → 81% target hit; mutation 72%
UX: Uma POST PASS (separate)
Loop route: code → Phase 2
```

### Markdown fallback (no bd) — `outputs/REVIEW-<feature>.md`
Full template per finding (file:line · why it matters · evidence path · suggested change)

### Storage rule (🔴 ห้ามเขียนซ้ำ 2 ที่)

report อยู่ที่เดียว: มี bd → **bd notes เป็น primary** (markdown เฉพาะตอนยาวเกิน 500 chars แล้ว bd note ต้อง link ไปหา)
ไม่มี bd → markdown fallback อย่างเดียว · **ห้าม** เขียนทั้ง bd และ md เนื้อหาเดียวกัน แล้วปล่อยให้ทั้งสองฝั่ง drift

### Always: link external tracker
- ถ้ามี Jira key → `addCommentToJiraIssue` กลับ ticket ด้วย bd link หรือ md path
- ถ้ามี GitHub PR → `gh pr review --comment "..."` หรือ inline comment

---

## Loop Routing Recommendation (Phase 4 input)

Chris/Quinn/Sentinel **must recommend** loop route ใน report:

| Finding type | Route → |
|---|---|
| Code logic / SOLID / perf | Phase 2 (Dave fix) |
| UI / visual / a11y manual | Phase 1b (Uma redesign) |
| Spec / AC / regulation gap | Phase 1a (Bella ∥ Sara revise) |
| Test gap | Phase 2 (Dave) + invoke `automate-test` skill (Quinn) |
| Security finding | Phase 1c (Sentinel threat model update) → Phase 2 |
| Multi-route | Oliver triage (don't recommend; defer) |

---

---

## Domain routing (ย้ายจาก SKILL.md v3.12)

Trigger ตาม code path:

| Keyword in changed code | Domain Expert |
|---|---|
| payment / ledger / money / settle | → **Felix** |
| accounting / journal / inventory (generic) | → **Elena** |
| SAP / ABAP / Fiori / BAPI / IDoc / S4HANA | → **Sam** |
| order / market / matching / FIX | → **Tara** |
| policy / claim / premium / actuarial | → **Iris** |
| booking / rate / yield (hotel/airline) | → **Brooke** |
| cart / checkout / promotion / catalog | → **Emma** |

Domain Expert verify: regulation cite (`shode-house-evidence`) + business rule + edge case ที่เฉพาะ domain. ห้าม skip ถ้า domain-sensitive

---
