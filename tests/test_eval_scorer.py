"""bd B1 — eval-scorer unit tests. One test per AC-1..8 (01-bella-1a.md §6) + alias/depth-tree tests.
Run: pytest tests/test_eval_scorer.py -v (from repo root /home/claude/shode-house-b1)
"""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'eval', 'fixtures', 'transcripts')
GOLDEN = os.path.join(ROOT, 'eval', 'scenarios', 'golden.json')
# iter6b (Oliver bd:B1, mechanical): repo's real outputs/ is gitignored, so synthetic fixture
# artifacts (SPEC-bd-*.md, bd-101/, bd-104/) must not live there or they'd never be committed.
# Moved to a tracked fixture location; golden.json's globs stay "outputs/..." relative to this root.
FIXTURE_ROOT = os.path.join(ROOT, 'eval', 'fixtures', 'outputs-root')
FIXTURE_OUTPUTS_DIR = os.path.join(FIXTURE_ROOT, 'outputs')

spec = importlib.util.spec_from_file_location('eval_scorer', os.path.join(ROOT, 'scripts', 'eval-scorer.py'))
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)


def run(case, scenario_id, outputs_dir=None, tmp_out=None):
    scen = scorer.load_golden(GOLDEN, scenario_id)
    fixture_root = outputs_dir or FIXTURE_ROOT
    result, code = scorer.score(os.path.join(FIX, case), scen, fixture_root)
    return result, code


# --- AC-1: given real transcript, scorer produces output format + JSON file at requested path ---
def test_ac01_output_format_and_json_file(tmp_path):
    result, code = run('routing-ok', 'GS2-implement-backend')
    assert code == 0
    assert result['verdict'] == 'PASS'
    assert set(result['dimensions']) == {'routing', 'spec_fidelity', 'security_trigger',
                                          'evidence', 'anti_puppet', 'bd_end_state'}
    # CLI writes score.json to --out
    rc = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'eval-scorer.py'),
                          os.path.join(FIX, 'routing-ok'), '--scenario', 'GS2-implement-backend',
                          '--outputs-dir', FIXTURE_OUTPUTS_DIR,
                          '--out', str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
    out_file = tmp_path / 'GS2-implement-backend' / 'score.json'
    assert out_file.is_file(), rc.stdout + rc.stderr
    data = json.loads(out_file.read_text())
    assert data['verdict'] == 'PASS'


# --- AC-2: routing wrong order -> Routing FAIL with step identified ---
def test_ac02_routing_wrong_order_fail():
    result, code = run('routing-wrong-order', 'GS2-implement-backend')
    assert result['dimensions']['routing']['verdict'] == 'FAIL'
    assert 'step 1' in result['dimensions']['routing']['detail']
    assert code == 1


# --- AC-3: GS3 fixture, business-analyst output doesn't mention AC-4 gap -> Spec fidelity FAIL ---
def test_ac03_spec_gap_silent_pass_fail():
    result, code = run('spec-gap-missed', 'GS3-spec-axis-gap')
    assert result['dimensions']['spec_fidelity']['verdict'] == 'FAIL'
    assert 'AC-4' in result['dimensions']['spec_fidelity']['detail']
    assert code == 1


# --- AC-4: GS4 fixture, no relay to main (subagent answers ambiguity itself) -> relay violation FAIL ---
def test_ac04_relay_violation_fail():
    result, code = run('relay-violation', 'GS4-askuser-relay')
    assert result['dimensions']['anti_puppet']['verdict'] == 'FAIL'
    assert 'relay' in result['dimensions']['anti_puppet']['detail'].lower() or \
           'AskUserQuestion' in result['dimensions']['anti_puppet']['detail']
    assert code == 1


# --- AC-5: claim "เสร็จแล้ว" without adjacent tool_result -> Anti-puppet FAIL quoting the line ---
def test_ac05_anti_puppet_claim_without_evidence():
    result, code = run('anti-puppet-violation', 'GS2-implement-backend')
    d = result['dimensions']['anti_puppet']
    assert d['verdict'] == 'FAIL'
    assert 'เสร็จแล้ว' in d['detail']
    assert result['dimensions']['evidence']['verdict'] == 'FAIL'
    assert code == 1


# --- AC-6: PII/money keyword present but security-engineer not spawned -> Security trigger FAIL ---
def test_ac06_security_trigger_missed():
    result, code = run('security-trigger-missed', 'GS5-phase3b-sensitive')
    d = result['dimensions']['security_trigger']
    assert d['verdict'] == 'FAIL'
    assert 'shode-house:security-engineer' in d['detail']
    assert code == 1


# --- AC-7: usage-report.py med_p90 still works the same way for e2e scenario dirs (reuse, not reimplemented) ---
def test_ac07_usage_report_med_p90_reused():
    usage_report = '/home/claude/shode-house-a1/B1/repo/scripts/usage-report.py'
    if not os.path.isfile(usage_report):
        pytest.skip('usage-report.py not present in this tree (reused as-is, not modified per constraint)')
    uspec = importlib.util.spec_from_file_location('usage_report', usage_report)
    ur = importlib.util.module_from_spec(uspec)
    uspec.loader.exec_module(ur)
    m, p90 = ur.med_p90([10, 20, 30])
    assert m == 20 and p90 == 30


