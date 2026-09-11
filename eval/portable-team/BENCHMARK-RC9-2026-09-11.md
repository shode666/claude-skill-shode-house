# RC9 Codex matched qualification — FAIL

Frozen instruction source e8f31da; all 18 fresh invocations completed without
timeouts or retries. Three independent trials per arm per scenario, following
CODEX-STABLE-PROTOCOL.md without changing controls, prompts or thresholds.
Review baseline fe639c0; two-session resume baseline fd620f0. Results are not
pooled with RC7/RC8. Raw streams, frozen hashes, per-phase artifacts, evaluator
results and normalized records: ignored `test/codex-stable-rc9-benchmark/`.

Codex CLI 0.153.4, actual native model gpt-6-astra, effort null, approval never,
ignore-user-config. Review is read-only; implementation uses workspace-write with
network disabled. Each resume trial sums two fresh sessions once. Native thread
identity and rollout settings are checked before completed-stream normalization.

| Scenario / metric | Baseline trials | Candidate trials | Median delta | p90 delta | Gate |
| --- | --- | --- | ---: | ---: | --- |
| Review total volume | 89952 / 107408 / 108315 | 87870 / 87829 / 87204 | -18.23% | -18.88% | PASS |
| Review uncached + output | 9056 / 8976 / 9243 | 13502 / 13589 / 8228 | +49.09% | +47.02% | FAIL |
| Resume total volume | 262502 / 260711 / 259071 | 250265 / 229109 / 248926 | -4.52% | -4.66% | PASS |
| Resume uncached + output | 28774 / 28391 / 40703 | 29721 / 34805 / 31710 | +10.20% | -14.49% | FAIL |

Both metrics must meet median <= +3% and sample p90 <= +5% (max for n=3).
Thus combined efficiency qualification FAILS despite lower total volume in both
scenarios. Cache variation matters; neither this small batch nor the effective
metric establishes monetary savings. No selective retries or larger batch is
authorized by a favorable subset of these results.

Review wall median -12.65%, p90 -21.23%; resume median -7.78%, p90 +10.61%.
Concurrent probes and host load prevent treating these as controlled latency
effects. Benchmark observed volume **2079162**, including cache, excluding
evaluators and separate recovery probes.

Scoped behavioral checks pass: review finds negative-input, clamping and unnecessary
abstraction issues without edits. Each first implementation session changes only
inventory.js and PROJECT.md and stops with 3 tests passing/1 clamping failure;
each resumed session completes with 4/4, independently evaluated. Spec and test
files remain unchanged. Jira DEMO-31 authority/pending sync, unresolved D-31 and
demo-release-31 UNKNOWN remain explicit; no release replay is claimed.

Current-source first-use, bounded-edit, missing-reference, diagnosis, high-risk
exclusion, actual manual compaction/stale-PASS and same-line concurrent annotation
checks are documented separately in BEHAVIOR-RC9-2026-09-11.md, with their limits.
They do not waive this token gate. Codex is the sole qualification target;
Claude Code, Cursor and Antigravity remain experimental/unverified.

RC7/RC8/RC9 matched batches consumed 6251066 observed CLI token volume; separate
RC7/RC9 behavioral CLI probes add 758784, for **7009850** across those measured
sets. This excludes native app-server recovery, independent evaluators and other
work, so it is not complete task-wide accounting. Further large trials need a
concrete new hypothesis and an explicit budget/scope decision, not repeated
sampling until green. Keep RC status unless the user explicitly accepts a release
exception; record any exception as a waiver, never a passed gate.
