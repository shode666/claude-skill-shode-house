---
name: automate-test
description: Set up a project's test automation strategy and infrastructure, meaning the mix of unit, integration and end-to-end tests, CI gates and thresholds. Not for the tests of a single change, one changed screen, or spikes and one-off scripts.
---

# Automate Test (CI test gate + pyramid)

> **Owner**: `verify` (runtime axis) (design + integration/E2E) + `verify` (standards axis) (unit) + `operate` (deploy mode) (CI wiring)

## When NOT to use

- **Single-file script / utility** — manual test ครั้งเดียวพอ ไม่ต้อง pyramid
- **POC / spike** ก่อน decision — เน้น exploration; test มา phase 2
- **Pure data migration** (one-shot) — ตรวจด้วย count/checksum + rollback plan; pyramid overkill
- **Legacy codebase ที่ `verify` (runtime axis) ยังไม่ baseline** — `verify` (runtime axis) ต้อง `coverage report` baseline ก่อน

## Required inputs — discover before selecting gates

ก่อนเริ่ม test strategy ต้องมี:

- [ ] **Tech stack ระบุ** (language + framework — เพื่อเลือก test tool ที่ฟิต)
- [ ] **Service boundary clear** (อะไรเป็น unit, อะไรเป็น integration — ต้องมี SA หรือ `build` ระบุ)
- [ ] **CI platform ระบุ** (GitHub Actions / GitLab / CircleCI — สำหรับ `operate` (deploy mode) wire gate)
- [ ] **Baseline coverage** (ถ้า legacy: รัน `coverage report` หา starting point; ห้ามตั้ง threshold ลอย ๆ)
- [ ] **Test data strategy** (fixture / factory / production sample / synthetic — ห้าม "เดี๋ยวค่อย mock")

Discover these inputs from the project first. Missing decisions block only the
dependent configuration; continue authorized baseline collection and preparation.

## Test Pyramid (planning heuristic)

```
       /E2E\         10% (`verify` (runtime axis) — Playwright)
      /Integ\        20% (`verify` (runtime axis) — Testcontainers)
     / Unit  \       70% (`verify` (standards axis) — pytest/Vitest/JUnit)
```

❌ Anti-pattern (inverted pyramid): E2E เยอะ = slow, fragile, expensive

The ratio illustrates a broad base of fast tests, not a required test-count quota.
Choose coverage by behavior, boundaries and risk; preserve meaningful existing tests.

## CI Gate (applicable project-required checks block merge)

Use the project's existing tools and adopted targets. The table is a menu: select
checks for affected surfaces, not a requirement to add Docker, staging, nightly
jobs or new test infrastructure to every project.

| Stage | Tool | Gate |
|-------|------|------|
| **Format** | ruff/prettier/gofmt | clean |
| **Lint** | ruff/eslint/golangci-lint | 0 error |
| **Type** | mypy/tsc/javac | strict pass |
| **Unit** | pytest/Vitest/JUnit | coverage ≥ 80% business logic |
| **Integration** | Testcontainers + WireMock | critical path 100% |
| **SAST** | Semgrep/Bandit/gosec | 0 high+ |
| **SCA** | Trivy/Grype/npm audit | 0 critical CVE |
| **Secret** | gitleaks | 0 finding |
| **Build** | Docker | success |
| **Image scan** | Trivy | 0 critical |
| **E2E** (after deploy staging) | Playwright | smoke + critical journey |
| **Perf** (nightly) | k6 | p95 < SLO |

## Threshold (เก็บใน config)

Defaults below are examples until the project adopts them; `verify` (standards axis) grades by risk.

- Unit coverage: business ≥ 80%, infra ≥ 50%
- Integration: critical path 100%, normal 70%+
- E2E: critical user flow 100% (login, checkout, payment, claim, booking)
- Mutation kill rate: ≥ 70% (mutmut/Stryker — nightly)
- Perf: p95 < SLO, error < 0.1%, throughput ≥ target
- Flaky rate: < 1% (CI auto-mark + ticket ถ้าเกิน)

## Test Types & Tools

### Unit (`verify` (standards axis))
- pytest (Py), Vitest+Jest (JS/TS), testing+testify (Go), JUnit+Mockito (Java/Kt)
- Property-based: Hypothesis, fast-check
- Mutation: mutmut, Stryker

### Integration (`verify` (runtime axis))
- **Testcontainers** (Postgres/Redis/Kafka/MinIO/Elastic) — real services
- WireMock — mock HTTP boundary
- Schemathesis — OpenAPI fuzz
- DB tx rollback / isolated DB per test

### Contract (`verify` (runtime axis) — microservices essential)
- **Pact** (consumer-driven): consumer publish → provider verify
- Pactflow broker
- Run ใน CI ทั้งสอง side

### Performance (`verify` (runtime axis) — nightly)
- **k6** (recommended) / Gatling / Locust / JMeter
- Load (sustained peak), Stress (find breaking), Soak (long-run leak), Spike (sudden ramp)

### Chaos (🟡 production-grade)
- Chaos Mesh / LitmusChaos / Gremlin
- Inject: kill pod, latency, partition, disk fill
- Run: staging continuous, prod scheduled

## CI Pipeline (`operate` (deploy mode) set up)

```yaml
on: [push, pull_request]
jobs:
  quality:
    - format / lint / type
  unit:
    - pytest --cov --cov-fail-under=80
  security:
    - semgrep / gitleaks / trivy
  build:
    - docker build + scan
  integration:
    - docker compose up + pytest tests/integration
  deploy-staging:
    needs: [quality, unit, security, build, integration]
  e2e:
    needs: deploy-staging
    - playwright test --grep @smoke
  promote-prod:
    needs: e2e
    if: github.ref == 'refs/heads/main'
```

`operate` (deploy mode) configures applicable adopted checks as required, within authorized CI scope.
The pipeline is illustrative; promotion to production requires actual deployment
authorization and the project's release gates.

## Flaky Test Discipline

- Flaky = bug → ห้าม retry หลบ
- Auto-mark `@flaky` + ticket (high priority) → fix ภายใน 1 sprint
- ถ้า fix ไม่ได้ → quarantine (skip + ticket) ไม่ใช่ delete

## Hand-off

- `build`: smoke test + emit observability (`/health`, metric, trace)
- `verify` (standards axis): unit test deep + edge case
- `verify` (runtime axis): integration + E2E + contract + perf
- `operate` (deploy mode): wire เข้า CI + threshold + alert

## ห้าม

- ห้าม invert pyramid (E2E เยอะ)
- ห้าม disable test silently → ticket
- ห้าม retry flaky test หลบ → fix root cause
- ห้าม mock หมดใน integration → = unit test แล้ว
- ห้าม commit code โดย CI red
- ห้าม skip security gate (SAST/SCA/secret)
- ห้ามตั้ง coverage gate แล้วลด → ratchet (เพิ่มได้ ลดไม่ได้)
