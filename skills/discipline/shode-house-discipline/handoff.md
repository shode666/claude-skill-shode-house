---
name: handoff
description: Reference (lazy-load) ของ `shode-house-discipline` — handoff schema เต็ม + ตัวอย่าง delegation message ที่ถูก/ผิด. โหลดก่อน delegate ครั้งแรกใน session หรือเมื่อ consumer แจ้งว่า context ไม่พอ
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-discipline/handoff.md
WHEN: delegation_first_in_session=true OR consumer_reported_missing_context=true
OWNER: orchestrator
REQUIRED-BEFORE: delegate_task
```

# Handoff schema (เต็ม)

sub-agent เกิดใน **context ว่าง** — เห็นแค่ agent body + delegation message + target `CLAUDE.md`
ส่ง path/revision เป็นหลัก; ถ้า consumer ไม่มี shared filesystem ส่งเฉพาะ excerpt ที่จำเป็นพร้อม source/revision ตาม harness และเปิดเผยข้อจำกัด

## Schema

```
task    : <canonical task ID and record path/URL> (Beads/Jira/Redmine/Markdown ตาม project)
phase   : <phase name>          เช่น phase-2, phase-3b
iter    : <n>                   รอบที่เท่าไรของ bd นี้
paths   : outputs/<bd-id>/<NN>-<agent>-<phase>.md  (≥1 path)
outcome : <งานที่อนุญาต + scope/non-goals + write ownership>
gate    : <verdict ที่ต้องได้กลับ | gate ที่ต้องผ่าน>
```

## ✅ ตัวอย่างที่ถูก

```
[Oliver|state:phase-3b|bd:42] Oliver ▸ Chris : review payment service (bd:42)
bd      : 42
phase   : phase-3b
iter    : 1
paths   : outputs/42/03-developer-phase-2.md, outputs/42/01-business-analyst-spec.md
task    : review diff ตาม standards axis 7 มิติ + เขียน unit test ที่ขาด
gate    : PASS/FAIL + severity table + artifact path
```

## ❌ ตัวอย่างที่ผิด

- ส่งสรุป spec ที่ตรวจต้นฉบับไม่ได้โดยไม่แจ้งข้อจำกัด → consumer ตัดสินจากข้อมูลที่ lossy; ใช้ artifact ที่เข้าถึงได้หรือ provenance-marked excerpt
- ไม่มี canonical task/context ที่ต้องใช้ → ส่งกลับ Oliver ให้เติม ไม่สร้าง Beads แทน tracker เดิม
- `paths` ชี้ไฟล์ที่ยังไม่ได้เขียน → producer ต้องเขียน artifact **ก่อน** hand-off เสมอ
- return dump transcript ทั้งหมด → return = verdict + artifact path + open questions เท่านั้น

## 🤝 Handoff Broadcast Protocol (caveman 1-line)

### Arrow convention (🔴)

ใช้ 2 arrows คนละความหมาย (accept divergence — semantic distinction):

| Arrow | ความหมาย | When |
|-------|---------|------|
| `▸` | **Handoff broadcast** (formal, between agents/teams in workflow) | Phase transition, agent-to-agent handoff, multi-sig gate |
| `→` | **General flow / sequence / implication** (informal) | Process steps, code flow, "X causes Y", documentation flow |

ตัวอย่าง:
- `Bella ▸ Dave : impl bd-42` — handoff (use ▸)
- `Phase 1a → 1b` — general phase sequence (use →)
- `low contrast → fail WCAG` — implication (use →)

> ห้ามใช้ `▸` ใน documentation flow / code-flow / general explanation. ห้ามใช้ `→` ใน formal handoff (M3 protocol บังคับ `▸`)

### Format มาตรฐาน
```
[<from>] ▸ [<to>] : <what> (bd-<id>)
```

### Agent-to-agent
```
Bella ▸ Dave   : impl bd-42
Dave  ▸ Verify : CR + test + sec (bd-42)
Verify ▸ Oliver : 2 Major, 1 Minor
Oliver ▸ Dave   : fix M (bd-42, iter 2)
Oliver ▸ Ops    : deploy bd-42
Ops    ▸ ✓      : prod stable, SLO green
```

### Team-level (whole team activates)
```
Design  ▸ Dev    : spec done (bd-42)
Dev     ▸ Verify : impl done
Verify  ▸ Lead   : triage
Lead    ▸ Ops    : ship it
```

### กติกา 4 ข้อ
1. **1 บรรทัด** สำหรับ summary; รายละเอียดที่ confirmed evidence home ของ project รวม Markdown โดย link กับ canonical task ID
2. Canonical task ID is required for inner-loop handoffs; a Beads ID is only one example.
3. **Arrow** = `▸` (ใช้ consistent ทั้ง project)
4. **State explicit** สั้น: `impl / CR / test / sec / fix / retest / clean / deploy / ✓`
