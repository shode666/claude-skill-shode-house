---
name: diagnose
description: Debug something broken or wrong (an error, crash, failing test, wrong output, flaky behavior, regression or slowdown) by reproducing it and isolating the root cause before fixing. For live production impact that needs mitigation, use incident instead.
---

# Diagnose (structured debugging)

> Inspired by mattpocock/skills (engineering/diagnose) — adapted for shode-house

> **Owner**: Chris (review) + Quinn (test) + Dave (implement)

**Goal**: identify the cause of an unresolved failure and verify the smallest justified fix.

## หลักการ (always)

- objective evidence ของ failure ก่อน · inspect ก่อนเดา · symptom ≠ root cause · หลัง fix validate พฤติกรรมที่กระทบ
- **No fix without a loop that goes red** — fix ได้หลังมี loop ที่แดงเท่านั้น (ไม่มี loop = ยังไม่ถึงขั้นเสนอ fix): ก่อนตั้งสมมติฐานใด ๆ ต้องมี **คำสั่งเดียว** ที่รันแล้วเห็น bug จริง. "ลองเปลี่ยนดู" = anti-pattern
- **ทุกการเปลี่ยน code ต้องมี hypothesis ที่เขียน prediction ได้** อยู่เบื้องหลัง
- **revert ก็ต้องเข้าใจก่อน** ว่ามันย้อนอะไรกลับบ้าง — revert คือการเปลี่ยน code ชนิดหนึ่ง กฎข้างบนใช้เหมือนกัน

## 🔒 Redact ก่อน paste (🔴 อ่านก่อนเริ่ม)

skill นี้บังคับให้ paste command/output/artifact เป็นหลักฐาน (per evidence protocol) — **ความลับต้องถูกลบก่อน**:
- เขียน `<REDACTED>` แทน secret/token/auth header/PII ทุกครั้ง
- build loop ผ่าน **env var** เพื่อให้ credential อยู่ใน environment ไม่ใช่ในสิ่งที่ paste
- captured artifact (HAR / log dump / request trace) พก auth header มาด้วยเสมอ → quote **เฉพาะบรรทัดที่มี signal**
- redact แล้วข้อมูลไม่พอวินิจฉัย → บอก user ตรง ๆ แล้วขอเพิ่ม ห้ามเดาต่อ

## When NOT to use

- Bug อยู่ใน **production** และยังมี customer impact หรือ SLO burn → `incident` ก่อน (Reggie IC + war room — diagnose ไม่มี comms/severity); mitigate แล้วค่อยกลับมา
- ยังไม่มี symptom ที่ reproduce ได้และไม่มี log/error — ไปเก็บหลักฐานก่อน
- Feature request ที่ถูกเรียกว่า "bug" — นั่นคืองานของ Bella/Patrick
- Known issue ที่มี ticket + root cause แล้ว — fix ตรง ๆ

## Inputs and decision boundaries

- [ ] วิธี reproduce — หาเองก่อนจาก test ที่มี · README/Makefile · log/fixture ที่ได้รับ; หรือช่องทางที่จะหามาได้ (env, ข้อมูล, ขั้นตอน); หาไม่ได้ → ส่งกลับ Oliver (§ Step 1)
- When to ask → `shode-house-discipline` § Ask vs derive

### Stop and return

- [ ] Symptom ที่ระบุได้ (error message / behavior ที่ผิด / metric ที่เปลี่ยน) — ไม่มีใครระบุ → ส่งคำถามกลับ Oliver
- [ ] Access ไป log / trace / ตัว service — ไม่มี = ระบุว่าติดตรงไหน ห้ามเดา root cause
- [ ] Redact ผ่านแล้ว (§ Redact ก่อน paste)

## เลือกความเข้มก่อน (ไม่ใช่ทุก bug คุ้มกับ 5 ขั้น)

| ระดับ | เมื่อไหร่ | ทำอะไร |
|---|---|---|
| **Fast path** | error message ชี้ตรงจุด · deterministic · 1 ไฟล์ · แก้แล้วเห็นผลทันที | ทำ **ขั้น 1 (loop) → 4 (fix + regression test)** พอ · ข้าม minimise/hypothesis list แล้วบอกใน report ว่าข้าม |
| **Full** | flaky · perf regression · ข้าม service · reproduce ไม่ตรงกับที่ user เจอ · fast path fix แล้วยังไม่หาย | ครบ 5 ขั้น |

เลือก fast path แล้วพลาด (fix ไม่หาย / bug อื่นโผล่) → **ขึ้น Full ทันที ห้ามลองเดาต่อ**

## 5 Steps

### 1. สร้าง feedback loop ที่ **tight** และ **red-capable** (นี่คือหัวใจ ที่เหลือ mechanical)

มี loop ที่แดงกับ bug ตัวนี้ = เจอสาเหตุแน่
ไม่มี loop = จ้อง code ให้ตายก็ไม่เจอ → **ทุ่มเวลาตรงนี้มากเป็นพิเศษ ก้าวร้าว สร้างสรรค์ ห้ามยอมแพ้**

**วิธีสร้าง — 3 อันแรกครอบเกือบทุกเคส**
1. **Failing test** ที่ seam ซึ่งเข้าถึง bug · 2. **curl / HTTP script** ยิงใส่ dev server · 3. **CLI + fixture** diff stdout กับ snapshot ที่รู้ว่าถูก
ทั้งสามไม่ได้ผล **หรือ** loop ที่ได้ยังช้า / flaky / bug ไม่ deterministic → เปิด **`loop-ladder.md`** ก่อนไป Step 2 (วิธีที่ 4–10 + วิธีลับ loop)

