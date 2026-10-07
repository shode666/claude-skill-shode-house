# shode-house

<p align="center"><img src="docs/assets/shode-house-team.jpg" alt="Shode House team (3.x artwork: 19 AI specialists in 7 teams): Lead, Product & Design, Development, Quality & Security, DevOps & Operations, Domain Experts" width="900"></p>

**4.0.0** — the main session is the **router**: the plugin's output style
`output-styles/shode-house.md` (forced by the plugin) routes, gates, relays and closes; it replaces the
3.x `orchestrator` agent and the `oliver` style. 18 specialist agents are spawned as `shode-house:<id>`
(3.x persona names map to agent ids in the § Formerly table of
[`ownership.md`](skills/discipline/shode-house-routing/ownership.md)), 20 skills ([ask](skills/workflow/ask/SKILL.md)
is the entry), and one canonical **safety floor** is copied byte-identical into every agent body and the
router style (`scripts/floor.py --check --require`). Team execution needs the router style, which only
Claude Code applies: on Codex, Cursor and Antigravity the skills run in one session and team execution
reports `BLOCKED: team execution needs the router style (Claude Code)`. Release notes: [CHANGELOG](CHANGELOG.md) 4.0.0.

3.16.x brought the full software house back ([ask](skills/workflow/ask/SKILL.md) as the single team
entrypoint, the original 19 roles and 23 skills, consolidated by v3.17 into 20 skills with no capability
removed); 3.16.1+ superseded 3.16.0, which shipped a single-skill package without the team.

