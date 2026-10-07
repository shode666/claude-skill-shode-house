#!/usr/bin/env python3
"""คำนวณ static context budget จาก dispatch graph จริง (WS9).

ห้ามดูแค่ agent file หรือ preload แยกกัน — ต้องรวม:
  command + output style + agents dispatched + agent core + preload skills + required lazy refs

Data-driven (v4 ADR §7 W1): the shipped skill buckets and the plugin name come from
.claude-plugin/plugin.json, the output style is the one marked `force-for-plugin: true`, and a preload
may be written bare (`x`) or namespaced (`<plugin>:x`). A preload that resolves to no shipped skill, a
missing scenario agent, or not exactly one forced style is an error -- never a silent 0 B, which would
make a scenario look artificially cheap. A scenario agent written `?name` is counted only while
agents/name.md exists (a role the 4.0.0 switch retires).

usage:
  scripts/context-budget.py            แสดงตาราง
  scripts/context-budget.py --json     machine-readable
  scripts/context-budget.py --check    เทียบกับ .workflow-scenario-budget แล้ว exit 1 ถ้าเกิน
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def die(msg):
    print(f"  X context budget: {msg}")
    sys.exit(2)


def size(p):
    return os.path.getsize(p) if os.path.exists(p) else 0


def required_size(p):
    if not os.path.isfile(p):
        die(f"required file missing: {p}")
    return os.path.getsize(p)


def manifest():
    try:
        data = json.load(open('.claude-plugin/plugin.json', encoding='utf-8'))
        buckets = [s.strip('./').split('/')[-1] for s in data['skills']]
        return data['name'], [b for b in buckets if b]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        die(f".claude-plugin/plugin.json unreadable or without name/skills ({e!r})")


PLUGIN, BUCKETS = manifest()
SKILLS = {os.path.basename(os.path.dirname(p)): p for b in BUCKETS for p in glob.glob(f'skills/{b}/*/SKILL.md')}


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        return []
    return lines[1:lines.index('---', 1)]


# YAML spellings a host may read as a boolean (1.1 and 1.2 core), quoted or not, any case (Sentinel W3-4):
# CI must count a style as forced whenever the host might, and must not guess about anything else.
TRUTHY, FALSY = {'true', 'yes', 'on', 'y'}, {'false', 'no', 'off', 'n'}


def force_flag(path):
    """True / False for a style's `force-for-plugin:` (absent = False); an unknown value is an error.
    The key may be quoted (YAML reads "force-for-plugin" as the same key); a second occurrence is an error,
    because hosts disagree on a duplicate key (last wins, first wins or a parse error) (Chris W1 r2 L-1)."""
    found = [m for m in (re.fullmatch(r'(?P<q>["\']?)force-for-plugin(?P=q)\s*:\s*(?P<v>.*?)\s*(?:#.*)?', line)
                         for line in frontmatter(open(path, encoding='utf-8').read())) if m]
    if len(found) > 1:
        die(f"{path}: force-for-plugin is a duplicate key ({len(found)} lines); hosts disagree on which one wins")
    for m in found:
        value = m.group('v')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1].strip()
        if value.lower() in TRUTHY:
            return True
        if value.lower() in FALSY or value == '':
            return False
        die(f"{path}: force-for-plugin: {m.group('v')!r} is not a recognisable boolean (write true or false)")
    return False


def forced_style():
    forced = [p for p in sorted(glob.glob('output-styles/*.md')) if force_flag(p)]
    if len(forced) != 1:
        die(f"expected exactly one output style with 'force-for-plugin: true', found {forced or 'none'}")
    return forced[0]


def preload_names(text):
    m = next((re.match(r'skills:\s*(.*)$', l) for l in frontmatter(text) if l.startswith('skills:')), None)
    if not m:
        return []
    try:
        names = json.loads(m.group(1))
    except ValueError:
        names = None
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        die(f"skills: must be a one-line JSON array of strings, got {m.group(1)!r}")
    prefix = PLUGIN + ':'
    return [n[len(prefix):] if n.startswith(prefix) else n for n in names]


def agent(name):
    """body + preload ของ agent 1 ตัว"""
    p = f'agents/{name}.md'
    if not os.path.isfile(p):
        die(f"agent file missing: {p}")
    s = open(p, encoding='utf-8').read()
    names = preload_names(s)
    unknown = [n for n in names if n not in SKILLS]
    if unknown:
        die(f"{name}: preload {unknown} is not a shipped skill (buckets {BUCKETS})")
    pre = sum(size(SKILLS[n]) for n in names)
    return {'body': size(p), 'preload': pre, 'total': size(p) + pre, 'skills': names}


# scenario = command + output style + agents ที่ถูก dispatch + lazy ref ที่ required ใน scenario นั้น
SCENARIOS = {
    'consult':            ('commands/consult.md',       ['solution-architect'], []),
    'design-system-be':   ('commands/design-system.md', ['business-analyst','solution-architect'], []),
    'design-system-fe':   ('commands/design-system.md', ['business-analyst','solution-architect','ux-ui-designer','fintech-expert'],
                           ['references/runbooks/ux-ui-designer-phase-1b.md']),
    'implement-be':       ('commands/implement.md',     ['developer','code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md']),
    'implement-ui':       ('commands/implement.md',     ['developer','ux-ui-designer','code-reviewer','qa-engineer','business-analyst'],
                           ['references/runbooks/ux-ui-designer-phase-3a.md','skills/discipline/review-checklist/spec-axis.md']),
    'phase3b-base':       ('commands/implement.md',     ['code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md','skills/discipline/review-checklist/report-format.md']),
    'phase3b-sensitive':  ('commands/implement.md',     ['code-reviewer','qa-engineer','business-analyst','security-engineer','fintech-expert'],
                           ['skills/discipline/review-checklist/spec-axis.md','skills/discipline/review-checklist/report-format.md']),
    'review-cmd':         ('commands/review.md',        ['code-reviewer','qa-engineer','business-analyst'],
                           ['skills/discipline/review-checklist/spec-axis.md']),
    'diagnose-fast':      (None,                         ['developer'], ['skills/workflow/diagnose/SKILL.md']),
    'diagnose-full':      (None,                         ['developer','qa-engineer'],
                           ['skills/workflow/diagnose/SKILL.md','skills/workflow/diagnose/full-investigation.md','skills/workflow/diagnose/loop-ladder.md']),
    'map-mode':           (None,                         ['?orchestrator','product-manager'],
                           ['skills/discipline/shode-house-workflow/wayfinding.md']),
    'full-fanout':        (None,                         sorted(os.path.basename(p)[:-3] for p in glob.glob('agents/*.md')), []),
}
OUTPUT_STYLE = required_size(forced_style())


def present(agents):
    """`?name` = optional (retired by the 4.0.0 switch); every other agent must exist."""
    return [a[1:] for a in agents if a.startswith('?') and os.path.isfile(f'agents/{a[1:]}.md')] + \
           [a for a in agents if not a.startswith('?')]


def scenario(cmd, agents, refs):
    agents = present(agents)
    a = {n: agent(n) for n in agents}
    command = required_size(cmd) if cmd else 0
    lazy = sum(required_size(r) for r in refs)
    return {
        'command': command,
        'output_style': OUTPUT_STYLE,
        'agents': sum(v['total'] for v in a.values()),
        'lazy_refs': lazy,
        'total': command + OUTPUT_STYLE + sum(v['total'] for v in a.values()) + lazy,
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
