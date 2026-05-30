---
name: shode-house-evidence
description: |
  [WHAT] Evidence protocol — Project Evidence (NO MAGIC extension) + UX Evidence + Domain Evidence + REVIEW report format. บังคับ cite ก่อน claim.
  [AUDIENCE] ทุก agent ที่ผลิต claim/finding; Domain experts (Felix/Iris/Sam/Tara/Elena/Brooke/Emma); Uma (UX claim); Chris (review report).
  [WHEN] ทุกครั้งที่ agent claim "ระบบนี้ทำ X" หรือ "regulation บังคับ Y" หรือ "perf p95 = Z"; ก่อน hand-off; เขียน REVIEW report.
  [TRIGGER] /shode-house:evidence, "Project Evidence", "UX Evidence", "Domain Evidence", "cite", "evidence", "regulation cite", "REVIEW report", "WCAG", "axe", "Lighthouse".
---

# shode-house — Evidence Protocol

> ทุก claim ต้องมี evidence ตามมาทันที. ห้าม "ผมคิดว่า..." "น่าจะ..." "โดยปกติ..."

---
## 🔍 Project Evidence Protocol (🔴 v2.4 — NO MAGIC extension)

**Real-world knowledge ≠ project-specific fact.** ก่อน claim ใดๆ เกี่ยว stack/version/config/feature/convention ของ project นี้ — ต้อง verify ด้วย artifact จริงของ project

### 🚫 Forbidden phrase (ใช้ = ต้องมี evidence ตามมาทันที)
- "usually" / "by default" / "typically" / "standard practice" / "best practice"
- "Spring Boot/PG/Node/React ใช้..." (โดยไม่ check version + config)
- "should support" / "น่าจะรองรับ" / "ปกติแล้ว"
- "in most cases" / "โดยทั่วไป"

### ✅ Required evidence types
| Claim category | Evidence (paste actual output) |
|----------------|--------------------------------|
| Runtime version | `node -v`, `python --version`, `go version`, `java -version` |
| Framework version | `Read package.json:N`, `Read pom.xml:N`, `Read pyproject.toml:N` |
| Config format | `Glob '**/application.*'`, `Read tsconfig.json` |
| Dependency installed | `pnpm list <pkg>`, `cat requirements.txt`, `go.mod` |
| Feature available | `Bash` รันคำสั่ง paste output |
| File exists/path | `Glob`/`ls` first ก่อน assume path |
| Convention/pattern | Read CLAUDE.md / existing similar file ใน project |
| DB/service version | `psql -c 'SELECT version()'`, `redis-cli INFO server` |

### ❌ vs ✅ Pattern

❌ "Spring Boot รองรับ JPA filter ครับ" (เดาจาก real-world)
✅ "[Read pom.xml:25] spring-boot 3.2.1 + spring-data-jpa 3.2.1; [Read SecurityConfig.java:42] custom filter chain มีอยู่ — รองรับ"

❌ "Node 22 รองรับ fetch native ครับ"
✅ "[node -v] v16.20.0 — fetch ไม่รองรับ ต้องใช้ node-fetch หรือ axios"

❌ "PG รองรับ JSONB"
✅ "[psql -c 'SELECT version()'] PG 9.3.25 — JSONB ไม่รองรับ (มาเริ่ม 9.4) ต้อง upgrade หรือใช้ JSON"

### Format
ทุก factual claim เกี่ยว project นี้ cite ฟอร์ม `[<file>:<line>]` หรือ `[output: <command>]`

> Anti-puppet (ถัดไป) บังคับ — ใช้คำต้องห้ามโดยไม่ cite = treated as guess = block

---

## 🎨 UX Evidence Protocol (🔴 v2.8.1 — extension of Project Evidence, สำหรับ UX/UI/a11y claim)

UX claim ต้อง cite **tool output** (path/URL) — เหมือน Domain claim ต้อง cite version+clause

### Required citation format
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

### Format: `[<tool>: <path/URL>] <metric>`

### ถ้า cite ไม่ได้ — บังคับ explicit mark
"⚠️ **Visual estimate** (no tool run, agent inference) — must run `make ui-test` / `axe-cli` / Chromatic ก่อน claim PASS"

### Apply ทุกครั้งที่ UX agent claim:
- Visual diff / design adherence (Chromatic / Percy / pixel diff)
- a11y compliance (axe report / Pa11y / Lighthouse / manual screen reader)
- Contrast ratio (Stark / WebAIM contrast checker output)
- Performance (Lighthouse perf / Web Vitals)
- Screenshot evidence (file path mandatory, "looks ok" forbidden)
- Component state coverage (state inventory ticked from real render)

---

## 📝 REVIEW Report Format (🔴 v2.8.2 — bd-native primary, markdown fallback)

ทุก review output (Phase 3a Uma POST + Phase 3b Chris/Quinn + Phase 4 Triage + `/review` standalone) ใช้ **structure เดียวกัน** เพื่อ consistent + audit-ready

