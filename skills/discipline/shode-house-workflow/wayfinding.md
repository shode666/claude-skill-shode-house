---
name: wayfinding
description: Reference (lazy-load) ของ `shode-house-workflow` — Map mode สำหรับงานที่ใหญ่เกิน 1 session และยังมองไม่เห็นทาง. โหลดเมื่อ user มาด้วยไอเดียก้อนใหญ่ที่ยังไม่รู้ว่าจะเริ่มตรงไหน
---

# Wayfinding — Map mode (งานใหญ่เกิน 1 session, ยังมองไม่เห็นทาง)

> Adapted จาก [mattpocock/skills · wayfinder](https://github.com/mattpocock/skills) (MIT) — port ไป `bd` + PEV loop ของเรา
> **Owner**: Oliver (ถือแผนที่) + Patrick (destination + scope) · Bella/Sara (decision ticket ที่เป็น spec/architecture) · Domain expert (decision ที่ต้องใช้ความรู้ domain)

## ปัญหาที่มันแก้ (ช่องที่ pipeline เดิมไม่มี)

```
ไอเดียก้อนใหญ่ที่ยังมองไม่เห็นทาง
        ↓  ← ❌ เดิมไม่มีอะไรตรงนี้
   Map mode (ไฟล์นี้)
        ↓
Phase 0 Discover (Patrick) → Phase 1a Spec (Bella ∥ Sara) → ... → drain
```
- `/design-system` สมมติว่า **รู้รูปงานแล้ว** — ผลิต spec ของ **1 bd** ไม่ใช่ของ initiative ทั้งก้อน
- `drain` ต้องการ item ที่ **verified + concrete + independent** อยู่แล้ว — ไม่ได้สร้าง ready set
- ไม่มี Map → ได้ 2 ทางที่แย่ทั้งคู่: **spec ยักษ์ล่วงหน้า** (Bella เขียนทุกอย่างจากการเดา = anchoring + เขียนทิ้ง) หรือ **ค่อย ๆ ไหลไปเรื่อย ๆ** (SCOPE DRIFT ที่ไม่มีใครจับได้)

## หลักการ

**หาทาง ไม่ใช่พุ่งใส่ปลายทาง.** Map คือแผนที่ร่วมของ **decision ticket** — ticket ที่ผลลัพธ์คือ *การตัดสินใจ* ไม่ใช่ชิ้นงานที่ build เสร็จ. แก้ทีละใบจนกว่าทางจะชัด

🔴 **Plan อย่างเดียว ห้าม do** — Map จบเมื่อ "ไม่เหลืออะไรต้องตัดสินใจก่อนลงมือ" แล้ว hand off เข้า pipeline ปกติ
ความรู้สึกอยากลงมือทำเลย = สัญญาณว่ามาถึงขอบแผนที่แล้ว → **hand off** ไม่ใช่ทำต่อ (ยกเว้น Notes ของ effort นั้นเขียนไว้ว่าให้ทำ)

## โครงสร้างบน `bd`

| ของ wayfinder | บน bd |
|---|---|
| Map | `bd create "MAP: <destination>" -t map -p1` — 1 issue เป็น canonical artifact |
| Ticket | `bd create "<คำถาม>" -t decision` แล้ว `bd link <map> <ticket> parent-child` |
| Blocking | `bd link <a> <b> blocks` — ใช้ native เสมอ เพื่อให้ `bd ready` คำนวณ frontier ให้เอง |
| Claim | `bd update <id> --claim` **ก่อนเริ่มงานทุกครั้ง** — unassigned = ยังไม่มีใครจับ |
| Frontier | `bd ready --json` = open + unblocked + unclaimed |
| Resolution | `bd close <id> --reason "<คำตอบ>"` + append 1 บรรทัดเข้า Decisions so far ของ map |

> tracker อื่น (GitHub/Linear/Jira) → ใช้ native label + parent-child + blocking ของตัวเอง; abstraction เดิม `tracker.link(from,to,type)` ใน `shode-house-workflow` ครอบให้แล้ว

### Map body (`bd update <map> --notes`)

```markdown
## Destination
<ถึงปลายทางแล้วหน้าตาเป็นยังไง — spec ที่ส่งต่อได้ / decision ที่ล็อคแล้ว / การเปลี่ยนที่ทำเสร็จ. 1-2 บรรทัด>

## Notes
<domain · skill ที่ทุก session ต้องโหลด · engagement mode · ข้อกำหนดประจำ effort นี้>

## Decisions so far
- [<ชื่อ ticket ที่ปิดแล้ว>](<link>): <gist ของคำตอบ 1 บรรทัด>

## Not yet specified
<fog: คำถามที่รู้ว่ากำลังจะมา แต่ยังตั้งให้คมไม่ได้>

## Out of scope
<สิ่งที่ตัดออกจาก effort นี้อย่างตั้งใจ + เหตุผล + link ticket ที่ปิดไป>
```

🔴 **Map = index ไม่ใช่คลัง** — decision อยู่ที่ ticket ของมันที่เดียว; map แค่ gist + link. ห้าม list ticket ที่ยังเปิด (หาเอาจาก `bd ready`)

## Fog of war — แผนที่ไม่สมบูรณ์โดยตั้งใจ

อย่าวาดสิ่งที่ยังมองไม่เห็น. พอปิด ticket หนึ่ง หมอกข้างหน้ามันจะจาง → **graduate** ส่วนที่คมพอแล้วเป็น ticket ใหม่ ทีละก้อน

**เป็น ticket หรือเป็น fog?** เกณฑ์คือ **ตั้งคำถามให้คมได้ตอนนี้ไหม** ไม่ใช่ *ตอบได้ตอนนี้ไหม*
- **ticket** เมื่อคำถามคมแล้ว — ถึงจะยัง blocked อยู่ก็ตาม
- **Not yet specified** เมื่อยังตั้งคำถามให้คมไม่ได้ · **ห้ามซอย fog เป็นชิ้นขนาด ticket ล่วงหน้า** (หมอกก้อนเดียวอาจกลายเป็นหลาย ticket หรือศูนย์ ticket ก็ได้)

## Out of scope = ที่อยู่ของ Philosophy #4 (SCOPE DRIFT)

หมอกจับตัวเฉพาะ **ทางไปหา destination** — งานที่เลยปลายทางไปแล้ว = **out of scope** ไม่ใช่ fog
เดิม SCOPE DRIFT เป็นกฎเฝ้าระวังที่ **ไม่มีที่ให้บันทึก** ว่า "อันนี้เราตัดออกแล้วนะ" → ตอนนี้มี

ticket ที่มีอยู่แล้วแต่พบว่าอยู่เลย destination → **ปิดมัน** (ticket ที่ปิดแล้ว = พ้น frontier แน่นอน) + เขียน 1 บรรทัดใน Out of scope พร้อมเหตุผล
❌ ห้ามใส่ใน Decisions so far — นั่นคือบันทึกของ *เส้นทางที่เดินจริง* ขอบเขตที่ตัดออกไม่ใช่ก้าวหนึ่งบนเส้นทาง
out of scope ไม่มีวัน graduate; จะกลับมาได้ต่อเมื่อ **redraw destination** ซึ่งนับเป็น effort ใหม่ ไม่ใช่การทำต่อ

## Ticket types → agent ของเรา

ทุก ticket เป็น **HITL** (ต้องมีคนจริงตอบ) หรือ **AFK** (agent เดินเอง) — ละเอียดกว่า Engagement Mode ที่ตั้งครั้งเดียวทั้ง engagement
🔴 HITL ticket ปิดได้ด้วยบทสนทนาจริงเท่านั้น — **agent ห้ามตอบแทนคน** (grilling ที่ตอบคำถามตัวเองคือการโกง)

| Type | HITL? | ใครรับ | ใช้เมื่อ |
|---|---|---|---|
| **research** | AFK | Domain expert (regulation/business) · Sara (tech/vendor) — โหลด `shode-house-evidence` § Project/Domain Evidence, **primary source เท่านั้น** | ต้องรู้ข้อเท็จจริงนอก working directory ก่อนตัดสินใจ |
| **prototype** | HITL | Uma (หน้าตา/flow) · Dave (logic/state) — throwaway ตาม `dev-gate` § When NOT to use, จบแล้ว commit ไว้ throwaway branch + บันทึก verdict | คำถามคือ "หน้าตาควรเป็นยังไง / behave ยังไง" |
| **grilling** | HITL | Oliver · Bella · Patrick · Sara — ใช้ **frontier model** ใน `shode-house-discipline` § Clarifying | ค่าเริ่มต้น: เป็นการคุยเพื่อตัดสินใจ |
| **task** | ทั้งคู่ | Aaron (provision/access) · owner (สมัคร service, ขอสิทธิ์) | ไม่มีอะไรให้ตัดสินใจ แต่ decision ติดอยู่จนกว่างานนี้จะเสร็จ. ปิดแล้วบันทึก fact ที่ ticket หลังต้องใช้ (ที่อยู่ credential, URL ใหม่, จำนวนแถว) |

## เรียกด้วยชื่อ ห้ามเรียกด้วยเลข (🔴)

ทุกอย่างที่ **คน** อ่าน (broadcast, Decisions so far, รายงาน) → เรียก ticket **ด้วยชื่อของมัน** ไม่ใช่ `bd:42`
กำแพง `bd:42, bd:43, bd:44` อ่านไม่รู้เรื่อง; ชื่ออ่านปราดเดียวเข้าใจ. id/URL ไม่ได้หายไป — มันอยู่ *ข้างใน* ลิงก์ของชื่อ ไม่ใช่มาแทนชื่อ
> Agent Tag Prefix (`[Oliver|state:...|bd:42]`) ยังใช้ id ตามเดิม — นั่นเป็น metadata ของ machine คนละเรื่องกับเนื้อความ

## 2 โหมด

🔴 **ห้ามปิดเกิน 1 ticket ต่อ session** — ยกเว้น research ticket (fan-out ขนานได้)
เหตุผล: ticket ถูกออกแบบให้พอดี 1 session; ปิดสองใบใน session เดียวแปลว่าใบที่สองถูกตัดสินด้วย context ที่เหนื่อยแล้วและปนกับใบแรก

### A. Chart the map (user มาด้วยไอเดียก้อนใหญ่)

1. **ตั้งชื่อ destination** — grill (frontier model) + สร้าง domain glossary ให้ชัดว่า map นี้กำลังไปหาอะไร. **destination ตรึง scope จึงต้องเสร็จก่อนเพื่อนเสมอ**
2. **สำรวจ frontier แบบ breadth-first** — กวาดให้ทั่วพื้นที่ ไม่ลงลึกเส้นใดเส้นหนึ่ง; หา decision ที่เปิดอยู่ + ก้าวแรกที่ทำได้เลย
   **ถ้าไม่เจอ fog เลย** (ทางชัดอยู่แล้ว ทั้งงานจบใน session เดียว) → **ไม่ต้องมี map** หยุดแล้วถาม user ว่าจะเอายังไงต่อ (อาจไป `/design-system` ตรง ๆ)
3. **สร้าง map** — Destination + Notes ครบ, Decisions so far ว่าง, หมอกร่างลง Not yet specified
4. **สร้าง ticket เท่าที่ตั้งคำถามได้คม** เป็น child ของ map แล้ว **wire blocking เป็นรอบที่สอง** (issue ต้องมี id ก่อนถึงอ้างกันได้)
5. **ยิง research subagent ขนาน** สำหรับทุก research ticket ที่เพิ่งสร้าง — เขียนผลลง `outputs/<map-id>/research-<name>.md` แล้ววาง path ไว้ที่ ticket (Handoff Contract: ส่ง path ไม่ส่งเนื้อหา)
6. **หยุด** — charting เป็นงานของ session เดียว มันไม่ปิด ticket ให้ใคร

### B. Work through the map (user มาพร้อม map id)

1. อ่าน **map** อย่างเดียว (low-res) — ห้ามดึง body ของทุก ticket มากอง
2. เลือก ticket: user ระบุมา → ใช้อันนั้น; ไม่ระบุ → ใบแรกของ frontier. **claim ก่อนแตะงาน**
3. แก้มัน — **zoom เมื่อจำเป็น**: ดึง body ของ ticket ที่เกี่ยว/ที่ปิดแล้วเป็นราย ๆ ไป; โหลด skill ตามที่ `## Notes` สั่ง
4. บันทึกผล: `bd close <id> --reason "<คำตอบ>"` → `bd show <id>` ยืนยัน CLOSED (M8) → append 1 บรรทัดเข้า Decisions so far
5. **graduate fog** ที่คำตอบนี้ทำให้คมพอแล้ว → สร้าง ticket ใหม่ (create-then-wire) + **ลบ patch นั้นออกจาก Not yet specified** เพื่อไม่ให้มันอยู่สองที่
   คำตอบเผยว่า ticket ใด (ใบนี้หรือใบอื่น) อยู่เลย destination → **rule out of scope** ไม่ใช่แก้มันบนเส้นทาง
   คำตอบล้มส่วนอื่นของแผนที่ → แก้หรือลบ ticket เหล่านั้น

> user รัน ticket ที่ unblocked ขนานกันได้ → **คาดหมายว่ามี session อื่นแก้ tracker พร้อมกัน** อ่าน `bd show` ใหม่ก่อนเขียนทับเสมอ

## จบ map แล้วไปไหนต่อ

ทางชัด (ไม่เหลือ decision) → destination กลายเป็น input ของ pipeline ปกติ:
- destination = spec → `/design-system` (Bella ∥ Sara) ต่อได้ทันที เพราะรูปงานนิ่งแล้ว
- destination = ชุดงานที่ concrete + independent → `drain`
- destination = decision ล้วน ๆ (เช่นเลือก platform) → `bd close` map + บันทึกเป็น ADR (`shode-house-deliverable` § ADR Lifecycle)
