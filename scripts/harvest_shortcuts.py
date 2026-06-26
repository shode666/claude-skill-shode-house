#!/usr/bin/env python3
"""harvest_shortcuts.py — รวบ `shortcut(bd:N):` comment ทั้ง repo เป็น debt ledger.

จาก ponytail `/ponytail-debt`: ทางลัดที่ YAGNI ladder ตัดไว้ ต้อง track ไม่ให้ "later"
กลาย "never". Grep หา convention `shortcut(bd:<id>): <reason>; upgrade -> <path>`,
group ตาม bd id, เขียน outputs/DEBT-<date>.md.

Report tool — exit 0 เสมอ (ไม่ใช่ gate). Stdlib only. Python 3.9+.

Usage:
  python3 scripts/harvest_shortcuts.py            # scan repo, write ledger
  python3 scripts/harvest_shortcuts.py --print    # print only, no file
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, green, yellow  # noqa: E402

# Match: shortcut(bd:42): reason text  (upgrade path optional, kept in reason)
PATTERN = re.compile(r"shortcut\(bd:(\d+)\):\s*(.+)", re.IGNORECASE)
SKIP_DIRS = {".git", "node_modules", "__pycache__", "outputs", ".beads"}
# Text-ish extensions worth scanning for inline comments.
SCAN_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".kt", ".rs",
    ".php", ".dart", ".swift", ".sql", ".vue", ".rb", ".cs", ".cpp", ".c",
    ".sh", ".yaml", ".yml", ".md",
}


def scan(root: Path) -> list[tuple[int, str, int, str]]:
    """Return list of (bd_id, rel_path, line_no, reason)."""
    hits: list[tuple[int, str, int, str]] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in SCAN_EXT:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            m = PATTERN.search(line)
            if m:
                hits.append((int(m.group(1)), str(path.relative_to(root)), i, m.group(2).strip()))
    return hits


def render(hits: list[tuple[int, str, int, str]]) -> str:
    out = [f"# Debt ledger — deferred shortcuts ({date.today().isoformat()})", ""]
    if not hits:
        out += ["ไม่พบ `shortcut(bd:N):` ทางลัด — repo clean หรือยังไม่ใช้ convention.", ""]
        return "\n".join(out)
    out += [f"พบ {len(hits)} ทางลัด ใน {len({h[1] for h in hits})} ไฟล์.", ""]
    by_bd: dict[int, list[tuple[int, str, int, str]]] = {}
    for h in hits:
        by_bd.setdefault(h[0], []).append(h)
    for bd_id in sorted(by_bd):
        out.append(f"## bd:{bd_id}")
        out.append("")
        out.append("| ไฟล์ | บรรทัด | upgrade path / reason |")
        out.append("|---|---|---|")
        for _, rel, line_no, reason in sorted(by_bd[bd_id]):
            safe = reason.replace("|", "\\|")
            out.append(f"| `{rel}` | {line_no} | {safe} |")
        out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    root = repo_root()
    hits = scan(root)
    report = render(hits)
    if "--print" in argv:
        print(report)
        return 0
    out_dir = root / "outputs"
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / f"DEBT-{date.today().isoformat()}.md"
    dest.write_text(report, encoding="utf-8")
    if hits:
        yellow(f"  {len(hits)} deferred shortcut(s) → {dest.relative_to(root)}")
    else:
        green(f"  no deferred shortcuts → {dest.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
