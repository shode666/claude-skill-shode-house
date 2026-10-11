---
name: domain-erp
description: Reference (lazy-load) for the plan type in domain mode - erp rules and costing choice, GL, AR, AP, inventory, MRP, procurement, payroll, fixed assets, budgeting and revenue recognition catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/erp.md
WHEN: domain_topic in {gl,ar,ap,inventory,mrp,procurement,payroll,fixed_assets,budgeting,revenue}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# erp - domain reference

**Contents**

- [Domain rules](#domain-rules)
- [Costing choice](#costing-choice)
- [โมดูล](#โมดูล)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

## Domain rules

Persona: ERP/accounting AI co-pilot (GL/AR-AP/MRP literate; Odoo, NetSuite, MS Dynamics, custom). AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim). Refuse a feature that misses accounting pain or conflicts with a reporting standard (TFRS/IFRS).

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- ห้ามออกแบบโดยลืม GL impact
- ห้าม float กับ amount → Decimal
- ห้ามให้ user แก้ posted journal ตรง → reversing
- ห้ามข้าม period control + audit trail
- Never hardcode a tax or regulatory parameter (VAT/WHT rate etc.) → configurable + effective-dated.
- Never recommend LIFO under IFRS/TFRS (not allowed).

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## Costing choice

- ห้าม default FIFO ถ้า industry = perishable / lot-traceable (consider FEFO + lot tracking)
- ก่อน propose costing → cite industry (pharma/food/manufacturing/general) + TFRS-IFRS acceptance
- Weighted Avg vs FIFO vs Specific Identification — match context, ห้าม tribal default

## โมดูล

### GL
- CoA: 5-hierarchy/segment, dimensional
- Journal: manual, recurring, reversing, accrual, adjusting
- **Period close** (soft/hard), month/year-end
- **Multi-entity Consolidation**: IC posting, **elimination** (IC sale/AR-AP, IC profit in inventory, IC dividend), FX (temporal vs current rate), minority interest, goodwill
- Standards: TFRS / IFRS / TH GAAP

### AR
- Customer master: credit limit, payment term, dunning
- Invoice → Receipt → Application; Aging 30/60/90/120+
- **IFRS 15 Revenue Recognition** (5-step):
  1. Identify contract
  2. Identify performance obligations
  3. Determine transaction price
  4. Allocate
  5. Recognize as obligation satisfied (point-in-time vs over-time)
- SaaS: ratable, contract modification, SSP

### AP
- Vendor master: term, WHT profile
- **3-way matching** (PO + GR + Invoice)
- Payment run, void/reissue, netting
- WHT TH: PND 3/53/54

### Inventory
- **Costing**:
  - **FIFO**: expense oldest inventory costs first; with rising unit costs these are lower than newer costs, not higher ([IAS 2](https://www.ifrs.org/issued-standards/list-of-standards/ias-2-inventories/))
  - **LIFO** (IFRS not allowed)
  - **Weighted Average** (periodic), **Moving Average** (perpetual)
  - **Standard Cost** + variance (price/quantity)
  - **Specific Identification** (serialized)
- Multi-warehouse + bin + lot/serial (traceability, expiry, recall)
- Movement: receipt/issue/transfer/adjustment/cycle count
- Valuation: perpetual vs periodic, **NRV**

### MRP / Production
- BOM (multi-level, phantom, alternate)
- Routing (operation, work center, capacity)
- MRP run: gross/net req, planned order
- Production order: release → confirmation → back-flush
- Costing: material + labor + overhead + variance

### Procurement
- PR → RFQ → PO → GR → Invoice
- Vendor evaluation, blanket order, scheduled agreement
- Approval workflow

### HR / Payroll (TH)
- Employee master, org structure, position
- Time/attendance, OT, leave
- **Payroll**: gross-to-net, SSO 5%, WHT (PND 1/91)
- Benefits: provident fund, group insurance
- TH forms: กท.20ก, PND 1, PND 1ก, 50 ทวิ
- Compliance: SSO, RD, Department of Labor

### Fixed Assets
- Asset master, depreciation (straight-line, declining, SoYD, units)
- Acquisition/disposal/transfer/impairment
- Capital WIP → capitalization
- **IFRS 16 Lease**: ROU asset + lease liability (except <12m / low-value)

### Budgeting
- Top-down vs bottom-up, zero-based
- **Variance**: budget vs actual, volume vs price
- Rolling forecast quarterly
- Cost center vs profit center

### Revenue Rec — Advanced (SaaS)
- Subscription ratable
- Contract modification (prospective vs retrospective)
- Licensing: functional vs symbolic
- Principal vs agent (marketplace)

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| GL/AR/AP/Inventory/MRP/Payroll | `plan` with the erp domain reference |
| **SAP** (ABAP/S4HANA/Fiori/BTP) | → `plan` with the sap domain reference |
| Payment/banking | → `plan` with the fintech domain reference |
| Insurance accounting (IFRS 17) | → `plan` with the insurance domain reference |
| Trading P&L | → `plan` with the trading domain reference |
| Implementation | → `build` (`plan` with the erp domain reference ส่ง schema + posting rule) |

## Best Practices

- **Master data governance** — duplicate vendor/customer/item = หายนะ
- **Effective-dated config** — VAT/WHT rate version
- **Sub-ledger first** → GL ผ่าน journal entry
- **Standard cost + variance** for manufacturing
- **Cycle count > full count** (continuous)
- **Tax/regulatory ใน config** ไม่ใช่ code
- **Soft close → hard close** (month soft, quarter hard)
- **Drill-down report** — summary → detail → transaction
