---
name: reporting
description: Reference (lazy-load) ของ `shode-house-discipline` — ตัวอย่าง report เต็ม, สิ่งที่ห้าม/ห้ามตัดในรายงาน, risk template, ตัวอย่าง tag prefix. โหลดเมื่อกำลังจะเขียนรายงานยาวหรือไม่แน่ใจว่าอะไรตัดได้
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-discipline/reporting.md
WHEN: report_length_exceeds_return_format=true OR risk_statement_required=true
OWNER: router
REQUIRED-BEFORE: report_to_user
```

# Report & risk conventions

**Contents**

- [✍️ Work deep, report short](#️-work-deep-report-short)
- [🏷️ Tag prefix — ตัวอย่าง](#️-tag-prefix--ตัวอย่าง)
- [⚠️ Risk Template](#️-risk-template)
- [🗣️ Communication](#️-communication)

## ✍️ Work deep, report short

**ทำละเอียด ≠ พูดเยอะ.** ความละเอียดอยู่ใน artifact file + tool output ที่ paste ไม่ใช่ในคำบรรยาย

| ต้องยาว (ไม่จำกัด) | ต้องสั้น (บังคับ) |
|---|---|
| artifact file ที่เขียนลง `outputs/` | ข้อความที่ส่งกลับ orchestrator/user |
| tool output ที่ paste เป็นหลักฐาน | คำอธิบายสิ่งที่กำลังจะทำ |
| code + test ที่เขียนจริง | สรุปสิ่งที่เพิ่งทำเสร็จ |

**ห้าม**: preamble ("ผมจะเริ่มด้วย…") · narrate ทุก tool call · เล่าซ้ำสิ่งที่อยู่ใน artifact แล้ว · restate คำถาม user · สรุปปิดท้ายที่ไม่มีข้อมูลใหม่
**ตัดคำบรรยายได้ ห้ามตัด**: evidence · security finding · ตัวเลข · dissent · สิ่งที่ทำไม่สำเร็จ
เกินไปอีกขั้น (long loop / broadcast) → โหลด `shode-house:caveman` skill

## 🏷️ Tag prefix — ตัวอย่าง

```
[developer|state:phase-2|bd:42]
[ux-ui-designer|state:adhoc|bd:none]
developer ▸ code-reviewer : payment service implement เสร็จ พร้อม review (bd:42)
```
ไม่มี task → `bd:none` · ไม่มี phase → `state:adhoc`

## ⚠️ Risk Template

```
Risk: [what] | Likelihood: L/M/H | Impact: L/M/H | Mitigation: [concrete] | Owner: [agent]
```
ใช้ทุกครั้งที่เสนอ R0/R1 action, dissent, หรือ trade-off ที่ user ต้องตัดสินใจ

> Keep ownership and state visible in handoffs; avoid repeated tags in ordinary conversation.

## 🗣️ Communication

**Default**: mirror the user's language; keep code, paths and logs verbatim.

### 🏷️ Agent Tag Prefix (handoff identity)

Worker results identify their owner; these examples are not a required prefix for every user-facing message:

```
[router] รับงาน, triage → business-analyst + solution-architect
[business-analyst] เก็บ requirement → 5 clarifying options
[solution-architect] ออกแบบ C4 + ADR-01 ledger
[developer#1] implementing POST /payments/create
[developer#2] implementing POST /payments/refund (parallel)
[code-reviewer] reviewing src/payment.py — 2 high finding
[qa-engineer] running E2E checkout → 8/8 pass
[devops-engineer] docker compose up → all healthy ✅
[fintech-expert] validating ledger flow — double-entry ok
[ux-ui-designer] Figma checkout v2 → handoff developer
```

**กติกา**:
- Worker return tag = `[agent id]`; parallel developer = `[developer#1]`, `[developer#2]`
- 1 message = 1 agent voice (ห้ามผสม)
- Preserve owner, task ID and phase at handoffs and meaningful state changes.
- Long output (BRD/ADR/code) → tag header + content ปกติ

### 🔬 Structured Tag (optional — สำหรับ pipeline integration)

ขยาย `[ชื่อ]` → `[ชื่อ|key:val|key:val]` เมื่อต้องการให้ tool downstream parse ได้:

```
[router|state:plan|engagement:E-42] รับงาน triage
[developer#1|state:impl|task:bd-15|file:payment.py] writing handler
[code-reviewer|state:review|finding:HIGH:2|MED:5] block merge
[qa-engineer|state:test|suite:e2e|pass:8|fail:0] checkout flow ✅
[devops-engineer|state:deploy|env:staging|health:200] live
```

**Standard keys**:
- `state` — plan/impl/review/test/deploy/block/done
- `task` — task id (bd-N) หรือ tracker external id
- `engagement` — E-N (router track)
- `file` — file path ที่กำลังแก้
- `finding` — severity:count (code-reviewer/qa-engineer)
- `pass`/`fail` — test counter
- `env` — dev/staging/uat/prod
- `health` — HTTP status / pass/fail
- `mode` — afk/interactive/hybrid (router)

**Default**: human-readable `[ชื่อ]` พอ; structured ใช้เมื่อ user สั่ง "structured" หรือมี downstream parser

### Router caveman broadcast (1 บรรทัด ≤ 80 chars; when → `handoff.md` § Handoff Broadcast Protocol)
```
[router] solution-architect+business-analyst → requirement
[router] business-analyst done → solution-architect reviewing
[router] blocked: waiting auth spec
```
