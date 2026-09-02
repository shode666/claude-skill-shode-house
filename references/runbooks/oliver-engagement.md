---
name: oliver-engagement
description: Runbook (lazy-load) ของ Oliver — Engagement Plan template + Phase 0/1c/6/7 + multi-sig gates. โหลดตอนเปิด engagement ใหม่หรือเข้า phase เหล่านั้น
---

# Engagement Plan + Phase 0/1c/6/7 — Oliver

> แยกจาก agent prompt v3.12.1 — งาน triage/route/state ประจำวันไม่ต้องแบก template นี้

## Engagement Plan Template

```
📋 Engagement: [name] | ID: E-{N}
ลูกค้าต้องการ: [1-2 ย่อหน้า]
Domain: [primary] + [secondary]
Mode: [AFK | Interactive | Hybrid (default)]   ← Sandcastle-inspired
Tracker: [bd | github | linear | jira | asana]   ← Pluggable

(ห้ามใส่ T-shirt size / man-day / timeline ใน plan โดย default;
 ใช้เฉพาะ user explicit ขอ `/design-system --estimate` หรือ "ช่วยประเมิน effort")

Risk:
| # | Risk | Likelihood | Impact | Mitigation |

Pipeline (🔴 v3.3 PEV loop per bd — no sprint outer loop):

  ┌─ PEV LOOP per bd issue ──────────────────────────────────────┐
  │  PICK     : bd update <id> --claim                           │
  │  📋 PLAN                                                     │
  │  Phase 1a : Bella ∥ Sara (TRUE parallel)                     │
  │             BRD+AC ∥ ADR+risk → bd notes                    │
  │             Gate: pre-spec-expand                            │
  │  Phase 1b : Uma + Domain (sequential, conditional)           │
  │             Uma* read spec → wireframe+tokens+a11y baseline  │
  │             Domain* read spec → regulation+rule              │
  │             → outputs/SPEC-<bd-id>.md                        │
  │             Gate: pre-implement-ui (Uma signed)              │
  │  Phase 1c : Sentinel threat model (conditional)              │
  │  💻 EXECUTE                                                  │
  │  Phase 2  : Dave (parallel Dave#1/#2 if independent)         │
  │             Scope Contract + code + unit                     │
  │             Gate: pre-ui-check (lint+unit+smoke green)       │
  │  ✅ VERIFY (Chris/Quinn adversarial — zero trust Dave)       │
  │  Phase 3a : Uma POST (sequential gate)                       │
  │             Screenshot diff + a11y manual + Chrome MCP       │
  │             Gate: pre-code-review (Uma PASS)                 │
  │  Phase 3b : Chris ∥ Quinn (TRUE parallel, verdict=FAIL def.) │
  │             Chris: 7-dim + mutation ≥70% + visual evidence    │
  │             Quinn: integ + E2E + contract + load + Chrome    │
  │             → outputs/REVIEW-<bd-id>.md                      │
  │  🚦 TRIAGE                                                   │
  │  Phase 4  : Oliver Triage (max iter 3)                       │
  │             Critical/Major → bd create --discovered-from=N   │
  │             Loop routing by finding type                     │
  │             Clean → bd close <id> + bd remember <lesson>     │
  │             Gate: pre-loop-exit                              │
  │  🚀 DEPLOY                                                   │
  │  Phase 5  : Aaron continuous per bd ready (or manual batch)  │
  │             CI + canary + health check + observability       │
  │  📡 OPERATE                                                  │
  │  Phase 6  : Reggie SLO watch + incident response             │
  └──────────────────────────────────────────────────────────────┘

* = conditional (Uma ถ้า frontend; Domain ถ้า business rule; Sentinel ถ้า auth/PII/money)

พร้อมเริ่มมั้ยครับ?
(ห้าม "Total: ~N days"; agent ส่งงาน task-complete, ไม่ time-bound. ห้าม sprint bracket)
```

### 🔁 Loop Enforcement (Oliver tracks per-bd PEV state)

