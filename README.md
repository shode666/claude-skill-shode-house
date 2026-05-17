# shode-house

> Multi-agent ทีม software house สำเร็จรูป — 15 expert agents + workflow discipline

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages

ออกแบบเน้น: **lean • token-optimized • production-ready • domain-driven • ภาษาไทย**

[![Version](https://img.shields.io/badge/version-2.8.0-blue.svg)](https://github.com/shode666/claude-skill-shode-house)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🚀 Install

### Claude Code (CLI/terminal)
```bash
/plugin marketplace add shode666/claude-skill-shode-house
/plugin install shode-house@shode-house
```

### Cowork (desktop app)
- Drag & drop `.plugin` file → Cowork window
- หรือ Settings → Plugins → Install from file

### Update (เครื่องอื่น)
```bash
/plugin marketplace update shode-house
/plugin install shode-house@shode-house
```

---

## 🧭 5 Core Philosophy

ทุก agent ยึดเป็นอันดับหนึ่ง:

1. **NO MAGIC** — ห้ามเดา. Path/service ไม่รู้ → `Glob`/`Grep` หาก่อน. Assumption explicit + risk
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0/R1/R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

---

## 👥 ทีม (15 agents)

### Core (8)
| Key | ชื่อ | Model | Role |
|-----|------|-------|------|
| Or | **Oliver** | sonnet | Orchestrator — engagement lead, triage, broadcast, approval gates |
| Ba | **Bella** | sonnet | BA — BRD/FRD, Event Storming, RTM (bd) |
| Sa | **Sara** | **opus** | SA — C4, ADR, NFR, threat model (STRIDE), DR/BCP |
| Dv | **Dave** | sonnet | Polyglot Dev (parallelizable, 14 languages, lazy-load refs) |
| Cr | **Chris** | sonnet | Code Review (7 มิติ) + Unit Test + mutation testing |
| Qa | **Quinn** | sonnet | QA — Integration/E2E/Pen test, contract, perf, chaos |
| Do | **Aaron** | sonnet | DevOps — Docker, CI/CD, K8s, observability, worktree pattern |
| Ux | **Uma** | sonnet | UX/UI + Design System + a11y (WCAG) + Figma handoff |

### Domain Experts (7)
| Key | ชื่อ | Model | Domain |
|-----|------|-------|--------|
| Fe | **Felix** | **opus** | Fintech — payment, ledger, ISO 8583/20022, PCI-DSS, KYC/AML |
| Ee | **Elena** | sonnet | ERP/Accounting — GL, AR/AP, MRP, IFRS 15/16, consolidation |
| Sm | **Sam** | **opus** | SAP — ECC + S/4HANA, ABAP, Fiori, BTP, BAPI/IDoc, S/4 migration |
| Te | **Tara** | **opus** | Trading — OMS, matching, FIX, microstructure, clearing |
| Ie | **Iris** | **opus** | Insurance — policy, claim, IFRS 17, reinsurance, OIC |
| Bk | **Brooke** | sonnet | Booking — PMS, channel manager, yield, overbooking |
| Ec | **Emma** | sonnet | E-commerce — catalog, cart, promo, marketplace, fraud |

### Model Strategy
- **Opus** (5): judgment-critical (architecture, money, SAP, insurance reg, trading microstructure)
- **Sonnet** (10): execution + structured patterns (capable + fast)

---

## ⚡ Slash Commands (7)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:init [project-name]` 🆕 | **Init wizard** — interactive scaffold (option-style 6 ข้อ + Aaron+Bella+Oliver setup) |
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:spec-only [ระบบ]` | Spec อย่างเดียว — proposal/estimation (ไม่ implement) |
| `/shode-house:design-system [ระบบ]` | Full design — BA → Domain → SA → summary |
| `/shode-house:implement [feature]` | Implement — Dave + Chris review/unit + Quinn integration |
| `/shode-house:review [path\|jira\|bug]` | Code review — Chris 7 มิติ + Quinn security + Domain |
| `/shode-house:setup-project [stack]` | Aaron setup — Docker-first, CI/CD, observability |

---

## 🎯 meeting Skill (Foundation)

**`/shode-house:meeting`** — entry-point "ประชุมทีม shode-house"

รวม: 5 Philosophy + clarifying (option-style) + routing + conflict resolution + bd tracking + workflow discipline + safety + universal rules

Trigger เมื่อ user mention "shode-house", "ประชุมทีม", "Oliver", หรือชื่อ agent อื่น

---

## 🔁 Workflow Discipline (Archon + Sandcastle inspired)

| Concept | Implementation |
|---------|----------------|
| **Phase Contract** | Oliver enforce ห้าม jump phase (clarify → design → impl → review → integration → deploy) |
| **Lifecycle Hooks** 🆕 | pre/post hook ทุก phase — Aaron auto-trigger (lint/test/scan) |
| **Loop with Exit** | Dave/Quinn — max 5 iter, binary pass/fail, fail max → escalate Sara |
| **Approval Gates** | 6 standard gates: pre-merge, pre-deploy-{staging,uat,prod}, pre-data-migration, pre-destructive |
| **Worktree Isolation** | Aaron Makefile pattern สำหรับ parallel-safe dev |
| **Engagement Mode** 🆕 | AFK / Interactive / Hybrid (default) — เลือกใน Phase 2 |
| **Pluggable Tracker** 🆕 | beads (default) / GitHub / Linear / Jira / Asana |
| **UI Test Hard Gate** 🆕 v2.4 | Quinn trigger condition + evidence template + Aaron auto-scaffold + `pre-merge-ui` gate |
| **Project Evidence Protocol** 🆕 v2.4 | NO MAGIC ext — ห้ามเดาจาก real-world; cite `[file:line]` หรือ `[output: cmd]` |

---

## 💬 Clarifying Style

ทุก agent ใช้ **`AskUserQuestion` tool ก่อนเสมอ** (Cowork + Claude Code):

```
Q: ใช้ database อะไร?
A) PostgreSQL (Recommended — relational + JSON)
B) MySQL (familiar)
C) MongoDB (document)
D) อื่นๆ
```

- 2-4 options + Recommend ตัวแรก + reason 1 บรรทัด
- Batch ≤ 4 คำถามต่อ call → ลด round-trip
- ห้ามคำถามเปิด

---

## 🌐 Polyglot Dave — 14 Languages (lazy-load)

Dave อ่าน best practice **เฉพาะภาษาที่ใช้** จาก `references/languages/<lang>.md` → ประหยัด token

### Startup tier (modern)
TypeScript, Python, JavaScript, Go, SQL, Kotlin, Swift, Rust, PHP, Dart

### Enterprise tier (business)
Java, C#, C++, COBOL/PL-SQL/VBA

### Generic Patterns
- `references/patterns/general.md` — DB/API/Observability/FeatureFlag/AI integration
- `references/modern-stack.md` — 2025+ tech recommendation (Edge/Serverless/RAG/Drizzle/Bun/Biome)

---

## 🔌 Bundled MCPs

| MCP | ใช้แทน | ประโยชน์ |
|-----|--------|----------|
| **[Context7](https://context7.com)** | `WebFetch` lib docs | Library docs ตาม version, snippet เป๊ะ — token-saving |

Prerequisite: `brew install node` (Context7 ใช้ npx)

---

## 🧵 Task Tracking — beads (bd)

ทีมใช้ **[beads](https://github.com/steveyegge/beads)** เป็น single source of truth (ไม่ใช่ markdown TODO):

```bash
brew install beads
cd your-project && bd init
bd create "FR-101: POST /refund" -t functional-req --blocked-by 1
bd ready --json    # next unblocked tasks
bd graph --format=mermaid    # auto dep diagram
```

- RTM (BR → FR → US → ADR → Test → Code) อยู่ใน bd
- Agent claim ด้วย `bd ready` → close เมื่อเสร็จ
- Commit message ref `[bd:N]`
- Markdown artifact (BRD/ADR/spec) save `outputs/` แต่ status = bd

---

## 🛡️ Safety Discipline

**Destructive actions** ขออนุญาตเสมอ (R0):
- `git push --force` (main), `git reset --hard`
- `DROP TABLE`, `DELETE without WHERE`
- `rm -rf` กว้าง, delete prod resource
- Edit migration ที่ apply prod แล้ว
- Modify auth/IAM permission

Pattern: ระบุ action + impact + rollback → ขอ confirm → execute

---

## 🎨 Output Format Standard

```markdown
# [Agent prefix] Title

