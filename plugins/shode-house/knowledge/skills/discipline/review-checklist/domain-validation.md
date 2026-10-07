---
name: domain-validation
description: Reference (lazy-load) ของ `review-checklist` — กติกาว่า diff แบบไหนต้องให้ domain expert ลงชื่อ + วิธี route ไปหาคนที่ใช่. โหลดเมื่อ diff แตะ business rule / money / regulation
---

```lazy-load-contract
LOAD: skills/discipline/review-checklist/domain-validation.md
WHEN: diff_touches_business_rule=true OR diff_touches in {money,regulation,PII}
OWNER: code-reviewer
REQUIRED-BEFORE: merge_approval
```

# Domain validation axis (conditional)

changed code แตะ business rule ของ domain ไหน → **domain expert ตัวนั้นต้อง validate**; keywords ช่วยหา scope แล้วตรวจ code path จริง Parallel กับ reviewers อื่นเมื่อ host รองรับและงานอิสระ มิฉะนั้น serialize โดยรักษา independent verdict
money / regulation = **ห้าม merge โดยไม่มีลายเซ็นของ domain expert**

| keyword ใน diff | expert |
|---|---|
| payment · ledger · settlement · wallet | fintech-expert |
| policy · claim · premium · underwriting | insurance-expert |
| SAP · ABAP · IDoc · BAPI | sap-expert |
| order · matching · orderbook · position | trading-expert |
| accounting · GL · inventory · costing | erp-expert |
| booking · availability · yield · overbooking | booking-expert |
| cart · promotion · checkout · catalog | ecommerce-expert |

ตารางเต็ม + tie-break เมื่อ diff แตะหลาย domain → `report-format.md` § Domain routing

**Verdict rule**: domain expert ต้อง cite primary source (regulation clause / spec section) ไม่ใช่ความจำ — ดู `domain-core` § Citation contract
ไม่มี expert ตัวนั้นใน session → **BLOCKED** ไม่ใช่ PASS
