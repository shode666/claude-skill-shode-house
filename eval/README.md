# eval/ — shode-house quality harness

> Makes plugin quality **observable**: skill-trigger accuracy, Oliver routing
> correctness, and discipline-regression (G1-G11) — the gap bd-101 closes.

## Two layers

1. **Deterministic gate (`validate_fixtures.py`)** — schema-checks the corpus and
   verifies every `expect_skill` / `expect_primary` still names a real
   skill/agent. Runs in CI, no agent needed. **This is what protects the corpus
   from silent rot after a rename.**
2. **Agent-orchestrated scorer (manual / Task tool)** — per CLAUDE.md the actual
   grading is agent-run, no script. Procedure below.

## Fixtures

| File | Kind | What it grades |
|---|---|---|
| `fixtures/triggers.yaml` | trigger | does the right SKILL fire? (incl. 1 known-negative) |
| `fixtures/routing.yaml` | routing | does Oliver pick the right owning agent + T-shirt? |
| `fixtures/failure_modes.yaml` | failure_mode | G1-G11 + anti-puppet — known-bad anchors (AC-2) |

## Run the deterministic gate

```bash
python3 eval/validate_fixtures.py     # exit 0 = corpus clean
```

## Run the scorer (agent-orchestrated)

For each `trigger` case: present `utterance` to a fresh agent context; record
which skill fires; mark hit if it equals `expect_skill` and none of `must_not`
fire. For each `routing` case: present `request` to Oliver; record primary
agent + T-shirt; mark hit on exact primary match.

Score = hits / total per kind. Commit the scorecard as the **baseline**; set the
**regression budget** (e.g. trigger recall ≥ 0.9, routing acc ≥ 0.85). Re-run
before any skill/agent edit; a drop below budget blocks the change.

The `failure_mode` cases are the adversarial anchors: each describes a discipline
that must produce a FAIL when violated. Use them to confirm the scorer can fail
(not rubber-stamp) — AC-2.

## Adding a fixture

1. Append a case to the relevant `fixtures/*.yaml` (keep the required keys —
   see `REQUIRED` in `validate_fixtures.py`).
2. `python3 eval/validate_fixtures.py` must stay green.
3. Re-baseline if it shifts scores.
