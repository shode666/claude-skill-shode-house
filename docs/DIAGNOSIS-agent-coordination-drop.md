# Diagnosis — ทำไม agent coordination หลุด (v3.7.0)

> **Verdict**: ไม่ใช่ Claude version. เป็น **architectural defect ที่ verify ได้จาก repo** — discipline layer ไปไม่ถึง subagent เลยแม้แต่ตัวเดียว
> **Date**: 2026-07-20 · **Repo state**: v3.7.0 @ `22a02a2`
> **Method**: repo inspection (file:line evidence) + primary-source research. ทุก claim ด้านล่าง cite ได้

---

## TL;DR

`meeting/SKILL.md:40` เขียนว่า **"ทุก agent ต้องโหลดอย่างน้อย `shode-house-discipline`"**

Agent ทั้ง 19 ตัว **ทำตามคำสั่งนี้ไม่ได้ในทางกายภาพ** — ไม่ใช่ "ทำแล้วลืม" แต่คือ **ไม่มีช่องทางให้ทำ**:

| ช่องทางที่ discipline จะเข้า subagent ได้ | สถานะใน repo |
|---|---|
| `Skill` tool ใน `tools:` frontmatter | ❌ 0/19 (`agents/*.md` ทุกไฟล์) |
| `skills:` frontmatter (preload injection) | ❌ 0/19 |
| `SubagentStart` hook + `additionalContext` | ❌ ไม่มี `hooks/` dir, ไม่มี `hooks` ใน `plugin.json` |
| CLAUDE.md (auto-load เข้า subagent) | ⚠️ โหลดของ **target project** ไม่ใช่ของ plugin repo → ไม่มี discipline |
| Read ไฟล์ SKILL.md เอง | ⚠️ ไม่มีใครบอก path; Bella/Patrick ไม่มี Glob/Grep ด้วยซ้ำ |

→ **subagent context = agent body + delegation prose + target CLAUDE.md เท่านั้น**
Recite Card, 5 Philosophy, evidence protocol, Phase Contract, M1–M7 drift defense — **หายหมดทุกครั้งที่ Task delegate**

---

## Evidence (verifiable)

### E1 — ไม่มี agent ตัวไหนเรียก Skill tool ได้

```
$ grep -H "^tools:" agents/*.md
agents/business-analyst.md:tools: ["Read", "Write", "Edit", "WebSearch"]
agents/developer.md:tools:       ["Read", "Write", "Edit", "Grep", "Glob", "Bash"]
agents/orchestrator.md:tools:    ["Read", "Write", "Edit", "Glob", "Grep", "Task"]
...
$ grep -l '"Skill"' agents/*.md
(none)
```

**19/19 ไม่มี `Skill`** → เรียก `shode-house-discipline` ไม่ได้

### E2 — ไม่มี agent ตัวไหน preload skill

```
$ grep -c "^skills:" agents/*.md | grep -v ":0"
(none)
```

`skills:` frontmatter คือกลไก **inject full content เข้า subagent ตอน startup** (plugin agents รองรับ — ดู plugins-reference). ใช้อยู่ 0 ตัว

### E3 — ไม่มี hook layer

```
$ ls hooks/ ; grep -n "hooks" .claude-plugin/plugin.json
no hooks/ dir
no hooks in plugin.json
```

### E4 — Bella/Patrick หา SKILL.md เองไม่ได้แม้จะอยากทำ

`agents/business-analyst.md:12` → `tools: ["Read", "Write", "Edit", "WebSearch"]`
ไม่มี Glob/Grep/Bash → **discover path ไม่ได้** และ plugin install dir เป็น version string ที่เปลี่ยนทุก update

### E5 — CLAUDE.md ที่โหลดเข้า subagent เป็นของ target project

`CLAUDE.md` ใน repo นี้ = **plugin repo invariants** (skill ≤300 บรรทัด, Cowork validator cap, ฯลฯ) — เป็น maintainer doc ไม่ใช่ runtime discipline. เวลา plugin ไปทำงานใน project อื่น ไฟล์นี้ไม่ตามไป

