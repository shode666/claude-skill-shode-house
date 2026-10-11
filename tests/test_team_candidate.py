"""Candidate packaging invariants, not host-execution acceptance.

v4 (ADR iter 5 F-4/§5.8, addendum 1 X11, erratum 1 r1 §5.8.1/§5.8.2): the generated tree carries
agent files, skill roots and commands as the source with plugin-root and `./`/`../` references
re-pointed to its knowledge/ copy (outside floor markers only), plus a generated footer; keeps
`model:`, carries the style floor in the `ask` skill only, a pointer line in exactly the derived set
of skills, and the pinned `/ask` wrapper. Every `./`/`../` reference in the tree's Markdown resolves
(R53); agents and commands carry none, every code fence closes, and the tree holds no symlink
(v7u.4.23: S21-1..3). Every rule has a mutation test below that turns `pack.audit` (or `--check`) red.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Directories the host scans for ACTIVE registrations at a plugin root. A style
# under knowledge/ is inert data, so the three shipped shapes must agree on this set.
REGISTRATION_DIRS = ("agents", "commands", "output-styles", "skills")
# sha256 of the tree `commands/ask.md`. erratum 1 r1 (E1-1): the wrapper is NOT repointed; it keeps
# resolving to the floor-carrying tree skill `${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md`.
# Pin history (every change deliberate; the target path never changed):
# - 079932a7b933efef2391361fa558aeaa470a3f7ef4bd5c83a717f6cafc908e27: 3.17.2 (git show
#   1bc8174:plugins/shode-house/commands/ask.md).
# - da47a5ba3fcc9bd44c6dc39861911dae47e143c3b351da29dc8f09af25138de9: W2 iter 2 (shode-house-v7u.4.9), the
#   persona wording left the wrapper (A6); the description and the delegation sentence name the router and
#   agent ids.
# - fe5b3951ba31414c46c31e2bc285d6674468d24df261366b626b5bff9d6b0afe: S2 integration (v7u.4.12), Bella W2 L1
#   conditional wording keyed on "the shode-house router style" (Chris C14-4 recorded this history).
# - 71e85764d533e6b2977300acffa74701c610cd9877e8e85e065c49c6b3f64481: S2 fix-up (v7u.4.21, UD R52,
#   Bella S2 M-1): the condition names no style; it is keyed on a working delegation tool (Agent or Task),
#   as skills/workflow/ask/SKILL.md decides, so it holds at S2 and S3 alike.
# - bed0181e3f85aa03c21f4212eb87a2e05aa5639150ed31356ae551f27f01a43e (current): W7 (v7u.4.18, UD R56, erratum 1
#   §5.8.2): delegation also needs the ask skill not to report team execution unavailable; the wrapper defers to
#   the skill's style-less-session rule and still names no style.
# Any other edit of the wrapper must update this pin on purpose and add a line above.
ASK_WRAPPER_PIN = "bed0181e3f85aa03c21f4212eb87a2e05aa5639150ed31356ae551f27f01a43e"
# UD R56: the only delegation clause of the wrapper; it defers to the ask skill's decision.
ASK_DELEGATE = ("If this session has a working delegation tool (Agent or Task) and the ask skill does not report "
                "team execution unavailable, delegate")
# erratum 1 §5.8.2 (W7): the ask skill's style-less-session rule, fail-closed.
ASK_STYLELESS_RULE = ("- No shode-house output style in this session's system prompt (the router style that makes "
                      "this main session the team lead; absent on Codex, Cursor, Antigravity and on a surface "
                      "without plugin output styles; the safety-floor block in this skill's adapter is not that "
                      "style): team execution is unavailable. Never spawn or delegate shode-house roles; report "
                      "`BLOCKED: team execution needs the router style (Claude Code)`, then help in this one "
                      "session; never present it as independent review or role-play a team.")
EXECUTOR = ('- Design run (the delegation names a design-run order and its sha256): run only `python3 -I '
            '"${CLAUDE_PLUGIN_ROOT}/references/design-intel/scripts/design_run.py" --order <path> --sha256 <hash>`.\n')
EXECUTOR_TREE = '"${CLAUDE_PLUGIN_ROOT}/knowledge/references/design-intel/scripts/design_run.py"'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pack = module("pack_team", ROOT / "scripts/pack-team.py")
inventory = module("team_inventory", ROOT / "tests/test_team_package.py")


def registration_entries(paths):
    """dir -> the NAMES it registers, for any shape given as repo-relative paths.

    Names, not paths, because the three shapes lay the same registrations out
    differently: the root nests skills under buckets (skills/<bucket>/<name>/SKILL.md),
    the generated tree flattens them (skills/<name>/SKILL.md). Everything else is the
    file's basename. Comparing names is what catches "the directory is there but five
    of its six files are missing".
    """
    found = {name: set() for name in REGISTRATION_DIRS}
    for path in paths:
        parts = path.split("/")
        if parts[0] not in found:
            continue
        if parts[0] == "skills":
            if parts[-1] == "SKILL.md" and len(parts) >= 3:
                found["skills"].add(parts[-2])
        elif len(parts) == 2 and parts[1].endswith(".md"):
            found[parts[0]].add(parts[1])
    return found


def source_paths():
    """Repo-relative paths the REPO-ROOT shape registers (what every eval installs).

    `agents/`, `commands/` and `output-styles/` are the host's default scan; `skills/`
    is not scanned by default here, so the roots come from the root manifest's own
    `skills` array -- which is why skills/in-progress/ and skills/deprecated/ are not
    registrations and must not enter the comparison.
    """
    roots = [name for name in REGISTRATION_DIRS if name != "skills" and (ROOT / name).is_dir()]
    roots += [entry.strip("./") for entry in
              json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["skills"]]
    return [item.relative_to(ROOT).as_posix()
            for name in roots for item in (ROOT / name).rglob("*") if item.is_file()]


def tree_paths():
    """What the COMMITTED generated tree registers on disk (not just what the packer
    would emit), so deleting a shipped adapter fails this invariant directly."""
    tree = ROOT / "plugins/shode-house"
    return [item.relative_to(tree).as_posix() for item in tree.rglob("*") if item.is_file()]


def packed_paths():
    """What `make pack` puts in the .plugin zip, derived (never built) from
    `.pack-allowlist` -- the single source of truth for that shape, which the
    `pack build:` recipe reads (tests/test_pack_allowlist.py asserts the recipe names
    no path of its own) -- applied to the working tree, exactly as `zip -r` would walk
    it. Deterministic: this leg runs on every checkout, including in CI where the
    archive is built after the gate."""
    lines = (ROOT / ".pack-allowlist").read_text().splitlines()
    tokens = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")
              and line.strip().split("/")[0] in REGISTRATION_DIRS]
    if not tokens:
        raise RuntimeError(".pack-allowlist ships no registration directory")
    paths = []
    for token in tokens:
        item = ROOT / token
        if item.is_dir():
            paths += [child.relative_to(ROOT).as_posix() for child in item.rglob("*")
                      if child.is_file() and "__pycache__" not in child.parts
                      and child.name != ".DS_Store"]
        elif item.is_file():
            paths.append(token)
    return paths


def preloaded_on_disk():
    """Preloaded skill names, derived HERE from agents/*.md `skills:` lines (independent of the packer)."""
    names = set()
    for path in (ROOT / "agents").glob("*.md"):
        header = path.read_text().split("---", 2)[1]
        for line in header.splitlines():
            if line.startswith("skills:"):
                names |= {n.split(":", 1)[-1] for n in json.loads(line.split(":", 1)[1])}
    return names


def source_skills():
    """flat name -> (bucket, source path) for the 20 shipped skills."""
    return {p.parent.name: (p.parent.parent.name, p.relative_to(ROOT).as_posix())
            for b in pack.BUCKETS for p in (ROOT / "skills" / b).glob("*/SKILL.md")}


def terminated(data):
    text = data.decode()
    return text if text.endswith("\n") else text + "\n"


def put_body_floor(data, inner):
    """`data` (agent source bytes) with a body floor holding `inner`: replaces the existing block (W5 markers),
    else inserts one directly after the frontmatter, where floor.py's R44 grammar requires it."""
    begin, end = pack.BODY_FLOOR
    text = data.decode()
    if begin in text:
        start, stop = text.index(begin), text.index(end) + len(end) + 1
        return (text[:start] + begin + "\n" + inner + end + "\n" + text[stop:]).encode()
    header, rest = pack.frontmatter(text, "agent")
    return (header + "\n" + begin + "\n" + inner + end + "\n" + rest).encode()


