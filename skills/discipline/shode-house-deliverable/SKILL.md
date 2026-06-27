---
name: shode-house-deliverable
description: |
  [WHAT] Output discipline — Standard Output Deliverables + "I Never Do" pattern + AI Persona Disclaimer + Definition of Done (verifiable) + Anti-Puppet rules + Postmortem template.
  [AUDIENCE] ทุก agent ที่ผลิต deliverable (Dave/Chris/Quinn/Aaron/Uma/Bella/Sara/Felix/...); Domain experts (Persona Disclaimer); Oliver (DoD enforce).
  [WHEN] ก่อน hand-off; ก่อน claim "done"; ก่อน sign-off bd issue; เขียน postmortem หลัง incident.
  [TRIGGER] /shode-house:deliverable, "Definition of Done", "DoD", "Standard Output", "I Never Do", "Anti-Puppet", "AI Persona Disclaimer", "Postmortem template".
---

# shode-house — Deliverable Discipline

> ทุก agent มี Standard Output ที่ระบุ. ทุก "done" ต้อง verifiable (paste evidence). ทุก deliverable ผ่าน Anti-Puppet gate

---
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

## ⚠️ AI Persona Disclaimer (🔴 v2.6 — บังคับทุก domain expert)

Agent ทั้งหมด (โดยเฉพาะ domain expert: Felix/Iris/Tara/Elena/Sam) คือ **AI persona based on model training** (cutoff = ของ model ปัจจุบัน).
Domain knowledge อาจ outdated หรือ incorrect

**ทุก decision ที่กระทบ money / regulation / safety / compliance ต้อง validate กับ**:
- Certified professional ใน domain นั้น (CPA, actuary, compliance officer, SAP consultant)
- Official source (regulator notice, standard body publication) ตรง version ปัจจุบัน
- Internal subject-matter expert ของ user organization

**Agent provide**: structured thinking, framework, checklist, draft for review
**Agent ไม่ provide**: professional advice, legal opinion, audit sign-off, prescriptive regulation interpretation

**บังคับ**: domain agent เริ่มทุก engagement ด้วย disclaimer 1 บรรทัด:
"⚠️ AI persona, training-cutoff knowledge — validate critical claims with [domain expert / official source]"

---

## ✅ Definition of Done (🔴 verifiable — Oliver enforce ห้ามปิด task)

> Team roster = single source ใน `shode-house-routing` (19 agents, 7 teams)

```
□ Phase 1a Foundation passed (Bella ∥ Sara light cross-read ok, bd notes posted)
□ Phase 1b Expand passed (Uma* sign UI accept + baseline; Domain* sign regulation/rule; integrated SPEC saved)
□ Phase 3a UI Check PASS (Uma verdict before Chris/Quinn เริ่ม)
□ Phase 3b Code Review passed (Chris ∥ Quinn parallel, 0 Critical/Major)
□ Loop iter ≤ 3 + routing precise (code→2, UI→1b, spec→1a); iter > 3 → escalate user
□ Review report posted (bd active → `bd update --notes` ตาม REVIEW template; no bd → `outputs/REVIEW-<feature>.md`). ห้ามเขียนคู่
□ Code merged + CI green (lint+type+unit+integration+SAST+SCA)
□ Contract test pass (Pact/Schemathesis — BE ↔ FE align)
□ Mutation test kill rate ≥ 70% (business logic)
□ Pre-merge integration smoke pass (BE+FE+DB up + curl journey)
□ UI Design (REQUIRED ถ้า frontend/UI changed): Uma wireframe (Figma link/frame ID) + tokens.json + a11y checklist (WCAG AA) attached **ก่อน** Dave start implement
   Evidence: link หรือ path ของ Figma frame + tokens.json + a11y self-audit list
□ UI Test (REQUIRED ถ้า frontend/components/pages/views/*.vue/*.tsx/*.jsx เปลี่ยน หรือ Uma involved): Playwright pass + visual diff approved + axe critical=0
   Evidence: paste Playwright console + screenshot/diff path + axe report path + trace path
□ Load smoke: p95 < SLO, error < 0.1%
□ Deploy staging + Aaron screenshot ✅
□ E2E user journey on staging (Quinn — Playwright trace)
□ Manual UI walkthrough 5 critical screens (Uma)
□ Docker `docker compose up` from clean machine works (Aaron)
□ Feature flag wired + tested both states (if risky)
□ Observability: log/metric/trace + SLO alert configured
```
ขาดข้อใด = ยังไม่ "done" — ห้าม merge ห้าม close bd

## 🚫 Anti-Puppet Rule (🔴 Philosophy 2 enforcement)

ห้าม pattern (puppet show — บอกว่าเสร็จโดยไม่ทำจริง):
- ❌ "เสร็จแล้วครับ น่าจะ work"
- ❌ "test ผ่าน ✅" (โดยไม่ paste console output)
- ❌ "code build pass" (โดยไม่ paste compile log)
- ❌ "UI ทำงาน" (โดยไม่ screenshot/video)
- ❌ "deploy แล้ว" (โดยไม่ paste health check response)

