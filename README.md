# shode-house

> Multi-agent ทีม software house สำเร็จรูป — **19 expert agents in 7 teams** + workflow discipline

ครอบคลุม **ERP, Booking, Trading, Fintech, Insurance, E-commerce, SAP, UX/UI** + polyglot 14 languages

ออกแบบเน้น: **lean • token-optimized • production-ready • domain-driven • zero-overlap capability • ภาษาไทย**

[![Version](https://img.shields.io/badge/version-3.12.1-blue.svg)](https://github.com/shode666/claude-skill-shode-house)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🆕 v3.12.1 — token diet (patch)

**full fan-out 702,788 → 587,398 B (−16.4%)** โดยไม่ตัด safety / evidence / Spec axis / approval gates — ทุกอย่างเป็นการย้ายไป **lazy reference** ไม่ใช่ลบกฎ: `review-checklist` เหลือ orchestration core (7-dim ของ Chris กับ matrix ของ Quinn ซ้ำกับ agent body อยู่แล้ว) · `deliverable` เหลือ Anti-Puppet + 3 reference · skill frontmatter 15.6 → 9.4 KB · แยก runbook ของ Oliver/Uma · `diagnose` ladder lazy · CI #20 ratchet 62 → 50 KB

---

## 🆕 v3.12 — Review มีแกน Spec + debug เริ่มที่ loop + run ที่กู้ได้

**Root cause รอบนี้: discipline ที่บอก "ให้ทำ" แต่ไม่ได้บอก "ทำยังไงถึงจะรู้ว่าจริง"**

- 🎯 **Spec axis ใน `review-checklist`** — Chris 7-dim + Quinn 6-axis เป็น **standards ล้วน** ตอบแค่ "code เขียนถูกหลักไหม" ไม่มีใครตอบ "code ทำในสิ่งที่ spec ขอหรือเปล่า". เพิ่มแกนที่ 2 รันเป็น sub-agent แยก รายงาน (a) requirement ที่ขาด (b) scope creep (c) ดูเหมือนทำแล้วแต่ผิด — **ห้าม merge/rerank ข้ามแกน** เพราะแกนหนึ่งจะบังอีกแกน. บวก **pin fixed point** (`git diff <base>...HEAD` three-dot + verify ก่อน fan-out) เพราะเดิม `/review` รับ path/Jira ID โดยไม่มี diff range
- 🔬 **`diagnose` เริ่มที่ feedback loop ไม่ใช่ "reproduce"** — Step 1 เปลี่ยนเป็นสร้าง loop ที่ **tight** + **red-capable** พร้อมบันได 10 วิธี และ **เงื่อนไขจบที่ตรวจได้**: ต้องมี *คำสั่งเดียว* ที่รันไปแล้วจริง + paste output ก่อนขึ้น step ถัดไป — จับได้ว่ากำลังอ่าน code เพื่อตั้งทฤษฎีก่อนมีคำสั่งนี้ = **STOP**. เพิ่ม **minimise** (เดิมไม่มีเลย), hypothesis 3-5 ข้อแบบ falsifiable + ranked, `[DEBUG-xxxx]` tag ให้ cleanup เป็น grep เดียว, perf branch (วัดก่อนแก้), **"ไม่มี seam ที่ถูกต้อง = นั่นแหละคือ finding"**
- 🔒 **Redact ก่อน paste** — evidence protocol บังคับ paste tool output แต่ไม่เคยมีกฎ redact → log/HAR/curl พก auth header + PII มาด้วย. ตอนนี้เป็น section แรกของ `diagnose`
- 🔐 **Run Durability (`shode-house-workflow`)** — session ของ agent ไม่ durable: **run stamp** (plugin version + model ต่อ run, เดิมไม่มี = reproduce/postmortem ไม่ได้) · **approval ผูก artifact sha** — artifact เปลี่ยนหลัง approve = **approval เป็นโมฆะ** (เดิม approve แล้วแก้ต่อได้เงียบ ๆ) · **resume protocol** สำหรับ session ตายกลาง pipeline (มี notes แต่ไม่มีไฟล์ = ยังไม่เสร็จจริง)
- 📐 **`references/patterns/durable-agent-runtime.md`** — เดิม `CLAUDE.md` สั่งว่า "Aaron generate runner ที่มี retry/checkpoint" โดยไม่มีที่ไหนบอกว่า runner ที่ถูกต้องต้องมีอะไร → Aaron ต้องเดา. ตอนนี้มี contract: journal/step record · replay ที่ไม่รัน side-effect ซ้ำ · idempotency key ที่ tool boundary · version stamp · HITL approval hash · **crash injection test** · platform landscape (Temporal/Inngest/DBOS/Restate) + เกณฑ์ว่าเมื่อไหร่ **ไม่ต้องมี** durable engine
- 🪶 **แตก `shode-house-workflow` 4,716 → 2,399 tok** — Smart Coop Pattern (61% ของไฟล์ ใช้เฉพาะตอนรัน pipeline) ย้ายไป `smart-coop.md`; Handoff Contract ที่ซ้ำกับ discipline ตัดออก. **Oliver ลงมาอยู่ใน budget 31,000 B เท่าทุก agent → CI check #16 ไม่มี exception อีกต่อไป**
- ✂️ **`decompose` skill ใหม่** — epic → leaf task. `shode-house-routing` เขียนกฎ *"XL → split into smaller bd"* ไว้ตั้งนานแต่ **ไม่มี step ไหนทำจริง**: `/design-system` สรุปว่างานเป็น XL 4 module แล้วออกไปเป็น bd ใบเดียว. ตอนนี้มี **tracer bullet** เป็นเกณฑ์ (merge ใบเดียวแล้วต้องมีคนได้อะไร) · เกณฑ์ "เล็กพอหรือยัง" ที่ตรวจได้ · **blocking edge ประกาศตอนสร้าง + create-then-wire 2 pass + `bd ready` verify** · เข้า pipeline เป็น `/design-system` **Step 3.5** และป้อน `drain` ต่อได้ตรง ๆ
- 🗺️ **Map mode** (`shode-house-workflow/wayfinding.md`) — เดิมไม่มีอะไรอยู่ระหว่าง *"ไอเดียก้อนใหญ่ที่ยังมองไม่เห็นทาง"* กับ *"item ที่ `drain` รันได้"*: `/design-system` สมมติว่ารูปงานนิ่งแล้ว จะได้ spec ยักษ์ที่เขียนจากการเดา. ตอนนี้มี **Map + decision ticket** บน `bd` (ticket ที่ผลลัพธ์คือ *การตัดสินใจ*) · **fog of war** (แผนที่ไม่สมบูรณ์โดยตั้งใจ — ticket เมื่อคำถามคม, fog เมื่อยังไม่คม) · **Out of scope section** = ที่บันทึกของ SCOPE DRIFT ที่เดิมเป็นกฎลอย ๆ ไม่มีที่เขียน · ticket type map เข้า agent (research/prototype/grilling/task) · **1 ticket ต่อ session** · เรียก ticket ด้วยชื่อ ห้ามด้วย `bd:42`
- 🧪 **`dev-gate`: seam ต้องตกลงก่อนเขียน test** + 3 anti-pattern (implementation-coupled · **tautological** — assertion ที่คำนวณค่าคาดหวังแบบเดียวกับ code จึงเขียวตลอดกาล · horizontal slicing → vertical slice/tracer bullet) + **deep module** ใน Gate 0 (deletion test · 1 adapter = seam สมมติ 2 = seam จริง)
- 🔀 **`drain` invariant #9 — conflict ต้องมีร่องรอย** — เดิมบอกแค่ "จัดกลุ่มใหม่" ไม่ได้บอกว่า tree ที่ค้างกลางคันไปไว้ไหน. ตอนนี้: `--abort` ปลอดภัยเฉพาะที่ step นี้ (งานอยู่บน `fix/<id>` ครบ) + ตารางเลือกทางด้วยจำนวน item ที่ต้องรันซ้ำ + ถ้า resolve ต้องหา primary source ของทั้งสองฝั่งและแนบ evidence

---

## 🆕 v3.11 — WCAG 2.2 ที่มี check จริง + preload rebalance + Uma มี lookup layer

**Root cause รอบนี้: กฎที่ประกาศไว้แต่ไม่มีเครื่องมือรองรับ + ของที่ทุก agent แบกทั้งที่ใช้ไม่กี่ตัว**

- 🔴 **WCAG 2.2 AA มี criterion จริงแล้ว** — เดิม Uma กับ `ui-test` เขียน "WCAG 2.1/2.2 AA" ไว้ 4 จุด แต่ **ไม่มี success criterion ของ 2.2 อยู่ที่ไหนเลย** และ axe-core ก็ auto-detect ให้ไม่ได้ = claim ที่ไม่มี check รองรับ (ผิด Philosophy #1). เพิ่ม 2.4.11 Focus Not Obscured · 2.5.7 Dragging Movements · 2.5.8 Target Size · 3.3.7 Redundant Entry · 3.3.8 Accessible Authentication พร้อมวิธีตรวจต่อข้อ, บังคับเขียน `N/A: <SC>` ถ้าหน้าจอไม่มีองค์ประกอบนั้น, และ `ui-test` § a11y coverage ระบุชัดว่า **"axe 0 violations ≠ WCAG 2.2 AA ผ่าน"**
- 🪶 **Preload rebalance — 155k → 111k tok ต่อ fan-out 19 agent (-29%)** — v3.10 เปิดให้ agent โหลด skill เองได้ (`Skill` ใน `tools:`) แต่ **เนื้อหา preload ยังไม่ได้ rebalance ตาม** ยังยัดทุกอย่างไว้เหมือนตอนที่โหลดเองไม่ได้. ย้ายของที่เป็นของบาง role ออก: Recite Card (main session เท่านั้น) · Response Language (ตัดส่วน main-session) · No Man-Day → Oliver/Patrick · ตาราง skill-loading → agent file ของตัวเอง (แต่ละตัวเคยแบก row ของอีก 18 role) · UX Evidence → Uma · Domain Evidence → 7 domain expert · REVIEW format → ตัดทิ้ง (`review-checklist` เป็น DRY source-of-truth อยู่แล้ว) · Postmortem → `incident`
  - `shode-house-evidence` 2,253 → **1,079 tok** (-52%) · `shode-house-discipline` 3,763 → **2,803 tok**
  - **CI check #16 preload budget** (ratchet — ขึ้นไม่ได้ ลงได้อย่างเดียว) กันไม่ให้บวมกลับ
- 🐛 **AI Persona Disclaimer preload ผิดกลุ่ม 100%** — กฎอยู่ใน `shode-house-deliverable` ซึ่ง **domain expert ทั้ง 7 ตัวไม่ได้ preload** → กฎไปไม่ถึงกลุ่มเป้าหมาย ขณะที่ 8 agent ที่ไม่ใช่เป้าหมายแบกไว้ทุกครั้ง. ย้ายลง agent file ของ 7 expert แล้ว
- 🎨 **`references/design-intel` — lookup layer ของ Uma (1.2 MB, preload 0 tok)** — Uma Phase 1b สั่งให้ผลิต design token (primitive → semantic → component) แต่เดิม **ไม่มีแหล่งว่าค่าอะไร** → เสกจากหัว model ทุกครั้ง, reproduce ไม่ได้ และผลแปรผันตาม model. vendored subset ของ [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT): 192 palette · 74 font pairing · 119 UX guideline (ครอบ WCAG 2.2) · 88 style · 15 stack · GSAP preset — **ข้อมูลไม่เข้า context เข้าเฉพาะผล query**
  - `check_contrast.py` (เขียนเอง) = gate **catalog → evidence**: palette จาก catalog เป็น *ข้อเสนอ* ยังไม่ใช่หลักฐาน จนกว่าจะผ่าน WCAG. พิสูจน์แล้วว่าจำเป็น — palette ของ catalog เองมี `Border` 1.36:1 ตกเกณฑ์ non-text 3:1 → gate block ถูกต้อง
  - Phase 1b: **stack detection ห้ามเดา** · **design dials** (variance/motion/density) แทนคำถามเปิด "อยากได้แนวไหน" · **MASTER.md + pages/ override** (เดิม `tokens.json` เป็น artifact ราย bd จึง drift ข้าม bd ได้) · `--force` = R0
  - **CI check #17** กัน pack หายเงียบ
- 🧪 **Clarifying → frontier model** (จาก [mattpocock/skills](https://github.com/mattpocock/skills), MIT) — เดิม "batch 3-7 คำถาม" ไม่ได้บอกว่า *เลือก 7 ข้อไหน* → ถามคำถามที่คำตอบขึ้นกับคำถามที่ยังไม่ได้ตอบ. ตอนนี้: design tree → ถามทั้ง frontier รอบเดียว → คำถามที่ขึ้นกับข้อที่ยังเปิด = รอบถัดไป → dispatch sub-agent หา fact แบบไม่ block → **จบเมื่อ frontier ว่าง**

---

## 🆕 v3.10 — Enforcement repair + Oliver takes the main session

**Root cause รอบนี้: rule ที่เขียนไว้ไปไม่ถึง agent ที่ต้องทำตาม** (ต่อจาก v3.8 ที่ยังแก้ไม่หมด)

- 🔴 **19/19 agents ได้ `Skill` ใน `tools:`** — ก่อนหน้านี้ทุก agent ระบุ `tools:` แบบ explicit และไม่มี `Skill` → ตาม [docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) = subagent **โหลด skill ไม่ได้เลย**; 12 จาก 19 skill (dev-gate, secure, slo, incident, ui-test, web-q, diagnose, automate-test, caveman, broadcast, drift, meeting) เข้าไม่ถึง subagent มาตลอด. CI check #14 กันไม่ให้กลับมา
- 🔴 **Tool defect**: Oliver ไม่มี `Bash` ทั้งที่เป็นเจ้าของ `bd ready/update/close`, `bd show` (M8) และ `git worktree` · Bella + Patrick ไม่มี `Grep`/`Glob` ทั้งที่ NO MAGIC บังคับ cite ด้วย Glob/Grep · Stan ไม่มี `Write`/`Edit` ทั้งที่ Handoff Contract บังคับเขียน artifact — แก้ครบ
- 🔴 **ย้าย rule ที่ต้องถึง 19/19 เข้า `shode-house-discipline`**: Handoff Contract (เดิมอยู่ `shode-house-workflow` preload 1/19) · Agent Tag Prefix (เดิม `shode-house-broadcast` preload 0/19) · Close-on-Done M8 · Skill-loading map
- ✍️ **Report Brevity — work deep, report short** (ใหม่, 19/19): artifact ยาวได้ tool output paste ได้ แต่ข้อความที่ส่งกลับต้องสั้น + return format บังคับ ≤ ~15 บรรทัด. ห้าม preamble / narrate ทุก tool call / เล่าซ้ำสิ่งที่อยู่ใน artifact
- 🎭 **`output-styles/oliver.md` (`force-for-plugin: true`)** — Oliver ยึด **main session** ไม่ใช่แค่เป็น subagent. Output style แก้ system prompt ของ main loop โดยตรง และไม่กระทบ subagent (แต่ละตัวมี system prompt ของตัวเอง)
- 📦 **Skill ใหม่**: `data-migration` (expand-contract, batched backfill, rollback drill, ledger append-only, gate `pre-data-migration`) · `api-contract` (breaking vs non-breaking, deprecation window ที่ใช้ metric ไม่ใช่ความรู้สึก, consumer-driven contract test)
- 🛡️ **Prompt-injection section ใน `secure`** — 7 agent ถือ WebFetch/WebSearch แต่เดิม repo ไม่มีคำว่า injection เลย. **ADR lifecycle ใน `deliverable`** — เดิมไม่มี `Superseded by` ทั้ง repo
- 🪶 **Token diet**: `shode-house-discipline` 20,097 → 16,245 B (**-71 KB ต่อ fan-out 19 ตัว**) โดยย้ายของที่ไม่ใช่ของทุกคนออก — Engagement Mode + phase-orchestration → `shode-house-workflow` (Oliver), Universal UX/UI rules → `ui-test` (frontend เท่านั้น), No Man-Day 34→7 บรรทัด, Clarifying 82→17
- 🐛 **แก้ขัดแย้ง**: Recite Card เคยมี 2 เวอร์ชัน (v3.1 ใน `meeting` vs v3.5 ใน `discipline`) ทั้งคู่เขียน "verbatim ห้าม paraphrase" → เหลือ source เดียว · `dev-gate` บอก 7 gates แต่ body มี 11 · 5 commands hardcode "ภาษาไทย" ขัด rule mirror-the-user ของ v3.8 · README อ้าง Phase 7 Learn ที่ลบไปแล้ว + ชื่อ gate ที่ไม่มีจริง · `drift` โฆษณา M1 ที่ย้ายออกไปแล้ว · dead ref `skills/in-progress/` (ไม่ถูก pack) ใน 17 agent

---

## 🆕 v3.9 — Backlog drain + Close-on-Done Guard

**Root cause ที่ปิดในรุ่นนี้: bd ค้าง OPEN ทั้งที่งานเสร็จ** (stale-open) + git race ตอน agent หลายตัวแตะ trunk พร้อมกัน

- **`drain` skill ใหม่** ([`skills/ops/drain/SKILL.md`](skills/ops/drain/SKILL.md)) — เปลี่ยน backlog ที่ **verified แล้ว** N item อิสระ เป็น: 1 worktree-isolated agent ต่อ item (TDD, no push) → **serial cherry-pick** เข้า trunk → 1 fast-gate → 1 push → `bd close` ทุก item พร้อม evidence. 8 invariants (verify-before-done, close-on-done, no-false-close, false-positive honesty, worktree isolation, no-push-in-worktree, scope-lock + no-delete, unit-tests-only-in-parallel)
- **M8 Close-on-Done Guard** (`shode-house-drift`) — งาน land แล้ว → `bd close --reason "<verdict> <sha> <test_result>"` + `bd show` re-confirm CLOSED + **paste output**. "ปิด bd แล้ว" โดยไม่มี `bd show` = anti-puppet violation. `bd list` ไม่นับเป็นหลักฐานสถานะ
- **DoD เพิ่มข้อ bd CLOSED with evidence** (`shode-house-deliverable`) — code merged แต่ bd ยัง OPEN = **ยังไม่ done**
- **`/implement` Phase 4 Triage** — ทุก `bd close` ต้องมี `--reason` + `bd show` verify; batch หลาย bd → route ไป `drain` แทนการรัน `/implement` ซ้ำ
- **CI gate check #11** รู้จัก `drain` (cross-ref resolution)

---

## 🆕 v3.1 — Skill Craft Refactor (9arm-inspired)

**Focused on skill quality + lazy-load + token saving** ขณะที่ keep v3.0 org structure ครบ:

- **Meeting god-skill split** — เดิม `meeting/SKILL.md` = 1316 บรรทัด (everyone loaded). แตกเป็น 7 lazy-load skills ใต้ `skills/discipline/` + meeting เหลือ 180-line thin entry-point + Recite Discipline Card → **86% token reduction** สำหรับ entry context
- **Bucket folder lifecycle** (`workflow/`, `ops/`, `ui/`, `style/`, `discipline/`, `in-progress/`, `deprecated/`) — maturity visible จาก folder; CLAUDE.md invariants บังคับ index integrity
- **Command consolidation** — `/init` รวม `/setup-project` ด้วย `--quick` flag; `/design-system` รวม `/spec-only` ด้วย `--stop --estimate` flags. ลด 8 → 6 commands (+ 2 deprecated alias 1-release window)
- **9arm-inspired skill craft** ทุก SKILL.md:
  - 4-section description format: `[WHAT] · [AUDIENCE] · [WHEN] · [TRIGGER]`
  - `When NOT to use` + `Required inputs — refuse without` gate
  - Skill composition pointer (textual handoff between skills — ลด orchestrator round-trip)
- **`review-checklist` skill (DRY)** — Chris 7-dim + Quinn integration matrix อยู่ที่เดียว; `/implement` Phase 3b + `/review` อ้างที่นี่
- **Recite Discipline Card** — ทุก agent recite 5 Philosophy verbatim ใน first response (anchor against drift)
- **CLAUDE.md repo invariants** + `Makefile` + `.github/workflows/ci.yml` dev-loop (no Python; gate inline in CI: bash + jq)
- **22 skills** (14 functional + 7 discipline modules + 1 review-checklist), **5 commands**, **1 output style** (+ 2 deprecated). v3.3 drops sprint outer loop + Evan agent — **PEV loop per bd** (Plan/Execute/Verify/Triage), bias discipline embedded in 19 agent prompts, Chris/Quinn adversarial vs Dave + visual/interaction evidence mandatory (Playwright เป็นทางหลัก — ดู `review-checklist` § Mandatory Visual Verify). ห้าม man-day negotiation

### v3.0 features ที่ยัง keep

- 4 core agents: Patrick (PM), Stan (Staff Eng), Sentinel (Security Eng), Reggie (SRE)
- 3 phases: 0 Discovery, 1c Threat Model, 6 Operate (Phase 7 Learn ถูกลบใน v3.3 — reflect ย้ายไป Phase 4 Triage)
- 7-team structure + single-owner capability matrix
- Workflow Drift Defense (M1 อยู่ `shode-house-discipline`; M2-M8 อยู่ `shode-house-drift`)
- Handoff Broadcast Protocol (caveman 1-line)
- RACI matrix per phase + Multi-sig pre-deploy-prod gate

---

## 🚀 Install

### Claude Code (CLI/terminal)
```bash
/plugin marketplace add shode666/claude-skill-shode-house
/plugin install shode-house@shode-house
```

### Cowork (desktop app)
- Drag & drop `.plugin` file → Cowork window
- หรือ Settings → Plugins → Install from file

### Update
```bash
/plugin marketplace update shode-house
/plugin install shode-house@shode-house
```

---

## 👥 7 Teams (parallel within, sequential across via phase gate)

| Team | Members | Phase | Deliverable |
|------|---------|-------|-------------|
| 🧭 **Lead** | Oliver + Stan | All | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | 0 | OKR + opportunity + pain validation |
| 📐 **Design** | Bella + Sara + Uma | 1a/1b/3a | BRD + ADR + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | 0/1b/3b | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel) | 1 | Production code (data/ML = Dave interim) |
| ✅ **Verify** | Chris + Quinn + Sentinel | 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | 5/6 | Deploy + SLO + Incident |

**Single-owner capability matrix** — ทุก capability มี sole owner; agent อื่น consult ได้แต่ห้ามผลิต deliverable

---

## 🤖 Agents (19 = 12 core + 7 domain)

### Core (12)
| Key | ชื่อ | Model | Team | Role |
|-----|------|-------|------|------|
| Or | **Oliver** | sonnet | Lead | Engagement Lead — orchestrate, classify follow-up, multi-sig gate |
| St | **Stan** 🆕 | **fable-5** | Lead | Staff Engineer — cross-team consistency, tech radar, polyglot review |
| Pa | **Patrick** 🆕 | sonnet | Discover | Product Manager — OKR, RICE/WSJF, opportunity sizing, kill decision |
| Ba | **Bella** | sonnet | Design | BA — BRD/FRD/AC G-W-T, Event Storming, RTM |
| Sa | **Sara** | **fable-5** | Design | SA — C4, ADR, NFR (threat model → Sentinel) |
| Ux | **Uma** | **fable-5** | Design | UX/UI + Design System + a11y + **Design Authority** — นำ look & feel, advise Sara/Dave/Bella |
| Dv | **Dave** | sonnet | Dev | Polyglot Dev (parallel Dave#N, 14 languages, lazy-load) |
| Cr | **Chris** | sonnet | Verify | Code Review 7-dim + Unit + Mutation kill ≥ 70% |
| Qa | **Quinn** | sonnet | Verify | QA — Integration/E2E/Contract/Load/Perf/axe (pen test → Sentinel) |
| Se | **Sentinel** 🆕 | **fable-5** | Verify | Security Engineer — STRIDE/LINDDUN, SAST/DAST, CSP/Trusted Types, pen test |
| Do | **Aaron** | sonnet | Ops | DevOps/Platform — Docker, CI/CD, IaC (SLO → Reggie) |
| Re | **Reggie** 🆕 | sonnet | Ops | SRE — SLO/SLI, error budget, runbook, on-call, blameless postmortem |

### Domain Experts (7) — Phase 0 active driver in v3.0
| Key | ชื่อ | Model | Domain |
|-----|------|-------|--------|
| Fe | **Felix** | **opus** | Fintech — payment, ledger, ISO 8583/20022, PCI-DSS v4, KYC/AML, BOT |
| Ee | **Elena** | sonnet | ERP/Accounting — GL, AR/AP, MRP, IFRS 15/16, consolidation |
| Sm | **Sam** | **opus** | SAP — ECC + S/4HANA, ABAP, Fiori, BTP, BAPI/IDoc, migration |
| Te | **Tara** | **opus** | Trading — OMS/EMS, matching, FIX, microstructure, clearing |
| Ie | **Iris** | **opus** | Insurance — policy, claim, IFRS 17, reinsurance, OIC |
| Bk | **Brooke** | sonnet | Booking — PMS, channel manager, yield, overbooking, GDS |
| Ec | **Emma** | sonnet | E-commerce — catalog, cart, promo, marketplace, fraud |

### Model Strategy (v3.5 — Claude 5 family)

| Tier | Agents | Frontmatter value | เหตุผล |
|------|--------|-------------------|--------|
| **Fable 5** (4) | Stan, Sara, Sentinel, Uma | `claude-fable-5` | judgment สูงสุด: cross-team architecture + security + **design direction** (Uma = Design Authority นำ look & feel) |
| **Opus** (4) | Felix, Sam, Tara, Iris | `opus` (alias → Opus ล่าสุด) | regulated-domain judgment (money, SAP, trading, insurance reg) |
| **Sonnet** (11) | ที่เหลือทั้งหมด | `sonnet` (alias → Sonnet ล่าสุด) | execution + structured patterns |
| **Haiku** (0 agent) | mechanical sub-task เท่านั้น | Task `model` override | status digest, broadcast aggregation, bd hygiene — ห้ามผลิต deliverable |

> **กติกา**: full string เฉพาะ Fable (ยังไม่มี alias เป็นทางการ); ตัวอื่นใช้ alias เพื่อตาม model ใหม่อัตโนมัติ. **ห้าม pin dated string** (เช่น `claude-sonnet-4-6-2025xxxx`)

**Fallback (กรณีเรียก Fable 5 ไม่ได้ — quota/availability)** — Claude Code รองรับ fallback chain (สูงสุด 3, ครอบคลุม subagent ทุกตัว):

```jsonc
// .claude/settings.json (project) หรือ ~/.claude/settings.json
{ "fallbackModel": "opus,sonnet" }   // fable-5 ล่ม → Opus → Sonnet
```

หรือ per-session: `claude --fallback-model opus,sonnet`

**Budget mode** (บังคับทุก subagent ลง sonnet ชั่วคราว — ไม่ต้องแก้ไฟล์):

```bash
CLAUDE_CODE_SUBAGENT_MODEL=sonnet claude
```

---

## 🧭 5 Core Philosophy

ทุก agent ยึดเป็นอันดับหนึ่ง:

1. **NO MAGIC** — ห้ามเดา. Path/service ไม่รู้ → `Glob`/`Grep` หาก่อน. Assumption explicit + cite evidence
2. **VERIFY BEFORE DONE** — Edit + show test/curl/screenshot. ห้าม "should work"
3. **DISSENT** — ก่อน major change: blast radius / assumption / reversibility / momentum
4. **SCOPE DRIFT** — track stated vs actual. "ทำเพิ่มนิดนึง" = warning
5. **R0/R1/R2** — R0 (irreversible) STOP+ask | R1 (costly) inform+rollback | R2 (easy) just do

---

## ⚡ Slash Commands (5 — v3.5: deprecated aliases removed)

| Command | ใช้เมื่อ |
|---------|----------|
| `/shode-house:consult [คำถาม]` | ปรึกษาด่วน — route ไป agent ตัวเดียว |
| `/shode-house:init [project]` | Init project scaffold — **default**: interactive wizard; `--quick "<stack>"` direct Aaron Docker-first |
| `/shode-house:design-system [feature]` | Smart Spec pipeline — **default**: spec → suggest implement; `--stop`: stop at spec; `--estimate`: add T-shirt sizing; `--stop --estimate` = proposal mode |
| `/shode-house:implement [feature]` | Phase 2-4 — Dave + Uma + Chris ∥ Quinn (uses `review-checklist` skill) |
| `/shode-house:review [path\|jira\|bug]` | Ad-hoc code review (uses `review-checklist` skill) |

> Removed: `/sprint` (v3.3 — PEV loop per bd), `/setup-project` → `/init --quick`, `/spec-only` → `/design-system --stop --estimate` (v3.5 — aliases past deprecation window)

> **3-flag rule** (CLAUDE.md invariant): ห้ามเพิ่ม command ใหม่ถ้า command เดิม + ≤ 3 flag รองรับได้ → prefer flags over command proliferation

---

## 📚 Skills (21 lazy-load — bucket organized v3.1)

### `skills/workflow/` — daily process
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`meeting`](skills/workflow/meeting/SKILL.md) | ALL | **Entry-point** + Recite Discipline Card + index (v3.1 thin) |
| [`dev-gate`](skills/workflow/dev-gate/SKILL.md) | Dave + Chris | TDD red-green-refactor + 7-gate quality |
| [`automate-test`](skills/workflow/automate-test/SKILL.md) | Quinn + Chris + Aaron | CI test pyramid 70/20/10 + threshold |
| [`diagnose`](skills/workflow/diagnose/SKILL.md) | Chris + Quinn + Dave | Bug + perf root cause (4-step) |
| [`data-migration`](skills/workflow/data-migration/SKILL.md) 🆕 | Dave + Aaron + Sara | expand-contract + backfill + rollback drill |
| [`api-contract`](skills/workflow/api-contract/SKILL.md) 🆕 | Dave + Sara + Quinn | semver + deprecation window + consumer contract |
| [`decompose`](skills/workflow/decompose/SKILL.md) 🆕 | Bella + Oliver + Patrick | epic → leaf: tracer bullet + blocking edge + create-then-wire |

### `skills/ops/` — operational discipline
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`incident`](skills/ops/incident/SKILL.md) | Reggie + Oliver | Runbook + on-call + blameless postmortem + 5-why |
| [`slo`](skills/ops/slo/SKILL.md) | Reggie | SLI / SLO / error budget (Google SRE Book) |
| [`secure`](skills/ops/secure/SKILL.md) | Sentinel | STRIDE + LINDDUN + CSP + Trusted Types + SAST/DAST |
| [`drain`](skills/ops/drain/SKILL.md) 🆕 | Oliver + Dave/Chris/Quinn/Aaron/Uma | Verified backlog → parallel worktree → serial merge → close-on-done |

### `skills/ui/` — frontend quality
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`ui-test`](skills/ui/ui-test/SKILL.md) | Quinn + Uma + Dave | Playwright + axe + visual regression |
| [`web-q`](skills/ui/web-q/SKILL.md) | Uma + Dave + Quinn + Aaron + Sentinel | CWV + Lighthouse + SEO + security headers |

### `skills/style/` — communication style
| Skill | Owner | Trigger |
|-------|-------|---------|
| [`caveman`](skills/style/caveman/SKILL.md) | Oliver + ALL | Compressed output mode |

### `skills/discipline/` — v3.1 split modules (from meeting god-skill)
| Skill | Owner | Role |
|-------|-------|------|
| [`shode-house-discipline`](skills/discipline/shode-house-discipline/SKILL.md) 🆕 | ALL (mandatory) | Recite Card + 5 Philosophy + Safety + Universal Rules + Clarifying |
| [`shode-house-evidence`](skills/discipline/shode-house-evidence/SKILL.md) 🆕 | Claimers, Domain experts | Project + UX + Domain Evidence + REVIEW format |
| [`shode-house-routing`](skills/discipline/shode-house-routing/SKILL.md) 🆕 | Oliver | Routing + RACI + T-shirt + Trust Levels + Team v3.0 |
| [`shode-house-deliverable`](skills/discipline/shode-house-deliverable/SKILL.md) 🆕 | Producers | DoD + Anti-Puppet + I Never Do + Postmortem template |
| [`shode-house-broadcast`](skills/discipline/shode-house-broadcast/SKILL.md) 🆕 | ALL | Tag Prefix + Caveman broadcast + Handoff Protocol |
| [`shode-house-workflow`](skills/discipline/shode-house-workflow/SKILL.md) 🆕 | Oliver | Phase Contract + Smart Coop + hooks + gates + worktree |
| [`shode-house-drift`](skills/discipline/shode-house-drift/SKILL.md) 🆕 | Oliver enforcer | Drift Defense M2-M8 + Phase wiring (Discovery/Threat Model/Operate) |
| [`review-checklist`](skills/discipline/review-checklist/SKILL.md) 🆕 | Chris + Quinn + Sentinel + Domain | DRY checklist สำหรับ /implement Phase 3b + /review |

### `skills/in-progress/` + `skills/deprecated/` — not shipped
Skill ที่อยู่นี่จะไม่ถูกใส่ใน plugin.json (CLAUDE.md invariant)

**v3.1 changes**:
- Meeting god-skill (1316 lines) split → 7 discipline modules (avg 200 lines each) + 180-line thin entry
- New `review-checklist` skill — DRY for `/implement` Phase 3b + `/review`
- 9arm-inspired: 4-section description, When-NOT + Required-inputs gate, skill composition pointers
- Bucket folders enforce maturity lifecycle

---

## 🔁 Workflow — PEV Loop per bd (v3.3 — no sprint outer loop)

```
PEV loop per bd-issue (Plan → Execute → Verify → Triage):
  📋 PLAN
  Phase 0  Discovery       Patrick + Domain SME (opt — new initiative)
  Phase 1a Foundation      Bella ∥ Sara (parallel)
  Phase 1b Pre-Design      Uma + Domain (sequential after 1a, conditional)
  Phase 1c Threat Model    Sentinel (parallel-able with 1b, conditional)
  💻 EXECUTE
  Phase 2  Implement       Dave (parallel by scope contract)
  ✅ VERIFY (adversarial — Chris/Quinn vs Dave, zero trust)
  Phase 3a UI Check        Uma POST (sequential gate + Chrome MCP)
  Phase 3b Code Review     Chris ∥ Quinn (verdict default = FAIL + Chrome MCP)
  🚦 TRIAGE
  Phase 4  Triage          Oliver (max iter 3) → bd close + bd show verify (M8) + bd remember
  🚀 DEPLOY (continuous per bd)
  Phase 5  Deploy          Aaron + Reggie
  📡 OPERATE
  Phase 6  Operate         Reggie (SLO, incident)

No Phase 7 / sprint retro — per-bd reflect captured in Phase 4 Triage; continuous OKR review (Patrick)
```

### Phase Gates (RACI-aware + Evidence-mandatory)

10+ standard gates ทุก phase transition: `pre-spec`, `pre-spec-expand`, `pre-implement-ui`, `pre-implement`, `pre-ui-check`, `pre-quality-coop`, `pre-loop-exit`, `pre-deploy-staging/uat/prod`, `pre-data-migration`, `pre-destructive`

**Multi-sig pre-deploy-prod (R0)**:
- Aaron (build) + Reggie (SLO) + Sentinel (security) + Patrick (OKR/risk)

---

## 🤝 Handoff Broadcast Protocol (caveman 1-line)

ทุก phase transition → 1 บรรทัด:

```
Bella ▸ Dave   : impl bd-42
Dave  ▸ Verify : CR + test + sec
Verify ▸ Oliver : 2M 1m
Oliver ▸ Ops   : deploy
Ops    ▸ ✓    : prod stable
```

**Arrow convention**:
- `▸` = handoff broadcast (M3 protocol — formal between agents)
- `→` = general flow/sequence/implication (informal)

---

## 🛡️ Workflow Drift Defense (7 Mechanisms)

แก้ปัญหา agent หลุด workflow ใน warm follow-up — Dave บอก "เสร็จแล้ว" โดยไม่ผ่าน Verify, fix ตรงโดยไม่ผ่าน Phase 1a

| # | Mechanism | What it does |
|---|-----------|-------------|
| M1 | **Ingress Guard** | ทุก agent ก่อน respond: bd show → state → classify → route check |
| M2 | **Follow-up Classifier** | Oliver auto-triage user message (fix/spec/quest/approve/new/status) |
| M3 | **Anti-Puppet "Done"** | Dave/Chris/Quinn/Sentinel/Uma ห้าม claim "done"; only Oliver after multi-sig |
| M4 | **User Comment = FAIL** | feedback ใด ๆ = reopen bd + iter++ |
| M5 | **Spec Change = bd revision** | verbal change ห้าม fix ตรง → Bella revision → Phase 1a redo |
| M6 | **SESSION-STATE.md** | Oliver maintain persistent state; ทุก agent read first |
| M7 | **Direct-to-Agent block** | non-Oliver agents ห้าม accept direct-from-user → route Oliver |

---

## 💬 Clarifying Style

**`AskUserQuestion` ใช้ได้เฉพาะ main session** (`/init`, `/design-system`, `/implement` และ Oliver ที่ยึด main session ผ่าน `output-styles/oliver.md`) — **ไม่ใช่ `orchestrator` subagent**: Claude Code ยังไม่รองรับ tool นี้ใน agent ที่ spawn ผ่าน Task
sub-agent ทุกตัว (รวม Oliver-as-subagent) **return question bundle** ขึ้นไปให้ main session เปิด popup แล้วเขียนคำตอบกลับ tracker. รูปแบบคำถาม option-style:

```
Q: ใช้ database อะไร?
A) PostgreSQL (Recommended — relational + JSON)
B) MySQL (familiar)
C) MongoDB (document)
D) อื่นๆ
```

- 2-4 options + Recommend ตัวแรก + reason 1 บรรทัด
- Batch ≤ 4 คำถามต่อ call → ลด round-trip
- ห้ามคำถามเปิด

6 grill patterns: Stack / Scope / Severity / Auth method / Tracker / Deployment

---

## 🌐 Polyglot Dave — 14 Languages (lazy-load)

Dave อ่าน best practice **เฉพาะภาษาที่ใช้** จาก `references/languages/<lang>.md` → ประหยัด token

**Startup tier**: TypeScript, Python, JavaScript, Go, SQL, Kotlin, Swift, Rust, PHP, Dart
**Enterprise tier**: Java, C#, C++, COBOL/PL-SQL/VBA

---

## 🔌 Bundled MCPs

| MCP | ใช้แทน | ประโยชน์ |
|-----|--------|----------|
| **[Context7](https://context7.com)** | `WebFetch` lib docs | Library docs ตาม version, snippet เป๊ะ — token-saving |

Prerequisite: `brew install node` (Context7 ใช้ npx)

---

## 🧵 Task Tracking — beads (bd)

ทีมใช้ **[beads](https://github.com/steveyegge/beads)** เป็น single source of truth:

```bash
brew install beads
cd your-project && bd init
bd create "FR-101: POST /refund" -t functional-req --blocked-by 1
bd ready --json    # next unblocked
bd graph --format=mermaid    # auto dep diagram
```

RTM (BR → FR → US → ADR → Test → Code) อยู่ใน bd. Markdown artifact save `outputs/` แต่ status = bd

---

## 🏛️ Principles

- **Right answer > first answer** — ห้าม "พอใช้ได้"
- **Evidence-based** — cite version + clause (ISO/IFRS/OWASP/PCI/BOT/OIC)
- **Domain-aware vocabulary**
- **Test before claim "done"** (anti-puppet)
- **Reproducible** — git clone → run = work
- **Money = Decimal** — ห้าม float
- **Lazy-load reference** สำหรับ token-saving
- **Modular** — เพิ่ม/ลด agent ง่าย (drop file + update routing)
- **Zero overlap** — single-owner capability matrix (v3.0)

---

## 📁 Architecture (v3.1 bucket-organized)

```
shode-house/
├── CLAUDE.md                   🆕 v3.1 repo invariants (≤ 30 lines)
├── .claude-plugin/             manifest + marketplace (v3.1.0)
├── Makefile                    🆕 v3.7 dev-loop (no Python): pack/stats/skills
├── .github/workflows/ci.yml    invariant + lint gate (inline bash + jq; CI-only)
├── skills/
│   ├── workflow/               daily process
│   │   ├── meeting/            🔄 v3.1 thin entry-point (180 lines, was 1316)
│   │   ├── dev-gate/           TDD + 7-gate quality
│   │   ├── automate-test/      CI test pyramid 70/20/10
│   │   ├── diagnose/           4-step bug methodology
│   │   ├── data-migration/     🆕 v3.10 expand-contract + rollback drill
│   │   ├── api-contract/       🆕 v3.10 semver + deprecation window
│   │   └── decompose/         🆕 v3.12 epic → leaf (tracer bullet + blocking edge)
│   ├── ops/                    operational discipline
│   │   ├── incident/           runbook + war room + postmortem
│   │   ├── slo/                SLI/SLO/error budget
│   │   ├── secure/             STRIDE + CSP + Trusted Types
│   │   └── drain/              🆕 v3.9 backlog drain + close-on-done
│   ├── ui/                     frontend quality
│   │   ├── ui-test/            Playwright + axe + visual
│   │   └── web-q/              CWV + Lighthouse + SEO + headers
│   ├── style/                  communication
│   │   └── caveman/            compressed output
│   ├── discipline/             🆕 v3.1 split modules + DRY checklist
│   │   ├── shode-house-discipline/   Recite Card + 5 Philosophy + Safety
│   │   ├── shode-house-evidence/     Project + UX + Domain Evidence + REVIEW
│   │   ├── shode-house-routing/      Routing + RACI + T-shirt + Trust
│   │   ├── shode-house-deliverable/  DoD + Anti-Puppet + Postmortem
│   │   ├── shode-house-broadcast/    Tag Prefix + Caveman + Handoff
│   │   ├── shode-house-workflow/     Phase Contract + hooks + gates
│   │   ├── shode-house-drift/        Drift Defense M2-M8
│   │   └── review-checklist/         DRY for /implement Phase 3b + /review
│   ├── in-progress/            not shipped (drafts)
│   └── deprecated/             not shipped (retiring)
├── output-styles/              🆕 v3.10 oliver.md (Oliver ยึด main session)
├── agents/                     19 expert agents (12 core + 7 domain)
├── commands/                   5 active (v3.5 — aliases removed)
└── references/
    ├── design-intel/           🆕 v3.11 Uma lookup layer (data + search.py, preload 0 tok)
    ├── patterns/durable-agent-runtime.md  🆕 v3.12 contract ของ runner ที่ Aaron generate
    ├── modern-stack.md         2025+ tech recommendation
    ├── patterns/general.md     DB/API/Observability (Dave lazy-load)
    └── languages/<14 files>    per-language best practice (Dave lazy-load)
```

---

## 🛡️ Safety Discipline

**Destructive actions** ขออนุญาตเสมอ (R0):
- `git push --force` (main), `git reset --hard`
- `DROP TABLE`, `DELETE without WHERE`
- `rm -rf` กว้าง, delete prod resource
- Edit migration ที่ apply prod แล้ว
- Modify auth/IAM permission

Pattern: ระบุ action + impact + rollback → ขอ confirm → execute

---

## 🤝 Adding/Removing Agent

**Add new domain expert**:
1. Drop `agents/<name>.md` (ตาม 5-Dim Role template)
2. Update Team Routing ใน `agents/orchestrator.md` + Team Structure ใน `skills/workflow/meeting/SKILL.md` + `skills/discipline/shode-house-routing/SKILL.md`
3. Bump version, repackage

**Remove agent**: ลบไฟล์ + remove จาก routing + capability matrix

---

## 🔗 Inspirations

- **Workflow discipline**: [Archon](https://github.com/coleam00/archon) (phase contract + loop + approval gates)
- **Productivity skills**: [mattpocock/skills](https://github.com/mattpocock/skills) (caveman/grill-me concepts)
- **Web quality skills**: [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) (web-q port)
- **SRE discipline**: [Google SRE Book](https://sre.google/books/) (slo + incident port)
- **Tech radar**: Thoughtworks (Stan tech radar pattern)
- **Issue tracker**: [beads](https://github.com/steveyegge/beads)
- **Domain knowledge**: real-world projects (Thai banking, ERP, insurance, hospitality)

---

## 📜 License

MIT — use freely, improve freely, contribute back welcome
