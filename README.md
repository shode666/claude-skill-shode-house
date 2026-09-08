# shode-house

> **Multi-Agent Software Engineering Operating System** สำหรับ Claude Code / Cowork —
> 19 agent ใน 7 ทีม ที่มี ownership ชัด, quality gate ที่ต้องมีหลักฐาน, token-aware context routing,
> CI invariant ที่พิสูจน์ด้วย mutation test และ behavioral A/B eval

[![Version](https://img.shields.io/badge/version-3.14.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/shode666/claude-skill-shode-house/actions/workflows/ci.yml/badge.svg)](https://github.com/shode666/claude-skill-shode-house/actions/workflows/ci.yml)

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages · ภาษาไทยเป็นหลัก

**What's new**: [CHANGELOG.md](CHANGELOG.md) · release ล่าสุด v3.14.0 — public polish (LICENSE · README · architecture diagrams) + reference project #1 ที่ผ่าน pipeline เต็ม

---

## shode-house คืออะไร

ไม่ใช่ "รวม prompt 19 ตัว" แต่เป็น **ระบบปฏิบัติการของ software house** ที่รันบน Claude Code:

- **Orchestration** — Oliver ยึด main session, classify ทุก message, route ไป agent ที่เป็น *sole owner* ของ capability นั้น (zero-overlap)
- **Governance** — ทุกกฎมี owner · trigger · source-of-truth · verification ใน [`.enforcement-map.json`](.enforcement-map.json) — กฎที่ไม่มีเจ้าของหรือตรวจไม่ได้ = CI แดง
- **Evidence-first** — agent ห้าม claim โดยไม่ paste tool output; "เสร็จแล้ว" พูดได้คนเดียวคือ Oliver หลัง reviewer ครบ (Anti-Puppet)
- **Context engineering** — preload/agent/dispatch budget แบบ ratchet (ลงได้ ขึ้นไม่ได้) + วัด context จริงต่อ agent ด้วย A/B
- **Failure containment** — Drift Defense M1–M8, iter cap 3, approval ผูก artifact SHA, R0/R1/R2 risk tiers

---

## Architecture

```
                         user
                          │
                    ┌─────▼──────┐
                    │   Oliver   │  Engagement Lead — main session
                    │  (+ Stan)  │  M1 ingress → classify → route → gate
                    └─────┬──────┘
        PLAN              │
   ┌──────────┬───────────┼───────────┬────────────┐
   ▼          ▼           ▼           ▼            ▼
Patrick    Bella ∥ Sara   Uma      Sentinel    Domain SME ×7
 (0)         (1a)        (1b)       (1c)       Felix Elena Sam
                          │                    Tara Iris Brooke Emma
        EXECUTE           ▼
                        Dave (2)  ── polyglot, parallel by scope
                          │
        VERIFY   ┌────────┼────────┐
                 ▼        ▼        ▼
               Uma      Chris ∥  Quinn      (+ Sentinel / Domain on trigger)
              (3a)        (3b)
                          │
        TRIAGE          Oliver (4)  iter ≤ 3 → bd close + bd show
                          │
        DEPLOY / OPERATE  Aaron (5) → Reggie (6)
```

รูปเต็ม 3 มุมมอง (topology · lifecycle · enforcement, Mermaid) → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

ทุก transition ผ่าน **gate** ที่ต้องมี evidence (`pre-implement` · `pre-implement-ui` · `pre-ui-check` · `pre-loop-exit` · `pre-deploy-*` · `pre-destructive` …) — รายละเอียด § Workflow ด้านล่าง

---

## 60-second example

```
you   > /shode-house:implement "POST /refund — คืนเงินบางส่วนได้ ห้ามเกินยอดจ่าย"

[Oliver|M1 Ingress Guard|bd-42]
- classify : new-task   - route : Bella ∥ Sara (1a) → Felix (money trigger) → Sentinel (1c)

Bella   ▸ Sara    : BRD + AC (G-W-T ×6)        outputs/bd-42/01-bella-1a.md
Sara    ▸ Felix   : ADR-007 ledger append-only  outputs/bd-42/02-sara-1a.md
Felix   ▸ Oliver  : cite BOT + PCI-DSS v4 §3.4 · partial refund = reversal entry
Sentinel▸ Oliver  : STRIDE — 2 abuse case → security AC
Oliver  ▸ Dave    : impl bd-42  (gate pre-implement ✓ evidence: 4 artifact)

Dave    ▸ Verify  : code edited / smoke ✓  (paste pytest: 14 passed)
Chris   ∥ Quinn   : 7-dim clean · spec-axis: missing AC-5 (idempotency) → FAIL
Oliver            : triage → Phase 2 iter 2
Dave    ▸ Verify  : idempotency key added · 16 passed
Chris   ∥ Quinn   : 7-dim clean · E2E green · spec-axis 6/6

[Oliver|state:TRIAGE|bd:42]  bd close 42 --reason "PASS a1b2c3d 16 passed" → bd show 42: CLOSED
```

สิ่งที่ *ไม่* เกิดในตัวอย่างนี้ — Dave พูดว่า "เสร็จแล้ว" · reviewer ผ่านโดยไม่ paste output · Sara เดา business rule เรื่องเงินเองโดยไม่ผ่าน Felix

---

## ทำไมถึงต่างจาก prompt collection

| | prompt collection ทั่วไป | shode-house |
|---|---|---|
| กฎ | เขียนใน prompt แล้วหวังว่า agent จะทำตาม | `rule → owner → trigger → source_of_truth → verification` ใน enforcement map; CI ตรวจว่า source ยังมีกฎนั้นจริง (anchor) |
| ขนาด context | "พยายามให้สั้น" | static budget 3 ชั้น (agent · preload · dispatch graph) เป็น ratchet + วัด ctx0 จริงต่อ agent |
| ความถูกต้องของ gate | เชื่อว่า CI ทำงาน | gate ใหม่ทุกตัว **พิสูจน์ด้วย mutation test** ก่อน merge — ทำ invariant พังโดยตั้งใจแล้วต้องเห็น gate แดง (บันทึกผลใน CHANGELOG; ยังเป็นขั้นตอน manual) |
| "done" | agent ประกาศเอง | Anti-Puppet: producer พูดได้แค่ "code edited / 7-dim clean / E2E green"; close ต้องมี `bd show` CLOSED paste จริง |
| business rule | architect/dev เดา | งานที่แตะ money/regulation **บังคับ** ผ่าน domain expert + citation contract (cite primary source ก่อน claim) |
| การเปลี่ยนแปลง | เพิ่ม feature | ทุก release มี root-cause analysis ใน CHANGELOG + rule conservation check (กฎหายเงียบ ๆ = CI แดง) |

**CI = 24 gate** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml), รันเองได้ด้วย `make validate`): rule conservation · lazy-load reachability · agent/preload/dispatch budget · cross-reference + section-ref resolution · model single-source · enforcement-map anchor · design-intel pipeline smoke + negative test

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

