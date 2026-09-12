---
name: api-contract
description: |
  [WHAT] Public-interface discipline — semver policy, breaking-change checklist, deprecation window, consumer-driven contract test, event/schema evolution.
  [WHEN] ทุก PR ที่แตะ REST/GraphQL/gRPC/event payload/public SDK/DB view ที่ทีมอื่นใช้.
  [TRIGGER] /shode-house:api-contract, "breaking change", "semver", "API version", "deprecate", "backward compatible".
---

# API Contract (versioning + deprecation + consumer contract)

> **Owner**: Sara (policy/ADR) + Dave (implement) + Quinn (contract test). Cross-team → Stan. Payload ที่มี money/PII → Domain expert + Sentinel
> หลัก: **ผู้บริโภคที่คุณไม่รู้จักคือผู้บริโภคที่คุณจะพัง** — ถ้าออกนอกขอบ deploy unit ของคุณ = public

## When NOT to use

- **Internal function/class ในโมดูลเดียวกัน** — refactor ได้เสรี ใช้ `dev-gate`
- **API ที่ยังไม่มี consumer จริง** (pre-launch, consumer = ตัวเอง) — เร่ง iterate ได้ แต่ต้องประกาศ `v0`/unstable ชัดเจน
- **Internal DB schema ที่ไม่มีใครนอกทีมอ่าน** — ใช้ `data-migration`
- **UI component props** — ใช้ `design-system` (design token/component contract คนละเรื่อง)

## Required inputs — refuse without

- [ ] **รายชื่อ consumer จริง** — ใครเรียก endpoint/topic นี้บ้าง (จาก access log / API gateway / service map / grep ใน monorepo). "น่าจะไม่มีใครใช้" ไม่นับ
- [ ] **Versioning scheme ปัจจุบันของ project** (URI `/v1`, header, media type, package semver) — cite จาก repo
- [ ] **Contract artifact** ที่มีอยู่ (OpenAPI / proto / GraphQL SDL / Avro-JSON schema) — ไม่มี = สร้างก่อน ห้ามแก้ contract ที่ไม่มีตัวตน
- [ ] **Deprecation window ที่ยอมรับได้** (ตกลงกับ consumer/owner) ถ้าเป็น breaking

## Breaking vs non-breaking (🔴 ตัดสินก่อนเขียนโค้ด)

| Non-breaking (minor/patch) | Breaking (major) |
|---|---|
| เพิ่ม **optional** field ใน response | ลบ/เปลี่ยนชื่อ field · เปลี่ยน type · เปลี่ยนหน่วย |
| เพิ่ม endpoint / event type ใหม่ | เพิ่ม **required** request field |
| ขยาย enum ที่ consumer ต้อง ignore-unknown อยู่แล้ว | แคบ validation ให้เข้มขึ้น · ขยาย enum ที่ consumer switch แบบ exhaustive |
| ผ่อน validation ให้หลวมลง | เปลี่ยน default · เปลี่ยน error code/shape · เปลี่ยนลำดับ/pagination semantics |
| เพิ่ม optional query param | เปลี่ยน auth scope ที่ต้องใช้ · เปลี่ยน rate limit ลง · เปลี่ยน sync → async |

**เส้นแบ่งที่คนพลาดบ่อย**: เปลี่ยนหน่วยเงิน (บาท → สตางค์), เปลี่ยน timestamp เป็น timezone อื่น, เปลี่ยน id จาก int เป็น string, ทำให้ field ที่เคยมีค่าเสมอกลายเป็น nullable — **ทั้งหมดนี้ breaking** ถึงแม้ชื่อ field ไม่เปลี่ยน

## Rules

1. **Additive-first** — ทำให้ได้แบบ non-breaking ก่อนเสมอ; ขึ้น major เมื่อไม่มีทางเลี่ยงจริง ๆ
2. **Tolerant reader** — consumer ต้อง ignore field ที่ไม่รู้จัก; producer ห้ามพึ่งลำดับ field
3. **สอง version อยู่ร่วมกันได้** ตลอด deprecation window — ห้าม flip ทั้งระบบในดีพลอยเดียว
4. **Error shape คือ contract** — code/shape ของ error เปลี่ยน = breaking เท่ากับ success payload
5. **Event = append-only** — เปลี่ยนความหมายของ event เดิม ห้าม; ออก event type ใหม่แทน
6. **ห้ามใช้ค่าที่ consumer อ่านไม่ออกเป็น "default"** — เพิ่ม required field = breaking เสมอ

