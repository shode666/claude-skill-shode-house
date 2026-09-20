#!/usr/bin/env python3
"""Rule conservation gate (v3.13 finding F28; repaired v3.17 FR-G-1 / ADR-9.1).

refactor ที่ 'ย้าย' กฎออกจาก skill/agent ต้องมีกฎนั้นอยู่ที่อื่นเสมอ
budget ratchet ทุกตัว (#16/#20/#22) ให้รางวัลกับการ 'ลบ' กฎ -- gate นี้คือตัวถ่วง

Usage: rule-conservation.py [--base <ref>] [--root-only <anchor> ...]   (run from repo root)
  --base  compare `git show <base>:<path>` with the WORKING TREE (default HEAD).
          CI: merge-base with origin/main; phase gate: the baseline tag.

กติกาที่ทำให้ gate นี้ไม่เป็นของประดับ:
  1. changed set = `git diff --no-renames --name-only <base>` -- rename detection hides the old path
     (Quinn Q2); a deleted/moved file = empty current text, never a crash (B2).
  2. scope = every .md of the 5 shipped skill buckets + agents/*.md. deprecated/ + in-progress/ are
     neither checked nor allowed to 'hold' a rule.
  3. a rule line = any instruction line REMOVED from its file that is not a heading / blockquote /
     table separator / fenced example / pointer-only and has >= 4 tokens. The red marker and "ห้าม"
     no longer decide protection (Sentinel S7); they only keep a fenced line in scope and tag the report.
  4. corpus = files that can really host a rule (skills + agents + commands + output-styles +
     references/runbooks) in the working tree -- README/docs/eval describe rules, they do not hold them.
  5. tier: a removed line from a root-tier file (SKILL.md / agent file without a `LOAD:` block) that
     carries a `root_only` anchor of .enforcement-map.json must still be found in the ROOT tier;
     a lazy reference does not count (Sentinel S3). No root_only list yet = check is inert, not an error.
  6. เทียบทีละ fragment -- บรรทัดเดียวมักผสมตัวกฎกับข้อความนำทาง. Exceptions only via .rule-migrations.json
     (exact source + fragment, anchors validated by rule-migrations.py) -- a migration never waives rule 5.
"""
import argparse, importlib.util, json, pathlib, re, subprocess, sys

THRESHOLD = 0.55
TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_.\-]{2,}|[฀-๿]{3,}')
STOP = {'ที่', 'และ', 'ของ', 'ให้', 'ไม่', 'เป็น', 'ต้อง', 'the', 'and', 'for', 'not'}
HOST = ('skills/', 'agents/', 'commands/', 'output-styles/', 'references/runbooks/')
BUCKETS = 'workflow|ops|ui|style|discipline'
SCOPE = re.compile(rf'skills/(?:{BUCKETS})/.+\.md|agents/[^/]+\.md')
ROOT_FILE = re.compile(rf'skills/(?:{BUCKETS})/[^/]+/SKILL\.md|agents/[^/]+\.md')
SKIP_DIRS = {'in-progress', 'deprecated'}
TABLE_SEP = re.compile(r'^[\s|:\-]+$')


def toks(line): return {t.lower() for t in TOKEN.findall(line)} - STOP
def is_marked(line): return '🔴' in line or 'ห้าม' in line
def norm(text): return ' '.join(text.split())


def instruction_lines(text):
    """Check instructions, not discovery metadata or its example triggers."""
    lines = text.splitlines()
    if lines and lines[0] == '---':
        end = lines.index('---', 1)  # malformed frontmatter fails closed
        return lines[end + 1:]
    return lines


def rule_lines(text):
    """Candidate rule lines, marker-independent (S7). Fenced examples count only when marked."""
    out, fenced = [], False
    for line in instruction_lines(text):
        s = line.strip()
        if s.startswith(('```', '~~~')):
            fenced = not fenced
            continue
        if len(s) < 25 or s.startswith(('#', '>')) or TABLE_SEP.match(s):
            continue
        if fenced and not is_marked(s):
            continue
        out.append(line)
    return out


def is_lazy(text): return re.search(r'^LOAD:', text, re.M) is not None


def git(*args):
    r = subprocess.run(('git',) + args, capture_output=True, text=True)
    return r.returncode, r.stdout


