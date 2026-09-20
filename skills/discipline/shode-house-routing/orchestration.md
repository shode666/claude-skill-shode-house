---
name: orchestration
description: Reference (lazy-load) ของ `shode-house-routing` — pipeline parallel (chunk stagger), multi-task long-run orchestration, token-saving runtime notes, Chris/Quinn vs Dave adversarial relation. Parallel criterion + conflict table อยู่ใน SKILL.md root
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-routing/orchestration.md
WHEN: pipeline_parallel=true OR multi_task_long_run=true OR reviewer_vs_producer_dispute=true
OWNER: orchestrator
REQUIRED-BEFORE: fan_out_second_task_or_stagger
```

# Routing — orchestration depth

### Pipeline parallel (cross-bd staggered — producer/consumer)

intra-bd มี parallel แล้ว (Dave#N, Chris∥Quinn). **cross-phase pipeline** (เช่น Sara detail-design chunk 1 → Dave build chunk 1 **พร้อม** Sara design chunk 2) ทำผ่าน **chunk-bd decomposition**:

```
bd-1: Sara design ▸ Dave build ─────────
bd-2:        Sara design ▸ Dave build ───   ← Sara เลื่อนไป design bd-2 ตอน Dave build bd-1
bd-3:               Sara design ▸ Dave ───
```

- แตก feature เป็น chunk-bd ที่ **interface ชัด** (Sara กำหนด contract ระหว่าง chunk ก่อน) → downstream chunk ไม่ block จนกว่า interface เปลี่ยน
- Oliver schedule แบบ stagger: bd-N เข้า Phase 2 ขณะ bd-(N+1) อยู่ Phase 1 — **owner คนละ stage ไม่ชนกัน** (Sara=design stage, Dave=build stage)
- ห้าม pipeline ถ้า chunk มี hard data-dep (bd-2 ต้องใช้ผล bd-1) → sequential
- WIP cap: ไม่เกิน 2-3 bd in-flight ต่อ stage (กัน Sara/Dave context bloat + rework ตอน interface เปลี่ยน)

## 🔁 Multi-bd Long-run Orchestration (🔴 wire harness contract)

long run = หลาย bd ต่อเนื่อง. enforce ด้วย harness contract (ดู `/init` rule 11 + Oliver Harness Contract Check):

- **Checkpoint** = confirmed canonical record ตาม `shode-house-workflow/harness.md`; resume จาก phase/owner/evidence จริง ไม่สร้าง store ที่สอง
- **Fan-out cap** = WIP limit ต่อ stage (default 2-3); ห้าม spawn bd พร้อมกันเกิน cap (token spike + Oliver context bloat)
- **Retry/backoff** = bd fail → iter++ (max 3, per Phase 4) → escalate; ไม่ retry เงียบ
- **Reduce** = อ่าน current checkpoint และงานที่พร้อม ไม่ดึงประวัติทุก task เข้า context
- หากต้องการ runtime enforcement เพิ่ม → Aaron เสนอ runner เป็น project opt-in; สร้าง/ติดตั้งเมื่อได้รับอนุญาตเท่านั้น ไม่ใช่ prerequisite ของ long run และไม่ ship ใน plugin

---

## 🔧 Token-saving (🔴 runtime)

- **Lazy-load**: Dave อ่าน `references/languages/<lang>.md` เฉพาะภาษาที่ใช้; skill โหลดเมื่อ trigger เท่านั้น
- **Confirmed source of truth**: status/spec/evidence ใช้ home ที่ project เลือก รวม Markdown; เก็บ links แทนสำเนาซ้ำ
- **Caveman broadcast**: 1 บรรทัดต่อ handoff; รายละเอียดอยู่ใน confirmed evidence home พร้อม canonical task ID

---

### Adversarial relation: Chris/Quinn vs Dave (🔴 embedded discipline)

| Question | Answer | Why |
|---|---|---|
| Chris/Quinn trust Dave's claim "test ผ่าน"? | ❌ ห้าม — Zero trust; ต้อง run + paste evidence เอง | Anti-Puppet (per discipline + review-checklist) |
| Chris/Quinn verdict default? | ❌ FAIL until proven PASS with paste-output evidence | Pessimistic mindset → catch hidden bugs |
| Dave push back ด้วย "should be fine"? | ❌ Chris/Quinn ห้าม yield; counter ด้วย **own-run evidence** | Adversarial gate, ไม่ใช่ social negotiation |
| UI or API behavior touched? | Select reviewers by harness tier and changed boundaries; UI requires visual/interaction evidence, API requires applicable contract/integration evidence | Use the review-checklist evidence ladder; unavailable required evidence = BLOCKED, not a demand to install browser MCP |
| Chris/Quinn agree blindly with each other? | Cross-check allowed; each selected reviewer must reach an independent verdict from evidence, parallel or sequential | Independence is separate judgment and context, not simultaneous execution |