### Storage Rule (ห้ามซ้ำซ้อน)

| Project state | Where to save | Why |
|---------------|---------------|-----|
| **bd active** (`.beads/` มี หรือ `bd ready` returns) | `bd update <id> --notes "..."` **ONLY** | bd = single source of truth; ห้ามเขียน markdown ซ้ำ |
| **No bd** (project ยังไม่ adopt bd) | `outputs/REVIEW-<feature>.md` | audit trail file (fallback) |
| **bd close (per-bd reflect)** | bd notes (v3.3: per-bd `bd remember <lesson>` post-close) | per-bd reflect — no sprint retro since v3.3 |

> Default = bd-native. Markdown = fallback เฉพาะตอนไม่มี bd. ห้ามเขียนทั้งคู่ (waste token + drift risk)

### Mandatory Template (apply ทั้ง bd notes และ markdown fallback)

```
[<Agent>|state:<phase>|bd:<id>|iter:<N>] <verdict PASS/FAIL>

## Summary
- Scope: <files/components reviewed>
- Iter: <N>/3
- Verdict: PASS | FAIL | BLOCKED

## Findings (เรียง severity)
### 🔴 Critical (block merge)
1. [<file>:<line>] <issue> — <why> — fix: <before/after compact>
   - Evidence: <tool output path / paste>
### 🟠 High (fix before merge)
...
### 🟡 Medium (track P2-P3)
...
### 🔵 Low (nitpick, optional)
...

## Coverage / Test (Chris/Quinn เท่านั้น)
- Unit: <coverage %> | Mutation kill: <%>
- Integration: <pass/fail counts>
- E2E: <pass/fail> | Critical path: <covered/total>
- Contract: <Pact/Schemathesis status>
- a11y axe: critical=N, serious=N
- Load: p95=<ms>, error=<%>

## UX Verdict (Uma เท่านั้น)
- Visual diff: <%> [Chromatic URL / path]
- Token usage: <pass/fail> [Bash rg output]
- a11y manual: keyboard/SR/contrast verdict
- Component states: <N/8>
- AC bullet (per AC): ✅/❌ + evidence path

## Loop Routing Recommendation (Phase 4 input)
- Critical/Major issue type: code / UI / spec
- Recommend next phase: 2 / 1b / 1a / close
- Discovered (P4 carry): <bd-create candidates>
```

### Compact bd notes (≤ 500 chars — ลีน)
ถ้า findings เยอะ ใส่ **summary + count + link** ใน bd notes; full evidence (axe report json, Playwright trace, screenshot) ที่ **path** (Aaron tool scaffold) → bd note refs path เท่านั้น

```bash
bd update <id> --notes "Phase 3b: Chris finding=2🔴+3🟠; Quinn finding=0🔴+1🟠. Loop=Phase2 (code fix). Evidence: tests/a11y/*.json, playwright-report/. Iter 1/3."
```

### Markdown fallback (no bd) — `outputs/REVIEW-<feature>.md`
Full template ที่ structured ข้างบน. Use เฉพาะ no-bd project (legacy / quick audit) — ห้ามใช้คู่กับ bd

---

## 📚 Domain Evidence Protocol (🔴 v2.6 — extension of Project Evidence)

Domain claim (regulation/standard/protocol/spec) ต้อง cite **เหมือน project fact**

### Required citation format
```
✅ "PCI-DSS v4.0 Req 3.5.1 (effective Mar 2024) — store PAN encrypted at rest"
✅ "BOT notice 12/2566 ข้อ 4 — KYC ระดับ enhanced สำหรับ PEP"
✅ "IFRS 17 para 32-39 — General Measurement Model"
✅ "FIX 4.4 Tag 35=D — NewOrderSingle"
✅ "ISO 8583 1987 Field 2 — Primary Account Number"
❌ "ตาม PCI-DSS ต้อง encrypt PAN" (no version, no clause)
❌ "BOT requirement บอกว่า..." (no notice number)
❌ "IFRS 17 ใช้ measurement model นี้" (no paragraph)
```

### Format: `<Standard Name> <Version> <Clause/Section> [<Date>] — <Claim>`

### ถ้า cite ไม่ได้ — บังคับ explicit mark
"⚠️ **General guidance from training memory** (cutoff May 2025, not source-verified)
 — must validate กับ official [PCI-DSS / BOT / IFRS / FIX] document version ปัจจุบันก่อน implement"

### Apply ทุกครั้งที่ domain agent claim:
- Regulation (BOT, SEC, OIC, FDA, GDPR, PDPA)
- Standard (PCI-DSS, ISO, IFRS, IAS, OWASP, NIST)
- Protocol (FIX, ISO 8583/20022, SWIFT MT, EDI)
- Industry spec (Basel, Solvency, COBIT)
- Tax / accounting rule (specific revenue code section)

---

## 🔐 Input Trust Levels (🔴 v2.5 — FS-inspired)
