```lazy-load-contract
LOAD: references/patterns/durable-agent-runtime.md
WHEN: runner_needs_retry_or_checkpoint=true
OWNER: devops-engineer
REQUIRED-BEFORE: runner_generate
```

# Durable agent runtime — contract สำหรับ runner ที่ Aaron generate (v3.12)

> **Audience**: Aaron (generate runner ระดับ infra/CI) · Sara (ADR ตอนเลือก platform) · Dave (app-level idempotency)
> **โหลดเมื่อ**: target project ต้องการ long-running agent / fan-out cap / retry / checkpoint / human approval ที่กินเวลาเป็นวัน
> **ห้าม ship engine ใน plugin** (`CLAUDE.md` § Runtime guarantee = generate, don't ship) — ไฟล์นี้คือ *contract ว่า runner ที่ถูกต้องต้องมีอะไร* ไม่ใช่ตัว runner
> **YAGNI**: ไม่มี need = ไม่ generate. Agent ที่รันจบใน session เดียว ไม่ต้องมีอะไรในนี้เลย

---

## หลักการกลาง — แยก loop ที่ replay ได้ ออกจาก step ที่ replay ไม่ได้

```
Deterministic outer loop  (workflow code)      : plan → act → observe
   ห้ามแตะ system clock / random / env โดยตรง — ใช้ primitive ของ framework
   given journal เดิม ต้อง replay ได้ผลเหมือนเดิมเป๊ะ

Non-deterministic inner steps (activities)     : LLM call · tool call · HTTP · shell · file write
   รันครั้งแรก → บันทึกผลลง journal
   ตอน replay → ดึงจาก journal ไม่รันซ้ำ
```

non-determinism **ยอมรับได้** ตราบใดที่มันอยู่ในขอบเขต journal. ผิดข้อนี้ = recovery กลายเป็นการรันงานซ้ำ (ส่งเงินซ้ำ, deploy ซ้ำ, เขียนไฟล์ทับ)

---

## 6 อย่างที่ runner ต้องมี (ตรวจได้ ห้ามอ้างว่า "มีแล้ว" ลอย ๆ)

### 1. Event journal — ไม่ใช่ log
Log คือข้อความ; journal คือ **บันทึกขอบเขตงานที่เสร็จแล้ว**. ทุก run มี id ที่เสถียร และทุก step ที่มีความหมายต้องมี record:

```
step_id · run_id · planned_action · inputs(hash) · versions · result · retry_count · started_at · finished_at
```
เกณฑ์ตรวจ: kill process กลางคัน → อ่าน journal แล้วบอกได้ว่า step ไหนเสร็จ step ไหนยัง **โดยไม่ต้องเดา**

### 2. Replay ที่ไม่รัน side-effect ซ้ำ
recovery ต้อง **ข้าม step ที่เสร็จแล้วและใช้ผลเดิม** — ห้ามยิง LLM ซ้ำ ห้ามรัน shell ซ้ำ ห้าม POST ซ้ำ ห้ามเขียนไฟล์ซ้ำ
เกณฑ์ตรวจ: รัน workflow เดิม 2 รอบหลัง crash → side-effect เกิดขึ้นครั้งเดียว

### 3. Idempotency ที่ tool boundary
ทุก operation ที่ mutate ต้องมี **idempotency key** + duplicate detection แบบ Stripe: ผลลัพธ์แรกของ key ถูกเก็บ และถูกส่งคืนทุกครั้งที่ retry
pattern: **บันทึก intent ก่อนลงมือ → บันทึก receipt หลังสำเร็จ** ช่องว่างระหว่างสองอันคือจุดที่ crash แล้วเจ็บ
🔴 money/ledger (Felix) · schema migration (`data-migration` skill) · deploy (Aaron) = ห้ามไม่มี idempotency key

### 4. Version stamp — กัน divergence ตอน replay
บันทึกลง journal ทุก run: **model id · prompt/agent version · plugin version · tool schema version · sandbox image**
ไม่มีสิ่งนี้ = replay ด้วย prompt คนละเวอร์ชันแล้วได้ผลคนละอย่าง โดยไม่มีใครรู้ว่าทำไม
> ระดับ plugin เราทำแล้วแบบเบา ๆ: run stamp ใน `bd` (ดู `shode-house-workflow` § Run Durability)

### 5. HITL durability — approval เป็น event ไม่ใช่ข้อความ
เก็บ **artifact ที่ผู้อนุมัติเห็นจริง** พร้อม: ใครอนุมัติ · เมื่อไหร่ · เห็นอะไร · **hash ของ artifact นั้น**
🔴 recovery **ห้ามสันนิษฐานว่า approval เก่ายังใช้กับ artifact ที่แก้ไปแล้วได้** — hash ไม่ตรง = ขออนุมัติใหม่
approval ที่อยู่ในแชท/หน่วยความจำ session = ไม่นับ (process ตาย = หลักฐานหาย)

### 6. Observability ที่มีขอบเขต
trace ต้องตอบ "เกิดอะไรขึ้น" ได้ **โดยไม่กลายเป็น memory system ตัวที่สองที่ไม่มีใครคุม**
- correlation id ต่อ run/step เพื่อไล่ปัญหา
- 🔴 **redact ก่อนเก็บเสมอ**: secret · token · auth header · PII · prompt ที่มีข้อมูลลูกค้า → `<REDACTED>`
- จำกัดสิทธิ์เข้าถึง trace payload; captured artifact (HAR/log dump) เก็บเฉพาะบรรทัดที่มี signal

---

## Testing ที่บังคับ — crash injection

ระบบ recovery ที่ไม่เคยถูกทดสอบ = ระบบที่กู้ได้เพราะโชคดี. Quinn ต้องมี test ที่ **จงใจฆ่า process** ที่จุดเหล่านี้:

- [ ] หลัง API สำเร็จ **แต่ก่อน** เขียน receipt ลง journal (จุดที่เกิด double-execute)
- [ ] หลัง approval ผ่าน **แต่ก่อน** เริ่ม execute
- [ ] ระหว่าง version rotation (deploy prompt/model ใหม่ขณะมี run ค้าง)
- [ ] ระหว่าง retry ที่ค้างครึ่งทาง

ผลที่ต้องได้: resume แล้ว side-effect เกิดครั้งเดียว · approval ที่ artifact เปลี่ยนถูก reject · ไม่มี step ไหนหาย

---

## Platform landscape (2026) — เลือกใน ADR ของ Sara ไม่ใช่ default

| Platform | รูปแบบ | เหมาะเมื่อ |
|---|---|---|
| **Temporal** | server + worker, หลายภาษา, โตเต็มที่ | ระบบใหญ่ ทีมมีคนดูแล infra ได้ |
| **Inngest** | serverless-native (Vercel/Cloudflare), managed | ทีมเล็ก ไม่อยากดูแล server |
| **DBOS Transact** | ใช้ Postgres เป็น runtime, เป็น library | มี Postgres อยู่แล้ว ไม่อยากเพิ่ม component |
| **Restate** | single binary, cross-language | อยาก self-host แบบเบา |

🔴 **ก่อนเลือก ถามก่อนว่าต้องการจริงไหม**: agent ที่จบใน session เดียว ไม่มี side-effect ที่ทำซ้ำแล้วเจ็บ และไม่มี human approval ที่กินเวลาข้ามวัน → **ไม่ต้องมี durable engine** (YAGNI ladder ของ `dev-gate` ข้อ 1)
เกณฑ์ที่บอกว่า "ต้องมี": มี side-effect ที่ทำซ้ำแล้วเสียหาย (เงิน/migration/deploy) **หรือ** มี human approval ที่รอเป็นชั่วโมง/วัน **หรือ** run ยาวเกินอายุ process เดียว

---

## Mapping กับของเราเอง

| contract ข้างบน | shode-house ระดับ plugin | ระดับ target project |
|---|---|---|
| journal | `bd` notes + `outputs/<bd-id>/` artifact + commit sha (= audit trail, replay ไม่ได้) | Aaron generate |
| replay / idempotency | ❌ ไม่มี — resume ทำด้วย `state.json` + ตรวจ artifact จริง (ดู § Run Durability) | Aaron generate |
| version stamp | ✅ run stamp ใน bd | ต่อยอดเป็น journal field |
| HITL durability | ✅ approval + artifact sha ใน bd | ต่อยอดเป็น approval event |
| redaction | ✅ กฎใน `diagnose` + evidence protocol | ใส่ใน trace pipeline |
| crash injection | ❌ ไม่มี (agent session ไม่ใช่ระบบที่เรา deploy) | ✅ Quinn เขียน |

Sources: [Zylos — Durable Execution for AI Agent Runtimes (2026-04)](https://zylos.ai/research/2026-04-24-durable-execution-agent-runtimes/) · [Reactify — Durable AI agents in 2026](https://www.reactify-solutions.com/articles/durable-ai-agents-2026) · [Inngest — Durable Execution & AI Agents](https://www.inngest.com/blog/durable-execution-key-to-harnessing-ai-agents) · [Microsoft Learn — Durable Task for AI Agents](https://learn.microsoft.com/en-us/azure/durable-task/sdks/durable-task-for-ai-agents)