# --- AC-8: transcript truncated / evidence missing -> UNSCORABLE, never PASS ---
def test_ac08_truncated_unscorable():
    result, code = run('truncated', 'GS2-implement-backend')
    assert result['verdict'] == 'UNSCORABLE'
    assert code == 2
    assert any('records' in r for r in result['reasons'])


# --- extra: tool name alias Agent vs Task both recognized as spawn ---
def test_agent_task_alias():
    session = scorer.load_session(os.path.join(FIX, 'routing-ok'))
    idx = scorer.build_spawn_index(session)
    # nested spawn inside agent-ba1.jsonl uses name="Task"
    ba_batches = idx['file_batches']['agent-ba1']
    names = {s['name'] for batch in ba_batches for s in batch}
    assert 'Task' in names
    main_names = {s['name'] for batch in idx['main_batches'] for s in batch}
    assert 'Agent' in main_names


# --- extra: subagent tree depth 2 detected (business-analyst -> solution-architect nested) ---
# (iter4 cleanup: max_spawn_depth() removed per Chris's cut list, inlined here directly)
def test_subagent_tree_depth_2():
    session = scorer.load_session(os.path.join(FIX, 'routing-ok'))
    idx = scorer.build_spawn_index(session)
    depths = [d for d in idx['depth_by_agent'].values() if d is not None]
    max_depth = max(depths) if depths else 0
    assert max_depth == 2
    assert idx['depth_by_agent']['agent-nested1'] == 2


# --- extra: bd end_state — no bd on PATH (this sandbox truly has none) -> unscorable, never PASS ---
def test_bd_end_state_unscorable_when_bd_absent():
    assert shutil.which('bd') is None, 'test assumes sandbox has no bd binary'
    scen = scorer.load_golden(GOLDEN, 'GS2-implement-backend')
    verdict, detail = scorer.bd_end_state(scen)
    assert verdict == 'UNSCORABLE'
    assert 'PATH' in detail


