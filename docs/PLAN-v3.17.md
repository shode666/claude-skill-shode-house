# แผนงาน v3.17 — Multi-Model Prompt & Skill Simplification

> **Baseline**: working tree ของ `main` ณ 2026-09-20 (3.16.2 + uncommitted 160 ไฟล์) — ต้อง commit ให้สะอาดก่อนวัด (Phase 0)
> **ที่มา**: spec "Multi-Model Prompt & Skill Simplification" (ต้นฉบับเขียนเป็น v3.14; ปรับเลขเป็น v3.17 เพราะ repo อยู่ที่ 3.16.2)
> **ประเภท release**: simplification + architecture cleanup — **ไม่ใช่** redesign capability
> 🔴 **หลักการกำกับทั้ง release**: ไม่ถามว่า "ประโยคนี้ลบได้ไหม" แต่ถามว่า "ถ้าประโยคนี้หายไป อะไรที่ *สังเกตได้* ยังคุ้มครองเราอยู่" — ไม่มี eval/CI คุม + ซ้ำกับ canonical owner ⇒ ลบ · คุม failure mode จริง ⇒ เก็บ invariant แล้วย้ายไป scope ที่เล็กที่สุด

Target models รอบแรก: Claude Sonnet / Opus / Fable · OpenAI Astra / GPT-5.6-class. Core ต้องทำงานได้โดย **ไม่รู้ชื่อ model**.

---

## 0. Baseline ที่วัดแล้ว (working tree, static byte)

| Surface | ปัจจุบัน | หมายเหตุ |
|---|---:|---|
| `AGENTS.md` | 5,926 B / 128 บรรทัด | `## Beads Issue Tracker` ซ้ำ 2 รอบ (บรรทัด 51, 107) + Agent Context Profiles + Session Completion |
| `CLAUDE.md` | 21,094 B | header ยังเขียน v3.12.0 (stale); ปน runtime workflow กับ repo invariant |
| `SHODE-HOUSE-MASTER.md` | 10,475 B | ต้องยืนยันว่าไม่มี runtime path ไหนโหลด |
| skill metadata `__total__` | 9,398 B | `.skill-metadata-budget` — format `[WHAT]·[AUDIENCE]·[WHEN]·[TRIGGER]` บังคับ |
| discovery adapter ที่มี "Read … in full … including prerequisite skills" | 24/24 | `plugins/shode-house/skills/*/SKILL.md` |
| SKILL.md ที่มี "refuse without" | 8 | ต้อง classify A–E |
| `dev-gate/SKILL.md` | 22,211 B | tool-matrix แยกแล้ว (uncommitted) |
| `drain/SKILL.md` | 18,614 B | |
| `shode-house-routing/SKILL.md` | 16,883 B | |
| `diagnose/SKILL.md` | 13,376 B | full-investigation แยกแล้ว (uncommitted) |
| `decompose` / `ui-test` / `workflow` | 11,463 / 11,404 / 9,905 B | |
| agent ใหญ่สุด | orchestrator 16,470 · product-manager 14,374 · qa 13,867 · ux 13,319 · architect 12,577 · devops 12,549 · developer 11,995 B | |
| preload budget | orchestrator 25,854 · reviewer/qa 16,160 · ที่เหลือ ~14.3–14.6 KB | `.preload-budget` |

> ตัวเลขเป็น **static byte** เท่านั้น. ตาม PLAN-v3.13: byte ลด ≠ usage ลด. หลักฐานสุดท้ายคือ eval behavior + usage report จาก run จริง.

---

## 1. ขอบเขต

**ทำ**: ลด always-on context · ลด rule ซ้ำ · skill root เป็น thin router · description สั้นเชิง semantic · decision boundary แทน "refuse without" · completion contract ชัด · model calibration แบบ thin delta · cross-model eval matrix

