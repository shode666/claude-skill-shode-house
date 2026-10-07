#!/usr/bin/env python3
"""Build a full-team test candidate; maintainer-only, never a runtime dependency.

Does not publish, install, edit source, or certify host compatibility. Existing
artifacts are never overwritten. Stable publication requires separate qualification.

Generated tree = source layout (v4 ADR iter 5 F-4, §5.8; erratum 1 §5.8.1/§5.8.2):
agent files, skill roots and command bodies at the plugin root are the authored file
(frontmatter incl. `model:` kept) with plugin-root and `./`/`../` references re-pointed to
its knowledge/ copy, plus a generated resolution footer. Two generated insertions exist and
nothing else: the style safety floor in the `ask` skill (skills-only hosts) and one pointer
line in every skill neither preloaded nor `ask`.
`${CLAUDE_PLUGIN_ROOT}/references/` (and bucketed skill paths) are rewritten to the
tree's `knowledge/` copy, never between floor markers. A `./` or `../` file reference outside
code fences and floor markers is rewritten to the same file's `knowledge/` copy, relative to
where the generated file sits (S2I-1, UD R53). `--check` asserts all of it, and that every
`./`/`../` reference in the tree's Markdown resolves inside the tree (file:line on failure).
Refused (v7u.4.23): a code fence that never closes (S21-2), any `./`/`../` reference (a dotfile
one, a doubled separator or an emphasis-wrapped one included, S23-1/S23-7) in an agent, command or
output style, whose text has no file location (S21-3, R59), a plugin-root or source-root path that
climbs with `..` (S23-9), and any symlink in the tree, on read and on write (S21-1), or above it
inside the repository (S23-2). A source problem is cited at the source file:line with the authored
text. `--tree` writes only into a new or empty directory or an existing shode-house tree (S23-6),
never through a link, hardlink or FIFO planted after its checks (S23-3/S23-4), and refuses a tree
path with a `..` component, so its checks and writes see one directory (S23-8).
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _load_floor():
    """scripts/floor.py owns the floor-marker grammar (R44); the packer parses markers with ITS locate()."""
    spec = importlib.util.spec_from_file_location("shode_floor", Path(__file__).resolve().with_name("floor.py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


floor = _load_floor()
BUCKETS = ("workflow", "ops", "ui", "style", "discipline")
# Publishing a command is a decision, not a side effect of adding a file: this is the
# explicit allowlist of authored commands the distributions register. A new
# commands/<name>.md is NOT published until it is named here (the packer refuses a
# mismatch), so "should users get this?" is answered on purpose.
PUBLISHED_COMMANDS = ("ask", "consult", "design-system", "implement", "init", "review")
# 3.17.2 ships 19 roles; the 4.0.0 switch deletes the retired orchestrator (ADR §5.2).
RETIRED_ROLE = "agents/orchestrator.md"

# Floor markers: taken from scripts/floor.py, which owns the grammar and the check; the packer only
# refuses to touch what lies between them.
BODY_KIND, STYLE_KIND = floor.KINDS
BODY_FLOOR = (BODY_KIND.begin, BODY_KIND.end)
STYLE_FLOOR = (STYLE_KIND.begin, STYLE_KIND.end)
# The style whose floor the `ask` skill carries on skills-only hosts (erratum 1 §5.8.1 item 4).
FLOOR_STYLE = "output-styles/shode-house.md"
ASK_SKILL = "skills/ask/SKILL.md"
# Files that may carry a floor block in the tree; anything else carrying one is red.
FLOOR_CARRIERS = re.compile(r"^(?:knowledge/)?(?:agents|output-styles)/[^/]+\.md$|^skills/ask/SKILL\.md$")

# F-4 prefix rewrite: these roots exist in the tree only under knowledge/. (`skills/ask/...`,
# `agents/...`, `commands/...` and `output-styles/...` also exist at the tree root, so stay.)
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}/"
REWRITE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/(?=(?:references|skills/(?:%s))/)" % "|".join(BUCKETS))
# A shipped script named in a generated body (X11): only ever as the quoted, root-anchored
# knowledge path, and the file must exist in the tree. A relative path runs a project file.
SCRIPT = re.compile(r"(?:knowledge/)?references/[A-Za-z0-9._/-]+\.(?:py|sh|js|mjs|cjs)\b")
ANCHORED = '"' + PLUGIN_ROOT
# S2I-1 / UD R53: a file-relative reference (`./x`, `../x`, `../../x/y.md`, `../dir/`, and a dotfile such as
# `./.env` or `../../.ssh/id_rsa`, Sentinel S23-1). A separator may be doubled (`..//.ssh`, `.//.env`, S23-7):
# POSIX reads it as one. The first name may start with any letter or punctuation a file name can (`../ไทย.md`,
# `../@x`, `./~x`, `./-x.md`, S23-10); the name runs to whitespace or a closing delimiter. It must name something
# after the dots: a segment of dots only (a bare `../`, `../..`, `.../`) or `../$(VAR)`, `../{a,b}`, `../<x>` is
# shell text, not a reference. It must not continue a longer path or a `${...}` expansion; a `_` before it is
# emphasis (`_../.env_`, S23-7) and a `~` strikethrough (`~~../.env~~`, S23-11), not a longer name. Fenced code
# is not scanned: it is project shell/config text.
RELATIVE = re.compile(r"(?<![^\W_])(?<![./$}-])(?:\.\.?/+)+"
                      r"(?:\.+[^\s./\\)>\]'\"`*|<,;:!?]|[^\s./\\)>\]'\"`*|<,;:!?${])[^\s)>\]'\"`*|<]*")
# What ends a matched reference without being part of it: a sentence's punctuation, and a closing `_` of emphasis.
TRAILING = ".,;:!?"
# S23-9: a plugin-root or source-root path (`${CLAUDE_PLUGIN_ROOT}/x`, `references/x`, `knowledge/skills/x`). The
# host resolves it under the plugin (the footer says so), so a `..` segment in it climbs out of the plugin root.
ROOTED = re.compile(r"(?<![^\W_])(?<![./~$}-])(?:\$\{?CLAUDE_PLUGIN_ROOT\}?|(?:knowledge/)?(?:agents|skills|"
                    r"references|commands|output-styles))/[^\s)>\]'\"`*|<]*")
ROOTED_RULE = ("climbs with `..`; a plugin-root or source-root path names a plugin file directly and never leaves "
               "the plugin root (S23-9)")
# A fence line (CommonMark-style, Chris C15-2): a run of 3+ backticks or tildes, then an info string. It closes
# only on the same character, at least as long, with nothing after it (see _fence_scan).
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
# A fence written after a list marker or `>` on the same line (Chris C23-2). It is NOT recognized as a fence:
# CommonMark closes such a fence when the list item or quote ends, so treating it as one could hide prose. It
# is only used to point the author at the cause when a later fence line is then left unclosed.
CONTAINER_FENCE = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)]|>)[ \t]*(?:`{3,}|~{3,})")
# S21-3 + R59: an agent system prompt, an injected command body and an output style (the main-session system
# prompt) have no file location, so a `./`/`../` path in them would be resolved from the project's working
# directory. None may carry one (outside fences). One rule text for the source and the tree side (C23-4).
LOCATION_FREE = re.compile(r"^(?:agents|commands|output-styles)/[^/]+\.md$")
LOCATION_FREE_RULE = ("in an agent, command or output style has no file location (it would resolve from the "
                      "project's working directory); name a plugin file in the source-root form (references/..., "
                      "skills/...) or fence a project path")
UNCLOSED = ("code fence never closed (a ``` or ~~~ fence closes only on a line of the same character, at least "
            "as long, with no info string); the rest of the file would skip the reference check")

# Footer lines (generated; never in source). The resolution line is the 3.17 wording.
RESOLVE = ("Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ "
           "under this plugin's knowledge/ directory, not the user's project.\n")
AUTHORITY = "Use actual host tools and preserve host/project/user authority.\n"
# erratum 1 §5.8.1 item 5 (SE1 E1-4(ii)): the ask skill sits under a floor that nothing relaxes.
AUTHORITY_ASK = ("Use actual host tools and preserve host/project/user authority, "
                 "except R0 and the rest of the safety floor above.\n")
# erratum 1 §5.8.1 "Pointer line" (SE1 E1-2(b)): 117 B, in every skill neither preloaded nor ask.
POINTER = ("No shode-house safety floor in this context (a main session without the router style)? "
           "Load `shode-house:ask` first.\n")

# `/ask` stays the hand-written wrapper of the tree `ask` skill (erratum 1 r1, E1-1: no repoint
# to knowledge/ -- the floor-carrying skill is reached through every host's `/ask`).
# Persona-free since W2 iter 2 (A6 retires the persona). Conditional since the S2 integration (v7u.4.12, Bella W2 L1).
# The condition names no style (UD R52, Bella S2 M-1): it is keyed on a working delegation tool, as the ask
# skill decides ("If delegation is unavailable ..."), so it holds at S2 and S3 alike; a session without one
# (Codex, Cursor, Antigravity; option A) reports team execution BLOCKED.
# UD R56 (W7, with erratum 1 §5.8.2): the wrapper defers to the ask skill's decision -- delegation also needs
# the skill not to report team execution unavailable (its style-less-session rule, fail-closed), so a session
# with Agent but no router style gets BLOCKED from the skill and no contradicting "delegate" from here.
ASK_WRAPPER = (
    '---\ndescription: "Work with the full Shode House team."\n---\n\n'
    'User request: $ARGUMENTS\n\n'
    'Use `${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md` as the entry point; '
    'load further references only when it directs you to. '
    'If this session has a working delegation tool (Agent or Task) and the ask skill does not report team '
    'execution unavailable, delegate specialist work to the shode-house agents by agent id and never spawn the '
    'main-session lead or router as an agent; otherwise report team execution BLOCKED instead of role-playing '
    'the team.\n'
).encode()
ASK_TARGET = PLUGIN_ROOT + ASK_SKILL

# erratum 1 §5.8.2 (UD R37 option A). ASCII, <= 200 chars (Cowork).
TREE_DESCRIPTION = ("Shode House: full expert team on Claude Code; skills-only, single session on "
                    "Codex, Cursor and Antigravity.")
# erratum 1 §5.8.1 "HOST-NOTES" bullets, persona-free; Antigravity per W0 P4 (agy 1.2.2 validate).
HOST_BULLETS = (
    "- Claude Code: `.claude-plugin` manifest, flat skills, agents, the authored commands (`/ask` is the "
    "entry). Team execution (the router style delegating to specialist agents) is supported here only.\n"
    "- Codex, Cursor, Antigravity: skills run in one session; there is no router style. Agent spawns return "
    "`BLOCKED: unrouted` by design; never replace delegation with role-play.\n"
    "- On those hosts the safety floor is in the `ask` skill (other shode-house skills point to it); it "
    "applies only once loaded and can be lost when context is compacted. The only enforced control for "
    "irreversible actions there is the host's own command-approval and sandbox setting: keep approval on "
    "for shell and MCP actions.\n"
    "- Manifests: `.codex-plugin` (skills), `.cursor-plugin` (skills; `ask` is a skill, no commands), root "
    "`plugin.json` (Antigravity). Antigravity's validator (agy 1.2.2) processes the agent files and converts "
    "the commands to skills. Whether agents run on Codex, Cursor or Antigravity, and whether their `model:` "
    "values are honoured there, is unverified.\n"
)
# Wording 3.17 shipped and W0 P4 contradicted (agy processes the agents): must never return.
STALE_HOST_CLAIM = "Agent files are knowledge, not native registrations"


def frontmatter(text, name):
    """-> (header incl. both --- lines and the newline after the closing one, rest)."""
    if not text.startswith("---\n"):
        raise ValueError(f"missing frontmatter: {name}")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError(f"missing frontmatter: {name}")
    return text[:end + 5], text[end + 5:]


def segments(text, name=""):
    """[(is_floor, text)] -- the floor segment is the block exactly as scripts/floor.py `locate()` finds it:
    one marker pair of one kind, whole LF lines, the begin marker the first non-blank line after the
    frontmatter (R44). Text without floor-marker text is one plain segment. Any malformed or misplaced
    marker is an error: the packer never guesses floor bounds and parses them with floor.py's grammar."""
    data = text.encode("utf-8")
    if floor.MARK.encode() not in data:
        return [(False, text)]
    style = STYLE_FLOOR[0] in text or STYLE_FLOOR[1] in text
    kind, other = (STYLE_KIND, BODY_KIND) if style else (BODY_KIND, STYLE_KIND)
    start, stop, problem = floor.locate(data, kind, other)
    if problem is not None:
        raise ValueError(f"{name}: malformed floor markers ({problem})")
    parts = ((False, data[:start]), (True, data[start:stop]), (False, data[stop:]))
    return [(is_floor, part.decode("utf-8")) for is_floor, part in parts if part]