class TeamCandidateTest(unittest.TestCase):
    def test_unified_tree_carries_all_four_host_manifests_and_same_knowledge(self):
        _, baseline = pack.payload()
        version, entries = pack.unified_payload()
        for path, body in baseline.items():
            if path.startswith(("knowledge/", "skills/")):
                self.assertEqual(body, entries[path], path)
        for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                     ".cursor-plugin/plugin.json", "plugin.json"):
            manifest = json.loads(entries[name])
            self.assertEqual("shode-house", manifest["name"])
            self.assertEqual(version, manifest["version"], name)
        # Cursor must not discover the Claude-dialect command; ask stays a skill there.
        self.assertEqual([], json.loads(entries[".cursor-plugin/plugin.json"])["commands"])
        self.assertIn("commands/ask.md", entries)

    # --- verbatim + footer (A7) -----------------------------------------------------------------
    def test_agent_files_are_source_verbatim_plus_footer_with_model_kept(self):
        _, entries = pack.unified_payload()
        sources = sorted((ROOT / "agents").glob("*.md"))
        self.assertEqual(sorted("agents/" + p.name for p in sources),
                         sorted(p for p in entries if p.startswith("agents/")))
        for path in sources:
            rel = "agents/" + path.name
            text = entries[rel].decode()
            self.assertEqual(pack.rewrite(terminated(path.read_bytes()), rel) + pack.AGENT_FOOTER, text, rel)
            src_model = re.findall(r"^model: *(\S+)", path.read_text().split("---", 2)[1], re.M)
            self.assertEqual(src_model, re.findall(r"^model: *(\S+)", text.split("---", 2)[1], re.M), rel)
            self.assertNotIn("model: inherit", text, rel)
            self.assertNotIn("This is a discovery adapter", text, rel)   # no 3.17 adapter left

    def test_skill_roots_are_source_verbatim_plus_footer(self):
        _, entries = pack.unified_payload()
        block = pack.style_floor_block(pack.collect()[1])
        preload = preloaded_on_disk()
        for name, (bucket, rel) in source_skills().items():
            source = terminated((ROOT / rel).read_bytes())
            footer = pack.skill_footer(bucket, name, name not in preload and name != "ask")
            tree = entries[f"skills/{name}/SKILL.md"].decode()
            if name == "ask":
                header, rest = pack.frontmatter(source, rel)
                self.assertEqual(header + "\n" + block + pack.rewrite(rest, rel) + footer, tree)
            else:
                self.assertEqual(pack.rewrite(source, rel) + footer, tree, name)
            self.assertTrue((ROOT / "skills" / bucket / name).is_dir())   # the footer's directory exists
            self.assertIn(f"knowledge/skills/{bucket}/{name}/ directory.", footer)

    def test_commands_are_source_verbatim_plus_footer_except_the_ask_wrapper(self):
        _, entries = pack.unified_payload()
        for path in sorted((ROOT / "commands").glob("*.md")):
            rel = "commands/" + path.name
            if rel == "commands/ask.md":
                continue
            self.assertEqual(pack.rewrite(terminated(path.read_bytes()), rel) + pack.COMMAND_FOOTER,
                             entries[rel].decode(), rel)

    def test_packer_output_satisfies_the_packaging_contract(self):
        _, entries = pack.unified_payload()
        self.assertEqual([], pack.audit(entries, pack.collect()[1]))

    def test_committed_plugin_tree_matches_source(self):
        tree = ROOT / "plugins/shode-house"
        self.assertTrue(tree.is_dir(), "run: python3 scripts/pack-team.py --tree plugins/shode-house")
        self.assertEqual([], pack.tree_drift(tree))
        self.assertEqual([], pack.tree_links(tree))   # S21-1
        self.assertEqual([], pack.linked_ancestors(tree))   # S23-2: `plugins` is no link
        self.assertTrue(pack.is_tree(tree))                 # S23-6: it carries the tree marker
        self.assertEqual([], pack.audit(pack.read_tree(tree), pack.collect()[1]))

    def test_all_original_knowledge_matches_source(self):
        _, entries = pack.payload()
        for name in inventory.required_paths():
            self.assertIn("knowledge/" + name, entries)
            self.assertEqual((ROOT / name).read_bytes(), entries["knowledge/" + name])

    def test_no_automatic_runtime_hooks_or_mcp(self):
        _, entries = pack.unified_payload()
        self.assertFalse(any(p.startswith(("hooks/", "scripts/")) for p in entries))
        for name in (".mcp.json", "mcp.json", "hooks.json", "mcp_config.json"):
            self.assertNotIn(name, entries)
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"):
            manifest = json.loads(entries[name])
            self.assertNotIn("hooks", manifest)
            self.assertNotIn("mcpServers", manifest)

    def test_command_sources_preserved_and_every_command_registered(self):
        # Was: "...not publicly registered" -- the tree registered /ask only while the
        # repo root (and the zip) registered all six by default scan. The authored
        # sources stay under knowledge/; the verbatim copies are what the host scans.
        _, entries = pack.payload()
        authored = sorted(path.name for path in (ROOT / "commands").glob("*.md"))
        for path in (ROOT / "commands").glob("*.md"):
            self.assertEqual(path.read_bytes(), entries["knowledge/commands/" + path.name])
        self.assertEqual(["./commands/" + name for name in authored],
                         json.loads(entries[".claude-plugin/plugin.json"])["commands"])

    def test_command_adapters_pass_the_user_argument_through(self):
        # `$ARGUMENTS` is substituted in the invoked file only, never in a file it links
        # to, so a registered command whose source takes an argument must carry it itself.
        _, entries = pack.unified_payload()
        for path in sorted(p for p in entries if p.startswith("commands/")):
            source = (ROOT / path).read_text()   # the authored command, e.g. commands/review.md
            header = source.split("---", 2)[1]
            if "$ARGUMENTS" not in source and not re.search(r"^argument-hint:", header, re.M):
                continue
            self.assertIn("$ARGUMENTS", entries[path].decode(), path)
            shipped = ROOT / "plugins/shode-house" / path
            self.assertIn("$ARGUMENTS", shipped.read_text(), str(shipped))

    def test_publishing_a_command_stays_an_explicit_decision(self):
        # The registered set is derived from commands/*.md, so without this a new command
        # file would be published with nothing objecting. PUBLISHED_COMMANDS is the gate;
        # the packer refuses a mismatch, and this pins the allowlist to what ships.
        _, entries = pack.unified_payload()
        self.assertEqual(sorted(pack.PUBLISHED_COMMANDS),
                         sorted(Path(p).stem for p in entries if p.startswith("commands/")))
        self.assertEqual(sorted(pack.PUBLISHED_COMMANDS),
                         sorted(path.stem for path in (ROOT / "commands").glob("*.md")))

    def test_versions_agree_and_every_authored_command_ships(self):
        version, entries = pack.payload()
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            self.assertEqual(version, json.loads(entries[name])["version"])
        self.assertEqual(sorted("commands/" + path.name for path in (ROOT / "commands").glob("*.md")),
                         sorted(p for p in entries if p.startswith("commands/")))
        self.assertIn("skills/ask/SKILL.md", entries)
        skills = [p for p in entries if p.startswith("skills/") and p.endswith("/SKILL.md")]
        self.assertEqual(20, len(skills))
        self.assertTrue(all(len(Path(p).parts) == 3 for p in skills))

    def test_role_set_is_the_six_types(self):
        # 4.0.1 (shode-house-jni): the 18 agent types of 4.0.0 are 6; the packer pins the set by name, so a missing,
        # extra or retired role fails the build instead of shipping.
        _, source = pack.collect()
        roles, _ = pack.roles_and_skills(source)
        self.assertEqual(sorted(pack.ROLES), sorted(Path(r).stem for r in roles))
        self.assertEqual(6, len(roles))
        dropped = {k: v for k, v in source.items() if k != "agents/build.md"}
        with self.assertRaises(ValueError):
            pack.roles_and_skills(dropped)
        revived = dict(source, **{"agents/" + "developer" + ".md": source["agents/build.md"]})   # a retired id comes back
        with self.assertRaises(ValueError):
            pack.roles_and_skills(revived)

    # --- §5.8.1: floor carrier, pointer lines, /ask wrapper -------------------------------------
    def test_ask_skill_carries_the_style_floor_byte_equal_and_nothing_else_does(self):
        _, entries = pack.unified_payload()
        style = (ROOT / pack.FLOOR_STYLE).read_text()
        begin, end = pack.STYLE_FLOOR
        block = style[style.index(begin):style.index(end) + len(end) + 1]
        ask = entries[pack.ASK_SKILL].decode()
        self.assertEqual(1, ask.count(begin))
        # directly after the frontmatter's closing line, separated by one blank line (§5.8.1 item 2)
        self.assertEqual("\n\n" + block, ask.split("---", 2)[2][:2 + len(block)])
        self.assertTrue(pack.AUTHORITY_ASK.rstrip("\n") in ask)
        self.assertNotIn(begin, (ROOT / "skills/workflow/ask/SKILL.md").read_text())   # source stays clean
        for path, body in entries.items():
            if path.startswith(("skills/", "knowledge/skills/", "commands/", "knowledge/commands/",
                                "knowledge/references/")) and path != pack.ASK_SKILL:
                self.assertNotIn(b"<!-- floor:", body, path)

    def test_no_role_preloads_ask(self):
        self.assertNotIn("ask", preloaded_on_disk())

    def test_pointer_line_sits_in_exactly_the_derived_set(self):
        # Derived from agents/*.md `skills:` lines -- NOT the literal 15: it is 14 while orchestrator
        # still preloads shode-house-workflow (Sentinel R2-1); W10 pins 15 in the switch commit.
        _, entries = pack.unified_payload()
        names = set(source_skills())
        derived = names - preloaded_on_disk() - {"ask"}
        self.assertEqual(20 - len(preloaded_on_disk() & names) - 1, len(derived))
        carrying = {Path(p).parent.name for p, body in entries.items()
                    if p.startswith("skills/") and p.endswith("/SKILL.md") and pack.POINTER.encode() in body}
        self.assertEqual(derived, carrying)
        self.assertEqual(117, len(pack.POINTER.encode()))
        for name in derived:   # placed after the authority line, last line of the file
            self.assertTrue(entries[f"skills/{name}/SKILL.md"].decode().endswith(pack.AUTHORITY + pack.POINTER))

    def test_pointer_line_ends_every_published_command_except_the_ask_wrapper(self):
        # Sentinel W2 S1: Antigravity converts commands/*.md to skills, which would otherwise carry neither
        # the floor nor the pointer. `/ask` is the entry itself and stays the pinned wrapper.
        _, entries = pack.unified_payload()
        for name in pack.PUBLISHED_COMMANDS:
            body = entries[f"commands/{name}.md"].decode()
            if name == "ask":
                self.assertNotIn(pack.POINTER, body)
            else:
                self.assertTrue(body.endswith(pack.RESOLVE + pack.POINTER), name)
                self.assertEqual(1, body.count(pack.POINTER), name)

    def test_ask_wrapper_is_pinned_and_resolves_to_the_tree_ask_skill(self):
        _, entries = pack.unified_payload()
        wrapper = entries["commands/ask.md"]
        self.assertEqual(ASK_WRAPPER_PIN, hashlib.sha256(wrapper).hexdigest())
        # UD R52 (Bella S2 M-1): keyed on a working delegation tool, never on a style the session may lack;
        # UD R56: and on the ask skill not reporting team execution unavailable.
        self.assertIn(ASK_DELEGATE.encode(), wrapper)
        self.assertIn(b"otherwise report team execution BLOCKED instead of role-playing the team.", wrapper)
        self.assertNotIn(b"style", wrapper)
        self.assertIn(b"${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md", wrapper)
        self.assertNotIn(b"knowledge/", wrapper)
        self.assertNotIn(b"Oliver", wrapper)                                  # persona-free (A6)
        self.assertNotIn(pack.POINTER.encode(), wrapper)                      # the wrapper IS the entry
        self.assertIn("skills/ask/SKILL.md", entries)
        self.assertIn(pack.STYLE_FLOOR[0].encode(), entries["skills/ask/SKILL.md"])   # it reaches the carrier

    # --- S2I-1 / UD R53: relative references ----------------------------------------------------------
    def test_relative_references_resolve_inside_the_tree(self):
        _, entries = pack.unified_payload()
        self.assertEqual([], pack._reference_problems(entries))
        ask = entries[pack.ASK_SKILL].decode()
        for ref in ("../../knowledge/skills/discipline/shode-house-discipline/SKILL.md",
                    "../../knowledge/skills/discipline/shode-house-workflow/harness.md"):
            self.assertIn("`" + ref + "`", ask)                         # the main session's first reads
            self.assertIn(posixpath.normpath(posixpath.join("skills/ask", ref)), entries)
        self.assertNotIn("`../../discipline/", ask)
        routing = entries["skills/shode-house-routing/SKILL.md"].decode()
        self.assertIn("](../../knowledge/skills/discipline/shode-house-discipline/handoff.md)", routing)
        self.assertNotIn("`../shode-house-discipline/", routing)
        self.assertNotIn("](../shode-house-discipline/", routing)
        # the knowledge/ copy stays the authored bytes (its references resolve in the source layout)
        self.assertEqual((ROOT / "skills/workflow/ask/SKILL.md").read_bytes(),
                         entries["knowledge/skills/workflow/ask/SKILL.md"])

    def test_relocation_rule(self):
        agent, skill = "agents/build.md", "skills/discipline/shode-house-routing/SKILL.md"
        self.assertEqual("see `../knowledge/references/scope-lock.md`.\n",
                         pack.relocate("see `../references/scope-lock.md`.\n", agent))
        self.assertEqual("read ../knowledge/references/a.md.\n", pack.relocate("read ../references/a.md.\n", agent))
        self.assertEqual("[h](../../knowledge/skills/discipline/shode-house-discipline/handoff.md)",
                         pack.relocate("[h](../shode-house-discipline/handoff.md)", skill))
        self.assertEqual("`../../knowledge/skills/discipline/shode-house-routing/ownership.md`",
                         pack.relocate("`./ownership.md`", skill))
        self.assertEqual("`../../knowledge/agents/`", pack.relocate("`../../../agents/`", "skills/workflow/ask/SKILL.md"))
        for kept in ("```bash\ncd ../$(PROJECT) && cat ./.gitignore ../a.md\n```\n",   # fenced: project text
                     "`../../../../x.md`",                                           # leaves the source root
                     "a/../b.md, ${X}/./c.md, ~/./d.md, ../ and ../$(PROJECT)"):     # not a reference start
            self.assertEqual(kept, pack.relocate(kept, skill))
        self.assertEqual("`../a.md`", pack.relocate("`../a.md`"))                    # no source name: no move
        # C15-3 / C15-2: `~~~` fences, and a fence that closes only on its own character and length.
        for kept in ("~~~\ncat ../a.md\n~~~\n",
                     "~~~text\n```\n../a.md\n```\n../b.md\n~~~\n",                    # ``` cannot close ~~~
                     "````md\n```bash\ncat ../a.md\n```\n../b.md\n````\n",          # ``` cannot close ````
                     "```\n../a.md\n```text\n../b.md\n```\n"):                     # a closer has no info string
            self.assertEqual(kept, pack.relocate(kept, skill))
        moved = "../../knowledge/skills/discipline/a.md"
        self.assertEqual("~~~\n../a.md\n~~~~\n" + moved + "\n", pack.relocate("~~~\n../a.md\n~~~~\n../a.md\n", skill))
        self.assertEqual("```a``` " + moved + "\n" + moved + "\n",                     # inline code, not a fence
                         pack.relocate("```a``` ../a.md\n../a.md\n", skill))
        # C23-1: the three fence rules no test pinned (Chris mutants C2, C3, C4).
        for kept in ("~~~ `x`\n../a.md\n~~~\n",                    # a backtick in the info string opens a ~~~ fence
                     "  ```\n../a.md\n  ```\n"):                   # an indented opener and closer are a fence
            self.assertEqual(kept, pack.relocate(kept, skill))
            self.assertIsNone(pack._fence_scan(kept)[1], kept)
        self.assertEqual("```\n../a.md\n```   \n" + moved + "\n",                    # a closer may end in blanks
                         pack.relocate("```\n../a.md\n```   \n../a.md\n", skill))

    def test_relocation_never_touches_a_floor_block(self):
        # C15-3 (Chris mutant M): a `../` reference between floor markers stays byte-equal; the same text after
        # the floor is relocated, so relocation is live in this file.
        skill = "skills/discipline/shode-house-routing/SKILL.md"
        block = "<!-- floor:begin -->\n## Safety floor (t)\n- see `../x.md` and ./y.md\n<!-- floor:end -->\n"
        text = "---\nname: t\n---\n\n" + block + "\nsee `../x.md`\n"
        out = pack.rewrite(text, skill)
        self.assertEqual([block], [s for f, s in pack.segments(out) if f])
        self.assertTrue(out.endswith("\nsee `../../knowledge/skills/discipline/x.md`\n"), out)

    def test_fence_scan_reports_the_line_of_a_fence_never_closed(self):
        # S21-2: an unclosed fence used to hide every later line from relocation and the reference check.
        self.assertIsNone(pack._fence_scan("a\n```\nb\n```\n")[1])
        self.assertIsNone(pack._fence_scan("~~~~\n~~~\n```\n~~~~~\n")[1])
        for text, line in (("a\n```text\n../b.md\n", 2), ("```\nx\n```\n````md\n```\n", 4),
                           ("~~~\nx\n```\n", 1), ("```\nx\n```bash\n", 1)):
            self.assertEqual(line, pack._fence_scan(text)[1], text)
            self.assertTrue(all(fenced for fenced, _ in pack._fence_scan(text)[0][line - 1:]), text)

    def test_lines_split_on_lf_only_so_cited_lines_match_the_editor(self):
        # C23-3: str.splitlines also splits on \x0c, \x85, U+2028 and a lone CR; a cited line ran ahead.
        for sep in ("\x0b", "\x0c", "\x1c", "\x85", " ", " ", "\r"):
            text = f"a{sep}b\n```\nx\n"
            self.assertEqual(2, pack._fence_scan(text)[1], repr(sep))
            self.assertEqual(text, "".join(pack._lines(text)))
        self.assertEqual(["a\r\n", "b"], pack._lines("a\r\nb"))
        self.assertEqual([], pack._lines(""))

    def test_a_list_item_or_blockquote_fence_is_named_as_the_cause_of_an_unclosed_fence(self):
        # C23-2 (Chris probe P4): `- ```` is not a fence for the packer, so its indented closer opens one that
        # never closes; the problem names the closer's line AND the list-item line as the cause.
        _, source = pack.collect()
        name = "skills/ops/slo/SKILL.md"
        body = terminated(source[name])
        line = body.count("\n") + 1
        for opener in ("- ```bash", "1. ```", "> ```"):
            closer = "  ```" if opener[0] != ">" else "```"         # a quote closed outside the quote
            mutant = body + f"{opener}\ncat x\n{closer}\n"
            with self.assertRaises(ValueError) as caught:
                pack.generate(name, mutant.encode(), source, set())
            self.assertIn(f"{name}:{line + 2}: code fence never closed", str(caught.exception), opener)
            self.assertIn(f"line {line} writes a fence after a list marker or `>`", str(caught.exception), opener)
        # an unclosed fence with no such line carries no cause clause
        self.assertEqual(f"x.md:2: {pack.UNCLOSED}", pack._unclosed_problem("x.md", *pack._fence_scan("a\n```\n")))

    # --- source-side reference checks: cited at the SOURCE file:line with the authored text (C15-2) -------
    def test_relative_reference_in_an_agent_or_command_source_is_refused_with_source_line(self):
        # S21-3: an agent system prompt / command body has no file location; `../x` would resolve from the project.
        _, source = pack.collect()
        for name in ("agents/secure.md", "commands/review.md"):
            body = terminated(source[name])
            line = body.count("\n") + 1
            # S23-1: a dotfile reference (`./.env`, `../.claude/...`) is a reference too
            for ref in ("../references/runbooks/", "./build.md", "./.env", "../.claude/settings.json"):
                with self.assertRaises(ValueError) as caught:
                    pack.generate(name, (body + f"Read `{ref}`.\n").encode(), source, set())
                self.assertIn(f"{name}:{line}: relative reference `{ref}` {pack.LOCATION_FREE_RULE}",
                              str(caught.exception))
                self.assertIn("fence a project path", str(caught.exception))
                with self.assertRaises(ValueError) as caught:                 # bare prose, sentence full stop
                    pack.generate(name, (body + f"Read {ref}.\n").encode(), source, set())
                self.assertIn(f"{name}:{line}: relative reference `{ref}` ", str(caught.exception))
            fenced = (body + "```bash\n./mvnw test && cat ../a.md\n```\n").encode()
            pack.generate(name, fenced, source, set())                     # project shell text: allowed
        # floor text is the same system prompt: refused there too (Sentinel F3b)
        agent = put_body_floor(source["agents/operate.md"], "## Safety floor (t)\n- `./build.md`\n")
        with self.assertRaisesRegex(ValueError, r"agents/operate\.md:\d+: relative reference `\./build\.md`"):
            pack.generate("agents/operate.md", agent, source, set())

    def test_project_path_in_skill_prose_is_refused_at_the_source_line(self):
        # C15-2: `./mvnw` in prose used to fail as a relocated tree reference at a tree line.
        _, source = pack.collect()
        name = "skills/ops/slo/SKILL.md"
        body = terminated(source[name])
        line = body.count("\n") + 1
        with self.assertRaises(ValueError) as caught:
            pack.generate(name, (body + "Run `./mvnw test`.\n").encode(), source, set())
        self.assertEqual(f"{name}:{line}: relative reference `./mvnw` names no shipped file from this source file; "
                         "fence a project path (e.g. `./mvnw`) in a code block", str(caught.exception))
        pack.generate(name, (body + "```bash\n./mvnw test\n```\n").encode(), source, set())
        for ref in ("../../../docs/repo-invariants/skills-agents.md", "../../../../../etc/passwd",   # M3, M4
                    "../../../../../.ssh/id_rsa", "./.env", "../../../.claude/settings.json"):           # S23-1
            with self.assertRaisesRegex(ValueError, re.escape(f"{name}:{line}: relative reference `{ref}` names no "
                                                              "shipped file")):
                pack.generate(name, (body + f"see {ref}\n").encode(), source, set())

    def test_relative_reference_pattern_takes_dotfiles_and_leaves_dot_only_segments(self):
        # S23-1: the first name after the dots may start with `.`; a segment of dots only is shell text.
        for text, refs in (("./.env", ["./.env"]), ("Read ./.env.", ["./.env."]),
                           ("../.claude/settings.json", ["../.claude/settings.json"]),
                           ("../../../../../.ssh/id_rsa", ["../../../../../.ssh/id_rsa"]),
                           ("[k](../.ssh/id_rsa)", ["../.ssh/id_rsa"]), ("../x.md", ["../x.md"]),
                           (".../y", []), ("./.../x", []), ("../..", []), ("../../", []), ("../...", []),
                           ("../.", []), ("../ and ../$(PROJECT)", []), ("a/./.env ${X}/./.env ~/./.env", [])):
            self.assertEqual(refs, [m.group(0) for m in pack.RELATIVE.finditer(text)], text)

    def test_relative_reference_pattern_takes_doubled_separators_emphasis_and_any_first_name(self):
        # S23-7: POSIX reads `..//x` as `../x`, and `_../x_` renders as an italic `../x`; S23-10: a first name may
        # start with a non-ASCII letter or punctuation. Each pair: text -> [the path each match names].
        for text, refs in (("..//.ssh/id_rsa", ["..//.ssh/id_rsa"]), (".//.env", [".//.env"]),
                           (".././/.env", [".././/.env"]), ("../../../..//.ssh/id_rsa", ["../../../..//.ssh/id_rsa"]),
                           ("..//etc/passwd", ["..//etc/passwd"]), ("..///x.md", ["..///x.md"]),
                           ("_../.claude/settings.json_", ["../.claude/settings.json"]), ("_../.env._", ["../.env"]),
                           ("see _..//.env_ now", ["..//.env"]), ("snake_../x", ["../x"]),
                           ("../ไทย.md", ["../ไทย.md"]), ("../été/x.md", ["../été/x.md"]), ("../@x", ["../@x"]),
                           ("../+x", ["../+x"]), ("./~x", ["./~x"]), ("./-x.md", ["./-x.md"]), ("./_x", ["./_x"]),
                           ("see ../x.md, then ../y.md; and ./z!", ["../x.md", "../y.md", "./z"]),
                           ("(../x.md) | ../y.md| <../z.md>", ["../x.md", "../y.md", "../z.md"]),
                           ("**./.env** `../.env` \"./.env\" '../.env'", ["./.env", "../.env", "./.env", "../.env"]),
                           # still shell text or a longer path, never a reference
                           ("../..", []), ("..//..", []), ("../...", []), (".../y", []), (".//", []), ("./,", []),
                           ("../ and ../$(PROJECT) ../{a,b} ../<x>", []), ("x-../y a/.//.env ${X}/.//.env", []),
                           ("ไทย../x", []), ("~/../x ~/./.env", []),
                           # S23-11: a GFM strikethrough wrapper hides nothing (the `~` stays on the named path)
                           ("~~../.ssh/id_rsa~~", ["../.ssh/id_rsa~~"]), ("~../.env~", ["../.env~"]),
                           ("see ~~..//.env~~ now", ["..//.env~~"])):
            self.assertEqual(refs, [pack._reference(m) for m in pack.RELATIVE.finditer(text)], text)
        # a `_` that is part of the name stays when no `_` opens the match
        self.assertEqual(["./x_"], [pack._reference(m) for m in pack.RELATIVE.finditer("./x_")])

    def test_doubled_separator_emphasis_or_any_first_name_reference_is_refused_in_every_source_kind(self):
        # S23-7 / S23-10, source side: agents and commands refuse any such reference, a skill one that names no
        # shipped file; an output style has no source-side pass, so its tree-side check (in unified_payload) is used.
        _, source = pack.collect()
        refs = (("..//.ssh/id_rsa", "..//.ssh/id_rsa"), (".//.env", ".//.env"), (".././/.env", ".././/.env"),
                ("_../.claude/settings.json_", "../.claude/settings.json"), ("../ไทย.md", "../ไทย.md"),
                ("../@x", "../@x"), ("./~x", "./~x"), ("./-x.md", "./-x.md"),
                ("~~../.ssh/id_rsa~~", "../.ssh/id_rsa~~"), ("~../.env~", "../.env~"))   # S23-11
        for name, rule in (("agents/build.md", pack.LOCATION_FREE_RULE), ("commands/review.md",
                           pack.LOCATION_FREE_RULE), ("skills/ops/slo/SKILL.md", "names no shipped file")):
            body = terminated(source[name])
            line = body.count("\n") + 1
            for written, ref in refs:
                with self.assertRaises(ValueError) as caught:
                    pack.generate(name, (body + f"Read {written} first.\n").encode(), source, set())
                self.assertIn(f"{name}:{line}: relative reference `{ref}` {rule}", str(caught.exception))
        _, entries = pack.unified_payload()
        for name in ("output-styles/shode-house.md",):  # v4 S3: output-styles/shode-house.md is deleted (rename map)
            for written, ref in refs:
                mutant = dict(entries)
                mutant[name] = (terminated(entries[name]) + f"Read {written} first.\n").encode()
                line = mutant[name].count(b"\n")
                self.assertIn(f"{name}:{line}: relative reference `{ref}` {pack.LOCATION_FREE_RULE}",
                              pack._reference_problems(mutant))

    def test_a_plugin_root_or_source_root_path_that_climbs_is_refused_in_source(self):
        # S23-9: the footer resolves a source-root path under the plugin's knowledge/, so `references/../../x` and
        # `${CLAUDE_PLUGIN_ROOT}/../x` leave the plugin. Refused in prose and in fenced code (a fenced command runs).
        _, source = pack.collect()
        paths = ("references/../../../../.ssh/id_rsa", "${CLAUDE_PLUGIN_ROOT}/../../.ssh/id_rsa",
                 "$CLAUDE_PLUGIN_ROOT/../x", "skills/../../../x", "knowledge/references//../../x",
                 "agents/../commands/review.md", "output-styles/../../x")
        for name in ("agents/build.md", "commands/review.md", "skills/ops/slo/SKILL.md"):
            body = terminated(source[name])
            line = body.count("\n") + 1
            for path in paths:
                for added, at in ((f"Read `{path}` first.\n", line), (f"```bash\ncat \"{path}\"\n```\n", line + 1)):
                    with self.assertRaises(ValueError) as caught:
                        pack.generate(name, (body + added).encode(), source, set())
                    self.assertIn(f"{name}:{at}: path `{path}` {pack.ROOTED_RULE}", str(caught.exception))
            # naming a plugin file directly, an ellipsis, or a project path that merely contains `references/`: fine
            pack.generate(name, (body + "Read `${CLAUDE_PLUGIN_ROOT}/references/runbooks/` and references/..., "
                                        "or src/references/../x.\n").encode(), source, set())

    def test_no_shipped_text_climbs_out_of_the_plugin_root(self):
        # S23-9: 0 instances today, in the source Markdown and the tree (fenced code included).
        _, source = pack.collect()
        _, entries = pack.unified_payload()
        for files in (source, entries):
            for path in sorted(p for p in files if p.endswith(".md")):
                lines = pack._lines(files[path].decode("utf-8", "replace"))
                self.assertEqual([], [p for n, line in enumerate(lines, 1) for p in pack._climbing(path, n, line)])

    def test_unclosed_fence_in_a_source_is_refused_at_the_source_line(self):
        # S21-2 (Sentinel mutant U): an unclosed fence before an escaping reference built and checked green.
        _, source = pack.collect()
        name = "skills/workflow/ask/SKILL.md"
        body = terminated(source[name])
        header, rest = pack.frontmatter(body, name)
        line = header.count("\n") + 2
        self.assertIn("../../discipline/shode-house-discipline/SKILL.md", rest)
        mutant = header + "Example:\n```text\n" + rest.replace(
            "../../discipline/shode-house-discipline/SKILL.md", "../../../discipline/shode-house-discipline/SKILL.md")
        with self.assertRaises(ValueError) as caught:
            pack.generate(name, mutant.encode(), source, set())
        self.assertIn(f"{name}:{line}: code fence never closed", str(caught.exception))

    # --- §5.8.2 host statements ---------------------------------------------------------------------
    def test_host_notes_state_option_a_and_the_corrected_antigravity_line(self):
        _, entries = pack.unified_payload()
        notes = entries["HOST-NOTES.md"].decode()
        self.assertIn("Team execution (the router style delegating to specialist agents) is supported here only.",
                      notes)
        self.assertIn("Codex, Cursor, Antigravity: skills run in one session; there is no router style.", notes)
        self.assertIn("`BLOCKED: unrouted` by design", notes)
        self.assertIn("the safety floor is in the `ask` skill", notes)
        self.assertIn("host's own command-approval and sandbox setting", notes)
        self.assertIn("Antigravity's validator (agy 1.2.2) processes the agent files", notes)
        self.assertNotIn(pack.STALE_HOST_CLAIM, notes)
        self.assertNotIn("Codex: `.claude-plugin` / `.codex-plugin` manifests, flat skills, agent adapters, "
                         "the authored commands", notes)   # 3.17 claim that Codex gets the commands (unverified)

    def test_tree_manifest_descriptions_state_option_a_within_cowork_limits(self):
        _, entries = pack.unified_payload()
        for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                     ".cursor-plugin/plugin.json", "plugin.json"):
            description = json.loads(entries[name])["description"]
            self.assertEqual(pack.TREE_DESCRIPTION, description, name)
            self.assertLessEqual(len(description), 200)
            self.assertTrue(description.isascii())
        interface = json.loads(entries[".codex-plugin/plugin.json"])["interface"]
        self.assertEqual(pack.TREE_DESCRIPTION, interface["longDescription"])
        # persona-free (A6): the Codex card names the team, not a persona
        self.assertEqual("The full software-house expert team", interface["shortDescription"])
        self.assertEqual(["Work with the Shode House team on this project."], interface["defaultPrompt"])
        for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
                     "plugin.json", "HOST-NOTES.md", "commands/ask.md"):
            self.assertNotIn(b"Oliver", entries[name], name)

    # --- F-4 rewrite and X11 ------------------------------------------------------------------------
    def test_rewrite_goes_to_knowledge_outside_the_floor_and_never_inside(self):
        floor = ("<!-- floor:begin -->\n## Safety floor (x)\n- see `${CLAUDE_PLUGIN_ROOT}/references/a.md`\n"
                 "<!-- floor:end -->\n")
        style = "<!-- floor:style:begin -->\n- `${CLAUDE_PLUGIN_ROOT}/skills/workflow/x/SKILL.md`\n<!-- floor:style:end -->\n"
        tail = ("\nread `${CLAUDE_PLUGIN_ROOT}/references/b.md`, then `${CLAUDE_PLUGIN_ROOT}/skills/ops/drain/"
                "execution.md` and `${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md`\n")
        for block in (floor, style):   # one floor per file, first after the frontmatter (floor.py, R44)
            text = "---\nname: x\n---\n\n" + block + tail
            out = pack.rewrite(text)
            self.assertIn(block, out)                                # floor bytes untouched
            self.assertIn("`${CLAUDE_PLUGIN_ROOT}/knowledge/references/b.md`", out)
            self.assertIn("`${CLAUDE_PLUGIN_ROOT}/knowledge/skills/ops/drain/execution.md`", out)
            self.assertIn("`${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md`", out)   # exists at the tree root: kept
            self.assertEqual([s for f, s in pack.segments(text) if f], [s for f, s in pack.segments(out) if f])
        with self.assertRaises(ValueError):                          # malformed floor: never guessed
            pack.rewrite("a\n<!-- floor:begin -->\nb\n")
        with self.assertRaises(ValueError):                          # ambiguous source: refused
            pack.rewrite("`${CLAUDE_PLUGIN_ROOT}/knowledge/references/a.md`\n")

    def test_floor_markers_are_parsed_with_the_floor_py_grammar(self):
        # Chris W2 S-8: the packer uses scripts/floor.py `locate()`, so where floor.py is red the packer refuses
        # (it used to accept indented, trailing-space and misplaced markers that floor.py rejects).
        floor_py = module("floor_py", ROOT / "scripts/floor.py")
        self.assertEqual((floor_py.KINDS[0].begin, floor_py.KINDS[0].end), pack.BODY_FLOOR)
        self.assertEqual((floor_py.KINDS[1].begin, floor_py.KINDS[1].end), pack.STYLE_FLOOR)
        head, block = "---\nname: x\n---\n\n", "<!-- floor:begin -->\nfloor text\n<!-- floor:end -->\n"
        good = head + block + "body\n"
        self.assertEqual([(False, head), (True, block), (False, "body\n")], pack.segments(good))
        self.assertEqual([(False, "no markers\n")], pack.segments("no markers\n"))
        for bad, why in (
                (head + "intro line\n" + block, "first non-blank line after the frontmatter"),   # R44
                (head + "  " + block, "whole line"),                                            # indented
                (head + block.replace("begin -->", "begin -->  "), "whole line"),               # trailing spaces
                (head + block + block, "exactly one marker pair"),                              # two pairs
                (head + block.replace("<!-- floor:end -->\n", ""), "exactly one marker pair"),  # unclosed
                (head + block + "<!-- floor:style:end -->\n", "wrong floor"),                    # mixed kinds
                (head + block.replace("\n", "\r\n"), "CRLF")):
            with self.assertRaises(ValueError) as caught:
                pack.segments(bad, "agents/x.md")
            self.assertIn(why, str(caught.exception))
            self.assertIn("agents/x.md", str(caught.exception))

    def test_every_root_file_needs_frontmatter(self):
        # Chris W2 S-7: the 3.17 packer refused a role or skill without frontmatter; so does generate().
        _, source = pack.collect()
        for name in ("skills/ops/slo/SKILL.md", "agents/build.md", "commands/review.md"):
            with self.assertRaises(ValueError) as caught:
                pack.generate(name, b"no frontmatter here\n", source, set())
            self.assertIn(f"missing frontmatter: {name}", str(caught.exception))

    def test_preloads_are_read_fail_closed(self):
        # Sentinel W2 S2: only the JSON-style quoted single-line list is understood; valid-YAML forms the host
        # would also preload (`[ask, x]`, a block list) are refused instead of silently read as "no ask".
        _, source = pack.collect()
        self.assertEqual(preloaded_on_disk(), pack.preloaded(source))   # the packer agrees with json.loads
        quoted = 'skills: ["shode-house:shode-house-discipline"'   # v4 W5b: preloads are namespaced
        self.assertIn(quoted.encode(), source["agents/build.md"])
        for bad in ('skills: [ask, shode-house-discipline', 'skills:\n  - ask\n  - "shode-house-discipline"\n#'):
            trial = dict(source)
            trial["agents/build.md"] = source["agents/build.md"].replace(quoted.encode(), bad.encode(), 1)
            with self.assertRaises(ValueError) as caught:
                pack.preloaded(trial)
            self.assertIn("agents/build.md: `skills:` must be a JSON-style quoted single-line list",
                          str(caught.exception))

    def test_footer_wording_is_pinned_literally(self):
        # Chris W2 S-9: literal text, so a wording change cannot ride along with a regeneration.
        resolve = ("Resolve source-root paths beginning agents/, skills/, references/, commands/ or output-styles/ "
                   "under this plugin's knowledge/ directory, not the user's project.\n")
        pointer = ("No shode-house safety floor in this context (a main session without the router style)? "
                   "Load `shode-house:ask` first.\n")
        self.assertEqual(resolve, pack.RESOLVE)
        self.assertEqual("Use actual host tools and preserve host/project/user authority.\n", pack.AUTHORITY)
        self.assertEqual("Use actual host tools and preserve host/project/user authority, except R0 and the rest "
                         "of the safety floor above.\n", pack.AUTHORITY_ASK)
        self.assertEqual(pointer, pack.POINTER)
        self.assertEqual("\n" + resolve, pack.AGENT_FOOTER)
        self.assertEqual("\n" + resolve + pointer, pack.COMMAND_FOOTER)
        # R53 (v7u.4.21): `./`/`../` paths are relocated in the body, so the footer sends only bare names to the
        # bucket directory (reading `../../knowledge/...` from there would break it again).
        relative = ("Resolve paths beginning ./ or ../ from this file's own directory; resolve other relative "
                    "file names in this skill under this plugin's ")
        self.assertEqual("\n" + resolve + relative + "knowledge/skills/ops/slo/ directory.\n" + pack.AUTHORITY + pointer,
                         pack.skill_footer("ops", "slo", True))
        self.assertEqual("\n" + resolve + relative + "knowledge/skills/workflow/ask/ directory.\n" + pack.AUTHORITY_ASK,
                         pack.skill_footer("workflow", "ask", False))

    def test_executor_path_is_rewritten_root_anchored_to_an_existing_tree_file(self):
        # X11 (addendum 1 §5.5.3): the generated executor line names the knowledge/ copy, quoted and
        # anchored at "${CLAUDE_PLUGIN_ROOT}/; a relative path would execute a same-named project file.
        out = pack.rewrite(EXECUTOR)
        self.assertIn(EXECUTOR_TREE, out)
        entries = {"knowledge/references/design-intel/scripts/design_run.py": b""}
        self.assertEqual([], pack._script_problems("agents/build.md", out, entries))

    # --- style --------------------------------------------------------------------------------------
    def test_generated_tree_carries_the_output_styles_verbatim_at_the_top_level(self):
        # A style cannot be an adapter: the file IS the main-session system prompt,
        # and the host only scans <plugin root>/output-styles/.
        # Packer output only (Chris W2 S-12); the committed copy is the next test.
        _, entries = pack.unified_payload()
        styles = sorted((ROOT / "output-styles").glob("*.md"))
        self.assertIn(pack.FLOOR_STYLE, ["output-styles/" + p.name for p in styles])
        self.assertEqual(sorted("output-styles/" + p.name for p in styles),
                         sorted(p for p in entries if p.startswith("output-styles/")))
        for path in styles:
            rel = "output-styles/" + path.name
            self.assertEqual(path.read_bytes(), entries[rel], rel)

    def test_committed_tree_carries_the_output_styles_verbatim(self):
        # On-disk half of the test above: red only while plugins/shode-house is stale (regenerate it).
        for path in sorted((ROOT / "output-styles").glob("*.md")):
            rel = "output-styles/" + path.name
            committed = ROOT / "plugins/shode-house" / rel
            self.assertTrue(committed.is_file(), f"{committed}: run: python3 scripts/pack-team.py --tree "
                                                 "plugins/shode-house")
            self.assertEqual(path.read_bytes(), committed.read_bytes(),
                             "run: python3 scripts/pack-team.py --tree plugins/shode-house")

    def test_exactly_one_top_level_output_style_is_forced(self):
        _, entries = pack.unified_payload()
        forced = []
        for rel in (p for p in entries if p.startswith("output-styles/")):
            parts = entries[rel].decode().split("---", 2)
            self.assertEqual("", parts[0], rel)
            self.assertRegex(parts[1], re.compile(r"^name: \S", re.M))
            if re.search(r"^force-for-plugin: true$", parts[1], re.M):
                forced.append(rel)
        self.assertEqual(1, len(forced), forced)

    def test_generated_manifests_leave_the_output_style_discoverable(self):
        # The activation contract, not just the absence of a key: either a manifest
        # declares no `outputStyles` (AGENTS.md -- the field REPLACES the default scan)
        # and the style then has to sit at the default path, or it declares one that
        # explicitly re-includes `./output-styles/`. Both legs must hold together, so
        # this fails on a tree that has neither the key nor the default directory.
        _, entries = pack.unified_payload()
        for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                     ".cursor-plugin/plugin.json", "plugin.json"):
            declared = json.loads(entries[name]).get("outputStyles")
            if declared is None:
                self.assertTrue(any(path.startswith("output-styles/") for path in entries),
                                f"{name}: no outputStyles key AND no default output-styles/ -- "
                                "the host would scan nothing")
            else:
                self.assertIn("./output-styles/", declared if isinstance(declared, list) else [declared])

    def test_active_registration_entries_agree_in_root_tree_and_zip(self):
        # Per-DIRECTORY, per-ENTRY: a shape that keeps the directory but drops entries
        # (the marketplace tree registered 1 of 6 commands) must fail here.
        version, entries = pack.unified_payload()
        source = registration_entries(source_paths())
        self.assertTrue(all(source[name] for name in REGISTRATION_DIRS), source)
        self.assertEqual(source, registration_entries(entries), "generated tree (packer output)")
        self.assertEqual(source, registration_entries(tree_paths()), "generated tree (on disk)")
        self.assertEqual(source, registration_entries(packed_paths()), "make pack zip")
        archive = ROOT / f"shode-house-v{version}.plugin"
        if archive.is_file():  # cross-check the real artifact when one was already built
            with zipfile.ZipFile(archive) as built:
                self.assertEqual(source, registration_entries(built.namelist()), str(archive))

    def test_reproducible_and_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix="shode-pack-test-") as first:
            with tempfile.TemporaryDirectory(prefix="shode-pack-test-") as second:
                one = pack.build(Path(first))
                two = pack.build(Path(second))
                self.assertEqual(one["sha256"], two["sha256"])
                before = Path(one["path"]).read_bytes()
                with self.assertRaises(FileExistsError):
                    pack.build(Path(first))
                self.assertEqual(before, Path(one["path"]).read_bytes())
                with zipfile.ZipFile(one["path"]) as archive:
                    self.assertIsNone(archive.testzip())