# --- extra: bd end_state — with a PATH shim, scorer calls `bd show <id>` itself and can PASS/FAIL ---
def test_bd_end_state_with_path_shim(tmp_path, monkeypatch):
    bd_bin = tmp_path / 'bd'
    bd_bin.write_text('#!/bin/sh\necho "bd-101: CLOSED verdict=CLOSED"\n')
    bd_bin.chmod(bd_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv('PATH', str(tmp_path) + os.pathsep + os.environ['PATH'])
    scen = scorer.load_golden(GOLDEN, 'GS2-implement-backend')
    verdict, detail = scorer.bd_end_state(scen)
    assert verdict == 'PASS', detail


# ===== iter 1 (Oliver): real-transcript smoke found one missing input (spec file path
# mismatch) wiped every dimension to UNSCORABLE. Fix: dimensions computed independently. =====

# --- iter1: a dimension missing its own input goes UNSCORABLE on its own; siblings keep their
# real PASS/FAIL/N-A verdict (this is exactly Oliver's maintainer-machine repro, reproduced here
# without a real transcript by pointing a known-good fixture at a spec_file that doesn't exist) ---
def test_iter1_missing_spec_file_does_not_wipe_other_dimensions():
    scen = dict(scorer.load_golden(GOLDEN, 'GS2-implement-backend'))
    scen['spec_file'] = 'outputs/DOES-NOT-EXIST-SPEC.md'
    result, code = scorer.score(os.path.join(FIX, 'routing-ok'), scen, FIXTURE_ROOT)
    assert result['dimensions']['spec_fidelity']['verdict'] == 'UNSCORABLE'
    assert 'DOES-NOT-EXIST-SPEC.md' in result['dimensions']['spec_fidelity']['detail']
    # routing/evidence/anti_puppet must NOT be wiped -- they had everything they needed
    assert result['dimensions']['routing']['verdict'] == 'PASS'
    assert result['dimensions']['evidence']['verdict'] == 'PASS'
    assert result['dimensions']['anti_puppet']['verdict'] == 'PASS'
    # overall: UNSCORABLE (a critical dim is unscorable) but never PASS, and never a false FAIL either
    assert result['verdict'] == 'UNSCORABLE'
    assert code == 2
    assert any('spec_fidelity' in r for r in result['reasons'])


# --- iter1: dimensions dict is always fully populated (never {} like the old blanket-wipe) ---
def test_iter1_dimensions_always_fully_populated_even_when_unscorable():
    result, code = run('truncated', 'GS2-implement-backend')
    assert result['verdict'] == 'UNSCORABLE'
    assert set(result['dimensions']) == {'routing', 'spec_fidelity', 'security_trigger',
                                          'evidence', 'anti_puppet', 'bd_end_state'}
    # spec_fidelity had everything it needed (real SPEC-bd-101.md + artifacts exist) -> still PASS
    # even though routing is starved of input in this same run
    assert result['dimensions']['routing']['verdict'] == 'UNSCORABLE'
    assert result['dimensions']['spec_fidelity']['verdict'] == 'PASS'


# --- iter1: reconstructed routing tree printed under Routing regardless of scenario match ---
def test_iter1_routing_tree_reconstructed_and_printed(capsys):
    result, code = run('routing-ok', 'GS2-implement-backend')
    tree = result['routing_tree']
    assert len(tree) == 4  # dev, chris||quinn, ba, nested solution-architect
    assert any('shode-house:developer' in line and line.startswith('depth1') for line in tree)
    assert any('depth2' in line and 'shode-house:solution-architect' in line and 'issued by agent-ba1' in line
               for line in tree)
    scorer.print_report(result)
    captured = capsys.readouterr().out
    assert 'routing tree (reconstructed, informational):' in captured
    assert 'shode-house:business-analyst' in captured


# --- iter1: bd_end_state is not critical -- absence of `bd` must not force overall UNSCORABLE
# on an otherwise-clean run (avoids every run being UNSCORABLE just because no bd on PATH) ---
def test_iter1_bd_end_state_not_critical_for_overall_verdict():
    result, code = run('routing-ok', 'GS2-implement-backend')
    assert result['dimensions']['bd_end_state']['verdict'] == 'UNSCORABLE'
    assert result['verdict'] == 'PASS'
    assert code == 0


# ===== iter 2 (Oliver): real transcript spawned a declared-parallel step's members in two
# consecutive assistant messages 21s apart -> old code compared whole batches as sets and
# FAILed with "order violation" on the first partial batch. Fix: a step's members can arrive
# in any order, across any number of separate messages, as long as they land strictly between
# the previous and next step's members. `parallel` (same assistant message) is now informational
# only, never a FAIL condition. =====

_EXPECTED_DEV_THEN_REVIEW_PARALLEL = [
    {"agents": ["shode-house:developer"]},
    {"agents": ["shode-house:code-reviewer", "shode-house:qa-engineer"], "parallel": True},
]


def _spawn(agent_type, ts, agent_id='x'):
    return {'agentType': agent_type, 'timestamp': ts, 'agentId': agent_id}


# --- iter2: order A — code-reviewer spawned first, qa-engineer 21s later, 2 separate messages ---
def test_iter2_parallel_step_two_messages_order_a_passes_not_fail():
    main_batches = [
        [_spawn('shode-house:developer', 't0')],
        [_spawn('shode-house:code-reviewer', 't1')],
        [_spawn('shode-house:qa-engineer', 't2')],
    ]
    verdict, detail, steps = scorer.check_routing(_EXPECTED_DEV_THEN_REVIEW_PARALLEL, main_batches, False)
    assert verdict == 'PASS', detail
    assert 'order violation' not in detail
    step2 = steps[1]
    assert step2['agents'] == ['shode-house:code-reviewer', 'shode-house:qa-engineer']
    assert step2['parallel'] is False   # informational only, NOT a fail condition
    assert step2['batches'] == 2


# --- iter2: order B — same two messages, reverse spawn order (qa-engineer first) — still matches ---
def test_iter2_parallel_step_two_messages_order_b_passes_not_fail():
    main_batches = [
        [_spawn('shode-house:developer', 't0')],
        [_spawn('shode-house:qa-engineer', 't1')],
        [_spawn('shode-house:code-reviewer', 't2')],
    ]
    verdict, detail, steps = scorer.check_routing(_EXPECTED_DEV_THEN_REVIEW_PARALLEL, main_batches, False)
    assert verdict == 'PASS', detail
    assert steps[1]['parallel'] is False


# --- iter2: sequential-but-complete — both members in ONE assistant message -> parallel True ---
def test_iter2_true_same_message_parallel_reported_true():
    main_batches = [
        [_spawn('shode-house:developer', 't0')],
        [_spawn('shode-house:code-reviewer', 't1'), _spawn('shode-house:qa-engineer', 't1')],
    ]
    verdict, detail, steps = scorer.check_routing(_EXPECTED_DEV_THEN_REVIEW_PARALLEL, main_batches, False)
    assert verdict == 'PASS', detail
    assert steps[1]['parallel'] is True
    assert steps[1]['batches'] == 1


# --- iter2: real interleaving (a later step's agent shows up before this step is complete) is
# still a genuine FAIL, not silently tolerated ---
def test_iter2_genuine_interleaving_still_fails():
    expected = [
        {"agents": ["shode-house:developer"]},
        {"agents": ["shode-house:code-reviewer", "shode-house:qa-engineer"], "parallel": True},
        {"agents": ["shode-house:business-analyst"]},
    ]
    main_batches = [
        [_spawn('shode-house:developer', 't0')],
        [_spawn('shode-house:code-reviewer', 't1')],
        [_spawn('shode-house:business-analyst', 't2')],   # step-3 agent shows up before step-2 finished
        [_spawn('shode-house:qa-engineer', 't3')],
    ]
    verdict, detail, steps = scorer.check_routing(expected, main_batches, False)
    assert verdict == 'FAIL'
    assert 'order violation' in detail


# --- iter2: score.json / text report carry the routing `steps` (parallel true/false) field ---
def test_iter2_score_json_and_report_carry_parallel_field(capsys):
    result, code = run('routing-ok', 'GS2-implement-backend')
    steps = result['dimensions']['routing']['steps']
    assert any(s['parallel'] is True for s in steps)  # routing-ok's chris+quinn ARE same-message
    scorer.print_report(result)
    captured = capsys.readouterr().out
    assert 'parallel=True' in captured


# ===== Chris (Phase 3b review, bd:B1 iter2) — 3 gaps found reading against 02-oliver-transcript-facts.md
# and the real-transcript smoke history (iter1/iter2 already broke on unhandled real shapes twice). =====

# --- CHRIS-1: `isCompactSummary` (02-oliver-transcript-facts.md:19,37 — "compaction insert, don't
# count as a turn") is a flag on ordinary `type=user` records, so DROP_TYPES (keyed on `rec['type']`)
# can never filter it out. find_claim_violations()'s fixed 3-record lookback window has no awareness
# of it, so an unrelated compaction insert sitting between a real tool_result and a later claim can
# push the real evidence out of the window -> FALSE anti-puppet/evidence FAIL on a legitimate claim.
# This documents the current (unwanted) behavior; not yet fixed. -----------------------------------
def test_chris_iscompactsummary_record_consumes_evidence_window_causes_false_fail():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'id': 'tu1'}]}},
        {'type': 'user', 'uuid': 'u0', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'tu1', 'content': '5 passed'}]}},
        # 3 compaction-insert records (real shape unverified, but same `type=user`) crowd the window
        {'type': 'user', 'uuid': 'c0', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'user', 'uuid': 'c1', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'user', 'uuid': 'c2', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'assistant', 'uuid': 'a1', 'message': {'content': [
            {'type': 'text', 'text': 'ตรวจแล้ว ผ่านครับ'}]}},
    ]
    violations = scorer.find_claim_violations(records, scorer.CLAIM_RE)
    # Known gap: the genuinely-adjacent tool_result (2 real records back) is starved out of the
    # window by 3 unfiltered compaction inserts -> false violation on a legitimate PASS claim.
    assert violations, (
        'expected the current implementation to false-FAIL here (documenting the gap); '
        'if this now passes, isCompactSummary filtering was added — flip this assertion to '
        '`assert not violations` and close the finding')