def tree_path(name):
    """Where the generated copy of an authored agent, skill root or command sits in the tree."""
    if name.startswith("skills/") and name.endswith("/SKILL.md"):
        return "skills/" + Path(name).parent.name + "/SKILL.md"
    return name


def _lines(text):
    """Lines split on LF only, endings kept (Chris C23-3): `str.splitlines` also splits on \\x0b \\x0c \\x1c-\\x1e
    \\x85 U+2028 U+2029 and a lone CR, so a cited line number could run ahead of the editor's."""
    parts = text.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _unclosed_problem(path, lines, unclosed):
    """The S21-2 problem line for a fence never closed at `unclosed`, naming a list-item or blockquote fence before
    it as the likely cause (C23-2): its closer is what then opens the fence that never closes."""
    container = [n for n, (_, line) in enumerate(lines[:unclosed - 1], 1) if CONTAINER_FENCE.match(line)]
    cause = (f"; line {container[-1]} writes a fence after a list marker or `>`, which is not recognized as a "
             "fence: put the fence on a line of its own (indent it to sit in a list item)") if container else ""
    return f"{path}:{unclosed}: {UNCLOSED}{cause}"


def _fence_scan(text):
    """-> ([(is_fenced, line)] with line endings kept, unclosed). A fence line itself counts as fenced. A fence
    opens on 3+ backticks or tildes (a backtick fence's info string holds no backtick) and closes only on a
    line of the same character, at least as long, with nothing after it but blanks; anything else inside is
    fenced text (``` inside ````md, ``` inside ~~~). `unclosed` = 1-based line of a fence never closed, else
    None (S21-2: a contract failure, since everything after it would skip relocation and the check)."""
    result, opener, unclosed = [], None, None
    for number, line in enumerate(_lines(text), 1):
        match = FENCE.match(line.rstrip("\r\n"))
        if opener is None:
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                opener, unclosed = match.group(1), number
                result.append((True, line))
            else:
                result.append((False, line))
            continue
        run = match.group(1) if match else ""
        if run[:1] == opener[0] and len(run) >= len(opener) and not match.group(2).strip():
            opener, unclosed = None, None
        result.append((True, line))
    return result, unclosed


