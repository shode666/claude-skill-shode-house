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
prose = lossy channel → **ส่ง path ไม่ส่งเนื้อหา**

## Schema

```
bd      : <bd-id>              (บังคับ — ไม่มี = STOP route Oliver)
phase   : <phase name>          เช่น phase-2, phase-3b
iter    : <n>                   รอบที่เท่าไรของ bd นี้
paths   : outputs/<bd-id>/<NN>-<agent>-<phase>.md  (≥1 path)
task    : <1-3 บรรทัด ว่าต้องทำอะไร ไม่ใช่เล่าว่าเกิดอะไรมาก่อน>
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

- สรุปเนื้อหา spec ลงใน delegation message แทนที่จะส่ง path → consumer อ่านของจริงไม่ได้ ตัดสินจากสรุปที่ lossy
- ไม่มี `bd` → agent ปลายทางทำงานโดยไม่มี tracker (M1 ต้อง STOP)
- `paths` ชี้ไฟล์ที่ยังไม่ได้เขียน → producer ต้องเขียน artifact **ก่อน** hand-off เสมอ
- return dump transcript ทั้งหมด → return = verdict + artifact path + open questions เท่านั้น
