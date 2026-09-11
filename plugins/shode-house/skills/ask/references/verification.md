# Behavior verification

Review/diagnosis does not authorize fixes. Select checks by affected behavior and
existing project gates: public API/CLI contracts, integration, or UI interaction,
visuals and accessibility as applicable. Pure API work needs no screenshot.
Do not install a framework or demand a universal coverage percentage/test ratio.

Inspect relevant existing tests before inventing a repro. If they demonstrate the
failure at the required boundary, reuse that evidence; add a probe only for an
uncovered input, disputed claim or interaction. Unit mocks do not prove real
integration. Mock external boundaries for isolation, not internal wiring.

Expected results come from requirements or independently worked examples, never
the implementation's own formula. Check observable behavior rather than private
methods. An unavailable required test remains BLOCKED; an existing failure stays
visible. Do not weaken a gate or substitute cheaper incomplete work for acceptance.

For an authorized regression fix, demonstrate the intended assertion failing
(not a setup error), make the minimal fix, then show it passing and recheck affected
dependencies. Take one behavior slice through this cycle before the next.
Do not rewrite working code to manufacture test-first history. Review-only work
reports gaps without changing tests or implementation.

## Diagnosis

Establish expected/actual behavior and environment. Use the smallest safe existing
test or permitted boundary repro that exposes the user's symptom. Clear local
defects need no theory ceremony. For uncertain/cross-component failures, compare
falsifiable hypotheses, change one relevant variable, and record what the evidence
settles. Baseline performance before optimizing; no unauthorized stress or mutating
replay. Redact secrets.

When execution is unavailable or forbidden, distinguish static evidence and
tentative hypotheses from a reproduced failure; state the missing evidence.
Continue safe investigation without requiring a new interpreter/harness.
After an authorized fix, verify the original symptom, not merely a nearby check.
Remove only temporary instrumentation you introduced; preserve user artifacts.
