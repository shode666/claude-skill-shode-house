---
name: anti-puppet
description: Reference (lazy-load) ของ `shode-house-deliverable` — ตัวอย่าง ❌/✅ ของ Anti-Puppet เต็ม + Anti-Real-World-Guess. โหลดเมื่อไม่แน่ใจว่า evidence แบบไหนนับ หรือเมื่อถูกตีกลับว่า claim ไม่มีหลักฐาน
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-deliverable/anti-puppet.md
WHEN: evidence_form_uncertain=true OR anti_puppet_violation_reported=true
OWNER: developer
REQUIRED-BEFORE: claim_done
```

# Anti-Puppet — ตัวอย่างเต็ม

## ❌ Puppet show (บอกว่าเสร็จโดยไม่ทำจริง)

- "เสร็จแล้วครับ น่าจะ work"
- "test ผ่าน ✅" (โดยไม่ paste console output)
- "code build pass" (โดยไม่ paste compile log)
- "UI ทำงาน" (โดยไม่ screenshot/video)
- "deploy แล้ว" (โดยไม่ paste health check response)
- "ปิด bd แล้ว" / "เคลียร์ backlog แล้ว" (โดยไม่ paste `bd show` ที่แสดง CLOSED)

## ✅ Real work

- "Run `pnpm test` → output: [paste console]"
- "Hit endpoint → response: [paste JSON]"
- "Open browser → screenshot: [link/path]"
- "Docker up → `docker compose ps`: [paste status]"
- "[`bd show bd-42`] status=CLOSED reason='FIXED a1b2c3d 214 passed'"

## 🔴 Anti-Real-World-Guess (extension)

ห้าม claim project-specific fact จาก real-world knowledge โดยไม่ verify:

- ❌ "Spring Boot ใช้ application.yml ใช่ครับ" (เดาจาก default ทั่วไป)
- ❌ "PG รองรับ JSONB" (ไม่ check version)
- ❌ "Node 22 มี fetch native" (ไม่ check `node -v`)
- ❌ "FastAPI ใช้ Pydantic v2" (ไม่ check requirements.txt)
- ❌ "ปกติ React 18 มี Suspense" (ปกติ ≠ project นี้)

บังคับ pattern (project evidence):

- ✅ "[Read pom.xml:25] spring-boot 3.2.1 + [Glob '**/application.*'] application.yml พบ → yml ✅"
- ✅ "[psql -c 'SELECT version()'] PG 14.5 → JSONB ใช้ได้"
- ✅ "[node -v] v16.20.0 → fetch ไม่มี ต้อง node-fetch"
- ✅ "[Read package.json:42] react 18.2.0 → Suspense รองรับ"

ทำไม่ได้ = "❌ ไม่ได้รัน เพราะ [reason ระบุ]" — ตรงไป ห้ามแกล้งเสร็จ ห้ามเดาจาก real-world
