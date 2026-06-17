---
name: learning-loop
description: |
  [WHAT] Self-improving loop (Hermes-inspired) แบบ gated — capture lesson อัตโนมัติ (non-blocking) + distill/gate offline; project-level ต่อเนื่อง, plugin-level เฉพาะ cross-project ผ่าน invariant gate.
  [AUDIENCE] Oliver (Phase 4 capture trigger); maintainer (offline distill+gate — sole promoter); Patrick (retro consume).
  [WHEN] Phase 4 Triage (capture, non-blocking); offline cadence (distill+gate); ก่อน promote candidate → plugin bucket. ห้ามรัน distill/gate ใน hot loop.
  [TRIGGER] /shode-house:learning-loop, "self-improving", "learning loop", "capture lesson", "distill skill", "promote skill", "Hermes loop".
---

# Learning Loop (self-improving — gated, non-blocking)

> Offline meta-tooling (เหมือน eval-harness). **ไม่ ship** จนกว่า bake เสร็จ + eval ผ่าน
> Hermes เขียน skill กลับเข้าตัวเองทันที — shode-house **capture อัตโนมัติ แต่ promote ต้องผ่าน gate** (NO MAGIC + invariant) → self-improving โดยไม่ drift

## When NOT to use

- **ใน hot PEV loop** — distill/gate ห้ามรัน inline (จะทำ loop สะดุด). hot path = capture อย่างเดียว
- **Project เพิ่งเริ่ม / lesson < threshold** — ยังไม่มี recurrence pattern พอ distill
- **Lesson เฉพาะ project** ที่ไม่ใช่ cross-project pattern — อยู่ project ตลอด ไม่ promote (YAGNI)
- **Auto-ship skill** — ห้าม; ทุก promote ผ่าน human + check_index/lint + eval-harness

## Required inputs — refuse without

- [ ] **Lessons store** (`.shode-house/lessons.md` ของ project หรือ bd `-t lesson`) — ห้าม distill จาก memory ลอย ๆ
- [ ] **Recurrence threshold N** (default 3 — pattern ต้องเจอ ≥ N project/bd ก่อน promote)
- [ ] **Gate owner** (human sign-off — maintainer; ห้าม agent self-approve promote)
- [ ] **Eval baseline** (eval-harness regression ก่อน promote skill เปลี่ยน default)

---

## 🔒 Non-blocking guarantee (🔴 กฎกันสะดุด — สำคัญสุด)

loop จะ **ไม่สะดุด** ถ้าแยก 2 path เด็ดขาด:

### Hot path (ใน PEV loop — ห้าม block)
- **Capture = append-only บรรทัดเดียว** (`bd remember <lesson>` ที่ Phase 4 — มีอยู่แล้ว) → near-zero cost, **ไม่บล็อก bd close**
- **session_start load = bounded** — top-N lesson (default 5) caveman-compressed เท่านั้น; **ห้ามโหลดทั้ง store** → context ไม่บวม → ไม่ช้า
- bd ปิดได้ทันที — **ไม่รอ** distill/gate/promote

### Cold path (offline / out-of-band — อยู่นอก loop จึงสะดุดไม่ได้)
- distill (recurrence ≥ N → candidate draft) + human gate + check_index/lint + eval-harness → รันแยก (maintainer-trigger / schedule) เหมือน eval-harness "offline, ไม่อยู่ใน /implement loop"
- promote เข้า bucket = ทำตอนว่าง, ไม่เกี่ยวกับ bd ที่กำลังวิ่ง

> สะดุดเมื่อไหร่: ถ้าเอา distill/gate ไปไว้ใน hot loop หรือ load lessons แบบ unbounded. กฎนี้ห้ามทั้งสอง

---

## 🗂️ Plugin vs Project level (2 ระดับ self-improving)

| ส่วน | อยู่ที่ | บทบาท |
|---|---|---|
| **skill `learning-loop`** (method) | **Plugin** | วิธี capture/distill/gate — reusable, human-authored, invariant-checked |
| **Lessons store / captured state** | **Project** (`.shode-house/lessons.md` / bd) | lesson เฉพาะ codebase/domain — ไม่ปน plugin |
| **Promote lesson → skill จริง** | **Plugin** (เฉพาะ cross-project) | ผ่าน gate offline เท่านั้น |

**ตัดสิน promote:**
- lesson **เฉพาะ project นี้** (quirk โค้ด, business rule) → อยู่ project ตลอด, **ไม่ขึ้น plugin** (กัน plugin บวม noise)
- pattern **ข้าม project** (เจอซ้ำ ≥ N project) → distill → gate → promote เข้า plugin bucket → ทุก project ได้ใช้

ผล: **Project-level** (ส่วนใหญ่) = local, async, ไม่แตะ plugin · **Plugin-level** (นาน ๆ ครั้ง) = ผ่าน gate, ไม่ drift

---

## 🔁 Pipeline (capture → distill → gate → promote)

```
[HOT] Phase 4 Triage: bd remember <lesson>      ← capture (non-blocking, มีอยู่แล้ว)
        ↓ append → .shode-house/lessons.md (project, bd-first)
[HOT] session_start: load top-N compressed lessons → context (bounded)
- - - - - - - - - - (loop ไม่ข้ามเส้นนี้) - - - - - - - - - -
[COLD] distill (offline): recurrence ≥ N → draft candidate ใน skills/in-progress/
        ↓
[COLD] gate: human sign-off + check_index.py + lint.py + eval-harness regression
        ↓ ผ่าน
[COLD] promote: candidate → bucket จริง (workflow/ops/ui/...) + README index + CHANGELOG
```

- distill ใช้ **skill-creator** (มีอยู่) ช่วยร่าง candidate; ห้าม hand-wave
- promote = version bump (ตาม CLAUDE.md release rule + Cowork drag-drop test)
- ทุก candidate ต้องมี `## When NOT to use` + `## Required inputs` ก่อน gate (per skill-craft)

---

## Lessons store schema (`.shode-house/lessons.md` — project, bd-first)

มี bd → `bd create -t lesson "<one-line>" --notes "<context + recurrence count>"`; ไม่มี → append:

```md
## <date> · bd-<id> · <tag: perf|bug|design|domain|process>
- lesson: <สิ่งที่เรียนรู้ 1 บรรทัด>
- trigger: <สถานการณ์ที่เจอ>
- recurrence: <count ข้าม project ถ้ารู้>
- scope: project-only | cross-project-candidate
```

> prune + caveman-compress เป็นระยะ (consolidate-memory pattern) กัน store บวม → session_start load ช้า

---

## ห้าม

- ห้ามรัน distill/gate ใน hot PEV loop (= loop สะดุด)
- ห้าม load lessons store แบบ unbounded เข้า context (cap top-N + compress)
- ห้าม auto-promote / agent self-approve — human gate + invariant เท่านั้น
- ห้าม promote lesson ที่ recurrence < N (single-project noise → drift)
- ห้าม block bd close เพื่อรอ capture/distill — capture ต้อง append-only
- ห้าม copy lesson เฉพาะ project ขึ้น plugin (plugin = cross-project pattern เท่านั้น)

---

## Used by

- Oliver — Phase 4 capture trigger (non-blocking)
- Maintainer — offline distill + gate + promote (sole promoter)
- Patrick — retro consume (which lessons recur → OKR signal)
- eval-harness — regression gate ก่อน promote skill เปลี่ยน default
- skill-creator — ช่วยร่าง candidate ตอน distill
