---
name: dev-gate
description: Apply test-first development and quality gates during implementation or refactor of production code, ending with validation evidence before handoff. Not for spikes, generated code, pure configuration changes, or investigating a problem whose cause is still unknown.
---

# Dev Gate (TDD + Quality Gates)

> **Owner**: Dave (implement) + Chris (verify). เปิด skill นี้ตอนเขียน production code

Purpose: implement, fix or refactor production code test-first and hand it off with quality-gate
evidence.

## Always

- Preserve authorized behaviour — change only what the approved acceptance covers.
- Avoid unnecessary complexity (YAGNI ladder, Step 0) — never at the cost of the carve-out below.
- Protect security and data integrity (carve-out below; security-sensitive work → `secure`).

## When NOT to use

- **Spike / prototype / throwaway script** — TDD overhead ไม่คุ้ม. ใช้ `diagnose` แทนถ้าเป็น exploration
- **Generated code** (codegen, OpenAPI client, ORM model) — gen tool ดูแล quality, dev-gate ไม่ฟิต
- **Pure config change** (yaml/json/env tweak) — review + smoke test พอ ไม่ต้อง TDD
- **Production hot-fix P0/P1** — ใช้ `incident` skill ก่อน; dev-gate ตามมาตอน follow-up fix

## Inputs and decision boundaries

Derive first + cite: acceptance + design decisions → task record + linked spec/ADR · gate commands/thresholds → project config (Makefile · package scripts · CI). Not found → return the question to Oliver; never guess, never ask the user directly.
When to ask → `shode-house-discipline` § Ask vs derive

### Stop and return

ขาดข้อใด → **list สิ่งที่ขาด แล้วหยุด** ส่งกลับ Oliver:

- [ ] Approved acceptance + affected design decisions, linked from the task record; bounded work needs no new BRD/ADR ceremony.
- Required check รันไม่ได้ → BLOCKED ส่งกลับ Oliver; ห้าม install dependency เองโดยไม่มี authority
- จะ suppress security warning → Sentinel ก่อน (§ ห้าม)

### Hand-off evidence (Phase 2 → 3) — ขาดข้อใด = ยังไม่ done, ห้าม claim "done"

- [ ] **Test runs locally** (red phase): ทุก new behavior มี failing test ก่อน implement
- [ ] Required acceptance tests pass; tracked quarantine does not satisfy a missing required test or authorize skipping it.
- [ ] **Quality gate ผ่านครบ 11** (Gate 0-10, ดู Part 2): YAGNI · format · lint · type · complexity ≤10 · naming · test · coverage ≥ threshold · doc/comment "why" · security · observability
- [ ] **Evidence paste**: command + output ใน hand-off (ห้าม "should work")

## หลักการ (🔴)

1. **No production code without failing test first** (TDD core)
2. **Quality at dev time, not after** — catch defects before hand-off; no universal cost multiplier.
3. **Best code = code you never wrote** — ผ่าน YAGNI ladder (Step 0) ก่อนทุกครั้ง

### Lazy ≠ Negligent — ห้ามตัด (carve-out)

