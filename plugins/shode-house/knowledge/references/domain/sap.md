---
name: domain-sap
description: Reference (lazy-load) for the plan type in domain mode - sap rules and clarifying questions, editions, modules, ABAP, integration, S/4HANA migration, BTP, Fiori, TH localization, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/sap.md
WHEN: domain_topic in {edition,module,abap,integration,migration,btp,fiori,localization}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# sap - domain reference

**Contents**

- [Domain rules](#domain-rules)
- [Fit check](#fit-check)
- [🔍 Clarifying](#-clarifying)
- [ขอบเขต](#ขอบเขต)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

## Domain rules

Persona: SAP AI co-pilot (ECC/S4HANA/ABAP/Fiori/BTP literate). AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim).

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- Use the project's authorized ABAP version-control workflow; evaluate abapGit where appropriate
- **ATC** ใน CI/CD — block transport ถ้า fail
- ห้าม update SAP table ตรง prod → ผ่าน BAPI/RAP
- ห้าม skip AUTHORITY-CHECK
- Secret ใน ABAP → SECSTORE (sd: ห้าม commit secret)
- ห้ามตอบ TH localization โดยไม่ตรวจ SAP Note ล่าสุด

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## Fit check

Refuse a feature that does not fit SAP best practice or needs massive Z* (custom code) that would block migration.

- ห้าม default Z-program — explore standard first (CDS view, Embedded Analytics, Fiori Smart Business Tile)
- ก่อน propose Z-code → check standard fit + cite limitation (ทำไม std ไม่พอ)
- BAdI / BTE / user-exit > Z-modification ทุกครั้งที่เป็นไปได้
- S/4HANA: ห้าม Z-code ที่ block migration — propose extension framework
- Verify version-dependent claims from recorded evidence; ask through the router only when the relevant ECC/S/4/Cloud version remains unknown
- ห้ามแนะนำ modification เป็น first option
- ห้ามใช้ internal API ใน S/4 Cloud / ABAP Cloud
- Released APIs only, OData v2/v4 binding

## 🔍 Clarifying

```
Q1: SAP version?
  A) ECC 6.0   B) S/4HANA on-premise   C) S/4HANA Private Cloud
  D) S/4HANA Public Cloud   E) อื่นๆ (B1, ByDesign)

Q2: Module หลัก? (เลือกได้หลาย)
  A) FI/CO   B) MM   C) SD   D) PP   E) HR/SuccessFactors   F) อื่นๆ

Q3: Custom code approach?
  A) Classic ABAP (in-stack)   B) ABAP Cloud / RAP (Recommended for new)
  C) BTP side-by-side extension   D) ยังไม่รู้ — แนะนำ

Q4: UI?
  A) Fiori (Recommended for S/4)   B) SAP GUI   C) Custom (React/Vue + OData)   D) ผสม
```

## ขอบเขต

### Editions
| Edition | DB | UI | ABAP | Customization |
|---------|----|----|------|---------------|
| ECC 6.0 | Any | GUI/Web Dynpro | Classic | Free | EOL 2027/2030 |
| S/4HANA on-prem | HANA | Fiori + GUI | ABAP + Cloud-ready | Limited |
| S/4HANA Private Cloud | HANA | Fiori | ABAP (some restriction) | Restricted |
| S/4HANA Public Cloud | HANA | Fiori only | **ABAP Cloud only (RAP)** | BTP only |

### Modules
- **FI/CO**: GL, AP/AR, AA; cost/profit center, CO-PA. S/4: **Universal Journal (ACDOCA)**
- **MM/SD**: PR→PO→GR→IR; Quote→SO→Delivery→Billing. S/4: **Business Partner (BP)**
- **PP**: BOM/Routing/Production Order; **MRP Live** (S/4)
- **HR**: ECC HCM → push เลิก; **SuccessFactors** + integration (CI)
- PM/QM/PS

### ABAP — Classic vs Cloud

**Classic** (ECC + S/4 on-prem): SE38/SE11/SE80, BAPI, BAdI, ALV (`cl_salv_table`)

**ABAP Cloud / RAP** (S/4 Cloud, recommended new):
- **CDS Views** (annotation-driven), **RAP** (Behavior Definition + Implementation)
- Tools: ADT in Eclipse / BAS

Quality: ATC, the project's version-control workflow (abapGit when adopted), Clean ABAP, ABAP Unit

### Integration

| Pattern | Use | Tool |
|---------|-----|------|
| BAPI/RFC | Sync function | SAP JCo/.NET Connector |
| IDoc | Async EDI-like | ALE, WE20 |
| OData | REST จาก CDS/Gateway | SEGW (legacy) → RAP (modern) |
| SOAP/REST | Web service | SOAMANAGER / ICF / RAP |
| Event Mesh | Pub/sub | BTP Event Mesh |

Middleware: **CPI** (recommended) > PI/PO (legacy, EOL); **API Mgmt** (BTP)

### S/4HANA Migration

| Approach | When |
|----------|------|
| **Greenfield** | Heavy customization, business reengineering |
| **Brownfield** | Preserve config+data+code; in-place upgrade |
| **Bluefield** | Multi-system consolidation, partial redesign |

Pre-Check: Readiness Check 2.0, SI Check, Custom Code Migration App, Maintenance Planner, **DMO**

Key Simplification:
- Customer/Vendor → BP
- Material 18→40 char
- BSEG/BSAS/BSAD/BSIS/BSID → ACDOCA
- CO-PA: Account-based default

### BTP
- App Dev: CAP (Node/Java), RAP (ABAP)
- Integration: CPI, API Mgmt, Event Mesh
- Data: Datasphere, SAC, HANA Cloud
- AI: Joule, AI Foundation
- **Clean Core** — extension อยู่ BTP, keep S/4 standard

### Fiori
- SAPUI5 (= OpenUI5 OSS)
- **Fiori Elements** (metadata-driven, no/low code)
- Freestyle SAPUI5 (full custom)
- Tools: BAS

### TH Localization
- WHT (PND 1/3/53/54), VAT (Phor.Por.30)
- e-Tax invoice + e-Receipt (RD)
- Payroll TH: SSO 5%, PND 1/91, 50 ทวิ
- ตรวจ SAP Note ล่าสุด — RD update บ่อย

### Methodology
- **SAP Activate** (Discover/Prepare/Explore/Realize/Deploy/Run)
- **Fit-to-Standard** ก่อน custom

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| SAP version-specific (ECC/S/4/Cloud) | `plan` with the sap domain reference |
| ABAP / RAP / CDS / Fiori | `plan` with the sap domain reference |
| Integration (BAPI/IDoc/RFC/OData/CPI) | `plan` with the sap domain reference |
| S/4 migration | `plan` with the sap domain reference |
| TH SAP localization | `plan` with the sap domain reference |
| Generic accounting (non-SAP) | → `plan` with the erp domain reference |
| Banking outside SAP | → `plan` with the fintech domain reference |
| Custom SAP UI (React/Vue + OData) | → `build` (`plan` with the sap domain reference ส่ง OData spec) |

## Best Practices

- **Fit-to-Standard ก่อน custom**
- Extension hierarchy: Configuration > Key User > Developer (BTP) > Modification (last resort)
- Use the project's authorized ABAP version-control workflow; evaluate abapGit where appropriate
- **ATC** ใน CI/CD — block transport ถ้า fail
- **CDS view** ก่อน raw SQL
- **HANA = analytic**; SAP standard read ก่อน custom
- **S/4 simplification check** ก่อน custom code
- **BTP side-by-side** ก่อน in-stack extension
