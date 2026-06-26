"""Shared pytest fixtures for shode-house dev-loop script tests.

Builds throwaway plugin trees in tmp_path so we can drive the real
check_index / lint functions against known-good and known-bad inputs.
Stdlib only (matches scripts/ constraints).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make scripts/ importable as top-level modules (check_index, lint, _lib).
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


VALID_SKILL = """\
---
name: {name}
description: |
  [WHAT] test skill body.
  [AUDIENCE] tests.
  [WHEN] never in prod.
  [TRIGGER] /x, "x".
---

# {name}

body line
"""

VALID_AGENT = """\
---
name: {name}
description: test agent
model: {model}
---

# {name}
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo_root_path() -> Path:
    """The real shode-house repo root (parent of tests/)."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def plugin_tree(tmp_path: Path):
    """Factory: build a minimal but valid plugin tree, return its root.

    Pass overrides to mutate plugin.json / marketplace.json into bad states.
    """

    def _build(
        *,
        plugin_overrides: dict | None = None,
        marketplace_overrides: dict | None = None,
        skills: dict[str, dict] | None = None,
        agents: dict[str, str] | None = None,
    ) -> Path:
        root = tmp_path
        # --- skills: {bucket: {skill_name: {"lines": n}}} ---
        skills = skills or {"workflow": {"meeting": {}}}
        for bucket, members in skills.items():
            for skill_name, opts in members.items():
                extra = "\n".join(f"line {i}" for i in range(opts.get("lines", 3)))
                _write(
                    root / "skills" / bucket / skill_name / "SKILL.md",
                    VALID_SKILL.format(name=skill_name) + extra,
                )
        # --- agents: {name: model} ---
        for agent_name, model in (agents or {"developer": "sonnet"}).items():
            _write(root / "agents" / f"{agent_name}.md", VALID_AGENT.format(name=agent_name, model=model))

        # --- manifests ---
        shippable = [f"./skills/{b}/" for b in skills]
        plugin = {
            "name": "shode-house",
            "version": "9.9.9",
            "description": "test plugin description ascii only",
            "skills": shippable,
        }
        if plugin_overrides:
            plugin.update(plugin_overrides)
        _write(root / ".claude-plugin" / "plugin.json", json.dumps(plugin, indent=2))

        market = {
            "name": "shode-house",
            "description": "test marketplace description ascii",
            "plugins": [{"name": "shode-house", "description": "short ascii desc"}],
        }
        if marketplace_overrides:
            market.update(marketplace_overrides)
        _write(root / ".claude-plugin" / "marketplace.json", json.dumps(market, indent=2))
        return root

    return _build
