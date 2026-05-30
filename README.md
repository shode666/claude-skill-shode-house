# shode-house

> Multi-agent ทีม software house สำเร็จรูป — **19 expert agents in 7 teams** + workflow discipline

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages

ออกแบบเน้น: **lean • token-optimized • production-ready • domain-driven • zero-overlap capability • ภาษาไทย**

[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](https://github.com/shode666/claude-skill-shode-house)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🆕 v3.1 — Skill Craft Refactor (9arm-inspired)

**Focused on skill quality + lazy-load + token saving** ขณะที่ keep v3.0 org structure ครบ:

- **Meeting god-skill split** — เดิม `meeting/SKILL.md` = 1316 บรรทัด (everyone loaded). แตกเป็น 7 lazy-load skills ใต้ `skills/discipline/` + meeting เหลือ 180-line thin entry-point + Recite Discipline Card → **86% token reduction** สำหรับ entry context
- **Bucket folder lifecycle** (`workflow/`, `ops/`, `ui/`, `style/`, `discipline/`, `in-progress/`, `deprecated/`) — maturity visible จาก folder; CLAUDE.md invariants บังคับ index integrity
- **Command consolidation** — `/init` รวม `/setup-project` ด้วย `--quick` flag; `/design-system` รวม `/spec-only` ด้วย `--stop --estimate` flags. ลด 8 → 6 commands (+ 2 deprecated alias 1-release window)
- **9arm-inspired skill craft** ทุก SKILL.md:
  - 4-section description format: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]`
  - `When NOT to use` + `Required inputs — refuse without` gate
  - Skill composition pointer (textual handoff between skills — ลด orchestrator round-trip)
- **`review-checklist` skill (DRY)** — Chris 7-dim + Quinn integration matrix อยู่ที่เดียว; `/implement` Phase 3b + `/review` อ้างที่นี่
- **Recite Discipline Card** — ทุก agent recite 5 Philosophy verbatim ใน first response (anchor against drift)
- **CLAUDE.md repo invariants** (≤ 30 lines) + `scripts/{list,check,build}.sh` dev-loop tooling
- **18 skills** (10 functional + 7 discipline modules + 1 review-checklist), **5 commands** (+ 2 deprecated). v3.3 drops sprint outer loop + Evan agent — **PEV loop per bd** (Plan/Execute/Verify/Triage), bias discipline embedded in 19 agent prompts, Chris/Quinn adversarial vs Dave + Claude in Chrome verify mandatory. ห้าม man-day negotiation

### v3.0 features ที่ยัง keep

- 4 core agents: Patrick (PM), Stan (Staff Eng), Sentinel (Security Eng), Reggie (SRE)
- 4 phases: 0 Discovery, 1c Threat Model, 6 Operate, 7 Learn
- 7-team structure + single-owner capability matrix
- Workflow Drift Defense (M1-M7 ตอนนี้อยู่ใน `shode-house-drift` skill)
- Handoff Broadcast Protocol (caveman 1-line)
- RACI matrix per phase + Multi-sig pre-deploy-prod gate

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

### Update
```bash
/plugin marketplace update shode-house
/plugin install shode-house@shode-house
```

---

## 👥 7 Teams (parallel within, sequential across via phase gate)

| Team | Members | Phase | Deliverable |
|------|---------|-------|-------------|
| 🧭 **Lead** | Oliver + Stan | All | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | 0 | OKR + opportunity + pain validation |
| 📐 **Design** | Bella + Sara + Uma | 1a/1b/3a | BRD + ADR + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | 0/1b/3b | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel) + Devon/Mason (opt) | 2 | Production code |
| ✅ **Verify** | Chris + Quinn + Sentinel | 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | 5/6 | Deploy + SLO + Incident |

**Single-owner capability matrix** — ทุก capability มี sole owner; agent อื่น consult ได้แต่ห้ามผลิต deliverable

---

## 🤖 Agents (19 = 12 core + 7 domain)

### Core (12)
| Key | ชื่อ | Model | Team | Role |
|-----|------|-------|------|------|
| Or | **Oliver** | sonnet | Lead | Engagement Lead — orchestrate, classify follow-up, multi-sig gate |
| St | **Stan** 🆕 | **opus** | Lead | Staff Engineer — cross-team consistency, tech radar, polyglot review |
| Pa | **Patrick** 🆕 | sonnet | Discover | Product Manager — OKR, RICE/WSJF, opportunity sizing, kill decision |
| Ba | **Bella** | sonnet | Design | BA — BRD/FRD/AC G-W-T, Event Storming, RTM |
| Sa | **Sara** | **opus** | Design | SA — C4, ADR, NFR (threat model → Sentinel) |
| Ux | **Uma** | sonnet | Design | UX/UI + Design System + a11y (WCAG 2.2 AA) |
| Dv | **Dave** | sonnet | Dev | Polyglot Dev (parallel Dave#N, 14 languages, lazy-load) |
| Cr | **Chris** | sonnet | Verify | Code Review 7-dim + Unit + Mutation kill ≥ 70% |
| Qa | **Quinn** | sonnet | Verify | QA — Integration/E2E/Contract/Load/Perf/axe (pen test → Sentinel) |
| Se | **Sentinel** 🆕 | **opus** | Verify | Security Engineer — STRIDE/LINDDUN, SAST/DAST, CSP/Trusted Types, pen test |
| Do | **Aaron** | sonnet | Ops | DevOps/Platform — Docker, CI/CD, IaC (SLO → Reggie) |
| Re | **Reggie** 🆕 | sonnet | Ops | SRE — SLO/SLI, error budget, runbook, on-call, blameless postmortem |

### Domain Experts (7) — Phase 0 active driver in v3.0
| Key | ชื่อ | Model | Domain |
|-----|------|-------|--------|
| Fe | **Felix** | **opus** | Fintech — payment, ledger, ISO 8583/20022, PCI-DSS v4, KYC/AML, BOT |
| Ee | **Elena** | sonnet | ERP/Accounting — GL, AR/AP, MRP, IFRS 15/16, consolidation |
| Sm | **Sam** | **opus** | SAP — ECC + S/4HANA, ABAP, Fiori, BTP, BAPI/IDoc, migration |
| Te | **Tara** | **opus** | Trading — OMS/EMS, matching, FIX, microstructure, clearing |
| Ie | **Iris** | **opus** | Insurance — policy, claim, IFRS 17, reinsurance, OIC |
| Bk | **Brooke** | sonnet | Booking — PMS, channel manager, yield, overbooking, GDS |
| Ec | **Emma** | sonnet | E-commerce — catalog, cart, promo, marketplace, fraud |

### Model Strategy
- **Opus** (6): judgment-critical (architecture, security, money, SAP, insurance reg, trading microstructure)
- **Sonnet** (13): execution + structured patterns (capable + fast)

---

## 🧭 5 Core Philosophy

ทุก agent ยึดเป็นอันดับหนึ่ง:

1. **NO MAGIC** — ห้ามเดา. Path/service ไม่รู้ → `Glob`/`Grep` หาก่อน. Assumption explicit + cite evidence
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0/R1/R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

---

## ⚡ Slash Commands (6 + 2 deprecated alias — v3.1 consolidation)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:init [project]` | Init project scaffold — **default**: interactive wizard; `--quick "<stack>"` direct Aaron Docker-first (replaces /setup-project) |
| `/shode-house:design-system [feature]` | Smart Spec pipeline — **default**: spec → suggest implement; `--stop`: stop at spec; `--estimate`: add T-shirt sizing; `--stop --estimate` = proposal mode (replaces /spec-only) |
| `/shode-house:implement [feature]` | Phase 2-4 — Dave + Uma + Chris ∥ Quinn (uses `review-checklist` skill) |
| `/shode-house:review [path\|jira\|bug]` | Ad-hoc code review (uses `review-checklist` skill) |
| ~~`/shode-house:sprint`~~ | ❌ **REMOVED v3.3** — sprint outer loop dropped; PEV loop per bd; continuous OKR review (Patrick); deploy continuous per bd |
| ~~`/shode-house:setup-project`~~ | ⚠️ DEPRECATED v3.1 → alias of `/init --quick`. ลบใน v3.2 |
| ~~`/shode-house:spec-only`~~ | ⚠️ DEPRECATED v3.1 → alias of `/design-system --stop --estimate`. ลบใน v3.2 |

