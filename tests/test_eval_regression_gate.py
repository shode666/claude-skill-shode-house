"""bd shode-roadmap/B3 -- unit tests for scripts/eval-regression-gate.py (Chris, Phase 3b Standards axis).

Run: pytest tests/test_eval_regression_gate.py -v (from repo root)

Two test tiers:
  - Unit tests on the pure parse functions (parse_baseline_runs / parse_thresholds) called
    directly with synthetic markdown -- no filesystem/module-global patching needed.
  - Integration tests on main() with BASELINE_MD/RUN_ROOT monkeypatched to a tmp_path fixture
    tree (never touches the real eval/baseline/e2e-golden/** -- that directory is Dave's
    protected evidence per the review scope lock).

Adversarial coverage per the review brief's "จุดที่ต้องเพ่งเป็นพิเศษ": every case is designed to
prove the gate FAILs loudly (non-zero exit / FATAL) rather than silently PASSing on bad/missing
input. Several tests below are INTENTIONALLY RED against the current implementation -- they
encode the exit-code contract the script's own docstring promises ("2 = cannot parse/locate
required input") or the behavioral guarantee the gate exists to provide (no cost regression
slips through uncounted). Each RED test is tagged "# FINDING <id> (HIGH/CRITICAL)" and cross-
referenced in outputs/shode-roadmap/C/07-chris-review-b3.md -- they are not flaky, they document
real bugs routed back to Dave for a fix in Phase 2.
"""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_BASELINE_MD = os.path.join(ROOT, 'eval', 'baseline', 'e2e-golden', 'GS1-BASELINE.md')

_spec = importlib.util.spec_from_file_location(
    'eval_regression_gate', os.path.join(ROOT, 'scripts', 'eval-regression-gate.py'))
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


# ---------------------------------------------------------------------------
# helpers -- build synthetic baseline md + per-run score.json fixtures under tmp_path
# ---------------------------------------------------------------------------

def make_baseline_text(rows, cost_bullet='- cost: median <= 1,500,000 (+3%) * p90 <= 1,700,000 (+5%)',
                        heading='## Regression gate', preamble_rows=None):
    """rows: list of (run_no, bd_id, verdict) tuples for the FIRST results table."""
    lines = ['# GS1-reference-refund -- E2E baseline (TEST FIXTURE)', '']
    if preamble_rows:
        lines += preamble_rows + ['']
    lines += ['| run | bd | verdict | X |', '|---|---|---|---|']
    for run_no, bd_id, verdict in rows:
        lines.append(f'| {run_no} | {bd_id} | {verdict} | dummy |')
    lines.append('')
    if heading:
        lines.append(heading)
        if cost_bullet is not None:
            lines.append(cost_bullet)
    return '\n'.join(lines) + '\n'


def write_score(run_root, run_no, scenario='GS1-reference-refund', verdict='PASS',
                 cost=1000000, cost_key='present', raw_text=None):
    """cost_key: 'present' (int cost) | 'absent' (no 'cost' object at all) | 'float' (JSON float)."""
    d = run_root / f'run-{run_no}' / scenario
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'score.json'
    if raw_text is not None:
        p.write_text(raw_text, encoding='utf-8')
        return
    data = {'verdict': verdict}
    if cost_key == 'present':
        data['cost'] = {'total_effective_tokens': cost}
    elif cost_key == 'float':
        data['cost'] = {'total_effective_tokens': float(cost)}
    # 'absent' -> no 'cost' key at all
    p.write_text(json.dumps(data), encoding='utf-8')


