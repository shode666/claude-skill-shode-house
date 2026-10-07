"""U23 item 5: a shipped reference over 100 lines opens with a table of contents that matches its headings.

Scope = every .md under a `.pack-allowlist` entry below `skills/` or `references`, except SKILL.md. Those are the
lazy-loaded references an agent opens part-way through a task. Not in scope: SKILL.md (300-line cap, CI #1),
agents/, commands/ and output-styles/ (entry prompts loaded whole and budgeted as a whole, not navigated), and the
generated copies under plugins/ (`pack-team.py --check`, CI #25, holds them to the source).

The TOC is the line `**Contents**`, a blank line, then one list item per entry, `- [Heading text](#anchor)`
(an indented `  - [...](#...)` for a `###`). It sits before the first `##`/`###` heading, after the frontmatter,
the title and the lazy-load-contract block. Strictness:
  - a file over 100 lines without a TOC is red;
  - every TOC entry must be the anchor of a heading of that file (GitHub slug, duplicates -1, -2 ...) and the
    entries must follow document order;
  - every `##` heading must be listed; a `###` entry is optional (listed for a file with few `##` sections);
  - headings inside fenced code blocks are not headings (templates such as `## Implementation: [feature]`);
  - a file of 100 lines or fewer needs no TOC, but if it has one the same checks apply (no stale TOC).
Run: python3 tests/test_reference_toc.py   (also collected by pytest)
     python3 tests/test_reference_toc.py --scan   (findings, with the TOC to paste for a missing one)
"""
import pathlib, re, sys, unicodedata, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIMIT = 100
MARKER = "**Contents**"
ENTRY = re.compile(r"^(  )?- \[(.+)\]\(#([^)\s]+)\)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def shipped_refs(root=ROOT):
    """Reference .md files shipped by .pack-allowlist (dirs under skills/ or references), SKILL.md excluded."""
    out = set()
    for line in (root / ".pack-allowlist").read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if not (entry.startswith("skills/") or entry == "references" or entry.startswith("references/")):
            continue
        base = root / entry
        files = [base] if base.is_file() else sorted(base.rglob("*.md"))
        out.update(p for p in files if p.suffix == ".md" and p.name != "SKILL.md")
    return sorted(out)


def slug(text):
    """GitHub heading anchor (github-slugger): lower case, keep letters, marks, digits, '_', '-' and space,
    then each space -> '-'. Inline code / emphasis markers are punctuation and drop out the same way."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).lower()
    kept = "".join(c for c in text if c in "- " or unicodedata.category(c)[0] in "LMN" or unicodedata.category(c) == "Pc")
    return kept.replace(" ", "-")


def headings(lines):
    """(line index, level, text, anchor) of every heading outside fenced code; duplicate anchors get -1, -2 ..."""
    out, seen, fence = [], {}, None
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip(" `~"):
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        h = HEADING.match(line)
        if h and h.group(2):
            base = slug(h.group(2))
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.append((i, len(h.group(1)), h.group(2), base if n == 0 else f"{base}-{n}"))
    return out


def toc(lines):
    """(marker line index or None, [(line index, depth, text, anchor)])."""
    marks = [i for i, l in enumerate(lines) if l == MARKER]
    if not marks:
        return None, []
    i, entries = marks[0] + 1, []
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and ENTRY.match(lines[i]):
        m = ENTRY.match(lines[i])
        entries.append((i, 3 if m.group(1) else 2, m.group(2), m.group(3)))
        i += 1
    return marks[0], entries


def check(text, name="<text>"):
    """Findings for one file (empty = ok)."""
    lines = text.splitlines()
    hs = headings(lines)
    mark, entries = toc(lines)
    if mark is None:
        return [f"{name}: {len(lines)} lines > {LIMIT} and no table of contents ({MARKER!r} + list)"] \
            if len(lines) > LIMIT else []
    bad = []
    if [i for i, l in enumerate(lines) if l == MARKER][1:]:
        bad.append(f"{name}: more than one {MARKER!r} line")
    if not entries:
        bad.append(f"{name}:{mark + 1}: {MARKER!r} without a list of '- [Heading](#anchor)' entries")
    first = next((i for i, lvl, _, _ in hs if lvl >= 2), None)
    if first is not None and mark > first:
        bad.append(f"{name}:{mark + 1}: table of contents after the first section heading (line {first + 1})")
    anchors = {a: (i, lvl) for i, lvl, _, a in hs}
    order = []
    for i, depth, label, anchor in entries:
        if anchor not in anchors:
            bad.append(f"{name}:{i + 1}: TOC entry '{label}' -> #{anchor} matches no heading anchor")
        elif anchors[anchor][1] != depth:
            bad.append(f"{name}:{i + 1}: TOC entry '{label}' is nested as level {depth}, the heading is level "
                       f"{anchors[anchor][1]}")
        else:
            order.append(anchors[anchor][0])
    if order != sorted(order) or len(set(order)) != len(order):
        bad.append(f"{name}: TOC entries are not in document order (or repeat an entry)")
    listed = {a for _, _, _, a in entries}
    for i, lvl, text_, anchor in hs:
        if lvl == 2 and anchor not in listed:
            bad.append(f"{name}:{i + 1}: '## {text_}' is missing from the table of contents (#{anchor})")
    return bad


def suggest(text):
    """The TOC block to paste for one file: every ##, plus ### when the file has fewer than 3 ## headings."""
    hs = [h for h in headings(text.splitlines()) if h[1] in (2, 3)]
    deep = sum(1 for h in hs if h[1] == 2) < 3
    rows = [("  " if lvl == 3 else "") + f"- [{t}](#{a})" for _, lvl, t, a in hs if lvl == 2 or deep]
    return "\n".join([MARKER, ""] + rows)


def scan(root=ROOT):
    out = []
    for p in shipped_refs(root):
        out += check(p.read_text(encoding="utf-8"), str(p.relative_to(root)))
    return out


class ReferenceTocTreeTest(unittest.TestCase):
    def test_scope_is_the_shipped_reference_set(self):
        refs = [str(p.relative_to(ROOT)) for p in shipped_refs()]
        self.assertGreater(len(refs), 50, refs)
        self.assertIn("references/scope-lock.md", refs)
        self.assertIn("skills/discipline/shode-house-workflow/harness.md", refs)
        self.assertFalse([r for r in refs if r.endswith("/SKILL.md")])
        self.assertFalse([r for r in refs if r.startswith(("skills/in-progress/", "skills/deprecated/", "plugins/"))])

    def test_every_long_shipped_reference_has_a_matching_toc(self):
        self.assertEqual([], scan())


GOOD = "\n".join(["---", "name: x", "---", "", "# Title", "", MARKER, "", "- [Alpha one](#alpha-one)",
                  "  - [Sub `code`](#sub-code)", "- [🔴 Beta](#-beta)", "- [Alpha one](#alpha-one-1)", "",
                  "## Alpha one", "### Sub `code`", "```markdown", "## Inside fence", "```", "## 🔴 Beta",
                  "## Alpha one", ""] + ["filler"] * LIMIT)


class ReferenceTocNegativeControlTest(unittest.TestCase):
    def test_good_toc_passes(self):
        self.assertEqual([], check(GOOD))

    def test_missing_toc_over_limit_is_red_and_short_file_is_not(self):
        body = "\n".join(l for l in GOOD.splitlines() if l != MARKER and not ENTRY.match(l))
        self.assertTrue(any("no table of contents" in f for f in check(body)))
        self.assertEqual([], check("# t\n\n## a\n"))

    def test_stale_anchor_is_red(self):
        self.assertTrue(any("matches no heading" in f for f in check(GOOD.replace("(#-beta)", "(#beta)"))))

    def test_heading_missing_from_toc_is_red(self):
        bad = GOOD.replace("- [🔴 Beta](#-beta)\n", "")
        self.assertTrue(any("'## 🔴 Beta' is missing" in f for f in check(bad)))

    def test_fenced_heading_is_not_required(self):
        self.assertFalse(any("Inside fence" in f for f in check(GOOD)))

    def test_out_of_order_toc_is_red(self):
        bad = GOOD.replace("- [Alpha one](#alpha-one)\n  - [Sub `code`](#sub-code)\n- [🔴 Beta](#-beta)",
                           "- [🔴 Beta](#-beta)\n- [Alpha one](#alpha-one)\n  - [Sub `code`](#sub-code)")
        self.assertTrue(any("document order" in f for f in check(bad)))

    def test_toc_after_first_section_is_red(self):
        lines = GOOD.splitlines()
        start, end = lines.index(MARKER), lines.index("## Alpha one")
        block = lines[start:end]
        moved = lines[:start] + lines[end:end + 1] + block + lines[end + 1:]
        self.assertTrue(any("after the first section heading" in f for f in check("\n".join(moved))))

    def test_wrong_nesting_is_red(self):
        self.assertTrue(any("nested as level" in f for f in check(GOOD.replace("  - [Sub", "- [Sub"))))

    def test_a_second_contents_line_is_red(self):
        """Chris final Info 3: only the first **Contents** line is read as the TOC; a second one (a stale copy left
        further down) is red, in a long file and in a short one."""
        lines = GOOD.splitlines()
        at = lines.index("## Alpha one")
        twice = "\n".join(lines[:at] + [MARKER, "", "- [Alpha one](#alpha-one)", ""] + lines[at:])
        self.assertTrue(any("more than one" in f for f in check(twice)), check(twice))
        self.assertFalse(any("more than one" in f for f in check(GOOD)), "control: one Contents line is fine")
        short = f"# t\n\n{MARKER}\n\n- [a](#a)\n\n## a\n\n{MARKER}\n"
        self.assertEqual([f"<text>: more than one {MARKER!r} line"], check(short))

    def test_short_file_with_stale_toc_is_red(self):
        self.assertTrue(check(f"# t\n\n{MARKER}\n\n- [Gone](#gone)\n\n## a\n"))

    def test_slug_matches_github(self):
        self.assertEqual("-risk-template", slug("⚠ Risk Template"))
        self.assertEqual("phase-1c-process", slug("Phase 1c process"))
        self.assertEqual("phase-3b--parallel-with-code-reviewer-cr--qa-engineer-test",
                         slug("Phase 3b — parallel with code-reviewer (CR) ∥ qa-engineer (test)"))
        self.assertEqual("ห้าม-method", slug("ห้าม (method)"))

    def test_suggest_round_trips(self):
        body = "\n".join(l for l in GOOD.splitlines() if l != MARKER and not ENTRY.match(l))
        lines = body.splitlines()
        at = lines.index("# Title") + 1
        fixed = "\n".join(lines[:at] + ["", suggest(body)] + lines[at:])
        self.assertEqual([], check(fixed))


if __name__ == "__main__":
    if "--scan" in sys.argv:
        found = scan()
        for f in found:
            print(f)
            if "no table of contents" in f:
                print(suggest((ROOT / f.split(":", 1)[0]).read_text(encoding="utf-8")))
        sys.exit(1 if found else 0)
    unittest.main()
