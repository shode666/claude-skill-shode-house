#!/usr/bin/env python3
"""Rule conservation gate (v3.13 finding F28; repaired v3.17 FR-G-1 / ADR-9.1).

refactor ที่ 'ย้าย' กฎออกจาก skill/agent ต้องมีกฎนั้นอยู่ที่อื่นเสมอ
budget ratchet ทุกตัว (#16/#20/#22) ให้รางวัลกับการ 'ลบ' กฎ -- gate นี้คือตัวถ่วง

Usage: rule-conservation.py [--base <ref>] [--root-only <anchor> ...] [--with-styles]
                            [--simulate-delete <path> ...] [--dry-run]   (run from repo root)
  --base  compare `git show <base>:<path>` with the WORKING TREE (default HEAD).
          CI: merge-base with origin/main; phase gate: the baseline tag.
  --with-styles      output-styles/*.md join the CHECKED scope (removed style lines must live on).
                     Automatic when .claude-plugin/plugin.json major >= 4 or SHODE_REQUIRE_V4=1
                     (v4 ADR A5; wired in v3.17.x, not yet required: the 3.17 cycle reworded the style
                     without migration entries, so the pinned-baseline run would be red today).
  --simulate-delete  treat <path> as deleted in the working tree (repeatable) -- planning aid.
  --dry-run          report every lost fragment and its count, always exit 0 (migration-count estimate).

กติกาที่ทำให้ gate นี้ไม่เป็นของประดับ:
  1. changed set = `git diff --no-renames --name-only <base>` -- rename detection hides the old path
     (Quinn Q2); a deleted/moved file = empty current text, never a crash (B2).
  2. scope = every .md of the 5 shipped skill buckets + agents/*.md (+ output-styles/*.md with
     --with-styles / from 4.0.0). deprecated/ + in-progress/ are neither checked nor allowed to 'hold' a rule.
  3. a rule line = any instruction line REMOVED from its file that is not a heading / blockquote /
     table separator / fenced example / pointer-only / safety-floor marker and has >= 4 tokens. The red
     marker and "ห้าม" no longer decide protection (Sentinel S7); they only keep a fenced line in scope and
     tag the report. Only the exact floor markers of scripts/floor.py (`<!-- floor:begin -->`,
     `<!-- floor:end -->`, `<!-- floor:style:begin -->`, `<!-- floor:style:end -->`) are skipped: any
     other HTML comment in a body is live prompt text and can carry a rule.
  4. corpus = files that can really host a rule (skills + agents + commands + output-styles +
     references/runbooks) in the working tree -- README/docs/eval describe rules, they do not hold them.
  5. tier: a removed line from a root-tier file (SKILL.md / agent file / output style without a `LOAD:` block) that
     carries a `root_only` anchor of .enforcement-map.json must still be found in the ROOT tier;
     a lazy reference does not count (Sentinel S3). No root_only list yet = check is inert, not an error.
     An output style reaches the main session only, never a subagent: style text is root-tier credit
     only for a line removed from a style or from a main-session agent (decided from data: the base
     version's `tools:` holds Task or Agent). A subagent's root-only rule moved into the style, or into an
     agent whose CURRENT `tools:` holds Task/Agent (a main-session body), is red. One parser reads `tools:`
     (spawn_tools): a second tools key in any spelling, a variant key spelling or a non-JSON value is
     unreadable and earns no credit (fail closed); `Task(...)` / `Agent(...)` count as spawn tools.
  6. เทียบทีละ fragment -- บรรทัดเดียวมักผสมตัวกฎกับข้อความนำทาง. Exceptions only via .rule-migrations.json
     (exact source + fragment, anchors validated by rule-migrations.py) -- a migration never waives rule 5.
"""
import argparse, importlib.util, json, os, pathlib, re, subprocess, sys

THRESHOLD = 0.55
TOKEN = re.compile(r'[A-Za-z][A-Za-z0-9_.\-]{2,}|[฀-๿]{3,}')
STOP = {'ที่', 'และ', 'ของ', 'ให้', 'ไม่', 'เป็น', 'ต้อง', 'the', 'and', 'for', 'not'}
HOST = ('skills/', 'agents/', 'commands/', 'output-styles/', 'references/runbooks/')
BUCKETS = 'workflow|ops|ui|style|discipline'
SCOPE = re.compile(rf'skills/(?:{BUCKETS})/.+\.md|agents/[^/]+\.md')
STYLE = re.compile(r'output-styles/[^/]+\.md')
# the router style is always-on (main session), so it is root tier like an agent body (v4 ADR §5.10)
ROOT_FILE = re.compile(rf'skills/(?:{BUCKETS})/[^/]+/SKILL\.md|agents/[^/]+\.md|output-styles/[^/]+\.md')
# exactly the floor-marker grammar of scripts/floor.py (KINDS); tests/test_rule_conservation.py pins the match
MARKER = re.compile(r'^<!-- floor:(?:style:)?(?:begin|end) -->$')
SPAWN_TOOLS = {'Task', 'Agent'}  # a type holding one of these spawns subagents = it runs as the main session
TOOLS_KEY = re.compile(r'''^\s*["']?tools["']?\s*:''')  # a tools key in any spelling (F5: count them all)
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
        if len(s) < 25 or s.startswith(('#', '>')) or TABLE_SEP.match(s) or MARKER.match(s):
            continue
        if fenced and not is_marked(s):
            continue
        out.append(line)
    return out


