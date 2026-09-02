# แผนงาน v3.13 — Prompt Architecture · Lazy-load Topology · Token Usage Observability

> **Baseline**: v3.12.1 (tag) · static measurement เก็บไว้ที่ `.baseline-3.12.1.json`
> **Pillar 3 อย่าง**: (1) prompt architecture (2) lazy-load ที่ตรวจได้ (3) **token ที่ใช้จริง ไม่ใช่แค่ byte**
> 🔴 **หลักการกำกับทั้ง release**: byte ที่ลดลง **ไม่เท่ากับ** usage ที่ลดลง — agent อาจโหลด reference ซ้ำ, fan-out มากขึ้น, หรือเขียน output ยาวกว่าเดิม. `bytes/4` ใช้เป็น *static estimate ก่อนรัน* เท่านั้น ห้ามใช้เป็นหลักฐานสุดท้าย

---

## 0. Baseline ที่วัดแล้ว (3.12.1)

| Scenario | static B |
|---|---:|
| `/consult` | 37,004 |
| Phase 1a (Bella ∥ Sara) | 80,088 |
| Phase 1b UI (Uma) | 34,573 |
| Phase 1b UI + Domain | 59,198 |
| Phase 3b base (Chris ∥ Quinn ∥ Bella-spec) | 117,927 |
| **Phase 3b + Sentinel + Domain** | **175,383** |
| Implement UI full | 186,331 |
| **Sensitive UI full** | **243,787** |
| **Full fan-out 19 agents** | **587,390** |

Agent ที่เกิน target 45 KB: **orchestrator เท่านั้น** (48,856 B) · skill frontmatter รวม 9,398 B · output style Oliver 10,721 B

> ตัวเลขทั้งหมดนี้คือ **static** ยังไม่มี runtime — Workstream 10 คือส่วนที่เติมด้าน runtime ให้ครบ

---

## เป้าหมาย

**Static**
- Full fan-out ลดจาก 587,390 B อีก **≥ 15-20%** → เป้า **470,000-500,000 B**
- Agent invocation ทั่วไป **≤ 45 KB** · Oliver/Uma **≤ 50 KB / 48 KB**
- duplicate source-of-truth เหลือ **1 แห่งต่อ 1 rule**

**Runtime (ตัวชี้วัดจริง)**
- median `input_tokens` ลด **≥ 15%** · Phase 3b total ลด **≥ 20%** · `/consult` ลด **≥ 25%** · diagnose fast path ลด **≥ 25%**
- output tokens ต่อ subagent ลด **≥ 15%** · duplicate reference reads ลด **≥ 50%** · cache read ratio เพิ่มขึ้น
- cost ต่อ workflow ลด **≥ 15%** · latency p50 ลด **≥ 10%** (ถ้า model/provider คงเดิม)

**Quality (ห้ามแลก)**
- critical enforcement fixtures **100%** · general accuracy ลดไม่เกิน **2%** · ไม่มี safety/evidence/approval regression

---

## Workstream 1 — Enforcement Map (ทำก่อน refactor ทุกอย่าง)

inventory ทุกกฎสำคัญ ก่อนย้ายของ:

| Rule | Owner | Trigger | preload? | Source of truth | Verification |
|---|---|---|---|---|---|
| Safety R0/R1/R2 | ทุก agent | ทุกงาน | ✅ | `discipline-core` | mutation fixture |
| NO MAGIC / evidence-before-claim | ทุก agent | ทุก claim | ✅ | `discipline-core` | evidence fixture |
| Handoff contract (min fields) | ทุกตัวที่ delegate | delegation | ✅ | `discipline-core` | CI path/tool check |
| Response language | ทุก agent | ทุก message | ✅ | `discipline-core` | fixture |
| Recite Card | main session | first response | ❌ | `discipline/main-session.md` | output-style test |
| Spec axis | Bella | Phase 3b | ❌ | `review/spec-bella.md` | dispatch graph + fixture |
| DoD | Oliver + producer | phase exit | บางส่วน | `deliverable/definition-of-done.md` | close gate |
| UX evidence | Uma/Quinn/Chris | frontend touched | ❌ | `ui-test` | frontend fixture |
| Domain citation + disclaimer | 7 domain agents | domain claim | ✅ (ย่อ) | `domain-core` | citation fixture ×7 |
| Anti-Puppet | ทุก producer | claim "done" | ✅ | `deliverable` core | anti-puppet fixture |
| Close-on-done (M8) | Oliver | item land | ✅ | `drift` | close fixture |
| AskUserQuestion relay | main session | ambiguity | ❌ | `discipline/main-session.md` | relay fixture |

