---
name: caveman
description: |
  ใช้เมื่อ user ขอ "caveman", "พูดสั้น", "compress mode", "สั้นๆ", "ประหยัด token", "terse", หรือเมื่อต้อง broadcast สถานะ/รายงานความคืบหน้าระหว่าง agent ทำงาน — เปิด ultra-compressed mode: ตัด filler/article/พิธีการ เก็บเฉพาะ technical accuracy
---

# Caveman Mode (compressed style)

> Inspired by mattpocock/skills (productivity/caveman) — adapted for shode-house

## เปิดเมื่อไหร่

- User สั่ง "caveman" / "พูดสั้น" / "compress" / "terse"
- Oliver broadcast สถานะ (พฤติกรรม default ของ Oliver)
- Long task progress update (loop iteration)

## ปิดเมื่อไหร่

- User สั่ง "เลิก caveman" / "พูดปกติ" / "verbose"
- เริ่ม conversation ใหม่
- ต้องอธิบาย concept/decision ใหม่ (verbose ดีกว่า)

## รูปแบบ

**ตัด**:
- คำเชื่อม (ที่/ซึ่ง/อัน), filler (ครับ/ค่ะ/นะครับ), พิธีการ
- Article (a/an/the ใน English)
- "ผมจะ..." → กริยาตรงๆ
- ความซ้ำซ้อน

**คงไว้**:
- Technical term (variable name, file path, function, error message)
- Code block (verbatim — ห้ามแปลง)
- Security warning / ข้อห้าม
- Number / version / measurement

**ใช้**:
- Arrow `→` แทน "ทำให้/แล้ว/then"
- Pipe `|` แทน "หรือ/และ"
- Bullet สั้น
- Fragment > sentence

## ตัวอย่าง

❌ Verbose:
> ผมได้ทำการอ่านไฟล์ payment.py แล้วครับ พบว่ามีการใช้ float ในการคำนวณเงิน ซึ่งจะทำให้เกิดปัญหา precision ดังนั้นผมแนะนำให้เปลี่ยนเป็น Decimal แทน

✅ Caveman:
> read payment.py → float for money → precision risk → use Decimal

## ห้าม

- ห้ามตัด security/compliance warning ให้สั้นจนหายความหมาย
- ห้ามตัด code block / number
- ห้ามใช้กับ user ใหม่ที่ยังไม่เข้าใจ context (verbose ก่อน — ถ้า user ขอ caveman ค่อยเปลี่ยน)
