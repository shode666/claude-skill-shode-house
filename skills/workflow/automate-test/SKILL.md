---
name: automate-test
description: |
  [WHAT] Design or update project-wide test strategy and CI gates from risks, existing checks and measured feedback cost.
  [WHEN] CI/test-system setup or a demonstrated cross-project test gap is in scope; not writing one feature or regression test.
  [TRIGGER] /shode-house:automate-test, "CI test strategy", "configure test gates", "test suite reliability".
---

# Automate Test (project-wide CI strategy)

Owner: QA identifies coverage/risk; operations wires authorized CI changes.
`dev-gate` owns per-change test quality and implementation checks. Do not copy its
test cycle or rerun it as a second pipeline. A strategy/report request does not
authorize editing CI, branch protection, secrets, deployments or external services.

## When NOT to use

A single feature/regression test belongs to `dev-gate`. No project-wide setup is
required just because a small utility has no CI. Missing baseline is a reason to
inspect, not refuse: report what can and cannot be measured.
Migration and incident work retain their specific safety/verification requirements.

## Required inputs

Inspect the actual stack, existing scripts/config, CI provider if any, important
interfaces/journeys and available test fixtures. Establish current failures,
coverage gaps, suite duration and flakiness where tools permit. Do not invent numbers.
Ask only unresolved choices that materially change cost, authority or scope.

## Test strategy and thresholds

Map risks to the cheapest reliable check that can expose them. Use unit tests for
isolated policy, integration/contract tests for real boundaries, and E2E for relevant
user journeys. No mandatory 70/20/10 ratio or universal coverage percentage.
Coverage is a gap signal, not proof of test sensitivity. Preserve existing required
thresholds; proposals to change them need explicit rationale and owner approval,
not a quiet relaxation to make the current change pass.

Use existing framework/provider first. Add test services, contract infrastructure,
load or mutation testing only for a demonstrated gap worth their cost. Separate
fast feedback from slower relevant suites; avoid running the same check repeatedly
under different job names. Keep necessary security and release checks blocking.

## CI wiring (only when authorized)

Map agreed checks to existing commands and provider syntax. Inspect current workflow
dependencies, permissions and secret handling; do not copy illustrative YAML blindly.
Validate configuration and run affected checks where possible. A local PASS does not
prove a hosted job ran; report that separately.

CI setup does not authorize staging/production deployment, branch protection changes,
secret provisioning or scheduled load/chaos experiments. Keep those as separate
explicitly authorized operations. Do not turn every optional diagnostic into a required
merge check without an agreed operational need.

For optional local hook setup using the project's chosen pre-commit manager, read
`skills/workflow/dev-gate/pre-commit-config.md`. Do not install a hook manager by default.

## Flaky Test Discipline

Record the actual failure and its frequency/environment when available. A later
passing retry does not erase the first failure. Do not retry indefinitely, silently
skip tests or quarantine a required check to claim green. If quarantine is approved,
retain the failure evidence, owner, restoration condition and coverage gap in the
project's designated tracker. Fix the cause rather than treating retries as correctness.

## Hand-off

Return risk/check mapping, changed CI artifacts if authorized, measured before/after
results and unverified hosted behavior. Link existing task/spec/evidence sources;
do not create a second tracker. Missing tools or credentials mean a specific limitation,
not permission to install infrastructure or claim CI success.
