---
description: "[shode-house] DEPRECATED v3.1 — alias ของ /design-system --stop --estimate. ใช้ flag form แทน. จะลบใน v3.2"
allowed-tools: Task, Read, Write, Edit, Grep, Glob
argument-hint: "[system description]"
---

# ⚠️ /spec-only DEPRECATED

Command นี้ถูก merge เข้า `/design-system --stop --estimate` ตั้งแต่ **v3.1.0**. กรุณาใช้:

```
/shode-house:design-system "$ARGUMENTS" --stop --estimate
```

**เหตุผล**: `/spec-only` กับ `/design-system` overlap 90% (Phase 1a Bella+Sara + Phase 1b Uma+Domain). v3.1 รวมเป็น command เดียวด้วย `--stop` (no implement suggest) + `--estimate` (add T-shirt) flags — ลด user confusion + maintain แห่งเดียว.

**Migration window**: alias นี้ยังทำงานได้ใน v3.1.x แต่ **จะลบใน v3.2**. update muscle memory ตอนนี้

---

## Auto-fallback (สำหรับ user เก่าที่พิมพ์ /spec-only)

Oliver: ตรวจถ้า user เรียก command นี้ → redirect ไป `/design-system --stop --estimate`:

```bash
echo "[Oliver] /spec-only deprecated → routing ไป /design-system \"$ARGUMENTS\" --stop --estimate"
# Then execute /design-system logic with --stop --estimate flags (ดู commands/design-system.md Step 0)
```

ดูรายละเอียดที่ [`commands/design-system.md`](./design-system.md) (Step 3 Phase Est + Step 4 If `--stop`)