**Deliverable**: `docs/enforcement-map.md` + `.enforcement-map.json` (machine-readable สำหรับ CI) · ระบุชัดว่ากฎไหน **หายไม่ได้** และกฎไหน **lazy-load ได้**

---

## Workstream 2 — แตก Discipline เป็น Core + Main-session policy

`shode-house-discipline` ถูกคูณ **19 ครั้ง** จึงต้องบางที่สุดในระบบ

```
shode-house-discipline/
├── SKILL.md          universal core เท่านั้น  (เป้า ≤ 7 KB)
├── main-session.md   Recite Card · AskUserQuestion relay · user-facing rules
├── reporting.md      report brevity · tag prefix · output conventions
└── handoff.md        schema + ตัวอย่าง delegation แบบเต็ม
```

**core (preload ทุก agent)**: NO MAGIC/evidence · VERIFY BEFORE DONE · Safety R0/R1/R2 · scope discipline · handoff **minimum fields** · response language · skill-loading rule
**ย้ายออก**: Recite Card → main-session · ตัวอย่าง report/tag → reporting · handoff schema ยาว → handoff.md · ingress behavior เฉพาะ Oliver → Oliver

**Acceptance**: core ≤ 7 KB · ทุก agent ผ่าน safety/handoff mutation fixture

---

## Workstream 3 — Deliverable Core + phase-specific references

```
shode-house-deliverable/
├── SKILL.md              thin output contract  (เป้า ≤ 4 KB)
├── definition-of-done.md
├── adr-lifecycle.md
├── ux-evidence.md
├── anti-puppet.md
└── templates/
```

**thin core**: output ต้องอยู่ใน artifact · evidence path · placeholder/TBD policy · no false done · **pointer ว่าต้องโหลด reference ไหนตาม deliverable type**

**loading policy**: Oliver โหลด DoD ก่อน phase exit · Sara โหลด ADR lifecycle ตอนสร้าง/แก้ ADR · Uma โหลด UX evidence ตอนเข้า 1b/3a · producer โหลด template ที่ตรงกับ artifact เท่านั้น

**Acceptance**: core ≤ 4 KB · ลด preload ≥ 8 KB ต่อ agent ที่เคยแบก · CI ตรวจ phase → required reference mapping

---

## Workstream 4 — Review architecture แยกตาม axis/owner

```
review/
├── SKILL.md              orchestration + severity + aggregation  (เป้า ≤ 4 KB)
├── standards-chris.md
├── integration-quinn.md
├── spec-bella.md
├── security-sentinel.md
├── domain-validation.md
└── report-format.md
```

**กติกา**: subagent เห็นเฉพาะ axis ของตัวเอง · orchestrator เห็น core · aggregate แยก Standards/Spec เหมือนเดิม · **ห้าม agent หนึ่ง preload checklist ของอีก agent** · severity/report schema อยู่ core เดียว

**Acceptance**: core ≤ 4 KB · Chris/Quinn/Spec ลดรวม ≥ 25 KB ต่อ Phase 3b · dispatch graph ตรวจ owner/reference ครบ
**Fixture ต้องจับ**: missing requirement · scope creep · standards-only defect · security defect · no-spec case

---

## Workstream 5 — Domain core + domain modules