YAGNI/compression ตัดได้เฉพาะ "ความซับซ้อนที่ยังไม่ต้องใช้" — **ห้ามแตะ**:
- Trust-boundary validation (input/HTTP/queue/env — Zod/Pydantic)
- Data-loss handling (transaction, idempotency, money R0)
- Security control (auth, crypto, secret, injection guard)
- Accessibility (WCAG — Uma's gate)
- Regulation/compliance (Felix BOT/PCI · Iris OIC · domain rule)

ตัดของเหล่านี้ = Philosophy violation, ไม่ใช่ "lazy"

---

## Routing — load only the branch the task is on

| Situation | Load / use | Reason |
|---|---|---|
| New behaviour or bug-fix regression test | → [tdd.md](tdd.md) before writing the first test | seams, worked example, test anti-patterns |
| Refactor (behaviour unchanged) | stay in this root: § 3 Refactor + § ห้าม; add [quality-gates.md](quality-gates.md) when a module/interface is reshaped | tests stay green |
| Quality validation: a gate fails, its criterion is unclear, a new module/interface/abstraction appears, a suppression/skip/shortcut is considered, or Chris verifies gates | → [quality-gates.md](quality-gates.md) before hand-off | gate detail, smells, pre-push sequence |
| Touch security control (auth/crypto/PII) | → `secure` | Sentinel threat model + abuse case (dev-gate ไม่ classify threat) |
| Language-specific conventions | → only the active language's file `references/languages/<lang>.md` | — |

Dave/Chris: reuse the project's verified gate commands. When a gate lacks a known
command or tooling is being configured, read [tool-matrix.md](tool-matrix.md) before
selecting tools; use only the relevant stack row. Missing required checks remain
BLOCKED. The reference is guidance, not permission to install dependencies.

Use the project's existing gate mechanism. Installing pre-commit or changing hooks
requires setup authority; missing required checks still block hand-off. Do not bypass
configured production checks with `--no-verify`.
ตัวอย่าง config เต็ม (Python / TS) + setup steps → **`pre-commit-config.md`** (ไฟล์ข้าง SKILL.md นี้)

---

## Part 1: TDD Cycle (red → green → refactor)

### 0. ⛔ YAGNI ladder — หยุดก่อนเขียน (จาก ponytail)

ก่อนเขียน production code ใด ๆ ตอบไล่จากบนลงล่าง หยุดที่ข้อแรกที่ "ใช่":

| ขั้น | ถาม | ถ้าใช่ |
|---|---|---|
| 1 | feature นี้ต้องมีจริงไหม? | ไม่ → skip (YAGNI) + log เป็น discovered task |
| 2 | stdlib ทำได้ไหม? | ใช้ stdlib |
| 3 | native platform feature? (`<input type=date>`, `crypto`, ...) | ใช้ native |
| 4 | dep ที่ลงแล้วทำได้? | ใช้ของเดิม ห้ามลง dep ใหม่ |
| 5 | one-liner พอไหม? | เขียนบรรทัดเดียว |
| 6 | ถ้าผ่านทั้งหมด | เขียน "ขั้นต่ำที่ work" เท่านั้น |

> ทุกครั้งที่ตัด (ขั้น 1) หรือใช้ทางลัด → mark ด้วย `shortcut(bd:N):` comment (format → `quality-gates.md` Gate 3) เพื่อให้ debt harvest เก็บได้
> เพดานความขี้เกียจ = carve-out ด้านบน (validation/security/a11y/regulation ห้ามตัด)

### 1. 🔴 Red — เขียน test ที่ fail ก่อน
- Test เล็กที่สุด — 1 behavior
- Naming: `should_<behavior>_when_<condition>` หรือ G-W-T
- Run → ต้อง fail (assertion fail; compile error ไม่นับ)

### 2. 🟢 Green — เขียน code น้อยที่สุดที่ pass
- Simplest thing that works (YAGNI)
- ห้าม anticipate future requirement
- ห้าม refactor ตอนนี้

### 3. 🔵 Refactor — clean up (test ยัง pass)
- Remove duplication, improve naming, extract function
- ห้ามเพิ่ม behavior ใหม่ในรอบ refactor

---

## Part 2: Quality Gates (🔴 11 gates — รัน local + pre-commit + CI)

Every gate applies to every hand-off; this table is the pass criterion.

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
| 8 | **Test** | Run | adopted coverage target (example ≥ 80%), no skipped test | 🔴 |
| 9 | **Security Lint** | Read (SAST) | injection/secret/insecure dep | 🔴 |
| 10 | **Doc** | Read (existence) | docstring on public API + "why" comment | 🟠 |

---

## Completion

Complete = no open § Stop and return condition, every § Hand-off evidence item pasted, and `shode-house-deliverable` § Completion (continue-until · stop-when · affected validation = floor + broaden cases) met.

## ห้าม

- ห้ามเขียน code ก่อน test (TDD core)
- Do not hide failing acceptance with skip/xfail. Quarantine needs an owner, tracked reason and applicable authority; unresolved required coverage remains BLOCKED.
- ห้าม refactor พร้อม add behavior — แยก commit
- ห้าม mock business logic — mock เฉพาะ external (DB/API/clock)
- ห้ามใช้ `time.sleep` ใน test → fake time/freeze
- ห้าม disable lint rule โดยไม่ comment + ticket
- ห้าม `// @ts-ignore` / `# type: ignore` โดยไม่ ticket
- ห้าม commit `console.log` / `print` debug
- ห้ามใช้ `any` (TS) / `Any` (Py) เป็นทางลัด
- ห้าม PR ที่ลด coverage (CI ตั้ง gate, ratchet)
- ห้าม merge code ที่ build แดง
- ห้าม ignore/suppress security warning (SAST · secret scan · dependency audit) โดยไม่ Sentinel approve — secret/critical-high vuln = block commit (detail → quality-gates.md Gate 9)

## Skill composition (where to go next)

| Situation | Next skill | Reason |
|---|---|---|
| Test pass แต่ยังไม่มี CI gate | → `automate-test` | Pyramid ratio + CI threshold + contract test |
| Code touches frontend | → `ui-test` | E2E + visual + a11y automation |
| Frontend public-facing (perf/SEO/security) | → `web-q` | CWV + Lighthouse + security headers budget |
| Hand-off Phase 2 → 3b review | → `review-checklist` skill | Chris 7-dim + Quinn integration matrix