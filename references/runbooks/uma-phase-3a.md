---
name: uma-phase-3a
description: Runbook (lazy-load) ของ Uma — Phase 3a POST-Check. โหลดเมื่อเข้า phase นี้จริงเท่านั้น
---

# Phase 3a POST-Check — Uma

> แยกจาก agent prompt v3.12.1 — consultation สั้น ๆ ไม่ต้องแบก runbook ของทุก phase

## 🔎 Phase 3a POST-Check (🔴 v2.8 — sequential gate BEFORE Chris+Quinn)

หลัง Dave implement (Phase 2 done) → Uma ตรวจ **ก่อน** Chris+Quinn เริ่ม (gate)

### Process (Phase 3a) — 🔴 v2.8.1 Mandatory Bash invocation pattern

ห้าม claim PASS โดยไม่ run tool — anti-puppet UX/UI (`shode-house-deliverable` § Anti-Puppet Rule) บังคับ paste evidence

1. **Read context**:
   ```bash
   bd show <id>                                       # bd issue context
   cat outputs/SPEC-<bd-id>.md                        # Phase 1b artifacts (Uma own AC + baseline path)
   ```

2. **Spin up app** (ถ้ายังไม่ run):
   ```bash
   docker compose up -d app                           # หรือ make dev
   curl -s http://localhost:3000/health | jq         # paste 200
   ```

3. **Capture current screenshot (Bash mandatory)**:
   ```bash
   # Playwright (scaffold จาก init.md Phase 2):
   pnpm exec playwright test tests/visual/<feature>.spec.ts --update-snapshots=false
   ls -lh tests/visual/__screenshots__/ | head        # paste output
   # หรือ headless screenshot ตรง ๆ:
   pnpm exec playwright screenshot --viewport-size=375,812 http://localhost:3000/checkout tests/visual/checkout-after.png
   ```

4. **Visual diff (Bash mandatory)**:
   ```bash
   # Chromatic CI:
   pnpm chromatic --exit-zero-on-changes              # paste URL + diff %
   # หรือ pixel diff ตรง ๆ:
   pnpm exec playwright test --grep "visual regression" 2>&1 | tee /tmp/visual.log
   grep -E "diff:|FAIL" /tmp/visual.log               # paste
   ```
   Flag deviation > 0.1% (threshold ปรับตามทีม)

5. **Design adherence (Bash mandatory — Grep token usage)**:
   ```bash
   # Hardcoded color check:
   rg "(color|background|border):\s*#[0-9a-fA-F]{3,8}" src/<feature>/ --type css --type vue --type tsx
   # ต้อง empty result → ถ้าเจอ = FAIL (ใช้ token instead)
   rg "padding|margin:\s*[0-9]+px" src/<feature>/ | grep -vE "(0px|2px|4px|8px|12px|16px|24px|32px|48px|64px)"
   # ต้อง empty → ถ้าเจอ off-grid spacing = FAIL
   ```

6. **a11y axe (Bash mandatory)**:
   ```bash
   # axe-cli (Aaron scaffold):
   npx @axe-core/cli http://localhost:3000/checkout --save tests/a11y/checkout.json
   cat tests/a11y/checkout.json | jq '.violations[] | {id, impact, nodes: (.nodes | length)}'
   # critical=0, serious ≤ tolerance — paste output
   ```

7. **a11y manual (paste actual test steps)**:
   ```
   Keyboard test:
   - Tab × 1: focus = header logo? [paste observation]
   - Tab × 2: focus = nav? [paste]
   - ... ครบ critical interactive
   - Enter on CTA: triggers action? [paste]
   - Esc on modal: closes? [paste]

   Screen reader test (manual VO/NVDA):
   - Page title announced: "Checkout - Shop" [paste]
   - Form labels announced: "Email, required" [paste]
   - Error: "Error: invalid email" [paste]
   ```

8. **Contrast verify (Bash mandatory)**:
   ```bash
   # WebAIM CLI or programmatic:
   npx wcag-contrast-checker "#333333" "#ffffff"      # paste ratio
   # หรือ axe ครอบแล้ว — re-confirm via jq
   ```

9. **Component state validation (Bash + Playwright)**:
   ```bash
   pnpm exec playwright test tests/states/<feature>.spec.ts
   # tests/states ต้องครอบ default/hover/active/focus/disabled/loading/error/empty
   # paste output 8/8 pass หรือ list failed states
   ```

10. **Content design check** — paste actual text vs spec:
    ```
    Spec error message: "อีเมลไม่ถูกต้อง"
    Actual: "Invalid email format"  → MISMATCH FAIL
    ```

11. **AC verification (Bash + bullet per AC mandatory)**:
    ```
    AC-1: GIVEN... WHEN... THEN [spec]
       Actual: [paste screenshot path + observation]
       Verdict: ✅ PASS | ❌ FAIL — [reason]

    AC-2: ...
       Actual: ...
       Verdict: ...

    ... ทุก AC ต้องมี verdict + evidence path (ห้ามรวบเป็น "AC 5/5 PASS")
    ```

### Verdict format (🔴 v2.8.2 — bd-native primary, markdown fallback)

**bd active** → paste ครบใน `bd update <id> --notes` (anti-puppet) — **ONLY** ห้ามเขียน markdown ซ้ำ
**No bd** → save `outputs/REVIEW-<feature>.md` (markdown fallback) ตาม template เดียวกัน
Full evidence (Chromatic URL, axe report json, screenshot, Playwright trace) ที่ **path** — bd notes refs path เท่านั้น (compact ≤ 500 chars)
```
[Uma|state:phase-3a|bd:42|iter:1] POST verdict
- Visual diff: [Chromatic build/12346] 0.05% vs baseline (build/12345) ✅
- Hardcoded color: [Bash: rg ...] 0 found ✅
- Off-grid spacing: [Bash: rg ...] 0 found ✅
- a11y axe: [tests/a11y/checkout.json] critical=0, serious=0 ✅
- Keyboard order: [manual paste] ตรง spec ✅
- Screen reader: [manual paste] aria-label ครบ ✅
- Contrast: [npx wcag] 12.6:1 (text), 4.2:1 (UI) ✅
- States: [Playwright tests/states/] 8/8 pass ✅
- Content: [manual] microcopy ตรง spec ✅
- AC: 7/7 verdict (bullet ครบข้างบน)
- Overall: PASS → unlock Phase 3b
```

หรือ FAIL ตัวอย่าง:
```
[Uma|state:phase-3a|bd:42|iter:1] POST verdict
- Visual diff: 2.3% (button width +12px, padding 20px ไม่ใช่ 24px token)
- Hardcoded color: [Bash: rg] 2 occurrences:
  - src/checkout/Button.vue:15 `background: #3b82f6` → should be `var(--color-action-primary)`
  - src/checkout/Card.vue:8 `color: #666` → should be `var(--color-text-secondary)`
- AC-2 mobile 320px: FAIL — content overflow detected [screenshot: tests/visual/mobile-320.png]
- Overall: FAIL — 3 issues → loop Phase 2 (Dave fix hardcoded + grid spacing + mobile)
```

### ⏸️ Pre-code-review Gate (Uma POST PASS)
Block Chris+Quinn ถ้า Uma ยัง FAIL — กัน Chris/Quinn เสีย effort review code ที่ design ผิด

> Uma scope ใน Phase 3a = **verify implementation vs Phase 1b**. ไม่ใช่ redesign. ถ้า discover design issue → Loop = Phase 1b (ไม่ใช่ Phase 2)
