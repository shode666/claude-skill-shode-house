# ADOPT — mattpocock/skills → apply เข้า skill ที่มีอยู่ (ไม่สร้าง skill ใหม่)

> Source: https://github.com/mattpocock/skills (MIT, Matt Pocock) — 37 skills
> Scope: **ปิด gap ใน 23 SKILL.md ที่มีอยู่** ไม่เพิ่ม skill ใหม่ ไม่เพิ่ม command ไม่เพิ่ม agent
> Baseline ที่วัด: shode-house skills 4,452 บรรทัด / 23 ไฟล์ · `diagnose` 87 · `dev-gate` 374 · `review-checklist` 259 · `discipline` 219 · `drain` 182
> หมายเหตุ: `diagnose` เครดิต mattpocock ไว้แล้วตั้งแต่ v2.x — รอบนี้คือ **deepen** ไม่ใช่ port ใหม่

---

## สรุปลำดับความคุ้ม

| # | Target file | Source | Gap ที่ปิด | Effort |
|---|---|---|---|---|
| 1 | `workflow/diagnose` | `diagnosing-bugs` | ไม่มี feedback loop / ไม่มี minimise / hypothesis ไม่ falsifiable / debug log ไม่มีกลไกเก็บ | M |
| 2 | `discipline/review-checklist` | `code-review` | **ไม่มี Spec axis** + diff range ลอย | M |
| 3 | `discipline/shode-house-discipline` § Clarifying | `grilling` | batch 3-7 ไม่มีเกณฑ์เลือกคำถาม + ไม่มีเงื่อนไขจบ | S |
| 4 | `workflow/dev-gate` | `tdd` + `codebase-design` | seam ไม่ได้ตกลงล่วงหน้า · tautological test · horizontal slicing | M |
| 5 | `ops/drain` | `resolving-merge-conflicts` | cherry-pick conflict = พฤติกรรมไม่กำหนด | S |
| 6 | ทุก SKILL.md + `CLAUDE.md` | `writing-for-agents` | negation-heavy · sprawl · cache ของ environment | L (ต่อเนื่อง) |
| 7 | `evidence` · `dev-gate` · `incident`/`init` | `research` · `prototype` · `wizard` | primary source · prototype exit · human-only steps | S |

---

## 1. `skills/workflow/diagnose` ← `engineering/diagnosing-bugs`

**จุดอ่อนปัจจุบัน**: Step 1 = "Reproduce" (บอกให้ทำ ไม่ได้บอกว่าทำยังไงตอนทำไม่ได้), ไม่มี minimise, hypothesis "2-3 ข้อ" ไม่มีรูปแบบ, "ลบ log หลังเสร็จ" ไม่มีกลไก

### 1.1 เปลี่ยน Step 1 → **Build a tight feedback loop** (นี่คือหัวใจ ที่เหลือ mechanical)

เพิ่มบันไดวิธีสร้าง loop เรียงตามลำดับที่ควรลอง:
failing test ที่ seam → curl/HTTP script → CLI + fixture diff snapshot → headless browser (Playwright) → **replay captured trace** → **throwaway harness** (subset ระบบ + mock dep) → property/fuzz loop 1000 input → **bisect harness** (`git bisect run`) → **differential loop** (old vs new diff output) → HITL bash script (ทางเลือกสุดท้าย)

เพิ่ม leading word 2 คำ ซึ่งเปลี่ยน gate ลอย ๆ ให้เป็น state ที่สังเกตได้:
- **tight** = เร็ว (วินาที) + deterministic (pin time, seed RNG, freeze network) + signal คม (assert อาการจริง ไม่ใช่ "ไม่ crash")
- **red-capable** = loop วิ่งผ่าน code path ของ bug จริง และ assert **อาการที่ user บอก** → แดงได้ตอนนี้ เขียวได้หลัง fix

### 1.2 Completion criterion ของ Step 1 (🔴 ตรงกับ VERIFY BEFORE DONE)

> ห้ามขึ้น Step 2 จนกว่าจะระบุได้ว่า **command เดียว** คืออะไร, **รันไปแล้วอย่างน้อย 1 ครั้ง**, และ paste invocation + output (redacted)
> เช็ค: red-capable ✓ deterministic ✓ เร็ว ✓ agent รันเองได้ ✓
> **ถ้าจับได้ว่ากำลังอ่าน code เพื่อสร้างทฤษฎีก่อนมี command นี้ → STOP** — นี่คือ failure mode ที่ skill นี้มีไว้กัน