def _unfenced_lines(text):
    """-> [(is_fenced, line)] with line endings kept; a fence line itself counts as fenced."""
    return _fence_scan(text)[0]


def _reference(match):
    """The path a RELATIVE match names: trailing sentence punctuation dropped, and a closing `_` when an opening
    `_` stands right before the match (emphasis, S23-7)."""
    emphasis = match.start() > 0 and match.string[match.start() - 1] == "_"
    return match.group(0).rstrip(TRAILING + ("_" if emphasis else ""))


def _climbing(path, number, line):
    """S23-9: one problem per plugin-root or source-root path on `line` that holds a `..` segment."""
    return [f"{path}:{number}: path `{match.group(0)}` {ROOTED_RULE}"
            for match in ROOTED.finditer(line) if ".." in match.group(0).split("/")]


def _dirs(names):
    """Every directory that holds one of `names` (posix paths), plus "."."""
    found = {"."}
    for name in names:
        parent = posixpath.dirname(name)
        while parent:
            found.add(parent)
            parent = posixpath.dirname(parent)
    return found


def source_problems(name, text, source_entries):
    """Authored-side reference check of one agent, skill root or command, cited at the SOURCE file:line with the
    authored reference (Chris C15-2): a fence never closed (S21-2); any `./`/`../` reference in an agent or a
    command (S21-3, floor text included: it is the same system prompt); in a skill, a reference that names no
    shipped file from the source layout (a project path such as `./mvnw` in prose); anywhere, fenced code
    included, a plugin-root or source-root path that climbs with `..` (S23-9)."""
    lines, unclosed = _fence_scan(text)
    found = [_unclosed_problem(name, lines, unclosed)] if unclosed is not None else []
    base, dirs = posixpath.dirname(name), _dirs(source_entries)
    for number, (fenced, line) in enumerate(lines, 1):
        found += _climbing(name, number, line)
        if fenced:
            continue
        for match in RELATIVE.finditer(line):
            ref = _reference(match)
            if LOCATION_FREE.match(name):
                found.append(f"{name}:{number}: relative reference `{ref}` {LOCATION_FREE_RULE}")
                continue
            # An escaping target (`..`, `../x`) is never a source key or directory, so membership covers it.
            target = posixpath.normpath(posixpath.join(base, ref))
            if target not in source_entries and target not in dirs:
                found.append(f"{name}:{number}: relative reference `{ref}` names no shipped file from this source "
                             "file; fence a project path (e.g. `./mvnw`) in a code block")
    return found


def relocate(text, name=""):
    """S2I-1 / UD R53: each `./`/`../` reference of the authored file `name`, outside fenced code, is pointed at
    the same file's knowledge/ copy, relative to where the generated copy sits (so "relative to this file"
    stays true in the tree). A reference that leaves the source root is kept; the resolution check reports it.
    Without a name (a text fragment) nothing moves."""
    if not name:
        return text
    source_dir, tree_dir = posixpath.dirname(name), posixpath.dirname(tree_path(name)) or "."

    def move(match):
        ref = match.group(0)
        body = _reference(match)                     # a sentence's full stop is not part of the path
        target = posixpath.normpath(posixpath.join(source_dir, body))
        if target in (".", "..") or target.startswith("../"):
            return ref
        moved = posixpath.relpath("knowledge/" + target, tree_dir) + ("/" if body.endswith("/") else "")
        return moved + ref[len(body):]

    return "".join(line if fenced else RELATIVE.sub(move, line) for fenced, line in _unfenced_lines(text))


def _plain(segment, name):
    """The generated form of one non-floor segment: relative references relocated, then the F-4 rewrite."""
    return REWRITE.sub(PLUGIN_ROOT + "knowledge/", relocate(segment, name))


def rewrite(text, name=""):
    """F-4 path rewrite plus the R53 relative-reference relocation, applied outside floor markers only (floor
    bytes are never touched)."""
    if PLUGIN_ROOT + "knowledge/" in text:
        raise ValueError(f"source already names the tree's knowledge/ path (rewrite would be ambiguous): {name}")
    return "".join(seg if is_floor else _plain(seg, name) for is_floor, seg in segments(text, name))


def floor_blocks(text, name=""):
    return [seg for is_floor, seg in segments(text, name) if is_floor]


def style_floor_block(source_entries):
    """The style floor of FLOOR_STYLE, markers included (an empty pair while pending, §5.8.1 item 4)."""
    if FLOOR_STYLE not in source_entries:
        raise ValueError(f"{FLOOR_STYLE} missing: the ask skill's floor has no source")
    blocks = [b for b in floor_blocks(source_entries[FLOOR_STYLE].decode(), FLOOR_STYLE)
              if b.strip().startswith(STYLE_FLOOR[0])]
    if len(blocks) != 1:
        raise ValueError(f"{FLOOR_STYLE} needs exactly one style floor marker pair (found {len(blocks)})")
    return blocks[0]


