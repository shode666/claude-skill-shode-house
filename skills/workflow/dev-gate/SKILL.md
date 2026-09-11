---
name: dev-gate
description: |
  [WHAT] Implement and verify a scoped code change using behavior tests and existing project quality gates.
  [WHEN] Authorized implementation, refactoring or regression fixes; not project-wide CI setup.
  [TRIGGER] /shode-house:dev-gate, "TDD", "test first", "verify this change".
---

# Dev Gate (per-change implementation quality)

Owner: implementer produces code/tests/evidence; reviewer challenges them.
This skill owns per-change test discipline. `automate-test` owns project-wide CI
selection/configuration, not another copy of these checks. Skill activation alone
does not authorize edits, commits, pushes, hook installation or deployment.

## When NOT to use

Review-only work uses `review-checklist`; diagnosis-only work uses `diagnose`.
Exploration/prototypes need checks proportional to their purpose, not a production
pipeline. Config/generated changes need appropriate validation of their source and
affected behavior, not fabricated TDD history. Active incidents use `incident`
within authorized scope; urgency does not silently waive safety controls.

## Required inputs

Resolve the requested behavior/acceptance, authorized scope, relevant existing
interfaces and project test/check commands. Missing BRD/ADR documents are not by
themselves blockers if the requirement is clear. Unknown business decisions or
consequential scope changes require the authorized owner's decision.
Missing tools/evidence limit verification; report the gap instead of inventing PASS.

## Part 1: TDD Cycle

### Step 0: YAGNI ladder

Check the current requirement before adding code. Prefer the existing implementation,
standard library, native platform or installed dependency when it meets the need.
Compare new layers/frameworks with a simpler application-layer solution. Do not
drop an accepted requirement because it looks expensive or optimize for one-liners.

### Lazy ≠ Negligent — carve-out

Simplification must preserve trust-boundary validation, data-loss protection,
transactions/idempotency where needed, security, applicable accessibility and
regulatory requirements. Record meaningful deferred work in the project's designated
tracker with rationale; routine reuse of existing code is not technical debt.
Preserve existing `shortcut(bd:N):` links where the project uses that convention.

### Seams and test quality

Use a public boundary that exposes the relevant behavior, including real integration
when a unit test cannot exercise it. Reuse agreed acceptance/interfaces rather than
asking the user to reconfirm each test. Ask when a choice changes scope or accepted risk.
Expected values come from independent requirements, known fixtures or worked examples,
not a copy of the implementation formula. Avoid tests of private wiring and mocks
of the business logic under test. Isolate external dependencies when useful, and
do not describe mocked integration as verified real integration.

### Red → Green → Refactor

For test-first work and regression fixes, take one behavior through an intended
failing assertion, minimal implementation and passing check before the next slice.
Setup/compile errors alone do not prove the test detects the bug. Refactor within
scope with tests green; do not mix speculative behavior into cleanup.
Use deterministic fixtures/time when appropriate, not sleep-based guesses.

## Part 2: Quality Gates

Run applicable existing project checks, not a fixed eleven-tool pipeline. Do not
invent Make targets, replace the toolchain or install extra frameworks for this skill.
Existing coverage/complexity/security thresholds remain authoritative; report failures
without lowering thresholds, disabling tests or suppressing warnings to obtain green.

### Gate 0: Architecture self-check

Apply SOLID proportionally. SRP means a cohesive responsibility/reason to change,
not one method per class or splitting every description containing "and".
Keep unrelated policy, persistence and presentation concerns from creating costly
coupling, while respecting working application-layer conventions. Do not require
interfaces for every concrete dependency or future extension that is not needed.

A useful deep module hides cohesive complexity behind an understandable interface.
The deletion test is a thought experiment: would removing a layer eliminate needless
wiring, or spread policy into callers? Do not delete code merely because it has one
adapter, and preserve security/transaction boundaries. Report concrete maintenance,
test or operational costs; subjective style alone is not a blocker.

### Mechanical checks and evidence

| Concern | Apply to the change |
|---|---|
| Format/imports/unused code | Follow configured conventions; restrict auto-fixes to authorized files and preserve public compatibility |
| Lint/types | Run configured checks; explain legitimate exceptions without hiding failures |
| Complexity/naming | Assess readability, cohesion and change locality; project limits, not universal line counts |
| Tests | Exercise acceptance, boundaries and error paths; follow configured coverage without treating coverage as correctness |
| Security | Relevant validation/auth/secret/dependency checks; retain required specialist review and project gates |
| Docs/build | Update affected public contracts and verify applicable build/config behavior |

Reuse evidence only for matching content, command and environment. Recheck changed
behavior and affected dependencies; no duplicate suite per reviewer unless independence
or a disputed/high-risk claim requires it. Never label unavailable checks as passed.

## Pre-commit hook

Existing hooks and required gates remain in force. This skill does not mandate a
hook manager or new interpreter. Only for authorized hook setup, read
`pre-commit-config.md`; it is an optional example, not a runtime requirement.
Do not bypass configured controls to force a successful commit.

## Hand-off

Return changed artifacts, decisive commands/results, applicable failed/unavailable
checks and remaining risks. Required checks failing means incomplete verification,
not permission to skip/xfail them. A green build is not permission to commit or push.

## Skill composition (where to go next)

| Situation | Next skill | Boundary |
|---|---|---|
| Authorized project-wide CI/strategy change | `automate-test` | Not mandatory for one regression test or merely because CI is absent |
| Relevant UI interactions | `ui-test` | Applicable visual/interaction evidence |
| Public web quality investigation | `web-q` | Only affected performance/SEO/security concerns |
| Security-sensitive change | `secure` | Relevant specialist review |
| Review handoff | `review-checklist` | Review findings, not duplicate implementation |