→ ช่องทางเดียวที่ **การันตี** ว่าถึง subagent ปัจจุบัน **ขนอะไรที่เกี่ยวกับ discipline ไปเลยแม้แต่บรรทัดเดียว**

---

## ทำไมถึงรู้สึกว่า "เพิ่งหลุดช่วงนี้"

Defect นี้มีมาตั้งแต่แตก god-skill เป็น 7 discipline modules (v3.1) แต่ **อาการเพิ่งเด่นขึ้น** เพราะ 3 อย่างซ้อนกัน:

1. **v3.1 refactor ย้าย discipline ออกจาก agent body ไปเป็น skill** — ก่อนหน้านั้น rule ฝังอยู่ใน `meeting/SKILL.md` 1316 บรรทัดที่ main thread โหลด; หลัง refactor กลายเป็น "ให้ agent ไปโหลดเอง" ซึ่งทำไม่ได้ (E1–E3). **นี่คือจุดที่ regression เข้ามา**
2. **Skill count โตขึ้น** — 18 skills, 7 discipline modules ที่ `[AUDIENCE]` เขียน "ทุก agent" + `[WHEN]` เขียน "ก่อน hand-off" เหมือนกันเกือบหมด → description collision, main thread เองก็เลือกผิดบ่อยขึ้น
3. **Model regression จริงมีอยู่ แต่จบไปแล้ว** — Anthropic postmortem 23 เม.ย. 2026 ยืนยัน bug ล้าง thinking history ทุก turn (26 มี.ค.–10 เม.ย., v2.1.101) อาการตรงกับ "ลืม/ทำซ้ำ/เลือก tool แปลก ๆ" **fix แล้วใน v2.1.116 (20 เม.ย.)** — ถ้ายังหลุดหลังจากนั้น = architectural ล้วน

> **Action ก่อนแก้อย่างอื่น**: เช็ค `claude --version` ≥ 2.1.116 เพื่อตัดตัวแปร model layer ออก

---

## ทำไม "สั่งให้ agent ทำตาม" ถึงไม่พอ (แม้ช่องทางจะเปิด)

- **IFScale** (arXiv:2507.11538): instruction-following เสื่อมตาม **จำนวน instruction** ไม่ใช่แค่ token — model ที่ดีที่สุดได้ 68% ที่ 500 instructions, และมี **bias ไปที่ instruction ที่มาก่อน**
- **Context Rot** (Chroma, ก.ค. 2025): distractor = ข้อความ *เกี่ยวข้องแต่ไม่ตอบคำถาม* — "แค่ 1 distractor ก็ลด performance, 4 ตัวยิ่งทบ". 7 discipline modules ที่หน้าตาคล้ายกัน = distractor set ของกันเอง
- **MAST** (arXiv:2503.13657, 7 frameworks, 200+ traces): **41.8%** ของ multi-agent failure = agent ไม่ทำตาม spec/role, **~37%** = inter-agent misalignment + context loss ตอน handoff
- **Anthropic multi-agent writeup**: "instruction สั้น ๆ อย่าง 'research the semiconductor shortage' คลุมเครือพอที่ subagent จะเข้าใจผิดหรือทำงานซ้ำกัน" → subagent ต้องได้ **objective + output format + tool guidance + task boundaries** ทุกครั้ง

**สรุป**: convention (บอกให้ทำ) แพ้ enforcement (inject ให้เลย) — และตอนนี้ shode-house ไม่มีทั้งคู่

---

## Fix (เรียงตาม leverage / effort)

### F1 — `skills:` frontmatter ทุก agent 🔴 **แก้ได้วันนี้ ปิดรูใหญ่สุด**

```yaml
# agents/developer.md
skills: ["shode-house-discipline", "shode-house-evidence", "shode-house-deliverable"]
```

Full content ถูก inject เข้า subagent ตอน startup — ไม่ต้องพึ่งให้ agent "จำได้ว่าต้องโหลด"

Mapping ที่เสนอ (ต่อ role, ไม่เกิน 3 ตัว/agent เพื่อคุม instruction density):