def preloaded(source_entries):
    """Skill names any role preloads, DERIVED from the `skills:` lines (never a hand list)."""
    names = set()
    for path, body in sorted(source_entries.items()):
        if path.startswith("agents/") and path.endswith(".md"):
            header, _ = frontmatter(body.decode(), path)
            for line in header.splitlines():
                if line.startswith("skills:"):
                    # Fail closed (Sentinel W2 S2): `skills: [ask, x]` and the block-list form are valid YAML
                    # the host would preload, but a lenient parse would miss them. Only the JSON-style
                    # quoted single-line list (the CI #13 form) is understood; anything else is refused.
                    try:
                        value = json.loads(line.split(":", 1)[1])
                    except ValueError:
                        value = None
                    if not isinstance(value, list) or not all(isinstance(n, str) and n for n in value):
                        raise ValueError(f"{path}: `skills:` must be a JSON-style quoted single-line list "
                                         f'(e.g. skills: ["shode-house-discipline"]), got {line!r}')
                    names |= {n.split(":", 1)[-1] for n in value}
    return names


def skill_footer(bucket, name, pointer):
    # R53: `./`/`../` references are already relocated to this file's location, so the bucket-directory rule
    # covers only the other (bare) relative names; reading it for `../` too would re-break them.
    return ("\n" + RESOLVE +
            "Resolve paths beginning ./ or ../ from this file's own directory; resolve other relative file names "
            f"in this skill under this plugin's knowledge/skills/{bucket}/{name}/ "
            "directory.\n" + (AUTHORITY_ASK if name == "ask" else AUTHORITY) + (POINTER if pointer else ""))


AGENT_FOOTER = "\n" + RESOLVE
# Sentinel W2 S1: Antigravity converts commands to skills, so every published command except the `/ask`
# wrapper (which IS the entry) carries the pointer line too.
COMMAND_FOOTER = "\n" + RESOLVE + POINTER


