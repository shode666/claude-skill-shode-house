---
name: build-method
description: Reference (lazy-load) for `build` - language references, code quality, implement loop, full process steps and output format. Load before implementing.
---

```lazy-load-contract
LOAD: references/runbooks/build-method.md
WHEN: phase=2 AND implementation_started
OWNER: build
REQUIRED-BEFORE: first_edit
```

# `build` - method

**Contents**

- [Adversarial review stance](#adversarial-review-stance)
- [🟡 Minion-style — parallel ได้](#-minion-style--parallel-ได้)
- [🌐 Languages — Lazy-load (token-saving)](#-languages--lazy-load-token-saving)
- [Self-Routing rows owned by others](#self-routing-rows-owned-by-others)
- [Bug prevention method (v2.2)](#bug-prevention-method-v22)
- [🏛️ Universal Code Quality](#️-universal-code-quality)
- [🔁 Implement Loop (Archon-inspired)](#-implement-loop-archon-inspired)
- [Process (full)](#process-full)
- [Output Format](#output-format)
- [Mode rules carried over from the former implementation](#mode-rules-carried-over-from-the-former-implementation)
- [Hand-off, routing and skills](#hand-off-routing-and-skills)

> Lazy reference for `build`: method moved out of the agent body (v4 W5b). It supplies method, never authority; the gates, safety and ownership rules stay in the agent body.

ยึด `shode-house:shode-house-discipline` skill + **5 Philosophy** (preloaded).

## Adversarial review stance

`verify` (standards axis) + `verify` (runtime axis) ทำงาน **adversarial ต่อ `build`** (pessimistic default; zero-trust). ดังนั้น `build` ต้อง paste evidence ก่อน hand-off (rules in the body § Adversary-Aware Hand-off).

- ห้าม defensive validation ที่ทำให้ valid input space empty (e.g. edit: `input == current`)

## 🟡 Minion-style — parallel ได้

`plan` (architecture)/the router เรียกหลาย `build` พร้อมกันเมื่อ independent (เช่น endpoint ละ `build`):
- `plan` (architecture mode) เสนอการแตกงานให้ the router dispatch (`shode-house:build` ไม่ self-spawn)
- Parallelize independent scoped work only when its benefit exceeds coordination/context cost; measure usage instead of assuming a fixed multiplier.

## 🌐 Languages — Lazy-load (token-saving)

อ่าน **เฉพาะภาษาที่ใช้** ก่อน implement:

### Startup
| Lang | Use case | File |
|------|----------|------|
| TypeScript | Web/Backend/Full-stack | `references/languages/typescript.md` |
| Python | AI/Data/Backend | `references/languages/python.md` |
| JavaScript | Frontend/Node legacy | `references/languages/javascript.md` |
| Go | API/Microservice/Infra | `references/languages/go.md` |
| SQL | Database/Analytics | `references/languages/sql.md` |
| Kotlin | Android/JVM Backend | `references/languages/kotlin.md` |
| Swift | iOS native | `references/languages/swift.md` |
| Rust | Perf/Safety/Blockchain | `references/languages/rust.md` |
| PHP | Web/Laravel/WordPress | `references/languages/php.md` |
| Dart | Flutter cross-platform | `references/languages/dart.md` |

### Enterprise
| Lang | Use case | File |
|------|----------|------|
| Java | Banking/Insurance/Enterprise | `references/languages/java.md` |
| C# | Enterprise/Windows/Azure | `references/languages/csharp.md` |
| C++ | Performance/Embedded/Trading | `references/languages/cpp.md` |
| COBOL/PL-SQL/VBA | Mainframe/Oracle/Office | `references/languages/legacy.md` |

### Generic Patterns
- `references/patterns/general.md` — DB/API/Observability/FeatureFlag/AI integration
- `references/modern-stack.md` — 2025+ tech recommendation

## Self-Routing rows owned by others

| งาน | ใคร |
|-----|-----|
| Implement ตาม spec ชัด, refactor, bug fix, integration | `build` |
| Setup/Docker/CI/Deploy | → `operate` (deploy mode) (Phase 5 continuous per bd, or manual batch) |
| Spec กำกวม | → `plan` (requirements mode) clarify (Phase 1a parallel `plan` (architecture mode)) |

## Bug prevention method (v2.2)

2. **Type from OpenAPI** (`plan` (architecture mode) produce, `build` consume)
   - Reuse project contract/type tools; generators are optional
3. **Risky feature → behind feature flag default-off**
   - Test ทั้ง flag-on + flag-off
   - Cleanup ≤ 90 day

## 🏛️ Universal Code Quality

### Naming
- Variable = noun; Function = verb_noun
- Boolean = `is_*`/`has_*`/`should_*`
- Constant = UPPER_SNAKE / convention
- ห้าม non-standard abbreviation, ห้าม magic number

### Function
- Single responsibility; 30 lines / 4 params are signals, not refactoring gates
- Pure when possible, early return / guard clause
- Same level of abstraction

### Error
- Fail fast, context พอ trace, ห้ามกลืน
- Typed error, boundary catch (router), propagate from layer ล่าง

- ห้าม `// @ts-ignore` / `# type: ignore` โดยไม่ ticket

## 🔁 Implement Loop (Archon-inspired)

```
implementation feedback loop:
  implement → smoke test
  if test pass + criteria met → Process 9 (Return)
  if failed → investigate root cause; retry with new evidence or a changed hypothesis
  if unchanged failure repeats → record blocker and return to the router
```
- ระบุ **success criteria** ชัด ตอนเริ่ม (test green, lint clean, type pass)
- Share the harness's three review→fix iterations; no separate debug cap. Return unresolved findings/evidence to the router at the cap
- Report PASS/FAIL/BLOCKED/PARTIAL accurately

## Process (full)

1. **Claim** — the router's assigned task, canonical tracker, existing authority
2. **Context** — อ่าน spec/requirement (artifact link จาก task record)
3. **Identify language + read ref** — `references/languages/<lang>.md` (+ `patterns/general.md` ถ้าต้องการ)
4. **Convention check** — `Glob`+`Grep` existing code
7. **Verify** (Philosophy 2) — lint + type + smoke test (run + show output)
8. **Scope Closed** — post `state:scope-closed` → ปลด file ownership
10. **Hand-off → Phase 3a UI Check (`design` POST gate, sequential 🔴 v2.8)** — ถ้า frontend changed: `design` ตรวจ visual diff + design adherence + a11y manual + own AC verification → PASS unlocks Phase 3b, FAIL loops Phase 2 (`build` fix) หรือ Phase 1b (`design` redesign baseline). Pure backend = skip → ตรง Phase 3b
11. **Phase 3b** — independent `verify` (standards axis); `verify` (runtime axis) per harness tier/boundaries; `design` POST for UI; `operate` (deploy mode) for environment/CI. Retain triggered reviews. Parallel or separate sequential contexts; evidence → the router.

Steps 0, 2.5, 5, 6, 9 and 12 are binding and stay in the agent body. Commit message example (project convention first):
```
feat(payment): add refund endpoint [bd:42]
fix(cart): handle empty coupon code [bd:51]
```

## Output Format

```markdown
## Implementation: [feature]

### Refs Used
### Files Changed — path + reason
### Code
### Verify (Philosophy 2) — commands run + real output
### Decisions + R0/R1/R2 — e.g. R1, rollback via revert + flag
### Hand-off — `verify` (standards axis) / `verify` (runtime axis) / `design`: what to check
```


## Mode rules carried over from the former implementation

### 🔴 Adversary-Aware Hand-off
`verify` (standards axis) and `verify` (runtime axis) review adversarially (zero-trust):
- Source rule: shode-house-discipline § VERIFY BEFORE DONE + Anti-Puppet

### 🟡 Parallel work
- Independent (ห้าม shared file/state); ห้ามชน file → serialize

### 🧭 Self-Routing (does not own → who)
| Business logic ลึก (money/policy/matching) | → Domain Expert validate |
| Integration/E2E acceptance | → `verify` (runtime axis) (Phase 3b parallel) |
| UX approval: visual/design tokens (pre-implement) | → `design` (Phase 1b sequential after 1a) |

### 🔴 Mandatory Bug Prevention (v2.2)
   - Use the project's type checks (examples: TS strict; Python mypy). Do not install a checker without authority; disclose a required check that cannot run.
   - Validate every external input with the existing stack (Zod/Pydantic are examples, not required dependencies). Runtime boundary validation remains required even without a type checker.
   - ห้าม `JSON.parse` raw → wrap with schema validate

### Security Baseline
- Input validation (allow-list > deny-list)
- Output encoding (HTML/SQL/shell context-aware)
- Parameterized query (ห้าม string concat SQL)
- Secret out → env / vault
- Auth check ทุก endpoint
- Audit log sensitive (auth, money, admin)
> ⛔ **ก่อนเข้า loop**: ผ่าน **YAGNI ladder** (dev-gate Step 0) — code ที่ดีที่สุด = code ที่ไม่ต้องเขียน. ตัดได้เฉพาะความซับซ้อนที่ยังไม่ต้องใช้; **ห้ามตัด** validation/data-loss/security/a11y/regulation (carve-out). ทางลัดที่ defer → `shortcut(bd:N):` comment

### Process
2.5. **UI Precondition** — reuse approved `design` design/tokens/state/a11y criteria; Figma optional. Missing necessary decisions → the router/`design`
5. **Scope Contract** — record IN/OUT/Files/Stop/Echo; check ownership/authority (`references/scope-lock.md`). No reapproval of authorized scope
6. **Implement** — type-safe + tested + observable: structured logging + RED metrics (reviewed as `verify` (standards axis) dimension 7) — edit only Files declared in scope
9. **Return** — ส่ง artifact/tests/findings ให้ the router; ไม่ปิด task เอง (the router ปิดหลัง independent review). งานที่พบเพิ่มให้เสนอ linked follow-up
12. **Commit** — only with user/project authority; follow project convention

### ข้อห้าม
- Never guess acceptance; unresolved requirements/design → the router/`plan`
- ห้าม Edit/Write โดยไม่ post Scope Contract ก่อน (v2.4.1 — ดู `references/scope-lock.md`)
- Additional file: amend scope/check ownership before edit. New authority → the router; reuse existing grants
- 🔴 v2.8.1 — ห้าม hand-off Phase 3a (`design` POST) ถ้า frontend changed แต่ไม่ paste screenshot path. `design` ต้องการ "after" image เพื่อ diff baseline; ไม่มี = `design` skip verify → bad UI หลุด

## Hand-off, routing and skills

`verify` reviews adversarially (zero-trust), one fresh spawn per axis:
- **Proactive evidence**: ก่อน hand-off ต้อง paste **tool output จริง** (lint stdout, unit test result, smoke curl response, screenshot path)
- Missing required verification = BLOCKED; demonstrated defect = FAIL; never claim done without evidence
- UI changes: load `shode-house:ui-test`; render/exercise affected screens, save screenshot/interaction evidence. Use available tools; browser MCP optional. Reviewers verify independently
- ห้าม hand-off Phase 3a (`design` POST) ถ้า frontend changed แต่ไม่ paste screenshot path: `design` needs the "after" image to diff the baseline
- ห้าม push back a `verify` finding ด้วย "should be fine" / "no impact" — counter ด้วย **evidence** (new test, profile, additional run) เท่านั้น

| งาน | ใคร |
|-----|-----|
| Architecture decision / approval, requirements, AC | → `plan` ก่อน |
| Business logic ลึก (money/policy/matching) | → `plan` with the domain reference (domain consult) |
| Code acceptance: deep code review + unit test ครอบคลุม | → `verify` standards axis (Phase 3b) |
| Integration/E2E acceptance | → `verify` runtime axis (Phase 3b) |
| Security approval, pen test | → `secure` |
| Visual diff / design adherence / a11y manual post-implement; UX approval pre-implement | → `design` (Phase 3a gate before 3b; Phase 1b after 1a) |

Skills: Read prerequisites once; load when applicable: `shode-house:dev-gate` (TDD/gates; its branch refs `skills/workflow/dev-gate/tdd.md` before the first test of new behaviour, `skills/workflow/dev-gate/quality-gates.md` when a gate fails/is unclear or a module is reshaped), `shode-house:diagnose` (bug; no feedback loop after its methods 1-3 → read `skills/workflow/diagnose/loop-ladder.md`), `shode-house:data-migration` (schema), `shode-house:api-contract` (public interface or cross-team consistency). Cite loaded instructions, not memory.

Before every return (hand-off, "done" claim, postmortem) load `shode-house:shode-house-deliverable` with `Skill`: output contract (`output-contract.md`), Anti-Puppet (`anti-puppet.md`), completion stop. Not preloaded, so a return without this load is not a verified return.
