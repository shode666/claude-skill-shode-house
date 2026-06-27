# Proposal — Adopt loop-engineering patterns into shode-house

> **Mode**: Proposal only (advisory doc). ยังไม่แตะ skill/plugin/version. ทุก section = gap analysis + diff preview + invariant check ให้ review ก่อน
> **Sources**: [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/) (June 2026, ตั้งชื่อ + anatomy) · [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) (evaluator-optimizer, orchestrator-workers) · [Anthropic — Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [ReAct (Yao 2022)](https://arxiv.org/abs/2210.03629) · [Reflexion (Shinn 2023)](https://arxiv.org/abs/2303.11366) · [Data Science Dojo — 10 Loop Engineering Patterns](https://datasciencedojo.com/blog/loop-engineering-design-patterns/) · [Tosea.ai — Loop Engineering guide](https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026)
> **Target**: shode-house v3.6.5 → **v3.7.0** (proposed minor, 1 batch ถ้า approve ทั้งชุด)
> **Scope**: gap-analysis + 6 candidate adoptions. ยังไม่ลง code — รอ sign-off ทีละ item

---

## TL;DR — loop engineering คืออะไร + shode-house อยู่ตรงไหน

**Loop engineering** = layer ที่ 4 ต่อจาก prompt → context → harness. เลิก hand-prompt, ออกแบบ **loop** ที่ act → observe feedback จริง → decide → repeat จน termination condition ที่ *check ได้* ผ่าน. แกนอยู่ที่ 3 hard parts: **context · termination · verification**.

**ข่าวดี**: shode-house เป็น loop-engineering system อยู่แล้ว แค่เรียกชื่ออื่น. ตารางนี้คือ pattern catalog มาตรฐาน (Ng + Anthropic + production-hardening) แม็พกับของที่มี:

| Pattern (มาตรฐาน) | shode-house มีแล้ว? | ที่ไหน |
|---|---|---|
| ReAct (reason→act→observe) | ✅ | PEV Loop (Plan→Execute→Verify→Triage per bd) |
| Plan-and-Execute | ✅ | Phase 1 (spec) แยกจาก Phase 2 (implement) |
| Orchestrator-Workers | ✅ | Oliver + 19 agents, worktree isolation |
| Ralph Loop (deterministic verifier) | ✅ | dev-gate 11 gates (tests/lint/type = green ก่อน hand-off) |
| Evaluator-Optimizer (critic แยก generator) | ✅ **จุดแข็งสุด** | Chris/Quinn review, verdict **default FAIL** |
| Reflection / Reflexion (memory + self-critique) | 🟡 partial | `skills/in-progress/learning-loop` (gated, ยังไม่ ship) |
| Hallucinated-success defense | ✅ | M3 Anti-Puppet Done + NO MAGIC + evidence protocol |
| Context engineering inside loop | 🟡 partial | caveman + sub-agent structured return (ยังไม่เป็น invariant) |
| **Circuit Breaker (no-progress trip)** | ❌ **gap** | — |
| **Bounded Execution (explicit budget)** | 🟡 implied | "fan-out cap/retry/checkpoint" generate per-project (CLAUDE.md) แต่ไม่ first-class ใน PEV contract |
| **Reward-hacking guard** | 🟡 partial | dev-gate มี verifier แต่ไม่กัน "ลบ test ให้ green" ตรง ๆ |
| **Heartbeat (scheduled/event loop)** | ❌ gap | request-driven 100% |

**สรุป**: shode-house แข็งเรื่อง **verification** (best axis), โอเคเรื่อง **orchestration**, แต่บางเรื่อง **termination/no-progress** + **within-session memory** — ตรงกับ "3 pattern สุดท้ายที่ทีมส่วนใหญ่ข้าม" ที่ research เตือน.

---

## 6 candidate adoptions (เรียงตาม value/effort)

| # | Adopt | แตะไฟล์ (ถ้า approve) | ประเภท | เสี่ยง |
|---|-------|----------------------|--------|--------|
| 1 | Circuit Breaker / no-progress trip | `shode-house-drift` (M8 ใหม่) หรือ `shode-house-workflow` (Phase 4) | prompt | ต่ำ |
| 2 | Promote `learning-loop` (Reflexion buffer) | `skills/in-progress/learning-loop/` → ship gate | skill | กลาง |
| 3 | Bounded Execution = first-class PEV contract | `shode-house-workflow` + CLAUDE.md invariant | prompt+doc | ต่ำ |
| 4 | Reward-hacking guard ใน dev-gate | `dev-gate` Gate 8 + `review-checklist` | prompt | ต่ำ |
| 5 | Sub-agent context isolation = invariant | `shode-house-workflow` + CLAUDE.md | prompt+doc | ต่ำ |
| 6 | Heartbeat loop (scheduled ops) | `slo`/`incident` + new mode (เคารพ 3-flag) | prompt | กลาง |

**Invariant ที่ต้องเคารพตลอด**: skill ≤300 บรรทัด (dev-gate exception ≤400) · 3-flag rule (เลี่ยง command ใหม่) · plugin.json desc ≤200 ASCII · model table อยู่ README ที่เดียว · in-progress/ + deprecated/ ไม่ ship · ทุก bump รัน CI gate + drag-drop Cowork test

---

## #1 — Circuit Breaker / no-progress detection (value สูงสุด)

**แนวคิด (Pattern 8)**: monitor progress signal ทุก iteration (tests passing, files changed, new vs repeated error). ถ้า stuck — error เดิม / state ไม่เปลี่ยน N cycle ติด → **trip**: log state, terminate loop, escalate human. นี่คือสาเหตุ #1 ของ token blowup ที่ research ชี้.

**Gap ปัจจุบัน**: M1–M7 กัน workflow *regression* (drift) แต่ไม่มีตัวจับ *stagnation* ระหว่าง retry. Phase 4 Triage loop หรือ close — ไม่มี exit แบบ "วน dead end".

**Where (เสนอ)**: `shode-house-drift` เพิ่ม **M8 — No-Progress Breaker**:
```
M8 — No-Progress Breaker (🔴 ก่อน loop iteration ถัดไป)
- Progress signal/bd: {tests_passing Δ, files_changed Δ, error_signature}
- Trip condition: error_signature ซ้ำ ≥ 3 cycle  OR  signal ไม่ขยับ ≥ 3 cycle
- On trip: append bd `-t breaker` (full state) → escalate Oliver → user (caveman 1-line)
- ห้าม auto-retry หลัง trip (ต้อง human review เหมือน M3 Anti-Puppet)
```
**Fit**: ขยาย Anti-Puppet (M3) จาก "อ้าง done โดยไม่ verify" → "วนไม่จบโดยไม่ progress". Recoverable (test fail) ต่างจาก fatal (creds หาย) → fatal escalate ทันที, recoverable นับ cycle.

**Invariant check**: drift SKILL.md ปัจจุบันต้องเช็คความยาว — M8 ~25 บรรทัด, ถ้าเกิน 300 ให้ trim M-table verbose แทน. ไม่กระทบ plugin.json.

---

## #2 — Promote `learning-loop` (Reflexion episodic buffer)

**แนวคิด (Reflexion, Shinn 2023)**: Actor + Evaluator + Self-Reflection. หลัง attempt fail เขียน *verbal lesson* ("patch fail เพราะ import ผิด") เข้า episodic buffer ที่ attempt ถัดไปอ่านกลับ → loop เก่งขึ้น *ภายใน session เดียว* โดยไม่ retrain.

**Gap ปัจจุบัน**: `harvest_shortcuts.py` + postmortem เก็บ lesson *ข้าม* bd แต่ไม่มี buffer *ภายใน* retry loop. `skills/in-progress/learning-loop/` ออกแบบไว้แล้ว (hot path = capture บรรทัดเดียว non-blocking; cold path = distill/gate offline) — **ตรงกับ Reflexion เป๊ะ** แต่ยัง unshipped.

**Where (เสนอ)**: bake `learning-loop` ให้ครบ → ship. ขั้นต่ำที่ขาดก่อน promote (ตาม skill's own gate):
- `.shode-house/lessons.md` schema + `bd remember` ที่ Phase 4 (hot path, append-only)
- session_start: load top-N (default 5) caveman-compressed (bounded, กัน context rot)
- eval-harness regression baseline ก่อน promote (ของก็ in-progress เหมือนกัน)

**Fit**: เติม "within-session memory" ที่เป็น gap จริงข้อ 2. ระวัง: skill เตือนเอง — **ห้ามรัน distill/gate ใน hot loop**. promote = human gate, ไม่ auto-ship (สอดคล้อง Bias Discipline + NO MAGIC).

**Invariant check**: ย้ายจาก `in-progress/` → bucket จริง → ต้องเพิ่มใน `plugin.json` skills list + README index + 4-section description + `## When NOT to use` + `## Required inputs` (มีแล้วในไฟล์). = minor bump.

---

## #3 — Bounded Execution = first-class PEV contract

**แนวคิด (Pattern 10)**: cap loop ชัดเจน — max iterations + token budget + wall-clock. ไม่มี ceiling = เจอ ceiling ที่ไม่ได้วางแผน (cost spike / rate limit / timeout).

**Gap ปัจจุบัน**: CLAUDE.md พูดถึง "long-run fan-out cap/retry/checkpoint" แต่เป็น **runtime guarantee ที่ Aaron generate per-project** (ไม่ ship generic script — ถูกต้องตาม YAGNI). ปัญหา: budget ไม่ใช่ส่วนหนึ่งของ **PEV contract** ระดับ orchestration → Oliver ไม่มี ceiling มาตรฐานต่อ bd loop.

**Where (เสนอ)**: `shode-house-workflow` Phase Contract เพิ่ม field (default + override ต่อ T-shirt):
```
PEV budget (ต่อ bd): max_iterations · token_ceiling · wall_clock
- exit = verifier pass (success) OR breaker trip (#1) OR budget exhausted → escalate
- default ผูกกับ T-shirt size (S/M/L) จาก routing
```
**Fit**: รวมกับ #1 (breaker = exit ตัวหนึ่ง). ทำให้ "termination เป็นครึ่งหนึ่งของ design" ตามที่ research ว่า. ไม่ขัด YAGNI — นี่คือ *contract* (หลักการ) ไม่ใช่ generic runner.

**Invariant check**: prompt + CLAUDE.md edit. ไม่กระทบ schema. เพิ่ม 1 บรรทัด invariant ใน CLAUDE.md "PEV budget" section.

---

## #4 — Reward-hacking guard ใน dev-gate

**แนวคิด**: failure mode คลาสสิก — agent ทำ proxy ผ่านแบบไม่ซื่อ: ลบ/skip test, อ่อน assertion, ลบ failing test ให้ CI green. verifier deterministic ดี แต่กันการ *โกง verifier* ไม่ได้เอง.

**Gap ปัจจุบัน**: dev-gate Gate 8 (Test) + coverage ≥ threshold มี แต่ไม่ได้พูดตรง ๆ ว่า "ห้าม coverage/test-count ลดลงเพื่อให้ green". M3 Anti-Puppet + verdict FAIL ช่วย แต่ไม่ระบุ abuse นี้.

**Where (เสนอ)**: dev-gate Gate 8 เพิ่ม rule + `review-checklist` (Chris 7-dim) เพิ่ม check:
```
Gate 8 (Test) — anti-reward-hack:
- test count / coverage ห้าม "ลดลง" เพื่อทำ gate green (diff เทียบ baseline)
- deleted/skipped/xfail test → flag เด่นใน REVIEW report (ต้อง justify)
- assertion ที่อ่อนลง (เช่น assertTrue(True), commented assert) = Quality Smell reject
```
**Fit**: ต่อ "Quality Smells (reject)" ที่มีอยู่. สอดคล้อง "trust deterministic verifier, never self-report" + termination criteria ที่ capture intent.

**Invariant check**: dev-gate exception ≤400 บรรทัด — เพิ่ม ~8 บรรทัด, เช็คก่อน. review-checklist เป็น DRY source ของ /implement Phase 3b + /review → แก้ที่เดียวพอ.

---

## #5 — Sub-agent context isolation = stated invariant

**แนวคิด (Orchestrator-Workers + context engineering)**: sub-agent รันใน **clean window** แล้ว return เฉพาะ *conclusion* → กัน context rot ใน long fan-out. ตอนนี้ shode-house ทำแบบ emergent แต่ไม่ใช่ rule.

**Where (เสนอ)**: `shode-house-workflow` ระบุชัด + CLAUDE.md 1 บรรทัด:
```
Sub-agent isolation (🔴): Task tool delegate = fresh context;
worker return = structured conclusion เท่านั้น (ไม่ dump transcript กลับ orchestrator).
Oliver synthesize จาก conclusion, ไม่ rehydrate worker's full trace.
```
**Fit**: เป็นกลไกหลักกัน "context rot" ใน fan-out. คู่กับ caveman (compression) + learning-loop (bounded load).

**Invariant check**: prompt + doc. ไม่กระทบ schema/version logic.

---

## #6 — Heartbeat loop (scheduled/event-driven ops)

**แนวคิด (Pattern 9)**: agent ไม่รันต่อเนื่อง — wake on schedule/event, check condition, act ถ้าจำเป็น, sleep. ต้องมี **"cycle in progress" lock** กัน heartbeat ซ้อน.

**Gap ปัจจุบัน**: shode-house request-driven 100%. Reggie SLO burn-rate + Patrick OKR review = continuous (per-bd) แต่ไม่มี autonomous trigger.

**Where (เสนอ)**: candidate ต่ำสุดในชุด (เพราะต้องมี infra). ถ้าทำ — `slo` skill เพิ่ม mode (เคารพ 3-flag): burn-rate check เป็น scheduled task → alert เฉพาะเมื่อ breach. ต้อง lock กัน overlapping run.

**Fit**: เปิด capability ใหม่ (overnight monitor) แต่ research เตือนเอง: "most developers don't need agent loops yet" — อย่าทำถ้ายังไม่มี need จริง (YAGNI). แนะนำ **defer** เป็น `shortcut(bd):` จนกว่ามี project ที่ขอ.

---

## Failure-mode coverage map (ใช้ verify ว่าครบ)

| Loop failure mode | shode-house defense (หลัง adopt) |
|---|---|
| Context overflow / rot | caveman + #5 sub-agent isolation + #2 bounded lesson load |
| No-progress loop | **#1 Circuit Breaker** |
| Reward hacking | **#4 dev-gate guard** + M3 Anti-Puppet |
| Hallucinated success | M3 + NO MAGIC + evidence protocol (มีแล้ว) |
| Compounding errors | dev-gate verify early/often + #2 lesson buffer |
| Cost blowup | **#3 Bounded Execution** + #1 breaker |

---

## แนะนำลำดับลง (ถ้า approve)

1. **Batch A (prompt-only, ต่ำเสี่ยง)**: #1 + #3 + #4 + #5 → 1 minor bump (v3.7.0). รัน CI gate + drag-drop Cowork test ก่อน publish.
2. **Batch B (skill bake)**: #2 promote `learning-loop` — หลัง eval-harness baseline พร้อม.
3. **Defer**: #6 Heartbeat — `shortcut(bd):` จนมี need.

> ทุก batch: edit script ก่อนถ้าจะแหก invariant (กฎ CLAUDE.md ข้อแรก) · CHANGELOG entry ต่อ minor bump · README link skill → SKILL.md.