```
domain-core/
├── SKILL.md              disclaimer + citation contract
└── source-validation.md
```

**domain core**: AI persona disclaimer · primary-source requirement · citation format · human validation สำหรับ high-stakes · stale-knowledge handling
**agent body เหลือ**: domain boundary · invariant · domain-specific failure mode · routing/ownership · regulation family ที่เกี่ยว — **ไม่ใส่ generic PCI/IFRS/BOT example ซ้ำทุกตัว**

**Acceptance**: common material มี source เดียว · domain agent body ลดเฉลี่ย 25-35% · citation/disclaimer fixture ผ่านครบ 7 domain

---

## Workstream 6 — Oliver / Uma phase runbooks

```
orchestrator.md           routing · M1 ingress · tracker/state · approval ownership · dispatch policy · close-on-done
workflow/
├── engagement-plan.md · phase-orchestration.md · map-mode.md · clarification-relay.md · resume-run.md

ux-ui-designer.md         design authority + UX/a11y core
ui/
├── phase-1b-design.md · phase-3a-verify.md · design-intel.md · wcag-manual.md · evidence-format.md
```

**Acceptance**: Oliver agent+preload ≤ 48-50 KB · Uma ≤ 45-48 KB · phase-trigger CI ตรวจว่า reference ที่ต้องโหลดถูกระบุ · Map/1b/3a fixture ผ่าน

---

## Workstream 7 — Lazy-load contract ที่ตรวจได้

convention กลางในทุก pointer:

```
LOAD: <reference>
WHEN: <machine-detectable trigger>
OWNER: <agent>
REQUIRED-BEFORE: <action/gate>
```
ตัวอย่าง:
```
LOAD: skills/ui/ui-test/phase-3a.md
WHEN: frontend_changed=true
OWNER: ux-ui-designer
REQUIRED-BEFORE: phase_3a_verdict
```

**CI ตรวจ**: reference มีจริง + ถูก pack · owner มี `Read`/`Skill` · trigger มี producer · gate ตรวจ load/evidence marker · ไม่มี reference cycle · ไม่มี required reference ที่ไม่มี caller

---

## Workstream 8 — Eval harness: in-progress → release gate

ต้องมี behavioral baseline **ก่อน** เปลี่ยน preload topology

**Fixture groups**: Safety/R0 · Evidence/no-magic · Handoff completeness · Scope drift · Spec axis · Domain citation · UX evidence · AskUserQuestion relay · Close-on-done · **Lazy-load omission**

**A/B**: A = 3.12.1 · B = 3.13 candidate · prompt เดียว/model เดียว/หลาย run · **ตรวจ accuracy ก่อน token saving**

**Promotion criteria**: critical invariant pass 100% · general accuracy ลดไม่เกิน 2% · input context ลดตาม target · **ไม่มี fixture ที่ผ่านเพราะ skip action**

---

## Workstream 9 — Token budget รุ่นใหม่ (static)

```
.skill-metadata-budget · .agent-core-budget · .preload-budget · .workflow-scenario-budget
```

scenario budgets: `/consult` · Phase 1a · Phase 1b UI · Phase 3b base · sensitive UI full · full fan-out

CI คำนวณจาก **graph จริง**: `command + output style + agents dispatched + each agent core + preload skills + required lazy references`
🔴 ห้ามดูแค่ agent file หรือ preload แยกกัน

---

## Workstream 10 — 🔴 Token Usage Observability (แกนหลักของ 3.13)

> byte ลดไม่ได้แปลว่า usage ลด — ต้องวัดของจริง

### 10.1 แยก token 5 ประเภท

| Metric | ความหมาย |
|---|---|
| `input_tokens` | prompt + agent body + preload + delegation + artifacts |
| `cache_read_tokens` | context ที่อ่านจาก prompt cache |
| `cache_write_tokens` | context ใหม่ที่ถูกนำไป cache |
| `output_tokens` | คำตอบ + report + transcript |
| `total_effective_tokens` | usage รวมที่ใช้เทียบก่อน-หลัง |

