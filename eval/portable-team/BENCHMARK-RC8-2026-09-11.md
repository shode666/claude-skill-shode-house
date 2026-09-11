# RC8 Codex matched qualification — FAIL

Completed 18 fresh invocations, three independent review trials and three
independent two-session workflow trials per arm. Same frozen prompts, fixtures,
controls, settings and gates as CODEX-STABLE-PROTOCOL.md; RC8 source 72384f4.
No retries, timeouts or out-of-scope edits. This is not a sample extension or pool
with RC7. Raw evidence and normalized records: ignored
`test/codex-stable-rc8-benchmark/`, including frozen source/fixture hashes.

Actual native rollout settings: Codex CLI 0.153.4, gpt-6-astra, effort null,
approval never, ignore-user-config; read-only review, workspace-write/network false
implementation. The two sessions of each resume trial are summed once under one
run ID. Evaluator work is separate. Native identity/settings and completion are
checked by the analyzer before using the completed-stream Codex collector.

| Scenario / metric | Baseline trials | Candidate trials | Median delta | p90 delta | Gate |
| --- | --- | --- | ---: | ---: | --- |
| Review total volume | 91156 / 107922 / 69912 | 107247 / 106715 / 106952 | +17.33% | -0.63% | FAIL |
| Review uncached + output | 13844 / 15122 / 14232 | 9071 / 14811 / 8904 | -36.26% | -2.06% | PASS |
| Resume total volume | 261338 / 239752 / 240921 | 256803 / 256674 / 256229 | +6.54% | -1.74% | FAIL |
| Resume uncached + output | 36570 / 31880 / 32537 | 34595 / 36514 / 35173 | +8.10% | -0.15% | FAIL |

Thresholds unchanged: each metric median <= +3%, sample p90 <= +5% (max for n=3).
Review wall median -2.25%, resume wall median +0.49%; concurrent probes/host load
are not controlled latency effects. Total benchmark volume **2101621**, including
cache, excluding evaluator and separate recovery probes. Not a monetary cost.

All review findings and immutable-file assertions pass. All first sessions stop
after negative rejection with 3 tests passing/1 clamping failure; all second
sessions complete clamping with 4/4, confirmed by independent evaluator tests.
No interface/refactor expansion or spec/test changes. Checkpoints preserve Jira
pending-sync authority, D-31 and demo-release-31 UNKNOWN; no external replay,
delegation, installation or Git mutation was observed.

Separate actual native compaction/stale-source and concurrent trailing-annotation
probes also pass on this snapshot under `test/codex-stable-rc8-recovery/`, following
the same method and limitations as BEHAVIOR-RC7-2026-09-11.md. They are behavioral
evidence, not completed-stream compaction-cost measurements. CLI and app-server
usage are not mixed. RC9 changes routing after these observed extra guidance/read
rounds; its future results cannot retroactively convert RC8 into PASS.
