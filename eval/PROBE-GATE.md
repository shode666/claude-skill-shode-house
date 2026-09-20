# Routing-probe comparison rule and gate (v3.17) — fixed BEFORE any N=5 data exists

Author: Chris (independent validator), 2026-09-20. Roles: Quinn builds/operates the run, Chris validates from raw
traces, Oliver does not judge. Held-out set lives outside git (`outputs/heldout-3.17/`); only its hashes
(`eval/heldout-3.17.SHA256SUMS`) and `AGG.tsv` are ever committed. Description authors must not open it, nor P28+.

1. Valid arms: same freeze manifest sha, model_id, CLI version, init hashes (plugin hash excepted); the after arm has
   `arm_diff` = description-only in BATCH.json (a WORKTREE after-arm is void); N = scored runs only; a probe with <4
   scored runs in either arm = no data.
2. Claim set = public class `description-sensitive` + held-out positives. `control-agent-table` and negatives are
   reported, not claimed.
3. Baseline 0/N rows are uninformative: excluded from the gate; a gain there is listed as "new" and never offsets a drop.
4. Per probe, paired k_after − k_base: gate FAILS if any claim-set probe drops by ≥2, or if claim-set total k drops at all.
5. Channel: a claim-set probe whose passes move from skill to agent in ≥2 runs is a regression even with k unchanged.
6. Over-trigger: FAIL if any negative (public or held-out) drops by ≥2, or mean distinct routable skills per run rises
   by >0.3 on the claim set.
7. Held-out is judged by rules 3–6 on its own and must pass on its own (independent group H01/H05/H06/H10/H11 reported
   separately from the sibling group); a public pass cannot compensate.
8. Both directions are always published per probe with run ids; "improved" may be claimed only if the gate passes and
   total k rises on both public and held-out.
9. No expectation edits after the after-arm runs; any edit re-scores BOTH arms from raw traces.
