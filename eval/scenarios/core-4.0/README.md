# Core scenarios, 4.0 set (frozen)

Why: the 3.17 core scenarios name the retired router agent type in `expected.must_not_dispatch`. After the 4.0.0
switch (W10) that type has no agent file, so `tests/test_core_scenarios.py` (`test_every_named_skill_and_agent_is_shipped_post_merge`)
turns red on E01..E1c. The 3.17 files are pinned by `eval/FREEZE.sha256` (frozen probe protocol) and are never
edited. This directory is the new set for 4.0, with its own manifest (task `shode-house-v7u.4.20`, review finding
N2 of `06-chris-w3-review-r2.md`).

| File | What |
|---|---|
| `core-4.0.json` | the 17 core scenarios (E01 from `golden.json`, E02..E15, E10b, E1c from `core-3.17.json`) |
| `check-freeze.sh` | verifies this manifest and re-derives the set from the frozen sources |
| `FREEZE.sha256` | sha256 of the three files here |

Derivation rule (the only difference from 3.17): the retired router type is removed from every
`expected.must_not_dispatch` list; a list that held only that entry stays `[]`. Prompts (`eval/prompts/E*.md`),
fixtures and every other field are unchanged. `derived_from` records the sha256 of both 3.17 sources, and
`check-freeze.sh` fails if the set is not exactly the rule applied to them.

```bash
bash eval/scenarios/core-4.0/check-freeze.sh            # verify (exit 0)
bash eval/scenarios/core-4.0/check-freeze.sh --update   # a new revision of this set; disclose it
```

Switch steps owned by W10 (ledger `outputs/shode-house-v7u/ledger/W9.json`): point `tests/test_core_scenarios.py`
and the core runners (`eval/run-core.sh`, `eval/run-e01.sh`) at this set, and add this check to CI.