**ไม่ทำ (non-goals)**: ไม่ถอด Beads · ไม่ลด/ควบ agent (19 คงเดิม) · ไม่ merge reviewer · ไม่เปลี่ยน domain ownership · ไม่ rewrite domain knowledge · ไม่เพิ่ม orchestrator framework · ไม่ optimize เพื่อ model เดียว · ไม่บังคับ byte target ตายตัว · ไม่ถอด validation/security gate · ไม่ loosen CI budget เพื่อให้เขียว

**คงไว้ห้ามแตะความหมาย**: R0/R1/R2 · NO MAGIC · VERIFY BEFORE DONE · DISSENT · SCOPE CONTROL · redact-before-paste · reviewer independence (Dave ≠ Chris ≠ Quinn ≠ Sentinel ≠ Uma) · review 2 แกน Standards/Spec · artifact-passing handoff (path + conclusion) · Lazy ≠ Negligent carve-outs · response language rule

---

## 2. Instruction layers (เป้า)

| Layer | เนื้อหา | Canonical owner |
|---|---|---|
| 1 Universal core | NO MAGIC, VERIFY, DISSENT, SCOPE, R0/R1/R2, authority precedence, secret handling, language, handoff contract | `shode-house-discipline` + repo instructions |
| 2 Role | owns / does-not-own / unique judgment / skill pointers / completion responsibility | `agents/<role>.md` |
| 3 Skill | root = goal + invariant + major exclusion + routing + completion boundary; depth อยู่ใน reference | `skills/<bucket>/<name>/` |
| 4 Model calibration | delta ที่ eval พิสูจน์แล้วเท่านั้น — ไม่มี workflow/safety/ownership | `references/model-profiles/` |

Ownership map (ใช้ตอน dedup — เก็บเป็นตารางใน `docs/enforcement-map.md` ที่มีอยู่ ไม่สร้างไฟล์ใหม่):

| Rule | Owner |
|---|---|
| R0/R1/R2, language, handoff, evidence integrity | `shode-house-discipline` |
| ใครเป็นเจ้าของงาน / domain trigger / parallelization | `shode-house-routing` |
| completion + report format | `shode-house-deliverable` |
| review criteria | `review-checklist` |
| lifecycle Plan→Execute→Verify→Triage | `shode-house-workflow` |
| UI validation | `ui-test` |
| tracker commands | `.agents/skills/beads` + `docs/bd-quickstart.md` |

---

## 3. Phases

ทำทีละ phase, 1 phase = 1 bd + commit แยก. หลังทุก phase: CI gate เขียว · `make pack` ผ่าน · regression fixture ที่เกี่ยวข้องผ่าน · บันทึก byte delta.

### Phase 0 — Baseline & clean tree
- จัดการ uncommitted 160 ไฟล์: review → commit เป็นชุดตามเรื่อง (diagnose/dev-gate split, hooks, tests, docs/evidence) หรือ stash ส่วนที่ไม่เกี่ยว
- แก้ header `CLAUDE.md` ให้ตรง version จริง
- รัน test ที่มี (`tests/*.sh`, `tests/test_*.py`, `test_drain_template.mjs`), CI gate, `make pack`
- บันทึก `.baseline-3.16.2.json`: metadata bytes, preload bytes, agent core bytes, AGENTS/CLAUDE size, top skill sizes
- **Exit**: tree clean · baseline artifact commit แล้ว · ทุก gate เขียว

### Phase 1 — Skill metadata
- ถอดกฎ 4-section description ออกจาก `CLAUDE.md` + CI validator
- เขียน description ใหม่ทุก shipped skill + adapter: 1–2 ประโยค ตอบ "capability อะไร / ใช้เมื่อไหร่" โดยเน้น **decision boundary** ให้ overlap ต่ำ (diagnose = unresolved failure · dev-gate = implementation/refactor validation · incident = active production impact · secure = security boundary · data-migration = DDL/backfill ไม่ใช่ทุก SQL · api-contract = shared/public interface)
- ยังไม่แตะ workflow body (แยก variable ของ routing change)
- ratchet `.skill-metadata-budget` ลงตามค่าจริง (เป้าเริ่ม `< 6,000 B`)
- **Verify**: `eval/fixtures/triggers.yaml` + `routing.yaml` ผ่าน — เฝ้า under-triggering (Risk 2)

