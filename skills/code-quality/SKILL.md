---
name: code-quality
description: |
  ใช้เมื่อ user สั่ง implement feature, refactor, "เน้น quality", "clean code", "ทำให้สะอาด", "code review", หรือเริ่มเขียน production code — บังคับ quality gate ระดับ dev (linter/type/complexity/naming/test) ก่อน hand-off
---

# Code Quality (dev-time discipline)

> **Owner**: Dave (implement) + Chris (verify). เปิด skill นี้ตอนเขียน production code

## หลักการ (🔴)

**Quality at dev time, not after** — fix early ถูกกว่า 100x; broken window = bad culture

## Quality Gates (รัน local ก่อน push)

### 1. Format
- **Auto-format on save**: ruff/black (Py), prettier (JS/TS), gofmt (Go), ktfmt (Kt)
- ห้าม commit unformatted code
- Pre-commit hook บังคับ

### 2. Lint
- **Strict config** — ไม่ใช่ default ที่อ่อน
- Py: ruff (extend rules `E,F,B,I,N,UP,S,A,C90,SIM,RET`)
- TS: ESLint + `@typescript-eslint/recommended` + `strict`
- Go: golangci-lint (`govet,staticcheck,ineffassign,unused,gosec`)
- Java/Kt: detekt + spotbugs

### 3. Type Check (🔴 strict)
- Py: `mypy --strict` (ห้าม `Any` ถ้าหลีกเลี่ยงได้)
- TS: `tsc --strict --noUncheckedIndexedAccess` (ห้าม `any` หรือใช้ `unknown` + narrow)
- Go: built-in
- Java: explicit null annotation (`@Nullable`/`@NonNull`)

### 4. Complexity
- Cyclomatic ≤ 10 / function (refactor ถ้าเกิน)
- Cognitive ≤ 15 / function
- Function ≤ 50 บรรทัด (≤ 30 ดีกว่า)
- File ≤ 500 บรรทัด
- Tools: radon (Py), eslint-complexity, gocyclo, detekt

### 5. Naming
- Variable: `noun` ที่บอก what (ไม่ใช่ `data`/`info`/`temp`)
- Function: `verb_noun` (`calculate_total`, `fetch_user`)
- Boolean: `is_*`/`has_*`/`should_*`/`can_*`
- Constant: `UPPER_SNAKE`
- ห้าม abbreviation ที่ไม่เป็นมาตรฐาน (`usr` ❌, `user` ✅)
- ห้าม magic number/string → constant + comment "why"

### 6. Test
- Unit test coverage ≥ 80% business logic (Chris's responsibility — Dave smoke test ก่อน hand-off)
- AAA pattern + G-W-T naming
- Edge case + error path
- Test รันใน CI = required check

### 7. Doc
- Docstring/JSDoc สำหรับ public API (signature + example + edge case)
- README quickstart + dev setup
- Inline comment เฉพาะ "why" ไม่ใช่ "what"

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

## Pre-Push Checklist

```bash
make fmt        # auto-format
make lint       # static analysis
make typecheck  # type check
make test       # unit test
make complexity # complexity check (optional)
```

ทุก check ต้องผ่าน → ค่อย push (Aaron set CI ให้ block PR ถ้าไม่ผ่าน)

## Hand-off

Dave finish → Chris deep review (7 มิติ) → Quinn integration test

## ห้าม

- ห้าม disable lint rule โดยไม่ comment "why" + bd issue track
- ห้าม `// @ts-ignore` / `# type: ignore` โดยไม่ comment + ticket
- ห้าม commit `console.log` / `print` debug
- ห้ามใช้ `any` (TS) / `Any` (Py) เป็นทางลัด
- ห้าม PR ที่ลด coverage (CI ตั้ง gate)
- ห้าม merge code ที่ build pipeline แดง
