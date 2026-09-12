---
name: bella-producer
description: Reference (lazy-load) ของ Bella — producer runbook Phase 0/1a: Event Storming, RTM via tracker, elicitation process, BRD output format. โหลดเฉพาะตอนทำหน้าที่ producer (ไม่โหลดใน branch review/spec-axis)
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-deliverable/bella-producer.md
WHEN: bella_role=producer (Phase 0/1a — clarifying / BRD / FRD / Event Storming / RTM)
OWNER: business-analyst
REQUIRED-BEFORE: write_brd_or_frd
```

# Bella — producer runbook (Phase 0/1a)

> ย้ายจาก `agents/business-analyst.md` (bd:shode-roadmap/C-G1) — branch review/spec-axis ไม่ใช้ section เหล่านี้
> Clarifying option-style + frontier ฉบับเต็ม → `references/runbooks/oliver-clarify-estimate.md` (canonical เดียว — ห้าม copy กลับ)

## Event Storming (DDD)

Sticky color:
- 🟧 Domain Event (past tense): "Order Placed"
- 🟦 Command (intent): "Place Order"
- 🟨 Actor/Role
- 🟩 Aggregate (consistency boundary)
- 🟪 Policy/Rule
- 🟥 Hotspot (ไม่แน่ใจ)
- 🟫 External System

Flow: Big Picture (event timeline) → Process (add command + actor) → Design (aggregate + bounded context)

Output: timeline, bounded context map, ubiquitous language, hotspots → Sara+Domain

Ubiquitous language lands in the project's `CONTEXT.md` (glossary only; format and
ownership per `shode-house-workflow/harness.md` § Source of truth and host capabilities) — update it the
moment a term is resolved, not in a batch at the end.

## RTM via the confirmed source of truth

Use the mapping confirmed on first project engagement, Markdown fallback. These
CLI examples apply only when that tracker is selected, available and writes are
authorized; inspect its supported commands before use. They are not setup steps.
```bash
bd create "BR-01: refund ภายใน 3 วัน" -t business-req
bd create "FR-101: POST /refund" --blocked-by 1
bd create "TC-33: refund happy path" -t test --blocked-by 2
bd graph --format=mermaid
```

GitHub: `gh issue create -t "BR-01: ..." -l business-req,p1`
Linear: `linear issue create -t "BR-01: ..." -p urgent`
Jira: ใช้ Atlassian MCP (`createJiraIssue`)

**Universal rules** (ตาม meeting skill tracker abstraction):
- BR → ≥1 FR → ≥1 test (link via blocked-by/parent-child)
- Orphan: FR ไม่มี BR = scope creep; BR ไม่มี test = untested
- Keep status/dependencies in the confirmed canonical home, including Markdown
  when selected. Link deliverables; do not create a competing task database.

## Process

1. Discover missing stakeholder/scope/constraint/success decisions; no question quota.
2. Validate against settled evidence; route consequential unresolved decisions through Oliver.
3. Event Storming (complex domain) → bounded context
4. BRD/FRD/Stories
5. RTM linking in the canonical record
6. Gap & risk

## Output Format (BRD)

```markdown
# BRD: [name]

## Executive Summary
## Business Objective (SMART)
## Stakeholders (RACI)
## Scope (in / out)
## Functional Requirements
- FR-001: [Priority] [Description]
  - AC: Given ... When ... Then ...
## NFR (refer Sara)
## Process Flow (Mermaid as-is + to-be)
## Event Storm + Bounded Context + Glossary
## User Stories
## Assumptions / Dependencies / Risks
## RTM (bd link)
## Open Questions
```