ถ้า runtime ส่ง cost มาด้วย → เก็บ `input_cost` · `cache_cost` · `output_cost` · `total_cost`

### 10.2 Usage record ต่อ agent invocation

```json
{
  "run_id": "review-bd-42-iter-1",
  "plugin_version": "3.13.0-rc.1",
  "model": "sonnet",
  "command": "implement",
  "phase": "3b",
  "agent": "code-reviewer",
  "loaded_skills": ["discipline-core", "review-standards"],
  "loaded_references": ["outputs/SPEC-bd-42.md"],
  "input_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0,
  "output_tokens": 0, "duration_ms": 0, "verdict": "PASS"
}
```
raw → `outputs/token-usage/<run-id>/<agent>.json` · aggregate → `outputs/token-usage/<run-id>/summary.json`

### 10.3 Benchmark scenarios (12 ตัว, fixture คงที่)

`/consult` คำถามเดียว · `/design-system` backend-only · `/design-system` frontend+domain · `/implement` backend · `/implement` UI · Phase 3b base · Phase 3b sensitive · `diagnose` fast · `diagnose` full · Map mode · Resume run · full 19-agent synthetic fan-out

แต่ละ scenario: fixture/snapshot/model/reasoning setting เดิม · **รัน 3-5 รอบ** · รายงาน **median + p90** ห้ามใช้ run เดียว

### 10.4 เปรียบเทียบ 3.12.1 ↔ 3.13

รายงานต่อ scenario แยก delta: input · cached input · output · total · cost · latency

| Scenario | เป้า delta | Accuracy |
|---|---:|---|
| Consult | −25% | ไม่ลด |
| Phase 1a | −15% | ไม่ลด |
| Phase 3b | −20% | ไม่ลด |
| UI full | −15% | ไม่ลด |
| Diagnose fast | −25% | ไม่ลด |

### 10.5 Repeated-load amplification

บันทึกทุก skill/reference load เพื่อจับ: agent โหลด skill ที่ preload อยู่แล้ว · reference เดียวถูกอ่านซ้ำใน agent เดียว · spec/diff ถูก paste ทั้งก้อนแทนส่ง path · Oliver re-analyze transcript ที่ agent สรุปแล้ว · report ถูกสร้างทั้ง bd notes และ markdown · retry ทั้ง phase แทน resume · subagent output ยาวเกิน contract

ตัวอย่าง finding ที่ต้องรายงานได้:
```
Phase 3b: review-checklist preloaded 3 ครั้ง · report-format read 3 ครั้ง
          SPEC read 3 ครั้ง · diff pasted 2 ครั้ง · aggregate repeated findings 1,840 output tokens
```

### 10.6 Output-token budgets

| Output | Budget |
|---|---:|
| Subagent return | ≤ 300-500 |
| Handoff | ≤ 250 + artifact path |
| Review finding summary | ≤ 500 (detail อยู่ใน artifact) |
| Status update | ≤ 150 |
| No-finding PASS | ≤ 200 + evidence path |
| Final report | proportional ตาม findings |

**ข้อยกเว้น**: user ขอรายละเอียด · security/regulatory explanation · incident/postmortem · artifact คือ deliverable หลัก
🔴 **ห้ามบีบจน evidence หรือ remediation หาย**

### 10.7 Tool-output budgets

`Read` ใช้ offset/limit · `rg` จำกัด path/pattern · test output เก็บ full log ในไฟล์แล้ว paste เฉพาะ signal · JSON ใช้ `jq` เลือก field · diff ใหญ่ใช้ `--stat`/`--name-only` ก่อน · browser network log กรองเฉพาะ failed/critical · subagent คืน path ไม่ dump log

metric เพิ่ม: `tool_calls` · `tool_output_chars` · `files_read` · `duplicate_files_read` · `largest_tool_output`

### 10.8 Token regression gates