Prerequisite (optional): `brew install node` (Context7 MCP ใช้ npx) · `brew install beads` (task tracker `bd`)

---

## 📊 Benchmarks

### v3.12.1 → v3.13.0 — runtime A/B (Cowork, ctx0 = context ตั้งต้นจริงของ subagent turn แรก)

| agent | 3.12.1 | 3.13.0 | Δ |
|---|---:|---:|---:|
| Sentinel | 29,534 | 26,516 | **−10.2%** |
| Sara | 30,418 | 27,588 | −9.3% |
| Bella | 29,892 | 27,178 | −9.1% |
| Chris | 33,602 | 30,616 | −8.9% |
| Uma | 30,986 | 28,234 | −8.9% |
| Quinn | 35,346 | 32,334 | −8.5% |
| Dave | 33,490 | 30,809 | −8.0% |
| Oliver | 39,551 | 37,172 | −6.0% |
| Felix | 25,806 | 24,539 | −4.9% |
| **รวม 9 agent** | **288,625** | **264,986** | **−8.2%** |

- behavioral invariant 8 ข้อ (NO MAGIC · M1 · M7 · zero-overlap · citation · Anti-Puppet · scope pin · money/PII trigger) ผ่าน 100% ทั้งสองฝั่ง — [`eval/results/3.13-rc1/BEHAVIOR.md`](eval/results/3.13-rc1/BEHAVIOR.md)
- target เดิม 10–25% **ไม่ผ่าน** — ตั้งบนสมมติฐานว่า plugin คือ context ทั้งหมด ซึ่งไม่จริงใน Cowork (harness คงที่) — [`eval/results/3.13-rc1/COMPARE.md`](eval/results/3.13-rc1/COMPARE.md)
- 🔴 ข้อจำกัด: 1 run/agent · ยังไม่ได้รัน pipeline เต็มผ่าน `/implement` `/review` — Spec-axis dispatch + AskUserQuestion relay **ยังไม่มี E2E proof** (roadmap Phase B)