ทำไมสำคัญกับเรา: ตอนนี้ "VERIFY BEFORE DONE" เป็นคำขวัญที่ enforce ตอน hand-off. อันนี้ทำให้มัน enforce **ตั้งแต่นาทีแรกของการ debug**

### 1.3 เพิ่ม **Minimise** (ตอนนี้ไม่มีเลย)

พอ loop แดงแล้ว → ตัด input/caller/config/data/step **ทีละอย่าง** re-run ทุกครั้ง เก็บเฉพาะที่ load-bearing
จบเมื่อ: ตัดอะไรออกอีกก็เขียว
ได้ 2 อย่าง: hypothesis space เล็กลงใน Step 3 + ได้ regression test สะอาดใน Step 4 ฟรี

### 1.4 Hypothesis ต้อง falsifiable + ranked ก่อนทดสอบข้อแรก

```
สร้าง 3-5 ข้อ เรียงอันดับ ก่อนทดสอบข้อใดข้อหนึ่ง (single hypothesis = anchoring bias)
รูปแบบบังคับ: "ถ้า <X> เป็นสาเหตุ แล้ว <เปลี่ยน Y> จะทำให้ bug หาย / <เปลี่ยน Z> จะทำให้แย่ลง"
เขียน prediction ไม่ได้ = vibe ไม่ใช่ hypothesis → ทิ้งหรือลับให้คม
แสดง ranked list ให้ user ก่อนทดสอบ (user มัก re-rank ได้ทันที: "เพิ่ง deploy ข้อ 3") — ไม่ block ถ้า user AFK
```
เข้ากับ `## Bias Discipline` ที่ฝังใน 19 agents อยู่แล้ว (anchoring)

### 1.5 Non-deterministic bug: เป้าคือ **เพิ่ม reproduction rate** ไม่ใช่หา repro สะอาด

ปัจจุบันเขียนแค่ "flaky = treat as bug". เปลี่ยนเป็น: loop trigger 100× · parallelise · stress · แคบ timing window · inject sleep — bug 50% flake debug ได้, 1% ไม่ได้ → ดันอัตราขึ้นจนกว่าจะ debug ได้

### 1.6 Tagged instrumentation (แก้ปัญหาที่ Universal Rule ห้ามไว้แต่ไม่มีกลไก)

```
ทุก debug log ต้องมี prefix เฉพาะ: [DEBUG-a4f2]
cleanup = grep prefix เดียว → log ที่ไม่ tag คือ log ที่รอด, log ที่ tag คือ log ที่ตาย
tool preference: debugger/REPL (1 breakpoint ชนะ 10 log) > targeted log ที่ boundary > ห้าม "log ทุกอย่างแล้ว grep"
probe 1 ตัว = 1 prediction จาก Step 3, เปลี่ยนทีละตัวแปร
```
> Perf branch: สำหรับ perf regression **log มักผิดทาง** — ตั้ง baseline measurement (timing harness / profiler / query plan) ก่อน แล้ว bisect. วัดก่อน แก้ทีหลัง

### 1.7 "ไม่มี seam ที่ถูกต้อง = นั่นแหละคือ finding"

เขียน regression test ก่อน fix **เฉพาะเมื่อมี seam ที่ถูก** (test ต้องเจอ bug pattern จริงอย่างที่มันเกิดที่ call site)
ถ้า seam ตื้นเกินไป → **บันทึกว่า architecture กันไม่ให้ล็อค bug ตัวนี้ได้** แล้ว route ต่อ (Sara/Stan) — ห้ามเขียน test ที่ให้ false confidence
ต่อตรงเข้ากับตาราง Loop Routing ของ `review-checklist`

### 1.8 Redact (🔴 ช่องรั่วที่มีอยู่จริง)

`shode-house-evidence` บังคับ paste tool output เป็นหลักฐาน แต่ **ไม่มีกฎ redact** → log/HAR/curl มี auth header, token, PII
เพิ่ม: เขียน `<REDACTED>` แทนความลับก่อน paste เสมอ · build loop ผ่าน env var ไม่ให้ credential โผล่ในสิ่งที่ paste · captured artifact ให้ quote เฉพาะบรรทัดที่มี signal · ถ้า redact แล้วข้อมูลไม่พอวินิจฉัย → บอก user ตรง ๆ แล้วขอ

