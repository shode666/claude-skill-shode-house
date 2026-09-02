# shode-house — Repo Invariants (v3.12.0)

> ทุก rule = invariant ที่ script ตรวจ. จะแหก → แก้ script ก่อน
> หมายเหตุ: ไฟล์นี้ terse อยู่แล้ว → caveman-compress ไม่คุ้ม (วัดแล้ว delta ≈ 0). compress capability ใช้กับ verbose memory file อื่น (project notes) แทน

## ⚙️ Prerequisites (no Python — v3.7)

- **bash + jq** for the CI gate (`.github/workflows/ci.yml`, invariant + lint — runs on GitHub, no local script). `jq`: `brew install jq` / `apt install jq`
- **make** + **zip** for packaging (`make pack`); validation runs in CI
- **git** + **gh CLI** for release/publish (or GitHub Actions)

## Skills

- **bucket folders** ใต้ `skills/`:
  - `workflow/` (meeting, dev-gate, automate-test, diagnose) · `ops/` (incident, slo, secure) · `ui/` (ui-test, web-q) · `style/` (caveman)
  - `workflow/` เพิ่ม data-migration + api-contract (v3.10) + decompose (v3.12)
  - `discipline/` (shode-house-discipline, -evidence, -routing, -deliverable, -broadcast, -drift, -workflow, review-checklist)
  - `in-progress/` + `deprecated/` — **ไม่ ship**
- 5 bucket แรก → ต้องอยู่ใน `.claude-plugin/plugin.json` skills list + `README.md` index
- `in-progress/` + `deprecated/` → **ไม่** อยู่
- SKILL.md description = **4-section format**: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]`
- SKILL.md **≤ 300 บรรทัด** เกิน → แตกเป็น reference file ข้าง ๆ. Exception: `meeting` (thin entry-point) + `dev-gate` (11 gates + per-language matrix) — **ยกเว้นจาก 300 แต่เพดาน 400 บังคับด้วย CI #1** (v3.12). ขนาดเป็น byte ไม่มี cap แยก: skill ที่ถูก preload คุมด้วย budget CI #16 อยู่แล้ว ที่เหลือคุมด้วย line cap (กฎ "≤ 12 KB" เดิมไม่เคยมี CI ตรวจและมี 7 ไฟล์เกินมาตลอด → ถอดออก)
- Skill ผลิต deliverable ต้องมี: `## When NOT to use` + `## Required inputs — refuse without`

## Handoff (🆕 v3.8)

- **Artifact-passing บังคับ**: phase artifact → ไฟล์ (`outputs/<bd-id>/<NN>-<agent>-<phase>.md`); delegation ส่ง **path ไม่ส่งเนื้อหา**; producer return = conclusion + path (ห้าม dump transcript กลับ orchestrator)
- Delegation message ต้องมี **bd-id + artifact paths + phase + iter** เสมอ — sub-agent ไม่เห็น conversation history
- Source-of-truth = `shode-house-discipline § Handoff Contract` (ย้ายมาจาก `shode-house-workflow` v3.10; workflow ไม่มี section นี้แล้ว)

## Language (🆕 v3.8)

- ทุก agent **ตอบภาษาเดียวกับที่ user เขียนมา** — ไม่ fix ไทย/อังกฤษ; เปลี่ยนตาม message ล่าสุด; user สั่งชัดเจน = override ตลอด session
- Verbatim ห้ามแปล: code/path/command/log · Recite Card · tag prefix + handoff line · regulation cite · bd field + phase/gate name
- Source-of-truth = `shode-house-discipline § Response Language`

## Commands

- **3-flag rule**: ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag/mode รองรับได้. เกิน 3 → ค่อยแตก
- Deprecated command keep เป็น alias 1–2 release window แล้วลบ

## Agents

