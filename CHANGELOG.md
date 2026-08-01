# Changelog

All notable changes to shode-house plugin.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [Semver](https://semver.org/).

## [3.10.0] — enforcement repair (Skill tool + tool defects) + Oliver output style + report brevity — 2026-08-01

> **Root-cause release #3.** v3.8 แก้ "discipline ไปไม่ถึง subagent" ด้วย `skills:` preload แต่แก้ไม่หมด: agent ทุกตัวระบุ `tools:` แบบ explicit โดยไม่มี `Skill` ซึ่ง [docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) ระบุว่าเท่ากับ **ห้าม subagent โหลด skill ใด ๆ** → 12 จาก 19 skill ไม่เคยถึง agent เลย

### 🐛 Fixed
- **`Skill` เพิ่มใน `tools:` ครบ 19 agents** + CI check #14 กัน regression
- **Tool defects**: Oliver +`Bash` (เป็นเจ้าของ `bd`/`git worktree`/M8 `bd show` แต่รันไม่ได้) · Bella + Patrick +`Grep`+`Glob` (NO MAGIC บังคับ cite ด้วย Glob/Grep) · Stan +`Write`+`Edit` (Handoff Contract บังคับเขียน artifact)
- **Recite Card 2 เวอร์ชันขัดกัน** (v3.1 ใน `meeting` / v3.5 ใน `discipline`) → source เดียว
- **`dev-gate` 7 vs 11 gates** · **5 commands hardcode "ภาษาไทย"** ขัด mirror-the-user (v3.8) · **README** Phase 7 Learn ที่ลบแล้ว + ชื่อ gate ที่ไม่มีจริง · **`drift`** โฆษณา M1 ที่ย้ายออกไป v3.8 · dead ref `skills/in-progress/…` ใน 17 agent

### ✨ Added
- **`output-styles/oliver.md`** (`force-for-plugin: true`) — Oliver ยึด main session; output style แก้ system prompt ของ main loop โดยตรง ไม่กระทบ subagent
- **Report Brevity** (`shode-house-discipline`, 19/19) — work deep, report short + return format ≤ ~15 บรรทัด
- **`data-migration`** + **`api-contract`** skills · **prompt-injection §** ใน `secure` (0 hits ก่อนหน้านี้ ทั้งที่ 7 agent ถือ WebFetch) · **ADR lifecycle §** ใน `deliverable` (`Superseded by` = 0 hits ก่อนหน้านี้)
- CI check #15 (output-style frontmatter) · `make pack` ship `output-styles/`

### 🔄 Changed
- ย้ายเข้า `shode-house-discipline` (ถึง 19/19): Handoff Contract (เดิม preload 1/19) · Agent Tag Prefix (เดิม 0/19) · Close-on-Done M8 · Skill-loading map
- ย้ายออกจาก `shode-house-discipline` (ไม่ใช่ของทุกคน): Engagement Mode + phase-orchestration → `shode-house-workflow` · Universal UX/UI rules → `ui-test`
- **`shode-house-discipline` 20,097 → 16,245 B = -71 KB ต่อ fan-out 19 ตัว**; No Man-Day 34→7 บรรทัด, Clarifying 82→17, PEV ASCII diagram ใน workflow → 8 บรรทัด

> Skill 19 → **21**. Bias Discipline **ไม่ถูกแตะ** — ตรวจแล้วทั้ง 19 บล็อกเนื้อหาต่างกัน ไม่ใช่ copy ซ้ำ

---

## [3.9.0] — backlog drain (worktree fan-out + serial merge) + M8 Close-on-Done Guard — 2026-07-30

> **Root-cause release #2.** ปิด 2 failure mode ที่วัดได้จริง: (1) **stale-open bd** — งานเสร็จ merged แล้วแต่ไม่มีใครปิด issue -> backlog โกหก รอบถัดไปทำซ้ำ (2) **git race / tree collision** ตอน agent หลายตัว commit บน trunk พร้อมกัน

### ✨ Added

- **`drain` skill** (`skills/ops/drain/`) — orchestration pattern สำหรับ backlog ที่ **verified แล้ว**: verify set (`bd show` ทีละตัว — `bd list` ไม่นับ) -> Oliver route + **group by file-locality** -> fan-out 1 worktree-isolated agent ต่อ item (TDD, unit test เท่านั้น, commit บน `fix/<id>`, **ห้าม push**) -> main loop `git cherry-pick` **serial** -> 1 aggregate fast-gate -> 1 push -> `bd close` ทุก item พร้อม evidence. 8 invariants + `When NOT to use` + `Required inputs — refuse without` + Skill composition ครบตาม repo invariant
- **`skills/ops/drain/workflow-template.js`** — Runner A (Workflow tool) parameterize `ITEMS`; guard `ITEMS.length === 0` และ `> 20`. Runner B = `Task` tool fan-out (Claude Code default) ใช้ COMMON brief เดียวกัน
- **M8 — Close-on-Done Guard** (`shode-house-drift`) — งาน land แล้วต้อง `bd close <id> --reason "<verdict> <commit_sha> <test_result>"` -> `bd show <id>` -> **paste output**. Can/Can-NOT table ต่อ agent; `PARTIAL`/`BLOCKED` **คง OPEN** พร้อม note (no false close); `FALSE_POSITIVE` ปิดเป็น invalid พร้อม proof

### 🔄 Changed

- **DoD** (`shode-house-deliverable`) — เพิ่มข้อ **bd CLOSED with evidence**; code merged แต่ bd ยัง OPEN = ยังไม่ done. Anti-Puppet list เพิ่ม "ปิด bd แล้ว" (ไม่มี `bd show`) เป็น pattern ต้องห้าม
- **`shode-house-workflow`** — Phase 4 Triage post-hook บังคับ close-with-reason + `bd show` re-confirm; tracker table (beads) แสดง `--reason` + verify step; Worktree Isolation ชี้ไป `drain` สำหรับ batch backlog; อ้าง Drift Defense เป็น M1-M8
- **`/implement`** — Step 7 Triage เพิ่ม `--reason` + `bd show` gate; rule ใหม่ #10 (Close-on-Done) + #11 (batch -> `drain` ไม่ใช่ `/implement` ซ้ำ)
- **Oliver** (`agents/orchestrator.md`) — bd close section เพิ่ม M8 requirement + ห้ามจบ run ที่มี item FIXED แต่ bd ยัง OPEN
- **CI gate check #11** — เพิ่ม `drain` ใน cross-ref alternation

> Skill count 18 -> **19** (ops bucket 3 -> 4). `drain` ไม่ถูกใส่ใน `skills:` frontmatter ของ Oliver — เพดาน <= 3 skill/agent (CLAUDE.md) ยังคงอยู่; เรียก on-demand ผ่าน `/shode-house:drain`

---

## [3.8.0] — 🔴 fix: discipline never reached subagents (skills preload + handoff contract) — 2026-07-20

> **Root-cause release.** Diagnosis: `docs/DIAGNOSIS-agent-coordination-drop.md`

### 🐛 Fixed — the coordination-drop root cause

- **`skills:` frontmatter on all 19 agents** — ก่อนหน้านี้ **0/19** agents โหลด discipline ได้เลย: ไม่มี `Skill` ใน `tools:` (0/19), ไม่มี `skills:` frontmatter (0/19), ไม่มี hook layer, และ CLAUDE.md ที่ auto-load เข้า subagent เป็นของ **target project** ไม่ใช่ของ plugin repo. `meeting/SKILL.md:40` สั่งว่า "ทุก agent ต้องโหลดอย่างน้อย `shode-house-discipline`" ซึ่ง **ทำไม่ได้ในทางกายภาพ** → Recite Card / 5 Philosophy / evidence protocol / Phase Contract / drift defense หายทุกครั้งที่ `Task` delegate. Regression นี้เข้ามาตั้งแต่ v3.1 ที่แตก god-skill เป็น lazy-load skills. `skills:` inject **full content เข้า subagent ตอน startup** — เปลี่ยนจาก convention เป็น enforcement
- **M1 Ingress Guard ย้าย `shode-house-drift` → `shode-house-discipline`** — M1 บังคับที่ *ทุก* agent แต่ `drift` เป็น Oliver-only skill ที่ agent อื่นไม่ preload. `drift` เหลือ M2–M7 (Oliver enforcer). ลบ duplicate header ที่ค้างอยู่ด้วย

### ✨ Added

- **Handoff Contract** (`shode-house-workflow`) — phase artifact ต้องอยู่ในไฟล์; delegation ส่ง **path ไม่ส่งเนื้อหา**; producer return = structured conclusion + artifact path (ห้าม dump transcript กลับ orchestrator); delegation message ต้องมี bd-id + paths + phase + iter เสมอ (sub-agent ไม่เห็น conversation history). ปิด "game of telephone" — inter-agent misalignment ≈ 37% ของ multi-agent failure (MAST, arXiv:2503.13657)
- **Response Language rule** (`shode-house-discipline`) — ทุก agent **ตอบภาษาเดียวกับที่ user เขียนมา** ไม่ fix ไทย ไม่ fix อังกฤษ; เปลี่ยนตาม message ล่าสุด; user สั่งชัดเจน = override. Verbatim ห้ามแปล: code/path/command/log, Recite Card, tag prefix + handoff line, regulation cite, bd field + phase/gate name
- **Language momentum trap guard** — 🔬 **measured defect**: smoke test v3.8 (Dave + Chris, prompt ภาษาอังกฤษ) → Chris ตอบอังกฤษ ✅ แต่ **Dave ตอบไทย ❌** ทั้งที่ preload rule เดียวกัน. สาเหตุ: Recite Card (ไทย verbatim) + agent prompt body (ไทย) มาก่อน → ลากภาษาทั้ง response (สอดคล้อง IFScale "bias towards earlier instructions"). เพิ่ม explicit rule: card + agent-file language **ไม่นับเป็น signal**, ตัดสินจาก user message เท่านั้น + self-check ก่อนส่ง
- **CI gate check #13** — ทุกชื่อใน `skills:` ต้อง resolve เป็น shipped skill + ห้ามชี้ `in-progress/` หรือ `deprecated/` + ต้องมี `shode-house-discipline` ขั้นต่ำ. **จำเป็นเพราะ Claude Code ข้าม skill ที่หาไม่เจอแบบเงียบ ๆ** (log ลง debug เท่านั้น) → ไม่มี check นี้ = regression กลับมาโดยไม่มีใครรู้

### 🔄 Changed

- `shode-house-workflow` trim (prompt-template + why-blocks) เพื่อคง invariant ≤ 300 บรรทัด หลังเพิ่ม Handoff Contract
- **`ADOPT-loop-engineering-proposal.md` #5 ประเมินผิด** — เขียนไว้ว่า sub-agent isolation "ทำแบบ emergent อยู่แล้ว แค่ยังไม่ใช่ rule / เสี่ยงต่ำ" ความจริง isolation ทำงาน *แรงเกินไป* จนตัด discipline ทิ้งหมด = root cause อันดับ 1 ไม่ใช่ nice-to-have. #1 circuit-breaker + #2 learning-loop เลื่อนไปหลังวัดผล v3.8

---

## [3.7.0] — no-Python dev-loop + content reconciliation + loop-engineering doc — 2026-06-27

### ✨ Added

- **Inline CI gate** (bash + jq) in `.github/workflows/ci.yml` — replaces `check_index.py` + `lint.py` with **no script file at all** (runs only on GitHub, never on a contributor's machine). Mirrors every fail-contributing check (skill size, excluded/shippable buckets, Cowork desc caps + ASCII, agent model + Fable-5 whitelist, model-table single-source, manifest array-of-path-strings, JSON syntax, frontmatter name/description, name==folder, cross-ref + path-ref resolution). Parity-tested: passes clean repo, fails on injected violations.
- **`Makefile`** — no-Python dev-loop: `make pack` (zip artifact, same include/exclude set as old builder) · `make stats` · `make skills`.
- **`docs/ADOPT-loop-engineering-proposal.md`** — maps 2026 loop-engineering patterns onto shode-house; proposes circuit-breaker, bounded-execution, Reflexion `learning-loop` promotion, reward-hack guard, sub-agent isolation.

### 🔄 Changed / 🐛 Fixed

- **No Python, no script files** — removed `scripts/` entirely (check_index, lint, build_plugin, publish, setup_precommit, list_skills, harvest_shortcuts, caveman_stats, _lib), `tests/` (pytest), `eval/validate_fixtures.py`, `pytest.ini`. `.pre-commit-config.yaml` now stock hooks only (no custom local script runs on commit — this was the source of the local "popup"); the gate is inlined in `.github/workflows/ci.yml` and runs only on GitHub.
- **All 19 agents** now reference `shode-house-evidence` (was 2/19) — CLAUDE.md invariant satisfied.
- **Stale-detail fixes** — removed dead "Phase 7 Learn" (staff-engineer); `15 agents` -> `19` (deliverable); persona disclaimer made model-agnostic (was hardcoded "May 2025"); stripped ~16 `v2.x` version-archaeology stamps from `implement.md` + `shode-house-workflow`; README/CLAUDE/meeting version labels reconciled.
- **CLAUDE.md** — prerequisites, dev-loop, build invariant rewritten for the no-Python toolchain.

> Shipped content: agent evidence refs + skill content trims only. Dev-loop migration is build/CI infra (not shipped in `.plugin`).

---

## [3.6.5] — quality harness: dev-loop tests + CI + manifest array guard — 2026-06-26

### ✨ Added

- **`tests/`** (dev infra, ไม่ ship) — pytest suite สำหรับ dev-loop scripts; 27 cases, good+bad fixture ต่อ Cowork-critical invariant (desc length/ASCII, model whitelist, skill size + thin-entry exception, manifest array form). พิสูจน์ว่า enforcement layer ยัง enforce จริง
- **`.github/workflows/ci.yml`** — gate ทุก PR/push: `check_index.py` + `lint.py` + `pytest` + `eval/validate_fixtures.py`
- **`eval/`** (foundation, ไม่ ship) — quality harness ตาม bd-101: `fixtures/{triggers,routing,failure_modes}.yaml` (24 cases, seed จาก pilot G1-G11), `validate_fixtures.py` (corpus gate, cross-check ชื่อ skill/agent จริง), `README.md` runbook. Scorer = agent-orchestrated (ยังไม่ทำ)

### 🐛 Fixed / 🔄 Changed

- **`check_index.py` check #8** `check_manifest_array_form` — reject object-form `skills`/`commands`/`agents` array (สาเหตุจริงของ v3.1.0 "Plugin validation failed"); บังคับ path string เริ่ม `./`, ห้าม `..`/`\`. ปิด gap ที่ schema check ครอบ description แล้วแต่ไม่ครอบ array shape
- **Hygiene** — `chmod +x` `scripts/caveman_stats.py` + `scripts/harvest_shortcuts.py` (ให้ตรงกับ script อื่น)

> หมายเหตุ: ไม่มี shipped content (skills/agents/commands/manifest) เปลี่ยน behavior — เป็น maintainer/build-gate + dev infra ล้วน. `.plugin` artifact bump version แต่ payload เท่าเดิม

---

## [3.6.4] — learning-loop (self-improving, gated, non-blocking) — 2026-06-15

### ✨ Added

- **`skills/in-progress/learning-loop/`** (ไม่ ship — bake ก่อนเหมือน eval-harness): self-improving loop แบบ Hermes-inspired แต่ gated
  - **Non-blocking guarantee**: HOT path = `bd remember` capture (append-only) + session_start load bounded top-N; COLD path = distill/gate/promote offline (ห้ามใน PEV loop) → loop ไม่สะดุด
  - **Plugin/project split**: lessons store = project artifact (bd-first); method skill + cross-project promote = plugin ผ่าน gate (human + check_index/lint + eval-harness)
  - promote เฉพาะ pattern ข้าม project (recurrence ≥ N); project-only lesson อยู่ project ตลอด (YAGNI, กัน plugin drift)

---

## [3.6.3] — workflow audit: no-overlap / no-gap + pipeline — 2026-06-15

### 🔄 Changed / 🐛 Fixed

- **Phantom agents resolved** (gap): Devon/Mason/Tex อ้างเป็น sole-owner แต่ไม่มีไฟล์ → reassign interim (data/ML = Dave, docs = Bella); สร้าง dedicated agent เมื่อ project ต้องการจริง (YAGNI). sync routing + orchestrator + README + CLAUDE
- **Pipeline parallel** (cross-bd staggered): Sara design chunk N ▸ Dave build chunk N พร้อม Sara design chunk N+1 — ผ่าน chunk-bd + interface contract + WIP cap 2-3 (routing)
- **Multi-bd long-run orchestration**: checkpoint (bd + state.json) + fan-out cap (WIP) + retry (iter++ max 3) + reduce-from-bd; wire harness contract (routing)
- **Harness runner owner** ชัด: Aaron (infra/CI-level) · Dave (app-level)

---

## [3.6.2] — harness contract + brownfield-safe adopt — 2026-06-15

### ✨ Added / 🔄 Changed

- **Runtime guarantee = generate, don't ship**: plugin ดูแลแค่หลักการ+วิธีการ (contract); runner ที่ enforce จริง (fan-out cap/retry/checkpoint/token budget) → **Aaron** generate fit-stack เข้า **target project repo** (infra-level; app-level → Dave; ผ่าน dev-gate) เมื่อมี long-run need
- **Harness contract = บังคับ establish ทุก project** (`/init` rule 11 → `.shode-house/config.yaml`)
- **Oliver Harness Contract Check** (project entry): grep `harness-contract` marker ใน **project ปลายทาง** `./.shode-house/config.yaml` + `./CLAUDE.md`/`AGENTS.md`; ไม่เจอ → บอก user + แนะนำ `/init` (ไม่ auto-generate)
- **`/init` brownfield guard (non-destructive)**: detect git/manifest → ADOPT mode — **check ของเดิมก่อน → reuse → เติมเฉพาะที่ขาด (ask ก่อน) → ห้ามทับ** (ชน → `*.shode-house.new` + ถาม)
- **adopt → append `## Harness (shode-house)` section ใน project CLAUDE.md** = marker + doc ว่า harness ทำอะไร (contract/long-run/tracker/runner/reused+added)

---

## [3.6.1] — harness de-script + bd-first + long-run — 2026-06-15

### 🔄 Changed

- **eval-harness = agent-orchestrated** (no python/sh): ลบ `run_eval.py`; Run Pipeline ใช้ Task tool (subject + judge subagent)
- **Measurement Protocol** (กู้ determinism แบบ non-script): raw-runs table transparency + measurement primitive (`wc`) paste-as-evidence + judge ordinal rubric `{0,.25,.5,.75,1}`
- **Long-run protocol**: map-reduce batch subagent + bd/file checkpoint + idempotent resume + bounded fan-out 3-5
- **bd-first storage**: `/review --debt`, eval output, long-run progress ledger, caveman stats → bd note/issue ถ้ามี `.beads`/bd; ไม่งั้น `.md` fallback (raw runs = file เสมอ)
- **PEV-loop align**: eval-harness WHEN sprint retro → Phase 4 Triage (per-bd)
- **SHODE-HOUSE-MASTER.md** scripts tree: `.sh` → `.py` (สะท้อนจริง + v3.6 scripts)

---

## [3.6.0] — ponytail + caveman adoptions — 2026-06-15

> **Focus**: adopt 7 ideas จาก [ponytail](https://github.com/DietrichGebert/ponytail) (YAGNI-first) + [caveman](https://github.com/JuliusBrussee/caveman) (compression) — ลด code/token, เพิ่ม drift guard

### ✨ Added

- **YAGNI ladder** (dev-gate Step 0): หยุดก่อนเขียน code — need? / stdlib / native / dep เดิม / one-line / minimum. Pointer ใน `agents/developer.md` Implement Loop
- **Lazy ≠ Negligent carve-out** (dev-gate + caveman + developer.md): YAGNI/compression ห้ามตัด validation/data-loss/security/a11y/regulation
- **Deferred-shortcut convention** `shortcut(bd:N): reason; upgrade → path` (dev-gate Gate 3) + `scripts/harvest_shortcuts.py` (debt ledger) + `/review --debt` mode
- **caveman levels** (lite/full/ultra) + **compress-memory-file** sub-mode + **stats mode** + `scripts/caveman_stats.py` (token-saving estimate)
- **3-arm compression eval** (in-progress/eval-harness): baseline / "Answer concisely." / caveman — claim เฉพาะ delta C-vs-B (honest)

### 🔄 Changed

- **`scripts/check_index.py`** เพิ่ม 2 check: (6) agent model frontmatter (allowed value + Fable-5 whitelist + no dated string) · (7) model-table single-source (ห้าม copy model table นอก README — drift guard ตาม CLAUDE.md)
- **CLAUDE.md** เพิ่ม invariant v3.6 (model enforce, new scripts, Lazy≠Negligent) — ประเมิน caveman-compress แล้ว: ไฟล์ terse อยู่แล้ว delta ≈ 0 → ไม่ compress (capability ใช้กับ verbose file อื่น)
- **eval-harness** แก้ owner drift: Evan (reverted v3.3) → maintainer offline
- **eval-harness = agent-orchestrated** (no python/sh): ลบ `run_eval.py`; Run Pipeline ใช้ Task tool (subject + judge subagent) ล้วน; fixtures JSON เก็บไว้ (data, agent อ้างถึง); แก้ fixture path drift (`tests/eval-fixtures/` → `skills/in-progress/eval-harness/fixtures/`)

---

## [3.5.1] — Uma = Design Authority on Fable 5 — 2026-06-11

### 🔄 Changed

- **Uma → `claude-fable-5`** (Fable 5 ตอนนี้ 4 ตัว: Stan, Sara, Sentinel, Uma; Sonnet 12 → 11) — Fable 5 ทำงาน design UX/UI ได้แข็งแรง user ต้องการให้ Uma นำการตัดสินใจ look & feel
- **Design Authority role ใหม่** (agents/ux-ui-designer.md § Design Authority): Uma = final say เรื่อง look & feel / visual direction / interaction pattern + proactive advisory ต่อ Sara (UX impact ของ architecture), Dave (implementation fidelity), Bella (UX acceptance criteria) — boundary ยัง zero-overlap (แนะนำ/veto ได้ แต่ไม่ผลิต deliverable ของคนอื่น)
- Routing skill: Conflict Resolution เพิ่ม row "Look & feel → Uma ชนะ" (ยกเว้นชน a11y law / security / regulation); capability matrix Uma เพิ่ม "Look & feel direction (final say)"
- README Model Strategy + core table + CLAUDE.md model whitelist sync

---

## [3.5.0] — Claude 5 model matrix + fallback + doc-drift cleanup — 2026-06-10

> **Focus**: Revise model ตาม Claude 5 family (Fable 5 ออกแล้ว) + fallback strategy + ล้าง doc drift ที่กิน token / ทำให้สับสน

### 🔄 Changed — Model matrix (19 agents)

- **Fable 5 (3)**: Stan (staff-engineer), Sara (solution-architect), Sentinel (security-engineer) — `model: claude-fable-5` (full string; ยังไม่มี alias `fable` เป็นทางการ). Judgment สูงสุด: cross-team architecture + security
- **Opus (4)**: Felix, Sam, Tara, Iris — keep `opus` alias (ตาม Opus ล่าสุด = 4.8 อัตโนมัติ). Regulated-domain judgment
- **Sonnet (12)**: ที่เหลือ — keep `sonnet` alias (= 4.6)
- **Haiku (0 agent)**: ใช้เฉพาะ mechanical sub-task ผ่าน Task `model` override (status digest, broadcast aggregation, bd hygiene) — doc ใน routing skill § Token-saving
- **Fallback**: README § Model Strategy — settings `"fallbackModel": "opus,sonnet"` (ครอบคลุม subagent, max 3 chain) + budget mode `CLAUDE_CODE_SUBAGENT_MODEL=sonnet`
- **CLAUDE.md invariant ใหม่**: model values whitelist + ห้าม pin dated string + ตาราง model มีที่เดียว (README)

### 🗑️ Removed

- `commands/setup-project.md` + `commands/spec-only.md` — deprecated alias เกิน window ที่สัญญา (ลบใน v3.2 แต่ค้างถึง v3.4.2); plugin description บอก 5 commands แต่ ship 7

### 🐛 Fixed — doc drift (token waste + contradiction)

- `shode-house-routing` skill: ตาราง "ทีม (15 agents)" stale จาก v2.x (ขาด Stan/Patrick/Sentinel/Reggie + model column ขัดกับ README) → แทนด้วย roster 19 ตัวแบบ 1 บรรทัด + pointer ไป frontmatter (single source of truth)
- `shode-house-routing` skill: เติม section ว่าง `## 🔧 Token-saving` (model tier + lazy-load + bd SoT + caveman); ลบ header ว่าง `## 📦 Standard Output Deliverables`, `## 💬 Clarifying`, `## 🆕 New Phases` (เนื้อหาหายตอน split v3.1)
- `shode-house-discipline` skill: ลบ header ว่าง `## 🔁 Workflow Discipline`; Recite Card tag → v3.5
- README: badge 3.1.0 → 3.5.0; "Opus (6)" ขัดกับตารางที่ mark opus 7 ตัว → ตาราง Model Strategy ใหม่; commands section 6+2 → 5

### ⚠️ Known issue — Cowork install (ต้อง verify หลัง release)

- Cache ฝั่ง Cowork ของ v3.4.2 พบ: manifest ถูก strip field `skills`, ไม่มี `agents/` + `commands/` + `skills/workflow/` → skills/agents ไม่โหลดใน session. ถ้า reinstall v3.5.0 แล้วยังไม่โหลด → พิจารณา flatten `skills/` เป็น 1 ระดับ (auto-discovery-safe) ใน v3.6

---

## [3.4.2] — Maintainer scripts .sh → .py (cross-platform) — 2026-05-31

> **Focus**: Convert 6 maintainer `.sh` scripts to Python (`.py`) for cross-platform parity. Python 3.9+ stdlib only (PyYAML optional). Each `.py` warns clearly on Python <3.9.

### 🔄 Changed (Option B — full conversion)

- `scripts/lint.sh` → **`scripts/lint.py`** (8 pre-publish checks; PyYAML preferred, regex fallback)
- `scripts/check-index.sh` → **`scripts/check_index.py`** (5 invariant checks; CLAUDE.md size/bucket/Cowork)
- `scripts/build-plugin.sh` → **`scripts/build_plugin.py`** (uses `zipfile` stdlib; no `zip` binary dep)
- `scripts/list-skills.sh` → **`scripts/list_skills.py`** (tabular skill index)
- `scripts/publish.sh` → **`scripts/publish.py`** (git/gh CLI via subprocess; --branch arg)
- `scripts/setup-precommit.sh` → **`scripts/setup_precommit.py`** (best-effort pre-commit install)
- **NEW**: `scripts/_lib.py` — shared helpers (Python version check + color output + repo_root)

### 🐍 Python prerequisite

- **Python 3.9+** mandatory for repo dev-loop scripts
- macOS/Linux: pre-installed (or `brew install python@3.12`)
- Windows: install from python.org or Microsoft Store
- Each `.py` checks `sys.version_info < (3, 9)` and fails with platform-specific install guide
- Optional: PyYAML for full YAML validation (`pip install --user pyyaml`); regex fallback when missing
- Documented in CLAUDE.md § Prerequisites

### 🔄 Misc updates

- `.pre-commit-config.yaml` — drop shellcheck hook; switch lint hook from `bash scripts/lint.sh` to `python3 scripts/lint.py`
- `CLAUDE.md` — header v3.3.0 → **v3.4.2**, add Prerequisites section
- `README.md` — script names updated (`scripts/{list_skills,check_index,build_plugin,lint,publish}.py`)
- `.claude-plugin/{plugin,marketplace}.json` — v3.4.1 → **v3.4.2**

### 📊 Stats v3.4.2

- Scripts: 6 .sh → **6 .py + 1 _lib.py** (7 total Python files)
- User-facing scripts: 0 (unchanged — agents don't invoke any script)
- Maintainer scripts: now cross-platform Mac/Windows/Linux ✓
- Lint check count: 8 (unchanged)

### 🧪 Smoke tests passed

- ✅ `list_skills.py` — 21 lines output, all skills shown
- ✅ `build_plugin.py` — built `shode-house-v3.4.2.plugin` correctly (71 files)
- ✅ `check_index.py` — all invariants pass
- ✅ `lint.py` — 8/8 PASS (PyYAML available)
- ✅ `publish.py --help` — argparse works
- ✅ `setup_precommit.py` — imports OK
- ✅ `_lib.py` — Python version check + repo_root + color helpers tested

### Migration

- ✅ Backward-compat: old `.sh` deleted; `python3 scripts/<name>.py` invocation
- ✅ pre-commit hook auto-runs lint.py (no manual change)
- ⚠ Contributors: ensure Python 3.9+ available before pre-commit fires

---

## [3.4.1] — Revert workflow script, keep schema in skill — 2026-05-31

> **Focus**: Drop `scripts/workflow_state.py` per v3.3 philosophy (discipline > mechanical layer; same lesson as Evan/sprint revert). Move state.json schema documentation to `shode-house-workflow` skill. Agents use Read/Write tools directly on JSON — no script needed.

### 🗑️ Removed

- **`scripts/workflow_state.py`** — over-engineer per v3.3 philosophy. ~30-40% extra enforcement over discipline didn't justify added complexity + Python dep + script-agent sync risk
- **`scripts/publish-v3.1.0.sh`** — legacy version-specific publish script (use `scripts/publish.sh`)

### 🔄 Changed

- `skills/discipline/shode-house-workflow/SKILL.md` — added **State persistence** section documenting structured `outputs/<bd-id>/state.json` schema (mandatory fields, phase status enum, Oliver bootstrap rule). Fixed duplicate "Lifecycle Hooks" header (cosmetic).
- `.claude-plugin/{plugin,marketplace}.json` — v3.4.0 → **v3.4.1** (description ASCII)

### 📊 Stats v3.4.1

- Scripts: 8 → **6** (drop workflow_state.py + publish-v3.1.0.sh legacy)
- User-facing scripts: 1 → **0** (back to "pure prompt + JSON" philosophy)
- 11 prompt fixes from pilot 001 — **kept** (G1-G4, G7-G8, G10-G11)
- Pilot artifacts under `outputs/pilot-001-refund-iter4/` — kept (reference)

### 🐛 Lessons learned

**Over-engineer creep detected + reverted same day** (similar to v3.2.0 Evan revert):
- workflow_state.py = 250 lines Python to enforce what 30 lines schema doc + discipline rule can cover
- User question "เรามีกี่ script เนี้ย ใช้แค่ json doc handoff เท่านั้นไม่ได้หรอ" = correct intuition
- shode-house = prompt-based discipline; mechanical layer should be **rare + justified**
- This pattern recurring: v3.2 (Evan), v3.3 hooks, v3.4 (workflow script) — all reverted same-day after audit

**Architectural principle (post-v3.4.1)**:
> Default to "agent + structured doc". Mechanical layer only when discipline provably failed via real engagement signal.

---

## [3.4.0] — Pilot fixes + Dynamic Workflow Script — 2026-05-31 (SUPERSEDED by v3.4.1 same day)

> **Note**: v3.4.0 tagged + built but workflow_state.py reverted same day. v3.4.1 = simplification. Tag v3.4.0 kept for git history; do NOT install v3.4.0 (use v3.4.1).

> **Focus**: 11 prompt fixes from real pilot (refund flow full-stack, 4 iterations) + Dynamic Workflow Script (Medium) externalizing state from agent context. Mitigate context rot, enable replay/resume, enforce gate criteria deterministically.

### 🆕 Added

**Dynamic Workflow Script** (Medium — `scripts/workflow_state.py`):
- Python stdlib (cross-platform); 240 lines; no external deps
- Externalize PEV state from agent context → `outputs/<bd-id>/state.json` (structured)
- Commands: `init / status / phases / validate / advance / record / findings / iter-inc`
- Gate validator: blocks `advance` if previous phase status ≠ passed/conditional_pass + artifacts + owners not recorded
- iter > 3 escalation built into `iter-inc` (exit code 2)
- Replaces SESSION-STATE.md (markdown) — legacy fallback kept

**11 prompt fixes from pilot 001** (refund flow full-stack):
- **G1** Oliver M1 Ingress Guard explicit recite mandatory (orchestrator.md)
- **G2** Patrick Never-Does: no Domain SME role-play (product-manager.md)
- **G3** Bella Phase 1a pickup protocol mandatory (business-analyst.md)
- **G4** Sara Project Evidence mandatory + Greenfield handling (solution-architect.md)
- **G7** Felix Domain Evidence cite format + PENDING disclaimer template (fintech-expert.md)
- **G8** Phase 0 CONDITIONAL PASS scope-clarification flow (shode-house-workflow.md)
- **G10** Oliver USER CLARIFY relay packaging (shode-house-workflow.md)
- **G11** Max 2-round clarification cap + escalate (shode-house-workflow.md)
- *(G5, G6, G9 = environment/positive — not prompt fixes)*

**Pilot 001 refund — full report**:
- `docs/pilot-reports/pilot-001-refund-iter4-final.md` — executive summary + 11 findings + v3.4 backlog
- 17 artifact files under `outputs/pilot-001-refund-iter4/` covering Phase 0 → 4 (kept for reference)

### 🔄 Changed

- `.claude-plugin/{plugin,marketplace}.json` — v3.3.0 → **v3.4.0** (description 137 chars ASCII)
- `skills/discipline/shode-house-workflow/SKILL.md` — Session State section rewritten for v3.4 Dynamic Workflow Script approach
- `scripts/lint.sh` — no change (8 checks; workflow_state.py self-tested in smoke)

### 🐛 Lessons learned (from pilot)

**Context rot is real in long sessions**: Oliver maintains markdown state via discipline rule (M6), but multi-hour engagements show drift. Structured JSON externalized to script = mechanical enforcement.

**Simulation limit caught (G9 meta)**: Single Claude role-playing 19 agents in pilot ≠ real multi-agent Task-dispatch. Pilot validated **structural** discipline; real engagement validates **independence**. v3.4 backlog: real engagement pilot.

**Adversary stance works as designed**: Chris/Quinn produced FAIL verdict on Dave's incomplete code (smoke PENDING + IDOR placeholder + webhook missing). Anti-Puppet rule held — no fake PASS. PEV loop correctly routed Phase 2 fix.

**Domain Evidence cite enforcement gap**: Felix's "BOT notice 15-day" without notice number proved Domain Evidence Protocol format existed but enforcement weak. G7 fix tightens per-agent.

### 📊 Stats v3.4.0

- Agents: 19 (no change)
- Skills shipped: 18 (no change)
- Commands: 5 (no change)
- Python scripts: 1 → **2** (+ workflow_state.py)
- Prompt fixes from pilot: **11**
- Pilot reports: 0 → **1** (`docs/pilot-reports/`)

### v3.4 backlog (post-pilot)

| Priority | Item |
|---|---|
| 🔴 1 | Real engagement (validate G9 multi-agent independence via Task-tool dispatch) |
| 🟠 2 | Extend G7 Domain Evidence enforcement to Iris/Sam/Tara/Elena/Brooke/Emma (Felix exemplar replicated) |
| 🟠 3 | Extend G3 pickup protocol to other phase transitions (1b→2, 3a→3b, 4→5) |
| 🟡 4 | Extend G4 Project Evidence to Aaron infra + Sara migrations |
| 🟡 5 | Failure-mode docs 002-009 from pilot patterns |
| 🟡 6 | Heavy workflow engine extension (advance commands → full state machine) |

### Migration v3.3 → v3.4

- ✅ Backward-compatible: existing SESSION-STATE.md keeps working (Oliver discipline rule unchanged)
- 🆕 New bd → use `python3 scripts/workflow_state.py init <bd-id>` (recommended)
- 🆕 Oliver prompt updated to query state.json via script first; falls back to SESSION-STATE.md if no state.json
- No breaking changes for v3.3 users

---

## [3.3.0] — Simplification: drop sprint + Evan, embed bias discipline — 2026-05-30

> **Focus**: Honest audit ของ v3.2.0 ก่อน ship → user feedback ว่า Evan + sprint = over-engineer. v3.3.0 = simplification: drop /sprint command + drop Evan agent + embed bias rules ใน 19 agent prompts. **PEV loop per bd** replaces sprint outer loop. Chris/Quinn ทำงาน adversarial vs Dave + Claude in Chrome verify mandatory. ห้าม agent ประเมิน man-day โดย user ไม่ร้องขอ.

### 🗑️ Removed

- **`agents/evaluator.md` (Evan)** — over-engineer for current scale. Bias detection rules embedded ใน 19 agent prompts แทน (single-source via `shode-house-discipline` + per-agent specifics)
- **`commands/sprint.md`** — sprint outer loop dropped. PEV loop per bd. Continuous OKR review (Patrick) without bracket.
- **Phase 7 (Sprint Learn)** from workflow — per-bd reflect captured in Phase 4 Triage (Oliver `bd remember <lesson>` post bd close)
- **Eval Harness shipped skill** → moved to `skills/in-progress/eval-harness/` (kept as offline tool for maintainer regression test before major bumps; not shipped in plugin.json)

### 🆕 Added

**Universal rules in `shode-house-discipline/SKILL.md`**:
- **§ No Man-Day Negotiation** (3 ห้าม + 4 exception + user-estimate purpose rule). Agent ทำงานไม่ตรงตาม man-day → ห้าม propose timeline / refuse งานเพราะ "ใหญ่เกิน X sprint" / ใช้ man-day ต่อรองเวลา. Exception: user explicit ขอ estimate → for user external report only, ไม่ใช่ agent scope contract.

**Adversary stance + Claude in Chrome (Chris/Quinn vs Dave)**:
- **Chris + Quinn**: `🔴 Adversary Stance` section — pessimistic default, zero trust on Dave's claims, verdict default = FAIL until proven PASS, ห้าม dismiss marginal issue
- **Mandatory Visual Verify via Claude in Chrome MCP** — frontend / API observable / user journey touched = บังคับ open + screenshot + console + network. Headless Playwright ≠ enough.
- **Dave**: `🔴 Adversary-Aware Hand-off` — proactive evidence paste; ห้าม "should be fine" push-back

**Bias discipline embedded in 19 agents** (`## 🎯 Bias Discipline` section per agent) — covers sycophancy, anchoring, pattern-bias, verdict-skew, convergence, alert-dismissal, std-vs-custom per role.

**PEV Loop concept** (replaces sprint outer loop):
- Plan (Phase 0-1c) → Execute (Phase 2) → Verify (Phase 3a/3b) → Triage (Phase 4)
- Deploy (Phase 5) = continuous per bd ready หรือ user manual batch (optional)
- No Phase 7 / sprint retro — per-bd reflect in Phase 4

### 🔄 Changed

- `.claude-plugin/{plugin,marketplace}.json` — v3.2.0 → **v3.3.0**; description 142 chars ASCII; keywords swap (eval-harness/no-bias-eval → pev-loop/bias-discipline/no-sprint)
- `CLAUDE.md` — drop "Eval Harness" section, add "Bias Discipline" + "PEV Loop" sections
- `README.md` — v3.3 banner + workflow diagram refactor (PEV loop) + /sprint marked REMOVED v3.3
- `scripts/lint.sh` — 9 checks → 8 (drop eval-harness fixture dry-run since skill moved to in-progress)
- `skills/discipline/shode-house-workflow/SKILL.md` — Phase Contract diagram = PEV loop; Lifecycle Hooks drop Pre-Sprint + Sprint Close
- `skills/discipline/shode-house-routing/SKILL.md` — drop Eval team + Evan; T-shirt = **internal routing only** (ห้ามส่ง user); add "Adversarial relation: Chris/Quinn vs Dave" table
- `skills/discipline/shode-house-drift/SKILL.md` — Phase 7 marked REMOVED
- `skills/discipline/shode-house-evidence/SKILL.md` — Storage row "bd + sprint close" → "bd close per-bd reflect"
- `skills/discipline/review-checklist/SKILL.md` — add `🔴 Adversary Stance` + `🌐 Mandatory Visual Verify`
- 19 agents — cleanup sprint refs + man-day negotiation removed

### 🐛 Lessons learned

**v3.2.0 over-engineering caught early**: Evan + 19 fixtures + run_eval.py = heavy weight for "regression bias test" when prompt rules can solve 80% directly. User audit: "ทำไม Chris/Quinn ตรวจตัวเองไม่ได้?" → self-preference bias. Better fix = embed bias rules IN Chris/Quinn prompt.

**Sprint = human concept**: Agents don't need sprint time-box. Task-completion natural unit. User insight: "agent ทำงานไม่ตรงตาม manday".

**Adversarial discipline > telemetry detection**: simpler to put verdict-default-FAIL + zero-trust-Dave in prompts than runtime gate.

### 📊 Stats v3.3.0

- Agents: 20 → **19** (drop Evan)
- Skills shipped (plugin.json): 19 → **18** (eval-harness → in-progress)
- Commands: 6 → **5** (drop /sprint, +2 deprecated kept)
- Bias discipline sections in agents: 0 → **19** (1 per agent)
- lint.sh checks: 9 → **8**
- **Host-OS dependency: ZERO**

### Migration v3.2.0 → v3.3.0

- ❌ `/shode-house:sprint` removed → use PEV per-bd flow
- ❌ Evan agent removed → bias enforcement now in Chris/Quinn/Felix/etc. prompts
- ❌ `outputs/EVAL-*.json` no longer produced
- ✅ Eval methodology preserved in `skills/in-progress/eval-harness/` (offline maintainer use)
- ✅ `/sprint close retro` users: per-bd reflect via Oliver `bd remember`

---

## [3.2.0] — Eval Harness + Bias-Aware Regression — 2026-05-30 (SUPERSEDED by v3.3.0 same day)

> **Note**: v3.2.0 was tagged + locally built but reverted same-day after user feedback that Evan + sprint = over-engineer. v3.3.0 = simplification. Tag v3.2.0 kept for git history; do NOT install v3.2.0.

> **Focus**: Bias-aware offline evaluation for all 19 agents. ตอบโจทย์ "งานหลุดคุณภาพ" จากมุม regression test แทน runtime gate — สงสัย agent drift จาก prompt refactor → run eval หา bias profile + compare baseline.
> **Scope: V2 (Spec + runner stub)** — agent + skill + 19 fixtures + Python runner. Real Claude SDK invoke pending.

### 🆕 Added

**1 new agent + 1 new skill**:
- **`agents/evaluator.md`** — Evan (Evaluator). Offline tool, NOT in /implement loop. Orchestrate bias-aware fixture runs + cross-LLM judge + bias profile output. Tools: Read/Write/Edit/Glob/Grep/Bash.
- **`skills/discipline/eval-harness/SKILL.md`** (224 lines) — methodology: 4 bias types (sycophancy/anchoring/pattern-bias/verbosity/position), per-agent bias priority table (19 agents), fixture schema, run pipeline, output JSON spec, calibration step.

**19 starter fixtures** (`tests/eval-fixtures/<agent>/01-*.json`):
- One per agent covering most-relevant bias type:
  - Decision (Chris, Quinn): verdict-skew + sycophancy
  - Domain (Felix, Iris, Sam, Tara, Elena, Brooke, Emma): pattern-bias + anchoring
  - Design (Bella, Sara, Uma): anchoring + pattern-bias
  - Workflow (Oliver, Patrick, Stan, Reggie): sycophancy + convergence/anchoring
  - Dev/Ops (Dave, Aaron): sycophancy + pattern-bias
  - Sentinel: sycophancy on "low risk"

**Runner script** (cross-platform Python stdlib):
- `scripts/run_eval.py` — `--dry-run` validates 19 fixtures schema across all agents; `--agent <name>` per-agent; `--invoke` STUB until Claude SDK harness pending

**No-bias methodology baked in**:
- Multi-run N≥5 per fixture (no single-shot)
- Cross-LLM judge (subject ≠ judge — mitigate self-preference)
- Blind judging (judge sees output + expected_keywords, NOT expected_verdict)
- Order shuffle (mitigate position bias)
- Judge calibration step on golden labels before real run

### 🔄 Changed

- `.claude-plugin/plugin.json` — v3.1.1 → v3.2.0 (description 141 chars ASCII)
- `.claude-plugin/marketplace.json` — v3.1.1 → v3.2.0
- `CLAUDE.md` — Eval Harness section + bucket list updated (eval-harness in discipline/)
- `README.md` — 18 → 19 skills + eval-harness row

### 🐛 Lessons learned

**Wave-based scope creep prior to v3.2.0 revert**: ออกแบบ v3.2.0 ใหญ่ (Quality Gate + Telemetry + Hooks + 5 fixtures + Devil's Advocate + sprint metrics ...) — user revert + replan focused เฉพาะ harness + no-bias. Lesson: **minimum viable feature** > comprehensive feature set; ship narrow + iterate

**Cross-platform from start**: Python stdlib only (no .sh user-facing); runs in Claude Code Bash sandbox regardless of host OS (Mac/Win/Linux)

### 📊 Stats v3.2.0

- Agents: 19 → **20** (+ Evan)
- Skills shipped (plugin.json): 18 → **19** (+ eval-harness)
- Commands: 6 (no change)
- Python scripts (cross-platform): 0 → **1** (run_eval.py)
- Maintainer .sh scripts: 6 (no change)
- Eval fixtures: 0 → **19** (1 per agent starter)
- Bias types covered: **9** (sycophancy, anchoring, pattern-bias, verbosity, position, verdict-skew, convergence, alert-dismissal, std-vs-custom)
- **Host-OS dependency: ZERO** (sandbox-only Python execution)

### ⚠️ Known limitations / scope NOT in v3.2.0

- `run_eval.py --invoke` = STUB. Real Claude SDK invocation pending.
- All 19 fixtures `expert_validated_by: PENDING` — need domain SME sign before baseline promote (CPA/actuary/SAP/OWASP/...)
- Only 1 fixture per agent. Promote requires ≥ 3 fixtures + 2 baseline runs separated by ≥ 1 week
- lint.sh integration: dry-run check optional (added in [11/11] check)
- No web-q / accessibility / security CI deeper integration (deferred to future)
- No telemetry hooks / sprint metrics / Anti-Puppet enforcement (deferred — was earlier v3.2.0 scope, reverted)

### Roadmap (next versions)

- v3.3: judge calibration tooling + Claude SDK wire-up
- v3.4: expand fixtures (3+ per agent) + expert validation drive
- v4.0: Real eval-driven prompt regression (breaking — fixtures become CI gate)

---

## [3.1.1] — Dev Discipline + Lint Gate — 2026-05-27

> **Focus**: ทำให้ "ตอน dev" มีคุณภาพจริงตาม software craft. v3.1.0 มี skill craft refactor แต่ขาดความลึก dev-gate + ขาด lint discipline ที่ระดับ repo. v3.1.1 fix ทั้งสองจุด.

### 🆕 Added

**dev-gate skill — 7 → 11 gates** (`skills/workflow/dev-gate/SKILL.md`):
- **Gate 0: Architecture self-check** (Dave judgment ก่อน hand-off) — SOLID 5 checkbox + cohesion + low coupling + human-readable. ห้าม "Chris จะ review ให้" — Dave ตอบ self-check ก่อน push
- **Gate 2: Organize Imports** (แตกจาก Format) — stdlib/3rd-party/local + alpha sort, ห้าม wildcard
- **Gate 3: Remove Unused** (แตกจาก Format) — unused import/var/function/parameter ต้องลบ
- **Gate 9: Security Lint** (เพิ่มใหม่) — SAST per language + secret scan (gitleaks) + dep audit
- **Per-language tool matrix** — 8 stacks (Py/TS/JS/Go/Java/Kt/Rust/Vue/PHP) บอก tool ที่ใช้ per gate
- **Pre-commit hook examples** — `.pre-commit-config.yaml` ตัวอย่าง Python + TS/JS

**Repo-level lint discipline**:
- `scripts/lint.sh` — comprehensive pre-publish gate (8 checks): JSON syntax, SKILL.md YAML + name+description, command YAML + string argument-hint, agent YAML, SKILL name == folder, cross-refs resolve, path refs in README+CLAUDE, Cowork constraints + invariants
- `.pre-commit-config.yaml` (template สำหรับ shode-house repo เอง) — gitleaks + yamllint + check-yaml + lint.sh
- `scripts/setup-precommit.sh` — bootstrap pre-commit สำหรับ shode-house contributor

### 🔄 Changed

**`scripts/publish-v3.1.0.sh` → `scripts/publish.sh`** (version-agnostic):
- Reads version จาก plugin.json (ไม่ hard-code)
- Step 2 ใช้ `lint.sh` (8 checks) แทน check-index.sh เดี่ยว
- Idempotent: safe to re-run

**Bug fixes ที่ค้นพบจาก lint pass** (v3.1.0 มี bug ที่เกือบ ship):
- `commands/design-system.md` `argument-hint: [a | b] [c] [d]` — YAML parse error (3 flow sequences ติดกัน) → quote เป็น string
- `commands/init.md`, `setup-project.md` — nested quote ใน argument-hint → single-quote wrap
- `commands/{consult,implement,sprint,review,spec-only}.md` — `argument-hint: [bd-id]` parse เป็น list ไม่ใช่ string → ทุกตัว quote
- `README.md` line 384 — stale ref `skills/meeting/SKILL.md` (post bucket migration) → `skills/workflow/meeting/SKILL.md` + `skills/discipline/shode-house-routing/SKILL.md`

### 🐛 Lessons learned

**v3.1.0 publish workflow ขาด lint gate** — เกือบ ship ของ buggy เพราะข้าม VERIFY BEFORE DONE step:
- ไม่มี YAML frontmatter parse check (8 commands พลาด)
- ไม่มี cross-reference check (README path stale)
- check-index.sh check แต่ structural ไม่ได้ check syntax
- **v3.1.1 fix**: `scripts/lint.sh` รวม 8 checks; publish script require pass ก่อน push

**dev-gate ใน v3.1.0 ไม่ครอบ "import/unused/security"** — ทำให้ Dave/Chris อาจ ship ของไม่ครบ:
- Old: 7 gates เน้น format + lint + test
- New: 11 gates เพิ่ม organize-imports + remove-unused + security lint + architecture self-check
- เพิ่ม per-language tool matrix ให้ Dave/Chris pick tool ถูกตั้งแต่ start project

### 📊 Stats v3.1.1

- Skills: 18 (no change)
- Commands: 6 active + 2 deprecated alias (no change)
- dev-gate gates: 7 → **11**
- lint.sh checks: 0 → **8** (gate ก่อน publish)
- Cowork validator constraints in CLAUDE.md: **enforced via check-index.sh + lint.sh**
- Pre-commit hook: ✅ template + setup script

---

## [3.1.0] — Skill Craft Refactor (9arm-inspired) — 2026-05-26

> **Focus**: skill quality + lazy-load + token saving. Keep v3.0 org structure (19 agents in 7 teams) ครบ. Inspired by [`thananon/9arm-skills`](https://github.com/thananon/9arm-skills) skill-craft patterns.

### 🆕 Added

**Repo invariants + dev-loop tooling**:
- `CLAUDE.md` (≤ 30 lines) — repo invariants: bucket convention, 4-section description format, ≤ 300-line SKILL.md limit, command 3-flag rule
- `scripts/list-skills.sh` — list every SKILL.md + lines + bucket + description
- `scripts/check-index.sh` — enforce invariants (CI gate; exits non-zero on violation)
- `scripts/build-plugin.sh` — build `shode-house-v<VERSION>.plugin` zip

**New skill files (8 total — split from meeting + DRY checklist)**:
- `skills/discipline/shode-house-discipline/SKILL.md` — Recite Discipline Card + 5 Philosophy + Safety + Universal Rules + Clarifying (mandatory load for all agents)
- `skills/discipline/shode-house-evidence/SKILL.md` — Project + UX + Domain Evidence Protocol + REVIEW Report Format
- `skills/discipline/shode-house-routing/SKILL.md` — Routing + RACI + T-shirt + Trust Levels + Team v3.0 + Conflict Resolution
- `skills/discipline/shode-house-deliverable/SKILL.md` — DoD + Anti-Puppet + I Never Do + AI Persona Disclaimer + Postmortem template
- `skills/discipline/shode-house-broadcast/SKILL.md` — Agent Tag Prefix + Structured Tag + Caveman Broadcast + Handoff Protocol v3.0
- `skills/discipline/shode-house-workflow/SKILL.md` — Phase Contract + Smart Coop + lifecycle hooks + approval gates + worktree isolation
- `skills/discipline/shode-house-drift/SKILL.md` — Workflow Drift Defense M1-M7 + New Phases v3.0 (0/1c/6/7)
- `skills/discipline/review-checklist/SKILL.md` — Chris 7-dim + Quinn integration matrix + Sentinel security + Domain validation — DRY source-of-truth for `/implement` Phase 3b + `/review`

**Bucket-folder lifecycle** (CLAUDE.md invariant):
- `skills/workflow/` (4 skills) — daily process
- `skills/ops/` (3 skills) — operational discipline
- `skills/ui/` (2 skills) — frontend quality
- `skills/style/` (1 skill) — communication
- `skills/discipline/` (8 skills) — v3.1 split modules + DRY checklist
- `skills/in-progress/` — not shipped placeholder
- `skills/deprecated/` — not shipped placeholder

**Plugin.json — explicit skills + commands list**:
- เพิ่ม `skills` array (18 entries with bucket + role + path)
- เพิ่ม `commands` array (8 entries with role)
- เพิ่ม keywords: `9arm-inspired`, `skill-craft`, `lazy-load`, `bucket-lifecycle`

### 🔄 Changed

**Skill description format — 4-section across ทุก 10 functional skills**:
- เดิม: run-on sentence "ใช้เมื่อ user สั่ง X, Y, Z ..."
- ใหม่: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]` (9arm-inspired hyper-specific trigger phrases)
- กระทบ: `meeting`, `dev-gate`, `automate-test`, `diagnose`, `incident`, `slo`, `secure`, `ui-test`, `web-q`, `caveman`

**Skill gates — When-NOT + Required-inputs** ใน 5 heavy skills:
- `dev-gate`, `automate-test`, `incident`, `slo`, `secure` — เพิ่ม `## When NOT to use` + `## Required inputs — refuse without` (9arm `post-mortem` pattern)

**Skill composition pointers** ใน 5 skills:
- `diagnose` → `incident`/`dev-gate`/`automate-test`/`ui-test`/`secure`
- `incident` → `slo`/`diagnose`/`dev-gate`/`secure`/`automate-test`
- `secure` → `dev-gate`/`incident`/`web-q`/`automate-test`/`diagnose`
- `dev-gate` → `automate-test`/`ui-test`/`web-q`/`secure`/`review-checklist`
- `slo` → `incident`/`automate-test`/`diagnose`
- Pattern: textual handoff ระหว่าง skills (ลด orchestrator round-trip — 9arm `post-mortem → management-talk` pattern)

**Meeting god-skill split** (P1-1 from audit):
- เดิม: `skills/meeting/SKILL.md` = **1316 บรรทัด, 45 KB** (god-skill — ทุก agent โหลด)
- ใหม่: `skills/workflow/meeting/SKILL.md` = **180 บรรทัด** (thin entry-point + Recite Discipline Card + index ไป 7 split skills)
- ผลที่ได้: **86% token reduction** สำหรับ entry context per agent

**Command consolidation** (audit Section 5 — user-requested):
- `/init` รวม `/setup-project` — เพิ่ม `--quick "<stack>"` flag (direct Aaron Docker-first mode)
- `/design-system` รวม `/spec-only` — เพิ่ม `--stop` (no implement suggest) + `--estimate` (add T-shirt sizing) flags
- ลด 8 → 6 active commands + 2 deprecated alias (1-2 release window)
- 3-flag rule (CLAUDE.md invariant): prefer flags over command proliferation

**`/implement` Phase 3b + `/review` rewired to use `review-checklist` skill** (DRY):
- เดิม: ทั้ง 2 command มี checklist ของตัวเอง (Chris 7-dim + Quinn matrix duplicated)
- ใหม่: invoke `review-checklist` skill เป็น source-of-truth — update ครั้งเดียวกระทบทั้ง 2

**Folder migration** (no functional change):
- `skills/meeting/` → `skills/workflow/meeting/`
- `skills/dev-gate/` → `skills/workflow/dev-gate/`
- `skills/automate-test/` → `skills/workflow/automate-test/`
- `skills/diagnose/` → `skills/workflow/diagnose/`
- `skills/incident/` → `skills/ops/incident/`
- `skills/slo/` → `skills/ops/slo/`
- `skills/secure/` → `skills/ops/secure/`
- `skills/ui-test/` → `skills/ui/ui-test/`
- `skills/web-q/` → `skills/ui/web-q/`
- `skills/caveman/` → `skills/style/caveman/`

### ⚠️ Deprecated (alias 1-2 release window — ลบใน v3.2)

- `commands/setup-project.md` → use `/init --quick "<stack>"` แทน
- `commands/spec-only.md` → use `/design-system --stop --estimate` แทน

Migration: ทั้ง 2 command ยังทำงานได้ใน v3.1.x — auto-redirect ผ่าน Oliver

### 🏛️ Architecture impact

- v3.0 agents ที่อ้าง *"ยึด meeting skill เป็น discipline foundation"* ยัง work — meeting skill ตอนนี้เป็น thin entry-point + Recite Card + index pointer
- เพื่อ token optimal: future agents ควร reference เป็น *"ยึด `shode-house-discipline` (mandatory) + `shode-house-evidence` (when claiming)"* — iterative adoption, ไม่บังคับใน v3.1
- เนื้อหา 1316 บรรทัดเดิมยังครบ — กระจายไปยัง 7 sub-skills + index ใน thin meeting

### 📊 Stats v3.1

- **Skills**: 18 (จาก 10) — 10 functional + 7 discipline modules + 1 review-checklist
- **Commands**: 6 active + 2 deprecated alias (จาก 8 active)
- **Skill descriptions**: 100% migrated to 4-section format
- **When-NOT gates**: 5/5 heavy skills covered
- **Skill composition pointers**: 5 skills cross-linked
- **Largest SKILL.md**: 272 lines (`shode-house-deliverable`) — ทุก skill ≤ 300 (CLAUDE.md invariant); meeting/ exception (180 thin)
- **9arm patterns adopted**: 7/7 (description 4-section, When-NOT, Required-inputs, Recite mantra, skill composition, bucket lifecycle, CLAUDE.md invariants)

### Inspired by

- [`thananon/9arm-skills`](https://github.com/thananon/9arm-skills) — skill-craft patterns (4-section description, When-NOT + Required-inputs gate, Recite mantra, skill composition, bucket-folder lifecycle, CLAUDE.md invariants)
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — caveman/diagnose concepts (already credited in v2.x)
- [`addyosmani/web-quality-skills`](https://github.com/addyosmani/web-quality-skills) — web-q port (already credited in v2.x)

### Why minor bump (3.0.1 → 3.1.0)

- **New features**: 8 new skills, command flag system, bucket folders, scripts/, CLAUDE.md
- **No breaking change**: agent reference to meeting still works (thin entry-point); deprecated commands still work as alias
- Per Semver: minor bump (backward-compatible additions)

---

## [3.0.1] — Self-audit Patch (Patch — consistency + de-duplication + arrow convention)

Self-audit ของ v3.0.0 ก่อน public — เจอ 3 inconsistency + apply fix

### Fixed

- **Skill name table** (meeting v3 section) — เคยอ้าง `ci-test` / `debug` (short names proposal) แต่ folder จริง = `automate-test` / `diagnose` → revert table ใช้ชื่อ folder จริง; defer short-name rename ไป v3.1+ (avoid breaking change for consumers)
- **STRIDE table duplication** (Sara) — ลบ STRIDE table จาก `agents/solution-architect.md` (เคย duplicate กับ Sentinel agent + secure skill); เหลือ Sara residual responsibility 4 ข้อ (trust boundary in C4, ADR mitigation support, NFR security row, joint-review threat model) + handoff pointer → Sentinel `secure` skill
- **Arrow convention** — Document explicit rule ใน meeting skill: `▸` = handoff broadcast (M3 protocol — formal); `→` = general flow/sequence/implication (informal). Accept divergence per Stan tech-radar pattern

### Bonus fixes

- **README version badge** — 2.8.2 → 3.0.1 (was outdated)
- **README header** — เพิ่ม v3.0 summary (19 agents / 7 teams / Patrick/Stan/Sentinel/Reggie / Phase 0/1c/6/7 / Drift Defense)
- **SHODE-HOUSE-MASTER.md** — `/Users/shode/development/shode-house/` → `~/development/shode-house/` (sanitize personal path before public)

### Token cost

- Net delta: **+~80 tokens (~0.05%)** — fix-only patch, no new feature

### Why patch bump (3.0.0 → 3.0.1)

Self-audit findings = consistency fix, ไม่มี behavior change (per Semver patch). No new agent / no new skill / no new phase / no breaking change

### Pre-public security

Self-scan สำหรับ sensitive data ก่อน repo public:
- ✅ 0 API keys / tokens / passwords / private keys
- ✅ 0 GitHub PAT / AWS / GCP / Azure credentials
- ✅ 0 production DB connection strings
- ✅ 0 JWT samples / session tokens
- ✅ 0 real customer / NDA names
- ✅ `.env*`, `outputs/` already in `.gitignore`
- ⚠️ Personal `/Users/shode` paths in SHODE-HOUSE-MASTER.md → sanitized to `~/development/shode-house/`

Recommended local-only scan ก่อน push: `gitleaks detect` + `trufflehog git file://$(pwd)` (sandbox can't deep-scan git history)

---

## [3.0.0] — Comprehensive Org Structure (Major)

**Single biggest release since v1.0** — real software-house org chart, zero-overlap capability, parallel-team execution, follow-up drift defense.

### 🆕 Added — 4 new core agents

- **Patrick (PM)** — `agents/product-manager.md` — sole owner Why/What: OKR, RICE/WSJF, opportunity sizing (TAM/SAM/SOM), kill decisions, stakeholder mgmt
- **Stan (Staff Engineer)** — `agents/staff-engineer.md` — sole owner cross-team technical depth: tech radar, polyglot consistency, convergence decisions, mentoring
- **Sentinel (Security Engineer)** — `agents/security-engineer.md` — sole owner security: STRIDE/LINDDUN threat modeling, SAST/DAST orchestration, CSP/Trusted Types/SRI, pen testing
- **Reggie (Site Reliability Engineer)** — `agents/sre-engineer.md` — sole owner operate: SLO/SLI/error budget, runbook, on-call, blameless postmortem

### 🆕 Added — 4 new phases

- **Phase 0 — Discovery** (Patrick + Domain SME) — OKR + opportunity sizing + pain validation BEFORE BRD
- **Phase 1c — Threat Model** (Sentinel + Sara) — STRIDE + abuse case + security AC, mandatory if feature touches auth/PII/money/external
- **Phase 6 — Operate** (Reggie + Aaron + Oliver) — continuous post-deploy: SLO burn rate, incident, postmortem
- **Phase 7 — Learn** (Patrick + Oliver) — sprint retro: OKR review, kill decision, tech debt RICE

### 🆕 Added — 4 new skills + 1 merged

- `dev-gate` — merged from `tdd` + `code-quality`
- `web-q` — Core Web Vitals + SEO + security headers (ported + adapted from `addyosmani/web-quality-skills` MIT)
- `secure` — STRIDE + threat-driven design + CSP/Trusted Types
- `slo` — SLI/SLO/error budget (Google SRE Book-aligned)
- `incident` — Runbook + on-call + blameless postmortem

### 🆕 Added — Workflow Drift Defense (7 Mechanisms — meeting skill)

แก้ปัญหา agent หลุด workflow ใน warm follow-up:
- M1 Ingress Guard | M2 Follow-up Classifier | M3 Anti-Puppet "Done"
- M4 User Comment = FAIL | M5 Spec Change = bd revision
- M6 SESSION-STATE.md persistent | M7 Direct-to-Agent block

### 🆕 Added — 7-Team Structure + Handoff Broadcast Protocol

7 teams (parallel within, sequential across via gate): Lead / Discover / Design / Domain / Dev / Verify / Ops + Content (opt). Single-owner capability matrix (zero overlap).

Handoff: 1-line caveman `Bella ▸ Dave : impl bd-42` consistent ทุก phase transition.

### 🆕 Added — RACI matrix per phase + Multi-sig pre-deploy-prod gate

ทุก phase มี explicit R/A/C/I. R0 deploy requires 4 sigs: Aaron (build) + Reggie (SLO) + Sentinel (security) + Patrick (OKR).

### Changed — scope split + handoff to new agents

- **Oliver** — keep Engagement Lead only; cross-team tech depth → Stan
- **Bella** — keep BA only; PM work → Patrick
- **Sara** — keep SA only; deep threat modeling → Sentinel
- **Aaron** — keep Platform/DevOps only; SLO/incident → Reggie
- **Chris** — surface security only; deep security → Sentinel
- **Quinn** — keep integration/E2E/contract/load; pen test → Sentinel
- **7 Domain SMEs** — elevated to Phase 0 active driver

### Removed — skill cleanup

- `skills/sd/` + `skills/do/` — identical (v1.1 stale); superseded by `meeting`
- `skills/tdd/` + `skills/code-quality/` — merged → `dev-gate`
- `skills/grill-me/` — merged → `meeting` Clarifying (6 patterns)
- `skills/triage/`, `to-prd/`, `to-issues/`, `zoom-out/` — empty stubs

### Token cost

- Removed: −1,500
- Added: +7,500
- Net: **+6,000 (~+4%)** — adds 4 roles + 4 phases + Drift Defense + Teams + Handoff + RACI

### ⚠️ Breaking changes

- Skills `sd`, `do`, `tdd`, `code-quality`, `grill-me`, `triage`, `to-prd`, `to-issues`, `zoom-out` removed — apply-v3.0.sh handles `rm -rf`
- Phase 5 deploy single-sig → multi-sig (Aaron + Reggie + Sentinel + Patrick R0)
- Drift Defense (M1-M7) opt-in via `mode: minimal` ใน engagement for legacy flow

### Reference

- Web-Q ported from [`addyosmani/web-quality-skills`](https://github.com/addyosmani/web-quality-skills) (MIT)
- SLO aligned with Google SRE Book
- RACI follows PMI standard
- Tech Radar pattern from Thoughtworks

---

## [2.8.2] — Review Audit Trail (Patch — bd-native primary, no markdown duplicate)

ตอบคำถาม "review เสร็จต้องเขียน md file ไหม": **bd active = bd notes ONLY (ห้ามเขียน md ซ้ำ); no bd = outputs/REVIEW-<feature>.md fallback**. ทั้งคู่ใช้ template structure เดียวกัน

### Added

- **📝 REVIEW Report Format section** (meeting skill) — mandatory template structure: Summary / Findings by severity 🔴🟠🟡🔵 / Coverage (Chris/Quinn) / UX Verdict (Uma) / Loop Routing Recommendation. Apply ทุก Phase 3a + 3b + 4 + `/review`
- **Storage rule conditional**:
  - bd active (`.beads/` exists OR `bd ready` returns) → `bd update <id> --notes` ONLY
  - No bd → `outputs/REVIEW-<feature>.md` (fallback)
  - bd + sprint close → optional `outputs/RETRO-sprint-<N>.md` (aggregate)
- **Universal Rule** — "ห้าม close Phase 3 ก่อน post review report"; "ห้ามเขียน markdown ถ้ามี bd" (bd = single source of truth)
- **DoD checkbox** — "Review report posted (bd notes OR outputs/REVIEW-*.md, conditional)"
- **Pre-loop-exit gate** — เพิ่มเงื่อนไข: review report posted ตาม REVIEW Report Format
- **Compact bd notes pattern** (≤ 500 chars) — summary + count + evidence paths; full evidence (axe.json, Playwright trace, mutation report) ที่ path เท่านั้น

### Changed

- **Chris/Quinn/Uma agent files** — Output section refactor:
  - ก่อน v2.8.2: "Output: section ใน outputs/REVIEW-<bd-id>.md" (always markdown)
  - หลัง v2.8.2: "bd active → bd update --notes ONLY; no bd → outputs/REVIEW-<feature>.md fallback"
- **`/review` command Step 4** — Consolidated Report: bash conditional storage (bd active vs no bd); ห้ามเขียนคู่
- **Anti-redundancy** — ลด token waste จาก double-write (bd notes + markdown ของเรื่องเดียวกัน)

### Token cost

- skills/meeting/SKILL.md: +~400 tokens (REVIEW Report Format section + 2 Universal Rules + DoD line)
- agents/code-reviewer.md: ~0 tokens (replace section content)
- agents/qa-engineer.md: ~0 tokens (replace section content)
- agents/ux-ui-designer.md: +~50 tokens (Verdict format conditional)
- agents/orchestrator.md: +~30 tokens (pre-loop-exit gate condition)
- commands/review.md: +~100 tokens (bash conditional storage)
- **Total: ~+580 tokens (~+0.4%)** — discipline + anti-redundancy

### Why patch bump (2.8.1 → 2.8.2)

Discipline tightening (storage rule + template) — no new phase, no new command. Patch per Semver

### Root cause (user question)

User: "มีการระบุว่า review เสร็จต้องเขียน md file หรือไม่"

Audit เจอ **soft hint ใน 8 จุด**: `outputs/REVIEW-<bd-id>.md` mentioned ที่ Chris/Quinn/orchestrator/developer/implement/meeting × 2/CHANGELOG — แต่:
- ไม่มี template/structure mandatory
- ไม่มี enforcement gate / DoD
- ไม่มี anti-puppet rule for missing report
- **Most important**: ซ้ำซ้อนกับ bd notes (waste token + drift risk)

User feedback: "ถ้ามี bd ไม่ต้องเขียน markdown" — v2.8.2 บังคับ conditional: bd active = bd notes ONLY; no bd = md fallback. ห้ามคู่

## [2.8.1] — Uma Hardened (Patch — UX/UI verification teeth)

แก้ root cause "Uma ทำงานแย่, UI บิด ๆ เบี้ย ๆ, verify หลัง dev ชอบหลุด" — Uma ขาดเครื่องมือ + ไม่มี anti-puppet UX + Universal UX rules บังคับไม่ได้

### Added

- **🔴 `Bash` tool ใน Uma YAML** — ใหญ่ที่สุด. Uma ก่อนหน้านี้ไม่มี Bash → execute screenshot/diff/axe ไม่ได้ → skip silent / hallucinate. ตอนนี้ run Playwright/Chromatic/axe-cli/rg ได้จริง
- **🎨 UX Evidence Protocol** (meeting skill, extension of Project Evidence) — UX/a11y claim ต้อง cite tool output: `[axe report: path] critical=0`, `[Chromatic: URL] diff=0.08%`, `[screenshot: path]`. ห้าม "UI ดูดี / a11y ok" — ต้องมี tool path
- **🔴 Anti-Puppet UX/UI extension** (meeting skill) — ห้าม UI claim โดยไม่ paste Bash output: Playwright run, axe report, Chromatic URL, rg hardcoded check, manual keyboard/screen reader paste
- **🔴 Universal UX/UI Quality Rules** (meeting skill, 13 rules) — บังคับ semantic token (no hardcoded color/spacing), 8-pt grid, focus order = visual order, contrast ≥ 4.5:1, touch ≥ 44×44, 7 atomic states ครบ, mobile-first 320px, no `tabindex>0`, no `outline:none` without alt, no flash w/o reduce-motion, i18n text expand 30%
- **Uma Phase 1b mandatory Bash baseline capture** — `pnpm playwright test --update-snapshots` + paste path; ห้าม "baseline.png" placeholder
- **Uma Phase 3a 11-step mandatory Bash invocation** — capture / diff / token check / axe / contrast / states / content / AC bullet — ทุก step paste tool output
- **Uma Phase 3a verdict format** — bullet per AC + evidence path + Bash output; ห้าม "AC 5/5 PASS" รวบ
- **Dave Phase 2 screenshot mandatory** ถ้า frontend changed — `pnpm playwright screenshot` desktop + mobile → paste path; ไม่มี = no hand-off Uma
- **🔴 Auto-trigger Phase 3a detection** (implement.md Step 0 + Step 5) — Bash `git diff` + `grep -E "\.(vue|tsx|jsx|svelte|html|css)$"` → MANDATORY Uma POST. ห้าม Oliver "skip เพราะ minor"

### Changed

- Uma `Best Practices` → enforce ผ่าน Universal UX/UI Quality Rules (meeting skill บังคับ ทุก agent)
- Dave ข้อห้าม — เพิ่ม "ห้าม hand-off Phase 3a Uma POST ถ้า frontend changed แต่ไม่ paste screenshot path"
- implement.md Step 0 — Bash auto-detection แทน manual judgment
- implement.md Step 5 — reference 11-step mandatory Bash pattern + anti-puppet UX

### Root cause (audit finding from real engagement)

User report: "Uma ทำงานแย่, UI บิด ๆ เบี้ย ๆ, verify หลัง dev ชอบหลุด"

Audit เจอ 8 root cause:
1. **Uma YAML ไม่มี `Bash` tool** — rule บอก "screenshot + diff + axe" แต่ technically ทำไม่ได้ → skip silent / hallucinate
2. ไม่มี **Anti-Puppet UX/UI rule** — Anti-Puppet เดิม cover แค่ Dave/Quinn; Uma claim "design ok" ได้โดยไม่ paste
3. ไม่มี **Universal UX/UI Quality rules** — Mobile-first / 8-pt grid / focus order = guidance เท่านั้น, ไม่ block
4. Phase 1b baseline = "baseline.png" placeholder ได้ (no enforcement)
5. **Dave hand-off ไม่ require screenshot** — Uma มี baseline แต่ไม่มี "after" diff → can't verify
6. Phase 3a trigger **manual judgment** — Oliver decide "minor change skip Uma" → bad UI หลุด
7. Uma AC verification "AC 5/5 PASS" รวบได้ — ไม่มี bullet-per-AC mandatory
8. **Domain Evidence Protocol cover เฉพาะ regulation** — UX claim ไม่มี evidence protocol

### Token cost

- agents/ux-ui-designer.md: +~700 tokens (Phase 1b mandatory Bash + Phase 3a 11-step + verdict format)
- skills/meeting/SKILL.md: +~500 tokens (UX Evidence Protocol + Anti-Puppet UX + Universal UX 13 rules)
- commands/implement.md: +~200 tokens (Step 0 auto-detect + Step 5 mandatory Bash ref)
- agents/developer.md: +~30 tokens (ข้อห้าม screenshot hand-off)
- **Total: ~+1430 tokens (~+0.9%)** — discipline patch, not new feature

### Why patch bump (2.8.0 → 2.8.1)

Hardening + discipline — no new phase, no new command. Bash tool addition + rule tightening. Patch per Semver

## [2.8.0] — Smart Coop + Sprint (Minor — best-of-best lean refactor)

Workflow refactor "ครั้งที่ดีที่สุด": parallel where independent, sequential gate where dependent. รวม strength ของ dev-flow.md (Sprint cadence + bd-native + Uma PRE/POST gate) + v2.7 (Domain Expert + iter cap + Aaron deploy) → **leaner token (~−25% vs v2.7)** + **higher quality** (precise gates + sharper loop routing)

### Added

- **Outer Sprint Loop** — Pre-Sprint (`bd ready` + audit + `bd create`) → Sprint Exec (inner loop) → Sprint Close (`bd close` + `git push` + `bd remember` + retro 1-pager) → next sprint
- **NEW `/sprint` command** — sub-commands: `pre` (planning), `status` (mid-sprint), `close` (deploy + retro), `retro` (standalone)
- **Phase 1a Foundation (TRUE parallel)** — Bella ∥ Sara on independent scope (BA vs SA), end with light cross-read (NO mid-checkpoint cross-read overhead from v2.7)
- **Phase 1b Conditional Expand (sequential)** — Uma + Domain read 1a baseline → produce wireframe/tokens/a11y/baseline + regulation/business rule → `outputs/SPEC-<bd-id>.md`
- **Phase 3a UI Check (Uma POST — sequential gate)** — Uma verify screenshot diff + a11y manual + own AC BEFORE Chris/Quinn (catches UI bug early, saves Chris/Quinn effort)
- **Phase 3b Code Review (Chris ∥ Quinn TRUE parallel)** — only after Uma POST PASS; truly independent scope (static review vs runtime test)
- **Phase 4 Triage routing (precise)** — code finding → Phase 2 ∥ UI finding → Phase 1b ∥ spec finding → Phase 1a (granular vs v2.7 binary Phase 1 or 2)
- **Phase 5 Deploy (Aaron batched sprint-end)** — reduce deploy overhead, consolidate risk; exception: P0 hotfix
- **4 new Approval Gates**: `pre-spec-expand` (1a→1b), `pre-ui-check` (2→3a), `pre-code-review` (3a→3b); `pre-loop-exit` retained
- **bd-native operational** — `bd ready`, `bd update --claim`, `bd update --notes`, `bd close`, `bd remember`, `bd dolt push` ทุก step (lean: state ใน bd, ไม่ verbose ใน chat)
- **Per-issue loop state tracking** — Oliver maintain `{iter, last-phase, findings, next-phase}` per bd-id
- **Sprint state tracking** — Oliver maintain `{sprint-N, ready, in_progress, closed, discovered}`
- **Uma own AC + baseline screenshot** — Phase 1b produces verifiable AC + baseline for Phase 3a diff (audit-ready)

### Changed

- **Phase Contract refactor** — replaces v2.7 "3 macro-phase + loop" with v2.8 "Outer Sprint + Inner 5-phase Smart Coop". Backward-compat phase names (clarify/design/ux-design/review/integration) ยังใช้อ้างอิงใน sub-step
- **Smart Coop Pattern section** — replaces "Coop Phase Pattern" (v2.7). New parallel-vs-sequential matrix อธิบายเมื่อไหร่ใช้ pattern ไหน
- **Lifecycle Hooks** — grouped by phase (Pre-Sprint / 1a / 1b / 2 / 3a / 3b / 4 / 5 / Sprint Close) with bd commands
- **commands/design-system.md** — refactor v2.7 7-step Coop pattern → v2.8 3-step (Triage → 1a parallel → 1b conditional sequential). Output: `outputs/SPEC-<bd-id>.md`
- **commands/implement.md** — refactor v2.7 Coop Review (3 parallel) → v2.8 sequence (Uma POST gate → Chris ∥ Quinn parallel). Output: `outputs/REVIEW-<bd-id>.md`
- **Oliver Engagement Plan** — sprint topology + phase-precise loop routing
- **Bella + Sara** — both got "Phase 1a Foundation" section (parallel pattern + bd notes compact format)
- **Uma** — replace v2.7 "Coop Design Participation + Coop Review Participation" with v2.8 "Phase 1b PRE-Design (sequential)" + "Phase 3a POST-Check (sequential gate)"
- **Chris + Quinn** — replace v2.7 "Coop Review Participation" with v2.8 "Phase 3b Code Review (parallel AFTER Uma POST PASS)" — clarifies ordering
- **Aaron** — add "Phase 5 Deploy (batched sprint-end)" section
- **Dave** — Process step 10 → 10+11 (Phase 3a Uma POST gate → Phase 3b Chris ∥ Quinn parallel); Self-Routing reflect new ordering
- **Approval Gates** — drop `pre-coop-design-exit` (v2.7), add `pre-spec-expand` + `pre-ui-check` + `pre-code-review` (v2.8); standard count remains **10**
- **Oliver ข้อห้าม** — drop v2.7 Coop bans, add v2.8 phase-precise bans (no serialize 1a, no parallel 1b, no skip 3a gate, no serialize 3b, no skip Triage routing)
- **DoD** — drop 3 v2.7 lines, add 5 v2.8 lines (phase-precise checkpoints)

### Token cost

- skills/meeting/SKILL.md: ~−1500 tokens (Coop Pattern section shrink, but added Sprint section) — net ~−500
- agents/orchestrator.md: ~+200 tokens (sprint topology + loop state table)
- commands/design-system.md: ~−800 tokens (3 steps vs 7 steps; integrated output instead of Coop bundle)
- commands/implement.md: ~−200 tokens (clearer sequence)
- **NEW commands/sprint.md**: +600 tokens
- agents/business-analyst.md: +80 tokens
- agents/solution-architect.md: +90 tokens
- agents/ux-ui-designer.md: ~−100 tokens (sections cleaner)
- agents/code-reviewer.md: ~−40 tokens
- agents/qa-engineer.md: ~−40 tokens
- agents/developer.md: ~+30 tokens
- agents/devops-engineer.md: +160 tokens
- **Total: ~−500 to −1000 tokens NET** (~−0.3% to −0.6%) — first version to REDUCE plugin size while increasing structural rigor

### Why minor bump (2.7 → 2.8)

Phase topology change (Coop 3-macro-phase → Smart 5-phase + Sprint outer) แต่ backward-compat phase names. Minor bump per Semver

### Root cause (audit finding from dev-flow.md comparison)

dev-flow.md surface ของ 3 gaps ใน v2.7.0:
1. **Coop everywhere = wasteful** — Bella → Sara มี natural BRD-informs-ADR dependency; 4-way parallel + cross-read = 40% redundant token
2. **Uma in Coop Review = lost gate signal** — UI bug ที่ Uma เจอ ระหว่าง parallel review = late; Uma POST sequential gate BEFORE code review = catch early
3. **Loop routing binary** — v2.7 "Phase 1 หรือ Phase 2" loose; v2.8 "1a / 1b / 2" precise

dev-flow.md gaps ที่ v2.8 ครอบ:
- เพิ่ม Domain Expert ใน Phase 1b (dev-flow ไม่มี)
- เพิ่ม Aaron Phase 5 Deploy (dev-flow ไม่มี)
- เพิ่ม max iter 3 cap (dev-flow loop ไม่มี cap)
- เพิ่ม 10 explicit Approval Gates

## [2.7.0] — Coop Workflow (Minor — structural workflow refactor)

ปรับ workflow discipline ให้ตรง user mental model: **3 macro-phase + loop** แทน sequential 7 phases. Design + Review เป็น Coop (parallel + cross-feedback + integrated artifact) ไม่ใช่ serialize hand-off

### Added

- **Phase Contract — 3 macro-phase + loop** (meeting skill)
  - Phase 1 🤝 Coop Design (parallel): Bella + Sara + Uma* + Domain* — output `outputs/01-coop-design.md` integrated bundle
  - Phase 2 🛠️ Implement: Dave (sequential or parallel Dave#1/#2)
  - Phase 3 🔎 Coop Review (parallel): Chris + Quinn + Uma* — output `outputs/03-coop-review.md`
  - Phase 4 🔁 Loop Decision (Oliver): all green → Phase 5 / code finding → Phase 2 / design finding → Phase 1; max iter 3
  - Phase 5 🚀 Deploy: Aaron
- **Coop Phase Pattern** (meeting skill) — explicit pattern: kick-off → parallel draft → mid-checkpoint cross-read → cross-feedback (1-2 round) → integration sign-off → bundle
- **Approval Gate `pre-coop-design-exit`** (Oliver) — Phase 1 → Phase 2 transition; ทุก participant ack cross-validation
- **Approval Gate `pre-loop-exit`** (Oliver) — Phase 4 Loop Decision → Phase 5 Deploy; all 3 reviewers green + iter ≤ 3
- **Loop Enforcement** (Oliver) — track iter state, decide loop target by finding type, escalate ถ้า iter > 3
- **Uma Coop Design Participation section** — explicit cross-direction matrix (Uma ↔ Bella, Sara, Domain)
- **Uma Coop Review Participation section** — visual diff + design adherence + a11y manual + component state + content design
- **Chris Coop Review Participation section** — scope split (unit/7-dim Chris; visual/a11y Uma; integration/E2E Quinn)
- **Quinn Coop Review Participation section** — scope split + automation/manual handoff to Uma

### Changed

- **commands/design-system.md** — refactor sequential 0/1/2/3/3.5/4 → 7-step Coop pattern (Triage → Kick-off → Parallel Draft → Mid-Checkpoint → Cross-Feedback → Integration Sign-off → Bundle → Exit Gate). Output: `outputs/01-coop-design.md` (integrated, แทน 01-brd / 02-domain / 03-arch / 04-ux)
- **commands/implement.md** — Step 5 Hand-off เพิ่ม Uma ใน Phase 3 Coop Review parallel; Step 6 Loop Decision section ใหม่; Step 7 Domain Validation (renumber)
- **agents/developer.md** — Process step 10 Hand-off เพิ่ม Uma; Self-Routing split Phase 1 vs Phase 3 Uma scope
- **agents/orchestrator.md** — Engagement Plan pipeline restructure เป็น 3 macro-phase + loop; Approval Gates table เพิ่ม pre-coop-design-exit + pre-loop-exit
- Approval Gates standard count: 8 → **10** (เพิ่ม pre-coop-design-exit + pre-loop-exit)
- Oliver ข้อห้าม — เพิ่ม "ห้าม serialize Coop phase", "ห้าม skip Loop Decision"
- DoD — เพิ่ม 3 บรรทัด: Coop Design checkpoint pass, Coop Review checkpoint pass, Loop iter ≤ 3

### Token cost

- skills/meeting/SKILL.md: +~700 tokens (Phase Contract refactor + Coop Pattern section + Lifecycle Hooks restructure + Universal rules + DoD + Approval Gates)
- agents/orchestrator.md: +~300 tokens (Engagement Plan + Loop Enforcement section + Gates + ข้อห้าม)
- commands/design-system.md: +~400 tokens (Coop pattern 7-step + cross-validation matrix)
- commands/implement.md: +~120 tokens (Step 5+6 + Rule 4+6+7)
- agents/developer.md: +~80 tokens (Process step 10 + Self-Routing)
- agents/ux-ui-designer.md: +~280 tokens (2 sections: Coop Design + Coop Review)
- agents/code-reviewer.md: +~80 tokens (Coop Review Participation)
- agents/qa-engineer.md: +~100 tokens (Coop Review Participation)
- **Total**: ~+2060 tokens (~+1.3%) — structural change ที่ตอบ user mental model

### Why minor bump (2.6.x → 2.7.0)

Structural workflow change: phase contract restructure จาก 7-phase linear → 3 macro-phase + loop. Backward-compatible terminology (clarify/design/ux-design/review/integration ยังใช้ภายใน macro-phase) แต่ pipeline topology เปลี่ยน → minor bump per Semver

### Root cause (audit finding)

Pre-v2.7 workflow ขัด user mental model 3 จุด:
1. **Phase 1 design** = sequential Bella → Sara → Uma → Domain (serialize) → conflict discover late, rework expensive
2. **Uma หายจาก review** (Phase 3) — Chris + Quinn ตรวจ code/test แต่ visual diff / design adherence / a11y manual ไม่มีคนทำ post-implement
3. **ไม่มี Loop mechanic** — review fail → ไม่ชัดว่ากลับไปไหน; agent ตัดสินใจตามใจ

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
