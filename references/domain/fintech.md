---
name: domain-fintech
description: Reference (lazy-load) for the plan type in domain mode - fintech rules and payments, ledger, banking, KYC/AML, fraud, custody and security catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/fintech.md
WHEN: domain_topic in {payment,ledger,banking,kyc_aml,fraud,custody,security}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# fintech - domain reference

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

**Contents**

- [Domain rules](#domain-rules)
- [โดเมน](#โดเมน)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)
- [Citation](#citation)

## Domain rules

Persona: fintech AI co-pilot (banking, payment, KYC/AML literate). AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim). **Money is sacred.** Refuse a feature that misses the domain pain or conflicts with regulation (BOT/PCI/SEC/AML).

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- Money in integer subunits or Decimal, never float; ledger append-only, corrections by reversing entry; idempotency key + dedupe on every money-moving request.
- ห้าม skip reconciliation
- ห้าม store CVV/full PAN → PCI violation
- ห้ามตอบ regulation มั่นใจถ้าไม่แน่ → consult lawyer (Philosophy 1)
- ห้าม skip audit log

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## โดเมน

### Payments & E-Money
- **Standards**: ISO 8583 (card MTI/field), ISO 20022, EMVCo, 3DS 2, PCI-DSS v4
- **TH**: PromptPay, Bill Payment 2.0, BAHTNET (RTGS), ITMX, NDID
- **Card**: Visa/Mastercard/JCB/UnionPay/AMEX
- **Reconciliation**: 3-way (gateway/acquirer/internal), break analysis, auto-match
- **Tokenization** (PCI scope reduction):
  - Network Token (Visa VTS, MC MDES) — replace PAN at network level
  - Vault Token (processor)
- **Chargeback**:
  - Flow: Merchant → Acquirer → Network → Issuer → Cardholder
  - Reason codes: fraud (4837), not-as-described (4853), auth (4808), processing (4834)
  - Stages: Retrieval → Chargeback → Representment → Pre-Arbitration → Arbitration
  - Timeline: 120d (fraud), 540d (service); rate threshold > 0.9% monitoring

### Ledger & Accounting
- **Double-entry** (DR/CR), CoA (TH GAAP/IFRS)
- **Immutable ledger** — append-only, event-sourced
- Multi-currency (FX rate, revaluation, gain/loss)
- Reconciliation daily/intra-day

### Banking
- Core: CASA, loan, deposit, GL integration
- Rails: RTGS (BAHTNET), ACH, instant (PromptPay), SWIFT (ISO 20022 migration 2025)
- **Open Banking**: OAuth 2.0, FAPI 1.0 Advanced, AISP/PISP
- Lending: NPL **TFRS 9** (3 stages)

### KYC/AML
- KYC: identity, EDD, ongoing, NDID
- AML: transaction monitoring, sanction (OFAC/UN/AMLO), PEP
- Reporting: STR, CTR, FATCA, CRS
- TH: BOT, SEC, OIC, AMLO

### Real-time Fraud
- Rule: velocity, geo mismatch, device change, amount spike
- ML: gradient boosting → score 0-100
- Graph (shared device/IP/card)
- Response: allow / step-up (OTP/3DS) / block / freeze
- Tools: SAS AML, Feedzai, Sift, FICO

### Crypto Custody
- Hot (online, limit) / Cold (offline, majority)
- **MPC** (key split), HSM
- Signing ceremony, key rotation, audit

### Security
- **PCI-DSS v4**: CDE, tokenization, P2PE, segmentation
- SOC 2 Type II, ISO 27001, GDPR/PDPA TH
- BOT IT-Risk Notification 2/2562

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Payment/ledger/banking/KYC/compliance | `plan` with the fintech domain reference |
| Generic ERP accounting | → `plan` with the erp domain reference |
| SAP-specific (FI/CO) | → `plan` with the sap domain reference |
| Trading exchange | → `plan` with the trading domain reference |
| Insurance financial | → `plan` with the insurance domain reference |
| API impl | → `build` |
| Architecture (event sourcing/saga) | → `plan` (architecture mode) + `plan` with the fintech domain reference consult |

## Best Practices

- **Subunit storage** (satang, cents) — int64 ดีสุด, fallback Decimal
- **Network token > vault token > raw PAN**
- **Outbox pattern** for event publishing (atomic with DB tx)
- **Idempotency-key** + dedupe table (TTL 24h+)
- **Saga (orchestration)** for multi-step payment
- **Eventual consistency** + reconciliation
- **Settlement window** ระบุ (same-day vs T+1 vs T+2)
- **Risk-based step-up** — 3DS frictionless > challenge

## Citation

กฎเต็ม (disclaimer · citation format · general-guidance mark) → **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง; ไม่ได้ preload) — general-guidance mark ต้อง specific ระบุ standard ที่อ้าง ไม่ใช่ generic AI persona disclaimer
`plan` with the fintech domain reference ✅ "BOT notice ธปท.สนช. 12/2566 ข้อ 4 — KYC enhanced สำหรับ PEP" · ❌ "BOT notice 15-day" (no number/clause/date)
