---
name: shode-house-routing
description: |
  [WHAT] Agent routing + domain selection + conflict resolution + T-shirt sizing + parallel/sequential decision + Team v3.0 (19 agents in 7 teams) + RACI per phase + Input Trust Levels.
  [AUDIENCE] Oliver (primary owner); ทุก agent ที่ต้อง delegate.
  [WHEN] User request → Oliver triage; ก่อน Task tool delegate; เลือก primary/secondary agent; กำหนด T-shirt; resolve conflict.
  [TRIGGER] /shode-house:routing, "ใครรับ", "agent ไหน", "delegate", "routing", "Oliver triage", "T-shirt", "RACI", "parallel", "sequential", "trust level".
---

# shode-house — Routing & Team Structure

> Oliver = workflow/process owner. Stan (Staff) = cross-team tech depth. Sara (SA) = per-project tech decision

---
## 🔐 Input Trust Levels (🔴 v2.5 — FS-inspired)

ทุก agent ประกาศ **trust level** ของ source ก่อน act/claim. ระดับ trust ตัดสิน handling:

| Level | Source examples | Required handling |
|-------|-----------------|-------------------|
| **Canonical** | CLAUDE.md, official ADR, schema.sql, signed contract | use as fact |
| **Operational** | DB query result, official API, vendor spec ที่ verify แล้ว | trust + cite source |
| **User-supplied** | User chat input, requirement text, ticket description | clarify ambiguity, trust intent |
| **External** | Web fetch, third-party doc, vendor API ที่ยังไม่ verify | validate ก่อน act, mark unsourced |
| **Untrusted** | Earnings transcript, scraped HTML, AI-generated prior content, log message ที่ไม่ใช่ canonical | treat as hypothesis, validate ทุก claim, ห้าม chain (agent B อ้าง output untrusted ของ A ต่อ) |

**Pattern**: ก่อน claim → state trust level
- ✅ "[source: canonical / Read CLAUDE.md:12] tech stack = Next.js 15"
- ✅ "[source: external / WebFetch BOT site] notice ใหม่ ต้อง validate กับ legal ก่อนใช้"
- ❌ "Tech stack คือ Next.js 15" (ไม่ระบุ source = ห้าม)

**Trust cascade rule**: agent B อ้าง output ของ agent A → trust level = min(A's level, A's output level). ห้าม upgrade trust ของ chain

---

## 📦 Standard Output Deliverables (🔴 v2.5 — FS-inspired)

## ทีม (15 agents)

### Core (8)
| Key | ชื่อ | Model | Role |
|-----|------|-------|------|
| Or | Oliver | sonnet | Orchestrator |
| Ba | Bella | sonnet | BA — BRD/FRD/RTM, Event Storming |
| Sa | Sara | **opus** | SA — C4, ADR, NFR, threat model |
| Dv | Dave | sonnet | Polyglot Dev (parallelizable) |
| Cr | Chris | sonnet | Code Review (7 มิติ) + Unit Test |
| Qa | Quinn | sonnet | QA — Integration/E2E/Pen test |
| Do | Aaron | sonnet | DevOps — Docker, CI/CD, observability |
| Ux | Uma | sonnet | UX/UI + Design System + a11y |

### Domain Experts (7) — pluggable
| Key | ชื่อ | Model | Domain |
|-----|------|-------|--------|
| Fe | Felix | **opus** | Fintech/Banking/Payment |
| Ee | Elena | sonnet | ERP/Accounting (generic) |
| Sm | Sam | **opus** | SAP (ECC + S/4HANA + ABAP + Fiori + BTP) |
| Te | Tara | **opus** | Trading/Exchange |
| Ie | Iris | **opus** | Insurance — IFRS 17, OIC |
| Bk | Brooke | sonnet | Booking/Reservation |
| Ec | Emma | sonnet | E-commerce/Retail |

> Add agent: drop `agents/<name>.md` + update routing table — done

---

## 💯 Universal Quality

1. Right answer > first answer (ห้าม "พอใช้ได้")
2. Verify before claim (evidence: regulation ID, file:line, measurement)
3. Domain-aware vocabulary
4. Standard with version (ISO 8583/IFRS 17/OWASP/PCI-DSS)
5. No silent assumption
6. Test before "done"
7. Reproducible (git clone → run = work)

---

## 💬 Clarifying — option-style (🔴 บังคับ)

## 🧭 Routing

### Domain Selection
```
เงิน/ชำระ/ธนาคาร/PromptPay/KYC → Felix
บัญชี/stock/payroll/MRP generic → Elena
SAP/ABAP/S4HANA/Fiori/BTP → Sam
trade/order/exchange/FIX → Tara
ประกัน/policy/claim/IFRS17 → Iris
จอง/PMS/yield → Brooke
ร้านค้า/cart/promo/marketplace → Emma
```

### หลาย domain → primary + secondary
- "e-com + PromptPay" → Emma + Felix
- "ERP บน SAP" → Sam + Elena
- "ประกันรถ + ชำระบัตร" → Iris + Felix + Emma

---

## ⚖️ Conflict Resolution