---

## 2. `skills/discipline/review-checklist` ← `engineering/code-review`

### 2.1 🔴 เพิ่ม **Spec axis** (gap ใหญ่สุดของ review ตอนนี้)

Chris 7-dim + Quinn 6-axis = **standards axis ล้วน**. ไม่มีใครถูกสั่งให้เทียบ diff ↔ spec อย่างเป็นระบบ
ตาราง Loop Routing มี "Spec / AC gap → Phase 1a" แต่ไม่มี step ไหนผลิต finding ประเภทนั้น

```
Spec axis รายงาน 3 อย่าง (quote บรรทัดของ spec ทุก finding):
(a) requirement ที่ spec ขอ แต่ขาด/ทำครึ่งเดียว
(b) behaviour ใน diff ที่ spec ไม่ได้ขอ  ← scope creep, ตรงกับ Philosophy #4 SCOPE DRIFT
(c) requirement ที่ดูเหมือนทำแล้ว แต่ implement ผิด
ไม่มี spec → sub-agent ข้าม + รายงาน "no spec available" (ไม่ใช่ pass เงียบ)
```
**ทำไมต้องแยกแกน**: code ที่ตาม standard ครบแต่ทำผิดเรื่อง = Standards pass / Spec fail. รายงานรวมกัน = แกนหนึ่งบังอีกแกน
→ **aggregate แล้วห้าม merge/rerank ข้ามแกน** ปิดท้ายด้วย 1 บรรทัด: จำนวน finding ต่อแกน + ตัวแย่สุด **ในแต่ละแกน** (ห้ามเลือกผู้ชนะข้ามแกน)

นี่คือฟันของ Anti-Puppet Gate ที่ยังขาด

### 2.2 Pin the fixed point (เพิ่มใน § Required inputs)

```bash
git rev-parse <fixed-point>              # ref ใช้ได้จริงไหม
git diff <fixed-point>...HEAD            # three-dot = เทียบกับ merge-base
git log <fixed-point>..HEAD --oneline    # commit list ส่งเข้า sub-agent
```
ref พังหรือ diff ว่าง → **fail ตรงนี้ ก่อน fan-out** ไม่ใช่ไปตายใน sub-agent 2 ตัว
ปัจจุบัน `/review` รับ path / Jira ID / bug description — ไม่มี diff range → ขอบเขต review ลอย

### 2.3 Fowler smell baseline — ให้ dim 5 Maintainability มีคำศัพท์

dim 5 ตอนนี้เป็น judgment ลอย. ใส่ชุดคำที่ชี้ได้ (จาก _Refactoring_ ch.3) ในรูป *มันคืออะไร → แก้ยังไง*:
Mysterious Name · Duplicated Code · Feature Envy · Data Clumps · Primitive Obsession · Repeated Switches · Shotgun Surgery · Divergent Change · Speculative Generality · Message Chains · Middle Man · Refused Bequest

2 กฎที่มาคู่กัน (สำคัญกว่าตัวรายการ):
- **repo standard ชนะ baseline เสมอ** — ที่ repo รับรอง ให้ระงับ smell
- **เป็น judgement call เสมอ** — ป้ายว่า "possible Feature Envy" ไม่ใช่ hard violation
- **ข้ามทุกอย่างที่ tooling ตรวจแล้ว** ← กัน Chris ไปรีวิวซ้ำ Gate 1-10 ของ dev-gate (token ซ้ำซ้อนที่วัดได้)

---

## 3. `discipline/shode-house-discipline` § Clarifying ← `productivity/grilling`

**จุดอ่อน**: "Batch 3-7 คำถามรอบเดียว" ไม่ได้บอกว่า **เลือก 7 ข้อไหน** → agent ถามคำถามที่คำตอบขึ้นกับคำถามอื่นที่ยังไม่ได้ตอบ + ไม่มีเงื่อนไขจบ

เพิ่ม 3 อย่าง (ยาวรวม ~8 บรรทัด):

1. **design tree + frontier** — ทุก decision แตกเป็น decision ที่ห้อยอยู่ใต้มัน. **frontier** = decision ที่ prerequisite settled แล้วทั้งหมด = คำถามที่ถามได้ *ตอนนี้* โดยไม่ต้องเดาคำตอบที่ยังไม่ได้ยิน. ถามทั้ง frontier ในรอบเดียว → รอคำตอบ → คำตอบ reshape tree → คำนวณ frontier ใหม่ → รอบถัดไป
   > คำถามที่คำตอบขึ้นกับคำถามที่ยังเปิดอยู่ในรอบนี้ = **ของรอบถัดไป ไม่ใช่รอบนี้**
