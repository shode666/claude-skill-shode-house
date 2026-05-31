#!/usr/bin/env python3
"""lint.py — comprehensive pre-publish gate (8 checks, cross-platform).

Replacement for scripts/lint.sh (v3.5+). Stdlib + PyYAML (or fallback).

Catches:
  - JSON syntax errors
  - YAML parse errors in frontmatter (skill/command/agent)
  - SKILL name vs folder mismatch
  - Cross-skill refs pointing to non-existent skills
  - Path refs in README/CLAUDE broken
  - CLAUDE.md invariants (delegates to check_index.py)

Usage::

    python3 scripts/lint.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, red, green, yellow  # noqa: E402

try:
    import yaml  # PyYAML
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def parse_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter. Returns None on error."""
    if not YAML_AVAILABLE:
        # Minimal fallback: extract name + description + argument-hint via regex
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            return None
        parts = text.split("---", 2)
        if len(parts) < 2:
            return None
        out: dict = {}
        for m in re.finditer(r"^([a-z_-]+):\s*(.+?)$", parts[1], re.MULTILINE):
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            out[key] = val
        # Detect description as multiline block (starts with |)
        m = re.search(r"^description:\s*\|", parts[1], re.MULTILINE)
        if m:
            out["description"] = "..."  # placeholder; just verify presence
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 2:
        return None
    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def check_json_syntax(root: Path) -> int:
    print("[1/8] JSON syntax")
    fail = 0
    for f in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        p = root / f
        try:
            json.loads(p.read_text(encoding="utf-8"))
            green(f"  ✓ {f}")
        except (OSError, json.JSONDecodeError) as exc:
            red(f"  ✗ {f} — {exc}")
            fail = 1
    return fail


def check_skill_frontmatter(root: Path) -> int:
    print("\n[2/8] SKILL.md frontmatter (YAML + name + description string)")
    fail = 0
    skills = sorted((root / "skills").glob("**/SKILL.md"))
    for f in skills:
        fm = parse_frontmatter(f)
        if not fm:
            red(f"  ✗ {f.relative_to(root)}: invalid/missing frontmatter")
            fail = 1
            continue
        if "name" not in fm or "description" not in fm:
            red(f"  ✗ {f.relative_to(root)}: missing name or description")
            fail = 1
            continue
        if not isinstance(fm["description"], str):
            red(f"  ✗ {f.relative_to(root)}: description must be string, got {type(fm['description']).__name__}")
            fail = 1
    if fail == 0:
        green(f"  ✓ {len(skills)}/{len(skills)} SKILL.md valid")
    return fail


def check_command_frontmatter(root: Path) -> int:
    print("\n[3/8] Command .md frontmatter (YAML + description + string argument-hint)")
    fail = 0
    cmds = sorted((root / "commands").glob("*.md"))
    for f in cmds:
        fm = parse_frontmatter(f)
        if not fm:
            red(f"  ✗ {f.relative_to(root)}: invalid frontmatter")
            fail = 1
            continue
        if not isinstance(fm.get("description", ""), str):
            red(f"  ✗ {f.relative_to(root)}: description not string")
            fail = 1
            continue
        if "argument-hint" in fm and not isinstance(fm["argument-hint"], str):
            red(f"  ✗ {f.relative_to(root)}: argument-hint must be string (quote it!)")
            fail = 1
    if fail == 0:
        green(f"  ✓ {len(cmds)}/{len(cmds)} commands valid")
    return fail


def check_agent_frontmatter(root: Path) -> int:
    print("\n[4/8] Agent .md frontmatter (YAML + name + description)")
    fail = 0
    agents = sorted((root / "agents").glob("*.md"))
    for f in agents:
        fm = parse_frontmatter(f)
        if not fm or "name" not in fm or "description" not in fm:
            red(f"  ✗ {f.relative_to(root)}")
            fail = 1
    if fail == 0:
        green(f"  ✓ {len(agents)}/{len(agents)} agents valid")
    return fail


