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
> `shode-house-discipline` § Extension protocols ชี้มาที่นี่ (single source of truth ของ REVIEW format)

## REVIEW Report Format (confirmed evidence home, Markdown fallback)

ใช้ format นี้ (cite-before-claim ตาม `shode-house-discipline` § Project Evidence Protocol). สรุป:

### Compact task summary (Beads example)
```
[code-reviewer|qa-engineer|security-engineer review bd-42] verdict: FAIL
- 🔴 1: <file:line> <issue>
- 🟠 2: <count + summary>
- 🟡 5: <count, see md fallback>
Coverage: unit 78% → 81% target hit; mutation 72%
UX: ux-ui-designer POST PASS (separate)
Loop route: code → Phase 2
```

### Markdown report — use the confirmed evidence path
Full template per finding (file:line · why it matters · evidence path · suggested change)
One file per axis, named for it: `outputs/<bd-id>/<NN>-review-<axis>-iter<n>.md` (or the same name in the confirmed evidence home), `<axis>` = `standards` · `runtime` · `spec` · `security` · `domain` · `ui`. Never a combined multi-axis file; never write into another axis's file.

### Output budget (§5.13 — bd:shode-roadmap/C-G1)
inline (task note / return message) ≤ **10 findings** เรียง severity — เกิน → นับรวมต่อ severity + full list ใน artifact/md แล้ว link path
return ต่อ orchestrator = status + artifact/revision + checks performed + decisive findings/dissent + questions/next owner ตาม harness; compact summary ต้องเก็บ evidence และ blockers ห้ามจำกัดเหลือ verdict/path จนตรวจ acceptance ไม่ได้

### Storage rule (ห้ามเขียนซ้ำ 2 ที่)

Store one canonical report in the confirmed evidence home, including Markdown when
selected alongside Jira, Beads or another task tracker. Other records link to it;
do not copy the report into competing sources of truth. Keep full findings and
evidence in the artifact; compact summaries must not discard dissent or blockers.

### External tracker or PR updates
An identifier or URL is not permission to post. Use actual available tools only
when the request/project authority covers that update. Otherwise return the report
and proposed update to the router. Record unavailable authorized updates as pending
sync, never claim they were posted. Include an accessible artifact link, not a
local-only path that the remote reader cannot open.

---

## Loop Routing Recommendation (Phase 4 input)

code-reviewer/qa-engineer/security-engineer **must recommend** loop route ใน report:

| Finding type | Route → |
|---|---|
| Code logic / SOLID / perf | Phase 2 (developer fix) |
| UI / visual / a11y manual | implementation ไม่ตรง approved design → Phase 2; baseline/design ผิด → Phase 1b (ux-ui-designer) |
| Spec / AC / regulation gap | Phase 1a (business-analyst ∥ solution-architect revise) |
| Test gap | Phase 2 (developer) + invoke `shode-house:automate-test` skill (qa-engineer) |
| Security finding | implementation gap → Phase 2; threat model/security acceptance gap → Phase 1c ก่อนแก้ affected implementation |
| Multi-route | router triage (don't recommend; defer) |

---

---

## Domain routing (ย้ายจาก SKILL.md v3.12)

Trigger ตาม code path:

| Keyword in changed code | Domain Expert |
|---|---|
| payment / ledger / money / settle | → **fintech-expert** |
| accounting / journal / inventory (generic) | → **erp-expert** |
| SAP / ABAP / Fiori / BAPI / IDoc / S4HANA | → **sap-expert** |
| order / market / matching / FIX | → **trading-expert** |
| policy / claim / premium / actuarial | → **insurance-expert** |
| booking / rate / yield (hotel/airline) | → **booking-expert** |
| cart / checkout / promotion / catalog | → **ecommerce-expert** |

Domain Expert verify: regulation cite (`shode-house-discipline` § Project Evidence Protocol) + business rule + edge case ที่เฉพาะ domain. ห้าม skip ถ้า domain-sensitive

---