## ความเข้าใจ / Context
## [main content]
## ⚠️ Risks / Edge Cases
## 🔗 Hand-off
## 📦 Artifacts
## ❓ Open Questions
```

---

## 🏛️ Principles

- **Right answer > first answer** — ห้าม "พอใช้ได้"
- **Evidence-based** — quote ID/version (ISO/IFRS/OWASP/PCI)
- **Domain-aware vocabulary**
- **Test before claim "done"**
- **Reproducible** — git clone → run = work
- **Money = Decimal** — ห้าม float
- **Lazy-load reference** สำหรับ token-saving
- **Modular** — เพิ่ม/ลด agent ง่าย (drop file + update routing table)

---

## 📁 Architecture

```
shode-house/
├── .claude-plugin/         manifest + marketplace
├── skills/sd/              foundation (5 philosophy + workflow + routing)
├── agents/                 15 expert agents (lean, focus expertise)
├── commands/               6 slash commands (workflow templates)
└── references/
    ├── modern-stack.md     2025+ tech (Sara/Aaron lazy-load)
    ├── patterns/
    │   └── general.md      DB/API/Observability (Dave lazy-load)
    └── languages/
        └── <14 files>      per-language best practice (Dave lazy-load)
```

---

## 🤝 Adding/Removing Agent

**Add new domain expert**:
1. Drop `agents/<name>.md` (ตาม template ของ agent ที่มีอยู่)
2. Update routing table ใน `skills/sd/SKILL.md`
3. Bump version, repackage

**Remove agent**: ลบไฟล์ + remove จาก routing table

---

## 🔗 Inspirations

- **Workflow discipline**: [Archon](https://github.com/coleam00/archon) (phase contract + loop + approval gates + worktree)
- **Productivity skills**: [mattpocock/skills](https://github.com/mattpocock/skills) (caveman/grill-me concept)
- **Issue tracker**: [beads](https://github.com/steveyegge/beads)
- **Domain knowledge**: real-world projects (Thai banking, ERP, insurance, hospitality)

---

## 📜 License

MIT — use freely, improve freely, contribute back welcome
