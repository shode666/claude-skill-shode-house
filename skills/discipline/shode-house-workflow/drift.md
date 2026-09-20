---
name: drift
description: Reference (lazy-load) ของ `shode-house-workflow` — Drift Defense detail: M3 Anti-Puppet "Done" table, M6 conversation state pin, M8 Close-on-Done procedure, phase notes 0/6/7. Detection rules M2/M4/M5/M7 อยู่ใน SKILL.md root
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-workflow/drift.md
WHEN: drift_detected=true OR done_claim_disputed=true OR state_recovery=true OR task_close=true
OWNER: orchestrator
REQUIRED-BEFORE: claim_done_or_close_task
```

# Workflow Drift Defense — detail (M3 · M6 · M8 + phase notes)

> v3.0 invariants ที่ Oliver enforce ทุก message. ขาด mechanism ไหน = workflow drift จะกลับมา

### M1 — Ingress Guard → ย้ายไป `shode-house-discipline` § M1

M1 บังคับที่ **ทุก agent** ไม่ใช่แค่ Oliver → ย้ายเข้า skill ที่ทุก agent preload เพื่อการันตีว่าถึงจริง
`shode-house-workflow` = **M2–M7 (Oliver enforcer)** เท่านั้น

### M3 — Anti-Puppet "Done" (extend v2.8.1 Anti-Puppet)

| Agent | Can say | Can NOT say |
|-------|---------|-------------|
| Dave | "code edited", "smoke ✓" | "feature done", "ready merge" |
| Chris | "7-dim clean", "unit ≥ 80%" | "ready merge", "ready prod" |
| Quinn | "E2E green", "load p95 ok" | "ready prod" |
| Sentinel | "STRIDE pass", "0 critical" | "secure" (without observability proof) |
| Uma | "UI verdict PASS" | "shipped" |
| **Oliver** | "ready merge" only with applicable independent reviews and triggered experts per harness tier, current evidence and merge authority | — |
| **Reggie** | "✓ prod stable" — ต้อง SLO 2hr observed | — |

### M6 — Conversation State pin (persistent)

Oliver maintain current checkpoint ใน record ที่ project ยืนยันตาม `shode-house-workflow/harness.md`. ตัวอย่าง Markdown ต่อไปนี้ไม่บังคับสร้าง `outputs/SESSION-STATE.md` ซ้ำ:
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

ทุก agent อ่าน current task record ที่ Oliver ส่งมาและ artifacts ที่เกี่ยวข้องก่อนลงมือ; ไม่บังคับโหลด checkpoint ทุก task หรือ history ทั้งหมด

### M8 — Close-on-Done Guard (ปิดช่อง stale-open)

> **Measured failure mode**: งานเสร็จจริง (merged / test green / verdict PASS) แต่ bd ค้าง OPEN — backlog โกหก, รอบถัดไปทำซ้ำ

```
Beads example, only when the project has selected Beads:
  1. bd close <id> --reason "<verdict> <commit_sha> <test_result>"
  2. bd show <id>            → ต้องอ่านได้ว่า CLOSED
  3. paste output ของข้อ 2   → หลักฐาน ไม่ใช่คำพูดของ agent
```

| Agent | Can say | Can NOT say |
|-------|---------|-------------|
| **Oliver** | "bd-42 CLOSED [paste `bd show`]" | "ปิด bd แล้ว" / "เคลียร์ backlog แล้ว" (ไม่มี output) |
| Dave/Chris/Quinn | "verdict FIXED, sha a1b2c3d, 214 passed" | "ปิด bd ให้แล้ว" (close = Oliver Phase 4 เท่านั้น) |

For any tracker, Oliver updates the canonical task after required acceptance and
authorized closure, then reads it back. Record the revision and actual evidence.
Unavailable remote updates remain pending sync; never create a parallel tracker
or claim CLOSED without the authoritative result.

**ห้าม**:
- ❌ claim task closure when the selected record was not updated and verified
- ❌ close without the applicable revision, verification and reason
- ❌ close `PARTIAL` / `BLOCKED` ให้ตัวเลขสวย — **คง OPEN + note ตรงไปตรงมา**
- ❌ เชื่อ `bd list` เป็นหลักฐานสถานะ — `bd show` เท่านั้นที่ trust ได้

**Batch / backlog run** (หลาย item รอบเดียว) → ใช้ `drain` skill; Step 5 = close-on-done + `bd show` verify ทุก item

## 🆕 New Phases (🔴)

### Phase 0 — Discovery (NEW)
- **Owner**: 🔍 Discover Team (Patrick + Domain SME)
- **Trigger**: New initiative, no bd issue yet (continuous — not sprint-bound)
- **Output**: OKR + opportunity sizing + RICE/WSJF priority + Domain pain validation
- **Gate**: `pre-spec` — sign-off ก่อน Phase 1a Foundation
- **Why**: validate the opportunity before speculative specification work

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