2. **fact เป็นงานของ agent เสมอ ไม่ใช่ของ user** — frontier ข้อไหนต้องใช้ fact จาก environment → dispatch sub-agent ไปหา **แล้วไม่ block**: sub-agent ที่ยังวิ่งอยู่ = prerequisite ที่ยัง unsettled → เฉพาะคำถามที่อยู่ใต้มันที่รอ, ที่เหลือถามเลย
   (ของเดิมมี "ตอบเองได้จาก code → อ่านเอง อย่าถาม" แล้ว — ที่เพิ่มคือ *ไม่หยุดรอ*)
3. **เงื่อนไขจบ** — จบเมื่อ **frontier ว่าง**: ทุกกิ่งของ tree ถูกเยี่ยม ไม่มีอะไรถูก assume เงียบ ๆ. **ห้ามลงมือจนกว่า user ยืนยันว่าเข้าใจตรงกัน**
4. เล็กน้อย: ➡️ **recommended answer ทุกข้อ** (ของเดิม recommend เฉพาะ option แรก)

---

## 4. `skills/workflow/dev-gate` ← `engineering/tdd` + `codebase-design`

### 4.1 Seam ต้องตกลงก่อนเขียน test (🔴 คุ้มสุดในหมวดนี้)

> เขียน test ไม่ได้จนกว่าจะ list **seam ที่จะ test** แล้ว confirm กับ user/spec. ไม่มี test ตัวไหนเขียนที่ seam ที่ยังไม่ confirm
> เหตุผล: test ทุกอย่างไม่ได้ → ตกลง seam ล่วงหน้าคือวิธีให้แรงเทสต์ลงที่ critical path + logic ซับซ้อน แทนที่จะกระจายทุก edge case
> ถามตรง ๆ: "public interface คืออะไร แล้วจะ test ที่ seam ไหน?"

แก้ปัญหาที่ Gate 8 มีอยู่: `coverage ≥ 80%` บอกว่า test **เยอะพอ** ไม่ได้บอกว่า test **ถูกที่**

### 4.2 เพิ่ม 3 anti-pattern ใน Part 1 (ตอนนี้มีแต่ "mock business logic ห้าม")

- **Implementation-coupled** — mock collaborator ภายใน / test private method / verify ผ่านช่องข้าง (query DB แทนใช้ interface). สัญญาณ: refactor แล้ว test แตก ทั้งที่ behavior ไม่เปลี่ยน
- **Tautological** — assertion คำนวณค่าคาดหวังด้วยวิธีเดียวกับ code (`expect(add(a,b)).toBe(a+b)`, snapshot ที่ derive มาแบบเดียวกัน) → ผ่านโดยโครงสร้าง ไม่มีวันเถียงกับ code ได้. **ค่าคาดหวังต้องมาจากแหล่งอิสระ**: literal ที่รู้ว่าถูก, worked example, spec
  > อันนี้คือเหตุผลที่ coverage 80% เขียวตลอดกาลโดยไม่จับอะไรเลย
- **Horizontal slicing** — เขียน test ทั้งชุดก่อน แล้วค่อย implement ทั้งชุด → test ที่ตรวจ behavior *ในจินตนาการ*, ล็อค test structure ก่อนเข้าใจ implementation
  → แทนด้วย **vertical slice**: 1 test → 1 implementation → ทำซ้ำ, แต่ละ test คือ **tracer bullet** ที่ตอบสนองสิ่งที่รอบก่อนสอน

### 4.3 ตัดสินใจเรื่อง Refactor ให้ชัด

mattpocock: **refactor ไม่ใช่ส่วนหนึ่งของ loop** — ย้ายไป review stage
shode-house: มี step 3 Refactor ใน loop **และ** Chris review dim 5 → ทำสองรอบ ไม่มีที่ไหนบอกว่าใครตัดสิน
→ ไม่ต้องลอกตาม แต่ **ต้องเลือกจุดยืนแล้วเขียนให้ตรงกันทั้ง `dev-gate` และ `review-checklist`**

### 4.4 Gate 0 ← `codebase-design` vocabulary

