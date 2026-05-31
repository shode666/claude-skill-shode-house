#!/usr/bin/env python3
"""check_index.py — enforce CLAUDE.md invariants (cross-platform).

Replacement for scripts/check-index.sh (v3.5+). Stdlib only.

Checks:
  1. Skill size ≤ 300 lines (with thin-entry exceptions)
  2. Excluded buckets (in-progress, deprecated) NOT listed in plugin.json
  3. Shippable bucket paths listed in plugin.json skills array
  4. Cowork validator constraints (description length + ASCII)
  5. SKILL.md description 4-section marker check (warn-only)

Exits non-zero on violation. Use as pre-commit / CI gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, red, green, yellow  # noqa: E402


SHIPPABLE_BUCKETS = ("workflow", "ops", "ui", "style", "discipline")
EXCLUDED_BUCKETS = ("in-progress", "deprecated")
THIN_ENTRY_EXCEPTIONS = {"meeting", "dev-gate"}
MAX_LINES = 300


def check_size(root: Path) -> int:
    fail = 0
    print(f"== 1. Skill size limits (≤ {MAX_LINES} lines) ==")
    for skill_md in sorted((root / "skills").glob("*/*/SKILL.md")):
        name = skill_md.parent.name
        try:
            lines = sum(1 for _ in skill_md.open(encoding="utf-8", errors="replace"))
        except OSError:
            lines = 0
        rel = skill_md.relative_to(root)
        if lines > MAX_LINES:
            if name in THIN_ENTRY_EXCEPTIONS:
                yellow(f"  ~ {rel}: {lines} lines (thin-entry exception)")
            else:
                red(f"  ✗ {rel}: {lines} lines > {MAX_LINES} — split required")
                fail = 1
        else:
            green(f"  ✓ {rel}: {lines} lines")
    return fail


def check_excluded(root: Path, plugin_json_text: str) -> int:
    fail = 0
    print("\n== 2. Excluded buckets not in plugin.json ==")
    for bucket in EXCLUDED_BUCKETS:
        bdir = root / "skills" / bucket
        if not bdir.is_dir():
            continue
        for skill_md in bdir.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if f'"{name}"' in plugin_json_text:
                red(f"  ✗ '{name}' in {bucket}/ but listed in .claude-plugin/plugin.json")
                fail = 1
            else:
                green(f"  ✓ '{name}' in {bucket}/ correctly excluded")
    return fail


def check_buckets_listed(root: Path, plugin_json_text: str) -> int:
    fail = 0
    print("\n== 3. Shippable bucket paths listed in plugin.json skills array ==")
    for bucket in SHIPPABLE_BUCKETS:
        bdir = root / "skills" / bucket
        if not bdir.is_dir():
            continue
        # Look for "./skills/<bucket>/" or "./skills/<bucket>"
        if f'"./skills/{bucket}/"' in plugin_json_text or f'"./skills/{bucket}"' in plugin_json_text:
            count = sum(1 for _ in bdir.glob("*/SKILL.md"))
            green(f"  ✓ '{bucket}/' bucket path listed (auto-discovers {count} skills)")
        else:
            red(f"  ✗ '{bucket}/' bucket path NOT in plugin.json skills array — skills won't load")
            fail = 1
    return fail


def _check_text(label: str, text: str, limit: int) -> int:
    errs = []
    if len(text) > limit:
        errs.append(f"length {len(text)} > {limit}")
    if any(ord(c) >= 128 for c in text):
        non_ascii = sorted({c for c in text if ord(c) >= 128})
        errs.append(f"non-ASCII chars present: {non_ascii}")
    if "—" in text or "–" in text:
        errs.append("em-dash/en-dash forbidden (use '-' or ':')")
    if any("฀" <= c <= "๿" for c in text):
        errs.append("Thai characters forbidden (move detail to README.md)")
    if errs:
        red(f"  ✗ {label}: {'; '.join(errs)}")
        return 1
    green(f"  ✓ {label}: {len(text)} chars ASCII (≤ {limit})")
    return 0


def check_cowork_constraints(root: Path) -> int:
    print("\n== 4. Cowork validator constraints (description length + ASCII) ==")
    fail = 0
    try:
        plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        fail += _check_text("plugin.json description", plugin.get("description", ""), 200)
    except (OSError, json.JSONDecodeError) as exc:
        red(f"  ✗ plugin.json: {exc}")
        fail = 1

    try:
        market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        fail += _check_text("marketplace.json description (top)", market.get("description", ""), 200)
        for i, pl in enumerate(market.get("plugins", [])):
            fail += _check_text(
                f"marketplace.json plugins[{i}].description", pl.get("description", ""), 100
            )
    except (OSError, json.JSONDecodeError) as exc:
        red(f"  ✗ marketplace.json: {exc}")
        fail = 1
    return fail


def check_description_format(root: Path) -> int:
    print("\n== 5. SKILL.md description format check (4-section: WHAT/AUDIENCE/WHEN/TRIGGER) ==")
    markers = ("WHAT", "AUDIENCE", "WHEN", "TRIGGER")
    for skill_md in sorted((root / "skills").glob("*/*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 2:
            continue
        # Extract description block: lines between description: and next top-level YAML key
        in_desc = False
        desc_lines: list[str] = []
        for line in parts[1].splitlines():
            if line.startswith("description:"):
                in_desc = True
                continue
            if in_desc and line and not line.startswith(" ") and not line.startswith("\t") and ":" in line:
                break
            if in_desc:
                desc_lines.append(line)
        desc = "\n".join(desc_lines)
        rel = skill_md.relative_to(root)
        for marker in markers:
            if f"[{marker}]" not in desc:
                yellow(f"  ~ {rel}: missing [{marker}] marker")
    return 0  # warn-only


def main() -> int:
    root = repo_root()
    plugin_json = root / ".claude-plugin" / "plugin.json"
    try:
        plugin_text = plugin_json.read_text(encoding="utf-8")
    except OSError as exc:
        red(f"ERROR: cannot read {plugin_json}: {exc}")
        return 1

    fail = 0
    fail += check_size(root)
    fail += check_excluded(root, plugin_text)
    fail += check_buckets_listed(root, plugin_text)
    fail += check_cowork_constraints(root)
    check_description_format(root)  # warn-only, no fail contribution

    print()
    if fail == 0:
        green("== All invariants pass ==")
        return 0
    red("== Invariants FAILED ==")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
