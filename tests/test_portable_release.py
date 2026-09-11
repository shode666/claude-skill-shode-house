"""Maintainer checks: package allowlist, source identity and mutation failures."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pack", ROOT / "scripts/pack-portable.py")
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class PortableReleaseTests(unittest.TestCase):
    def test_only_ask_and_exact_payload(self):
        config, bundles = pack.archives()
        self.assertEqual(config["release_host"], "codex")
        self.assertEqual(set(bundles), {"portable.zip"})
        config, bundles = pack.archives(include_experimental=True)
        self.assertEqual(len(bundles["portable.zip"]), 7)
        self.assertEqual(len(bundles["claude.plugin"]), 7)
        for name, content in bundles["portable.zip"].items():
            if name == "ask/agents/openai.yaml":
                self.assertEqual(content, (ROOT / "release/hosts/codex/openai.yaml").read_bytes())
                continue
            self.assertEqual(content, bundles["claude.plugin"]["skills/" + name])
        manifest = json.loads(bundles["claude.plugin"][".claude-plugin/plugin.json"])
        self.assertEqual(manifest, {key: config[key] for key in ("name", "version", "description")})
        for bundle in bundles.values():
            self.assertFalse(any(p.startswith(("hooks/", "agents/", "commands/", "scripts/", "output-styles/")) for p in bundle))

    def test_build_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            built = pack.build(out)
            before = {p.name: p.read_bytes() for p in out.iterdir()}
            for item in built:
                with zipfile.ZipFile(item["path"]) as archive:
                    self.assertIsNone(archive.testzip())
                    expected = pack.archives()[1]["portable.zip"]
                    self.assertEqual(set(archive.namelist()), set(expected))
                    for name, content in expected.items():
                        self.assertEqual(archive.read(name), content)
            with self.assertRaises(FileExistsError):
                pack.build(out)
            self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_experimental_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            built = pack.build(Path(directory), include_experimental=True)
            self.assertEqual(len(built), 2)
            expected = pack.archives(include_experimental=True)[1]
            for item, suffix in zip(built, ("portable.zip", "claude.plugin")):
                with zipfile.ZipFile(item["path"]) as archive:
                    self.assertEqual(set(archive.namelist()), set(expected[suffix]))
                    for name, content in expected[suffix].items():
                        self.assertEqual(archive.read(name), content)

    def test_host_configuration_mutations_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "release", root / "release")
            shutil.copytree(ROOT / ".agents/skills/ask", root / ".agents/skills/ask")
            metadata = root / "release/hosts/codex/openai.yaml"
            original = metadata.read_bytes()
            for content in (original + b'policy:\n  allow_implicit_invocation: false\n',
                            original.replace(b'$ask', b'$wrong')):
                metadata.write_bytes(content)
                with self.assertRaises(ValueError):
                    pack.archives(root)
            metadata.write_bytes(original)
            manifest = root / "release/hosts/claude/plugin.json"
            original_manifest = manifest.read_bytes()
            manifest.write_text('{"name":"wrong", "hooks":"./hooks.json"}\n')
            with self.assertRaises(ValueError):
                pack.archives(root)
            manifest.write_bytes(original_manifest)
            metadata.unlink()
            with self.assertRaises(ValueError):
                pack.archives(root)

    def test_missing_or_extra_runtime_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "release", root / "release")
            source = root / ".agents/skills/ask"
            shutil.copytree(ROOT / ".agents/skills/ask", source)
            extra = source / "injected.sh"
            extra.write_text("echo unexpected\n")
            with self.assertRaises(ValueError):
                pack.payload(root)
            extra.unlink()
            (source / "references/delivery.md").unlink()
            with self.assertRaises(ValueError):
                pack.payload(root)

    def test_bad_link_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "release", root / "release")
            source = root / ".agents/skills/ask"
            shutil.copytree(ROOT / ".agents/skills/ask", source)
            skill = source / "SKILL.md"
            skill.write_text(skill.read_text() + "\n[missing](references/missing.md)\n")
            with self.assertRaises(ValueError):
                pack.payload(root)


if __name__ == "__main__":
    unittest.main()