Gate 0 มี SOLID + cohesion + readable แต่ **ไม่มีเกณฑ์ตัดสินว่า "abstraction นี้ควรมีอยู่ไหม"** — ซึ่งคือคำถามที่ YAGNI ladder ถามพอดี. เพิ่ม 4 อย่าง:

- **Deep vs shallow** — deep = behaviour เยอะหลัง interface เล็ก; shallow = interface ซับซ้อนพอ ๆ กับ implementation (หลีกเลี่ยง). ถาม: ลดจำนวน method ได้ไหม? ลด parameter ได้ไหม? ซ่อนความซับซ้อนเพิ่มได้ไหม?
- **The deletion test** — ลบ module นี้ทิ้ง: ถ้าความซับซ้อนหายไป = มันเป็น pass-through (ลบจริง); ถ้าความซับซ้อนโผล่ที่ caller N ที่ = มันคุ้มค่าตัว
- **1 adapter = seam สมมติ · 2 adapters = seam จริง** — ห้ามสร้าง seam ถ้าไม่มีอะไรแปรผันข้ามมันจริง (= Speculative Generality ในตาราง smell ของข้อ 2.3)
- **interface คือ test surface** — caller กับ test ข้าม seam เดียวกัน. อยากเทสต์ *เลย* interface เข้าไป = module รูปร่างผิด
> ศัพท์ชุดนี้ยังใช้เป็นภาษากลางระหว่าง Dave ↔ Chris ↔ Sara/Stan (แก้ปัญหา dim 3 SOLID & Design ที่เถียงกันด้วยคำคนละชุด)

### 4.5 ผูก test naming เข้ากับ domain language

`tdd` และ `diagnosing-bugs` ทั้งคู่เปิดด้วย "อ่าน CONTEXT.md ก่อน เพื่อให้ชื่อ test และศัพท์ interface ตรงภาษาของ project + เคารพ ADR ในบริเวณที่แตะ"
เรามี CODEMAP/glossary + ADR อยู่แล้ว → เพิ่ม 1 บรรทัดใน Part 1 ก่อน Red step

---

## 5. `skills/ops/drain` ← `engineering/resolving-merge-conflicts`

Flow มี `git cherry-pick <sha>` serial แต่ **ไม่มีบรรทัดไหนบอกว่าทำอย่างไรตอน conflict** — `When NOT to use` บอกแค่ให้ group by file-locality เพื่อ*เลี่ยง*. เจอจริงเมื่อไหร่ = พฤติกรรมไม่กำหนด = จุดที่ run พังเงียบ

เพิ่มเป็น **Invariant #9** + protocol 5 บรรทัดใน Step cherry-pick:

```
1. ดู state จริงของ merge/rebase + ไฟล์ที่ conflict
2. หา primary source ของแต่ละ hunk — commit message + bd id ของ *ทั้งสองฝั่ง*; เข้าใจ intent เดิมก่อนตัดสิน
3. resolve ทุก hunk: เก็บ intent ทั้งคู่ถ้าเป็นไปได้; ขัดกันจริง → เลือกฝั่งที่ตรงเป้าของ merge + note trade-off
   ห้ามคิด behaviour ใหม่ระหว่าง resolve · **resolve เสมอ ห้าม --abort**
4. รัน fast-gate ของ project (typecheck → test → format) แก้สิ่งที่ merge ทำพัง
5. stage + commit ให้จบ; ถ้า rebase ทำต่อจนครบทุก commit
```
"ห้าม `--abort`" สำคัญเป็นพิเศษกับ drain: abort = ทิ้งงานของ worktree agent ที่ผ่าน TDD มาแล้ว → stale-open bd ซึ่งเป็น failure mode ที่ skill นี้ตั้งมาแก้

---

## 6. Meta — `productivity/writing-for-agents` → apply กับ CLAUDE.md + ทั้ง 23 SKILL.md

**อันนี้คือตัวที่ตรงกับ "ลดจุดด้อยของ plugin" มากที่สุด** เพราะปัญหาของ shode-house เป็นเชิงโครงสร้าง: `shode-house-discipline` โดน ×19 agent ทุกไบต์ (CLAUDE.md เขียนกฎนี้ไว้เอง), `dev-gate` 374 บรรทัดเกิน cap 300 ของตัวเอง, ทุก skill ปิดท้ายด้วยบล็อก `## ห้าม` ยาว

### 6.1 🔴 Negation เป็น failure mode ไม่ใช่ style