## Deprecation window (🔴 ประกาศ → เตือน → ปิด)

```
T0  ประกาศ: CHANGELOG + response header `Deprecation: <date>` + `Sunset: <date>` + doc + แจ้ง consumer ที่ระบุตัวได้
T0+ วัด: metric ต่อ consumer บน endpoint เก่า (ใครยังเรียก เรียกเท่าไหร่) ← ไม่มี metric = ห้ามปิด
T1  เตือนซ้ำเมื่อเหลือ ≤ 1/3 ของ window + ping consumer ที่ยัง traffic > 0
T2  ปิด — ต่อเมื่อ traffic = 0 ต่อเนื่อง หรือ owner ตัดสินใจปิดทั้งที่ยังมี traffic (บันทึกใน ADR ว่าใครรับ risk)
```

Window ขั้นต่ำ: internal consumer 1 release cycle · ทีมอื่นในองค์กร ≥ 1 quarter · external/partner ตาม SLA สัญญา
**ห้ามลบก่อน T2 เพราะ "ไม่น่ามีใครใช้แล้ว"** — ใช้ metric ไม่ใช่ความรู้สึก

## Consumer-driven contract test (Quinn)

- Consumer เขียน expectation → publish (Pact broker / schema registry / committed fixture)
- Producer CI ต้อง verify กับ expectation ทุกตัวก่อน merge → **แดง = block merge**
- ไม่มี broker → อย่างน้อย commit golden fixture ของ request/response จริง + snapshot test
- OpenAPI/proto/SDL diff ใน CI: ตรวจ breaking อัตโนมัติ (oasdiff / buf breaking / graphql-inspector) → paste ผล
- Schema registry สำหรับ event: ตั้ง compatibility mode (BACKWARD ขั้นต่ำ) แล้ว paste ค่าที่ตั้งจริง

## Gate `pre-merge` เพิ่มเติมสำหรับ PR ที่แตะ contract

```
□ จัดประเภทแล้ว: non-breaking / breaking (+ เหตุผล 1 บรรทัด)
□ contract artifact อัปเดต (OpenAPI/proto/SDL) และ commit มาด้วย
□ contract test เขียว — paste output
□ ถ้า breaking: version bump + ทั้งสอง version รันคู่ได้ + Deprecation/Sunset header + ADR
□ รายชื่อ consumer + ช่องทางที่แจ้ง
□ payload มี money/PII → Domain expert + Sentinel sign
```

## Evidence

```
✅ "[oasdiff breaking old.yaml new.yaml] 0 breaking, 3 non-breaking (added optional fields)"
✅ "[pact-verifier] 4/4 consumer contracts pass (checkout-web, mobile-ios, partner-api, batch-job)"
✅ "[gateway metrics 30d] /v1/orders: partner-api 12.4k req, mobile-ios 0 → ping partner ก่อนปิด"
❌ "backward compatible ครับ" (ไม่มี diff tool, ไม่มีรายชื่อ consumer)
```

## ห้าม

- ห้ามแก้ contract โดยไม่อัปเดต artifact (OpenAPI/proto/SDL) ใน commit เดียวกัน
- ห้ามลบ endpoint/field โดยไม่มี metric ยืนยันว่า traffic = 0
- ห้ามเพิ่ม required field ใน minor
- ห้ามเปลี่ยนความหมายของ event เดิม
- ห้ามบอกว่า "ไม่ breaking" โดยไม่รัน diff tool
- ห้ามใช้ deprecation window ที่สั้นกว่าที่ตกลงกับ consumer

## Skill composition

| Situation | Next skill |
|---|---|
| เขียน implement + unit test | → `dev-gate` |
| ตั้ง contract test ใน CI | → `automate-test` (Quinn pyramid + gate) |
| review PR ที่แตะ contract | → `review-checklist` |
| เปลี่ยน API พร้อม schema | → `data-migration` (ทำคู่กัน expand-contract) |
| auth scope / rate limit เปลี่ยน | → `secure` (Sentinel abuse case) |
| หลาย service ใช้คนละ convention | → Stan (`shode-house-routing` cross-team) |
