---
name: automation-patterns
description: Reference (lazy-load) ของ `ui-test` — tool stack, test patterns, visual-regression setup, axe script, device matrix, CI wiring. โหลดเมื่อเขียน/ดูแล automated E2E / visual-regression / a11y test เท่านั้น
---

```lazy-load-contract
LOAD: skills/ui/ui-test/automation-patterns.md
WHEN: writing_or_maintaining_ui_test_automation=true
OWNER: qa-engineer
REQUIRED-BEFORE: ui_test_code_commit
```

# UI test automation patterns

> Reference material; กฎบังคับ (universal UI rules, a11y gate, evidence ladder, selector/wait, ห้าม) อยู่ที่ root `SKILL.md` และยังมีผลเสมอ


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
