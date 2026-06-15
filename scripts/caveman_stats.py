#!/usr/bin/env python3
"""caveman_stats.py — ประเมิน token saving จาก caveman compression.

จาก caveman `/caveman-stats`: พิสูจน์ ROI ด้วยตัวเลข แทนการเดา.
เทียบ before vs after file (เช่น CLAUDE.full.md vs CLAUDE.md), ประเมิน token
(~chars/4), คิด %saved + USD ที่ rate ที่กำหนด, เขียน outputs/CAVEMAN-STATS-<date>.md.

ตัวเลข = **estimate** (chars/4 heuristic) ไม่ใช่ API-measured. ระบุชัดตอน claim
(evidence discipline). Stdlib only. Python 3.9+.

Usage:
  python3 scripts/caveman_stats.py BEFORE AFTER [--rate-per-mtok 3.0]
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import repo_root, red, green  # noqa: E402

CHARS_PER_TOKEN = 4  # rough heuristic; not API-measured


def est_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def main(argv: list[str]) -> int:
    rate = 3.0  # USD per 1M tokens (default; override with --rate-per-mtok)
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--rate-per-mtok" and i + 1 < len(argv):
            try:
                rate = float(argv[i + 1])
            except ValueError:
                red(f"  ✗ invalid rate: {argv[i + 1]}")
                return 1
            i += 2
            continue
        args.append(argv[i])
        i += 1

    if len(args) != 2:
        red("  usage: caveman_stats.py BEFORE AFTER [--rate-per-mtok N]")
        return 1

    before_p, after_p = Path(args[0]), Path(args[1])
    try:
        before = before_p.read_text(encoding="utf-8", errors="replace")
        after = after_p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        red(f"  ✗ {exc}")
        return 1

    tb, ta = est_tokens(before), est_tokens(after)
    saved = tb - ta
    pct = (saved / tb * 100) if tb else 0.0
    usd_per_session = saved / 1_000_000 * rate

    lines = [
        f"# Caveman stats — {date.today().isoformat()}",
        "",
        f"- before: `{before_p}` — ~{tb:,} tok ({len(before):,} chars)",
        f"- after:  `{after_p}` — ~{ta:,} tok ({len(after):,} chars)",
        f"- **saved: ~{saved:,} tok ({pct:.1f}%)**",
        f"- est. ${usd_per_session:.5f}/session @ ${rate}/Mtok (input)",
        "",
        "> Estimate (chars/4 heuristic), input tokens only — ไม่ใช่ API-measured.",
        "",
    ]
    report = "\n".join(lines)

    out_dir = repo_root() / "outputs"
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / f"CAVEMAN-STATS-{date.today().isoformat()}.md"
    dest.write_text(report, encoding="utf-8")
    print(report)
    green(f"  → {dest.relative_to(repo_root())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
