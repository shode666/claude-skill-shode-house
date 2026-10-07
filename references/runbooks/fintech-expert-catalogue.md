---
name: fintech-expert-catalogue
description: Reference (lazy-load) for fintech-expert - payments, ledger, banking, KYC/AML, fraud, custody and security catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/runbooks/fintech-expert-catalogue.md
WHEN: domain_topic in {payment,ledger,banking,kyc_aml,fraud,custody,security}
OWNER: fintech-expert
REQUIRED-BEFORE: domain_advice_stated
```

# fintech-expert - domain catalogue

> Lazy reference for `fintech-expert`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

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
| Payment/ledger/banking/KYC/compliance | fintech-expert |
| Generic ERP accounting | → erp-expert |
| SAP-specific (FI/CO) | → sap-expert |
| Trading exchange | → trading-expert |
| Insurance financial | → insurance-expert |
| API impl | → developer |
| Architecture (event sourcing/saga) | → solution-architect + fintech-expert consult |

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

กฎเต็ม (disclaimer · citation format · general-guidance mark) → **`domain-core`** (preload แล้ว) — general-guidance mark ต้อง specific ระบุ standard ที่อ้าง ไม่ใช่ generic AI persona disclaimer
fintech-expert ✅ "BOT notice ธปท.สนช. 12/2566 ข้อ 4 — KYC enhanced สำหรับ PEP" · ❌ "BOT notice 15-day" (no number/clause/date)
