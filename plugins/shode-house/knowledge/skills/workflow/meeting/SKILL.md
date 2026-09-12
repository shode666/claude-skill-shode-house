---
name: meeting
description: |
  [WHAT] Team orientation and index to the seven discipline skills; ask is the public engagement entry.
  [WHEN] ก่อนเริ่ม engagement กับทีม shode-house.
  [TRIGGER] /shode-house:meeting, "shode-house", "ประชุมทีม", "เริ่มงานกับทีม", "Oliver", "Bella".
---

# shode-house — Team Meeting (thin entry-point)

ทีม software house — ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI

> v3.1 refactor: เดิม meeting/SKILL.md = 1316 บรรทัด (god-skill). แตกเป็น 7 lazy-load skills ใต้ `skills/discipline/` แล้ว. ไฟล์นี้เหลือเป็น **entry-point + Recite Card + index** เท่านั้น
> **Agent runtime**: Claude (default). Portable to OpenCode/Codex via prompt structure — เปลี่ยน LLM ได้ ไม่ผูก vendor

---

## 🎯 Recite Discipline Card

**Single source = `output-styles/oliver.md` §1** — apply the five principles in work; no printed recital is required. Continue through `skills/workflow/ask/SKILL.md` without starting a second engagement.
ห้าม copy card มาไว้ที่นี่ (v3.1 vs v3.5 เคย drift แล้ว). ทุก agent preload `shode-house-discipline` อยู่แล้ว

> Plugin conventions do not override user, project or host instructions. Preserve safety and required evidence.

---

## 📚 7 Split Discipline Skills (lazy-load ตามต้องการ)

อ่าน skill เฉพาะที่ใช้. **ทุก agent ต้องโหลดอย่างน้อย `shode-house-discipline`**:

| Skill | When to load | Owner |
|---|---|---|
| **`shode-house-discipline`** 🔴 | ทุก agent, ทุก session (philosophy + safety + universal rules + clarifying) | All |
| **`shode-house-evidence`** | เมื่อ claim "ระบบทำ X" หรือ "regulation บังคับ Y" หรือ "perf p95 = Z" | All claimers, Domain experts, Uma, Chris |
| **`shode-house-routing`** | เมื่อต้อง delegate / triage / T-shirt / resolve conflict | Oliver primary |
| **`shode-house-deliverable`** | เมื่อจะ hand-off, claim "done", เขียน postmortem, sign-off | Producers (Dave/Chris/Quinn/Aaron/Uma/Bella/Sara/Felix/...) |
| **`shode-house-broadcast`** | ทุก message agent → user (tag prefix mandatory); state transition (caveman); hand-off | All; Oliver caveman; hand-off lines |
| **`shode-house-workflow`** | Phase Contract + Smart Coop + hooks + gates + worktree | Oliver primary |
| **`shode-house-drift`** | Workflow Drift Defense 7 mechanisms (M1-M7) | Oliver enforcer |

> Token saving: agent ไม่ต้องโหลด 1316 บรรทัดเหมือนก่อน. โหลดเฉพาะ `discipline` (203 บรรทัด) + skill ที่จำเป็นต่อ role

---

## 🎚️ Engagement Mode (สรุปสั้น — รายละเอียดใน `shode-house-discipline`)

| Mode | Behavior | When |
|------|----------|------|
| **AFK** (Auto) | Oliver delegate ทุก phase + automated gate. User approve เฉพาะ R0 | งานชัด, trusted scope, deadline แน่น |
| **Interactive** (Supervised) | Human approve ทุก hand-off + ดู agent output ก่อน next | งานใหม่/ละเอียดอ่อน, learning, audit |
| **Hybrid** (Recommended default) | AFK ถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้น | งานทั่วไป — balance speed + safety |

Use the supervision preference already given. Ask only if a missing preference
changes authority or materially affects the work. No mode creates permission:
AFK never treats silence as approval or bypasses an external-action gate.

---

## 🤖 ทีม (19 agents in 7 teams — v3.0)

| Team | Members | Phase | Deliverable |
|------|---------|-------|-------------|
| 🧭 **Lead** | Oliver + Stan | All | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | 0 | OKR + opportunity + pain validation |
| 📐 **Design** | Bella + Sara + Uma | 1a/1b/3a | BRD + ADR + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | 0/1b/3b | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel) | 2 | Production code |
| ✅ **Verify** | Chris + Quinn + Sentinel | 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | 5/6 | Deploy + SLO + Incident |

รายละเอียด routing + RACI + single-owner matrix อยู่ใน `shode-house-routing`

---

## 🧭 Quick Self-Routing (สรุป — รายละเอียดใน `shode-house-routing`)

