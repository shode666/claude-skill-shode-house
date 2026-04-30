# shode-house

ทีมสำเร็จรูปสำหรับ software house — 15 agents (8 core + 7 domain experts) + 6 slash commands
ครอบคลุม ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI

ออกแบบเน้น **SOLID, clean code, non over-engineering, keep it simple** + **domain-driven** + ภาษาไทย

---

## ทีม (15 agents)

### Core team (8)

| Key | ชื่อ | Role |
|-----|------|------|
| Or | **Oliver** | Orchestrator — engagement lead, triage, coordination, brief status broadcast |
| Ba | **Bella** | Business Analyst — BRD/FRD, user stories, Event Storming, RTM |
| Sa | **Sara** | Solution Architect — C4, ADR, NFR, threat model (STRIDE), migration, DR/BCP |
| Dv | **Dave** | Developer (minion-style, parallelizable) — feature code, refactor, integrate |
| Cr | **Chris** | Code Reviewer + Unit Test — review 7 มิติ + test doubles + mutation testing |
| Qa | **Quinn** | QA Engineer — integration, E2E, contract, perf, chaos, security |
| Do | **Aaron** | DevOps Engineer — Docker, CI/CD, K8s, SRE, observability, Caddy/Traefik |
| Ux | **Uma** | UX/UI Designer — research, IA, wireframe, visual, design system, a11y (WCAG), Figma handoff |

### Model Strategy (per agent)

| Model | Agents | เหตุผล |
|-------|--------|--------|
| **Opus** | Sara, Felix, Sam, Iris, Tara | Strategic decision + complex domain (architecture, money, SAP, insurance reg, trading microstructure) |
| **Sonnet** | Oliver, Bella, Dave, Chris, Quinn, Aaron, Uma, Elena, Brooke, Emma | Balanced execution — capable + fast |

### Domain Experts (7)

| Key | ชื่อ | Domain |
|-----|------|--------|
| Fe | **Felix** | Fintech/Banking — payment, ledger, ISO 8583/20022, PCI-DSS, tokenization, chargeback, KYC/AML |
| Ee | **Elena** | ERP/Accounting (generic) — GL, AR/AP, inventory, MRP, IFRS 15/16, consolidation |
| Sm | **Sam** | SAP (ECC + S/4HANA) — ABAP, Fiori, BTP, BAPI/IDoc/RFC, FI/CO/MM/SD/PP/HR, S/4 migration |
| Te | **Tara** | Trading — OMS, matching, order types, clearing (T+0/T+1/T+2), corporate actions |
| Ie | **Iris** | Insurance — policy admin, underwriting, claim, IFRS 17, reinsurance |
| Bk | **Brooke** | Booking/Reservation — PMS, channel manager, yield/RM, overbooking strategy |
| Ec | **Emma** | E-commerce — catalog, cart, promo, subscription, fraud, marketplace |

---

## Slash Commands (6)

| Command | ใช้เมื่อ |
|---------|----------|
| `/consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/spec-only [ระบบ]` | ทำ spec อย่างเดียว — proposal/estimation (ไม่ implement) |
| `/design-system [ระบบ]` | Full design pipeline — BA → Domain → SA → summary |
| `/implement [feature]` | Implement — Dave coding + Chris review/unit + Quinn integration |
| `/review [path]` | Code review — Chris 7 มิติ + Quinn security + Domain Expert |
| `/setup-project [stack]` | Aaron setup — Docker-first, CI/CD, observability, ready-to-code |

---

## Communication Rules

**Oliver**: คุย Core เท่านั้น → Bella/Sara ปรึกษา Domain Expert เอง
**ทุก design** ต้องมี domain input ≥ 1 domain
**Conflict resolution**: Domain > Architecture > Security > Simple

**Oliver speaks brief status lines** (ไม่เขียน paragraph):
```
sara and bella working on requirement
bella done → sara reviewing
sara done → dave coding
dave#1 + dave#2 parallel on payment endpoints
chris reviewing, quinn writing integration
aaron updating ci, ready to ship
```

---

## Bundled MCPs 🔌

Plugin มี `.mcp.json` แถม MCP server เพื่อประหยัด token:

| MCP | ใช้แทน | ประโยชน์ |
|-----|--------|----------|
| **[Context7](https://context7.com)** | `WebFetch` lib docs | Library docs ตาม version, snippet เป๊ะ |

**ติดตั้ง prerequisite ครั้งเดียว**:
```bash
# Context7 ต้องมี node
brew install node
```

Agent จะ prefer `mcp__context7__get-library-docs` > `WebFetch` อัตโนมัติ

## Task Tracking — beads (bd) 🧵

ทีมใช้ **[beads](https://github.com/steveyegge/beads) (`bd`)** เป็น single source of truth แทน markdown TODO list:

```bash
brew install beads
cd your-project && bd init
bd create "FR-101: POST /refund" -t functional-req --blocked-by 1
bd ready --json    # next unblocked tasks (agent query)
bd graph --format=mermaid    # auto dep diagram
```

- RTM (BR → FR → US → ADR → Test → Code) ทั้งหมดอยู่ใน `bd`
- ทุก agent claim task ด้วย `bd ready` → close เมื่อเสร็จ
- Commit message reference `[bd:N]`
- Markdown artifact (BRD/ADR/spec) save ที่ `outputs/` แต่ **status/dependency = bd เท่านั้น**

## Principles

- **SOLID + clean code** — ทุก agent enforce
- **Keep it simple** — ไม่ over-engineer
- **Domain-first** — business rule ชนะ tech เสมอ
- **Money = Decimal** — ห้าม float
- **Test coverage ≥ 80%** critical path 100%
- **Observability from day 1** — log/metric/trace
- **Feature flag** สำหรับ risky feature
- **Compliance-first** สำหรับ regulated domain (Fintech/Insurance)
- **beads > markdown** สำหรับ task/dependency
- **ภาษาไทย** สำหรับคำอธิบาย (code ตาม convention)

---

## Install

```bash
# ใน Claude Code
/plugin install shode-house
```

หรือ double-click ไฟล์ `.plugin` ใน Cowork

---

## License

MIT — use freely, improve freely
