#!/usr/bin/env python3
"""bd B1 — E2E behavioral scorer. stdlib only, python3.9+.

  scripts/eval-scorer.py <session-dir|main.jsonl> --scenario GS2 \
      [--golden eval/scenarios/golden.json] [--outputs-dir <fixture-project>/outputs] [--out <run-dir>]

Reads transcript(s) + outputs/<bd>/*.md + bd CLI (subprocess) only. No LLM judge.
Exit codes: 0 = all critical dims PASS · 1 = >=1 dim FAIL · 2 = UNSCORABLE.
See: outputs/B1/01-bella-1a.md §4, outputs/B1/03-sara-1a.md §1-5 (Sara, Phase 1a).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys

SPAWN_NAMES = {'Agent', 'Task'}
DROP_TYPES = {'bridge-session', 'queue-operation', 'attachment', 'atis-latch', 'last-prompt', 'custom-title'}
# NOTE (Chris F2, iter3; always-strict per iter4 cleanup): find_claim_violations() never trusts a
# bare '```' fence as evidence on its own — it must be backed by a real tool_use/tool_result
# adjacency (see find_claim_violations docstring).

# source of truth: Anti-Puppet §M3 (iter6, Oliver bd:B1, user-approved). Explicit phrase list
# replaces the old broad substring regex (Chris F4, iter3) which false-positived on "ที่ผ่านมา"
# (temporal "recently", not a completion claim — real transcript bug, Quinn 06-quinn-3b.md) and
# false-negatived on inflected English claims like "PASSED" (word-boundary killed the suffix too).
# Bare "ผ่าน" is intentionally NOT in this list (Quinn proved it: "ที่ผ่านมา" contains it as a
# substring with no relation to test/completion status). English tokens carry their own \b anchors
# inline; Thai phrases are multi-character compounds long enough that accidental substring
# collision inside an unrelated word is not a realistic risk (unlike the single bare "ผ่าน").
# iter7 (Oliver bd:B1): two guaranteed real-transcript false positives every Oliver session hit --
# (1) the Recite Card block ("[shode-house|discipline|v3.10] ... 2. VERIFY BEFORE DONE ...") matched
#     "DONE" -- fixed separately by skipping any text block that starts with the Recite Card prefix
#     (see find_claim_violations below), not by regex.
# (2) "[Oliver|state:summary|bd:21 open · 41 closed]" matched lowercase "closed" -- fixed by making
#     CLOSED/PASS/PASSED case-SENSITIVE (uppercase only, as the Anti-Puppet contract itself writes
#     them); everything else stays case-insensitive via scoped inline (?i:...) groups per phrase.
RECITE_CARD_PREFIX = '[shode-house|discipline|'
CLAIM_PHRASES = (
    # Thai (no case concept)
    'เสร็จแล้ว', 'เสร็จเรียบร้อย', 'ทำเสร็จ', 'ผ่านแล้ว', 'ผ่านทั้งหมด', 'ตรวจแล้ว', r'ปิด\s*bd',
    # English, case-insensitive (scoped per-phrase via (?i:...), not global re.IGNORECASE)
    r'(?i:\bdone\b)', r'(?i:\bcompleted\b)', r'(?i:\ball tests? pass(?:ed|ing)?\b)',
    r'(?i:\btests?\s+(?:are\s+)?green\b)', r'(?i:\b7-dim clean\b)', r'(?i:\bE2E green\b)',
    r'(?i:\bverdict PASS\b)',
    # English, case-SENSITIVE (uppercase only -- iter7 fix): the Anti-Puppet contract writes these
    # in all-caps; lowercase "closed"/"pass" show up constantly in ordinary chit-chat/state lines.
    r'\bPASS(?:ED)?\b', r'\bCLOSED\b',
)
CLAIM_RE = re.compile('|'.join(CLAIM_PHRASES))
PUPPET_HINT = ('เสร็จแล้ว', 'เสร็จเรียบร้อย', 'ทำเสร็จ', 'ผ่านแล้ว', 'ผ่านทั้งหมด', 'ตรวจแล้ว',
               'ปิด bd', 'done', 'completed', 'PASS', 'CLOSED')


# ---------- parse ----------

def load_jsonl(path):
    """Loads + filters one .jsonl file. Drops metadata-only DROP_TYPES *and* `isCompactSummary`
    records (Chris F1, iter3): per 02-oliver-transcript-facts.md:19,37 these are context-compaction
    inserts, not real turns — leaving them in would let them crowd genuine tool_result evidence out
    of find_claim_violations()'s fixed lookback window, causing a false anti-puppet/evidence FAIL on
    a legitimate claim. Filtering here (the ingestion boundary, same place as DROP_TYPES) means every
    real caller (load_session -> all scorer dimensions) is fixed; find_claim_violations() itself is
    untouched for callers who pass their own raw record lists directly."""
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get('type') in DROP_TYPES:
                continue
            if rec.get('isCompactSummary'):
                continue
            out.append(rec)
    return out


def load_session(path):
    """-> dict(main_path, main=[records], subagents={agentId:{records, meta, path}})"""
    if os.path.isdir(path):
        candidates = [p for p in glob.glob(os.path.join(path, '*.jsonl'))]
        main_path = max(candidates, key=os.path.getsize) if candidates else None
        sub_dir = os.path.join(path, 'subagents')
    else:
        main_path = path
        sub_dir = os.path.join(os.path.dirname(path) or '.', 'subagents')
    main = load_jsonl(main_path) if main_path else []
    subagents = {}
    if os.path.isdir(sub_dir):
        for fn in os.listdir(sub_dir):
            if fn.endswith('.meta.json'):
                agent_id = fn[:-len('.meta.json')]
                subagents.setdefault(agent_id, {})['meta'] = json.load(open(os.path.join(sub_dir, fn), encoding='utf-8'))
            elif fn.endswith('.jsonl'):
                agent_id = fn[:-len('.jsonl')]
                subagents.setdefault(agent_id, {})['records'] = load_jsonl(os.path.join(sub_dir, fn))
    for a in subagents.values():
        a.setdefault('records', [])
        a.setdefault('meta', {})
    return {'main_path': main_path, 'main': main, 'subagents': subagents}


def all_files(session):
    """-> {'main': records, agentId: records}"""
    files = {'main': session['main']}
    for aid, a in session['subagents'].items():
        files[aid] = a['records']
    return files


# ---------- spawn / routing tree ----------

def extract_spawn_batches(records):
    """-> list of batches; batch = list of {tool_use_id,name,declared_type,description}. Preserves record order."""
    batches = []
    for rec in records:
        if rec.get('type') != 'assistant':
            continue
        content = ((rec.get('message') or {}).get('content')) or []
        batch = []
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') in SPAWN_NAMES:
                inp = b.get('input') or {}
                batch.append({'tool_use_id': b.get('id'), 'name': b.get('name'),
                               'declared_type': inp.get('subagent_type'),
                               'description': inp.get('description'),
                               'timestamp': rec.get('timestamp')})
        if batch:
            batches.append(batch)
    return batches


def build_spawn_index(session):
    """Link every spawn tool_use (any file) to its resolved agentType via subagents/*.meta.json.
    -> {'main_batches':[...resolved...], 'all_spawn_types': set(), 'depth_by_agent': {agentId: spawnDepth}}
    """
    files = all_files(session)
    by_toolid = {}
    file_batches = {}
    for fid, recs in files.items():
        batches = extract_spawn_batches(recs)
        file_batches[fid] = batches
        for batch in batches:
            for spawn in batch:
                by_toolid[spawn['tool_use_id']] = spawn

    depth_by_agent = {}
    for aid, a in session['subagents'].items():
        meta = a.get('meta') or {}
        tid = meta.get('toolUseId')
        depth_by_agent[aid] = meta.get('spawnDepth')
        spawn = by_toolid.get(tid)
        if spawn is not None:
            spawn['agentId'] = aid
            spawn['agentType'] = meta.get('agentType') or spawn.get('declared_type')

    all_types = set()
    for batch in file_batches.get('main', []):
        for spawn in batch:
            spawn.setdefault('agentType', spawn.get('declared_type'))
            all_types.add(spawn['agentType'])
    for aid, batches in file_batches.items():
        if aid == 'main':
            continue
        for batch in batches:
            for spawn in batch:
                spawn.setdefault('agentType', spawn.get('declared_type'))
                all_types.add(spawn['agentType'])

    return {'main_batches': file_batches.get('main', []), 'file_batches': file_batches,
            'all_spawn_types': all_types, 'depth_by_agent': depth_by_agent}


def format_routing_tree(session):
    """Reconstructed routing tree (any file, any depth) for human eyeball — independent of scenario match."""
    idx = build_spawn_index(session)
    entries = []
    for fid, batches in idx['file_batches'].items():
        for batch in batches:
            if not batch:
                continue
            ts = batch[0].get('timestamp') or ''
            depth = None
            for s in batch:
                d = session['subagents'].get(s.get('agentId', ''), {}).get('meta', {}).get('spawnDepth')
                if d is not None:
                    depth = d
                    break
            if depth is None:
                depth = 1 if fid == 'main' else '?'
            types = [s.get('agentType') or '?' for s in batch]
            joined = ' || '.join(types)
            issuer_note = '' if fid == 'main' else f' (issued by {fid})'
            entries.append((ts, f'depth{depth}  {ts}  {joined}{issuer_note}'))
    entries.sort(key=lambda e: e[0])
    return [line for _, line in entries]


# ---------- Routing dimension (AC-1, AC-2) ----------

def _flatten_main_spawns(main_batches):
    """-> ordered list of spawn dicts, each tagged with its batch index (which assistant
    message/record it came from) so we can tell later whether a matched parallel step's
    members really shared one message, or landed in separate messages seconds apart."""
    flat = []
    for bi, batch in enumerate(main_batches):
        for s in batch:
            s['_batch_idx'] = bi
            flat.append(s)
    return flat


def check_routing(expected, main_batches, open_ended, main_record_count=0):
    """A step's members can arrive in any order, in any number of separate assistant messages,
    as long as they all land after the previous step's members and before the next step's
    members (iter 2 fix, Oliver bd:B1 — a 21s-apart 2-message parallel spawn is NOT a FAIL).
    `parallel` is reported per matched step as informational text/data only: true iff every
    matched member's tool_use came from the SAME assistant message (single batch)."""
    if not expected:
        return 'N/A', 'no expected_routing configured', []
    if not main_batches:
        return ('UNSCORABLE',
                f'no Agent/Task tool_use found in main though expected_routing is non-empty '
                f'(main has {main_record_count} records) — missing input, cannot resolve routing', [])
    total_spawns = sum(len(b) for b in main_batches)
    unresolved = sum(1 for b in main_batches for s in b if not s.get('agentId'))
    if total_spawns and unresolved > 0.5 * total_spawns:
        return ('UNSCORABLE',
                f'{unresolved}/{total_spawns} main-level spawns have no matching subagents/*.meta.json '
                f'(>50%) — cannot reliably resolve agentType', [])

    flat = _flatten_main_spawns(main_batches)
    all_expected = set()
    for step in expected:
        all_expected |= set(step['agents'])

    ptr = 0
    n = len(flat)
    steps_info = []
    for i, step in enumerate(expected):
        exp = set(step['agents'])
        collected = set()
        batches_used = set()
        timestamps = []
        j = ptr
        finished_at = None
        while j < n:
            spawn = flat[j]
            atype = spawn.get('agentType')
            if atype in exp:
                collected.add(atype)
                batches_used.add(spawn['_batch_idx'])
                timestamps.append(spawn.get('timestamp'))
                j += 1
                if collected >= exp:
                    finished_at = j
                    break
                continue
            if atype in all_expected:
                detail = (f"step {i+1} order violation: expected {sorted(exp)}, but encountered "
                          f"{atype!r} (belongs to another step) before finishing this step "
                          f"— collected so far {sorted(collected)}")
                return 'FAIL', detail, steps_info
            j += 1  # foreign/tolerated agent between steps — skip, not a violation
        if finished_at is None:
            if open_ended:
                detail = (f'open_ended, pipeline stopped before completing step {i+1} '
                           f'(collected {sorted(collected)} of {sorted(exp)})')
                return 'PASS', detail, steps_info
            return 'FAIL', f'step {i+1} missing: expected {sorted(exp)}, only found {sorted(collected)}', steps_info
        parallel_observed = len(batches_used) == 1 and len(exp) > 1
        steps_info.append({'step': i + 1, 'agents': sorted(exp), 'parallel': parallel_observed,
                            'batches': len(batches_used), 'timestamps': timestamps})
        ptr = finished_at
    parallel_notes = '; '.join(f"step{s['step']} parallel={s['parallel']}" for s in steps_info
                                if len(s['agents']) > 1)
    detail = f"{len(expected)}/{len(expected)} steps matched"
    if parallel_notes:
        detail += '; ' + parallel_notes
    return 'PASS', detail, steps_info


# ---------- Spec fidelity (AC-3) ----------

def resolve(fixture_root, rel):
    return rel if os.path.isabs(rel) else os.path.join(fixture_root, rel)


def spec_fidelity(scenario, fixture_root):
    """Missing input (spec file / required glob not found on disk) -> UNSCORABLE (own reason, doesn't
    wipe other dimensions). Content mismatch (file exists but doesn't say what's expected) -> FAIL."""
    spec_file = scenario.get('spec_file')
    req_artifacts = scenario.get('required_artifacts') or []
    req_evidence = scenario.get('required_evidence') or []
    if not spec_file and not req_artifacts and not req_evidence:
        return 'N/A', 'scenario has no spec-axis config'

    missing_inputs = []
    content_fails = []
    ac_ids = set()
    if spec_file:
        p = resolve(fixture_root, spec_file)
        if not os.path.isfile(p):
            missing_inputs.append(f'spec file not found: {spec_file} (resolved: {p})')
        else:
            ac_ids = set(re.findall(r'AC-\d+', open(p, encoding='utf-8').read()))

    matched_text = ''
    for pattern in req_artifacts:
        matches = glob.glob(resolve(fixture_root, pattern))
        if not matches:
            missing_inputs.append(f'no file matches required_artifacts glob: {pattern}')
            continue
        for m in matches:
            matched_text += open(m, encoding='utf-8', errors='ignore').read()

    if ac_ids:
        missing_ac = sorted(a for a in ac_ids if a not in matched_text)
        if missing_ac:
            content_fails.append(f'AC-ID not referenced in artifact: {missing_ac}')

    for ev in req_evidence:
        matches = glob.glob(resolve(fixture_root, ev['glob']))
        if not matches:
            missing_inputs.append(f"required_evidence glob no match: {ev['glob']}")
            continue
        text = ''.join(open(m, encoding='utf-8', errors='ignore').read() for m in matches)
        if not re.search(ev['pattern'], text):
            content_fails.append(f"required_evidence pattern not found: {ev['pattern']!r} in {ev['glob']}")

    if missing_inputs:
        detail = '; '.join(missing_inputs)
        if content_fails:
            detail += ' | (also content issues on files that were found: ' + '; '.join(content_fails) + ')'
        return 'UNSCORABLE', detail
    if content_fails:
        return 'FAIL', '; '.join(content_fails)
    return 'PASS', f'AC ids covered: {sorted(ac_ids) or "n/a"}; required_evidence matched'


# ---------- Security trigger (AC-6) ----------

def collect_all_text(session):
    parts = []
    for recs in all_files(session).values():
        for rec in recs:
            for b in ((rec.get('message') or {}).get('content') or []):
                if isinstance(b, dict) and b.get('type') == 'text':
                    parts.append(b.get('text') or '')
    return '\n'.join(parts)


def detect_trimmed_session(session):
    """Iter6 (Oliver bd:B1): transcript-trim.py truncates every text block to <=80 chars (+ '…'
    marker, so <=81 chars total). Evidence/Anti-puppet claim matching runs on the full text block
    (never re-truncated here), but a claim straddling that 80-char cut in the SOURCE transcript
    (before trimming) can flip verdict between the full transcript and its trimmed copy (Quinn,
    06-quinn-3b.md — proven with test_quinn_trim_truncation_flips_claim_match_at_80_chars).
    Heuristic: if every non-empty text block in the session is <=81 chars, this is very likely a
    trimmed fixture, not a real transcript -- warn so a human doesn't trust Evidence/Anti-puppet
    verdicts on it."""
    lens = [len(b.get('text') or '') for recs in all_files(session).values() for rec in recs
            for b in ((rec.get('message') or {}).get('content') or [])
            if isinstance(b, dict) and b.get('type') == 'text' and (b.get('text') or '')]
    return bool(lens) and all(n <= 81 for n in lens)


def security_trigger(scenario, session):
    """Over-caution (a security/domain agent spawned when the golden didn't strictly require it)
    is NEVER a failure (iter5, Oliver bd:B1) — only a REQUIRED agent being missing is a FAIL.
    `security_triggers: null` means "this scenario has no required security agent", not "no
    security agent may ever be spawned" — extra spawns are reported as an informational note."""
    st = scenario.get('security_triggers')
    spawn_types = build_spawn_index(session)['all_spawn_types']
    text = collect_all_text(session) + ' ' + (scenario.get('command') or '') + ' ' + (scenario.get('desc') or '')
    if st is None:
        spawned_security = sorted(t for t in spawn_types if t and 'security' in t)
        if spawned_security:
            return 'PASS', f'no security agent required; also spawned: {spawned_security} (over-caution, not a failure)'
        return 'N/A', 'no security trigger expected, none spawned'
    hit = [kw for kw in st.get('keywords', []) if kw in text]
    if not hit:
        return 'N/A', 'no trigger keyword present in prompt/text'
    missing = [a for a in st.get('required_agents', []) if a not in spawn_types]
    if missing:
        return 'FAIL', f'keyword hit {hit} but required agent(s) not spawned: {missing}'
    extra_security = sorted(t for t in spawn_types if t and 'security' in t and t not in st.get('required_agents', []))
    detail = f'keyword hit {hit}, required agents present: {st.get("required_agents")}'
    if extra_security:
        detail += f'; also spawned: {extra_security} (over-caution, not a failure)'
    return 'PASS', detail


# ---------- Evidence adjacency + Anti-puppet + relay (AC-4, AC-5) ----------

def _claim_match(pattern, text):
    """Iter6 (Oliver bd:B1, Quinn 06-quinn-3b.md): CLAIM_RE is now an explicit phrase list
    (CLAIM_PHRASES, source of truth: Anti-Puppet §M3) with word-boundary anchors baked directly
    into each English phrase and long enough Thai compounds to avoid Chris F4's old
    post-match-boundary-check approach entirely (that approach killed legitimate inflected claims
    like "PASSED" as a side effect of rejecting "PASS" inside "BYPASS" — Quinn's false-negative
    finding). This function is now a thin, boundary-agnostic wrapper: the regex itself is correct."""
    return pattern.search(text)


def find_claim_violations(records, pattern):
    """-> list of (uuid, quoted_text) where claim matched but no evidence adjacency.

    A '```' fence in the claim text is NOT treated as evidence on its own (Chris F2, iter3 —
    cleanup iter4 removed the legacy lenient default per Chris's cut list, always strict now): it
    must still be backed by a real tool_use/tool_result adjacency (window lookback or a tool_use
    in the same record), since a fence's mere presence proves nothing about whether the pasted
    content is real captured tool output."""
    violations = []
    for i, rec in enumerate(records):
        if rec.get('type') != 'assistant':
            continue
        for b in ((rec.get('message') or {}).get('content') or []):
            if not (isinstance(b, dict) and b.get('type') == 'text'):
                continue
            text = b.get('text') or ''
            if text.startswith(RECITE_CARD_PREFIX):
                # iter7 (Oliver bd:B1): the Recite Card block itself contains the discipline
                # checklist text (e.g. "2. VERIFY BEFORE DONE ...") which matches CLAIM_RE on
                # "DONE" every single session -- it is not an agent claiming completion, it is
                # the recited rule text. Exclude it from claim scanning entirely.
                continue
            if not _claim_match(pattern, text):
                continue
            window = records[max(0, i - 3):i]
            window_evidence = any(
                w.get('type') == 'user' and (w.get('toolUseResult') is not None or any(
                    isinstance(c, dict) and c.get('type') == 'tool_result'
                    for c in ((w.get('message') or {}).get('content') or [])))
                for w in window)
            same_record_tool_use = any(
                isinstance(c, dict) and c.get('type') == 'tool_use'
                for c in ((rec.get('message') or {}).get('content') or []))
            has_evidence = window_evidence or same_record_tool_use
            if not has_evidence:
                violations.append((rec.get('uuid'), text[:120]))
    return violations


def evidence_dimension(session):
    all_v = []
    for fid, recs in all_files(session).items():
        for uid, text in find_claim_violations(recs, CLAIM_RE):
            all_v.append(f'{fid}:{uid}: "{text}"')
    if all_v:
        return 'FAIL', f'{len(all_v)} claim(s) without adjacent tool_result: ' + '; '.join(all_v[:5])
    return 'PASS', 'all claims have adjacent tool_result / inline paste'


def anti_puppet_dimension(scenario, session):
    violations = []
    for fid, recs in all_files(session).items():
        for uid, text in find_claim_violations(recs, CLAIM_RE):
            if any(h in text for h in PUPPET_HINT):
                violations.append(f'{fid}:{uid}: "{text}"')
    forbidden = scenario.get('forbidden_phrases') or []
    if forbidden:
        text_all = collect_all_text(session)
        for phrase in forbidden:
            if phrase in text_all:
                violations.append(f'forbidden phrase found: "{phrase}"')

    # relay check
    files = all_files(session)
    for fid, recs in files.items():
        if fid == 'main':
            continue
        for rec in recs:
            for b in ((rec.get('message') or {}).get('content') or []):
                if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'AskUserQuestion':
                    violations.append(f'AskUserQuestion answered inside subagent {fid} (must relay to main)')
    if scenario.get('relay_expected'):
        main_has = any(
            isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'AskUserQuestion'
            for rec in files.get('main', []) for b in ((rec.get('message') or {}).get('content') or []))
        if not main_has:
            violations.append('relay_expected=true but no AskUserQuestion found in main session')

    if violations:
        return 'FAIL', '; '.join(violations[:6])
    return 'PASS', '0 violation'


# ---------- Cost (report only, AC-7 is usage-report.py's job) ----------

def cost_dimension(session):
    total = 0
    for recs in all_files(session).values():
        for rec in recs:
            usage = (rec.get('message') or {}).get('usage')
            if isinstance(usage, dict):
                total += usage.get('input_tokens', 0) or 0
                total += usage.get('output_tokens', 0) or 0
                total += usage.get('cache_creation_input_tokens', 0) or 0
    return total


# ---------- bd end_state (user decision: scorer calls `bd` itself) ----------

def bd_end_state(scenario):
    bd_id = scenario.get('bd_id')
    end = scenario.get('end_state') or {}
    if not bd_id:
        return 'UNSCORABLE', 'no bd_id configured for scenario — cannot check end_state'
    if shutil.which('bd') is None:
        return 'UNSCORABLE', 'bd CLI not found on PATH — cannot verify end_state'
    try:
        r = subprocess.run(['bd', 'show', bd_id], capture_output=True, text=True, timeout=10)
    except Exception as e:
        return 'UNSCORABLE', f'bd show failed to run: {e}'
    out = (r.stdout or '') + (r.stderr or '')
    want_status = end.get('bd_status')
    if want_status and want_status not in out:
        return 'FAIL', f'bd status {want_status!r} not found in `bd show {bd_id}` output'
    vp = end.get('verdict_pattern')
    if vp and not re.search(vp, out):
        return 'FAIL', f'verdict_pattern {vp!r} not matched in bd show output'
    return 'PASS', f'bd show {bd_id} matches expected end_state'


# ---------- report / main ----------

def load_golden(golden_path, scenario_id):
    data = json.load(open(golden_path, encoding='utf-8'))
    scenarios = data.get('scenarios', [])
    for sc in scenarios:
        if sc.get('id') == scenario_id:
            return sc
    prefix_matches = [sc for sc in scenarios if sc.get('id', '').startswith(scenario_id)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    raise SystemExit(f'scenario {scenario_id!r} not found (or ambiguous prefix) in {golden_path}')


CRITICAL_DIMS = ['routing', 'spec_fidelity', 'security_trigger', 'evidence', 'anti_puppet']


def score(session_path, scenario, fixture_root):
    """Each dimension is computed independently — a dimension lacking its own input becomes
    UNSCORABLE with its own reason; it never wipes the other dimensions (iter 1 fix, Oliver bd:B1).
    Overall: FAIL if any critical dim FAIL; else UNSCORABLE if any critical dim UNSCORABLE; else PASS.
    bd_end_state is reported but NOT critical (would otherwise force UNSCORABLE on every run without
    a `bd` binary on PATH) — same treatment as Cost (report-only)."""
    session = load_session(session_path)
    main_batches = build_spawn_index(session)['main_batches']

    dims = {}
    dims['routing'] = check_routing(scenario.get('expected_routing') or [], main_batches,
                                     scenario.get('routing_open_ended', False), len(session['main']))
    dims['spec_fidelity'] = spec_fidelity(scenario, fixture_root)
    dims['security_trigger'] = security_trigger(scenario, session)
    dims['evidence'] = evidence_dimension(session)
    dims['anti_puppet'] = anti_puppet_dimension(scenario, session)
    dims['bd_end_state'] = bd_end_state(scenario)
    cost_tok = cost_dimension(session)

    crit_verdicts = [dims[k][0] for k in CRITICAL_DIMS]
    if 'FAIL' in crit_verdicts:
        verdict, code = 'FAIL', 1
    elif 'UNSCORABLE' in crit_verdicts:
        verdict, code = 'UNSCORABLE', 2
    else:
        verdict, code = 'PASS', 0

    unscorable_reasons = [f'{k}: {dims[k][1]}' for k in CRITICAL_DIMS if dims[k][0] == 'UNSCORABLE']

    dims_out = {k: {'verdict': v[0], 'detail': v[1]} for k, v in dims.items()}
    dims_out['routing']['steps'] = dims['routing'][2] if len(dims['routing']) > 2 else []

    return {'scenario': scenario['id'], 'verdict': verdict,
            'dimensions': dims_out,
            'cost': {'total_effective_tokens': cost_tok},
            'routing_tree': format_routing_tree(session),
            'reasons': unscorable_reasons,
            'trimmed_warning': detect_trimmed_session(session)}, code


def print_report(result):
    """Every dimension is always printed (computed independently — iter 1 fix, Oliver bd:B1):
    a dimension missing its own input shows UNSCORABLE with its own reason; sibling dimensions
    still show real PASS/FAIL. Routing tree is reconstructed + printed regardless of scenario
    match, so a human can eyeball a real run even when routing doesn't match golden."""
    print(f"Scenario: {result['scenario']}")
    if result.get('trimmed_warning'):
        print('  WARNING: this session looks trimmed (every text block <=81 chars) — '
              'Evidence/Anti-puppet are NOT trim-safe (Quinn, 06-quinn-3b.md); score real transcripts for those two.')
    label = [('routing', 'Routing'), ('spec_fidelity', 'Spec fidelity'), ('security_trigger', 'Security trig'),
             ('evidence', 'Evidence'), ('anti_puppet', 'Anti-puppet'), ('bd_end_state', 'bd end_state')]
    for key, name in label:
        d = result['dimensions'][key]
        print(f"  {name:<15} {d['verdict']:<11} ({d['detail']})")
        if key == 'routing':
            for s in d.get('steps') or []:
                if len(s['agents']) > 1:
                    print(f"    step{s['step']} {s['agents']} parallel={s['parallel']} "
                          f"(spawned across {s['batches']} message(s), ts={s['timestamps']})")
            tree = result.get('routing_tree') or []
            if tree:
                print('    routing tree (reconstructed, informational):')
                for line in tree:
                    print(f'      {line}')
            else:
                print('    routing tree: (no Agent/Task spawn found in any file)')
    c = result['cost']['total_effective_tokens']
    print(f"  {'Cost':<15} {'—':<11} (this run total {c:,} tok; median/p90 across N runs: usage-report.py --compare)")
    print(f"Overall: {result['verdict']}")
    if result.get('reasons'):
        print('  (unscorable critical dim reasons: ' + ' | '.join(result['reasons']) + ')')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('session')
    ap.add_argument('--scenario', required=True)
    ap.add_argument('--golden', default=os.path.join('eval', 'scenarios', 'golden.json'))
    ap.add_argument('--outputs-dir', default=os.path.join(os.getcwd(), 'outputs'))
    ap.add_argument('--out', default=None)
    args = ap.parse_args(argv)

    scenario = load_golden(args.golden, args.scenario)
    fixture_root = os.path.dirname(args.outputs_dir.rstrip('/')) or '.'
    result, code = score(args.session, scenario, fixture_root)
    print_report(result)

    if args.out:
        out_dir = os.path.join(args.out, scenario['id'])
        os.makedirs(out_dir, exist_ok=True)
        json.dump(result, open(os.path.join(out_dir, 'score.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        print(f'-> {os.path.join(out_dir, "score.json")}')
    return code


if __name__ == '__main__':
    sys.exit(main())
