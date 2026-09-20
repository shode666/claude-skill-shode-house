# Dev Gate — Quality gate detail (Gate 0–10, smells, pre-push)

```lazy-load-contract
LOAD: skills/workflow/dev-gate/quality-gates.md
WHEN: gate_failed=true OR gate_criterion_unclear=true OR new_module_or_interface=true OR suppression_or_shortcut_considered=true OR gate_verification=true
OWNER: developer
REQUIRED-BEFORE: handoff_phase_2_to_3
```

Root `SKILL.md` rules (11-gate table, carve-out, hand-off boundary) apply throughout.
Tool selection per stack → [tool-matrix.md](tool-matrix.md) (only when a gate lacks a verified command).

> เพิ่ม Gate 0 Architecture self-check (SOLID/cohesion/readable) + เพิ่ม Gate 9 Security Lint. แตก Format เป็น Format / Imports / Remove-Unused เพราะ 3 หมวดใช้ tool ต่างกัน

### Gate 0: Architecture self-check

> Tool ตรวจ Gate 1-10 ได้ครบ แต่ **SOLID/cohesion/readable ต้องคนตัดสิน**. Dave self-check ก่อน hand-off ลด round-trip กับ Chris

**SOLID — apply to actual responsibilities, not an abstraction quota**:
- [ ] **SRP** — group behavior with one reason to change; the word "and" alone does not require splitting.
- [ ] **OCP** — isolate demonstrated variation; do not add interfaces for hypothetical extension.
- [ ] **LSP** — subclass แทน parent ได้ทุก context (ไม่ throw, ไม่ break invariant)
- [ ] **ISP** — interface เล็ก. ห้าม "fat interface" ที่ implementor ต้อง stub method ที่ไม่ใช้
- [ ] **DIP** — depend on abstraction (interface/protocol) ไม่ใช่ concrete class. business logic ห้าม import framework โดยตรง

**Cohesion + Coupling**:
- [ ] **High cohesion** — related behavior belongs together; split only for distinct responsibilities.
- [ ] **Low coupling** — module A ไม่ควรรู้ internal ของ module B. ผ่าน interface/event/DTO
- [ ] **Stable dependency** — depend ไปทาง stable (lower layer). ห้าม domain → infra direct

**Deep module — abstraction นี้ควรมีอยู่ไหม (🆕 v3.12, คู่กับ YAGNI ladder)**:
- [ ] **Deep ไม่ใช่ shallow** — behaviour เยอะหลัง interface เล็ก. shallow = interface ซับซ้อนพอ ๆ กับ implementation (ตัวส่งผ่าน). ถาม: ลด method ได้ไหม? ลด parameter ได้ไหม? ซ่อนความซับซ้อนเพิ่มได้ไหม?
- [ ] **The deletion test** — ลอง "ลบ module นี้ทิ้ง": ความซับซ้อนหายไป = มันเป็น pass-through (ลบจริง); ความซับซ้อนโผล่ที่ caller N ที่ = มันคุ้มค่าตัว
- [ ] **Justified seam** — present variation, testability, security or isolation can justify a boundary even with one implementation; speculative future adapters alone cannot.
- [ ] **interface คือ test surface** — caller กับ test ข้าม seam เดียวกัน. ถ้าอยากเทสต์ *เลย* interface เข้าไป = module รูปร่างผิด ไม่ใช่ test เขียนยาก

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

### Gate 1: Format
- Auto-format on save (IDE) + pre-commit hook + CI gate (3 จุด)
- **ห้าม**: manual format / "ไม่ตรง project standard but readable"

### Gate 2: Organize Imports
- Sort + group: stdlib → 3rd-party → local
- Alpha-sort within group
- ห้าม wildcard import (`from x import *` / `import *`)
- ห้าม relative `..` import เกิน 1 level

### Gate 3: Remove Unused
- Unused **import** → ลบ (F401 / no-unused-vars)
- Unused **local variable** → ลบ (F841)
- Unused **function parameter** → ลบ หรือ prefix `_` ถ้าจำเป็นต้องเก็บ signature
- Unused **function/class export** → ลบหรือ mark internal (ts-unused-exports / vulture)
- ห้าม `# noqa` / `// eslint-disable` โดยไม่ comment "why" + ticket

**Deferred-shortcut convention** (จาก ponytail — ทางลัดที่ YAGNI ladder ตัดไว้):
- รูปแบบบังคับ: `shortcut(bd:<id>): <reason>; upgrade → <path>`
- ตัวอย่าง: `# shortcut(bd:42): in-memory dict; upgrade → Redis เมื่อ >10k key`
- `grep -rn 'shortcut(bd' .` / `/review --debt` รวบเป็น ledger → "later" ไม่กลาย "never"
- ห้าม shortcut โดยไม่มี task id (ต้อง track ได้)

### Gate 4: Lint (strict — diagnose)
- Run adopted project lint rules; consult the tool matrix only when selecting missing tooling. Do not enable every rule without assessing project compatibility.
- Lint warning = ticket (track หรือ fix); ห้าม ignore

### Gate 5: Type Check (🔴 strict)
Use the project's adopted type checker and strictness. The language commands below
are examples, not authority to replace a verified checker or install another one.
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
- Unit coverage per adopted target (example ≥ 80% business logic; Chris's responsibility; Dave smoke ก่อน hand-off)
- AAA pattern + G-W-T naming
- Edge case + error path
- ห้าม skipped/disabled test ไม่มี ticket

### Gate 9: Security Lint
- SAST per language (ดู matrix Gate 9 column)
- Secret scan (gitleaks / `git-secrets`) — block commit ที่มี API key / password / cert
- Dependency audit (`npm audit` / `pip-audit` / `cargo audit`) — block critical/high vulns
- **ห้าม**: ignore security warning โดยไม่ Sentinel approve

### Gate 10: Doc
- Docstring/JSDoc สำหรับ public API (signature + example + edge case)
- Inline comment เฉพาะ "why" ไม่ใช่ "what"
- README update ถ้า API change

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

## Pre-Push Checklist (all 11 gates)

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