### Phase 2 — AGENTS.md
- ลบ Beads block ที่ซ้ำ; ย้าย Dolt internals / sync / profiles / session-completion sequence / command reference ไป `.agents/skills/beads/SKILL.md` + `docs/bd-quickstart.md`
- เหลือ: Authority · Task Tracking (pointer) · Safety (no commit/push/destructive โดยไม่ authorized) · Validation (affected checks, iterate โดยไม่ขออนุมัติทุกรอบ) · Shell (non-interactive)
- เป้า ≤ 2–3 KB โดยไม่เสียความชัด
- ⚠️ Beads block เป็น managed block ของ `bd` — ตรวจว่า `bd` จะ regenerate กลับมาไหม ถ้าใช่ต้องปิด/ตั้งค่า minimal profile
- **Verify**: Codex/AGENTS-style onboarding ยังใช้ `bd` ได้ถูก

### Phase 3 — Discovery adapters
- แก้ generator (`scripts/pack-team.py`) ไม่ใช่แก้มือ 24 ไฟล์: "Read … in full … including prerequisite skills" → "Use the referenced skill as the workflow entry point. Follow only branches applicable to the current task. Load additional references lazily when the root skill directs."
- adapter ถือแค่: name · short description · canonical path · host authority · source-root mapping
- เพิ่ม CI check: ห้าม unconditional "read in full" ใน adapter
- **Verify**: `test_team_package.py` + pack + discovery tests

### Phase 4 — Large skills → thin router
ลำดับ: `dev-gate` → `shode-house-routing` → `diagnose` → `drain` → `ui-test` → `shode-house-workflow` → `shode-house-drift` → `decompose`. **ทีละ skill**, หลังแต่ละตัวรัน routing + skill fixture + วัด loaded context (root อย่างเดียว vs root+reference ต่อ branch).

| Skill | Root เก็บ | แตกเป็น reference |
|---|---|---|
| dev-gate | preserve behavior, YAGNI, security/data carve-outs, test changed behavior, validate before handoff, routing | `tdd` · `refactor` · `quality` · (`tool-matrix` มีแล้ว) · language → ใช้ `references/languages` ไม่ copy |
| routing | งานประเภทไหน / ใคร own / ต้อง domain ไหม / parallel ได้ไหม | `ownership` (roster/RACI) · `domain-routing` · `parallelization` · `trust-levels` · `conflict-resolution` |
| diagnose | objective evidence, inspect-before-guess, symptom≠root cause, validate after fix, redact; incident แยก | `fast-path` · (`full-investigation` มีแล้ว) · `performance` · `distributed` |
| drain | eligibility + do-not-use (dependent/same files/unresolved design/prod degraded), isolation/approval invariant | `worktree` · `integration` · `completion` |
| ui-test | เมื่อไหร่ต้องใช้ + evidence ที่ต้องได้ | `accessibility` · `interaction` · `visual` · `design-tokens` · `browser-evidence` |
| workflow / drift / decompose | lifecycle ระดับสูง / detection | tracker+host detail · recovery logic โหลดเมื่อ drift เกิดจริง |

กฎ split (กัน Risk 5 — context fragmentation):
- root ต้องพอให้ **ไม่ทำสิ่ง unsafe** แม้ไม่มี reference ไหนโหลดเลย
- reference = ข้อมูลที่ใช้เฉพาะบาง branch; ห้าม "root ว่าง + reference ถือ mandatory rule ทั้งหมด"
- ย้าย body แบบ verbatim ก่อน แล้วค่อย simplify เป็น commit แยก (regression เทียบกับ tag ได้ เหมือนที่ทำกับ diagnose)
- จำนวนไฟล์ในตารางเป็น *เพดาน* ไม่ใช่เป้า — branch ไหนเล็กพอให้อยู่ใน root ต่อ (ห้าม over-split)

