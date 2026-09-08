#!/usr/bin/env python3
"""Trim session dir to structure-only fixture. Usage: transcript-trim.py <in-dir> <out-dir>

WARNING (iter6, Oliver bd:B1, Quinn 06-quinn-3b.md): trimmed copies are for STRUCTURE tests only
(routing/spawn-tree/security-trigger shape) -- NOT for Evidence/Anti-puppet scoring. Truncating
every text/prompt/tool_result string to the first 80 chars can cut a real claim phrase mid-word,
flipping the Evidence/Anti-puppet verdict versus the untrimmed source (proven: a claim spanning the
80-char boundary matches on the full transcript but not on the trimmed copy, or vice versa).
Evidence/Anti-puppet MUST be scored on full, untrimmed transcripts. eval-scorer.py detects a
likely-trimmed session (every text block <=81 chars) and prints a one-line warning at score time."""
import json, os, sys, shutil
DROP = {'bridge-session', 'queue-operation', 'attachment', 'atis-latch', 'last-prompt', 'custom-title'}
TOP = ['type', 'uuid', 'parentUuid', 'timestamp', 'isSidechain', 'agentId']


def trunc(s):
    return s if not isinstance(s, str) or len(s) <= 80 else s[:80] + '…'


def trim_block(b):
    t = b.get('type')
    if t == 'text':
        return {'type': t, 'text': trunc(b.get('text', ''))}
    if t == 'tool_use':
        i = b.get('input') or {}
        return {'type': t, 'name': b.get('name'), 'id': b.get('id'),
                'input': {k: i[k] for k in ('subagent_type', 'description') if k in i}}
    if t == 'tool_result':
        c = b.get('content')
        c = trunc(c) if isinstance(c, str) else [trim_block(x) if isinstance(x, dict) else trunc(x) for x in (c or [])]
        return {'type': t, 'tool_use_id': b.get('tool_use_id'), 'content': c}
    return {'type': t}


def trim_record(r):
    if r.get('type') in DROP:
        return None
    out = {k: r[k] for k in TOP if k in r}
    if 'toolUseResult' in r:
        out['toolUseResult'] = trunc(json.dumps(r['toolUseResult'], ensure_ascii=False))
    m = r.get('message')
    if isinstance(m, dict):
        out['message'] = {'model': m.get('model'), 'usage': m.get('usage'),
                           'content': [trim_block(b) for b in (m.get('content') or []) if isinstance(b, dict)]}
    return out


def trim_file(src, dst):
    with open(src, encoding='utf-8') as fi, open(dst, 'w', encoding='utf-8') as fo:
        for line in fi:
            try:
                rec = trim_record(json.loads(line))
            except Exception:
                continue
            if rec is not None:
                fo.write(json.dumps(rec, ensure_ascii=False) + '\n')


def main(argv):
    in_dir, out_dir = argv[1], argv[2]
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(in_dir):
        if fn.endswith('.jsonl') and os.path.isfile(os.path.join(in_dir, fn)):
            trim_file(os.path.join(in_dir, fn), os.path.join(out_dir, fn))
    sub = os.path.join(in_dir, 'subagents')
    if os.path.isdir(sub):
        os.makedirs(os.path.join(out_dir, 'subagents'), exist_ok=True)
        for fn in os.listdir(sub):
            src, dst = os.path.join(sub, fn), os.path.join(out_dir, 'subagents', fn)
            shutil.copy(src, dst) if fn.endswith('.meta.json') else trim_file(src, dst)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