- 🔴 **Redact ก่อน paste** (v3.12) — evidence protocol บังคับ paste command/output/artifact เป็นหลักฐาน ⇒ ต้องเขียน `<REDACTED>` แทน secret/token/auth header/PII **ทุกครั้ง** · build loop ผ่าน env var · captured artifact (HAR/log dump) quote เฉพาะบรรทัดที่มี signal · redact แล้วข้อมูลไม่พอ → บอก user ตรง ๆ ห้ามเดาต่อ. เต็มที่ `diagnose` § Redact
- 🔴 **Review มี 2 แกน** (v3.12) — Standards (Chris 7-dim: *เขียนถูกหลักไหม*) กับ Spec (*ทำตรงกับที่ spec ขอไหม*) เป็นคนละ sub-agent และ **ห้าม merge/rerank ข้ามแกน**; code ที่ standards ผ่านครบแต่ทำผิดเรื่อง = Standards PASS / Spec FAIL. ทุก review ต้อง **pin fixed point** ด้วย `git diff <base>...HEAD` (three-dot) ก่อน fan-out
- 🔴 **Preload budget** (v3.11) — `skills:` cap 3 คุม *จำนวน* แต่ไม่คุม *ขนาด*. ก่อน v3.11 agent จ่าย preload ~10k tok ก่อนอ่าน delegation message ด้วยซ้ำ. กฎ: **skill ที่ถูก preload ต้องเป็นสิ่งที่ *ทุก branch* ใช้** — rule ที่เป็นของบาง role ให้อยู่ใน agent file ของ role นั้น หรือให้โหลดเองด้วย `Skill` tool ตอน runtime. **enforce CI gate check #16** (ratchet เป็น byte: **31,000 B/agent ทุกตัวไม่มีข้อยกเว้น** ตั้งแต่ v3.12 — ขึ้นไม่ได้ ลงได้อย่างเดียว)
- 🔴 **Catalog ≠ Evidence** (v3.11) — `references/design-intel` เป็น *ข้อเสนอ* (palette/pairing/pattern จาก CSV ที่ upstream ระบุเองว่า `derived` / `needs-review`) ส่วน **หลักฐาน** คือ WCAG/axe/Lighthouse/Playwright output เท่านั้น. ขัดกันเมื่อไหร่ **มาตรฐานชนะ catalog**; ห้าม cite ตัวเลขจาก CSV ในระดับเดียวกับ tool output (ผิด UX Evidence Protocol). 0 result → retry แคบลง 1 ครั้ง → ยังว่าง = บอกตรง ๆ ว่าใช้ built-in default. **enforce CI gate check #17** + `check_contrast.py` gate ก่อนเขียน `tokens.json`
- 🔴 **`Skill` บังคับใน `tools:` ทุก agent** (v3.10) — `tools:` ที่ระบุ explicit และ **ไม่มี** `Skill` = subagent โหลด skill ไม่ได้เลย (ไม่ใช่แค่ที่ไม่ได้ preload — *ทั้งหมด*). ก่อน v3.10 เป็น 0/19 → 12 skill ตายอยู่ในไฟล์. `skills:` = preload (inject full content, cap 3); `Skill` ใน `tools:` = โหลดเพิ่มเองตอน runtime. **ต้องมีทั้งคู่** — enforce CI gate check #14
- 🔴 **rule ที่ "ทุก agent ต้องทำตาม" ต้องอยู่ใน `shode-house-discipline`** (ตัวเดียวที่ preload 19/19). rule ที่เป็นของบาง role ห้ามอยู่ที่นี่ — ย้ายไป skill ของ role นั้นแล้วให้เขาโหลดเอง (discipline โดน ×19 ทุกไบต์)

- 🔴 **`skills:` frontmatter บังคับทุก agent** (v3.8) — reference ใน prompt body **ไม่พอ**: sub-agent เกิดใน context ว่าง เห็นแค่ agent body + delegation message + target-project CLAUDE.md. skill ที่ orchestrator โหลดไว้ **ไม่ตามไป**. `skills:` = inject full content ตอน startup (enforcement, ไม่ใช่ convention)
  - ขั้นต่ำ `shode-house-discipline`; ≤ 3 skill/agent (คุม instruction density — IFScale: instruction เยอะ = following เสื่อม)
  - ห้ามชี้ `in-progress/` หรือ `deprecated/` — **Claude Code ข้ามเงียบ ๆ** (debug log เท่านั้น) ไม่ error
  - **enforce**: CI gate check #13
