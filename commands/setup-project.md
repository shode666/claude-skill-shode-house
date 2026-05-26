---
description: "[shode-house] DEPRECATED v3.1 — alias ของ /init --quick. ใช้ /init --quick <stack> แทน. จะลบใน v3.2"
allowed-tools: Read, Write, Edit, Bash, Task
argument-hint: [stack, e.g. "FastAPI + Postgres + Redis"]
---

# ⚠️ /setup-project DEPRECATED

Command นี้ถูก merge เข้า `/init --quick` ตั้งแต่ **v3.1.0**. กรุณาใช้:

```
/shode-house:init --quick "$ARGUMENTS"
```

**เหตุผล**: `/init` กับ `/setup-project` ทำงาน 80% เหมือนกัน (Aaron + Docker + CI + tracker). v3.1 รวมเป็น command เดียวด้วย mode flag — ลด user confusion + maintain แห่งเดียว.

**Migration window**: alias นี้ยังทำงานได้ใน v3.1.x แต่ **จะลบใน v3.2**. update muscle memory ตอนนี้

---

## Auto-fallback (สำหรับ user เก่าที่พิมพ์ /setup-project)

Oliver: ตรวจถ้า user เรียก command นี้ → redirect ไป `/init --quick`:

```bash
echo "[Oliver] /setup-project deprecated → routing ไป /init --quick \"$ARGUMENTS\""
# Then execute /init --quick logic (ดูใน commands/init.md Mode B)
```

ดูรายละเอียดที่ [`commands/init.md`](./init.md) Mode B section
