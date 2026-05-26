---
name: shode-house-broadcast
description: |
  [WHAT] Communication discipline — Agent Tag Prefix + Structured Tag + Oliver caveman broadcast + Handoff Broadcast Protocol (v3.0 caveman 1-line).
  [AUDIENCE] ทุก agent (Tag Prefix mandatory ทุก message); Oliver (caveman broadcast every state transition); ทุก agent hand-off.
  [WHEN] ทุก message agent → user; Oliver state transition (caveman); agent A → agent B (hand-off broadcast).
  [TRIGGER] /shode-house:broadcast, "tag prefix", "caveman broadcast", "handoff", "Agent A ▸ Agent B", "structured tag".
---

# shode-house — Communication & Broadcast

> Tag prefix ทุก message. Oliver caveman broadcast ทุก state. Handoff ใช้ caveman 1-line

---
## 🗣️ Communication

**Default**: ไทย + technical term อังกฤษ

### 🏷️ Agent Tag Prefix (🔴 บังคับ — ทุก message)

ทุก message ที่ออกจาก agent **ต้องขึ้นต้นด้วย `[ชื่อ]`** เพื่อ visibility:

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
- Tag = `[ชื่อ]` ทุก message; parallel Dave = `[Dave#1]`, `[Dave#2]`
- 1 message = 1 agent voice (ห้ามผสม)
- Mandatory: ตอนเริ่ม + ทุก state change + ตอนเสร็จ + hand-off
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

---

## 🧵 Task Tracking — Pluggable Tracker (default: beads/bd)

## 🤝 Handoff Broadcast Protocol (🔴 v3.0 — caveman 1-line)

### Arrow convention (🔴 v3.0.1)

ใช้ 2 arrows คนละความหมาย (accept divergence — semantic distinction):

| Arrow | ความหมาย | When |
|-------|---------|------|
| `▸` | **Handoff broadcast** (formal, between agents/teams in workflow) | Phase transition, agent-to-agent handoff, multi-sig gate |
| `→` | **General flow / sequence / implication** (informal) | Process steps, code flow, "X causes Y", documentation flow |

ตัวอย่าง:
- `Bella ▸ Dave : impl bd-42` — handoff (use ▸)
- `Phase 1a → 1b` — general phase sequence (use →)
- `low contrast → fail WCAG` — implication (use →)

> ห้ามใช้ `▸` ใน documentation flow / code-flow / general explanation. ห้ามใช้ `→` ใน formal handoff (M3 protocol บังคับ `▸`)

### Format มาตรฐาน
```
[<from>] ▸ [<to>] : <what> (bd-<id>)
```

### Agent-to-agent
```
Bella ▸ Dave   : impl bd-42
Dave  ▸ Verify : CR + test + sec (bd-42)
Verify ▸ Oliver : 2 Major, 1 Minor
Oliver ▸ Dave   : fix M (bd-42, iter 2)
Oliver ▸ Ops    : deploy bd-42
Ops    ▸ ✓      : prod stable, SLO green
```

### Team-level (whole team activates)
```
Design  ▸ Dev    : spec done (bd-42)
Dev     ▸ Verify : impl done
Verify  ▸ Lead   : triage
Lead    ▸ Ops    : ship it
```

### กติกา 4 ข้อ
1. **1 บรรทัด** เท่านั้น (รายละเอียดที่ bd notes)
2. **bd-id บังคับ** ถ้า inner-loop; team-level ไม่ต้อง
3. **Arrow** = `▸` (ใช้ consistent ทั้ง project)
4. **State explicit** สั้น: `impl / CR / test / sec / fix / retest / clean / deploy / ✓`

---

## 📋 RACI per Phase (🔴 v3.0)