> การสั่งด้วยข้อห้ามลาก behaviour ที่ห้ามเข้ามาใน context ทำให้มัน **available มากขึ้น** ไม่ใช่น้อยลง — _อย่านึกถึงช้าง_ แล้วมีแต่ช้าง. คำห้ามเป็น modifier ที่อ่อน ส่วน concept ที่ถูก activate แรงจะกลบมัน จนคำสั่งห้ามอ่านออกมาครึ่งหนึ่งเป็นคำสั่งให้ทำ

นับจริง: `dev-gate` ห้าม 11 ข้อ · `discipline` Universal Rules ห้าม 15 ข้อ · `diagnose` ห้าม 5 ข้อ · `review-checklist` มีบล็อก "ห้าม (consolidated)"
→ **แปลงเป็น positive target**: `ห้าม commit console.log` → `debug log ทุกตัวใส่ prefix [DEBUG-xxxx]; cleanup = grep prefix เดียว` (ข้อ 1.6 ให้ positive form มาแล้ว)
→ เก็บรูปห้ามไว้เฉพาะ **hard guardrail ที่เขียนเป็นบวกไม่ได้** (R0 destructive) และแม้ตอนนั้นก็ **pair กับ positive target เสมอ**

### 6.2 No-op test — ลบทั้งประโยค ไม่ใช่ตัดคำ

คำสั่งที่ model ทำอยู่แล้วโดย default = จ่าย load เพื่อไม่พูดอะไรเลย. เกณฑ์วัดคือ **เทียบกับ default ของ model** (คนสองคนเถียงกันว่าอันไหน no-op = เถียงกันเรื่อง default → ตัดสินด้วยการ *รัน* ไม่ใช่ debate)
เกณฑ์นี้ยังใช้เกรด leading word ด้วย: คำที่อ่อนเกินกว่าจะชนะ default (_be thorough_ กับ agent ที่ thorough อยู่แล้ว) = no-op → แก้ด้วย **คำที่แรงกว่า** (_relentless_) ไม่ใช่เทคนิคอื่น
> ผลตรงกับกฎของเราเอง: "discipline โดน ×19 ทุกไบต์"

### 6.3 Single source of truth vs **cache ของ environment**

environment เป็น source of truth ด้วย (`package.json` scripts, config, layout, `--help`). เอกสารที่ restate มัน = **cache** ซึ่งคุ้มเฉพาะตอน lookup แพง
→ cache สิ่งที่ agent หาเองไม่ได้: convention ที่ไม่ได้เขียนไว้, เหตุผลเบื้องหลังการเลือก, gotcha ที่ไม่มี config ไหนสารภาพ
→ ปล่อย lookup ที่เป็นไฟล์เดียว/คำสั่งเดียวไว้ที่ environment ที่มันเก่าไม่ได้
**เป้าในบ้านเรา**: per-language tool matrix 8 แถว + `.pre-commit-config.yaml` 2 ชุดเต็ม ๆ ใน `dev-gate` — ส่วนใหญ่คือ cache ของสิ่งที่อยู่ใน repo ปลายทางอยู่แล้ว

### 6.4 Information hierarchy + progressive disclosure

3 ชั้น: **in-file step** (สิ่งที่ agent ทำ ตามลำดับ) → **in-file reference** (ปรึกษาเมื่อต้องใช้) → **disclosed reference** (ไฟล์แยก เข้าถึงผ่าน pointer)
เกณฑ์ตัดสินที่สะอาดที่สุดคือ **branch**: inline สิ่งที่ *ทุก* branch ต้องใช้ · push หลัง pointer สิ่งที่ *บาง* branch เท่านั้นที่เอื้อม
> เมื่อเอกสารมี step อยู่ด้วย reference ที่ควรถูก disclose จะ **ฝัง step** จนการใส่ใจ step กลายเป็นการโยนหัวก้อย — เป็น variance lever ไม่ใช่แค่เรื่องอ่านง่าย

**Sprawl** = ยาวเกินไปทั้งที่ทุกบรรทัดยังมีชีวิต → attention เจือจาง. ยาที่ถูกคือบันได ไม่ใช่ตัดเนื้อหา
→ ใช้กับ `dev-gate` (374) : per-language matrix + pre-commit yaml = disclosed reference ชี้ด้วย pointer 1 บรรทัด
→ ใช้กับ cap 300 บรรทัดที่ CLAUDE.md ตั้งไว้: เกณฑ์ควรเป็น "branch ไหนต้องใช้" ไม่ใช่ตัวเลขล้วน

