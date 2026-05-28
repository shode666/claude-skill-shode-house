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

## Part 2: Quality Gates (🔴 11 gates — รัน local + pre-commit + CI)

> **เปลี่ยน v3.1.1**: เพิ่ม Gate 0 Architecture self-check (SOLID/cohesion/readable) + เพิ่ม Gate 9 Security Lint. แตก Format เป็น Format / Imports / Remove-Unused เพราะ 3 หมวดใช้ tool ต่างกัน

| # | Gate | Read/Write | ตรวจอะไร | บล็อก hand-off ถ้า fail |
|---|---|---|---|---|
| 0 | **Architecture self-check** | Read (judgment) | SOLID + cohesion + human-readable | 🟠 (Dave judge; Chris verify) |
| 1 | **Format** | Write (rewrite style) | indent/space/quote/line-length | 🔴 |
| 2 | **Organize Imports** | Write (sort+group) | stdlib/3rd-party/local + alpha sort | 🔴 |
| 3 | **Remove Unused** | Write (delete) | unused import/var/function/parameter | 🔴 |
| 4 | **Lint** | Read (diagnose) | code smell + rule violation | 🔴 |
| 5 | **Type Check** | Read (diagnose types) | `--strict`, no `Any`/`any` escape | 🔴 |
| 6 | **Complexity** | Read (measure) | cyclomatic ≤ 10, file ≤ 500, fn ≤ 50 | 🔴 |
| 7 | **Naming** | Read (convention check) | noun/verb/bool/const pattern | 🟠 |
| 8 | **Test** | Run | coverage ≥ 80%, no skipped test | 🔴 |
| 9 | **Security Lint** | Read (SAST) | injection/secret/insecure dep | 🔴 |
| 10 | **Doc** | Read (existence) | docstring on public API + "why" comment | 🟠 |

### Gate 0: Architecture self-check (🔴 v3.1.1 added — Dave's judgment ก่อน hand-off)

> Tool ตรวจ Gate 1-10 ได้ครบ แต่ **SOLID/cohesion/readable ต้องคนตัดสิน**. Dave self-check ก่อน hand-off ลด round-trip กับ Chris

**SOLID (5 ข้อ — ตอบ "yes" ทุกข้อก่อน hand-off)**:
- [ ] **SRP** — class/function ทำสิ่งเดียว. "และ" ใน description = แตก
- [ ] **OCP** — extend ได้ผ่าน interface/composition โดยไม่ต้องแก้ class เดิม
- [ ] **LSP** — subclass แทน parent ได้ทุก context (ไม่ throw, ไม่ break invariant)
- [ ] **ISP** — interface เล็ก. ห้าม "fat interface" ที่ implementor ต้อง stub method ที่ไม่ใช้
- [ ] **DIP** — depend on abstraction (interface/protocol) ไม่ใช่ concrete class. business logic ห้าม import framework โดยตรง

**Cohesion + Coupling**:
- [ ] **High cohesion** — code ในไฟล์เดียวกันแก้ปัญหาเดียว. ถ้า "และ" ปะปน → แตก module
- [ ] **Low coupling** — module A ไม่ควรรู้ internal ของ module B. ผ่าน interface/event/DTO
- [ ] **Stable dependency** — depend ไปทาง stable (lower layer). ห้าม domain → infra direct

**Human readability (ก่อน push อ่าน diff ตัวเอง 1 รอบ)**:
- [ ] **Intent revealing** — ชื่อ + structure บอกเจตนาได้โดยไม่ต้องอ่าน implementation
- [ ] **Linear flow** — อ่าน top-to-bottom เข้าใจได้. ห้ามกระโดดข้าม helper > 3 hop
- [ ] **Comment "why"** — code อ่านได้แล้ว; comment เฉพาะตอน trade-off / business rule / quirk
- [ ] **Symmetry** — pattern ซ้ำในไฟล์ใช้ shape เดียวกัน (อ่าน 1 รอบเข้าใจ 10)
- [ ] **Abstraction level** — function เดียวอย่าผสม high-level + low-level (e.g., business logic + bit twiddling)

**Self-check format ตอน hand-off**:
```
Dave ▸ Chris : impl bd-42 (dev-gate passed 1-10)
- Gate 0 self-check:
  - SOLID: SRP ✓ OCP ✓ LSP ✓ ISP ✓ DIP ✓
  - Cohesion: high (1 module = 1 concern)
  - Readable: diff อ่านแล้ว linear; no surprise
- Trade-off documented: <link to comment line:N> (if any)
```

