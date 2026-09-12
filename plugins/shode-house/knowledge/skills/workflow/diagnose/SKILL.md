---
name: diagnose
description: |
  [WHAT] Structured debugging methodology — บังคับ reproduce → isolate → fix → prevent ก่อน "ลอง fix"; ห้าม patch โดยไม่มี root cause.
  [WHEN] ทันทีที่ user รายงาน bug.
  [TRIGGER] /shode-house:diagnose, "พัง", "ไม่ทำงาน", "ช้า", "ทำไมถึง", "bug".
---

# Diagnose (structured debugging)

> Inspired by mattpocock/skills (engineering/diagnose) — adapted for shode-house

> **Owner**: Chris (review) + Quinn (test) + Dave (implement) — เปิด skill นี้เมื่อมี bug/perf

## หลักการ

**No fix without a loop that goes red** — ก่อนตั้งสมมติฐานใด ๆ ต้องมี **คำสั่งเดียว** ที่รันแล้วเห็น bug จริง. "ลองเปลี่ยนดู" = anti-pattern

## 🔒 Redact ก่อน paste (🔴 อ่านก่อนเริ่ม)

skill นี้บังคับให้ paste command/output/artifact เป็นหลักฐาน (per evidence protocol) — **ความลับต้องถูกลบก่อน**:
- เขียน `<REDACTED>` แทน secret/token/auth header/PII ทุกครั้ง
- build loop ผ่าน **env var** เพื่อให้ credential อยู่ใน environment ไม่ใช่ในสิ่งที่ paste
- captured artifact (HAR / log dump / request trace) พก auth header มาด้วยเสมอ → quote **เฉพาะบรรทัดที่มี signal**
- redact แล้วข้อมูลไม่พอวินิจฉัย → บอก user ตรง ๆ แล้วขอเพิ่ม ห้ามเดาต่อ

## When NOT to use

- ยังไม่มี symptom ที่ reproduce ได้และไม่มี log/error — ไปเก็บหลักฐานก่อน
- Feature request ที่ถูกเรียกว่า "bug" — นั่นคืองานของ Bella/Patrick
- Known issue ที่มี bd + root cause แล้ว — ไป fix ตรง ๆ

## Required inputs — refuse without

- [ ] Symptom ที่ระบุได้ (error message / behavior ที่ผิด / metric ที่เปลี่ยน)
- [ ] วิธี reproduce หรือช่องทางที่จะหามาได้ (env, ข้อมูล, ขั้นตอน)
- [ ] Access ไป log / trace / ตัว service — ไม่มี = ระบุว่าติดตรงไหน ห้ามเดา root cause
- [ ] Redact ผ่านแล้ว (§ Redact ก่อน paste)

## เลือกความเข้มก่อน (ไม่ใช่ทุก bug คุ้มกับ 5 ขั้น)

| ระดับ | เมื่อไหร่ | ทำอะไร |
|---|---|---|
| **Fast path** | error message ชี้ตรงจุด · deterministic · 1 ไฟล์ · แก้แล้วเห็นผลทันที (typo, off-by-one, null guard ที่ขาด) | ทำ **ขั้น 1 (loop) → 4 (fix + regression test)** พอ · ข้าม minimise/hypothesis list แล้วบอกใน report ว่าข้าม |
| **Full** | flaky · perf regression · ข้าม service · reproduce ไม่ตรงกับที่ user เจอ · fast path fix แล้วยังไม่หาย | ครบ 5 ขั้น |

เลือก fast path แล้วพลาด (fix ไม่หาย / bug อื่นโผล่) → **ขึ้น Full ทันที ห้ามลองเดาต่อ**

## 5 Steps

### 1. สร้าง feedback loop ที่ **tight** และ **red-capable** (🔴 นี่คือหัวใจ ที่เหลือ mechanical)

มี loop ที่แดงกับ bug ตัวนี้ = เจอสาเหตุแน่ (bisect / test hypothesis / instrument ล้วนกิน loop นี้ทั้งนั้น)
ไม่มี loop = จ้อง code ให้ตายก็ไม่เจอ → **ทุ่มเวลาตรงนี้มากเป็นพิเศษ ก้าวร้าว สร้างสรรค์ ห้ามยอมแพ้**

