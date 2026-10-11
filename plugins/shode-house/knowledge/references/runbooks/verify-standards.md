---
name: verify-standards
description: Reference (lazy-load) for `verify` (standards axis) - report output, triage routes, test-quality techniques, review dimensions 3-6 and judgment. Load before the standards-axis review starts (dimensions 3-6 are applied during the review).
---

```lazy-load-contract
LOAD: references/runbooks/verify-standards.md
WHEN: phase=3b AND standards_axis_review
OWNER: verify
REQUIRED-BEFORE: standards_axis_review_start
```

# `verify` (standards axis) - method

> Lazy reference for `verify` (standards axis): method moved out of the agent body (v4 W5b). It supplies method, never authority; the verdict rules, axis split and safety lines stay in the agent body.

## Output — confirmed evidence home, Markdown fallback

- Use `skills/discipline/review-checklist/report-format.md`; store one canonical report in the project's confirmed evidence home and link it from the task record. Do not create a second tracker or duplicate report. Each finding = a `review-finding` task in the confirmed tracker.
- Keep full evidence at accessible paths with revisions; return decisive findings and links. Unavailable remote writes remain pending sync, not claimed posted.
- Report ภาษาไทย + code: สรุป (จุดดี + ผ่าน/แก้/block) · findings เรียง severity · test/edge case ที่ขาด · action items (block/track)
- Triage route loop (blocking Critical/High):
  - Code/perf/security implementation finding → Phase 2 (`build` fix)
  - Spec/AC issue discovered → Phase 1a (`plan` (requirements mode)+`plan` (architecture mode) revise)

## Routing rows

| งาน | ใคร |
|-----|-----|
| Architecture issue ใหญ่ | → **`plan` (architecture mode)** |
| Refactor implementation | → **`build`** (`verify` (standards axis) ระบุ smell + concrete fix) |

## Test-quality techniques (select by risk)

1. **Mutation testing** (mutmut/Stryker; example target ≥ 70%) — useful for critical business invariants; mutate code random → test ต้อง fail (ถ้าไม่ fail = test ไม่จับ bug); use adopted targets and inspect surviving meaningful mutants
2. **Property-based tests** (Hypothesis / fast-check / QuickCheck-style) for invariants with a meaningful input space — generate random valid input → edge case auto
3. **Coverage** (example ≥ 80% business logic): inspect missed error/boundary paths, not the number alone
4. **Test mix**: justify unit/integration/E2E coverage by risk and feedback cost, not a fixed 70/20/10 quota

## Dimensions 3-6

### 3. SOLID & Design
Apply SRP/OCP/LSP/ISP/DIP proportionally. Read `skills/discipline/shode-house-workflow/engineering-loop.md` before design review for application-layer boundaries, overengineering checks and required safeguards. Style alone is not a blocker.

### 4. Performance
N+1, missing index, full scan; O(n²) ที่ควร O(n log n); memory leak, unbounded growth; blocking I/O ใน async; missing pagination/rate limit

### 5. Maintainability
File >500/function >50/cyclomatic >10/cognitive >15; magic number/string; duplicate (DRY); naming; missing docstring; **Code smells** (Fowler): long parameter list, feature envy, data clump, shotgun surgery, primitive obsession

### 6. Testing (Unit — `verify` (standards axis)'s job)
Check adopted coverage targets, edge cases and error paths, clear behavior naming,
AAA structure and isolation (no shared state). A percentage alone is not quality. Techniques → § Test-quality techniques above.

**Test doubles**: Dummy / Stub / Spy / Mock / Fake — pick by intent
- Mock boundary (external), not internals
- Frameworks: pytest / Vitest+Jest / testing+testify / JUnit+Mockito

## Judgment

- **Process**: scan structure → read ทุก file ที่เปลี่ยน → cross-reference caller/dependency/test → run static check (lint/type/SAST) → categorize by severity → concrete fix (file:line + before/after)
- **Focus substance**: bug > security > perf > design > maintainability > style
- **Reviewer mindset**: "ฉันจะ maintain code นี้ในอีก 6 เดือน"
- **Praise + critique** — note สิ่งดีด้วย
- **Suggest, don't dictate** — propose alternative (ยกเว้น security)
- **Pair review for complex** — 2 reviewer สำหรับ critical/security
- **Small PR > big** — < 400 บรรทัด
- `Grep` (symbol/pattern) > `Read` ทั้งไฟล์; `Read` with `offset`/`limit` เฉพาะช่วงที่ grep เจอ
- ห้าม nitpick อย่างเดียว → Critical/High ก่อน
- ห้าม "ควรปรับ" โดยไม่บอกยังไง → concrete fix


## Mode rules carried over from the former standards axis

Start from the assigned canonical task, pinned diff and acceptance, not a new backlog search.

### 🔴 Independent evidence — apply the preloaded review-checklist gates
"tested" is not evidence. Remain an independent gatekeeper. UI evidence follows

### 🔎 Phase 3b — independent code review; `design` gate for UI changes
not applicable with diff evidence. `verify` (standards axis) and `verify` (runtime axis) remain independent; parallel
| `verify` (standards axis) scope (Phase 3b) | Hand-off (split scope) |
| **Visual diff / design adherence / baseline approval** | → **`design` Phase 3a** (`verify` (standards axis) ไม่ตรวจ — passed gate ก่อนแล้ว) |
| **Integration / E2E / contract / load / a11y axe automation / Pen** | → **`verify` (runtime axis) Phase 3b** (`verify` (standards axis) ไม่ตรวจ); pen test → **`secure`** |
| Domain rule wrong | → **Domain Expert** |

### 2. Security (OWASP Top 10 — surface review only)
- Security surface (OWASP Top 10): injection (SQL/NoSQL/cmd/LDAP/XSS), SSRF, authN/authZ (IDOR, JWT), crypto (weak algo, hardcoded key, IV reuse), secrets, input validation, CVE deps, money/PII (float, encryption, log leak).
> 🔴 **Handoff**: deep security (STRIDE/LINDDUN, CSP/Trusted Types/SRI verify, SAST/DAST orchestration, pen test, secrets management, headers grading) → **`secure` Phase 3b parallel**. `verify` (standards axis) ดู obvious code-level vuln + flag suspicious → escalate `secure`

## Prohibitions (both axes)

- Challenge assumptions and error paths. A high PASS rate alone does not prove bias; do not invent findings or inflate severity to meet a failure quota.
- Grade subtle issues by demonstrated impact, not change size or appearance.
- ห้ามผ่านโดยไม่อ่านจริง; ห้ามรับรอง code ที่ไม่มี test สำหรับ business logic หลัก
- Security severity follows demonstrated impact and adopted criteria; Critical/High blocks, unrelated repairs need separate authority
- ห้ามรัน destructive pen test บน prod โดยไม่ได้รับอนุญาต (R0); เจอ secret leak → report promptly to the router without exposing the value

Start from the router's assigned scope, the pinned diff and the canonical task, not a new backlog search.
