# shode-house — Repo Invariants (v3.16.3)

> ทุก rule = invariant ที่ script ตรวจ. จะแหก → แก้ script ก่อน

## ⚙️ Prerequisites

- **bash + jq + python3 (stdlib)** for the gate — inline in `.github/workflows/ci.yml`, run locally with `make validate`. `jq`: `brew install jq` / `apt install jq`
- **make** + **zip** for packaging (`make pack`)
- **git** + **gh CLI** for release/publish (or GitHub Actions)

## Skills

- **bucket folders** ใต้ `skills/`:
  - `workflow/` (ask, dev-gate, automate-test, diagnose, data-migration, api-contract, decompose) · `ops/` (incident, slo, secure, drain) · `ui/` (ui-test, web-q) · `style/` (caveman)
  - `discipline/` (shode-house-discipline, -routing, -deliverable, -workflow, review-checklist, domain-core) — 20 shipped skills (7 · 4 · 2 · 1 · 6); v3.17 merge 4 ชื่อเก่าไม่มี stub (ตาราง → CHANGELOG) และชื่อเก่าห้ามกลับมา (`tests/test_tombstone.py`)
  - `in-progress/` + `deprecated/` — **ไม่ ship**
- 5 bucket แรก → ต้องอยู่ใน `.claude-plugin/plugin.json` skills list + `README.md` index
- `in-progress/` + `deprecated/` → **ไม่** อยู่
- SKILL.md description = **1–2 English sentences**: capability + decision boundary (what it is for, and the nearest thing it is not for) — no trigger/keyword lists, no fixed section format; ≤ 320 chars (CI #9)
- SKILL.md **≤ 300 บรรทัด** เกิน → แตกเป็น reference file ข้าง ๆ. **ไม่มี exception** (CI #1). ขนาดเป็น byte: skill ที่ถูก preload คุมด้วย CI #16 ที่เหลือคุมด้วย line cap
- Skill ผลิต deliverable ต้องมี: `## When NOT to use` + `## Inputs and decision boundaries` ที่มี `### Stop and return` ไม่ว่าง (CI #24c บังคับ 6 root: dev-gate · decompose · drain · secure · review-checklist · diagnose; skill อื่นยังใช้ `## Required inputs — <เงื่อนไข>` ได้ แต่ห้ามคำว่า "refuse without")

## Handoff + Language

- **Artifact-passing บังคับ**: phase artifact → ไฟล์; delegation ส่ง **path + task id + phase + iter ไม่ส่งเนื้อหา** (sub-agent ไม่เห็น conversation history); producer return = conclusion + path. Owner = `shode-house-discipline § Handoff Contract`
- ทุก agent **ตอบภาษาเดียวกับ message ล่าสุดของ user**; รายการ verbatim ห้ามแปล อยู่ที่ owner = `shode-house-discipline § Response Language`

## Commands

- **3-flag rule**: ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag/mode รองรับได้. เกิน 3 → ค่อยแตก
- Deprecated command keep เป็น alias 1–2 release window แล้วลบ (skill = no stub: test_tombstone)

## Agents

- 🔴 **Redact ก่อน paste** — secret/token/auth header/PII → `<REDACTED>` ทุกครั้งที่ paste evidence. Owner = `shode-house-discipline` § Universal Rules; detail `diagnose` § Redact
- 🔴 **Review มี 2 แกน** (v3.12) — Standards (Chris 7-dim: *เขียนถูกหลักไหม*) กับ Spec (*ทำตรงกับที่ spec ขอไหม*) เป็นคนละ sub-agent และ **ห้าม merge/rerank ข้ามแกน**; code ที่ standards ผ่านครบแต่ทำผิดเรื่อง = Standards PASS / Spec FAIL. ทุก review ต้อง **pin fixed point** ด้วย `git diff <base>...HEAD` (three-dot) ก่อน fan-out
- 🔴 **Preload budget** — `skills:` cap 3 คุม *จำนวน* ไม่คุม *ขนาด*. กฎ: **skill ที่ถูก preload ต้องเป็นสิ่งที่ *ทุก branch* ใช้** — rule ของบาง role อยู่ใน agent file ของ role นั้น หรือโหลดเองด้วย `Skill` ตอน runtime. **CI #16**: hard cap 31,000 B/agent + key ต่อ agent ใน `.preload-budget` (grace 0 — ขึ้นไม่ได้ ลงได้อย่างเดียว)
- 🔴 **Catalog ≠ Evidence** (v3.11) — `references/design-intel` เป็น *ข้อเสนอ* (palette/pairing/pattern จาก CSV ที่ upstream ระบุเองว่า `derived` / `needs-review`) ส่วน **หลักฐาน** คือ WCAG/axe/Lighthouse/Playwright output เท่านั้น. ขัดกันเมื่อไหร่ **มาตรฐานชนะ catalog**; ห้าม cite ตัวเลขจาก CSV ในระดับเดียวกับ tool output (ผิด UX Evidence Protocol). Runtime steps (0-result retry ฯลฯ) → `references/runbooks/uma-phase-1b.md`. **enforce CI gate check #17** + `check_contrast.py` gate ก่อนเขียน `tokens.json`
- 🔴 **`Skill` บังคับใน `tools:` ทุก agent** (v3.10) — `tools:` ที่ระบุ explicit และ **ไม่มี** `Skill` = subagent โหลด skill ไม่ได้เลย (ไม่ใช่แค่ที่ไม่ได้ preload — *ทั้งหมด*). `skills:` = preload (inject full content, cap 3); `Skill` ใน `tools:` = โหลดเพิ่มเองตอน runtime. **ต้องมีทั้งคู่** — enforce CI gate check #14
- 🔴 **rule ที่ "ทุก agent ต้องทำตาม" ต้องอยู่ใน `shode-house-discipline`** (ตัวเดียวที่ preload 19/19). rule ที่เป็นของบาง role ห้ามอยู่ที่นี่ — ย้ายไป skill ของ role นั้นแล้วให้เขาโหลดเอง (discipline โดน ×19 ทุกไบต์)

- 🔴 **`skills:` frontmatter บังคับทุก agent** (v3.8) — reference ใน prompt body **ไม่พอ**: sub-agent เกิดใน context ว่าง เห็นแค่ agent body + delegation message + target-project CLAUDE.md. skill ที่ orchestrator โหลดไว้ **ไม่ตามไป**
  - ขั้นต่ำ `shode-house-discipline`; ≤ 3 skill/agent (คุม instruction density — IFScale: instruction เยอะ = following เสื่อม)
  - ห้ามชี้ `in-progress/` หรือ `deprecated/` — **Claude Code ข้ามเงียบ ๆ** (debug log เท่านั้น) ไม่ error
  - **enforce**: CI gate check #13
- Recite Card อยู่ที่ `output-styles/oliver.md` §1
- `ask/SKILL.md` = public entry-point + team orientation
- **Model frontmatter (v3.5)**: ค่าที่อนุญาต = `claude-fable-5` (Stan/Sara/Sentinel/Uma เท่านั้น) | `opus` | `sonnet`. ห้าม pin dated model string. ตาราง model มีที่เดียว = README § Model Strategy (skill อื่นห้าม copy — เคย drift ใน routing skill v2.x). Fallback = settings `fallbackModel`, budget = `CLAUDE_CODE_SUBAGENT_MODEL` (doc ใน README)
- **enforce**: CI gate (`.github/workflows/ci.yml`) ตรวจ model value + Fable-5 whitelist + ห้าม model table นอก README

## Output styles

- อยู่ที่ `output-styles/<name>.md` (plugin root, default scan path) — **ห้ามใส่ `outputStyles` ใน `plugin.json`** เพราะ field นั้น *replace* default scan และเพิ่มความเสี่ยง Cowork validator
- Frontmatter: `name` + `description` บังคับ (CI #15) · `keep-coding-instructions: true` เก็บ engineering prompt เดิมไว้ · `force-for-plugin: true` = ยึด main session อัตโนมัติทันทีที่ plugin เปิด (override `outputStyle` ของ user)
- Output style แก้ **system prompt ของ main loop เท่านั้น** (subagent ไม่ได้รับผล); มีผลหลัง `/clear` หรือ session ใหม่
- `make pack` ต้อง ship `output-styles/` (อยู่ใน zip list แล้ว)
- ⚠️ **ยังไม่ยืนยันว่า Cowork รองรับ output style** — docs ครอบเฉพาะ Claude Code CLI/Code tab; ต้องทดสอบ drag-drop จริง

## Plugin

- `plugin.json` version = SemVer; `marketplace.json` ตาม
- `.plugin` zip artifact = `shode-house-v<MAJOR>.<MINOR>.<PATCH>.plugin`
- Build via `make pack` (zip ผ่าน Makefile); ห้าม zip มือนอก Makefile

### Plugin manifest — Cowork validator constraints (🔴 บังคับ — ป้องกัน "Plugin validation failed")

> **History**: v2.5.1 + v3.1.0 เคย fail "Plugin validation failed" ตอน Cowork drag-drop. CLI `claude plugin validate` ผ่าน + JSON schema ผ่าน **ไม่ได้แปลว่า Cowork ผ่าน** — Cowork validator stricter ที่ runtime

**Hard cap (Cowork enforce, schema ไม่ enforce)**:

- `plugin.json` → `description` **≤ 200 chars, ASCII only** (no em-dash `—`, no Thai, no Unicode quote)
- `marketplace.json` → `description` (top-level) **≤ 200 chars ASCII**
- `marketplace.json` → `plugins[].description` **≤ 100 chars ASCII**
- เกิน → Cowork ขึ้น "Plugin validation failed" เงียบ ๆ (no specific error)

**Schema rules (CLI enforce, ทั้ง Cowork + CLI)**:

- `skills` / `commands` / `agents` field = **array of path strings** เท่านั้น (เริ่มด้วย `./`, ห้าม `..`, ห้าม `\`)
  - ❌ **ห้าม array of objects** เช่น `[{"name": "x", "path": "y", "role": "z"}]` — schema reject
  - ✅ ถูก: `"skills": ["./skills/workflow/", "./skills/ops/"]`
- ไม่ใส่ field → loader auto-discover ที่ default path (`skills/`, `commands/`, `agents/`) **1 level deep เท่านั้น**
- Nested `skills/<bucket>/<name>/SKILL.md` ต้องประกาศ bucket paths ใน `skills` field — ไม่งั้น loader หาไม่เจอ
- `additionalProperties: false` — ห้ามเพิ่ม field นอก schema (`name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `category`, `tags`, `commands`, `agents`, `skills`, `outputStyles`, `hooks`, `mcpServers`, `lspServers`, `settings`)

**Anti-patterns ที่เคยทำให้ fail (อย่าทำซ้ำ)**:

```jsonc
// ❌ Round 1 v3.1.0 — Object form + ยาว + Thai
{
  "description": "Multi-agent software house team v3.1: 19 expert agents in 7 teams + 18 lazy-load skills (split meeting-god-skill into 7 discipline modules + review-checklist DRY) + 6 commands (consolidated /init+/setup-project, /design-system+/spec-only). Bucket-folder lifecycle (workflow/ops/ui/style/discipline/in-progress/deprecated). CLAUDE.md repo invariants + scripts/ dev-loop. 9arm-inspired skill craft: 4-section description format, When-NOT + Required-inputs gates, Recite Discipline Card, skill composition pointers. Covers Fintech, ERP, SAP, Trading, Insurance, Booking, E-commerce, UX/UI.", // 586 chars + em-dash → FAIL
  "skills": [
    {"name": "ask", "path": "skills/workflow/ask", "bucket": "workflow", "role": "..."} // object form → schema reject
  ]
}

// ❌ Round 2 v3.1.0 — schema fix แล้ว แต่ description ยังยาว
{
  "description": "Multi-agent software house team v3.1: ... 586 chars + Thai ...", // ยังเกิน → FAIL Cowork (CLI pass)
  "skills": ["./skills/workflow/"] // schema ok
}

// ✅ Round 3 v3.1.0 — ผ่านทั้ง CLI + Cowork
{
  "description": "Multi-agent software house team v3.1: 19 agents in 7 teams + 18 lazy-load skills + 6 commands. Bucket-folder lifecycle. 9arm-inspired skill craft.", // 146 chars ASCII → PASS
  "skills": ["./skills/workflow/", "./skills/ops/", "./skills/ui/", "./skills/style/", "./skills/discipline/"]
}
```

**Rules ก่อน bump version**:

1. **Detail / marketing copy → `README.md` เท่านั้น** ห้ามใส่ใน manifest description
2. ก่อน push: CI gate (`.github/workflows/ci.yml`) enforce description ≤ 200 chars + ASCII (รันบน GitHub)
3. ก่อน release: **drag-drop ทดสอบ Cowork จริง** — CLI validate ผ่าน ≠ Cowork ผ่าน
4. ถ้า fail: `git log --grep="validator"` ดู lesson learned เก่าก่อน — มี history v2.5.1 + v3.1.0
5. เจอ bug ใหม่ที่ schema ไม่ enforce แต่ Cowork enforce → เพิ่ม rule ที่นี่ + เพิ่ม check ใน `.github/workflows/ci.yml` (gate step) ทันที

## Repo

- README → link skill name ไปยัง SKILL.md เสมอ
- CHANGELOG → ทุก minor/major bump เพิ่ม entry
- ทุก PR run CI gate (`.github/workflows/ci.yml`) ผ่านก่อน merge
- **Dev-loop**: `make validate` (gate เดียวกับ CI) · `python3 -m pytest -q tests` · `make pack` (zip) · `make stats` · `make skills`; publish via `gh` / GitHub Actions

## Lazy ≠ Negligent

- YAGNI ladder (dev-gate Step 0) + caveman compression ตัดได้เฉพาะความซับซ้อน/word ที่ยังไม่ต้องใช้
- **ห้ามตัด**: trust-boundary validation · data-loss handling · security control · accessibility (WCAG) · regulation/compliance
- ทางลัดที่ defer → `shortcut(bd:<id>): <reason>; upgrade → <path>` → `grep -rn 'shortcut(bd' .` / `/review --debt`
- Memory-file compress → เก็บ `<file>.full.md` + verify CI gate (push → CI เขียว) เหมือนเดิม
- **Runtime guarantee = generate, don't ship**: plugin ดูแลแค่หลักการ+วิธีการ (contract). Harness contract ต้อง **establish ทุกครั้งที่เข้า project** (`/init` rule 11 → `.shode-house/config.yaml`). guarantee ที่ต้อง enforced runtime (long-run fan-out cap/retry/checkpoint, ฯลฯ) → **Aaron** generate runner **ตาม contract ใน `references/patterns/durable-agent-runtime.md`** (journal/idempotency/replay boundary/version stamp/HITL hash/crash injection) (infra/CI-level; app-level → Dave) ที่ fit project เข้า **target project repo** (ผ่าน dev-gate); ห้าม ship generic script ใน plugin. ไม่มี need = ไม่ generate (YAGNI) แต่ contract ต้องมี

## Bias Discipline

- **Embed in agent prompts**: 19 agents มี `## Bias Discipline` (Chris/Quinn: no PASS without required evidence — defect = FAIL, missing evidence = BLOCKED/PARTIAL (`agents/code-reviewer.md`, `agents/qa-engineer.md`, `review-checklist` §Adversary stance); Felix/Tara = "ห้าม blindly accept vendor"; Sentinel = hold on "low risk" ถ้า trigger)
- **No separate eval agent**; `skills/in-progress/eval-harness/` = maintainer reference, ไม่ ship
- **Anti-bias source-of-truth**: agent prompt + `output-styles/oliver.md` §1 Recite Card

## PEV Loop

- Plan → Execute → Verify → Triage per task (no sprint loop, no `/sprint`); phases 0 → 1a/1b/1c → 2 → 3a/3b → 4. Owner = `shode-house-workflow`

## Budgets · rule conservation · generated tree (v3.17)

- **4 budget files** (`.skill-metadata-budget` · `.preload-budget` · `.agent-core-budget` · `.workflow-scenario-budget`) = ค่าวัดจริง ลงได้อย่างเดียว. ห้ามเพิ่ม budget file; ห้ามขึ้น key/grace เพื่อให้เขียว → ตัด non-safety text ใน change เดียวกัน
- ลบ/reword rule line ใน shipped skill/agent → entry ใน `.rule-migrations.json` (exact source + fragment + reason) + count pin ใน `tests/test_rule_migrations.py`; gate = `scripts/rule-conservation.py` (pinned base `.rule-baseline`). กฎที่มี `root_only` anchor (`.enforcement-map.json`, CI #21 floor 123) ต้องอยู่ root file ไม่ใช่ lazy reference
- `plugins/shode-house/**` = generated — `python3 scripts/pack-team.py --tree plugins/shode-house`; ห้ามแก้มือ (CI #25 `--check`); skill adapter ห้ามบังคับ full read (#25b)
- Shipped surface = tracker-neutral: ห้าม hardcode `bd <verb>` (`tests/test_tracker_neutral.py`); tracker ตาม target project
- skills/agents/commands/output-styles ห้ามพึ่ง `CHANGELOG.md` / `SHODE-HOUSE-MASTER.md` (maintainer history เท่านั้น)
- Frozen probe protocol: ไฟล์ที่ pin ใน `eval/FREEZE.sha256` ห้ามแก้ (`bash eval/check-freeze.sh`)

## Contribution rules (v3.17)

- **New rule**: failure ที่กันคืออะไร · canonical owner คือใคร (ตาราง → `docs/enforcement-map.md`) · ต้อง always-on หรือเป็น lazy reference ได้ · eval/gate ตัวไหนคุ้มครอง. ห้ามเพิ่ม prompt text เพียงเพราะ "ฟังดูปลอดภัยกว่า"
- **New skill**: capability แยกใช้ซ้ำได้จริงไหม · skill เดิม + ≤ 1 branch/reference รองรับได้ไหม · discovery ยัง unambiguous ไหม — default = ไม่เพิ่ม (20)
- **New model profile**: eval ไหน fail · model family ไหน · สม่ำเสมอแค่ไหน · ทำไม core wording แก้ไม่ได้ · override ที่เล็กที่สุด. ตอบไม่ครบ = ไม่เพิ่ม; profile ห้าม redefine workflow/safety/ownership/domain


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
