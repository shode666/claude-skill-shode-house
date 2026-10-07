---
name: ux-ui-designer-catalogue
description: Reference (lazy-load) for ux-ui-designer - advisory boundaries, pattern-choice checks, scope catalogue, other routing rows, best practices, hand-off, output format and citation examples. Load before design work.
---

```lazy-load-contract
LOAD: references/runbooks/ux-ui-designer-catalogue.md
WHEN: task in {ux_research,ia,wireframe,visual,design_system,a11y,usability,mobile,motion}
OWNER: ux-ui-designer
REQUIRED-BEFORE: design_artifact_written
```

# ux-ui-designer - design catalogue

**Contents**

- [Pattern choice](#pattern-choice)
- [ขอบเขต](#ขอบเขต)
- [Other routing rows](#other-routing-rows)
- [Best Practices](#best-practices)
- [Hand-off → developer](#hand-off--developer)
- [Output Format](#output-format)
- [Design discipline](#design-discipline)
- [Citation examples](#citation-examples)

> Lazy reference for `ux-ui-designer`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.

**Advisory role ต่อ agent อื่น** (proactive — ไม่ต้องรอถูกถาม):

| Agent | ux-ui-designer แนะนำเรื่อง | Boundary (zero-overlap) |
|-------|----------------|-------------------------|
| **solution-architect** | UX impact ของ architecture choice (SSR vs SPA → perceived perf, offline UX, latency budget) | solution-architect ยังเป็น owner ของ C4/ADR — ux-ui-designer ให้ UX constraint เป็น input |
| **developer** | Implementation fidelity: token ถูกตัว, state ครบ 7, motion/easing spec, responsive behavior | developer ยังเป็น owner ของ code — ux-ui-designer review ผ่าน Phase 3a gate |
| **business-analyst** | UX acceptance criteria ใน BRD/FRD (usability metric, a11y AC, error/empty state coverage) | business-analyst ยังเป็น owner ของ spec — ux-ui-designer ให้ AC เป็น input ก่อน Phase 1a close |

## Pattern choice

- เลือก pattern/library (Material vs HIG vs Tailwind) → cite platform + brand evidence ก่อนเสนอ ไม่เลือกตามความเคยชินหรือ option แรก; ไม่แน่ใจ → หยุด ส่ง options + recommendation ให้ the router
- ห้าม Material UI default บน iOS premium app → HIG-native + brand audit ก่อน
- Verify fit per platform + brand for the user's design system; report material constraints without overriding a settled preference
- Mobile: iOS = HIG; Android = Material; cross-platform = headless tokens + platform-aware components

## ขอบเขต

### 1. UX Research
- **Interview** (5-7 คน เห็น pattern), **Survey** (≥30), Persona (≤5), JTBD
- **Journey Map**, Service blueprint, Empathy Map
- Card sorting / tree testing for IA
- Tools: Maze, UserTesting, Lookback, Dovetail, FigJam

### 2. IA + Wireframe
- Sitemap, user flow (happy + edge + error)
- Wireframe: low-fi → mid-fi (Figma)
- Content design: microcopy, error, empty state, button (verb-driven)
- Heuristic eval: Nielsen 10

### 3. Visual / UI
- Visual hierarchy (size/weight/color/contrast/space)
- Typography: scale (1.25/1.333/1.5), line-height (body 1.4-1.6, heading 1.1-1.3)
- Color: HSL/OKLCH, semantic + state
- Spacing: 4-pt or 8-pt grid
- Iconography: Lucide/Heroicons/Phosphor
- Dark mode: semantic token (ไม่ invert)
- **Mobile-first** → desktop expand

### 4. Design System

**Atomic** (Brad Frost): Atom → Molecule → Organism → Template → Page

**Tokens** (W3C DTCG):
- Primitive: `color.blue.500: #3b82f6`
- Semantic: `color.action.primary: {color.blue.500}`
- Component: `button.primary.background: {color.action.primary}`
- Export: Style Dictionary / Tokens Studio → CSS var / iOS / Android

Governance: contribution model, semver, deprecation, Storybook (a11y addon), visual regression (Chromatic/Percy)

### 5. Accessibility (WCAG 2.1 AA + 2.2 AA)

**POUR**: Perceivable / Operable / Understandable / Robust

Practical (2.1 AA):
- Tools: **axe DevTools**, Lighthouse, Pa11y, Stark (Figma), screen readers

### 6. Usability + Validation
- Moderated (5 users, Nielsen rule of 5), unmoderated (Maze)
- A/B test (sample size + significance)
- Analytics: heatmap (Hotjar), session replay (FullStory)
- **SUS** score (≥68 average, ≥80 excellent)

### 7. Mobile

| Platform | Guideline |
|----------|-----------|
| iOS | **HIG** — Bottom tab, swipe-back, large title, SF Symbols, Dynamic Type |
| Android | **Material 3** — FAB, bottom nav, dynamic color |
| Web | WAI-ARIA APG |

### 8. Motion
- Easing: ease-in-out (default), ease-out (enter), ease-in (exit)
- Duration: 150-250ms (small), 300-400ms (large)
- Tools: Lottie, Framer Motion, Rive

## Other routing rows

| งาน | ใคร |
|-----|-----|
| Research/IA/wireframe/visual/design system (Phase 1) | ux-ui-designer |
| a11y audit (manual + axe automation) | ux-ui-designer |
| Visual regression baseline + review (Phase 3) | ux-ui-designer + qa-engineer (automate) |
| Requirement | → business-analyst ก่อน (Phase 1 Coop) |
| Animation complex | ux-ui-designer spec + developer implement |

## Best Practices

- **Accessibility-first** ตั้งแต่ wireframe — ห้าม retrofit
- **Consistency > creativity** — design system rules
- **Content-first** — copy ก่อน layout
- **Empty/loading/error/disabled** = first-class state ทุก component
- **Touch target ≥ 44×44** (HIG) / 48dp (Material)
- **i18n-ready** — text expand 30%, RTL, locale
- **Atomic design + token hierarchy**

## Hand-off → developer

- **Design reference**: accessible approved artifact and revision (Figma dev mode/frame link when used)
- **Tokens**: W3C DTCG JSON → Style Dictionary → Tailwind/CSS var/iOS/Android
- **Asset**: SVG + 1×/2×/3× PNG (SVGO optimized)
- **Spec**: state (default/hover/active/focus/disabled/loading/error/empty), responsive, motion
- **a11y note**: aria-label, role, keyboard interaction
- **AC**: G-W-T visual + interaction

## Output Format

```markdown
# UX/UI: [feature]

## 1. Discovery (persona + JTBD + journey + success metric)
## 2. IA + Flow (Mermaid)
## 3. Wireframe / Visual (Figma link + frame ID)
## 4. Tokens (Primitive / Semantic / Component)
## 5. a11y Checklist
- [ ] Contrast ≥ 4.5:1
- [ ] Keyboard
- [ ] Screen reader
- [ ] Reduced motion
- [ ] WCAG AA
## 6. Hand-off (Figma + tokens.json + spec)
```

## Design discipline

- Ground design in available user/project evidence; request missing consequential research through the router/business-analyst, reusing existing validated research when sufficient
- ห้ามสร้าง one-off component ขัด design system
- ห้าม override platform pattern ไม่มีเหตุผล
- ห้าม design ที่พังกับ real content/data

## Citation examples

```
✅ "[axe report: tests/a11y/checkout-report.json] critical=0, serious=2"
✅ "[Chromatic baseline: build/12345] diff=0.08%, threshold=0.1% → PASS"
✅ "[Lighthouse: build/lh-report.html] a11y=98, perf=92"
✅ "[screenshot: tests/visual/checkout-after.png] vs baseline:checkout-before.png"
✅ "[Playwright trace: playwright-report/trace.zip] keyboard order verified"
❌ "UI ดูดี contrast ผ่าน" (no tool output, no path)
❌ "a11y ok" (no axe report, no manual checklist paste)
❌ "matches Figma" (no screenshot diff, no Chromatic URL)
```
