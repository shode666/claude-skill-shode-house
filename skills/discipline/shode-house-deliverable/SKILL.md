---
name: shode-house-deliverable
description: |
  [WHAT] Output discipline — Standard Output Deliverables + "I Never Do" pattern + AI Persona Disclaimer + Definition of Done (verifiable) + Anti-Puppet rules + Postmortem template.
  [WHEN] ก่อน hand-off.
  [TRIGGER] /shode-house:deliverable, "Definition of Done", "DoD", "Standard Output", "I Never Do", "Anti-Puppet".
---

# shode-house — Deliverable Discipline

> ทุก agent มี Standard Output ที่ระบุ. ทุก "done" ต้อง verifiable (paste evidence). ทุก deliverable ผ่าน Anti-Puppet gate

---
## 📎 Reference (lazy-load — โหลดตอนจะ produce/finalize deliverable)

| ต้องการ | อ่านที่ |
|---|---|
| Standard output ต่อ agent · "I Never Do" ต่อ agent | `output-contract.md` |
| **Definition of Done** (checklist verifiable ต่อ owner) | `definition-of-done.md` — Oliver enforce ก่อนปิด bd |
| ADR lifecycle + template (Context/Options/Decision/Consequences) | `adr.md` |

**Anti-Puppet Rule ด้านล่างคือส่วนที่ preload** — เป็นกฎที่ต้องอยู่ในหัวตลอดเวลา ไม่ใช่เปิดอ่านตอนจะส่งงาน

## 🚫 Anti-Puppet Rule (🔴 Philosophy 2 enforcement)

ห้าม pattern (puppet show — บอกว่าเสร็จโดยไม่ทำจริง):
- ❌ "เสร็จแล้วครับ น่าจะ work"
- ❌ "test ผ่าน ✅" (โดยไม่ paste console output)
- ❌ "code build pass" (โดยไม่ paste compile log)
- ❌ "UI ทำงาน" (โดยไม่ screenshot/video)
- ❌ "deploy แล้ว" (โดยไม่ paste health check response)
- ❌ "ปิด bd แล้ว" / "เคลียร์ backlog แล้ว" (โดยไม่ paste `bd show` ที่แสดง CLOSED)

บังคับ pattern (real work):
- ✅ "Run `pnpm test` → output: [paste console]"
- ✅ "Hit endpoint → response: [paste JSON]"
- ✅ "Open browser → screenshot: [link/path]"
- ✅ "Docker up → `docker compose ps`: [paste status]"
- ✅ "[`bd show bd-42`] status=CLOSED reason='FIXED a1b2c3d 214 passed'"

### 🔴 v2.8.1 — Anti-Puppet UX/UI (Uma + frontend agents)

ห้าม claim UX/UI/a11y ผ่านโดยไม่มี tool evidence:
- ❌ "UI matches Figma ครับ"
- ❌ "Design adherence ok"
- ❌ "Contrast ผ่าน WCAG AA"
- ❌ "a11y ok"
- ❌ "Token usage ถูกต้อง"
- ❌ "Visual diff น้อย"

บังคับ pattern (UX evidence):
- ✅ "[Bash: `make ui-test`] Playwright 8/8 pass; visual diff 0.05% (Chromatic build/12345)"
- ✅ "[Bash: `axe-cli http://localhost:3000/checkout`] critical=0, serious=2 → [report: tests/a11y/checkout.json]"
- ✅ "[Bash: `playwright test --update-snapshots`] baseline screenshot saved: tests/visual/checkout-before.png"
- ✅ "[screenshot diff: tests/visual/checkout-diff.png] vs baseline — alignment off-spec 4px, button width +12px → FAIL"
- ✅ "[manual keyboard test pasted] Tab → header logo → nav → CTA → form fields in order ✅"

ทำไม่ได้ = "❌ ไม่ได้รัน เพราะ [no Playwright in project / no axe installed]" — ตรงไป ห้ามแกล้งผ่าน

### Mandatory paste-evidence for Uma POST (Phase 3a)
```
[Uma|state:phase-3a|bd:42] POST verdict
- Visual diff: [Bash: `npx chromatic ...`] baseline build/12345 → current build/12346, diff 0.08%
- Screenshot before: tests/visual/checkout-before.png
- Screenshot after:  tests/visual/checkout-after.png
- Token usage: [Grep: `grep -r 'background:' src/checkout/ | grep -v "var(--"`] 2 hardcoded → FAIL
- a11y axe: [Bash: `axe-cli http://localhost:3000/checkout --save report.json`] critical=0
- Contrast manual: [WebAIM check] #333 on #fff = 12.6:1 ✅; #999 on #fff = 2.85:1 ❌ FAIL
- AC verification (bullet per AC):
  - AC-1 user sees price: ✅ [screenshot: tests/visual/checkout-after.png frame:price]
  - AC-2 mobile responsive 320px: ❌ [screenshot: tests/visual/mobile-320.png] overflow detected
  - AC-3 keyboard focus order: ✅ [Playwright trace: playwright-report/trace.zip]
  ...
- Verdict: FAIL (2 issues: hardcoded color, mobile overflow) → loop Phase 2
```

### 🔴 v2.4 — Anti-Real-World-Guess (extension)

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

## 📎 ย้ายออกจาก preload

- **AI Persona Disclaimer** → agent file ของ domain expert แต่ละตัว (เคยอยู่ที่นี่ แต่ domain expert **ไม่ได้ preload skill นี้** → กฎไปไม่ถึงกลุ่มเป้าหมาย ขณะที่ 8 agent ที่ไม่ใช่เป้าหมายแบกไว้)
- **Postmortem Template** → `incident` skill (Reggie/Oliver โหลดตอนมี incident เท่านั้น)

## 🛡️ Safety (🔴)
