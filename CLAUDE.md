# shode-house — Repo Invariants (v3.7.0)

> ทุก rule = invariant ที่ script ตรวจ. จะแหก → แก้ script ก่อน
> หมายเหตุ: ไฟล์นี้ terse อยู่แล้ว → caveman-compress ไม่คุ้ม (วัดแล้ว delta ≈ 0). compress capability ใช้กับ verbose memory file อื่น (project notes) แทน

## ⚙️ Prerequisites (no Python — v3.7)

- **bash + jq** for the CI gate (`.github/workflows/ci.yml`, invariant + lint — runs on GitHub, no local script). `jq`: `brew install jq` / `apt install jq`
- **make** + **zip** for packaging (`make pack`); validation runs in CI
- **git** + **gh CLI** for release/publish (or GitHub Actions)

## Skills

- **bucket folders** ใต้ `skills/`:
  - `workflow/` (meeting, dev-gate, automate-test, diagnose) · `ops/` (incident, slo, secure) · `ui/` (ui-test, web-q) · `style/` (caveman)
  - `discipline/` (shode-house-discipline, -evidence, -routing, -deliverable, -broadcast, -drift, -workflow, review-checklist)
  - `in-progress/` + `deprecated/` — **ไม่ ship**
- 5 bucket แรก → ต้องอยู่ใน `.claude-plugin/plugin.json` skills list + `README.md` index
- `in-progress/` + `deprecated/` → **ไม่** อยู่
- SKILL.md description = **4-section format**: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]`
- SKILL.md ≤ 300 บรรทัด (≤ 12 KB). เกิน → แตก. Exception: `meeting` (thin entry-point) + `dev-gate` (11 gates + per-language matrix, ≤ 400)
- Skill ผลิต deliverable ต้องมี: `## When NOT to use` + `## Required inputs — refuse without`

## Commands

- **3-flag rule**: ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag/mode รองรับได้. เกิน 3 → ค่อยแตก
- Deprecated command keep เป็น alias 1–2 release window แล้วลบ

## Agents

- ทุก agent reference `shode-house-discipline` (Recite Card) + `shode-house-evidence` ขั้นต่ำ
- `meeting/SKILL.md` = thin entry-point เท่านั้น (≤ 300 บรรทัด)
- **Model frontmatter (v3.5)**: ค่าที่อนุญาต = `claude-fable-5` (Stan/Sara/Sentinel/Uma เท่านั้น) | `opus` | `sonnet`. ห้าม pin dated model string. ตาราง model มีที่เดียว = README § Model Strategy (skill อื่นห้าม copy — เคย drift ใน routing skill v2.x). Fallback = settings `fallbackModel`, budget = `CLAUDE_CODE_SUBAGENT_MODEL` (doc ใน README)
- **enforce**: CI gate (`.github/workflows/ci.yml`) ตรวจ model value + Fable-5 whitelist + ห้าม model table นอก README

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
    {"name": "meeting", "path": "skills/workflow/meeting", "bucket": "workflow", "role": "..."} // object form → schema reject
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
- **Dev-loop (no Python, v3.7)**: invariant + lint gate inline ใน `.github/workflows/ci.yml` (bash + jq, CI-only — no local script) · `make pack` (zip) · `make stats` · `make skills`; publish via `gh` / GitHub Actions

## Lazy ≠ Negligent (🆕 v3.6 — ponytail/caveman adoption)

- YAGNI ladder (dev-gate Step 0) + caveman compression ตัดได้เฉพาะความซับซ้อน/word ที่ยังไม่ต้องใช้
- **ห้ามตัด**: trust-boundary validation · data-loss handling · security control · accessibility (WCAG) · regulation/compliance
- ทางลัดที่ defer → `shortcut(bd:<id>): <reason>; upgrade → <path>` → `grep -rn 'shortcut(bd' .` / `/review --debt`
- Memory-file compress → เก็บ `<file>.full.md` + verify CI gate (push → CI เขียว) เหมือนเดิม
- **Runtime guarantee = generate, don't ship**: plugin ดูแลแค่หลักการ+วิธีการ (contract). Harness contract ต้อง **establish ทุกครั้งที่เข้า project** (`/init` rule 11 → `.shode-house/config.yaml`). guarantee ที่ต้อง enforced runtime (long-run fan-out cap/retry/checkpoint, ฯลฯ) → **Aaron** generate runner (infra/CI-level; app-level → Dave) ที่ fit project เข้า **target project repo** (ผ่าน dev-gate); ห้าม ship generic script ใน plugin. ไม่มี need = ไม่ generate (YAGNI) แต่ contract ต้องมี

## Bias Discipline (🆕 v3.3 — replaces v3.2 Evan agent)

- **Embed in agent prompts**: 19 agents มี `## Bias Discipline` (Chris/Quinn = verdict default FAIL; Felix/Tara = "ห้าม blindly accept vendor"; Sentinel = hold on "low risk" ถ้า trigger)
- **No separate eval agent**: v3.2 Evan = over-engineer → reverted; methodology kept in `skills/in-progress/eval-harness/` (reference only, maintainer offline)
- **In-progress harness**: `skills/in-progress/eval-harness/{SKILL.md,fixtures/}` — agent-orchestrated (Task tool, no script; run_eval.py ลบ v3.6); future major-release regression; ไม่ ship
- **Anti-bias source-of-truth**: agent prompt + `shode-house-discipline` Recite Card

## PEV Loop (🆕 v3.3 — replaces sprint)

- **Loop**: Plan → Execute → Verify → Triage per bd (no sprint outer loop)
- **No /sprint command**: deleted; Patrick OKR review = continuous (per-bd)
- **No sprint retro**: per-bd reflect in Phase 4 Triage
- **Continuous deploy**: per-bd ready → Aaron deploy (or manual batch)
- **Workflow phases unchanged**: 0 Discover → 1a/1b/1c → 2 → 3a/3b → 4 (loop or close)
