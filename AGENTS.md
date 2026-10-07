# Repository Instructions

Repo-wide rules for every agent and tool working in this repository. This file is loaded in full on every session (Claude Code imports it from `CLAUDE.md`), so it holds one line per rule; explanation, history and examples live in the `docs/` files it links and are read only when opened. Add detail there, not here.

## Authority

Current user instructions and repository rules take precedence over plugin, tool, and tracker defaults. Generated or tool-managed guidance (including anything Beads writes) is task-tracking help, not permission to override them.

## Task Tracking

This repository uses Beads (`bd`) for durable task tracking: `bd ready` to find work, `bd show <id>` to read it, `bd update <id> --claim` to take it, `bd close <id>` when it is done. Do not keep markdown TODO lists as the source of truth.

Run `bd prime` when detailed Beads workflow guidance is required.

Detailed Beads workflow: `.agents/skills/beads/SKILL.md`. Install, command reference, storage/sync architecture, agent context profiles, and the session completion sequence: `docs/bd-quickstart.md`.

## Safety

Do not commit, push, sync remote state (including `bd dolt push` / `bd dolt pull`), or perform destructive actions unless authorized by the current task or repository policy. Do not commit or push without clear authority; a current "do not commit" or "do not push" instruction always wins. If an authorized sync or push is blocked, stop and report the exact command and error.

## Validation

Run checks relevant to the changed behavior (`make validate`, `python3 -m pytest tests -q`, or the narrower check the change touches).

Fix failures caused by the requested change and rerun affected checks without requesting approval after every local iteration. At handoff, report changed files, the validation you ran, and its result.

## Shell

Use non-interactive shell operations in automated workflows; `cp`, `mv`, and `rm` may be aliased to `-i` and hang on a prompt.

- Files: `cp -f`, `mv -f`, `rm -f`; recursive: `cp -rf`, `rm -rf`
- `ssh` / `scp`: `-o BatchMode=yes`
- `apt-get`: `-y`; `brew`: `HOMEBREW_NO_AUTO_UPDATE=1`
- `bd`: never `bd edit` (opens an editor); use `bd update` flags

## Repo Invariants (v4.0.0)

> ทุก rule = invariant ที่ script ตรวจ. จะแหก → แก้ script ก่อน

The rules are stated in this file and nowhere else. The linked files add detail, rationale, history and examples to a rule stated here and never restate it (`tests/test_docs_no_rule_copy.py`); if a linked file seems to say otherwise, this file is the rule. Open the file before touching that area:

| Open | Before touching |
|------|-----------------|
| `docs/repo-invariants/skills-agents.md` | `skills/`, `agents/`, `commands/`, `output-styles/`, review or handoff rules |
| `docs/repo-invariants/plugin-release.md` | `.claude-plugin/`, `.pack-allowlist`, README/CHANGELOG, a version bump or release |
| `docs/cowork-validator-history.md` | a manifest `description` or schema change, or a "Plugin validation failed" report |
| `docs/repo-invariants/budgets-contribution.md` | a budget file, a rule line in a shipped skill/agent, `plugins/shode-house/`, a new rule / skill / model profile |

## Skills