def is_lazy(text): return re.search(r'^LOAD:', text, re.M) is not None


NO_TOOLS = 'no tools: line'  # spawn_tools() result for an agent that omits tools: (the host's default set)


def spawn_tools(text):
    """The one `tools:` parser of main_session() and subagent_visible() (Chris W1 follow-up C-3).
    -> NO_TOOLS when the frontmatter has no tools key, a set of the spawn tools (Task, Agent, and any
    parameterised `Task(...)` / `Agent(...)` form) the one `tools:` line holds, or None when it cannot be read:
    no frontmatter, a tools key spelled any other way (`tools :`, `"tools":`, indented), more than one tools
    key in any spelling (Sentinel W1 follow-up F5: a host may read either one), or a value that is not a
    one-line JSON array of strings. Each caller decides which way None fails closed."""
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        return None
    keys = [line for line in lines[1:lines.index('---', 1)] if TOOLS_KEY.match(line)]
    if not keys:
        return NO_TOOLS
    if len(keys) != 1 or not keys[0].startswith('tools:'):
        return None
    try:
        tools = json.loads(keys[0][len('tools:'):].strip())
    except ValueError:
        return None
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        return None
    return {t for t in tools if t in SPAWN_TOOLS or t.startswith(tuple(f'{s}(' for s in SPAWN_TOOLS))}


def main_session(path, text):
    """True when `path` (as of its base text) reaches the main session: a style, or an agent whose
    `tools:` holds Task/Agent. Read from the base version, so a deleted router agent still counts.
    An unreadable tools: (spawn_tools() None) is not main-session: its lines need subagent-visible credit."""
    if STYLE.fullmatch(path):
        return True
    if not path.startswith('agents/'):
        return False
    spawn = spawn_tools(text)
    return spawn not in (None, NO_TOOLS) and bool(spawn)


def subagent_visible(path, text):
    """True when the CURRENT text of a root-tier file reaches a subagent (Chris W1 r2 R2-1): not a style,
    and not an agent whose tools: hold Task/Agent. Fails closed on the credit side: an agent whose
    frontmatter or tools: cannot be read (spawn_tools() None) earns no subagent credit."""
    if STYLE.fullmatch(path):
        return False
    if not path.startswith('agents/'):
        return True
    spawn = spawn_tools(text)
    if spawn is None:
        return False
    return spawn == NO_TOOLS or not spawn  # no tools: line = a subagent with the default tool set


def v4_required(root):
    """Data switch for checks that are wired in 3.x and required from 4.0.0 (v4 ADR §7 W1/W10)."""
    if os.environ.get('SHODE_REQUIRE_V4') == '1':
        return True
    try:
        version = json.loads((root / '.claude-plugin/plugin.json').read_text())['version']
        return int(str(version).split('.')[0]) >= 4
    except (OSError, ValueError, KeyError, TypeError):
        return False


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
        for r in json.loads(path.read_text()).get('rules', []):
            if r.get('root_only') is not True:
                continue
            anchor = r.get('anchor')
            if not isinstance(anchor, str) or not norm(anchor):  # Chris W1 r2 L-4: rc 2, not a traceback
                raise ValueError(f"root_only rule {r.get('id')!r} has no anchor")
            anchors.append(norm(anchor))
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