class PackagingContractMutationTest(unittest.TestCase):
    """Each rule of `pack.audit` goes red on a one-rule mutation of a good tree."""

    @classmethod
    def setUpClass(cls):
        _, cls.entries = pack.unified_payload()
        cls.source = pack.collect()[1]
        cls.preload = pack.preloaded(cls.source)

    def red(self, entries, needle, source=None):
        problems = pack.audit(entries, self.source if source is None else source)
        self.assertTrue(any(needle in p for p in problems), f"expected '{needle}' in {problems}")

    def edit(self, path, old, new, entries=None):
        entries = dict(self.entries if entries is None else entries)
        text = entries[path].decode()
        self.assertIn(old, text, path)
        entries[path] = text.replace(old, new, 1).encode()
        return entries

    def test_baseline_is_green(self):
        self.assertEqual([], pack.audit(self.entries, self.source))

    def test_model_inherit_is_red(self):
        model = re.search(r"^model: .*$", self.entries["agents/build.md"].decode(), re.M).group(0)
        self.red(self.edit("agents/build.md", model, "model: inherit"), "agents/build.md: `model:` not kept")

    def test_three_line_adapter_instead_of_verbatim_body_is_red(self):
        entries = dict(self.entries)
        header = entries["agents/verify.md"].decode().split("---", 2)[1]
        entries["agents/verify.md"] = ("---" + header + "---\n\nRead [verify](../knowledge/agents/"
                                            "verify.md) in full.\n" + pack.AGENT_FOOTER).encode()
        # "differs from its source" today; "floor marker layout differs" once the body carries floor markers
        self.red(entries, "agents/verify.md: ")

    def test_missing_footer_is_red(self):
        self.red(self.edit("commands/review.md", pack.COMMAND_FOOTER, "\n"), "commands/review.md: does not end")

    def test_changed_body_text_is_red(self):
        text = self.entries["skills/dev-gate/SKILL.md"].decode()
        word = re.search(r"\b[a-z]{6,}\b", text.split("---", 2)[2]).group(0)
        self.red(self.edit("skills/dev-gate/SKILL.md", word, word.upper()), "skills/dev-gate/SKILL.md")

    def test_rewrite_inside_the_floor_is_red(self):
        # A source whose floor names a rewritable path: the packer keeps it, a tree that rewrote it is red.
        source = dict(self.source)
        floor = ("<!-- floor:begin -->\n## Safety floor (t)\n- `${CLAUDE_PLUGIN_ROOT}/references/x.md`\n"
                 "<!-- floor:end -->\n")
        source["agents/build.md"] = put_body_floor(source["agents/build.md"],
                                                       "## Safety floor (t)\n- `${CLAUDE_PLUGIN_ROOT}/references/x.md`\n")
        entries = dict(self.entries)
        good = pack.generate("agents/build.md", source["agents/build.md"], source, set())
        self.assertIn(floor, good)
        entries["agents/build.md"] = good.encode()
        self.assertEqual([], pack.audit(entries, source))
        bad = good.replace("${CLAUDE_PLUGIN_ROOT}/references/x.md", "${CLAUDE_PLUGIN_ROOT}/knowledge/references/x.md")
        entries["agents/build.md"] = bad.encode()
        self.red(entries, "floor bytes differ from source", source)

    def test_unrewritten_and_unanchored_executor_paths_are_red(self):
        source = dict(self.source)
        source["agents/verify.md"] = source["agents/verify.md"] + EXECUTOR.encode()
        entries = dict(self.entries)
        entries["knowledge/references/design-intel/scripts/design_run.py"] = b"#"
        good = pack.generate("agents/verify.md", source["agents/verify.md"], source, set())
        self.assertIn(EXECUTOR_TREE, good)
        entries["agents/verify.md"] = good.encode()
        self.assertEqual([], pack.audit(entries, source))
        for bad, needle in (
                (good.replace(EXECUTOR_TREE, '"${CLAUDE_PLUGIN_ROOT}/references/design-intel/scripts/design_run.py"'),
                 "not rewritten"),
                (good.replace(EXECUTOR_TREE, '"knowledge/references/design-intel/scripts/design_run.py"'),
                 "not root-anchored"),
                (good.replace(EXECUTOR_TREE, "${CLAUDE_PLUGIN_ROOT}/knowledge/references/design-intel/scripts/"
                                             "design_run.py"), "not root-anchored")):
            entries["agents/verify.md"] = bad.encode()
            self.red(entries, needle, source)
        entries["agents/verify.md"] = good.encode()
        del entries["knowledge/references/design-intel/scripts/design_run.py"]
        self.red(entries, "does not resolve to a file in the tree", source)

    def test_style_block_copied_into_the_discipline_skill_is_red(self):
        block = pack.style_floor_block(self.source)
        entries = self.edit("skills/shode-house-discipline/SKILL.md", "\n# ", "\n" + block + "\n# ")
        self.red(entries, "skills/shode-house-discipline/SKILL.md: carries a floor block outside")

    def test_ask_without_or_with_a_changed_block_is_red(self):
        block = pack.style_floor_block(self.source)
        self.red(self.edit(pack.ASK_SKILL, block, ""), "style floor block is not directly after")
        self.red(self.edit(pack.ASK_SKILL, block, block.replace("floor:style:end", "floor:style:end ")),
                 pack.ASK_SKILL)

    def test_ask_authority_line_without_the_floor_exception_is_red(self):
        self.red(self.edit(pack.ASK_SKILL, pack.AUTHORITY_ASK, pack.AUTHORITY), "does not end with its generated")

    def test_pointer_line_in_a_preloaded_skill_or_missing_from_a_derived_one_is_red(self):
        preloaded = sorted(self.preload & {Path(p).parent.name for p in self.entries if p.startswith("skills/")})[0]
        path = f"skills/{preloaded}/SKILL.md"
        self.red(self.edit(path, pack.AUTHORITY, pack.AUTHORITY + pack.POINTER), f"{path}: pointer line present")
        self.red(self.edit("skills/diagnose/SKILL.md", pack.POINTER, ""), "skills/diagnose/SKILL.md: pointer line missing")
        self.red(self.edit(pack.ASK_SKILL, pack.AUTHORITY_ASK, pack.AUTHORITY_ASK + pack.POINTER),
                 f"{pack.ASK_SKILL}: pointer line present")

    def test_a_role_preloading_ask_is_red(self):
        source = dict(self.source)
        source["agents/build.md"] = source["agents/build.md"].replace(
            b'skills: ["shode-house:shode-house-discipline"', b'skills: ["shode-house:ask", "shode-house:shode-house-discipline"', 1)
        self.assertNotEqual(source["agents/build.md"], self.source["agents/build.md"])
        self.red(self.entries, "a role preloads `ask`", source)

    def test_ask_wrapper_repointed_to_knowledge_is_red(self):
        entries = self.edit("commands/ask.md", "${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md",
                            "${CLAUDE_PLUGIN_ROOT}/knowledge/skills/workflow/ask/SKILL.md")
        self.red(entries, "commands/ask.md: must resolve to")
        self.red(self.edit("commands/ask.md", "otherwise report team execution BLOCKED instead of role-playing the team",
                           "otherwise act as the team"),
                 "commands/ask.md: the /ask wrapper changed")
        condition = ASK_DELEGATE
        for mutant in ("Delegate",                                                  # condition dropped
                       "If this session has the shode-house router style, delegate",  # keyed on a style (M-1)
                       "If this session has the Oliver style, delegate",              # a persona style
                       "If this session has a delegation tool, delegate",             # tool not required working
                       "If this session has a working delegation tool (Agent or Task), delegate"):  # R56 deferral dropped
            self.red(self.edit("commands/ask.md", condition, mutant), "commands/ask.md: the /ask wrapper changed")

    def test_style_less_session_with_agent_gets_blocked_from_the_skill_and_no_contradicting_delegate(self):
        # UD R56 + erratum 1 §5.8.2: a session that has Agent but no router style. The ask skill (source and the
        # tree adapter /ask resolves to) reports team execution unavailable and BLOCKED; the wrapper's only
        # "delegate" sits behind the deferral to that report, and its else-branch is BLOCKED, never "delegate".
        _, entries = pack.unified_payload()
        source_skill = (ROOT / "skills/workflow/ask/SKILL.md").read_text()
        tree_skill = entries["skills/ask/SKILL.md"].decode()
        for skill in (source_skill, tree_skill):
            self.assertEqual(1, skill.count(ASK_STYLELESS_RULE))
        wrapper = entries["commands/ask.md"].decode()
        self.assertEqual(1, wrapper.lower().count("delegate"), "one delegation clause only")
        before, _, after = wrapper.partition("delegate specialist work")
        self.assertTrue(before.endswith(ASK_DELEGATE[:-len("delegate")]), "the delegation clause must follow the R56 deferral")
        self.assertIn("the ask skill does not report team execution unavailable", before)
        self.assertIn("; otherwise report team execution BLOCKED instead of role-playing the team.", after)
        self.assertNotIn("delegate", after.split("; otherwise", 1)[1])

    def test_stale_host_notes_or_description_is_red(self):
        self.red(self.edit("HOST-NOTES.md", "Antigravity's validator (agy 1.2.2) processes the agent files",
                           pack.STALE_HOST_CLAIM), "HOST-NOTES.md")
        self.red(self.edit("HOST-NOTES.md", "No automatic", pack.STALE_HOST_CLAIM + ". No automatic"),
                 "Antigravity 'skills only' claim")
        self.red(self.edit("plugin.json", "skills-only, single session", "instruction-only"), "plugin.json: description")
        self.red(self.edit("HOST-NOTES.md", "keep approval on for shell and MCP actions", "approval is optional"),
                 "host bullets are missing or changed")
        self.red(self.edit("HOST-NOTES.md", "is supported here only.", "is supported on every host."),
                 "host bullets are missing or changed")

    def test_over_rewritten_plugin_root_path_is_red(self):
        # Chris W2 S-1: the old lossy inverse (knowledge/ -> plugin root) accepted a tree that also moved
        # paths the tree keeps at its root (skills/ask/, agents/) to knowledge/, where skills/ask/ does not exist.
        source = dict(self.source)
        line = ("See `${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md`, `${CLAUDE_PLUGIN_ROOT}/agents/verify.md` "
                "and `${CLAUDE_PLUGIN_ROOT}/references/scope-lock.md`.\n")
        source["agents/build.md"] = source["agents/build.md"] + line.encode()
        good = pack.generate("agents/build.md", source["agents/build.md"], source, set())
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/knowledge/references/scope-lock.md`", good)
        entries = dict(self.entries)
        entries["agents/build.md"] = good.encode()
        self.assertEqual([], pack.audit(entries, source))
        for wrong in ("skills/ask/SKILL.md", "agents/verify.md"):
            entries["agents/build.md"] = good.replace("${CLAUDE_PLUGIN_ROOT}/" + wrong,
                                                          "${CLAUDE_PLUGIN_ROOT}/knowledge/" + wrong).encode()
            self.red(entries, "agents/build.md: rewrites a plugin-root path outside the F-4 set", source)

    def test_source_ask_skill_carrying_the_style_floor_is_red(self):
        # Chris W2 S-3 (M14): the carrier is the generated tree skill only; a source copy would reach it twice.
        block = pack.style_floor_block(self.source)
        source = dict(self.source)
        header, rest = pack.frontmatter(source["skills/workflow/ask/SKILL.md"].decode(), "ask")
        source["skills/workflow/ask/SKILL.md"] = (header + "\n" + block + rest).encode()
        self.red(self.entries, "skills/workflow/ask/SKILL.md: the source ask skill carries the style floor", source)

    def test_style_source_without_exactly_one_style_pair_is_red(self):
        # Chris W2 S-3 (M10): two pairs (refused by floor.py's grammar) and none both name the style file.
        style = self.source[pack.FLOOR_STYLE].decode()
        block = pack.style_floor_block(self.source)
        for text, needle in ((style + "\n" + block, f"{pack.FLOOR_STYLE}: malformed floor markers (needs exactly one"),
                             (style.replace(block, ""), f"{pack.FLOOR_STYLE} needs exactly one style floor marker "
                                                        "pair (found 0)")):
            source = dict(self.source)
            source[pack.FLOOR_STYLE] = text.encode()
            self.red(self.entries, needle, source)

    def test_unquoted_or_block_list_preload_of_ask_is_red(self):
        # Sentinel W2 S2: `skills: [ask, x]` is valid YAML the host preloads; it must not read as "no ask".
        for bad in (b'skills: [ask, shode-house-discipline', b'skills:\n  - ask\n  - "shode-house-discipline"\n#'):
            source = dict(self.source)
            source["agents/build.md"] = source["agents/build.md"].replace(
                b'skills: ["shode-house:shode-house-discipline"', bad, 1)   # v4 W5b: preloads are namespaced
            self.assertNotEqual(source["agents/build.md"], self.source["agents/build.md"])
            self.red(self.entries, "agents/build.md: `skills:` must be a JSON-style quoted", source)

    def test_command_without_the_pointer_or_ask_wrapper_with_it_is_red(self):
        # Sentinel W2 S1.
        self.red(self.edit("commands/review.md", pack.POINTER, ""), "commands/review.md: pointer line missing")
        self.red(self.edit("commands/ask.md", "instead of role-playing the team.\n",
                           "instead of role-playing the team.\n" + pack.POINTER), "commands/ask.md: pointer line present")

    @staticmethod
    def line_of(entries, path, needle):
        return next(n for n, line in enumerate(entries[path].decode().splitlines(), 1) if needle in line)

    def test_unrelocated_relative_reference_is_red_with_file_and_line(self):
        # S2I-1 / UD R53: the 3.17-adapter-era text (source path, unresolvable from skills/ask/) must not pass.
        stale = "../../discipline/shode-house-discipline/SKILL.md"
        entries = self.edit(pack.ASK_SKILL, "../../knowledge/skills/discipline/shode-house-discipline/SKILL.md", stale)
        problems = pack.audit(entries, self.source)
        line = self.line_of(entries, pack.ASK_SKILL, stale)
        self.assertIn(f"{pack.ASK_SKILL}:{line}: relative reference `{stale}` does not resolve inside the tree "
                      "(fence a project path)", problems)
        self.assertIn(f"{pack.ASK_SKILL}: a ./ or ../ reference is not the source reference relocated to its "
                      "knowledge/ copy (R53)", problems)

    def test_relocated_reference_to_another_existing_file_is_red(self):
        # Resolves, but not to the file the source names: the forward comparison catches it.
        entries = self.edit("skills/shode-house-routing/SKILL.md",
                            "../../knowledge/skills/discipline/shode-house-discipline/handoff.md",
                            "../../knowledge/skills/discipline/shode-house-discipline/SKILL.md")
        self.assertEqual([], pack._reference_problems(entries))
        self.red(entries, "skills/shode-house-routing/SKILL.md: a ./ or ../ reference is not the source reference")

    def test_broken_or_escaping_reference_anywhere_in_the_tree_markdown_is_red(self):
        path = "knowledge/skills/discipline/shode-house-routing/SKILL.md"
        entries = self.edit(path, "../shode-house-discipline/handoff.md", "../shode-house-discipline/nope.md")
        self.red(entries, f"{path}:{self.line_of(entries, path, 'nope.md')}: relative reference "
                          "`../shode-house-discipline/nope.md` does not resolve")
        entries = self.edit("HOST-NOTES.md", "No automatic", "See ../outside.md. No automatic")
        self.red(entries, f"HOST-NOTES.md:{self.line_of(entries, 'HOST-NOTES.md', 'outside.md')}: relative "
                          "reference `../outside.md` does not resolve")

    def test_reference_in_fenced_code_is_not_checked_but_the_same_text_outside_is(self):
        fenced = self.edit("HOST-NOTES.md", "No automatic", "```\ncat ../outside.md\n```\nNo automatic")
        self.assertEqual([], pack._reference_problems(fenced))
        bare = self.edit("HOST-NOTES.md", "No automatic", "cat ../outside.md\nNo automatic")
        self.assertEqual(1, len(pack._reference_problems(bare)))

    def test_unclosed_fence_in_the_tree_is_red_with_file_and_line(self):
        # S21-2 (Sentinel mutant U, tree side): the fence and the escaping reference after it are both reported.
        entries = self.edit(pack.ASK_SKILL, "../../knowledge/skills/discipline/shode-house-discipline/SKILL.md",
                            "../../../discipline/shode-house-discipline/SKILL.md")
        clean = pack._reference_problems(entries)
        self.assertTrue(any("../../../discipline/" in p for p in clean), clean)
        lines = entries[pack.ASK_SKILL].decode().splitlines(keepends=True)
        line = self.line_of(entries, pack.ASK_SKILL, "../../../discipline/")    # the fence opens on this line
        lines.insert(line - 1, "```text-s21\n")
        entries[pack.ASK_SKILL] = "".join(lines).encode()
        problems = pack._reference_problems(entries)
        self.assertIn(f"{pack.ASK_SKILL}:{line}: {pack.UNCLOSED}", problems)
        self.red(entries, f"{pack.ASK_SKILL}:{line}: code fence never closed")
        # a knowledge/ file is checked too, and a shorter or other-character closer does not close
        path = "knowledge/skills/discipline/shode-house-routing/SKILL.md"
        for opener in ("````md\n```\n", "~~~\n```\n"):
            self.red(self.edit(path, "\n# ", "\n" + opener + "# "), f"{path}:")
            self.assertTrue(any(p.startswith(path) and "code fence never closed" in p
                                for p in pack._reference_problems(self.edit(path, "\n# ", "\n" + opener + "# "))))

    def test_relative_reference_in_a_tree_agent_or_command_is_red_even_when_it_resolves(self):
        # S21-3 (Sentinel mutant): `../knowledge/agents/build.md` resolves from agents/, but an agent system
        # prompt or a command body has no file location, so the host would resolve it from the project.
        for path, ref in (("agents/secure.md", "../knowledge/agents/build.md"),
                          ("commands/review.md", "../knowledge/references/runbooks/")):
            footer = pack.AGENT_FOOTER if path.startswith("agents/") else pack.COMMAND_FOOTER
            entries = self.edit(path, footer, f"\nRead `{ref}`.\n" + footer)
            line = self.line_of(entries, path, ref)
            self.red(entries, f"{path}:{line}: relative reference `{ref}` {pack.LOCATION_FREE_RULE}")
        fenced = self.edit("commands/review.md", pack.COMMAND_FOOTER, "\n```bash\n./mvnw test\n```\n" + pack.COMMAND_FOOTER)
        self.assertEqual([], pack._reference_problems(fenced))
        # the knowledge/ copy is read as a file, so a resolving reference there is fine
        knowledge = self.edit("knowledge/agents/secure.md", "\n## ", "\nsee ./build.md\n## ")
        self.assertEqual([], pack._reference_problems(knowledge))

    def test_dotfile_reference_in_the_tree_is_red(self):
        # S23-1 (Sentinel e2e): `./.env` in an agent or command, and an escaping `.ssh` reference in a skill or a
        # knowledge/ copy, passed --tree and --check.
        for path, ref in (("agents/build.md", "./.env"), ("commands/review.md", "./.env"),
                          ("agents/build.md", "../.claude/settings.json")):
            footer = pack.AGENT_FOOTER if path.startswith("agents/") else pack.COMMAND_FOOTER
            entries = self.edit(path, footer, f"\nRead {ref} first.\n" + footer)
            self.red(entries, f"{path}:{self.line_of(entries, path, ref)}: relative reference `{ref}` "
                              f"{pack.LOCATION_FREE_RULE}")
        for path in ("skills/slo/SKILL.md", "knowledge/skills/ops/slo/SKILL.md"):
            ref = "../../../../../.ssh/id_rsa"
            entries = self.edit(path, "\n# ", f"\nRead {ref}.\n# ")
            self.red(entries, f"{path}:{self.line_of(entries, path, ref)}: relative reference `{ref}` does not "
                              "resolve inside the tree")

    def test_relative_reference_in_an_output_style_is_red_even_when_it_resolves(self):
        # R59: an output style is the main-session system prompt, with no file location (same class as S21-3).
        for path in ("output-styles/shode-house.md",):  # v4 S3: output-styles/shode-house.md is deleted (rename map)
            for ref in ("../agents/build.md", "../knowledge/agents/build.md", "./shode-house.md",
                        "../.claude/settings.json"):
                entries = dict(self.entries)
                entries[path] = entries[path] + f"\nRead {ref} first.\n".encode()
                self.red(entries, f"{path}:{self.line_of(entries, path, ref)}: relative reference `{ref}` "
                                  f"{pack.LOCATION_FREE_RULE}")
            fenced = dict(self.entries)
            fenced[path] = fenced[path] + b"\n```bash\n./mvnw test\n```\n"
            self.assertEqual([], pack._reference_problems(fenced))
        # the knowledge/ copy is inert data read as a file: a resolving reference there is fine
        knowledge = dict(self.entries)
        knowledge["knowledge/output-styles/shode-house.md"] += b"\nsee ./shode-house.md\n"
        self.assertEqual([], pack._reference_problems(knowledge))

    def append(self, path, added):
        """`added` as the last authored line of tree file `path` (before a generated footer) -> (entries, line)."""
        footer = next((f for f in (pack.AGENT_FOOTER, pack.COMMAND_FOOTER) if path.split("/")[0] in ("agents",
                       "commands") and self.entries[path].decode().endswith(f)), None)
        if footer is not None:
            entries = self.edit(path, footer, "\n" + added + footer)
        elif path.startswith("skills/"):
            entries = self.edit(path, "\n# ", "\n" + added + "# ")
        else:
            entries = dict(self.entries)
            entries[path] = (terminated(entries[path]) + added).encode()
        return entries, self.line_of(entries, path, added.rstrip("\n").splitlines()[-1])

    def test_doubled_separator_or_emphasis_reference_in_the_tree_is_red(self):
        # S23-7 / S23-10 (Sentinel r2 e2e), S23-11 (r3 e2e): these spellings passed --tree and --check in an agent,
        # a command, a skill and a style.
        cases = (("..//.ssh/id_rsa", "..//.ssh/id_rsa"), (".//.env", ".//.env"), (".././/.env", ".././/.env"),
                 ("_../.claude/settings.json_", "../.claude/settings.json"), ("..//agents/build.md",
                 "..//agents/build.md"), ("../ไทย.md", "../ไทย.md"), ("../@x", "../@x"), ("./~x", "./~x"),
                 ("./-x.md", "./-x.md"), ("~~../.ssh/id_rsa~~", "../.ssh/id_rsa~~"), ("~../.env~", "../.env~"),
                 ("~~..//agents/build.md~~", "..//agents/build.md~~"))   # S23-11 (Sentinel r3 e2e)
        for path in ("agents/build.md", "commands/review.md", "output-styles/shode-house.md"):
            for written, ref in cases:
                entries, line = self.append(path, f"Read {written} before routing.\n")
                self.red(entries, f"{path}:{line}: relative reference `{ref}` {pack.LOCATION_FREE_RULE}")
        for path in ("skills/slo/SKILL.md", "knowledge/skills/ops/slo/SKILL.md"):
            for written, ref in cases:
                if written.startswith("..//agents"):
                    continue                                    # may resolve from a skill; the location rule is moot
                entries, line = self.append(path, f"Read ../../../..//.ssh/id_rsa and {written} before acting.\n")
                self.red(entries, f"{path}:{line}: relative reference `../../../..//.ssh/id_rsa` does not resolve")
                self.red(entries, f"{path}:{line}: relative reference `{ref}` does not resolve inside the tree")

    def test_plugin_root_or_source_root_path_that_climbs_is_red_anywhere_in_the_tree(self):
        # S23-9: an agent, command, skill root, style and a knowledge/ reference document, in prose or fenced code.
        paths = ("references/../../../../.ssh/id_rsa", "${CLAUDE_PLUGIN_ROOT}/../../.ssh/id_rsa",
                 "${CLAUDE_PLUGIN_ROOT}/knowledge/references/../../../x", "knowledge/skills/../../x")
        for path in ("agents/build.md", "commands/review.md", "skills/slo/SKILL.md", "output-styles/shode-house.md",
                     "knowledge/references/runbooks/resolve-merge-conflicts.md"):
            for climbing in paths:
                for added in (f"Read `{climbing}` first.\n", f"```bash\ncat \"{climbing}\"\n```\n"):
                    entries, _ = self.append(path, added)
                    line = self.line_of(entries, path, climbing)
                    self.red(entries, f"{path}:{line}: path `{climbing}` {pack.ROOTED_RULE}")

    def test_damaged_tree_frontmatter_is_reported_not_raised(self):
        # Chris W2 S-5: one damaged file is a problem line; the other problems are still reported.
        entries = self.edit("agents/build.md", "---\n", "--- \n")
        entries = self.edit("commands/review.md", pack.COMMAND_FOOTER, "\n", entries)
        problems = pack.audit(entries, self.source)
        self.assertTrue(any(p.startswith("agents/build.md: ") for p in problems), problems)
        self.assertTrue(any(p.startswith("commands/review.md: does not end") for p in problems), problems)