> **3-flag rule** (CLAUDE.md invariant): ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag รองรับได้ → prefer flags over command proliferation

---

## 📚 Skills (18 lazy-load — bucket organized v3.1)

### `skills/workflow/` — daily process
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`meeting`](skills/workflow/meeting/SKILL.md) | ALL | **Entry-point** + Recite Discipline Card + index (v3.1 thin) |
| [`dev-gate`](skills/workflow/dev-gate/SKILL.md) | Dave + Chris | TDD red-green-refactor + 7-gate quality |
| [`automate-test`](skills/workflow/automate-test/SKILL.md) | Quinn + Chris + Aaron | CI test pyramid 70/20/10 + threshold |
| [`diagnose`](skills/workflow/diagnose/SKILL.md) | Chris + Quinn + Dave | Bug + perf root cause (4-step) |

### `skills/ops/` — operational discipline
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`incident`](skills/ops/incident/SKILL.md) | Reggie + Oliver | Runbook + on-call + blameless postmortem + 5-why |
| [`slo`](skills/ops/slo/SKILL.md) | Reggie | SLI / SLO / error budget (Google SRE Book) |
| [`secure`](skills/ops/secure/SKILL.md) | Sentinel | STRIDE + LINDDUN + CSP + Trusted Types + SAST/DAST |