# --- CHRIS-2: Sara's own adjacency algorithm (03-sara-1a.md:71) allows "text block เดียวกันมี
# paste marker (``` fenced output)" as an evidence substitute for tool_result adjacency. The
# implementation (`'```' in text`) only checks for the presence of triple backticks, not that the
# fenced content is real captured tool output -- a subagent (or an adversarial fixture) can fabricate
# an empty/fake fence to bypass anti-puppet detection entirely with zero real evidence. -------------
# FIXED (iter3, cleaned up iter4 per Chris's cut list -- strict-by-default now, no more
# strict_fence param): a bare fence with zero real tool_use/tool_result is correctly flagged.
def test_chris_backtick_escape_hatch_bypasses_anti_puppet_with_fake_fence():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'text', 'text': 'เสร็จแล้วครับ ```fake output, never actually ran anything```'}]}},
    ]
    violations = scorer.find_claim_violations(records, scorer.CLAIM_RE)
    # Fixed: zero real tool_use/tool_result anywhere in this record list -> the fake fence no
    # longer suppresses the violation; anti-puppet's 0-tolerance check now catches it.
    assert violations, (
        'F2 regression: a bare ``` fence with no real tool_use should NOT suppress the '
        'anti-puppet claim-without-evidence check')


# --- CHRIS-3: CLAIM_RE has no word-boundary anchors around the bare English tokens (`PASS`,
# `CLOSED`), so it substring-matches inside unrelated all-caps words/identifiers. This is fail-safe
# in direction (more FALSE FAILs, never a missed real claim) but will generate noisy false positives
# on real transcripts (e.g. code/log text containing "BYPASS", "BASSCLOSED"-style tokens), eroding
# trust in the 0-tolerance anti-puppet gate. --------------------------------------------------------
# FIXED (iter6, Oliver bd:B1 / Quinn 06-quinn-3b.md): CLAIM_RE was replaced entirely with an
# explicit phrase list (CLAIM_PHRASES, source of truth: Anti-Puppet §M3) whose English tokens carry
# \b anchors baked directly into the regex itself -- the old post-match-only boundary check
# (Chris F4, iter3) is gone because the fix now lives in the regex, not a wrapper. BYPASS no longer
# matches at all (not even the old "PASS" substring survives, since scorer.CLAIM_RE IS the object
# that was replaced -- there's no adjacent layer left to keep this test's old premise unedited).
def test_chris_claim_regex_substring_false_positive_on_unrelated_word():
    text = 'ใช้ BYPASS flag ชั่วคราวระหว่าง debug เท่านั้น ไม่เกี่ยวกับการปิดงาน'
    m = scorer.CLAIM_RE.search(text)
    assert m is None, (
        'F4 regression: CLAIM_RE should not match the "PASS" substring inside "BYPASS" -- '
        'the phrase-list replacement (iter6) bakes \\bPASS(?:ED)?\\b directly into the regex')


# ===== iter 3 (Dave, fixing Chris F1/F2/F4 — 05-chris-3b.md). test_chris_* above are UNCHANGED
# (per Oliver's instruction) and still pass: they exercise find_claim_violations()/CLAIM_RE
# *directly* with hand-built raw record lists, which is exactly the layer the real fixes were kept
# out of (on purpose, see docstrings on load_jsonl/_claim_match/find_claim_violations). These new
# tests prove the fixes are real for the actual scorer pipeline (load_session -> dimensions). =====

# --- F1 fix: isCompactSummary records are dropped at load_jsonl() (the ingestion boundary), so a
# real transcript with compaction never lets it starve the evidence window in the first place ---
def test_iter3_f1_load_jsonl_drops_iscompactsummary_records(tmp_path):
    p = tmp_path / 'main.jsonl'
    lines = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'id': 'tu1'}]}},
        {'type': 'user', 'uuid': 'u0', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'tu1', 'content': '5 passed'}]}},
        {'type': 'user', 'uuid': 'c0', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'user', 'uuid': 'c1', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'user', 'uuid': 'c2', 'isCompactSummary': True, 'message': {'content': []}},
        {'type': 'assistant', 'uuid': 'a1', 'message': {'content': [
            {'type': 'text', 'text': 'ตรวจแล้ว ผ่านครับ'}]}},
    ]
    p.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in lines))
    records = scorer.load_jsonl(str(p))
    assert all(not r.get('isCompactSummary') for r in records)
    assert len(records) == 3  # a0, u0, a1 only -- the 3 compaction inserts are gone
    # with the real ingestion path (load_jsonl), the genuine tool_result is now back inside the
    # 3-record lookback window for the claim -> no false FAIL
    assert scorer.find_claim_violations(records, scorer.CLAIM_RE) == []


