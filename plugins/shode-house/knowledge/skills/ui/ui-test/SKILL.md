---
name: ui-test
description: Automated browser-level end-to-end, visual regression and accessibility testing of a changed, rendered user interface, plus the UI quality rules every frontend change follows. Not for backend-only changes, unrendered designs, or site performance audits.
---

# UI Test (E2E + Visual + a11y automation)

> **Owner**: Quinn (E2E + a11y) + Uma (visual regression spec) + Dave (test ID hooks)

## 🔴 Universal UX/UI Quality Rules (บังคับทุก frontend agent — ย้ายมาจาก `shode-house-discipline` v3.10)

- ห้าม **hardcoded color** ใน code → use semantic token (CSS var / tailwind class จาก tokens.json)
- ห้าม **hardcoded spacing** ที่ไม่ใช่ 8-pt grid (`4px / 8px / 12px / 16px / 24px / 32px / 48px / 64px`) — token ปกติ scale 1.0 / 1.5 / 2
- ห้าม **focus order ≠ visual order** (no `tabindex>0`; rely on DOM order)
- ห้าม **contrast < 4.5:1** สำหรับ text หรือ **< 3:1** สำหรับ UI/large text (WCAG AA)
- ห้าม **color เดี่ยวสื่อ status** (ต้องคู่กับ icon/label/pattern)
- ห้าม **fixed-pixel layout** ที่ไม่ responsive — mobile-first 320px expand
- ห้าม **missing focus indicator** (default browser outline ok; ห้าม `outline: none` without alternative)
- Interactive elements need an accessible name, role and state; prefer native
  semantics and associated labels. Add ARIA only where those semantics are missing.
- ห้าม **touch target < 44×44** (iOS HIG) / < 48dp (Material)
- ห้าม **applicable component state ขาด** — cover default/hover/active/focus and
  disabled/loading/error/empty where the component's behavior supports those states.
- ห้าม **heading skip level** (h1→h3 ห้าม; ต้อง h1→h2→h3)
- ห้าม **flash/auto-play motion** ที่ไม่ respect `prefers-reduced-motion`
- ห้าม **i18n text overflow** — design text expand 30% (ภาษาเยอรมัน/ไทย ยาวกว่าอังกฤษ)

---

## When NOT to use

- ยังไม่มี UI ที่ render ได้ (ยังอยู่ Phase 1b design) — ยังไม่มีอะไรให้ test
- Backend-only diff · CLI tool ที่ไม่มีหน้าจอ
- Prototype ทิ้ง / spike ที่ไม่ merge

## Required inputs — for the applicable check

- [ ] URL หรือ dev server ที่เปิดได้จริง (ไม่มี = BLOCKED ไม่ใช่ PASS)
- [ ] Stable selector: accessible role/name or existing `data-testid`; add test hooks only when needed and authorized
- [ ] Design source or existing approved design-system reference for design-conformity checks
- [ ] Baseline screenshot for visual-regression comparison (รอบแรกให้สร้างแล้วบันทึกไว้)

Missing a visual baseline blocks that comparison, not independent functional or
accessibility checks. Report each applicable check's actual evidence and limitations.

## References — load only when needed

- Writing or maintaining automated E2E / visual-regression / a11y tests (tool choice, Page Object / data builder, snapshot setup, axe script, device matrix, CI wiring, Storybook) → load `automation-patterns.md` first.
- Reviewing, manually verifying or implementing a UI change → this root is enough; do not load the reference.
- Backend-only work loads neither this skill nor its reference.

## a11y coverage — axe จับได้แค่ไหน (🔴)

