#!/usr/bin/env python3
"""CI workflow wiring outside gate #27's A15/W9 block (W10a, decision U21; bd v7u.4.7 notes).

- Sentinel W1 follow-up F6: the workflow declares a top-level least-privilege `permissions:` block.
- Sentinel F6 / Chris W1 follow-up C-7: pytest is installed only from the hash-pinned .github/requirements-ci.txt
  (setup step and the in-gate venv fallback alike); every requirement is pinned with `==` and carries a hash.
- CI #21 (W5b note): anchors are read without `jq @tsv`, which doubled every backslash, so an anchor that holds
  a '\\' was always reported missing.
- CI #23 router owner form (v4 ADR §5.10, ledger W3 "CI #23 lazy-load OWNER"): `OWNER: router` resolves to the
  router style output-styles/<plugin>.md plus the skills it loads as `<plugin>:<skill>`. The 12 `OWNER:
  orchestrator` flips are shipped text and stay with the switch commit (W10b).
- CI #24a (Bella W10a S-1): a namespaced `<plugin>:<skill>` § Y section reference is checked, not skipped.
- CI #17 (U22 slice D): the design-intel smoke writes its payloads into a per-run `mktemp -d` under $TMPDIR that is
  removed on exit, never into fixed /tmp names (concurrent gates collided on /tmp/ds.json; fixed names are predictable).
- U22 iter 2: no pid-based (`$$`) temp name anywhere in the workflow; the build step uses `mktemp` + an EXIT trap.
The #17, #21, #23 and #24 sections are cut out of .github/workflows/ci.yml together with the gate prelude and run with bash
in a scratch tree, so the real shell text is tested, not a copy of it.
Run: python3 tests/test_ci_wiring.py   (CI gate #27 runs it; stdlib + bash + jq)
"""
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
REQ = ROOT / ".github/requirements-ci.txt"
# The PATH every extracted gate section runs with; the bash/jq probe reads the same PATH, so a tool found only on
# the caller's PATH skips the test instead of failing it inside the gate run.
GATE_PATH = "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"


def gate_has(*tools):
    return all(shutil.which(tool, path=GATE_PATH) for tool in tools)


def gate_script():
    """The gate exactly as `make validate` extracts it (Makefile awk: first `run: |` block, 10-space indent)."""
    out, on = [], False
    for line in CI.read_text().splitlines():
        if re.match(r"^        run: \|", line):
            on = True
            continue
        if on and re.match(r"^      - name:", line):
            break
        if on:
            out.append(line[10:] if line.startswith(" " * 10) else line)
    return out


def section(number):
    """Gate prelude (up to section 1) + section `number` up to the next section."""
    lines = gate_script()
    first = next(i for i, l in enumerate(lines) if l.startswith('sec "1. '))
    start = next(i for i, l in enumerate(lines) if l.startswith(f'sec "{number}. '))
    stop = next(i for i, l in enumerate(lines) if i > start and re.match(r'sec "\d', l))
    return "\n".join(lines[:first] + lines[start:stop]) + '\necho "fail=$fail"\n'


def sub24a():
    """Gate prelude + CI #24a only (the rest of #24 needs the whole repo)."""
    lines = gate_script()
    first = next(i for i, l in enumerate(lines) if l.startswith('sec "1. '))
    start = next(i for i, l in enumerate(lines) if l.startswith("# 24a. "))
    stop = next(i for i, l in enumerate(lines) if l.startswith("# 24b. "))
    return "\n".join(lines[:first] + lines[start:stop]) + '\necho "fail=$fail"\n'


def run_section(number, root):
    r = subprocess.run(["bash", "-c", section(number)], cwd=root, capture_output=True, text=True,
                       env={"PATH": GATE_PATH, "HOME": str(root)})
    return r.stdout + r.stderr


