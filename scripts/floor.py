#!/usr/bin/env python3
"""Safety floor: one canonical text, byte-identical copies (v4 ADR §5.5.2, slice W4).

Canonical texts (repo-only, never shipped):
  .safety-floor/body.md   -> every agents/*.md and every generated agent copy under plugins/*/
  .safety-floor/style.md  -> every output-styles/*.md and every generated style copy under plugins/*/
Each canonical file is exactly one marker-delimited block. A copy is the bytes from its begin-marker
line through its end-marker line, newline included, and must have the same sha256 as the canonical file.
.safety-floor/held/ holds lines kept OUT of the floor pending a decision; they are not part of any hash.

Usage (run from the repo root, or pass --root):
  floor.py --check   sha256 equality for every copy. Red: a byte difference, a missing or second marker
                     pair, an unpaired / reversed / indented marker, the other floor's markers in a file, CRLF or a
                     BOM in a file with markers, and a begin marker that is not the first non-blank line after
                     the frontmatter (R44: nothing -- fence, comment, framing text -- can sit before the block;
                     R3-2: every target starts with an exact '---' frontmatter line, so a block above it is red).
                     In both modes, "floor elsewhere": floor-marker text (any spelling: <!--floor:, <!-- FLOOR:)
                     in a shipped non-target file (agents/ skills/ commands/ references/ output-styles/ plugins/)
                     or outside the block of a target, and a line there with a normalised form (NFKC, invisible
                     characters dropped, HTML entities decoded and tags dropped (a quoted attribute may hold '>'),
                     casefolded, * _ ` ~ and backslashes removed, links read three ways -- the W10a fix-up 1
                     inline-link rule; an inline link [text](url) (one level of balanced parens in url) and a
                     reference link [text][ref] / [text][] reduced to their text; '[' as a space and ']' dropped --
                     leading # > - + * [ , task boxes and list numbers stripped; lines split at LF only) that
                     starts with "safety floor (" or "r0 (irreversible:". Any one form is enough (fail-closed
                     union: a decoding is added as a view, never replacing one; Sentinel W10a fix2 B2).
                     Invisible = Unicode Cf plus every Default_Ignorable_Code_Point (F3).
                     The style floor also targets the generated plugins/*/skills/ask/SKILL.md adapter.
                     Not yet required (plugin.json major < 4 and SHODE_REQUIRE_V4 != 1, no --require): a file
                     with no markers or an empty marker pair is reported as pending, not red.
                     Required: every copy must carry the floor, and every source and generated pattern must
                     match at least one file (a missing plugins/ tree or ask adapter is red).
  floor.py --write   writes the canonical block between EXISTING markers in source files only (agents/,
                     output-styles/). It never inserts markers and never touches plugins/ (the packer copies).
Exit: 0 ok, 1 check or write failed, 2 canonical file invalid or bad usage.
"""
import argparse, hashlib, html, json, os, pathlib, re, sys, unicodedata
from collections import namedtuple

