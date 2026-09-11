# Current-checkpoint evaluation protocol

Status: predeclared before execution; completed results in GROWTH-RC3-2026-09-11.md
and the evidence-driven RC4 retest in GROWTH-RC4-2026-09-11.md. Criteria below were
not changed after results. Beads `shode-house-5cs.11.6`.

## Targeted experiment

Compare frozen RC2 at `fd620f0` with the RC3 continuity-only change, recording
the exact source hashes and commit before execution. Use the same model/host,
settings and initial synthetic fixture for both arms. No network task actions,
delegation, installs or commits inside test workspaces. Keep raw evidence ignored
under `/test/`; do not change runtime dependencies to support this experiment.

Two isolated chains, baseline and candidate, three fresh sessions each (six CLI
invocations total), interleaved B1/C1/B2/C2/B3/C3. Each session receives the previous
disk state of its own arm, never prior chat. This is a longitudinal growth probe,
not three independent trials per arm. Do not apply independent-run median/p90 gates
to these dependent sessions or pool them with earlier benchmarks.

Start with identical inventory code/tests/spec and a synthetic project record
containing a confirmed source mapping, current authorized scope, historical test
evidence, an unresolved decision and a timed-out external operation with its ID.
Authorize edits only to PROJECT.md and a designated history directory; preserve
code/tests/spec/skills. Existing history is retained, not expendable test clutter.
The remote tracker remains canonical and unavailable; fallback stays pending-sync.

Every session prompt requests a current local assessment and durable handoff under
the existing scope, with no new implementation or external authority. The scenario
remains unchanged: repeated turns must not invent progress or inflate records with
new snapshots merely because another session occurred. Freeze exact prompt and
fixture hashes before either arm runs; no per-arm coaching about expected output.

## Acceptance and measurements

Quality must pass in every session: source mapping/remote authority and pending-sync
survive; UNKNOWN operation ID and no-blind-retry constraint survive; unresolved
decision and scope remain explicit; current verification is accurate; no unauthorized
edits/actions. Any removed historical evidence must remain accessible through a
verified durable link. Inspect actual tool calls and resulting artifacts, not wording
matches. A shorter record that loses information is FAIL.

Measure current-record bytes separately from retained history bytes, files read,
whether history was loaded, uncached/cached input, output, total token volume and
elapsed time. Missing usage is unavailable, never zero. Include preservation/archive
overhead in the chain cost. Do not equate fewer bytes with fewer billed tokens.

The candidate must end with a smaller current record than baseline, and must not
append duplicate full snapshots on unchanged sessions 2/3. Report exact trajectories
and total costs even if worse; no reruns until green or post-result threshold changes.
This experiment tests context-growth behavior only. Existing efficiency thresholds
(median +3%, p90 +5% maximum regression, both tracked token metrics) remain unchanged
for a later matched, independently repeated whole-workflow evaluation.

## Cost and limits

Six live sessions may consume roughly 0.7–1.0 million total tokens including cache,
based on recent 90–140k-token sessions; this is an estimate, not a spending cap or
price quote. Request approval before starting this substantial batch. Run once,
with a per-process timeout and no automatic retries. If an arm fails or permission
is missing, preserve evidence and mark affected comparisons incomplete.

Even a passing probe does not establish unbounded long-run behavior, cross-host
compatibility, crash safety during archive writes or general token savings.