### 6.5 Completion criterion = ชื่อจริงของโรค Anti-Puppet Done

> ทุก step จบที่ **completion criterion**. bound ที่กำกวม ("เข้าใจตรงกันแล้ว") ชวนให้เกิด **premature completion** — จบก่อนเสร็จจริง เพราะ attention ไหลไปที่ *การได้จบ*; step ที่ยังมองเห็นข้างหน้า (**post-completion steps**) คือแรงดึง ส่วนความคมของ criterion คือแรงต้าน
> ป้องกันตามลำดับ: **ลับ bound ให้คมก่อน** (ถูกและ local); เฉพาะเมื่อมันฟัซซี่จริง ๆ *และ* สังเกตเห็นการรีบ ค่อยซ่อน step ข้างหลังด้วยการแยก sequence — และการซ่อนได้ผลเฉพาะเมื่อข้าม **context boundary จริง** (hand-off / subagent dispatch) เท่านั้น การเรียก inline ไม่ได้เคลียร์อะไร
> **Demand**: "ทุก model ที่แก้ถูกนับครบ" บังคับงานละเอียดกว่า "ทำ change list" — และไม่ผูกกับ step: "ใช้ทุกกฎ" มัด reference ที่แบนราบได้เหมือนที่ "ทำครบทุก step" มัดลำดับ
> criterion ที่แข็งแรงที่สุด = **checkable + exhaustive**

ของเรามี context boundary จริงอยู่แล้ว (Handoff Contract + worktree agent) → เครื่องมือครบ ขาดแต่การเขียน criterion ให้คมทีละ step. เทียบ: ข้อ 1.2 คือตัวอย่าง criterion ที่ checkable, `bd close` + `bd show` paste = criterion ที่ exhaustive (M8 ทำถูกอยู่แล้ว)

### 6.6 Leading words — เรามีของดีอยู่แล้ว เทคนิคคือหาที่ยุบ

`NO MAGIC` · `R0/R1/R2` · `caveman` · `drain` · `shortcut(bd:N)` = leading word ที่ใช้ได้ผล
เทคนิค: หา passage ที่กาง triad ไว้ 3 ที่ หรือ pointer ที่ใช้ทั้งประโยคชี้ไอเดียเดียว → ยุบเป็น token เดียว
- "เร็ว + deterministic + overhead ต่ำ" → **tight**
- "loop ที่เชื่อถือได้" → **red** (เปลี่ยน gate ฟัซซี่เป็น state binary ที่สังเกตได้)
> คำที่คิดเองใช้ได้ถ้านิยามชัด แต่ **คำที่แต่งขึ้นไม่ recruit prior** — จ่ายเป็น token นิยามในสิ่งที่คำที่ pretrained ให้ฟรี. หาคำที่มีอยู่แล้วก่อนเสมอ

### 6.7 Context pointer = description ของ skill

4-section format (`[WHAT]/[AUDIENCE]/[WHEN]/[TRIGGER]`) ของเราคือ context pointer ที่ดี แต่ 3 กฎนี้จะทำให้คมขึ้นและถูกลง (ทุกคำของ pointer จ่ายทุก turn):
- **front-load คำนำ** — pointer คือที่ที่มันทำงาน trigger
- **1 trigger ต่อ 1 branch** — synonym ที่เรียก branch เดียวกันซ้ำ = branch เดียวเขียนสองรอบ ยุบทิ้ง
  (ตรวจดู `[TRIGGER]` ของเรา: `diagnose` มี 11 คำ, `meeting` list ชื่อ agent 20 ตัว — หลายตัวเป็น branch เดียวกัน)
- **ตัด identity ที่ body บอกอยู่แล้ว**
- **pointer ที่อ่อนคือ variance bug**: material สำคัญที่อยู่หลัง pointer ที่เขียนอ่อน → ลับถ้อยคำก่อน แล้วค่อย inline ถ้าลับแล้วยังไม่ติด
> **สอง budget**: *context load* (สิ่งที่อยู่ใน window ทุก turn) กับ *cognitive load* (ภาระของคนว่ามีเอกสารอะไรบ้าง). cognitive load ไม่ใช่สิ่งที่ต้อง minimise — มันคือราคาของ human agency: จ่ายตรงที่ต้องใช้วิจารณญาณคน ตัดตรงที่ไม่ต้อง

