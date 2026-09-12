---
name: shode-house-deliverable
description: |
  [WHAT] Output discipline — output contract (artifact + evidence path + no placeholder) + Anti-Puppet rule + pointer ไป DoD/ADR/UX evidence.
  [WHEN] Preload ของ producer agent; บังคับก่อน hand-off ทุกครั้ง.
  [TRIGGER] /shode-house:deliverable, "Definition of Done", "DoD", "Standard Output", "I Never Do", "Anti-Puppet".
---

# shode-house — Deliverable Core

> ทุก "done" ต้อง **verifiable** (paste evidence จริง). ทุก deliverable ผ่าน Anti-Puppet gate

## 📤 Output contract (🔴 บังคับ)

1. **Output อยู่ใน artifact file** — `outputs/<bd-id>/<NN>-<agent>-<phase>.md` ไม่ใช่ในข้อความ chat
2. **Evidence path** — ทุก claim แนบ path/command/output ที่ตรวจซ้ำได้; claim ที่ไม่มี evidence = ยังไม่ทำ
3. **No placeholder** — ห้ามส่งงานที่มี `TBD` / `<fill this>` / example data ปลอม โดยไม่ mark เป็น **OPEN QUESTION** พร้อมชื่อคนตอบ
4. **No false done** — ทำไม่ได้ = พูดว่าทำไม่ได้ + เหตุผล (`PARTIAL` / `BLOCKED`) ห้าม claim PASS
5. **Return = verdict + artifact path + open questions** ไม่ dump transcript

## 🚫 Anti-Puppet Rule (🔴 Philosophy 2 enforcement — preload)

ห้าม claim "เสร็จ / ผ่าน / deploy แล้ว / ปิด bd แล้ว" **โดยไม่ paste output ของ tool ที่รันจริง**
รูปแบบที่นับเป็น evidence: console output · HTTP response · screenshot/trace path · `docker compose ps` · `bd show` ที่อ่านได้ว่า CLOSED
ห้าม claim project fact จาก real-world knowledge โดยไม่ verify ใน repo นี้ (NO MAGIC)
ทำไม่ได้ → `"❌ ไม่ได้รัน เพราะ <reason>"` ตรงไปตรงมา ห้ามแกล้งผ่าน

ตัวอย่าง ❌/✅ เต็ม + Anti-Real-World-Guess → `anti-puppet.md`

## 📎 Reference (lazy-load — โหลดตาม deliverable type)

| Deliverable / จังหวะ | โหลด | ใคร |
|---|---|---|
| ก่อนปิด bd / phase exit | `definition-of-done.md` | Oliver (enforce) + producer |
| standard output + "I Never Do" ต่อ agent | `output-contract.md` | producer ตอนไม่แน่ใจ scope ของตัวเอง |
| สร้าง/แก้ ADR | `adr.md` | Sara |
| UI/a11y claim · Phase 1b, 3a | `ux-evidence.md` | Uma + frontend agent |
| ตัวอย่าง evidence ที่นับ/ไม่นับ | `anti-puppet.md` | ทุก producer |

**ย้ายออกจาก skill นี้แล้ว**: AI Persona Disclaimer + citation contract → `domain-core` (domain expert preload ตัวนั้นแทน) · Postmortem Template → `incident` skill
