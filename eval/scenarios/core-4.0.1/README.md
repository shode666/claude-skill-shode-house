# Core scenarios, 4.0.1 set (frozen)

Why: v4.0.1 consolidates the 18 agent types of 4.0.0 into 6 (`plan`, `build`, `verify`, `operate`, `secure`, `design`).
The 4.0 core set names retired ids in `expected.agents` and `expected.must_not_dispatch`, so
`tests/test_core_scenarios.py` (`test_every_named_skill_and_agent_is_shipped_post_merge`) is red against it. The 3.17 files
(`eval/FREEZE.sha256`) and the 4.0 set (`eval/scenarios/core-4.0/FREEZE.sha256`) are pinned and are never edited; this
directory is the set for 4.0.1, with its own manifest. `eval/core-set.sh` selects it for plugin version 4.0.1 and later 4.x;
4.0.0 keeps `core-4.0`.

| File | What |
|---|---|
| `core-4.0.1.json` | the 17 core scenarios of `core-4.0.json`, retired ids rewritten to their 4.0.1 type |
| `routing-4.0.1.json` | 5 new routing scenarios (E16..E20) for the consolidation gates; shape-checked offline, scored by the live runner when the probes are re-run |
| `probes-4.0.1.json` | the PRE-REGISTERED thresholds and the fallback for E19 (served model, SEC-3) and E20 (spec-axis seeded violations, SEC-8), and the ordinary-work negative rule |
| `check-probes.py` | offline scorer of those probes from a stream-json trace; reads thresholds only from `probes-4.0.1.json` |
| `check-freeze.sh` | verifies this manifest and re-derives the set from the frozen 4.0 set |
| `FREEZE.sha256` | sha256 of `core-4.0.1.json`, `routing-4.0.1.json`, `probes-4.0.1.json`, `check-probes.py`, `README.md`, `check-freeze.sh` |

Derivation rule (the only difference from the 4.0 set): each retired 4.0.0 agent id in `expected.agents`,
`expected.must_not_dispatch`, `expected.first_action` and `expected.route_any` becomes its 4.0.1 type (domain ids and the `*-expert` glob ->
`plan`; developer -> `build`; code-reviewer, qa-engineer -> `verify`; security-engineer -> `secure`; ux-ui-designer ->
`design`; business-analyst, product-manager, solution-architect -> `plan`); `staff-engineer` is dropped from
`must_not_dispatch` (the staff-grade brief is `build`, which the implementer legitimately is) and the scenario gains
`post_checks: ["no-fable-dispatch"]` instead, so the old negative (no over-dispatch of the staff-grade tier on ordinary work)
is still tested: `check-probes.py <id> <trace>` fails if a main-session spawn requests a fable model or `modelUsage` names one;
duplicates collapse, order is kept. Prompts (`eval/prompts/E*.md`), fixtures and every other field are unchanged.

`routing-4.0.1.json` is outside the 17 (the "exactly 17" shape tests stay as they are). Its scenarios
pin what a description-rewrite regression would break, and are NOT measured yet: no model has run them. Re-run the routing
probes (same N, Sonnet) and these five before any release decision; report the result next to the 4.0.0 baseline.

```bash
bash eval/scenarios/core-4.0.1/check-freeze.sh            # verify (exit 0)
bash eval/scenarios/core-4.0.1/check-freeze.sh --update   # a new revision of this set; disclose it
```

## Pre-registered probes (E19, E20): thresholds fixed before any run

`probes-4.0.1.json` is committed and pinned in `FREEZE.sha256` before any model has run these probes. A threshold changed
after a run is a new disclosed revision and never rescues that run. Nothing below has been measured.

