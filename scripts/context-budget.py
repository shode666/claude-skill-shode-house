#!/usr/bin/env python3
"""คำนวณ static context budget จาก dispatch graph จริง (WS9).

ห้ามดูแค่ agent file หรือ preload แยกกัน — ต้องรวม:
  command + output style + agents dispatched + agent core + preload skills + required lazy refs

usage:
  scripts/context-budget.py            แสดงตาราง
  scripts/context-budget.py --json     machine-readable
  scripts/context-budget.py --check    เทียบกับ .workflow-scenario-budget แล้ว exit 1 ถ้าเกิน
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def size(p):
    return os.path.getsize(p) if os.path.exists(p) else 0

SKILLS = {os.path.basename(os.path.dirname(p)): p for p in glob.glob('skills/*/*/SKILL.md')}

def agent(name):
    """body + preload ของ agent 1 ตัว"""
    p = f'agents/{name}.md'
    s = open(p, encoding='utf-8').read()
    m = re.search(r'^skills:\s*\[(.*?)\]', s, re.M)
    names = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    pre = sum(size(SKILLS[n]) for n in names if n in SKILLS)
    return {'body': size(p), 'preload': pre, 'total': size(p) + pre, 'skills': names}

# scenario = command + output style + agents ที่ถูก dispatch + lazy ref ที่ required ใน scenario นั้น
SCENARIOS = {
    'consult':            ('commands/consult.md',       ['solution-architect'], []),
    'design-system-be':   ('commands/design-system.md', ['business-analyst','solution-architect'], []),
    'design-system-fe':   ('commands/design-system.md', ['business-analyst','solution-architect','ux-ui-designer','fintech-expert'],
                           ['references/runbooks/uma-phase-1b.md']),
    'implement-be':       ('commands/implement.md',     ['developer','code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md']),
    'implement-ui':       ('commands/implement.md',     ['developer','ux-ui-designer','code-reviewer','qa-engineer','business-analyst'],
                           ['references/runbooks/uma-phase-3a.md','skills/discipline/review-checklist/spec-axis.md']),
    'phase3b-base':       ('commands/implement.md',     ['code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md','skills/discipline/review-checklist/report-format.md']),
    'phase3b-sensitive':  ('commands/implement.md',     ['code-reviewer','qa-engineer','business-analyst','security-engineer','fintech-expert'],
                           ['skills/discipline/review-checklist/spec-axis.md','skills/discipline/review-checklist/report-format.md']),
    'review-cmd':         ('commands/review.md',        ['code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md']),
    'diagnose-fast':      (None,                         ['developer'], ['skills/workflow/diagnose/SKILL.md']),
    'diagnose-full':      (None,                         ['developer','qa-engineer'],
                           ['skills/workflow/diagnose/SKILL.md','skills/workflow/diagnose/loop-ladder.md']),
    'map-mode':           (None,                         ['orchestrator','product-manager'],
                           ['skills/discipline/shode-house-workflow/wayfinding.md']),
    'full-fanout':        (None,                         sorted(os.path.basename(p)[:-3] for p in glob.glob('agents/*.md')), []),
}
OUTPUT_STYLE = size('output-styles/oliver.md')

def scenario(cmd, agents, refs):
    a = {n: agent(n) for n in agents}
    return {
        'command': size(cmd) if cmd else 0,
        'output_style': OUTPUT_STYLE,
        'agents': sum(v['total'] for v in a.values()),
        'lazy_refs': sum(size(r) for r in refs),
        'total': (size(cmd) if cmd else 0) + OUTPUT_STYLE + sum(v['total'] for v in a.values()) + sum(size(r) for r in refs),
        'agent_count': len(agents),
    }

res = {k: scenario(*v) for k, v in SCENARIOS.items()}

if '--json' in sys.argv:
    print(json.dumps({'scenarios': res, 'agents': {n: agent(n) for n in
          (os.path.basename(p)[:-3] for p in sorted(glob.glob('agents/*.md')))}}, indent=2))
    sys.exit(0)

if '--check' in sys.argv:
    budget, fail = {}, 0
    if os.path.exists('.workflow-scenario-budget'):
        for line in open('.workflow-scenario-budget', encoding='utf-8'):
            line = line.split('#')[0].strip()
            if '=' in line:
                k, v = line.split('='); budget[k.strip()] = int(v)
    for k, v in sorted(res.items()):
        cap = budget.get(k)
        if cap is None:
            print(f"  X {k}: ไม่มี budget ใน .workflow-scenario-budget"); fail = 1
        elif v['total'] > cap:
            print(f"  X {k}: {v['total']:,} B > budget {cap:,} B"); fail = 1
    print("  ok scenario budgets" if not fail else "  scenario budget FAILED")
    sys.exit(fail)

print(f"{'scenario':22} {'total':>9} {'agents':>8} {'preload+body':>13} {'lazy':>7} {'n':>3}")
for k, v in sorted(res.items(), key=lambda x: -x[1]['total']):
    print(f"{k:22} {v['total']:9,} {v['agents']:8,} {v['agents']:13,} {v['lazy_refs']:7,} {v['agent_count']:3}")
