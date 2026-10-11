---
name: domain-ecommerce
description: Reference (lazy-load) for the plan type in domain mode - ecommerce rules and platform checks, catalog, cart, promotion, OMS, payment, tax, shipping, subscription, fraud and scaling catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/ecommerce.md
WHEN: domain_topic in {platform,catalog,cart,promotion,oms,payment,tax,shipping,subscription,fraud,scaling}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# ecommerce - domain reference

**Contents**

- [Domain rules](#domain-rules)
- [Platform choice](#platform-choice)
- [โดเมน](#โดเมน)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

## Domain rules

Persona: e-commerce/retail expert. AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim). Refuse a feature that misses e-commerce pain, breaks checkout, or breaches tax/VAT, PDPA, DBD, consumer-protection or PCI-DSS scope.

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- ห้าม capture ก่อน ship physical
- ห้าม overwrite inventory → atomic
- ห้าม double-count promotion → precedence + exclusive group
- ห้าม skip idempotency สำหรับ payment/order
- ห้าม store full card — gateway token

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## Platform choice

- ห้าม default Shopify ถ้า B2B + tiered pricing + ERP integration + quote flow (พิจารณา headless / Adobe Commerce / BigCommerce B2B)
- ก่อน propose platform → cite catalog size + B2C vs B2B + integration complexity + ERP coupling
- Headless + custom commerce stack > monolith ถ้า case demand customization

## โดเมน

### Catalog
- Product (concept) vs Variant (SKU) vs Item (physical)
- Variant matrix, bundle/kit, digital, subscription
- Search (ES/OpenSearch/Meilisearch/Typesense), facet, merchandising

### Cart & Checkout
- Guest cart (cookie) vs auth cart (DB), merge on login
- Inventory reservation: on add (pessimistic) / on checkout start (balanced) / on place (optimistic)
- Pricing order: subtotal → discount → shipping → tax → total (rounding rule documented)

### Promotion Engine
- Types: %off, amount off, BOGO, free shipping, bundle, tier, loyalty point, coupon
- Targeting: category/brand/SKU × segment × channel × time window
- Stacking: exclusive vs stackable + priority + max cap + min spend
- Rule engine declarative (JSON) + cache eligible

### OMS
- Lifecycle: Pending → Paid → Processing → Shipped → Delivered → Completed (+ Cancelled/Returned/Refunded)
- Split shipment, backorder, pre-order
- WMS/3PL integration, wave picking

### Payment (TH)
- Card, PromptPay QR, transfer + slip, COD, installment 0%, True Money / Rabbit LINE / ShopeePay, BNPL (Atome/Akulaku)
- Flow: Authorize → Capture → partial capture for split shipment (the capture-before-ship rule stays in the agent body)
- Refund: full/partial, restocking fee, idempotency key

### Tax & Fiscal (TH)
- VAT 7% inclusive/exclusive, threshold 1.8M/yr
- e-Tax Invoice + e-Receipt (RD > 30M revenue)
- WHT B2B (PND 3/53/54)

### Shipping
- Standard/Express/Same-day/Pickup/Locker
- TH carriers: Kerry, Flash, Thailand Post, J&T, Ninja Van, DHL, FedEx
- Rate: flat / weight / zone / real-time API; free shipping threshold
- Tracking: webhook + fallback polling

### Customer, Loyalty, Returns
- Customer: guest/registered, multi-address, tax profile
- Loyalty: point earning + tier + redemption
- RMA: request → approve → ship back → inspect → refund/exchange
- Return window: 7/14/30 days

### Multi-channel
- Web / app / social (LINE/IG/TikTok Shop) / marketplace (Shopee/Lazada) / POS
- Unified inventory, allocation per channel
- **Headless**: decouple storefront (Shopify Hydrogen, commercetools, Saleor, Medusa)

### Subscription
- Recurring: monthly/annual/usage-based
- **Dunning**: smart retry on payday, decline code aware
- Proration on plan change (upgrade immediate, downgrade end-of-period)
- Pause/skip, trial-to-paid, grandfathered pricing

### Fraud Prevention
- **Velocity**: max orders/hour per account/IP/device
- **Device fingerprint**: FingerprintJS, Sift, Riskified
- AVS + CVV check
- Chargeback rate alert > 0.9%
- 3DS step-up for high-risk
- Block list (email/device/card BIN)

### Search & Recommendation
- Recommendation: collaborative, content-based, hybrid, "frequently bought together"
- Search ranking: TF-IDF + business boost (popular, margin, in-stock, freshness)
- A/B testing hooks

### Multi-currency / B2B
- FX rate, rounding, display vs settlement currency
- B2B: tier pricing, quote-to-order, credit terms (Net 30), bulk discount

### Scalability
- Read-heavy: CDN + product cache
- Flash sale: inventory pre-allocation, queue checkout, K8s HPA
- DB sharding by region/customer

### Compliance
- PDPA, DBD, consumer protection, PCI-DSS (if storing card)

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Catalog/cart/checkout/promo/OMS/subscription | `plan` with the ecommerce domain reference |
| Marketplace sync, fraud (e-com pattern) | `plan` with the ecommerce domain reference + `plan` with the fintech domain reference consult |
| Payment gateway integration | → `plan` with the fintech domain reference |
| Tax/VAT/WHT rule | → `plan` with the erp domain reference |
| Booking-style inventory (time-slot) | → `plan` with the booking domain reference |
| UX/checkout flow design | → `design` |
| Implementation | → `build` (`plan` with the ecommerce domain reference ส่ง schema + state + rule) |
| Architecture (CQRS catalog, event order) | → `plan` (architecture mode) + `plan` with the ecommerce domain reference consult |

## Best Practices

- **Reservation strategy**: on add (low conv) / on checkout start (balanced default) / on place (optimistic)
- **Cart merge on login** — preserve guest items + dedupe SKU
- **Price-at-add vs price-at-checkout** — document business decision
- **Promotion engine declarative** (JSON rule) — business edit, ไม่ deploy
- **Subscription dunning** — smart retry on payday
- **Marketplace allocation** — strict per-channel inventory
- **Search ranking** = relevance + business boost
- **Flash sale**: pre-allocate inventory + queue + HPA + cache
- **3DS frictionless > challenge** for low-risk
