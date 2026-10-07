#!/usr/bin/env python3
r"""The .plugin archive ships an explicit allowlist, and nothing in it points outside it.

What ships
  `.pack-allowlist` is the only list of paths `make pack` zips (a directory ships recursively,
  minus JUNK). docs/, AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md and every other maintainer
  file are simply not on it. This test fails when the Makefile `pack` recipe names a path of its own
  on ANY of its command lines (a second zip call, a prefixed list), expands a make variable other
  than $(PLUGIN), runs a word that is not in RECIPE_WORDS (an interpreter one-liner, a copy), reads
  the allowlist with another awk program, when `pack` / `build` has a second rule line or the
  Makefile includes another file, when an entry is missing, or when a maintainer root is listed.

Shipped executables parse
  Every shipped `*.sh` goes through `bash -n`, every shipped `*.py` through `py_compile`, every
  shipped `*.js` through `node --check` as a script, a module or a workflow-script body (skipped,
  visibly, when node is not on PATH; see _js_error for why the bare command is not trusted). `--archive`
  runs the same check on the files unpacked from the built archive. A syntax check only: behaviour
  is covered by the maintainer shell suites.

No dangling reference
  Every shipped text file (UTF-8, no NUL) is scanned line by line. A REFERENCE is one of:
    link     a markdown link target `[text](target)`, resolved against the file's directory;
    import   an `@path.md` import, resolved against the file's directory, then the plugin root;
    section  a `README §` / `AGENTS §` / `CLAUDE §` / `CHANGELOG §` section pointer;
    path     a path token whose first segment is a top-level name of THIS repository
             (ROOT NAMES = the allowlist's first segments + MAINTAINER_ROOTS + HOMONYM_DIRS +
             GENERIC_FILES), wherever it stands: in backticks, in prose, in a script string,
             a script comment or after `$VAR/` / `${VAR}/`. `../` is resolved against the file.
    loose    a MAINTAINER_ROOTS name in any letter case, after URLs are removed and `\` / `%2F`
             are read as `/`, standing at a token start or right after `)/`, `}/`, `./`, `../`,
             or a `"/` / `'/` whose quote closes a word or a substitution (`"$dir"/`, `")"/`) --
             `"$dir"/AGENTS.md`, `$(git rev-parse --show-toplevel)/AGENTS.md`,
             `"$(dirname "$0")/../docs/x.json"`, `${CLAUDE_PLUGIN_ROOT}/../AGENTS.md`, a
             wrong-depth `../docs/x.md`, `docs\x.md`, `docs%2Fx.md`, `agents.md`, `Docs/x.md`.
             A directory root written in ANOTHER letter case counts only with a file extension
             or a second path segment (`Docs/x.md`, `Eval/fixtures/a`): `Release/Rollback plan`
             and `the Eval/Test split` are two words. No `..` arithmetic here: under those names
             nothing ships, at any depth.
    outputs  an `outputs/...` path that belongs to THIS repository: its second segment starts with
             one of MAINTAINER_OUTPUT_PREFIXES (this repository's tracker ids), with the same
             URL / `\` / `%2F` reading as `loose`. Text only: the git-ignored outputs/ directory
             is never looked at, so the result is the same in CI and in a maintainer checkout.
  A reference is satisfied when its target is in the archive, resolved from the plugin root or
  from any directory above the referencing file (a self-contained package such as
  references/design-intel addresses its own files from its own root).

  A path reference that is not satisfied is a HIT when
    - its root is in MAINTAINER_ROOTS (docs/, AGENTS.md, CLAUDE.md, eval/, ...): always, whether
      or not the file exists -- nothing under those names can ever be in the archive; or
    - its root ships (scripts/, skills/, references/, ...) and the path exists in this repository
      but is not on the allowlist (`scripts/eval-scorer.py`, `skills/in-progress/`); or
    - its root is in HOMONYM_DIRS (tests/, .github/) and the path is an existing FILE of this
      repository (`tests/test-lock.sh`).
  Links, imports and section pointers that are not satisfied are always hits.

Not a reference (each exemption is declared below with its reason)
  - URLs and anchors: a link target with a scheme, `mailto:` or a bare `#anchor`; a path token
    preceded by `/` -- the path part of a URL, an absolute path, a quoted route or link such as
    `app.get("/docs/openapi.json")` or `href="/docs/guide"` -- unless that `/` follows one of
    the shell prefixes listed under `loose`.
  - Paths inside the TARGET project: `.shode-house/...` and every `outputs/...` path that is not
    this repository's own (see `outputs` above) -- `outputs/<bd-id>/01-dave.md`,
    `outputs/SPEC-<bd-id>.md`, `outputs/42/03-developer-phase-2.md`, `outputs/adr/INDEX.md`.
    Neither is a top-level name of this repository (TARGET_PROJECT_ROOTS, asserted).
  - HOMONYM_DIRS paths that do not exist here (`tests/visual/checkout.png`): the reader's project.
  - GENERIC_FILES written bare (`Makefile`, `.gitignore`, `README.md`): the reader's project.
    As a link / import / section pointer they are still checked.
  - Globs and placeholders (`<...>`, `*`, `?`, `{...}`, `$VAR`, `…`): only the literal directory
    before the first placeholder is checked -- `references/languages/<lang>.md` needs
    `references/languages/` shipped, `docs/<x>.md` is still a hit, and so is a pattern over a
    maintainer root (`^docs/.*$`, `^docs\/.*$`).
  - A bare directory word without a slash (`docs`, `tests`, `hooks`) is an English word.
  - SKIP_FILES and EXEMPT: named files / lines, one reason each. Every EXEMPT entry must name a
    token whose first segment is a root name, give a non-blank reason, and pin exactly one line
    of its file with a text fragment that says more than the token itself (a fragment equal to,
    inside, or only punctuation around the token is rejected); every entry must still match
    something (no stale exemption).
    references/scope/example.manifest.json is skipped as a WHOLE file and its sample strings do
    name maintainer paths of this repository: `outputs/shode-roadmap/C/review-**` (the very form
    the `outputs` rule hits), `eval/baseline/e2e-golden/GS1-BASELINE.md`, `tests/...`,
    `scripts/eval-scorer.py`, `.preload-budget`. Sample data; nobody is told to open them.

Allowed on purpose (a DEFAULT pending the user's confirmation, Spec S-15 / N-1 -- not yet a user
decision)
  A maintainer document named WITHOUT a path inside a script comment or a JSON note string
  (`_comment`, `_boundary_note`, ...) may stay. They record where a design came from, nobody is
  told to open them, and they carry no path. Cited that way today:
    - `ROADMAP-runtime-10.md` (scripts/*.sh, references/**/*.json);
    - "the maintainer suite test-lock.sh" and the other `test-*.sh` suites (scripts/, hooks/scripts/,
      references/state-machine/transitions.json);
    - `02-sara-adr-1a.md`, `08-sentinel-threat-model-hooks.md` (hooks/scripts/session-start.sh,
      guard-state-write.sh, stop-integrity.sh);
    - `14-oliver-L1-iter1-verified.md`, `18-dave-L1-implement-iter2.md`,
      `21-quinn-L1-review-iter2.md`, `23-dave-L1-implement-iter3.md`,
      `28-chris-L1-review-iter3b.md`, `29-quinn-L1-review-iter3b.md` (scripts/route.sh);
    - `15-sentinel-runtime-security.md`, "threat model 08-sentinel", "15-sentinel artifact"
      (references/security/tool-profiles.json, trust-levels.json).
  Not all of these lines carry the word "maintainer". Prose that an agent reads (agents/, skills/,
  commands/, references/*.md) must not cite an unshipped document even by bare name -- that half
  is a review matter, this test cannot tell a bare name from a word.

NOT caught (review matter)
  - a file named without its directory (`test-lock.sh`, `ROADMAP-runtime-10.md`), a pointer in
    words ("the repo invariants"), a sibling-relative path in a script (`"$dir/lib/x.sh"`);
  - a bare GENERIC_FILES name used for THIS repository's file: `Strategy + fallback: see README.md`
    passes, as does `./README.md` (only `README §`, a link, an import or `../README.md` is seen);
  - a name assembled at run time (`f=AGENTS; cat "$root/$f.md"`), split across two lines, or held
    in a variable; a root name after a prefix other than the ones listed under `loose`
    (`$dir//AGENTS.md`, `${root}docs/x.md` without a slash, `path.join(root, "docs", "x.md")`);
  - other encodings (`docs%252Fx.md`, `docs&#47;x.md`, `docs%5Cx.md`);
  - a case variant of a SHIPPED root or of a tests/ / .github/ path (`Scripts/eval-scorer.py`);
  - a maintainer DIRECTORY root in another letter case followed by one segment without a file
    extension (`Docs/guide`, `Eval/fixtures`);
  - an `outputs/` path of this repository whose second segment has no MAINTAINER_OUTPUT_PREFIXES
    prefix (`outputs/run-3/x.md`, `outputs/SESSION-STATE.md`): the text cannot tell it from the
    target project's evidence home, and the checkout is deliberately not consulted;
  - a pinned EXEMPT line that is later EXTENDED with a pointer to this repository: the whole
    line stays exempt for that token (`... project's `CLAUDE.md` ..., see also CLAUDE.md SS Agents`);
  - a script that parses but fails when run, or that sources a file which is not shipped;
  - a `pack` recipe that misbehaves using only RECIPE_WORDS and no root name (the CI build step
    checks the built archive and that `make pack` leaves nothing else in the working tree).

Run: python3 tests/test_pack_allowlist.py                       (CI gate #26; also collected by pytest)
     python3 tests/test_pack_allowlist.py --scan                prints the hits and the parse failures
                                                                of the working tree
     python3 tests/test_pack_allowlist.py --archive X.plugin    checks a built archive: same file set
                                                                as the allowlist + no hit + every
                                                                unpacked executable parses
                                                                (CI runs it in "Build .plugin artifact")
"""
import fnmatch, importlib.util, os, pathlib, posixpath, py_compile, re, shutil, subprocess, sys, tempfile, unittest, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWLIST = ".pack-allowlist"
# Same four patterns as the `-x` arguments of the Makefile recipe (asserted below).
JUNK = ("*.DS_Store", "*__pycache__*", "*/.git/*", "*.fuse_hidden*")