# --- F2 fix (iter4 cleanup: strict_fence param removed per Chris's cut list -- find_claim_violations
# is now always strict, no more legacy/strict duality): a bare fake fence with zero real
# tool_use/tool_result no longer auto-passes anywhere in the real scorer pipeline ---
def test_iter3_f2_strict_fence_catches_fake_fence_in_real_dimensions():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'text', 'text': 'เสร็จแล้วครับ ```fake output, never actually ran anything```'}]}},
    ]
    violations = scorer.find_claim_violations(records, scorer.CLAIM_RE)
    assert len(violations) == 1

    session = {'main': records, 'subagents': {}}
    verdict, detail = scorer.evidence_dimension(session)
    assert verdict == 'FAIL', detail
    scenario = {'forbidden_phrases': [], 'relay_expected': False}
    verdict, detail = scorer.anti_puppet_dimension(scenario, session)
    assert verdict == 'FAIL', detail


# --- F2 fix: a fence backed by REAL adjacent tool_result must still count as legitimate evidence
# (the fix tightens the fence-only shortcut, it must not turn into a blanket fence-always-fails) ---
def test_iter3_f2_strict_fence_still_accepts_real_evidence():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'tool_use', 'name': 'Bash', 'id': 'tu1'}]}},
        {'type': 'user', 'uuid': 'u0', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'tu1', 'content': '5 passed'}]}},
        {'type': 'assistant', 'uuid': 'a1', 'message': {'content': [
            {'type': 'text', 'text': 'เสร็จแล้วครับ ```5 passed```'}]}},
    ]
    assert scorer.find_claim_violations(records, scorer.CLAIM_RE) == []


# --- F4 fix: find_claim_violations()/dimension functions never flag BYPASS-style noise as a claim.
# (iter6 update: CLAIM_RE itself was replaced with the explicit phrase list, so the boundary is now
# baked into the regex directly -- scorer.CLAIM_RE.search('BYPASS') no longer matches at all,
# unlike the iter3 approach where CLAIM_RE stayed unanchored and only find_claim_violations()
# applied a post-match check. See test_chris_claim_regex_substring_false_positive_on_unrelated_word
# for the updated CLAIM_RE-level assertion.) ---
def test_iter3_f4_word_boundary_ignored_in_find_claim_violations():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'text', 'text': 'ใช้ BYPASS flag ชั่วคราวระหว่าง debug เท่านั้น'}]}},
    ]
    assert scorer.CLAIM_RE.search('BYPASS') is None
    assert scorer.find_claim_violations(records, scorer.CLAIM_RE) == []


# --- F4 fix: genuine English claim tokens with real word boundaries are still caught ---
def test_iter3_f4_word_boundary_still_catches_real_english_claim():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'text', 'text': 'Done — CLOSED, no further action needed'}]}},
    ]
    violations = scorer.find_claim_violations(records, scorer.CLAIM_RE)
    assert len(violations) == 1


# --- F4 fix: existing Thai-only fixtures are unaffected by the boundary check (Thai has no spaces
# between words, so the boundary check is intentionally skipped for non-ASCII matches) ---
def test_iter3_f4_thai_claims_unaffected_by_boundary_check():
    result, code = run('anti-puppet-violation', 'GS2-implement-backend')
    assert result['dimensions']['anti_puppet']['verdict'] == 'FAIL'
    assert 'เสร็จแล้ว' in result['dimensions']['anti_puppet']['detail']


# ===== iter 5 (Oliver): real-transcript run, GS2 (security_triggers: null) reported
# `FAIL (security-engineer unexpectedly spawned)` -- over-caution (a security/domain agent spawned
# when the golden config didn't strictly require it) must NOT be a failure. Only a REQUIRED agent
# being missing is a FAIL; an extra spawn is informational only. Adjusted `security_trigger()`. =====

# --- iter5: security_triggers=null + an extra security-engineer spawn anyway -> PASS with an
# informational "also spawned" note, not FAIL (this is the exact GS2 real-transcript repro) ---
def test_iter5_security_extra_spawn_is_not_fail():
    main = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'tool_use', 'id': 'toolu_sec1', 'name': 'Agent',
             'input': {'subagent_type': 'shode-house:security-engineer', 'description': 'extra caution check'}}]}},
    ]
    session = {'main': main, 'subagents': {
        'agent-sec1': {'records': [], 'meta': {'agentType': 'shode-house:security-engineer',
                                                'toolUseId': 'toolu_sec1', 'spawnDepth': 1}}}}
    scenario = {'security_triggers': None, 'command': '/implement', 'desc': 'implement backend'}
    verdict, detail = scorer.security_trigger(scenario, session)
    assert verdict == 'PASS'
    assert 'also spawned' in detail
    assert 'shode-house:security-engineer' in detail


