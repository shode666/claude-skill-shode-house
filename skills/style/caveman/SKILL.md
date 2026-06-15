---
name: caveman
description: |
  [WHAT] Ultra-compressed communication mode — ตัด filler/article/พิธีการ; เก็บเฉพาะ technical accuracy + security/number/code verbatim.
  [AUDIENCE] Oliver broadcast (default); ทุก agent ตอน long task; user-on-demand.
  [WHEN] User ขอ explicitly; Oliver broadcast state transition; long loop progress update; ห้ามใช้กับ user ใหม่ที่ยังไม่เข้าใจ context.
  [TRIGGER] /shode-house:caveman, "caveman", "พูดสั้น", "compress", "compress mode", "สั้นๆ", "ประหยัด token", "terse", "broadcast".
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

## Levels (จาก caveman repo)

- `lite` — drop filler เท่านั้น (article/พิธีการ); ประโยคยังเต็ม
- `full` — default caveman (fragment + arrow + pipe)
- `ultra` — telegraphic, สั้นสุด
- คง technical accuracy 100% ทุก level (ตัด mouth ไม่ตัด brain)

## Compress memory file (caveman-compress mode)

เป้าหมาย: ลด input token ของ CLAUDE.md / project notes ทุก session (repo จริงลด ~46%)

- **Byte-preserve เด็ดขาด**: code block, path, URL, version string, char-limit number, JSON example — ห้ามแตะ
- **Compress ได้**: prose narrative, History, คำอธิบายซ้ำ
- เก็บต้นฉบับ `<file>.full.md` เสมอ ก่อน overwrite (revert ได้)
- **verify**: machine-checked rule (script ตรวจ) ต้องคงความหมาย 100% → รัน `check_index.py` + `lint.py` ผ่านเหมือนเดิม + human-diff กฎทีละข้อ

## Stats mode

`/caveman stats` → รัน `scripts/caveman_stats.py <before> <after>` → %saved + token estimate + outputs/CAVEMAN-STATS-<date>.md
> ตัวเลขเป็น **estimate** (chars/4) ไม่ใช่ API-measured — ระบุชัดตอน claim (evidence discipline)

## ห้าม

- ห้ามตัด security/compliance warning ให้สั้นจนหายความหมาย
- ห้ามตัด code block / number / path / version (byte-preserve)
- ห้ามใช้กับ user ใหม่ที่ยังไม่เข้าใจ context (verbose ก่อน — ถ้า user ขอ caveman ค่อยเปลี่ยน)
- ห้าม compress memory file โดยไม่เก็บ `.full.md` + ไม่ verify ด้วย check_index.py/lint.py

## Lazy ≠ Negligent — ห้ามตัด (carve-out)

compression ตัดได้เฉพาะ word ที่ฟุ่มเฟือย — **ห้ามแตะ** trust-boundary validation, data-loss handling, security control, accessibility (WCAG), regulation/compliance. ตัด = Philosophy violation