**✅ เงื่อนไขจบ Step 1 (ห้ามข้ามไป Step 2 ก่อนครบ)**
ระบุได้ว่า **คำสั่งเดียว** คืออะไร (path ของ script / test invocation / curl) และ **รันไปแล้วอย่างน้อย 1 ครั้ง** พร้อม paste invocation + output (redacted):
- [ ] **red-capable** — วิ่งผ่าน code path ของ bug จริง และ assert อาการที่ user บอก → แดงได้ตอนนี้ เขียวได้หลัง fix (ไม่ใช่แค่ "รันแล้วไม่ error")
- [ ] **deterministic** — verdict เดิมทุกรอบ (flaky: rate สูงและคงที่)
- [ ] **เร็ว** — หน่วยวินาที ไม่ใช่นาที
- [ ] **agent รันเองได้** — ไม่ต้องมีคนกดกลางทาง

**ห้ามกระโดดไปสรุปสาเหตุก่อนมีคำสั่งนี้** — นั่นคือ failure mode ที่ skill นี้มีไว้กัน
✅ **อ่าน code ได้เต็มที่เพื่อ *สร้าง* loop** (หา route/entry point, test setup, fixture, วิธี boot ระบบ, ชื่อ config) — หลายระบบสร้าง harness ไม่ได้เลยถ้าไม่อ่านก่อน
เส้นแบ่ง: อ่านเพื่อ **"จะ trigger มันยังไง"** = ส่วนหนึ่งของขั้นนี้ · อ่านเพื่อ **"มันน่าจะพังเพราะ..."** = ข้ามขั้นตอน

**สร้าง loop ไม่ได้จริง ๆ**: หยุดแล้วบอกตรง ๆ + list สิ่งที่ลองแล้ว + ขอ (ก) access environment ที่ repro ได้ (ข) captured artifact ที่ redact แล้ว (HAR/log/core dump/วิดีโอพร้อม timestamp) หรือ (ค) อนุญาตให้ใส่ instrumentation ชั่วคราวใน production — **ห้ามเดาต่อโดยไม่มี loop**

### 2–3. Full investigation (Full path only)

Before minimising the reproduction or ranking/instrumenting hypotheses on the Full path,
read [full-investigation.md](full-investigation.md) in full (Steps 2–3). Fast path skips these steps;
promote to Full and load this reference if the first fix fails or another symptom appears.

### 4. Fix + Regression test

เขียน regression test **ก่อน** fix — แต่เฉพาะเมื่อมี **seam ที่ถูกต้อง** คือ seam ที่ test ได้เจอ bug pattern จริงอย่างที่มันเกิดที่ call site

**ไม่มี seam ที่ถูกต้อง = นั่นแหละคือ finding** — ถ้า seam ที่มีตื้นเกินไป (unit test ที่ replicate chain ที่ trigger bug ไม่ได้ / test caller เดียวทั้งที่ bug ต้องมีหลาย caller) การเขียน test ตรงนั้นให้ **false confidence**. บันทึกว่า **architecture กันไม่ให้ล็อค bug ตัวนี้ได้** แล้ว route ต่อ (Sara/Stan) — อย่าฝืนเขียน

มี seam ที่ถูก:
1. เปลี่ยน repro ที่ minimise แล้วเป็น failing test ที่ seam นั้น
2. ดูมัน fail
3. ใส่ fix — **root cause ไม่ใช่ symptom** (fix แล้ว bug อื่นโผล่ = ยังไม่ใช่ root cause) และเลือก **change ที่เล็กที่สุดที่ fix ได้**
4. ดูมัน pass
5. **รัน loop จาก Step 1 กับ scenario เต็ม (ที่ยังไม่ minimise) อีกครั้ง**

### 5. Cleanup + Prevent (บังคับก่อนบอกว่าเสร็จ)

- [ ] repro เดิมไม่ repro แล้ว (รัน loop จาก Step 1 ซ้ำ + paste output)
- [ ] ship fix พร้อม regression test ที่ผ่าน (หรือบันทึกไว้ว่าไม่มี seam ที่ถูกต้อง)
- [ ] instrumentation `[DEBUG-...]` ถูกลบครบ (`grep` prefix ยืนยัน + paste ว่าไม่เจอ)
- [ ] throwaway harness/prototype ถูกลบ หรือย้ายไปที่ที่ mark ชัดว่าเป็นของ debug
- [ ] **เขียน hypothesis ที่ถูกลงใน commit / PR message** — คนที่ debug คนต่อไปจะได้เรียนรู้
- [ ] pattern เดียวกันอาจมีที่อื่น → `grep` แล้วแก้ให้หมด
- [ ] doc ที่ทำให้เข้าใจผิด → แก้
- [ ] production incident → postmortem แบบ blameless: โทษระบบ ไม่โทษคน (`incident` skill)

## Hand-off / next skill

Diagnose finished → Chris: review fix + regression unit test · Quinn: integration test เผื่อ pattern อื่น · Aaron: monitoring/alert ถ้าเป็น infra · Domain Expert: ถ้า business rule ผิด

| Situation | Next skill | Reason |
|---|---|---|
| Diagnosis เสร็จ → จะเขียน fix code | → `dev-gate` | TDD + 11-gate |
| Bug เกิดเพราะ test gap | → `automate-test` | เพิ่ม regression coverage + CI gate |
| Bug ใน frontend (visual/a11y) | → `ui-test` | Playwright + axe + visual diff |
| Bug เกี่ยวกับ security vuln | → `secure` | Sentinel STRIDE + abuse case