def patch_gate(monkeypatch, tmp_path, baseline_text):
    baseline_md = tmp_path / 'GS1-BASELINE.md'
    baseline_md.write_text(baseline_text, encoding='utf-8')
    monkeypatch.setattr(gate, 'BASELINE_MD', str(baseline_md))
    monkeypatch.setattr(gate, 'RUN_ROOT', str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# unit tests -- parse_baseline_runs (pure function, no I/O)
# ---------------------------------------------------------------------------

class TestParseBaselineRuns:
    def test_happy_path_against_real_committed_file(self):
        """given the real, committed GS1-BASELINE.md -- when parsed -- then the exact 3 accepted
        baseline rows come back, in file order (regression guard against the fixture text drifting
        out of sync with reality; read-only, never writes to eval/baseline/**)."""
        md = open(REAL_BASELINE_MD, encoding='utf-8').read()
        rows = gate.parse_baseline_runs(md)
        assert rows == [('4', 'ftx', 'PASS'), ('5', 't4n', 'PASS'), ('6', '0rf', 'PASS')]

    def test_ignores_header_and_separator_rows(self):
        md = make_baseline_text(rows=[])
        rows = gate.parse_baseline_runs(md)
        assert rows == []

    def test_stops_at_first_heading_once_rows_started(self):
        """rows after the FIRST '## ' heading (e.g. a stale-baseline history table further down)
        must never be picked up -- this is what keeps 'รอบก่อน baseline' out of the checked set."""
        md = (
            '# doc\n\n'
            '| run | bd | verdict | X |\n|---|---|---|---|\n'
            '| 1 | aaa | PASS | x |\n'
            '| 2 | bbb | PASS | x |\n\n'
            '## history (should NOT be counted)\n'
            '| 9 | zzz | FAIL | x |\n'
        )
        rows = gate.parse_baseline_runs(md)
        assert rows == [('1', 'aaa', 'PASS'), ('2', 'bbb', 'PASS')]
        assert ('9', 'zzz', 'FAIL') not in rows

    def test_tolerates_extra_whitespace_in_cells(self):
        md = '| run | bd | verdict |\n|---|---|---|\n|   3   |  ccc  |   FAIL   |\n'
        rows = gate.parse_baseline_runs(md)
        assert rows == [('3', 'ccc', 'FAIL')]

    def test_no_table_at_all_returns_empty_list(self):
        rows = gate.parse_baseline_runs('just prose, no pipes anywhere.\n')
        assert rows == []

    # FINDING F5 (Medium/suggestion, characterization -- documents design tradeoff, not a bug in
    # the strict sense): a row silently missing from the table (e.g. accidental deletion during a
    # manual edit) shrinks the checked population with ZERO error signal. The script's own design
    # treats the table as ground truth (docstring: run list is parsed, not hardcoded), so this is
    # not a contract violation -- but it means a maintainer typo that drops one row is
    # indistinguishable from an intentional baseline shrink. No cross-check exists against the
    # narrative "N/N run" sentence elsewhere in the same file.
    def test_missing_row_silently_shrinks_the_checked_population(self):
        full = make_baseline_text(rows=[('1', 'aaa', 'PASS'), ('2', 'bbb', 'PASS'), ('3', 'ccc', 'PASS')])
        one_row_dropped = make_baseline_text(rows=[('1', 'aaa', 'PASS'), ('2', 'bbb', 'PASS')])
        assert len(gate.parse_baseline_runs(full)) == 3
        assert len(gate.parse_baseline_runs(one_row_dropped)) == 2  # no error raised for the drop


# ---------------------------------------------------------------------------
# unit tests -- parse_thresholds (pure function, no I/O)
# ---------------------------------------------------------------------------

class TestParseThresholds:
    def test_happy_path_against_real_committed_file(self):
        # bd:shode-roadmap/C-C2 (R-1), Dave: caps updated after the cost_dimension dedupe fix
        # (message.id dedupe -- old caps were set on a scorer that inflated cost 2.6-2.7x, see
        # GS1-BASELINE.md § Cost metric correction). New caps: median +10% / p90 +12% on the
        # re-scored (deduped) N=3 baseline (median 717,757 / p90 727,503).
        md = open(REAL_BASELINE_MD, encoding='utf-8').read()
        assert gate.parse_thresholds(md) == (789533, 814803)

    def test_scoped_to_cost_bullet_not_narrative_line(self):
        """the narrative line above '## Regression gate' also contains the words median/p90 but
        with the OBSERVED values (1,876,223 / 1,984,149), not the caps (1,932,510 / 2,083,356) --
        parse_thresholds must never pick up the narrative numbers."""
        md = open(REAL_BASELINE_MD, encoding='utf-8').read()
        median_cap, p90_cap = gate.parse_thresholds(md)
        assert median_cap != 1876223 and p90_cap != 1984149

    def test_missing_regression_gate_heading_returns_none(self):
        md = make_baseline_text(rows=[('1', 'aaa', 'PASS')], heading=None)
        assert gate.parse_thresholds(md) is None

    def test_heading_case_mismatch_returns_none(self):
        """'## regression gate' (lowercase g) must not silently match -- and it doesn't: proves
        the gate fails loud (exit 2 upstream in main()) rather than parsing garbage."""
        md = make_baseline_text(rows=[('1', 'aaa', 'PASS')], heading='## regression gate')
        assert gate.parse_thresholds(md) is None

    def test_missing_cost_bullet_returns_none(self):
        md = make_baseline_text(rows=[('1', 'aaa', 'PASS')], cost_bullet=None)
        assert gate.parse_thresholds(md) is None

    def test_cost_bullet_without_commas_still_parses(self):
        """'comma หาย' case: no comma separators -- must still parse (regex is [\\d,]+, commas
        optional)."""
        md = make_baseline_text(rows=[('1', 'aaa', 'PASS')],
                                 cost_bullet='- cost: median <= 1932510 (+3%) * p90 <= 2083356 (+5%)')
        assert gate.parse_thresholds(md) == (1932510, 2083356)

    def test_cost_bullet_present_but_no_median_or_p90_numbers_returns_none(self):
        md = make_baseline_text(rows=[('1', 'aaa', 'PASS')],
                                 cost_bullet='- cost: see dashboard for numbers')
        assert gate.parse_thresholds(md) is None

    def test_next_heading_after_regression_gate_bounds_the_section(self):
        """a 'known gap' bullet further down that happens to also start with '- cost:' must NOT
        leak into the Regression gate section's threshold parse."""
        md = (make_baseline_text(rows=[('1', 'aaa', 'PASS')]) +
              '\n## known gap\n- cost: median <= 999 (+3%) * p90 <= 999 (+5%)\n')
        assert gate.parse_thresholds(md) == (1500000, 1700000)

    # FINDING F4 (Medium): abbreviated notation ("1.9M") is not rejected -- MEDIAN_CAP_RE /
    # P90_CAP_RE ([\d,]+) matches only the leading digit run before the literal '.', so "1.9M"
    # silently becomes the integer 1 instead of failing to parse. In main() this still fails the
    # overall gate LOUDLY (real median always > 1) so it is not a false-green -- but it produces a
    # confusing false-block ("cap 1") that looks like a data-entry bug, not a clean FATAL asking a
    # human to fix the format. Characterization test, not a contract violation -- kept GREEN.
    def test_abbreviated_M_notation_is_misparsed_not_rejected(self):
        md = make_baseline_text(
            rows=[('1', 'aaa', 'PASS')],
            cost_bullet='- cost: median <= 1.9M tok * p90 <= 2.1M tok')
        median_cap, p90_cap = gate.parse_thresholds(md)
        assert (median_cap, p90_cap) == (1, 2), (
            "parse_thresholds silently turned '1.9M'/'2.1M' into (1, 2) instead of failing to "
            "parse -- see review finding F4 (Medium)")


# ---------------------------------------------------------------------------
# integration tests -- main() end to end (BASELINE_MD / RUN_ROOT monkeypatched to tmp_path)
# ---------------------------------------------------------------------------

class TestMainHappyAndParserFailures:
    def test_all_pass_within_cap_exits_0(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('1', 'aaa', 'PASS'), ('2', 'bbb', 'PASS')]))
        write_score(tmp_path, 1, cost=1000000)
        write_score(tmp_path, 2, cost=1100000)
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 0
        assert 'Overall: PASS' in out

    def test_baseline_md_not_found_exits_2(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(gate, 'BASELINE_MD', str(tmp_path / 'nope-GS1-BASELINE.md'))
        monkeypatch.setattr(gate, 'RUN_ROOT', str(tmp_path))
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 2
        assert 'FATAL' in out and 'not found' in out

    def test_no_rows_parsed_exits_2(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path, 'no table here at all\n')
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 2
        assert 'FATAL' in out and 'no baseline run rows parsed' in out

    def test_regression_gate_heading_missing_exits_2(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path,
                    make_baseline_text(rows=[('1', 'aaa', 'PASS')], heading=None))
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 2
        assert 'FATAL' in out and 'Regression gate' in out

    def test_cost_bullet_missing_exits_2(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path,
                    make_baseline_text(rows=[('1', 'aaa', 'PASS')], cost_bullet=None))
        code = gate.main()
        assert code == 2

    def test_score_json_file_missing_exits_1_not_0(self, tmp_path, monkeypatch, capsys):
        """run-7 declared in the table but score.json was never produced/committed; run-8 is a
        normal healthy run -- must FAIL loud (exit 1), never silently PASS just because run-7's
        table verdict says PASS."""
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('7', 'xyz', 'PASS'), ('8', 'qrs', 'PASS')]))
        # deliberately do NOT write eval/.../run-7/GS1-reference-refund/score.json
        write_score(tmp_path, 8, cost=1000000)
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 1
        assert 'score.json not found' in out
        assert 'Overall: FAIL' in out

    # FINDING F6 (Low/observability): when the ONLY declared run has no score.json, `costs` ends
    # up empty and main() hits the earlier "no cost data collected" FATAL (exit 2) before the
    # already-True `fail` flag from the "score.json not found" line ever gets reported as the
    # exit-1 regression path. Root cause and exit code are therefore inconsistent depending on
    # whether any OTHER run in the table happened to contribute valid cost data -- not a
    # false-green (still loud/non-zero), just a confusing exit-code split for the same root cause.
    def test_F6_single_run_missing_score_json_exits_2_not_1_inconsistent_with_multi_run_case(
            self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path, make_baseline_text(rows=[('7', 'xyz', 'PASS')]))
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 2  # NOT 1, even though the same "score.json not found" root cause as above
        assert 'score.json not found' in out
        assert 'no cost data collected' in out

    def test_table_verdict_disagrees_with_score_json_exits_1(self, tmp_path, monkeypatch, capsys):
        """mutation-equivalent of Aaron's manual Mutation A (table PASS/FAIL flip vs score.json)."""
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('1', 'aaa', 'FAIL'), ('2', 'bbb', 'PASS')]))
        write_score(tmp_path, 1, verdict='PASS', cost=1000000)  # score.json says PASS, table says FAIL
        write_score(tmp_path, 2, verdict='PASS', cost=1000000)
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 1
        assert 'Overall: FAIL' in out

    def test_cost_over_cap_exits_1(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('1', 'aaa', 'PASS')], cost_bullet='- cost: median <= 100 (+3%) * p90 <= 100 (+5%)'))
        write_score(tmp_path, 1, cost=9999999)
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 1
        assert 'Overall: FAIL' in out

    def test_all_costs_missing_exits_2(self, tmp_path, monkeypatch, capsys):
        patch_gate(monkeypatch, tmp_path, make_baseline_text(rows=[('1', 'aaa', 'PASS')]))
        write_score(tmp_path, 1, verdict='PASS', cost_key='absent')
        code = gate.main()
        out = capsys.readouterr().out
        assert code == 2
        assert 'no cost data collected' in out


