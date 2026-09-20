---
name: decompose
description: Split an agreed, signed-off scope into small, independently verifiable outcome slices with owners, acceptance criteria and explicit dependencies. Not for work whose finished shape is still unclear, tasks already small, or a backlog already verified and ready.
---

# Decompose (epic → leaf task ที่ลงมือได้)

> **Owner**: Bella (จาก user story) + Oliver (จาก XL triage). Co-pilot: Sara (interface contract), Patrick (ลำดับตาม outcome), Quinn (test slice)
> Use the confirmed tracker/evidence home, including Markdown. Beads is not required. Planning does not authorize creating remote tickets: draft locally when writes are unavailable or unapproved, mark pending sync, and never claim remote creation.

## When NOT to use

- **ยังมีหมอก** — ยังตอบไม่ได้ว่า "เสร็จ" หน้าตายังไง หรือมี decision ค้างที่ต้องตัดก่อน → **`shode-house-workflow/wayfinding.md` (Map mode)** ก่อน. แตกหมอกเป็น task = ซอยสิ่งที่ยังไม่รู้ว่าคืออะไร
- **งานเล็กอยู่แล้ว** — 1 task จบใน pipeline เดียว (S/M) → อย่าแตก แตกแล้วจ่ายค่า coordination ฟรี ๆ
- **แตกเพื่อให้ดูมีความคืบหน้า** — no verifiable behavior, risk reduction or named downstream benefit = rethink the slice (see Tracer bullet)
- **backlog ที่ verified + concrete แล้ว** → do not split again; use `drain` only for an eligible ready frontier. If all tasks are legitimately blocked, record the blockers and checkpoint instead of starting workers.

## Required inputs — refuse without

- [ ] **Spec หรือ BRD ที่ sign-off แล้ว** (Phase 1a) — แตกจาก AC/FR ไม่ใช่จากชื่อ feature
- [ ] **Outcome ของก้อนใหญ่** 1-2 บรรทัด — ใช้ตัดสินว่า leaf ไหน "อยู่ในทาง" (ขาดข้อนี้ = แตกได้ แต่เรียงลำดับไม่ได้)
- [ ] **Confirmed record location and write authority** — publish only where authorized; an explicitly labelled local draft can hold task IDs and dependencies until remote sync is available
- [ ] **Interface contract** ถ้าข้าม service/module (Sara กำหนดก่อน — ดู § Chunk)

ขาดข้อใด → list สิ่งที่ขาด แล้วหยุด ห้ามเดา

## 🎯 Tracer bullet — เกณฑ์เดียวที่ตัดสินว่าแตกถูกหรือผิด

**leaf 1 ใบ = outcome ที่ verify ได้จริง ผ่านเฉพาะ layer ที่เกี่ยวข้อง** — ไม่เพิ่ม UI, DB หรือ abstraction เพียงเพื่อให้ครบชั้น. Backend fixes, security repairs and enabling work are valid slices when their acceptance and consumer benefit are explicit.

```
✅ ถูก (vertical)                        ❌ ผิด (horizontal)
"ผู้ใช้ขอคืนเงิน 1 รายการได้"            "สร้าง DB schema ทั้งหมด"
  relevant layers + acceptance tests       "ทำ API ทุก endpoint"
  merge แล้วมีคนใช้ได้จริง                 "ต่อ UI ทั้งหมด"
                                          merge 2 ใบแรกแล้วยังไม่มีอะไรใช้ได้
```

horizontal slicing เป็น anti-pattern เดียวกับที่ `dev-gate` ห้ามในระดับ test — ที่นี่คือระดับ backlog: **ล็อคโครงสร้างก่อนเข้าใจงาน แล้วรู้ตัวตอนใบสุดท้าย**

**Test**: what behavior, risk reduction or prerequisite does this slice prove? A prerequisite may enable a later user outcome; name that consumer and verify the prerequisite independently instead of inventing a user-facing feature.

## 📏 เล็กพอหรือยัง

INVEST ของ Bella มี "Small" แต่ไม่มีตัวเลข — ที่นี่ให้เกณฑ์ที่ตรวจได้:

- [ ] **1 leaf = bounded outcome** with a durable checkpoint; apply the harness review tier and relevant phases. Session interruption does not require splitting or replaying completed work.
- [ ] **AC ≤ ~5 ข้อ** — เกินนั้นมักมีมากกว่า 1 behavior ปนอยู่
- [ ] **แตะ module/service เดียว** — ข้าม service = ต้องมี interface contract ก่อน (§ Chunk)
- [ ] **verify ได้ด้วยตัวมันเอง** — มี test/หลักฐานที่บอกว่า "ใบนี้เสร็จ" โดยไม่ต้องรอใบอื่น
- [ ] **Describe one outcome** for a user or named consumer; a layer name alone does not explain its acceptance or value

ยังไม่ผ่าน 2 ข้อขึ้นไป → แตกต่อ. **แตกได้ ≤ 2 ชั้น** (epic → leaf); ลึกกว่านั้นแปลว่า outcome กว้างเกิน → กลับไปคุย scope กับ Patrick

