# Design review

Verify design proportionality as well as correctness. Prefer application-layer
delivery using the project's existing stack and boundaries. For each added layer,
interface, dependency, service or framework, identify the current requirement or
demonstrated risk it solves and compare a simpler alternative. Flag speculative
extension points, pass-through layers, generic engines for one use case, duplicated
configuration and new infrastructure without a present need. Do not redesign valid
existing architecture merely to satisfy this preference.

Apply SOLID proportionally, especially single responsibility: a module should have
one cohesive responsibility/reason to change. Separate unrelated policy, persistence
and presentation concerns where they create real coupling; do not equate SRP with
one function per class or an interface for every implementation. Preserve necessary
transaction, security and reliability boundaries even when they add code.

The code reviewer owns this check; involve architecture only for consequential
boundary changes. Report concrete added maintenance/test/operational cost, evidence
and the simpler design. Spec reviewers link any scope violation to that same finding.
Block for demonstrated correctness/security risk or unauthorized scope; a subjective
style preference alone is a suggestion. Do not reward fewer lines at the expense of
correctness or expand a review request into an unsolicited refactor.

## Judge the boundary, not just the line count

Ask what a caller must know: parameters, ordering, invariants, errors and configuration.
A useful module hides cohesive complexity behind a small understandable interface.
If removing a layer eliminates complexity without spreading knowledge into callers,
it may be unnecessary; if callers would repeat policy, the layer may earn its keep.
This is a thought experiment, not permission to delete code during review.

Compare a simpler design against current behavior, change locality and testability.
Do not demand an interface solely for hypothetical implementations, or collapse
security/transaction boundaries because there is only one implementation today.
An application service may coordinate a use case without becoming a generic engine.
Keep project vocabulary; no mandated architecture jargon or framework migration.
