# Diagnose — Full-path investigation

Load only for Full diagnosis, before Step 2. Owner: the assigned Dave, Chris or Quinn.
Use the core skill's redaction, scope and authorization constraints throughout.

### 2. Reproduce + Minimise

รัน loop → ดูมันแดง แล้วยืนยัน:
- [ ] อาการที่ออกมาคือ **อาการที่ user บอก** ไม่ใช่ failure ตัวข้าง ๆ (bug ผิดตัว = fix ผิดที่)
- [ ] แดงซ้ำได้หลายรอบ
- [ ] จับอาการไว้แล้ว (error message / output ที่ผิด / ตัวเลขเวลา) เพื่อให้ step หลังตรวจได้ว่า fix ตรงอาการ

**Minimise** (Full path; fast path ข้ามได้) — พอแดงแล้ว ย่อ repro ให้เหลือ **scenario เล็กที่สุดที่ยังแดง**: ตัด input/caller/config/data/step **ทีละอย่าง** แล้ว re-run ทุกครั้ง เก็บเฉพาะที่ load-bearing
จบเมื่อ **ตัดอะไรออกอีกก็เขียว**
> คุ้มเพราะ: hypothesis space เล็กลงใน Step 3 (เหลือของให้สงสัยน้อยลง) + ได้ regression test สะอาดใน Step 4 ฟรี

ห้ามไป Step 3 ก่อน reproduce **และ** minimise

### 3. Hypothesise + Instrument

**สร้าง 3-5 hypothesis เรียงอันดับ ก่อนทดสอบข้อใดข้อหนึ่ง** (fast path: 1 ข้อพอ ถ้า error ชี้ตรงจุดอยู่แล้ว) — สร้างข้อเดียวแล้วลุยเลย = anchor ติดไอเดียแรกที่ดูเข้าท่า
ทุกข้อต้อง **falsifiable** — เขียน prediction ให้ได้:
```
"ถ้า <X> เป็นสาเหตุ แล้ว <เปลี่ยน Y> จะทำให้ bug หาย / <เปลี่ยน Z> จะทำให้แย่ลง"
```
เขียน prediction ไม่ได้ = vibe ไม่ใช่ hypothesis → ทิ้งหรือลับให้คม
**โชว์ ranked list ให้ user ก่อนทดสอบ** (เฉพาะ Full path; fast path ไม่ต้องรบกวน) — user มัก re-rank ได้ทันที ("เพิ่ง deploy ข้อ 3 เมื่อวาน") หรือรู้ว่าข้อไหนตัดไปแล้ว. checkpoint ราคาถูก ประหยัดเวลามาก — แต่ไม่ block ถ้า user AFK

**Instrument** — probe 1 ตัว = 1 prediction จาก list, **เปลี่ยนทีละตัวแปร**
1. **Debugger / REPL** ถ้า env รองรับ — 1 breakpoint ชนะ 10 log
2. **Targeted log** ที่ boundary ซึ่งแยก hypothesis ออกจากกัน
3. ห้าม "log ทุกอย่างแล้ว grep"

🔴 **ทุก debug log ใส่ prefix เฉพาะ** เช่น `[DEBUG-a4f2]` → cleanup = grep prefix เดียว. log ที่ไม่ tag คือ log ที่รอดไปถึง prod; log ที่ tag คือ log ที่ตายแน่นอน

**Perf branch** — สำหรับ performance regression **log มักผิดทาง**: ตั้ง baseline measurement ก่อน (timing harness / `performance.now()` / profiler / query plan) แล้วค่อย bisect. **วัดก่อน แก้ทีหลัง**
