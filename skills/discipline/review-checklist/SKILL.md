---
name: review-checklist
description: |
  [WHAT] Code review discipline — Chris 7-dim checklist + Quinn integration/E2E/contract/load/a11y matrix + Sentinel security + Domain Expert validation + severity grading + bd-native report format. DRY source-of-truth สำหรับ /implement Phase 3b และ /review.
  [AUDIENCE] Chris (7-dim primary) + Quinn (integration/E2E/security scan) + Sentinel (CSP/SAST/abuse) + Domain Experts (Felix/Iris/Sam/Tara/Elena/Brooke/Emma).
  [WHEN] Phase 3b ใน /implement pipeline; ทุก call ของ /review; ก่อน merge gate; หลัง bug fix.
  [TRIGGER] /shode-house:review-checklist, "code review", "review", "7-dim", "Chris review", "Quinn integration test", "security scan", "domain validate", "REVIEW report format".
---

# Review Checklist (v3.1 DRY source-of-truth)

> v3.1 refactor: เดิม `/implement` Phase 3b และ `/review` มี checklist ของตัวเอง — duplicate logic. v3.1 รวมเป็น skill เดียว, ทั้ง 2 command อ้างที่นี่
> **Owners**: Chris (primary 7-dim) + Quinn (integration matrix) + Sentinel (security depth) + Domain Expert (regulation/business rule)

---

## When NOT to use

- **Spike / throwaway script** — review overhead ไม่คุ้ม
- **Generated code** (codegen output, ORM model auto-generated) — review template, ไม่ใช่ instance
- **Pure doc/markdown change** — Bella/Uma review เนื้อหา, ไม่ใช่ review-checklist
- **Production hot-fix P0** ที่ต้อง ship ทันที — รัน checklist เฉพาะ 🔴 Critical (Security + Correctness); defer มิติอื่นเป็น follow-up

## Required inputs — refuse without

- [ ] **Code locatable** (path / Jira PR / commit SHA — ห้าม "review โค้ดทั่ว ๆ ไป")
- [ ] **Spec context** (BRD AC / bd issue / Jira description — review เทียบ spec, ไม่ใช่ลอย ๆ)
- [ ] **Static analysis tool พร้อม** (lint/SAST configured — Chris ใช้ Bash จริง, ไม่ใช่ "ดู visually")
- [ ] **Tracker available** (bd active หรือ Jira key — finding ต้อง track, ไม่ใช่ chat message)
- [ ] **Severity scale agreed** (project ใช้ 🔴/🟠/🟡/🔵/💡 default — ห้าม "minor/major" loose)

---

## Chris — 7 Dimensions (รัน parallel เป็น 7 pass)

ทุกมิติ output: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low / 💡 Suggestion

### 1. Correctness
- Logic ตรง spec/AC
- Edge case (null/empty/boundary/overflow/unicode)
- Error path (catch + re-throw + meaningful message)
- Concurrent: race / deadlock / lost update
- Idempotency (retry-safe)

### 2. Security (OWASP Top 10 + lang-specific)
- Injection (SQL/NoSQL/cmd/LDAP/XPath)
- Broken auth + session
- Sensitive data (PII/PCI/secret)
- XXE / SSRF / deserialization
- Broken access (BOLA/IDOR/missing authz check)
- Misconfig (default password, exposed admin, verbose error)
- XSS (stored/reflected/DOM) + CSP bypass
- Vulnerable component (audit dep)
- Logging gap (audit trail missing)
- SSRF / open redirect

→ 🔴 Security Critical/High = **block merge** เสมอ (no exception)

### 3. SOLID & Design
- SRP — class/function ทำสิ่งเดียว
- OCP — extend ผ่าน interface
- LSP — subtype substitutable
- ISP — interface เล็ก
- DIP — depend on abstraction
- Cohesion สูง / coupling ต่ำ
- DRY (แต่ไม่ over-DRY = WET tolerable)

### 4. Performance
- N+1 query
- Time/space complexity (Big-O)
- Memory allocation (loop alloc, leak)
- DB index utilization
- Cache strategy (TTL, invalidation)
- Async/await + thread pool sizing
- Cold start / startup time

### 5. Maintainability
- File size ≤ 300 lines (function ≤ 30; cyclomatic ≤ 10)
- Naming descriptive (intent revealing)
- Comment "why" ไม่ใช่ "what" (code อ่านได้แล้ว)
- Magic number → constant
- Test as documentation
- Tech debt label (TODO/FIXME/HACK) มี ticket

### 6. Testing
- Unit coverage ≥ project threshold (Chris baseline ratchet)
- Mutation kill ≥ 70% (Stryker/PIT/mutmut)
- Property-based test (Hypothesis/fast-check) สำหรับ invariant
- Test doubles ถูก: stub/fake/mock/spy ตามจุด
- ห้าม mock business logic (mock เฉพาะ external: DB/API/clock)
- ห้าม `time.sleep` (fake time/freeze)

### 7. Observability
- Structured log (JSON, key fields: req_id, user_id, latency)
- Metric (RED: rate/error/duration หรือ USE: utilization/saturation/error)
- Trace (OpenTelemetry span ที่ critical path)
- Alert ทุก SLO breach (link runbook)
- Audit log สำหรับ R0 action (money/auth/PII access)

---

## Quinn — Integration Matrix (รัน 6 axes)

### 1. Integration (Testcontainers + real dep)
- Real DB (Postgres/MySQL/Mongo via Testcontainers)
- Real cache (Redis Testcontainers)
- Real queue (Kafka/RabbitMQ Testcontainers)
- ห้าม mock DB/cache/queue ถ้า test integration