def collect(root=ROOT):
    root = root.resolve()
    # U22 H3: the manifest's fields (description, author, homepage ...) are copied into the tree, so it is read
    # only as a regular file in a regular directory, never through a link to a file outside the repository
    for name in (".claude-plugin", ".claude-plugin/plugin.json"):
        if (root / name).is_symlink():
            raise ValueError(f"symlink not allowed: {name}")
    manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
    if manifest["name"] != "shode-house":
        raise ValueError("unexpected plugin identity")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", manifest["version"]):
        raise ValueError("invalid version")
    entries = {}
    roots = [root / "agents", root / "references", root / "output-styles", root / "commands"]
    roots += [root / "skills" / bucket for bucket in BUCKETS]
    for folder in roots:
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError(f"invalid source directory: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"symlink not allowed in candidate: {path}")
            if not path.is_file() or "__pycache__" in path.parts or path.name == ".DS_Store":
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError("source escapes repository")
            entries[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("commands/ask.md", "LICENSE"):
        path = root / name
        if path.is_symlink():
            raise ValueError(f"symlink not allowed: {name}")
        entries[name] = path.read_bytes()
    return manifest, entries


def roles_and_skills(source_entries):
    roles = sorted(p for p in source_entries if p.startswith("agents/") and p.endswith(".md"))
    skills = sorted(p for p in source_entries if p.endswith("/SKILL.md"))
    want = 19 if RETIRED_ROLE in source_entries else 18
    if len(roles) != want or len(skills) != 20:
        raise ValueError(f"candidate must ship exactly {want} roles and the 20 skills (incl. ask); "
                         f"found {len(roles)} roles, {len(skills)} skills")
    return roles, skills


def terminated(text):
    """A source without a final newline gets one before the footer (tree = source + "\\n" + footer)."""
    # shortcut(bd:shode-house-xtb): normalise a missing final newline (today only
    # skills/workflow/dev-gate/SKILL.md); upgrade -> add the newline to that source (W7), then raise
    # ValueError("source must end with a newline") here instead.
    return text if text.endswith("\n") else text + "\n"


def generate(name, source, source_entries, pointer_set):
    """Tree text for one authored agent/skill/command: source (rewritten outside floors) + footer."""
    text = terminated(source.decode("utf-8"))
    frontmatter(text, name)   # every agent, skill root and command must open with frontmatter
    problems = source_problems(name, text, source_entries)
    if problems:
        raise ValueError("\n  ".join(problems))
    if name.startswith("agents/"):
        return rewrite(text, name) + AGENT_FOOTER
    if name.startswith("commands/"):
        return rewrite(text, name) + COMMAND_FOOTER
    bucket, skill = Path(name).parts[1], Path(name).parent.name
    footer = skill_footer(bucket, skill, skill in pointer_set)
    if skill != "ask":
        return rewrite(text, name) + footer
    header, rest = frontmatter(text, name)
    # §5.8.1 item 2: the block goes directly after the frontmatter, separated by one blank line.
    return header + "\n" + style_floor_block(source_entries) + rewrite(rest, name) + footer


def payload(root=ROOT):
    manifest, source_entries = collect(root)
    roles, skills = roles_and_skills(source_entries)
    # Preserve authored relative layout under one knowledge root (recovery inventory, and
    # the target of every footer). Native discovery requires flat skills/<name>/SKILL.md.
    entries = {"knowledge/" + name: body for name, body in source_entries.items()}
    preload = preloaded(source_entries)
    pointer_set = {Path(p).parent.name for p in skills} - preload - {"ask"}
    for name in [*roles, *skills]:
        target = name if name in roles else "skills/" + Path(name).parent.name + "/SKILL.md"
        if target in entries:
            raise ValueError(f"duplicate discovery path: {target}")
        entries[target] = generate(name, source_entries[name], source_entries, pointer_set).encode()
    # An output style is the main-session system prompt: verbatim at the host's default scan
    # path (plugin root output-styles/), which is what activates `force-for-plugin`. No
    # `outputStyles` manifest key: that field replaces the default scan (AGENTS.md § Output styles).
    for name in sorted(p for p in source_entries if p.startswith("output-styles/")):
        if name in entries:
            raise ValueError(f"duplicate discovery path: {name}")
        entries[name] = source_entries[name]
    authored = sorted(Path(p).stem for p in source_entries
                      if p.startswith("commands/") and p.endswith(".md"))
    if authored != sorted(PUBLISHED_COMMANDS):
        raise ValueError("authored commands differ from PUBLISHED_COMMANDS: "
                         f"{authored} != {sorted(PUBLISHED_COMMANDS)} -- publishing a command is a "
                         "deliberate decision; add or remove it in PUBLISHED_COMMANDS")
    # Commands: the authored body verbatim + footer (it carries its own `$ARGUMENTS`). ask.md keeps
    # its hand-written wrapper, which enters through the floor-carrying tree ask skill.
    for name in sorted(p for p in source_entries
                       if p.startswith("commands/") and p.endswith(".md") and p != "commands/ask.md"):
        if name in entries:
            raise ValueError(f"duplicate discovery path: {name}")
        entries[name] = generate(name, source_entries[name], source_entries, pointer_set).encode()
    entries["commands/ask.md"] = ASK_WRAPPER
    entries["LICENSE"] = source_entries["LICENSE"]
    # No hooks directory, root runner scripts or auto-start MCP is copied. The
    # knowledge/reference tree remains intact, including optional project examples.
    manifest = {key: manifest[key] for key in
                ("name", "version", "author", "homepage", "repository", "license")}
    manifest.update(description=TREE_DESCRIPTION,
                    skills="./skills/",
                    commands=sorted("./" + name for name in entries if name.startswith("commands/")))
    entries[".claude-plugin/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    codex = {key: manifest[key] for key in
             ("name", "version", "description", "author", "homepage", "repository", "license")}
    codex.update(skills="./skills/", interface={
        "displayName": "Shode House",
        "shortDescription": "The full software-house expert team",
        "longDescription": TREE_DESCRIPTION,
        "developerName": "shode666",
        "category": "Developer Tools",
        "capabilities": ["Interactive", "Write"],
        "websiteURL": manifest["homepage"],
        "defaultPrompt": ["Work with the Shode House team on this project."],
    })
    entries[".codex-plugin/plugin.json"] = (json.dumps(codex, indent=2) + "\n").encode()
    return manifest["version"], entries


def unified_payload(root=ROOT):
    """One tree, four host manifests. Schema layout is not execution qualification."""
    version, entries = payload(root)
    manifest = json.loads(entries[".claude-plugin/plugin.json"])
    # Agent frontmatter is kept verbatim, `model:` included (UD R13; W0 P4 confirmed on Claude Code).
    roles = sum(1 for p in entries if p.startswith("knowledge/agents/") and p.endswith(".md"))
    cursor = {key: manifest[key] for key in ("name", "version", "description", "author", "license")}
    # commands/ask.md uses the Claude command dialect; Cursor gets ask as a skill only.
    cursor.update(displayName="Shode House", keywords=["software-house", "agents", "skills"], commands=[])
    entries[".cursor-plugin/plugin.json"] = (json.dumps(cursor, indent=2) + "\n").encode()
    # Antigravity marker (also the agent-plugins.org root manifest shape).
    marker = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
              "name": "shode-house", "version": version, "description": manifest["description"]}
    entries["plugin.json"] = (json.dumps(marker, indent=2) + "\n").encode()
    entries["HOST-NOTES.md"] = (
        f"# Shode House {version} host notes\n\n"
        f"All {roles} role sources and 20 skills are preserved under knowledge/. The agent files, skill roots "
        "and commands at the plugin root are those sources with plugin-root and `./`/`../` references re-pointed "
        "to their knowledge/ copies, plus a generated resolution footer; "
        "`/ask` is the pinned wrapper of the ask skill. Use ask as the entry.\n\n" + HOST_BULLETS + "\n"
        "Skill discovery does not prove separate workers are available. If delegation is "
        "unavailable, report team execution BLOCKED; never replace it with role-play.\n"
        "No automatic hooks or MCP startup are included.\n"
    ).encode()
    problems = audit(entries, collect(root)[1])
    if problems:
        raise ValueError("generated tree violates the packaging contract:\n  " + "\n  ".join(problems))
    return version, entries


def _core_problems(path, core, source, name):
    """`core` (tree text minus footer and the ask block) against its authored source `name`."""
    found = []
    try:
        tree_segs, src_segs = segments(core, path), segments(source, path)
    except ValueError as error:
        return [f"{path}: {error}"]
    if [f for f, _ in tree_segs] != [f for f, _ in src_segs]:
        return [f"{path}: floor marker layout differs from source"]
    for (is_floor, seg), (_, src) in zip(tree_segs, src_segs):
        if is_floor:
            if seg != src:
                found.append(f"{path}: floor bytes differ from source (the path rewrite must skip floor markers)")
            continue
        # Forward comparison (Chris W2 S-1): exact against both an under- and an over-rewrite.
        if seg == _plain(src, name):
            continue
        if REWRITE.search(seg):
            found.append(f"{path}: plugin-root path not rewritten to knowledge/ outside the floor")
        elif RELATIVE.sub("<ref>", seg) == RELATIVE.sub("<ref>", _plain(src, name)):
            found.append(f"{path}: a ./ or ../ reference is not the source reference relocated to its knowledge/ "
                         "copy (R53)")
        elif seg.replace(PLUGIN_ROOT + "knowledge/", PLUGIN_ROOT) == relocate(src, name):
            found.append(f"{path}: rewrites a plugin-root path outside the F-4 set (only references/ and "
                         "skills/<bucket>/ move to knowledge/)")
        else:
            found.append(f"{path}: differs from its source beyond the knowledge/ path rewrite")
    return found


def _script_problems(path, text, entries):
    """X11: every shipped script named outside the floor is `"${CLAUDE_PLUGIN_ROOT}/knowledge/...` and exists."""
    found = []
    try:
        outside = "".join(seg for is_floor, seg in segments(text, path) if not is_floor)
    except ValueError:
        return found  # reported by the core check
    for match in SCRIPT.finditer(outside):
        start, target = match.start(), match.group(0)
        if not target.startswith("knowledge/") or outside[max(0, start - len(ANCHORED)):start] != ANCHORED:
            found.append(f"{path}: script path `{target}` is not root-anchored as "
                         f"\"${{CLAUDE_PLUGIN_ROOT}}/knowledge/... (a relative path runs a project file)")
        elif target not in entries:
            found.append(f"{path}: script path `{target}` does not resolve to a file in the tree")
    return found


def _reference_problems(entries):
    """S2I-1 / UD R53: every `./`/`../` reference in the tree's Markdown (outside fenced code) resolves from the
    file's own directory to a file or directory inside the tree; an agent, command or output style at the tree
    root carries none (S21-3, R59); every fence closes (S21-2); no plugin-root or source-root path climbs with
    `..`, fenced code included (S23-9). One `path:line` problem each."""
    dirs = _dirs(entries)
    found = []
    for path in sorted(p for p in entries if p.endswith(".md")):
        base = posixpath.dirname(path)
        lines, unclosed = _fence_scan(entries[path].decode("utf-8", "replace"))
        if unclosed is not None:
            found.append(_unclosed_problem(path, lines, unclosed))
        for number, (fenced, line) in enumerate(lines, 1):
            found += _climbing(path, number, line)
            if fenced:
                continue
            for match in RELATIVE.finditer(line):
                ref = _reference(match)
                # An escaping target (`..`, `../x`) is never a tree key or directory, so membership covers it.
                target = posixpath.normpath(posixpath.join(base, ref))
                if LOCATION_FREE.match(path):
                    found.append(f"{path}:{number}: relative reference `{ref}` {LOCATION_FREE_RULE}")
                elif target not in entries and target not in dirs:
                    found.append(f"{path}:{number}: relative reference `{ref}` does not resolve inside the tree "
                                 "(fence a project path)")
    return found


def _file_problems(path, name, footer, block, entries, source_entries):
    """One generated agent/skill/command against its source: footer, ask block, core, model, X11."""
    text, source = entries[path].decode("utf-8", "replace"), terminated(source_entries[name].decode("utf-8"))
    if not text.endswith(footer):
        return [f"{path}: does not end with its generated footer"]
    found = []
    core = text[:len(text) - len(footer)]
    if path == ASK_SKILL:
        header, _ = frontmatter(source, name)
        if block in source:
            found.append(f"{name}: the source ask skill carries the style floor (tree adapter only)")
        if not core.startswith(header + "\n" + block):
            return found + [f"{path}: the style floor block is not directly after the frontmatter, "
                            f"byte-equal to {FLOOR_STYLE}"]
        core = header + core[len(header) + 1 + len(block):]
    found += _core_problems(path, core, source, name)
    if path.startswith("agents/"):
        src_model = re.findall(r"^model:.*$", frontmatter(source, name)[0], re.M)
        tree_model = re.findall(r"^model:.*$", frontmatter(text, path)[0], re.M)
        if src_model != tree_model:
            found.append(f"{path}: `model:` not kept from source ({tree_model} != {src_model})")
    return found + _script_problems(path, text, entries)


def audit(entries, source_entries):
    """Packaging contract of the generated tree (A7, X11, erratum 1 §5.8.1/§5.8.2) -> [problem]."""
    found = []
    try:
        roles, skills = roles_and_skills(source_entries)
        block = style_floor_block(source_entries)
        preload = preloaded(source_entries)
    except ValueError as error:
        return [str(error)]
    if "ask" in preload:
        found.append("a role preloads `ask`: the style floor would reach a spawn twice (UD R32)")
    pointer_set = {Path(p).parent.name for p in skills} - preload - {"ask"}
    generated = {}
    for name in roles:
        generated[name] = (name, AGENT_FOOTER)
    for name in skills:
        bucket, skill = Path(name).parts[1], Path(name).parent.name
        generated["skills/" + skill + "/SKILL.md"] = (name, skill_footer(bucket, skill, skill in pointer_set))
    for name in source_entries:
        if name.startswith("commands/") and name.endswith(".md") and name != "commands/ask.md":
            generated[name] = (name, COMMAND_FOOTER)
    for path, (name, footer) in sorted(generated.items()):
        if path not in entries:
            found.append(f"{path}: missing from the tree")
            continue
        try:   # a damaged file is reported as a problem, never raised (Chris W2 S-5)
            found += _file_problems(path, name, footer, block, entries, source_entries)
        except ValueError as error:
            found.append(f"{path}: {error}")
    # The pointer line sits in exactly the derived set (skills) and in every published command but the
    # `/ask` wrapper (Sentinel W2 S1); the style block nowhere but its carriers.
    for path, body in sorted(entries.items()):
        has = POINTER in body.decode("utf-8", "replace")
        if path.startswith("skills/") and path.endswith("/SKILL.md"):
            if has != (Path(path).parent.name in pointer_set):
                found.append(f"{path}: pointer line {'present' if has else 'missing'}; "
                             f"derived set = skills neither preloaded nor ask")
        elif re.fullmatch(r"commands/[^/]+\.md", path):
            if has != (path != "commands/ask.md"):
                found.append(f"{path}: pointer line {'present' if has else 'missing'}; "
                             f"every published command except the /ask wrapper carries it")
        if not FLOOR_CARRIERS.match(path) and (STYLE_FLOOR[0].encode() in body or BODY_FLOOR[0].encode() in body):
            found.append(f"{path}: carries a floor block outside the floor carriers")
    # `/ask`: the hand-written wrapper of the tree ask skill, never repointed (E1-1).
    wrapper = entries.get("commands/ask.md", b"")
    if wrapper != ASK_WRAPPER:
        found.append("commands/ask.md: the /ask wrapper changed (must stay the tree ask-skill wrapper)")
    if ASK_TARGET.encode() not in wrapper or b"knowledge/" in wrapper or ASK_SKILL not in entries:
        found.append(f"commands/ask.md: must resolve to {ASK_TARGET} (the floor carrier), not a knowledge/ copy")
    # Host statements (§5.8.2) where the tree has them.
    for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
                 "plugin.json"):
        if name in entries and json.loads(entries[name]).get("description") != TREE_DESCRIPTION:
            found.append(f"{name}: description is not the §5.8.2 tree description")
    notes = entries.get("HOST-NOTES.md")
    if notes is not None:
        notes = notes.decode()
        if HOST_BULLETS not in notes:
            found.append("HOST-NOTES.md: the §5.8.1/§5.8.2 host bullets are missing or changed")
        if STALE_HOST_CLAIM in notes:
            found.append("HOST-NOTES.md: repeats the Antigravity 'skills only' claim W0 P4 contradicted")
    return found + _reference_problems(entries)


DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
# A FIFO opened for reading must not block (Sentinel S23-4: `--tree` hung on one).
READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
# The marker of a shode-house tree (S23-6): both files, regular, the manifest naming this plugin.
TREE_MARKER = (".claude-plugin/plugin.json", "HOST-NOTES.md")


def _parts_under_root(destination, root):
    """C23R2-1: the components of `destination` below `root`, or None when it does not lie under `root`. The repo
    is found among the destination's ancestors by identity (device + inode), not by spelling, so a path written
    through a symlinked ancestor of the repo (`/tmp` -> `/private/tmp`, a linked workspace dir) is still under it.
    Only the ancestors are compared (C23R3-1): the destination itself is never matched through a link, so a tree
    replaced by a link to the repo after the checks is still opened without following it, and refused."""
    parts = Path(os.path.abspath(destination)).parts
    for depth in range(1, len(parts)):
        try:
            if os.path.samefile(Path(*parts[:depth]), root):
                return parts[depth:]
        except OSError:
            return None                                 # a missing ancestor: nothing below it is the repo either
    return None


def linked_ancestors(destination, root=ROOT):
    """S23-2: the symlinked path components strictly between `root` and `destination` (posix, relative to root),
    when `destination` lies under `root`; [] otherwise. A destination outside the repository keeps its system
    ancestors (`/tmp` -> `/private/tmp`); the tree marker (S23-6) still guards what it would delete there."""
    parts = _parts_under_root(destination, root)
    if parts is None:
        return []
    return [Path(*parts[:i]).as_posix() for i in range(1, len(parts)) if (root / Path(*parts[:i])).is_symlink()]