Kind = namedtuple('Kind', 'name canonical begin end sources generated')
KINDS = (
    Kind('body', '.safety-floor/body.md', '<!-- floor:begin -->', '<!-- floor:end -->',
         ('agents/*.md',), ('plugins/*/agents/*.md', 'plugins/*/knowledge/agents/*.md')),
    # the generated tree's `ask` adapter carries the style floor for skills-only hosts (ADR erratum 1 §5.8.1);
    # the packer (W2) inserts it, so until then the adapter is pending like any copy without markers
    Kind('style', '.safety-floor/style.md', '<!-- floor:style:begin -->', '<!-- floor:style:end -->',
         ('output-styles/*.md',), ('plugins/*/output-styles/*.md', 'plugins/*/knowledge/output-styles/*.md',
                                   'plugins/*/skills/ask/SKILL.md')),
)
# "floor elsewhere": a floor marker in any other shipped file is red in both modes -- the floor never sits in a
# preloaded skill root (the discipline root reaches every spawn) or any other text it was not hashed for
SHIPPED = ('agents', 'skills', 'commands', 'references', 'output-styles', 'plugins')
# text sentinel (ADR erratum 1 r1, E1-3): floor lines pasted WITHOUT markers outside a floor block are red too.
# Matched on a normalised line (R2-2 / S4r2-6), so case, heading level, bold, list markers, '>' quoting, NBSP,
# zero-width characters and a BOM do not hide "## Safety floor (" or "- R0 (irreversible:".
FLOOR_TEXT = ('safety floor(', 'r0(irreversible:')
# invisible characters dropped before matching (Sentinel W1 follow-up F3): every Unicode format character
# (category Cf: zero-width, soft hyphen, BOM, bidi embeddings/isolates, invisible operators, tag characters) plus
# the Default_Ignorable_Code_Point ranges that are not Cf (combining grapheme joiner, variation selectors, Hangul
# fillers, Mongolian free variation selectors, unassigned ignorables). One rule, shared with the A16(b) lint.
DEFAULT_IGNORABLE = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                     (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                     (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                     (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF))
# leading markup a near-verbatim paste may carry (Sentinel W4 r3 R3-1): quote, heading, bullet, number, task box
# ([ ] / [x]) and a link's opening '['; backslash escapes, ~ strike-through and HTML tags are removed before this
LEAD = re.compile(r'^(?:\[[ x]?\]|[\s>#*+\[-]|\d+[.)])+')
# an HTML tag; a quoted attribute value may hold '<' or '>' (Sentinel W10a FU-3: <span title="a>b">)
TAG = re.compile(r'''<(?:[^<>"']|"[^"]*"|'[^']*')*>''')
# an inline Markdown link renders as its text only: [R](x)0 reads "R0" (FU-3); CommonMark allows balanced parens in the
# destination, one level folded here ([R](a(b)c)0, FU-9 / Chris W10a2-C5). Linear (Chris W10a2-C2): the text holds no
# '[' or ']' and every destination alternative starts with a different character, so no span is rescanned
LINK = re.compile(r'\[([^\[\]]*)\]\((?:[^()]|\([^()]*\))*\)')
# a full or collapsed reference link renders as its text too: [R][1]0 and [R][]0 read "R0" (FU-9 / C5); a shortcut
# reference [R]0 is not folded here (every bracketed word would fold) -- the space view of link_views() reads it
REF_LINK = re.compile(r'\[([^\[\]]*)\]\[[^\[\]]*\]')
# a link destination up to the next ')' that holds no ']' (Sentinel W10a fix2 B2): the space view's link rule
DEST = re.compile(r'\]\([^)\]]*\)')
MARK = '<!-- floor:'  # the one exact spelling a real marker uses (counted by locate)
MARK_ANY = re.compile(r'<!--\s*floor\s*:', re.I)  # every spelling, matched on normalised text
BOM = b'\xef\xbb\xbf'


class CanonicalError(Exception):
    pass


def v4_required(root):
    """Same data switch as rule-conservation.py / CI #27: plugin.json major >= 4 or SHODE_REQUIRE_V4=1."""
    if os.environ.get('SHODE_REQUIRE_V4') == '1':
        return True
    try:
        version = json.loads((root / '.claude-plugin/plugin.json').read_text())['version']
        return int(str(version).split('.')[0]) >= 4
    except (OSError, ValueError, KeyError, TypeError):
        return False


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(root, kind):
    """The canonical block, validated: one pair, nothing outside it, ASCII, LF, final newline."""
    path = root / kind.canonical
    try:
        data = path.read_bytes()
    except OSError as e:
        raise CanonicalError(f'{kind.canonical}: unreadable ({e.strerror})')
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError:
        raise CanonicalError(f'{kind.canonical}: non-ASCII byte (invisible or look-alike characters are not allowed)')
    lines = text.split('\n')
    if '\r' in text or not text.endswith('\n'):
        raise CanonicalError(f'{kind.canonical}: must use LF line ends and end with a newline')
    if lines[0] != kind.begin or lines[-2] != kind.end or text.count(MARK) != 2:
        raise CanonicalError(f'{kind.canonical}: must be exactly {kind.begin} ... {kind.end} with nothing outside')
    if len(lines) < 4:
        raise CanonicalError(f'{kind.canonical}: empty floor')
    return data


def locate(data, kind, other):
    """-> (start, stop, problem). start/stop = byte span of the block incl. the end line's newline.
    problem is None (well-formed pair), 'missing' (no markers) or a message (malformed)."""
    if data.count(other.begin.encode()) or data.count(other.end.encode()):
        return None, None, f'carries the {other.name} floor markers (wrong floor for this file)'
    b, e = kind.begin.encode(), kind.end.encode()
    nb, ne, nm = data.count(b), data.count(e), data.count(MARK.encode())
    if nb == ne == nm == 0:
        return None, None, 'missing'
    if b'\r' in data:
        return None, None, 'CRLF line ends (a file carrying the floor must use LF only)'
    if data.startswith(BOM):
        return None, None, 'starts with a UTF-8 BOM (remove it; the frontmatter and the floor must start at byte 0)'
    if nb != 1 or ne != 1 or nm != 2:
        return None, None, f'needs exactly one marker pair (found begin x{nb}, end x{ne}, floor markers x{nm})'
    start, end_at = data.index(b), data.index(e)
    if end_at < start:
        return None, None, 'end marker before begin marker'
    if (start and data[start - 1:start] != b'\n') or data[start + len(b):start + len(b) + 1] != b'\n':
        return None, None, 'begin marker must be a whole line'
    stop = end_at + len(e)
    if data[end_at - 1:end_at] != b'\n' or data[stop:stop + 1] != b'\n':
        return None, None, 'end marker must be a whole line ending in a newline'
    where = misplaced(data[:start])
    if where:
        return None, None, f'begin marker must be the first non-blank line after the frontmatter ({where})'
    return start, stop + 1, None


def misplaced(before):
    """Why the begin marker is not the first non-blank line after the frontmatter, or None (R44). The hash
    proves the bytes, not that they are read as binding text; with only frontmatter and empty lines before
    the block, no fence, comment, quote or framing text can wrap it (W4-5 / S4-1 / S4r2-2 / R2-3)."""
    lines = before.decode('utf-8', 'replace').split('\n')[:-1]  # complete lines before the begin marker
    if not lines or lines[0] != '---':  # R3-2 / S4r3-1: every target has frontmatter, opened by exactly '---'
        return ('the file must start with a --- frontmatter line; a block above it, or no frontmatter, '
                'strips the host metadata (tools:, name, force-for-plugin)')
    closer = next((n for n, line in enumerate(lines[1:], 1) if line == '---'), None)
    if closer is None:
        return 'it sits inside YAML frontmatter: no closing --- line before it'
    body = closer + 1
    extra = next((n for n in range(body, len(lines)) if lines[n] != ''), None)
    return None if extra is None else f'line {extra + 1} before it is not empty: {lines[extra][:50]!r}'


def invisible(char):
    """True for a character that renders as nothing: Unicode Cf or Default_Ignorable_Code_Point (F3)."""
    code = ord(char)
    return unicodedata.category(char) == 'Cf' or any(lo <= code <= hi for lo, hi in DEFAULT_IGNORABLE)


def visible(text):
    """`text` without invisible characters (ASCII has none, so it is returned as is)."""
    return text if text.isascii() else ''.join(c for c in text if not invisible(c))


def link_fu1(text):
    """The W10a fix-up 1 inline-link rule, re.sub(r'\\[([^\\]]*)\\]\\([^)]*\\)', r'\\1', text), computed in linear time
    (the regex rescans '[[[...' from every '['). A match from a '[' runs to the first ']' after it, needs '(' right
    after that ']' and ends at the first ')' after the '('; every '[' before that ']' shares the same ']', so a '['
    that fails lets the search jump past the ']'."""
    out, copied, at = [], 0, 0
    while True:
        start = text.find('[', at)
        close = text.find(']', start + 1) if start >= 0 else -1
        if close < 0:
            break                                   # no '[' or no ']' after it: no later '[' can match either
        if text.startswith('(', close + 1):
            end = text.find(')', close + 2)
            if end < 0:
                break                               # no ')' left: no later '[' can match either
            out += [text[copied:start], text[start + 1:close]]
            copied = at = end + 1
        else:
            at = close + 1
    return ''.join(out) + text[copied:]


def link_views(text):
    """The link readings of `text`, matched as a fail-closed union (Sentinel W10a fix2 B2: a decoding is ADDED as a
    view and never replaces one, so nothing an earlier rule found is lost): (1) the W10a fix-up 1 rule (link_fu1),
    (2) inline links with one level of balanced parens plus full / collapsed reference links (LINK, REF_LINK;
    FU-9 / C5), (3) a space view -- a destination up to the next ')' or ']' dropped, '[' read as a space and ']'
    dropped (`[ skip[R]()0` reads ` skip R0`). Each view is linear."""
    return (link_fu1(text), REF_LINK.sub(r'\1', LINK.sub(r'\1', text)),
            DEST.sub(']', text).replace(']', '').replace('[', ' '))


def norms(line):
    """Every form of one line the floor-text sentinel compares (R2-2 / S4r2-6 / R3-1), one per link view: HTML
    entities decoded before NFKC (&#82;0, &nbsp;), HTML tags dropped (<b>R0</b>), * _ ` ~ and backslash escapes
    removed, links read by each of link_views() ([R](x)0, [R](a(b)c)0, [R][1]0, [R][]0, [][R0 (...)] all read
    "R0"). A line is a floor line when ANY form starts with FLOOR_TEXT (fail-closed union, B2)."""
    text = visible(unicodedata.normalize('NFKC', visible(html.unescape(line)))).casefold()
    text = re.sub(r'[*_`~\\]', '', TAG.sub('', text))
    # ' ([(:])' is ' ?([(:])' without the no-op rewrites of every bare '(' (same result, fewer substitutions)
    return tuple(re.sub(r' ([(:])', r'\1', re.sub(r'\s+', ' ', LEAD.sub('', view))) for view in link_views(text))


def stray(text, first_line=1):
    """-> [why] for floor-marker text in any spelling and floor heading / R0 lines in `text` (which must not
    hold a floor block: a non-target file, or a target's bytes outside its block)."""
    found = []
    if MARK_ANY.search(visible(unicodedata.normalize('NFKC', visible(text)))):
        found.append('floor marker')
    # lines split at LF only (FU-2): CommonMark ends a line at LF/CR, not at U+2028/U+2029/U+0085/VT/FF/FS-RS,
    # so splitlines() would cut one rendered heading in two; norms() fold those characters as whitespace
    hits = [n for n, line in enumerate(text.split('\n'), first_line)
            if any(form.startswith(FLOOR_TEXT) for form in norms(line))]
    if hits:
        found.append(f'floor text line {hits[0]}')
    return found


def files(root, patterns):
    seen = []
    for pattern in patterns:
        seen += [p for p in sorted(root.glob(pattern)) if p.is_file() and p not in seen]
    return seen


def first_difference(block, want):
    got_lines, want_lines = block.decode('utf-8', 'replace').split('\n'), want.decode().split('\n')
    for n, (g, w) in enumerate(zip(got_lines, want_lines), 1):
        if g != w:
            return f'block line {n} differs: {g[:70]!r}'
    return f'block has {len(got_lines) - 1} lines, canonical {len(want_lines) - 1}'


def elsewhere(root):
    """-> [(path, why)] for shipped files that are not a floor target of any kind but carry floor-marker text
    or a floor heading / floor R0 line (with or without markers)."""
    targets = {p for k in KINDS for p in files(root, k.sources + k.generated)}
    found = []
    for top in SHIPPED:
        for path in sorted((root / top).rglob('*')):
            if not path.is_file() or path in targets:
                continue
            rel = path.relative_to(root).as_posix()
            found += [(rel, f'{why} outside a floor target')
                      for why in stray(path.read_bytes().decode('utf-8', 'replace'))]
    return found


def outside_block(data, start, stop):
    """-> [why] for floor text in a target outside its block (S4r2-5 / R2-4); the whole file if it has none."""
    if start is None:
        return stray(data.decode('utf-8', 'replace'))
    return (stray(data[:start].decode('utf-8', 'replace'))
            + stray(data[stop:].decode('utf-8', 'replace'), data[:stop].count(b'\n') + 1))


def check(root, required, verbose=False):
    fail = pending = ok = 0
    for rel, why in elsewhere(root):
        print(f'  X {rel}: {why} (floor elsewhere) -- the floor lives only in agent bodies, output styles and '
              f'the generated ask adapter')
        fail += 1
    for kind in KINDS:
        other = next(k for k in KINDS if k is not kind)
        want = canonical(root, kind)
        targets = files(root, kind.sources + kind.generated)
        for pattern in kind.sources + kind.generated if required else ():  # R2-5
            if not files(root, (pattern,)):
                print(f'  X {kind.name} floor: no file matches {pattern} -- required from 4.0.0')
                fail += 1
        for path in targets:
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            start, stop, problem = locate(data, kind, other)
            if problem is None or problem == 'missing':
                for why in outside_block(data, start, stop):
                    print(f'  X {rel}: {why} outside the {kind.name} floor block (floor elsewhere)')
                    fail += 1
            empty = problem is None and data[start:stop] == f'{kind.begin}\n{kind.end}\n'.encode()
            if problem == 'missing' or empty:
                why = 'markers present, text not written yet (floor.py --write)' if empty else 'no floor markers'
                if required:
                    print(f'  X {rel}: {why} -- required from 4.0.0')
                    fail += 1
                else:
                    pending += 1
                    if verbose:
                        print(f'  ~ pending {rel}: {why} (required from 4.0.0)')
                continue
            if problem:
                print(f'  X {rel}: {problem}')
                fail += 1
                continue
            block = data[start:stop]
            if sha(block) != sha(want):
                print(f'  X {rel}: {kind.name} floor sha256 {sha(block)[:12]} != canonical {sha(want)[:12]} -- '
                      f'{first_difference(block, want)}')
                fail += 1
                continue
            ok += 1
    mode = 'required' if required else 'not yet required'
    hashes = ', '.join(f'{k.name} {sha(canonical(root, k))[:12]} ({len(canonical(root, k))} B)' for k in KINDS)
    if fail:
        print(f'  X safety floor: {fail} file(s) red ({mode}; {hashes})')
        return 1
    listed = '' if verbose or not pending else ', --verbose lists them'
    print(f'  ok safety floor: {ok} copy(ies) match, {pending} pending{listed} ({mode}; {hashes})')
    return 0


def write(root):
    fail = written = 0
    for kind in KINDS:
        other = next(k for k in KINDS if k is not kind)
        want = canonical(root, kind)
        for path in files(root, kind.sources):  # sources only: the generated tree comes from the packer
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            start, stop, problem = locate(data, kind, other)
            if problem == 'missing':
                print(f'  ~ skipped {rel}: no floor markers (--write never inserts markers)')
                continue
            if problem:
                print(f'  X {rel}: {problem} -- not written')
                fail += 1
                continue
            new = data[:start] + want + data[stop:]
            if new != data:
                tmp = path.with_name(path.name + '.floor-tmp')
                tmp.write_bytes(new)
                os.replace(tmp, path)
                written += 1
                print(f'  wrote {rel}')
    print(f'  {"X" if fail else "ok"} floor write: {written} file(s) changed, {fail} refused')
    return 1 if fail else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='sha256 equality across every copy')
    mode.add_argument('--write', action='store_true', help='write the canonical block between existing markers')
    ap.add_argument('--require', action='store_true',
                    help='every copy must carry the floor (automatic from 4.0.0 or SHODE_REQUIRE_V4=1)')
    ap.add_argument('--root', default='.', help='repository root (default: current directory)')
    ap.add_argument('--verbose', action='store_true', help='list pending files too')
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    try:
        return write(root) if args.write else check(root, args.require or v4_required(root), args.verbose)
    except CanonicalError as e:
        print(f'  X canonical floor invalid: {e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