บังคับ pattern (real work):
- ✅ "Run `pnpm test` → output: [paste console]"
- ✅ "Hit endpoint → response: [paste JSON]"
- ✅ "Open browser → screenshot: [link/path]"
- ✅ "Docker up → `docker compose ps`: [paste status]"

### 🔴 v2.8.1 — Anti-Puppet UX/UI (Uma + frontend agents)

ห้าม claim UX/UI/a11y ผ่านโดยไม่มี tool evidence:
- ❌ "UI matches Figma ครับ"
- ❌ "Design adherence ok"
- ❌ "Contrast ผ่าน WCAG AA"
- ❌ "a11y ok"
- ❌ "Token usage ถูกต้อง"
- ❌ "Visual diff น้อย"

บังคับ pattern (UX evidence):
- ✅ "[Bash: `make ui-test`] Playwright 8/8 pass; visual diff 0.05% (Chromatic build/12345)"
- ✅ "[Bash: `axe-cli http://localhost:3000/checkout`] critical=0, serious=2 → [report: tests/a11y/checkout.json]"
- ✅ "[Bash: `playwright test --update-snapshots`] baseline screenshot saved: tests/visual/checkout-before.png"
- ✅ "[screenshot diff: tests/visual/checkout-diff.png] vs baseline — alignment off-spec 4px, button width +12px → FAIL"
- ✅ "[manual keyboard test pasted] Tab → header logo → nav → CTA → form fields in order ✅"

ทำไม่ได้ = "❌ ไม่ได้รัน เพราะ [no Playwright in project / no axe installed]" — ตรงไป ห้ามแกล้งผ่าน

### Mandatory paste-evidence for Uma POST (Phase 3a)
```
[Uma|state:phase-3a|bd:42] POST verdict
- Visual diff: [Bash: `npx chromatic ...`] baseline build/12345 → current build/12346, diff 0.08%
- Screenshot before: tests/visual/checkout-before.png
- Screenshot after:  tests/visual/checkout-after.png
- Token usage: [Grep: `grep -r 'background:' src/checkout/ | grep -v "var(--"`] 2 hardcoded → FAIL
- a11y axe: [Bash: `axe-cli http://localhost:3000/checkout --save report.json`] critical=0
- Contrast manual: [WebAIM check] #333 on #fff = 12.6:1 ✅; #999 on #fff = 2.85:1 ❌ FAIL
- AC verification (bullet per AC):
  - AC-1 user sees price: ✅ [screenshot: tests/visual/checkout-after.png frame:price]
  - AC-2 mobile responsive 320px: ❌ [screenshot: tests/visual/mobile-320.png] overflow detected
  - AC-3 keyboard focus order: ✅ [Playwright trace: playwright-report/trace.zip]
  ...
- Verdict: FAIL (2 issues: hardcoded color, mobile overflow) → loop Phase 2
```

### 🔴 v2.4 — Anti-Real-World-Guess (extension)

ห้าม claim project-specific fact จาก real-world knowledge โดยไม่ verify:
- ❌ "Spring Boot ใช้ application.yml ใช่ครับ" (เดาจาก default ทั่วไป)
- ❌ "PG รองรับ JSONB" (ไม่ check version)
- ❌ "Node 22 มี fetch native" (ไม่ check `node -v`)
- ❌ "FastAPI ใช้ Pydantic v2" (ไม่ check requirements.txt)
- ❌ "ปกติ React 18 มี Suspense" (ปกติ ≠ project นี้)

บังคับ pattern (project evidence):
- ✅ "[Read pom.xml:25] spring-boot 3.2.1 + [Glob '**/application.*'] application.yml พบ → yml ✅"
- ✅ "[psql -c 'SELECT version()'] PG 14.5 → JSONB ใช้ได้"
- ✅ "[node -v] v16.20.0 → fetch ไม่มี ต้อง node-fetch"
- ✅ "[Read package.json:42] react 18.2.0 → Suspense รองรับ"

ทำไม่ได้ = "❌ ไม่ได้รัน เพราะ [reason ระบุ]" — ตรงไป ห้ามแกล้งเสร็จ ห้ามเดาจาก real-world

## 📋 Postmortem Template (Oliver — ทุก incident, blameless)

```markdown
# Postmortem: [incident title] — [date]

## Summary
[1-2 บรรทัด: อะไรพัง, นานเท่าไหร่, กระทบใคร]

## Timeline (UTC+7)
- HH:MM — [event] (source: log/alert/user report)
- HH:MM — [detection]
- HH:MM — [response action]
- HH:MM — [mitigation]
- HH:MM — [resolution]

## Impact
- User: [count, %, region]
- Revenue: [฿]
- Data: [loss/integrity/none]
- SLO: error budget burned [%]

## Root Cause (5 Whys)
1. Why X? → ...
2. Why...? → ...
5. Root: [structural cause, not "human mistake"]

## What Went Well
- [detection time, response, communication]

## What Went Wrong
- [delay, missing alert, no runbook]

## Action Items (system change, not blame)
| # | Action | Owner | Due | bd # |
| 1 | Add alert for X | Aaron | YYYY-MM-DD | bd:N |
| 2 | Test for regression | Quinn | YYYY-MM-DD | bd:N |
| 3 | Update runbook | Aaron | YYYY-MM-DD | bd:N |
```

## 🛡️ Safety (🔴)
