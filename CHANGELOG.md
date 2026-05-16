# Changelog

All notable changes to shode-house plugin.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [Semver](https://semver.org/).

## [2.6.1] — UX Gate Closure (Patch)

ปิด hole ใน workflow discipline: Dave (developer) เริ่ม implement frontend ได้โดยไม่ผ่าน Uma (UX/UI). Audit เจอ Uma หาย 7 จุดทั่ว pipeline — patch ทุกจุดให้บังคับ pre-implement-ui gate

### Added

- **Phase Contract — `ux-design` phase** (meeting skill, conditional)
  - Insert ระหว่าง `design` → `implement`. Exit = wireframe (Figma link/frame ID) + tokens.json + a11y checklist
  - Trigger: feature touch frontend/UI/component/page/view/email template/dashboard
  - Skip: pure backend/API/data pipeline/CLI/library — Oliver confirm กับ user ถ้ากำกวม
- **Lifecycle Hook — ux-design** (meeting skill) — Pre: BRD+ADR loaded, frontend trigger detected. Post: hand-off bundle to Dave saved
- **Approval Gate — `pre-implement-ui`** (Oliver) — block Dave start frontend implement โดยไม่มี Uma artifact ครบ (Figma + tokens + a11y + state inventory)
- **DoD line — UI Design pre-check** — Uma artifact ต้องมีก่อน implement; แยกจาก UI Test (post-implement) ที่มีอยู่
- **commands/design-system.md Step 3.5** — Uma UX/UI design step (conditional หลัง Sara, ก่อน Summary) → `outputs/04-ux-ui.md`
- **commands/implement.md Step 0** — Oliver UI Precondition Check ก่อน delegate Dave
- **Orchestrator Engagement Plan step 3.5 Uma** — conditional ถ้า frontend; Approval Gate table มี pre-implement-ui row
- **Dave Process step 2.5** — UI Precondition check before identify language
- **Universal rule** (meeting skill) — "ห้าม start implement frontend โดยไม่มี Uma artifact"

### Changed

- Approval Gates standard count: 7 → **8** (pre-implement-ui เพิ่ม)
- Oliver ข้อห้าม — เพิ่ม "ห้าม design ข้าม Uma สำหรับ frontend; ห้าม delegate Dave implement FE โดยไม่มี Uma artifact"
- Dave ข้อห้าม — เพิ่ม "ห้าม implement frontend โดยไม่มี Uma artifact" + reference pre-implement-ui gate
- commands/implement.md Rule 0 — UI artifact precondition (priority สูงสุด ก่อน spec rule)
- commands/design-system.md Rule 6 — ห้าม skip Step 3.5 Uma ถ้า frontend

### Token cost

- meeting skill: +~250 tokens (Phase Contract row + Lifecycle Hook row + Gate update + DoD line + Universal rule)
- commands/design-system.md: +~200 tokens (Step 3.5 Uma section)
- commands/implement.md: +~150 tokens (Step 0 + Rule 0)
- agents/orchestrator.md: +~80 tokens (gate row + pipeline step + ban)
- agents/developer.md: +~60 tokens (ข้อห้าม + Process step 2.5)
- **Total**: ~+740 tokens (~+0.5%) — แค่ rule update, ไม่กระทบ persona/scope/expertise

### Root cause (audit finding)

Pre-v2.6.1 Uma หายจาก default pipeline 7 จุด:
1. commands/design-system.md (Triage→Bella→Domain→Sara→Summary, no Uma)
2. commands/implement.md (allow Dave start ถ้ามี spec; spec ไม่ครอบ UI artifact)
3. commands/init.md Phase 4 (next-step suggest /implement หลัง /design-system แม้ขาด Uma)
4. agents/orchestrator.md Engagement Plan (Bella→Domain→Sara→Dave→Chris→Quinn→Aaron, Uma หาย)
5. agents/developer.md ข้อห้าม (spec ก่อน — ไม่ครอบ UI artifact)
6. skills/meeting/SKILL.md Phase Contract (design exit = ADR+diagram+threat model only)
7. skills/meeting/SKILL.md DoD (ตรวจ UI Test post-implement; ไม่มี pre-implement design check)

Real-world impact: Dave เดา UI, hardcode styling, no design tokens, retrofit a11y, visual inconsistency, pre-merge-ui gate block ที่ PR (rework cycle)

## [2.6.0] — Lean Credibility Edition

จาก realworld feedback — domain expert (Felix/Iris/Tara/Elena/Sam) confident แต่ผิดบ่อย; persona "Senior Expert" overpromise. Root cause: agent file = persona prompt only, knowledge = Claude training (cutoff May 2025), ไม่มี citation discipline สำหรับ domain claim. **Fix lean (~+1500 tokens, ~+1%)** ก่อน RAG/eval

### Added

- **⚠️ AI Persona Disclaimer** (universal ใน meeting skill — apply ทุก domain expert)
  - Agent = AI persona based on Claude training (cutoff May 2025), อาจ outdated
  - ระบุชัด: provide structured thinking/framework/checklist; ไม่ provide professional advice/legal opinion/audit sign-off
  - บังคับ disclaimer 1 บรรทัดเริ่มทุก engagement: "⚠️ AI persona, training cutoff May 2025 — validate critical claims with [domain expert / official source]"
  - Money / regulation / safety / compliance decision ต้อง validate กับ certified pro + official source + internal SME

- **📚 Domain Evidence Protocol** (extension ของ Project Evidence — meeting skill)
  - Domain claim (regulation/standard/protocol/spec) ต้อง cite เหมือน project fact
  - Format: `<Standard> <Version> <Clause/Section> [<Date>] — <Claim>`
    - ✅ "PCI-DSS v4.0 Req 3.5.1 (effective Mar 2024) — store PAN encrypted at rest"
    - ✅ "BOT notice 12/2566 ข้อ 4 — KYC ระดับ enhanced สำหรับ PEP"
    - ✅ "IFRS 17 para 32-39 — General Measurement Model"
    - ❌ "ตาม PCI-DSS ต้อง encrypt PAN" (no version, no clause)
  - cite ไม่ได้ → mark explicit "⚠️ General guidance from training memory — must validate กับ official document version ปัจจุบัน"
  - Apply ทุก: regulation, standard, protocol, industry spec, tax/accounting rule

### Changed

- **Honest Persona Reframe** — 5 domain agents เปลี่ยน persona intro line จาก "Senior Expert" → "AI Co-pilot literate" (scope/expertise list/อื่นๆ คงเดิม)
  - Felix: "Senior Fintech Expert" → "Fintech AI Co-pilot (Banking, Payment, KYC/AML literate)"
  - Iris: "Senior Insurance Expert" → "Insurance Domain AI Co-pilot (Life/Health/Motor/Property literate)"
  - Tara: "Senior Trading Expert" → "Trading Microstructure AI Co-pilot (OMS/EMS/Matching literate)"
  - Elena: "Senior ERP/Accounting Expert" → "ERP/Accounting AI Co-pilot (GL/AR-AP/MRP literate)"
  - Sam: "Senior SAP Expert" → "SAP AI Co-pilot (ECC/S4HANA/ABAP/Fiori literate)"
  - All 5 agents inherit AI Persona Disclaimer + Domain Evidence Protocol จาก meeting skill

### Skip / Backlog (need engagement evidence ก่อน — ห้าม build > use repeat)

- **#3 RAG Knowledge Skills** (fintech-knowledge / insurance-knowledge / trading-knowledge / sap-knowledge) — +30-60% token cost; revisit after 2-3 real engagements + evidence "Claude memory ผิด version X / regulation Y ซ้ำๆ"
- **#4 Eval Harness** (golden Q&A per domain) — 0 production cost แต่ต้อง domain expert review answers; revisit when CPA/actuary/SAP consultant พร้อม validate
- **FS Idea 1 Guardrails Architecture** (subagent role split) — structural change ขัด lean
- **FS Idea 3 5-Phase Operational Flow** (per-agent workflow) — per-agent deep change
- **FS Idea 4 Steering Examples** — file proliferation; use เป็น test fixture เมื่อ eval harness setup

### Token cost

- meeting skill: +~900 tokens (Disclaimer + Domain Evidence)
- 5 agent files: +~50 tokens each (persona reframe + 2 inheritance refs)
- **Total**: ~+1500 tokens upfront (~+1% of plugin)

### Lesson reinforced

- v2.5.0 → v2.6.0 ไม่ผ่าน real engagement → keep changes lean (Disclaimer + citation discipline เท่านั้น)
- ห้าม adopt RAG/eval/role-split จนกว่าจะมี evidence ว่า lean fix ไม่พอ

## [2.5.1] — Cowork Validator Fix

จาก realworld pain — Claude for Mac drag-drop install fail "Plugin validation failed" ตั้งแต่ v2.4.1 (v2.4.0 ผ่าน). Binary search ผ่าน 7 builds (FIX-A ถึง FIX-G) → root cause = **plugin description ยาวเกิน Cowork validator limit** (CLI `claude plugin validate` ผ่าน, Cowork stricter)

### Fixed

- **plugin.json description**: 530 → 179 chars, ASCII only, ตัด em-dash + Thai
- **marketplace.json top-level description**: 206 → 51 chars
- **marketplace.json plugin description**: 301 → 85 chars
- ทั้งหมด ASCII safe, no em-dash, no Thai mix
- Cowork drag-drop install ผ่านแล้ว ✅ (ทั้ง content unchanged from v2.5.0)

### Lesson learned (เพิ่มใน meeting skill ว่าควร)

- Cowork validator มี description length cap ที่เข้มกว่า CLI
- ทุกครั้งที่ bump version: keep all descriptions **≤ 200 chars, ASCII safe**
- Detail / feature list / marketing copy → README.md (ไม่ใช่ description)
- Pre-release: `claude plugin validate` ผ่าน CLI ≠ install ผ่าน Cowork. ทดสอบ drag-drop จริงก่อน push
- `docs/`, `CHANGELOG.md`, `.mcp.json` — ปลอดภัย ไม่ใช่ culprit (testing ผ่าน FIX-C/D/E)

## [2.5.0] — FS-Inspired Discipline

จาก audit `anthropics/financial-services` repo (May 2026) — adopt 3 patterns ที่ map กับ shode-house lean philosophy. **Universal patterns ใน meeting skill** ไม่แตะ agent files (single source of truth, agent inherit)

### Added

- **🔐 Input Trust Levels** (FS Idea 2 — Untrusted Input Threat Modeling)
  - 5 levels: Canonical / Operational / User-supplied / External / Untrusted
  - Required handling per level (use as fact / trust+cite / clarify / validate / treat as hypothesis)
  - **Trust cascade rule**: agent B อ้าง agent A → trust = min(A's level, A's output level), ห้าม upgrade chain (กัน hallucination cascade — risk #4 ใน handoff)
  - Pattern: ก่อน claim → state `[source: <level> / <evidence>]`

- **📦 Standard Output Deliverables** (FS Idea 6 — Output Format Specificity)
  - Universal template (3-4 named deliverables/agent)
  - Examples สำหรับ 5 domain agents (Felix/Elena/Iris/Tara/Sam)
    - Felix: Ledger model + Compliance gap + Reg cite + Risk register
    - Elena: TB extract + Accrual schedule + Roll-forward + Variance
    - Iris: Policy state machine + Reserve calc + IFRS 17 model + Reinsurance
    - Tara: Order lifecycle + Pre-trade risk + Matching priority + Clearing
    - Sam: Customizing config + ABAP/CDS + Integration + S/4 migration
  - Agent inherit ผ่าน meeting skill (ไม่ duplicate ใน agent file)

- **🚫 "I Never Do" Pattern** (FS Idea 9 — Explicit Prohibition + Evidence)
  - Universal template + examples ทั้ง 5 domain agents
    - Felix: ห้าม post ledger ตรง / make KYC decision / approve payment / update rate table
    - Iris: ห้าม approve payout / set reserve final / issue policy / authorize ex gratia
    - Tara: ห้าม execute trade / override risk block / modify priority / cancel client order
    - Elena: ห้าม post journal / close period / approve payment run / modify CoA
    - Sam: ห้าม transport to PRD / modify standard SAP / open prod debug / disable auth
  - Audit-ready guardrail visible to user/auditor

### Skip (need engagement evidence ก่อน)

- FS Idea 1 Guardrails Architecture (subagent split — structural change, ขัด lean)
- FS Idea 3 5-Phase Operational Flow (per-agent deep — รอ engagement พิสูจน์ pain)
- FS Idea 4 Steering Examples (file proliferation — รอจำเป็นจริง)
- FS Idea 10 Specialist Subagent Dispatch (ซ้ำกับ Idea 1)

### Why universal in meeting skill ไม่แก้ agent files

- Single source of truth — agents inherit, ไม่ duplicate
- ลด context cost (1 edit แทน 5 edits)
- Agent-specific refinement ทำใน engagement ถัดไป — after using → know what to refine
- ตรงกับ design constraint v2.4.1: token-net ≤ 0 ใน main context

## [2.4.1] — Token-Lean + Anti-Sprawl

จาก realworld pain (May 2026 engagement): (1) test pass แต่ UI ใช้จริงไม่ได้ — เคส edit screen validate `input == current_state` → save ไม่ได้ตลอด, (2) agent ทำเกิน scope / ตีความผิดทิศ / overlap แก้ file เดียวกัน, (3) plugin sprawl เริ่มเสี่ยง — patch ใส่ rule ทับโดยไม่ trace origin

**Design constraints**: token-net ≤ 0 ใน main context (zero meeting skill change), 1 mechanism = ครอบหลาย painpoint, ทุก rule ต้อง trace origin ได้

### Added

- **🎯 Scope Contract** (pre-implement gate, lazy load)
  - 5 fields: `IN` / `OUT` / `Files` / `Stop` / `Echo` — 1 template ครอบ scope creep + misinterpretation + agent overlap + token waste
  - `Files` field = natural file ownership lock — Oliver scan active contracts, overlap = block + wait
  - `Echo` field = confirm understanding 1 บรรทัดก่อน implement → จับ misinterpretation ก่อน work
  - **Location**: `references/scope-lock.md` (lazy, 0 main-context cost) + `agents/orchestrator.md` § Scope Contract Enforcement (Oliver enforce) + `agents/developer.md` § Process step 5 (Dave trigger)
  - **Token impact**: 0 in meeting skill, +250 in orchestrator (lazy), +50 in developer (lazy), +250 in references (lazy when triggered)

- **🔄 Mutation Evidence** (Quinn — state-changing flow)
  - Trigger: edit/update/create/delete/toggle/submit/save/transfer/approve/cancel
  - บังคับ: pre-state + action (NEW value, not equal current) + post-state (must differ) + backend verify + no-op safety check
  - ห้าม test แบบ no-op (submit ค่าเดิม) → จับ tautology test
  - **Location**: `agents/qa-engineer.md` § Mutation Evidence (lazy)
  - **Catches**: edit-validation-contradiction, optimistic update rollback, cache stale, wrong row update

- **📋 Failure-mode Catalog** (data-driven rule evolution)
  - `docs/failure-modes/<NNN>-<slug>.md` — ทุก realworld failure = 1 entry
  - Format: summary / symptom / root cause (ตาม pipeline layer) / pattern / mechanism ที่จับ / mechanism ที่ยังไม่จับ / status
  - **Seed**: `001-edit-validation-contradiction.md`
  - **Why**: kill "ผมว่าน่ามี" rule patching → rule ทุกข้อในอนาคตต้อง trace กลับ catalog entry หรือ external authority

- **📜 Why Provenance Convention** (anti-sprawl)
  - ทุก rule section ใหม่ต้องมี comment `<!-- Why: failure-modes/<id> | engagement: <id> | external: <ref> -->`
  - Rule ที่ไม่มี Why = candidate ลบใน periodic audit
  - **Already applied**: Mutation Evidence (link to failure-mode 001), Scope Contract (link to realworld pain)

### Changed

- `agents/qa-engineer.md`: เพิ่ม § Mutation Evidence ใต้ UI Test Evidence Template; provenance comment link to failure-mode 001
- `agents/orchestrator.md`: เพิ่ม § Scope Contract Enforcement (Oliver registry + 3 enforcement points)
- `agents/developer.md`: Process step ปรับจาก 8 → 10 (เพิ่ม Scope Contract pre + close); ข้อห้าม เพิ่ม "ห้าม Edit/Write โดยไม่ post Scope Contract"
- `.claude-plugin/plugin.json`, `marketplace.json`: version bump 2.4.0 → 2.4.1 + describe ใหม่

### Token economy

| File | Cost type | Δ tokens |
|------|-----------|----------|
| `skills/meeting/SKILL.md` | main context (every engagement) | **0** (no change — patched in lazy load files only) |
| `agents/orchestrator.md` | lazy (Oliver active) | +250 |
| `agents/qa-engineer.md` | lazy (Quinn active) | +180 (Mutation Evidence) + 30 (provenance) |
| `agents/developer.md` | lazy (Dave active) | +50 |
| `references/scope-lock.md` | lazy (when triggered) | +900 (new file, used on demand) |
| `docs/failure-modes/001-*.md` | not loaded by agent | +0 (reference for human + future Devil's Advocate) |

**Net effect on baseline engagement** (no implement work): 0 token added
**Net effect on engagement with implement** (load Dave + Oliver + scope-lock once): ~+1200 token, but offsets rework cost (Echo field alone saves 1 misinterpretation → typically saves 5000+ tokens of wrong work)

## [2.4.0] — Enforcement Edition

จากปัญหาจริง: agent (1) ไม่ค่อยทำ UI test แม้มี rule, (2) ยืนยัน fact ตาม real-world แต่ไม่ตรง project นี้ → เพิ่ม hard gate + evidence protocol

### Added

- **🎬 UI Test Hard Gate** (combo C — trigger + anti-puppet + scaffold + CI block)
  - **Trigger condition** (Quinn): Mandatory ถ้าไฟล์เปลี่ยนใน `frontend/`/`ui/`/`components/`/`pages/`/`views/` หรือ `*.vue`/`*.tsx`/`*.jsx`/`*.svelte`/`*.html` หรือ Uma involved หรือ AC pattern "When user clicks/sees/types..."
  - **Evidence template** (Quinn): Playwright console + visual diff path + axe critical/serious/total + trace path + 5 critical screen screenshots — incomplete = block PR
  - **Auto-scaffold** (Aaron): Web project type → pre-install `@playwright/test` + `@axe-core/playwright` + visual baseline (Chromatic/Percy/Loki) + folder convention `tests/{e2e,visual,a11y,fixtures}` + Makefile targets (`ui-test/ui-test-ui/ui-baseline/ui-codegen`) + parallel CI job
  - **Approval Gate `pre-merge-ui`** (7th gate, added to standard 6): block merge ถ้า UI changed but no Playwright/visual/axe evidence
  - **DoD updated**: visual+a11y entry → conditional UI test + evidence requirement

- **🔍 Project Evidence Protocol** (NO MAGIC philosophy extension)
  - **Strengthened Philosophy 1**: "real-world knowledge ≠ project's fact"
  - **Forbidden phrase list**: "usually" / "by default" / "typically" / "standard practice" / "should support" / "in most cases" — ใช้ = ต้อง cite project evidence ทันที
  - **Required evidence types**: runtime version (`node -v`), framework (`Read package.json:N`), config format (`Glob '**/application.*'`), dependency (`pnpm list`), feature (Bash output), file (`Glob` first), convention (CLAUDE.md), DB version (`SELECT version()`)
  - **Anti-puppet extended**: ❌/✅ pattern สำหรับ real-world guess vs project evidence
  - **Format**: ทุก factual claim cite `[<file>:<line>]` หรือ `[output: <command>]`
  - **Universal Rules**: เพิ่ม "ห้าม claim project fact จาก real-world knowledge"

### Changed

- meeting skill: NO MAGIC philosophy strengthened, Approval Gates 6 → 7 (added pre-merge-ui), DoD checklist UI test entry conditional, Anti-puppet extended with real-world-guess section
- Quinn (qa-engineer): Mandatory Pre-merge Gates + UI Test Trigger Condition + Evidence Template
- Aaron (devops-engineer): New section 2.5 UI Test Scaffold (Web project default)
- init.md: Aaron Phase 2 auto-trigger UI scaffold for Q1=Web app/Full-stack monorepo, Phase 3 Verify paste UI test output

## [2.3.0] — Sandcastle-Inspired Edition

Inspired by [mattpocock/sandcastle](https://github.com/mattpocock/sandcastle) ([video](https://www.youtube.com/watch?v=E5-QK3CDVQM)).

### Added

- **AFK / Interactive / Hybrid mode** (Oliver Phase 2 — บังคับเลือก option-style)
  - AFK = auto delegate, R0 only ask
  - Interactive = human approve ทุก hand-off
  - Hybrid (default) = AFK pre-deploy → Interactive deploy ขึ้น
  - Mode binds R0/R1/R2 enforcement

- **Pluggable Tracker** (replace hardcoded beads)
  - Support: beads (bd), GitHub Issues, Linear, Jira, Asana
  - Universal abstraction: `tracker.create/ready/close/link`
  - Bella + Oliver use tracker abstraction

- **Structured Tag Prefix** (extend `[agent]`)
  - Format: `[name|state:..|task:..|finding:..]`
  - Standard keys: state/task/engagement/file/finding/pass/fail/env/health/mode
  - Default human-readable; structured สำหรับ pipeline parser

- **`/shode-house:init` wizard** (interactive scaffold)
  - 6 option-style clarifying (project type/stack/domain/tracker/mode/sandbox)
  - Aaron scaffold + Bella seed + Oliver config (`.shode-house/config.yaml`)
  - Verify anti-puppet protocol (Phase 3)

- **Lifecycle Hooks** (per Phase Contract)
  - pre/post hook ทุก phase (clarify/design/implement/review/integration/deploy)
  - Aaron auto-trigger via Makefile/CI

- **Prompt Template Substitution** (commands convention)
  - Static: `{{PROJECT_NAME}} {{STACK}} {{DOMAIN}} {{TRACKER}} {{ENV}} {{ENGAGEMENT_ID}}`
  - Shell eval: `` {{!`bash command`}} ``

- **Sandbox Provider Table** (Aaron — Docker/Podman/Devcontainer/Codespaces/Vercel/Local)

- **Provider-agnostic agent note** (meeting skill intro)
  - Default: Claude. Portable to OpenCode/Codex via prompt structure

### Changed

- Engagement Plan template เพิ่ม `Mode` + `Tracker` field
- Bella RTM section เปลี่ยนจาก bd-only → tracker abstraction
- meeting skill: Tracking section restructure (table + selection)

## [2.2.1] — Agent Tag Prefix
- Mandatory `[agent]` prefix ทุก message สำหรับ visibility

## [2.2.0] — Bug Slayer Edition
- 13 mandatory layers (contract-first, type strict, mutation+property test, pre-merge integration smoke, visual+a11y block, canary+auto-rollback)
- 3 mandatory mechanisms (DoD checklist, Anti-puppet rule, Postmortem template, Docker verify protocol)

## [2.1.0]
- Skill rename: sd → meeting (`/shode-house:meeting`)

## [2.0.0]
- Plugin rename: sd → shode-house
- Commands: `/sd:*` → `/shode-house:*`

## [1.2.0]
- Adopt 4 Archon concepts (Phase Contract, Loop with Exit, Approval Gates, Worktree Isolation)

## [1.1.0]
- Lean audit: sd skill -44%, Dave -27%

## [1.0.0]
- Optimal Edition: consolidate, modernize, lazy-load references

## [0.x]
- Initial development (15 agents + 6 commands + 1 skill)