# Top-level names of this repository that never ship. A path under one of them is a hit even when
# the file does not exist. A new tracked top-level name must be classified here or allowlisted.
MAINTAINER_ROOTS = frozenset({
    "AGENTS.md", "CLAUDE.md", "SHODE-HOUSE-MASTER.md", "docs", "eval", "plugins", "release",
    ".pack-allowlist", ".agent-core-budget", ".preload-budget", ".skill-metadata-budget",
    ".workflow-scenario-budget", ".rule-baseline", ".safety-floor", ".rule-migrations.json",
    ".baseline-3.12.1.json", ".baseline-3.16.3.json",
    ".agents", ".beads", ".claude", ".codex", ".cursor-plugin", ".mcp.json",
    "ai-agent-software-house-series", "ai-engineering-standards-script.md", "wcpred-prompt.md",
})
# The MAINTAINER_ROOTS that are directories: bare (no slash) they are words, not paths
# (`docs`, `eval`, jq's `.agents[]`). The rest of MAINTAINER_ROOTS are files and count bare.
DIRECTORY_ROOTS = frozenset({"docs", "eval", "plugins", "release", ".agents", ".beads", ".claude", ".codex",
                             ".cursor-plugin", "ai-agent-software-house-series"})
# Directory names every project has. Shipped text uses them for the READER's project
# (`tests/visual/<feature>.png`), so only a path that is an existing file of this repository counts.
HOMONYM_DIRS = frozenset({"tests", ".github"})
# File names every project has. Bare, they denote the reader's project and are not references.
GENERIC_FILES = frozenset({"Makefile", ".gitignore", "README.md", "CHANGELOG.md", ".pre-commit-config.yaml"})
# Evidence / runtime homes in the TARGET project. Never a top-level name of this repository.
TARGET_PROJECT_ROOTS = ("outputs", ".shode-house")
# ...except that this repository keeps its OWN evidence under outputs/ too (git-ignored, never
# packed). A second segment with one of these prefixes is this repository's tracker id, so the path
# names a maintainer document: `outputs/shode-roadmap/C/05-oliver-decisions.md`.
MAINTAINER_OUTPUT_PREFIXES = ("shode-house-", "shode-roadmap")
# Section pointers `<name> §` to a root file, with or without `.md`.
SECTION_FILES = {"README": "README.md", "AGENTS": "AGENTS.md", "CLAUDE": "CLAUDE.md", "CHANGELOG": "CHANGELOG.md"}