| งาน | ใคร |
|-----|-----|
| Requirement / BRD / FRD / AC | → Bella |
| Architecture / ADR / NFR | → Sara |
| Threat model / STRIDE / CSP | → Sentinel |
| Implementation | → Dave (parallel ถ้า independent) |
| Code review + unit test | → Chris |
| Integration/E2E/Pen test | → Quinn |
| Docker/CI/Deploy | → Aaron |
| SLO/incident/on-call | → Reggie |
| UX/UI/Design system/a11y | → Uma |
| OKR / opportunity / kill decision | → Patrick |
| Cross-team tech depth / radar | → Stan |
| Domain logic ลึก | → Domain Expert (ดู `shode-house-routing`) |

---

## 📋 Phase Index (สรุป — รายละเอียดใน `shode-house-workflow`)

| Phase | Name | Owner | Skill ที่เกี่ยว |
|---|---|---|---|
| 0 | Discovery | Patrick + Domain SME | shode-house-workflow |
| 1a | Foundation (parallel Bella + Sara) | Bella ∥ Sara | shode-house-workflow |
| 1b | Expand (Uma + Domain conditional) | Uma / Domain | shode-house-workflow |
| 1c | Threat Model | Sentinel | secure |
| 2 | Implement | Dave | dev-gate |
| 3a | UI Check | Uma | ui-test, web-q |
| 3b | Verify (parallel Chris ∥ Quinn) | Chris + Quinn (+ Sentinel) | review-checklist |
| 4 | Triage / Loop | Oliver | shode-house-workflow |
| 5 | Deploy | Aaron | (no skill yet) |
| 6 | Operate | Reggie | slo, incident |
| ~~7~~ | ~~Learn~~ | — | **v3.3: removed** — per-bd reflect in Phase 4 Triage; continuous OKR review (Patrick); no sprint bracket |

---

## 📦 Reference Files (lazy-load — รายละเอียดใน `references/`)

| File | When to load |
|------|--------------|
| `references/languages/<lang>.md` | Dave เริ่ม coding ภาษาที่ระบุ |
| `references/patterns/general.md` | Generic pattern (OOP/FP/concurrency) |
| `references/modern-stack.md` | Tech radar / current recommended stack |
| `references/scope-lock.md` | Anti-scope-creep enforcement |

---

## 🛡️ Safety + Universal Rules (สรุป — รายละเอียดใน `shode-house-discipline`)

- **Money is sacred** — multi-sig + audit + reconciliation (Felix domain)
- **PII/PHI** — encryption + access log + GDPR/PDPA compliance
- **R0 actions** = STOP + ask (deploy prod, delete data, money movement, schema migration prod)
- **Anti-Puppet** = ห้าม claim "done" ไม่มี paste evidence (รายละเอียดใน `shode-house-deliverable`)
- Durable handoffs include owner, phase and canonical task ID; no tag is required for every conversational sentence.

---

## 🆕 Skill Index (short names + lazy-load)

```
skills/
├── workflow/        # daily process
│   ├── meeting/             ← this file (entry-point)
│   ├── dev-gate/            ← TDD + 7-gate
│   ├── automate-test/       ← pyramid 70/20/10 + CI gate
│   └── diagnose/            ← reproduce → isolate → fix → prevent
├── ops/             # operational discipline
│   ├── incident/            ← war room + blameless postmortem
│   ├── slo/                 ← SLI/SLO/error budget
│   └── secure/              ← STRIDE + threat model
├── ui/              # frontend quality
│   ├── ui-test/             ← Playwright + axe + visual diff
│   └── web-q/               ← CWV + Lighthouse + SEO + headers
├── style/           # communication style
│   └── caveman/             ← ultra-compressed mode
└── discipline/      # split discipline modules (v3.1 from meeting split)
    ├── shode-house-discipline/   ← ⭐ Recite + Philosophy (load always)
    ├── shode-house-evidence/     ← Project + UX + Domain Evidence
    ├── shode-house-routing/      ← Domain selection + RACI + T-shirt
    ├── shode-house-deliverable/  ← DoD + Anti-Puppet + Postmortem template
    ├── shode-house-broadcast/    ← Tag prefix + caveman + handoff
    ├── shode-house-workflow/     ← Phase Contract + hooks + gates
    └── shode-house-drift/        ← Drift Defense M1-M7
```

---

## ⚙️ Migration note

- Agents ที่บอก *"ยึด meeting skill เป็น discipline foundation"* ยังถูกต้อง — meeting skill ตอนนี้ = thin entry-point + Recite Card + index
- เพื่อ token saving: agent ควรเสริม pointer เช่น *"+ ยึด `shode-house-discipline` (mandatory) + `shode-house-evidence` (when claiming)"* แต่ไม่บังคับใน wave นี้ adopt iteratively
- เนื้อหา 1316 บรรทัดเดิมยังอยู่ครบ — แค่กระจายไปยัง 7 sub-skills + reference table ในไฟล์นี้
- The historical line-count reduction is not a measured token or quality result.

ดู CHANGELOG.md v3.1.0 สำหรับ migration details