| Probe | What it checks | Registered pass rule |
|---|---|---|
| E19 (SEC-3 served model) | a regulated-domain brief is dispatched as a `plan` spawn carrying `model: opus`; the reply records the requested model and the served model; the served model is the one in `modelUsage`; a mismatch is reported BLOCKED | 5 runs; all 5 record correctly and all 5 are served as requested (a missed or unhonoured override is a failed control); no `modelUsage` on the result = UNSCORABLE |
| E20 (SEC-8 spec axis) | the spec-axis `plan` spawn reports the 4 seeded violations (AC-2, AC-3, AC-4, AC-6) of a change with green tests as `AC-n: VIOLATED` lines and does not flag the 2 met criteria (AC-1, AC-5); scored from those closed-form lines only, a run without them is UNSCORABLE for human adjudication | 5 runs; catch rate over 20 seeded opportunities >= 0.80 and not below the 4.0.0 `business-analyst` baseline measured with the same checker on the same fixture; false-positive rate over 10 decoy opportunities <= 0.25 |

Revision note (pre-run, user decision U30 after reviews N1-N5): before any model run the E20 scorer was re-pinned twice. First it
bound a free-text verdict to the AC id (N1); reviews N2, N3 and N5 then showed the same failure class in other phrasings ("AC-2
violated? no", "could not find any violation", a markdown table row, "nothing missing"), so the natural-language heuristic was
removed. E20 is now a **structured text scorer with human adjudication**: the E20 prompt (`eval/prompts/E20-spec-axis-seeded-violations.md`)
requires the reviewer to emit one `AC-n: MET` or `AC-n: VIOLATED` line per criterion; `check-probes.py` reads ONLY lines whose whole
stripped text has that form (`verdict_line_regex`, upper case, nothing else on the line) and prints the verdict it read per id and
run. A run with a criterion that has no such line, a duplicate line, two different verdicts for one id, or no such line at all
(a table, a bullet, a bold line, prose) is UNSCORABLE (exit 2): a human reads the reply and adjudicates; the scorer never guesses.
The verdict lines are taken ONLY from the spec reviewer's own spawn result (the `tool_result` of its `plan` spawn, matched on
`tool_use_id`); the router's final text may only corroborate them. A different verdict there is a conflict (UNSCORABLE), and a line
missing from the reviewer's reply is UNSCORABLE even when the router's text has it, so a prose-only or partial reviewer is never
completed by the router. A trace count other than the registered `runs` is UNSCORABLE too. `violation_word_regex`, `weak_violation_regex`, `negated_violation_regex`,
`cleared_word_regex` were removed from `probes-4.0.1.json`; thresholds are unchanged and the manifest was regenerated. The E20
prompt gained its closed-form answer line. Nothing had run, so this is not a post-run change.
Second pre-run re-pin (iter 5, reviews F1, F3, F5): the relay rule above replaced a union of all text sources (which let the
router's final text supply verdicts the reviewer never wrote); the boundaries (16 of 20 catches = 0.80 passes, an id outside the six
is ignored) are pinned by tests; and the E19 and E20 prompt files, which carry the closed-form contract, are now listed in
`FREEZE.sha256` (and verified by `check-freeze.sh`). The manifest was regenerated; thresholds are unchanged; nothing had run.

Fallback, decided by the user and never applied by an agent: if E20 fails (or is below the baseline) the spec axis moves from
`plan` to `verify` (a spec mode of `verify`, still a fresh spawn that never wrote the AC) and the review card, `plan.md`,
`verify.md` and the tool-ceiling test change in one revision. If E19 fails, domain, architecture and staff-grade briefs run at the
type default and the router reports BLOCKED for them until the user chooses between a host-pinned domain type and an accepted
lower tier. The same text is in `CHANGELOG.md` and `README.md` (4.0.1).

```bash
python3 eval/scenarios/core-4.0.1/check-probes.py E19 run1.jsonl ... run5.jsonl
python3 eval/scenarios/core-4.0.1/check-probes.py E20 run1.jsonl ... run5.jsonl [--baseline-rate 0.85]
python3 eval/scenarios/core-4.0.1/check-probes.py E01 trace.jsonl     # no-fable-dispatch on ordinary work
```