### static (byte) — full fan-out 19 agent

v3.12.0 → v3.12.1: 702,788 → 587,398 B (−16.4%) โดยไม่ตัดกฎ · baseline ปัจจุบัน `.baseline-3.12.1.json` · วัดด้วย `scripts/context-budget.py`

harness + วิธีรัน → [`eval/README.md`](eval/README.md) · [`eval/RUNBOOK.md`](eval/RUNBOOK.md)

### Reference project — สร้างด้วย pipeline จริงทั้งสาย

[`shode666/shode-house-example-refund`](https://github.com/shode666/shode-house-example-refund) — partial refund + double-entry ledger (FastAPI/PostgreSQL, Decimal). ทุก artifact ที่ขับ code อยู่ใน folder docs/pipeline ของ repo นั้น (01 → 08): Bella BRD (8 AC) → Felix ledger rules → Sara ADR/schema → Sentinel SEC-01..03 → Dave (23 tests) → Chris 7-dim **FAIL 1 🔴** (scientific-notation amount → 500) → fix iter 1 → Chris CLEAN → Quinn E2E จริง + spec axis 11/11 → Felix domain CLEAN → **28 passed**. โชว์ทั้ง domain gate, spec axis และ reviewer ที่จับ bug ได้จริง — ไม่ใช่ pipeline ที่ผ่านทุกอย่างเขียว

---

## 👥 7 Teams (parallel within, sequential across via phase gate)

| Team | Members | Phase | Deliverable |
|------|---------|-------|-------------|
| 🧭 **Lead** | Oliver + Stan | All | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | 0 | OKR + opportunity + pain validation |
| 📐 **Design** | Bella + Sara + Uma | 1a/1b/3a | BRD + ADR + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | 0/1b/3b | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel) | 2 | Production code (data/ML = Dave interim) |
| ✅ **Verify** | Chris + Quinn + Sentinel | 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | 5/6 | Deploy + SLO + Incident |

**Single-owner capability matrix** — ทุก capability มี sole owner; agent อื่น consult ได้แต่ห้ามผลิต deliverable

---

## 🤖 Agents (19 = 12 core + 7 domain)

