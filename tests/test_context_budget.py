"""Conditional extraction must not make full-path accounting artificially cheap.

Data-driven cases (v4 ADR §7 W1) run the real script in a scratch copy of the tree, so the 4.0.0
switch (namespaced preloads, renamed forced style, retired orchestrator) is exercised before it lands.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COPY = ("agents", "commands", "output-styles", "skills", "references/runbooks", ".claude-plugin",
        ".workflow-scenario-budget", "scripts/context-budget.py")


def run(root, *args):
    r = subprocess.run([sys.executable, str(root / "scripts/context-budget.py"), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class ContextBudgetTest(unittest.TestCase):
    def test_full_diagnosis_counts_required_extracted_investigation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/context-budget.py"), "--json"],
            check=True, capture_output=True, text=True,
        )
        scenarios = json.loads(result.stdout)["scenarios"]
        root = ROOT / "skills/workflow/diagnose"
        expected = sum((root / name).stat().st_size for name in
                       ("SKILL.md", "full-investigation.md", "loop-ladder.md"))
        self.assertEqual(scenarios["diagnose-full"]["lazy_refs"], expected)
        self.assertEqual(scenarios["diagnose-fast"]["lazy_refs"],
                         (root / "SKILL.md").stat().st_size)


class DataDrivenBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Chris W1 suggestion 9: one real-tree failure must not repeat as 7 identical errors. The real tree
        # itself stays red in ContextBudgetTest (check=True) and in CI #20/#22; these cases need a sound base.
        rc, out = run(ROOT, "--json")
        if rc != 0:
            raise unittest.SkipTest(f"real tree: context-budget.py --json rc={rc} (reported once; red in "
                                    f"ContextBudgetTest and CI #20/#22): {out.strip()[:300]}")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for rel in COPY:
            src, dst = ROOT / rel, self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        rc, out = run(self.root, "--json")
        self.assertEqual(0, rc, out)
        self.base = json.loads(out)
        self.plugin = json.loads((self.root / ".claude-plugin/plugin.json").read_text())["name"]

    def json_ok(self):
        rc, out = run(self.root, "--json")
        self.assertEqual(0, rc, out)
        return json.loads(out)

    def assert_error(self, needle):
        rc, out = run(self.root, "--check")
        self.assertEqual(2, rc, out)
        self.assertNotIn("Traceback", out)
        self.assertIn(needle, out)

    def edit(self, rel, old, new):
        p = self.root / rel
        text = p.read_text()
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1))

    def rewrite_preloads(self, fn):
        """Apply fn to every quoted name on each agent's skills: line; return how many names changed."""
        changed = 0
        for p in (self.root / "agents").glob("*.md"):
            def line(m):
                nonlocal changed
                def name(q):
                    nonlocal changed
                    new = fn(q.group(1))
                    changed += new != q.group(1)
                    return '"%s"' % new
                return re.sub(r'"([^"]+)"', name, m.group(1))
            p.write_text(re.sub(r'^(skills:.*)$', line, p.read_text(), count=1, flags=re.M))
        return changed

    def test_namespaced_preload_costs_the_same_as_bare(self):
        # v4 W5b: every body is namespaced, so first strip the prefix (bare = the 3.x form), then add it back;
        # both forms must resolve to the same preloaded skills (Chris W5a C-6: the test must still compare two forms)
        prefix = self.plugin + ":"
        self.assertGreater(self.rewrite_preloads(lambda n: n[len(prefix):] if n.startswith(prefix) else n), 0)
        self.assertIn('"shode-house-discipline"', (self.root / "agents/developer.md").read_text())
        bare = self.json_ok()
        self.assertGreater(self.rewrite_preloads(lambda n: n if n.startswith(prefix) else prefix + n), 0)
        self.assertIn('"%s:shode-house-discipline"' % self.plugin, (self.root / "agents/developer.md").read_text())
        after = self.json_ok()   # bodies grow by the prefix bytes; the preload must resolve to the same skills
        for key in ("preload", "skills"):
            self.assertEqual({k: v[key] for k, v in bare["agents"].items()},
                             {k: v[key] for k, v in after["agents"].items()})
            self.assertEqual({k: v[key] for k, v in self.base["agents"].items()},
                             {k: v[key] for k, v in after["agents"].items()})
        self.assertTrue(all(v["preload"] > 0 for v in after["agents"].values()))

    def deliverable_preload(self):
        text = (self.root / "agents/developer.md").read_text()
        for form in ('"%s:shode-house-deliverable"' % self.plugin, '"shode-house-deliverable"'):
            if form in text:
                return form
        self.fail("agents/developer.md preloads no shode-house-deliverable")

    def test_unknown_preload_is_an_error_not_zero_bytes(self):
        self.edit("agents/developer.md", self.deliverable_preload(), '"%s:code-index"' % self.plugin)
        self.assert_error("developer: preload ['code-index'] is not a shipped skill")

    def test_preload_from_unshipped_bucket_is_an_error(self):
        self.edit("agents/developer.md", self.deliverable_preload(), '"eval-harness"')
        self.assertTrue(any((self.root / "skills").glob("*/eval-harness/SKILL.md")))   # exists, but not shipped
        self.assert_error("not a shipped skill")

    def test_forced_style_is_found_by_flag_not_by_file_name(self):
        styles = [p for p in (self.root / "output-styles").glob("*.md") if "force-for-plugin: true" in p.read_text()]
        self.assertEqual(1, len(styles))
        styles[0].rename(styles[0].with_name("renamed-router.md"))
        self.assertEqual(self.base["scenarios"], self.json_ok()["scenarios"])

    def test_two_or_zero_forced_styles_fail_closed(self):
        style = next(p for p in (self.root / "output-styles").glob("*.md") if "force-for-plugin: true" in p.read_text())
        shutil.copy2(style, style.with_name("second.md"))
        self.assert_error("exactly one output style")
        style.with_name("second.md").unlink()
        style.write_text(style.read_text().replace("force-for-plugin: true", "force-for-plugin: false"))
        self.assert_error("exactly one output style")

    def test_quoted_or_yaml_truthy_force_flag_counts_as_forced(self):
        """Sentinel W3-4: a second style forced as "true" / 'True' / yes / on must not slip past the one-style check."""
        style = next(p for p in (self.root / "output-styles").glob("*.md") if "force-for-plugin: true" in p.read_text())
        other = style.with_name("second.md")
        for spelling in ('"true"', "'True'", "TRUE", "yes", "On", "true  # comment"):
            with self.subTest(spelling=spelling):
                other.write_text(style.read_text().replace("force-for-plugin: true", "force-for-plugin: " + spelling))
                self.assert_error("exactly one output style")
        for spelling in ('"false"', "no", "False"):
            with self.subTest(spelling=spelling):
                other.write_text(style.read_text().replace("force-for-plugin: true", "force-for-plugin: " + spelling))
                self.assertEqual(self.base["scenarios"], self.json_ok()["scenarios"])
        other.write_text(style.read_text().replace("force-for-plugin: true", "force-for-plugin: maybe"))
        self.assert_error("not a recognisable boolean")

    def test_quoted_or_duplicate_force_key_fails_closed(self):
        """Chris W1 r2 L-1: YAML reads a quoted key as the same key; a duplicate key is read differently by hosts."""
        style = next(p for p in (self.root / "output-styles").glob("*.md") if "force-for-plugin: true" in p.read_text())
        other = style.with_name("second.md")
        for key in ('"force-for-plugin"', "'force-for-plugin'"):
            with self.subTest(key=key):
                other.write_text(style.read_text().replace("force-for-plugin: true", key + ": true"))
                self.assert_error("exactly one output style")
        other.write_text(style.read_text().replace("force-for-plugin: true",
                                                   "force-for-plugin: false\nforce-for-plugin: true"))
        self.assert_error("duplicate key")
        other.write_text(style.read_text().replace("force-for-plugin: true",
                                                   "force-for-plugin: false\n'force-for-plugin': false"))
        self.assert_error("duplicate key")

    def test_retired_optional_agent_drops_out_and_required_agent_does_not(self):
        # 4.0.0 retired agents/orchestrator.md, so the `?orchestrator` slot of map-mode is absent in the real tree.
        # A fixture agent file under that name (a copy of a shipped agent, scratch copy only) exercises both sides of
        # the optional branch: counted while present, dropped once removed (the test used to skip at 4.0.0).
        orch = self.root / "agents/orchestrator.md"
        self.assertFalse(orch.exists(), "agents/orchestrator.md is retired in 4.0.0")
        shutil.copy2(self.root / "agents/product-manager.md", orch)
        present = self.json_ok()
        added = present["agents"]["orchestrator"]["total"]
        self.assertGreater(added, 0)
        self.assertEqual(self.base["scenarios"]["map-mode"]["total"] + added, present["scenarios"]["map-mode"]["total"])
        self.assertEqual(self.base["scenarios"]["map-mode"]["agent_count"] + 1,
                         present["scenarios"]["map-mode"]["agent_count"])
        removed = added
        orch.unlink()
        after = self.json_ok()["scenarios"]
        self.assertEqual(present["scenarios"]["map-mode"]["total"] - removed, after["map-mode"]["total"])
        self.assertEqual(present["scenarios"]["map-mode"]["agent_count"] - 1, after["map-mode"]["agent_count"])
        (self.root / "agents/product-manager.md").unlink()
        self.assert_error("agent file missing: agents/product-manager.md")

    def test_missing_lazy_reference_is_an_error(self):
        (self.root / "skills/workflow/diagnose/loop-ladder.md").unlink()
        self.assert_error("required file missing: skills/workflow/diagnose/loop-ladder.md")


if __name__ == "__main__":
    unittest.main()
