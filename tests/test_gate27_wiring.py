#!/usr/bin/env python3
"""CI gate #27 wiring (v4 ADR §7 W1): how A15 (the design-runner suite, required in every mode) runs.

- Bella W1 r2 N1 / W12 F-12: a missing tests/test_design_run.py must be red, never a silent ok. The A15
  block of the gate script is cut out of .github/workflows/ci.yml and executed with bash in a scratch
  directory, so the real shell text is tested, not a copy of it.
- Chris W1 r2 R2-3: pytest on the Ubuntu runner comes from a Python that actions/setup-python installs
  (not the PEP 668 system python3), before the gate step, so `make validate`'s extraction (the first
  `run: |` block) still finds the gate; the in-gate fallback uses a private venv, never `pip --user`.
- Chris W1 follow-up C-7 / Sentinel F6: the fallback installs from the same hash-pinned file, and its temp dir
  is removed in every case, also when pip fails.
- W9 wiring (bd v7u.4.7): gate #27 also runs eval/scenarios/core-4.0/check-freeze.sh and the eval/v4-security +
  eval/shadow-floor pytest suites, required in every mode; a missing script or suite is red.
Run: python3 tests/test_gate27_wiring.py   (CI gate #27 runs it; stdlib + bash)
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"


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


def block(first, last):
    lines = gate_script()
    start = next(i for i, l in enumerate(lines) if l.startswith(first))
    stop = next(i for i, l in enumerate(lines) if i > start and l.startswith(last))
    return "\n".join(lines[start:stop]) + "\n"


def a15_block():
    return block("# A15 (router decision", "# W9 eval suites")


def w9_block():
    return block("# W9 eval suites", '[ $fail -eq 0 ] && ok "v4 gate tests')


PRELUDE = "set +e -u -o pipefail\nfail=0\nerr(){ printf '  X %s\\n' \"$*\"; fail=1; }\nok(){ printf '  ok %s\\n' \"$*\"; }\n"


def gate_env(cwd, env_extra=None):
    """The one environment the gate block runs in (and the pytest probe uses): HOME is the scratch cwd."""
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd)}
    env.update(env_extra or {})
    return env


def run_a15(cwd, env_extra=None, with_w9=False, trailer=""):
    script = PRELUDE + a15_block() + (w9_block() if with_w9 else "") + trailer + 'echo "fail=$fail"'
    r = subprocess.run(["bash", "-c", script], cwd=cwd, capture_output=True, text=True, env=gate_env(cwd, env_extra))
    return r.returncode, r.stdout + r.stderr


def this_python_env(cwd):
    """PATH with this interpreter first (setup-python's on CI) and the user site this interpreter resolves now.

    PYTHONUSERBASE is pinned to site.getuserbase() of the running interpreter, not copied from the caller: the gate
    runs with HOME=<cwd>, which would otherwise move the user site (macOS ~/Library/Python/X.Y) away from pytest.
    """
    import site
    return {"PATH": os.path.dirname(sys.executable) + ":/usr/bin:/bin:/usr/local/bin",
            "PYTHONUSERBASE": site.getuserbase()}


def pytest_importable(cwd, env_extra):
    """Probe pytest in exactly the environment run_a15(cwd, env_extra) gives the gate, so probe and run agree."""
    return subprocess.run(["python3", "-c", "import pytest"], cwd=cwd, env=gate_env(cwd, env_extra),
                          capture_output=True).returncode == 0


class A15WiringTest(unittest.TestCase):
    def test_missing_design_run_suite_is_red(self):
        """Bella N1: deleting or renaming tests/test_design_run.py must not leave gate #27 green."""
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = run_a15(pathlib.Path(tmp))
        self.assertIn("fail=1", out, out)
        self.assertIn("X A15 design runner suite", out)
        self.assertIn("tests/test_design_run.py missing", out)

    def test_missing_pytest_without_ci_is_red_not_checked(self):
        """No pytest and not on CI: red 'NOT CHECKED', never a pass (python3 with an empty path)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "tests").mkdir()
            (root / "tests/test_design_run.py").write_text("def test_ok():\n    assert True\n")
            rc, out = run_a15(root, {"PYTHONPATH": str(root / "nothing"), "PYTHONNOUSERSITE": "1",
                                     "PYTHONUSERBASE": str(root / "nobase")})
        if "ok A15" in out:
            self.skipTest("pytest importable from the system python here; the not-checked branch is not reachable")
        self.assertIn("fail=1", out, out)
        self.assertIn("NOT CHECKED", out)

    def test_no_user_site_pip_install_in_ci(self):
        """R2-3: `pip install --user` into the Ubuntu system python can be refused (PEP 668)."""
        self.assertNotIn("pip install --user", a15_block())
        self.assertIn("-m venv", a15_block())

    def test_setup_python_and_pytest_come_before_the_gate_step(self):
        text = CI.read_text()
        gate = text.index("      - name: Invariant + lint gate")
        setup = text.find("uses: actions/setup-python@")
        pip = text.find("-m pip install")
        self.assertTrue(0 <= setup < gate, "actions/setup-python must run before the gate step")
        self.assertTrue(0 <= pip < gate and "-r .github/requirements-ci.txt" in text[pip:text.index("\n", pip)],
                        "pytest must be installed (from the hash-pinned file) before the gate step")
        self.assertIn("pytest==", (ROOT / ".github/requirements-ci.txt").read_text())
        first_block = text.index("        run: |")
        self.assertGreater(first_block, gate, "a `run: |` step before the gate would become make validate's script")

    def test_venv_fallback_installs_from_the_pinned_file(self):
        """C-7: the CI-only fallback pins the same versions and hashes as the setup step."""
        self.assertIn('-m pip install --quiet --require-hashes --only-binary :all: -r .github/requirements-ci.txt',
                      a15_block())
        self.assertNotRegex(a15_block(), r"pip install --quiet pytest")

    def test_venv_temp_dir_is_removed_when_pip_fails(self):
        """C-7: venv created, pip fails -> the temp dir must not be left behind (it was removed on success only)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "bin").mkdir()
            (root / "tmp").mkdir()
            fake = root / "bin/python3"     # no pytest; `-m venv DIR` makes a venv whose pip always fails
            fake.write_text('#!/bin/bash\nif [ "$1" = -m ] && [ "$2" = venv ]; then mkdir -p "$3/bin"; '
                            'printf \'#!/bin/bash\\nexit 1\\n\' > "$3/bin/python"; chmod +x "$3/bin/python"; exit 0; fi\n'
                            'exit 1\n')
            fake.chmod(0o755)
            (root / "tests").mkdir()
            (root / "tests/test_design_run.py").write_text("def test_ok():\n    assert True\n")
            # mktemp -d may ignore TMPDIR (macOS), so the trailer reports the dir the gate made and whether it is gone
            trailer = 'echo "venv-dir=${a15v:-}"; if [ -n "${a15v:-}" ] && [ -e "$a15v" ]; then echo LEFT; fi\n'
            rc, out = run_a15(root, {"PATH": f"{root / 'bin'}:/usr/bin:/bin", "CI": "true", "TMPDIR": str(root / "tmp")},
                              with_w9=True, trailer=trailer)
            made = re.search(r"^venv-dir=(\S+)$", out, re.M)
            if made and "LEFT" in out:
                import shutil
                shutil.rmtree(made.group(1), ignore_errors=True)    # this test's own leftover, never a real dir
            self.assertIn("NOT CHECKED", out, out)
            self.assertIn("fail=1", out)
            self.assertTrue(made, "the venv fallback did not run (no temp dir made)")
            self.assertNotIn("LEFT", out, "venv temp dir left behind when pip failed")

    def test_venv_temp_dir_is_removed_when_the_gate_stops_early(self):
        """U22 iter 2 (Chris L3): an EXIT trap removes the venv dir when the gate stops before the explicit removal
        (here: an `exit` straight after the A15 block, standing in for an interrupt or a `set -u` abort)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "bin").mkdir()
            (root / "tmp").mkdir()
            fake = root / "bin/python3"
            fake.write_text('#!/bin/bash\nif [ "$1" = -m ] && [ "$2" = venv ]; then mkdir -p "$3/bin"; '
                            'printf \'#!/bin/bash\\nexit 1\\n\' > "$3/bin/python"; chmod +x "$3/bin/python"; exit 0; fi\n'
                            'exit 1\n')
            fake.chmod(0o755)
            (root / "tests").mkdir()
            (root / "tests/test_design_run.py").write_text("def test_ok():\n    assert True\n")
            r = subprocess.run(["bash", "-c", PRELUDE + a15_block() + 'echo "venv-dir=${a15v:-}"; exit 3\n'], cwd=root,
                               capture_output=True, text=True,
                               env=gate_env(root, {"PATH": f"{root / 'bin'}:/usr/bin:/bin", "CI": "true",
                                                   "TMPDIR": str(root / "tmp")}))
            made = re.search(r"^venv-dir=(\S+)$", r.stdout, re.M)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertTrue(made, "the venv fallback did not run (no temp dir made)")
            left = pathlib.Path(made.group(1)).exists()
            if left:
                import shutil
                shutil.rmtree(made.group(1), ignore_errors=True)    # this test's own leftover, never a real dir
            self.assertFalse(left, "venv temp dir left behind when the gate stopped early")

    def test_pyt_mktemp_failure_is_red_and_runs_no_pytest(self):
        """U22 iter 2 (Chris L3): pyt's `mktemp -d` failing used to leave h empty and run pytest with HOME=/home,
        GIT_CONFIG_GLOBAL=/gitconfig (a non-hermetic run that could pass). It must be red and run nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            env = this_python_env(root)
            if not pytest_importable(root, env):
                self.skipTest("pytest not importable from this interpreter")
            (root / "bin").mkdir()
            fake = root / "bin/mktemp"
            fake.write_text("#!/bin/sh\necho 'mktemp: stub failure' >&2\nexit 1\n")
            fake.chmod(0o755)
            env["PATH"] = f"{root / 'bin'}:{env['PATH']}"
            (root / "tests").mkdir()
            (root / "tests/test_design_run.py").write_text("def test_ok():\n    assert True\n")
            rc, out = run_a15(root, env)
        self.assertIn("pyt: mktemp -d failed -- pytest not run", out, out)
        self.assertIn("A15 design runner suite red", out, out)
        self.assertNotIn("ok A15", out, out)
        self.assertIn("fail=1", out)