# (file glob, reason) -- the whole file is data, not prose that points at files.
SKIP_FILES = (
    ("references/design-intel/data/*",
     "third-party design catalogue rows (CSV files + their two JSON summaries): advice about paths in the reader's stack"),
    ("references/scope/example.manifest.json",
     "sample scope manifest: its strings are example glob patterns of a project tree, read as data"),
)
# (file, token prefix, line fragment, reason). The fragment must say more than the token and pin
# exactly one line that carries the token (exemption_problems, asserted). Every entry must match
# at least one line (asserted).
EXEMPT = (
    (".claude-plugin/marketplace.json", "plugins/shode-house", '"source"',
     "marketplace catalogue field, resolved against the marketplace repository, not the archive. The file "
     "itself is not a runtime file (Spec S-16): it ships until the user has tested a Cowork drag-drop of an "
     "archive without it; then drop its .pack-allowlist line and this entry"),
    # ADR erratum 1 rev 1 (F-1, W1): the router style's fast-path exclusion list names the TARGET project's files
    ("output-styles/shode-house.md", "CLAUDE.md", "no agent instruction or skill file", "fast-path exclusion: the TARGET project's agent-instruction files"),
    ("output-styles/shode-house.md", "AGENTS.md", "no agent instruction or skill file", "fast-path exclusion: the TARGET project's agent-instruction files"),
    ("output-styles/shode-house.md", ".mcp.json", "no agent instruction or skill file", "fast-path exclusion: the TARGET project's MCP server config"),
    # v4 S3 (ledger W3 tests "EXEMPT (S3)"): the router-fast-path-excludes anchor quotes the style's fast-path line
    (".enforcement-map.json", "CLAUDE.md", "no agent instruction or skill file", "anchor of router-fast-path-excludes quotes the style's fast-path line: the TARGET project's files"),
    (".enforcement-map.json", "AGENTS.md", "no agent instruction or skill file", "anchor of router-fast-path-excludes quotes the style's fast-path line: the TARGET project's files"),
    (".enforcement-map.json", ".mcp.json", "no agent instruction or skill file", "anchor of router-fast-path-excludes quotes the style's fast-path line: the TARGET project's files"),
    ("commands/init.md", "CLAUDE.md", "`CLAUDE.md`/`AGENTS.md`", "checks whether the TARGET project has these files"),
    ("commands/init.md", "AGENTS.md", "`CLAUDE.md`/`AGENTS.md`", "checks whether the TARGET project has these files"),
    ("commands/init.md", "CLAUDE.md", "project's `CLAUDE.md`", "the TARGET project's guidance file /init appends to"),
    ("commands/init.md", "AGENTS.md", "project's `CLAUDE.md`", "the TARGET project's guidance file /init appends to"),
    ("commands/init.md", "CLAUDE.md", "CONTRIBUTING + CLAUDE.md", "file Aaron scaffolds in the TARGET project"),
    ("commands/init.md", "CLAUDE.md", "quickstart + `CLAUDE.md`", "file Aaron scaffolds in the TARGET project"),
    ("commands/init.md", "docs/DEPLOY.md", "runbook + rollback", "file Aaron scaffolds in the TARGET project"),
    ("references/runbooks/devops-engineer-method.md", "CLAUDE.md", "CONTRIBUTING + CLAUDE.md",
     "file devops-engineer scaffolds in the TARGET project (v4 W5b: moved from agents/devops-engineer.md)"),
    ("skills/discipline/shode-house-discipline/SKILL.md", "CLAUDE.md", "existing similar file",
     "evidence source: the TARGET project's CLAUDE.md"),
    ("skills/discipline/shode-house-discipline/handoff.md", "CLAUDE.md", "target `CLAUDE.md`",
     "what a sub-agent sees: the TARGET project's CLAUDE.md"),
    ("skills/discipline/shode-house-routing/SKILL.md", "CLAUDE.md", "official ADR", "trust table: the TARGET project's CLAUDE.md"),
    ("skills/discipline/shode-house-routing/SKILL.md", "CLAUDE.md", "Read CLAUDE.md:12", "citation example from the TARGET project"),
    ("skills/discipline/shode-house-workflow/smart-coop.md", "CLAUDE.md", "CLAUDE.md loaded",
     "phase entry condition: the TARGET project's CLAUDE.md is loaded"),
    ("skills/style/caveman/SKILL.md", "CLAUDE.md", "input token", "memory file of the reader's project being compressed"),
    ("skills/style/caveman/SKILL.md", ".github/workflows/ci.yml", "CI gate", "CI workflow of the reader's project"),
    ("commands/init.md", "CLAUDE.md", "document ใน CLAUDE.md", "brownfield adopt documents in the TARGET project's CLAUDE.md"),
    ("references/state-machine/transitions.json", "CLAUDE.md", "bd issue context + CLAUDE.md loaded",
     "quotes the phase pre-hook: the TARGET project's CLAUDE.md is loaded"),
    (".enforcement-map.json", ".preload-budget", '"source_of_truth"',
     "data: a maintainer-owned rule row names its gate file; policy-check.sh reads only id + verification"),
    ("references/security/trust-levels.json", "CLAUDE.md", '"pattern": "CLAUDE.md"',
     "data: file-name pattern matched against TARGET project paths"),
)

_TEXT_PH = re.compile(r"[<>*?{}$…]")
_LINK = re.compile(r"\]\(([^)\s]+)\)")
_IMPORT = re.compile(r"(?:^|\s)@([A-Za-z0-9_./\-]+\.md)\b")
_SECTION = re.compile(r"(?<![\w./\-])(README|AGENTS|CLAUDE|CHANGELOG)(?:\.md)?`?\s*§")
_TAIL = r"(?:/[A-Za-z0-9_.\-/<>*?{}$…@+%~]*)?"
_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://\S+")
_OUTPUTS = re.compile(r"(?<![A-Za-z0-9_\-])outputs/[A-Za-z0-9_.\-/<>*?{}$…@+%~]*")
# `"/` and `'/` count only when the quote closes a word or a substitution (`"$dir"/`, `")"/`):
# `("/docs/openapi.json")` and `href="/docs/guide"` are routes of the reader's project.
_LOOSE = re.compile(
    r"(?i)(?:(?<=[)}]/)|(?<=[A-Za-z0-9_)}][\"']/)|(?<=\./)|(?<![A-Za-z0-9_./\-$}~]))"
    r"(?P<root>" + "|".join(re.escape(n) for n in sorted(MAINTAINER_ROOTS, key=len, reverse=True)) + r")"
    r"(?![A-Za-z0-9_\-])(?P<tail>" + _TAIL + r")")
_CANON = {n.lower(): n for n in MAINTAINER_ROOTS}
_FILE_EXT = re.compile(r"\.[A-Za-z][A-Za-z0-9]*$")
# Every word the `pack` recipe may contain once single-quoted text, `$$name` shell variables,
# `$(PLUGIN)` and option flags are removed. A command that is not here (python3, perl, cp, tar,
# sh -c, eval ...) fails the recipe check: extend this set only together with a reviewed recipe.
RECIPE_WORDS = frozenset(
    "rm d mktemp shode pack XXXXXX list awk allowlist test miss for p in do echo make allowlisted "
    "path missing done zip mv rc exit built du cut K unzip tail files".split())
_PACK_LIST = "list=$$(awk '!/^[[:space:]]*(#|$$)/{print $$1}' .pack-allowlist)"


def allowlist(root=ROOT):
    lines = (root / ALLOWLIST).read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]


def _junk(path):
    return any(fnmatch.fnmatch(path, pat) for pat in JUNK)


def shipped_files(root=ROOT):
    """Repo-relative files the allowlist puts in the archive, exactly as `zip -r` walks them."""
    out = set()
    for entry in allowlist(root):
        item = root / entry
        if item.is_dir():
            out |= {p.relative_to(root).as_posix() for p in item.rglob("*") if p.is_file()}
        elif item.is_file():
            out.add(entry)
    return {p for p in out if not _junk(p)}


def root_names(root=ROOT):
    return {e.split("/")[0] for e in allowlist(root)} | MAINTAINER_ROOTS | HOMONYM_DIRS | GENERIC_FILES


def _path_re(names):
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(
        r"(?:(?P<var>\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/)|(?<![A-Za-z0-9_./\-$}~]))"
        r"(?P<up>(?:\.\./)+|\./)?(?P<root>" + alt + r")(?![A-Za-z0-9_\-])"
        r"(?P<tail>" + _TAIL + r")")


def _trim(token):
    """Drop sentence punctuation and an unbalanced closing bracket from the end of a path token."""
    token = token.rstrip(".,;:")
    for close, open_ in ("}{", "><"):
        while token.endswith(close) and token.count(close) > token.count(open_):
            token = token[:-1].rstrip(".,;:")
    return token


def _literal(token):
    """(the part of the token before its first placeholder, cut back to a directory; has placeholder)."""
    cut = _TEXT_PH.search(token)
    if not cut:
        return token, False
    head = token[:cut.start()]
    return head[:head.rfind("/") + 1], True


def _texts(files, read):
    for path in sorted(files):
        if any(fnmatch.fnmatch(path, glob) for glob, _ in SKIP_FILES):
            continue
        try:
            text = read(path).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "\0" not in text:
            yield path, text


def _exempt(path, token, line):
    for i, (glob, prefix, fragment, _) in enumerate(EXEMPT):
        if fnmatch.fnmatch(path, glob) and token.startswith(prefix) and fragment in line:
            return i
    return None


