#!/usr/bin/env python3
"""build_plugin.py — zip shippable bits into shode-house-v<VERSION>.plugin.

Cross-platform replacement for scripts/build-plugin.sh (v3.5+).
Reads version from .claude-plugin/plugin.json.

Excludes: in-progress/, deprecated/, outputs/, *.plugin (prior versions),
.git, .DS_Store, __pycache__.

Usage::

    python3 scripts/build_plugin.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root  # noqa: E402


INCLUDE_DIRS = (
    ".claude-plugin",
    "agents",
    "commands",
    "skills/workflow",
    "skills/ops",
    "skills/ui",
    "skills/style",
    "skills/discipline",
    "references",
    "docs",
)
INCLUDE_FILES = ("README.md", "CHANGELOG.md", "CLAUDE.md", ".pre-commit-config.yaml")
EXCLUDE_PARTS = {".git", ".DS_Store", "__pycache__"}


def should_skip(path: Path) -> bool:
    parts = path.parts
    return any(part in EXCLUDE_PARTS for part in parts)


def main() -> int:
    root = repo_root()
    plugin_json = root / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(plugin_json.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read version from {plugin_json}: {exc}", file=sys.stderr)
        return 1

    out_name = f"shode-house-v{version}.plugin"
    out_path = root / out_name
    tmp_path = Path("/tmp") / out_name if Path("/tmp").exists() else out_path.with_suffix(".plugin.tmp")

    print(f"Building {out_name} (version {version}) ...")
    if tmp_path.exists():
        tmp_path.unlink()

    file_count = 0
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in INCLUDE_DIRS:
            base = root / d
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or should_skip(path):
                    continue
                arcname = path.relative_to(root)
                zf.write(path, arcname)
                file_count += 1
        for f in INCLUDE_FILES:
            p = root / f
            if p.exists() and p.is_file():
                zf.write(p, p.relative_to(root))
                file_count += 1

    # Copy to repo root (overwrite — works on mounted fs where rm may fail)
    out_path.write_bytes(tmp_path.read_bytes())
    if tmp_path != out_path:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    size_kb = out_path.stat().st_size // 1024
    print(f"Built: {out_name} ({size_kb}K, {file_count} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