> ถ้า self-check fail → refactor ก่อน hand-off ห้าม "Chris จะ review ให้". Chris จะ reject + bd revision รอบใหม่

### Per-language tool matrix (🔴 บังคับ use ตาม stack)

| Stack | 1 Format | 2 Imports | 3 Unused | 4 Lint | 5 Type | 6 Complexity | 9 Security |
|---|---|---|---|---|---|---|---|
| **Python** | `ruff format` / black | `ruff --fix I` / isort | `ruff --fix F401,F841` | `ruff E,F,B,N,UP,S,A,C90,SIM,RET` | `mypy --strict` | `radon cc -nb` | `bandit` / semgrep |
| **TypeScript/JS** | `biome format` / prettier | `biome check --apply` / `eslint-plugin-import/order` | `eslint --fix no-unused-vars,no-unused-imports` / ts-unused-exports | `biome check` / `eslint @typescript-eslint/strict` | `tsc --strict --noUncheckedIndexedAccess` | `eslint complexity` | `npm audit` / semgrep |
| **Go** | `gofmt` / `goimports` | `goimports` (built-in) | `golangci-lint unused` | `golangci-lint` (`govet,staticcheck,ineffassign,unused,gosec`) | (compile = check) | `gocyclo -over 10` | `gosec` (in golangci) |
| **Java** | `google-java-format` / spotless | spotless (importOrder) | `error-prone UnusedVariable` | spotbugs + checkstyle | `@Nullable`/`@NonNull` strict | `pmd CyclomaticComplexity` | spotbugs (FindSecBugs) |
| **Kotlin** | `ktfmt` / ktlint | ktlint (import-ordering) | `detekt UnusedImports` | `detekt` | (compile + `-Werror`) | detekt complexity rules | detekt (`detekt-formatting`) |
| **Rust** | `cargo fmt` (rustfmt) | rustfmt (built-in) | `cargo +nightly udeps` | `cargo clippy -- -D warnings` | (compile = check) | clippy `cognitive_complexity` | `cargo audit` |
| **Vue/Nuxt** | prettier + biome | biome | eslint-plugin-vue + ts-unused-exports | eslint-plugin-vue + biome | tsc + `vue-tsc` | eslint complexity | npm audit |
| **PHP** | php-cs-fixer / pint | php-cs-fixer (ordered_imports) | rector dead-code | phpstan / psalm | phpstan strict | phpmd | `composer audit` |

> **Rule**: ใช้ all-in-one tool (Ruff / Biome / golangci-lint) ดีกว่า stitch หลาย tool — boundary error น้อย, config เดียว

### Gate 1: Format
- Auto-format on save (IDE) + pre-commit hook + CI gate (3 จุด)
- **ห้าม**: manual format / "ไม่ตรง project standard but readable"

### Gate 2: Organize Imports (🔴 v3.1 split out)
- Sort + group: stdlib → 3rd-party → local
- Alpha-sort within group
- ห้าม wildcard import (`from x import *` / `import *`)
- ห้าม relative `..` import เกิน 1 level

### Gate 3: Remove Unused (🔴 v3.1 split out)
- Unused **import** → ลบ (F401 / no-unused-vars)
- Unused **local variable** → ลบ (F841)
- Unused **function parameter** → ลบ หรือ prefix `_` ถ้าจำเป็นต้องเก็บ signature
- Unused **function/class export** → ลบหรือ mark internal (ts-unused-exports / vulture)
- ห้าม `# noqa` / `// eslint-disable` โดยไม่ comment "why" + bd track

### Gate 4: Lint (strict — diagnose)
- ดู per-language matrix; เปิด strict rule set ทั้งหมด ไม่ใช่ default ที่อ่อน
- Lint warning = bd issue (track หรือ fix); ห้าม ignore

### Gate 5: Type Check (🔴 strict)
- Py: `mypy --strict` — ห้าม `Any` เลี่ยงได้
- TS: `tsc --strict --noUncheckedIndexedAccess` — ห้าม `any`, ใช้ `unknown` + narrow
- Java: explicit null annotation (`@Nullable`/`@NonNull`)
- ห้าม `# type: ignore` / `// @ts-ignore` / `@SuppressWarnings` โดยไม่ ticket

### Gate 6: Complexity
- Cyclomatic ≤ 10 / function
- Cognitive ≤ 15 / function
- Function ≤ 50 บรรทัด (≤ 30 ดีกว่า)
- File ≤ 500 บรรทัด
- Nesting ≤ 3 (early return / guard clause แทน)