def scan(files, read, repo=ROOT, names=None, used=None, only=None):
    """[(file, line no, kind, reference, reason)] for every dangling reference in `files`.

    files = the shipped paths; read(path) -> bytes; repo = the checkout used for the
    "exists in this repository" test of shipped-root and homonym paths (tracked directories only:
    never outputs/); only = scan just these files (the others still count as shipped targets).
    """
    files = set(files)
    names = names or root_names(repo)
    path_re = _path_re(names)
    ship_dirs = {f.split("/")[0] for f in files if "/" in f}

    def shipped(p):
        p = p.rstrip("/")
        return p in files or any(f.startswith(p + "/") for f in files)

    def reachable(p, base):
        """Shipped from the plugin root or from any directory above the referencing file."""
        parts = base.split("/") if base else []
        return any(shipped(posixpath.join(*parts[:n], p)) for n in range(len(parts), -1, -1))

    hits = []
    for path, text in _texts(files if only is None else only, read):
        base = posixpath.dirname(path)
        for no, line in enumerate(text.split("\n"), 1):
            found = {}

            def hit(kind, ref, reason):
                i = _exempt(path, ref, line)
                if i is None:
                    found.setdefault(ref, (kind, reason))
                elif used is not None:
                    used.add(i)

            for m in _LINK.finditer(line):
                target = m.group(1)
                if "://" in target or target.startswith(("#", "mailto:")) or _TEXT_PH.search(target):
                    continue
                resolved = posixpath.normpath(posixpath.join(base, target.split("#")[0]))
                if resolved.startswith("..") or not shipped(resolved):
                    hit("link", target, f"link target {resolved} is not in the archive")
            for m in _IMPORT.finditer(line):
                target = m.group(1)
                if not (shipped(posixpath.normpath(posixpath.join(base, target))) or shipped(target)):
                    hit("import", target, "imported file is not in the archive")
            for m in _SECTION.finditer(line):
                if not shipped(SECTION_FILES[m.group(1)]):
                    hit("section", SECTION_FILES[m.group(1)], f"`{m.group(1)} §` points at a file that is not in the archive")
            for m in path_re.finditer(line):
                token = _trim(m.group("root") + m.group("tail"))
                literal, pattern = _literal(token)
                if not literal:
                    continue
                up = m.group("up") or ""
                if up.startswith(".."):
                    literal = posixpath.normpath(posixpath.join(base, up + literal))
                    if literal.startswith(".."):
                        hit("path", token, "resolves outside the archive")
                        continue
                    if reachable(literal, ""):
                        continue
                elif reachable(literal, base):
                    continue
                first = literal.split("/")[0]
                if first not in names:
                    continue
                bare = "/" not in literal.rstrip("/") and not literal.endswith("/")
                if first in GENERIC_FILES and bare and not up.startswith(".."):
                    continue  # `../../Makefile` climbs to this repository's own file: checked below
                if bare and first in DIRECTORY_ROOTS | HOMONYM_DIRS | ship_dirs:
                    continue  # a directory name without a slash: the word `docs`, jq's `.agents`
                if first in MAINTAINER_ROOTS:
                    hit("path", token, "maintainer path, never in the archive")
                elif first in HOMONYM_DIRS:
                    if not pattern and (repo / literal).is_file():
                        hit("path", token, "a file of this repository that is not in the archive")
                elif (repo / literal).exists():
                    hit("path", token, "exists in this repository but is not on the allowlist")
            # loose: a maintainer name in any case / separator / encoding, behind a shell prefix
            loose = _URL.sub(" ", line).replace("%2F", "/").replace("%2f", "/").replace("\\", "/")
            for m in _LOOSE.finditer(loose):
                token = _trim(m.group("root") + m.group("tail"))
                first = _CANON[m.group("root").lower()]
                if first in DIRECTORY_ROOTS:
                    if "/" not in token:
                        continue  # the word `docs`, `Eval`
                    rest = token.split("/", 1)[1].strip("/")
                    if m.group("root") != first and "/" not in rest and not _FILE_EXT.search(rest):
                        continue  # two words joined by a slash: `Release/Rollback`, `Docs/Design`
                hit("path", token, "maintainer path, never in the archive")
            # outputs: this repository's own evidence home, not the target project's. Decided from
            # the text alone -- outputs/ is git-ignored, so the checkout must not change the verdict.
            for m in _OUTPUTS.finditer(loose):
                token = _trim(m.group(0))
                literal, _ = _literal(token)
                parts = [s for s in literal.split("/") if s]
                if len(parts) >= 2 and parts[1].startswith(MAINTAINER_OUTPUT_PREFIXES):
                    hit("path", token, "maintainer evidence path of this repository, never in the archive")
            hits += [(path, no, kind, ref, reason) for ref, (kind, reason) in sorted(found.items())]
    return hits


def scan_tree(root=ROOT, used=None):
    files = shipped_files(root)
    return scan(files, lambda p: (root / p).read_bytes(), repo=root, used=used)


_JS_EXPORT = re.compile(r"^export\s+(?=const|let|var|function|async|class)", re.M)


def _node_check(node, tmp, name, text):
    """"" when node parses `text` under the file name `name`, else the first error line."""
    f = pathlib.Path(tmp) / name
    f.write_text(text, encoding="utf-8")
    run = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
    if run.returncode == 0:
        return ""
    return next((l.strip() for l in run.stderr.splitlines() if "Error" in l), run.stderr.strip()[:200]) or "node --check failed"


def _workflow_body(node, source, tmp):
    """`source` as an async function body, with the `export` keyword of each TOP-LEVEL export removed.

    An export is top-level exactly when the text before it is a run of complete statements, i.e.
    parses as a function body on its own. `function f(){\nexport const a=1\n}` keeps its `export`
    (the text before it is an open function) and so still fails to parse.
    """
    wrap = lambda body: "async function __workflow__() {\n" + body + "\n}\n"
    done, pos = "", 0
    for m in _JS_EXPORT.finditer(source):
        done += source[pos:m.start()]
        if _node_check(node, tmp, "smoke-prefix.cjs", wrap(done)):
            done += m.group(0)
        pos = m.end()
    return wrap(done + source[pos:])


def _js_error(node, source, tmp):
    """None when `source` parses as a CommonJS script, an ES module or a workflow script body.

    `node --check x.js` is NOT used on the file as it stands: for a `.js` file that contains `export`
    and has no package.json beside it, node (v24) exits 0 without reporting a syntax error. Each
    form below is a real parse, selected by the file suffix. The third form is the shape of
    skills/ops/drain/workflow-template.js: `export const meta` + top-level `await` and `return`,
    i.e. the body of an async function.
    """
    error = ""
    for name, text in (("smoke.cjs", lambda: source), ("smoke.mjs", lambda: source),
                       ("smoke-body.cjs", lambda: _workflow_body(node, source, tmp))):
        error = _node_check(node, tmp, name, text())
        if not error:
            return None
    return f"parses neither as a script, a module nor a workflow body ({error})"


