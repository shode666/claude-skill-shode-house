---
name: developer-method
description: Reference (lazy-load) for developer - language references, code quality, implement loop, full process steps and output format. Load before implementing.
---

```lazy-load-contract
LOAD: references/runbooks/developer-method.md
WHEN: phase=2 AND implementation_started
OWNER: developer
REQUIRED-BEFORE: first_edit
```

# developer - method

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

> Lazy reference for `developer`: method moved out of the agent body (v4 W5b). It supplies method, never authority; the gates, safety and ownership rules stay in the agent body.

ยึด `shode-house:shode-house-discipline` skill + **5 Philosophy** (preloaded).

## Adversarial review stance

code-reviewer + qa-engineer ทำงาน **adversarial ต่อ developer** (pessimistic default; zero-trust). ดังนั้น developer ต้อง paste evidence ก่อน hand-off (rules in the body § Adversary-Aware Hand-off).

- ห้าม defensive validation ที่ทำให้ valid input space empty (e.g. edit: `input == current`)

## 🟡 Minion-style — parallel ได้

solution-architect/the router เรียกหลาย developer พร้อมกันเมื่อ independent (เช่น endpoint ละ developer):
- solution-architect เสนอการแตกงานให้ the router dispatch (developer ไม่ self-spawn)
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
| Implement ตาม spec ชัด, refactor, bug fix, integration | developer |
| Setup/Docker/CI/Deploy | → devops-engineer (Phase 5 continuous per bd, or manual batch) |
| Spec กำกวม | → business-analyst clarify (Phase 1a parallel solution-architect) |

## Bug prevention method (v2.2)

2. **Type from OpenAPI** (solution-architect produce, developer consume)
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
10. **Hand-off → Phase 3a UI Check (ux-ui-designer POST gate, sequential 🔴 v2.8)** — ถ้า frontend changed: ux-ui-designer ตรวจ visual diff + design adherence + a11y manual + own AC verification → PASS unlocks Phase 3b, FAIL loops Phase 2 (developer fix) หรือ Phase 1b (ux-ui-designer redesign baseline). Pure backend = skip → ตรง Phase 3b
11. **Phase 3b** — independent code-reviewer; qa-engineer per harness tier/boundaries; ux-ui-designer POST for UI; devops-engineer for environment/CI. Retain triggered reviews. Parallel or separate sequential contexts; evidence → the router.

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
### Hand-off — code-reviewer / qa-engineer / ux-ui-designer: what to check
```