> **Multi-Agent Software Engineering Operating System** สำหรับ Claude Code / Cowork —
> router (main session) + 18 agent ใน 7 ทีม ที่มี ownership ชัด, quality gate ที่ต้องมีหลักฐาน, token-aware context routing,
> CI invariant ที่พิสูจน์ด้วย mutation test และ behavioral A/B eval

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/shode666/claude-skill-shode-house/actions/workflows/ci.yml/badge.svg)](https://github.com/shode666/claude-skill-shode-house/actions/workflows/ci.yml)

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages · ภาษาไทยเป็นหลัก

**What's new**: [CHANGELOG.md](CHANGELOG.md) · release ล่าสุด **v4.0.0** · host notes: [docs/team-candidate-hosts.md](docs/team-candidate-hosts.md)

---

## shode-house คืออะไร

ไม่ใช่ "รวม prompt 18 ตัว" แต่เป็น **ระบบปฏิบัติการของ software house** ที่รันบน Claude Code:

- **Orchestration** — router (output style `shode-house`) ยึด main session, classify ทุก message, route ไป agent ที่เป็น *sole owner* ของ capability นั้น (zero-overlap)
- **Governance** — ทุกกฎมี owner · trigger · source-of-truth · verification ใน [`.enforcement-map.json`](.enforcement-map.json) — กฎที่ไม่มีเจ้าของหรือตรวจไม่ได้ = CI แดง
- **Evidence-first** — agent ห้าม claim โดยไม่ paste tool output; "เสร็จแล้ว" พูดได้คนเดียวคือ router หลัง reviewer ครบ (Anti-Puppet)
- **Context engineering** — preload/agent/dispatch budget แบบ ratchet (ลงได้ ขึ้นไม่ได้) + วัด context จริงต่อ agent ด้วย A/B
- **Failure containment** — Drift Defense M1–M8, iter cap 3, approval ผูก artifact SHA, R0/R1/R2 risk tiers

---

## Architecture

```
                         user
                          │
                    ┌─────▼──────┐
                    │   router   │  main session (output style shode-house)
                    │            │  M1 ingress → classify → route → gate
                    └─────┬──────┘
        PLAN              │
   ┌──────────┬───────────┼───────────┬────────────┐
   ▼          ▼           ▼           ▼            ▼
product-   business-   ux-ui-     security-    Domain SME ×7 (*-expert)
manager    analyst ∥   designer   engineer     fintech erp sap trading
 (0)       solution-     (1b)       (1c)       insurance booking ecommerce
           architect (1a)
        EXECUTE           ▼
                      developer (2)  ── polyglot, parallel by scope
                          │
        VERIFY   ┌────────┼────────┐
                 ▼        ▼        ▼
          ux-ui-designer  code-reviewer ∥ qa-engineer   (+ security-engineer / domain on trigger)
              (3a)              (3b)
                          │
        TRIAGE          router (4)  iter ≤ 3 → close + read back
                          │
        DEPLOY / OPERATE  devops-engineer (5) → sre-engineer (6)
```

รูปเต็ม 3 มุมมอง (topology · lifecycle · enforcement, Mermaid) → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

ทุก transition ผ่าน **gate** ที่ต้องมี evidence (`pre-implement` · `pre-implement-ui` · `pre-ui-check` · `pre-loop-exit` · `pre-deploy-*` · `pre-destructive` …) — รายละเอียด § Workflow ด้านล่าง

---

## Model Support

shode-house uses a **model-agnostic core**: the same 18 agents, the router style and 20 skills are written to work on any capable reasoning model, and nothing in a skill or agent asks the model which model it is.

Six layers, each with one owner:

| Layer | Holds | Lives in |
|---|---|---|
| Core | universal rules: NO MAGIC, verify-before-done, R0/R1/R2, authority precedence, redaction, language, handoff | [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) (preloaded by all 18 agents); R0, redaction, input trust and no-skip-security are in the safety floor of every agent body and the router style |
| Roles | owns / does not own, judgment, bias default, skill pointers | `agents/<role>.md` |
| Skills | thin root = goal, invariants, exclusions, stop conditions, routing | `skills/<bucket>/<name>/SKILL.md` |
| References | depth, loaded only when the root says so | files beside each `SKILL.md` + `references/` |
| Model calibration | per-family deltas, only when an eval proves the need | none shipped in 3.17 - the base workflow runs without a profile |
| Evals | frozen routing probes + E01 + 16 core scenarios, scored from raw traces | [`eval/`](eval/) |

**What is designed vs what is measured (status, stated plainly):**

- *Designed, checked statically in CI:* the 3.17 simplification (semantic descriptions, thin-router roots, decision boundaries, role-only agent files) and the 4.0.0 switch (router style, verbatim generated tree, safety floor) keep every rule - rule conservation against the cycle baseline, 190 root-tier safety anchors, four byte budgets that only go down.
- *Measured (3.17.0): Claude Code with Sonnet only* (`claude-sonnet-5`). 3.17.0 is released for Sonnet; full numbers and known limitations are in the [CHANGELOG](CHANGELOG.md) 3.17.0 release notes.
  - Core behaviour gate [`eval/CORE-GATE-rc2.md`](eval/CORE-GATE-rc2.md): CORE-GATE-rc2: PASSED (N=3, Sonnet). No regression >= 2 detected on the held-out set (held-out, N=3, Sonnet). The 17-id core set is a DEV set, tuned-on-test: rc2 is the 4th wording iteration made after reading its prompts, expectations and traces. Dev numbers show fit, not generalisation.
  - Routing-probe gate [`eval/PROBE-GATE.md`](eval/PROBE-GATE.md): **NOT PASSED** for the v3.17 skill-description rewrite (N=5 per probe): `diagnose` probe P02 5/5 → 0/5, `drain` probe P09 4/5 → 1/5, description-sensitive total k 64 → 55.
  - Post-gate re-measure (not pre-registered) of the fixed `diagnose` / `drain` descriptions: P02 2/5 (baseline 5/5), P09 3/5 (baseline 4/5) - below the target the maintainer set before this re-run (not in a pre-registered gate file), shipped as a known limitation; held-out routing probes (N=5 each), positives excluding the baseline-0 H07: 40/45 → 43/45; largest per-id drop 1. Probe aggregates: [`eval/baseline/`](eval/baseline/); raw traces stay on the maintainer machine (gitignored).
- *Not measured:* Opus, Fable, Astra and OpenAI (Codex CLI) have **no 3.17 run**. No pass rate, cost or latency claim is made for them, and no "supported" label is given to a model family until its row exists; the cross-model matrix is deferred to 3.17.x.
- *How to measure:* comparison rule and gate fixed before any data - [`eval/PROBE-GATE.md`](eval/PROBE-GATE.md); probes - `bash eval/run-probes.sh`; core matrix - `bash eval/run-core.sh <model>` (the 17-scenario set follows the plugin major: `eval/core-set.sh` picks `eval/scenarios/core-4.0/core-4.0.json` for 4.x, frozen with its own manifest); both need a real Claude Code / Codex CLI on the maintainer machine ([`eval/RUNBOOK.md`](eval/RUNBOOK.md)). OpenAI runs are recorded manually and kept separate from CI.

A model profile may be added later only under the contribution rule in [`AGENTS.md`](AGENTS.md) § Contribution rules: it never redefines workflow, safety, ownership or domain rules. The `model:` values in § Model Strategy below are Claude Code frontmatter defaults, not a statement about which models were evaluated.

---

## 60-second example

```
you   > /shode-house:implement "POST /refund — คืนเงินบางส่วนได้ ห้ามเกินยอดจ่าย"

[router|M1 Ingress Guard|bd-42]
- classify : new-task   - route : business-analyst ∥ solution-architect (1a) → fintech-expert (money trigger) → security-engineer (1c)

business-analyst   ▸ solution-architect    : BRD + AC (G-W-T ×6)        outputs/bd-42/01-business-analyst-1a.md
solution-architect    ▸ fintech-expert   : ADR-007 ledger append-only  outputs/bd-42/02-solution-architect-1a.md
fintech-expert   ▸ router  : cite BOT + PCI-DSS v4 §3.4 · partial refund = reversal entry
security-engineer▸ router  : STRIDE — 2 abuse case → security AC
router  ▸ developer    : impl bd-42  (gate pre-implement ✓ evidence: 4 artifact)

developer    ▸ Verify  : code edited / smoke ✓  (paste pytest: 14 passed)
code-reviewer   ∥ qa-engineer   : 7-dim clean
business-analyst  (spec axis)   : missing AC-5 (idempotency) → FAIL
router            : triage → Phase 2 iter 2
developer    ▸ Verify  : idempotency key added · 16 passed
code-reviewer   ∥ qa-engineer   : 7-dim clean · E2E green
business-analyst  (spec axis)   : 6/6 AC met → PASS

[router|state:TRIAGE|bd:42]  bd close 42 --reason "PASS a1b2c3d 16 passed" → bd show 42: CLOSED
```

สิ่งที่ *ไม่* เกิดในตัวอย่างนี้ — developer พูดว่า "เสร็จแล้ว" · reviewer ผ่านโดยไม่ paste output · solution-architect เดา business rule เรื่องเงินเองโดยไม่ผ่าน fintech-expert

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

**CI = 28 gate sections (#1–#27 + #11b)** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml), รันเองได้ด้วย `make validate`): rule conservation · lazy-load reachability · agent/preload/dispatch budget · cross-reference + section-ref resolution · model single-source · enforcement-map anchor · design-intel pipeline smoke + negative test · skill description cap · generated-tree `--check` (verbatim sources + resolution footer) · retired-name tombstone · tracker-neutral scan · **#27 v4 gates**: A1 tools pin, A8 namespaced skill names and spawn forms, A2 safety floor (`scripts/floor.py --check --require`), A16(a)/(b) shipped-text lint, A15 design-runner suite, W9 eval suites + core-4.0 freeze, `test_floor`, `test_ci_wiring`, `test_ux_design_runbooks`, `test_eval_runners` — required from plugin.json major 4 (`SHODE_REQUIRE_V4=1` rehearses it). CI installs pytest from the hash-pinned [`.github/requirements-ci.txt`](.github/requirements-ci.txt) (`pip install --require-hashes --only-binary :all:`); the workflow token is read-only (`permissions: contents: read`).

**A16(a), the plugin-root rule:** shipped text never falls back from `CLAUDE_PLUGIN_ROOT` to the project — an unset root would make an agent read a same-named project file as plugin knowledge. Red: a default (`${CLAUDE_PLUGIN_ROOT:-.}`, `:=`, `-`, `=`), an alternate value (`:+`, `+`), `||` / `??` / `or` / a ternary after the root or after a parameter-expansion operator (`cd "${CLAUDE_PLUGIN_ROOT%/}" || exit 1` too), an unquoted root test (`test -d $CLAUDE_PLUGIN_ROOT || exit 1`: an empty root vanishes), a root test with a path after the root, and `|| :`, `|| true`, `|| false` or `|| return` after a root test (they carry on). Green: `${CLAUDE_PLUGIN_ROOT:?…}`, or a quoted `test -d "$CLAUDE_PLUGIN_ROOT" || exit 1` before the first use. A16(a) and A16(b) are static heuristics, a best-effort tripwire and never a guarantee: shapes and phrasings not in the tree are recorded known limits, and security review of every shipped-text change stays the primary control.

---

## 🚀 Install

Package source for every host: `plugins/shode-house` (generated from this repo by
`scripts/pack-team.py --tree plugins/shode-house`; CI fails if it drifts).

### Claude Code (CLI/terminal)
```bash
/plugin marketplace add shode666/claude-skill-shode-house
/plugin install shode-house@shode-house
```
Entry: `/shode-house:ask <request>` — the router style runs the main session and dispatches the specialists.
Unattended runs (`claude -p`): set `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, otherwise the CLI kills
reviewers still running after 600 s before the router can integrate their verdicts.

### Codex
Add the repo as a plugin marketplace (`.claude-plugin/marketplace.json` is the shared catalog);
`plugins/shode-house/.codex-plugin/plugin.json` registers the 20 skills. Start with the `ask` skill. Skills run in one
session (no router style on this host): agent spawns return `BLOCKED: unrouted` by design, the safety floor is in the
`ask` skill, and the host's own approval/sandbox setting is the only enforced control for irreversible actions.

### Cursor
Install from this repository (`.cursor-plugin/marketplace.json` → `plugins/shode-house`).
Skills are discovered; there is no slash command — invoke the `ask` skill. Same one-session limits as Codex
(no router style; agent spawns return `BLOCKED: unrouted`; keep the host's approval on).

### Antigravity
Copy or clone `plugins/shode-house` into `.agents/plugins/` (workspace) or
`~/.gemini/config/plugins/` (global). Skills run in one session; Antigravity's validator (agy 1.2.2)
processes the agent files, but whether agents run there is unverified; without the router style the `ask`
skill reports `BLOCKED: team execution needs the router style (Claude Code)` instead of role-playing.

### Cowork (desktop app)
- Drag & drop the `.plugin` file from the GitHub release → Cowork window
- หรือ Settings → Plugins → Install from file

### Update (e.g. from 3.16.0)
```bash
/plugin marketplace update shode-house
/plugin update shode-house@shode-house      # `install` alone keeps the already-installed version
```
Check with `/plugin list` — the version must read 4.0.0.

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

| Team | Members (agent id) | Phase | Deliverable |
|------|---------|-------|-------------|
| 🧭 **Lead** | router (main-session output style) + staff-engineer | All | Workflow state + tech depth |
| 🔍 **Discover** | product-manager + Domain SME | 0 | OKR + opportunity + pain validation |
| 📐 **Design** | business-analyst + solution-architect + ux-ui-designer | 1a/1b/3a | BRD + ADR + UI artifacts |
| 🎓 **Domain** | fintech / erp / sap / trading / insurance / booking / ecommerce `-expert` | 0/1b/3b | Regulation cite + business rule |
| 🛠 **Dev** | developer (parallel) | 2 | Production code (data/ML = developer interim) |
| ✅ **Verify** | code-reviewer + qa-engineer + security-engineer | 3b | Code review + Test + Security |
| 🚀 **Ops** | devops-engineer + sre-engineer | 5/6 | Deploy + SLO + Incident |

**Single-owner capability matrix** — ทุก capability มี sole owner; agent อื่น consult ได้แต่ห้ามผลิต deliverable

---

## 🤖 Agents (18 = 11 core + 7 domain) + the router style

The router is not an agent: it is the forced output style `output-styles/shode-house.md` of the main session (the 3.x
`orchestrator` agent / Oliver, retired in 4.0.0). Spawn agents only as `shode-house:<id>`; a bare type reaches a project
agent. 3.x persona names (formerly column) map to agent ids in `skills/discipline/shode-house-routing/ownership.md` § Formerly (one table).

### Core (11)
| Agent id | Formerly | Model | Team | Role |
|-----|------|-------|------|------|
| staff-engineer | Stan | **fable-5** | Lead | Staff Engineer — cross-team consistency, tech radar, polyglot review |
| product-manager | Patrick | sonnet | Discover | Product Manager — OKR, RICE/WSJF, opportunity sizing, kill decision |
| business-analyst | Bella | sonnet | Design | BA — BRD/FRD/AC G-W-T, Event Storming, RTM |
| solution-architect | Sara | **fable-5** | Design | SA — C4, ADR, NFR (threat model → security-engineer) |
| ux-ui-designer | Uma | **fable-5** | Design | UX/UI + Design System + a11y + **Design Authority**; no Bash in 4.0.0 (design scripts run through the design runner) |
| developer | Dave | sonnet | Dev | Polyglot Dev (parallel developer#N, 14 languages, lazy-load) |
| code-reviewer | Chris | sonnet | Verify | Code Review 7-dim + Unit + Mutation kill ≥ 70% |
| qa-engineer | Quinn | sonnet | Verify | QA — Integration/E2E/Contract/Load/Perf/axe (pen test → security-engineer) |
| security-engineer | Sentinel | **fable-5** | Verify | Security Engineer — STRIDE/LINDDUN, SAST/DAST, CSP/Trusted Types, pen test |
| devops-engineer | Aaron | sonnet | Ops | DevOps/Platform — Docker, CI/CD, IaC (SLO → sre-engineer) |
| sre-engineer | Reggie | sonnet | Ops | SRE — SLO/SLI, error budget, runbook, on-call, blameless postmortem |

### Domain Experts (7)
| Agent id | Formerly | Model | Domain |
|-----|------|-------|--------|
| fintech-expert | Felix | **opus** | Fintech — payment, ledger, ISO 8583/20022, PCI-DSS v4, KYC/AML, BOT |
| erp-expert | Elena | sonnet | ERP/Accounting — GL, AR/AP, MRP, IFRS 15/16, consolidation |
| sap-expert | Sam | **opus** | SAP — ECC + S/4HANA, ABAP, Fiori, BTP, BAPI/IDoc, migration |
| trading-expert | Tara | **opus** | Trading — OMS/EMS, matching, FIX, microstructure, clearing |
| insurance-expert | Iris | **opus** | Insurance — policy, claim, IFRS 17, reinsurance, OIC |
| booking-expert | Brooke | sonnet | Booking — PMS, channel manager, yield, overbooking, GDS |
| ecommerce-expert | Emma | sonnet | E-commerce — catalog, cart, promo, marketplace, fraud |

### Model Strategy (v3.5 — Claude 5 family; 4.0.0 roster)

| Tier | Agents | Frontmatter value | เหตุผล |
|------|--------|-------------------|--------|
| **Fable 5** (4) | staff-engineer, solution-architect, security-engineer, ux-ui-designer | `claude-fable-5` | judgment สูงสุด: cross-team architecture + security + **design direction** (ux-ui-designer = Design Authority นำ look & feel) |
| **Opus** (4) | fintech-expert, sap-expert, trading-expert, insurance-expert | `opus` (alias → Opus ล่าสุด) | regulated-domain judgment (money, SAP, trading, insurance reg) |
| **Sonnet** (10) | ที่เหลือทั้งหมด | `sonnet` (alias → Sonnet ล่าสุด) | execution + structured patterns |
| **Haiku** (0 agent) | mechanical sub-task เท่านั้น | Task `model` override | status digest, broadcast aggregation, bd hygiene — ห้ามผลิต deliverable |

The main session (router style) runs on the session's own model. A project can force every dispatch to Sonnet with `.shode-house/config.yaml` `model_policy: sonnet-only` (the router records `model_downgraded` and tells the user once per session).

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

## ⚡ Slash Commands (6)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:ask [คำถาม / outcome / continue]` | public entry point — ทำงานกับ router และทั้งทีม (skill [`ask`](skills/workflow/ask/SKILL.md)) |
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:init [project]` | Init project scaffold — **default**: interactive wizard; `--quick "<stack>"` direct devops-engineer Docker-first |
| `/shode-house:design-system [feature]` | Smart Spec pipeline — **default**: spec → suggest implement; `--stop`: stop at spec; `--estimate`: add T-shirt sizing; `--stop --estimate` = proposal mode |
| `/shode-house:implement [feature]` | Phase 2-4 — developer + ux-ui-designer + code-reviewer ∥ qa-engineer (uses `review-checklist` skill) |
| `/shode-house:review [path\|jira\|bug]` | Ad-hoc code review (uses `review-checklist` skill) |

> **3-flag rule** (AGENTS.md invariant): ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag รองรับได้ → prefer flags over command proliferation

---

## 📚 Skills (20 lazy-load — bucket organized)

**v3.17 (24 → 20, no stub):** four skills were merged into their owners — the team-meeting entry into [`ask`](skills/workflow/ask/SKILL.md), the evidence protocol and the broadcast/handoff protocol into [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) (root + `handoff.md`/`reporting.md`), drift defense into [`shode-house-workflow`](skills/discipline/shode-house-workflow/SKILL.md) (root + `drift.md`). Old names are no longer loadable; old → new table: [CHANGELOG](CHANGELOG.md).

### `skills/workflow/` — daily process
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`ask`](skills/workflow/ask/SKILL.md) | ALL | **Entry-point** — engage the team + team orientation (discipline card อยู่ที่ router style `output-styles/shode-house.md`) |
| [`dev-gate`](skills/workflow/dev-gate/SKILL.md) | developer + code-reviewer | TDD red-green-refactor + 7-gate quality |
| [`automate-test`](skills/workflow/automate-test/SKILL.md) | qa-engineer + code-reviewer + devops-engineer | CI test pyramid 70/20/10 + threshold |
| [`diagnose`](skills/workflow/diagnose/SKILL.md) | code-reviewer + qa-engineer + developer | Bug + perf root cause — เริ่มที่ feedback loop |
| [`data-migration`](skills/workflow/data-migration/SKILL.md) | developer + devops-engineer + solution-architect | expand-contract + backfill + rollback drill |
| [`api-contract`](skills/workflow/api-contract/SKILL.md) | developer + solution-architect + qa-engineer | semver + deprecation window + consumer contract |
| [`decompose`](skills/workflow/decompose/SKILL.md) | business-analyst + router + product-manager | epic → leaf: tracer bullet + blocking edge + create-then-wire |

### `skills/ops/` — operational discipline
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`incident`](skills/ops/incident/SKILL.md) | sre-engineer + router | Runbook + on-call + blameless postmortem + 5-why |
| [`slo`](skills/ops/slo/SKILL.md) | sre-engineer | SLI / SLO / error budget (Google SRE Book) |
| [`secure`](skills/ops/secure/SKILL.md) | security-engineer | STRIDE + LINDDUN + CSP + Trusted Types + SAST/DAST + prompt injection |
| [`drain`](skills/ops/drain/SKILL.md) | router + developer/code-reviewer/qa-engineer/devops-engineer/ux-ui-designer | Verified backlog → parallel worktree → serial merge → close-on-done |

### `skills/ui/` — frontend quality
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`ui-test`](skills/ui/ui-test/SKILL.md) | qa-engineer + ux-ui-designer + developer | Playwright + axe + visual regression + WCAG 2.2 coverage |
| [`web-q`](skills/ui/web-q/SKILL.md) | ux-ui-designer + developer + qa-engineer + devops-engineer + security-engineer | CWV + Lighthouse + SEO + security headers |

### `skills/style/` — communication style
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`caveman`](skills/style/caveman/SKILL.md) | router + ALL | Compressed output mode |

### `skills/discipline/` — preload modules
| Skill | Owner | Role |
|-------|-------|------|
| [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) | ALL (mandatory) | 5 Philosophy + Safety + Universal Rules + M1 + handoff min fields + Project Evidence Protocol + Input trust (refs: handoff/broadcast protocol, reporting/tag prefix) |
| [`shode-house-routing`](skills/discipline/shode-house-routing/SKILL.md) | router | Routing + RACI + T-shirt + Trust Levels |
| [`shode-house-deliverable`](skills/discipline/shode-house-deliverable/SKILL.md) | Producers | Output contract + Anti-Puppet rule + pointer ไป DoD/ADR/UX evidence |
| [`shode-house-workflow`](skills/discipline/shode-house-workflow/SKILL.md) | router | Phase Contract + Smart Coop + hooks + gates + worktree + run durability + Phase 1c trigger list + Drift Defense M2-M8 |
| [`review-checklist`](skills/discipline/review-checklist/SKILL.md) | code-reviewer + qa-engineer + security-engineer + Domain | Review orchestration core (แกน standards + แกน Spec / severity / gate) |
| [`domain-core`](skills/discipline/domain-core/SKILL.md) | Domain experts (7) | AI Persona Disclaimer + citation contract + source validation |

### `skills/in-progress/` + `skills/deprecated/` — not shipped
Skill ที่อยู่นี่จะไม่ถูกใส่ใน plugin.json (AGENTS.md invariant)

---

## 🔁 Workflow — PEV Loop per bd

```
PEV loop per bd-issue (Plan → Execute → Verify → Triage):
  📋 PLAN
  Phase 0  Discovery       product-manager + Domain SME (opt — new initiative)
  Phase 1a Foundation      business-analyst ∥ solution-architect (parallel)
  Phase 1b Pre-Design      ux-ui-designer + Domain (sequential after 1a, conditional)
  Phase 1c Threat Model    security-engineer (parallel-able with 1b, conditional)
  💻 EXECUTE
  Phase 2  Implement       developer (parallel by scope contract)
  ✅ VERIFY (adversarial — code-reviewer/qa-engineer vs developer, zero trust)
  Phase 3a UI Check        ux-ui-designer POST (sequential gate + Chrome MCP)
  Phase 3b Code Review     code-reviewer ∥ qa-engineer — แกน standards + แกน Spec (verdict default = FAIL)
  🚦 TRIAGE
  Phase 4  Triage          router (max iter 3) → bd close + bd show verify (M8)
  🚀 DEPLOY (continuous per bd)
  Phase 5  Deploy          devops-engineer + sre-engineer
  📡 OPERATE
  Phase 6  Operate         sre-engineer (SLO, incident)

No sprint outer loop / retro — per-bd reflect ใน Phase 4 Triage; continuous OKR review (product-manager)
```

### Phase Gates (RACI-aware + Evidence-mandatory)

`pre-spec` · `pre-spec-expand` · `pre-implement-ui` · `pre-implement` · `pre-ui-check` · `pre-quality-coop` · `pre-loop-exit` · `pre-deploy-staging/uat/prod` · `pre-data-migration` · `pre-destructive`

**Multi-sig pre-deploy-prod (R0)**: devops-engineer (build) + sre-engineer (SLO) + security-engineer (security) + product-manager (OKR/risk)

**Run durability**: run stamp (plugin version + model) · approval ผูก artifact SHA — artifact เปลี่ยนหลัง approve = approval โมฆะ · resume protocol สำหรับ session ที่ตายกลาง pipeline · contract ของ durable runner ที่ devops-engineer generate → [`references/patterns/durable-agent-runtime.md`](references/patterns/durable-agent-runtime.md)

### Handoff Broadcast Protocol (caveman 1-line)

```
business-analyst ▸ developer   : impl bd-42
developer  ▸ Verify : CR + test + sec
Verify ▸ router : 2M 1m
router ▸ Ops   : deploy
```

`▸` = handoff broadcast (formal between agents) · `→` = general flow (informal)

---

## 🛡️ Workflow Drift Defense (8 Mechanisms)

แก้ปัญหา agent หลุด workflow ใน warm follow-up — developer บอก "เสร็จแล้ว" โดยไม่ผ่าน Verify, fix ตรงโดยไม่ผ่าน Phase 1a

| # | Mechanism | What it does |
|---|-----------|-------------|
| M1 | **Ingress Guard** | ทุก agent ก่อน respond: bd show → state → classify → route check |
| M2 | **Follow-up Classifier** | router auto-triage user message (fix/spec/quest/approve/new/status) |
| M3 | **Anti-Puppet "Done"** | developer/code-reviewer/qa-engineer/security-engineer/ux-ui-designer ห้าม claim "done"; only router after multi-sig |
| M4 | **User Comment = FAIL** | feedback ใด ๆ = reopen bd + iter++ |
| M5 | **Spec Change = bd revision** | verbal change ห้าม fix ตรง → business-analyst revision → Phase 1a redo |
| M6 | **SESSION-STATE.md** | router maintain persistent state; ทุก agent read first |
| M7 | **Direct-to-Agent block** | agents other than the router ห้าม accept direct-from-user → route router |
| M8 | **Close-on-Done Guard** | งาน land แล้วต้อง `bd close --reason` + `bd show` paste CLOSED; `bd list` ไม่นับเป็นหลักฐาน |

---

## 💬 Clarifying Style

**`AskUserQuestion` ใช้ได้เฉพาะ main session** (`/init`, `/design-system`, `/implement` และ router ผ่าน `output-styles/shode-house.md`) — sub-agent ทุกตัว **return question bundle** ขึ้นไปให้ main session เปิด popup แล้วเขียนคำตอบกลับ tracker

- option-style 2-4 ตัวเลือก + Recommend ตัวแรก + reason 1 บรรทัด · batch ≤ 4 คำถามต่อ call · ห้ามคำถามเปิด
- **frontier model**: ถามทั้ง frontier ของ design tree รอบเดียว → คำถามที่ขึ้นกับข้อที่ยังเปิด = รอบถัดไป → จบเมื่อ frontier ว่าง

---

## 🌐 Polyglot developer — 14 Languages (lazy-load)

developer อ่าน best practice **เฉพาะภาษาที่ใช้** จาก `references/languages/<lang>.md`
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
├── AGENTS.md                   repo invariants, always-on core (canonical, tool-neutral; detail in docs/repo-invariants/)
├── CLAUDE.md                   @AGENTS.md import + Beads-managed block
├── .claude-plugin/             manifest + marketplace
├── .enforcement-map.json       rule → owner → trigger → source_of_truth → verification
├── .agent-core-budget / .preload-budget / .workflow-scenario-budget   ratchet budgets
├── Makefile                    make validate | pack | stats | skills
├── .pack-allowlist             the only list of what `make pack` ships (docs/, AGENTS.md, CLAUDE.md, README, CHANGELOG do not)
├── .github/workflows/ci.yml    gate invariant + lint (inline bash + jq; = make validate)
├── agents/                     18 expert agents (11 core + 7 domain)
├── commands/                   5 slash commands
├── output-styles/shode-house.md the router style (forced) ยึด main session
├── skills/                     workflow/ ops/ ui/ style/ discipline/  (+ in-progress/ deprecated/ ไม่ ship)
├── references/
│   ├── design-intel/           ux-ui-designer lookup layer (data + search.py, preload 0 tok)
│   ├── patterns/               durable-agent-runtime.md · general.md
│   └── languages/<14 files>    per-language best practice (developer lazy-load)
├── eval/                       scenarios · prompts · baseline · results/<version>/
├── scripts/                    context-budget.py · rule-conservation.py · usage-from-transcript.py …
└── docs/                       PLAN-*.md · pilot-reports/ · failure-modes/ · ADOPT-*-proposal.md
```

---

## 🔐 Security notes — design runner

- **Post-run detection is best-effort.** After a design run, `references/design-intel/scripts/design_run.py` compares the project tree with its state before the run and reports the changes it can see. A payload that runs during the run and then erases its own trace may go undetected. To limit this, the router dispatches no other writer (any agent holding Write, Edit, NotebookEdit or Bash) while a design run is running, until the runner's completion line or report. This is a risk the user accepted for 4.0.0 (decision U3), not a security certification; running the child from a private snapshot of the project is planned after 4.0.0.
- Design runs target loopback origins only; `ux-ui-designer` has no Bash and writes a request, never a command line (runner contract `RUNNER_VERSION` 2.0.0).
- The runner treats global and system git configuration as the user's own, including the global git attributes file `$HOME/.config/git/attributes` (applied by default; the runner drops `XDG_CONFIG_HOME`, so the HOME-relative default is read), the global ignore file `$HOME/.config/git/ignore`, and a global `core.attributesFile` / `core.excludesFile` (recorded as user-trusted in the report's config scan). In bypass-permissions mode an agent can write these files, which voids that assumption.

## 🔐 Security notes — hooks (Claude Code `.plugin` distribution)

- Hooks are a control only where hooks execute: Claude Code with the plugin's hooks/hooks.json loaded and not switched off. A project (or any settings file the host reads) can set disableAllHooks: true, and then no plugin hook runs at all. They are defence in depth, not a guarantee, and they never stop a hostile repository.
- The generated (marketplace) tree ships no hooks; in Cowork the hooks stay unconfirmed until a manual check.
- Fail-open: without python3, or when python3 cannot start the scanner (missing file, unsupported -I, crash), the F-10 collision scan is skipped with a stderr note; without jq the state and scope guards fall back to advisory (.degraded / silent in a project with no engagement). A missing hooks/scripts/_casefold.sh (a broken install: the shared case fold ships next to the hooks) also fails open: the scope guard and the state guard exit 0 and record a .degraded line when the project has an engagement, so .git, scope and state writes are then not protected by the hooks; scripts/scope-check.sh itself exits 64, which its hook callers treat as a deny. Hook input that jq cannot parse or evaluate is NOT a fail-open case for the two write guards: the scope guard and the state guard deny any non-empty input that jq rejects (malformed JSON, a lone UTF-16 surrogate escape such as \ud800 anywhere in the input, including the file content, or a tool_input that is not an object) with the reason 'malformed/unsupported hook input', and the payload is never echoed. A jq built without regex support makes the same check fail, so with such a jq every Write, Edit and NotebookEdit these guards judge is denied. The scope guard also denies a Bash call whose input jq cannot parse or evaluate (for example a tool_input that is not an object); a valid Bash call still runs with a jq that has no regex support. Empty input still exits 0, and a missing jq still fails open as above. Every other hook keeps fail-open on unparsable input.
- A hook process that crashes (for example a shell that segfaults) exits with a code other than 2, which the host treats as non-blocking: a crashing hook fails open, like every other hook failure that is not an explicit deny. A locale-related crash of Homebrew bash 5.3.15 on macOS (inside the system locale libraries, after a forked subshell restores a non-C locale variable) was observed in the test harness only; the guards never set a non-C locale in a forked shell and did not crash in 6,000 runs under that bash. A failure of scripts/scope-check.sh, which the scope guard runs, is treated differently: the guard denies when it ends with an exit code that is not one of its documented results for the call (a crash, a signal, 126 or 127). A failure that ends with a code documented for the call is read as that result; the case known to arise is exit 2: in a subagent's binding resolution and ownership check, exit 2 is the documented 'no scope manifest' result, which allows, so a scope-check.sh that fails with exit 2 (bash's own code for a usage or syntax error) is read as that result and the write is allowed.
- The F-10 scan runs the first python3 on the host shell's PATH (a residual risk). A Python start failure also fails open (exit 0, stderr note). Control of the hook's environment can force it, and the same control turns off the state and scope write guards too: which programs PATH finds (a fake python3 for this scan; a substituted bash, or a fake jq, whose answers then decide the write guards' verdicts), BASH_ENV (for example through .claude/settings.json env), SHELLOPTS with noexec or onecmd, SHELLOPTS with xtrace together with a PS4 that runs a command substitution, or that assigns a variable the scripts do not reset (bash still expands PS4 once, at the trace of each script's first command, before that command turns xtrace off), an exported shell function (BASH_FUNC_<name>%%), and the dynamic loader's variables (DYLD_* on macOS, LD_PRELOAD on Linux). These act as the hook's shell or its tools start, before any command of the hook has run, so no hook code can stop them (DYLD_* and LD_PRELOAD were not probed, nor was a PS4 that runs a command substitution, because it recurses). That is equivalent to disableAllHooks, the disclosed full bypass, so it is no new capability for a hostile project. BASHOPTS is listed with this class, but a shopt option it turns on could be turned off by script code, and none of bash 5.3's 59 shopt options, each tried through BASHOPTS, changed a verdict. The other shell options SHELLOPTS can turn on that loosened a verdict are turned off by the first command of both write guards and of scripts/scope-check.sh: errexit, keyword, noglob and xtrace (with xtrace, bash expands PS4 in the script's own shell before each traced command, so an arithmetic PS4 such as $((tool_name=0)) assigned the variables a verdict branches on); verbose only adds denies, and posix, which also only added denies, is turned off when the scripts unset POSIXLY_CORRECT. Ordinary variables that bash or jq read later and that loosened a write guard are cleared by both write guards and by scripts/scope-check.sh at their start: HOME (jq sources $HOME/.jq, which can redefine a jq builtin), FUNCNEST and TMOUT, and the shell-behaviour variables GLOBIGNORE, EXECIGNORE, CDPATH, POSIXLY_CORRECT and BASH_COMPAT, with IFS set back to space, tab and newline, whether the environment or that PS4 set them (on bash 5.3 and 5.2 a PS4 ${GLOBIGNORE:=*} made the scope guard's scan of the state directory find no file, so collisions were allowed). The state guard clears them before its jq check, so an EXECIGNORE cannot hide jq from it; a PATH without jq stays the missing-jq fail-open described above.
- Fail-closed cases a legitimate user can hit: a Write, Edit or NotebookEdit is denied when its target has more than 64 not-yet-existing directory levels, when an existing parent directory cannot be entered, when the path uses '..' to step back over a symlink, or when the target itself is a symlink. For the designer (ux-ui-designer) this holds wherever hooks run; in a project with an engagement it holds for every agent. Create the directories first, or write to the real (non-symlink) path. On macOS, in a project with an engagement, the outsider collision check also compares the Unicode NFC form of a non-ASCII path, because APFS treats canonically equivalent spellings as one name: a decomposed (NFD) spelling of another agent's file, or a Thai name with its marks typed in another order, collides like the composed one. The normaliser is /usr/bin/perl with Unicode::Normalize from the macOS base system, started once per scope check (one check for each active bd a write is compared with, two for a scripts/scope-check.sh --amend) for the path and every non-ASCII manifest entry together; if a non-ASCII path cannot be normalised (it is not valid UTF-8, or that perl cannot run), the write is denied with that reason. Owner (grant) matching never normalises, so an agent writing its own file must use the spelling its Scope Contract pattern uses. Linux does not normalise. macOS is recognised by the kernel's own name, which /usr/bin/uname (or /bin/uname) reports when it runs with an empty environment, never by a variable of the hook's environment (not OSTYPE, and not UNAME_s or UNAME_SYSNAME, which macOS's uname would otherwise print in place of the kernel's name), and no variable of the hook's environment chooses the helper or the lock library the scope check loads: a variable of the environment may only shorten the scope check's time budget (SCOPECHECK_BUDGET_MS) or add a deny, with one exception, SCOPECHECK_ROOT, which names the project the check reads and which the scope guard sets on every call. Control of the hook's environment that acts before the hook's first command has run (which programs PATH finds, bash and jq among them, BASH_ENV, SHELLOPTS with noexec or onecmd, SHELLOPTS with xtrace and a PS4 that runs a command substitution or assigns a variable the scripts do not reset, an exported shell function, DYLD_* or LD_PRELOAD: the start-up class above, equal to disableAllHooks, where BASHOPTS is listed too) reaches past this, as it reaches past every hook. Where the platform cannot be determined, the check behaves as on macOS: so on a host with neither /usr/bin/uname nor /bin/uname, every non-ASCII Write, Edit or NotebookEdit in a project with an engagement needs /usr/bin/perl with Unicode::Normalize, and is denied without it. In a project with an engagement, the scope check of a Write, Edit or NotebookEdit (finding the active bds and comparing the path with their manifests) has a time budget, so that it ends inside the 5 s hook timeout (a hook cut off by the timeout lets the write through): it ends 3 seconds after the hook starts, and a write whose check runs past it is denied (reason token scope-budget). With /bin/bash 3.2, whose clock counts whole seconds, it ends between about 1 and about 4 seconds after the hook starts, so on that shell a write whose check needs about 1 to 2 seconds can be allowed on one try and denied on the next. The clock takes nothing from the hook's environment. One step is not covered: a single read of a manifest file cannot be interrupted, so a manifest of several hundred MB, which only a write outside the scope lock can create, could still run past the timeout. Direct calls of scripts/scope-check.sh, for example --amend, have the same 3-second budget for each check: a call that runs past it is refused (scope-budget), and a refused --amend leaves the manifest unchanged. Lower-case ASCII manifest entries cost almost nothing (2,000 of them take about 0.3 s per write on macOS), but each upper-case or non-ASCII entry starts case-fold processes (measured on macOS with bash 5.3: about 3-4 ms per upper-case ASCII entry, about 8 ms per non-ASCII entry, about 15 ms per entry stored in decomposed (NFD) form when the path is non-ASCII; on Linux about 1 ms per upper-case and 2 ms per non-ASCII entry). So a manifest with several hundred such entries, many active bds (each is one more scope-check call), or thousands of workflow state files can make writes in that project denied until the manifest or the state directory is reduced.
- The F-10 scan never follows a symlinked container: if the project's Claude directory itself, or its skills, commands or output-styles subdirectory, is a symlink, it is reported 'not scanned', and a shadow placed behind it is not detected.
- The F-10 scan stops at 500 entries per directory; a shadow confirmed elsewhere is still denied, but a shadow hidden among more than 500 entries in the same directory may not be seen. The scan also stops at 2 s of wall time: a shadow confirmed before that is still denied, but anything not yet scanned is not checked (allowed with a warning).
- Git directories: where hooks execute, a Write, Edit or NotebookEdit that lands in .git, .git/**, or the git dir that a .git file points to (a linked worktree, a submodule, a --separate-git-dir checkout, and that git dir's commondir) is denied for every agent and for the main session, with or without an engagement; case variants, symlinked aliases, '..' and trailing '/' or '/.' are resolved first, and a pointed git dir is also matched by directory identity, so any spelling the filesystem treats as that directory (for example the decomposed (NFD) spelling of an accented path on macOS) is denied too. A path with '..' is judged under both readings a host may use (the '..' normalised away first, or the missing directories created and every symlink followed before the next '..'), and a git dir under either reading is denied. The git CLI is not affected: use git config, git commit and so on. Bash commands are not judged (the advisory Bash ceiling), so a shell redirect into .git is not blocked.
- Host-level protection for .git (rule syntax per the Claude Code permissions documentation, code.claude.com/docs/en/permissions): hooks protect .git only where they run (not with disableAllHooks, not in the generated tree, unconfirmed in Cowork). To protect it wherever Claude Code itself enforces permissions, add this to the project's .claude/settings.json: {"permissions":{"deny":["Edit(/.git/**)"]}}. One Edit(...) deny rule covers every built-in file-editing tool: Write, Edit and NotebookEdit. In project settings a path that starts with a single '/' is anchored at the project root, and the host checks a rule against both the requested path and the symlink-resolved path. In a linked worktree or a submodule checkout the project's .git is a FILE, not a directory; add "Edit(/.git)" next to it so the pointer file itself is covered (the same anchored path form). A linked worktree, a submodule or a --separate-git-dir checkout keeps its git dir at the path its .git file names, usually OUTSIDE the project (the main repository's .git/worktrees/<name>, the superproject's .git/modules/<name>, or the separate git dir): each such git dir needs its own deny entry with an absolute path, written with a leading '//', for example "Edit(//abs/path/to/repo.git/**)". A linked worktree also uses its common dir, the main repository's whole git dir, where git runs hooks and reads config for every commit made in the worktree: add "Edit(//abs/path/to/main/.git/**)" for it, which also covers .git/worktrees/<name>. For a worktree of a --separate-git-dir repository the common dir is that separate git dir, so its own "Edit(//abs/path/to/repo.git/**)" entry is the one to add. Bash is not covered by these rules (only the file commands and redirections the host itself recognises), so a shell command can still write into .git; the git CLI keeps working. Recommended deny list, all five forms: "Edit(/.git)", "Edit(/.git/**)", "Edit(**/.git)", "Edit(**/.git/**)" and "Edit(//<absolute path of the common git dir>/**)". The permissions documentation states the directory forms directly: a leading '/' anchors the rule at the project root, a leading '//' makes it an absolute path, '**' crosses directories, so the common-dir entry also covers .git/worktrees/<name>, a relative pattern such as "Edit(**/.git/**)" matches at any depth, which reaches the .git directory of a nested repository, and an anchored rule matches only at its anchored location, so "Edit(/.git)" does not reach a nested submodule's <sub>/.git pointer file. The two single-file forms, "Edit(/.git)" for the project's own pointer file and "Edit(**/.git)" for a nested submodule's pointer file, are inferred from the documented gitignore pattern semantics (a pattern without a trailing '/' matches a file as well as a directory) and are not separately documented. The hooks deny writes to these pointer files regardless; the host rules are defence in depth where hooks do not run.
- Fail-closed availability effects of the .git rule: because the rule judges the physical target, any Write, Edit or NotebookEdit, in any project with the plugin's hooks, is denied when the target cannot be resolved physically: more than 40 symlinks followed in one path, counted together however they nest (a loop, a long chain of links, or links that name other links many times over), a symlink that cannot be read, more than 64 not-yet-existing directory levels, a lookup longer than 1023 bytes while the existing part of the path is resolved (only lookups along the existing part are capped, at the smallest PATH_MAX of the supported hosts; the not-yet-existing tail is not measured. So on Linux a path of 1,024 to 4,095 bytes is refused when its existing part needs such a lookup, and so is a write into an existing directory whose own path is longer than 1,018 bytes), or an existing directory that cannot be searched. It is also denied when a .git file or a commondir file on the paths checked has a first line longer than 1,063 bytes (the read stops there, so a huge or blank-padded pointer file cannot stall the check), or holds anything after its first line other than line breaks (git takes the whole file, line breaks included, as the path of the git dir, and every pointer git writes is one line), or has 1,065 bytes or more before its first NUL byte even when everything after its first line is line breaks (the read stops there, so the end of the file is not seen: a short first line padded with line breaks, and a first line of exactly 1,063 bytes followed by two line breaks, are denied too), or has a CR, a space or a tab right before its first NUL byte (git reads the file only up to its first NUL byte and keeps that character in the path of the git dir, while the check drops a trailing CR or blank), and when the check exceeds its work budget, so that it always ends inside the 5 s hook timeout (a hook cut off by the timeout lets the write through): more than 4,096 path steps (components read, .git entries probed and directory comparisons), more than 16 .git files or .git symlinks on the paths checked, or more than 2 seconds. Create the directories first, or write to the real path the links lead to. Separately, every Write, Edit or NotebookEdit whose path contains a line break (LF, CR) or another control character (U+0000-U+001F, U+007F-U+009F) is denied, by the scope guard in every project and by the state guard in a project with an engagement, because a shell reading of such a path can differ from the name the filesystem opens (reason token path-control-char).
- The designer's ux path set also refuses manifest, lockfile and tool-config names: package.json, composer.json, deno.json, project.json, package-lock.json, npm-shrinkwrap.json, tsconfig.json, tsconfig.*.json, jsconfig.json, jsconfig.*.json, *.config.json and any name starting with a dot, under outputs/ and design-system/ (reason token ux-config).

