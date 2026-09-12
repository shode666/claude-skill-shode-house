# Engineering loop inside the team

Read for design, implementation or diagnosis; not for greetings or routine status.
This refines existing role ownership, not a second workflow or replacement team.

## Resolve uncertainty before expanding work

Bella records observable acceptance and shared business vocabulary. Inspect project
facts first. Oliver routes technical uncertainty to Sara/Stan or the relevant domain
expert; only unresolved policy, scope or authority goes to the user. Ask the current
decision frontier together, with alternatives and a recommendation. Do not ask a
dependent question before its prerequisite is settled. Reuse recorded decisions;
do not turn every continuation into another approval ceremony.

## Deliver vertical, testable increments

Sara and Dave choose a thin end-to-end slice that exercises the risky boundary,
then decompose remaining work by dependency and verifiable outcome. Each slice has
one owner, acceptance and a test seam. Do not split by arbitrary file counts or
build every abstraction before a working behavior exists. Domain experts preserve
business invariants; Sentinel preserves security and transaction boundaries.

Dave uses red-green-refactor for changed behavior: establish an intended failure,
make the smallest correct implementation, then refactor with checks green. Read
existing tests first. A recorded matching reproduction can establish the red step;
do not rerun merely to manufacture ceremony. Expected results must come from the
contract or independently derived examples, not a copy of the implementation.
Prefer public-behavior tests; mock genuine external boundaries, not every internal
method. Keep meaningful integration checks where mocks could hide a broken contract.

## Diagnose with falsifiable hypotheses

For a diagnosis request, reproduce or collect relevant evidence, form a bounded
hypothesis, choose a discriminating check, and revise from the result. Do not make
an unrequested fix. For an authorized fix, add the regression and verify neighboring
behavior. An unchanged failure requires a new hypothesis/evidence, not blind retries
or a full pipeline reset. Record environmental limits as BLOCKED, never green.

## Review without overlap or overengineering

Bella verifies requirement conformity; Chris checks internal behavior, invariants,
error paths and maintainability; Quinn checks integration and user journeys. Link
the same defect under one finding ID across axes. Keep independent review contexts
and preserve dissent rather than counting duplicate findings as extra assurance.

Chris and Sara challenge each new abstraction: what current responsibility or
variation requires it, and what simpler application-layer design satisfies the
same contract? Prefer cohesive modules with small interfaces. Apply SRP by reason
to change, not one class per line of logic. Reject speculative frameworks, empty
pass-through layers and generic engines with no demonstrated need. Do not remove
required authorization, transaction, audit or isolation boundaries for simplicity.

## Spend context on decisions

Keep shared terms and consequential ADRs in the confirmed record home. Load only
the affected expert knowledge; retain the complete knowledge in the distribution.
Send artifact deltas, evidence locations and unresolved questions, not transcripts.
Never trim acceptance, approvals, domain constraints or UNKNOWN operations to fit
a token budget. Measure actual usage when the host exposes it; label byte counts
as bytes, not token savings or quality proof.

Design inspiration: https://github.com/mattpocock/skills (shared vocabulary,
decision questioning, feedback loops and deep modules). These are applied through
Shode House's existing specialists, harness and verification ownership.
