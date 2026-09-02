---
name: ux-evidence
description: Reference (lazy-load) ของ `shode-house-deliverable` — Anti-Puppet เฉพาะ UX/UI/a11y + template paste-evidence ของ Uma Phase 3a POST. โหลดเมื่อเข้า Phase 1b/3a หรือก่อน claim ว่า UI/a11y ผ่าน
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-deliverable/ux-evidence.md
WHEN: frontend_changed=true OR phase in {1b,3a}
OWNER: ux-ui-designer
REQUIRED-BEFORE: phase_3a_verdict
```

# UX/UI evidence contract

## ❌ ห้าม claim UX/UI/a11y ผ่านโดยไม่มี tool evidence

- "UI matches Figma ครับ" · "Design adherence ok" · "Contrast ผ่าน WCAG AA"
- "a11y ok" · "Token usage ถูกต้อง" · "Visual diff น้อย"

## ✅ บังคับ pattern (UX evidence)

- "[Bash: `make ui-test`] Playwright 8/8 pass; visual diff 0.05% (Chromatic build/12345)"
- "[Bash: `axe-cli http://localhost:3000/checkout`] critical=0, serious=2 → [report: tests/a11y/checkout.json]"
- "[Bash: `playwright test --update-snapshots`] baseline screenshot saved: tests/visual/checkout-before.png"
- "[screenshot diff: tests/visual/checkout-diff.png] vs baseline — alignment off-spec 4px, button width +12px → FAIL"
- "[manual keyboard test pasted] Tab → header logo → nav → CTA → form fields in order ✅"

ทำไม่ได้ = "❌ ไม่ได้รัน เพราะ [no Playwright in project / no axe installed]" — ตรงไป ห้ามแกล้งผ่าน
Evidence ladder (Playwright ก่อน · browser MCP ถ้ามี · ไม่มีเลย = BLOCKED) → `ui-test` skill

## Mandatory paste-evidence — Uma POST (Phase 3a)

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
- Verdict: FAIL (2 issues: hardcoded color, mobile overflow) → loop Phase 2
```