### Phase 5 — Decision boundaries
- grep: `refuse without` · `ห้าม proceed` · `STOP` · `ask user` · `confirm before`
- classify ทุกจุด: **A** safety · **B** ownership · **C** required external decision · **D** derivable implementation detail · **E** legacy guardrail → เก็บ A/B/C, rework D/E
- แทนด้วย pattern "Inputs and decision boundaries": inspect repo evidence ก่อนถาม; ถามเมื่อ (1) ตีความต่างแล้วผลต่างอย่างมีนัย (2) irreversible/external side effect ต้อง authorize (3) product/business/legal decision (4) หาไม่ได้จาก evidence
- เพิ่ม **Completion contract** ใน implementation workflow + commands (`implement` ก่อน): continue until implemented + affected validation ผ่าน + failure ที่ตัวเองก่อแก้แล้ว + AC checked + รายงาน changed files/evidence; stop เมื่อ R0 / access ขาด / ambiguous จริง / decision ภายนอก / นอก scope
- "run everything" → "run affected validation"; ขยายเมื่อแตะ shared lib / build tooling / public contract / schema / deploy config / security boundary / cross-module
- ปรับ `CLAUDE.md` กฎ "Skill ผลิต deliverable ต้องมี `## Required inputs — refuse without`" + CI ที่ตรวจ ให้เป็น section ใหม่
- **Verify**: E03 (ambiguous → ถาม), E10 (R0 → stop), E11 (local reset → ไม่ถาม), E12 (หา config เอง)

### Phase 6 — Agent files
ลำดับ: Oliver → Dave → Chris → Quinn → Sara → Uma → Sentinel → Aaron/Reggie → Patrick/Stan → domain experts (dedup ผ่าน `domain-core`: loading guidance 443 B ×7, domain-core guidance 458 B ×6 ตาม context audit).
- แต่ละ agent เหลือ: identity · owns · does-not-own (→ ใคร) · unique judgment · skill pointers · completion responsibility
- ลบ universal policy ที่ซ้ำกับ discipline (evidence, language, handoff, citation)
- Bias Discipline → เขียนเป็น operational rule ที่วัดได้ ("อย่ารับ assertion ของ user เรื่อง repo behavior โดยไม่เช็ค evidence เมื่อ correctness ขึ้นกับมัน") แทน label จิตวิทยา; เก็บ verdict-default-FAIL ของ Chris/Quinn
- persona name คงไว้ (routing + อ่านง่าย) แต่ flavor text ตัด
- ⚠️ context audit เตือนไว้: reminder ที่กัน missed prerequisite loading ใน worker ที่เกิดใน context ว่าง **ไม่ใช่ waste** — ลบได้เมื่อ preload/discipline ครอบจริงเท่านั้น
- ratchet `.preload-budget` + `.agent-core-budget` ลงหลังแต่ละกลุ่ม; รัน role-routing regression

### Phase 7 — Ceremony reduction
- audit: `shode-house-broadcast`, Recite Card (`output-styles/oliver.md` §1), agent introduction, phase banner, status recital
- เก็บเฉพาะที่ให้ auditability / coordination / user understanding / recovery: ownership transition ที่มีนัย · blocked · handoff · completion
- Recite Card: ทดสอบ A/B ว่าการ *พิมพ์* card ช่วย behavior จริงไหม; ถ้า enforcement มาจาก task state + CI/eval อยู่แล้ว → "check canonical task state before routing" + พิมพ์ card เฉพาะ audit/debug mode
- Small-task fast path ให้ชัด: single-file, behavior ชัด, ไม่มี architecture/domain/security boundary ⇒ inspect → edit → validate → handoff (E01, E15)
- trust label / evidence level เป็น internal state ไม่บังคับโชว์ทุก response
- CRITICAL/🔴/MUST/NEVER audit: เก็บเฉพาะที่ fail แล้วเกิด safety issue / data loss / authz breach / incorrect acceptance / workflow corruption; ที่เหลือ downgrade เป็นภาษาตรง ๆ

