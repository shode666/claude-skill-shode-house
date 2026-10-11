# Routing-probe battery, 4.0.1 (frozen, not run)

Why: v4.0.1 consolidates the 18 agent types of 4.0.0 into 6 (`plan`, `build`, `verify`, `operate`, `secure`, `design`). The
P01..P47 routing probes (`eval/scenarios/golden.json`, prompts `eval/prompts/probes/`) name the retired ids (`developer`,
`fintech-expert`, `sre-engineer` ...), so they cannot score a 4.0.1 tree. They stay exactly as they are, pinned by
`eval/FREEZE.sha256`, as the **historical baseline** (3.17 / 4.0.0). This directory is the additive 4.0.1 battery: the same
probes, with the expected route mapped to the 6 types. Nothing here has been run; there is no measurement of any model.

| File | What |
|---|---|
| `battery-4.0.1.json` | the 47 probes (P21 stays `not_applicable`), derived from `golden.json` by the rule below; per probe `type_4_0_1`, `mode_4_0_1` (the expected type and mode or review axis), `dropped_4_0_1`, and for 7 probes `domain_4_0_1`; top-level `domain_tier` |
| `check-freeze.sh` | verifies this manifest and re-derives the battery from the frozen `golden.json` every time |
| `check-domain.py` | offline check for the 7 single-domain probes: which domain reference the `plan` spawn names and the requested model tier |
| `FREEZE.sha256` | sha256 of the battery JSON, this README, `check-freeze.sh`, `check-domain.py` and the runner `eval/run-battery-4.0.1.sh` (5 entries, repo-relative paths) |
| `../../run-battery-4.0.1.sh` | the 4.0.1 runner: the logic of `eval/run-probes.sh` under a new name, scoring this battery |

## Derivation rule (the only difference from the baseline)

Each `kind: probe` scenario of `golden.json` is copied in order with its id, prompt file, `max_turns`, class, description, source,
`fixture_flags`, `related` and every `expected` field (skills, `must_not_load`, `max_skills`, `max_spawns`) unchanged. Only agent ids
change, in `expected.route_any` (`agent:<id>`) and `expected.must_not_dispatch`: each 4.0.0 id becomes its 4.0.1 type
(product-manager, business-analyst, solution-architect, the 7 domain experts and the `*-expert` glob -> `plan`; developer,
staff-engineer -> `build`; code-reviewer, qa-engineer -> `verify`; security-engineer -> `secure`; ux-ui-designer -> `design`;
devops-engineer, sre-engineer -> `operate`). `orchestrator` is the router itself, not a spawn type, and is dropped. A type the probe
requires is removed from its own `must_not_dispatch` (two old ids that are one type now cannot be required and forbidden at once),
and every removed name is listed in `dropped_4_0_1`. Prompts are the baseline's, byte for byte (pinned by `eval/FREEZE.sha256`).

What the mapping cannot keep, stated plainly:
- Modes of one type are not separable by the spawn type: Patrick (discover), Bella (requirements) and Sara (architecture) are all `plan`,
  so P40 no longer forbids the others; `mode_4_0_1` records the intended mode, it is not scored.
- The 7 domain probes (P15, P23, P24, P42..P45) score `agent:plan` only in the shared scorer. Which domain is checked by
  `check-domain.py` from the dispatch request (the delegation names `references/domain/<domain>.md`; the model follows the pinned tier:
  `opus` for fintech, sap, trading, insurance; erp, booking, ecommerce at the type default, `opus` only with a recorded high-stakes
  reason). The runner records it as `domain-check.txt` in the run directory; it is report-only and is not part of `score.txt`.
- The dropped negatives are these and no others: P40's "not the other discovery/requirements/architecture mode" (all `plan`), and
  for each of the 7 domain probes the six other experts (all `plan`); both are listed per probe in `dropped_4_0_1`, and the domain
  check is report-only. The CHANGELOG and README say the same.
- The probe hook blocks the spawn after the dispatch request is recorded, so the sub-agent's own behaviour is never observed here.

## Same prompt, model and N as the baseline

The baseline battery is 46 applicable probes x N=5 on Sonnet, 6 turns, USD 1 cap (`eval/RUNBOOK.md` "Routing-probe protocol"). The 4.0.1
runner uses the same prompts, `sonnet` by default, `REPEATS=5` by default, the same caps, and writes the same `SUMMARY.tsv` / `AGG.tsv`
(`eval/probe-agg.py`), so its k/N per probe is read next to the baseline's. No pass threshold is registered here: the result is
reported per probe beside the baseline and the 4.0.1 decision belongs to the user.

## Output hygiene (pre-run revision, iter 5, security review SEC-13)

The runner writes owner-only: `umask 077` before anything exists (directories 0700, files 0600), a symlinked out-dir is refused, and
an existing out-dir is locked down before any run with `eval/redact_derived.py lockdown` (every directory 0700, every file 0600; a
symlink, special file, hard-linked or foreign entry refuses the batch with exit 4 and nothing changed). Like `eval/run-core.sh`, after
each run its derived files (`tools-seen.txt`, `score.txt`, `score.json`, `meta.json`, plus `domain-check.txt`, the buffered console
output, `SUMMARY.tsv`, `AGG.tsv`) are redacted in place by `eval/redact_derived.py` and `run.jsonl` stays byte-exact (its sha256 is
recorded in `redaction.json` and checked); a redaction failure stops the batch (exit 4). `.redact-pending` names the run in flight, so
the next invocation seals an interrupted run before anything else. The frozen `run-lib.sh` is wrapped, never edited; the
descriptor isolation and signal handling of `run-core.sh` are not replicated here (the runner is a foreground loop).

```bash
bash eval/scenarios/battery-4.0.1/check-freeze.sh            # verify (exit 0); the runner also requires bash eval/check-freeze.sh
bash eval/run-battery-4.0.1.sh sonnet outputs/eval-4.0.1/battery/<new-dir>    # needs a real Claude Code; not run in CI
python3 eval/scenarios/battery-4.0.1/check-domain.py P15 <trace.jsonl>        # one domain probe, offline
bash eval/scenarios/battery-4.0.1/check-freeze.sh --update   # a new revision of this battery; disclose it, only before a run
```
