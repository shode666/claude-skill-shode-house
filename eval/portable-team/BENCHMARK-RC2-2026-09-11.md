# Codex inventory-review benchmark — RC2

**Quality PASS; continuity-loading correction observed; combined efficiency gate
FAIL.** All six additionally authorized trials completed, none discarded or rerun.
No further live trials were started. This is not stable-release acceptance.

## Controlled inputs

Fresh baseline `fe639c0` (the portable pre-ask skill, not the full legacy plugin)
versus RC2 `0ea7904`, three independent sessions each, alternating baseline/candidate.
Same fixture, prompt and procedure as [RC1](BENCHMARK-2026-09-11.md). Codex CLI
0.153.4; actual rollout metadata reports gpt-6-astra in all six runs, unset effort,
approval policy never, read-only sandbox and ignore-user-config. These settings
match across all six records. No model override or cache reset; cache warmth,
run ordering and model/tool scheduling variability remain limitations.

Source/fixture fingerprints use the path-to-file-SHA256 map method documented in
the RC1 report. Baseline source and fixture hashes match that report. RC2 source:
`50569f806ffb7d3a66080b5d5e11fb28d24f2d4c296db72738f203db1a30e98e`.
Raw streams, stderr, snapshots, normalized usage and copied evaluation scripts live
under ignored `test/benchmark-rc2-2026-09-11/`. Execution used isolated temporary
workspaces; no test data, logs or evaluation scripts ship in the plugin.

Collector SHA256: `d7c1085db3bd196d4121a2bd4fa44fc7db32e1f2542783d5842264332da64e38`.
Comparator SHA256: `f3c0a4512045e6aba6cd2a8895e1de255e19d949df949aabb0ad0bce04d12002`
(pre-existing working-tree comparator, unchanged by these trials).
Runner SHA256: `d43bf342a4a4b6263855159dca0ebce985634998e6a9090b48c9313eb236e343`.

## Results

| Trial | Uncached input | Cache read | Output | Total volume | Wall seconds |
|---|---:|---:|---:|---:|---:|
| Baseline 1 | 7,700 | 61,824 | 655 | 70,179 | 32.647 |
| Baseline 2 | 8,345 | 98,560 | 781 | 107,686 | 46.824 |
| Baseline 3 | 14,680 | 92,672 | 693 | 108,045 | 54.770 |
| RC2 1 | 8,783 | 81,664 | 677 | 91,124 | 48.158 |
| RC2 2 | 8,061 | 61,952 | 759 | 70,772 | 37.555 |
| RC2 3 | 9,014 | 100,736 | 633 | 110,383 | 39.056 |

Native input includes cached input. The normalized uncached and cache-read columns
are disjoint; cache writes were zero. Reasoning is not added to output again.
All-six volume: 558,189 tokens; sum of sequential invocation wall time: 259.010s.

`usage-report.py --compare` exited 1 against unchanged median +3% / p90 +5% gates:

- Total-volume median: 107,686 → 91,124 (**−15.4%**); p90: 108,045 → 110,383
  (**+2.2%**). This metric passes.
- Legacy uncached-input-plus-output median: 9,126 → 9,460 (**+3.7%**, FAIL);
  p90: 15,373 → 9,647 (**−37.2%**). This is not monetary cost.
- Median wall time: 46.824 → 39.056s (**−16.6%**), descriptive only.

With three samples, the comparator's p90 is the sample maximum. The unchanged
baseline itself had a 70,098 median volume in the RC1 batch versus 107,686 here:
variation is substantial. Do not advertise the observed −15.4% as a general or
causally established plugin saving. Do not pool historical trials post hoc to
obtain a passing score, discard expensive runs or relax the gate.

## Behavior and trace audit

Every trial found both seeded correctness defects (negative inputs and missing
clamping), and the unnecessary registry/strategy abstraction. Each ran the existing
four tests and accurately reported two passes/two failures. All input file hashes
remained unchanged. Completed item types were only local command executions and
agent messages; inspected commands showed no external project operation or
delegation. The main-only normalized records plus that inspection account for this
no-subagent scenario, not arbitrary whole-team workloads.

All three RC2 trials omitted continuity.md while reading the required review and
verification references. This confirms the targeted confirmed-mapping optimization
for this scenario. First-use confirmation, checkpoint resume, unknown external
outcomes and high-risk specialist behavior were NOT exercised by this batch.
Do not transfer earlier RC1 smoke evidence as proof of those RC2 behaviors.

Command counts were 5/8/7 baseline and 10/7/10 RC2. Some reads were separate command
items; item counts are not model round-trip counts. The prompt change did not
establish consistently lower tool overhead. Further optimization needs a specific
evidence-backed mechanism, not another rule or repeated runs until one passes.

## Raw-stream identities

| Trial | Thread ID | Raw SHA256 |
|---|---|---|
| Baseline 1 | 01a08f3d-dd27-7460-88d8-41017c23d651 | 8dad8f2ccf76e8e0c69efc905d7cbaf88ed24b0c981f7a4cc73b65cca8dea2c6 |
| Baseline 2 | 01a08f3f-191b-7e42-86b2-5b15bdf8d7eb | ede0bf0a19cdf05c3c48a8a2c4cfb483ac6c7017f9ef76d00aa3d4ea377bd88d |
| Baseline 3 | 01a08f40-6332-76d3-8324-76ae80c8950a | 30a1482b13a033a093fb0e13542abfeac4fbbf7fcfb0d487bc1b7d0860f372da |
| RC2 1 | 01a08f3e-5cbf-7741-9b89-4eb085b71167 | 41767aaad458421d936483216c77ffd92e75c51090f467bd51d35aa396653a6a |
| RC2 2 | 01a08f3f-d022-72f1-8802-2a82bb25a55f | 718ec862d5f484dc96101e0b032620ea56f3ade42aaacd48d0891aa6547e8be7 |
| RC2 3 | 01a08f41-393b-7d23-8599-d765f46da27e | ac48b0dc8bfdb4f5ba9277ae705a8cd389c0f21ee89ec8dba4d9fd4bd92896a6 |