## 🛡️ Safety Discipline

**Destructive actions** ขออนุญาตเสมอ (R0): `git push --force` (any branch) · `git reset --hard` · `DROP TABLE` / `DELETE without WHERE` · `rm -rf` กว้าง / delete prod resource · edit migration ที่ apply prod แล้ว · modify auth/IAM

Pattern: ระบุ action + impact + rollback → ขอ confirm → execute

---

## 🤝 Contributing — Adding/Removing Agent

**Add new domain expert**:
1. Drop `agents/<name>.md` (ตาม 5-Dim Role template)
2. Update the routing table ใน `output-styles/shode-house.md` + role directory ใน `skills/workflow/ask/SKILL.md` + `skills/discipline/shode-house-routing/SKILL.md`
3. `make validate` ต้องเขียว → bump version → `make pack`

**Remove agent**: ลบไฟล์ + remove จาก routing + capability matrix

**New rule / new skill / new model profile** → ตอบคำถามใน [`AGENTS.md`](AGENTS.md) § Contribution rules ก่อน (failure ที่กัน · canonical owner ใน [`docs/enforcement-map.md`](docs/enforcement-map.md) · always-on หรือ lazy · eval ที่คุ้มครอง). Default = ไม่เพิ่ม.

> ตอนนี้ **ไม่รับ agent ใหม่** — 18 agent + router ครอบ capability ครบแล้ว; สิ่งที่ project ต้องการคือ E2E proof, benchmark และ reliability ไม่ใช่ agent ที่ 20

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
