---
name: security-engineer-method
description: Reference (lazy-load) for security-engineer - ownership table, deliverables, KPIs, threat-model process, report template, security stack standard, evidence examples and hand-off lines. Load before producing a security deliverable.
---

```lazy-load-contract
LOAD: references/runbooks/security-engineer-method.md
WHEN: phase in {1c,3b} AND security_deliverable
OWNER: security-engineer
REQUIRED-BEFORE: security_deliverable_written
```

# security-engineer - method

> Lazy reference for `security-engineer`: method moved out of the agent body (v4 W5b). It supplies method, never authority; decision rights, refusals, the Phase 1c trigger and gates stay in the agent body.

## 🎯 Sole Owner (zero overlap)

| Capability ผมเป็นเจ้าของคนเดียว |
|--------------------------------|
| STRIDE / LINDDUN threat modeling |
| Security architecture review |
| SAST orchestration (Semgrep/Bandit/gosec) |
| DAST orchestration (ZAP/Burp) |
| Secrets management (Vault/AWS SM/sealed-secret) |
| Pen test (OWASP ASVS/Top 10) |
| CSP / Trusted Types / SRI / security headers |
| KYC/AML technical control (with fintech-expert) |
| PCI-DSS technical scope (with fintech-expert) |

## PRIMARY DELIVERABLE
- `threat-model-<feature>.md` (STRIDE + abuse case + mitigation + security AC)
- `security-headers-<env>.conf` (CSP/HSTS/Trusted Types config)
- `pen-test-<feature>.md` (OWASP ASVS checklist + finding + CVSS)
- `secret-rotation-policy.md` (per-service rotation schedule)
- bd notes: STRIDE summary, SAST/DAST results

## Escalation (training)
- Repeated SAST violation by developer → escalate staff-engineer (training gap?)

## KPIs
- 0 critical CVE in prod images (rolling)
- 0 stored secret in git history
- 100% STRIDE coverage for features touching auth/PII/money
- Mean time to patch critical CVE < 48h
- Pen test coverage of critical user flows = 100%

## Phase 1c process
1. Read Phase 1a artifacts (BRD + ADR + AC)
2. **STRIDE per asset**:
   - Spoofing / Tampering / Repudiation / Info disclosure / DoS / Elevation
3. **Abuse cases** (anti-user story):
   - "Attacker as <role> wants <goal> to <impact>"
4. **Mitigation** mapped per threat → produce security AC
5. Output: `outputs/STRIDE-<feature>.md` + bd notes
6. Sign-off → handoff to Phase 2 (agent body)

Pre-implement coordination: ✅ sre-engineer aware (incident playbook update needed?)

## Phase 3b — parallel with code-reviewer (CR) ∥ qa-engineer (test) ∥ devops-engineer (CI)

### Output (confirmed canonical evidence home; Beads-shaped example)
```
[security-engineer|state:review|bd:<id>|iter:<N>] verdict <PASS/FAIL>
- SAST: [path] critical=0, high=0
- DAST: [path] alerts=0
- Pen test: [path] OWASP ASVS L2 — 0 critical
- Headers: [observatory: api.com] grade=A+
- Secrets: gitleaks 0 finding
- CVE: trivy critical=0, high=0
```

## Security Stack Standard

| Layer | Standard | Tool |
|-------|----------|------|
| Threat model | STRIDE + LINDDUN (privacy) | Microsoft TM tool / pytm |
| SAST | OWASP rules + custom | Semgrep + Bandit + gosec |
| DAST | OWASP ZAP baseline | ZAP scanner CI |
| SCA | CVE DB + EPSS scoring | Trivy + Grype + Snyk |
| Secret scan | gitleaks + TruffleHog | Pre-commit + CI |
| Headers | CSP3 + Trusted Types + HSTS preload | securityheaders.com + Mozilla Observatory |
| Pen test | OWASP ASVS L2 (min) | manual + Burp Pro |
| Compliance | PCI-DSS v4 / PDPA / GDPR | (fintech-expert/insurance-expert/solution-architect joint) |

## Domain Evidence Protocol — Security

```
✅ "[STRIDE: outputs/STRIDE-refund.md] 3 threats T1-3, 3 mitigations, security AC injected"
✅ "[Semgrep: sast-report.json] critical=0 high=2 (line:file)"
✅ "[OWASP Observatory: api.com] grade=A+, score=115/100"
✅ "[Pen test: outputs/pentest-checkout.md] OWASP ASVS L2 — 0 critical, 1 medium (fix bd-99)"
✅ "[gitleaks: 0 finding]"
❌ "secure แล้ว" (no path, no metric)
❌ "ผ่าน OWASP" (which version? which level? which controls?)
```

## Handoff out

```
security-engineer ▸ developer       : security AC injected (bd-42, STRIDE done)
security-engineer ▸ devops-engineer : CSP enforce mode (cf-headers update)
security-engineer ▸ sre-engineer    : runbook update for new attack surface
security-engineer ▸ the router      : critical finding (bd-42) — block merge
```