**static (CI)**: agent+preload bytes · scenario graph bytes · skill metadata bytes · reference size · duplicate block threshold · historical wording threshold
**runtime (eval)**: median total ห้ามเพิ่มเกิน 3% · p90 ห้ามเพิ่มเกิน 5% · output tokens ห้ามเพิ่มโดยไม่มี accuracy gain · critical scenario ต้องลดตาม target · accuracy/security/safety ห้ามลด

**budget exception** (ต้องมีเหตุผลบันทึกไว้): accuracy ดีขึ้นอย่างมีนัยสำคัญ · security finding ดีขึ้น · user-requested detail · เพิ่ม evidence ที่จำเป็น

---

## ลำดับการทำงาน

**Phase A — Baseline**: tag 3.12.1 ✅ · บันทึก context/scenario budget ✅ (`.baseline-3.12.1.json`) · **รัน eval baseline** · สร้าง enforcement map
**Phase B — Universal core**: แตก discipline core → แตก deliverable core → รัน CI + mutation + eval
**Phase C — Role topology**: แยก review axes → domain core → แยก Oliver/Uma runbook → รัน scenario budget + eval **หลังแต่ละก้อน**
**Phase D — Harden**: lazy-load contract CI → package boundary → full fan-out simulation → independent full scan → `3.13.0-rc.1`
**Phase E — Release**: แก้ RC findings → A/B eval รอบสุดท้าย → build/integrity/install smoke → tag `3.13.0`

---

## Definition of Done

- [ ] Enforcement map ครบทุก critical rule
- [ ] Critical fixtures ผ่าน **100%**
- [ ] Behavioral accuracy ลดไม่เกินเกณฑ์ (2%)
- [ ] **Static** full fan-out ลด ≥ 15-20% จาก 587,390 B
- [ ] **Runtime** median input tokens ลด ≥ 15% · Phase 3b total ลด ≥ 20% · consult ลด ≥ 25%
- [ ] Output token ต่อ subagent ลด ≥ 15% · duplicate reference read ลด ≥ 50%
- [ ] Cost ต่อ workflow ลด ≥ 15% · latency p50 ลด ≥ 10%
- [ ] Oliver/Uma อยู่ใน target
- [ ] ไม่มี required rule ที่พึ่ง prompt memory
- [ ] ไม่มี lazy reference ที่ unreachable/unpacked
- [ ] CI เดิม + topology CI + eval ผ่าน
- [ ] Full scan ไม่พบ Critical/High
- [ ] Migration note ระบุ source-of-truth ใหม่ทุก rule

> **DoD ของ 3.13 ไม่ใช่ "ไฟล์เล็กลง" แต่คือ: token ที่ใช้จริงลดลง · cost/latency ดีขึ้น · enforcement accuracy ไม่ลด**

---

## Release report ที่ต้องออกมาหน้าตาแบบนี้

```
Token Usage — 3.12.1 → 3.13.0
Static context:
  full fan-out: 587 KB → 4xx KB (-xx%)
Runtime median:
  consult:       xx.xk → xx.xk (-xx%)
  phase 1a:      xx.xk → xx.xk (-xx%)
  phase 3b:      xx.xk → xx.xk (-xx%)
  sensitive UI:  xxxk  → xxxk  (-xx%)
Output:
  subagent median: xxx → xxx (-xx%)
Quality:
  critical fixtures: 100% → 100%
  general accuracy:  xx.x% → xx.x%
  false PASS rate:   x.x% → x.x%
```

---

## ห้ามทำพร้อม 3.13

เพิ่ม agent ใหม่ · เพิ่ม domain ใหม่ · เปลี่ยน Phase Contract · เปลี่ยน tracker abstraction · เพิ่ม feature workflow ใหม่ · เปลี่ยน model matrix โดยไม่เกี่ยวกับ eval

> ให้ 3.13 เป็น release ด้าน **prompt architecture · lazy-loading · enforcement preservation · token observability** เท่านั้น เพื่อให้วัดผลและหาสาเหตุ regression ได้ชัด