class TestFindingsFalseGreen:
    """RED against current implementation -- each documents a HIGH/CRITICAL false-green finding
    from the Phase 3b Standards review (outputs/shode-roadmap/C/07-chris-review-b3.md). Kept
    un-skipped on purpose: a green full suite here would be exactly the false confidence the
    review brief warns against ("false-green = ไร้ค่า")."""

    def test_F1_missing_cost_field_on_one_run_must_not_silently_pass(self, tmp_path, monkeypatch, capsys):
        """FINDING F1 (HIGH). run-2's score.json has verdict=PASS but NO 'cost' object at all
        (e.g. scorer crashed mid-write for that run only). Desired: the gate must not silently
        drop that run from the cost population and PASS on the remaining runs alone -- missing
        per-run cost data is itself something the gate should refuse to certify silently.
        Actual (main.py:137-138): `if isinstance(cost, int): costs.append(cost)` runs
        UNCONDITIONALLY after the ok-check, which never inspects `cost` -- so a run with
        verdict=PASS/table=PASS but no cost data at all just quietly never enters the median/p90
        sample. Exit stays 0."""
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('1', 'aaa', 'PASS'), ('2', 'bbb', 'PASS')],
            cost_bullet='- cost: median <= 2,000,000 (+3%) * p90 <= 2,000,000 (+5%)'))
        write_score(tmp_path, 1, verdict='PASS', cost=1000000)
        write_score(tmp_path, 2, verdict='PASS', cost_key='absent')  # no cost data recorded at all
        code = gate.main()
        out = capsys.readouterr().out
        assert code != 0, (
            "false-green: gate returned PASS (exit 0) while run-2 had no cost data recorded at "
            f"all -- it was silently dropped from the median/p90 sample. stdout was:\n{out}")

    def test_F2_json_float_cost_is_silently_dropped_causing_a_real_false_pass(self, tmp_path, monkeypatch, capsys):
        """FINDING F2 (CRITICAL). Concrete demonstration of an ACTUAL cost regression slipping
        through: run-21 legitimately cost 3,000,000 tokens (over cap) but its score.json recorded
        that number as a JSON float (`3000000.0`) rather than an int -- a wholly plausible
        serialization difference depending on the scorer's json.dump path.
        `isinstance(cost, int)` (main.py:137) is False for a float, so run-21's cost is silently
        excluded from `costs`. Only run-20's 1,000,000 (int) survives -> median=1,000,000, comfortably
        under the 1,500,000 cap -> gate reports PASS even though a real regression run (3,000,000
        tokens, 2x over cap) was in the baseline table with verdict=PASS the whole time."""
        patch_gate(monkeypatch, tmp_path, make_baseline_text(
            rows=[('20', 'aaa', 'PASS'), ('21', 'bbb', 'PASS')],
            cost_bullet='- cost: median <= 1,500,000 (+3%) * p90 <= 1,500,000 (+5%)'))
        write_score(tmp_path, 20, verdict='PASS', cost=1000000, cost_key='present')
        write_score(tmp_path, 21, verdict='PASS', cost=3000000, cost_key='float')  # regression, but as float
        code = gate.main()
        out = capsys.readouterr().out
        assert code != 0, (
            "false-green: a run costing 3,000,000 tok (2x the 1,500,000 cap) was silently "
            f"excluded from the median because its score.json stored it as a JSON float, not an "
            f"int -- gate reported PASS anyway. stdout was:\n{out}")

    def test_F3_corrupted_score_json_should_exit_2_not_crash(self, tmp_path, monkeypatch):
        """FINDING F3 (HIGH). The script's own docstring promises exit code 2 for 'cannot
        parse/locate required input'. A syntactically-corrupt score.json (e.g. truncated write,
        disk-full mid-commit) is exactly that case -- but `json.load(open(sp, ...))` (main.py:129)
        is not wrapped in a try/except, so it raises an uncaught json.JSONDecodeError instead of
        the documented, controlled FATAL exit 2. CI would show a raw Python traceback instead of
        the clean 'FATAL: ...' message every other unparseable-input path produces."""
        patch_gate(monkeypatch, tmp_path, make_baseline_text(rows=[('1', 'aaa', 'PASS')]))
        write_score(tmp_path, 1, raw_text='{not valid json,,,')
        code = gate.main()  # desired: returns 2 cleanly; actual: raises json.JSONDecodeError
        assert code == 2


