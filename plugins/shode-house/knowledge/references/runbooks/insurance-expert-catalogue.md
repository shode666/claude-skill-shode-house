---
name: insurance-expert-catalogue
description: Reference (lazy-load) for insurance-expert - policy admin, underwriting, claims, actuarial, reinsurance, IFRS 17 / TFRS 17 and TH regulatory catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/runbooks/insurance-expert-catalogue.md
WHEN: domain_topic in {policy_admin,underwriting,claims,actuarial,reinsurance,ifrs17,regulatory}
OWNER: insurance-expert
REQUIRED-BEFORE: domain_advice_stated
```

# insurance-expert - domain catalogue

**Contents**

- [โดเมน](#โดเมน)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

> Lazy reference for `insurance-expert`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

## โดเมน

### Policy Admin
- **Lifecycle**: Quote → Application → Underwrite → Issue → Endorsement → Renewal → Cancel/Lapse/Maturity/Claim
- Policy data: policyholder, insured, beneficiary, coverage, exclusion, premium, term
- **Endorsement immutable** — append history (effective date, sequence)
- Renewal: auto vs manual, rate refresh, eligibility re-check
- Cancellation: short-rate vs pro-rata, reason code

### Underwriting
- Risk classification: standard/sub-standard/decline
- Tools: rule engine, predictive model, manual referral
- **Life**: medical UW (lab, MIB, attending physician statement)
- **Motor**: vehicle data, driver history, geo
- **Health**: pre-existing exclusion, waiting period
- Auto-UW threshold (instant issue) vs manual queue

### Claims
- Lifecycle: FNOL → Triage → Investigation → Adjudication → Settlement → Subrogation → Close
- Coverage check (in-force, sum insured, deductible, co-pay, exclusion)
- Reserve types: case, IBNR, IBNER, ULAE
- Fraud: rule + ML (Friss, Shift Tech)
- TPA, network provider, direct billing

### Actuarial / Pricing
- **Pricing**: pure premium + loading (expense, profit, contingency)
- Rating factors (motor: vehicle/driver/geo; health: age/sex/preexisting)
- Loss ratio, combined ratio, expense ratio
- **Reserving**: chain-ladder, Bornhuetter-Ferguson, Cape Cod
- Tools: Prophet (life), ResQ (non-life), R, Python

### Reinsurance
- **Treaty**: proportional (quota share, surplus), non-proportional (XoL — risk/aggregate/cat)
- **Facultative** — case-by-case
- Bordereau reporting, premium ceding, claim recovery

### IFRS 17 / TFRS 17

Effective periods differ: [IFRS 17](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-17/) from 1 January 2023; [Thai TFRS 17](https://acpro-std.tfac.or.th/standard/113) from 1 January 2025. Verify the entity's jurisdiction, reporting period and applicable amendments before advising.

| Model | When |
|-------|------|
| **BBA** (Building Block) | Default (long-term) |
| **PAA** (Premium Allocation) | Short-term, simpler |
| **VFA** (Variable Fee) | Direct participating |

CSM (Contractual Service Margin), risk adjustment, fulfillment cash flow
Disclosure: complex (LRC, LIC, OCI option)

### Regulatory (TH)
- **OIC**: product registration, premium rate filing, policy wording approval
- **Solvency**: RBC framework, CAR ≥ 140%
- **Accounting**: TFRS 17 (BBA/PAA/VFA)
- Market conduct, complaint handling, PDPA, anti-fraud, AML

### Tech Stack
- Policy admin: Guidewire, Duck Creek, Majesco, custom
- Claims: EIS, Mitchell, custom
- Distribution: Salesforce FSC, agent portal
- Health: TPA, PBM, clearinghouse

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Policy/UW/claim/actuarial/IFRS17/OIC | insurance-expert |
| Payment (premium, claim payout) | → fintech-expert |
| Generic accounting | → erp-expert |
| SAP for Insurance | → sap-expert + insurance-expert |
| Implementation | → developer (insurance-expert ส่ง business rule + state) |

## Best Practices

- **Policy data model = core** — ทุก module reference
- **Endorsement = event** — append-only, effective-date sorted
- **Coverage decision tree** declarative (rule engine)
- **Reserve = function of claim** — actuarial review quarterly
- **PAA สำหรับ short-term** (motor 1y), **BBA default** สำหรับ long-term life
- **Risk-based pricing** — segment + factor + relativity
- **Fraud rule + ML** — score 0-100 + threshold + manual review
- **NCD** for motor — reset on claim
- **Catastrophe reinsurance** — XoL aggregate
- **PII + health = sensitive** (encryption, access, PDPA)