### Core (12)
| Key | ชื่อ | Model | Team | Role |
|-----|------|-------|------|------|
| Or | **Oliver** | sonnet | Lead | Engagement Lead — orchestrate, classify follow-up, multi-sig gate |
| St | **Stan** | **fable-5** | Lead | Staff Engineer — cross-team consistency, tech radar, polyglot review |
| Pa | **Patrick** | sonnet | Discover | Product Manager — OKR, RICE/WSJF, opportunity sizing, kill decision |
| Ba | **Bella** | sonnet | Design | BA — BRD/FRD/AC G-W-T, Event Storming, RTM |
| Sa | **Sara** | **fable-5** | Design | SA — C4, ADR, NFR (threat model → Sentinel) |
| Ux | **Uma** | **fable-5** | Design | UX/UI + Design System + a11y + **Design Authority** — นำ look & feel, advise Sara/Dave/Bella |
| Dv | **Dave** | sonnet | Dev | Polyglot Dev (parallel Dave#N, 14 languages, lazy-load) |
| Cr | **Chris** | sonnet | Verify | Code Review 7-dim + Unit + Mutation kill ≥ 70% |
| Qa | **Quinn** | sonnet | Verify | QA — Integration/E2E/Contract/Load/Perf/axe (pen test → Sentinel) |
| Se | **Sentinel** | **fable-5** | Verify | Security Engineer — STRIDE/LINDDUN, SAST/DAST, CSP/Trusted Types, pen test |
| Do | **Aaron** | sonnet | Ops | DevOps/Platform — Docker, CI/CD, IaC (SLO → Reggie) |
| Re | **Reggie** | sonnet | Ops | SRE — SLO/SLI, error budget, runbook, on-call, blameless postmortem |

### Domain Experts (7)
| Key | ชื่อ | Model | Domain |
|-----|------|-------|--------|
| Fe | **Felix** | **opus** | Fintech — payment, ledger, ISO 8583/20022, PCI-DSS v4, KYC/AML, BOT |
| Ee | **Elena** | sonnet | ERP/Accounting — GL, AR/AP, MRP, IFRS 15/16, consolidation |
| Sm | **Sam** | **opus** | SAP — ECC + S/4HANA, ABAP, Fiori, BTP, BAPI/IDoc, migration |
| Te | **Tara** | **opus** | Trading — OMS/EMS, matching, FIX, microstructure, clearing |
| Ie | **Iris** | **opus** | Insurance — policy, claim, IFRS 17, reinsurance, OIC |
| Bk | **Brooke** | sonnet | Booking — PMS, channel manager, yield, overbooking, GDS |
| Ec | **Emma** | sonnet | E-commerce — catalog, cart, promo, marketplace, fraud |

### Model Strategy (v3.5 — Claude 5 family)

| Tier | Agents | Frontmatter value | เหตุผล |
|------|--------|-------------------|--------|
| **Fable 5** (4) | Stan, Sara, Sentinel, Uma | `claude-fable-5` | judgment สูงสุด: cross-team architecture + security + **design direction** (Uma = Design Authority นำ look & feel) |
| **Opus** (4) | Felix, Sam, Tara, Iris | `opus` (alias → Opus ล่าสุด) | regulated-domain judgment (money, SAP, trading, insurance reg) |
| **Sonnet** (11) | ที่เหลือทั้งหมด | `sonnet` (alias → Sonnet ล่าสุด) | execution + structured patterns |
| **Haiku** (0 agent) | mechanical sub-task เท่านั้น | Task `model` override | status digest, broadcast aggregation, bd hygiene — ห้ามผลิต deliverable |

> **กติกา**: full string เฉพาะ Fable (ยังไม่มี alias เป็นทางการ); ตัวอื่นใช้ alias เพื่อตาม model ใหม่อัตโนมัติ. **ห้าม pin dated string** (เช่น `claude-sonnet-4-6-2025xxxx`)

**Fallback** (Fable 5 ล่ม — quota/availability) — Claude Code รองรับ fallback chain (สูงสุด 3, ครอบคลุม subagent ทุกตัว):

```jsonc
// .claude/settings.json (project) หรือ ~/.claude/settings.json
{ "fallbackModel": "opus,sonnet" }   // fable-5 ล่ม → Opus → Sonnet
```

หรือ per-session: `claude --fallback-model opus,sonnet`

**Budget mode** (บังคับทุก subagent ลง sonnet ชั่วคราว — ไม่ต้องแก้ไฟล์): `CLAUDE_CODE_SUBAGENT_MODEL=sonnet claude`

---

## 🧭 5 Core Philosophy

ทุก agent ยึดเป็นอันดับหนึ่ง:

1. **NO MAGIC** — ห้ามเดา. Path/service ไม่รู้ → `Glob`/`Grep` หาก่อน. Assumption explicit + cite evidence
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0/R1/R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

---

## ⚡ Slash Commands (5)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:init [project]` | Init project scaffold — **default**: interactive wizard; `--quick "<stack>"` direct Aaron Docker-first |
| `/shode-house:design-system [feature]` | Smart Spec pipeline — **default**: spec → suggest implement; `--stop`: stop at spec; `--estimate`: add T-shirt sizing; `--stop --estimate` = proposal mode |
| `/shode-house:implement [feature]` | Phase 2-4 — Dave + Uma + Chris ∥ Quinn (uses `review-checklist` skill) |
| `/shode-house:review [path\|jira\|bug]` | Ad-hoc code review (uses `review-checklist` skill) |

> **3-flag rule** (CLAUDE.md invariant): ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag รองรับได้ → prefer flags over command proliferation

---

## 📚 Skills (21 lazy-load — bucket organized)

### `skills/workflow/` — daily process
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`meeting`](skills/workflow/meeting/SKILL.md) | ALL | **Entry-point** + index ไป discipline skills (Recite Card อยู่ที่ `output-styles/oliver.md` §1) |
| [`dev-gate`](skills/workflow/dev-gate/SKILL.md) | Dave + Chris | TDD red-green-refactor + 7-gate quality |
| [`automate-test`](skills/workflow/automate-test/SKILL.md) | Quinn + Chris + Aaron | CI test pyramid 70/20/10 + threshold |
| [`diagnose`](skills/workflow/diagnose/SKILL.md) | Chris + Quinn + Dave | Bug + perf root cause — เริ่มที่ feedback loop |
| [`data-migration`](skills/workflow/data-migration/SKILL.md) | Dave + Aaron + Sara | expand-contract + backfill + rollback drill |
| [`api-contract`](skills/workflow/api-contract/SKILL.md) | Dave + Sara + Quinn | semver + deprecation window + consumer contract |
| [`decompose`](skills/workflow/decompose/SKILL.md) | Bella + Oliver + Patrick | epic → leaf: tracer bullet + blocking edge + create-then-wire |