def _read_regular(path, dir_fd=None):
    """The bytes of a regular file, opened without following a link and without blocking on a FIFO; None for
    anything else (a link, FIFO, socket or device is never read)."""
    try:
        fd = os.open(path, READ_FLAGS, dir_fd=dir_fd)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(fd)


def _is_empty(directory):
    """True if the directory (a path or an open directory fd) has no entries; the iterator is closed (C23R4-2)."""
    with os.scandir(directory) as entries:
        return not any(entries)


def _carries_marker(read):
    """S23-6: `read(name)` -> bytes or None; True if `.claude-plugin/plugin.json` names `shode-house` and
    `HOST-NOTES.md` is this packer's host notes."""
    manifest, notes = (read(name) for name in TREE_MARKER)
    try:
        named = json.loads(manifest).get("name") == "shode-house"
    except (TypeError, ValueError, AttributeError):
        named = False
    return named and notes is not None and notes.startswith(b"# Shode House ")


def _read_at(dir_fd, name):
    """The bytes of the regular file `name` below the open directory `dir_fd`, no component followed through a
    link; None for anything else."""
    *parents, leaf = name.split("/")
    try:
        fd = _open_dir(dir_fd, parents, create=False)
    except ValueError:
        return None
    try:
        return _read_regular(leaf, dir_fd=fd)
    finally:
        os.close(fd)


def tree_state(destination):
    """S23-6: "fresh" if `destination` is absent or an empty directory, "tree" if it is already a shode-house tree
    (`_carries_marker`), None otherwise (`--tree` must not write or clean there)."""
    destination = Path(destination)
    if not os.path.lexists(destination):
        return "fresh"
    if not destination.is_dir() or destination.is_symlink():
        return None
    if _is_empty(destination):
        return "fresh"
    return "tree" if _carries_marker(lambda name: _read_regular(destination / name)) else None


def is_tree(destination):
    """S23-6: True if `destination` is absent, an empty directory, or already a shode-house tree."""
    return tree_state(destination) is not None


def _open_dir(dir_fd, parts, create):
    """Walk `parts` from the open directory `dir_fd`, never following a link (S23-3: a link planted after the
    check is refused, not written through); missing directories are made when `create`. -> a new fd."""
    fd = os.dup(dir_fd)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                child = os.open(part, DIR_FLAGS, dir_fd=fd)
            except OSError as error:
                raise ValueError(f"refusing to write: {part!r} is not a plain directory (a symlink or other file "
                                 f"appeared in the tree: {error.strerror})") from error
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_destination(destination, root, create=True):
    """An fd of the tree directory, made if missing when `create`. Under `root` every component below `root` is
    opened without following a link (S23-2, also after the check); elsewhere only the tree directory itself is
    (S21-1), so the caller re-checks what was opened (`_check_opened`, S23-16)."""
    path = Path(os.path.abspath(destination))
    parts = _parts_under_root(path, root)
    if parts is None:
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
        base = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        parts = (path.name,)
    else:
        base = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        return _open_dir(base, parts, create=create)
    finally:
        os.close(base)


def _check_opened(tree_fd, state, identity):
    """S23-16: the S23-6 decision made again on the opened directory, before any write or delete. A path component
    swapped after the checks (outside the repo the parent is opened following links) can make the fd name another
    directory, such as the repo: it must be the directory that was checked (`identity`, (st_dev, st_ino), when one
    existed), still empty if it was fresh, and still carry the marker, read through the fd, if it was a tree."""
    info = os.fstat(tree_fd)
    if identity is not None and (info.st_dev, info.st_ino) != identity:
        problem = "is not the directory that was checked"
    elif state == "fresh" and not _is_empty(tree_fd):
        problem = "was absent or empty when checked and is not empty now"
    elif state == "tree" and not _carries_marker(lambda name: _read_at(tree_fd, name)):
        problem = f"no longer carries the shode-house marker ({' + '.join(TREE_MARKER)})"
    else:
        return
    raise ValueError(f"refusing to write: the opened tree directory {problem} (S23-16: a path component changed "
                     "after the checks); nothing was written or deleted")


def _write_entry(tree_fd, name, content):
    """Write one tree file without ever writing through what is at its path (S23-3/S23-4): parents are opened
    with O_NOFOLLOW, an unchanged regular file with one link is left alone, and anything else (a changed file, a
    hardlink, a symlink, a FIFO) is replaced by a new file renamed over the entry in the same directory."""
    *parents, leaf = name.split("/")
    fd = _open_dir(tree_fd, parents, create=True)
    temp = None
    try:
        try:
            info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            info = None
        if info is not None and stat.S_ISREG(info.st_mode) and info.st_nlink == 1 \
                and _read_regular(leaf, dir_fd=fd) == content:
            return
        temp = f".{leaf}.pack-{os.getpid()}-{os.urandom(4).hex()}"
        out = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
        try:
            view = memoryview(content)
            while view:
                view = view[os.write(out, view):]
        finally:
            os.close(out)
        os.replace(temp, leaf, src_dir_fd=fd, dst_dir_fd=fd)
        temp = None
    finally:
        if temp is not None:
            try:
                os.unlink(temp, dir_fd=fd)
            except OSError:
                pass
        os.close(fd)


def logical_spelling(destination):
    """S23-15: the logical spelling `$PWD/<destination>` of a relative tree path, or None. A shell `cd` through a
    link leaves getcwd() physical, so a cwd reached through a link inside the repo looks like an outside
    destination; $PWD keeps the link. It is used only to refuse more, and only when it is absolute, has no `..`
    and names the cwd (a stale or foreign $PWD is ignored)."""
    pwd = os.environ.get("PWD")
    if Path(destination).is_absolute() or not pwd or not os.path.isabs(pwd) or ".." in Path(pwd).parts:
        return None
    try:
        if not os.path.samefile(pwd, os.getcwd()):
            return None
    except OSError:
        return None
    return Path(os.path.abspath(Path(pwd) / destination))


def destination_path(destination):
    """S23-8: the one absolute path every check, write and delete of `--tree` / `--check` uses. A `..` component is
    refused: after a symlinked component the OS resolves `x/..` through the link target while a lexical
    normalisation drops it, so the checks and the writes could name two different directories."""
    if ".." in Path(destination).parts:
        raise ValueError(f"{destination}: refusing a tree path with a `..` component (S23-8: through a symlink the "
                         "OS and a lexical normalisation name different directories); name the directory directly")
    return Path(os.path.abspath(destination))