### 2. E2E (Playwright/Cypress — critical user journey)
- Critical path 100% coverage (login/checkout/payment/booking)
- Happy + 1 error path ต่อ journey
- Mobile + desktop viewport

### 3. Contract (Pact + Schemathesis)
- Consumer-driven (consumer Pact → provider verify)
- OpenAPI schema fuzz (Schemathesis)
- Pact broker integration (CI gate)

### 4. Load smoke (k6 / Locust / Gatling)
- p95 < SLO (จาก `slo` skill)
- Error rate < 0.1%
- 1-2x peak สำหรับ smoke; nightly = full load

### 5. a11y automation (axe-core)
- WCAG AA — critical violations = 0
- jq filter axe report → bd note ถ้าเจอ
- Storybook addon-a11y per component

### 6. Pen test (OWASP ASVS Level 1-2)
- Automated: ZAP baseline
- Manual: spot check top-OWASP per release
- Sensitive flow (payment/auth) — Sentinel co-review

---

## Sentinel — Security Depth (conditional, when secure skill triggered)

- SAST (Semgrep/CodeQL) — full repo
- SCA (Trivy/Grype/npm audit) — dep + container
- Secret scan (gitleaks/truffleHog) — commit history + current
- CSP / Trusted Types policy review
- Abuse case validation (จาก `secure` skill threat model)
- Pen test (OWASP ASVS, ถ้า PCI/HIPAA scope)

---

## Domain Expert — Conditional Validation (parallel กับ Chris+Quinn)

Trigger ตาม code path:

| Keyword in changed code | Domain Expert |
|---|---|
| payment / ledger / money / settle | → **Felix** |
| accounting / journal / inventory (generic) | → **Elena** |
| SAP / ABAP / Fiori / BAPI / IDoc / S4HANA | → **Sam** |
| order / market / matching / FIX | → **Tara** |
| policy / claim / premium / actuarial | → **Iris** |
| booking / rate / yield (hotel/airline) | → **Brooke** |
| cart / checkout / promotion / catalog | → **Emma** |

Domain Expert verify: regulation cite (`shode-house-evidence`) + business rule + edge case ที่เฉพาะ domain. ห้าม skip ถ้า domain-sensitive

---

## Severity Grading (consistent)

| Severity | Meaning | Action |
|---|---|---|
| 🔴 **Critical** | Security exploit / data loss / production-breaking / regulation violation | **Block merge**, immediate fix |
| 🟠 **High** | Wrong behavior / perf regression > 10% / a11y critical | Fix before merge |
| 🟡 **Medium** | Code smell / minor inefficiency / test gap | Track P2-P3, fix in sprint |
| 🔵 **Low** | Nitpick / style / could-be-better | Optional, defer P4 backlog |
| 💡 **Suggestion** | Refactor opportunity / pattern improvement | Inform, no block |

---

## REVIEW Report Format (bd-native primary, markdown fallback)

ใช้ format ใน `shode-house-evidence` (REVIEW Report Format section). สรุป:

### bd notes (≤ 500 chars compact)
```
[Chris|Quinn|Sentinel review bd-42] verdict: FAIL
- 🔴 1: <file:line> <issue>
- 🟠 2: <count + summary>
- 🟡 5: <count, see md fallback>
Coverage: unit 78% → 81% target hit; mutation 72%
UX: Uma POST PASS (separate)
Loop route: code → Phase 2
```

### Markdown fallback (no bd) — `outputs/REVIEW-<feature>.md`
Full template per finding (file:line · why it matters · evidence path · suggested change)

### Always: link external tracker
- ถ้ามี Jira key → `addCommentToJiraIssue` กลับ ticket ด้วย bd link หรือ md path
- ถ้ามี GitHub PR → `gh pr review --comment "..."` หรือ inline comment

---

## Loop Routing Recommendation (Phase 4 input)

Chris/Quinn/Sentinel **must recommend** loop route ใน report:

| Finding type | Route → |
|---|---|
| Code logic / SOLID / perf | Phase 2 (Dave fix) |
| UI / visual / a11y manual | Phase 1b (Uma redesign) |
| Spec / AC / regulation gap | Phase 1a (Bella ∥ Sara revise) |
| Test gap | Phase 2 (Dave) + invoke `automate-test` skill (Quinn) |
| Security finding | Phase 1c (Sentinel threat model update) → Phase 2 |
| Multi-route | Oliver triage (don't recommend; defer) |

---

## Anti-Puppet Gate

- ห้าม claim "PASS" โดยไม่ paste tool output (jq axe / coverage report / Semgrep finding / Pact verification)
- ห้าม "should be fine" / "looks good" — verbatim cite line numbers
- ห้าม skip 7-dim เพราะ "minor change" — minor = bypass ก็ minor effort
- ห้าม domain skip ถ้า code touches money/regulation/PII

---

## ห้าม (consolidated)

- ห้าม review โดยไม่อ่าน code จริง (prefer `Grep` > `Read` full file สำหรับ pattern; full file ถ้าต้องเข้าใจ flow)
- ห้าม approve ที่ static analysis ไม่ผ่าน (Chris รัน lint + SAST จริง)
- ห้าม merge ถ้า 🔴 Critical ติด
- ห้าม invent finding (cite line + evidence ทุกครั้ง)
- ห้าม blame author (review = code-on-the-page, ไม่ใช่ engineer-on-the-team)
- ห้าม skip Domain Expert validation ถ้า code touches sensitive area
- ห้ามเก็บ finding ทั้ง bd และ markdown — เลือกตาม project state (CLAUDE.md storage rule)

---

## Used by

- `commands/implement.md` Phase 3b (Chris ∥ Quinn parallel pass)
- `commands/review.md` (standalone ad-hoc review)
- Both commands invoke this skill — DRY source-of-truth
