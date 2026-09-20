# Delivery benchmark — 2026-09-15

Status: **IN PROGRESS — authorized online batch running**. Not a release
qualification or proof of lower whole-team token use.

## Requested five checks

| Check | Result |
|---|---|
| Real backend/UI/auth-payment delivery | Backend candidate pilot produced implementation and 23 passing Node tests. UI/payment not run. Independent acceptance incomplete. |
| Conditional reference loading | Entry, harness, engineering loop, role and prerequisite reads observed. Full-diagnosis versus fast-path probe not run. |
| Long-run interruption/resume | Pilot interrupted while waiting; no controlled recovery qualification yet. |
| Matched repeated baseline/candidate | Twelve-run design prepared: three scenarios, two variants, two repetitions. Batch not launched. |
| Repair regressions and retest | No plugin change justified by this incomplete pilot. Release remains unqualified. |

## Backend pilot

Codex CLI: 0.154.0-alpha.6.2, workspace-write, ephemeral, ignore-user-config,
default model selection (actual model identity not exposed in captured events).
Source snapshots are separate from the installed plugin; the working tree was not
checked out or reset. Fixture uses confirmed Markdown records and no remote service.
Task: reject nonnegative-safe-integer violations and clamp available inventory at zero.

The pilot loaded the candidate ask entry, harness, implementation/review roles and
prerequisites. PROJECT.md records Dave assignment and planned Chris review. Captured
collaboration events show waits but do not establish completed independent review;
role names in the checkpoint alone are not proof. Implementation and red/green test
logs were produced. Independent local rerun after interruption: **23/23 tests pass**.
No Chris verdict or final integrated acceptance was available in the captured snapshot.

The operator interrupted the pilot after repeated wait events; CLI exited 1 without
a completed-turn usage record. This is an **interrupted run**, not a demonstrated
plugin deadlock. Input/output/whole-team token totals and final delivery time are
unknown; do not treat missing usage as zero or calculate a saving from it.

Raw partial trace, fixture and evidence are retained locally under
`test/delivery-pilot-2026-09-15/` (gitignored). No credentials were intentionally
read or included. Logs may contain the plugin instructions and should remain local.

## Authorization history

Automatic approval rejected the proposed 12-session batch because it sends the
unpublished plugin source/instructions and dummy-project content to the external
OpenAI/Codex model service. The initial single pilot had separate approval. No
alternative route was used to bypass the batch rejection. After the explicit
source-transfer/quota question, the user directed testing to completion; the
subsequent approval accepted the scoped batch. No credentials or real service
operations are included.

The batch design holds fixture, tool permissions and invocation settings constant,
alternates variant order, and records source hashes, durations, results and usage.
Two repetitions are only a pilot; they cannot establish reliable p90 or universal
non-inferiority. Worker usage must be included or whole-team comparison marked unknown.

No commit, push, installation or release was performed. Existing 210 Python and
three Node regression passes from the preceding audit do not replace these live checks.
