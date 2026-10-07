---
name: ux-ui-designer-phase-3a
description: Runbook (lazy-load) ของ ux-ui-designer — Phase 3a POST-Check. โหลดเมื่อเข้า phase นี้จริงเท่านั้น
---

```lazy-load-contract
LOAD: references/runbooks/ux-ui-designer-phase-3a.md
WHEN: phase=3a AND frontend_changed=true
OWNER: ux-ui-designer
REQUIRED-BEFORE: phase_3a_verdict
```

# Phase 3a POST-Check — ux-ui-designer

**Contents**

- [🔎 Phase 3a POST-Check (🔴 v2.8 — sequential gate BEFORE code-reviewer+qa-engineer)](#-phase-3a-post-check--v28--sequential-gate-before-code-reviewerqa-engineer)
  - [Process (Phase 3a) — 🔴 v2.8.1 evidence = design-run report + Read/Grep output](#process-phase-3a---v281-evidence--design-run-report--readgrep-output)
  - [Verdict format (🔴 v2.8.2 — bd-native primary, markdown fallback)](#verdict-format--v282--bd-native-primary-markdown-fallback)
  - [⏸️ Pre-code-review Gate (ux-ui-designer POST PASS)](#️-pre-code-review-gate-ux-ui-designer-post-pass)

> แยกจาก agent prompt v3.12.1 — consultation สั้น ๆ ไม่ต้องแบก runbook ของทุก phase

Use the harness's actual host tools and confirmed evidence home. You have no Bash:
Playwright, axe and contrast checks run through a design-run request (format and rules:
`references/runbooks/ux-ui-designer-phase-1b.md` § Design-run request, with `"phase": "3a"`
and the templates whose `phases` include `3a`); reading and searching use Read/Grep. Record
any unperformed check and do not claim PASS for missing evidence.

## 🔎 Phase 3a POST-Check (🔴 v2.8 — sequential gate BEFORE code-reviewer+qa-engineer)

หลัง developer implement (Phase 2 done) → ux-ui-designer ตรวจ **ก่อน** code-reviewer+qa-engineer เริ่ม (gate)

### Process (Phase 3a) — 🔴 v2.8.1 evidence = design-run report + Read/Grep output

ห้าม claim PASS โดยไม่มี tool output — anti-puppet UX/UI (`shode-house-deliverable` § Anti-Puppet Rule) บังคับ cite evidence

1. **Read context** (Read): the task in the confirmed tracker · `outputs/SPEC-<bd-id>.md` (Phase 1b artifacts: own AC + baseline report path)
2. **App reachable**: Playwright `test` templates (`ui-capture`, `visual-diff`, `state-tests`) start the app through the tracked Playwright config (`webServer`). `ui-screenshot` and `axe-scan` need it already running at a loopback URL. Not running → ask the router for the role that starts it (developer or devops-engineer); never a command line.
3. **Capture current screenshot**: `ui-capture` (`feature`) and/or `ui-screenshot` (`viewport_w` e.g. 375, `viewport_h` e.g. 812, `url`) → cite the report artifact `<run-id>.png`
4. **Visual diff**: `visual-diff` (fixed filter "visual regression") → cite the run's exit + diff lines from its raw output; flag deviation > 0.1% (threshold ปรับตามทีม). Chromatic is not in the catalogue (third-party upload = a user-confirmed step outside the runner)
5. **Design adherence (Grep, read-only)**:
   - hardcoded color: `(color|background|border):\s*#[0-9a-fA-F]{3,8}` in `src/<feature>/` (css/vue/tsx) → ต้อง empty; เจอ = FAIL (ใช้ token instead)
   - spacing: `(padding|margin):\s*[0-9]+px` in `src/<feature>/`, minus the grid values 0/2/4/8/12/16/24/32/48/64px → ต้อง empty; off-grid = FAIL
6. **a11y axe**: `axe-scan` (`url`) → Read the report artifact `<run-id>.axe.json`: violations by id, impact, node count; critical=0, serious ≤ tolerance
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
8. **Contrast verify**: `contrast-pair` (`fg`, `bg` = `#RRGGBB`) → ratio from the run's raw output; or axe ครอบแล้ว — re-confirm in the axe artifact
9. **Component state validation**: `state-tests` (`feature`; `tests/states/<feature>.spec.ts` ต้องครอบ default/hover/active/focus/disabled/loading/error/empty) → cite 8/8 pass หรือ list failed states
10. **Content design check** — paste actual text vs spec:
    ```
    Spec error message: "อีเมลไม่ถูกต้อง"
    Actual: "Invalid email format"  → MISMATCH FAIL
    ```
11. **AC verification (bullet per AC mandatory)**:
    ```
    AC-1: GIVEN... WHEN... THEN [spec]
       Actual: [report artifact path + observation]
       Verdict: ✅ PASS | ❌ FAIL — [reason]

    AC-2: ...
       Actual: ...
       Verdict: ...

    ... ทุก AC ต้องมี verdict + evidence path (ห้ามรวบเป็น "AC 5/5 PASS")
    ```

### Verdict format (🔴 v2.8.2 — bd-native primary, markdown fallback)

Store the complete verdict and per-AC evidence in one canonical report in the
confirmed evidence home. If that home is Beads, use its authorized notes operation;
otherwise use the confirmed service or Markdown fallback. Task notes may link to
the report and full evidence (design-run report, axe JSON, screenshots, trace). Keep
summaries concise without a character cap that removes findings, dissent or checks.
```
[ux-ui-designer|state:phase-3a|bd:42|iter:1] POST verdict
- Design-run report: outputs/42/design-run/07-design-run-order-3a-iter1.report.json (sha256 relayed by the router)
- Visual diff: [report r2 visual-diff exit 0] 0.05% vs baseline ✅
- Hardcoded color: [Grep ...] 0 found ✅
- Off-grid spacing: [Grep ...] 0 found ✅
- a11y axe: [report r3 r3.axe.json] critical=0, serious=0 ✅
- Keyboard order: [manual paste] ตรง spec ✅
- Screen reader: [manual paste] aria-label ครบ ✅
- Contrast: [report r4 contrast-pair] 12.6:1 (text), 4.2:1 (UI) ✅
- States: [report r5 state-tests] 8/8 pass ✅
- Content: [manual] microcopy ตรง spec ✅
- AC: 7/7 verdict (bullet ครบข้างบน)
- Overall: PASS → unlock Phase 3b
```

หรือ FAIL ตัวอย่าง:
```
[ux-ui-designer|state:phase-3a|bd:42|iter:1] POST verdict
- Visual diff: 2.3% (button width +12px, padding 20px ไม่ใช่ 24px token)
- Hardcoded color: [Grep] 2 occurrences:
  - src/checkout/Button.vue:15 `background: #3b82f6` → should be `var(--color-action-primary)`
  - src/checkout/Card.vue:8 `color: #666` → should be `var(--color-text-secondary)`
- AC-2 mobile 320px: FAIL — content overflow detected [report r1 r1.png]
- Overall: FAIL — 3 issues → loop Phase 2 (developer fix hardcoded + grid spacing + mobile)
```

### ⏸️ Pre-code-review Gate (ux-ui-designer POST PASS)
Block code-reviewer+qa-engineer ถ้า ux-ui-designer ยัง FAIL — กัน code-reviewer/qa-engineer เสีย effort review code ที่ design ผิด

> ux-ui-designer scope ใน Phase 3a = **verify implementation vs Phase 1b**. ไม่ใช่ redesign. ถ้า discover design issue → Loop = Phase 1b (ไม่ใช่ Phase 2)