**วิธีสร้าง — 3 อันแรกครอบเกือบทุกเคส**
1. **Failing test** ที่ seam ซึ่งเข้าถึง bug · 2. **curl / HTTP script** ยิงใส่ dev server · 3. **CLI + fixture** diff stdout กับ snapshot ที่รู้ว่าถูก
ทั้งสามไม่ได้ผล → เปิด **`loop-ladder.md`** (ไฟล์ข้าง SKILL.md นี้): headless browser · replay captured trace · throwaway harness · property/fuzz · bisect harness · differential loop · HITL script

**ลับ loop ให้คม** (treat the loop as a product) — ได้ loop แล้วยังไม่พอ:
- เร็วขึ้นได้ไหม (cache setup, ข้าม init ที่ไม่เกี่ยว, แคบ scope ของ test)
- signal คมขึ้นได้ไหม (assert **อาการที่ user บอก** ไม่ใช่ "ไม่ crash")
- deterministic ขึ้นได้ไหม (pin เวลา, seed RNG, isolate filesystem, freeze network)
> loop 30 วินาทีที่ flaky แทบไม่ต่างจากไม่มี loop; loop 2 วินาทีที่ deterministic = superpower

**Bug ที่ไม่ deterministic**: เป้าหมายไม่ใช่ repro สะอาด แต่คือ **ดัน reproduction rate ให้สูงพอจะ debug** — ยิง trigger 100× · parallelise · stress · แคบ timing window · แทรก sleep. flake 50% debug ได้, 1% ไม่ได้

**✅ เงื่อนไขจบ Step 1 (ห้ามข้ามไป Step 2 ก่อนครบ)**
ระบุได้ว่า **คำสั่งเดียว** คืออะไร (path ของ script / test invocation / curl) และ **รันไปแล้วอย่างน้อย 1 ครั้ง** พร้อม paste invocation + output (redacted):
- [ ] **red-capable** — วิ่งผ่าน code path ของ bug จริง และ assert อาการที่ user บอก → แดงได้ตอนนี้ เขียวได้หลัง fix (ไม่ใช่แค่ "รันแล้วไม่ error")
- [ ] **deterministic** — verdict เดิมทุกรอบ (flaky: rate สูงและคงที่)
- [ ] **เร็ว** — หน่วยวินาที ไม่ใช่นาที
- [ ] **agent รันเองได้** — ไม่ต้องมีคนกดกลางทาง

🔴 **ห้ามกระโดดไปสรุปสาเหตุก่อนมีคำสั่งนี้** — นั่นคือ failure mode ที่ skill นี้มีไว้กัน
✅ **อ่าน code ได้เต็มที่เพื่อ *สร้าง* loop** (หา route/entry point, test setup, fixture, วิธี boot ระบบ, ชื่อ config) — หลายระบบสร้าง harness ไม่ได้เลยถ้าไม่อ่านก่อน
เส้นแบ่ง: อ่านเพื่อ **"จะ trigger มันยังไง"** = ส่วนหนึ่งของขั้นนี้ · อ่านเพื่อ **"มันน่าจะพังเพราะ..."** = ข้ามขั้นตอน

**สร้าง loop ไม่ได้จริง ๆ**: หยุดแล้วบอกตรง ๆ + list สิ่งที่ลองแล้ว + ขอ (ก) access environment ที่ repro ได้ (ข) captured artifact ที่ redact แล้ว (HAR/log/core dump/วิดีโอพร้อม timestamp) หรือ (ค) อนุญาตให้ใส่ instrumentation ชั่วคราวใน production — **ห้ามเดาต่อโดยไม่มี loop**

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

### 4. Fix + Regression test

เขียน regression test **ก่อน** fix — แต่เฉพาะเมื่อมี **seam ที่ถูกต้อง** คือ seam ที่ test ได้เจอ bug pattern จริงอย่างที่มันเกิดที่ call site

