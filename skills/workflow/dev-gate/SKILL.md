---
name: dev-gate
description: |
  [WHAT] บังคับ TDD cycle (red → green → refactor) + quality gate (format/lint/type/complexity/naming/test/doc) ก่อน hand-off production code.
  [AUDIENCE] Dave (implement) + Chris (verify) — sole owners.
  [WHEN] Phase 2 implement / refactor / bug-fix; ก่อน push หรือ open PR; หลัง spec ครบจาก Phase 1.
  [TRIGGER] /shode-house:dev-gate, "TDD", "test first", "red-green-refactor", "clean code", "เน้น quality", "production code", "refactor", "เริ่มเขียน code".
---

# Dev Gate (TDD + Quality Gates) — v3.0 merged

> **Owner**: Dave (implement) + Chris (verify). เปิด skill นี้ตอนเขียน production code
> Merged from v2 skills: `tdd` + `code-quality` — ลด context, รวม dev-time discipline

## When NOT to use

- **Spike / prototype / throwaway script** — TDD overhead ไม่คุ้ม. ใช้ `diagnose` แทนถ้าเป็น exploration
- **Generated code** (codegen, OpenAPI client, ORM model) — gen tool ดูแล quality, dev-gate ไม่ฟิต
- **Pure config change** (yaml/json/env tweak) — review + smoke test พอ ไม่ต้อง TDD
- **Production hot-fix P0/P1** — ใช้ `incident` skill ก่อน; dev-gate ตามมาตอน follow-up fix

## Required inputs — refuse without

ก่อน hand-off Phase 2 → 3, confirm ทุก checklist. ถ้าขาด **list สิ่งที่ขาด แล้วหยุด** — ห้าม claim "done":

- [ ] **Spec ครบ** จาก Phase 1 (BRD + AC G-W-T + ADR ที่กระทบ)
- [ ] **Test runs locally** (red phase): ทุก new behavior มี failing test ก่อน implement
- [ ] **Test pass** (green): ทุก unit/integration test green; ไม่ skip/disable
- [ ] **Quality gate ผ่านครบ 7**: format ✓ · lint ✓ · type ✓ · complexity ≤10 ✓ · naming ✓ · coverage ≥ threshold ✓ · doc/comment "why" ✓
- [ ] **Evidence paste**: command + output ใน hand-off (ห้าม "should work")

## หลักการ (🔴)

1. **No production code without failing test first** (TDD core)
2. **Quality at dev time, not after** — fix early ถูกกว่า 100x

---

## Part 1: TDD Cycle (red → green → refactor)

### 1. 🔴 Red — เขียน test ที่ fail ก่อน
- Test เล็กที่สุด — 1 behavior
- Naming: `should_<behavior>_when_<condition>` หรือ G-W-T
- Run → ต้อง fail (assertion fail; compile error ไม่นับ)

```python
def test_calculate_total_with_vat_includes_7_percent():
    cart = Cart(items=[Item(price=Decimal("100"))])
    total = cart.total_with_vat(rate=Decimal("0.07"))
    assert total == Decimal("107.00")
```

### 2. 🟢 Green — เขียน code น้อยที่สุดที่ pass
- Simplest thing that works (YAGNI)
- ห้าม anticipate future requirement
- ห้าม refactor ตอนนี้

### 3. 🔵 Refactor — clean up (test ยัง pass)
- Remove duplication, improve naming, extract function
- ห้ามเพิ่ม behavior ใหม่ในรอบ refactor

### TDD scope
✅ **เหมาะ**: business logic, calc, validation, state machine, parser, algorithm, bug-fix regression
❌ **ไม่เหมาะ**: UI prototype, spike, pure framework integration

---

## Part 2: Quality Gates (รัน local ก่อน push)

### Gate 1: Format
- Auto-format on save: ruff/black (Py), prettier (JS/TS), gofmt (Go), ktfmt (Kt)
- Pre-commit hook บังคับ

### Gate 2: Lint (strict, ไม่ใช่ default ที่อ่อน)
- Py: `ruff` rules `E,F,B,I,N,UP,S,A,C90,SIM,RET`
- TS: ESLint + `@typescript-eslint/strict`
- Go: `golangci-lint` (`govet,staticcheck,ineffassign,unused,gosec`)
- Java/Kt: detekt + spotbugs

