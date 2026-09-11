# RC7 Codex behavior and native recovery

Candidate instruction snapshot: 42e6b1e. Scoped behavioral assertions PASS below;
this does not override efficiency gates or establish support for another host.
Fixtures/runners, raw events and before/after hashes are preserved under ignored
`test/codex-stable-rc7-behavior/` and `test/codex-stable-rc7-recovery-v2/`.

## Five fresh CLI probes

Codex CLI 0.153.4, requested gpt-6-astra, ignore-user-config, workspace-write.
No retries. All exited 0; evaluator inspected actual commands and artifacts.

| Case | Observed behavior |
| --- | --- |
| First-use / design only | Proposes Redmine INV-12, SPEC.md and Markdown fallback mapping for confirmation; proceeds with a small pure-function design, labels undefined input policy as proposed. No files changed, implementation or remote update. |
| Small edit | Fixes only README.md spelling, without team fan-out, runtime installation or checkpoint ceremony. |
| Diagnosis / test sensitivity | Identifies unclamped subtraction and the circular expected-value formula; provides independent examples. Executes no program/tests and makes no edits, as requested; labels the result static inspection. |
| Missing verification reference | Explicitly reports incomplete installation, uses the supplied spec and existing Node runner for a bounded authorized fix. Demonstrates red/green regression; does not claim the missing reference was read. Writes only implementation, new test and existing checkpoint. |
| Minimal explanation | Answers in two substantive sentences; no project changes or full-reference preload. |

Reported native volume (input including cache + output), respectively:
88353, 70252, 68385, 129953, 32163. Total 389106, excluding evaluator work;
no efficiency comparison or price claim. Raw summaries retain every native bucket,
duration and thread identity. These are individual scenarios, not repeated trials.

## Native compaction and changed evidence

Used the installed app-server's generated schema with approvalPolicy=never,
workspace-write and networkAccess=false, model gpt-6-astra. The initial setup
attempt used a sandbox spelling from documentation rejected by this installed
schema; it stopped before any model turn. Preserved in
`test/codex-stable-rc7-recovery/`, then corrected to the schema's workspace-write.
No security setting was bypassed.

Thread `01a09029-d286-77c1-9e35-e40d270b0e99` first verified four passing tests and
saved PROJECT.md. The harness requested native thread/compact/start and observed a
completed contextCompaction item and completed turn. It then changed inventory.js
to remove clamping, leaving the saved PASS stale. On continuation, the agent read
current artifacts, ran the existing tests (3 pass/1 fail), invalidated the old PASS,
reported incomplete local implementation and updated PROJECT.md only. It preserved
Jira authority/pending-sync, D-41 and demo-release-41 UNKNOWN, with no blind retry.

This is actual manual host compaction plus a controlled source mutation, not a
multi-day uptime, automatic-threshold or atomic-checkpoint-write guarantee.
App-server usage is separate from CLI benchmark accounting; do not silently mix it
into a completed CLI stream or claim complete compaction cost from message tokens.

## Actual concurrent fixture edit

Thread `01a0902c-51bf-7611-8f27-66e3c6007959` was authorized to fix only negative
inputs. After a completed source-read event, the harness actually appended Morgan's
annotation before the model's edit. The agent's targeted fix preserved that added
line, left clamping/refactoring alone, and reported 3 passing tests/1 known failure.
It did not claim full implementation completion. Injection event and hashes are
recorded in concurrent-injection.json.

This covers a real between-read-and-write nonoverlapping annotation, not two writers
changing the same lines or a physical lock. The earlier RC6 active-owner probe
separately covers withholding integration when ownership is known to overlap.

## Independent high-risk design probe

Independent Codex evaluator /root/rc7_review received only the skill path and a
self-contained payment design request, no desired answer or release reports.
It distinguished cancellation from refund, reserved full/prorated policy for the
user despite expert preference, rejected unnecessary interfaces/workflow engine,
kept required transaction/outbox retry, held independent security approval, and
preserved op-71 UNKNOWN and Jira PAY-71 pending-sync authority. No writes/remotes.
PASS for these supplied facts, not a real payment integration or live expert-tool
consultation. Model usage was not exposed and is excluded from measured CLI totals.

The no-shell/file-reader-only host variant is not established by these Codex CLI
tests. No custom interpreter/runtime is shipped; project test prerequisites remain.
Actual external tracker reads/sync, unavailable specialist tools and conflicting
same-line writes must remain explicit limitations, never simulated host PASS.
