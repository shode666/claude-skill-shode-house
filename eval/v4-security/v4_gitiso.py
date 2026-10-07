"""W9's git isolation helper (ADR iter 5 addendum 2 section 5.6.12; UD R28, incident shode-house-2g0).

The ONE module under eval/v4-security/ and eval/shadow-floor/ that starts a git process. Every git
process gets HOME, GIT_CONFIG_GLOBAL and XDG_CONFIG_HOME inside the caller's temporary directory and
GIT_CONFIG_NOSYSTEM=1. It refuses before exec when any of the four is missing or points outside that
directory, when `--system` appears, or when cwd is outside it. A "global" config in a fixture is
<tmp>/home/.gitconfig, never the developer's file.
"""
import json
import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

ISOLATION_KEYS = ("HOME", "GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM")
GIT_ABS = shutil.which("git")
IDENTITY = {"GIT_AUTHOR_NAME": "w9-eval", "GIT_AUTHOR_EMAIL": "w9-eval@test.invalid",
            "GIT_COMMITTER_NAME": "w9-eval", "GIT_COMMITTER_EMAIL": "w9-eval@test.invalid"}


class IsolationError(RuntimeError):
    """Raised instead of starting git when the environment is not isolated."""


def isolation_env(tmp):
    tmp = Path(tmp)
    home, xdg = tmp / "home", tmp / "xdg"
    home.mkdir(parents=True, exist_ok=True)
    xdg.mkdir(parents=True, exist_ok=True)
    return {"HOME": str(home), "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"), "XDG_CONFIG_HOME": str(xdg),
            "GIT_CONFIG_NOSYSTEM": "1"}


def _inside(path, tmp):
    real_tmp, real = os.path.realpath(str(tmp)), os.path.realpath(str(path))
    return real == real_tmp or real.startswith(real_tmp + os.sep)


def assert_isolated(env, tmp):
    for key in ISOLATION_KEYS:
        if not env.get(key):
            raise IsolationError("missing " + key)
    if env["GIT_CONFIG_NOSYSTEM"] != "1":
        raise IsolationError("GIT_CONFIG_NOSYSTEM must be 1")
    for key in ("HOME", "GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME"):
        if not _inside(env[key], tmp):
            raise IsolationError(key + " points outside the temporary directory")


def base_env(tmp, path=None):
    env = {"PATH": path or os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C", "LC_ALL": "C"}
    env.update(isolation_env(tmp))
    env.update(IDENTITY)
    return env


def git_isolated(argv, tmp, cwd=None, check=True, env_override=None):
    """Run git with the isolating environment. env_override exists only for the refusal tests."""
    env = dict(env_override) if env_override is not None else base_env(tmp)
    assert_isolated(env, tmp)
    if "--system" in argv:
        raise IsolationError("--system is banned")
    if cwd is not None and not _inside(cwd, tmp):
        raise IsolationError("cwd outside the temporary directory")
    if not GIT_ABS:
        raise IsolationError("git not found")
    proc = subprocess.run([GIT_ABS, "-c", "init.defaultBranch=main", "-c", "commit.gpgsign=false",
                           "-c", "core.hooksPath=/dev/null"] + list(argv),
                          cwd=str(cwd) if cwd else None, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, timeout=60)
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (argv[:2], proc.stderr.decode(errors="replace")))
    return proc


def runner_env(tmp, path=None):
    """Environment for the design runner under test: same isolated HOME (the runner drops GIT_*/XDG)."""
    env = base_env(tmp, path=path)
    env["TMPDIR"] = str(Path(tmp) / "runner-tmp")
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    return env