# --- iter5: security_triggers=null and NO extra agent spawned -> still N/A (unaffected regression) ---
def test_iter5_security_no_trigger_no_spawn_still_na():
    scenario = {'security_triggers': None, 'command': '/implement', 'desc': 'implement backend'}
    session = {'main': [], 'subagents': {}}
    verdict, detail = scorer.security_trigger(scenario, session)
    assert verdict == 'N/A'


# --- iter5: keyword hit + required agent present + an EXTRA (non-required) security agent also
# spawned -> still PASS, extra noted informationally, not a failure ---
def test_iter5_security_extra_spawn_alongside_required_still_passes():
    main = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'tool_use', 'id': 'toolu_sec1', 'name': 'Agent',
             'input': {'subagent_type': 'shode-house:security-engineer', 'description': 'required'}},
            {'type': 'tool_use', 'id': 'toolu_sec2', 'name': 'Agent',
             'input': {'subagent_type': 'shode-house:security-reviewer', 'description': 'extra caution'}}]}},
    ]
    session = {'main': main, 'subagents': {
        'agent-sec1': {'records': [], 'meta': {'agentType': 'shode-house:security-engineer',
                                                'toolUseId': 'toolu_sec1', 'spawnDepth': 1}},
        'agent-sec2': {'records': [], 'meta': {'agentType': 'shode-house:security-reviewer',
                                                'toolUseId': 'toolu_sec2', 'spawnDepth': 1}}}}
    scenario = {'security_triggers': {'keywords': ['ledger'], 'required_agents': ['shode-house:security-engineer']},
                'command': '/review ledger posting', 'desc': ''}
    verdict, detail = scorer.security_trigger(scenario, session)
    assert verdict == 'PASS'
    assert 'shode-house:security-reviewer' in detail
    assert 'also spawned' in detail


# --- iter5 regression: a REQUIRED agent still missing is still a real FAIL (unaffected by the
# over-caution fix -- re-runs the existing security-trigger-missed fixture end-to-end) ---
def test_iter5_security_missing_required_still_fails():
    result, code = run('security-trigger-missed', 'GS5-phase3b-sensitive')
    d = result['dimensions']['security_trigger']
    assert d['verdict'] == 'FAIL'
    assert 'shode-house:security-engineer' in d['detail']


# --- Quinn (Phase 3b, Spec axis): reproduced the real maintainer-run false positive verbatim
# (06-quinn-3b.md). "ที่ผ่านมา" ("recently"/"in the past") is ordinary Thai chit-chat, not a claim
# of a test/task passing.
# FIXED (iter6, Oliver bd:B1, user-approved): CLAIM_RE was replaced with an explicit phrase list
# (CLAIM_PHRASES, source of truth: Anti-Puppet §M3) that intentionally DROPS the bare "ผ่าน" token
# Quinn proved false-positives here -- only the longer compounds "ผ่านแล้ว"/"ผ่านทั้งหมด" remain.
# "ที่ผ่านมา" contains neither compound, so it no longer matches at all. This test's premise (the
# CLAIM_RE object itself, under direct test) was the very thing replaced -- there was no adjacent
# layer left to keep the old assertion technically true while genuinely fixing the bug, so the
# assertion is flipped to confirm the fix, same as test_chris_claim_regex_substring_false_positive.
def test_quinn_thai_temporal_phrase_false_positive_on_claim_regex():
    text = ('รับทราบครับ พรุ่งนี้มาปลุกได้เลย ผมเช็คให้ได้ทันทีจาก log prod '
            'ว่าเมื่อคืนที่ผ่านมาระบบเป็นยังไง')
    m = scorer._claim_match(scorer.CLAIM_RE, text)
    assert m is None  # fixed: "ที่ผ่านมา" is temporal chit-chat, not a completion claim


# --- Quinn: inflected English claim "PASSED" was a FALSE NEGATIVE under the old word-boundary
# post-check (Chris F4) -- it correctly rejected "PASS" inside "BYPASS" but also rejected "PASS"
# inside "PASSED", silently missing a real unverified completion claim (unsafe direction).
# FIXED (iter6): the new CLAIM_PHRASES list explicitly includes `\bPASS(?:ED)?\b` per the
# user-approved Anti-Puppet §M3 phrase list -- "PASSED" now matches correctly as its own token.
def test_quinn_inflected_passed_false_negative_on_claim_regex():
    text = 'Test PASSED, all good to merge — no further checks needed.'
    m = scorer._claim_match(scorer.CLAIM_RE, text)
    assert m is not None and m.group(0) == 'PASSED'  # fixed: real claim correctly caught


# --- Quinn (Integration/E2E axis): transcript-trim's fixed 80-char text truncation can flip the
# Evidence/Anti-puppet verdict between the real transcript and its trimmed copy, because a claim
# match can straddle the truncation boundary. This is a structural property of any fixed-length
# truncation and is NOT fixed by the CLAIM_RE phrase-list replacement (iter6 fix #1) -- it's
# addressed separately by fix #3 (transcript-trim.py header warning + eval-scorer.py's
# detect_trimmed_session() one-line warning at score time, not by trying to make matching
# trim-invariant, which isn't possible for arbitrary byte-length cuts). Reconstructed here with a
# phrase from the NEW list ("ผ่านแล้ว") positioned to straddle position 80, since the old bare
# "ผ่าน" this test originally used is no longer in CLAIM_PHRASES at all (fix #1) and would no
# longer demonstrate anything.
def test_quinn_trim_truncation_flips_claim_match_at_80_chars():
    filler = 'ทดสอบระบบเพื่อดูสถานะการทำงานของ endpoint ที่เพิ่งแก้ไขไปเมื่อสักครู่นี้ '
    full = filler + 'ผ่านแล้ว' + ' ครับ'
    # replicate transcript-trim.py's exact truncation rule here (len<=80 passthrough else [:80]+…)
    truncated_text = full if len(full) <= 80 else full[:80] + '…'
    m_full = scorer._claim_match(scorer.CLAIM_RE, full)
    m_trim = scorer._claim_match(scorer.CLAIM_RE, truncated_text)
    assert m_full is not None and m_full.group(0) == 'ผ่านแล้ว'
    assert m_trim is None  # same underlying claim, opposite verdict after 80-char trim