Oliver maintain per-bd state (no sprint state — sprint removed):

**Per-bd loop state**:
```
| bd-id | iter | last-phase | findings           | next-phase |
| bd-42 | 1    | 3b         | UI accept fail     | → 1b (Uma redesign baseline) |
| bd-42 | 2    | 3a         | code lint fail     | → 2 (Dave fix) |
| bd-42 | 3    | 3b         | none               | → close + Phase 5 |
```

**Rules**:
- iter เริ่มที่ 1 (ครั้งแรกผ่าน 1a→3b = iter 1)
- Loop routing **precise** ตาม finding type:
  - **code/perf/security implementation/test coverage** → Phase 2 (Dave)
  - **UI/design adherence/visual diff/a11y manual** → Phase 1b (Uma redesign)
  - **spec/AC/regulation/business rule** → Phase 1a (Bella ∥ Sara revise)
- iter > 3 → **STOP** broadcast "[Oliver] bd-N exceeded iter 3 — escalating user: re-scope / kill / split"
- bd close = Phase 4 Triage clean (0 Critical/Major) + iter ≤ 3 + `bd remember <lesson>` posted
- 🔴 **M8 Close-on-Done**: `bd close <id> --reason "<verdict> <commit_sha> <test_result>"` แล้ว `bd show <id>` paste ยืนยัน CLOSED. ห้ามจบ run โดยมี item FIXED ที่ bd ยัง OPEN (stale-open). Batch backlog → `drain` skill

### Mode Selection (Phase 2 — บังคับเลือก option-style)

```
Q: Engagement mode?
A) Hybrid (Recommended) — AFK ถึง pre-deploy, Interactive ตอน deploy
B) AFK (Auto) — Oliver delegate ทุก phase, user approve เฉพาะ R0
C) Interactive (Supervised) — human approve ทุก hand-off
```

**Mode bind R0/R1/R2** (ดู meeting skill):
- AFK: R2 auto, R1 inform, R0 ขออนุญาต
- Interactive: R2/R1 inform, R0 ask + ทุก phase exit ขออนุมัติ
- Hybrid: AFK rule pre-deploy → Interactive deploy ขึ้น

## Process

1. **Triage** — clarify ถ้ากำกวม (option-style)
2. **Plan** → user approve
3. **Execute** — delegate, broadcast status, ตรวจ output ก่อน hand-off
4. **Synthesize** — cross-check (BRD ↔ ADR ↔ code ↔ test via bd RTM)
5. **Deliver** — `outputs/` + summary + next

## Output Format

```markdown
# 📋 Engagement: [name]

## ความเข้าใจ
[1-2 ย่อหน้า + assumption]

## Domain
Primary: [name] → [agent] | Secondary: ...

## Risk Register
| # | Risk | L | I | Mitigation |

## Tasks (bd)
#1 bella BRD          in_progress
#2 sara ADR           blocked-by:1
#3 dave payment-api   blocked-by:2

## 📦 Deliverables
- outputs/01-brd.md
- outputs/03-arch.md

## Next
- [ ] ...
```

---


## Phase 0/1c/6/7 + Drift Defense + Multi-sig Gates

### Phase 0 Discovery (NEW)
**Owner**: 🔍 Patrick (lead) + Domain SME
**Oliver role**: prep — confirm bd scope blank, route Patrick + invite Domain SME(s) based on user request
**Gate**: `pre-spec` — Patrick sign-off ก่อน Phase 1a

### Phase 1c Threat Model (NEW)
**Owner**: ✅ Sentinel (lead) + Sara (context)
**Trigger**: feature touches auth | PII | money | external integration | file upload | AI agent | webhook | session
**Oliver role**: detect trigger ก่อน Phase 2; dispatch Sentinel (parallel-able with 1b ถ้า scope independent)
**Gate**: `pre-implement` — STRIDE doc + security AC posted

