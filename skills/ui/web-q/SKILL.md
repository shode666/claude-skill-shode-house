---
name: web-q
description: |
  [WHAT] Web quality discipline — Core Web Vitals (LCP/INP/CLS) + Lighthouse + SEO + structured data + CSP + security headers + measured threshold/budget.
  [WHEN] Public-facing frontend project.
  [TRIGGER] /shode-house:web-q, "Core Web Vitals", "LCP", "INP", "CLS", "Lighthouse".
---

# Web-Q (Web Quality discipline — CWV + SEO + Sec headers)

> Port + adapt จาก [`addyosmani/web-quality-skills`](https://github.com/addyosmani/web-quality-skills) (MIT)
> **Owners cross-cutting**: Uma (Phase 1b AC + 3a Lighthouse) + Dave (impl) + Quinn (Phase 3b CI gate) + Aaron + **Sentinel** (security headers)

## When NOT to use

- Internal tool / admin ที่ไม่ public-facing และไม่มี SEO/CWV requirement
- Backend-only หรือ API-only service
- Prototype ที่ยังไม่ deploy

## Required inputs — refuse without

- [ ] URL ที่ deploy แล้ว (staging/prod) — Lighthouse บน localhost ไม่ใช่ตัวแทน field data
- [ ] Threshold ที่ตกลงกันแล้ว (LCP/INP/CLS budget) — ไม่มี = ไม่มีเส้นแบ่ง pass/fail
- [ ] Device/network profile ที่จะวัด (mobile 4G เป็น default)

## 🎯 4 Axes (ผ่านทั้งหมด ก่อน prod)

| Axis | Metric | Target (p75) | Tool |
|------|--------|--------------|------|
| **CWV** | LCP / INP / CLS | ≤ 2.5s / ≤ 200ms / ≤ 0.1 | Lighthouse + web-vitals |
| **Budget** | JS/CSS/IMG/FONT/3P bytes | ดู table | Lighthouse `budget.json` |
| **SEO** | title/canonical/structured data | 100% must-have | Lighthouse SEO + Schema.org validator |
| **Sec headers** | CSP/HSTS/SRI/Trusted Types | enforce mode | mozilla-observatory + securityheaders.com |

ห้าม "perf=92" — ต้อง breakdown 4 axes พร้อม Lighthouse JSON path

---

## 1. Core Web Vitals

### LCP fix (Dave/Uma audit)

```html
<!-- ✅ Preload + fetchpriority -->
<link rel="preload" href="/hero.webp" as="image" fetchpriority="high">
<img src="/hero.webp" alt="..." fetchpriority="high" width="1200" height="600">

<!-- ✅ Critical CSS inlined (< 14KB) -->
<style>/* above-fold */</style>
<link rel="preload" href="/styles.css" as="style"
      onload="this.onload=null;this.rel='stylesheet'">

<!-- ✅ Speculation Rules — prerender next-likely (moderate eagerness) -->
<script type="speculationrules">
{"prerender":[{"where":{"href_matches":"/*"},"eagerness":"moderate"}]}
</script>
```

### INP fix

```javascript
// ❌ Long task blocks
items.forEach(item => heavy(item))  // 800ms

// ✅ Break with scheduler.yield (Chrome 129+)
for (const item of items) {
  heavy(item)
  if (navigator.scheduling?.isInputPending()) await scheduler.yield()
}

// ✅ React 18 useTransition for non-urgent
const [pending, startTransition] = useTransition()
startTransition(() => setFilter(newFilter))
```

### CLS fix

```html
<img src="..." width="800" height="400" alt="..."> <!-- explicit dim -->
@font-face { font-display: optional; }              <!-- no swap = no CLS -->
<div class="ad-slot" style="min-height: 250px"></div> <!-- reserve space -->
```

### Measure (Bash mandatory — Uma 3a + Aaron 5)

```bash
# Lab (per-build CI)
npx lhci collect --url=http://localhost:3000/checkout --numberOfRuns=3
npx lhci assert --preset=lighthouse:recommended

# Field (production p75 RUM)
import {onLCP, onINP, onCLS} from 'web-vitals'
onLCP(m => sendBeacon('/metrics/lcp', m.value))
```

---

## 2. Performance Budget

`lighthouse-budget.json`:

```json
[{
  "path": "/*",
  "resourceSizes": [
    {"resourceType": "script", "budget": 300},
    {"resourceType": "stylesheet", "budget": 100},
    {"resourceType": "image", "budget": 500},
    {"resourceType": "font", "budget": 100},
    {"resourceType": "third-party", "budget": 200},
    {"resourceType": "total", "budget": 1500}
  ],
  "timings": [
    {"metric": "largest-contentful-paint", "budget": 2500},
    {"metric": "interaction-to-next-paint", "budget": 200},
    {"metric": "cumulative-layout-shift", "budget": 100}
  ]
}]
```

Aaron CI (`.lighthouserc.json`):
```json
{"ci": {
  "collect": {"numberOfRuns": 3, "settings": {"budgetPath": "./lighthouse-budget.json"}},
  "assert": {"preset": "lighthouse:recommended"}
}}
```

---

## 3. SEO (Emma + Brooke + Uma public-facing)

### Must-have
```html
<title>... 50-60 char</title>
<meta name="description" content="... 150-160 char">
<link rel="canonical" href="...">
<meta property="og:title" content="..."> <meta property="og:image" content="...">
<meta name="twitter:card" content="summary_large_image">
<html lang="th">
<h1>... single h1 ...</h1>
```

### JSON-LD per domain (mandatory)
| Domain | Schema |
|--------|--------|
| Emma product page | `Product` + `Offer` + `AggregateRating` + `BreadcrumbList` |
| Emma category | `BreadcrumbList` + `ItemList` |
| Brooke property | `LodgingBusiness` / `Hotel` + `aggregateRating` |
| Brooke confirmation | `Reservation` |
| Org-wide | `Organization` + `WebSite` + `SearchAction` |
| Article/blog | `Article` + `Author` |

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"...","offers":{"@type":"Offer","price":"1234.56","priceCurrency":"THB"}}
</script>
```

### Crawl infra
- `/robots.txt` — allow + `Sitemap:` line
- `/sitemap.xml` — auto-gen, < 50K URLs/file, `<lastmod>` ทุก URL
- Mobile-friendly: tap target ≥ 48×48px

---

## 4. Security Headers (Sentinel + Aaron)

```nginx
# CSP — start report-only แล้ว flip enforce
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'nonce-$REQUEST_ID'; style-src 'self' 'nonce-$REQUEST_ID'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'; require-trusted-types-for 'script'; trusted-types default" always;

