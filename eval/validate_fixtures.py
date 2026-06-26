#!/usr/bin/env python3
"""validate_fixtures.py — schema-check eval fixtures (AXI-style output).

The eval SCORING loop is agent-orchestrated (Task tool, no script) per
CLAUDE.md. This validator is the cheap, deterministic gate that keeps the
fixture corpus well-formed and CI-runnable. It also cross-checks that every
expect_skill / expect_primary names a real skill / agent in the repo, so a
rename can't silently rot the corpus.

Output is TOON-ish: counts first, then only problems. Exit 1 on any error.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

REQUIRED = {
    "trigger": {"id", "utterance", "expect_skill"},
    "routing": {"id", "request", "expect_primary", "tshirt"},
    "failure_mode": {"id", "rule", "bad_behaviour", "catch"},
}


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        # Minimal stdlib fallback: enough to validate our flat fixture shape.
        return _mini_yaml(path.read_text(encoding="utf-8"))


def _mini_yaml(text: str) -> dict:
    """Tiny YAML subset parser for the fixture shape (list of dict cases)."""
    out: dict = {"cases": []}
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.split(" #")[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if line.startswith("  - "):
            cur = {}
            out["cases"].append(cur)
            line = "    " + line[4:]
        if line.startswith("    ") and ":" in line and cur is not None:
            k, _, v = line.strip().partition(":")
            v = v.strip()
            if v in ("null", ""):
                val: object = None
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                val = [x.strip() for x in inner.split(",")] if inner else []
            else:
                val = v.strip('"')
            cur[k.strip()] = val
        elif ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            if v.strip():
                out[k.strip()] = v.strip().strip('"')
    return out


def _skill_names() -> set[str]:
    return {p.parent.name for p in (ROOT / "skills").glob("*/*/SKILL.md")}


def _agent_names() -> set[str]:
    return {p.stem for p in (ROOT / "agents").glob("*.md")}


def main() -> int:
    skills = _skill_names()
    agents = _agent_names()
    errors: list[str] = []
    total = 0

    files = sorted(FIXTURES.glob("*.yaml"))
    for fp in files:
        data = _load_yaml(fp)
        kind = data.get("kind")
        cases = data.get("cases", [])
        if kind not in REQUIRED:
            errors.append(f"{fp.name}: unknown kind {kind!r}")
            continue
        for c in cases:
            total += 1
            missing = REQUIRED[kind] - set(c)
            if missing:
                errors.append(f"{fp.name}:{c.get('id','?')}: missing {sorted(missing)}")
            if kind == "trigger" and c.get("expect_skill") not in (None, "null") and c.get("expect_skill") not in skills:
                errors.append(f"{fp.name}:{c.get('id')}: expect_skill '{c.get('expect_skill')}' is not a real skill")
            if kind == "routing" and c.get("expect_primary") not in agents:
                errors.append(f"{fp.name}:{c.get('id')}: expect_primary '{c.get('expect_primary')}' is not a real agent")

    print(f"fixtures: files={len(files)} cases={total} skills={len(skills)} agents={len(agents)}")
    if errors:
        print(f"errors: {len(errors)}")
        for e in errors:
            print(f"  x {e}")
        return 1
    print("ok: all fixtures well-formed and reference real skills/agents")
    print("next: run the agent-orchestrated scorer (eval/README.md) to grade trigger/routing accuracy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
