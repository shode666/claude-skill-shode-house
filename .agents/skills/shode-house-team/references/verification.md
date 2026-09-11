# Behavior verification

Use this for implementation tests, review of test quality, and diagnosis; these
share evidence rules, not authorization. Diagnosis/review alone does not permit fixes.

## Tests for a change

Choose checks from affected behavior and existing project tools: API contracts and
integration, CLI outputs/exit codes/error paths, or UI interaction/visual/accessibility
as applicable. Do not require screenshots for pure API/CLI work or introduce a
framework to satisfy a generic checklist. Mark missing/inapplicable checks explicitly.

Test at the public boundary that can expose the failure, including real interactions
when a unit test cannot represent them. Reuse agreed interfaces and acceptance criteria;
ask only when choosing a test boundary would change scope or accepted risk.
Expected results must come from requirements, independently worked examples or known
fixtures, not a copy of the implementation's calculation. Avoid private-method
assertions and mocks of internal wiring; mock external boundaries when isolation is
needed, without presenting mocks as proof that the real integration works.

For test-first work or a regression fix, take one behavior through failing test,
minimal implementation and passing test before the next slice. Confirm failure is
the intended assertion, not broken setup. Refactor within scope with tests remaining
green. Do not rewrite working code merely to make historical work look test-first.
In review-only work, inspect test sensitivity using permitted non-mutating checks;
describe an untested gap rather than silently editing the target.

No universal coverage percentage or unit/integration/E2E ratio: use project gates
and risk. An existing gate failure remains visible; do not lower it to get green.
For CI strategy work, baseline failures, runtime and flakiness before adding gates.
Use the smallest suite that covers the change and meaningful affected dependencies.

## Diagnosis

Identify expected versus actual behavior and the affected environment. Try the
smallest safe repro: existing test, API request, CLI fixture, or UI interaction.
Verify it catches the user's symptom, not a nearby failure or merely "did not crash".
Redact credentials and private data from logs, traces and shared artifacts.

For a clear local defect, avoid a ceremony of multiple theories. For uncertain,
cross-component or intermittent failures, reduce the repro and compare falsifiable
hypotheses; change one relevant variable per probe. Record which evidence changes
the next action. For performance, measure an appropriate baseline before proposing
an optimization. Avoid stress tests or replaying mutating requests without authority.

If reproduction is inaccessible, code/log analysis may produce explicitly tentative
hypotheses, not a confirmed root cause or verified fix. State the missing access or
evidence and continue safe investigation. Do not require a new harness or interpreter
when existing tools suffice.

When a fix is authorized, demonstrate that the regression check detects the original
failure and passes after the change; recheck the original scenario as well. A live
side effect is not a safe test fixture. Remove only temporary instrumentation you
introduced, preserve user artifacts, and report any missing regression coverage.
