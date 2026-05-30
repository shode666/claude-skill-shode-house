#!/usr/bin/env python3
"""shode-house Eval Harness runner (cross-platform Python stdlib).

Modes:
    --dry-run (default): validate fixture schema for all 19 agents
    --agent <name>:      validate fixtures for specific agent
    --invoke:            STUB until Claude SDK harness wired

Source-of-truth: ``skills/discipline/eval-harness/SKILL.md``
Owner: Evan agent (offline tool — NOT in /implement loop).

Usage::

    python3 scripts/run_eval.py --dry-run
    python3 scripts/run_eval.py --agent felix --dry-run
    python3 scripts/run_eval.py --agent felix --n 5 --invoke   # STUB
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REQUIRED_FIELDS = (
    "id",
    "agent",
    "bias_type",
    "input",
    "expected_behavior",
    "run_config",
    "metrics",
    "expert_validated_by",
)

VALID_BIAS_TYPES = {
    "sycophancy",
    "anchoring",
    "pattern-bias",
    "verbosity",
    "position",
    "verdict-skew",
    "convergence",
    "alert-dismissal",
    "std-vs-custom",
}

EXPECTED_AGENTS = {
    "oliver",
    "bella",
    "sara",
    "dave",
    "chris",
    "quinn",
    "aaron",
    "uma",
    "patrick",
    "stan",
    "sentinel",
    "reggie",
    "felix",
    "iris",
    "sam",
    "tara",
    "elena",
    "brooke",
    "emma",
}


def validate_fixture(path: Path) -> list[str]:
    """Return list of error strings; empty = valid."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"parse error: {exc}"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing field: {field}")

    bias = data.get("bias_type")
    if bias and bias not in VALID_BIAS_TYPES:
        errors.append(f"unknown bias_type: {bias!r} (expected one of {sorted(VALID_BIAS_TYPES)})")

    agent = data.get("agent")
    if agent and agent not in EXPECTED_AGENTS:
        errors.append(f"unknown agent: {agent!r}")

    folder_agent = path.parent.name
    if agent and agent != folder_agent:
        errors.append(f"agent field {agent!r} != folder {folder_agent!r}")

    run_cfg = data.get("run_config", {})
    if isinstance(run_cfg, dict):
        n = run_cfg.get("n_runs", 0)
        if not isinstance(n, int) or n < 1:
            errors.append(f"run_config.n_runs must be int ≥ 1 (got {n!r})")

    expected = data.get("expected_behavior", {})
    if isinstance(expected, dict) and "expected_keywords" not in expected:
        errors.append("expected_behavior.expected_keywords missing (required for blind judging)")

    return errors


def dry_run(fixtures_dir: Path, agent_filter: str | None) -> int:
    if not fixtures_dir.exists():
        print(f"  ✗ {fixtures_dir} not found")
        return 1

    found_agents: set[str] = set()
    fixtures_per_agent: dict[str, int] = defaultdict(int)
    total_errors = 0
    total_fixtures = 0
    pending_expert = 0

    for fixture in sorted(fixtures_dir.rglob("*.json")):
        rel = fixture.relative_to(fixtures_dir)
        # Skip top-level non-fixture files (none expected; defensive)
        if len(rel.parts) < 2:
            continue
        agent = rel.parts[0]
        if agent_filter and agent != agent_filter:
            continue
        found_agents.add(agent)
        fixtures_per_agent[agent] += 1
        total_fixtures += 1

        errors = validate_fixture(fixture)
        if errors:
            print(f"  ✗ {rel}")
            for err in errors:
                print(f"      - {err}")
            total_errors += len(errors)
            continue

        try:
            data = json.loads(fixture.read_text(encoding="utf-8"))
            if data.get("expert_validated_by") == "PENDING":
                pending_expert += 1
        except (OSError, json.JSONDecodeError):
            pass

        print(f"  ✓ {rel}: bias={data.get('bias_type')} expert={data.get('expert_validated_by')}")

    print()
    if not agent_filter:
        missing_agents = EXPECTED_AGENTS - found_agents
        if missing_agents:
            print(f"  ⚠ agents without any fixture: {sorted(missing_agents)}")
            print("     (each of 19 agents should have ≥ 1 starter fixture)")

    print(f"  Total fixtures: {total_fixtures}")
    print(f"  Agents covered: {len(found_agents)} / {len(EXPECTED_AGENTS) if not agent_filter else 1}")
    print(f"  PENDING expert validation: {pending_expert}")
    print(f"  Schema errors: {total_errors}")

    return 1 if total_errors > 0 else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="shode-house Eval Harness runner")
    parser.add_argument("--agent", default=None, help="Validate only this agent's fixtures")
    parser.add_argument("--n", type=int, default=5, help="Runs per fixture (reserved for --invoke)")
    parser.add_argument(
        "--fixtures-dir",
        default="tests/eval-fixtures",
        help="Fixtures root (default: tests/eval-fixtures)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Schema validate (default)")
    mode.add_argument("--invoke", action="store_true", help="STUB: invoke subject + judge LLMs")
    args = parser.parse_args()

    print("=" * 63)
    mode_str = "invoke" if args.invoke else "dry-run"
    agent_str = args.agent or "all-agents"
    print(f"  shode-house eval-harness — mode={mode_str} target={agent_str}")
    print("=" * 63)

    fixtures_dir = Path(args.fixtures_dir)

    if args.invoke:
        print("  ⚠ --invoke mode: STUB. Wire Claude SDK in Evan agent before real eval.")
        print("  ⚠ Required: subject_model, judge_model (different), N runs, judge calibration step")
        print("  ⚠ Output dest: outputs/EVAL-<agent>-<date>.json")
        return 0

    rc = dry_run(fixtures_dir, args.agent)
    print()
    if rc == 0:
        print("  ✅ dry-run PASS — all fixtures valid")
    else:
        print("  ❌ dry-run FAIL — fix schema errors")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
