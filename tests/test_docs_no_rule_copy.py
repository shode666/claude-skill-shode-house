#!/usr/bin/env python3
"""One source per rule: a rule of AGENTS.md must not be copied into docs/.

AGENTS.md § Repo Invariants (the heading that starts with `## Repo Invariants`, through end of file) is
the ONLY place a repo rule is stated. The detail files its index table links hold detail, rationale,
history and examples for those rules and point back with `AGENTS.md § <heading>`. This test stops rule
text from being copied back into docs. It deliberately does NOT compare two copies for equality: there
is no second copy to keep in sync.

Scanned files
  Every `docs/**/*.md`, plus every path named in the index table of AGENTS.md (each must exist), minus
  HISTORICAL (empty today: the whole of docs/ scans clean; an entry needs its reason beside it, and a
  file of the index table can never be listed there).

Normalisation
  Leading markdown markers (`#`, `>`, `-`, `*`, `1.`, table pipes) dropped, emphasis / backtick
  characters removed, lower-cased, runs of whitespace collapsed to one space. Each docs line is checked
  on its own AND each docs paragraph (consecutive non-blank lines) is checked with its lines joined by
  one space, so a rule pasted and hard-wrapped is still seen.

A docs line / paragraph is a copy when
  (a) it shares a run of WINDOW (= 60) consecutive normalised characters with a rule line -- a pasted
      rule whose bullet, bold markers, indentation, line breaks or one end were edited; or
  (b) it CONTAINS a whole clause of a rule line. Clauses = the non-heading rule line split at `. `,
      `; ` and ` — `, a leading marker emoji, closing punctuation and one trailing `(...)` (the CI
      reference) removed, kept when at least MIN_CLAUSE (= 20) characters long. A rule line shorter
      than WINDOW that yields no clause is matched as a whole from MIN_SHORT (= 12) characters; or
  (c) it EQUALS a heading of the invariant section, at any heading level or in any list/bold markup.

Allowance: a list of names is not a rule
  Shared text in which no two words stand next to each other -- every neighbour is a list separator
  (`·`, `+`, `/`, or a comma) -- is ignored: `.preload-budget · .agent-core-budget · ...`, the six
  root skill names, or one bare word such as `Skills`. Detail files have to be able to name the same
  files and sections as the rule. This cannot carry a rule: the allowance looks only at the text the
  docs line shares with AGENTS.md, and a rule clause ("never zip by hand") always has adjacent words.
  A names list followed by a copied clause on the same line is still a hit.

Why a back-reference is not a hit
  `AGENTS.md § Lazy ≠ Negligent` has to repeat the heading text, so headings are matched by equality
  only (c), never by containment: a line that also carries the file name, or any other word, is not
  equal. A docs heading that is exactly a multi-word AGENTS.md heading IS a hit -- name the docs section
  `Detail for AGENTS.md § <heading>`.

Caught: verbatim copies of a rule line, of a 60+ character part of one, or of one complete clause of
  20+ characters, whatever the markup, hard wrapping or surrounding sentence, in Thai or English.
NOT caught (review matter, Spec axis): a rule re-stated in different words; a translation (for example
  the Thai original of a rule that is English in AGENTS.md); a copy with a word changed inside every
  clause and every 60-character run; a clause shorter than 20 characters; a clause that AGENTS.md
  separates with a comma or colon only, copied alone and shorter than 60 characters; a copy wrapped
  under 60 columns with a BLANK line between the wrapped lines, or with `<br>` at the line ends
  (lines are joined into a paragraph only while they are consecutive and non-blank); a copy into a
  file under docs/ that is not `.md` (`.txt`, `.mdx`, ...) -- only `docs/**/*.md` is scanned.

Run: python3 tests/test_docs_no_rule_copy.py   (CI gate #24 runs it; also collected by pytest)
     python3 tests/test_docs_no_rule_copy.py --scan   prints the hits
"""
import pathlib, re, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = "AGENTS.md"
SECTION = "## Repo Invariants"
DOCS_DIR = "docs"
HISTORICAL = ()   # no docs file needs skipping today; add a path only with its reason beside it
WINDOW = 60
MIN_CLAUSE = 20
MIN_SHORT = 12
LIST_SEPS = {"·", "+", "/"}

_LEAD = re.compile(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+|\d+[.)]\s+|\|\s*)+")
_TABLE_RULE = re.compile(r"^[\s|:-]+$")
_CLAUSE_SPLIT = re.compile(r"(?<=[.;])\s+|\s+—\s+")
_INDEX_PATH = re.compile(r"^\|\s*`([^`|]+\.md)`\s*\|")


def norm(line):
    if _TABLE_RULE.match(line):
        return ""
    line = _LEAD.sub("", line)
    line = re.sub(r"[*_`]", "", line).replace("|", " ")
    return re.sub(r"\s+", " ", line).strip().lower()


