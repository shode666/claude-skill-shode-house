"""Git isolation helper for the design-run tests (ADR iter 5 addendum 2, section 5.6.12).

This is the ONE module in the W12 test tree that starts a git process or writes "global" git
config. Every git process it starts carries HOME, GIT_CONFIG_GLOBAL and XDG_CONFIG_HOME pointing
into the test's own temporary directory, plus GIT_CONFIG_NOSYSTEM=1. It refuses, before exec,
when any of the four is missing or points outside that directory, and it never passes --system.

Why: a scratch script once rewrote a developer's real ~/.gitconfig (incident shode-house-2g0).
"""
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

ISOLATION_KEYS = ("HOME", "GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM")
GIT_ABS = shutil.which("git")  # resolved once, at import; tests never pass a bare name to exec
_IDENTITY = {
    "GIT_AUTHOR_NAME": "design-run-test", "GIT_AUTHOR_EMAIL": "design-run@test.invalid",
    "GIT_COMMITTER_NAME": "design-run-test", "GIT_COMMITTER_EMAIL": "design-run@test.invalid",
}


class IsolationError(RuntimeError):
    """Raised instead of starting git when the environment is not isolated."""


def isolation_env(tmp):
    """The four isolating variables for one test directory (directories are created)."""
    tmp = Path(tmp)
    home, xdg = tmp / "home", tmp / "xdg"
    home.mkdir(parents=True, exist_ok=True)
    xdg.mkdir(parents=True, exist_ok=True)
    return {
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "XDG_CONFIG_HOME": str(xdg),
        "GIT_CONFIG_NOSYSTEM": "1",
    }


def _inside(path, tmp):
    real_tmp = os.path.realpath(str(tmp))
    real = os.path.realpath(path)
    return real == real_tmp or real.startswith(real_tmp + os.sep)


def assert_isolated(env, tmp):
    """Raise IsolationError unless all four variables are present and point under tmp."""
    for key in ISOLATION_KEYS:
        if not env.get(key):
            raise IsolationError("missing " + key)
    if env["GIT_CONFIG_NOSYSTEM"] != "1":
        raise IsolationError("GIT_CONFIG_NOSYSTEM must be 1")
    for key in ("HOME", "GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME"):
        if not _inside(env[key], tmp):
            raise IsolationError(key + " points outside the test directory")


def base_env(tmp, path=None):
    env = {"PATH": path or os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C", "LC_ALL": "C"}
    env.update(isolation_env(tmp))
    env.update(_IDENTITY)
    return env


def git_isolated(argv, tmp, cwd=None, input=None, check=True, env_override=None, extra_env=None):
    """Run git with the isolating environment. env_override exists only for refusal tests."""
    env = dict(env_override) if env_override is not None else base_env(tmp)
    if extra_env:
        clash = set(extra_env) & set(ISOLATION_KEYS)
        if clash:
            raise IsolationError("extra_env may not override " + ", ".join(sorted(clash)))
        env.update(extra_env)
    assert_isolated(env, tmp)
    if "--system" in argv:
        raise IsolationError("--system is banned")
    if cwd is not None and not _inside(str(cwd), tmp):
        raise IsolationError("cwd outside the test directory")
    proc = subprocess.run(
        [GIT_ABS, "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false"] + list(argv),
        cwd=str(cwd) if cwd else None, env=env, input=input,
        stdin=None if input is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, timeout=60,
    )
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (argv[:2], proc.stderr.decode(errors="replace")))
    return proc


def config_global(tmp, key, value):
    """Write a key to the test's own global config (<tmp>/home/.gitconfig) through git."""
    return git_isolated(["config", "--global", key, value], tmp)


def runner_env(tmp, path, extra=None):
    """Environment for a runner under test: same isolated HOME (the runner drops GIT_*/XDG)."""
    env = base_env(tmp, path=path)
    env["TMPDIR"] = str(Path(tmp) / "runner-tmp")
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    if extra:
        env.update(extra)
    return env


# --- test_git_isolation (c): real config untouched -------------------------------------------

def real_home():
    return pwd.getpwuid(os.getuid()).pw_dir  # never $HOME


def system_config_candidates():
    """System gitconfig paths the host git may use, found without running `git config --system`.

    Sentinel X16: Apple Git keeps it under the developer-tools prefix, Homebrew under its prefix.
    """
    cands = [
        "/etc/gitconfig",
        "/usr/local/etc/gitconfig",
        "/opt/homebrew/etc/gitconfig",
        "/Library/Developer/CommandLineTools/usr/share/git-core/gitconfig",
        "/Applications/Xcode.app/Contents/Developer/usr/share/git-core/gitconfig",
    ]
    dev = os.environ.get("DEVELOPER_DIR")
    if dev:
        cands.append(os.path.join(dev, "usr/share/git-core/gitconfig"))
    if GIT_ABS:
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(GIT_ABS)))
        cands += [os.path.join(prefix, "etc/gitconfig"), os.path.join(prefix, "share/git-core/gitconfig")]
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def watched_config_paths(original_xdg=None):
    home = real_home()
    paths = [os.path.join(home, ".gitconfig"), os.path.join(home, ".config/git/config")]
    if original_xdg:
        paths.append(os.path.join(original_xdg, "git/config"))
    return paths + system_config_candidates()


def stat_snapshot(paths):
    """Metadata only (inode, size, mtime_ns) or None when absent; content is never read."""
    snap = {}
    for p in paths:
        try:
            st = os.stat(p)
            snap[p] = (st.st_ino, st.st_size, st.st_mtime_ns)
        except FileNotFoundError:
            snap[p] = None
    return snap


# --- test_git_isolation (a): static scan --------------------------------------------------------

_SCAN_PATTERNS = (
    ("config-global-or-system", re.compile(r"config['\"]?\s*,?\s*['\"]?--(?:global|system)\b")),
    ("git-argv0", re.compile(r"(?<![\w\])'\"])\[\s*['\"]git['\"]\s*[,\]]")),
    ("git-argv0-call", re.compile(r"(?:run|Popen|call|check_output|check_call)\(\s*['\"]git\b")),
    ("git-config-global-assignment", re.compile(r"GIT_CONFIG_GLOBAL['\"]?\s*\]?\s*(?:=|:)")),
)


def static_scan(paths):
    """Return (file, line_no, pattern_name) for every hit outside this helper module."""
    me = os.path.realpath(__file__)
    hits = []
    for p in paths:
        if os.path.realpath(p) == me:
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            for no, line in enumerate(fh, 1):
                for name, rx in _SCAN_PATTERNS:
                    if rx.search(line):
                        hits.append((str(p), no, name))
    return hits
