---
name: qa-engineer-method
description: Reference (lazy-load) for qa-engineer - report output, triage routes, evidence templates, test-layer catalogue, routing, best practices, process and output format. Load before planning tests or writing the runtime-axis report.
---

```lazy-load-contract
LOAD: references/runbooks/qa-engineer-method.md
WHEN: phase in {3b,test_planning} AND runtime_axis_review
OWNER: qa-engineer
REQUIRED-BEFORE: runtime_axis_report
```

# qa-engineer - method

> Lazy reference for `qa-engineer`: method moved out of the agent body (v4 W5b). It supplies method, never authority; the gates, verdict rules and safety lines stay in the agent body.

## Output — confirmed evidence home, Markdown fallback

- Use `skills/discipline/review-checklist/report-format.md`; store one canonical report in the project's confirmed evidence home and link it from the task record. Do not create a second tracker or duplicate report.
- Keep full evidence at accessible paths with revisions; return decisive findings and links. Unavailable remote writes remain pending sync, not claimed posted.
- Triage route loop (blocking Critical/High):
  - Test gap / integration / contract failure → Phase 2 (developer fix)
  - Spec/AC issue discovered → Phase 1a (business-analyst+solution-architect revise)

## Gate 1 journey example

- signup → login → critical action → result/receipt

## 📋 UI Test Evidence Template (confirmed evidence home; link from PR when applicable)

```
[qa-engineer|state:test|suite:ui] UI test verify
- Journey checks: <adopted tool + console output — N tests, X.Xs, fail: 0>
- Visual diff: <path/url — % diff, baseline status>
- a11y: <automated report + applicable manual criteria and findings>
- Interaction evidence: <trace/log/recording path from the available verification tools>
- Screenshots of affected critical screens: <paths or grid link>
```

## 🔄 Mutation evidence template

```
[qa-engineer|state:test|suite:mutation] Mutation evidence
- Pre-state: <value/row ก่อน action — screenshot หรือ DB query>
- Action: <user เปลี่ยนเป็น NEW value, NEW ≠ original>
- Post-state: <value/row หลัง action — MUST differ from pre>
- Backend verify: <SELECT/GET/log line ที่พิสูจน์ persisted ใน source of truth>
- No-op safety: <submit ค่าเดิมโดยไม่แก้ → ต้องไม่ break / ไม่ลบ data>
```

**Catches (ตัวอย่าง bug ที่ rule นี้จับได้):**
- Validation ที่ contradict feature — เช่น edit screen validate "input == current state" → save ไม่ได้ตลอด
- Defensive validation ที่ agent ใส่เองโดยไม่มีใน spec → ปิด valid input space
- Optimistic update rollback เงียบ ๆ (UI โชว์สำเร็จ, backend ไม่ write)
- Cache stale หลัง mutation (read กลับมาเป็นค่าเก่า)
- Wrong row updated / wrong tenant scope
- Tautology test (assertion ผ่านสำหรับทุก input = test ไม่ได้ทดสอบอะไร)

## Test-layer catalogue

E2E + integration = qa-engineer; unit = code-reviewer. No fixed layer ratio: choose layers by risk and useful feedback; justify expensive or redundant tests.

### 1. Integration
- Real DB/cache/broker/external API
- Typical speed: 100ms-1s; cover critical behavior and adopted project thresholds.
- Tools: **Testcontainers** (Postgres/Redis/Kafka/MinIO), WireMock, Schemathesis, k6
- Pattern: Setup→Execute→Verify→Teardown; isolated DB / tx rollback
- Test: repository, API e2e, message producer/consumer, cache, tx boundary, retry/circuit breaker

### 2. E2E
- User journey (UI→API→DB→side-effect)
- Speed: 5-30s; critical flow 100% (login/checkout/payment/claim/booking)
- Tools: **Playwright** (recommended), Cypress, Detox/Appium (mobile)
- Pattern: Page Object Model, data builder, **explicit wait** (ห้าม sleep), screenshot+video on failure
- Selector priority: `data-testid` > ARIA role > text > CSS (last resort)

### 3. Contract Testing (microservices)
- **Pact** (consumer-driven), **Schemathesis** (OpenAPI fuzz)
- Run ใน CI ทั้ง consumer + provider; broker (Pactflow)

### 4. Performance
- **Load** (peak QPS), **Stress** (find break), **Soak** (4-24hr leak), **Spike** (10× ramp)
- Tools: **k6** (recommended), Gatling, Locust, JMeter
- Threshold: p95 < SLO, error < 0.1%, throughput ≥ target

### 5. Other (🟡)
- **Chaos**: Chaos Mesh, LitmusChaos, Gremlin
- **Property-based**: Hypothesis, fast-check

Penetration testing (OWASP ASVS, SAST/DAST/SCA, secret scan) is security-engineer's; qa-engineer hands it off (agent body scope table).

## 🧭 Routing rows

| งาน | ใคร |
|-----|-----|
| Chaos engineering | qa-engineer |
| CI wire | → devops-engineer |
| Production bug | → developer fix + qa-engineer regression |
| Architecture impact | → solution-architect + qa-engineer re-evaluate |

## Best Practices

- **Independent test** — ห้าม test depend บน order / shared state; parallel-safe
- **AAA + G-W-T** naming
- **Test failure = test docs** — error message ต้องบอกอะไรพัง + คาด vs จริง
- **Quarantine flaky** (skip + ticket + bound to next iter fix) > delete

## Process

1. Plan: critical path → coverage target ต่อ layer
2. Design: G-W-T + fixture + mock boundary
3. Implement: integration → E2E (bottom-up); coordinate SAST/SCA and pen test evidence with security-engineer through the router
4. Report: coverage + flaky + gap recommendation; security findings come from security-engineer

## Output Format

**Test Plan**: critical paths + matrix (layer/target/tool/coverage/owner) + TC-### G-W-T + Priority P0/P1/P2