## 🔗 Blocking edge — ประกาศตอนสร้าง ไม่ใช่ค่อยไปเดาทีหลัง

🔴 ทุกใบต้องประกาศ dep ของตัวเอง **ตอนสร้าง**: list real blockers or explicitly record none. Missing dependency information is not proof of independence; an empty verified list is valid.

**Create then wire** when the tracker needs existing IDs; atomic creation with dependencies is also valid. In Markdown use stable local IDs and links. This illustrative sequence is tracker-neutral, not shell syntax:

```text
create refund request slice -> A
create request-history slice -> B
create refund-approval slice -> C
record B blocked by A; C blocked by A; A has no blockers
associate A, B, C with the epic
read back graph and ready tasks -> A (if no other blockers apply)
```

**Edge criteria**: `blocks` means a real prerequisite: output/interface, data, access or approval needed by the dependent task. Ordering preferences belong in tracker priority, not dependency edges. False edges unnecessarily prevent parallel work.

**Verify หลัง wire (🔴 ห้ามข้าม)**: read back task IDs, parent links, dependency direction and ready tasks. If none are ready, distinguish a cycle/bad edge from legitimate external dependencies, pending approval, deferred work or completed scope. Record the real blocker; never delete a valid dependency just to obtain ready work.

## 🧩 Chunk — เมื่อต้องข้าม service/module

Sara defines the interface contract before parallel implementation. An agreed contract can unblock independent coding against a test double, but does not remove real data, deployment, approval or integration dependencies.

```
Agreed A↔B contract + independent ownership -> coding may proceed in parallel
Integration acceptance still needs the real dependencies and evidence
```
contract เปลี่ยนกลางทาง = **spec change** → canonical record revision ตาม drift M5 ไม่ใช่แก้เงียบ ๆ

## ✂️ Process

1. **อ่าน spec + outcome** — ถ้าเป็น XL ให้ดู T-shirt ต่อ module จาก `/design-system --estimate` (ถ้ามี) เป็นจุดตั้งต้นของการแบ่ง
2. **ร่าง leaf จาก AC ไม่ใช่จาก layer** — ไล่ user story/AC แล้วถามทีละข้อว่า "ข้อนี้ merge เดี่ยว ๆ แล้วมีคนได้อะไรไหม"
3. **เช็คขนาด** (§ เล็กพอหรือยัง) → ยังใหญ่ก็แตกต่อ (≤ 2 ชั้น)
4. **หา dep จริง** — เขียน edge ลงกระดาษก่อน แล้วถามทุกเส้นว่า "ถ้าไม่มีเส้นนี้ ใบหลังพังตรงไหน" ตอบไม่ได้ = edge ปลอม ตัดทิ้ง
5. **Create and link** in the confirmed tracker (§ Blocking edge), associating each leaf with its epic; draft-only when remote writes are not authorized
6. **Read back and verify** the graph and ready set; retain evidence or mark pending sync, not a fabricated remote result
7. **ส่งต่อ**: one ready leaf → Oliver continues the approved implementation workflow with its canonical ID; several concrete independent leaves → `drain` after checking its applicability. No additional public command is required.

## 🚫 Anti-pattern

| อาการ | ทำไมผิด | แก้ |
|---|---|---|
| leaf ชื่อเป็น layer (`"ทำ API"`, `"ต่อ DB"`) | lacks a stated outcome or consumer | name the verified behavior, risk reduction or prerequisite benefit |
| แตกก่อนมี spec | ซอยสิ่งที่ยังไม่รู้ว่าคืออะไร | wayfinding (fog) → design-system (spec) → ค่อยแตก |
| ทุกใบ `blocks` กันเป็นสายโซ่ | ส่วนใหญ่เป็น priority ไม่ใช่ dep → drain ทำขนานไม่ได้ | ตัด edge ที่ตอบไม่ได้ว่าพังตรงไหน |
| แตก 4-5 ชั้น | outcome กว้างเกินจะเป็น 1 epic | กลับไปคุย scope กับ Patrick |
| leaf ไม่มี AC | ไม่มีใครรู้ว่าเสร็จเมื่อไหร่ → Anti-Puppet Done | reference canonical AC IDs/revision and add slice-specific checks; do not duplicate the full spec |

## Skill composition (where to go next)

| สถานการณ์ | ไปไหน | เพราะ |
|---|---|---|
| ยังมีหมอก ตอบไม่ได้ว่าเสร็จหน้าตายังไง | → `shode-house-workflow/wayfinding.md` | Map + decision ticket ก่อน (decompose ต้องการ spec ที่นิ่ง) |
| spec ยังไม่มี | → `/design-system` | Bella ∥ Sara ผลิต BRD + ADR ก่อน |
| แตกเสร็จ มี frontier หลายใบ concrete + file-disjoint | → `drain` | fan-out worktree + serial cherry-pick + close-on-done |
| แตกเสร็จ frontier ใบเดียว | → Oliver continues with canonical task ID | approved pipeline, no extra public command |
| leaf ข้าม service ยังไม่มี contract | → Sara (`api-contract` skill) | contract คือสิ่งที่ทำให้ chunk ขนานได้ |
