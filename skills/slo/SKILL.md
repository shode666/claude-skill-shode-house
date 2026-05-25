---
name: slo
description: |
  ใช้เมื่อ Reggie กำหนด SLI/SLO/error budget, capacity planning, observability, หรือ user mention "SLO", "SLI", "error budget", "p95", "availability target", "burn rate" — บังคับ measured SLO + error budget formula + Grafana dashboard
---

# SLO (Service Level Objective discipline)

> **Owner**: Reggie (sole). Co-pilot: Aaron (infra metric scrape), Patrick (error budget conversation)

## หลักการ (Google SRE Book)

1. **SLI** = วัดของจริง (latency p95, availability ratio, error rate)
2. **SLO** = เป้าหมายที่ user คาดหวัง (≥ 99.9% availability rolling 30d)
3. **Error Budget** = (1 - SLO) × time period (0.1% × 30d = 43.2 min)
4. **Burn Rate** = error per hour ÷ acceptable error per hour (1x = on pace; 14x = exhaust in 1d)

## SLI menu (ทำ less ดีกว่า more)

| Service type | Critical SLI |
|--------------|--------------|
| **Request-driven** (API) | Availability ratio, Latency (p95/p99), Error rate |
| **Pipeline** (data/batch) | Freshness, Throughput, Correctness ratio |
| **Storage** | Availability, Durability (≥ 11 nines), Throughput |
| **Async/queue** | Lag, Throughput, Error rate |

> 3-5 SLI per service พอ. มากกว่านี้ = noise

## SLO target (defaults — adjust per business)

| Tier | Availability | Latency p95 | Error rate |
|------|--------------|-------------|------------|
| Critical (payment/auth) | 99.95% | < 200ms | < 0.05% |
| Standard (core API) | 99.9% | < 500ms | < 0.1% |
| Best-effort (internal) | 99.5% | < 1s | < 1% |

## SLO definition file template

```yaml
# slo-payment.yml
service: payment-api
owners: [Reggie, Aaron]
slis:
  availability:
    sli: success_count / total_count
    measurement_window: 30d_rolling
  latency_p95:
    sli: histogram_quantile(0.95, http_request_duration)
    measurement_window: 30d_rolling
slos:
  - sli: availability
    target: 99.95  # %
    error_budget: 21.6  # min/30d
  - sli: latency_p95
    target: 200  # ms
    consequence_if_breach: page_oncall_after_5m
alerts:
  burn_rate_1h:
    expression: burn_rate(availability, 1h) > 14
    severity: P0
    runbook: runbooks/payment-availability.md
```

## Burn rate alert (Google multi-window pattern)

| Window | Burn rate | Severity | Why |
|--------|-----------|----------|-----|
| 1h | > 14x | **P0 page** | Exhaust monthly budget in 1d if continues |
| 6h | > 6x | **P1 page** | Exhaust in 4d |
| 24h | > 3x | P2 ticket | Exhaust in 10d (trend concern) |
| 72h | > 1x | Slow burn warning | Trend over week — investigate |

## Error budget policy (negotiate with Patrick)

| Budget remaining | Policy |
|-----------------|--------|
| > 75% | Normal — feature dev OK |
| 50-75% | Caution — extra review on risky changes |
| 25-50% | Slow down — pause low-priority risky features |
| < 25% | **Freeze** — only reliability work + critical bugfix |
| < 0% (negative) | Hard freeze — Patrick conversation about scope cut |

## Observability stack (Reggie config)

| Layer | Tool | Output |
|-------|------|--------|
| Metric | Prometheus + node/cadvisor + custom | `/metrics` scrape |
| Trace | OpenTelemetry + Jaeger/Tempo | trace-id propagation |
| Log | structured JSON + Loki/Cloudwatch | trace-id in every log |
| Dashboard | Grafana (provisioned via Terraform) | per-service overview |
| Alert | Alertmanager → PagerDuty/Opsgenie | runbook URL in alert |

## RED + USE method

- **RED** (request-driven): **R**ate, **E**rrors, **D**uration → primary for API
- **USE** (resource): **U**tilization, **S**aturation, **E**rrors → primary for infra (CPU/mem/disk/net)

## Phase wiring

- **Phase 1a Sara**: NFR row ตรง SLO target (latency p95, availability) — Reggie sign
- **Phase 1c Sentinel**: security AC ที่กระทบ SLO (rate-limit, circuit breaker)
- **Phase 5 Reggie**: SLO baseline capture (last 7d) + dashboard live + alert wired
- **Phase 6 Reggie**: burn rate watch continuous + incident trigger + postmortem

## Evidence

```
✅ "[SLO: slo-payment.yml] target=99.95% (21.6m/30d); actual=99.97% (12.4m used) — 57% budget left"
✅ "[Grafana: dash-id=payment] p95=180ms (target<200) ✓"
✅ "[Burn alert: prom-alert-id=high-burn] not firing"
✅ "[Postmortem: 2026-05-22-payment-db-pool.md] MTTR=42min, 5-why complete"
❌ "service ok" (no metric, no path)
❌ "latency ดี" (no p95/p99 — avg ไม่นับ)
```

## ห้าม

- ห้าม "average latency" — p50/p95/p99 เท่านั้น (avg ปกปิด long tail)
- ห้าม SLO ที่ Patrick ไม่ได้ negotiate (ไม่ realistic + ไม่มี budget conversation)
- ห้าม alert ไม่มี runbook (alert = "do something now")
- ห้าม "100% availability" target (impossible + ไม่มี budget for change)
- ห้าม close incident ไม่มี postmortem schedule
- ห้าม SLI ที่วัดไม่ได้จริง (must be from production telemetry)