| Agent | skills preload |
|---|---|
| Oliver | discipline, routing, workflow |
| Dave | discipline, evidence, deliverable |
| Chris / Quinn | discipline, evidence, review-checklist |
| Domain (Felix/Iris/Sam/Tara/Elena/Brooke/Emma) | discipline, evidence |
| Bella / Sara / Patrick / Uma / Stan / Aaron / Sentinel / Reggie | discipline, evidence |

⚠️ **Silent failure**: ถ้า skill ที่ list ไว้หาไม่เจอหรือ disabled → Claude Code **ข้ามเงียบ ๆ** log ลง debug เท่านั้น → **ต้องเพิ่ม CI check ว่าทุกชื่อใน `skills:` resolve ได้จริง**

⚠️ `shode-house-drift` (M1–M7) ปัจจุบันเขียนแบบ Oliver-only แต่ M1 Ingress Guard ต้องทำงานที่ทุก agent — ตัดสินใจว่าจะ preload ให้ทุกตัวหรือย่อ M1 เข้า `discipline`

### F2 — Handoff state ลงไฟล์ ไม่ส่งผ่าน prose 🔴

Anthropic เรียก failure นี้ว่า **"game of telephone"** และ fix ด้วย: subagent เขียนงานลง external system แล้วส่งกลับแค่ **reference**

shode-house มี `bd` + `.shode-house/` อยู่แล้ว → ทำให้เป็น **invariant**: Phase artifact ต้องอยู่ในไฟล์, delegation message ส่ง **path** ไม่ส่งเนื้อหา, Oliver synthesize จาก conclusion ไม่ rehydrate transcript