### `skills/ui/` — frontend quality
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`ui-test`](skills/ui/ui-test/SKILL.md) | Quinn + Uma + Dave | Playwright + axe + visual regression |
| [`web-q`](skills/ui/web-q/SKILL.md) | Uma + Dave + Quinn + Aaron + Sentinel | CWV + Lighthouse + SEO + security headers |

### `skills/style/` — communication style
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`caveman`](skills/style/caveman/SKILL.md) | Oliver + ALL | Compressed output mode |

### `skills/discipline/` — v3.1 split modules (from meeting god-skill)
| Skill | Owner | Role |
|-------|-------|------|
| [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) 🆕 | ALL (mandatory) | Recite Card + 5 Philosophy + Safety + Universal Rules + Clarifying |
| [`shode-house-evidence`](skills/discipline/shode-house-evidence/SKILL.md) 🆕 | Claimers, Domain experts | Project + UX + Domain Evidence + REVIEW format |
| [`shode-house-routing`](skills/discipline/shode-house-routing/SKILL.md) 🆕 | Oliver | Routing + RACI + T-shirt + Trust Levels + Team v3.0 |
| [`shode-house-deliverable`](skills/discipline/shode-house-deliverable/SKILL.md) 🆕 | Producers | DoD + Anti-Puppet + I Never Do + Postmortem template |
| [`shode-house-broadcast`](skills/discipline/shode-house-broadcast/SKILL.md) 🆕 | ALL | Tag Prefix + Caveman broadcast + Handoff Protocol |
| [`shode-house-workflow`](skills/discipline/shode-house-workflow/SKILL.md) 🆕 | Oliver | Phase Contract + Smart Coop + hooks + gates + worktree |
| [`shode-house-drift`](skills/discipline/shode-house-drift/SKILL.md) 🆕 | Oliver enforcer | Drift Defense M1-M7 + New Phases v3.0 |
| [`review-checklist`](skills/discipline/review-checklist/SKILL.md) 🆕 | Chris + Quinn + Sentinel + Domain | DRY checklist สำหรับ /implement Phase 3b + /review |

### `skills/in-progress/` + `skills/deprecated/` — not shipped
Skill ที่อยู่นี่จะไม่ถูกใส่ใน plugin.json (CLAUDE.md invariant)

**v3.1 changes**:
- Meeting god-skill (1316 lines) split → 7 discipline modules (avg 200 lines each) + 180-line thin entry
- New `review-checklist` skill — DRY for `/implement` Phase 3b + `/review`
- 9arm-inspired: 4-section description, When-NOT + Required-inputs gate, skill composition pointers
- Bucket folders enforce maturity lifecycle

---

## 🔁 Workflow — PEV Loop per bd (v3.3 — no sprint outer loop)

