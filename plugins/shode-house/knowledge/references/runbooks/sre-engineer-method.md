---
name: sre-engineer-method
description: Reference (lazy-load) for sre-engineer - ownership table, deliverables, escalation routes, KPIs, burn-rate math, incident steps, postmortem pointer, evidence examples and hand-off lines. Load before SLO, incident or postmortem work.
---

```lazy-load-contract
LOAD: references/runbooks/sre-engineer-method.md
WHEN: task in {slo,incident,postmortem,on_call,capacity}
OWNER: sre-engineer
REQUIRED-BEFORE: sre_deliverable_written
```

# sre-engineer - method

> Lazy reference for `sre-engineer`: method moved out of the agent body (v4 W5b). It supplies method, never authority; decision rights, refusals, the pre-deploy-prod checklist and safety lines stay in the agent body.

## 🎯 Sole Owner (zero overlap)

| Capability ผมเป็นเจ้าของคนเดียว |
|--------------------------------|
| SLI definition (latency p95/p99, availability, error rate, throughput) |
| SLO target + error budget per service |
| Runbook per critical alert |
| On-call rotation + handoff doc |
| Blameless postmortem |
| Observability deep config (Prom/OTel/Grafana dashboards) |
| Incident commander role |
| Capacity planning + load forecast |

devops-engineer ยังคงเป็น Platform/DevOps (Docker, CI/CD, IaC, deploy build): sre-engineer keeps cars running, devops-engineer builds the road.

## PRIMARY DELIVERABLE
- `slo-<service>.yml` (SLI definition + SLO target + error budget formula)
- `runbook-<alert>.md` (symptom → diagnosis → mitigation → escalation)
- `postmortem-<incident>.md` (timeline + root cause + 5-why + action items)
- `oncall-schedule.md` (rotation + handoff template)
- Grafana dashboard JSON per service (paste path)

## Escalation routes
- Repeated root cause in code → escalate **code-reviewer** (review fix quality)
- Repeated root cause in architecture → escalate **solution-architect** (rethink)
- Capacity exhaustion → escalate **devops-engineer** (scale) + **product-manager** (growth assumption)
- SLO ที่ไม่ได้ negotiate กับ Product — escalate product-manager

## KPIs
- SLO attainment ≥ 99.5% rolling 30d
- MTTR P0 < 30 min, P1 < 2 hr
- Postmortem published < 5 business days post-incident
- Runbook coverage 100% of critical alerts
- Toil ≤ 50% of SRE time (Google SRE definition)

## Anti-patterns (method)
- Postmortem with named blame — rewrite blameless

## Phase 5 — Deploy (co-owner with devops-engineer)

```
devops-engineer build + canary → sre-engineer SLO check → joint approve → 100%
```

## Phase 6 — Operate (continuous post-deploy)

### SLO burn rate watch (continuous)
```
burn rate = actual error ratio over window / (1 - SLO target)
1x = consuming budget at SLO pace (normal)
2x = double the allowed error rate
14x sustained uses a full 30-day budget in 30/14 ≈ 2.14 days
```
Source: [Google SRE](https://sre.google/workbook/alerting-on-slos/). Use adopted alert windows/thresholds; exhaustion time depends on remaining budget.

- Support tickets +30% / p99 > SLO → investigate and apply adopted incident criteria

### Incident response (when burn rate paging)
1. **Acknowledge** within 5 min (P0) / 15 min (P1)
2. **Triage** in 15 min — assemble war room (sre-engineer IC + devops-engineer infra + security-engineer if sec)
3. **Mitigate** ก่อน "fix" — rollback / scale / circuit break / feature flag off
4. **Communicate** every 30 min in war room channel
5. **Resolve** when SLO returns to normal
6. **Postmortem** within 5 business days

### Postmortem template (blameless)
Load `shode-house:incident` § Postmortem template (blameless) — the single canonical template (summary · UTC timeline · 5-why root cause · went well/poorly · action items with owner + due + tracked item).

## ห้าม (method)

- ห้ามใช้ "average latency" — p50/p95/p99 เท่านั้น (avg ปกปิด long tail)
- ห้าม alert ที่ไม่มี action (alert = "do something now"; ไม่ใช่ FYI)

## Domain Evidence Protocol — SRE

```
✅ "[SLO: slo-payment.yml] target=99.9% (43m budget/30d); actual=99.92% (35m used)"
✅ "[Grafana: dashboard-id=payment-overview] p95=180ms (target<200)"
✅ "[Postmortem: postmortems/2026-05-22-payment.md] root=DB connection pool exhaustion"
✅ "[Runbook: runbooks/payment-high-error.md] verified during incident 2026-05-22"
✅ "[Burn rate alert: cw-alarm-id] fired at HH:MM, ack HH:MM (5 min)"
❌ "service ok" (no metric)
❌ "incident resolved" (no MTTR, no root cause)
```

## Handoff

```
devops-engineer ▸ sre-engineer : staged (bd-42, image scan ✓)
sre-engineer    ▸ the router   : prod stable, SLO green (bd-42)
```
