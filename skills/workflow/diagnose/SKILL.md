---
name: diagnose
description: |
  [WHAT] Investigate a concrete bug or performance regression and report cause, evidence and uncertainty.
  [WHEN] Root-cause investigation is requested or needed within an authorized bug fix; not general review or feature discovery.
  [TRIGGER] /shode-house:diagnose, "diagnose", "debug this failure", "หาสาเหตุ".
---

# Diagnose (structured debugging)

## Intent and authority

Diagnosis explains a failure; it does not authorize a fix. Review of existing code
belongs to `review-checklist`; a known cause does not need a repeated diagnosis.
For diagnosis-only requests, use safe inspection and non-mutating checks, then return
the cause, confidence, evidence and proposed next action. Do not edit application
code, post externally, commit or expand to similar bugs without authorization.
Pass this boundary to delegates. An authorized fix may continue through Step 4.

## When NOT to use

General code review uses `review-checklist`. Feature discovery is not diagnosis.
Reuse a known cause instead of repeating investigation; fixing it still needs authority.

## Required inputs

A concrete symptom and relevant code, logs or access to investigate it. Missing
runtime access limits confidence, not safe inspection. State expected/actual behavior
and any evidence still needed; do not demand a tracker or new test framework.

## Redact ก่อน paste

Redact secrets, auth headers and private data before sharing commands, logs or traces.
Quote only decisive excerpts. If redaction removes necessary evidence, request a safe
artifact rather than exposing sensitive content.

## 1. Establish the symptom and feedback loop

Identify expected versus actual behavior and the relevant environment. Read code
and logs to find a safe way to exercise the failure. Prefer existing project tools:
1. Existing test at the relevant public boundary.
2. Safe API request against an isolated test environment.
3. CLI invocation with a fixture.

If these are insufficient and further reproduction is useful and permitted, read
`loop-ladder.md` for alternatives. Do not install a runtime or build a harness
merely to satisfy this skill. Never replay live payment/deployment requests as tests.

A useful loop asserts the user's exact symptom and can fail on this bug, not merely
"did not crash". Capture the invocation, decisive output and environment.
For intermittent failures, record observed frequency and conditions; do not require
arbitrary trial counts or authorize production stress by implication.

If reproduction is unavailable, continue safe code/log analysis as explicitly
tentative hypotheses. Report the missing evidence or access. Do not claim a
confirmed runtime cause, successful reproduction or verified fix from inspection alone.

## 2. Reproduce and isolate

Check that observed failure matches the reported symptom. For complex failures,
reduce inputs, callers or setup one element at a time while retaining the failure.
For a clear local error, skip unnecessary minimization and competing-theory ceremony.
Optimize feedback time by narrowing scope without removing the relevant interaction.

## 3. Test hypotheses

Use evidence-ranked, falsifiable hypotheses: what observation would support or
reject each? Probe one meaningful variable at a time, within authorized scope.
Do not repeat failed probes without new evidence. Prefer existing debugger/logs;
temporary instrumentation requires permission to modify that environment.
Performance diagnosis needs an appropriate measured baseline, not guessed timings.

Diagnosis-only completion: return findings and limits here. Recommend follow-up
without executing it; report storage/posting follows active project authority.

## 4. Fix and regression test (only when authorized)

Use `dev-gate` for implementation/test discipline; do not run a second test pipeline
for the same evidence. Choose a boundary that actually exercises the failure pattern.
Demonstrate the intended failing assertion before the fix and passing result after;
also rerun the original scenario. Expected values must be independent of the code's
formula. If no appropriate regression check is possible, explain the coverage gap
and do not label the fix fully verified.

Prefer the smallest correct change within scope. Similar bugs discovered elsewhere
are findings, not automatic permission to fix every occurrence.

## 5. Cleanup and handoff

Remove only temporary instrumentation/artifacts you introduced and are authorized
to remove; preserve user files. Report commands/results, hypothesis outcome and
remaining gaps. Diagnosis completion is not fix completion. Commit/PR publication
and incident postmortems follow the user's request and active project workflow.

## Skill composition (where to go next)

| Situation | Next skill | Boundary |
|---|---|---|
| Active production incident | `incident` | Mitigation/communications within authorized incident scope |
| Authorized code fix | `dev-gate` | Owns implementation tests and quality checks |
| Project-wide CI/test strategy gap | `automate-test` | Not required for a single regression test |
| UI interaction failure | `ui-test` | Applicable interaction evidence, not every UI checklist |
| Security issue | `secure` | Relevant threat review; no implicit remediation authority |
