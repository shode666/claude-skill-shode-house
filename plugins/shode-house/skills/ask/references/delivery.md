# Design through delivery

Identify the requested outcome, existing behavior and acceptance criteria. For setup,
inspect the repository before proposing missing tools/config; never scaffold over
working files or install CI/hooks merely because a workflow lists them.

For design, reuse current code, specs and domain terms. Produce the smallest useful
design: scope/non-goals, behavior and error cases, affected interfaces/data, risks and
verification criteria. UI-only work needs relevant tokens/states/interaction decisions,
not an unrelated BRD/C4/DR package. New infrastructure/abstractions need a present
requirement and comparison with a simpler application-layer option. Record only
consequential tradeoffs; no fixed quota of ADRs, diagrams, experts or rounds.

Resolve consequential questions using `decisions.md`. Specialists provide evidence
and recommendations, not user permission. Never claim an independent review when
the same actor did the work or the host has no independent reviewer.

Design completion alone does not authorize implementation. If the user asked only
for design, return its result and wait. A follow-up such as "start implementing" or
"เริ่มทำได้เลย" can authorize the identified design within its agreed scope: reuse
that artifact and conversation/checkpoint, without requiring `/implement` or restarting
discovery. A generic "ok" acknowledging a report is not necessarily an implementation
request; ask only when the intended next action is consequential and unclear.
If design and implementation were already both authorized, no redundant approval
ceremony is needed. Changed scope or risk may require a new decision.

Implement in verifiable behavior slices with existing conventions. Use `verification.md`
for meaningful regression checks and `design-review.md` for proportional architecture.
Delegate only useful independent work with bounded context and nonoverlapping writes;
keep main-session ownership. Integrate and review results before declaring completion.
Commit, publish, deployment and destructive/external actions need their own authority;
"implement this design" is not permission to ship it to production.

At a meaningful boundary, record artifacts, verification and the next action using
`continuity.md`. On resume, inspect actual current implementation separately from
design approval and invalidate stale evidence. Continue authorized unaffected work;
stop affected work at a genuine unresolved permission, scope or evidence boundary.