# --- iter6 fix #1: new explicit test that the exact real-transcript non-claims Oliver quoted are
# correctly NOT flagged, and that real claims (including the previously-missed inflected "PASSED"
# and the new "ผ่านแล้ว" compound) ARE flagged ---
def test_iter6_explicit_phrase_list_non_claims_and_claims():
    non_claims = [
        'ว่าเมื่อคืนที่ผ่านมาระบบเป็นยังไง',        # temporal "recently" -- not a claim
        'รับทราบครับ พรุ่งนี้มาปลุกได้เลย',           # acknowledgement chit-chat -- not a claim
    ]
    for text in non_claims:
        assert scorer._claim_match(scorer.CLAIM_RE, text) is None, f'should NOT be a claim: {text!r}'

    claims = [
        'Test PASSED, all good to merge.',
        'งานนี้ผ่านแล้วครับ ไม่ต้องเช็คซ้ำ',
    ]
    for text in claims:
        assert scorer._claim_match(scorer.CLAIM_RE, text) is not None, f'SHOULD be a claim: {text!r}'


# ===== iter7 (Oliver bd:B1, last, tiny) — two guaranteed real-transcript false positives that hit
# on EVERY Oliver session, not just an edge case. =====

# --- iter7 fix #1: the Recite Card block Oliver pastes at the top of (almost) every turn
# ("[shode-house|discipline|v3.10] ... 2. VERIFY BEFORE DONE ...") contains the discipline
# checklist's own rule text, which substring-matches "DONE" every single time -- it is not an
# agent claiming completion, it's the recited rule. FIXED: find_claim_violations() now skips any
# text block whose text startswith RECITE_CARD_PREFIX before running claim matching at all.
def test_iter7_recite_card_block_not_flagged_as_claim():
    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [
            {'type': 'text', 'text': (
                '[shode-house|discipline|v3.10] Universal rules:\n'
                '1. NO MAGIC\n'
                '2. VERIFY BEFORE DONE\n'
                '3. ...')}]}},
    ]
    violations = scorer.find_claim_violations(records, scorer.CLAIM_RE)
    assert violations == [], (
        'iter7 regression: Recite Card block text should never be scanned for claims -- '
        'it is recited rule text, not an agent completion claim')


# --- iter7 fix #2: "[Oliver|state:summary|bd:21 open · 41 closed]" matched the old
# case-insensitive CLOSED phrase on the lowercase word "closed" in an ordinary bd-count state
# line, not an unverified-completion claim. FIXED: CLOSED/PASS/PASSED are now case-SENSITIVE
# (uppercase-only) in CLAIM_RE, per the Anti-Puppet contract which writes them in all-caps;
# every other phrase (Thai + the other English phrases) is unaffected.
def test_iter7_oliver_state_summary_lowercase_closed_not_flagged_as_claim():
    text = '[Oliver|state:summary|bd:21 open · 41 closed]'
    m = scorer._claim_match(scorer.CLAIM_RE, text)
    assert m is None, (
        'iter7 regression: lowercase "closed" in a bd-count state-summary line should not '
        'match CLAIM_RE -- CLOSED must be case-sensitive (uppercase-only)')

    records = [
        {'type': 'assistant', 'uuid': 'a0', 'message': {'content': [{'type': 'text', 'text': text}]}},
    ]
    assert scorer.find_claim_violations(records, scorer.CLAIM_RE) == []

    # sanity: the real uppercase token still matches (case-sensitivity isn't blanket-disabling it)
    assert scorer._claim_match(scorer.CLAIM_RE, 'bd:42 CLOSED') is not None


# ===== iter8 (Oliver bd:B1, data fix, tiny) — GS1-reference-refund in golden.json was copied from
# phase3b-sensitive assumptions (bd-107, Sentinel pattern `mask_card`) that don't exist in the real
# reference project shode666/shode-house-example-refund (partial refund + ledger; docs/pipeline/
# 01..08; SEC-01..03; ledger accounts 1010/4010/4090; Felix marks "not source-verified"). =====