- Shipped buckets = `workflow/` · `ops/` · `ui/` · `style/` · `discipline/` (20 skills): each bucket path is in the `.claude-plugin/plugin.json` skills list (CI #3) and each skill is linked in the `README.md` index (CI #11b). `in-progress/` + `deprecated/` never ship and are never listed (CI #2).
- The 4 skill names retired in v3.17 have no stub and must not come back (`tests/test_tombstone.py`).
- SKILL.md description = 1–2 English sentences: capability + decision boundary (what it is for, and the nearest thing it is not for) — no trigger/keyword lists, no fixed section format; ≤ 320 chars (CI #9).
- SKILL.md ≤ 300 lines, no exception; over → split into a sibling reference file (CI #1). Size in bytes: a preloaded skill is capped by CI #16, the rest by the line cap.
- A skill that produces a deliverable has `## When NOT to use` + `## Inputs and decision boundaries` with a non-empty `### Stop and return` (CI #24c enforces this on 6 roots: dev-gate · decompose · drain · secure · review-checklist · diagnose; other skills may still use `## Required inputs — <condition>`, but never the words "refuse without").

## Handoff + Language

- **Artifact-passing บังคับ**: phase artifact → ไฟล์; delegation ส่ง **path + task id + phase + iter ไม่ส่งเนื้อหา** (sub-agent ไม่เห็น conversation history); producer return = conclusion + path. Owner = `shode-house-discipline § Handoff Contract`
- ทุก agent **ตอบภาษาเดียวกับ message ล่าสุดของ user**; รายการ verbatim ห้ามแปล อยู่ที่ owner = `shode-house-discipline § Response Language`

## Commands

- **3-flag rule**: ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag/mode รองรับได้. เกิน 3 → ค่อยแตก
- Deprecated command keep เป็น alias 1–2 release window แล้วลบ (skill = no stub: test_tombstone)

## Agents

- 🔴 **Redact ก่อน paste** — secret/token/auth header/PII → `<REDACTED>` ทุกครั้งที่ paste evidence. Owner = the safety floor (`.safety-floor/body.md`, copied into every agent body and the router style by `scripts/floor.py`); detail `diagnose` § Redact
- 🔴 **Review has 2 axes** — Standards (`code-reviewer`) and Spec (`business-analyst`) are separate sub-agents; never merge or rerank findings across axes. Every review pins its fixed point with `git diff <base>...HEAD` (three-dot) before fan-out. CI #19 checks dispatch only, not this.
- 🔴 **Preload budget** — a preloaded skill must be something every branch uses; a role-specific rule lives in that role's agent file or is loaded at runtime with `Skill`. CI #16: hard cap 31,000 B/agent + per-agent key in `.preload-budget` (down only).
- 🔴 **Catalog ≠ Evidence** — `references/design-intel` is a proposal; evidence is WCAG/axe/Lighthouse/Playwright output only. Standard beats catalog; never cite a CSV number at the level of tool output. CI #17 + the `check_contrast.py` gate before writing `tokens.json`.
- 🔴 **`Skill` in `tools:` of every agent**, in addition to `skills:` — an explicit `tools:` list without it leaves the subagent unable to load any skill at all (CI #14).
- 🔴 **A rule every agent must follow lives in `shode-house-discipline`** (the only skill preloaded by all 18). A rule for some roles must not go there — it goes in that role's skill or agent file.
- 🔴 **`skills:` frontmatter on every agent** — a reference in the prompt body is not enough. Minimum `shode-house-discipline`, ≤ 3 skills, never pointing at `in-progress/` or `deprecated/` (silently skipped) (CI #13).
- **Model frontmatter**: `claude-fable-5` (staff-engineer, solution-architect, security-engineer, ux-ui-designer only) | `opus` | `sonnet`; never a dated model string (CI #5). The model table exists only in README § Model Strategy (CI #6).
- **Bias Discipline**: all 18 agents carry `## Bias Discipline`; no separate eval agent (`skills/in-progress/eval-harness/` is maintainer reference, not shipped). Source of truth = agent prompt + the discipline card in the router style `output-styles/shode-house.md`.
- **PEV Loop**: Plan → Execute → Verify → Triage per task (no sprint loop, no `/sprint`); phases 0 → 1a/1b/1c → 2 → 3a/3b → 4. Owner = `shode-house-workflow`

## Output styles

- Live at `output-styles/<name>.md`; **never add `outputStyles` to `plugin.json`** (the field replaces the default scan). Frontmatter `name` + `description` required (CI #15).
- `make pack` must ship `output-styles/`. ⚠️ Cowork support for output styles is still unconfirmed — test by real drag-drop.

## Plugin

- `plugin.json` version = SemVer and `marketplace.json` follows; the `## Repo Invariants` heading carries the same version (CI #9). Artifact = `shode-house-v<MAJOR>.<MINOR>.<PATCH>.plugin`.
- Build only with `make pack`; never zip by hand outside the Makefile.
- What ships = `.pack-allowlist` only: a path read at run time, or one the plugin format / the licence needs. `docs/`, `AGENTS.md`, `CLAUDE.md`, `README.md` and `CHANGELOG.md` never ship; shipped text never points at a path that does not ship, and a document it has to open lives under `references/` (CI #26).
- 🔴 **Cowork validator** (stricter than CLI validate and the JSON schema; fails silently with "Plugin validation failed"):
  - `plugin.json` `description` and `marketplace.json` top-level `description` ≤ 200 chars, `marketplace.json` `plugins[].description` ≤ 100 chars; all ASCII only: no em-dash, no Thai, no Unicode quote (CI #4).
  - `skills` / `commands` / `agents` = arrays of path strings starting with `./`, never objects, no `..`, no `\` (CI #7). Nested skill buckets must be declared in `skills` (CI #3).
  - No field outside the manifest schema (`additionalProperties: false`; allowed list in the docs file). No gate checks this.
- Before a version bump: detail / marketing copy goes in `README.md`, never in a manifest description; **drag-drop test in Cowork before release** (CLI validate passing ≠ Cowork passing); a new failure that Cowork enforces and the schema does not → add the rule to this file and a check to `.github/workflows/ci.yml` in the same change.
- On a "Plugin validation failed": read the earlier lessons with `git log --grep="validator"` before changing anything.

## Repo

- README links every skill name to its SKILL.md (CI #11b). CHANGELOG gets an entry for every minor/major bump.
- Every PR passes the CI gate (`.github/workflows/ci.yml`) before merge.
- CI #27 (v4 gates) runs A1 tools pin, A8 skill names + spawn forms, A2 safety floor (`scripts/floor.py --check --require`), A16(a)/(b) shipped-text lint, the A15 design-runner suite, the W9 eval suites + `eval/scenarios/core-4.0/check-freeze.sh`, `test_floor`, `test_ci_wiring`, `test_ux_design_runbooks` and `test_eval_runners`; all required from `plugin.json` major ≥ 4 (`SHODE_REQUIRE_V4=1` rehearses it on 3.x).

## Lazy ≠ Negligent

- YAGNI ladder (dev-gate Step 0) + caveman compression ตัดได้เฉพาะความซับซ้อน/word ที่ยังไม่ต้องใช้
- **ห้ามตัด**: trust-boundary validation · data-loss handling · security control · accessibility (WCAG) · regulation/compliance
- ทางลัดที่ defer → `shortcut(bd:<id>): <reason>; upgrade → <path>` → `grep -rn 'shortcut(bd' .` / `/review --debt`
- Memory-file compress → เก็บ `<file>.full.md` + verify CI gate (push → CI เขียว) เหมือนเดิม
- **Runtime guarantee = generate, don't ship**: the plugin ships only the contract (principle + method). The harness contract must be established on every project entry (`/init` rule 11 → `.shode-house/config.yaml`). A guarantee that must be enforced at runtime → **devops-engineer** (infra/CI-level; app-level → developer) generates a runner that fits the project, following the contract in `references/patterns/durable-agent-runtime.md`, into the **target project repo** (through dev-gate); never ship a generic script in the plugin. No need = no runner (YAGNI), but the contract must exist.

## Budgets · rule conservation · generated tree (v3.17)

- The 4 budget files (`.skill-metadata-budget` · `.preload-budget` · `.agent-core-budget` · `.workflow-scenario-budget`) are measured values and only go down. Never add a budget file or raise a key/grace to get green — cut non-safety text in the same change.
- Deleting or rewording a rule line in a shipped skill/agent needs a `.rule-migrations.json` entry + count pin in `tests/test_rule_migrations.py` (gate = `scripts/rule-conservation.py`). A rule with a `root_only` anchor stays in the root file, not a lazy reference (CI #21).
- `plugins/shode-house/**` = generated — `python3 scripts/pack-team.py --tree plugins/shode-house`; ห้ามแก้มือ (CI #25 `--check`); generated tree = source + footer (the source with plugin-root and `./`/`../` references re-pointed to its knowledge/ copy, plus a resolution footer; no thin adapters); `/ask` = the pinned wrapper
- Shipped surface = tracker-neutral: ห้าม hardcode `bd <verb>` (`tests/test_tracker_neutral.py`); tracker ตาม target project
- skills/agents/commands/output-styles ห้ามพึ่ง `CHANGELOG.md` / `SHODE-HOUSE-MASTER.md` (maintainer history เท่านั้น)
- Frozen probe protocol: ไฟล์ที่ pin ใน `eval/FREEZE.sha256`, `eval/scenarios/core-4.0/FREEZE.sha256` และ `eval/shape-baseline/FREEZE.sha256` ห้ามแก้ (`bash eval/check-freeze.sh`, `bash eval/scenarios/core-4.0/check-freeze.sh`, `bash eval/shape-baseline/check-freeze.sh`)

## Contribution rules (v3.17)

- Before adding a **rule**, a **skill** or a **model profile**, answer its questions in `docs/repo-invariants/budgets-contribution.md`.
- New rule: ห้ามเพิ่ม prompt text เพียงเพราะ "ฟังดูปลอดภัยกว่า". New skill: the default is not to add (20). New model profile: incomplete answers = do not add; a profile never redefines workflow / safety / ownership / domain.