# ---------------------------------------------------------------------------
# property-based tests (Hypothesis) -- pure-function invariants
# ---------------------------------------------------------------------------

hyp = pytest.importorskip('hypothesis')
from hypothesis import given, settings, strategies as st  # noqa: E402


@given(n=st.integers(min_value=0, max_value=999_999_999))
@settings(max_examples=200)
def test_property_threshold_roundtrips_through_comma_formatting(n):
    """for ANY non-negative integer, formatting it with thousands separators and embedding it in
    a well-formed cost bullet must parse back to exactly that integer -- the digit/comma-stripping
    logic (MEDIAN_CAP_RE + int(...replace(',', ''))) must be lossless for its supported domain."""
    bullet = f'- cost: median <= {n:,} (+3%) * p90 <= {n:,} (+5%)'
    md = make_baseline_text(rows=[('1', 'aaa', 'PASS')], cost_bullet=bullet)
    assert gate.parse_thresholds(md) == (n, n)


@given(
    rows=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=9999).map(str),
            st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=8),
            st.sampled_from(['PASS', 'FAIL']),
        ),
        min_size=0, max_size=8,
    )
)
@settings(max_examples=200)
def test_property_parse_baseline_runs_matches_row_count_exactly(rows):
    """for ANY list of well-formed table rows, parse_baseline_runs must return exactly that many
    rows, in order, with fields untouched -- no row dropped or duplicated, regardless of run
    count or bd-id content (within the [A-Za-z0-9]+ domain the regex declares it supports)."""
    md = make_baseline_text(rows=rows)
    parsed = gate.parse_baseline_runs(md)
    assert parsed == rows