def check_skill_name_match(root: Path) -> int:
    print("\n[5/8] SKILL frontmatter 'name' matches folder name")
    fail = 0
    for f in sorted((root / "skills").glob("*/*/SKILL.md")):
        folder = f.parent.name
        fm = parse_frontmatter(f)
        fm_name = fm.get("name") if fm else None
        if folder != fm_name:
            red(f"  ✗ folder='{folder}' frontmatter name='{fm_name}' in {f.relative_to(root)}")
            fail = 1
    if fail == 0:
        green("  ✓ all SKILL names match folder")
    return fail


def check_skill_cross_refs(root: Path) -> int:
    print("\n[6/8] Skill cross-references resolve (commands + README + CLAUDE)")
    pattern = re.compile(
        r"`(meeting|dev-gate|automate-test|diagnose|incident|slo|secure|ui-test|web-q|caveman|review-checklist|devils-advocate|shode-house-[a-z]+)`"
    )
    refs_files: list[Path] = list((root / "commands").glob("*.md"))
    for f in ("README.md", "CLAUDE.md"):
        p = root / f
        if p.exists():
            refs_files.append(p)
    skill_dirs = {p.parent.name for p in (root / "skills").glob("*/*/SKILL.md")}
    referenced: set[str] = set()
    for f in refs_files:
        for m in pattern.finditer(f.read_text(encoding="utf-8", errors="replace")):
            referenced.add(m.group(1))
    missing = referenced - skill_dirs
    if missing:
        red(f"  ✗ Referenced but missing: {missing}")
        return 1
    green(f"  ✓ {len(referenced)} skills referenced, all resolve")
    return 0


def check_path_refs(root: Path) -> int:
    print("\n[7/8] Path refs in README+CLAUDE resolve (CHANGELOG skipped)")
    pattern = re.compile(
        r"`(skills/[a-z\-/]+(?:/SKILL\.md)?|scripts/[a-z\-_]+\.(?:sh|py)|commands/[a-z\-]+\.md|agents/[a-z\-]+\.md)`"
    )
    ok = True
    for f in ("README.md", "CLAUDE.md"):
        p = root / f
        if not p.exists():
            continue
        for ref in set(pattern.findall(p.read_text(encoding="utf-8", errors="replace"))):
            if not (root / ref).exists():
                red(f"  ✗ {f}: broken {ref!r}")
                ok = False
    if not ok:
        return 1
    green("  ✓ All path references resolve")
    return 0


def check_invariants(root: Path) -> int:
    print("\n[8/8] CLAUDE.md invariants (size + Cowork caps + bucket lifecycle)")
    check_index_py = root / "scripts" / "check_index.py"
    if not check_index_py.exists():
        red(f"  ✗ {check_index_py.relative_to(root)} not found")
        return 1
    res = subprocess.run(
        [sys.executable, str(check_index_py)],
        capture_output=True, text=True, cwd=str(root),
    )
    if res.returncode == 0:
        green("  ✓ all invariants pass")
        return 0
    red("  ✗ check_index.py FAILED:")
    for line in res.stdout.splitlines()[-20:]:
        print(f"    {line}")
    return 1


def main() -> int:
    root = repo_root()
    print("=" * 63)
    print("  shode-house lint — pre-publish gate (8 checks)")
    print("=" * 63)
    print()

    if not YAML_AVAILABLE:
        yellow("  ⚠ PyYAML not installed — using regex fallback for frontmatter parsing")
        yellow("    Install for full YAML validation: pip install --user pyyaml")
        print()

    fail = 0
    fail += check_json_syntax(root)
    fail += check_skill_frontmatter(root)
    fail += check_command_frontmatter(root)
    fail += check_agent_frontmatter(root)
    fail += check_skill_name_match(root)
    fail += check_skill_cross_refs(root)
    fail += check_path_refs(root)
    fail += check_invariants(root)

    print()
    print("=" * 63)
    if fail == 0:
        green("  ✅ ALL 8 LINT CHECKS PASS — safe to publish")
        return 0
    red("  ❌ LINT FAILED — fix issues before publish")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
