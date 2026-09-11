"""Maintainer checks: package allowlist, source identity and mutation failures."""
import importlib.util
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
        self.assertEqual(len(bundles["portable.zip"]), 6)
        self.assertEqual(len(bundles["claude.plugin"]), 7)
        for name, content in bundles["portable.zip"].items():
            self.assertEqual(content, bundles["claude.plugin"]["skills/" + name])
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
            with self.assertRaises(FileExistsError):
                pack.build(out)
            self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})

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
