#!/usr/bin/env python3
"""list_skills.py — show every SKILL.md with line count + bucket + description first line.

Cross-platform replacement for scripts/list-skills.sh (v3.5+).
Usage::

    python3 scripts/list_skills.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root  # noqa: E402


def first_description_line(skill_md: Path) -> str:
    """Extract first non-empty line of YAML description block."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 2:
        return ""
    frontmatter = parts[1]
    in_desc = False
    for line in frontmatter.splitlines():
        if line.startswith("description:"):
            in_desc = True
            # Same-line value
            value = line.split(":", 1)[1].strip().lstrip("|").strip()
            if value:
                return value[:80]
            continue
        if in_desc:
            stripped = line.lstrip()
            if not stripped:
                continue
            if not line.startswith(" ") and not line.startswith("\t"):
                # Next top-level key — end of description
                break
            return stripped[:80]
    return ""


def main() -> int:
    root = repo_root()
    print(f"{'BUCKET':<12}  {'SKILL':<30}  {'LINES':>5}  DESCRIPTION")
    print(f"{'------':<12}  {'-----':<30}  {'-----':>5}  -----------")

    skill_files: list[Path] = []
    # Nested: skills/<bucket>/<name>/SKILL.md
    skill_files.extend(sorted((root / "skills").glob("*/*/SKILL.md")))
    # Flat (legacy): skills/<name>/SKILL.md
    skill_files.extend(sorted((root / "skills").glob("*/SKILL.md")))

    seen: set[Path] = set()
    for skill_md in skill_files:
        if skill_md in seen:
            continue
        seen.add(skill_md)
        rel_parts = skill_md.relative_to(root).parts
        # Expect skills/<bucket>/<name>/SKILL.md (4 parts) or skills/<name>/SKILL.md (3)
        if len(rel_parts) == 4:
            bucket, name = rel_parts[1], rel_parts[2]
        elif len(rel_parts) == 3:
            bucket, name = "(root)", rel_parts[1]
        else:
            continue
        try:
            lines = sum(1 for _ in skill_md.open(encoding="utf-8", errors="replace"))
        except OSError:
            lines = 0
        desc = first_description_line(skill_md)
        print(f"{bucket:<12}  {name:<30}  {lines:>5}  {desc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
