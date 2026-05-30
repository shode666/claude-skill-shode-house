---
name: shode-house-drift
description: |
  [WHAT] Workflow Drift Defense — 7 mechanisms (M1-M7) ป้องกัน workflow regression: Ingress Guard, Follow-up Classifier, Anti-Puppet Done, User Comment = FAIL, Spec change = mandatory bd revision, Conversation State pin, Direct-to-agent block.
  [AUDIENCE] Oliver (primary enforcer); ทุก agent ต้องผ่าน Ingress Guard.
  [WHEN] Every user message (M1 Ingress Guard); every follow-up (M2 Classifier); every "done" claim (M3); every comment (M4); every spec change (M5); session state (M6); agent invocation (M7).
  [TRIGGER] /shode-house:drift, "Drift Defense", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "Ingress Guard", "Follow-up Classifier", "Anti-Puppet Done", "Conversation State", "Direct-to-agent block", "drift", "regression".
---

# shode-house — Workflow Drift Defense (7 Mechanisms)

> v3.0 invariants ที่ Oliver enforce ทุก message. ขาด mechanism ไหน = workflow drift จะกลับมา

---
## 🆕 New Phases (🔴 v3.0)

### Phase 0 — Discovery (NEW)
- **Owner**: 🔍 Discover Team (Patrick + Domain SME)
- **Trigger**: New initiative, no bd issue yet (continuous — not sprint-bound)
- **Output**: OKR + opportunity sizing + RICE/WSJF priority + Domain pain validation
- **Gate**: `pre-spec` — sign-off ก่อน Phase 1a Foundation
- **Why**: ก่อน v3.0 กระโดดเข้า BRD ทันที → 30% งานถูก kill ภายหลัง

### Phase 1c — Threat Model (NEW)
- **Owner**: ✅ Sentinel (lead) + Sara (architecture context)
- **Trigger**: feature touching auth / PII / money / external integration / file upload / AI agent
- **Output**: STRIDE + abuse case + security AC injected into Phase 1a
- **Gate**: `pre-implement` — สิทธิ์ block Phase 2 ถ้าไม่ผ่าน
- **Note**: ขนาน parallel กับ 1b ได้ ถ้า scope independent

### Phase 6 — Operate (NEW — continuous post-deploy)
- **Owner**: 🚀 Reggie (lead) + Aaron (infra) + Oliver (escalation routing)
- **Trigger**: post-deploy continuous
- **Output**: SLO burn rate watch + incident response + blameless postmortem + runbook update
- **Escalation**: error budget < 0 → ping Patrick (PM) for feature freeze conversation

### ~~Phase 7 — Learn (REMOVED v3.3)~~
- **v3.3 change**: Phase 7 sprint retro deprecated — per-bd reflect in Phase 4 Triage (Oliver `bd remember <lesson>`)
- **Patrick OKR review**: continuous (per-bd contribution to OKR; no sprint bracket)
- **Tech debt RICE**: continuous backlog priority by Patrick (Stan tech-debt input)
- **ห้ามใช้** `/sprint close retro` — command removed

---

## 🛡️ Workflow Drift Defense (🔴 v3.0 — 7 Mechanisms)

## 🛡️ Workflow Drift Defense (🔴 v3.0 — 7 Mechanisms)

แก้ปัญหา **agent หลุด workflow ใน follow-up message** — Dave บอก "เสร็จแล้ว" โดยไม่ผ่าน Verify, fix ตรงโดยไม่ผ่าน Phase 1a

### M1 — Ingress Guard (🔴 บังคับ ก่อน respond ทุก message)

ทุก agent ก่อนตอบ user message ใน active engagement:
```
1. bd show <id>   → no bd-id → STOP, route Oliver triage
2. read state     → state ∈ {pick|impl|ui-check|review|triage|done}
3. classify msg   → {new-task|fix|spec-change|question|done-claim|cancel}
4. route check    → message type × current state = valid? FAIL → STOP, explicit reroute
```

### M2 — Follow-up Classifier (Oliver auto-triage ทุก user message)

```
User message → Oliver classify (1-line caveman):
  "ลองใหม่ / ไม่ work"   → fix     → reopen bd, iter+1, Phase 2
  "เปลี่ยน X"             → spec    → reopen bd, Phase 1a (Bella/Sara redo)
  "ทำไม Y / ที่นี่ทำไม"   → quest   → answer, no phase change
  "OK / ผ่าน / approve"   → approve → bd close gate check
  "เพิ่ม Z"               → new     → bd create child issue
  "เสร็จยัง"              → status  → bd show, no action
```

ห้าม Dave/Chris/Quinn proceed ก่อน Oliver classify

### M3 — Anti-Puppet "Done" (extend v2.8.1 Anti-Puppet)

| Agent | Can say | Can NOT say |
|-------|---------|-------------|
| Dave | "code edited", "smoke ✓" | "feature done", "ready merge" |
| Chris | "7-dim clean", "unit ≥ 80%" | "ready merge", "ready prod" |
| Quinn | "E2E green", "load p95 ok" | "ready prod" |
| Sentinel | "STRIDE pass", "0 critical" | "secure" (without observability proof) |
| Uma | "UI verdict PASS" | "shipped" |
| **Oliver** | "ready merge" — ต้องมี Chris+Quinn+Sentinel(+Uma) bd notes ครบ | — |
| **Reggie** | "✓ prod stable" — ต้อง SLO 2hr observed | — |

### M4 — User Comment = FAIL by default

```
User comments on agent claim ("ยังไม่ดี" / "ลองใหม่" / "เพิ่มอันนี้"):
  → bd update <id> --notes "user-feedback: <quote>"
  → iter++
  → reopen Phase ที่ feedback ชี้ไป (default = Phase 2)
  → ห้าม close bd ในรอบเดียวกัน
```

ห้าม Dave "OK เพิ่มให้ครับ" → fix ตรง ๆ โดยไม่ผ่าน iter counter

### M5 — Spec change = mandatory bd revision

```
User: "เปลี่ยน amount เป็น decimal"
  ❌ WRONG: Dave fix code ตรง
  ✅ RIGHT:
     Oliver  ▸ Bella  : spec change request
     Bella   → bd create bd-42-r2 (revision)
     Bella ∥ Sara : Phase 1a redo (delta only — light)
     Gate: pre-spec-expand
     Phase 1b → 1c → 2 → 3 → propagate
```

### M6 — Conversation State pin (persistent)

ไฟล์ `outputs/SESSION-STATE.md` (Oliver maintain) — สำคัญสำหรับ warm follow-up:
```
Active Engagement: E-1 "Refund flow"
Active bd issues:
  - bd-42 : state:review-pending  iter:2  last:Chris-3b
  - bd-43 : state:impl             iter:1  last:Dave#2

Last handoff:
  Dave ▸ Verify (bd-42, iter:2)

Pending gates:
  - pre-loop-exit (bd-42) : waiting Quinn + Sentinel notes
```

ทุก agent **read SESSION-STATE first** → ห้าม respond ก่อน

### M7 — Direct-to-agent block

```
User direct ping → Dave (bypass Oliver):
  ❌ WRONG: Dave "OK ครับ" ทำ
  ✅ RIGHT: Dave ▸ "ผมต้อง escalate Oliver ก่อน — message นอก phase context
                   (bd-42 state:review-pending). Classify ก่อน"
  → Oliver ingest, re-classify (M2)
```

ทุก agent ที่ไม่ใช่ Oliver ห้าม accept direct-from-user ใน active engagement — ส่งกลับ Oliver

---

## 🆕 Skills (v3.0 — short names + lazy-load)
