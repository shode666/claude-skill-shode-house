# RC7 Codex matched qualification — FAIL

Completed all 18 invocations from CODEX-STABLE-PROTOCOL.md: three independent
review trials and three independent two-session workflow trials per arm. No
retries, timeouts or out-of-scope file changes. Source candidate 42e6b1e; controls
fe639c0 for review and fd620f0 for resume. Never pool those different scenarios.

Codex CLI 0.153.4, gpt-6-astra, actual rollout effort null, approval never;
read-only for review and workspace-write/network false for resume, ignore-user-config.
Frozen inputs, exact source/fixture hashes, streams, summaries, phase snapshots,
independent test results and normalized usage live under ignored
`test/codex-stable-rc7-benchmark/`. Each fresh invocation has a distinct native
thread identity; the two resume invocations share one trial ID. Native rollout
settings are checked before normalization with scripts/usage-from-codex.py.

| Scenario / metric | Baseline trials | Candidate trials | Median delta | p90 delta | Gate |
| --- | --- | --- | ---: | ---: | --- |
| Review total volume | 108569 / 69773 / 88446 | 89521 / 89170 / 108314 | +1.22% | -0.23% | PASS |
| Review uncached + output | 9497 / 12429 / 8830 | 9521 / 13266 / 9498 | +0.25% | +6.73% | FAIL |
| Resume total volume | 240665 / 239258 / 239361 | 257091 / 281002 / 259113 | +8.25% | +16.76% | FAIL |
| Resume uncached + output | 27673 / 29978 / 31617 | 34883 / 34346 / 27433 | +14.57% | +10.33% | FAIL |

Both token metrics must satisfy median +3% and sample p90 +5%; for three trials,
p90 is the maximum by the existing convention. Review wall median +19.79%,
resume wall median +7.52%. Wall time includes local invocation startup/tools;
concurrent qualification probes and host load are not controlled latency claims.
Total benchmark volume **2070283**, including cache, excluding evaluator work.

Quality assertions PASS: all reviews identify negative-input rejection, clamping
and unnecessary strategy infrastructure without edits or duplicate axis findings.
All first implementation sessions fix only negative rejection and stop with
3 tests passing/1 clamping failure; all fresh continuations fix clamping and pass
4/4. Independent evaluator tests agree. Specs/tests remain immutable, interface
and unrelated classes are preserved under the no-refactor scope. All handoffs
retain Jira pending-sync authority, D-31 and demo-release-31 UNKNOWN without replay.
Local completion is distinguished from remote synchronization/deployment.

The checkpoint-size improvement is real but not enough: first baseline chain ends
at 6552 bytes versus candidate 3545 bytes, yet candidate workflow usage is higher.
Do not infer token savings from this byte reduction. Traces still show separate
inventories, guidance reads and repeated probes; cache ratios also vary materially.
RC8's separately declared verification correction does not erase this failure.
