# shode-house

> Multi-agent ทีม software house สำเร็จรูป — **19 expert agents in 7 teams** + workflow discipline

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages

ออกแบบเน้น: **lean • token-optimized • production-ready • domain-driven • zero-overlap capability • ภาษาไทย**

[![Version](https://img.shields.io/badge/version-3.0.1-blue.svg)](https://github.com/shode666/claude-skill-shode-house)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🆕 v3.0 — Comprehensive Org Structure

**Biggest release since v1.0** — real software-house org chart:

- **4 new core agents**: Patrick (PM), Stan (Staff Eng), Sentinel (Security Eng), Reggie (SRE)
- **4 new phases**: Phase 0 Discovery → 1c Threat Model → 6 Operate → 7 Learn
- **7-team structure** with single-owner capability matrix (zero overlap)
- **Workflow Drift Defense** — 7 mechanisms to keep workflow tight in follow-up
- **Handoff Broadcast Protocol** — caveman 1-line between agents (`Bella ▸ Dave : impl bd-42`)
- **RACI matrix** explicit per phase + Multi-sig pre-deploy-prod gate
- **5 new skills**: dev-gate (merged tdd+code-quality), web-q, secure, slo, incident

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

## ⚡ Slash Commands (8)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:init [project]` | Init wizard — interactive scaffold |
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:spec-only [ระบบ]` | Spec อย่างเดียว — proposal/estimation |
| `/shode-house:design-system [ระบบ]` | Full design pipeline — Phase 0/1a/1b/1c |
| `/shode-house:implement [feature]` | Implement — Dave + UI check + 4-way Verify |
| `/shode-house:review [path\|jira\|bug]` | Code review — Chris + Quinn + Sentinel |
| `/shode-house:setup-project [stack]` | Aaron setup — Docker-first, CI/CD, observability |
| `/shode-house:sprint [pre\|status\|close\|retro]` | Sprint management — outer loop |

---

## 📚 Skills (10 lazy-load)

| Skill | Owner | Trigger |
|-------|-------|---------|
| `meeting` | ALL | Engagement entry — discipline foundation v3.0 |
| `dev-gate` 🆕 | Dave + Chris | TDD red-green-refactor + quality gates (merged from tdd + code-quality) |
| `automate-test` | Quinn + Chris + Aaron | CI test pyramid 70/20/10 + threshold |
| `ui-test` | Quinn + Uma + Dave | Playwright + axe + visual regression + a11y |
| `diagnose` | Chris + Quinn + Dave | Bug + perf root cause (4-step methodology) |
| `caveman` | Oliver + ALL | Compressed output mode |
| `web-q` 🆕 | Uma + Dave + Quinn + Aaron + Sentinel | Core Web Vitals + SEO + security headers |
| `secure` 🆕 | Sentinel | STRIDE + LINDDUN + CSP + Trusted Types + SAST/DAST |
| `slo` 🆕 | Reggie | SLI / SLO / error budget (Google SRE Book-aligned) |
| `incident` 🆕 | Reggie + Oliver | Runbook + on-call + blameless postmortem + 5-why |

**Removed in v3.0**: `sd`/`do` (duplicate v1.1), `tdd`+`code-quality` (merged → `dev-gate`), `grill-me` (merged → `meeting` Clarifying), `triage`/`to-prd`/`to-issues`/`zoom-out` (empty stubs)

---

## 🔁 Workflow — 8 Phases

```
Outer loop (Sprint = 1-2 weeks):
  Phase 7 Learn (Patrick + Oliver) → Phase 0 Discovery (Patrick + Domain SME)
  → Per-issue Inner Loop ↓ → Phase 5 Deploy (Aaron + Reggie) → Phase 6 Operate (Reggie)

Inner loop per bd-issue:
  Phase 1a Foundation     Bella ∥ Sara (parallel)
  Phase 1b Pre-Design     Uma + Domain (sequential after 1a, conditional)
  Phase 1c Threat Model   Sentinel (parallel-able with 1b, conditional)
  Phase 2  Implement      Dave (parallel by scope contract)
  Phase 3a UI Check       Uma POST (sequential gate)
  Phase 3b Quality Coop   Chris ∥ Quinn ∥ Sentinel ∥ Aaron (4-way parallel)
  Phase 4  Triage         Oliver (max iter 3)
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

## 📁 Architecture

```
shode-house/
├── .claude-plugin/             manifest + marketplace
├── skills/
│   ├── meeting/                discipline foundation (5 philosophy + teams + drift defense + RACI + handoff)
│   ├── dev-gate/        🆕     TDD + quality gates (merged)
│   ├── automate-test/          CI test pyramid
│   ├── ui-test/                Playwright + axe + visual
│   ├── diagnose/               4-step bug methodology
│   ├── caveman/                compressed output
│   ├── web-q/           🆕     Core Web Vitals + SEO + sec headers
│   ├── secure/          🆕     STRIDE + CSP + Trusted Types
│   ├── slo/             🆕     SLI/SLO/error budget
│   └── incident/        🆕     Runbook + postmortem
├── agents/                     19 expert agents (12 core + 7 domain)
├── commands/                   8 slash commands
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
2. Update Team Routing ใน `agents/orchestrator.md` + Team Structure ใน `skills/meeting/SKILL.md`
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
