---
name: ui-test
description: |
  [WHAT] E2E + visual regression + a11y (axe) + mobile/responsive UI automation — บังคับ stable selector (`data-testid`).
  [WHEN] Phase 3a UI done.
  [TRIGGER] /shode-house:ui-test, "test UI", "E2E", "Playwright", "Cypress", "visual regression".
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
- ห้าม **missing aria-label/role** บน interactive element (button/input/link)
- ห้าม **touch target < 44×44** (iOS HIG) / < 48dp (Material)
- ห้าม **component state ขาด** — ทุก interactive component ต้องมี default/hover/active/focus/disabled/loading/error/empty (atomic 7 state)
- ห้าม **heading skip level** (h1→h3 ห้าม; ต้อง h1→h2→h3)
- ห้าม **flash/auto-play motion** ที่ไม่ respect `prefers-reduced-motion`
- ห้าม **i18n text overflow** — design text expand 30% (ภาษาเยอรมัน/ไทย ยาวกว่าอังกฤษ)

---

## When NOT to use

- ยังไม่มี UI ที่ render ได้ (ยังอยู่ Phase 1b design) — ยังไม่มีอะไรให้ test
- Backend-only diff · CLI tool ที่ไม่มีหน้าจอ
- Prototype ทิ้ง / spike ที่ไม่ merge

## Required inputs — refuse without

- [ ] URL หรือ dev server ที่เปิดได้จริง (ไม่มี = BLOCKED ไม่ใช่ PASS)
- [ ] Stable selector (`data-testid`) หรือสิทธิ์เพิ่มให้ได้
- [ ] Design source (Figma/wireframe/token) ที่จะเทียบ — ไม่มี = ไม่มี baseline ของ "ถูก"
- [ ] Baseline screenshot (รอบแรกให้สร้างแล้วบันทึกไว้)

## Stack

| Layer | Tool | When |
|-------|------|------|
| **E2E user journey** | **Playwright** (recommended) | cross-browser + auto-wait + trace viewer |
|  | Cypress | TS-friendly, dev experience ดี |
|  | Detox / Appium | Mobile native |
| **Component test** | Storybook + Vitest/Jest | isolated, fast |
|  | Cypress component | DOM-real |
| **Visual regression** | **Chromatic** (Storybook) | hosted, review workflow |
|  | Percy | cross-browser |
|  | BackstopJS | self-hosted |
|  | Playwright snapshot | inline (cheap) |
| **a11y** | **axe-core** (Playwright/Storybook addon) | WCAG 2.1 AA (auto) — 2.2 ดู § a11y coverage |
|  | Lighthouse a11y | full audit |
|  | Pa11y | CLI |

## a11y coverage — axe จับได้แค่ไหน (🔴)

axe-core auto-detect ครอบ **WCAG 2.1 AA เป็นหลัก** — ประมาณ 30-40% ของ success criteria ทั้งหมด และ **แทบไม่ครอบ 2.2 เลย**. "axe 0 violations" ≠ "WCAG 2.2 AA ผ่าน" — เขียนแบบนั้นคือ Anti-Puppet claim

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

## Test Pattern

### Page Object Model (POM)
```typescript
class CheckoutPage {
  constructor(private page: Page) {}
  goto = () => this.page.goto('/checkout')
  fillEmail = (v: string) => this.page.getByTestId('checkout-email').fill(v)
  pay = () => this.page.getByRole('button', {name: 'Pay'}).click()
  expectSuccess = () => expect(this.page.getByText('Order confirmed')).toBeVisible()
}
```

### Data Builder
```typescript
const cart = aCart().withItem(price=100).withCoupon('SAVE10').build()
```
- Avoid hardcoded fixture เกะกะ
- Fluent API → readable

### G-W-T Naming
```typescript
test('should apply coupon and reduce total when valid code entered', async ({page}) => {
  // Given
  await checkoutPage.goto()
  // When
  await checkoutPage.applyCoupon('SAVE10')
  // Then
  await expect(checkoutPage.total).toHaveText('฿90.00')
})
```

## Visual Regression

### Setup
- Storybook stories ครอบทุก component state (default/hover/disabled/loading/error/empty/dark)
- Chromatic / Percy snapshot baseline ทุก story
- Diff threshold: 0.1% pixel (config per story)
- Review workflow: design (Uma) approve diff ก่อน merge

### Coverage
- Component (atomic): button, input, card... (Storybook)
- Page-level: critical pages (Playwright snapshot)
- Responsive: mobile (375), tablet (768), desktop (1440)
- Theme: light + dark

## Accessibility Test (axe-core)

### Playwright + axe
```typescript
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('checkout page is a11y clean', async ({page}) => {
  await page.goto('/checkout')
  const results = await new AxeBuilder({page})
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()
  expect(results.violations).toEqual([])
})
```

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

## Mobile/Responsive Test

### Playwright projects
```typescript
projects: [
  { name: 'desktop-chrome', use: devices['Desktop Chrome'] },
  { name: 'mobile-iphone', use: devices['iPhone 13'] },
  { name: 'mobile-android', use: devices['Pixel 5'] },
  { name: 'tablet', use: devices['iPad Pro'] },
]
```

### Critical Mobile Test
- Touch target ≥ 44×44 px
- Swipe gesture (back, dismiss)
- Orientation change (portrait/landscape)
- Network throttling (slow 3G)

## CI Integration (Aaron wire)

```yaml
e2e:
  needs: deploy-staging
  steps:
    - playwright test --grep @smoke   # PR: smoke only
    - playwright test                 # main: full suite
  artifacts:
    - playwright-report/              # trace + screenshot + video
    - test-results/                   # failure detail
```

- **Trace + screenshot + video** on failure (Playwright auto)
- **Sharding**: parallel ใน CI matrix (2-4 shards)
- **Retry**: ครั้งเดียว เพื่อ filter flaky → flaky = bd issue

## Storybook + Test Discipline

- Story = test case + design doc
- `play()` function = interaction test
- a11y addon (`@storybook/addon-a11y`) = inline check
- Visual: Chromatic auto-snapshot ทุก story

## ห้าม

- ห้ามใช้ CSS class / xpath เป็น selector
- ห้าม `waitForTimeout` (sleep) → explicit wait
- ห้าม shared state ระหว่าง test
- ห้าม test order dependency
- ห้าม skip a11y check on critical page
- ห้าม baseline visual diff โดย Uma ไม่ได้ review
- ห้าม commit failing snapshot (ใช้ `--update-snapshots` มี ticket review)
- ห้าม disable test silently → bd issue + retry plan