def work_tree_of(path):
    """The nearest ancestor (or the path itself) holding a `.git` entry, else None. Files only, no git process."""
    p = os.path.realpath(str(path))
    while True:
        if os.path.lexists(os.path.join(p, ".git")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def assert_outside_work_tree(tmp):
    """Fixture builders refuse a temporary directory inside a git work tree (section 5.6.12 rule 4): a fixture
    repository there would be nested in, and could act on, that checkout (for example the shode-house tree)."""
    top = work_tree_of(tmp)
    if top:
        raise IsolationError("refuse: %s is inside the git work tree %s; use a scratch directory outside any "
                             "repository" % (tmp, top))


# ---- live W11 sessions (r0 / g10c): the model's own git calls run under the isolating env (F5) -----------------
LIVE_KEYS = ("GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME", "GIT_CONFIG_NOSYSTEM")


def live_session_env(tmp):
    """Variables the live session (the claude process and so every Bash call of the model) must carry. HOME is
    left to the operator (the CLI needs its login); git reads no global or system file of the operator's."""
    env = isolation_env(tmp)
    return {k: env[k] for k in LIVE_KEYS}


def session_begin(tmp, record_path):
    assert_outside_work_tree(tmp)
    rec = {"tmp": os.path.realpath(str(tmp)), "env": live_session_env(tmp),
           "watched": watched_config_paths(os.environ.get("XDG_CONFIG_HOME")), "after": None}
    rec["before"] = {k: list(v) if v else None for k, v in stat_snapshot(rec["watched"]).items()}
    with open(record_path, "x", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def session_end(record_path):
    rec = json.load(open(record_path, encoding="utf-8"))
    rec["after"] = {k: list(v) if v else None for k, v in stat_snapshot(rec["watched"]).items()}
    with open(record_path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def session_record_problems(rec):
    """Why a session record does not evidence an isolated live session ([] = it does)."""
    out = []
    env, tmp = rec.get("env") or {}, rec.get("tmp") or ""
    if env.get("GIT_CONFIG_NOSYSTEM") != "1":
        out.append("GIT_CONFIG_NOSYSTEM is not 1")
    for k in ("GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME"):
        if not env.get(k) or not tmp or not _inside(env[k], tmp):
            out.append("%s not set inside the session tmp" % k)
    if not tmp or work_tree_of(tmp):
        out.append("session tmp missing or inside a git work tree")
    if not rec.get("before") or rec.get("after") is None:
        out.append("no before/after config stat")
    elif rec["before"] != rec["after"]:
        changed = sorted(k for k in rec["before"] if rec["before"].get(k) != rec["after"].get(k))
        out.append("operator git config metadata changed: %s" % changed)
    return out


# ---- test_git_isolation (c): real config untouched ----------------------------------------------------
def real_home():
    return pwd.getpwuid(os.getuid()).pw_dir          # never $HOME


def watched_config_paths(original_xdg=None):
    home = real_home()
    paths = [os.path.join(home, ".gitconfig"), os.path.join(home, ".config/git/config"), "/etc/gitconfig",
             "/usr/local/etc/gitconfig", "/opt/homebrew/etc/gitconfig"]
    if original_xdg:
        paths.append(os.path.join(original_xdg, "git/config"))
    if GIT_ABS:
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(GIT_ABS)))
        paths += [os.path.join(prefix, "etc/gitconfig"), os.path.join(prefix, "share/git-core/gitconfig")]
    return sorted(set(paths))


def stat_snapshot(paths):
    """inode, size, mtime_ns per path, or None when absent. Content is never read."""
    snap = {}
    for p in paths:
        try:
            st = os.stat(p)
            snap[p] = (st.st_ino, st.st_size, st.st_mtime_ns)
        except FileNotFoundError:
            snap[p] = None
    return snap


# ---- test_git_isolation (a): static scan -------------------------------------------------------------
SCAN_PATTERNS = (
    ("config-global-or-system", re.compile(r"config['\"]?\s*,?\s*['\"]?--(?:global|system)\b")),
    ("git-argv0", re.compile(r"(?<![\w\])'\"])\[\s*['\"]git['\"]\s*[,\]]")),
    ("git-argv0-call", re.compile(r"(?:run|Popen|call|check_output|check_call)\(\s*['\"]git\b")),
    ("git-config-global-assignment", re.compile(r"GIT_CONFIG_GLOBAL['\"]?\s*\]?\s*(?:=|:)")),
)
SHELL_PATTERNS = (
    ("shell-git", re.compile(r"(?:^|[\s;&|(`\"'])git\s+(?:-c\s+\S+\s+)*(?:config|init|commit|add|clone)\b")),
)


def static_scan(paths):
    """(file, line, pattern) for every hit outside this module. A line that calls git_isolated( goes through
    the helper and is isolated by construction; shell files are also scanned for a bare `git config|init|...`."""
    me = os.path.realpath(__file__)
    hits = []
    for p in paths:
        if os.path.realpath(str(p)) == me:
            continue
        pats = SCAN_PATTERNS + (SHELL_PATTERNS if str(p).endswith(".sh") else ())
        with open(p, encoding="utf-8", errors="replace") as fh:
            for no, line in enumerate(fh, 1):
                if "git_isolated(" in line:
                    continue
                for name, rx in pats:
                    if rx.search(line):
                        hits.append((str(p), no, name))
    return hits


def main(argv):
    """python3 v4_gitiso.py session-begin <tmp-dir> <record.json>   -> prints the export lines for the session
       python3 v4_gitiso.py session-end <record.json>                -> exit 1 when the operator's config changed
    Copy the finished record to <run-dir>/raw/session-env.json; score_v4.py checks it (expect `session_env`)."""
    import sys
    if len(argv) == 3 and argv[0] == "session-begin":
        rec = session_begin(argv[1], argv[2])
        for k, v in rec["env"].items():
            print("export %s=%s" % (k, v))
        return 0
    if len(argv) == 2 and argv[0] == "session-end":
        problems = session_record_problems(session_end(argv[1]))
        for p in problems:
            sys.stderr.write(p + "\n")
        return 1 if problems else 0
    sys.stderr.write(main.__doc__ + "\n")
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
