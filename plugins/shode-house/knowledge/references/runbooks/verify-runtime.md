---
name: verify-runtime
description: Reference (lazy-load) for `verify` (runtime axis) - report output, triage routes, evidence templates, test-layer catalogue, routing, best practices, process and output format. Load before planning tests or writing the runtime-axis report.
---

```lazy-load-contract
LOAD: references/runbooks/verify-runtime.md
WHEN: phase in {3b,test_planning} AND runtime_axis_review
OWNER: verify
REQUIRED-BEFORE: runtime_axis_report
```

# `verify` (runtime axis) - method

**Contents**

- [Output — confirmed evidence home, Markdown fallback](#output--confirmed-evidence-home-markdown-fallback)
- [Gate 1 journey example](#gate-1-journey-example)
- [📋 UI Test Evidence Template (confirmed evidence home; link from PR when applicable)](#-ui-test-evidence-template-confirmed-evidence-home-link-from-pr-when-applicable)
- [🔄 Mutation evidence template](#-mutation-evidence-template)
- [Test-layer catalogue](#test-layer-catalogue)
- [🧭 Routing rows](#-routing-rows)
- [Best Practices](#best-practices)
- [Process](#process)
- [Output Format](#output-format)
- [Mode rules carried over from the former runtime axis](#mode-rules-carried-over-from-the-former-runtime-axis)

> Lazy reference for `verify` (runtime axis): method moved out of the agent body (v4 W5b). It supplies method, never authority; the gates, verdict rules and safety lines stay in the agent body.

## Output — confirmed evidence home, Markdown fallback

- Use `skills/discipline/review-checklist/report-format.md`; store one canonical report in the project's confirmed evidence home and link it from the task record. Do not create a second tracker or duplicate report.
- Keep full evidence at accessible paths with revisions; return decisive findings and links. Unavailable remote writes remain pending sync, not claimed posted.
- Triage route loop (blocking Critical/High):
  - Test gap / integration / contract failure → Phase 2 (`build` fix)
  - Spec/AC issue discovered → Phase 1a (`plan` (requirements mode)+`plan` (architecture mode) revise)

## Gate 1 journey example

- signup → login → critical action → result/receipt

## 📋 UI Test Evidence Template (confirmed evidence home; link from PR when applicable)

```
[`verify` (runtime axis)|state:test|suite:ui] UI test verify
- Journey checks: <adopted tool + console output — N tests, X.Xs, fail: 0>
- Visual diff: <path/url — % diff, baseline status>
- a11y: <automated report + applicable manual criteria and findings>
- Interaction evidence: <trace/log/recording path from the available verification tools>
- Screenshots of affected critical screens: <paths or grid link>
```

## 🔄 Mutation evidence template

```
[`verify` (runtime axis)|state:test|suite:mutation] Mutation evidence
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

E2E + integration = `verify` (runtime axis); unit = `verify` (standards axis). No fixed layer ratio: choose layers by risk and useful feedback; justify expensive or redundant tests.

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

Penetration testing (OWASP ASVS, SAST/DAST/SCA, secret scan) is `secure`'s; `verify` (runtime axis) hands it off (agent body scope table).

## 🧭 Routing rows

| งาน | ใคร |
|-----|-----|
| Chaos engineering | `verify` (runtime axis) |
| CI wire | → `operate` (deploy mode) |
| Production bug | → `build` fix + `verify` (runtime axis) regression |
| Architecture impact | → `plan` (architecture mode) + `verify` (runtime axis) re-evaluate |

## Best Practices

- **Independent test** — ห้าม test depend บน order / shared state; parallel-safe
- **AAA + G-W-T** naming
- **Test failure = test docs** — error message ต้องบอกอะไรพัง + คาด vs จริง
- **Quarantine flaky** (skip + ticket + bound to next iter fix) > delete

## Process

1. Plan: critical path → coverage target ต่อ layer
2. Design: G-W-T + fixture + mock boundary
3. Implement: integration → E2E (bottom-up); coordinate SAST/SCA and pen test evidence with `secure` through the router
4. Report: coverage + flaky + gap recommendation; security findings come from `secure`

## Output Format

**Test Plan**: critical paths + matrix (layer/target/tool/coverage/owner) + TC-### G-W-T + Priority P0/P1/P2


## Mode rules carried over from the former runtime axis

Read the router's assigned scope and canonical task; do not claim unrelated backlog work.

### 🔴 Adversary Stance — canonical `review-checklist` § Gate ที่ทุกแกนต้องผ่าน
runtime-axis-specific เพิ่มจาก gate (**ห้าม PASS** หากขาด):
- Run affected integration/journey checks independently and preserve evidence;
  `build`'s PASS is not verification. Use real boundaries where required, not an
  unconditional Docker/browser dependency for every module.
- **`verify` (runtime axis) = gatekeeper** ที่ `build` ต้องผ่าน ไม่ใช่ team-mate — decision adversarial
- browser MCP = second channel ไม่บังคับ — 🔴 ห้ามตั้งเป็นเงื่อนไข PASS (gate 3 บังคับ*หลักฐาน* ไม่ใช่ tool ใดตัวหนึ่ง)

### 🎯 Bias Discipline
- Coverage gap on critical path → ≥🟠 (ห้าม dismiss "covered upstream")

### ขอบเขต — Phase 3b runtime axis; `design` gate for UI changes
not applicable with diff evidence. `verify` (runtime axis) and `verify` (standards axis) remain separate reviewers;
parallel when supported or sequential independent contexts.
| `verify` (runtime axis) scope (Phase 3b) | Hand-off (split scope) |
| E2E (Playwright user journey, critical path 100%) | — |
| Contract test (Pact + Schemathesis) | — |
| Load smoke (k6 — p95 < SLO, error < 0.1%) | — |
| Pen test (OWASP ASVS + SAST/DAST/SCA) | → **`secure` Phase 3b parallel** (v3.0 handoff) |
| a11y **axe automation** (axe-core CI gate, WCAG AA critical=0) | — |
| Visual regression **automation** (Chromatic/Percy snapshot — run only) | baseline approval → **`design` Phase 3a** (`verify` (runtime axis) ไม่ approve) |
| **a11y manual** (keyboard + screen reader + focus order spot check) | → **`design` Phase 3a** (passed gate ก่อนแล้ว) |
| **Design adherence / visual diff manual review** | → **`design` Phase 3a** (passed gate ก่อนแล้ว) |
| **Code review (SOLID/maintainability/unit/mutation)** | → **`verify` (standards axis) Phase 3b parallel** |
| Integration/E2E/Contract/Perf | `verify` (runtime axis); deep pen test → `secure` |
| Visual regression / a11y automation | `verify` (runtime axis) (axe) + `design` consult (baseline) |
| Unit test | → `verify` (standards axis) |

### 🔴 Mandatory Pre-merge Gates (v2.2 — block PR)
Apply gates to affected surfaces and project acceptance. A library/module without
UI, API, DB or deployment does not require inventing those surfaces or Docker.
Use its public behavior journeys and existing test runner. Required checks on an
affected surface remain blocking; missing tools/evidence are not a reason for N/A.
Record concrete applicability reasons. Tool names and load values below are
examples unless adopted by the project; do not install dependencies without authority.
1. **Pre-merge integration smoke** — `docker compose up` (BE+FE+DB+cache) → run **full user journey** with curl/Playwright
   - block ถ้า fail หรือ flaky
2. **Contract test** — Schemathesis (OpenAPI fuzz) + Pact (consumer-driven)
   - Block ถ้า BE/FE drift
3. **Visual regression** — Chromatic/Percy snapshot diff
   - block ถ้า diff > 0.1% โดย `design` ไม่ approve baseline
4. **a11y axe-core** — 0 violation บน critical page (block)
5. **Load smoke** — k6 10 RPS × 1 min, p95 < SLO, error < 0.1% (block ถ้า perf regression > 20%)
6. **Real UI walkthrough** — exercise affected critical screens with available tools and save screenshots/interaction evidence; no fixed screen-count quota

### 🎬 UI Test Trigger Condition (🔴 v2.4 — บังคับ)
Gates 3-4-6 = **MANDATORY** ถ้าเข้าเงื่อนไขข้อใดข้อหนึ่ง:
- ไฟล์เปลี่ยนใน path: `frontend/`, `ui/`, `components/`, `pages/`, `views/`, `app/` (Next), `src/routes/` (Sveltekit)
- Extension เปลี่ยน: `*.vue`, `*.tsx`, `*.jsx`, `*.svelte`, `*.html`
- `design` เข้ามาในรอบนี้ (design exists)
- AC pattern: "When user clicks/sees/types..."
- Story tagged `ui` / `ux` / `frontend`
UI gates are N/A only when the affected behavior has no UI (for example, a pure backend API/CLI/library change). Internal admin interfaces still require applicable UI verification.
> Anti-puppet (`skills/discipline/review-checklist/report-format.md`): ห้าม "UI test ผ่าน ✅" — ต้อง paste evidence ทุกบรรทัดของ UI evidence template (`references/runbooks/verify-runtime.md`)

### 🔄 Mutation Evidence (🔴 v2.4.1 — บังคับสำหรับ state-changing flow)
Trigger เมื่อ feature เปลี่ยน state: **edit / update / create / delete / toggle / submit / save / transfer / approve / cancel**
ห้าม test แบบ no-op (submit ค่าเดิม / ไม่เปลี่ยน state) — bug ส่วนใหญ่ซ่อนอยู่ที่ "ทำได้จริงไหม" ไม่ใช่ "logic function ถูกไหม"
- Mutation evidence, all five or block: pre-state; NEW ≠ original; post ≠ pre; backend proof it persisted in the source of truth; no-op submit (unchanged values) breaks nothing and deletes no data.
ขาดข้อใด → block (ใต้ Approval Gate `pre-merge-ui` เดิม, ไม่เพิ่ม gate ใหม่)
> Anti-puppet: ห้าม "edit/update ทำงานถูก ✅" — ต้องมี **before ≠ after** + **backend proof** เสมอ

### ข้อห้าม
- **Coverage ratchet** — เพิ่มได้ ลดไม่ได้
- ห้าม skip test silent → ระบุเหตุผล
- ห้าม mock หมดใน integration → = unit test แล้ว
- ห้าม report "ไม่เจอ" โดยไม่บอก scope (Philosophy 1)
- เจอ secret leak → report promptly to the router without exposing the value; rotate or notify others only under existing action-specific authority
