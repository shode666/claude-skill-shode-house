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
# iter11 (Oliver bd:B1): first REAL GS1 run found the iter7 fix only covered the Recite Card
# appearing as the WHOLE text block (bare `[shode-house|discipline|v3.10] ...`). The real card is
# usually pasted inside a fenced code block ("```\n[shode-house|discipline|v3.10]\n1. NO MAGIC...\n
# 2. VERIFY BEFORE DONE...\n```", any version e.g. v3.5 in a subagent) sitting alongside OTHER real
# content in the same text block -- `text.startswith(RECITE_CARD_PREFIX)` never matches because the
# text starts with the fence marker, not the card. Fix (a): match the recite card by its FIRST LINE
# pattern (any version number), and strip only the fenced block(s) whose first line matches it,
# leaving any other real content in the same text block intact for normal claim scanning.
RECITE_CARD_FIRST_LINE_RE = re.compile(r'^\[shode-house\|discipline\|v[0-9.]+\]')
_FENCE_BLOCK_RE = re.compile(r'```[^\n]*\n.*?```', re.DOTALL)
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

# bd:B3 / B1 iter12 (Oliver, Sara §2/§6): REVIEW DISPATCH CARD persona label -> agentType map.
# Moved here (top-of-file, ahead of its first use) in iter13 so PERSONA_AGENT_TYPE (relay-evidence
# roster below, in the Evidence section) can build directly on it without a definition-order issue.
CARD_AGENT_TYPE = {
    'Chris': 'shode-house:code-reviewer',
    'Quinn': 'shode-house:qa-engineer',
    'Bella': 'shode-house:business-analyst',
    'Sentinel': 'shode-house:security-engineer',
}


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
    """-> dict(main_path, main=[records], subagents={agentId:{records, meta, path}})

    iter9 (Oliver bd:B1): real Claude Code on-disk layout is
    `~/.claude/projects/<proj>/<session-id>.jsonl` (a FILE, sibling files for other sessions) with
    subagents at `~/.claude/projects/<proj>/<session-id>/subagents/agent-*.jsonl|.meta.json` — i.e.
    a directory *named after the session id*, not a flat `<proj>/subagents/` next to every session's
    jsonl. The old flat-`subagents/`-next-to-file assumption silently resolved zero subagents on a
    real transcript (65/65 unresolved -> routing UNSCORABLE). Fix: when given a `.jsonl` file path,
    prefer `<dirname>/<stem>/subagents/` (real layout) and fall back to the old flat
    `<dirname>/subagents/` only if that doesn't exist (keeps any pre-existing flat fixtures working).
    When given a directory, prefer `main.jsonl` if present (synthetic fixture convention used
    throughout this test suite), else the single `*.jsonl` in it if there's exactly one, else fall
    back to the largest-by-size file (old ambiguous-multi-file behavior, unchanged)."""
    if os.path.isdir(path):
        candidates = [p for p in glob.glob(os.path.join(path, '*.jsonl'))]
        main_in_dir = os.path.join(path, 'main.jsonl')
        if os.path.isfile(main_in_dir):
            main_path = main_in_dir
        elif len(candidates) == 1:
            main_path = candidates[0]
        else:
            main_path = max(candidates, key=os.path.getsize) if candidates else None
        sub_dir = os.path.join(path, 'subagents')
    else:
        main_path = path
        dirname = os.path.dirname(path) or '.'
        stem = os.path.splitext(os.path.basename(path))[0]
        session_id_sub_dir = os.path.join(dirname, stem, 'subagents')
        flat_sub_dir = os.path.join(dirname, 'subagents')
        sub_dir = session_id_sub_dir if os.path.isdir(session_id_sub_dir) else flat_sub_dir
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
            # iter14 (Oliver, 2026-09-08): execution window of the subagent = first/last record
            # timestamp in its own jsonl. Used by check_routing to decide real concurrency —
            # Claude Code's Agent tool launches async (`status: async_launched`, returns ~2s), so
            # members of a parallel step land in SEPARATE assistant messages seconds apart yet run
            # concurrently. "same message" was a false sequential signal on every real GS1 run.
            ts = [r.get('timestamp') for r in (a.get('records') or []) if r.get('timestamp')]
            if ts:
                spawn['window_start'] = min(ts)
                spawn['window_end'] = max(ts)

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
    `parallel` is reported per matched step as informational text/data only. iter14: true iff the
    members' subagent execution windows (first..last record timestamp of each subagent file)
    all overlap at one instant — max(start) <= min(end) — i.e. they really ran concurrently
    (Claude Code launches Agent async, so "same assistant message" is NOT the right signal).
    When no member carries a window (synthetic fixtures / unresolved subagents) it falls back to
    the old same-message rule. `concurrency` names which rule fired:
    'overlap' | 'sequential' | 'same-message' | 'separate-messages'.

    iter9 (Oliver bd:B1): a step can carry `"optional": true` (e.g. GS1's trailing developer
    fix-iteration step, which only happens when /review finds something to fix) — if an optional
    step's agents are never observed, that is NOT a routing FAIL, just a skipped/unobserved step;
    `ptr` does not advance past it, and later required steps still match normally from the same
    position."""
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
        optional = bool(step.get('optional'))
        collected = set()
        batches_used = set()
        timestamps = []
        windows = []
        j = ptr
        finished_at = None
        while j < n:
            spawn = flat[j]
            atype = spawn.get('agentType')
            if atype in exp:
                collected.add(atype)
                batches_used.add(spawn['_batch_idx'])
                timestamps.append(spawn.get('timestamp'))
                if spawn.get('window_start') and spawn.get('window_end'):
                    windows.append((spawn['window_start'], spawn['window_end']))
                j += 1
                if collected >= exp:
                    finished_at = j
                    break
                continue
            if atype in all_expected:
                if optional and not collected:
                    # iter9: an optional step hasn't started collecting yet and we've hit a spawn
                    # belonging to a DIFFERENT step -- treat as "not observed", not an order
                    # violation; leave ptr where it was and let the outer loop try later steps.
                    break
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
            if optional:
                steps_info.append({'step': i + 1, 'agents': sorted(exp), 'parallel': False,
                                    'batches': 0, 'timestamps': [], 'optional': True, 'observed': False})
                continue  # skipped, not a failure; ptr unchanged, next step matches from here
            return 'FAIL', f'step {i+1} missing: expected {sorted(exp)}, only found {sorted(collected)}', steps_info
        same_message = len(batches_used) == 1 and len(exp) > 1
        if len(exp) > 1 and len(windows) == len(exp):
            overlap = max(w[0] for w in windows) <= min(w[1] for w in windows)
            parallel_observed = overlap
            concurrency = 'overlap' if overlap else 'sequential'
        else:
            parallel_observed = same_message
            concurrency = 'same-message' if same_message else 'separate-messages'
        steps_info.append({'step': i + 1, 'agents': sorted(exp), 'parallel': parallel_observed,
                            'concurrency': concurrency, 'same_message': same_message,
                            'batches': len(batches_used), 'timestamps': timestamps,
                            'windows': windows, 'optional': optional, 'observed': True})
        ptr = finished_at
    parallel_notes = '; '.join(f"step{s['step']} parallel={s['parallel']}({s['concurrency']})"
                                for s in steps_info if len(s['agents']) > 1 and s.get('observed', True))
    observed_count = sum(1 for s in steps_info if s.get('observed', True))
    detail = f"{observed_count}/{len(expected)} steps matched"
    skipped = [s['step'] for s in steps_info if not s.get('observed', True)]
    if skipped:
        detail += f'; optional step(s) not observed (skipped, not a failure): {skipped}'
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


def _strip_recite_card(text):
    """iter11 (Oliver bd:B1) fix (a): removes Recite Card content before claim scanning, handling
    both shapes seen on real transcripts:
      1. the whole text block IS the card, unfenced (iter7's original repro) -- text itself
         starts with the card's first-line pattern.
      2. the card is pasted inside a fenced code block alongside OTHER real content in the same
         text block (iter11's real repro, main AND subagent, any version e.g. v3.10/v3.5) -- only
         the qualifying fenced block(s) are stripped; anything else in the text is left intact for
         normal claim scanning (so a claim sitting next to a recited card is still caught)."""
    def _maybe_strip_fence(m):
        block = m.group(0)
        inner = block.split('\n', 1)[1] if '\n' in block else ''
        first_line = inner.split('\n', 1)[0].strip()
        return '' if RECITE_CARD_FIRST_LINE_RE.match(first_line) else block

    stripped = _FENCE_BLOCK_RE.sub(_maybe_strip_fence, text)
    if RECITE_CARD_FIRST_LINE_RE.match(stripped.strip()):
        return ''
    return stripped


# iter11 (Oliver bd:B1) fix (b): first REAL GS1 run flagged Oliver relaying a subagent's verdict
# ("[Oliver|state:3b|bd:...] Quinn PASS (...) — รอ Felix") right after the Agent tool_result for
# Quinn as an anti-puppet violation. A real transcript can have a few housekeeping records
# (permission/hook/system entries, additional Read/Glob calls Oliver made before relaying) between
# the subagent's tool_result and the relay text -- the old fixed 3-record lookback was too tight
# for that realistic gap. Widened to 8 (still bounded, not unlimited scan-to-start-of-file).
EVIDENCE_LOOKBACK_WINDOW = 8

# iter13 (Oliver bd:B1): real GS1 run-2 still flagged an Oliver relay line, verbatim:
# "[Oliver|state:3b-running|bd:769] Quinn: **PASS** (...) — เหลือ Chris". Two fixes:
# (a) strip markdown emphasis (`*`/`_`) before matching -- defensive; Oliver named this as a
#     *probable* cause, not confirmed, so applied regardless.
# (b) the REAL root cause: EVIDENCE_LOOKBACK_WINDOW=8 is still bounded, and other tool calls
#     (e.g. `bd update`) between the subagent's tool_result and the relay text can legitimately
#     push it further back than any reasonable fixed window. A main-session line that starts with
#     an Oliver tag prefix and names a known persona followed by a verdict IS a relay, by
#     construction (Tag Prefix + Return format, shode-house-broadcast) -- it is evidenced if that
#     persona's agent type was spawned ANYWHERE earlier in the same main file, not window-bound.
MARKDOWN_EMPHASIS_CHARS = str.maketrans('', '', '*_')


def _strip_markdown_emphasis(text):
    """iter13 fix (a): removes literal `*`/`_` markdown-emphasis characters before claim/relay
    matching (word-boundary regex already treats them as non-word chars either way, so this is a
    defensive normalization, not a behavior-changing one for CLAIM_RE itself)."""
    return text.translate(MARKDOWN_EMPHASIS_CHARS)


OLIVER_RELAY_PREFIX_RE = re.compile(r'^\[Oliver\|')
# source of truth for the persona roster: shode-house-broadcast Tag Prefix convention. Reuses
# CARD_AGENT_TYPE (Chris/Quinn/Bella/Sentinel, bd:B3 iter12) and extends with the rest of the team
# that Oliver can plausibly relay a verdict for.
PERSONA_AGENT_TYPE = dict(CARD_AGENT_TYPE)
PERSONA_AGENT_TYPE.update({
    'Dave': 'shode-house:developer',
    'Uma': 'shode-house:ux-ui-designer',
    'Sara': 'shode-house:solution-architect',
    'Aaron': 'shode-house:devops-engineer',
    'Patrick': 'shode-house:product-manager',
    'Felix': 'shode-house:fintech-expert',
})
PERSONA_NAME_RE = re.compile(r'\b(' + '|'.join(sorted(PERSONA_AGENT_TYPE, key=len, reverse=True)) + r')\b')


def _relay_persona_agent_type(text):
    """-> agentType string if `text` is a main-session Oliver relay line (starts with the
    `[Oliver|...]` tag prefix) naming a known persona followed somewhere in the same line by a
    verdict-shaped claim match; else None. Text is expected pre-stripped of markdown/recite-card."""
    if not OLIVER_RELAY_PREFIX_RE.match(text):
        return None
    if not _claim_match(CLAIM_RE, text):
        return None
    m = PERSONA_NAME_RE.search(text)
    if not m:
        return None
    return PERSONA_AGENT_TYPE.get(m.group(1))


def _agent_type_spawned_before(records, before_index, agent_type):
    """-> True if an Agent/Task tool_use declaring `subagent_type == agent_type` appears anywhere
    in records[:before_index] -- UNBOUNDED backward scan (iter13 fix (b), intentionally not
    EVIDENCE_LOOKBACK_WINDOW-limited: a relay can legitimately follow several intervening tool
    calls, e.g. `bd update`, before Oliver writes the summary line)."""
    for rec in records[:before_index]:
        if rec.get('type') != 'assistant':
            continue
        for c in ((rec.get('message') or {}).get('content') or []):
            if (isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') in SPAWN_NAMES
                    and (c.get('input') or {}).get('subagent_type') == agent_type):
                return True
    return False


def find_claim_violations(records, pattern, is_main=False):
    """-> list of (uuid, quoted_text) where claim matched but no evidence adjacency.

    A '```' fence in the claim text is NOT treated as evidence on its own (Chris F2, iter3 —
    cleanup iter4 removed the legacy lenient default per Chris's cut list, always strict now): it
    must still be backed by a real tool_use/tool_result adjacency (window lookback or a tool_use
    in the same record), since a fence's mere presence proves nothing about whether the pasted
    content is real captured tool output.

    Adjacency backward window looks EVIDENCE_LOOKBACK_WINDOW records back, in the SAME file, for a
    tool_result from ANY tool (Bash/Read/Agent/Task/... -- no name filtering; iter11 fix (b)).

    `is_main=True` (iter13 fix (b)) additionally allows an UNBOUNDED-backward relay escape hatch:
    a main-session Oliver relay line naming a known persona + verdict is evidenced if that
    persona's agent type was spawned anywhere earlier in `records` at all, regardless of window."""
    violations = []
    for i, rec in enumerate(records):
        if rec.get('type') != 'assistant':
            continue
        for b in ((rec.get('message') or {}).get('content') or []):
            if not (isinstance(b, dict) and b.get('type') == 'text'):
                continue
            raw_text = b.get('text') or ''
            text = _strip_recite_card(raw_text)  # iter11 fix (a)
            text = _strip_markdown_emphasis(text)  # iter13 fix (a)
            if not text.strip():
                continue
            if not _claim_match(pattern, text):
                continue
            window = records[max(0, i - EVIDENCE_LOOKBACK_WINDOW):i]
            window_evidence = any(
                w.get('type') == 'user' and (w.get('toolUseResult') is not None or any(
                    isinstance(c, dict) and c.get('type') == 'tool_result'
                    for c in ((w.get('message') or {}).get('content') or [])))
                for w in window)
            same_record_tool_use = any(
                isinstance(c, dict) and c.get('type') == 'tool_use'
                for c in ((rec.get('message') or {}).get('content') or []))
            has_evidence = window_evidence or same_record_tool_use
            if not has_evidence and is_main:  # iter13 fix (b)
                persona_agent_type = _relay_persona_agent_type(text)
                if persona_agent_type and _agent_type_spawned_before(records, i, persona_agent_type):
                    has_evidence = True
            if not has_evidence:
                violations.append((rec.get('uuid'), text[:120]))  # (c): quote the flagged line
    return violations


def evidence_dimension(session):
    all_v = []
    for fid, recs in all_files(session).items():
        for uid, text in find_claim_violations(recs, CLAIM_RE, is_main=(fid == 'main')):
            all_v.append(f'{fid}:{uid}: "{text}"')
    if all_v:
        return 'FAIL', f'{len(all_v)} claim(s) without adjacent tool_result: ' + '; '.join(all_v[:5])
    return 'PASS', 'all claims have adjacent tool_result / inline paste'


# ---------- REVIEW DISPATCH CARD (bd:B3 / B1 iter12, Oliver — Sara's 01-sara-1a.md §2/§6) ----------
# /review's non-deterministic fan-out (FACT 1: sequential 3-message spawn missing spec+security
# axes on one run, full 5-agent parallel fan-out on another) is fixed at the prompt layer by a
# mandatory printed block Oliver must emit before spawning anything -- this is the runtime (E2E)
# half of that fix (§6): golden.json's `required_main_phrases` names literal phrase(s) that MUST
# appear in the main transcript (e.g. `[REVIEW DISPATCH CARD]`); if the marker phrase is present,
# the card is additionally PARSED and its DISPATCH-set is compared against the actually-spawned
# agent set. A scenario can also force specific labels to DISPATCH via `required_dispatch_agents`
# (GS1: Sentinel, since GS1's money/ledger/refund/card content makes a SKIP always wrong) --
# independent of whether the card's own DISPATCH/SKIP set is internally self-consistent with what
# was actually spawned.
DISPATCH_CARD_MARKER = '[REVIEW DISPATCH CARD]'
DISPATCH_LINE_RE = re.compile(r'^-\s*([A-Za-z]+)\s*\([^)]*\)\s*:\s*(DISPATCH|SKIP)\b', re.MULTILINE)
# CARD_AGENT_TYPE moved up near CLAIM_RE/PUPPET_HINT (module top) in iter13 so PERSONA_AGENT_TYPE
# (the relay-evidence persona roster, reused/extended from this same map) can build on it without
# a definition-order NameError -- see top-of-file constants.
DOMAIN_AGENT_SUFFIX = '-expert'  # 'Domain' label maps to any shode-house:*-expert (Felix/Iris/...)
CARD_SCAN_WINDOW = 2000  # bounded chars past the marker -- keeps parsing scoped to the printed
                          # card itself, not later prose that happens to mention an agent name


def parse_dispatch_card(main_text):
    """-> dict {agent_label: 'DISPATCH'|'SKIP'} parsed from the first `[REVIEW DISPATCH CARD]`
    block in `main_text`, or {} if the marker isn't present at all."""
    idx = main_text.find(DISPATCH_CARD_MARKER)
    if idx == -1:
        return {}
    card_region = main_text[idx: idx + CARD_SCAN_WINDOW]
    return dict(DISPATCH_LINE_RE.findall(card_region))


def _main_text(session):
    return '\n'.join(
        b.get('text') or '' for rec in session['main']
        for b in ((rec.get('message') or {}).get('content') or [])
        if isinstance(b, dict) and b.get('type') == 'text')


def dispatch_card_check(scenario, session):
    """-> (verdict, detail). N/A when the scenario has no `required_main_phrases` configured
    (this is opt-in per scenario, not a blanket rule on every /review run)."""
    required_phrases = scenario.get('required_main_phrases') or []
    if not required_phrases:
        return 'N/A', 'no required_main_phrases configured for this scenario'

    main_text = _main_text(session)
    missing = [p for p in required_phrases if p not in main_text]
    if missing:
        return 'FAIL', f'required main-transcript phrase(s) missing: {missing}'

    if DISPATCH_CARD_MARKER not in required_phrases:
        return 'PASS', f'all required main-transcript phrases present: {required_phrases}'

    card = parse_dispatch_card(main_text)
    if not card:
        return 'FAIL', (f'{DISPATCH_CARD_MARKER} phrase present but no parseable DISPATCH/SKIP '
                         f'lines found under it')

    required_dispatch = scenario.get('required_dispatch_agents') or []
    forced = [label for label in required_dispatch if card.get(label) != 'DISPATCH']
    if forced:
        return 'FAIL', f'card marks {forced} as SKIP but scenario requires DISPATCH (card: {card})'

    spawn_types = build_spawn_index(session)['all_spawn_types']
    mismatches = []
    for label, verdict in sorted(card.items()):
        if label == 'Domain':
            has_domain_spawn = any(t and t.endswith(DOMAIN_AGENT_SUFFIX) for t in spawn_types)
            if verdict == 'DISPATCH' and not has_domain_spawn:
                mismatches.append('Domain: DISPATCH in card but no *-expert agent spawned')
            elif verdict == 'SKIP' and has_domain_spawn:
                mismatches.append('Domain: SKIP in card but a *-expert agent WAS spawned')
            continue
        atype = CARD_AGENT_TYPE.get(label)
        if atype is None:
            continue  # unrecognized label -- not mappable, don't false-fail on it
        spawned = atype in spawn_types
        if verdict == 'DISPATCH' and not spawned:
            mismatches.append(f'{label}: DISPATCH in card but {atype!r} never spawned')
        elif verdict == 'SKIP' and spawned:
            mismatches.append(f'{label}: SKIP in card but {atype!r} WAS spawned anyway')
    if mismatches:
        return 'FAIL', '; '.join(mismatches)
    dispatch_labels = sorted(label for label, v in card.items() if v == 'DISPATCH')
    return 'PASS', f'DISPATCH-set from card matches spawned set: {dispatch_labels}'


def anti_puppet_dimension(scenario, session):
    violations = []
    for fid, recs in all_files(session).items():
        for uid, text in find_claim_violations(recs, CLAIM_RE, is_main=(fid == 'main')):
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

def bd_end_state(scenario, bd_id_override=None, cwd=None):
    """iter8 (Oliver bd:B1): golden.json's `bd_id` is now optional -- a scenario like
    GS1-reference-refund is scored against a real project's bd tracker where the id is assigned
    at run time, not known ahead in golden.json. `--bd-id <id>` (CLI) lets the caller supply it
    at run time instead; the override always wins over a scenario's own (possibly absent) bd_id.
    If neither is given, bd end_state is UNSCORABLE with its own reason (never PASS/FAIL) --
    same independent-dimension treatment as every other missing-input case (iter1 fix).

    iter9 (Oliver bd:B1): first real GS1 scoring found `bd show` was invoked from the scorer's own
    cwd, not the fixture project's cwd where `.beads` (the bd tracker db) actually lives -- so it
    resolved the wrong (or no) tracker and the expected `CLOSED` status was never found even though
    the real `bd show <id>` output (run from the right directory) plainly printed
    `[● P2 · CLOSED]`. Fix: run with `cwd=<--outputs-dir>` (the caller passes it through); also
    match `bd_status` case-insensitively anywhere in output (defensive — real `bd` output casing is
    not guaranteed identical to golden.json's configured value), and treat a non-zero exit code as
    UNSCORABLE (bd/session likely missing) rather than blindly regex-matching empty/error output.

    iter13 (Oliver bd:B1): real GS1 run-2 false-FAILed here because `bd` stayed OPEN -- which is
    the CORRECT pipeline behaviour for `/review` with unresolved findings, not a bug. `bd_status`
    now accepts either a single string (implement scenarios: CLOSED-only, unchanged) OR a list of
    acceptable statuses (`["OPEN","CLOSED"]` for /review scenarios — either is fine, since /review
    doesn't always close the bd). New `notes_pattern` field independently verifies the review
    verdict was actually RECORDED in `bd show` output (e.g. `Standards|Spec|verdict|PASS|FAIL`) --
    this is what actually proves the review ran and left a trail, since bd_status alone can no
    longer distinguish "reviewed, findings open" from "never reviewed at all" once OPEN is
    accepted."""
    bd_id = bd_id_override or scenario.get('bd_id')
    end = scenario.get('end_state') or {}
    if not bd_id:
        return 'UNSCORABLE', 'no bd_id configured for scenario and no --bd-id override given — cannot check end_state'
    if shutil.which('bd') is None:
        return 'UNSCORABLE', 'bd CLI not found on PATH — cannot verify end_state'
    try:
        r = subprocess.run(['bd', 'show', bd_id], capture_output=True, text=True, timeout=10, cwd=cwd)
    except Exception as e:
        return 'UNSCORABLE', f'bd show failed to run: {e}'
    if r.returncode != 0:
        return ('UNSCORABLE',
                f'bd show {bd_id} exited {r.returncode} (bd/session likely missing): '
                f'{((r.stderr or r.stdout or "").strip())[:200]}')
    out = (r.stdout or '') + (r.stderr or '')
    want_status = end.get('bd_status')
    if want_status:
        acceptable = [want_status] if isinstance(want_status, str) else list(want_status)
        if not any(re.search(re.escape(s), out, re.IGNORECASE) for s in acceptable):
            return 'FAIL', f'none of bd_status {acceptable!r} found (case-insensitive) in `bd show {bd_id}` output'
    vp = end.get('verdict_pattern')
    if vp and not re.search(vp, out):
        return 'FAIL', f'verdict_pattern {vp!r} not matched in bd show output'
    notes_pattern = end.get('notes_pattern')
    if notes_pattern and not re.search(notes_pattern, out):
        return 'FAIL', (f'notes_pattern {notes_pattern!r} not matched in bd show output '
                         f'(review verdict not recorded)')
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


def score(session_path, scenario, fixture_root, bd_id_override=None, outputs_dir=None):
    """Each dimension is computed independently — a dimension lacking its own input becomes
    UNSCORABLE with its own reason; it never wipes the other dimensions (iter 1 fix, Oliver bd:B1).
    Overall: FAIL if any critical dim FAIL; else UNSCORABLE if any critical dim UNSCORABLE; else PASS.
    bd_end_state is reported but NOT critical (would otherwise force UNSCORABLE on every run without
    a `bd` binary on PATH) — same treatment as Cost (report-only).

    iter9 (Oliver bd:B1): `outputs_dir` (the CLI's `--outputs-dir`) is passed through as `bd show`'s
    cwd — that's the fixture project directory where `.beads` (the bd tracker db) actually lives;
    `fixture_root` (used for spec_fidelity's artifact globs) is a *different*, already-existing
    path and must not be conflated with it.

    iter10 (Oliver bd:B1): a real-run edge case — `session_path` pointing at a bad/wrong/empty
    path (0 main records loaded, not merely "no spawns" like the `truncated` fixture's 2 records)
    — was letting `security_trigger()` FAIL on a keyword match found only in `scenario['command']`/
    `scenario['desc']` text (independent of the empty transcript), which is misleading: there is no
    real transcript content to judge here at all. When main has 0 records, every dimension except
    `bd_end_state` (which never reads main records anyway) is forced to UNSCORABLE with one shared
    reason, overriding the normal per-dimension independence for this specific bad-path safety net."""
    session = load_session(session_path)
    main_batches = build_spawn_index(session)['main_batches']

    dims = {}
    if not session['main']:
        no_input = (f'main session has 0 records (bad/empty/missing transcript path: '
                    f'{session_path!r}) — cannot score')
        dims['routing'] = ('UNSCORABLE', no_input, [])
        dims['spec_fidelity'] = ('UNSCORABLE', no_input)
        dims['security_trigger'] = ('UNSCORABLE', no_input)
        dims['evidence'] = ('UNSCORABLE', no_input)
        dims['anti_puppet'] = ('UNSCORABLE', no_input)
    else:
        r_verdict, r_detail, r_steps = check_routing(
            scenario.get('expected_routing') or [], main_batches,
            scenario.get('routing_open_ended', False), len(session['main']))
        # bd:B3 / iter12 (Oliver): a mismatch between the printed [REVIEW DISPATCH CARD]'s
        # DISPATCH-set and the actually-spawned agent set surfaces IN the Routing dimension's
        # detail (Sara §6) -- a FAIL here always wins (strongest signal), regardless of what the
        # step-matching routing check itself concluded; N/A (no required_main_phrases configured)
        # leaves routing completely untouched.
        card_verdict, card_detail = dispatch_card_check(scenario, session)
        if card_verdict == 'FAIL':
            if r_verdict == 'FAIL':
                r_detail = f'{r_detail} | dispatch card: {card_detail}'
            else:
                r_detail = f'dispatch card: {card_detail}'
            r_verdict = 'FAIL'
        dims['routing'] = (r_verdict, r_detail, r_steps)
        dims['spec_fidelity'] = spec_fidelity(scenario, fixture_root)
        dims['security_trigger'] = security_trigger(scenario, session)
        dims['evidence'] = evidence_dimension(session)
        dims['anti_puppet'] = anti_puppet_dimension(scenario, session)
    dims['bd_end_state'] = bd_end_state(scenario, bd_id_override, cwd=outputs_dir)
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
                          f"[{s.get('concurrency', '?')}] "
                          f"(spawned across {s['batches']} message(s), ts={s['timestamps']})")
                    for w in s.get('windows') or []:
                        print(f"      window {w[0]} .. {w[1]}")
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


def resolve_project_root(project, outputs_dir):
    """iter10 (Oliver bd:B1): the old `--outputs-dir` semantics silently assumed the path always
    ended in `/outputs` and took `dirname(outputs_dir)` as the fixture root — so passing the
    project root itself (what a human naturally does, and what RUNBOOK said to do) made every
    `outputs/*/...` glob in golden.json miss entirely. `--project <fixture project root>` replaces
    it directly: golden.json's globs are resolved relative to it, and it is also `bd show`'s cwd
    (where `.beads` lives) — no path-shape guessing. `--outputs-dir` is kept as a DEPRECATED alias
    that maps to the same root: if its basename is exactly `outputs`, the PARENT is used (old
    semantics, unchanged for anyone still passing `.../outputs`); otherwise the path itself IS the
    root directly (covers the exact bug this iteration fixes — someone passing the project root
    into the old `--outputs-dir` flag). `--project` always wins if both are given."""
    if project:
        return project
    if outputs_dir:
        stripped = outputs_dir.rstrip('/') or '/'
        if os.path.basename(stripped) == 'outputs':
            return os.path.dirname(stripped) or '.'
        return stripped
    return os.getcwd()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('session')
    ap.add_argument('--scenario', required=True)
    ap.add_argument('--golden', default=os.path.join('eval', 'scenarios', 'golden.json'))
    ap.add_argument('--project', default=None,
                     help='fixture project root — golden.json required_artifacts/required_evidence '
                          'globs (e.g. "outputs/*/...") are resolved relative to it, and it is also '
                          '`bd show`\'s cwd (where .beads lives). Replaces --outputs-dir (iter10).')
    ap.add_argument('--outputs-dir', default=None,
                     help='DEPRECATED alias for --project (iter10) — kept for backward '
                          'compatibility only; prefer --project.')
    ap.add_argument('--out', default=None)
    ap.add_argument('--bd-id', default=None,
                     help='override/supply bd id for end_state check when golden.json\'s scenario '
                          'has no bd_id (e.g. a real project where the id is assigned at run time)')
    args = ap.parse_args(argv)

    project_root = resolve_project_root(args.project, args.outputs_dir)
    scenario = load_golden(args.golden, args.scenario)
    result, code = score(args.session, scenario, project_root, args.bd_id, project_root)
    print_report(result)

    if args.out:
        out_dir = os.path.join(args.out, scenario['id'])
        os.makedirs(out_dir, exist_ok=True)
        json.dump(result, open(os.path.join(out_dir, 'score.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        print(f'-> {os.path.join(out_dir, "score.json")}')
    return code


if __name__ == '__main__':
    sys.exit(main())