def write_tree(destination, root=ROOT):
    """Materialize the unified tree (the in-repo plugins/shode-house source). Refused before anything is written
    or deleted: a tree path with a `..` component (S23-8), a tree that holds a symlink or is one (S21-1), a
    symlinked component between `root` and the tree (S23-2; for a relative path also in its logical $PWD spelling,
    S23-15), and an existing non-empty directory that is not already a shode-house tree (S23-6: the stale cleanup
    would delete its files). Writes and deletes never follow a link planted after those checks (S23-3/S23-4), and
    the S23-6 decision is made again on the opened directory before the first write (S23-16)."""
    shown, destination = destination, destination_path(destination)
    links = tree_links(destination)
    if links:
        raise ValueError(f"{shown}: refusing to write through symlink(s) in the tree: {', '.join(links)} "
                         "(the tree holds regular files only; remove them)")
    logical = logical_spelling(shown)
    for spelling, note in ((destination, ""), (logical, f"; S23-15: the cwd is reached as {os.environ.get('PWD')}")):
        ancestors = linked_ancestors(spelling, root) if spelling is not None else []
        if ancestors:
            raise ValueError(f"{shown}: refusing to write through a symlinked path component: {', '.join(ancestors)} "
                             f"(S23-2: the tree and its deletions would land in the link target{note})")
    try:
        info = os.lstat(destination)
        identity = (info.st_dev, info.st_ino)
    except FileNotFoundError:
        identity = None
    state = tree_state(destination)
    if state is None:
        raise ValueError(f"{shown}: refusing to write: not empty and not a shode-house tree (no "
                         f"{' + '.join(TREE_MARKER)} of this plugin); `--tree` deletes every file that is not a "
                         "tree entry (S23-6), so point it at an empty or new directory or an existing tree")
    version, entries = unified_payload(root)
    tree_fd = _open_destination(destination, root, create=identity is None)
    try:
        _check_opened(tree_fd, state, identity)
        for name, content in sorted(entries.items()):
            _write_entry(tree_fd, name, content)
        # Stale cleanup through directory fds: fwalk never enters a linked directory, and unlink never follows
        # a link at the leaf. Only regular files are removed (as before); anything else is left for --check.
        for folder, _, filenames, folder_fd in os.fwalk(".", dir_fd=tree_fd, follow_symlinks=False):
            for leaf in filenames:
                rel = posixpath.normpath(posixpath.join(folder, leaf))
                info = os.stat(leaf, dir_fd=folder_fd, follow_symlinks=False)
                if rel not in entries and stat.S_ISREG(info.st_mode):
                    os.unlink(leaf, dir_fd=folder_fd)
    finally:
        os.close(tree_fd)
    return version, entries


def _walk(destination):
    """-> ({rel: Path} regular files, [rel] symlinks) under `destination`, never following a symlink (S21-1).
    `destination` itself being a symlink is reported as "."."""
    destination = Path(destination)
    if destination.is_symlink():
        return {}, ["."]
    files, links = {}, []
    for folder, dirnames, filenames in os.walk(destination):   # followlinks=False: a linked dir is not entered
        here = Path(folder)
        for name in dirnames + filenames:
            path = here / name
            if path.is_symlink():
                links.append(path.relative_to(destination).as_posix())
            elif name in filenames and path.is_file():
                files[path.relative_to(destination).as_posix()] = path
    return files, sorted(links)


def tree_links(destination):
    """Symlinks (file or directory) in the tree, or "." if the tree path is one; [] if it does not exist."""
    return _walk(destination)[1]


def read_tree(destination):
    """The tree's regular files; a symlink is never read through (`tree_links` reports it), and a file swapped for
    a link or FIFO after the walk is skipped, never read (S23-3/S23-4)."""
    found = ((rel, _read_regular(path)) for rel, path in sorted(_walk(destination)[0].items()))
    return {rel: data for rel, data in found if data is not None}


def tree_drift(destination, root=ROOT):
    """Paths whose committed tree differs from a fresh build (empty = in sync)."""
    _, entries = unified_payload(root)
    actual = read_tree(destination)
    return sorted(set(actual) ^ set(entries) | {k for k in entries if k in actual and actual[k] != entries[k]})


def build(destination, root=ROOT):
    version, entries = unified_payload(root)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"shode-house-v{version}-team.plugin"
    # Exclusive creation fails safely rather than overwriting an earlier candidate.
    with output.open("xb") as stream:
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(entries.items()):
                item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError("archive integrity check failed")
    return {"path": str(output), "entries": len(entries),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "qualification": "structural only; see CHANGELOG for live evidence"}


def check(tree, root=ROOT):
    """`--check`: 0 = in sync and the contract holds; 1 = drift or a contract problem (one prefixed line
    each); 2 = the tree path does not exist. A source the packer cannot build, or a tree path with a `..`
    component (S23-8), raises ValueError (main: 2)."""
    shown, tree = tree, destination_path(tree)
    if not tree.is_dir():
        print(f"error: tree not found: {shown}", file=sys.stderr)
        return 2
    drift = tree_drift(tree, root)
    problems = [f"{link}: symlink in the generated tree (S21-1: a read through it can leave the plugin)"
                for link in tree_links(tree)]
    problems += [f"{link}: symlinked path component above the tree (S23-2: the tree is read from the link target)"
                 for link in linked_ancestors(tree, root)]
    problems += audit(read_tree(tree), collect(root)[1])
    for line in [f"drift: {path}" for path in drift] + [f"contract: {problem}" for problem in problems]:
        print(line)
    if drift or problems:
        return 1
    print(f"  ok {shown} in sync with source; packaging contract holds")
    return 0


def main(argv=None):
    """Exit codes: 0 ok; 1 tree drifted or breaks the packaging contract; 2 bad usage, missing tree, or a
    source/tree the packer cannot build (one `error:` line on stderr, never a traceback)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--out", type=Path, help="directory for the .plugin archive")
    mode.add_argument("--tree", type=Path, help="write the unified tree here (e.g. plugins/shode-house)")
    mode.add_argument("--check", type=Path, nargs="?", const=ROOT / "plugins/shode-house",
                      help="exit 1 if this tree (default plugins/shode-house) drifted from the source "
                           "or breaks the packaging contract")
    args = parser.parse_args(argv)
    try:
        if args.check is not None:
            return check(args.check)
        if args.tree is not None:
            version, entries = write_tree(args.tree)
            print(json.dumps({"tree": str(args.tree), "version": version, "entries": len(entries)}, indent=2))
            return 0
        destination = args.out or Path(tempfile.mkdtemp(prefix="shode-team-"))
        print(json.dumps(build(destination.resolve()), indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
