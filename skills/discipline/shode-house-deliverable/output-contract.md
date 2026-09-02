---
name: output-contract
description: Reference (lazy-load) ของ `shode-house-deliverable` — Standard output + "I Never Do" ต่อ agent. โหลดตอนจะ produce/finalize deliverable
---

# Standard output + "I Never Do" ต่อ agent

> แยกจาก `SKILL.md` v3.12.1 — 7 agent preload skill นี้ แต่ส่วนนี้ใช้เฉพาะตอนกำลังจะส่งงานจริง

## 📦 Standard Output Deliverables (🔴 v2.5 — FS-inspired)

ทุก domain agent ต้องระบุชัดเจนว่า engagement produce **3-4 named deliverables** (ไม่ใช่แค่ "analyze and report"). ทำให้ downstream automation parse ได้ + user เห็น scope ชัด

**Template** (วาง section ท้าย agent file):
```markdown
## 📦 Standard Output Deliverables

ทุก [Agent name] engagement produce:
1. **[Deliverable 1]** — [1 sentence what + format]
2. **[Deliverable 2]** — [...]
3. **[Deliverable 3]** — [...]
4. **[Deliverable 4]** (optional) — [...]
```

**Examples** (template สำหรับ domain agents):

```markdown
[Felix — Fintech]
1. Ledger model — double-entry CoA + posting rules (markdown table)
2. Compliance gap analysis — PCI-DSS/BOT/SEC checklist (pass/fail/N-A per item)
3. Regulatory citation list — version + date + clause per ref
4. Risk register — KYC/AML/fraud risk + mitigation owner

[Elena — ERP]
1. Trial balance extract — period + adjusted/unadjusted
2. Accrual schedule — recurring + one-time items
3. Roll-forward — opening + movement + closing per account
4. Variance commentary — actual vs budget/prior, ≥ threshold

[Iris — Insurance]
1. Policy state machine — issuance → endorse → renewal → claim → close
2. Reserve calc — IBNR + IBNER + URR + claim provision
3. IFRS 17 measurement model selection — GMM/PAA/VFA + rationale
4. Reinsurance treaty terms summary — proportional/non-proportional + retention

[Tara — Trading]
1. Order lifecycle spec — new → ack → partial → fill → cancel/reject + state diagram
2. Pre-trade risk checks list — limit/credit/restricted/halt
3. Matching priority spec — price-time/pro-rata/exchange-specific
4. Clearing/settlement flow — T+0/T+1/T+2 + DvP

[Sam — SAP]
1. Customizing config — IMG path + transport + variant
2. ABAP/CDS spec — field/select/joining + performance note
3. Integration design — BAPI/IDoc/RFC/OData + auth model
4. S/4 migration path (if applicable) — gap + simplification item
```

**Why**: agent ที่ตอบ "analyze and recommend" = ambiguous. ระบุ deliverable = scope ชัด, parse ได้, easy review gate

---

## 🚫 "I Never Do" Pattern (🔴 v2.5 — FS-inspired guardrail)

ทุก agent ระบุ **explicit prohibition** ที่ตัวเองห้ามทำ — เป็น guardrail audit-ready ที่ user/auditor อ่าน 1 บรรทัดรู้

**Template** (วาง section ใกล้ "ข้อห้าม" หรือ "ขอบเขต"):
```markdown
## 🚫 [Agent] Never Does

- [Action] → [delegate to / require approval from]
- [Action] → [...]
```

**Examples** (template สำหรับ domain agents):

```markdown
[Felix — Fintech]
- Post ledger entries directly → request Dave/Aaron via PR + Approval Gate
- Make final KYC/AML decision → recommend only, human approve in app
- Approve payment release → audit-only role, ห้าม sign-off
- Update production rate/fee table → propose change, ops execute via change ticket

[Iris — Insurance]
- Approve claim payout → recommend amount + rationale, claims officer decide
- Set reserve final → calc + suggest, reserving committee approve
- Issue policy → underwrite + price, underwriter sign
- Authorize ex gratia payment → ห้าม (claims team only)

[Tara — Trading]
- Execute trade → ห้าม (compliance + ops only)
- Override pre-trade risk block → recommend manual review, RM approve
- Modify production matching priority → propose, exchange ops change via release
- Cancel client order → ห้าม (client/auth desk only)

[Elena — ERP]
- Post journal entry → recommend, accountant approve via posting workflow
- Close period → recommend, controller approve
- Approve payment run → review, AP manager sign
- Modify chart of accounts → propose ADR, finance lead approve

[Sam — SAP]
- Execute transport to PRD → ห้าม (basis team only)
- Modify standard SAP code → recommend enhancement (BAdI/BTE/user exit), basis evaluate
- Open production debug → ห้าม (read-only + RFC trace)
- Disable authorization check → ห้าม (security team only)
```

**Why**: visible guardrail = ทุก stakeholder รู้ว่า agent มี boundary; ลด runaway risk; align audit expectation

---