```
PEV loop per bd-issue (Plan → Execute → Verify → Triage):
  📋 PLAN
  Phase 0  Discovery       Patrick + Domain SME (opt — new initiative)
  Phase 1a Foundation      Bella ∥ Sara (parallel)
  Phase 1b Pre-Design      Uma + Domain (sequential after 1a, conditional)
  Phase 1c Threat Model    Sentinel (parallel-able with 1b, conditional)
  💻 EXECUTE
  Phase 2  Implement       Dave (parallel by scope contract)
  ✅ VERIFY (adversarial — Chris/Quinn vs Dave, zero trust)
  Phase 3a UI Check        Uma POST (sequential gate + Chrome MCP)
  Phase 3b Code Review     Chris ∥ Quinn (verdict default = FAIL + Chrome MCP)
  🚦 TRIAGE
  Phase 4  Triage          Oliver (max iter 3) → bd close + bd remember
  🚀 DEPLOY (continuous per bd)
  Phase 5  Deploy          Aaron + Reggie
  📡 OPERATE
  Phase 6  Operate         Reggie (SLO, incident)

No Phase 7 / sprint retro — per-bd reflect captured in Phase 4 Triage; continuous OKR review (Patrick)
```

### Phase Gates (RACI-aware + Evidence-mandatory)

10+ standard gates ทุก phase transition: `pre-spec`, `pre-spec-expand`, `pre-implement-ui`, `pre-implement`, `pre-ui-check`, `pre-quality-coop`, `pre-loop-exit`, `pre-deploy-staging/uat/prod`, `pre-data-migration`, `pre-destructive`

**Multi-sig pre-deploy-prod (R0)**:
- Aaron (build) + Reggie (SLO) + Sentinel (security) + Patrick (OKR/risk)

---

## 🤝 Handoff Broadcast Protocol (caveman 1-line)

ทุก phase transition → 1 บรรทัด:

```
Bella ▸ Dave   : impl bd-42
Dave  ▸ Verify : CR + test + sec
Verify ▸ Oliver : 2M 1m
Oliver ▸ Ops   : deploy
Ops    ▸ ✓    : prod stable
```

**Arrow convention**:
- `▸` = handoff broadcast (M3 protocol — formal between agents)
- `→` = general flow/sequence/implication (informal)

---

## 🛡️ Workflow Drift Defense (7 Mechanisms)

แก้ปัญหา agent หลุด workflow ใน warm follow-up — Dave บอก "เสร็จแล้ว" โดยไม่ผ่าน Verify, fix ตรงโดยไม่ผ่าน Phase 1a

| # | Mechanism | What it does |
|---|-----------|-------------|
| M1 | **Ingress Guard** | ทุก agent ก่อน respond: bd show → state → classify → route check |
| M2 | **Follow-up Classifier** | Oliver auto-triage user message (fix/spec/quest/approve/new/status) |
| M3 | **Anti-Puppet "Done"** | Dave/Chris/Quinn/Sentinel/Uma ห้าม claim "done"; only Oliver after multi-sig |
| M4 | **User Comment = FAIL** | feedback ใด ๆ = reopen bd + iter++ |
| M5 | **Spec Change = bd revision** | verbal change ห้าม fix ตรง → Bella revision → Phase 1a redo |
| M6 | **SESSION-STATE.md** | Oliver maintain persistent state; ทุก agent read first |
| M7 | **Direct-to-Agent block** | non-Oliver agents ห้าม accept direct-from-user → route Oliver |

---

## 💬 Clarifying Style

ทุก agent ใช้ **`AskUserQuestion` tool ก่อนเสมอ**:

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

6 grill patterns: Stack / Scope / Severity / Auth method / Tracker / Deployment

---

## 🌐 Polyglot Dave — 14 Languages (lazy-load)

Dave อ่าน best practice **เฉพาะภาษาที่ใช้** จาก `references/languages/<lang>.md` → ประหยัด token

**Startup tier**: TypeScript, Python, JavaScript, Go, SQL, Kotlin, Swift, Rust, PHP, Dart
**Enterprise tier**: Java, C#, C++, COBOL/PL-SQL/VBA

---

## 🔌 Bundled MCPs

