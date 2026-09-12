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

## REVIEW Report Format (confirmed evidence home, Markdown fallback)

ใช้ format ใน `shode-house-evidence` (REVIEW Report Format section). สรุป:

### Compact task summary (Beads example)
```
[Chris|Quinn|Sentinel review bd-42] verdict: FAIL
- 🔴 1: <file:line> <issue>
- 🟠 2: <count + summary>
- 🟡 5: <count, see md fallback>
Coverage: unit 78% → 81% target hit; mutation 72%
UX: Uma POST PASS (separate)
Loop route: code → Phase 2
```

### Markdown report — use the confirmed evidence path
Full template per finding (file:line · why it matters · evidence path · suggested change)

### Output budget (🔴 §5.13 — bd:shode-roadmap/C-G1)
inline (bd note / return message) ≤ **10 findings** เรียง severity — เกิน → นับรวมต่อ severity + full list ใน artifact/md แล้ว link path
return ต่อ orchestrator = verdict + ตัวเลขสรุป + path เท่านั้น — **ห้ามตัด**: evidence line · security finding · ตัวเลข · dissent (ตาม discipline)

### Storage rule (🔴 ห้ามเขียนซ้ำ 2 ที่)

Store one canonical report in the confirmed evidence home, including Markdown when
selected alongside Jira, Beads or another task tracker. Other records link to it;
do not copy the report into competing sources of truth. Keep full findings and
evidence in the artifact; compact summaries must not discard dissent or blockers.

### External tracker or PR updates
An identifier or URL is not permission to post. Use actual available tools only
when the request/project authority covers that update. Otherwise return the report
and proposed update to Oliver. Record unavailable authorized updates as pending
sync, never claim they were posted. Include an accessible artifact link, not a
local-only path that the remote reader cannot open.

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