def tree_snapshot(folder):
    """{relative posix path: bytes} of every regular file under `folder` (C23R4-1: one helper for the race tests)."""
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def source_copy(root):
    """A copied source root (the packer's inputs and the packer itself) under `root`; -> its packer script."""
    for name in ("agents", "references", "output-styles", "commands", "skills", ".claude-plugin"):
        shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "scripts").mkdir()
    for name in ("LICENSE", "scripts/pack-team.py", "scripts/floor.py"):
        shutil.copy2(ROOT / name, root / name)
    return root / "scripts/pack-team.py"


class CheckCommandLineTest(unittest.TestCase):
    """`pack-team.py --check` as CI #25 runs it: exit codes and messages (Chris W2 S-2, S-5, S-11)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="shode-pack-cli-")
        cls.tree = Path(cls.tmp.name) / "tree"
        pack.write_tree(cls.tree)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_cli(self, *args, script=ROOT / "scripts/pack-team.py"):
        return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                              timeout=300)

    def test_in_sync_tree_exits_0(self):
        result = self.run_cli("--check", self.tree)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("in sync with source; packaging contract holds", result.stdout)

    def test_one_byte_drift_exits_1_and_names_the_path(self):
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree = Path(tmp) / "tree"
            pack.write_tree(tree)
            target = tree / "commands/review.md"
            target.write_bytes(target.read_bytes() + b" ")
            result = self.run_cli("--check", tree)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("drift: commands/review.md\n", result.stdout)
        self.assertIn("contract: commands/review.md: does not end with its generated footer", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_unresolved_relative_reference_exits_1_with_file_and_line(self):
        # S2I-1 / UD R53 mutant: one reference left unrelocated in the generated routing skill.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree = Path(tmp) / "tree"
            pack.write_tree(tree)
            target = tree / "skills/shode-house-routing/SKILL.md"
            text = target.read_text()
            moved = "../../knowledge/skills/discipline/shode-house-discipline/handoff.md"
            line = next(n for n, row in enumerate(text.splitlines(), 1) if moved in row)
            target.write_text(text.replace(moved, "../shode-house-discipline/handoff.md", 1))
            result = self.run_cli("--check", tree)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn(f"contract: skills/shode-house-routing/SKILL.md:{line}: relative reference "
                      "`../shode-house-discipline/handoff.md` does not resolve inside the tree (fence a project path)\n",
                      result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    # --- S21-1: symlinks are never read or written through -----------------------------------------------
    def test_symlinked_tree_file_or_directory_exits_1(self):
        # Sentinel S2/S2b/S3: a file (absolute or escaping relative link) or a directory linked outside the tree.
        rel = "knowledge/skills/discipline/shode-house-discipline/SKILL.md"
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree, outside = Path(tmp) / "tree", Path(tmp) / "outside-SKILL.md"
            pack.write_tree(tree)
            outside.write_bytes((tree / rel).read_bytes())                 # identical bytes: no drift by content
            for link_to in (outside, Path("../../../../../outside-SKILL.md")):
                (tree / rel).unlink()
                (tree / rel).symlink_to(link_to)
                self.assertEqual((tree / rel).read_bytes(), outside.read_bytes())
                self.assertNotIn(rel, pack.read_tree(tree))                # never read through
                self.assertEqual([rel], pack.tree_links(tree))
                result = self.run_cli("--check", tree)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn(f"drift: {rel}\n", result.stdout)
                self.assertIn(f"contract: {rel}: symlink in the generated tree", result.stdout)
            (tree / rel).unlink()
            folder = tree / "knowledge/skills/discipline/shode-house-discipline"
            shutil.move(str(folder), str(Path(tmp) / "moved"))
            folder.symlink_to(Path(tmp) / "moved", target_is_directory=True)
            (Path(tmp) / "moved" / "SKILL.md").write_bytes(outside.read_bytes())
            result = self.run_cli("--check", tree)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("contract: knowledge/skills/discipline/shode-house-discipline: symlink in the generated tree",
                      result.stdout)

    def test_tree_write_never_goes_through_a_symlink(self):
        # Sentinel S21-1 write-through: `--tree` overwrote the link target outside the tree.
        rel = "knowledge/skills/discipline/shode-house-discipline/SKILL.md"
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree, victim = Path(tmp) / "tree", Path(tmp) / "victim.md"
            pack.write_tree(tree)
            victim.write_bytes(b"victim original\n")
            (tree / rel).unlink()
            (tree / rel).symlink_to(victim)
            with self.assertRaisesRegex(ValueError, "refusing to write through symlink"):
                pack.write_tree(tree)
            result = self.run_cli("--tree", tree)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn(f"refusing to write through symlink(s) in the tree: {rel}", result.stderr)
            self.assertEqual(b"victim original\n", victim.read_bytes())
            self.assertTrue((tree / rel).is_symlink())
            linked = Path(tmp) / "linked-tree"                             # the tree path itself is a link
            linked.symlink_to(tree, target_is_directory=True)
            (tree / rel).unlink()
            with self.assertRaisesRegex(ValueError, r"refusing to write through symlink\(s\) in the tree: \."):
                pack.write_tree(linked)
            self.assertEqual(["."], pack.tree_links(linked))

    def test_source_reference_problem_exits_2_citing_the_source_file_and_line(self):
        # C15-2: `--check` against a bad SOURCE names the authored file, line and reference, not a tree line.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            root = Path(tmp)
            script = source_copy(root)
            agent = root / "agents/build.md"
            text = agent.read_text()
            line = text.count("\n") + 1
            agent.write_text(text + "Run `./mvnw test`.\n")
            (root / "plugins/shode-house").mkdir(parents=True)
            result = self.run_cli("--check", root / "plugins/shode-house", script=script)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertTrue(result.stderr.startswith(f"error: agents/build.md:{line}: relative reference `./mvnw` "
                                                 + pack.LOCATION_FREE_RULE), result.stderr)

    def test_dotfile_or_output_style_reference_in_the_source_fails_tree_and_check(self):
        # S23-1 + R59 end to end (Sentinel scratchpad/s23/e2e): each mutant source used to give --tree rc=0 and
        # --check rc=0; now neither builds, and nothing is written.
        mutants = (("agents/build.md", "Read ./.env and ../.claude/settings.json first.\n",
                    "agents/build.md:{line}: relative reference `./.env` "),
                   ("commands/review.md", "Read ./.env first.\n", "commands/review.md:{line}: relative reference "
                                                                  "`./.env` "),
                   ("skills/ops/slo/SKILL.md", "Read ../../../../../.ssh/id_rsa before acting.\n",
                    "skills/ops/slo/SKILL.md:{line}: relative reference `../../../../../.ssh/id_rsa` names no "
                    "shipped file"),
                   ("output-styles/shode-house.md", "Read ../agents/build.md before routing.\n",
                    "output-styles/shode-house.md:{line}: relative reference `../agents/build.md` "
                    + pack.LOCATION_FREE_RULE),
                   # S23-7 (Sentinel r2 scratchpad/s23b/e2e, verbatim): doubled separators and `_` emphasis
                   ("agents/build.md", "Read ..//.ssh/id_rsa and .//.env first.\n",
                    "agents/build.md:{line}: relative reference `..//.ssh/id_rsa` " + pack.LOCATION_FREE_RULE),
                   ("commands/review.md", "See _../.claude/settings.json_ before routing.\n",
                    "commands/review.md:{line}: relative reference `../.claude/settings.json` "
                    + pack.LOCATION_FREE_RULE),
                   ("skills/ops/slo/SKILL.md", "Read ../../../..//.ssh/id_rsa and .././/.env before acting.\n",
                    "skills/ops/slo/SKILL.md:{line}: relative reference `../../../..//.ssh/id_rsa` names no shipped"),
                   ("output-styles/shode-house.md", "Read ..//agents/build.md before routing.\n",
                    "output-styles/shode-house.md:{line}: relative reference `..//agents/build.md` "
                    + pack.LOCATION_FREE_RULE),
                   # S23-11 (Sentinel r3 scratchpad/s23c/e2e, verbatim): a `~~` strikethrough wrapper
                   ("agents/build.md", "Read ~~../.ssh/id_rsa~~ first.\n",
                    "agents/build.md:{line}: relative reference `../.ssh/id_rsa~~` " + pack.LOCATION_FREE_RULE),
                   # S23-10: a first name starting with a non-ASCII letter
                   ("skills/ops/slo/SKILL.md", "Read ../ไทย.md first.\n",
                    "skills/ops/slo/SKILL.md:{line}: relative reference `../ไทย.md` names no shipped file"),
                   # S23-9: a plugin-root or source-root path that climbs, in prose or fenced, in any shipped Markdown
                   ("agents/build.md", "Read `references/../../../../.ssh/id_rsa` first.\n",
                    "agents/build.md:{line}: path `references/../../../../.ssh/id_rsa` " + pack.ROOTED_RULE),
                   ("references/runbooks/resolve-merge-conflicts.md",
                    "Run `cat \"${CLAUDE_PLUGIN_ROOT}/../../.ssh/id_rsa\"`.\n",
                    "knowledge/references/runbooks/resolve-merge-conflicts.md:{line}: path "
                    "`${CLAUDE_PLUGIN_ROOT}/../../.ssh/id_rsa` " + pack.ROOTED_RULE),
                   ("output-styles/shode-house.md", "```bash\ncat skills/../../x\n```\n",
                    "output-styles/shode-house.md:{next}: path `skills/../../x` " + pack.ROOTED_RULE))
        for name, added, needle in mutants:
            with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
                root = Path(tmp)
                script = source_copy(root)
                text = (root / name).read_text()
                text += "" if text.endswith("\n") else "\n"
                line = text.count("\n") + 1
                (root / name).write_text(text + added)
                tree = root / "plugins/shode-house"
                written = self.run_cli("--tree", tree, script=script)
                self.assertFalse(tree.exists(), name)
                tree.mkdir(parents=True)
                checked = self.run_cli("--check", tree, script=script)
            for result in (written, checked):
                self.assertEqual(2, result.returncode, name + result.stdout + result.stderr)
                self.assertIn(needle.replace("{line}", str(line)).replace("{next}", str(line + 1)), result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    # --- S23-2 / S23-3 / S23-4 / S23-6: where --tree may write and delete -----------------------------------
    def test_symlinked_path_component_above_the_tree_is_refused(self):
        # S23-2: `plugins` -> elsewhere sent --tree (and its stale-file deletion) into the link target, and --check
        # read the target and gave rc=0.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tmp = Path(tmp).resolve()                    # the CLI's ROOT is resolved (/var -> /private/var on macOS)
            root, elsewhere = tmp / "repo", tmp / "elsewhere"
            root.mkdir()
            script = source_copy(root)
            pack.write_tree(elsewhere / "shode-house")                     # a real tree: only S23-2 can refuse
            precious = elsewhere / "shode-house/precious.txt"
            precious.write_bytes(b"keep\n")
            (root / "plugins").symlink_to(elsewhere, target_is_directory=True)
            tree = root / "plugins/shode-house"
            self.assertEqual(["plugins"], pack.linked_ancestors(tree, root))
            with self.assertRaisesRegex(ValueError, "symlinked path component: plugins"):
                pack.write_tree(tree, root)
            result = self.run_cli("--tree", tree, script=script)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("refusing to write through a symlinked path component: plugins", result.stderr)
            self.assertEqual(b"keep\n", precious.read_bytes())
            precious.unlink()
            result = self.run_cli("--check", tree, script=script)
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("contract: plugins: symlinked path component above the tree", result.stdout)
            self.assertEqual([], pack.linked_ancestors(elsewhere / "shode-house", root))   # outside the repo

    def test_a_tree_path_spelled_through_a_symlinked_ancestor_of_the_repo_is_still_refused(self):
        # C23R2-1: the repo was located by spelling (`relative_to` the resolved ROOT), so `/tmp/...` for
        # `/private/tmp/...`, or any linked directory above the repo, put the tree "outside the repo": --tree wrote
        # into the link target of `plugins` and deleted a stray file there, and --check dropped the S23-2 line.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            real = Path(tmp).resolve()
            root, elsewhere = real / "repo", real / "elsewhere"
            root.mkdir()
            script = source_copy(root)
            pack.write_tree(elsewhere / "shode-house")                     # a real tree: only S23-2 can refuse
            (elsewhere / "shode-house/precious.txt").write_bytes(b"keep\n")
            (root / "plugins").symlink_to(elsewhere, target_is_directory=True)
            (real / "alias").symlink_to(real, target_is_directory=True)  # a symlinked parent directory of the repo
            spellings = [real / "alias/repo"]
            for system in ("/tmp", "/var"):                              # the unresolved system spelling (macOS)
                target = Path(os.path.realpath(system))
                if Path(system).is_symlink() and real.is_relative_to(target):
                    spellings.append(Path(system) / real.relative_to(target) / "repo")
            before = tree_snapshot(elsewhere)
            for repo in spellings:
                self.assertNotEqual(root, repo)
                self.assertTrue(os.path.samefile(repo, root), repo)
                for leaf in ("shode-house", "fresh"):                   # an existing tree, and a new directory
                    tree = repo / "plugins" / leaf
                    self.assertEqual(["plugins"], pack.linked_ancestors(tree, root), tree)
                    with self.assertRaisesRegex(ValueError, "symlinked path component: plugins"):
                        pack.write_tree(tree, root)
                    written = self.run_cli("--tree", tree, script=script)
                    self.assertEqual(2, written.returncode, written.stdout + written.stderr)
                    self.assertIn("refusing to write through a symlinked path component: plugins (S23-2",
                                  written.stderr)
                    self.assertEqual(before, tree_snapshot(elsewhere), tree)    # nothing written, nothing deleted
                    self.assertFalse((elsewhere / "fresh").exists(), tree)
                tree = repo / "plugins/shode-house"
                checked = self.run_cli("--check", tree, script=script)      # the same contract failure as --tree
                self.assertEqual(1, checked.returncode, checked.stdout + checked.stderr)
                self.assertIn("contract: plugins: symlinked path component above the tree (S23-2", checked.stdout)
                self.assertEqual(before, tree_snapshot(elsewhere), tree)
            self.assertEqual(["plugins"], pack.linked_ancestors(real / "alias/repo/plugins/shode-house",
                                                                real / "alias/repo"))   # root spelled through a link

    def test_a_link_inside_the_repo_back_to_the_repo_is_still_a_linked_component(self):
        # C23R3-2 (R5): the repo is the shortest ancestor of the destination that is the repo. Searched longest
        # first, `repo/loop -> repo` itself matched the repo, `loop` vanished from the components and went unreported.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            (root / "loop").symlink_to(root, target_is_directory=True)
            for tree in (root / "loop/x", root / "loop/plugins/shode-house"):
                self.assertEqual(["loop"], pack.linked_ancestors(tree, root), tree)
            with self.assertRaisesRegex(ValueError, "symlinked path component: loop"):
                pack.write_tree(root / "loop/shode-house", root)
            self.assertEqual(["loop"], sorted(p.name for p in root.iterdir()))   # nothing written

    def test_a_case_variant_spelling_of_the_repo_is_still_under_it(self):
        # C23R3-2 (R6): on a case-insensitive filesystem `REPO` names `Repo`, but no spelling comparison (not even of
        # resolved paths: realpath keeps the letter case) sees it; only the directory identity (samefile) does.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            real = Path(tmp).resolve()
            root, elsewhere = real / "Repo", real / "elsewhere"
            root.mkdir()
            variant = real / "REPO"
            if not variant.exists():
                self.skipTest("case-sensitive filesystem: a case variant names another directory")
            self.assertNotEqual(str(root), str(variant.resolve()))         # the spelling survives resolve()
            pack.write_tree(elsewhere / "shode-house")                     # a real tree: only S23-2 can refuse
            (elsewhere / "shode-house/precious.txt").write_bytes(b"keep\n")
            (root / "plugins").symlink_to(elsewhere, target_is_directory=True)
            tree = variant / "plugins/shode-house"
            self.assertEqual(["plugins"], pack.linked_ancestors(tree, root))
            with self.assertRaisesRegex(ValueError, "symlinked path component: plugins"):
                pack.write_tree(tree, root)
            self.assertEqual(b"keep\n", (elsewhere / "shode-house/precious.txt").read_bytes())

    def test_tree_refuses_a_directory_that_is_not_a_shode_house_tree(self):
        # S23-6 (data loss): --tree deleted every non-entry file of whatever directory it was pointed at.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            work = Path(tmp) / "work"
            work.mkdir()
            stray = work / "notes.txt"
            stray.write_bytes(b"untracked work\n")
            (work / "sub").mkdir()
            (work / "sub/draft.md").write_bytes(b"draft\n")
            with self.assertRaisesRegex(ValueError, "not empty and not a shode-house tree"):
                pack.write_tree(work)
            result = self.run_cli("--tree", work)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("not a shode-house tree", result.stderr)
            self.assertEqual(b"untracked work\n", stray.read_bytes())
            self.assertEqual(b"draft\n", (work / "sub/draft.md").read_bytes())
            self.assertEqual(sorted(["notes.txt", "sub"]), sorted(p.name for p in work.iterdir()))   # nothing written
            # half a marker is not a tree: another plugin's manifest, or ours without the host notes
            (work / ".claude-plugin").mkdir()
            for manifest, notes in (({"name": "other"}, b"# Shode House 1.0.0 host notes\n"),
                                    ({"name": "shode-house"}, None), ({"name": "shode-house"}, b"# Other\n")):
                (work / ".claude-plugin/plugin.json").write_text(json.dumps(manifest))
                if notes is None:
                    (work / "HOST-NOTES.md").unlink(missing_ok=True)
                else:
                    (work / "HOST-NOTES.md").write_bytes(notes)
                self.assertFalse(pack.is_tree(work), (manifest, notes))
                self.assertEqual(2, self.run_cli("--tree", work).returncode)
                self.assertEqual(b"untracked work\n", stray.read_bytes())
            plain = Path(tmp) / "a-file"
            plain.write_bytes(b"x\n")
            self.assertFalse(pack.is_tree(plain))
            self.assertEqual(2, self.run_cli("--tree", plain).returncode)
            self.assertEqual(b"x\n", plain.read_bytes())
            empty = Path(tmp) / "empty"                                    # new or empty: a fresh tree is written
            empty.mkdir()
            pack.write_tree(empty)
            self.assertEqual(0, self.run_cli("--check", empty).returncode)
            (empty / "stale.md").write_bytes(b"old\n")                      # an existing tree: stale files go
            pack.write_tree(empty)
            self.assertFalse((empty / "stale.md").exists())

    def test_a_tree_path_through_a_symlink_and_dot_dot_cannot_bypass_the_tree_marker(self):
        # S23-8: `<link>/../data` was checked where the OS resolves it (the link target's sibling, absent: "a fresh
        # tree") but written and cleaned where a lexical normalisation puts it (`data`, a non-tree dir), wiping it.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tmp = Path(tmp).resolve()                    # the CLI's ROOT is resolved (/var -> /private/var on macOS)
            root, other = tmp / "repo", tmp / "other"
            root.mkdir()
            (other / "a").mkdir(parents=True)
            script = source_copy(root)
            for base in (tmp / "bp", root / "plugins"):                   # outside the repo, and under it via the CLI
                data = base / "data"
                data.mkdir(parents=True)
                (data / "precious.txt").write_bytes(b"keep\n")
                (data / "notes.md").write_bytes(b"notes\n")
                (base / "x").symlink_to(other / "a", target_is_directory=True)
                dest = base / "x/../data"
                with self.assertRaisesRegex(ValueError, r"refusing a tree path with a `\.\.` component \(S23-8"):
                    pack.write_tree(dest, root)
                with self.assertRaisesRegex(ValueError, "S23-8"):
                    pack.check(dest, root)
                for args in (("--tree", dest), ("--check", dest), ("--tree", "plugins/x/../data")):
                    result = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                                            text=True, timeout=300, cwd=root)
                    self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                    self.assertIn("refusing a tree path with a `..` component (S23-8", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(sorted(["notes.md", "precious.txt"]), sorted(p.name for p in data.iterdir()))
                self.assertEqual(b"keep\n", (data / "precious.txt").read_bytes())
                self.assertEqual([], list((other).glob("data")) + list((other / "a").iterdir()))
            # the same directory named directly is still refused by the marker (S23-6), so `..` was the only bypass
            result = self.run_cli("--tree", root / "plugins/data", script=script)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("not a shode-house tree", result.stderr)
            # `.` and doubled separators normalise to one path, and the checks run on it
            self.assertEqual(pack.destination_path(tmp / "bp/./data"), pack.destination_path(f"{tmp}//bp//data"))
            self.assertEqual(tmp / "bp/data", pack.destination_path(tmp / "bp/./data"))
            # one absolute path for every check, write and delete (a relative argument is taken from the cwd once)
            self.assertEqual(Path.cwd() / "plugins/shode-house", pack.destination_path("plugins/shode-house"))

    def test_tree_write_never_follows_a_link_planted_after_the_check(self):
        # S23-3: a link planted between tree_links() and the writes was written through (victim overwritten).
        rel = "knowledge/skills/discipline/shode-house-discipline/SKILL.md"
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree, victim = Path(tmp) / "tree", Path(tmp) / "victim.md"
            victim_dir = Path(tmp) / "victim-dir"
            pack.write_tree(tree)
            victim.write_bytes(b"victim\n")
            victim_dir.mkdir()
            (victim_dir / "important.txt").write_bytes(b"important\n")
            original = pack.unified_payload

            def plant_file_link(root=pack.ROOT):
                result = original(root)
                (tree / rel).unlink()
                (tree / rel).symlink_to(victim)                            # at an entry path
                (tree / "extra-dir").symlink_to(victim_dir, target_is_directory=True)   # at a non-entry path
                return result

            with mock.patch.object(pack, "unified_payload", plant_file_link):
                pack.write_tree(tree)
            self.assertEqual(b"victim\n", victim.read_bytes())
            self.assertFalse((tree / rel).is_symlink())
            self.assertEqual(pack.unified_payload()[1][rel], (tree / rel).read_bytes())
            self.assertEqual(b"important\n", (victim_dir / "important.txt").read_bytes())
            (tree / "extra-dir").unlink()
            moved = Path(tmp) / "moved-commands"

            def plant_dir_link(root=pack.ROOT):
                result = original(root)
                shutil.move(str(tree / "commands"), str(moved))
                (moved / "review.md").write_bytes(b"victim review\n")
                (tree / "commands").symlink_to(moved, target_is_directory=True)   # a parent of entries
                return result

            with mock.patch.object(pack, "unified_payload", plant_dir_link):
                with self.assertRaisesRegex(ValueError, "'commands' is not a plain directory"):
                    pack.write_tree(tree)
            self.assertEqual(b"victim review\n", (moved / "review.md").read_bytes())
            self.assertTrue((moved / "consult.md").is_file())

    def test_a_tree_swapped_for_a_link_to_the_repo_after_the_checks_is_refused(self):
        # C23R3-1 (data loss): the identity walk also compared the tree directory itself, so a tree outside the repo
        # replaced by a link to the repo after the checks "was" the repo: the tree was written into the repo root
        # and the stale cleanup deleted the repo's other files. The tree directory itself is never followed.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            real = Path(tmp).resolve()
            root, tree = real / "repo", real / "out/shode-house"
            root.mkdir()
            source_copy(root)                                              # a repo-like directory, inside tmp only
            (root / "victim.txt").write_bytes(b"repo file\n")
            pack.write_tree(tree, root)
            before, names = tree_snapshot(root), sorted(os.listdir(root))
            original = pack.unified_payload

            def swap_tree_for_repo_link(source=pack.ROOT):
                result = original(source)
                shutil.rmtree(tree)
                tree.symlink_to(root, target_is_directory=True)
                return result

            with mock.patch.object(pack, "unified_payload", swap_tree_for_repo_link):
                with self.assertRaisesRegex(ValueError, "'shode-house' is not a plain directory"):
                    pack.write_tree(tree, root)
            self.assertTrue(tree.is_symlink())
            self.assertEqual(names, sorted(os.listdir(root)))              # no HOST-NOTES.md / tree entry written
            self.assertEqual(before, tree_snapshot(root))                  # nothing overwritten, nothing deleted
            self.assertIsNone(pack._parts_under_root(tree, root))          # the leaf is never matched through a link

    def test_a_linked_parent_planted_after_the_check_is_refused_when_the_repo_is_spelled_through_a_link(self):
        # C23R3-2 (R4): S23-3 for a tree under the repo spelled through a linked ancestor of the repo (an alias, or
        # `/tmp` for `/private/tmp`). Found by spelling, the open took it for "outside the repo" and followed a
        # `plugins` link planted after the checks into its target, writing there and deleting a stray file.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            real = Path(tmp).resolve()
            root, elsewhere = real / "repo", real / "elsewhere"
            root.mkdir()
            source_copy(root)
            pack.write_tree(elsewhere / "shode-house")                     # a real tree in the link target
            (elsewhere / "shode-house/precious.txt").write_bytes(b"keep\n")
            (real / "alias").symlink_to(real, target_is_directory=True)
            spellings = [real / "alias/repo"]
            for system in ("/tmp", "/var"):                              # the unresolved system spelling (macOS)
                target = Path(os.path.realpath(system))
                if Path(system).is_symlink() and real.is_relative_to(target):
                    spellings.append(Path(system) / real.relative_to(target) / "repo")
            before = tree_snapshot(elsewhere)
            original = pack.unified_payload

            def plant_plugins_link(source=pack.ROOT):
                result = original(source)
                (root / "plugins").rmdir()
                (root / "plugins").symlink_to(elsewhere, target_is_directory=True)
                return result

            for repo in spellings:
                self.assertNotEqual(root, repo)
                if (root / "plugins").is_symlink():
                    (root / "plugins").unlink()
                (root / "plugins").mkdir()                                 # a plain directory when checked
                tree = repo / "plugins/shode-house"
                self.assertEqual([], pack.linked_ancestors(tree, root), tree)
                with mock.patch.object(pack, "unified_payload", plant_plugins_link):
                    with self.assertRaisesRegex(ValueError, "'plugins' is not a plain directory"):
                        pack.write_tree(tree, root)
                self.assertTrue((root / "plugins").is_symlink(), tree)
                self.assertEqual(before, tree_snapshot(elsewhere), tree)   # nothing written, nothing deleted

    def test_an_ancestor_swapped_after_the_checks_is_refused_on_the_opened_directory(self):
        # S23-16 (data loss; Sentinel r5 P1/P2): outside the repo the destination's parent is opened following links,
        # so `out/x` swapped after the checks for a link to the repo's parent (leaf `repo`: P1) or to the repo (leaf
        # `plugins/shode-house`: P2) sent the writes and the stale cleanup into the repo. The S23-6 decision is now
        # re-made on the opened directory: the directory checked, still empty or still marked, or nothing happens.
        with tempfile.TemporaryDirectory(prefix="shode-pack-race-") as tmp:
            real = Path(tmp).resolve()
            lab = real / "a/b"
            root = lab / "repo"
            root.mkdir(parents=True)
            source_copy(root)                                              # a repo-like directory, inside tmp only
            (root / "victim.txt").write_bytes(b"repo file\n")
            pack.write_tree(root / "plugins/shode-house", root)            # a real tree: its marker re-check passes
            (root / "plugins/shode-house/stray.txt").write_bytes(b"uncommitted\n")
            before, names = tree_snapshot(lab), sorted(os.listdir(root))
            original = pack.unified_payload
            parent = real / "out/x"

            def swap_parent(link_to):
                def swap(source=pack.ROOT):
                    result = original(source)
                    shutil.rmtree(parent)
                    parent.symlink_to(link_to, target_is_directory=True)
                    return result
                return swap

            rows = (("P1 tree", parent / "repo", lab, "tree"),
                    ("P2 tree", parent / "plugins/shode-house", root, "tree"),
                    ("P1 fresh", parent / "repo", lab, "absent"),
                    ("P2 fresh", parent / "plugins/shode-house", root, "absent"),
                    ("P1 empty", parent / "repo", lab, "empty"),
                    ("P2 empty", parent / "plugins/shode-house", root, "empty"))
            for row, tree, link_to, state in rows:
                for via_main in (False, True):
                    if parent.is_symlink():
                        parent.unlink()
                    shutil.rmtree(real / "out", ignore_errors=True)
                    if state == "tree":
                        pack.write_tree(tree, root)
                    elif state == "empty":
                        tree.mkdir(parents=True)
                    else:
                        tree.parent.mkdir(parents=True)
                    self.assertIsNone(pack._parts_under_root(tree, root), row)   # the outside branch is taken
                    with mock.patch.object(pack, "unified_payload", swap_parent(link_to)):
                        if via_main:                                       # the CLI path: exit 2, one error line
                            err = io.StringIO()
                            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                                self.assertEqual(2, pack.main(["--tree", str(tree)]), row)
                            self.assertIn("(S23-16", err.getvalue(), row)
                        else:
                            with self.assertRaisesRegex(ValueError, r"refusing to write: the opened tree directory "
                                                                    r".* \(S23-16"):
                                pack.write_tree(tree, root)
                    self.assertTrue(parent.is_symlink(), row)              # the swap happened
                    self.assertEqual(names, sorted(os.listdir(root)), row)  # no HOST-NOTES.md in the repo root
                    self.assertEqual(before, tree_snapshot(lab), row)       # nothing written, nothing deleted
            # an existing destination is never made again through a swapped parent: the open fails, nothing is made
            parent.unlink()
            (parent / "gone").mkdir(parents=True)
            with mock.patch.object(pack, "unified_payload", swap_parent(lab)):
                with self.assertRaisesRegex(ValueError, "'gone' is not a plain directory"):
                    pack.write_tree(parent / "gone", root)
            self.assertFalse(os.path.lexists(lab / "gone"))
            # the same directory, its marker removed after the checks: the marker is re-read on the opened fd
            tree = real / "plain/shode-house"
            pack.write_tree(tree, root)
            (tree / "keep.txt").write_bytes(b"keep\n")

            def unmark(source=pack.ROOT):
                result = original(source)
                (tree / "HOST-NOTES.md").unlink()
                return result

            with mock.patch.object(pack, "unified_payload", unmark):
                with self.assertRaisesRegex(ValueError, r"no longer carries the shode-house marker .*\(S23-16"):
                    pack.write_tree(tree, root)
            self.assertEqual(b"keep\n", (tree / "keep.txt").read_bytes())
            self.assertFalse((tree / "HOST-NOTES.md").exists())
            # no race: a new, an empty and an existing (marked again) tree outside the repo are still written
            (tree / "HOST-NOTES.md").write_bytes(pack.unified_payload(root)[1]["HOST-NOTES.md"])
            (real / "empty").mkdir()
            for tree in (real / "new/deep/shode-house", real / "empty", tree):
                pack.write_tree(tree, root)
                self.assertEqual([], pack.tree_drift(tree, root), tree)
            self.assertFalse((tree / "keep.txt").exists())                  # an existing tree: strays still go

    def test_a_relative_tree_from_a_cwd_reached_through_an_in_repo_link_is_refused(self):
        # S23-15: `cd repo/plugins` (a link to `elsewhere`) then `--tree shode-house`: getcwd() is the physical
        # `elsewhere`, so the run was taken for an outside destination and deleted `elsewhere/shode-house` strays.
        # The logical spelling ($PWD, used only when it names the cwd) is checked for S23-2 as well.
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            real = Path(tmp).resolve()
            root, elsewhere = real / "repo", real / "elsewhere"
            root.mkdir()
            script = source_copy(root)
            pack.write_tree(elsewhere / "shode-house")                     # a real tree: only S23-2 can refuse
            (elsewhere / "shode-house/precious.txt").write_bytes(b"keep\n")
            (root / "plugins").symlink_to(elsewhere, target_is_directory=True)
            before = tree_snapshot(elsewhere)

            def run(pwd):
                env = {k: v for k, v in os.environ.items() if k != "PWD"}
                if pwd is not None:
                    env["PWD"] = str(pwd)
                return subprocess.run([sys.executable, str(script), "--tree", "shode-house"], capture_output=True,
                                      text=True, timeout=300, cwd=elsewhere, env=env)

            for pwd in (root / "plugins", real / "alias/repo/plugins", f"{root}/plugins/."):
                if "alias" in str(pwd) and not (real / "alias").exists():
                    (real / "alias").symlink_to(real, target_is_directory=True)
                result = run(pwd)
                self.assertEqual(2, result.returncode, f"{pwd}: {result.stdout}{result.stderr}")
                self.assertIn("refusing to write through a symlinked path component: plugins", result.stderr)
                self.assertIn("S23-15", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(before, tree_snapshot(elsewhere), pwd)      # nothing written, nothing deleted
            with mock.patch.dict(os.environ, {"PWD": str(root / "plugins")}):
                with mock.patch.object(os, "getcwd", return_value=str(elsewhere)):
                    self.assertEqual(root / "plugins/shode-house", pack.logical_spelling("shode-house"))
                    self.assertIsNone(pack.logical_spelling(elsewhere / "shode-house"))   # absolute: no cwd involved
            # $PWD is used only when it names the cwd: a stale, relative or `..` spelling is ignored, and without
            # it the run is the by-design outside destination (S23-6 accepts a real tree; strays are cleaned)
            for pwd in (root, Path("repo/plugins"), f"{root}/plugins/../elsewhere"):   # the last one names the cwd
                with mock.patch.dict(os.environ, {"PWD": str(pwd)}):
                    with mock.patch.object(os, "getcwd", return_value=str(elsewhere)):
                        self.assertIsNone(pack.logical_spelling("shode-house"), pwd)
            result = run(elsewhere)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse((elsewhere / "shode-house/precious.txt").exists())

    def test_tree_write_replaces_a_hardlink_or_fifo_instead_of_writing_through_it(self):
        # S23-4: a hardlinked tree file overwrote its other name; a FIFO at an entry path hung --tree.
        rel = "commands/review.md"
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            tree, victim = Path(tmp) / "tree", Path(tmp) / "hard-victim.md"
            pack.write_tree(tree)
            want = (tree / rel).read_bytes()
            victim.write_bytes(b"hard victim\n")
            (tree / rel).unlink()
            os.link(victim, tree / rel)
            result = self.run_cli("--tree", tree)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(b"hard victim\n", victim.read_bytes())
            self.assertEqual(want, (tree / rel).read_bytes())
            self.assertEqual(1, (tree / rel).stat().st_nlink)
            twin = Path(tmp) / "twin.md"                                   # identical bytes: still its own file
            os.link(tree / rel, twin)
            pack.write_tree(tree)
            self.assertEqual(1, (tree / rel).stat().st_nlink)
            self.assertEqual(1, twin.stat().st_nlink)
            (tree / rel).unlink()
            os.mkfifo(tree / rel)
            self.assertNotIn(rel, pack.read_tree(tree))                    # never read (it would block)
            result = self.run_cli("--tree", tree)                          # run_cli times out instead of hanging
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(want, (tree / rel).read_bytes())
            self.assertEqual(0, self.run_cli("--check", tree).returncode)

    def test_missing_tree_is_one_not_found_line(self):
        result = self.run_cli("--check", self.tree / "nowhere")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual([f"error: tree not found: {self.tree / 'nowhere'}"], result.stderr.splitlines())

    def test_check_with_tree_is_rejected(self):
        result = self.run_cli("--check", self.tree, "--tree", self.tree)
        self.assertEqual(2, result.returncode)
        self.assertIn("not allowed with argument", result.stderr)

    def test_malformed_source_is_a_clear_error_not_a_traceback(self):
        # exit 2 (the packer cannot build) is distinct from 1 (the tree drifted)
        with tempfile.TemporaryDirectory(prefix="shode-pack-cli-") as tmp:
            root = Path(tmp)
            script = source_copy(root)
            agent = root / "agents/build.md"
            agent.write_bytes(put_body_floor(agent.read_bytes(), "text\n").replace(b"<!-- floor:end -->\n", b"", 1))
            (root / "plugins/shode-house").mkdir(parents=True)
            result = self.run_cli("--check", root / "plugins/shode-house", script=script)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(1, len(result.stderr.splitlines()), result.stderr)
        self.assertTrue(result.stderr.startswith("error: agents/build.md: malformed floor markers"), result.stderr)


class SourceSymlinkRefusalTest(unittest.TestCase):
    """U22 H3: `collect` reads the source the tree is generated from and never through a symlink -- a link inside a
    source root, a linked source root, and (added in U22) a linked `.claude-plugin` or `.claude-plugin/plugin.json`,
    whose fields are copied into the tree. Every planted link and its target lie inside a temporary directory."""

    def _source_copy(self, tmp):
        root = Path(tmp) / "src"
        names = ["agents", "references", "output-styles", "commands", ".claude-plugin", "LICENSE"]
        names += ["skills/" + b for b in pack.BUCKETS]
        for name in names:
            src, dst = ROOT / name, root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, dst, follow_symlinks=False)
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (outside / "plugin.json").write_bytes((ROOT / ".claude-plugin/plugin.json").read_bytes())
        (outside / "note.md").write_text("outside the source\n", encoding="utf-8")
        return root, outside

    def test_collect_refuses_every_source_symlink(self):
        with tempfile.TemporaryDirectory(prefix="shode-pack-src-") as tmp:
            root, outside = self._source_copy(tmp)
            manifest, entries = pack.collect(root)                     # control: the copy is collected
            self.assertEqual(manifest["name"], "shode-house")
            self.assertIn("references/scope-lock.md", entries)
            cases = (("a link inside a source root", "references/u22-link.md", outside / "note.md",
                      "symlink not allowed in candidate"),
                     ("a linked manifest", ".claude-plugin/plugin.json", outside / "plugin.json",
                      "symlink not allowed: .claude-plugin/plugin.json"),
                     ("a linked manifest directory", ".claude-plugin", outside,
                      "symlink not allowed: .claude-plugin"))
            for label, rel, target, message in cases:
                link, aside = root / rel, None
                if link.exists():
                    aside = root / (rel + ".aside")
                    link.rename(aside)
                link.symlink_to(target)
                try:
                    with self.assertRaises(ValueError, msg=label) as raised:
                        pack.collect(root)
                    self.assertIn(message, str(raised.exception), label)
                finally:
                    link.unlink()
                    if aside is not None:
                        aside.rename(link)
            self.assertEqual(pack.collect(root)[1], entries)           # restored: the same source again


if __name__ == "__main__":
    unittest.main()
