---
name: shode-house-team
description: Coordinate software delivery, bug fixes and reviews with clear ownership, risk-based verification and resumable handoffs. Use when the user requests the Shode team or a multi-step engineering workflow; not for ordinary standalone questions.
---

# Shode team

Use available host tools and project build/test tools; no custom runtime scripts,
interpreter, hooks or tracker are required by this skill. Follow repository rules
and existing authorization. Do not auto-load legacy Shode prompts, skills or output
styles: they define a different workflow. Never emulate missing permissions.

## Pick the outcome and load only relevant guidance

Resolve acceptance criteria, affected scope and uncertainty from the request and
current evidence. Choose by outcome, not keywords; "bug" alone does not authorize
a fix. Combined requests may use several modes, without repeating shared checks.

| Requested outcome | Guidance to read when applicable |
|---|---|
| Explain or consult | Answer directly; no delivery pipeline. For consequential uncertainty, read [decisions.md](references/decisions.md) |
| Review existing work | Report findings, do not edit. Read [design-review.md](references/design-review.md) for architecture/maintainability; [verification.md](references/verification.md) when assessing behavior or tests |
| Diagnose a failure | Read the diagnosis section of [verification.md](references/verification.md); establish cause/confidence without implementing an unrequested fix |
| Build or fix | Read [verification.md](references/verification.md); also [design-review.md](references/design-review.md) when adding/changing boundaries, dependencies or abstractions |
| Clarify business terms or consequential choices | Read [decisions.md](references/decisions.md); reuse project vocabulary and settled decisions |
| Resume, hand off, or work across sessions | Read [continuity.md](references/continuity.md) before resuming or the first durable checkpoint |

References live inside this skill folder. Read relevant files with the host's file
reader; no Skill tool or command alias is required. Do not load every reference
for every task. If a required reference is missing, disclose the incomplete install.

## Ownership and execution

Assign one delivery owner per work item. Roles are responsibilities, not mandatory
personas or processes. Use the smallest useful team supported by the host.

| Responsibility | Boundary |
|---|---|
| Lead | Scope, dependencies, routing, synthesis and delivery status |
| Product/spec | User outcome, acceptance and missing/wrong requirements |
| Architecture | Consequential interfaces and cross-component tradeoffs |
| Implementer | Code, relevant tests and implementation evidence |
| Code reviewer | Internal correctness, error paths, security and maintainability |
| QA / UX | Affected integration, user journeys, interaction and accessibility |
| Security/domain / operations | Triggered specialist risk, deployment and recovery |

Implementers own tests; reviewers challenge them. Spec review does not repeat code
review: link scope concerns to the same finding. For money/auth/PII or irreversible
actions, retain relevant specialist review and approval controls. Expert advice
cannot grant user authority. Independent review must actually be independent;
if required but unavailable, hold the affected action and disclose the gap.

Split only into verifiable outcomes. Delegate objective, authorized scope, relevant
paths, constraints and expected return, not the full conversation. Parallelize only
independent work when permitted; serialize shared-file writes. Ownership is not a lock.
Ask only blocking decisions, continue unaffected work, and never treat silence as
approval. Reuse approvals only within unchanged scope; facts require evidence.

Reuse verification only when revision/content, command and environment still match.
Reproduce high-risk or disputed claims independently. Recheck affected dependencies,
not every previous phase. Preserve evidence and dissent under one finding ID.
Distinguish FAIL, BLOCKED, PARTIAL and verified completion.

Return outcome, artifacts, decisive verification and remaining risks. Keep full logs
in artifacts and redact secrets. No mandatory recital, role introductions, dispatch
cards or fixed report template for trivial work.