def tree(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


MANIFEST = json.dumps({"name": "shode-house", "version": "3.17.2", "skills": ["./skills/discipline/"]})


@unittest.skipUnless(gate_has("bash", "jq"), "needs bash + jq on the gate PATH")
class AnchorReadTest(unittest.TestCase):
    """CI #21: the anchor must reach grep -F byte for byte."""

    def run21(self, anchor, body):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            rule = {"id": "r-backslash", "source_of_truth": "agents/a.md", "anchor": anchor}
            tree(root, {".claude-plugin/plugin.json": MANIFEST, "agents/a.md": body,
                        ".enforcement-map.json": json.dumps({"rules": [rule]})})
            return run_section(21, root)

    def test_anchor_with_a_backslash_is_found(self):
        anchor = r"never run `rm -rf \"$X\"` blind"
        out = self.run21(anchor, "# a\n- " + anchor + " here\n")
        self.assertNotIn("r-backslash' anchor", out, out)       # neither missing nor too short
        self.assertIn("rules -- inventory looks incomplete", out)  # the section ran to its end (1 rule < 15)

    def test_anchor_with_a_backslash_that_is_absent_is_red(self):
        anchor = r"match C:\temp\new only"
        out = self.run21(anchor, "# a\n- match C:\\\\temp\\\\new only (doubled, not the anchor)\n")
        self.assertIn("r-backslash' anchor 'match C:\\temp\\new only' ไม่พบใน agents/a.md", out)

    def test_anchor_with_a_tab_is_matched_exactly(self):
        anchor = "column one\tcolumn two"
        self.assertNotIn("r-backslash' anchor", self.run21(anchor, "# a\n" + anchor + "\n"))
        self.assertIn("ไม่พบใน agents/a.md", self.run21(anchor, "# a\ncolumn one column two\n"))

    def test_anchor_with_a_line_break_is_red(self):
        out = self.run21("first line of it\nsecond", "# a\nfirst line of it\nsecond\n")
        self.assertIn("rule 'r-backslash' มี field ที่มี line break หรือ U+001F", out)

    def test_no_tsv_read_of_anchors(self):
        sec21 = section(21)
        self.assertNotRegex(sec21, r"\.anchor[^\n]*@tsv")
        self.assertIn("IFS=$'\\x1f'", sec21)


@unittest.skipUnless(gate_has("bash", "jq"), "needs bash + jq on the gate PATH")
class RouterOwnerTest(unittest.TestCase):
    """CI #23: `OWNER: router` = the router style + the skill roots it loads."""

    LAZY = ("<!-- lazy-load-contract -->\nLOAD: skills/discipline/wf/detail.md\nWHEN: engagement start\n"
            "OWNER: {owner}\nREQUIRED-BEFORE: phase 1\n\n# detail\n")

    def run23(self, owner="router", style="Load `shode-house:wf` at engagement start.\n",
              skill="See detail.md for the steps.\n", agent=None, style_name="shode-house"):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            files = {".claude-plugin/plugin.json": MANIFEST,
                     "skills/discipline/wf/SKILL.md": "---\nname: wf\n---\n" + skill,
                     "skills/discipline/wf/detail.md": self.LAZY.format(owner=owner),
                     "agents/caller.md": "---\nname: caller\n---\nreads detail.md\n"}
            if style is not None:
                files[f"output-styles/{style_name}.md"] = "---\nname: shode-house\n---\n" + style
            if agent:
                files[f"agents/{owner}.md"] = agent
            tree(root, files)
            return run_section(23, root)

    def test_router_owner_reaches_through_a_skill_the_style_loads(self):
        out = self.run23()
        self.assertNotIn("detail.md: OWNER", out, out)
        self.assertNotIn("skills/discipline/wf/detail.md:", out, out)

    def test_router_owner_with_the_pointer_in_the_style_itself(self):
        out = self.run23(style="Read skills/discipline/wf/detail.md first.\n", skill="nothing here\n")
        self.assertNotIn("skills/discipline/wf/detail.md:", out, out)

    def test_router_owner_without_a_pointer_is_red(self):
        out = self.run23(style="No skill named here.\n")
        self.assertIn("detail.md: OWNER router ไม่มี pointer", out)

    def test_router_owner_without_the_router_style_is_red(self):
        self.assertIn("OWNER router แต่ไม่มี router style output-styles/shode-house.md", self.run23(style=None))
        self.assertIn("OWNER router แต่ไม่มี router style", self.run23(style_name="other"))

    def test_agent_owner_still_needs_the_agent_and_its_closure(self):
        out = self.run23(owner="ghost")
        self.assertIn("OWNER 'ghost' ไม่ใช่ agent ที่มีอยู่", out)
        ok = self.run23(owner="dev", agent='---\nname: dev\ntools: ["Read"]\nskills: ["wf"]\n---\n')
        self.assertNotIn("skills/discipline/wf/detail.md:", ok, ok)

    def test_orphan_check_applies_to_the_router_form_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            tree(root, {".claude-plugin/plugin.json": MANIFEST,
                        "skills/discipline/wf/SKILL.md": "---\nname: wf\n---\nnothing\n",
                        "skills/discipline/wf/detail.md": self.LAZY.format(owner="router"),
                        "output-styles/shode-house.md": "---\nname: s\n---\nRead skills/discipline/wf/detail.md\n"})
            out = run_section(23, root)
        # callers are counted in agents/ skills/ commands/ references/ for both forms; a pointer in the style alone
        # does not make a caller, so the router form keeps the orphan check
        self.assertIn("detail.md: ไม่มี caller อ้างถึงเลย (orphan lazy reference)", out)


@unittest.skipUnless(gate_has("bash", "jq"), "needs bash + jq on the gate PATH")
class NamespacedSectionRefTest(unittest.TestCase):
    """CI #24a (Bella W10a S-1, R41): a `<plugin>:<skill>` § Y reference is resolved like a bare skill name and its
    heading checked; before, the extraction regex had no ':' and skipped it silently."""

    def run24(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            tree(root, {".claude-plugin/plugin.json": MANIFEST,
                        "skills/discipline/wf/SKILL.md": "---\nname: wf\n---\n# wf\n\n## Postmortem template (blameless)\n",
                        "agents/a.md": "---\nname: a\n---\n" + "".join(l + "\n" for l in lines)})
            r = subprocess.run(["bash", "-c", sub24a()], cwd=root, capture_output=True, text=True,
                               env={"PATH": GATE_PATH, "HOME": str(root)})
            return r.stdout + r.stderr

    def test_namespaced_ref_with_a_real_heading_passes(self):
        out = self.run24(["Load `shode-house:wf` § Postmortem template (blameless) first.", "Bare `wf` § Postmortem template"])
        self.assertNotIn("agents/a.md:", out, out)

    def test_namespaced_ref_to_a_missing_heading_is_red(self):
        out = self.run24(["Load `shode-house:wf` § Incident timeline first."])
        self.assertRegex(out, r"X agents/a\.md: อ้าง 'wf § Incident timeline ?' แต่ไม่พบ heading นั้นใน skills/discipline/wf/SKILL\.md")

    def test_namespaced_ref_to_a_missing_skill_is_red(self):
        out = self.run24(["Load `shode-house:ghost` § Postmortem template first."])
        self.assertIn("X agents/a.md: อ้าง 'ghost § Postmortem templat' แต่หาไฟล์ 'ghost' ไม่เจอในรีโป", out)

    def test_other_namespace_or_a_path_after_the_namespace_is_red(self):
        out = self.run24(["Load `other-plugin:wf` § Postmortem template first."])
        self.assertIn("X agents/a.md: อ้าง 'other-plugin:wf § Postmortem templat' ด้วย namespace ที่ไม่ใช่ 'shode-house:'", out)
        out = self.run24(["Load `shode-house:wf/SKILL.md` § Postmortem template first."])
        self.assertIn("ไม่ใช่ชื่อ skill (<plugin>:<skill>)", out)

    def test_extraction_keeps_the_colon(self):
        self.assertIn("[A-Za-z0-9/_.:-]*", sub24a())
        self.assertIn("fail=0", self.run24(["nothing to check here"]))

class WorkflowPermissionsAndPinsTest(unittest.TestCase):
    def test_top_level_permissions_are_read_only(self):
        text = CI.read_text()
        block = re.search(r"^permissions:\n((?:  \S.*\n)+)", text, re.M)
        self.assertTrue(block, "no top-level permissions: block")
        self.assertEqual("  contents: read\n", block.group(1))
        self.assertLess(text.index("\npermissions:"), text.index("\njobs:"))
        self.assertNotRegex(text, r":\s*write\b")
        self.assertNotRegex(text, r"permissions:\s*write-all")

    def test_requirements_are_pinned_with_hashes(self):
        reqs = [r for r in re.sub(r"\\\n", " ", REQ.read_text()).splitlines() if r.strip() and not r.startswith("#")]
        names = set()
        for r in reqs:
            with self.subTest(req=r.split()[0]):
                self.assertRegex(r, r"^[A-Za-z0-9_.-]+==[\w.]+(?: ; [^-]+)?\s+--hash=sha256:[0-9a-f]{64}")
                names.add(r.split("==")[0].lower())
        self.assertIn("pytest", names)
        # pytest 8.4's own runtime dependencies (requires_dist without extras) are all listed
        self.assertLessEqual({"iniconfig", "packaging", "pluggy", "pygments", "exceptiongroup", "tomli"}, names)

    def test_every_pip_install_uses_the_hash_pinned_file(self):
        installs = [l for l in CI.read_text().splitlines() if "pip install" in l and not l.strip().startswith("#")]
        self.assertGreaterEqual(len(installs), 2, installs)               # the setup step + the venv fallback
        for line in installs:
            with self.subTest(line=line):
                self.assertIn("--require-hashes", line)
                self.assertIn("-r .github/requirements-ci.txt", line)
                self.assertNotIn("--user", line)
        self.assertNotRegex(CI.read_text(), r"pip install --quiet pytest\b")


@unittest.skipUnless(gate_has("bash", "python3", "mktemp"), "needs bash + python3 + mktemp on the gate PATH")
class DesignIntelScratchDirTest(unittest.TestCase):
    """CI #17 run from the real tree: it only reads the repo; every file it writes goes under $TMPDIR."""
    def run17(self, tmpdir, home):
        r = subprocess.run(["bash", "-c", section(17)], cwd=ROOT, capture_output=True, text=True,
                           env={"PATH": GATE_PATH, "HOME": str(home), "TMPDIR": str(tmpdir)})
        return r.stdout + r.stderr

    def test_smoke_runs_in_tmpdir_and_removes_its_dir(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            out = self.run17(tmp, home)
            self.assertIn("fail=0", out)
            self.assertIn("design-intel pack intact + gate runs", out)
            self.assertEqual([], sorted(p.name for p in pathlib.Path(tmp).iterdir()), "per-run dir left behind")

    def test_unusable_tmpdir_is_red_not_a_fallback_to_tmp(self):
        with tempfile.TemporaryDirectory() as home:
            out = self.run17(pathlib.Path(home) / "absent", home)
            self.assertIn("mktemp -d failed under", out)
            self.assertIn("fail=1", out)

    def test_no_fixed_tmp_path_is_written(self):
        body = section(17).split('sec "17. ', 1)[1].replace("${TMPDIR:-/tmp}", "")
        self.assertNotRegex(body, r"(?<![\w$}])/tmp/")


class WorkflowTempNamesTest(unittest.TestCase):
    """U22 iter 2 (Chris L2/L3, Sentinel I2): no temp name in the workflow is built from the shell pid (`$$` is
    predictable), and the "Build .plugin artifact" step makes its snapshot with `mktemp` and removes it and the
    unpack dir with an EXIT trap."""
    def build_step(self):
        text = CI.read_text(encoding="utf-8")
        start = text.index("      - name: Build .plugin artifact\n")
        stop = text.index("\n      - name:", start + 1)
        return text[start:stop]

    def test_no_pid_based_temp_name(self):
        self.assertNotIn("$$", CI.read_text(encoding="utf-8"))

    def test_build_step_uses_mktemp_and_an_exit_trap(self):
        step = self.build_step()
        self.assertIn('before=$(mktemp "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/pack-tree-before.XXXXXX") || exit 1', step)
        self.assertIn("""d=""; trap 'rm -rf "$before" ${d:+"$d"}' EXIT""", step)
        self.assertLess(step.index("trap 'rm -rf"), step.index("make pack"))


if __name__ == "__main__":
    unittest.main()