### Gate 7: Naming
- Variable: `noun` ที่บอก what (ไม่ใช่ `data`/`info`/`temp`)
- Function: `verb_noun` (`calculate_total`)
- Boolean: `is_*`/`has_*`/`should_*`/`can_*`
- Constant: `UPPER_SNAKE`
- ห้าม abbreviation ที่ไม่เป็นมาตรฐาน
- ห้าม magic number/string → constant + comment "why"

### Gate 8: Test
- Unit coverage ≥ 80% business logic (Chris's responsibility; Dave smoke ก่อน hand-off)
- AAA pattern + G-W-T naming
- Edge case + error path
- ห้าม skipped/disabled test ไม่มี bd track

### Gate 9: Security Lint (🔴 v3.1 added)
- SAST per language (ดู matrix Gate 9 column)
- Secret scan (gitleaks / `git-secrets`) — block commit ที่มี API key / password / cert
- Dependency audit (`npm audit` / `pip-audit` / `cargo audit`) — block critical/high vulns
- **ห้าม**: ignore security warning โดยไม่ Sentinel approve

### Gate 10: Doc
- Docstring/JSDoc สำหรับ public API (signature + example + edge case)
- Inline comment เฉพาะ "why" ไม่ใช่ "what"
- README update ถ้า API change

---

## Pre-commit hook (🔴 v3.1 — บังคับทุก repo)

ติดตั้ง `pre-commit` ([pre-commit.com](https://pre-commit.com)) + `.pre-commit-config.yaml`:

```yaml
# .pre-commit-config.yaml — Python project example
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff-format         # Gate 1
      - id: ruff                # Gate 2+3+4 (--fix organize+unused+lint)
        args: [--fix, --exit-non-zero-on-fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy                # Gate 5
        args: [--strict]
  - repo: https://github.com/pycqa/bandit
    rev: 1.7.9
    hooks:
      - id: bandit              # Gate 9
        args: [-c, pyproject.toml]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks            # Gate 9 secret scan
```

```yaml
# .pre-commit-config.yaml — TS/JS project example
repos:
  - repo: https://github.com/biomejs/pre-commit
    rev: v0.5.0
    hooks:
      - id: biome-check         # Gate 1+2+3+4 (format + imports + unused + lint)
        args: [--apply]
  - repo: local
    hooks:
      - id: tsc
        name: TypeScript strict
        entry: npx tsc --noEmit --strict
        language: system
        types: [ts]
      - id: ts-unused-exports
        name: Unused exports
        entry: npx ts-unused-exports tsconfig.json
        language: system
        pass_filenames: false
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

**Setup steps**:
```bash
pip install pre-commit              # หรือ brew install pre-commit
pre-commit install                  # ติด git hook
pre-commit run --all-files          # รัน lint ทั้ง repo ครั้งแรก
```

ทุก `git commit` จะถูก block ถ้า gate ใด fail. ห้าม `--no-verify` (bypass) ใน production code

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
| Unused import / variable | dead code | ลบ ห้าม keep "for later" |
| Wildcard import (`from x import *`) | namespace pollution | explicit import |

---

## Pre-Push Checklist (🔴 v3.1.1 — all 11 gates)

```bash
# Gate 0 — Architecture self-check (Dave answers each checkbox above ก่อนรัน mechanical gates)

make fmt          # Gate 1 — auto-format
make imports      # Gate 2 — organize imports
make clean-unused # Gate 3 — remove unused (CI auto-fail if anything found)
make lint         # Gate 4 — strict lint
make typecheck    # Gate 5 — strict types (no Any/any)
make complexity   # Gate 6 — cyclomatic + size limits
make test         # Gate 8 — unit + coverage
make security     # Gate 9 — SAST + secret scan + dep audit
make doc-check    # Gate 10 — public API docstring present
```

หรือเรียก `make pre-push` ที่รวมทุก mechanical gate ในคำสั่งเดียว:

```makefile
# Makefile snippet
pre-push: fmt imports clean-unused lint typecheck complexity test security doc-check
	@echo "✅ Gates 1-10 pass — Dave: confirm Gate 0 self-check before push"
```

ทุก check ผ่าน → ค่อย push. CI ก็ต้องรันชุดเดียวกัน (pre-commit + GitHub Actions / GitLab CI / CircleCI)

> **Gate 0 ไม่อยู่ใน Makefile** — ตั้งใจให้ Dave หยุดคิด 30 วินาทีก่อน push, ไม่ใช่ auto-pass. มันคือ judgment ไม่ใช่ tool

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
