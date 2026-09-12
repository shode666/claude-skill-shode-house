"""Candidate packaging invariants, not host-execution acceptance."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pack = module("pack_team", ROOT / "scripts/pack-team.py")
inventory = module("team_inventory", ROOT / "tests/test_team_package.py")


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

    def test_private_command_references_preserved_not_publicly_registered(self):
        _, entries = pack.payload()
        for path in (ROOT / "commands").glob("*.md"):
            self.assertEqual(path.read_bytes(), entries["knowledge/commands/" + path.name])
        self.assertEqual(["./commands/ask.md"], json.loads(entries[".claude-plugin/plugin.json"])["commands"])

    def test_versions_agree_and_only_ask_command_ships(self):
        version, entries = pack.payload()
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            self.assertEqual(version, json.loads(entries[name])["version"])
        self.assertEqual(["commands/ask.md"], [p for p in entries if p.startswith("commands/")])
        self.assertIn("skills/ask/SKILL.md", entries)
        skills = [p for p in entries if p.startswith("skills/") and p.endswith("/SKILL.md")]
        self.assertEqual(24, len(skills))
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