### Gate 3: Type Check (🔴 strict)
- Py: `mypy --strict` — ห้าม `Any` เลี่ยงได้
- TS: `tsc --strict --noUncheckedIndexedAccess` — ห้าม `any`, ใช้ `unknown` + narrow
- Java: explicit null annotation (`@Nullable`/`@NonNull`)

### Gate 4: Complexity
- Cyclomatic ≤ 10 / function
- Cognitive ≤ 15 / function
- Function ≤ 50 บรรทัด (≤ 30 ดีกว่า)
- File ≤ 500 บรรทัด

### Gate 5: Naming
- Variable: `noun` ที่บอก what (ไม่ใช่ `data`/`info`/`temp`)
- Function: `verb_noun` (`calculate_total`)
- Boolean: `is_*`/`has_*`/`should_*`/`can_*`
- Constant: `UPPER_SNAKE`
- ห้าม abbreviation ที่ไม่เป็นมาตรฐาน
- ห้าม magic number/string → constant + comment "why"

### Gate 6: Test
- Unit coverage ≥ 80% business logic (Chris's responsibility; Dave smoke ก่อน hand-off)
- AAA pattern + G-W-T naming
- Edge case + error path

### Gate 7: Doc
- Docstring/JSDoc สำหรับ public API (signature + example + edge case)
- Inline comment เฉพาะ "why" ไม่ใช่ "what"

---

## Quality Smells (🚫 reject)

| Smell | Why bad | Fix |
|-------|---------|-----|
| God class (> 500 lines) | hard to test/change | extract module |
| Long parameter list (> 4) | hard to read | parameter object |
| Duplicate code | DRY violation | extract function |
| Deep nesting (> 3) | cognitive load | early return / guard clause |
| Magic number/string | meaning unclear | named constant |
| Comment explaining hack | code smell | refactor + remove comment |
| `try` ... `pass` | swallow error | log + re-raise / handle |

---

## Pre-Push Checklist

```bash
make fmt        # auto-format
make lint       # static analysis
make typecheck  # strict types
make test       # unit + coverage gate
make complexity # optional
```

ทุก check ผ่าน → ค่อย push

---

## Hand-off

```
Dave  ▸ Chris   : impl + smoke (dev-gate passed)
Chris ▸ Quinn   : 7-dim + unit ≥ 80% + mutation ≥ 70%
```

---

## ห้าม

- ห้ามเขียน code ก่อน test (TDD core)
- ห้าม commit test ที่ยัง fail (ใช้ skip/xfail + bd issue)
- ห้าม refactor พร้อม add behavior — แยก commit
- ห้าม mock business logic — mock เฉพาะ external (DB/API/clock)
- ห้ามใช้ `time.sleep` ใน test → fake time/freeze
- ห้าม disable lint rule โดยไม่ comment + bd track
- ห้าม `// @ts-ignore` / `# type: ignore` โดยไม่ ticket
- ห้าม commit `console.log` / `print` debug
- ห้ามใช้ `any` (TS) / `Any` (Py) เป็นทางลัด
- ห้าม PR ที่ลด coverage (CI ตั้ง gate, ratchet)
- ห้าม merge code ที่ build แดง

## Skill composition (where to go next)

| Situation | Next skill | Reason |
|---|---|---|
| Test pass แต่ยังไม่มี CI gate | → `automate-test` | Pyramid ratio + CI threshold + contract test (dev-gate = per-task; automate-test = project-wide) |
| Code touches frontend | → `ui-test` | E2E + visual + a11y automation (dev-gate ไม่ครอบ visual) |
| Frontend public-facing (perf/SEO/security) | → `web-q` | CWV + Lighthouse + security headers budget |
| Touch security control (auth/crypto/PII) | → `secure` | Sentinel threat model + abuse case (dev-gate ไม่ classify threat) |
| Hand-off Phase 2 → 3b review | → `review-checklist` skill | Chris 7-dim + Quinn integration matrix (used by /implement Phase 3b + /review)
