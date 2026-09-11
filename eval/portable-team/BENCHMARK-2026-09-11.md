# Codex inventory-review benchmark — RC1

Result: **quality PASS; token-volume regression FAIL**. Six authorized invocations
completed; none omitted or rerun. This is a single read-only review scenario, not
long-run recovery or four-host acceptance. RC2 edits made afterward require new
forward tests; the results below apply only to RC1.

## Method and provenance

- Baseline: portable shode-house-team at `fe639c0`, NOT the full legacy 3.15 plugin.
- Candidate: ask RC1 at `9b8eb72`; source files unchanged during the trials.
- Codex CLI 0.153.4; observed `gpt-6-astra` in all six rollout turn contexts;
  effort unset, approval policy never, read-only sandbox, ignore-user-config.
  Model was not overridden. No delegation or remote-service commands observed.
- Synthetic inventory function, SPEC.md, four Node tests and confirmed Markdown
  mapping. Fixtures identical between all trials; working directories isolated
  outside the repository to avoid its Beads/legacy instruction inheritance.
- Three fresh independent sessions per variant, alternating baseline/candidate.
  No cache reset; warm-cache and ordering effects remain a limitation. Sample
  size is small: the repository's p90 estimator equals the maximum for three runs.
- Raw stdout/stderr, snapshots, summaries and normalized usage are retained under
  ignored `test/benchmark-2026-09-11/`. They are local evidence, not shipped files.
  Input includes cache reads in native Codex usage; normalized input subtracts
  them before aggregation. Output includes reasoning; no extra reasoning sum.
- Fixture fingerprint: `46fe786a1616b31ea726f834f4e9808377dae5c1365c9e1a94dccff9d4638e45`.
  Baseline source fingerprint: `dee04ff19e706aa824c7f8f1a47f709cce291203ff2cf7b269a1e31cd98d65bf`.
  RC1 source fingerprint: `611f1792c131b3bfaf8291cccd17228fca3f68241ccd46dde1c0c3fb7efe7a76`.
  Fingerprints hash sorted compact JSON maps of relative file paths to SHA256;
  source maps contain .agents files, fixture maps contain the remaining inputs.

## Observations

All six reviews found negative-input acceptance, missing zero clamping and the
unnecessary registry/strategy infrastructure. Every trial ran the existing tests,
correctly reported two passes/two failures, and kept input files unchanged. Findings
were not duplicated by review axis. No false PASS, edits, delegation or external
project operations were observed. This proves these cases, not general reliability.

| Trial | Uncached input | Cache read | Output | Total volume | Wall seconds |
|---|---:|---:|---:|---:|---:|
| Baseline 1 | 18,241 | 70,272 | 683 | 89,196 | 39.758 |
| Baseline 2 | 11,731 | 57,728 | 639 | 70,098 | 37.322 |
| Baseline 3 | 10,760 | 58,624 | 665 | 70,049 | 35.370 |
| RC1 1 | 8,959 | 62,720 | 629 | 72,308 | 41.723 |
| RC1 2 | 8,703 | 62,592 | 744 | 72,039 | 36.212 |
| RC1 3 | 9,544 | 101,632 | 696 | 111,872 | 46.112 |

`usage-report.py --compare` returned exit 1 with the configured unchanged gate
(median +3%, p90 +5%). Median total volume rose **3.2%**, sample p90 **25.4%**.
Median uncached-input-plus-output fell **22.5%**, but that is neither full token
volume nor a monetary-cost calculation. Median wall time rose from 37.322 to
41.723 seconds (11.8%). Do not present the cache-excluding improvement as overall
token savings. Total six-run token volume: 485,562; measured execution time: 236.497s.

## Trace findings and response

Every RC1 trial loaded continuity.md despite an already-confirmed mapping and a
standalone review. Baseline loaded only design-review and verification guidance.
Repeated directory listings and extra read rounds occurred; command counts were
6/5/5 in baseline and 6/7/7 in RC1. These are observed overhead opportunities, not
a controlled attribution of all token variance to one cause. Extra negative-input
probes in baseline 3 and RC1 2 also had a legitimate evidentiary purpose.

RC2 narrows continuity loading to missing/conflicting mappings, checkpoint resume
or durable handoff, preserving first-use confirmation. It encourages reuse of known
file inventories and batching independent reads, without skipping required rules
or changed evidence. Static package/link checks pass; no measured RC2 efficiency
or behavioral claim is made before a fresh test. The optional skill quick validator
could not run because PyYAML was missing; Ruby YAML parsing and package checks pass.

## Raw-stream identities

| Trial | Thread ID | Raw SHA256 |
|---|---|---|
| Baseline 1 | 01a08f34-49cc-7ee3-8103-bb69f1e7d743 | 9b830a4e255c533dfe35f3ae2f674a019b467c0a99bc2f6e912bbb9a7f76b69a |
| Baseline 2 | 01a08f35-888f-70c2-922d-25cb387eb77b | eae02f1f657bf1c9f4fb5b61ebde94470bf649aac9554eb10dff249b6f960389 |
| Baseline 3 | 01a08f36-a846-7c50-9754-2064c6b10f2b | 60cffa0a636bc48535718cabe7aa8576f5148e91efe21e604b6ab588ec8e2ac5 |
| RC1 1 | 01a08f34-e534-7cc1-9b6c-555518e488fc | 565357ab337f38ad4c8f8cc36a79c6fda946fff237e1bdaf0618ecc473267f45 |
| RC1 2 | 01a08f36-1a72-7bb2-882b-aef9e1d4efba | 5b78d79354b0466db6e138888ecefdf411e0409a4db216dedd4597ae56acec65 |
| RC1 3 | 01a08f37-3289-7e11-a4b0-72efe44f5ed1 | 7a93ec2d6f67daf07b4e9d3c703cbc35144f1a11496d1a79673886ad9c5b35d0 |