### `skills/ops/` — operational discipline
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`incident`](skills/ops/incident/SKILL.md) | Reggie + Oliver | Runbook + on-call + blameless postmortem + 5-why |
| [`slo`](skills/ops/slo/SKILL.md) | Reggie | SLI / SLO / error budget (Google SRE Book) |
| [`secure`](skills/ops/secure/SKILL.md) | Sentinel | STRIDE + LINDDUN + CSP + Trusted Types + SAST/DAST + prompt injection |
| [`drain`](skills/ops/drain/SKILL.md) | Oliver + Dave/Chris/Quinn/Aaron/Uma | Verified backlog → parallel worktree → serial merge → close-on-done |

### `skills/ui/` — frontend quality
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`ui-test`](skills/ui/ui-test/SKILL.md) | Quinn + Uma + Dave | Playwright + axe + visual regression + WCAG 2.2 coverage |
| [`web-q`](skills/ui/web-q/SKILL.md) | Uma + Dave + Quinn + Aaron + Sentinel | CWV + Lighthouse + SEO + security headers |

### `skills/style/` — communication style
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`caveman`](skills/style/caveman/SKILL.md) | Oliver + ALL | Compressed output mode |

### `skills/discipline/` — preload modules
| Skill | Owner | Role |
|-------|-------|------|
| [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) | ALL (mandatory) | 5 Philosophy + Safety + Universal Rules + M1 + handoff min fields |
| [`shode-house-evidence`](skills/discipline/shode-house-evidence/SKILL.md) | Claimers, Domain experts | Project + UX + Domain Evidence |
| [`shode-house-routing`](skills/discipline/shode-house-routing/SKILL.md) | Oliver | Routing + RACI + T-shirt + Trust Levels |
| [`shode-house-deliverable`](skills/discipline/shode-house-deliverable/SKILL.md) | Producers | Output contract + Anti-Puppet rule + pointer ไป DoD/ADR/UX evidence |
| [`shode-house-broadcast`](skills/discipline/shode-house-broadcast/SKILL.md) | ALL | Tag Prefix + Caveman broadcast + Handoff Protocol |
| [`shode-house-workflow`](skills/discipline/shode-house-workflow/SKILL.md) | Oliver | Phase Contract + Smart Coop + hooks + gates + worktree + run durability |
| [`shode-house-drift`](skills/discipline/shode-house-drift/SKILL.md) | Oliver enforcer | Drift Defense M2-M8 |
| [`review-checklist`](skills/discipline/review-checklist/SKILL.md) | Chris + Quinn + Sentinel + Domain | Review orchestration core (แกน standards + แกน Spec / severity / gate) |
| [`domain-core`](skills/discipline/domain-core/SKILL.md) | Domain experts (7) | AI Persona Disclaimer + citation contract + source validation |