def load_migrations(root):
    if not (root / '.rule-migrations.json').is_file():
        return {}
    spec = importlib.util.spec_from_file_location(
        'rule_migrations', pathlib.Path(__file__).with_name('rule-migrations.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load(root)


def bad_migration(root):
    """Best-effort: name the entry whose replacement target is gone (the loader's message does not)."""
    try:
        items = json.loads((root / '.rule-migrations.json').read_text())['migrations']
        bad = [i for i in items if not (root / str(i.get('replacement', ''))).is_file()]
    except (ValueError, KeyError, TypeError, AttributeError):
        return ''
    return ''.join(f"\n    entry source={i.get('source')!r} replacement={i.get('replacement')!r} (file not found): "
                   f"{str(i.get('old_fragment'))[:60]}" for i in bad)


def root_only_anchors(root, extra):
    """anchors of enforcement-map rules flagged root_only (ticket .6 owns the list; absent = none)."""
    anchors = [norm(a) for a in extra]
    path = root / '.enforcement-map.json'
    if path.is_file():
        anchors += [norm(r.get('anchor', '')) for r in json.loads(path.read_text()).get('rules', [])
                    if r.get('root_only') is True]
    return [a for a in anchors if a]


class Corpus:
    """Token sets of every current instruction line, with an inverted index for the overlap search."""
    def __init__(self):
        self.lines, self.index = [], {}

    def add(self, text):
        for line in instruction_lines(text):
            t = toks(line)
            if t:
                for tok in t:
                    self.index.setdefault(tok, []).append(len(self.lines))
                self.lines.append(t)

    def best(self, old):
        hits = {}
        for tok in old:
            for i in self.index.get(tok, ()):
                hits[i] = hits.get(i, 0) + 1
        return max(hits.values(), default=0) / len(old)


def build_corpora(root):
    everything, root_tier = Corpus(), Corpus()
    for p in sorted(root.rglob('*.md')):
        rel = p.relative_to(root).as_posix()
        if not rel.startswith(HOST) or SKIP_DIRS & set(p.parts):
            continue
        text = p.read_text(errors='ignore')
        everything.add(text)
        if ROOT_FILE.fullmatch(rel) and not is_lazy(text):
            root_tier.add(text)
    return everything, root_tier


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--base', default='HEAD', help='git ref to compare the working tree against')
    ap.add_argument('--root-only', action='append', default=[], metavar='ANCHOR',
                    help='extra root-only anchor (in addition to .enforcement-map.json root_only rules)')
    args = ap.parse_args(argv)
    root = pathlib.Path.cwd()

    if git('rev-parse', '--verify', '--quiet', args.base + '^{commit}')[0] != 0:
        print(f"  X rule conservation: base ref '{args.base}' not found (shallow clone? fetch-depth: 0)")
        return 2
    rc, names = git('diff', '--no-renames', '--name-only', args.base, '--')
    if rc != 0:
        print("  X rule conservation: git diff failed"); return 2
    changed = [f for f in names.splitlines()
               if SCOPE.fullmatch(f) and not SKIP_DIRS & set(f.split('/'))]
    if not changed:
        print(f"  ok no skill/agent file changed vs {args.base}"); return 0

    try:
        migrations = load_migrations(root)
    except (ValueError, KeyError, TypeError) as e:  # loader fails closed; say which entry, no traceback
        print(f"  X rule conservation: .rule-migrations.json invalid -- {e!r}{bad_migration(root)}")
        return 2
    anchors = root_only_anchors(root, args.root_only)
    everything, root_tier = build_corpora(root)

    fail = checked = 0
    for f in changed:
        rc, old_text = git('show', f'{args.base}:{f}')
        if rc != 0:
            continue  # file is new since base: nothing to conserve
        path = root / f
        cur_text = path.read_text(errors='ignore') if path.is_file() else ''  # deleted/moved = empty
        cur_lines = {norm(l) for l in instruction_lines(cur_text)}
        was_root = ROOT_FILE.fullmatch(f) and not is_lazy(old_text)
        for line in rule_lines(old_text):
            if norm(line) in cur_lines:
                continue  # untouched line
            tier_anchor = next((a for a in anchors if a in norm(line)), None) if was_root else None
            corpus = root_tier if tier_anchor else everything
            for frag in re.split(r'[·|]|\. ', line):
                frag = frag.strip()
                migration = migrations.get((f, frag))
                if migration and not tier_anchor:
                    print(f"  migrated {f}: {frag[:48]} -> {migration['replacement']} (structural trace; not runtime proof)")
                    continue
                old = toks(frag)
                if len(old) < 4 or any(t.endswith('.md') for t in old):
                    continue
                checked += 1
                best = corpus.best(old)
                if best < THRESHOLD:
                    mark = '🔴 ' if is_marked(line) else ''
                    why = (f"root-only rule '{tier_anchor}' ไม่อยู่ใน root tier (SKILL.md/agent)" if tier_anchor
                           else "กฎหาย")
                    gone = '' if path.is_file() else ' [file deleted]'
                    print(f"  X {f}{gone}: {why} ({best:.0%} match) -- {mark}{frag[:72]}")
                    fail = 1
    if not fail:
        print(f"  ok rule conservation vs {args.base} ({len(changed)} file, {checked} removed fragment, "
              f"{len(anchors)} root-only anchor)")
    return fail


if __name__ == '__main__':
    sys.exit(main())