🔴 **ไม่มี seam ที่ถูกต้อง = นั่นแหละคือ finding** — ถ้า seam ที่มีตื้นเกินไป (unit test ที่ replicate chain ที่ trigger bug ไม่ได้ / test caller เดียวทั้งที่ bug ต้องมีหลาย caller) การเขียน test ตรงนั้นให้ **false confidence**. บันทึกว่า **architecture กันไม่ให้ล็อค bug ตัวนี้ได้** แล้ว route ต่อ (Sara/Stan) — อย่าฝืนเขียน

มี seam ที่ถูก:
1. เปลี่ยน repro ที่ minimise แล้วเป็น failing test ที่ seam นั้น
2. ดูมัน fail
3. ใส่ fix — **root cause ไม่ใช่ symptom** (fix แล้ว bug อื่นโผล่ = ยังไม่ใช่ root cause) และเลือก **change ที่เล็กที่สุดที่ fix ได้**
4. ดูมัน pass
5. **รัน loop จาก Step 1 กับ scenario เต็ม (ที่ยังไม่ minimise) อีกครั้ง**

### 5. Cleanup + Prevent (บังคับก่อนบอกว่าเสร็จ)

- [ ] repro เดิมไม่ repro แล้ว (รัน loop จาก Step 1 ซ้ำ + paste output)
- [ ] regression test ผ่าน (หรือบันทึกไว้ว่าไม่มี seam ที่ถูกต้อง)
- [ ] instrumentation `[DEBUG-...]` ถูกลบครบ (`grep` prefix ยืนยัน + paste ว่าไม่เจอ)
- [ ] throwaway harness/prototype ถูกลบ หรือย้ายไปที่ที่ mark ชัดว่าเป็นของ debug
- [ ] **เขียน hypothesis ที่ถูกลงใน commit / PR message** — คนที่ debug คนต่อไปจะได้เรียนรู้
- [ ] pattern เดียวกันอาจมีที่อื่น → `grep` แล้วแก้ให้หมด
- [ ] doc ที่ทำให้เข้าใจผิด → แก้
- [ ] production incident → postmortem (`incident` skill)

## Hand-off pattern

```
Diagnose finished →
  - Chris: review fix + write regression unit test
  - Quinn: integration test เผื่อ pattern อื่น
  - Aaron: monitoring/alert ถ้าเป็น infra
  - Domain Expert: ถ้า business rule ผิด
```

## กฎที่ต้องทำ (positive form — v3.12)

- **fix ได้หลังมี loop ที่แดงเท่านั้น** — ไม่มี loop = ยังไม่ถึงขั้นเสนอ fix
- **ทุกการเปลี่ยน code ต้องมี hypothesis ที่เขียน prediction ได้** อยู่เบื้องหลัง
- **ship fix พร้อม regression test** (หรือพร้อมบันทึกว่าไม่มี seam ที่ถูกต้อง)
- **revert ก็ต้องเข้าใจก่อน** ว่ามันย้อนอะไรกลับบ้าง — revert คือการเปลี่ยน code ชนิดหนึ่ง กฎข้างบนใช้เหมือนกัน
- **postmortem โทษระบบ ไม่โทษคน** (blameless — `incident` skill)

## Skill composition (where to go next)

| Situation | Next skill | Reason |
|---|---|---|
| Bug อยู่ใน **production**, มี customer impact หรือ SLO burn | → `incident` | Reggie IC + war room + blameless postmortem (diagnose ไม่มี comms/severity) |
| Diagnosis เสร็จ → จะเขียน fix code | → `dev-gate` | TDD red-green-refactor + 7-gate (diagnose ไม่บังคับ TDD) |
| Bug เกิดเพราะ test gap | → `automate-test` | เพิ่ม regression coverage + CI gate (close the hole) |
| Bug ใน frontend (visual/a11y) | → `ui-test` | Playwright + axe + visual diff (diagnose ไม่มี UI tooling) |
| Bug เกี่ยวกับ security vuln | → `secure` | Sentinel STRIDE + abuse case (diagnose ไม่ classify threat)