class W9WiringTest(unittest.TestCase):
    """bd v7u.4.7 W9 wiring: core-4.0 freeze + the two eval pytest suites run in gate #27, required in every mode."""

    def stub_tree(self, root, freeze_rc=0, suite_ok=True):
        (root / "tests").mkdir()
        (root / "tests/test_design_run.py").write_text("def test_ok():\n    assert True\n")
        freeze = root / "eval/scenarios/core-4.0/check-freeze.sh"
        freeze.parent.mkdir(parents=True)
        freeze.write_text(f'echo "core-4.0 freeze stub"; exit {freeze_rc}\n')
        for d in ("eval/v4-security/tests", "eval/shadow-floor/tests"):
            (root / d).mkdir(parents=True)
        (root / "eval/v4-security/tests/test_w9_stub_a.py").write_text("def test_a():\n    assert True\n")
        (root / "eval/shadow-floor/tests/test_w9_stub_b.py").write_text(
            "def test_b():\n    assert %s\n" % ("True" if suite_ok else "False"))

    def test_missing_w9_parts_are_red(self):
        """Sentinel W10a FU-4: each missing part is its own `X` (err) line -- fail=1 alone could come from another
        part, so an `ok` (or silent) line for one of them would pass a fail=1-only assertion."""
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = run_a15(pathlib.Path(tmp), with_w9=True)
        self.assertIn("fail=1", out)
        for needle in ("W9 core-4.0 freeze: eval/scenarios/core-4.0/check-freeze.sh missing -- NOT CHECKED",
                       "W9 eval suite: eval/v4-security/tests missing -- NOT CHECKED",
                       "W9 eval suite: eval/shadow-floor/tests missing -- NOT CHECKED"):
            with self.subTest(needle=needle):
                self.assertRegex(out, r"(?m)^  X " + re.escape(needle), out)

    def test_each_missing_w9_part_alone_is_red(self):
        """FU-4: one part missing, the other two present and green -> still red, from that part's own err line."""
        for missing in ("eval/scenarios/core-4.0/check-freeze.sh", "eval/v4-security/tests", "eval/shadow-floor/tests"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                env = this_python_env(root)
                if not pytest_importable(root, env):
                    self.skipTest("pytest not importable from this interpreter")
                self.stub_tree(root)
                import shutil
                (shutil.rmtree if (root / missing).is_dir() else os.remove)(root / missing)
                rc, out = run_a15(root, env, with_w9=True)
                self.assertIn("fail=1", out, out)
                self.assertRegex(out, r"(?m)^  X W9 [^\n]*" + re.escape(missing) + " missing -- NOT CHECKED", out)
                self.assertNotRegex(out, r"(?m)^  X (?!W9 [^\n]*" + re.escape(missing) + ")", out)  # nothing else red

    def test_ci_wiring_and_the_other_unit_suites_are_in_the_always_required_loop(self):
        """Chris W10a-C5: CI runs tests/test_ci_wiring.py (and the other eight) only from #27's loop; dropping one
        from the list would stop checking it and stay green."""
        lines = gate_script()
        loop = [l for l in lines if re.match(r"for t in test_[\w ]+; do", l)]
        self.assertEqual(1, len(loop), loop)
        body = lines[lines.index(loop[0]) + 1]
        names = re.match(r"for t in ([\w ]+); do", loop[0]).group(1).split()
        self.assertEqual(["test_agent_tools_pin", "test_skill_names", "test_shipped_text_lint", "test_floor",
                          "test_gate27_wiring", "test_ci_wiring", "test_ux_design_runbooks", "test_eval_runners",
                          "test_reference_toc"], names)
        for name in names:
            self.assertTrue((ROOT / "tests" / f"{name}.py").is_file(), name)
        self.assertIn('python3 tests/$t.py >/dev/null 2>&1 || { err "tests/$t.py red', body)

    def test_green_red_and_freeze_red(self):
        for freeze_rc, suite_ok, want in ((0, True, None), (0, False, "X W9 eval suites red"),
                                          (1, True, "X W9 core-4.0 freeze red")):
            with self.subTest(freeze_rc=freeze_rc, suite_ok=suite_ok), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                env = this_python_env(root)
                if not pytest_importable(root, env):
                    self.skipTest("pytest not importable from this interpreter")
                self.stub_tree(root, freeze_rc, suite_ok)
                rc, out = run_a15(root, env, with_w9=True)
                if want is None:
                    self.assertIn("fail=0", out, out)
                    self.assertIn("ok W9 core-4.0 freeze stub", out)
                    self.assertRegex(out, r"ok W9 eval suites \(2 passed")
                else:
                    self.assertIn("fail=1", out, out)
                    self.assertIn(want, out)

    def test_w9_runs_the_real_paths(self):
        w9 = w9_block()
        for path in ("eval/scenarios/core-4.0/check-freeze.sh", "eval/v4-security/tests", "eval/shadow-floor/tests"):
            self.assertIn(path, w9)
            self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