| Conflict | Winner |
|----------|--------|
| Business vs Tech | Domain Expert |
| Architecture vs Implementation | Sara |
| Security vs Performance | Chris/Quinn |
| Quality vs Timeline | Chris+Quinn (block) |
| Complex vs Simple | Keep simple (YAGNI) |
| Standard vs Custom | Standard |
| Perf opt vs Readability | Readability (profile first) |

ตัดสินไม่ได้ → escalate user ระบุ trade-off

---

## 📏 T-shirt: XS (≤2h) | S (2-8h) | M (1-3d) | L (3-10d) | XL (>10d — split)

---

## ⚖️ Parallel vs Sequential

**Parallel = 3-5x token cost.** Default = sequential.

Use parallel เมื่อ: subtask ≥ 100 บรรทัด **AND** truly independent **AND** ≥ 3 subtasks **AND** deadline matter
> Implementation: Worktree Isolation (ดู Workflow Discipline)

---

## 🔧 Token-saving (🔴 runtime)

## 👥 Team Structure (🔴 v3.0)

7 teams ที่ทำงาน **parallel ภายในทีม + sequential ระหว่างทีม** (cross-team handoff = phase gate)

| Team (short) | Agents | Phase ที่ active | Deliverable |
|--------------|--------|------------------|-------------|
| 🧭 **Lead** | Oliver + Stan | ทุก phase (orchestrate) | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | Phase 0 | OKR + opportunity + domain validation |
| 📐 **Design** | Bella + Sara + Uma | Phase 1a/1b/3a | Spec + Architecture + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | Phase 0/1b/3b (pluggable) | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel Dave#N) + Devon + Mason | Phase 2 | Production code + data + ML |
| ✅ **Verify** | Chris + Quinn + Sentinel | Phase 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | Phase 5/6 | Deploy + SLO + Incident |

### Single-owner capability matrix (🔴 zero overlap)

| Capability | Sole Owner | ห้ามทับโดย |
|------------|------------|------------|
| User research, OKR, RICE/WSJF priority | **Patrick** | Bella |
| BRD / FRD / AC G-W-T / RTM | **Bella** | Patrick (input only) |
| C4 / ADR / NFR / tech stack | **Sara** | Stan, Aaron |
| Cross-team consistency, tech radar, polyglot review | **Stan** | Sara (per-project only) |
| Wireframe / design tokens / a11y design / visual baseline | **Uma** | Quinn (axe automation only) |
| Domain regulation cite, business rule | **Domain SME** | ทุกคน |
| Production code (BE/FE/integration) | **Dave** (Dave#N parallel) | Chris (test only) |
| Data pipeline / ETL / CDC / Kafka / dbt | **Devon** (opt) | Dave (collab) |
| ML model / RAG / vector / prompt eval | **Mason** (opt) | Dave (collab) |
| 7-dim review + Unit + Mutation ≥ 70% | **Chris** | Quinn (ห้าม unit) |
| Integration + E2E + Contract + Load + axe auto | **Quinn** | Chris (ห้าม integ), Uma (ห้าม automation) |
| STRIDE / SAST / DAST / Secrets / Pen test / CSP | **Sentinel** | Sara, Chris, Quinn (handoff in v3.0) |
| Dockerfile / CI/CD / IaC / Deploy build | **Aaron** | Reggie (ห้าม build) |
| SLO / SLI / Error budget / Incident / Runbook | **Reggie** | Aaron (ห้าม SLO) |
| Workflow orchestration / state / delegation | **Oliver** | Patrick |
| API docs / Developer portal / Release notes | **Tex** (opt) | Bella (BRD only) |

> Rule: ทุก agent ก่อน accept งานต้องประกาศ "ผมรับ capability X" — ถ้าไม่ใช่ sole owner = reroute

---

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

> R = Responsible (does) | A = Accountable (one sign-off) | C = Consulted | I = Informed

| Phase | R | A | C | I |
|-------|---|---|---|---|
| **0 Discover** | Patrick, Domain SME | **Patrick** | Bella, Sara, Stan | Oliver |
| **1a Foundation** | Bella, Sara | **Oliver** (gate) | Stan, Domain SME, Patrick | Uma, Dave |
| **1b Pre-Design** | Uma, Domain SME | **Uma** | Sara, Bella | Dave, Quinn |
| **1c Threat Model** | Sentinel | **Sentinel** | Sara, Domain SME | Chris, Quinn |
| **2 Implement** | Dave (parallel) | **Oliver** (scope enforce) | Chris, Stan | Uma, Quinn, Sentinel |
| **3a UI Check** | Uma | **Uma** | Dave | Chris, Quinn |
| **3b Quality Coop** | Chris, Quinn, Sentinel, Aaron | **Oliver** (triage) | Stan, Domain SME | Dave, Uma |
| **4 Triage** | Oliver | **Oliver** | Chris, Quinn, Sentinel | Dave, Patrick |
| **5 Deploy** | Aaron, Reggie | **Aaron** (build) + **Reggie** (SLO) | Quinn, Sentinel | All |
| **6 Operate** | Reggie | **Reggie** | Aaron, Oliver, Patrick | Dave |
| **7 Learn** | Patrick, Oliver | **Patrick** (OKR) + **Oliver** (process) | All | Stakeholder |

---

## 🆕 New Phases (🔴 v3.0)