- ทุก agent reference `shode-house-discipline` (Recite Card) + `shode-house-evidence` ขั้นต่ำ
- `meeting/SKILL.md` = thin entry-point เท่านั้น (≤ 300 บรรทัด)
- **Model frontmatter (v3.5)**: ค่าที่อนุญาต = `claude-fable-5` (Stan/Sara/Sentinel/Uma เท่านั้น) | `opus` | `sonnet`. ห้าม pin dated model string. ตาราง model มีที่เดียว = README § Model Strategy (skill อื่นห้าม copy — เคย drift ใน routing skill v2.x). Fallback = settings `fallbackModel`, budget = `CLAUDE_CODE_SUBAGENT_MODEL` (doc ใน README)
- **enforce**: CI gate (`.github/workflows/ci.yml`) ตรวจ model value + Fable-5 whitelist + ห้าม model table นอก README

## Output styles (🆕 v3.10)

- อยู่ที่ `output-styles/<name>.md` (plugin root, default scan path) — **ห้ามใส่ `outputStyles` ใน `plugin.json`** เพราะ field นั้น *replace* default scan และเพิ่มความเสี่ยง Cowork validator
- Frontmatter: `name` + `description` บังคับ (CI #15) · `keep-coding-instructions: true` เก็บ engineering prompt เดิมไว้ · `force-for-plugin: true` = ยึด main session อัตโนมัติทันทีที่ plugin เปิด (override `outputStyle` ของ user)
- Output style แก้ **system prompt ของ main loop เท่านั้น** — subagent มี system prompt ของตัวเอง ไม่ได้รับผลกระทบ
- มีผลหลัง `/clear` หรือ session ใหม่ (อ่านครั้งเดียวตอน startup)
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
- **Dev-loop (bash + jq; python3 เฉพาะ design-intel smoke ใน gate #17 — v3.12)**: invariant + lint gate inline ใน `.github/workflows/ci.yml` (bash + jq, CI-only — no local script) · `make pack` (zip) · `make stats` · `make skills`; publish via `gh` / GitHub Actions

## Lazy ≠ Negligent (🆕 v3.6 — ponytail/caveman adoption)

- YAGNI ladder (dev-gate Step 0) + caveman compression ตัดได้เฉพาะความซับซ้อน/word ที่ยังไม่ต้องใช้
- **ห้ามตัด**: trust-boundary validation · data-loss handling · security control · accessibility (WCAG) · regulation/compliance
- ทางลัดที่ defer → `shortcut(bd:<id>): <reason>; upgrade → <path>` → `grep -rn 'shortcut(bd' .` / `/review --debt`
- Memory-file compress → เก็บ `<file>.full.md` + verify CI gate (push → CI เขียว) เหมือนเดิม
- **Runtime guarantee = generate, don't ship**: plugin ดูแลแค่หลักการ+วิธีการ (contract). Harness contract ต้อง **establish ทุกครั้งที่เข้า project** (`/init` rule 11 → `.shode-house/config.yaml`). guarantee ที่ต้อง enforced runtime (long-run fan-out cap/retry/checkpoint, ฯลฯ) → **Aaron** generate runner **ตาม contract ใน `references/patterns/durable-agent-runtime.md`** (v3.12 — journal/idempotency/replay boundary/version stamp/HITL hash/crash injection; ก่อนหน้านี้ contract ระบุแค่ชื่อ guarantee ไม่ได้บอกว่าต้องมีอะไร Aaron จึงต้องเดา = ผิด NO MAGIC) (infra/CI-level; app-level → Dave) ที่ fit project เข้า **target project repo** (ผ่าน dev-gate); ห้าม ship generic script ใน plugin. ไม่มี need = ไม่ generate (YAGNI) แต่ contract ต้องมี

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
