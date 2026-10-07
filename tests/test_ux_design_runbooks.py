"""v4 W7 (UD R68, Sentinel W7 S7-1): design runs requested by ux-ui-designer target loopback origins only.

Neither ux runbook may offer a preview (non-loopback) origin, in the source or in a generated copy, and the
3a reachability step names a loopback URL as the only target of `ui-screenshot` and `axe-scan`.
Run: python3 tests/test_ux_design_runbooks.py   (also collected by pytest)
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNBOOKS = ("references/runbooks/ux-ui-designer-phase-1b.md", "references/runbooks/ux-ui-designer-phase-3a.md")
GENERATED = ("plugins/shode-house/knowledge",)


def copies(rel):
    yield ROOT / rel
    for base in GENERATED:
        copy = ROOT / base / rel
        if copy.exists():
            yield copy


class UxDesignRunbookLoopbackTest(unittest.TestCase):
    def test_no_preview_origin_in_either_ux_runbook(self):
        for rel in RUNBOOKS:
            self.assertTrue((ROOT / rel).is_file(), rel)
            for path in copies(rel):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertNotRegex(path.read_text(), re.compile("preview", re.I))

    def test_3a_reachability_step_is_loopback_only(self):
        lines = [l for l in (ROOT / RUNBOOKS[1]).read_text().splitlines() if l.startswith("2. **App reachable**")]
        self.assertEqual(1, len(lines), "one 3a reachability step")
        self.assertIn("`ui-screenshot` and `axe-scan` need it already running at a loopback URL.", lines[0])


if __name__ == "__main__":
    unittest.main()