axe-core includes WCAG 2.2 AA rule tags; coverage depends on version and enabled rules ([Deque rule tags](https://www.deque.com/axe/core-documentation/api-documentation/)). No fixed coverage percentage proves conformance. "axe 0 violations" ≠ "WCAG 2.2 AA ผ่าน"; retain manual and interaction checks.

| ชั้น | ครอบ | ใครรับผิดชอบ |
|---|---|---|
| axe-core ใน CI | contrast, alt, label, ARIA misuse, heading order, landmark | Quinn (gate) |
| Playwright assertion เขียนเอง | 2.4.11 focus not obscured · 2.5.8 target size ≥24×24 CSS px | Quinn (เขียน) + Dave (test id) |
| Manual walkthrough + paste evidence | 2.5.7 dragging alternative · 3.3.7 redundant entry · 3.3.8 accessible auth (paste + password manager) | Uma (Phase 3a) |

ดูรายละเอียด criterion + วิธีตรวจต่อข้อที่ `agents/ux-ui-designer.md` § 5. Accessibility

## 🌐 Visual evidence ladder

**Visual/interaction evidence — บังคับก่อน PASS (v3.12: บังคับ *หลักฐาน* ไม่ใช่บังคับ *tool ตัวใดตัวหนึ่ง*)**

plugin **ไม่ได้จัดหา** browser MCP (`.mcp.json` มีแค่ Context7) และชื่อ tool ต่างกันตาม config ของผู้ใช้ → บังคับ MCP ตรง ๆ = ออกแบบให้ block ด้วยของที่ agent ใช้ไม่ได้

ไล่จากบนลงล่าง หยุดที่ตัวแรกที่ใช้ได้จริง:
1. **Playwright script ผ่าน `Bash`** (พึ่งพาได้เสมอ — `Bash` อยู่ใน `tools:` ของ Chris/Quinn อยู่แล้ว): navigate → screenshot → `console` + network log → paste path + บรรทัดที่มี signal
2. **browser MCP** ถ้า session นั้นมีจริง (เช็คว่ามี tool ชื่อขึ้นต้น `mcp__` ที่เป็น browser ก่อนเรียก — ห้าม hardcode ชื่อ)
3. ทำทั้งสองทางไม่ได้ → **verdict = BLOCKED ไม่ใช่ PASS** + ระบุว่าขาด browser automation แล้วขอจาก user

หลักฐานที่ต้องได้เหมือนกันทุกทาง: **screenshot path จริง · console error (หรือยืนยันว่าไม่มี) · network status ของ request หลัก**

## Selector Strategy (🔴)

**Priority**:
1. `data-testid` (Dave add ตอน implement) — stable
2. ARIA role + accessible name (`getByRole('button', {name: 'Pay'})`)
3. Text (i18n-aware: alias text key)
4. ❌ CSS class / xpath (brittle — break เมื่อ CSS เปลี่ยน)

**Convention**: `data-testid="<feature>-<element>"` เช่น `checkout-pay-button`, `cart-item-row`

## Wait Strategy (🔴 ห้าม sleep)

- **Auto-wait** (Playwright/Cypress default): wait for actionable
- **Explicit wait**: `await expect(locator).toBeVisible()`, `waitForResponse()`, `waitForURL()`
- **Network idle**: `waitForLoadState('networkidle')` เฉพาะที่จำเป็น
- ❌ `await page.waitForTimeout(2000)` — bug magnet

## Accessibility gate

### a11y Coverage (🔴 บังคับ)
- ทุก critical page → axe scan ใน CI
- Manual: keyboard navigation (tab order = visual order)
- Screen reader spot check (VoiceOver/NVDA): label + role + state

### Common WCAG Violations (Block PR)
- `color-contrast` — text < 4.5:1, UI < 3:1
- `label` — input ไม่มี associated label
- `aria-required-attr` — ARIA missing required attribute
- `image-alt` — img ไม่มี alt
- `landmark-one-main` — page ไม่มี `<main>`
- `heading-order` — skip heading level

## Evidence rule (Catalog ≠ Evidence)

- Tool output from this run — axe / Lighthouse / Playwright report, screenshot, console + network log — is evidence: cite the command and the artifact path. Catalog ≠ evidence → `references/design-intel/README.md` § กฎเหล็ก.
- An axe or Lighthouse pass is evidence only for the rules it ran (see a11y coverage above); the manual keyboard and screen-reader checks stay.

## Completion boundary

- PASS = every applicable check has evidence from this run, no open a11y blocker, and any visual diff reviewed by Uma.
- No reachable UI, no browser automation, or a missing input for an applicable check → that check is BLOCKED, not PASS; report what is missing.
- This skill yields evidence and a verdict for the Phase 3a / QA gate owner; it does not approve release. Stop and report instead of changing product code, adding test hooks or updating a baseline without authorization.

## ห้าม

- ห้ามใช้ CSS class / xpath เป็น selector
- ห้าม `waitForTimeout` (sleep) → explicit wait
- ห้าม shared state ระหว่าง test
- ห้าม test order dependency
- ห้าม skip a11y check on critical page
- ห้าม baseline visual diff โดย Uma ไม่ได้ review
- ห้าม commit failing snapshot (ใช้ `--update-snapshots` มี ticket review)
- ห้าม disable test silently → ticket + retry plan
