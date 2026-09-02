# Enforcement Map — กฎสำคัญ 20 ข้อ (Workstream 1 ของ v3.13)

> ทำ **ก่อน** refactor topology: ย้ายของได้ก็ต่อเมื่อรู้ว่ากฎไหนหายไม่ได้ และกฎไหน lazy-load ได้
> machine-readable: `.enforcement-map.json` (CI ใช้ตรวจว่า source-of-truth ยัง resolve ได้)

| # | Rule | Owner | Trigger | preload? | Source of truth | Verification |
|---|---|---|---|:--:|---|---|
| 1 | Safety R0/R1/R2 | ทุก agent | ทุกงาน | ✅ | `skills/discipline/shode-house-discipline/SKILL.md` | mutation |
| 2 | NO MAGIC / evidence-before-claim | ทุก agent | ทุก claim | ✅ | `skills/discipline/shode-house-evidence/SKILL.md` | fixture |
| 3 | VERIFY BEFORE DONE | ทุก agent | ก่อน claim done | ✅ | `skills/discipline/shode-house-discipline/SKILL.md` | fixture |
| 4 | Handoff contract (min fields) | ทุกตัวที่ delegate | delegation | ✅ | `skills/discipline/shode-house-discipline/SKILL.md` | ci:path-tool |
| 5 | Response language mirror | ทุก agent | ทุก message | ✅ | `skills/discipline/shode-house-discipline/SKILL.md` | fixture |
| 6 | Recite Discipline Card | main session | first response | ❌ | `output-styles/oliver.md` | output-style-test |
| 7 | AskUserQuestion main-session relay | main session | ambiguity | ❌ | `skills/discipline/shode-house-workflow/smart-coop.md` | ci:18 + fixture |
| 8 | Spec axis (diff vs spec) | business-analyst | Phase 3b / review | ❌ | `skills/discipline/review-checklist/spec-axis.md` | ci:19 + fixture |
| 9 | Standards axis 7-dim | code-reviewer | Phase 3b | ❌ | `agents/code-reviewer.md` | fixture |
| 10 | Integration/E2E matrix | qa-engineer | Phase 3b | ❌ | `agents/qa-engineer.md` | fixture |
| 11 | Definition of Done | orchestrator + producer | phase exit | ❌ | `skills/discipline/shode-house-deliverable/definition-of-done.md` | close-gate |
| 12 | Anti-Puppet (no false done) | ทุก producer | claim done | ✅ | `skills/discipline/shode-house-deliverable/SKILL.md` | fixture |
| 13 | Close-on-done M8 | orchestrator | item land | ✅ | `skills/discipline/shode-house-drift/SKILL.md` | fixture |
| 14 | UX/visual evidence ladder | ux-ui-designer, qa-engineer, code-reviewer | frontend touched | ❌ | `skills/ui/ui-test/SKILL.md` | frontend fixture |
| 15 | WCAG 2.2 AA manual SC | ux-ui-designer | frontend touched | ❌ | `agents/ux-ui-designer.md` | a11y fixture |
| 16 | Contrast gate + border ACK | ux-ui-designer | Phase 1b tokens | ❌ | `references/design-intel/README.md` | ci:17 smoke |
| 17 | Domain citation + persona disclaimer | 7 domain experts | domain claim | ✅ | `agents/*-expert.md` | citation fixture x7 |
| 18 | Scope discipline / out-of-scope record | ทุก agent | spec change | ✅ | `skills/discipline/shode-house-discipline/SKILL.md` | fixture |
| 19 | Preload + agent budget ratchet | maintainer | ทุก PR | ❌ | `.preload-budget` | ci:16 + ci:20 |
| 20 | Redact ก่อน paste evidence | ทุก agent ที่ paste output | ทุก evidence | ✅ | `skills/workflow/diagnose/SKILL.md` | fixture |

## กฎที่ **หายไม่ได้** (preload ทุก agent — 10 ข้อ)

Safety R0/R1/R2, NO MAGIC / evidence-before-claim, VERIFY BEFORE DONE, Handoff contract (min fields), Response language mirror, Anti-Puppet (no false done), Close-on-done M8, Domain citation + persona disclaimer, Scope discipline / out-of-scope record, Redact ก่อน paste evidence

## กฎที่ **lazy-load ได้** (10 ข้อ)

โหลดตาม trigger — ต้องมี `LOAD/WHEN/OWNER/REQUIRED-BEFORE` ตาม Workstream 7 และมี fixture ยืนยันว่า **ถ้าไม่โหลดแล้ว gate ต้องจับได้**

Recite Discipline Card, AskUserQuestion main-session relay, Spec axis (diff vs spec), Standards axis 7-dim, Integration/E2E matrix, Definition of Done, UX/visual evidence ladder, WCAG 2.2 AA manual SC, Contrast gate + border ACK, Preload + agent budget ratchet

## บทเรียนจาก v3.12 ที่ทำให้ต้องมีเอกสารนี้

กฎ 5 ข้อนี้เคย **พังเงียบ** เพราะไม่มีใครถือ inventory: Recite Card (ซ้ำ 2 ที่ ขัดกันเอง) · AskUserQuestion (permission ถูกชั้น API แต่ผิดชั้น runtime) · Close-on-done (เขียนไว้แต่ไม่มี step รัน) · WCAG 2.2 (ประกาศ 4 จุด ไม่มี criterion) · XL split (กฎมี ไม่มีใครรัน)