(ตรงกับ #5 ใน `ADOPT-loop-engineering-proposal.md` — แต่ต้องเป็น mechanism ไม่ใช่ prompt rule)

### F3 — Plugin-level `SubagentStart` hook 🟡

⚠️ **ข้อจำกัดสำคัญ**: plugin subagent **ไม่รองรับ** `hooks` / `mcpServers` / `permissionMode` ใน frontmatter — ถูก ignore เงียบ ๆ. ต้องใช้ **plugin-level** `hooks/hooks.json` + `matcher` regex (unanchored → ต้อง anchor เอง: `^shode-house:developer$`)

ใช้ inject Phase Contract state ต่อ agent ผ่าน `hookSpecificOutput.additionalContext` (cap 10,000 chars)

⚠️ **เขียนเป็น factual statement ห้ามเป็น imperative** — ข้อความแบบ "YOU MUST RECITE..." จะไป trigger prompt-injection defense แล้วถูกโชว์ให้ user แทนที่จะเข้า context

### F4 — Structured delegation contract 🟡

`shode-house-workflow` บังคับ template ตอน Task delegate: `objective` · `output format` · `tool/source guidance` · `task boundaries` · `input artifact paths`. ห้าม Oliver improvise prose

### F5 — ลด skill count / de-overlap description 🟡

7 discipline modules `[AUDIENCE] ทุก agent` + `[WHEN] ก่อน hand-off` = เลือกไม่ถูก

**Test ง่าย ๆ**: เอา description 2 อันให้เพื่อนอ่านพร้อม task — ถ้าเพื่อนเลือกไม่ได้ model ก็เลือกไม่ได้
(Anthropic: *"If a human engineer can't definitively say which tool should be used, an AI agent can't be expected to do better"*)

Candidate merge: `broadcast` + `deliverable` (output discipline ทั้งคู่) · `drift` M1 → ย้ายเข้า `discipline`

### F6 — DoD เป็น `SubagentStop` gate + `maxTurns` 🟡

`SubagentStop` exit 2 = **บล็อกไม่ให้ subagent จบ** → Anti-Puppet Done (M3) กลายเป็น mechanism จริง ไม่ใช่ honor system
`maxTurns` frontmatter = bounded execution (ตรงกับ #3 ใน loop-eng proposal) — ใช้อยู่ 0/19

### F7 — Verifier hardening 🟢

**16% ของ 1,968 task ใน 5 terminal-agent benchmark hack ได้จาก task description อย่างเดียว** (arXiv:2606.08960) — วิธี hack ที่พบ: ลบ failing test, monkey-patch verifier

Chris/Quinn "verdict default FAIL" = prompt-layer verifier → **hack ได้เอง**. DoD ต้อง anchor กับ **CI exit code ที่ agent แก้ไม่ได้**
(= #4 reward-hacking guard ใน loop-eng proposal แต่ต้องแรงกว่าที่เสนอไว้)

### F8 — เปิด eval-harness ก่อนแก้ discipline ต่อ 🟢

Anthropic postmortem: system prompt เพิ่ม **2 ประโยค** ทำ intelligence ตก **3%** และรอด "multiple weeks of internal testing + multiple human and automated code reviews + unit tests + e2e + dogfooding"

`skills/in-progress/eval-harness/` = สัญชาตญาณถูก แต่ยัง offline → **ทุก discipline edit ตอนนี้ ship แบบไม่มีการวัด**

---

## Cross-check กับ `ADOPT-loop-engineering-proposal.md`

Proposal เดิม (มิ.ย. 2026) วินิจฉัยถูกหลายข้อ แต่ **ประเมิน #5 ต่ำเกินไป**:

| Proposal | เดิมประเมิน | ประเมินใหม่ |
|---|---|---|
| #5 Sub-agent isolation | "ทำแบบ emergent อยู่แล้ว แค่ยังไม่ใช่ rule" · เสี่ยงต่ำ | ❌ **ผิด** — isolation ทำงาน *แรงเกินไป*: discipline ไม่ผ่านเลย. นี่คือ **root cause อันดับ 1** ไม่ใช่ nice-to-have |
| #4 Reward-hack guard | เสี่ยงต่ำ, prompt fix | ⬆️ ต้อง anchor CI exit code — prompt rule กัน verifier hacking ไม่ได้ |
| #1 Circuit breaker | value สูงสุด | ⬇️ ยังดี แต่รองจาก F1/F2. **หมายเหตุ**: ไม่มี primary source ทางวิชาการ (มาจาก OSS issue tracker) |
| #2 learning-loop | Batch B | คงเดิม — Reflexion "ไม่มีประโยชน์ถ้าไม่มี evaluator ที่เชื่อถือได้" → ต้อง F7 ก่อน |

**ลำดับที่แนะนำใหม่**: F1 → F2 → (วัดผล) → F4/F6 → F5 → F7/F8 → ค่อยกลับไปทำ #1/#2

---

## สิ่งที่ยัง verify ไม่ได้ (ไม่เอาไปใช้ตัดสินใจ)

- **ไม่มี benchmark head-to-head** ระหว่าง "สั่งให้โหลด doc" vs "inject doc" — ทิศทางมีหลักฐานหนุนแน่น แต่ **effect size ไม่มีตัวเลข**
- **ไม่ได้อ่าน transcript ที่หลุดจริง** — session ที่ list ได้ไม่มีอันไหนเป็น shode-house pipeline run ที่ fail. E1–E5 เป็น structural evidence ไม่ใช่ observed failure. **ถ้ามี session ที่หลุดจริง ส่ง session id มา จะ confirm ว่า mechanism ตรงกัน**
- **Claude Code changelog หลัง 20 เม.ย. 2026** ยังไม่ได้ไล่ — ตัด subagent/skill behavior change ใหม่ ๆ ออกไม่ได้ 100%
- **ข่าว "Opus 4.7 regression" จาก third-party** (buildfastwithai, releasebot, gradually.ai) — **ขัดกับ postmortem ของ Anthropic เอง** อย่าเอาไปวางแผน
- **Circuit breaker / no-progress detection** — ไม่เจอ primary academic source

---

## Sources

- [Anthropic — April 23 postmortem](https://www.anthropic.com/engineering/april-23-postmortem)
- [Anthropic — Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Claude Code — Sub-agents](https://code.claude.com/docs/en/sub-agents) · [Hooks](https://code.claude.com/docs/en/hooks) · [Plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Chroma — Context Rot](https://research.trychroma.com/context-rot)
- [IFScale — arXiv:2507.11538](https://arxiv.org/abs/2507.11538) · [MAST — arXiv:2503.13657](https://arxiv.org/abs/2503.13657) · [Verifier hacking — arXiv:2606.08960](https://arxiv.org/abs/2606.08960) · [Reflexion — arXiv:2303.11366](https://arxiv.org/abs/2303.11366)