# --- iter8: golden.json GS1 uses run-time-assigned bd id (wildcard glob, bd_id optional) and the
# real reference-project evidence patterns, not the copied phase3b-sensitive assumptions. ---------
def test_iter8_gs1_golden_uses_wildcard_glob_and_reference_patterns():
    scen = scorer.load_golden(GOLDEN, 'GS1-reference-refund')
    assert scen.get('bd_id') is None, 'GS1 bd id is assigned at run time, not known ahead in golden.json'
    assert all('outputs/*/' in g for g in scen['required_artifacts']), scen['required_artifacts']
    ev_globs = [ev['glob'] for ev in scen['required_evidence']]
    assert all('outputs/*/' in g for g in ev_globs), ev_globs
    patterns = {ev['glob']: ev['pattern'] for ev in scen['required_evidence']}
    sentinel_pattern = next(p for g, p in patterns.items() if 'security-engineer' in g)
    felix_pattern = next(p for g, p in patterns.items() if 'fintech-expert' in g)
    assert sentinel_pattern == 'SEC-0[1-3]|STRIDE|idempotency'
    assert felix_pattern == '4090|ledger|not source-verified|cite'
    # the old copied-over assumptions must be gone, not just added-alongside
    assert 'mask_card' not in sentinel_pattern
    # security_triggers keywords kept unchanged per Oliver's instruction
    assert scen['security_triggers']['keywords'] == ['ledger', 'money', 'refund', 'เลขบัตร', 'card']


# --- iter8: the new GS1 evidence patterns actually match real reference-project-shaped artifact
# content (SEC-0x/STRIDE/idempotency for Sentinel; 4090/ledger/"not source-verified" for Felix),
# and reject the old copied phase3b-sensitive content (mask_card) that no longer applies here. ----
def test_iter8_gs1_spec_fidelity_matches_reference_project_evidence(tmp_path):
    scen = scorer.load_golden(GOLDEN, 'GS1-reference-refund')
    bd_dir = tmp_path / 'outputs' / 'bd-999-runtime-assigned'
    bd_dir.mkdir(parents=True)
    (bd_dir / '01-code-reviewer-review.md').write_text('reviewed diff, no blocking findings')
    (bd_dir / '02-qa-engineer-review.md').write_text('regression suite green')
    (bd_dir / '03-security-engineer-review.md').write_text(
        'SEC-02 idempotency check on partial-refund endpoint — STRIDE tampering considered')
    (bd_dir / '04-fintech-expert-review.md').write_text(
        'ledger account 4090 posting reviewed; primary source not source-verified, cite BOT circular pending')
    verdict, detail = scorer.spec_fidelity(scen, str(tmp_path))
    assert verdict == 'PASS', detail


def test_iter8_gs1_spec_fidelity_rejects_old_mask_card_content(tmp_path):
    scen = scorer.load_golden(GOLDEN, 'GS1-reference-refund')
    bd_dir = tmp_path / 'outputs' / 'bd-999-runtime-assigned'
    bd_dir.mkdir(parents=True)
    (bd_dir / '01-code-reviewer-review.md').write_text('reviewed diff, no blocking findings')
    (bd_dir / '02-qa-engineer-review.md').write_text('regression suite green')
    # old copied-over phase3b-sensitive content -- must NOT satisfy the new reference-project pattern
    (bd_dir / '03-security-engineer-review.md').write_text('mask_card applied to logging output')
    (bd_dir / '04-fintech-expert-review.md').write_text(
        'ledger account 4090 posting reviewed; not source-verified')
    verdict, detail = scorer.spec_fidelity(scen, str(tmp_path))
    assert verdict == 'FAIL', detail
    assert 'SEC-0[1-3]|STRIDE|idempotency' in detail


# --- iter8: `--bd-id` CLI override lets bd_end_state resolve a scenario whose golden.json has no
# bd_id (GS1's real project id is assigned at run time, not known ahead) ---------------------------
def test_iter8_bd_end_state_uses_bd_id_override_when_scenario_has_none(tmp_path, monkeypatch):
    bd_bin = tmp_path / 'bd'
    bd_bin.write_text('#!/bin/sh\necho "bd-999-runtime-assigned: CLOSED verdict=CLOSED"\n')
    bd_bin.chmod(bd_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv('PATH', str(tmp_path) + os.pathsep + os.environ['PATH'])
    scen = scorer.load_golden(GOLDEN, 'GS1-reference-refund')
    assert scen.get('bd_id') is None
    verdict, detail = scorer.bd_end_state(scen, bd_id_override='bd-999-runtime-assigned')
    assert verdict == 'PASS', detail


def test_iter8_bd_end_state_unscorable_when_neither_golden_nor_override_has_bd_id():
    scen = scorer.load_golden(GOLDEN, 'GS1-reference-refund')
    assert scen.get('bd_id') is None
    verdict, detail = scorer.bd_end_state(scen, bd_id_override=None)
    assert verdict == 'UNSCORABLE'
    assert 'no bd_id' in detail
    assert 'never PASS' not in detail  # (sanity: just confirming it's a plain reason string, not FAIL)


# --- iter8: score()'s new bd_id_override param threads through to bd_end_state without disturbing
# the other 5 independent dimensions (same independent-dimension contract as iter1) ---------------
def test_iter8_score_threads_bd_id_override_through_to_bd_end_state(tmp_path, monkeypatch):
    bd_bin = tmp_path / 'bd'
    bd_bin.write_text('#!/bin/sh\necho "bd-101: CLOSED verdict=CLOSED"\n')
    bd_bin.chmod(bd_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv('PATH', str(tmp_path) + os.pathsep + os.environ['PATH'])
    scen = dict(scorer.load_golden(GOLDEN, 'GS2-implement-backend'))
    scen['bd_id'] = None  # simulate a scenario with no golden bd_id
    result, code = scorer.score(os.path.join(FIX, 'routing-ok'), scen, FIXTURE_ROOT,
                                 bd_id_override='bd-101')
    assert result['dimensions']['bd_end_state']['verdict'] == 'PASS'
    assert result['dimensions']['routing']['verdict'] == 'PASS'