# HSTS preload-ready
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Other
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(self)" always;

# ❌ ห้าม X-XSS-Protection (deprecated, มี vuln เอง)
```

### Trusted Types (DOM XSS — Baseline 2026)
```javascript
const escape = trustedTypes.createPolicy('default', {
  createHTML: (s) => DOMPurify.sanitize(s, {RETURN_TRUSTED_TYPE: true})
})
element.innerHTML = escape.createHTML(userInput)  // ✅
```

Rollout: `Content-Security-Policy-Report-Only` ก่อน → flip enforce

### SRI for external CDN script (mandatory)
```html
<script src="https://cdn.example.com/lib@1.2.3/dist/lib.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```
Generate: `openssl dgst -sha384 -binary file.js | openssl base64 -A`

### Verify (Bash)
```bash
curl -sI https://example.com | grep -iE "csp|hsts|x-content|x-frame|referrer"
npx observatory-cli example.com           # grade ≥ A
```

---

## Universal Web-Q Rules (🔴 บังคับทุก agent)

1. ห้าม "perf ok" — paste Lighthouse JSON path + 4-axis breakdown
2. ทุก image > 50KB ต้องมี `width` + `height` (CLS prevent)
3. ทุก LCP candidate ต้อง `fetchpriority="high"` + preload
4. ทุก non-critical script → `defer` หรือ dynamic import
5. ทุก @font-face ต้อง `font-display: swap` (optional ดีกว่า)
6. ทุก 3rd-party script add → budget check (≤ 200KB total)
7. ทุก public page → canonical + meta desc + h1 เดียว
8. ทุก domain entity → JSON-LD per table ข้างบน
9. ทุก prod deploy → CSP enforce + HSTS preload-ready
10. ทุก external CDN script → SRI `integrity` + `crossorigin`

---

## Phase wiring (where this skill activates)

- **Phase 1a Bella**: AC template เพิ่ม CWV target + SEO must-have row
- **Phase 1a Sara**: ADR เพิ่ม "Performance budget" + CSP rollout date
- **Phase 1b Uma**: Lighthouse target ใน AC + Structured Data spec per page
- **Phase 1c Sentinel**: CSP/Trusted Types/SRI policy + headers spec
- **Phase 2 Dave**: implement ตาม Universal Rules + smoke `npx lhci collect`
- **Phase 3a Uma POST**: Lighthouse Bash + paste JSON + 4-axis breakdown
- **Phase 3b Quinn**: Lighthouse CI perf ≥ 90 + budget pass gate
- **Phase 3b Sentinel**: mozilla-observatory grade ≥ A + securityheaders ≥ A
- **Phase 5 Aaron**: prod Lighthouse (mobile+desktop) + observatory pre-deploy gate
- **Phase 6 Reggie**: web-vitals RUM live + p75 alarm

---

## Evidence format

```
✅ "[Lighthouse: .lighthouseci/lhr-mobile.json] LCP=1.8s INP=120ms CLS=0.05 perf=94 seo=98 → PASS"
✅ "[budget: lighthouse-budget.json] script=287KB/300 total=1.42MB/1.5 → PASS"
✅ "[Observatory: api.com] grade=A+, score=115/100"
✅ "[Schema validator: validator.schema.org] Product valid, 0 error"
❌ "Lighthouse ผ่าน" (no path, no breakdown)
```

## Reference
- [Addy Osmani web-quality-skills](https://github.com/addyosmani/web-quality-skills) (MIT, port source)
- [Google web.dev Vitals](https://web.dev/articles/vitals)
- [Mozilla Observatory](https://observatory.mozilla.org/)
