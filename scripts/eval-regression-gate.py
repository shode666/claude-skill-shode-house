#!/usr/bin/env python3
"""bd B3 -- GS1 E2E regression gate. stdlib only, python3.9+.

  scripts/eval-regression-gate.py

CI-safe (no live agent run): reads the *committed* per-run evidence under
eval/baseline/e2e-golden/run-*/GS1-reference-refund/score.json (each score.json was produced
by a real, already-completed Claude Code CLI session -- CI never spawns a live E2E run here,
because one GS1 run costs ~1.9M tokens / ~11 min; see eval/baseline/e2e-golden/GS1-BASELINE.md
"plugin/runner/date" header for how each score.json was actually generated).

Two things this gate proves on every CI run:
  1. Every run row listed in GS1-BASELINE.md's results table still shows verdict=PASS in its
     committed score.json (0 tolerance on behavior -- GS1-BASELINE.md itself declares this:
     "behavior: ทุก run ต้อง PASS ทุก critical dimension (0 tolerance)").
  2. median/p90 of those runs' cost.total_effective_tokens is within the tolerance already
     declared in the SAME "## Regression gate" section of GS1-BASELINE.md, using the SAME
     formula + threshold this repo already applies to A/B baseline comparisons elsewhere
     (scripts/usage-report.py:53-55 med_p90(), :72-75 "median +3% / p90 +5%") -- this gate does
     NOT invent a new number; it re-derives the caps by parsing GS1-BASELINE.md and reuses the
     existing percentile function by import (not a re-implementation, to avoid the two formulas
     silently drifting apart over time).

Both the run list AND the cost caps are PARSED from GS1-BASELINE.md, not hardcoded here --
so the next time a maintainer records a new N=3 (or N=5, ...) baseline and rewrites that file's
table + "## Regression gate" line, this script re-validates the new numbers with zero code change.

Exit codes: 0 = PASS · 1 = regression (behavior or cost) · 2 = cannot parse/locate required input.
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_MD = os.path.join(ROOT, 'eval', 'baseline', 'e2e-golden', 'GS1-BASELINE.md')
RUN_ROOT = os.path.join(ROOT, 'eval', 'baseline', 'e2e-golden')
SCENARIO = 'GS1-reference-refund'

# reuse the exact percentile formula already used for baseline regression elsewhere in this
# repo (importlib because the filename has a hyphen -- same pattern tests/test_eval_scorer.py
# already uses to import scripts/eval-scorer.py).
_spec = importlib.util.spec_from_file_location('usage_report', os.path.join(ROOT, 'scripts', 'usage-report.py'))
usage_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(usage_report)
med_p90 = usage_report.med_p90

# matches rows of the FIRST results table in GS1-BASELINE.md, e.g.:
# "| 4 | ftx | PASS | 5/5 card [check] (seq) | PASS | PASS | PASS | PASS | CLOSED | 1,876,223 | 12.0 min |"
TABLE_ROW_RE = re.compile(r'^\|\s*(\d+)\s*\|\s*([A-Za-z0-9]+)\s*\|\s*(PASS|FAIL)\s*\|')
# scoped to the "## Regression gate" section's own "- cost:" bullet only (NOT the narrative
# baseline-stats line above it, which also contains the words "median"/"p90" but with the
# observed values, not the caps) -- e.g. "- cost: median <= 1,932,510 (+3%) * p90 <= 2,083,356
# (+5%) -- ...". [^0-9]*? (lazy, non-digit) skips over the "<=" glyph without assuming which
# comparator character the file uses.
GATE_HEADING_RE = re.compile(r'^##\s*Regression gate\b.*$', re.MULTILINE)
COST_BULLET_RE = re.compile(r'^-\s*cost:.*$', re.MULTILINE)
MEDIAN_CAP_RE = re.compile(r'median[^0-9]*?([\d,]+)')
P90_CAP_RE = re.compile(r'p90[^0-9]*?([\d,]+)')


def parse_baseline_runs(md_text):
    """-> list of (run_no, bd_id, table_verdict) from the FIRST markdown table only.

    Stops at the first heading line once rows have started, so the "## รอบก่อน baseline"
    history table further down (explicitly annotated "เก็บเป็น evidence, ไม่นับ" -- kept as
    evidence, not counted) is never picked up as a baseline row.
    """
    rows = []
    for line in md_text.splitlines():
        if line.startswith('## ') and rows:
            break
        m = TABLE_ROW_RE.match(line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def parse_thresholds(md_text):
    """-> (median_cap, p90_cap) parsed strictly from the '- cost:' bullet inside the
    '## Regression gate' section -- never from the narrative baseline-stats line above it,
    which reports the *observed* median/p90, not the *caps*."""
    gm = GATE_HEADING_RE.search(md_text)
    if not gm:
        return None
    section = md_text[gm.end():]
    next_heading = re.search(r'^##\s', section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]
    bm = COST_BULLET_RE.search(section)
    if not bm:
        return None
    bullet = bm.group(0)
    med = MEDIAN_CAP_RE.search(bullet)
    p90 = P90_CAP_RE.search(bullet)
    if not (med and p90):
        return None
    return int(med.group(1).replace(',', '')), int(p90.group(1).replace(',', ''))


def main():
    if not os.path.isfile(BASELINE_MD):
        print(f'FATAL: {BASELINE_MD} not found')
        return 2
    md = open(BASELINE_MD, encoding='utf-8').read()

    runs = parse_baseline_runs(md)
    if not runs:
        print('FATAL: no baseline run rows parsed from GS1-BASELINE.md results table')
        return 2

    thresholds = parse_thresholds(md)
    if not thresholds:
        print("FATAL: could not parse 'median ... p90 ...' cost caps from "
              "GS1-BASELINE.md § Regression gate")
        return 2
    median_cap, p90_cap = thresholds

    fail = False
    costs = []
    print(f'GS1 regression gate -- {len(runs)} baseline run(s) declared in GS1-BASELINE.md')
    for run_no, bd_id, table_verdict in runs:
        sp = os.path.join(RUN_ROOT, f'run-{run_no}', SCENARIO, 'score.json')
        if not os.path.isfile(sp):
            print(f'  run-{run_no} ({bd_id}): FAIL -- score.json not found at {sp}')
            fail = True
            continue
        data = json.load(open(sp, encoding='utf-8'))
        verdict = data.get('verdict')
        cost = data.get('cost', {}).get('total_effective_tokens')
        ok = verdict == 'PASS' and table_verdict == 'PASS'
        print(f'  run-{run_no} ({bd_id}): score.json verdict={verdict} table={table_verdict} '
              f"cost={cost if cost is None else format(cost, ',')} tok -- {'PASS' if ok else 'FAIL'}")
        if not ok:
            fail = True
        if isinstance(cost, int):
            costs.append(cost)

    if not costs:
        print('FATAL: no cost data collected from any run -- cannot check cost tolerance')
        return 2

    median, p90 = med_p90(costs)
    cost_ok_med = median <= median_cap
    cost_ok_p90 = p90 <= p90_cap
    print(f"\ncost: median {median:,.0f} tok (cap {median_cap:,}) -- {'PASS' if cost_ok_med else 'FAIL'}")
    print(f"cost: p90    {p90:,.0f} tok (cap {p90_cap:,}) -- {'PASS' if cost_ok_p90 else 'FAIL'}")
    if not (cost_ok_med and cost_ok_p90):
        fail = True

    print(f"\nOverall: {'FAIL -- regression vs GS1-BASELINE.md' if fail else 'PASS'}")
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
