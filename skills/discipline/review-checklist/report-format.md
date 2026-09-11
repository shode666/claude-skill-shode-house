---
name: report-format
description: Reference for review results, authorized project-selected storage and suggested follow-up routing. Load when returning a review report.
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

## REVIEW Report Format (project-selected storage)

This file owns the review format; `shode-house-evidence` links here, not vice versa.

### Compact task note (example when Beads is the designated tracker)
```
[Chris|Quinn|Sentinel review bd-42] verdict: FAIL
- 🔴 1: <file:line> <issue>
- 🟠 2: <count + summary>
- 🟡 5: <count, see authorized linked report if needed>
Coverage: unit 78% → 81% target hit; mutation 72%
UX: Uma POST PASS (separate)
Loop route: code → Phase 2
```

### Linked report artifact (when the project uses Markdown)
Full template per finding (file:line · why it matters · evidence path · suggested change)

### Output budget (🔴 §5.13 — bd:shode-roadmap/C-G1)
inline (bd note / return message) ≤ **10 findings** เรียง severity — เกิน → นับรวมต่อ severity + full list ใน artifact/md แล้ว link path
return ต่อ orchestrator = verdict + ตัวเลขสรุป + path เท่านั้น — **ห้ามตัด**: evidence line · security finding · ตัวเลข · dissent (ตาม discipline)

### Storage rule (🔴 ห้ามเขียนซ้ำ 2 ที่)

Return findings in the conversation by default. Persist only when the user or
active project instructions authorize it, to that project's designated tracker or
artifact location (Markdown, Jira, Redmine, Beads or another system). Reuse IDs and
status conventions; do not select Beads merely because its CLI is installed.
Keep one authoritative report, with links rather than duplicate content. If the
designated system is inaccessible, return the report and disclose unsynchronized
status; a permitted local handoff is pending synchronization, not a new tracker.

### External posting authority

A Jira key or PR URL identifies the review target, not permission to comment,
submit a PR review, change status or create an issue. Post only when the user or
active project instructions authorize that operation; the main session uses an
available host tool and verifies the result. Delegates return findings to the owner,
not directly to external systems. Do not claim a post succeeded without confirmation.

---

## Loop Routing Recommendation (Phase 4 input)

Chris/Quinn/Sentinel **must recommend** loop route ใน report:

Routes below are recommendations, not authorization to implement, deploy or post.

| Finding type | Route → |
|---|---|
| Code logic / SOLID / perf | Phase 2 (Dave fix) |
| UI / visual / a11y manual | Phase 1b (Uma redesign) |
| Spec / AC / regulation gap | Phase 1a (Bella ∥ Sara revise) |
| Test gap | Phase 2 (Dave regression test); `automate-test` only for a project-wide CI/strategy gap |
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