def smoke(root, files, node="auto"):
    """Parse every shipped executable under `root`. -> (problems, {suffix: files checked}, notes).

    A file that fails is counted as checked and listed in problems.

    .sh -> `bash -n`; .py -> py_compile; .js -> `node --check` (see _js_error), or a note when node
    is not on PATH.
    """
    node = shutil.which("node") if node == "auto" else node
    problems, parsed, notes = [], {".sh": 0, ".py": 0, ".js": 0}, []
    with tempfile.TemporaryDirectory() as tmp:
        for p in sorted(files):
            f, suffix = str(pathlib.Path(root) / p), pathlib.PurePosixPath(p).suffix
            if suffix == ".sh":
                run = subprocess.run(["bash", "-n", f], capture_output=True, text=True)
                if run.returncode:
                    problems.append(f"{p}: bash -n: {run.stderr.strip()}")
            elif suffix == ".py":
                try:
                    py_compile.compile(f, cfile=str(pathlib.Path(tmp) / "smoke.pyc"), dfile=p, doraise=True)
                except py_compile.PyCompileError as e:
                    problems.append(f"{p}: py_compile: {' '.join(e.msg.split())}")
            elif suffix == ".js":
                if not node:
                    continue
                error = _js_error(node, pathlib.Path(f).read_text(encoding="utf-8"), tmp)
                if error:
                    problems.append(f"{p}: node --check: {error}")
            else:
                continue
            parsed[suffix] += 1
    unparsed = sorted(p for p in files if p.endswith(".js")) if not node else []
    if unparsed:
        notes.append(f"SKIP node --check: node is not on PATH; {len(unparsed)} shipped .js file(s) NOT parsed: {', '.join(unparsed)}")
    return problems, parsed, notes


def unchecked_fails(notes, env=None):
    """A check that could not run (smoke's notes) is a failure where CI is set, a printed note elsewhere."""
    return bool(notes) and bool((os.environ if env is None else env).get("CI"))


def scan_archive(archive, root=ROOT):
    with zipfile.ZipFile(archive) as z:
        members = {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp)
            problems, parsed, notes = smoke(tmp, members)
    expected = shipped_files(root)
    drift = [f"not on the allowlist but in the archive: {p}" for p in sorted(set(members) - expected)]
    drift += [f"on the allowlist but not in the archive: {p}" for p in sorted(expected - set(members))]
    return drift, scan(members, members.__getitem__, repo=root), len(members), (problems, parsed, notes)


def fmt(hits):
    return [f"{f}:{no}: [{kind}] {ref} -- {why}" for f, no, kind, ref, why in hits]


def _recipe_of(makefile):
    m = re.search(r"^pack build:\n((?:\t.*\n|\n)+)", makefile, re.M)
    return m.group(1) if m else ""


def _pack_recipe(root=ROOT):
    return _recipe_of((root / "Makefile").read_text(encoding="utf-8"))


def makefile_problems(makefile, names):
    """Why the Makefile as a WHOLE does not pack "exactly the allowlist": the rule lines, then the recipe."""
    out = []
    for line in makefile.split("\n"):
        if re.match(r"-?s?include\b", line):
            out.append(f"the Makefile includes another file, which could carry a `pack` rule: {line!r}")
        rule = re.match(r"([^\t#:=\n][^#:=\n]*):(?!=)", line)
        if not rule:
            continue
        targets = rule.group(1)
        if re.search(r"[$%]", targets):
            out.append(f"a rule target that cannot be read as a name: {line!r}")
        elif {"pack", "build"} & set(targets.split()) and line != "pack build:":
            out.append(f"`pack` / `build` must have exactly one rule line, `pack build:` with no prerequisite: {line!r}")
    return out + recipe_problems(_recipe_of(makefile), names)


def recipe_problems(recipe, names):
    """Why the WHOLE `pack` recipe is not "zip exactly the allowlist": every command line counts."""
    out = []
    body = re.sub(r"-x '[^']+'", "", recipe).replace("\\\n", " ")
    if ALLOWLIST not in recipe:
        out.append(f"the pack recipe does not read {ALLOWLIST}")
    reads = re.findall(r"list=[^\n]*", body)
    if len(reads) != 1 or not (reads[0] + " ").startswith(_PACK_LIST + " "):
        out.append(f"`list` must be assigned once, as `{_PACK_LIST}` and nothing else: {reads}")
    expansions = re.findall(r"\$(?!\(PLUGIN\))\S{0,16}", recipe.replace("$$", ""))
    if expansions:
        out.append(f"the pack recipe expands a make variable other than $(PLUGIN): {expansions}")
    plain = re.sub(r"\$\$[A-Za-z_?]\w*|\$\(PLUGIN\)|(?<=\s)-[A-Za-z0-9]+", " ", re.sub(r"'[^'\n]*'", " ", recipe))
    unknown = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", plain)) - RECIPE_WORDS)
    if unknown:
        out.append(f"the pack recipe runs or names words outside RECIPE_WORDS (an interpreter, a copy, another archiver?): {unknown}")
    zips = re.findall(r"(?<![A-Za-z0-9_\-])zip\b[^&;|\n]*", body)
    if [" ".join(z.split()) for z in zips] != ['zip -rq "$$d/$(PLUGIN)" $$list']:
        out.append(f"the recipe must run exactly one zip command, over $$list alone: {zips}")
    for token in re.findall(r"[A-Za-z0-9_.\-/]+", body):
        first = next((s for s in token.split("/") if s not in ("", ".", "..")), "")
        if first in names - {ALLOWLIST}:
            out.append(f"the pack recipe names {token!r} itself -- list it in {ALLOWLIST} instead")
    return out


def exemption_problems(entries=EXEMPT, root=ROOT):
    """Why an EXEMPT entry exempts more than the one line it was written for."""
    out = []
    for glob, prefix, fragment, reason in entries:
        where = f"EXEMPT {glob} / {prefix}"
        if not (reason or "").strip():
            out.append(f"{where}: no reason")
        if prefix.split("/")[0] not in root_names(root):
            out.append(f"{where}: the token's first segment must be a root name -- an empty or partial prefix exempts every token on the line")
        if _TEXT_PH.search(glob) or not (root / glob).is_file():
            out.append(f"{where}: an exemption names one existing file")
            continue
        if not fragment:
            out.append(f"{where}: must pin its line with a text fragment")
        elif fragment in prefix or len(re.sub(r"[\W_]+", "", fragment.replace(prefix, ""))) < 3:
            out.append(f"{where}: fragment {fragment!r} is no more specific than the token -- it would exempt every mention in the file")
        else:
            lines = [l for l in (root / glob).read_text(encoding="utf-8").split("\n") if fragment in l and prefix in l]
            if len(lines) != 1:
                out.append(f"{where}: fragment {fragment!r} pins {len(lines)} lines carrying the token, must be exactly 1")
    return out


