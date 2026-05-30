# shode-house — Repo Invariants (v3.3.0)

> รวบรัด. ทุก rule ในที่นี้ = invariant ที่ script ตรวจ. ถ้าจะแหก ต้องเปลี่ยน script ก่อน

## Skills

- จัดใน **bucket folders** ใต้ `skills/`:
  - `workflow/` — daily process (meeting, dev-gate, automate-test, diagnose)
  - `ops/` — operational discipline (incident, slo, secure)
  - `ui/` — frontend quality (ui-test, web-q)
  - `style/` — communication style (caveman)
  - `discipline/` — split discipline modules (shode-house-discipline, -evidence, -routing, -deliverable, -broadcast, -drift, -workflow, review-checklist)
  - `in-progress/` — drafts, **ไม่ ship**
  - `deprecated/` — retiring, **ไม่ ship**
- ทุก skill ใน 5 bucket แรกต้องอยู่ใน `.claude-plugin/plugin.json` skills list + `README.md` index
- `in-progress/` + `deprecated/` ต้อง **ไม่** อยู่
- SKILL.md description ใช้ **4-section format**: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]`
- SKILL.md ขนาด ≤ 300 บรรทัด (≤ 12 KB). เกิน → แตก. Exception: `meeting` (thin entry-point + Recite Card) + `dev-gate` (11 gates + per-language tool matrix justified, ≤ 400)
- Skill ที่ผลิต deliverable ต้องมี: `## When NOT to use` + `## Required inputs — refuse without`

## Commands

- **3-flag rule**: ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag/mode รองรับได้. เกิน 3 flag → ค่อยแตก
- Deprecated command keep เป็น alias 1–2 release window แล้วลบ

## Agents

- ทุก agent reference `shode-house-discipline` (Recite Card) + `shode-house-evidence` ขั้นต่ำ
- `meeting/SKILL.md` = thin entry-point เท่านั้น (≤ 300 บรรทัด)

## Plugin

- `plugin.json` version = SemVer; `marketplace.json` ตาม
- `.plugin` zip artifact = `shode-house-v<MAJOR>.<MINOR>.<PATCH>.plugin`
- Build via `scripts/build-plugin.sh`; ห้าม zip มือ

### Plugin manifest — Cowork validator constraints (🔴 บังคับ — ป้องกัน "Plugin validation failed")

> **History**: v2.5.1 + v3.1.0 เคย fail "Plugin validation failed" ตอน Cowork drag-drop install. CLI `claude plugin validate` ผ่าน + JSON schema ผ่าน **ไม่ได้แปลว่า Cowork ผ่าน** — Cowork validator stricter ที่ runtime

**Hard cap (Cowork enforce, schema ไม่ enforce)**:

- `plugin.json` → `description` **≤ 200 chars, ASCII only** (no em-dash `—`, no Thai, no Unicode quote)
- `marketplace.json` → `description` (top-level) **≤ 200 chars ASCII**
- `marketplace.json` → `plugins[].description` **≤ 100 chars ASCII**
- เกินก็ Cowork ขึ้น "Plugin validation failed" เงียบ ๆ (no specific error message)

**Schema rules (CLI enforce, ทั้ง Cowork + CLI)**:

- `skills` / `commands` / `agents` field = **array of path strings** เท่านั้น (เริ่มด้วย `./`, ห้าม `..`, ห้าม `\`)
  - ❌ **ห้ามใช้ array of objects** เช่น `[{"name": "x", "path": "y", "role": "z"}]` — schema reject
  - ✅ ถูก: `"skills": ["./skills/workflow/", "./skills/ops/"]`
- ถ้าไม่ใส่ field พวกนี้ → loader auto-discover ที่ default path (`skills/`, `commands/`, `agents/`) **1 level deep เท่านั้น**
- Nested structure เช่น `skills/<bucket>/<name>/SKILL.md` ต้องประกาศ bucket paths ใน `skills` field — ไม่งั้น loader หาไม่เจอ
- `additionalProperties: false` — ห้ามเพิ่ม field นอกเหนือจาก schema (`name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `category`, `tags`, `commands`, `agents`, `skills`, `outputStyles`, `hooks`, `mcpServers`, `lspServers`, `settings`)

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
2. ก่อน push: รัน `scripts/check-index.sh` (ต้อง enforce description ≤ 200 chars + ASCII)
3. ก่อน release: **drag-drop ทดสอบ Cowork จริง** — CLI validate ผ่าน ≠ Cowork ผ่าน
4. ถ้า fail: `git log --grep="validator"` ดู lesson learned เก่าก่อน debug ใหม่ — เรามี history v2.5.1 + v3.1.0 แล้ว
5. ถ้าเจอ bug ใหม่ที่ schema ไม่ enforce แต่ Cowork enforce — เพิ่ม rule ในส่วนนี้ + เพิ่ม check ใน `scripts/check-index.sh` ทันที (อย่าให้รุ่นถัดไปลืม)

## Repo

- README → link skill name ไปยัง SKILL.md เสมอ
- CHANGELOG → ทุก minor/major bump เพิ่ม entry
- ทุก PR run `scripts/lint.sh` ผ่านก่อน merge

## Bias Discipline (🆕 v3.3 — replaces v3.2 Evan agent)

- **Embed in agent prompts**: 19 agents มี `## Bias Discipline` section ใน prompt (Chris/Quinn = verdict default FAIL; Felix/Tara/etc. = "ห้าม blindly accept vendor"; Sentinel = hold position on "low risk" if triggers fire)
- **No separate eval agent**: v3.2 Evan = over-engineer for current scale → reverted; eval methodology kept in `skills/in-progress/eval-harness/` (reference only)
- **In-progress harness**: `skills/in-progress/eval-harness/{SKILL.md,fixtures/,run_eval.py}` — keep for future major-release regression (maintainer offline use); ไม่ ship plugin
- **Anti-bias rule source-of-truth**: ในแต่ละ agent prompt + `shode-house-discipline` Recite Card

## PEV Loop (🆕 v3.3 — replaces sprint)

- **Loop**: Plan → Execute → Verify → Triage per bd (no sprint outer loop)
- **No /sprint command**: deleted; Patrick OKR review = continuous (per-bd contribution)
- **No sprint retro**: per-bd reflect in Phase 4 Triage
- **Continuous deploy**: per-bd ready → Aaron deploy (or manual batch optional)
- **Workflow phases unchanged**: 0 Discover → 1a/1b/1c → 2 → 3a/3b → 4 (loop or close)