---

## 7. Patch เล็ก ๆ ที่ใส่ได้เลย

### 7.1 `discipline/shode-house-evidence` ← `engineering/research`
Domain Evidence Protocol บังคับ cite แต่ไม่ได้จัดชั้นแหล่ง → เพิ่ม:
> สืบกับ **primary source** เท่านั้น (official docs, source code, spec, first-party API) ไม่ใช่บทสรุปมือสอง — **ตามทุก claim กลับไปที่แหล่งที่เป็นเจ้าของมัน**
> งานอ่านหนัก → spawn background agent แล้วทำงานอื่นต่อ; ให้มันเขียนไฟล์ Markdown เดียวพร้อม cite ต่อ claim ลงที่ที่ repo เก็บ note แบบนี้อยู่แล้ว

### 7.2 `workflow/dev-gate § When NOT to use` ← `engineering/prototype`
ปัจจุบันเขียนแค่ "spike/prototype ไม่ต้อง TDD" — ไม่ได้บอกว่า prototype **จบยังไง** → code ทดลองไหลเข้า main
เพิ่ม 4 บรรทัด: throwaway ตั้งแต่วันแรกและ**ตั้งชื่อให้คนอ่านผ่าน ๆ รู้ว่าเป็น prototype** · วางไว้ใกล้ที่ที่มันจะถูกใช้จริง · **ไม่มี persistence** (state อยู่ใน memory — persistence คือสิ่งที่ prototype กำลัง*ตรวจ* ไม่ใช่สิ่งที่มันควรพึ่ง) · **แสดง state ทั้งหมดหลังทุก action** · จบแล้ว: พับ decision ที่ validate แล้วเข้า code จริง แล้ว **commit prototype ไว้ throwaway branch นอก main + บันทึก verdict + คำถามที่มันตอบ ลง bd** — main เก็บเฉพาะ decision ที่ผ่านการตรวจ

### 7.3 `ops/incident` · `commands/init` ← `engineering/wizard`
ขั้นตอนที่ **มีแต่คนทำได้** (provision infra, credential, CI secret, third-party dashboard, cutover ครั้งเดียว) → **generate interactive bash wizard** ที่พา user เดินทีละขั้น แทนการ list 12 ข้อให้ทำเอง
ห้าม generate wizard สำหรับขั้นที่ agent ทำเองได้
(`diagnose` ก็ใช้ท่านี้: HITL loop script เป็นทางเลือกสุดท้ายของการสร้าง feedback loop — ข้อ 1.1)

---

## สิ่งที่ **ไม่** เอา

`ask-matt` (= Oliver + `/consult`) · `implement`/`implement-spec` (= `/implement`) · `setup-matt-pocock-skills` (= `/init`) · `retro` (= Postmortem template ใน `shode-house-deliverable`) · `setup-pre-commit` (มี `.pre-commit-config.yaml` แล้ว) · `grill-me`/`grill-with-docs`/`teach`/`to-questionnaire`/`wait-what`/`loop-me` (personal workflow) · `writing-beats|fragments|shape` · `migrate-to-shoehorn`/`scaffold-exercises`/`setup-ts-deep-modules` (ผูก TypeScript/course) · `triage`/`to-tickets`/`to-spec`/`wayfinder` (ผูก GitHub issues — ถ้าจะเอาต้อง port ไป `bd` ก่อน, ยังไม่คุ้มรอบนี้)

## ลำดับลงมือที่แนะนำ

1. **1.2 + 1.3 + 1.8** (`diagnose`: completion criterion + minimise + redact) — เล็ก, ปิดช่องรั่ว secret ทันที
2. **2.1 + 2.2** (`review-checklist`: Spec axis + pin fixed point) — gap ใหญ่สุดเชิงคุณภาพ
3. **3** (`discipline`: frontier + เงื่อนไขจบ) — ~8 บรรทัด กระทบทุก agent
4. **5** (`drain`: conflict protocol) — ~7 บรรทัด กัน run พังเงียบ
5. **4.1 + 4.2** (`dev-gate`: seam + 3 anti-pattern)
6. **6** (writing-for-agents pass ทั้ง repo) — ทำต่อเนื่อง วัดผลด้วย CI gate เดิม

> License: MIT — derive ได้ ใส่ attribution บรรทัดเดียวต่อไฟล์ตามแบบที่ `diagnose` ทำไว้แล้ว