def names_only(text, trim_ends=False):
    """True when no two words are adjacent: a separator-joined list of names, or a single word."""
    toks = text.split()
    if trim_ends:                       # a character window may cut its first and last token
        toks = toks[1:-1]
    return not any(a not in LIST_SEPS and b not in LIST_SEPS and not a.endswith(",") for a, b in zip(toks, toks[1:]))


def clauses(text):
    out = []
    parts = _CLAUSE_SPLIT.split(text)
    for part in parts:
        part = re.sub(r"^[^\w<(#.'\"/]+", "", part).strip(" .;:,")       # leading marker emoji (red dot, warning sign)
        bare = re.sub(r"\s*\([^()]*\)$", "", part).strip(" .;:,")
        part = bare if len(bare) >= MIN_CLAUSE else part
        if len(part) >= MIN_CLAUSE and not names_only(part):
            out.append(part)
    if not out and MIN_SHORT <= len(text) < WINDOW and not names_only(text):   # a short rule line, as a whole
        out.append(text)
    return out


def _section(root):
    lines = (root / RULES).read_text().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(SECTION)), None)
    if start is None:
        raise AssertionError(f"{RULES}: no '{SECTION}' heading -- the invariant section moved or was renamed")
    return [(i + 1, l) for i, l in enumerate(lines) if i >= start]


def rule_lines(root=ROOT):
    return [(no, norm(l), l.startswith("#")) for no, l in _section(root) if norm(l)]


def index_paths(root=ROOT):
    """Paths named in the first cell of the index table of the invariant section."""
    return [m.group(1) for _, l in _section(root) for m in [_INDEX_PATH.match(l)] if m]


def doc_files(root=ROOT):
    found = {p for p in (root / DOCS_DIR).rglob("*.md")} | {root / p for p in index_paths(root)}
    return sorted(p for p in found if p.is_file() and p.relative_to(root).as_posix() not in HISTORICAL)


def _index(root):
    windows, parts, heads = {}, [], {}
    for no, text, heading in rule_lines(root):
        if heading:
            if not names_only(text):
                heads[text] = no
            continue
        parts += [(no, c) for c in clauses(text)]
        for i in range(len(text) - WINDOW + 1):
            w = text[i:i + WINDOW]
            if not names_only(w, trim_ends=True):
                windows.setdefault(w, no)
    return windows, parts, heads


def _source(d, windows, parts):
    src = next((no for no, c in parts if c in d), None)
    if src is None:
        src = next((windows[d[i:i + WINDOW]] for i in range(len(d) - WINDOW + 1) if d[i:i + WINDOW] in windows), None)
    return src


def scan(root=ROOT):
    windows, parts, heads = _index(root)
    hits = []
    for f in doc_files(root):
        rel = f.relative_to(root).as_posix()
        para, para_hit = [], False

        def flush():
            if len(para) > 1 and not para_hit:
                src = _source(" ".join(d for _, d, _ in para), windows, parts)
                if src is not None:
                    hits.append(f"{rel}:{para[0][0]}: copies {RULES}:{src} (wrapped over {len(para)} lines): {para[0][2].strip()[:80]}")

        for dno, raw in enumerate(f.read_text().splitlines() + [""], 1):
            d = norm(raw)
            if not d:
                flush()
                para, para_hit = [], False
                continue
            para.append((dno, d, raw))
            src = heads.get(d)
            if src is None:
                src = _source(d, windows, parts)
            if src is not None:
                para_hit = True
                hits.append(f"{rel}:{dno}: copies {RULES}:{src}: {raw.strip()[:100]}")
    return hits


def _wrap(text, width):
    out, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur); cur = word
        else:
            cur = (cur + " " + word).strip()
    return out + [cur]


