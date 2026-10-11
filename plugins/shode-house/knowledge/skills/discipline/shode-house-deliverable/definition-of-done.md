---
name: definition-of-done
description: Reference (lazy-load) ของ `shode-house-deliverable` — Definition of Done (verifiable, per owner). โหลดตอนจะ produce/finalize deliverable
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-deliverable/definition-of-done.md
WHEN: phase_exit=true
OWNER: router
REQUIRED-BEFORE: bd_close
```

# Definition of Done (verifiable, per owner)

> แยกจาก `SKILL.md` v3.12.1 — 7 agent preload skill นี้ แต่ส่วนนี้ใช้เฉพาะตอนกำลังจะส่งงานจริง

## ✅ Definition of Done (🔴 verifiable — router enforce ห้ามปิด task)

Evaluate the checklist against the agreed deliverable, affected surfaces and
project-required gates before executing it. Record applicability and evidence;
do not add UI, databases, containers, feature flags or deployment merely to satisfy
a checklist example. Backend-only work has no UI gate. A module without an external
API/DB has no BE-FE/DB journey. Deployment/merge checks apply only to an authorized
deployment/merge outcome, not permission to perform those actions.

Missing evidence for an applicable requirement is BLOCKED, never N/A. N/A requires
a concrete scope/diff reason. Reuse unchanged approved design where appropriate;
Required reviewers follow the harness risk tier/triggers and remain separate actors,
whether parallel or serial. For bounded work, linked acceptance/design/evidence in
one task record suffices; do not invent full BRD/ADR documents for phase labels.
Use existing project quality targets and tools. Do not install a mutation/load tool
or invent a measured score when the agreed scope forbids it; disclose any required
check that cannot run. The numbers/tool names below are examples unless adopted as
the project's acceptance thresholds.

Tracker operations below show Beads syntax only. Use the confirmed canonical home;
verify the update by reading it back, or record pending sync if the service is down.

> Team roster = single source ใน `shode-house-routing` (6 agent types + the router style, 7 teams)

```
□ Phase 1a Foundation passed (`plan` (requirements mode) ∥ `plan` (architecture mode) light cross-read ok, task notes posted)
□ Phase 1b Expand passed (`design`* sign UI accept + baseline; Domain* sign regulation/rule; integrated SPEC saved)
□ Phase 3a UI Check PASS (`design` verdict before `verify` เริ่ม)
□ Phase 3b Code Review passed (`verify` (standards axis) + `verify` (runtime axis) independent, 0 Critical/Major)
□ Loop iter ≤ 3 + routing precise (code→2, UI→1b, spec→1a); iter > 3 → escalate user, or BLOCKED + checkpoint when no user channel (harness § iteration cap)
□ Review report saved in the confirmed evidence home; canonical task links it without duplicating the report. Verify authorized remote updates or record pending sync.
□ Code merged + CI green (lint+type+unit+integration+SAST+SCA)
□ Contract test pass (Pact/Schemathesis — BE ↔ FE align)
□ Mutation test on business logic when adopted or risk requires (example ≥ 70%)
□ Pre-merge integration smoke pass (BE+FE+DB up + curl journey)
□ UI Design (UI changed): `design`-approved design/existing design system + affected a11y criteria before `build` implements
   Evidence: design link/path + applicable tokens/a11y criteria; Figma/tokens.json are examples
□ UI Test (rendered UI/interaction changed): affected interaction/visual/a11y checks pass via project/host tools; applicable visual diff approved
   Evidence: test output + screenshot/diff + a11y report + applicable trace; missing required evidence = BLOCKED
□ Load smoke: p95 < SLO, error < 0.1%
□ Deploy staging + `operate` (deploy mode) screenshot ✅
□ E2E user journey on staging (`verify` (runtime axis) — Playwright trace)
□ Manual UI walkthrough 5 critical screens (`design`)
□ Docker `docker compose up` from clean machine works (`operate` (deploy mode))
□ Feature flag wired + tested both states (if risky)
□ Observability: log/metric/trace + SLO alert configured
□ 🔴 **Router closes the task with evidence** (M8 Close-on-Done): the router closes it in the confirmed tracker with reason "<verdict> <commit_sha> <test_result>" and reads it back as CLOSED; workers return this evidence and never close
   Evidence: paste output ของ read-back — code merged แต่ bd ยัง OPEN = **ยังไม่ done** (stale-open)
```
Any applicable unresolved criterion blocks completion and the affected merge/closure.
Report actual evidence, approved scope and N/A reasons; never claim a remote status
change without its authoritative read-back.
