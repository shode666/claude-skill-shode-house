"""Candidate packaging invariants, not host-execution acceptance."""
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Directories the host scans for ACTIVE registrations at a plugin root. A style
# under knowledge/ is inert data, so the three shipped shapes must agree on this set.
REGISTRATION_DIRS = ("agents", "commands", "output-styles", "skills")


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
    """What `make pack` puts in the .plugin zip, derived (never built) from the
    `pack build:` recipe -- the single source of truth for that shape -- applied to
    the working tree, exactly as `zip -r` would walk it. Deterministic: this leg runs
    on every checkout, including in CI where the archive is built after the gate."""
    recipe = re.search(r"^pack build:\n((?:\t.*\n|\n)+)", (ROOT / "Makefile").read_text(), re.M)
    if not recipe:
        raise RuntimeError("Makefile pack recipe not found")
    tokens = [token for token in re.findall(r"[\w.\-/]+", recipe.group(1))
              if token.split("/")[0] in REGISTRATION_DIRS]
    if not tokens:
        raise RuntimeError("Makefile pack recipe ships no registration directory")
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

    def test_agent_adapters_use_shared_host_neutral_frontmatter(self):
        import re
        _, entries = pack.unified_payload()
        roles = [path for path in entries if path.startswith("agents/")]
        self.assertEqual(19, len(roles))
        for path in roles:
            header = entries[path].decode().split("---", 2)[1]
            self.assertNotRegex(header, re.compile(r"^(color|model: (sonnet|opus|claude))", re.M))
            self.assertIn("model: inherit", header)
            self.assertRegex(header, re.compile(r"^tools:", re.M))
            self.assertRegex(header, re.compile(r"^skills:", re.M))

    def test_committed_plugin_tree_matches_source(self):
        tree = ROOT / "plugins/shode-house"
        self.assertTrue(tree.is_dir(), "run: python3 scripts/pack-team.py --tree plugins/shode-house")
        self.assertEqual([], pack.tree_drift(tree))

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
        # sources stay under knowledge/; the adapters are what the host scans.
        _, entries = pack.payload()
        authored = sorted(path.name for path in (ROOT / "commands").glob("*.md"))
        for path in (ROOT / "commands").glob("*.md"):
            self.assertEqual(path.read_bytes(), entries["knowledge/commands/" + path.name])
        self.assertEqual(["./commands/" + name for name in authored],
                         json.loads(entries[".claude-plugin/plugin.json"])["commands"])

    def test_command_adapters_pass_the_user_argument_through(self):
        # `$ARGUMENTS` is substituted in the invoked file only, never in a file it links
        # to, so an adapter whose source takes an argument must carry the placeholder
        # itself -- otherwise `argument-hint` still prompts and the answer goes nowhere.
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

    def test_every_adapter_points_to_full_preserved_source(self):
        _, entries = pack.payload()
        import posixpath
        import re
        for path, body in entries.items():
            if path.startswith(("agents/", "skills/")) and path.endswith(".md"):
                links = re.findall(r"\]\(([^)]+)\)", body.decode())
                self.assertEqual(1, len(links), path)
                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), links[0]))
                self.assertTrue(target.startswith("knowledge/"), path)
                self.assertEqual((ROOT / target[len("knowledge/"):]).read_bytes(), entries[target])

    def test_skill_adapters_never_force_full_reads(self):
        # SPEC 12/95: skill adapters are thin entry points. Role adapters keep
        # the role + prerequisite read (fresh-context worker contract, ADR-4).
        import re
        eager = re.compile(r"\bin full\b|read (this|the) (skill|full)", re.I)
        _, entries = pack.unified_payload()
        skills = [p for p in entries if p.startswith("skills/") and p.endswith("/SKILL.md")]
        self.assertGreaterEqual(len(skills), 20)
        for path in skills:
            body = entries[path].decode().split("---", 2)[2]
            self.assertIsNone(eager.search(body), path)
            self.assertIn("as the workflow entry point", body, path)
            self.assertIn("under this plugin's knowledge/ directory", body, path)
            self.assertIn("preserve host/project/user authority", body, path)
        self.assertIsNone(eager.search(entries["commands/ask.md"].decode()))
        self.assertIsNotNone(eager.search(entries["skills/ask/SKILL.md"].decode().replace(
            "Use the referenced", "Read this skill in full. Use the referenced")))
        for path in (p for p in entries if p.startswith("agents/")):
            self.assertIn("including its declared prerequisite skills", entries[path].decode(), path)

    def test_generated_tree_carries_a_top_level_output_style(self):
        # A style cannot be an adapter: the file IS the main-session system prompt,
        # and the host only scans <plugin root>/output-styles/.
        _, entries = pack.unified_payload()
        self.assertIn("output-styles/oliver.md", set(entries))
        self.assertTrue((ROOT / "plugins/shode-house/output-styles/oliver.md").is_file(),
                        "run: python3 scripts/pack-team.py --tree plugins/shode-house")

    def test_top_level_output_style_is_byte_identical_to_the_repo_root(self):
        _, entries = pack.unified_payload()
        source = (ROOT / "output-styles/oliver.md").read_bytes()
        self.assertEqual(source, entries["output-styles/oliver.md"])
        self.assertEqual(source, (ROOT / "plugins/shode-house/output-styles/oliver.md").read_bytes())

    def test_top_level_output_style_keeps_its_activating_frontmatter(self):
        _, entries = pack.unified_payload()
        parts = entries["output-styles/oliver.md"].decode().split("---", 2)
        self.assertEqual("", parts[0])
        self.assertRegex(parts[1], re.compile(r"^name: Oliver$", re.M))
        self.assertRegex(parts[1], re.compile(r"^force-for-plugin: true$", re.M))

    def test_generated_manifests_leave_the_output_style_discoverable(self):
        # The activation contract, not just the absence of a key: either a manifest
        # declares no `outputStyles` (CLAUDE.md -- the field REPLACES the default scan)
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


if __name__ == "__main__":
    unittest.main()