class PackAllowlistTest(unittest.TestCase):
    def test_entries_exist_and_are_plain_repo_paths(self):
        entries = allowlist()
        self.assertEqual(len(entries), len(set(entries)), "duplicate allowlist entry")
        for e in entries:
            self.assertRegex(e, r"^[A-Za-z0-9_.\-]+(/[A-Za-z0-9_.\-]+)*$", f"not a plain relative path: {e!r}")
            self.assertNotIn("..", e.split("/"))
            self.assertTrue((ROOT / e).exists(), f"allowlisted path does not exist: {e}")
            self.assertFalse(any(o != e and e.startswith(o + "/") for o in entries), f"{e} is already inside another entry")

    def test_no_maintainer_path_is_allowlisted(self):
        for e in allowlist():
            first = e.split("/")[0]
            self.assertNotIn(first, MAINTAINER_ROOTS, e)
            self.assertNotIn(first, HOMONYM_DIRS, e)
            self.assertNotIn(first, GENERIC_FILES, e)
        files = shipped_files()
        for banned in ("AGENTS.md", "CLAUDE.md", "README.md", "CHANGELOG.md"):
            self.assertNotIn(banned, files)
        self.assertFalse([p for p in files if p.startswith(("docs/", "tests/", "eval/", "plugins/"))])
        self.assertFalse([p for p in files if _junk(p)])

    def test_plugin_format_and_licence_files_ship(self):
        files = shipped_files()
        for needed in (".claude-plugin/plugin.json", "LICENSE", "hooks/hooks.json", "output-styles/shode-house.md"):  # v4 S3: router style replaces oliver.md
            self.assertIn(needed, files)

    def test_makefile_packs_the_allowlist_and_nothing_else(self):
        recipe = _pack_recipe()
        self.assertEqual(sorted(re.findall(r"-x '([^']+)'", recipe)), sorted(JUNK), "JUNK differs from the recipe's -x patterns")
        self.assertEqual([], makefile_problems((ROOT / "Makefile").read_text(encoding="utf-8"), root_names()))
        self.assertEqual([], recipe_problems(recipe, root_names()))

    def test_recipe_guard_reads_every_command_line(self):
        # Standards M-5: the two mutants that passed while only the first zip line was inspected, and three more.
        recipe, names = _pack_recipe(), root_names()
        zip_cmd, read = 'zip -rq "$$d/$(PLUGIN)" $$list', "list=$$(awk "
        self.assertIn(zip_cmd, recipe); self.assertIn(read, recipe)
        mutants = {
            "second zip call": recipe.replace(" mv ", ' zip -gqr "$$d/$(PLUGIN)" docs AGENTS.md && \\\n\t mv ', 1),
            "prefixed list": recipe.replace(read, 'list="README.md $$(awk ', 1).replace(".pack-allowlist) &&", '.pack-allowlist)" &&', 1),
            "path on the zip line": recipe.replace(zip_cmd, zip_cmd + " docs", 1),
            "dot-slash path on the zip line": recipe.replace(zip_cmd, zip_cmd + " ./CLAUDE.md", 1),
            "list extended afterwards": recipe.replace(" miss= &&", ' list="$$list plugins" && miss= &&', 1),
            "second zip call, unknown name": recipe.replace(" mv ", ' zip -gq "$$d/$(PLUGIN)" notes.txt && mv ', 1),
        }
        for name, mutant in mutants.items():
            self.assertNotEqual(recipe, mutant, name)
            self.assertTrue(recipe_problems(mutant, names), f"mutant not caught: {name}")

    def test_makefile_guard_sees_indirect_changes(self):
        # Standards L-15: the six mutants that survived while only the lines under `pack build:` were
        # read literally -- a make variable defined above the rule, a prerequisite on its own line,
        # a writer that is not `zip`, an awk program that prints a name which is not a root name.
        makefile, names = (ROOT / "Makefile").read_text(encoding="utf-8"), root_names()
        zip_cmd, rule, mv = 'zip -rq "$$d/$(PLUGIN)" $$list', "\npack build:\n", ' mv "$$d/$(PLUGIN)" ./ ;'
        for anchor in (zip_cmd, rule, mv, _PACK_LIST):
            self.assertEqual(1, makefile.count(anchor), anchor)
        mutants = {
            "D zip through a make variable": makefile.replace(rule, "\nZIPX := zip" + rule, 1).replace(
                mv, ' $(ZIPX) -gqr "$$d/$(PLUGIN)" outputs && mv "$$d/$(PLUGIN)" ./ ;', 1),
            "D3 operands through a make variable": makefile.replace(rule, "\nZIPX := zip\nEXTRA := docs AGENTS.md" + rule, 1).replace(
                mv, ' $(ZIPX) -gqr "$$d/$(PLUGIN)" $(EXTRA) && mv "$$d/$(PLUGIN)" ./ ;', 1),
            "E2 copy through make variables": makefile.replace(rule, "\nSRC := AGENTS.md\nDST := skills/workflow/ask/" + rule, 1).replace(
                "\t@rm -f $(PLUGIN)\n", "\t@rm -f $(PLUGIN)\n\t@cp $(SRC) $(DST)\n", 1),
            "G prerequisite on a separate line": makefile.replace(
                rule, "\npack: prepack\nprepack:\n\t@cp CHANGELOG.md skills/workflow/ask/history.txt\n" + rule, 1),
            "G double-colon rule": makefile.replace(rule, "\npack::\n\t@cp x y\n" + rule, 1),
            "G rule for build only": makefile.replace(rule, "\nbuild: prepack\n" + rule, 1),
            "G target through a variable": makefile.replace(rule, "\nT := pack\n$(T): prepack\n" + rule, 1),
            "G included rule file": makefile.replace(rule, "\n-include local.mk" + rule, 1),
            "F prerequisite on the rule line": makefile.replace(rule, "\npack build: prepack\n", 1),
            "H interpreter one-liner writes the archive": makefile.replace(
                mv, " python3 -c \"import zipfile,sys; zipfile.ZipFile(sys.argv[1],'a').write('outputs/x.md')\" \"$$d/$(PLUGIN)\" && mv \"$$d/$(PLUGIN)\" ./ ;", 1),
            "H shell one-liner": makefile.replace(mv, ' sh -c "$$HOOK" && mv "$$d/$(PLUGIN)" ./ ;', 1),
            "H copy with no root name": makefile.replace(mv, ' cp -R "$$HOME/x" "$$d" && mv "$$d/$(PLUGIN)" ./ ;', 1),
            "J2 awk program prints another name": makefile.replace(
                "{print $$1}' .pack-allowlist", "{print $$1} END{print \"outputs\"}' .pack-allowlist", 1),
            "make variable, brace form": makefile.replace(zip_cmd, zip_cmd + " ${EXTRA}", 1),
            "make variable, one letter": makefile.replace(zip_cmd, zip_cmd + " $E", 1),
        }
        for name, mutant in mutants.items():
            self.assertNotEqual(makefile, mutant, name)
            self.assertTrue(makefile_problems(mutant, names), f"mutant not caught: {name}")
        # RECIPE_WORDS is exactly the recipe's vocabulary: no spare word a mutant could use
        plain = re.sub(r"\$\$[A-Za-z_?]\w*|\$\(PLUGIN\)|(?<=\s)-[A-Za-z0-9]+", " ", re.sub(r"'[^'\n]*'", " ", _pack_recipe()))
        self.assertEqual(RECIPE_WORDS, set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", plain)))

    def test_every_tracked_top_level_name_is_classified(self):
        try:
            out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, text=True, capture_output=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git not available")
        known = root_names() | {"LICENSE"}
        self.assertFalse(sorted({l.split("/")[0] for l in out.splitlines()} - known),
                         "new top-level name: allowlist it or add it to MAINTAINER_ROOTS")
        for name in TARGET_PROJECT_ROOTS:
            self.assertNotIn(name, known, f"{name} is a TARGET project path and must not be a root name")

    def test_generated_tree_sources_are_a_subset_of_the_allowlist(self):
        # scripts/pack-team.py walks its own roots. It may ship LESS than the zip (no hooks, no
        # runner scripts, its own manifests), never a source file the zip does not ship.
        spec = importlib.util.spec_from_file_location("pack_team", ROOT / "scripts/pack-team.py")
        pack = importlib.util.module_from_spec(spec); spec.loader.exec_module(pack)
        _, entries = pack.payload()
        sources = {p[len("knowledge/"):] for p in entries if p.startswith("knowledge/")}
        files = shipped_files()
        self.assertFalse(sorted(sources - files), "generated tree copies a source the archive does not ship")
        only_zip = files - sources
        allowed_only_zip = ("hooks/", "scripts/", ".claude-plugin/", ".enforcement-map.json")
        self.assertFalse(sorted(p for p in only_zip if not p.startswith(allowed_only_zip)),
                         "archive ships a knowledge file the generated tree drops")

    def test_shipped_text_has_no_dangling_reference(self):
        used = set()
        hits = scan_tree(used=used)
        self.assertFalse(hits, "\n" + "\n".join(fmt(hits)))
        stale = [EXEMPT[i][:3] for i in range(len(EXEMPT)) if i not in used]
        self.assertFalse(stale, f"exemption matches nothing any more -- delete it: {stale}")

    def test_exemptions_pin_exactly_one_line(self):
        self.assertEqual([], exemption_problems())

    def test_exemption_guard_rejects_a_fragment_that_pins_nothing(self):
        # Standards L-11: ("commands/review.md", "AGENTS.md", "AGENTS.md", ...) exempted the whole file.
        why = "reason"
        for bad in (
            ("commands/init.md", "AGENTS.md", "AGENTS.md", why),          # fragment == token
            ("commands/init.md", "AGENTS.md", "`AGENTS.md`", why),        # token + punctuation
            ("commands/init.md", "docs/DEPLOY.md", "DEPLOY", why),        # fragment inside the token
            ("commands/init.md", "CLAUDE.md", "", why),                   # no fragment
            ("commands/init.md", "CLAUDE.md", None, why),
            ("commands/init.md", "CLAUDE.md", "project", why),            # pins several lines
            ("commands/init.md", "CLAUDE.md", "no such text anywhere", why),
            ("commands/*.md", "CLAUDE.md", "project's `CLAUDE.md`", why),  # glob
            ("commands/init.md", "CLAUDE.md", "project's `CLAUDE.md`", ""),  # no reason
            # Standards L-16: a blank reason; an empty or partial prefix matches every token of the pinned line
            ("commands/init.md", "CLAUDE.md", "project's `CLAUDE.md`", " "),
            ("commands/init.md", "CLAUDE.md", "project's `CLAUDE.md`", None),
            ("commands/init.md", "", "runbook + rollback", why),
            ("commands/init.md", "d", "runbook + rollback", why),
            ("skills/discipline/shode-house-workflow/smart-coop.md", "", "CLAUDE.md", why),
            ("commands/init.md", "CLAUDE", "project's `CLAUDE.md`", why),
            ("commands/init.md", "outputs/x.md", "runbook + rollback", why),   # not a root name
        ):
            self.assertTrue(exemption_problems((bad,)), bad)
        self.assertEqual([], exemption_problems((("commands/init.md", "CLAUDE.md", "project's `CLAUDE.md`", why),)))
        # Spec S-16: marketplace.json is not a runtime file; the reason it still ships stays beside its exemption
        self.assertIn("Cowork drag-drop", next(e[3] for e in EXEMPT if e[0] == ".claude-plugin/marketplace.json"))

    # --- shipped executables parse (Standards M-4)
    def test_shipped_shell_and_python_parse(self):
        problems, parsed, _ = smoke(ROOT, shipped_files(), node=None)
        self.assertEqual([], problems)
        self.assertGreaterEqual(parsed[".sh"], 13, "shipped shell scripts were not found -- the check would be vacuous")
        self.assertGreaterEqual(parsed[".py"], 5, "shipped python files were not found -- the check would be vacuous")

    def test_shipped_javascript_parses(self):
        js = [p for p in shipped_files() if p.endswith(".js")]
        if not shutil.which("node"):
            self.skipTest(f"node is not on PATH: {len(js)} shipped .js file(s) not parsed")
        problems, parsed, notes = smoke(ROOT, js)
        self.assertEqual(([], len(js), []), (problems, parsed[".js"], notes))

    def test_smoke_check_fails_on_a_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = {"scripts/bad.sh": "#!/usr/bin/env bash\nprintf 'it's broken\\n'\n",
                   "references/x/bad.py": "def f(:\n    pass\n",
                   "skills/x/bad.js": "function ( {\n",
                   "scripts/good.sh": "#!/usr/bin/env bash\nprintf 'ok\\n'\n"}
            for rel, body in bad.items():
                (pathlib.Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
                (pathlib.Path(tmp) / rel).write_text(body)
            problems, parsed, notes = smoke(tmp, bad, node=None)
            self.assertEqual(["references/x/bad.py", "scripts/bad.sh"], sorted(p.split(":")[0] for p in problems))
            self.assertEqual((2, 1, 0), (parsed[".sh"], parsed[".py"], parsed[".js"]))
            self.assertEqual(1, len(notes)); self.assertIn("skills/x/bad.js", notes[0])   # the skip is visible
            if shutil.which("node"):
                self.assertIn("skills/x/bad.js", [p.split(":")[0] for p in smoke(tmp, bad)[0]])
                # the three shapes a shipped .js may have parse; the same shapes with an error do not
                shapes = ("module.exports = 1\nreturn\n", "export const a = 1\nawait a\n",
                          "export const meta = {}\nconst r = await f()\nreturn r\n")
                shapes += ("export const meta = {}\nexport function g() {}\nconst r = await g()\nreturn r\n",)
                for body in shapes:
                    self.assertIsNone(_js_error(shutil.which("node"), body, tmp), body)
                    self.assertTrue(_js_error(shutil.which("node"), body + "function ( {\n", tmp), body)
                # Standards L-17: only a TOP-LEVEL export is removed for the body form
                for body in ("function f(){\nexport const a=1\n}\nreturn 1\n",
                             "const r = await f()\nif (r) {\nexport const a = 1\n}\nreturn r\n",
                             "export const meta = {}\nfunction f(){\nexport const a=1\n}\nreturn 1\n"):
                    self.assertTrue(_js_error(shutil.which("node"), body, tmp), body)

    def test_unparsed_file_fails_in_ci_and_only_there(self):
        # Standards L-21: the archive is what gets uploaded; a runner without node must not pass it
        note = ["SKIP node --check: node is not on PATH; 1 shipped .js file(s) NOT parsed: skills/x/a.js"]
        self.assertTrue(unchecked_fails(note, {"CI": "true"}))
        self.assertFalse(unchecked_fails(note, {}))
        self.assertFalse(unchecked_fails(note, {"CI": ""}))
        self.assertFalse(unchecked_fails([], {"CI": "true"}))

    # --- negative tests: the matcher must see planted references, and must not see the exempt forms
    def _scan_text(self, text, name="skills/workflow/ask/planted.md"):
        body = text.encode("utf-8")
        return [(kind, ref) for _, _, kind, ref, _ in scan(shipped_files() | {name}, lambda p: body, only={name})]

    def test_planted_references_are_hits(self):
        cases = {
            "see `docs/x.md` for detail": ("path", "docs/x.md"),
            "see docs/x.md for detail": ("path", "docs/x.md"),
            "rule lives in AGENTS.md": ("path", "AGENTS.md"),
            "(CLAUDE.md 3-flag rule preserved)": ("path", "CLAUDE.md"),
            "@AGENTS.md": ("import", "AGENTS.md"),
            "[the rules](../../../AGENTS.md)": ("link", "../../../AGENTS.md"),
            "[plan](../../../docs/PLAN-v3.17.md#scope)": ("link", "../../../docs/PLAN-v3.17.md#scope"),
            'MAP="$SELF_DIR/../../../docs/x.json"': ("path", "docs/x.json"),
            "cat ${CLAUDE_PLUGIN_ROOT}/docs/x.md": ("path", "docs/x.md"),
            "Strategy: README § Model Strategy": ("section", "README.md"),
            "grep-enforced by tests/test-lock.sh": ("path", "tests/test-lock.sh"),
            "python3 scripts/eval-scorer.py run": ("path", "scripts/eval-scorer.py"),
            "kept in `skills/in-progress/` for later": ("path", "skills/in-progress/"),
            "all of `docs/<name>.md`": ("path", "docs/<name>.md"),
            "budget in `.preload-budget`": ("path", ".preload-budget"),
            # Spec S-14: this repository's own outputs/ documents
            "# see outputs/shode-roadmap/C/09-dave-workflow-state.md for that history": ("path", "outputs/shode-roadmap/C/09-dave-workflow-state.md"),
            "(see outputs/shode-house-5cs/00-oliver-plan.md's track table)": ("path", "outputs/shode-house-5cs/00-oliver-plan.md"),
            "owns outputs/shode-roadmap/C/review-**": ("path", "outputs/shode-roadmap/C/review-**"),
            "see outputs\\shode-house-5cs\\x.md": ("path", "outputs/shode-house-5cs/x.md"),          # Standards S-7
            "see outputs%2Fshode-house-5cs%2Fx.md": ("path", "outputs/shode-house-5cs/x.md"),
            # Standards L-10: shell prefixes, wrong depth, separators, encoding, letter case
            'MAP="$(dirname "$0")/../docs/x.json"': ("path", "docs/x.json"),
            'cat "$dir"/AGENTS.md': ("path", "AGENTS.md"),
            'cat "$(git rev-parse --show-toplevel)/AGENTS.md"': ("path", "AGENTS.md"),
            "cat ${CLAUDE_PLUGIN_ROOT}/../AGENTS.md": ("path", "AGENTS.md"),
            "see ../docs/x.md (one level short)": ("path", "docs/x.md"),
            "see docs\\x.md": ("path", "docs/x.md"),
            "see docs%2Fx.md": ("path", "docs/x.md"),
            "rule lives in agents.md": ("path", "agents.md"),
            "rule lives in AGENTS.MD": ("path", "AGENTS.MD"),
            "see Docs/X.md and claude.MD": ("path", "Docs/X.md"),
            # Standards L-14: the forms the loose pass exists for still hit after it was narrowed
            "cat '$d'/CLAUDE.md": ("path", "CLAUDE.md"),
            'cat "$d"/docs/x.md': ("path", "docs/x.md"),
            "cat $(pwd)/docs/x.md": ("path", "docs/x.md"),
            'cat "$d"/.Preload-Budget': ("path", ".Preload-Budget"),
            "see Eval/fixtures/a.md": ("path", "Eval/fixtures/a.md"),
            "see PLUGINS/shode-house/x": ("path", "PLUGINS/shode-house/x"),
            "open .Claude/settings.json": ("path", ".Claude/settings.json"),
            "run make -f ../../../Makefile pack": ("path", "Makefile"),
        }
        for text, expected in cases.items():
            self.assertIn(expected, self._scan_text(text), text)

    def test_exempt_forms_are_not_hits(self):
        for text in (
            "https://github.com/shode666/shode-house/blob/main/docs/x.md",
            "[repo](https://example.com/AGENTS.md) and [top](#docs)",
            "artifact : outputs/<bd-id>/01-dave.md",
            "`.shode-house/config.yaml` holds the harness contract",
            "screenshot: tests/visual/checkout-after.png and tests/visual/<feature>.png",
            "the project's src/docs/x.md and my-docs/x.md",
            "read `references/languages/<lang>.md`",
            "the docs say so; tests pass; hooks fire",
            "Makefile · README.md · .gitignore of the project",
            "load `skills/workflow/diagnose/loop-ladder.md` and `references/scope-lock.md`",
            "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start.sh",
            # the TARGET project's evidence home: placeholders, numeric ids, generic names
            "save `outputs/SPEC-<bd-id>.md`, outputs/$BD and outputs/42/03-developer-phase-2.md",
            "outputs/adr/INDEX.md · outputs/opportunity-refund.md · `outputs/` · outputs/shode-<id>/x.md",
            "the Docs team said so; EVAL is pending; see https://example.com/a/AGENTS.MD",
            "an agent's own notes: my-agents.md, src/Docs/x.md",
            # Standards L-14: routes, links and capitalised word pairs of the reader's project
            'app.get("/docs/openapi.json")',
            '<a href="/docs/guide">',
            "Release/Rollback plan is required",
            "Docs/Design review",
            "the Eval/Test split",
            'location "/release/" { }',
            "git flow: Release/Hotfix branches",
            # Standards S-7: a URL whose path happens to contain outputs/
            "https://example.com/outputs/shode-house-1/x.md",
        ):
            self.assertEqual([], self._scan_text(text), text)

    def test_outputs_rule_does_not_read_the_checkout(self):
        # Standards M-6: outputs/ is git-ignored. Shipped text tells the reader's project to write
        # `outputs/SESSION-STATE.md` and `outputs/adr/INDEX.md`; when a maintainer's checkout happened
        # to hold those files the gate went red locally and stayed green in CI.
        text = ("write outputs/SESSION-STATE.md and outputs/adr/INDEX.md; "
                "not outputs/shode-house-v7u/08-diff.patch").encode("utf-8")
        name = "skills/workflow/ask/planted.md"
        files = shipped_files() | {name}
        verdicts = []
        with tempfile.TemporaryDirectory() as tmp:
            for present in (False, True):
                if present:
                    for rel in ("outputs/SESSION-STATE.md", "outputs/adr/INDEX.md", "outputs/shode-house-v7u/08-diff.patch"):
                        (pathlib.Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
                        (pathlib.Path(tmp) / rel).write_text("x")
                hits = scan(files, lambda p: text, repo=pathlib.Path(tmp), names=root_names(), only={name})
                verdicts.append([(kind, ref) for _, _, kind, ref, _ in hits])
        self.assertEqual([("path", "outputs/shode-house-v7u/08-diff.patch")], verdicts[0])
        self.assertEqual(verdicts[0], verdicts[1], "the verdict changed with the files under outputs/")
        # ...and structurally: a checkout whose outputs/ cannot even be listed gives the same answer
        class NoOutputs(type(ROOT)):
            def __truediv__(self, other):
                assert not str(other).startswith("outputs"), f"scan looked at the checkout for {other}"
                return super().__truediv__(other)
        hits = scan(files, lambda p: text, repo=NoOutputs(ROOT), names=root_names(), only={name})
        self.assertEqual(verdicts[0], [(kind, ref) for _, _, kind, ref, _ in hits])

    def test_reference_from_a_shipped_script_is_seen(self):
        self.assertIn(("path", "CLAUDE.md"),
                      self._scan_text('report FAIL "$id" "see CLAUDE.md SS Agents Redact"', name="scripts/planted.sh"))


if __name__ == "__main__":
    if sys.argv[1:] == ["--scan"]:
        problems, _, notes = smoke(ROOT, shipped_files())
        found = fmt(scan_tree()) + problems
        print("\n".join(found + notes)); sys.exit(1 if found else 0)
    if len(sys.argv) == 3 and sys.argv[1] == "--archive":
        drift, found, count, (problems, parsed, notes) = scan_archive(sys.argv[2])
        print("\n".join(drift + fmt(found) + problems + notes))
        bad = drift or found or problems or unchecked_fails(notes)
        print(("FAIL" if bad else "PASS") + f": {count} files in {sys.argv[2]}; "
              f"{len(drift)} file-set differences vs {ALLOWLIST}, {len(found)} dangling references, "
              f"{len(problems)} parse failures ({parsed['.sh']} sh, {parsed['.py']} py, {parsed['.js']} js checked)")
        sys.exit(1 if bad else 0)
    unittest.main()
