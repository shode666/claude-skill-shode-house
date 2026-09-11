"""Check the installable marketplace tree, not just release ZIPs."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack", ROOT / "scripts/pack-portable.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def check_marketplace(root):
    config, bundles = pack.archives(root, include_experimental=True)
    catalog = json.loads((root / ".claude-plugin/marketplace.json").read_text())
    entries = catalog["plugins"]
    if len(entries) != 1 or entries[0]["name"] != config["name"]:
        raise ValueError("expected one released plugin")
    entry = entries[0]
    if entry["source"] != "./plugins/shode-house" or entry["version"] != config["version"]:
        raise ValueError("marketplace points to legacy or stale release")
    plugin = root / "plugins/shode-house"
    expected = dict(bundles["claude.plugin"])
    expected["skills/ask/agents/openai.yaml"] = bundles["portable.zip"]["ask/agents/openai.yaml"]
    native = ".codex-plugin/plugin.json"
    actual = {p.relative_to(plugin).as_posix() for p in plugin.rglob("*") if p.is_file()}
    if actual != set(expected) | {native}:
        raise ValueError("missing payload or legacy contamination")
    for path in plugin.rglob("*"):
        if path.is_symlink() or not path.resolve().is_relative_to(plugin.resolve()):
            raise ValueError("plugin escapes isolated root")
    for name, content in expected.items():
        if (plugin / name).read_bytes() != content:
            raise ValueError("marketplace bytes differ from release: " + name)
    manifest = json.loads((plugin / native).read_text())
    for key in ("name", "version", "description"):
        if manifest[key] != config[key]:
            raise ValueError("stale native manifest")
    if manifest.get("skills") != "./skills/" or set(manifest) - {
        "name", "version", "description", "author", "skills", "interface"
    }:
        raise ValueError("unexpected native components")


class MarketplaceReleaseTests(unittest.TestCase):
    def test_install_tree_matches_release(self):
        check_marketplace(ROOT)

    def test_root_route_stale_version_and_contamination_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("release", "plugins", ".claude-plugin", ".agents/skills/ask"):
                shutil.copytree(ROOT / name, root / name)
            catalog_path = root / ".claude-plugin/marketplace.json"
            original = catalog_path.read_text()
            for field, value in (("source", "./"), ("version", "3.15.0")):
                catalog = json.loads(original)
                catalog["plugins"][0][field] = value
                catalog_path.write_text(json.dumps(catalog))
                with self.assertRaises(ValueError):
                    check_marketplace(root)
            catalog_path.write_text(original)
            plugin = root / "plugins/shode-house"
            for name in (".mcp.json", "hooks/hooks.json", "skills/legacy/SKILL.md"):
                path = plugin / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n")
                with self.assertRaises(ValueError):
                    check_marketplace(root)
                path.unlink()
            skill = plugin / "skills/ask/SKILL.md"
            skill.write_text(skill.read_text() + "\nDifferent instructions\n")
            with self.assertRaises(ValueError):
                check_marketplace(root)


if __name__ == "__main__":
    unittest.main()
