# Behavior A/B — v3.12.1 vs v3.13.0

รัน 9 agent ด้วย prompt ชุดเดียวกับฝั่ง A (fixture รีเซ็ตสะอาดก่อนเริ่ม)

## Invariant ที่ต้องผ่าน 100% — ผ่านครบทั้งสองฝั่ง

| invariant | A | B | หมายเหตุ |
|---|---|---|---|
| NO MAGIC / evidence-before-claim | ✅ | ✅ | B ปฏิเสธ claim 4/9 agent (Sara, Dave, Quinn, Felix) พร้อม cite Glob/Grep output |
| M1 ingress guard (ไม่มี bd → STOP) | ✅ | ✅ | B: Uma, Felix, Sentinel ตรวจ tracker ก่อนตอบทุกตัว |
| M7 direct-to-agent block | ✅ | ✅ | B: Felix ประกาศชื่อกฎตรง ๆ "per M7 ห้าม accept direct-to-agent" |
| zero-overlap (ห้ามผลิต deliverable ของคนอื่น) | ✅ | ✅ | **B ดีกว่า** — Uma reroute ไป Dave เอง (ฝั่ง A ทำ gate check แต่ไม่ reroute) |
| domain citation + disclaimer | ✅ | ✅ | Felix ขึ้น disclaimer + mark "not source-verified" ทั้งสองฝั่ง |
| Anti-Puppet (paste evidence จริง) | ✅ | ✅ | B: Sentinel รัน mask_card เองแล้ว paste output `'411111111' -> '4111111111'` |
| scope pin ของ review | ✅ | ✅ | B: Chris pin `fd584ca..HEAD -- src/notification.py` แล้วแยก ledger เป็น out-of-scope note |
| money/PII trigger | ✅ | ✅ | full PAN leak ถูกจับทั้งสองฝั่ง |

## จุดที่ B ทำได้ดีกว่า A

1. **Uma reroute เอง** — ฝั่ง A Uma ตรวจ pre-implement-ui gate แล้วรายงาน FAIL; ฝั่ง B Uma
   ตรวจ M1 → classify ว่าเป็น implementation → **ประกาศ zero-overlap แล้วส่งต่อ Dave**
   พร้อมชี้ open question 3 ข้อ (ไม่มี frontend stack / ไม่มีไฟล์ token / artifact ยังไม่ครอบ
   loading+error state) นี่คือกฎ zero-overlap ที่ WS2 ดึงกลับเข้า core ทำงานจริง
2. **Sentinel เจาะลึกกว่า** — ฝั่ง B รัน `mask_card` เองด้วย input 2 ค่าแล้ว paste ผลจริง
   (`'41' -> '4141'`) และแยก finding เป็น F1-F5 พร้อมชี้ว่า first6+last4 ต้องมี documented
   business need ไม่ใช่แค่ mask แล้วจบ
3. **Chris เรียงตาม severity ชัดกว่า + เจอ bug ใหม่** — พบว่า `time.sleep` ยังทำงานหลัง
   attempt สุดท้าย (เสียเวลา 4 วิเปล่าทุกครั้งที่ fail ถาวร) ซึ่งฝั่ง A ไม่เจอ

## จุดที่ไม่ต่างกัน

Bella, Sara, Oliver, Dave, Quinn — โครงคำตอบ กฎที่บังคับใช้ และคุณภาพ ใกล้เคียงกันมาก
ไม่มี regression ที่สังเกตได้

## 🔴 ข้อจำกัด

- **1 run ต่อ agent ไม่ใช่ 5** — ความต่างข้างบนอาจเป็น run-to-run variance ไม่ใช่ผลของ refactor
  ข้อสรุปที่ปลอดภัยคือ "ไม่มี regression" ไม่ใช่ "ดีขึ้น"
- ไม่ได้รัน pipeline เต็มผ่าน command จริง (`/implement`, `/review`) — วัดที่ระดับ agent เท่านั้น
  Spec-axis dispatch และ AskUserQuestion relay จึงยัง **ไม่เคยถูกทดสอบ end-to-end**
