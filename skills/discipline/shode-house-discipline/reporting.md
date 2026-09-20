---
name: reporting
description: Reference (lazy-load) ของ `shode-house-discipline` — ตัวอย่าง report เต็ม, สิ่งที่ห้าม/ห้ามตัดในรายงาน, risk template, ตัวอย่าง tag prefix. โหลดเมื่อกำลังจะเขียนรายงานยาวหรือไม่แน่ใจว่าอะไรตัดได้
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-discipline/reporting.md
WHEN: report_length_exceeds_return_format=true OR risk_statement_required=true
OWNER: orchestrator
REQUIRED-BEFORE: report_to_user
```

# Report & risk conventions

## ✍️ Work deep, report short

**ทำละเอียด ≠ พูดเยอะ.** ความละเอียดอยู่ใน artifact file + tool output ที่ paste ไม่ใช่ในคำบรรยาย

| ต้องยาว (ไม่จำกัด) | ต้องสั้น (บังคับ) |
|---|---|
| artifact file ที่เขียนลง `outputs/` | ข้อความที่ส่งกลับ orchestrator/user |
| tool output ที่ paste เป็นหลักฐาน | คำอธิบายสิ่งที่กำลังจะทำ |
| code + test ที่เขียนจริง | สรุปสิ่งที่เพิ่งทำเสร็จ |

**ห้าม**: preamble ("ผมจะเริ่มด้วย…") · narrate ทุก tool call · เล่าซ้ำสิ่งที่อยู่ใน artifact แล้ว · restate คำถาม user · สรุปปิดท้ายที่ไม่มีข้อมูลใหม่
**ตัดคำบรรยายได้ ห้ามตัด**: evidence · security finding · ตัวเลข · dissent · สิ่งที่ทำไม่สำเร็จ
เกินไปอีกขั้น (long loop / broadcast) → โหลด `caveman` skill

## 🏷️ Tag prefix — ตัวอย่าง

```
[Dave|state:phase-2|bd:42]
[Uma|state:adhoc|bd:none]
Dave ▸ Chris : payment service implement เสร็จ พร้อม review (bd:42)
```
ไม่มี bd → `bd:none` · ไม่มี phase → `state:adhoc`

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
[Oliver] รับงาน, triage → Bella + Sara
[Bella] เก็บ requirement → 5 clarifying options
[Sara] ออกแบบ C4 + ADR-01 ledger
[Dave#1] implementing POST /payments/create
[Dave#2] implementing POST /payments/refund (parallel)
[Chris] reviewing src/payment.py — 2 high finding
[Quinn] running E2E checkout → 8/8 pass
[Aaron] docker compose up → all healthy ✅
[Felix] validating ledger flow — double-entry ok
[Uma] Figma checkout v2 → handoff Dave
```

**กติกา**:
- Worker return tag = `[ชื่อ]`; parallel Dave = `[Dave#1]`, `[Dave#2]`
- 1 message = 1 agent voice (ห้ามผสม)
- Preserve owner, task ID and phase at handoffs and meaningful state changes.
- Long output (BRD/ADR/code) → tag header + content ปกติ

### 🔬 Structured Tag (optional — สำหรับ pipeline integration)

ขยาย `[ชื่อ]` → `[ชื่อ|key:val|key:val]` เมื่อต้องการให้ tool downstream parse ได้:

```
[Oliver|state:plan|engagement:E-42] รับงาน triage
[Dave#1|state:impl|task:bd-15|file:payment.py] writing handler
[Chris|state:review|finding:HIGH:2|MED:5] block merge
[Quinn|state:test|suite:e2e|pass:8|fail:0] checkout flow ✅
[Aaron|state:deploy|env:staging|health:200] live
```

**Standard keys**:
- `state` — plan/impl/review/test/deploy/block/done
- `task` — bd issue id (bd-N) หรือ tracker external id
- `engagement` — E-N (Oliver track)
- `file` — file path ที่กำลังแก้
- `finding` — severity:count (Chris/Quinn)
- `pass`/`fail` — test counter
- `env` — dev/staging/uat/prod
- `health` — HTTP status / pass/fail
- `mode` — afk/interactive/hybrid (Oliver)

**Default**: human-readable `[ชื่อ]` พอ; structured ใช้เมื่อ user สั่ง "structured" หรือมี downstream parser

### Oliver caveman broadcast (1 บรรทัด ≤ 80 chars)
```
[Oliver] sara+bella → requirement
[Oliver] bella done → sara reviewing
[Oliver] dave#1+#2 parallel on payment endpoints
[Oliver] chris reviewing | quinn integration test
[Oliver] blocked: waiting auth spec
```