class DocsNoRuleCopyTest(unittest.TestCase):
    def test_scan_set_covers_index_table_and_all_docs(self):
        self.assertGreaterEqual(len(rule_lines()), 40, "invariant section of AGENTS.md is unexpectedly short")
        indexed = index_paths()
        self.assertGreaterEqual(len(indexed), 4, "index table of AGENTS.md not found -- scan set is stale")
        scanned = {p.relative_to(ROOT).as_posix() for p in doc_files()}
        for p in indexed:
            self.assertTrue((ROOT / p).is_file(), f"{RULES} index table names a missing file: {p}")
            self.assertIn(p, scanned, f"indexed detail file is not scanned: {p}")
        every = {p.relative_to(ROOT).as_posix() for p in (ROOT / DOCS_DIR).rglob("*.md")}
        self.assertEqual(set(HISTORICAL), every - scanned, "a docs file is skipped without a HISTORICAL entry")
        self.assertFalse(set(HISTORICAL) & set(indexed), "an indexed detail file must never be excluded")

    def test_no_rule_line_copied_into_docs(self):
        self.assertEqual([], scan())

    def _tree(self, d, doc_lines, name="docs/repo-invariants/x.md", extra_rules=()):
        root = pathlib.Path(d)
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / RULES).write_text((ROOT / RULES).read_text() + "".join(r + "\n" for r in extra_rules))
        (root / name).write_text("\n\n".join(doc_lines) + "\n")   # blank line between items: one paragraph each
        return root

    def _raw(self):
        return [l for l in (ROOT / RULES).read_text().split(SECTION, 1)[1].splitlines() if l.strip()]

    def test_negative_a_copied_rule_line_is_caught(self):
        raw = self._raw()
        long_rule = next(l for l in raw if l.startswith("- ") and len(norm(l)) > 2 * WINDOW)
        head = next(l for l in raw if l.startswith("## ") and not names_only(norm(l)))
        short_rule = "- Xq never ships"                                   # MIN_SHORT..MIN_CLAUSE: matched as a whole line
        clause_rule = "- Alpha beta stays put; never frobnicate the quux by hand. Gamma delta too (CI #99)."
        planted = [
            long_rule,                                                    # verbatim
            "  * " + long_rule[2:].replace("**", "").replace("`", ""),    # other bullet, emphasis stripped
            "Note: " + long_rule[2:len(long_rule) // 2 + 40],             # a pasted fragment inside a sentence
            head,                                                         # a section heading
            "### " + head[3:],                                            # same heading at another level
            "- Never frobnicate the quux by hand.",                       # M-3a: one clause of a multi-clause rule
            "As said before, never frobnicate the quux by hand, ok?",     # M-3a: the clause inside another sentence
            "\n".join(_wrap(long_rule, 50)),                              # M-3b: pasted and hard-wrapped
            "\n".join("> " + l for l in _wrap(long_rule[2:], 40)),        # M-3b: wrapped inside a quote block
            "`a.md` · `b.md` · never frobnicate the quux by hand",        # L-5: a names list cannot carry a clause
            "Remember: xq never ships.",                                  # a short rule line inside a sentence
            "| Open | Before touching |",                                 # the short table-header line of the index
            "Skill in tools: of every agent, in addition to skills.",     # clause whose rule line starts with an emoji
        ]
        with tempfile.TemporaryDirectory() as d:
            hits = scan(self._tree(d, planted, extra_rules=[short_rule, clause_rule]))
            self.assertEqual(len(planted), len(hits), "\n".join(hits))
            self.assertEqual(2, sum("wrapped over" in h for h in hits), "\n".join(hits))

    def test_negative_copy_into_any_docs_file_is_caught(self):
        long_rule = next(l for l in self._raw() if l.startswith("- ") and len(norm(l)) > 2 * WINDOW)
        for name in ("docs/new-detail.md", "docs/deep/er/new.md", "docs/repo-invariants/x.md"):
            with tempfile.TemporaryDirectory() as d:
                self.assertEqual(1, len(scan(self._tree(d, [long_rule], name=name))), name)

    def test_negative_back_references_names_and_detail_pass(self):
        raw = self._raw()
        heads = [l[3:] for l in raw if l.startswith("## ")]
        allowed = [f"## Detail for `AGENTS.md` § {h}" for h in heads]
        allowed += [f"See `AGENTS.md` § {h}, which is the rule; this adds an example." for h in heads]
        allowed += ["The cap of 3 keeps instruction density down.", "Skills the orchestrator has loaded do not travel."]
        # L-5: the same names as a rule line, and a bare section word, are detail -- not a copy
        files = re.search(r"\(([^()]*·[^()]*·[^()]*·[^()]*budget`)\)", "\n".join(raw)).group(1)
        self.assertGreater(len(norm(files)), WINDOW)
        allowed += ["The files are " + files + ".", "- " + files, "Roots today: dev-gate · decompose · drain · secure · review-checklist · diagnose"]
        allowed += [w for h in heads if names_only(norm(h)) for w in (f"- {h}", f"**{h}**", f"| {h} |", f"#### {h}")]
        allowed += ["never frobnicate the quux"]                          # not the whole clause
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(d, allowed, extra_rules=["- Alpha beta stays put; never frobnicate the quux by hand."])
            self.assertEqual([], scan(root))

    def test_names_only_criterion(self):
        for text in ("skills", ".a-budget · .b-budget · .c-budget", "ask, dev-gate, diagnose", "handoff + language"):
            self.assertTrue(names_only(text), text)
        for text in ("never zip", "output styles", "x = generated", ".a-budget · .b-budget only go down", "lazy ≠ negligent"):
            self.assertFalse(names_only(text), text)
        self.assertEqual(["never zip by hand outside the makefile"],
                         [c for c in clauses(norm("- Use `make`; never zip by hand outside the Makefile (CI #1)."))])


if __name__ == "__main__":
    if sys.argv[1:] == ["--scan"]:
        found = scan()
        print("\n".join(found)); sys.exit(1 if found else 0)
    unittest.main()