def build_corpora(root, deleted=()):
    """-> (everything, root tier incl. styles, root tier a subagent sees = no style, no main-session agent)."""
    everything, root_tier, root_sub = Corpus(), Corpus(), Corpus()
    for p in sorted(root.rglob('*.md')):
        rel = p.relative_to(root).as_posix()
        if not rel.startswith(HOST) or SKIP_DIRS & set(p.parts) or rel in deleted:
            continue
        text = p.read_text(errors='ignore')
        everything.add(text)
        if ROOT_FILE.fullmatch(rel) and not is_lazy(text):
            root_tier.add(text)
            if subagent_visible(rel, text):
                root_sub.add(text)
    return everything, root_tier, root_sub


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--base', default='HEAD', help='git ref to compare the working tree against')
    ap.add_argument('--root-only', action='append', default=[], metavar='ANCHOR',
                    help='extra root-only anchor (in addition to .enforcement-map.json root_only rules)')
    ap.add_argument('--with-styles', action='store_true',
                    help='check output-styles/*.md too (automatic from 4.0.0 or SHODE_REQUIRE_V4=1)')
    ap.add_argument('--simulate-delete', action='append', default=[], metavar='PATH',
                    help='treat PATH as deleted in the working tree (planning aid; repeatable)')
    ap.add_argument('--dry-run', action='store_true', help='report lost fragments and their count; exit 0')
    args = ap.parse_args(argv)
    root = pathlib.Path.cwd()
    styles = args.with_styles or v4_required(root)
    deleted = {pathlib.PurePosixPath(p).as_posix() for p in args.simulate_delete}

    def in_scope(f):
        return (SCOPE.fullmatch(f) or (styles and STYLE.fullmatch(f))) and not SKIP_DIRS & set(f.split('/'))

    if git('rev-parse', '--verify', '--quiet', args.base + '^{commit}')[0] != 0:
        print(f"  X rule conservation: base ref '{args.base}' not found (shallow clone? fetch-depth: 0)")
        return 2
    for p in sorted(deleted):  # a typo or an absolute path must not print a reassuring "0 fragment(s)"
        if p.startswith('/') or '..' in p.split('/') or not in_scope(p) \
                or git('cat-file', '-e', f'{args.base}:{p}')[0] != 0:
            print(f"  X rule conservation: --simulate-delete {p}: not a checked skill/agent .md (a style needs "
                  f"--with-styles) that exists at {args.base}; give a repo-relative path")
            return 2
    rc, names = git('diff', '--no-renames', '--name-only', args.base, '--')
    if rc != 0:
        print("  X rule conservation: git diff failed"); return 2
    changed = [f for f in dict.fromkeys(names.splitlines() + sorted(deleted)) if in_scope(f)]
    if not changed:
        print(f"  ok no skill/agent file changed vs {args.base}"); return 0

    try:
        migrations = load_migrations(root)
    except (ValueError, KeyError, TypeError) as e:  # loader fails closed; say which entry, no traceback
        print(f"  X rule conservation: .rule-migrations.json invalid -- {e!r}{bad_migration(root)}")
        return 2
    try:
        anchors = root_only_anchors(root, args.root_only)
    except (ValueError, AttributeError, TypeError) as e:
        print(f"  X rule conservation: .enforcement-map.json invalid -- {e}")
        return 2
    everything, root_tier, root_sub = build_corpora(root, deleted)

    fail = checked = 0
    for f in changed:
        rc, old_text = git('show', f'{args.base}:{f}')
        if rc != 0:
            continue  # file is new since base: nothing to conserve
        path = root / f
        gone_now = f in deleted or not path.is_file()
        cur_text = '' if gone_now else path.read_text(errors='ignore')  # deleted/moved = empty
        cur_lines = {norm(l) for l in instruction_lines(cur_text)}
        was_root = ROOT_FILE.fullmatch(f) and not is_lazy(old_text)
        tier = root_tier if main_session(f, old_text) else root_sub  # style text reaches the main session only
        for line in rule_lines(old_text):
            if norm(line) in cur_lines:
                continue  # untouched line
            tier_anchor = next((a for a in anchors if a in norm(line)), None) if was_root else None
            corpus = tier if tier_anchor else everything
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
                    audience = ('SKILL.md/agent/style' if tier is root_tier
                                else 'subagent-visible SKILL.md/agent; styles and Task/Agent agents reach the '
                                     'main session only')
                    why = (f"root-only rule '{tier_anchor}' ไม่อยู่ใน root tier ({audience})" if tier_anchor
                           else "กฎหาย")
                    gone = ' [file deleted]' if gone_now else ''
                    print(f"  X {f}{gone}: {why} ({best:.0%} match) -- {mark}{frag[:72]}")
                    fail += 1
    if args.dry_run:
        print(f"  dry-run vs {args.base}: {fail} fragment(s) would need a new home or a .rule-migrations.json "
              f"entry ({len(changed)} file, {checked} removed fragment, styles {'in' if styles else 'out of'} scope, "
              f"simulated delete: {', '.join(sorted(deleted)) or 'none'})")
        return 0
    if not fail:
        print(f"  ok rule conservation vs {args.base} ({len(changed)} file, {checked} removed fragment, "
              f"{len(anchors)} root-only anchor)")
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
