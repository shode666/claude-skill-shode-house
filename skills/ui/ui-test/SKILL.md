---
name: ui-test
description: |
  [WHAT] E2E + visual regression + a11y (axe) + mobile/responsive UI automation — บังคับ stable selector (`data-testid`).
  [AUDIENCE] Quinn (E2E + a11y) + Uma (visual regression spec) + Dave (test ID hooks).
  [WHEN] Phase 3a UI done; Phase 3b verify; ก่อน frontend deploy; หลัง design system change.
  [TRIGGER] /shode-house:ui-test, "test UI", "E2E", "Playwright", "Cypress", "visual regression", "accessibility test", "axe", "Storybook test", "ทดสอบหน้าเว็บ", "ทดสอบแอป", "UI automation".
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
| **a11y** | **axe-core** (Playwright/Storybook addon) | WCAG 2.1/2.2 AA |
|  | Lighthouse a11y | full audit |
|  | Pa11y | CLI |

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