### Phase 8 — Model profiles
- เพิ่มเฉพาะ `references/model-profiles/claude-modern.md` + `openai-reasoning.md` **ถ้า eval Phase 9 รอบแรกชี้ว่าจำเป็น**; `base` ให้ไปอยู่ใน discipline (ไม่สร้างไฟล์ถ้า universal)
- profile ถือแค่ calibration: clarification tendency · tool-trigger sensitivity · test breadth · delegation tendency · action bias — ห้ามซ้ำ NO MAGIC / R0 / review ownership / TDD / migration / API compat
- เลือก profile ผ่าน host/config (เช่น `SHODE_MODEL_PROFILE`) — ห้ามให้ agent เดาว่าตัวเองเป็น model อะไร; unknown model → core only
- override รายตัว (opus/fable/astra) เพิ่มได้เมื่อ: fail ซ้ำ · แก้ที่ core แล้วกระทบ model อื่น · override แก้ได้ · regression เขียว · เล็กกว่า duplicate workflow; ทุก override ต้องถอดได้และ re-eval ต่อ model generation
- tool portability: skill พูดเป็น capability ("search repository", "run affected test") → host mapping อยู่ที่ adapter/`HOST-NOTES.md` ไม่ฝัง `if Claude … if GPT …` ใน skill

### Phase 9 — Cross-model eval
- ต่อยอด `eval/` ที่มีอยู่ (scenarios/golden/fixtures + `team-run-check.py`) — ไม่สร้าง harness ใหม่; fixture assert **observable behavior** เท่านั้น (skills selected, `must_not_load`, `ask_user`, `requires_r0`, files touched, validation run, artifact produced) ห้าม assert reasoning step
- 15 core scenarios: E01 typo fix · E02 reproducible bug · E03 ambiguous product behavior · E04 Java backend (ไม่โหลด UI) · E05 UI change · E06 schema migration · E07 SQL query only (ไม่โหลด data-migration) · E08 API breaking change · E09 production outage → incident · E10 dangerous DB command → R0 · E11 local disposable DB reset → R2 ไม่ถาม · E12 missing config → search ก่อน · E13 Chris review อิสระ · E14 Quinn verify อิสระ · E15 small task ไม่มี PEV ceremony
- matrix: Sonnet · Opus · Fable · Astra · GPT-5.6 → `PASS / FAIL / FLAKY / UNSUPPORTED`; model ที่ CI เข้าไม่ถึงบันทึก manual แยก
- Claude runs: script `claude -p --plugin-dir` ใน `outputs/` รันบน Mac; OpenAI runs ผ่าน Codex host — **ยังไม่มี run path ที่พิสูจน์แล้ว ต้องกำหนดก่อนเริ่ม phase**
- compatibility test: ถอด model profile ออก → fixture ต้องยังผ่าน
- metrics ต่อ model: completion · skill selection accuracy · unnecessary loads · context bytes loaded · tool calls · unnecessary clarification · validation correctness · scope/safety violation · review independence · completion without intervention

### Phase 10 — CI & budget ratchet
- CI เพิ่ม/ปรับ: description length cap (แทน 4-section check) · adapter target exists · no unconditional read-in-full · packaged knowledge == source · broken skill reference
- ratchet ทุก budget ลงตามค่าจริงหลัง validated reduction เท่านั้น
- **ไม่เพิ่ม** `.runtime-context-budget` / `.skill-root-budget` / duplicate-rule detector เว้นแต่มี failure จริงที่ต้องคุม (ห้ามสร้าง process เพื่อ track process)
- `CLAUDE.md`: ย้าย runtime workflow detail เข้า skill เหลือ maintainer invariant (packaging, folder, CI constraint, budget ratchet, release rule, Cowork validator constraints คงไว้ทั้งหมด)
- README: เพิ่ม `## Model Support` + อธิบาย Core / Roles / Skills / References / Model calibration / Evals แบบสั้น
- CHANGELOG entry · `SHODE-HOUSE-MASTER.md` ระบุชัดว่า maintainer/historical ไม่ใช่ runtime dependency
- ก่อน release: drag-drop ทดสอบ Cowork จริง (กฎเดิม)