| MCP | ใช้แทน | ประโยชน์ |
|-----|--------|----------|
| **[Context7](https://context7.com)** | `WebFetch` lib docs | Library docs ตาม version, snippet เป๊ะ — token-saving |

Prerequisite: `brew install node` (Context7 ใช้ npx)

---

## 🧵 Task Tracking — beads (bd)

ทีมใช้ **[beads](https://github.com/steveyegge/beads)** เป็น single source of truth:

```bash
brew install beads
cd your-project && bd init
bd create "FR-101: POST /refund" -t functional-req --blocked-by 1
bd ready --json    # next unblocked
bd graph --format=mermaid    # auto dep diagram
```

RTM (BR → FR → US → ADR → Test → Code) อยู่ใน bd. Markdown artifact save `outputs/` แต่ status = bd

---

## 🏛️ Principles

- **Right answer > first answer** — ห้าม "พอใช้ได้"
- **Evidence-based** — cite version + clause (ISO/IFRS/OWASP/PCI/BOT/OIC)
- **Domain-aware vocabulary**
- **Test before claim "done"** (anti-puppet)
- **Reproducible** — git clone → run = work
- **Money = Decimal** — ห้าม float
- **Lazy-load reference** สำหรับ token-saving
- **Modular** — เพิ่ม/ลด agent ง่าย (drop file + update routing)
- **Zero overlap** — single-owner capability matrix (v3.0)

---

## 📁 Architecture (v3.1 bucket-organized)

```
shode-house/
├── CLAUDE.md                   🆕 v3.1 repo invariants (≤ 30 lines)
├── .claude-plugin/             manifest + marketplace (v3.1.0)
├── scripts/                    🆕 v3.1 dev-loop
│   ├── list-skills.sh          list every SKILL.md + line count + bucket
│   ├── check-index.sh          enforce CLAUDE.md invariants (CI gate)
│   └── build-plugin.sh         build shode-house-v3.1.0.plugin
├── skills/
│   ├── workflow/               daily process
│   │   ├── meeting/            🔄 v3.1 thin entry-point (180 lines, was 1316)
│   │   ├── dev-gate/           TDD + 7-gate quality
│   │   ├── automate-test/      CI test pyramid 70/20/10
│   │   └── diagnose/           4-step bug methodology
│   ├── ops/                    operational discipline
│   │   ├── incident/           runbook + war room + postmortem
│   │   ├── slo/                SLI/SLO/error budget
│   │   └── secure/             STRIDE + CSP + Trusted Types
│   ├── ui/                     frontend quality
│   │   ├── ui-test/            Playwright + axe + visual
│   │   └── web-q/              CWV + Lighthouse + SEO + headers
│   ├── style/                  communication
│   │   └── caveman/            compressed output
│   ├── discipline/             🆕 v3.1 split modules + DRY checklist
│   │   ├── shode-house-discipline/   Recite Card + 5 Philosophy + Safety
│   │   ├── shode-house-evidence/     Project + UX + Domain Evidence + REVIEW
│   │   ├── shode-house-routing/      Routing + RACI + T-shirt + Trust
│   │   ├── shode-house-deliverable/  DoD + Anti-Puppet + Postmortem
│   │   ├── shode-house-broadcast/    Tag Prefix + Caveman + Handoff
│   │   ├── shode-house-workflow/     Phase Contract + hooks + gates
│   │   ├── shode-house-drift/        Drift Defense M1-M7
│   │   └── review-checklist/         DRY for /implement Phase 3b + /review
│   ├── in-progress/            not shipped (drafts)
│   └── deprecated/             not shipped (retiring)
├── agents/                     19 expert agents (12 core + 7 domain)
├── commands/                   6 active + 2 deprecated alias
└── references/
    ├── modern-stack.md         2025+ tech recommendation
    ├── patterns/general.md     DB/API/Observability (Dave lazy-load)
    └── languages/<14 files>    per-language best practice (Dave lazy-load)
```

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

## 🤝 Adding/Removing Agent

**Add new domain expert**:
1. Drop `agents/<name>.md` (ตาม 5-Dim Role template)
2. Update Team Routing ใน `agents/orchestrator.md` + Team Structure ใน `skills/workflow/meeting/SKILL.md` + `skills/discipline/shode-house-routing/SKILL.md`
3. Bump version, repackage

**Remove agent**: ลบไฟล์ + remove จาก routing + capability matrix

---

## 🔗 Inspirations

- **Workflow discipline**: [Archon](https://github.com/coleam00/archon) (phase contract + loop + approval gates)
- **Productivity skills**: [mattpocock/skills](https://github.com/mattpocock/skills) (caveman/grill-me concepts)
- **Web quality skills**: [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) (web-q port)
- **SRE discipline**: [Google SRE Book](https://sre.google/books/) (slo + incident port)
- **Tech radar**: Thoughtworks (Stan tech radar pattern)
- **Issue tracker**: [beads](https://github.com/steveyegge/beads)
- **Domain knowledge**: real-world projects (Thai banking, ERP, insurance, hospitality)

---

## 📜 License

MIT — use freely, improve freely, contribute back welcome