### `skills/in-progress/` + `skills/deprecated/` — not shipped
Skill ที่อยู่นี่จะไม่ถูกใส่ใน plugin.json (CLAUDE.md invariant)

---

## 🔁 Workflow — PEV Loop per bd

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
  Phase 3b Code Review     Chris ∥ Quinn — แกน standards + แกน Spec (verdict default = FAIL)
  🚦 TRIAGE
  Phase 4  Triage          Oliver (max iter 3) → bd close + bd show verify (M8)
  🚀 DEPLOY (continuous per bd)
  Phase 5  Deploy          Aaron + Reggie
  📡 OPERATE
  Phase 6  Operate         Reggie (SLO, incident)

No sprint outer loop / retro — per-bd reflect ใน Phase 4 Triage; continuous OKR review (Patrick)
```

### Phase Gates (RACI-aware + Evidence-mandatory)

`pre-spec` · `pre-spec-expand` · `pre-implement-ui` · `pre-implement` · `pre-ui-check` · `pre-quality-coop` · `pre-loop-exit` · `pre-deploy-staging/uat/prod` · `pre-data-migration` · `pre-destructive`

**Multi-sig pre-deploy-prod (R0)**: Aaron (build) + Reggie (SLO) + Sentinel (security) + Patrick (OKR/risk)

**Run durability**: run stamp (plugin version + model) · approval ผูก artifact SHA — artifact เปลี่ยนหลัง approve = approval โมฆะ · resume protocol สำหรับ session ที่ตายกลาง pipeline · contract ของ durable runner ที่ Aaron generate → [`references/patterns/durable-agent-runtime.md`](references/patterns/durable-agent-runtime.md)

### Handoff Broadcast Protocol (caveman 1-line)

```
Bella ▸ Dave   : impl bd-42
Dave  ▸ Verify : CR + test + sec
Verify ▸ Oliver : 2M 1m
Oliver ▸ Ops   : deploy
```

`▸` = handoff broadcast (formal between agents) · `→` = general flow (informal)

---

## 🛡️ Workflow Drift Defense (8 Mechanisms)

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
| M8 | **Close-on-Done Guard** | งาน land แล้วต้อง `bd close --reason` + `bd show` paste CLOSED; `bd list` ไม่นับเป็นหลักฐาน |

---

## 💬 Clarifying Style

**`AskUserQuestion` ใช้ได้เฉพาะ main session** (`/init`, `/design-system`, `/implement` และ Oliver ผ่าน `output-styles/oliver.md`) — sub-agent ทุกตัว **return question bundle** ขึ้นไปให้ main session เปิด popup แล้วเขียนคำตอบกลับ tracker

- option-style 2-4 ตัวเลือก + Recommend ตัวแรก + reason 1 บรรทัด · batch ≤ 4 คำถามต่อ call · ห้ามคำถามเปิด
- **frontier model**: ถามทั้ง frontier ของ design tree รอบเดียว → คำถามที่ขึ้นกับข้อที่ยังเปิด = รอบถัดไป → จบเมื่อ frontier ว่าง

---

## 🌐 Polyglot Dave — 14 Languages (lazy-load)

Dave อ่าน best practice **เฉพาะภาษาที่ใช้** จาก `references/languages/<lang>.md`
**Startup tier**: TypeScript, Python, JavaScript, Go, SQL, Kotlin, Swift, Rust, PHP, Dart · **Enterprise tier**: Java, C#, C++, COBOL/PL-SQL/VBA

---

## 🧵 Task Tracking — beads (bd)

ทีมใช้ **[beads](https://github.com/steveyegge/beads)** เป็น single source of truth (alternative → [`docs/bd-quickstart.md`](docs/bd-quickstart.md)):

```bash
brew install beads
cd your-project && bd init
bd create "FR-101: POST /refund" -t functional-req --blocked-by 1
bd ready --json    # next unblocked
```

RTM (BR → FR → US → ADR → Test → Code) อยู่ใน bd. Markdown artifact save `outputs/` แต่ status = bd

**Bundled MCP**: [Context7](https://context7.com) — library docs ตาม version แทน `WebFetch`

---

## 📁 Repository layout

```
shode-house/
├── CLAUDE.md                   repo invariants
├── .claude-plugin/             manifest + marketplace
├── .enforcement-map.json       rule → owner → trigger → source_of_truth → verification
├── .agent-core-budget / .preload-budget / .workflow-scenario-budget   ratchet budgets
├── Makefile                    make validate | pack | stats | skills
├── .github/workflows/ci.yml    24-gate invariant + lint (inline bash + jq; = make validate)
├── agents/                     19 expert agents (12 core + 7 domain)
├── commands/                   5 slash commands
├── output-styles/oliver.md     Oliver ยึด main session
├── skills/                     workflow/ ops/ ui/ style/ discipline/  (+ in-progress/ deprecated/ ไม่ ship)
├── references/
│   ├── design-intel/           Uma lookup layer (data + search.py, preload 0 tok)
│   ├── patterns/               durable-agent-runtime.md · general.md
│   └── languages/<14 files>    per-language best practice (Dave lazy-load)
├── eval/                       scenarios · prompts · baseline · results/<version>/
├── scripts/                    context-budget.py · rule-conservation.py · usage-from-transcript.py …
└── docs/                       PLAN-*.md · pilot-reports/ · failure-modes/ · ADOPT-*-proposal.md
```

---

## 🛡️ Safety Discipline

**Destructive actions** ขออนุญาตเสมอ (R0): `git push --force` (main) · `git reset --hard` · `DROP TABLE` / `DELETE without WHERE` · `rm -rf` กว้าง / delete prod resource · edit migration ที่ apply prod แล้ว · modify auth/IAM

Pattern: ระบุ action + impact + rollback → ขอ confirm → execute

---

## 🤝 Contributing — Adding/Removing Agent

**Add new domain expert**:
1. Drop `agents/<name>.md` (ตาม 5-Dim Role template)
2. Update Team Routing ใน `agents/orchestrator.md` + Team Structure ใน `skills/workflow/meeting/SKILL.md` + `skills/discipline/shode-house-routing/SKILL.md`
3. `make validate` ต้องเขียว → bump version → `make pack`

**Remove agent**: ลบไฟล์ + remove จาก routing + capability matrix

> ตอนนี้ **ไม่รับ agent ใหม่** — 19 agent ครอบ capability ครบแล้ว; สิ่งที่ project ต้องการคือ E2E proof, benchmark และ reliability ไม่ใช่ agent ที่ 20

---

## 🔗 Inspirations

- **Workflow discipline**: [Archon](https://github.com/coleam00/archon) (phase contract + loop + approval gates)
- **Productivity skills**: [mattpocock/skills](https://github.com/mattpocock/skills) (caveman / grill-me / frontier clarifying)
- **Web quality skills**: [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) (web-q port)
- **Design intel data**: [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (vendored subset, MIT)
- **SRE discipline**: [Google SRE Book](https://sre.google/books/) (slo + incident port)
- **Tech radar**: Thoughtworks (Stan tech radar pattern)
- **Issue tracker**: [beads](https://github.com/steveyegge/beads)
- **Domain knowledge**: real-world projects (Thai banking, ERP, insurance, hospitality)

---

## 📜 License

[MIT](LICENSE) © 2026 Bundit Rattanang — use freely, improve freely, contribute back welcome