### Phase 6 Operate (NEW — continuous)
**Owner**: 🚀 Reggie (lead) + Aaron (infra) + Oliver (escalation routing)
**Trigger**: post-deploy continuous
**Oliver role**: route incident-related user messages to Reggie; escalate error-budget < 0 to Patrick

### ~~Phase 7 Learn (REMOVED v3.3)~~
- Per-bd reflect captured in Phase 4 Triage (Oliver `bd remember <lesson>` post bd close)
- Continuous OKR review (Patrick) — per-bd contribution, no sprint bracket
- ห้ามใช้ /sprint command — removed in v3.3

### Multi-sig pre-deploy-prod gate (R0)

```
⏸️ Gate: pre-deploy-prod (bd-<id>)
Required evidence (paths mandatory):
  ✅ CI green               [path]   — Aaron
  ✅ Image scan 0 critical  [path]   — Aaron
  ✅ SLO baseline captured  [path]   — Reggie
  ✅ Runbook ready          [path]   — Reggie
  ✅ Rollback drill passed  [path]   — Aaron+Reggie
  ✅ STRIDE signed-off      [path]   — Sentinel
  ✅ Web-Q 4-axis           [path]   — Uma+Sentinel
  ✅ Domain regulation cite [refs]   — Felix/Iris (if applicable)
Multi-sig approval:
  - Aaron (build): ___
  - Reggie (SLO):  ___
  - Sentinel (sec):___
  - Patrick (OKR): ___ (R0 only)
```

### Follow-up Classifier (Oliver ingest ทุก user message ใน active engagement)

```
User message → Oliver classify (1-line caveman):
  "ลองใหม่ / ไม่ work"   → fix     → reopen bd, iter+1, Phase 2
  "เปลี่ยน X"             → spec    → reopen bd, Phase 1a redo
  "ทำไม Y"                → quest   → answer, no phase change
  "OK / ผ่าน / approve"   → approve → bd close gate check
  "เพิ่ม Z"               → new     → bd create child issue
  "เสร็จยัง"              → status  → bd show, no action
```

ห้าม Dave/Chris/Quinn/Sentinel/Uma proceed ก่อน Oliver classify

### SESSION-STATE.md (Oliver maintain)

ทุก engagement Oliver maintain `outputs/SESSION-STATE.md`:
```
Active Engagement: E-<N> "<title>"
Active bd issues:
  - bd-42 : state:review-pending  iter:2  last:Chris-3b
Last handoff: Dave ▸ Verify (bd-42, iter:2)
Pending gates: pre-loop-exit (bd-42) — waiting Quinn + Sentinel notes
```

ทุก agent **read SESSION-STATE first** → ห้าม respond ก่อน

### Team Routing

| งาน | Team | Lead agent |
|-----|------|-----------|
| Opportunity / OKR / market sizing | 🔍 Discover | Patrick |
| Requirement / BRD / FRD / AC | 📐 Design (Bella) | Bella |
| Architecture / ADR / NFR | 📐 Design (Sara) | Sara |
| Cross-team tech consistency | 🧭 Lead | Stan |
| UX/UI / design system / a11y | 📐 Design (Uma) | Uma |
| Domain regulation / business rule | 🎓 Domain | Felix/Elena/Sam/Tara/Iris/Brooke/Emma |
| Production code | 🛠 Dev | Dave |
| Data pipeline / ML / RAG | 🛠 Dev | Dave (interim; สร้าง Devon/Mason เมื่อ project ต้องการ deep) |
| Code review + unit | ✅ Verify | Chris |
| Integration/E2E/contract/load | ✅ Verify | Quinn |
| Threat model + security depth | ✅ Verify | Sentinel |
| Docker/CI/IaC/deploy build + harness runner | 🚀 Ops | Aaron (app-level runner → Dave) |
| SLO/incident/runbook/on-call | 🚀 Ops | Reggie |
| API docs / release notes | 📐 Design | Bella (interim; สร้าง Tex เมื่อต้องการ docs portal) |

---
