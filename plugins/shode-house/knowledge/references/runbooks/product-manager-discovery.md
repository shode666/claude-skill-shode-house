---
name: product-manager-discovery
description: Reference (lazy-load) for product-manager - ownership vs business-analyst, deliverables, escalation, KPIs, anti-patterns, Phase 0 process and pre-spec gate, continuous review, RICE/OKR templates and evidence examples. Load before Phase 0 work.
---

```lazy-load-contract
LOAD: references/runbooks/product-manager-discovery.md
WHEN: phase=0 OR task in {okr,roadmap,prioritization,kill_decision}
OWNER: product-manager
REQUIRED-BEFORE: phase0_output_written
```

# product-manager - discovery method

**Contents**

- [🎯 Sole Owner (zero overlap — vs business-analyst)](#-sole-owner-zero-overlap--vs-business-analyst)
- [5-Dim Role](#5-dim-role)
- [Bias checks](#bias-checks)
- [Phase 0 — Discovery](#phase-0--discovery)
- [Continuous Review](#continuous-review)
- [RICE Template](#rice-template)
- [Evidence Protocol](#evidence-protocol)
- [Discipline](#discipline)

> Lazy reference for `product-manager`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.

- ❌ Frequency/severity numbers = guessed → cite source หรือ flag `ESTIMATE — needs domain confirm`

## 🎯 Sole Owner (zero overlap — vs business-analyst)

| product-manager ทำ (Why + What) | business-analyst ทำ (How requirement captured) |
|-------------------------|-------------------------------------|
| OKR + KR per quarter | BRD with FR/NFR |
| User research / interview / persona | User stories + AC G-W-T |
| Opportunity sizing (TAM/SAM/SOM) | Process flow (BPMN, swim lane) |
| RICE / WSJF / Kano prioritization | RTM (BR → FR → test) |
| Roadmap (now/next/later) | Event Storming |
| Stakeholder negotiation | — |
| Kill decision (feature/spike) | — |
| Pricing / monetization | — |

## 5-Dim Role

### 1. PRIMARY DELIVERABLE
- `OKR-<Q>.md` — quarterly objectives + key results
- `opportunity-<feature>.md` — TAM/SAM/SOM + ICP + pain validation
- `prioritization-<date>.md` — RICE scored backlog (continuous, not sprint-bound)
- `roadmap.md` — now / next / later
- `kill-decisions.md` — features killed + reason

### 3. ESCALATION PATH
- Engineering capacity short → escalate the router (workflow) + staff-engineer (tech depth tradeoff)
- Reliability tradeoff → joint sre-engineer (error budget conversation)
- Repeated kill (3+ feature ใน quarter) → re-OKR conversation

### 4. KPIs
- OKR attainment ≥ 70% (Google standard)
- Feature kill rate < 30% (too high = bad discovery; too low = no rigor)
- Time to first prototype on new opportunity < 2 sprints
- Stakeholder NPS ≥ 8
- Engineering uptake of prioritization > 90% (low = team ignoring PM)

### 5. ANTI-PATTERNS (refuse)
- Settle necessary kill criteria before dependent work; reuse authorized product decisions
- "OKR ทำตามที่ stakeholder พูด" — refuse, OKR ต้องอิง user pain + business outcome
- "Worry about reliability later" — refuse, joint sre-engineer ก่อน

## Bias checks
- ห้าม yield to stakeholder "เราลงทุนไปเยอะแล้ว" — RICE recalc with current data only
- OKR shift ก็ kill criteria ต้อง shift — ห้าม anchor บน original OKR ถ้า context เปลี่ยน

## Phase 0 — Discovery

### Process
1. **Pain validation** with Domain SME (fintech-expert/erp-expert/sap-expert/trading-expert/insurance-expert/booking-expert/ecommerce-expert):
   - Real pain? Frequency? Severity? Existing workaround?
2. **Opportunity sizing**:
   - TAM (total addressable) / SAM (serviceable) / SOM (obtainable share, year 1)
   - Unit economics: revenue per user × addressable users − cost
3. **ICP** (Ideal Customer Profile):
   - Persona + JTBD (Job-To-Be-Done) + buying trigger
4. **RICE score**:
   - **R**each × **I**mpact × **C**onfidence ÷ **E**ffort
   - High = top priority
5. **Kill criteria** (define ก่อนเริ่ม):
   - "Kill if X metric < Y by date Z"
6. Output: `outputs/opportunity-<feature>.md` → business-analyst inherits for Phase 1a

### Phase 0 Gate: `pre-spec` (when discovery is required by the engagement)
- ✅ Pain validated by Domain SME (real, not assumed)
- ✅ Opportunity sized (numbers, not vibes)
- ✅ Priority justified against the agreed objective; RICE when used by the project
- ✅ Kill criteria documented
- ✅ solution-architect light feasibility (1-line: doable in current arch?)

## Continuous Review

### Continuous review (per bd, not sprint)
- OKR progress vs target — recalc when a task closes (key result % attained, per-bd contribution)
- Kill review — flag when bd data drops below kill criteria threshold
- RICE recalibration — based on actual outcome vs projection
- Tech debt RICE — engineering raises, product-manager prioritizes (continuous queue)

### Periodic review (cadence = user discretion — typically monthly)
- Roadmap update (move now/next/later based on learnings)
- Capacity vs commitment (the router provides actuals)
- Error budget conversation (sre-engineer joint)
- Stakeholder report (1-pager)

## RICE Template

```
Feature: <name>
- Reach: <N> users/month
- Impact: 3 (massive=3, high=2, medium=1, low=0.5)
- Confidence: 80% (high=100, medium=80, low=50)
- Effort: 5 (relative; split into tasks, never person-weeks)
Score: (N × 3 × 0.8) / 5 = ...
```

OKR format: Objective <Q>: <outcome> / KRn: <metric> <baseline> → <target> (measured: <source>)

## Evidence Protocol

```
✅ "[Opportunity: outputs/opportunity-refund.md] TAM=฿1.2B SAM=฿180M SOM=฿24M y1; ICP validated by fintech-expert"
✅ "[Kill: kill-decisions.md] killed dashboard-v2 — RICE 8 (low impact + high effort); reallocate effort to refund"
❌ "feature สำคัญ" (no number, no comparison, no validation)
```

## Discipline

- Commit scope from decision evidence; reuse discovery and apply the harness tier
- ห้าม OKR ที่ไม่ measurable (KR ต้องมี metric + target + measurement source)
- Importance claims need evidence; use RICE for unresolved prioritization
- ห้าม backlog ที่ไม่ได้ ranked (priority unclear = team ignore)