---

## 4. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Over-simplification — ลบ instruction ที่เคยกัน failure | ระบุ failure mode ก่อนลบ → มี eval คุม → ลบ duplicate ก่อน capability |
| 2 | Skill under-triggering จาก description สั้น | semantic routing eval; เขียน scope boundary ไม่ใช่ keyword dictionary |
| 3 | Agent over-autonomy หลังผ่อน stop rule | R0/R1/R2 + authority + scope control + external side-effect boundary คงเดิม |
| 4 | Model-specific regression | cross-model matrix + thin profile |
| 5 | Context fragmentation จากการ split เกิน | root ถือ invariant; test scenario ที่ reference ไม่ถูกโหลด |
| 6 | งานซ้อนกับ dirty tree / `bd` regenerate managed block | Phase 0 เคลียร์ก่อน; ตรวจพฤติกรรม `bd` ใน Phase 2 |

---

## 5. Completion criteria

```
[ ] AGENTS.md ไม่มี Beads guidance ซ้ำ เหลือเฉพาะ repo-wide instruction
[ ] ถอดกฎ 4-section description; metadata total ลดลงอย่างมีนัย
[ ] adapter ไม่บังคับ full-skill read
[ ] dev-gate / routing / diagnose / drain root เป็น thin router; ui-test ใช้ progressive disclosure
[ ] "refuse without" ทุกจุดถูก classify; detail ที่ derive ได้ไม่ทำให้ถาม user
[ ] R0/R1/R2 ครบเหมือนเดิม
[ ] implementation workflow + implement command มี completion contract
[ ] agent file เหลือ role-specific เป็นหลัก; universal rule ซ้ำลดลง
[ ] reviewer independence · domain ownership · artifact handoff ครบ
[ ] model profile มีเฉพาะที่ eval พิสูจน์; base workflow ผ่านโดยไม่มี profile
[ ] eval suite ผ่าน: Sonnet · Opus · Fable · Astra · GPT-5.6-class
[ ] make pack + Cowork drag-drop ผ่าน · CI เขียว
[ ] ทุก context budget ≤ baseline
[ ] ไม่มี safety regression
```

## 6. กฎสำหรับ contribution หลัง release

- **Rule ใหม่** ต้องตอบ: กัน failure อะไร · canonical owner ที่ไหน · ต้อง always-on ไหม · เป็น lazy reference ได้ไหม · มี eval ไหม
- **Skill ใหม่**: เป็น capability ที่ reuse ได้จริงไหม · skill เดิม + ≤ 1 branch/reference รองรับได้ไหม · discovery ยัง unambiguous ไหม
- **Model profile ใหม่**: eval ไหน fail · model family ไหน · สม่ำเสมอแค่ไหน · ทำไม core wording แก้ไม่ได้ · override ที่เล็กที่สุดคืออะไร

## 7. Decisions (user, 2026-09-20) — รายละเอียดเต็ม `outputs/shode-house-8ss/00-oliver-decisions.md`

1. Phase 0 — commit dirty tree **ทั้งหมด** เป็น 3.16.x ต่อ (themed commits บน main)
2. Phase 9 — OpenAI run path = Codex CLI `codex` บน Mac, manual record; model ID ระบุตอนรัน
3. Phase 7 — Recite Card: A/B ไม่ชี้ชัด ⇒ **คงไว้**
4. Skill: ไม่เพิ่ม; รวม 24 → 20 (meeting→ask · evidence→discipline · broadcast→discipline refs · drift→workflow); ไม่มี stub, `git rm`
5. Tracker ตาม project ปลายทาง — shipped surface ห้าม hardcode `bd` (FR-T-1, wording only)
6. Tracking: epic `shode-house-8ss` (52 tickets) · spec/ADR/review/test plan ใน `outputs/shode-house-8ss/`
