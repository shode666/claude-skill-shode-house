#!/usr/bin/env python3
"""design_run.py -- launch the plugin's design-intel scripts and a fixed list of project-installed
UI tools from a router-written, sha256-pinned order. Python 3 standard library only.

Usage (by the design-run executor only; never edit this command):
    python3 -I "<plugin root>/references/design-intel/scripts/design_run.py" --order <path> --sha256 <hex64>

Wall clock: the whole invocation aims to stay inside RUN_BUDGET_S (540 s; every template timeout
is at most 540 s). A run starts its pre-run checks only while the budget left minus
POST_RUN_RESERVE_S (30 s, kept for the kill wait, drain, re-walk and report) is at least MIN_RUN_S;
otherwise it is skipped (`budget-exhausted`). Its timeout is computed again immediately before its
child starts, as the budget left minus POST_RUN_RESERVE_S, with the same skip below MIN_RUN_S. The
pre-run checks and the post-run tail are bounded only by their own caps (each walk 20 s, each git
call 30 s, kill wait 10 s, drain 2 s), so 540 s is a target, not a bound. For an E3 run the pre-run
checks are at most 17 git calls and 2 walks (550 s), and the post-run tail at most 5 git calls, 1
walk, the kill wait and the drain (182 s). Worst case: about 1,060 s when the run is then skipped
at the late check (550 s after an early check that saw 31 s left), or about 690 s when a child ran
(182 s against the 30 s reserve). Only one run per invocation can overshoot (the next is skipped at
the early check), and these figures need every git call or walk near its cap. The host tool call
gets at least 600 s (for example an explicit 600000 ms Bash timeout): that makes a host timeout
before the runner finishes rare, not impossible.

Signals: the first SIGTERM, SIGHUP or SIGINT kills the running child's process group, marks the
running run `terminated`, writes the report (exit 1) or, when no report exists yet, prints
`design-run: terminated (<signal>)` on stderr (exit 4), and removes the private directory; later
TERM/HUP/INT are ignored until that cleanup is done. A SIGINT that was already ignored when the
runner started stays ignored. SIGKILL of the runner cannot be handled (residual), and it
leaves behind: (1) orphans re-parented to pid 1 -- the project binary's process group and anything
it detached (Playwright launches the browser in its own process group); (2) a 0-byte
`<stem>.report.json` plus the run directory, which make a retry fail closed with
`design-run-output-exists` until they are deleted; (3) the private directory `$TMPDIR/design-run-*`
holding the run's UNREDACTED raw stdout/stderr and staged artifacts. Cleaning these up (killing
the orphans, deleting the files) is done by the user, or by the router with the user's authority,
never by the executor, which runs no kill, rm or other cleanup command and reports what it saw.
Whether a host tool timeout sends SIGTERM or SIGKILL is host-specific.

The order names a designer-written request (data only). Every argv is built by this file from
design_run_catalogue.json (loaded next to this file, never from the project, schema-checked at
start) and run with shell=False. Nothing but the runner's own safe `git` calls starts before every
check passed.

Exit codes
    0  every run exited 0
    1  at least one run exited non-zero, timed out, was tree-changed or skipped, or the runner was
       terminated by a signal after its report was opened
    2  CLI usage error
    3  BLOCKED (printed on stderr as `BLOCKED: <token> <detail>`); no project binary, package
       manager, node or plugin script was started, and no report or run directory is left
    4  internal error (redacted traceback in the report, or on stderr when no report exists), or
       a signal before the report was opened

Order of operations (all-or-nothing up to step 8):
    0 interpreter tripwire, sanitised PATH, absolute git      5 validate every run and param
    0a git version gate (cwd=/)                               6 resolve every binary (lstat/realpath)
    1 local git-config scan                                   7 tree check E1-E3
    2 cwd == work-tree top level                              8 exclusive output dir, private temp dir
    2a gitlink check E0 (before any `git status`)             9 per run: E0 first, E1-E3 again,
    3 order file, 4 request file (read once, hash, strict JSON)  execute, post-run diff, stage-out,
                                                                 redact (deny set re-read before
                                                                 every `git status`)

E3 enumerates candidate spec files by walking the file system the way Playwright does (scandir,
no symlinks, only `node_modules` skipped, directories named `.git` entered), because git never
lists a path under a directory named `.git`. The walk is capped (entries, seconds) and fails closed.
Any walked file under a directory named `.git` with a test-file extension blocks, whatever the
project's `testMatch` says (nothing there is ever tracked). Each run's pre-run checks start with
E0, then the walk signature and the pre-run snapshot, then the tree check, so an edit of a
work-tree file after the signature and snapshot is either refused by that check or differs from
them after the run. Git-internal inputs that change what git itself runs (the deny set in config,
every scope, and `info/attributes`) are read again immediately before every `git status` of
steps 7 and 9: a project-controlled deny-set key, or any deny-set record (user scope included) not
present at step 1, refuses the run before its child or makes it `tree-changed` after it, instead
of being run by the runner's git (a plant in the milliseconds between that read and the `status`
remains, as between steps 1 and 7). Not re-read: the global attributes file
(`$HOME/.config/git/attributes`) and the contents of a user-trusted `core.attributesFile`; a change
there can only name a filter driver the user's own config already defined at step 1. An OSError
in a run's pre-run checks or post-run inspection makes the run `tree-changed`. After each E3 run
the walk is repeated: a file E3 would block that appeared or changed while the child ran makes the
run `tree-changed`. Prevention is impossible in-process (check-then-use), and detection is
best-effort: a payload that runs can remove its own trace (a file planted and removed during the
run is in neither listing); prevention would require running from a private snapshot of the
tracked tree (out of W12 scope).

Redaction is a pattern backstop: an unknown token format can pass, and screenshots are copied
unredacted. Known residuals of the rule shapes: a token preceded by a letter or digit is not
matched (except a GitHub `gh[pousr]_` token, whose length is fixed), because removing that
boundary would redact ordinary names such as `risk-<16 chars>`; a GitHub token with a letter or
digit on both sides (`x` + `ghp_<36>` + `y`) is matched by neither rule; a non-ASCII space, a
mark or a quote between `Bearer` / `key=` and its value defeats those rules (a report value or
shown name whose JSON-escaped form then matches a rule is withheld whole, so the report bytes never
match); a token split by a space stays split. Global and system git config, as read at step 1, are treated as the user's own
(bypass-permissions mode voids that assumption).
"""
import argparse
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

RUNNER_VERSION = "2.0.0"
SCRIPTS_DIR = Path(__file__).resolve().parent
CATALOGUE_PATH = Path(__file__).resolve().parent / "design_run_catalogue.json"

EXIT_OK, EXIT_RUN_FAILED, EXIT_USAGE, EXIT_BLOCKED, EXIT_INTERNAL = 0, 1, 2, 3, 4
MAX_INPUT_BYTES = 64 * 1024
STREAM_CAP = 5 * 1024 * 1024
ARTIFACT_CAP = 20 * 1024 * 1024
GIT_TIMEOUT_S = 30
GIT_VERSION_TIMEOUT_S = 10
RUN_BUDGET_S = 540              # whole invocation; below the host Bash tool maximum (600 s)
MAX_TEMPLATE_TIMEOUT_S = 540
MIN_RUN_S = 1.0                 # a run with less budget left is skipped (budget-exhausted)
POST_RUN_RESERVE_S = 30.0       # kept back from each run's timeout for kill wait, drain, re-walk, report
DRAIN_GRACE_S = 2.0             # pipe drain after the child exits (a grandchild may hold the pipe)
WALK_MAX_ENTRIES = 200000       # E3 file-system walk caps; hitting one blocks (fail closed)
WALK_MAX_SECONDS = 20.0
MIN_GIT = (2, 26)
SAFE_GIT_PREFIX = ("--no-optional-locks", "--no-pager", "-c", "core.fsmonitor=false",
                   "-c", "core.untrackedCache=false", "-c", "core.hooksPath=/dev/null")
STATUS_EXTRA = ("--ignore-submodules=all",)
GIT_ENV_NAMES = ("HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR")
CHILD_ENV_NAMES = GIT_ENV_NAMES + ("PLAYWRIGHT_BROWSERS_PATH",)
DATA_EXTENSIONS = (".md", ".json", ".png", ".jpg", ".svg", ".txt", ".log")
DATA_ROOTS = ("outputs/", "design-system/")
INERT_BASENAMES = (".DS_Store", "Thumbs.db", "desktop.ini")
LOCKFILES = ("pnpm-lock.yaml", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "bun.lockb", "bun.lock")
PLAYWRIGHT_CONFIGS = ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs",
                      "playwright.config.cjs")
# Playwright 1.63 collectFilesForProject: the extensions a test file may have
TEST_FILE_EXTS = ("js", "cjs", "mjs", "ts", "cts", "mts", "jsx", "tsx", "mjsx", "mtsx", "cjsx", "ctsx")
TEXT_ARTIFACT_EXTS = (".json", ".txt", ".log")
DEVOPS_HINT = "ask `shode-house:operate` to add `%s` to the project's dev dependencies and install it"
# Isolated mode keeps the script's own directory off sys.path, and search.py imports its siblings,
# so plugin scripts start through this fixed bootstrap: it adds only the plugin script directory.
BOOTSTRAP = ("import os,runpy,sys;s=sys.argv[1];sys.argv=sys.argv[1:];"
             "sys.path.insert(0,os.path.dirname(s));runpy.run_path(s,run_name='__main__')")

TASK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
ORDER_PATH_RE = re.compile(r"outputs/(?P<task>[A-Za-z0-9][A-Za-z0-9._-]{0,63})/[0-9]{2}-design-run-order-"
                           r"(?P<phase>1b|3a)-iter(?P<iter>[1-3])\.json")
SHA_RE = re.compile(r"[0-9a-f]{64}")
RUN_ID_RE = re.compile(r"r[0-9]{1,2}")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")
URL_PATH_RE = re.compile(r"(/[A-Za-z0-9._~-]*)*")
URL_QUERY_RE = re.compile(r"[A-Za-z0-9_-]{1,32}=[A-Za-z0-9_-]{0,64}(&[A-Za-z0-9_-]{1,32}=[A-Za-z0-9_-]{0,64}){0,4}")
GIT_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)")
# URL netlocs are matched as ASCII before any parser reads them (no `+3000`, no non-ASCII digits)
LOOPBACK_NETLOC_RE = re.compile(r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?", re.I | re.A)
URL_HEAD_RE = re.compile(r"(https?)://([^/?#]*)", re.I | re.A)
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
BAD_CATEGORIES = ("Cc", "Cf", "Cs", "Co")
TEXT_BAD_CATEGORIES = BAD_CATEGORIES + ("Cn", "Zl", "Zp")
# characters that can split a token inside a shown name; removed only to test for a hidden token
# (combining marks too, Sentinel S13b-4: stripping a mark from an ordinary name leaves its letters)
HIDING_CATEGORIES = BAD_CATEGORIES + ("Mn", "Me")

ORDER_KEYS = {"schema", "task", "phase", "iter", "request_path", "request_sha256", "change_paths",
              "loopback_ports", "change_confirmation"}
ORDER_REQUIRED = {"schema", "task", "phase", "iter", "request_path", "request_sha256", "change_paths"}
REQUEST_KEYS = {"schema", "task", "phase", "iter", "runs"}
RUN_KEYS = {"id", "script_id", "params"}

# catalogue schema (checked at start; an unknown value blocks rather than switching a check off)
CAT_TEMPLATE_KEYS = {"phases", "runner", "argv", "params", "executes", "e3", "writes", "artifacts", "network",
                     "stdout_json", "timeout_s"}
CAT_OPTIONAL_KEYS = {"script", "bin", "spec"}
CAT_RUNNERS = ("plugin-python", "project-bin")
CAT_EXECUTES = ("spec", "playwright-config", "package-json", "lockfiles", "tracked-specs")
CAT_E3 = (None, "spec", "default-pattern")
CAT_PHASES = ("1b", "3a")
CAT_NETWORK = ("none", "loopback", "url")
CAT_PARAM_KINDS = ("text", "slug", "hex_color", "run_ref", "url")


class Blocked(Exception):
    """A step 0-8 failure: exit 3, nothing but safe git calls started."""

    def __init__(self, token, detail=""):
        super().__init__(token)
        self.token = token
        self.detail = detail


# ----------------------------------------------------------------------------------------------
# redaction (one pattern set for streams, argv, BLOCKED details, tracebacks and text artifacts)
# ----------------------------------------------------------------------------------------------

REDACTED = "<REDACTED>"
_KEYWORDS = (r"(?:token|secret|password|passwd|pwd|api[_-]?key|access[_-]?key|private[_-]?key|"
             r"client[_-]?secret|authorization|set-cookie|cookie)")
_KEY = r"[A-Za-z0-9_.-]*" + _KEYWORDS + r"[A-Za-z0-9_.-]*"
_REDACTIONS = (
    (re.compile(r"-----BEGIN ([A-Z0-9 ]*?)PRIVATE KEY-----.*?-----END \1PRIVATE KEY-----", re.S), REDACTED),
    (re.compile(r'("' + _KEY + r'"\s*:\s*")(?!<REDACTED>")((?:[^"\\]|\\.)+)(")', re.I), r"\1" + REDACTED + r"\3"),
    (re.compile(r"\b(Bearer)(\s+)(?!<REDACTED>)([A-Za-z0-9._~+/=-]+)", re.I), r"\1\2" + REDACTED),
    (re.compile(r"\b(Basic)(\s+)(?!<REDACTED>)([A-Za-z0-9+/]{8,}={0,2})"), r"\1\2" + REDACTED),
    (re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)(?!<REDACTED>@)([^/\s@\"'<>]+)@"), r"\1" + REDACTED + "@"),
    (re.compile(r"((?<![A-Za-z0-9])" + _KEY + r"[ \t]*[=:][ \t]*)([\"']?)(?!<REDACTED>)([^\s\"'&,;]+)", re.I),
     r"\1\2" + REDACTED),
    # a GitHub token has a fixed length, so it needs no left boundary (a letter before it, Sentinel S13b-4)
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])"), REDACTED),
    (re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|"
                r"sk-[A-Za-z0-9_-]{16,}|xox[abprs]-[A-Za-z0-9-]{10,}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
                r"glpat-[A-Za-z0-9_-]{16,}|npm_[A-Za-z0-9]{16,}|"
                r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,})"), REDACTED),
)


# an AWS key id in any case, for a git config key only (Sentinel S29-1; see _show_config_key)
AWS_ID_ANY_CASE_RE = re.compile(r"(?i)(?:akia|asia)[a-z0-9]{16}")


def _redact(text):
    """Return (redacted text, number of replacements)."""
    total = 0
    for rx, repl in _REDACTIONS:
        text, n = rx.subn(repl, text)
        total += n
    return text, total


def _redact_bytes(data):
    text, n = _redact(data.decode("utf-8", "surrogateescape"))
    return text.encode("utf-8", "surrogateescape"), n


def _r(text):
    return _redact(text)[0]


# a backslash escape as repr() / json.dumps print it; its last character is a letter or digit
ESCAPE_SEQ_RE = re.compile(r"(\\+(?:[abfnrtv]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}))")


def _redact_escaped(text):
    """_redact, then _redact again on each run of text between backslash escapes, for text that
    already holds escapes (a traceback): `\\n`, `\\x1b` or `\\u200b` right before a token would
    otherwise defeat the token rules' left boundary (Sentinel S13b-1)."""
    text, n = _redact(text)
    parts = ESCAPE_SEQ_RE.split(text)
    for i in range(0, len(parts), 2):
        parts[i], m = _redact(parts[i])
        n += m
    return "".join(parts), n


# ----------------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------------

def _is_isolated():
    return bool(sys.flags.isolated)


def _inside(path, anchor):
    return path == anchor or path.startswith(anchor.rstrip(os.sep) + os.sep)


def _origin_in_project(path, anchors):
    """Realpath compare: a symlink from outside into the project, or /tmp -> /private/tmp, counts."""
    real = os.path.realpath(path)
    return any(_inside(real, a) for a in anchors)


def _escape(path):
    """JSON-escape a path that holds odd characters (no redaction; use _show for output)."""
    if any(unicodedata.category(c) in BAD_CATEGORIES for c in path):
        return json.dumps(path)
    return path


def _show_redacted(path):
    """A project- or child-chosen path as printed in a BLOCKED line or report, with the number of
    replacements (Sentinel S13-1). Redaction runs on the raw string first, because an escape such as
    `\\n`, `\\t` or `\\u200b` ends in a letter that defeats the token rules' left boundary; then
    the escaped text is redacted again. A name whose odd characters or combining marks split or
    hide a known token format (they match once those characters are removed) is withheld whole,
    and so is one whose JSON-escaped form (as the report writes it) still matches a rule."""
    hidden = _hidden_token_count(path)
    if hidden:
        return REDACTED, hidden
    text, n = _redact(path)
    text, m = _redact(_escape(text))
    return _withhold_if_escaped_match(text, n + m)


def _withhold_if_escaped_match(text, count):
    """(text, count), or (REDACTED, count + matches) when json.dumps(text, ensure_ascii=True) -- the
    bytes the report holds -- matches the redaction set although text does not: a `\\uXXXX`
    escape of a non-ASCII space after `key=` (Sentinel S24-2, Chris C24-2). The rules' negative
    lookaheads keep an earlier `<REDACTED>` from matching again, so SAC-27's metric is 0 for these
    values by construction."""
    escaped = _redact(json.dumps(text, ensure_ascii=True))[1]
    return (REDACTED, count + escaped) if escaped else (text, count)


def _hidden_token_count(text):
    """Token matches that appear once the characters able to split or hide a token are removed
    (0 when the text holds none of them)."""
    if not _bad_chars(text, HIDING_CATEGORIES):
        return 0
    return _redact("".join(c for c in text if unicodedata.category(c) not in HIDING_CATEGORIES))[1]


def _show(path):
    """_show_redacted without the count."""
    return _show_redacted(path)[0]


def _redact_value_counted(text):
    """A host- or project-chosen string written as a report value (json.dumps escapes it, so it is
    not escaped here), with the number of replacements: redacted on the raw string, or withheld
    whole when odd characters or marks split or hide a token, as _show_redacted does (Bella L-2,
    SAC-27), or when its JSON-escaped form still matches a rule (_withhold_if_escaped_match)."""
    hidden = _hidden_token_count(text)
    if hidden:
        return REDACTED, hidden
    return _withhold_if_escaped_match(*_redact(text))


def _redact_value(text):
    """_redact_value_counted without the count."""
    return _redact_value_counted(text)[0]


def _bad_chars(value, categories=BAD_CATEGORIES):
    return any(unicodedata.category(c) in categories for c in value)


def _starts_with_dash(value):
    return value.startswith("-")


def _path_rule_ok(p):
    """change_paths / gitlink path rule: repo-relative, no `..`, no backslash, no control chars."""
    if not isinstance(p, str) or not p or len(p) > 4096:
        return False
    if p.startswith("/") or "\\" in p or "\x00" in p or _bad_chars(p):
        return False
    return all(seg not in ("", ".", "..") for seg in p.split("/"))


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _sanitise_path(value, root):
    """Keep absolute, existing directories outside the project; order kept, duplicates dropped."""
    kept = []
    for entry in value.split(os.pathsep):
        if not entry or not os.path.isabs(entry) or not os.path.isdir(entry):
            continue
        if _inside(os.path.realpath(entry), root) or entry in kept:
            continue
        kept.append(entry)
    return kept


def _resolve_tool(name, path_entries, root):
    found = shutil.which(name, path=os.pathsep.join(path_entries))
    if not found:
        return None
    real = os.path.realpath(found)
    try:
        st = os.stat(real)
    except OSError:
        raise Blocked("design-run-tool-unsafe", name)
    if _inside(real, root) or not stat.S_ISREG(st.st_mode) or not os.access(real, os.X_OK):
        raise Blocked("design-run-tool-unsafe", name)
    return real


def _env_from(names, path_entries):
    env = {"PATH": os.pathsep.join(path_entries)}
    for name in names:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


# ----------------------------------------------------------------------------------------------
# git (every runner git call goes through _git_call; every call after --version has the prefix)
# ----------------------------------------------------------------------------------------------

def _git_call(argv, cwd, env, stdin_bytes, timeout):
    return subprocess.run(argv, cwd=cwd, env=env, shell=False, timeout=timeout,
                          stdin=subprocess.DEVNULL if stdin_bytes is None else None,
                          input=stdin_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class Git:
    def __init__(self, exe, env, root):
        self.exe, self.env, self.root = exe, env, root

    def version(self):
        try:
            proc = _git_call([self.exe, "--version"], "/", self.env, None, GIT_VERSION_TIMEOUT_S)
        except (OSError, subprocess.TimeoutExpired):
            raise Blocked("design-run-tool-unsafe", "git (version unavailable)")
        first = proc.stdout.decode("utf-8", "replace").splitlines()[:1]
        line = first[0].strip() if first else ""
        m = GIT_VERSION_RE.match(line)
        if proc.returncode != 0 or not m or (int(m.group(1)), int(m.group(2))) < tuple(MIN_GIT):
            raise Blocked("design-run-tool-unsafe", "git (version %s)" % _r(line)[:80])
        return line

    def run(self, args, stdin_bytes=None, ok=(0,)):
        args = list(args)
        if args[0] == "status":
            args = args[:1] + list(STATUS_EXTRA) + args[1:]
        argv = [self.exe] + list(SAFE_GIT_PREFIX) + args
        try:
            proc = _git_call(argv, self.root, self.env, stdin_bytes, GIT_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise Blocked("design-run-tool-unsafe", "git (%s timed out)" % args[0])
        except OSError as exc:
            raise Blocked("design-run-tool-unsafe", "git (%s: %s)" % (args[0], exc.strerror))
        if ok is not None and proc.returncode not in ok:
            raise Blocked("design-run-tool-unsafe", "git (%s exit %d)" % (args[0], proc.returncode))
        return proc

    def z(self, args, stdin_bytes=None, ok=(0,)):
        out = self.run(args, stdin_bytes, ok).stdout
        return [os.fsdecode(x) for x in out.split(b"\0") if x]


# ----------------------------------------------------------------------------------------------
# step 1: local git-config scan
# ----------------------------------------------------------------------------------------------

def _deny_key(key, value):
    k = key.lower()
    if k == "core.fsmonitor":
        return not (value is not None and value.strip().lower() in ("false", "no", "off", "0", ""))
    # core.attributesfile: attribute conversions (ident, eol, working-tree-encoding) can make
    # `git status` call changed bytes clean, which E1 relies on (Sentinel W12 S-3); attr.tree is
    # the other config-named attribute source (git >= 2.42 reads .gitattributes from that tree-ish;
    # Sentinel W12 S2-4). GIT_ATTR_SOURCE is dropped by the env allowlist.
    if k in ("core.hookspath", "core.worktree", "core.excludesfile", "core.attributesfile", "attr.tree"):
        return True
    parts = k.split(".")
    return len(parts) >= 3 and parts[0] == "filter" and parts[-1] in ("clean", "smudge", "process")


def _parse_config_records(raw):
    parts = raw.split(b"\0")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    if len(parts) % 3:
        raise Blocked("design-run-tool-unsafe", "git (config scan unparsable)")
    records = []
    for i in range(0, len(parts), 3):
        scope, origin = os.fsdecode(parts[i]), os.fsdecode(parts[i + 1])
        kv = os.fsdecode(parts[i + 2])
        key, sep, value = kv.partition("\n")
        if not key or not scope:
            raise Blocked("design-run-tool-unsafe", "git (config scan unparsable)")
        records.append((scope, origin, key, value if sep else None))
    return records


def _project_controlled(scope, origin, anchors, root):
    if scope in ("local", "worktree"):
        return True
    if origin.startswith("file:"):
        return _origin_in_project(os.path.join(root, origin[5:]), anchors)
    if origin.startswith("command line:"):
        return False
    return True


def _config_records(git):
    proc = git.run(["config", "--list", "--show-origin", "--show-scope", "-z"], ok=None)
    if proc.returncode != 0:
        raise Blocked("design-run-tool-unsafe", "git (config scan exit %d)" % proc.returncode)
    return _parse_config_records(proc.stdout)


def _deny_hits(records, anchors, root):
    """(deny-set keys seen, BLOCKED details for the project-controlled ones)."""
    checked, blocked = [], []
    for scope, origin, key, value in records:
        if not _deny_key(key, value):
            continue
        project = _project_controlled(scope, origin, anchors, root)
        checked.append({"key": key, "scope": scope, "origin": origin,
                        "verdict": "project-controlled" if project else "user-trusted"})
        if project:
            blocked.append("git-config %s (%s)" % (_show_config_key(key), _show(origin)))
    return checked, blocked


def _show_config_key(key):
    """A config key for a BLOCKED / tree-changed detail. Only the section and the variable name are
    lowercased (git compares them case-insensitively); a subsection keeps its case, as git does, so
    _show sees an upper-case token such as an AKIA/ASIA id as written (Sentinel S24b-1). Git itself
    lowercases an old-syntax `[section.Sub]` subsection, so an AKIA/ASIA id is matched there in
    any case too (Sentinel S29-1)."""
    section, _, rest = key.partition(".")
    sub, dot, var = rest.rpartition(".")
    if not dot:
        return _show(key.lower())
    # the any-case pass runs after _show: an earlier <REDACTED> would stop the key=value, Bearer and
    # token rules from matching the rest of the value (Sentinel S31-1)
    return _redact_aws_id_any_case(_show("%s.%s.%s" % (section.lower(), sub, var.lower())))


def _redact_aws_id_any_case(text):
    """text with every AKIA/ASIA key id, in any case, replaced by <REDACTED>: the case-sensitive
    token rule misses the id git lowercases in an old-syntax config subsection (Sentinel S29-1)."""
    return AWS_ID_ANY_CASE_RE.sub(REDACTED, text)


def _deny_records(records):
    """The deny-set records of a config scan, every scope, as a comparable set."""
    return frozenset(r for r in records if _deny_key(r[2], r[3]))


def _deny_rescan(ctx):
    """Step 1's deny set and the attribute files outside config, read again immediately before a
    `git status` of steps 7 and 9 (Sentinel S13-3): a filter driver or attribute source planted
    after step 1 (for example while a child ran) would otherwise be executed by the runner's own
    git. A user-trusted deny-set record that was not there at step 1 blocks too (Sentinel S13b-2):
    trust in user config covers what the user had when the run started. A hit raises Blocked
    before that `status` runs."""
    anchors = (ctx.root, ctx.git_dir, ctx.common_dir)
    records = _config_records(ctx.git)
    blocked = _deny_hits(records, anchors, ctx.root)[1]
    blocked += ["git-config %s (%s) (new since step 1)" % (_show_config_key(key), _show(origin))
                for scope, origin, key, value in sorted(_deny_records(records) - ctx.deny_records,
                                                        key=lambda r: tuple(str(x) for x in r))
                if not _project_controlled(scope, origin, anchors, ctx.root)]
    blocked += ["%s (%s)" % (_show(p), reason) for p, reason in _attributes_check(ctx)]
    if blocked:
        raise Blocked("design-run-untrusted-input", "; ".join(blocked))


def _config_scan(git, root):
    records = _config_records(git)
    rp = git.run(["rev-parse", "--absolute-git-dir", "--git-common-dir"], ok=None)
    if rp.returncode != 0:
        raise Blocked("design-run-untrusted-input", "no-git")
    lines = os.fsdecode(rp.stdout).splitlines()
    if len(lines) != 2:
        raise Blocked("design-run-untrusted-input", "no-git")
    git_dir = os.path.realpath(lines[0])
    common_dir = os.path.realpath(os.path.join(root, lines[1]))
    checked, blocked = _deny_hits(records, (root, git_dir, common_dir), root)
    if blocked:
        raise Blocked("design-run-untrusted-input", "; ".join(blocked))
    scan = {"records": len(records), "deny_set_keys": checked, "blocked": []}
    return scan, git_dir, common_dir, _deny_records(records)


# ----------------------------------------------------------------------------------------------
# tree check E0-E3
# ----------------------------------------------------------------------------------------------

def _lstat(path):
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def _e0_check(git, root, common_dir):
    """Gitlinks: any initialized submodule blocks (block, not recurse). Returns (blocks, gitlinks)."""
    blocks, links = [], []
    for rec in git.z(["ls-files", "-s", "-z"]):
        meta, _, path = rec.partition("\t")
        if not meta.startswith("160000 "):
            continue
        if not _path_rule_ok(path):
            blocks.append("submodule %s" % _show(path))
            continue
        links.append(path)
    modules = os.path.join(common_dir, "modules")
    st = _lstat(modules)
    rel = os.path.relpath(modules, root)
    if st is not None and stat.S_ISDIR(st.st_mode):
        for entry in sorted(os.listdir(modules)):
            blocks.append("submodule %s/%s" % (rel, _show(entry)))
    elif st is not None:
        blocks.append("submodule %s (not-a-directory)" % rel)
    states = []
    for p in links:
        full = os.path.join(root, p)
        if _lstat(os.path.join(full, ".git")) is not None:
            blocks.append("submodule %s" % p)
            states.append({"path": p, "state": "initialized"})
            continue
        st = _lstat(full)
        if st is None:
            states.append({"path": p, "state": "absent"})
        elif stat.S_ISDIR(st.st_mode) and not os.listdir(full):
            states.append({"path": p, "state": "empty"})
        else:
            blocks.append("submodule %s (populated)" % p)
            states.append({"path": p, "state": "populated"})
    return blocks, states


def _is_data_path(p):
    return p.startswith(DATA_ROOTS) and not p.endswith("/") and os.path.splitext(p)[1].lower() in DATA_EXTENSIONS


def _inert_os_file(entry, root):
    if entry.endswith("/") or os.path.basename(entry) not in INERT_BASENAMES:
        return False
    st = _lstat(os.path.join(root, entry))
    return st is not None and stat.S_ISREG(st.st_mode)


def _ignore_source_trusted(src, ctx):
    """A tracked, unmodified, repo-relative .gitignore (work tree == index == HEAD, no filters)."""
    if os.path.isabs(src) or os.path.basename(src) != ".gitignore" or src.startswith(".git/"):
        return False
    if not _path_rule_ok(src):
        return False
    return ctx.blob_verified(src)


def _is_test_file(path):
    """Playwright's default test-file shape, widened: `.spec.` / `.test.` plus a JS/TS extension."""
    base = os.path.basename(path).lower()
    ext = os.path.splitext(base)[1].lstrip(".")
    return ext in TEST_FILE_EXTS and (".spec." in base or ".test." in base)


def _js_regex_escape(text):
    """Escape for Playwright's RegExp(pattern, 'gi'); the slug alphabet needs only `.` escaped."""
    return re.sub(r"([\\^$.*+?()\[\]{}|])", r"\\\1", text)


class TreeState:
    """One snapshot of the index/work tree, gathered with safe git calls."""

    def __init__(self, git, root, change_paths):
        self.git, self.root, self.change = git, root, set(change_paths)
        self.tags, self.index_blob = {}, {}
        self.flag_results = []
        for rec in git.z(["ls-files", "-v", "-z"]):
            if len(rec) >= 3 and rec[1] == " ":
                self.tags[rec[2:]] = rec[0]
        for rec in git.z(["ls-files", "-s", "-z"]):
            meta, _, path = rec.partition("\t")
            fields = meta.split()
            if len(fields) == 3:
                self.index_blob[path] = (fields[0], fields[1])
        self.modified = set()
        entries = git.z(["status", "--porcelain=v1", "-z", "--untracked-files=no"])
        i = 0
        while i < len(entries):
            rec = entries[i]
            xy, path = rec[:2], rec[3:]
            self.modified.add(path)
            if xy[0] in "RC":
                i += 1
                if i < len(entries):
                    self.modified.add(entries[i])
            i += 1
        self._head, self._work = {}, {}

    def tracked(self, p):
        return p in self.index_blob

    def flagged(self, p):
        tag = self.tags.get(p)
        return tag if tag is not None and (tag.islower() or tag in ("S", "s")) else None

    def _head_blobs(self, paths):
        need = [p for p in paths if p not in self._head]
        if not need:
            return
        proc = self.git.run(["ls-tree", "-r", "-z", "--full-tree", "HEAD", "--"] +
                            [":(literal)" + p for p in need], ok=None)
        for p in need:
            self._head[p] = None
        if proc.returncode == 0:
            for rec in proc.stdout.split(b"\0"):
                meta, _, path = os.fsdecode(rec).partition("\t")
                fields = meta.split()
                if len(fields) == 3:
                    self._head[path] = fields[2]

    def _work_blobs(self, paths):
        need = [p for p in paths if p not in self._work and "\n" not in p]
        if not need:
            return
        out = self.git.run(["hash-object", "--no-filters", "--stdin-paths"],
                           stdin_bytes=b"".join(os.fsencode(p) + b"\n" for p in need)).stdout
        hashes = os.fsdecode(out).split()
        for p, h in zip(need, hashes):
            self._work[p] = h

    def blob_verified(self, p):
        """Regular file whose bytes (no filters) equal both the index blob and HEAD:<p>."""
        st = _lstat(os.path.join(self.root, p))
        if st is None or not stat.S_ISREG(st.st_mode) or p not in self.index_blob or "\n" in p:
            return False
        self._head_blobs([p])
        self._work_blobs([p])
        idx = self.index_blob[p][1]
        return self._work.get(p) == idx and self._head.get(p) == idx


def _e1_inputs(tpl, spec, ts, root):
    names = []
    for kind in tpl.get("executes", []):
        if kind == "spec":
            names.append((spec, True))
        elif kind == "playwright-config":
            names += [(c, False) for c in PLAYWRIGHT_CONFIGS]
        elif kind == "package-json":
            names.append(("package.json", False))
        elif kind == "lockfiles":
            names += [(c, False) for c in LOCKFILES]
        elif kind == "tracked-specs":
            names += [(p, True) for p in sorted(ts.index_blob) if _is_test_file(p) and
                      "node_modules" not in p.split("/")]
        else:  # unreachable after _validate_catalogue; kept so a typo can never skip E1
            raise Blocked("design-run-schema", "catalogue executes %s" % _show(str(kind)))
    out = []
    for p, always in names:
        if always or ts.tracked(p) or _lstat(os.path.join(root, p)) is not None:
            out.append(p)
    return out


def _e1_check(inputs, ts):
    blocks = []
    for p in inputs:
        if p in ts.change:
            continue
        if not ts.tracked(p):
            blocks.append((p, "untracked"))
        elif ts.flagged(p):
            blocks.append((p, "index-flag %s" % ts.flagged(p)))
        elif p in ts.modified:
            # also blocked by E2 (every modified tracked path outside change_paths); kept here as
            # defence in depth, so removing one of the two never silently drops the check
            blocks.append((p, "modified"))
    return blocks


def _list_untracked(git, change):
    entries = git.z(["ls-files", "--others", "--directory", "--no-empty-directory", "-z"])
    out = []
    for e in entries:
        if e.endswith("/") and (e.startswith(DATA_ROOTS) or e in DATA_ROOTS or any(c.startswith(e) for c in change)):
            inner = git.z(["ls-files", "--others", "-z", "--", ":(literal)" + e])
            out += inner or [e]
        else:
            out.append(e)
    return out


def _e2_check(git, root, ts, created, records):
    blocks = []
    pending = []
    for e in _list_untracked(git, ts.change):
        if e in ts.change:
            records.append({"path": e, "rule": "change-paths"})
        elif os.path.basename(e) == ".gitattributes":
            # an untracked attributes file (even under an ignored directory) can change how
            # `git status` reads tracked bytes next to it (Sentinel W12 S-3)
            blocks.append((e, "attributes-source"))
        elif _is_data_path(e):
            records.append({"path": e, "rule": "data-path"})
        elif _inert_os_file(e, root):
            records.append({"path": e, "rule": "inert-os-file"})
        elif any(e == c or e.startswith(c.rstrip("/") + "/") for c in created):
            records.append({"path": e, "rule": "earlier-run-writes"})
        else:
            pending.append(e)
    if pending:
        out = git.run(["check-ignore", "-v", "-z", "--non-matching", "--stdin"],
                      stdin_bytes=b"".join(os.fsencode(p) + b"\0" for p in pending), ok=(0, 1)).stdout
        fields = [os.fsdecode(x) for x in out.split(b"\0")]
        results = {}
        for i in range(0, len(fields) - 3, 4):
            src, _line, pattern, path = fields[i:i + 4]
            results[path] = (src, pattern)
        for e in pending:
            src, pattern = results.get(e, ("", ""))
            if not src or not pattern or pattern.startswith("!"):
                # the ignore source is project-chosen: shown through _show like the entry (Bella L-1)
                blocks.append((e, "not-ignored" if not src else "negated %s" % _show(src)))
            elif _ignore_source_trusted(src, ts):
                records.append({"path": e, "rule": "tracked-gitignore", "source": src})
            else:
                blocks.append((e, "ignore-source %s" % _show(src)))
                records.append({"path": e, "rule": "blocked", "source": src})
    for p in sorted(ts.modified):
        if p in ts.change:
            records.append({"path": p, "rule": "change-paths"})
        elif _is_data_path(p):
            records.append({"path": p, "rule": "data-path"})
        else:
            blocks.append((p, "modified"))
    blocks += _index_flag_check(ts, records)
    return blocks


def _index_flag_check(ts, records):
    blocks = []
    for p, tag in sorted(ts.tags.items()):
        if not ts.flagged(p) or p in ts.change:
            continue
        st = _lstat(os.path.join(ts.root, p))
        if st is None:
            records.append({"path": p, "rule": "index-flag-absent", "tag": tag})
            ts_result = "absent"
        elif stat.S_ISREG(st.st_mode) and ts.blob_verified(p):
            records.append({"path": p, "rule": "index-flag-verified", "tag": tag})
            ts_result = "verified"
        else:
            blocks.append((p, "index-flag %s" % tag))
            ts_result = "blocked"
        ts.flag_results.append({"path": p, "tag": tag, "result": ts_result})
    return blocks


def _nested_repo_check(git):
    """Second layer behind the E3 walk: git never descends into a nested repository."""
    entries = git.z(["ls-files", "--others", "-z", "--", ":(exclude,glob)**/node_modules/**"])
    return [(e, "nested-repo") for e in entries if e.endswith("/")]


def _fs_walk(root):
    """Every regular file Playwright 1.63's collectFiles can reach from `root`: os.scandir, never
    following a symlink, skipping only directories named `node_modules`, and entering every
    directory named `.git` (git itself never lists those paths). Bounded: more than
    WALK_MAX_ENTRIES entries or WALK_MAX_SECONDS seconds blocks, as does an unreadable directory."""
    deadline = time.monotonic() + WALK_MAX_SECONDS
    files, count, stack = [], 0, [""]
    while stack:
        rel_dir = stack.pop()
        try:
            with os.scandir(os.path.join(root, rel_dir) if rel_dir else root) as it:
                for entry in it:
                    count += 1
                    if count > WALK_MAX_ENTRIES:
                        raise Blocked("design-run-untrusted-input", "tree-walk (entry cap %d)" % WALK_MAX_ENTRIES)
                    if time.monotonic() > deadline:
                        raise Blocked("design-run-untrusted-input", "tree-walk (time cap %gs)" % WALK_MAX_SECONDS)
                    rel = rel_dir + "/" + entry.name if rel_dir else entry.name
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name != "node_modules":
                            stack.append(rel)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(rel)
        except OSError as exc:
            raise Blocked("design-run-untrusted-input", "tree-walk (%s: %s)" % (_show(rel_dir or "."), exc.strerror))
    return files


def _e3_candidate_files(ctx):
    """The E3 candidate list (seam for the git-only mutation test)."""
    return _fs_walk(ctx.root)


def _tracked_unmodified(p, ts):
    if p in ts.change:
        return True
    if not ts.tracked(p) or p in ts.modified:
        return False
    return not ts.flagged(p) or ts.blob_verified(p)


def _has_test_ext(path):
    return os.path.splitext(os.path.basename(path))[1].lstrip(".").lower() in TEST_FILE_EXTS


def _git_dir_test_files(files):
    """Files under any directory named `.git` (case-folded) with a test-file extension. Nothing
    there is ever tracked and git hooks carry no extension, so this never over-blocks a real
    project; it closes the custom-`testMatch` gap (Sentinel W12 S2-1)."""
    return [p for p in files if _has_test_ext(p) and any(s.lower() == ".git" for s in p.split("/")[:-1])]


def _e3_matches(tpl, spec, root, files):
    """The files E3 treats as loadable for this template (the git-dir clause included)."""
    kind = tpl.get("e3")
    if kind is None:
        return []
    if kind == "spec":
        # Playwright tests RegExp(<escaped spec>$, "gi") against the absolute path
        suffix = spec.lower()
        hits = [p for p in files if os.path.join(root, p).lower().endswith(suffix)]
    elif kind == "default-pattern":
        hits = [p for p in files if _is_test_file(p)]
    else:  # unreachable after _validate_catalogue; kept so a typo can never skip E3
        raise Blocked("design-run-schema", "catalogue e3 %s" % _show(str(kind)))
    seen = set(hits)
    return hits + [p for p in _git_dir_test_files(files) if p not in seen]


def _e3_check(tpl, spec, ts, files):
    """Spec-filter collisions: every file Playwright could load for this template that is not a
    tracked, unmodified path, the named spec or a change path."""
    if tpl.get("e3") is None:
        return []
    hits = _e3_matches(tpl, spec, ts.root, files)
    blocks = [(p, "filter-collision") for p in hits if p != spec and not _tracked_unmodified(p, ts)]
    return blocks + _nested_repo_check(ts.git)


def _walk_sig(root, paths):
    """lstat signature of each path (None when it is gone)."""
    sig = {}
    for p in paths:
        st = _lstat(os.path.join(root, p))
        sig[p] = None if st is None else (st.st_mode, st.st_size, st.st_mtime_ns, st.st_ino)
    return sig


def _late_e3_files(ctx, item, before_sig):
    """Post-run re-walk (Sentinel W12 S2-2): files E3 would block for this template that are new,
    or whose lstat signature changed, since the pre-run walk. The git-based post-run diff never
    sees `.git/` paths or ignored directories, so this is the only detection there."""
    files = _e3_candidate_files(ctx)
    now = _walk_sig(ctx.root, _e3_matches(item["tpl"], item["spec"], ctx.root, files))
    return sorted(p for p, s in now.items() if before_sig.get(p, "absent") != s)


def _attributes_check(ctx):
    """Repository attribute files outside the tree (Sentinel W12 S-3): `info/attributes` in the git
    dir or common dir blocks unless it is an empty regular file."""
    blocks = []
    for d in sorted({ctx.git_dir, ctx.common_dir}):
        p = os.path.join(d, "info", "attributes")
        st = _lstat(p)
        if st is not None and (not stat.S_ISREG(st.st_mode) or st.st_size > 0):
            blocks.append((os.path.relpath(p, ctx.root), "attributes-source"))
    return blocks


def _tree_check(ctx, plan, created=()):
    """E0-E3 for every planned run; raises Blocked with every blocked path listed together."""
    e0, links = _e0_check(ctx.git, ctx.root, ctx.common_dir)
    ctx.gitlinks = links
    if e0:
        raise Blocked("design-run-untrusted-input", "; ".join(e0))
    _deny_rescan(ctx)            # config deny set + info/attributes, before TreeState's `status`
    ts = TreeState(ctx.git, ctx.root, ctx.change_paths)
    records = []
    blocks = _e2_check(ctx.git, ctx.root, ts, created, records)
    files = _e3_candidate_files(ctx) if any(item["tpl"].get("e3") is not None for item in plan) else []
    for item in plan:
        blocks += _e1_check(_e1_inputs(item["tpl"], item["spec"], ts, ctx.root), ts)
        blocks += _e3_check(item["tpl"], item["spec"], ts, files)
    ctx.flag_results = ts.flag_results
    seen, uniq = set(), []
    for path, reason in blocks:
        if (path, reason) not in seen:
            seen.add((path, reason))
            uniq.append("%s (%s)" % (_show(path), reason) if reason != "not-ignored" else _show(path))
    if uniq:
        raise Blocked("design-run-untrusted-input", "; ".join(uniq))
    return records


def _snapshot(ctx):
    """E2 listing for the post-run diff: untracked entries and modified tracked files + lstat. The
    deny set is read again first, so its `git status` never runs a filter planted since step 1."""
    _deny_rescan(ctx)
    snap = {}
    for e in ctx.git.z(["ls-files", "--others", "--directory", "--no-empty-directory", "-z"]):
        st = _lstat(os.path.join(ctx.root, e.rstrip("/")))
        snap[e] = None if st is None or e.endswith("/") else (st.st_mode, st.st_size, st.st_mtime_ns)
    for e in TreeState(ctx.git, ctx.root, ()).modified:
        st = _lstat(os.path.join(ctx.root, e))
        snap["M:" + e] = None if st is None else (st.st_mode, st.st_size, st.st_mtime_ns)
    return snap


def _under(entry, prefixes):
    path = entry[2:] if entry.startswith("M:") else entry
    return any(path == p + "/" or path.startswith(p + "/") or (path.endswith("/") and (p + "/").startswith(path))
               for p in prefixes)


# ----------------------------------------------------------------------------------------------
# order and request
# ----------------------------------------------------------------------------------------------

def _strict_json(buf, label):
    if buf.startswith(b"\xef\xbb\xbf"):
        raise Blocked("design-run-schema", "%s bom" % label)
    try:
        text = buf.decode("utf-8", "strict")
    except UnicodeDecodeError:
        raise Blocked("design-run-schema", "%s utf-8" % label)

    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise Blocked("design-run-schema", "%s duplicate-key %s" % (label, _show(k)))
            obj[k] = v
        return obj

    def constant(name):
        raise Blocked("design-run-schema", "%s %s" % (label, name))

    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ValueError:
        raise Blocked("design-run-schema", "%s json" % label)

    def walk(node):
        if isinstance(node, str):
            if _bad_chars(node, ("Cs",)):
                raise Blocked("design-run-schema", "%s lone-surrogate" % label)
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(k)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    if not isinstance(data, dict):
        raise Blocked("design-run-schema", "%s not-an-object" % label)
    return data


def _read_pinned(root, rel, expected, label, hash_token):
    cur = root
    for seg in rel.split("/"):
        cur = os.path.join(cur, seg)
        st = _lstat(cur)
        if st is None:
            raise Blocked(hash_token, "%s (missing)" % rel)
        if stat.S_ISLNK(st.st_mode):
            raise Blocked("design-run-untrusted-input", "%s (symlink)" % rel)
    full = os.path.join(root, rel)
    try:
        fd = os.open(full, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Blocked("design-run-untrusted-input", "%s (unreadable)" % rel)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise Blocked("design-run-untrusted-input", "%s (not-regular)" % rel)
        if st.st_size > MAX_INPUT_BYTES:
            raise Blocked("design-run-schema", "%s size" % label)
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, MAX_INPUT_BYTES + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_INPUT_BYTES:
                raise Blocked("design-run-schema", "%s size" % label)
    finally:
        os.close(fd)
    # defence in depth: the lstat walk plus O_NOFOLLOW above already refuse every symlink
    if not _inside(os.path.realpath(full), os.path.join(root, "outputs")):
        raise Blocked("design-run-untrusted-input", "%s (outside outputs)" % rel)
    buf = b"".join(chunks)
    digest = _sha256(buf)
    if digest != expected:
        raise Blocked(hash_token, rel)
    return _strict_json(buf, label), digest


def _int(value, lo, hi):
    return type(value) is int and lo <= value <= hi


def _quote_ok(value):
    return isinstance(value, str) and 0 < len(value) <= 500 and value.strip() and not _bad_chars(value, ("Cc", "Cs"))


def _ascii_visible(value):
    return all(0x21 <= ord(c) <= 0x7e for c in value)


def _port_ok(text):
    return text is None or 1 <= int(text) <= 65535


def _validate_order(order, path_match):
    extra = set(order) - ORDER_KEYS
    if extra:
        raise Blocked("design-run-schema", "order key %s" % _show(sorted(extra)[0]))
    missing = ORDER_REQUIRED - set(order)
    if missing:
        raise Blocked("design-run-schema", "order missing %s" % sorted(missing)[0])
    if type(order["schema"]) is not int or order["schema"] != 1:
        raise Blocked("design-run-schema", "order schema")
    task = order["task"]
    # a task id shaped like a token fails closed (Sentinel S24-7): the id is written raw into the
    # report's order/request/run paths (R64), so it must not carry anything the redaction set matches
    if not isinstance(task, str) or not TASK_RE.fullmatch(task) or ".." in task:
        raise Blocked("design-run-schema", "order task")
    if _redact(task)[1]:   # its own detail, without the id (Chris C24b-3)
        raise Blocked("design-run-schema", "order task token-shaped")
    if order["phase"] not in ("1b", "3a"):
        raise Blocked("design-run-schema", "order phase")
    if not _int(order["iter"], 1, 3):
        raise Blocked("design-run-schema", "order iter")
    if (task, order["phase"], str(order["iter"])) != (path_match["task"], path_match["phase"], path_match["iter"]):
        raise Blocked("design-run-schema", "order naming-pattern")
    req_re = r"outputs/%s/[0-9]{2}-ux-design-run-request-%s-iter%d\.json" % (re.escape(task), order["phase"],
                                                                              order["iter"])
    if not isinstance(order["request_path"], str) or not re.fullmatch(req_re, order["request_path"]):
        raise Blocked("design-run-schema", "order request_path")
    if not isinstance(order["request_sha256"], str) or not SHA_RE.fullmatch(order["request_sha256"]):
        raise Blocked("design-run-schema", "order request_sha256")
    cps = order["change_paths"]
    if not isinstance(cps, list) or len(cps) > 200 or not all(_path_rule_ok(p) for p in cps):
        raise Blocked("design-run-schema", "order change_paths")
    conf = order.get("change_confirmation")
    if conf is not None and not _quote_ok(conf):
        raise Blocked("design-run-schema", "order change_confirmation")
    if order["phase"] == "1b" and cps and conf is None:
        raise Blocked("design-run-schema", "order change_confirmation")
    ports = order.get("loopback_ports")
    if ports is not None and (not isinstance(ports, list) or not 1 <= len(ports) <= 4 or
                              not all(_int(p, 1, 65535) for p in ports)):
        raise Blocked("design-run-schema", "order loopback_ports")


def _url_ok(value, order):
    """Loopback only: ASCII netloc fullmatch, port pinned when the order lists ports, matched
    before urllib parses anything. The runner refuses every non-loopback URL (R69, 4.0.0)."""
    if len(value) > 300 or "#" in value or not _ascii_visible(value):
        return False
    head = URL_HEAD_RE.match(value)
    if not head:
        return False
    scheme, netloc = head.group(1).lower(), head.group(2)
    loop = LOOPBACK_NETLOC_RE.fullmatch(netloc)
    if not loop or not _port_ok(loop.group(1)):
        return False
    ports = order.get("loopback_ports")
    effective = int(loop.group(1)) if loop.group(1) else (80 if scheme == "http" else 443)
    if ports is not None and effective not in ports:
        return False
    parts = urllib.parse.urlsplit(value)
    if parts.netloc != netloc or not URL_PATH_RE.fullmatch(parts.path):
        return False
    return parts.query == "" or bool(URL_QUERY_RE.fullmatch(parts.query))


def _check_param(run_id, name, kind, value, order, earlier, catalogue):
    def bad():
        raise Blocked("design-run-param", "%s.%s" % (run_id, name))

    if isinstance(kind, dict) and "int_range" in kind:
        lo, hi = kind["int_range"]
        if not _int(value, lo, hi):
            bad()
        return
    if not isinstance(value, str):
        bad()
    if _starts_with_dash(value) or value != value.strip() or _bad_chars(value):
        bad()
    if isinstance(kind, dict) and "enum" in kind:
        if value not in kind["enum"]:
            bad()
    elif kind == "text":
        if not 1 <= len(value) <= 200 or _bad_chars(value, TEXT_BAD_CATEGORIES):
            bad()
    elif kind == "slug":
        if not SLUG_RE.fullmatch(value):
            bad()
    elif kind == "hex_color":
        if not HEX_RE.fullmatch(value):
            bad()
    elif kind == "run_ref":
        if not RUN_ID_RE.fullmatch(value) or value not in earlier:
            bad()
        if not catalogue["templates"][earlier[value]].get("stdout_json"):
            bad()
    elif kind == "url":
        if not _url_ok(value, order):
            bad()
    else:
        raise Blocked("design-run-schema", "catalogue param kind %s" % name)


def _validate_request(req, order, catalogue):
    extra = set(req) - REQUEST_KEYS
    if extra:
        raise Blocked("design-run-schema", "request key %s" % _show(sorted(extra)[0]))
    if REQUEST_KEYS - set(req):
        raise Blocked("design-run-schema", "request missing %s" % sorted(REQUEST_KEYS - set(req))[0])
    if type(req["schema"]) is not int or req["schema"] != 1:
        raise Blocked("design-run-schema", "request schema")
    for key in ("task", "phase", "iter"):
        if type(req[key]) is not type(order[key]) or req[key] != order[key]:
            raise Blocked("design-run-schema", "request %s" % key)
    runs = req["runs"]
    if not isinstance(runs, list) or not runs:
        raise Blocked("design-run-schema", "request runs")
    if len(runs) > catalogue["max_runs"]:
        raise Blocked("design-run-too-many-runs", "%d > %d" % (len(runs), catalogue["max_runs"]))
    earlier = {}
    for run in runs:
        if not isinstance(run, dict) or set(run) != RUN_KEYS:
            raise Blocked("design-run-schema", "run keys")
        rid = run["id"]
        if not isinstance(rid, str) or not RUN_ID_RE.fullmatch(rid) or rid in earlier:
            raise Blocked("design-run-schema", "run id")
        sid = run["script_id"]
        tpl = catalogue["templates"].get(sid) if isinstance(sid, str) else None
        if tpl is None:
            raise Blocked("design-run-schema", "%s.script_id" % rid)
        if order["phase"] not in tpl["phases"]:
            raise Blocked("design-run-schema", "%s.script_id phase" % rid)
        params = run["params"]
        if not isinstance(params, dict) or set(params) != set(tpl["params"]):
            raise Blocked("design-run-schema", "%s.params" % rid)
        for name, kind in tpl["params"].items():
            _check_param(rid, name, kind, params[name], order, earlier, catalogue)
        earlier[rid] = sid
    return runs


# ----------------------------------------------------------------------------------------------
# execution
# ----------------------------------------------------------------------------------------------

def _spawn_child(argv, cwd, env, stdout_f, stderr_f, timeout):
    """The only place a run's child starts: shell=False, own process group. The group is killed
    in `finally`, so a timeout, SIGTERM/SIGHUP (SystemExit) or KeyboardInterrupt never leaves the
    child running. Streams pass through pipes and at most STREAM_CAP + 1 bytes of each reach the
    raw files (the extra byte marks truncation)."""
    proc = subprocess.Popen(argv, cwd=cwd, env=env, shell=False, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        status = _pump(proc, ((proc.stdout, stdout_f), (proc.stderr, stderr_f)), timeout)
    finally:
        _kill_group(proc)
    return status, (proc.returncode if status == "exit" else None)


def _pump(proc, pairs, timeout):
    """Copy child pipes into capped files until both close or the deadline; returns exit|timeout."""
    deadline = time.monotonic() + timeout
    written = {}
    exited_at = None
    with selectors.DefaultSelector() as sel:
        for pipe, sink in pairs:
            sel.register(pipe, selectors.EVENT_READ, sink)
            written[id(sink)] = 0
        while sel.get_map():
            now = time.monotonic()
            if now >= deadline:
                return "timeout"
            if exited_at is None and proc.poll() is not None:
                exited_at = now
            if exited_at is not None and now - exited_at > DRAIN_GRACE_S:
                break  # an escaped grandchild holds the pipe; the group kill follows
            for key, _ in sel.select(min(deadline - now, 0.5)):
                data = os.read(key.fd, 65536)
                if not data:
                    sel.unregister(key.fileobj)
                    continue
                room = STREAM_CAP + 1 - written[id(key.data)]
                if room > 0:
                    key.data.write(data[:room])
                written[id(key.data)] += len(data)
    try:
        proc.wait(timeout=max(deadline - time.monotonic(), 0))
    except subprocess.TimeoutExpired:
        return "timeout"
    return "exit"


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            pipe.close()


def _stage_dir(private, run_dir, run_id):
    """Where a run's child writes its artifacts: always inside the private dir. `run_dir` is unused
    here; the parameter exists so the stage-bypass mutation test can redirect writes into it."""
    return os.path.join(private, "out", run_id)


def _private_dir(root):
    for base in (os.environ.get("TMPDIR"), "/tmp", "/var/tmp"):
        if base and os.path.isdir(base) and not _inside(os.path.realpath(base), root):
            return tempfile.mkdtemp(prefix="design-run-", dir=base)
    raise Blocked("design-run-untrusted-input", "tmpdir")


def _write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _capture(raw_path):
    size = os.path.getsize(raw_path)
    with open(raw_path, "rb") as fh:
        data = fh.read(STREAM_CAP)
    return data, size > STREAM_CAP


def _build_argv(item, ctx):
    tpl, params, rid = item["tpl"], item["params"], item["id"]
    args = []
    for el in tpl["argv"]:
        if el == "<root>":
            args.append(ctx.root)
        elif el == "<spec-filter>":
            args.append(_js_regex_escape(item["spec"]) + "$")
        elif el.startswith("<run-json:"):
            ref = params[el[len("<run-json:"):-1]]
            path = os.path.join(ctx.run_dir, ref + ".json")
            if not _inside(os.path.realpath(path), os.path.realpath(ctx.run_dir)):
                raise Blocked("design-run-untrusted-input", "%s (run-ref)" % ref)
            args.append(path)
        elif el.startswith("<out>/"):
            args.append(os.path.join(item["stage"], el[len("<out>/"):].replace("<run-id>", rid)))
        elif el == AXE_SAVE_NAME:
            # a bare file name: the axe CLI joins `--save` onto `--dir` (an absolute `--save` would be
            # joined onto the cwd, the project root), so the stage path goes in `--dir <out>/`
            args.append(el.replace("<run-id>", rid))
        else:
            args.append(PLACEHOLDER_RE.sub(lambda m: str(params[m.group(1)]), el))
    if tpl["runner"] == "plugin-python":
        return [sys.executable, "-I", "-c", BOOTSTRAP, str(SCRIPTS_DIR / tpl["script"])] + args
    return [item["exe"]] + args


def _stage_out(item, ctx, result):
    stage, rid = item["stage"], item["id"]
    declared = [a.replace("<run-id>", rid) for a in item["tpl"].get("artifacts", [])]
    count = 0
    present = sorted(os.listdir(stage)) if os.path.isdir(stage) else []
    for name in present:
        if name not in declared:
            # the child chose this name: redacted like tree_changed_paths (Bella W12 F-1, SAC-27)
            shown, n = _show_redacted(name)
            count += n
            result["dropped"].append({"name": shown, "reason": "undeclared"})
    for name in declared:
        src = os.path.join(stage, name)
        st = _lstat(src)
        if st is None:
            result["dropped"].append({"name": name, "reason": "missing"})
            continue
        if not stat.S_ISREG(st.st_mode):
            result["dropped"].append({"name": name, "reason": "not-regular"})
            continue
        if st.st_size > ARTIFACT_CAP:
            result["dropped"].append({"name": name, "reason": "too-large"})
            continue
        data, reason = _read_artifact(src)
        if reason:
            result["dropped"].append({"name": name, "reason": reason})
            continue
        if os.path.splitext(name)[1].lower() in TEXT_ARTIFACT_EXTS:
            data, n = _redact_bytes(data)
            count += n
        dest = os.path.join(ctx.run_dir, name)
        _write_new(dest, data)
        result["artifacts"].append({"name": name, "path": os.path.relpath(dest, ctx.root), "sha256": _sha256(data)})
    result["redactions"]["artifacts"] = count


def _read_artifact(src):
    """Read at most ARTIFACT_CAP bytes of a regular file without following a symlink or blocking on
    a FIFO an escaped grandchild may have swapped in. Returns (data, drop reason or None)."""
    try:
        fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return b"", "not-regular"
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return b"", "not-regular"
        chunks, size = [], 0
        while size <= ARTIFACT_CAP:
            chunk = os.read(fd, min(1 << 20, ARTIFACT_CAP + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
    finally:
        os.close(fd)
    if size > ARTIFACT_CAP:
        return b"", "too-large"
    return b"".join(chunks), None


def _write_stream(ctx, item, raw_path, suffix):
    data, truncated = _capture(raw_path)
    data, n = _redact_bytes(data)
    dest = os.path.join(ctx.run_dir, item["id"] + suffix)
    _write_new(dest, data)
    return {"path": os.path.relpath(dest, ctx.root), "sha256": _sha256(data), "bytes": len(data),
            "truncated": truncated}, n


def _new_result(item, ctx, child_env):
    return {"id": item["id"], "script_id": item["script_id"], "cwd": ctx.root, "env_names": sorted(child_env),
            "status": None, "exit_code": None, "reason": None, "artifacts": [], "dropped": [],
            "redactions": {"stdout": 0, "stderr": 0, "argv": 0, "artifacts": 0}}


def _record_argv(result, item, argv):
    red_argv = []
    for el in argv:
        red, n = _redact_value_counted(el)   # the root, TMPDIR and interpreter paths are host-chosen (S24-1)
        red_argv.append(red)
        result["redactions"]["argv"] += n
    result["argv"] = red_argv
    # project-bin argv[0] is already the realpath from step 6 (Bella W12 F-10: realpath for both)
    result["executable"] = argv[0] if item["tpl"]["runner"] == "project-bin" else os.path.realpath(sys.executable)


def _os_failure(exc, root):
    """A run's `tree-changed` reason for an OSError met while inspecting the tree; the file name may
    be child-chosen, so it is shown through _show, never through the exception's repr."""
    name = exc.filename
    shown = _show(os.path.relpath(os.fsdecode(name), root)) if isinstance(name, (str, bytes)) else "-"
    return _r("design-run-untrusted-input %s (%s)" % (shown, exc.strerror or type(exc).__name__))


def _post_run(ctx, item, result, before, created, raw, before_walk):
    """After a child ran: post-run diff, post-run E3 re-walk, streams, stage-out. Returns True when
    the run counts as tree-changed. A Blocked here (for example git failing because the child broke
    `.git`) is a tree change, never exit 3: the child has already run (Chris W12 S-1). So is an
    OSError (for example a tracked directory the child made unsearchable; Sentinel S13b-1)."""
    try:
        after, failure = _snapshot(ctx), None
        late = _late_e3_files(ctx, item, before_walk) if before_walk is not None else []
    except Blocked as b:
        after, failure, late = None, _r(b.token + " " + b.detail), []
    except OSError as exc:
        after, failure, late = None, _os_failure(exc, ctx.root), []
    suffix = ".json" if item["tpl"].get("stdout_json") else ".stdout.txt"
    preexisting = []
    for key, sfx, path in (("stdout", suffix, raw[0]), ("stderr", ".stderr.txt", raw[1])):
        try:
            result[key], result["redactions"][key] = _write_stream(ctx, item, path, sfx)
        except FileExistsError:  # the child planted the name in the run dir (Chris W12 N-3)
            preexisting.append(item["id"] + sfx)
    if failure:
        result.update(status="tree-changed", reason=failure)
        return True
    if preexisting:
        result.update(status="tree-changed", reason=_r("run-dir-preexisting " + " ".join(preexisting)))
        return True
    allowed = [w.replace("{feature}", str(item["params"].get("feature", ""))).rstrip("*").rstrip("/")
               for w in item["tpl"]["writes"]]
    changed = sorted(k for k in set(before) | set(after) if before.get(k, "absent") != after.get(k, "absent"))
    bad = [k for k in changed if not _under(k, allowed) and not _under(k, created)]
    created += [k.rstrip("/") for k in changed if k not in bad and not k.startswith("M:")]
    bad_paths = [k[2:] if k.startswith("M:") else k for k in bad]
    bad_paths += [p for p in late if p not in bad_paths]
    if bad_paths:
        result.update(status="tree-changed", reason="tree-changed",
                      tree_changed_paths=[_show(p) for p in bad_paths])
        return True
    try:
        _stage_out(item, ctx, result)
    except FileExistsError as exc:
        result.update(status="tree-changed",
                      reason=_r("run-dir-preexisting " + os.path.basename(exc.filename or "")))
        return True
    return False


def _execute(ctx, plan):
    results, statuses, created = [], {}, []
    ctx.results = results
    stop_reason = None
    child_env = _env_from(CHILD_ENV_NAMES, ctx.path_entries)
    child_env.update({"CI": "1", "NO_COLOR": "1"})
    for item in plan:
        rid = item["id"]
        result = _new_result(item, ctx, child_env)
        results.append(result)
        if stop_reason:
            result.update(status="skipped", reason=stop_reason)
            statuses[rid] = "skipped"
            continue
        dep = [item["params"][n] for n, k in item["tpl"]["params"].items() if k == "run_ref"]
        if any(statuses.get(d) != "ok" for d in dep):
            result.update(status="skipped", reason="dependency-failed")
            statuses[rid] = "skipped"
            continue
        # a run that could not start after its checks does not pay for them (Sentinel S3-4 / Chris R3-2)
        if ctx.deadline - time.monotonic() - POST_RUN_RESERVE_S < MIN_RUN_S:
            result.update(status="skipped", reason="budget-exhausted")
            statuses[rid], stop_reason = "skipped", "budget-exhausted"
            continue
        ctx.current = result
        item["stage"] = _stage_dir(ctx.private, ctx.run_dir, rid)
        os.makedirs(item["stage"], mode=0o700, exist_ok=True)
        try:
            # E0 first, before this run's first `git status` (erratum-2 §1.9, SAC-26; Chris C13-1)
            e0, ctx.gitlinks = _e0_check(ctx.git, ctx.root, ctx.common_dir)
            if e0:
                raise Blocked("design-run-untrusted-input", "; ".join(e0))
            # then walk signature and snapshot: an edit after them is either refused by the check
            # below or differs from them after the run (Sentinel W12 S3-2)
            before_walk = (_walk_sig(ctx.root, _e3_matches(item["tpl"], item["spec"], ctx.root,
                                                            _e3_candidate_files(ctx)))
                           if item["tpl"].get("e3") is not None else None)
            before = _snapshot(ctx)
            _tree_check(ctx, [item], created)
            argv = _build_argv(item, ctx)
            failure = None
        except Blocked as b:
            failure = _r(b.token + " " + b.detail)
        except OSError as exc:  # an earlier child may have left the tree unreadable (Sentinel S13b-1)
            failure = _os_failure(exc, ctx.root)
        if failure:
            result.update(status="tree-changed", reason=failure)
            statuses[rid], stop_reason = "failed", "tree-changed"
            ctx.current = None
            continue
        # the budget left is read here, after the pre-run checks (Sentinel S2-3 / Chris N-1)
        left = ctx.deadline - time.monotonic() - POST_RUN_RESERVE_S
        if left < MIN_RUN_S:
            result.update(status="skipped", reason="budget-exhausted")
            statuses[rid], stop_reason = "skipped", "budget-exhausted"
            ctx.current = None
            continue
        _record_argv(result, item, argv)
        timeout = min(item["tpl"]["timeout_s"], left)
        result["timeout_s"] = round(timeout, 3)
        raw = (os.path.join(ctx.private, rid + ".stdout"), os.path.join(ctx.private, rid + ".stderr"))
        result["start"] = _now()
        ctx.children_started += 1
        with open(raw[0], "wb") as of, open(raw[1], "wb") as ef:
            status, code = _spawn_child(argv, ctx.root, child_env, of, ef, timeout)
        result["end"] = _now()
        result["status"], result["exit_code"] = status, code
        changed = _post_run(ctx, item, result, before, created, raw, before_walk)
        ctx.current = None
        if changed:
            statuses[rid], stop_reason = "failed", "tree-changed"
            continue
        statuses[rid] = "ok" if status == "exit" and code == 0 else "failed"
    return results


# ----------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------

class Ctx:
    """Run state shared by the steps; every field the report reads exists from the start."""

    def __init__(self):
        self.deadline = time.monotonic() + RUN_BUDGET_S
        self.root = self.git = self.git_dir = self.common_dir = None
        self.catalogue, self.catalogue_sha = None, None
        self.git_version = self.config_scan = None
        self.deny_records = frozenset()
        self.path_entries, self.gitlinks, self.flag_results, self.tree_records = [], [], [], []
        self.order, self.order_rel, self.order_sha, self.request_sha = None, None, None, None
        self.change_paths = []
        self.run_dir = self.report_path = self.report_fd = self.private = None
        self.results, self.children_started, self.signal = [], 0, None
        self.current, self.exit_written, self.old_handlers = None, None, {}


def _hex64(value):
    if not SHA_RE.fullmatch(value.lower()):
        raise argparse.ArgumentTypeError("expected 64 hex characters")
    return value.lower()


def _parser():
    p = argparse.ArgumentParser(prog="design_run.py", description="Run a pinned design-run order.")
    p.add_argument("--order", required=True, help="outputs/<task>/<NN>-design-run-order-<phase>-iter<n>.json")
    p.add_argument("--sha256", required=True, type=_hex64, help="sha256 of the order file, from the router")
    return p


def _load_catalogue():
    raw = CATALOGUE_PATH.read_bytes()
    return json.loads(raw.decode("utf-8")), _sha256(raw)


def _param_kind_ok(kind):
    if isinstance(kind, str):
        return kind in CAT_PARAM_KINDS
    if isinstance(kind, dict) and set(kind) == {"int_range"}:
        r = kind["int_range"]
        return isinstance(r, list) and len(r) == 2 and all(type(x) is int for x in r) and r[0] <= r[1]
    if isinstance(kind, dict) and set(kind) == {"enum"}:
        return isinstance(kind["enum"], list) and kind["enum"] and all(isinstance(x, str) for x in kind["enum"])
    return False


def _str_list(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


CAT_WRITE_RE = re.compile(r"[a-z0-9._{}-]+(?:/[a-z0-9._{}-]+)*/\*\*")
CAT_ARTIFACT_RE = re.compile(r"<run-id>\.(?:png|axe\.json|json|txt|log)")
CAT_SPEC_RE = re.compile(r"tests/[a-z0-9_-]+/\{feature\}\.spec\.ts")
CAT_NAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,40}")
# executes kinds a template must list when it gets a given E3 kind / runs a given binary
E3_EXECUTES = {"spec": {"spec", "playwright-config", "package-json", "lockfiles"},
               "default-pattern": {"tracked-specs", "playwright-config", "package-json", "lockfiles"}}
# a param with this name must have this kind (a weaker kind would switch a check off)
PARAM_NAME_KINDS = {"feature": "slug", "url": "url"}
# Sentinel W12 S3-5: valid values that would still narrow a check
CAT_BINS = ("playwright", "axe")                        # project binaries the rules are written for
CAT_PLAYWRIGHT_COMMANDS = ("test", "screenshot")        # argv[0] of a Playwright run
CAT_FIXED_WRITES = ("design-system/**", "test-results/**", "playwright-report/**")
# Sentinel S13-2: Playwright argv is an allowlist of the element forms the shipped templates use;
# any other flag (attached `-c<p>`, `-xc<p>`, `--reporter=<p>`, `--tsconfig`, `--test-list`, ...)
# or a second positional is refused, because Playwright loads code or widens its file set from them
CAT_PW_SNAPSHOTS_NONE = "--update-snapshots=none"
# `-u, --update-snapshots [mode]` takes an optional argument, so the bare flag only as the last element
CAT_PW_SNAPSHOTS_BARE = "--update-snapshots"
CAT_PW_GREP_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.]{0,63}")           # a literal, never a placeholder
CAT_PW_VIEWPORT_RE = re.compile(r"--viewport-size=\{[a-z_]+\},\{[a-z_]+\}")
CAT_PW_SCREENSHOT_TAIL = ["{url}", "<out>/<run-id>.png"]
# Sentinel S13b-3: `axe` argv is exactly the shipped form; `--chromedriver-path` / `--chrome-path`
# name executables the CLI launches and `--axe-source` a script it loads. @axe-core/cli 4.13.0 saves
# to path.join(--dir or cwd, --save): `--save` must be a bare name and the stage dir goes in `--dir`
AXE_SAVE_NAME = "<run-id>.axe.json"
CAT_AXE_ARGV = ["{url}", "--dir", "<out>/", "--save", AXE_SAVE_NAME]


def _writes_ok(t):
    """`writes` may name only the fixed output trees and the spec's own snapshot directory:
    `writes` also exempts modified tracked files, so anything wider hides source or spec edits."""
    own = (t["spec"] + "-snapshots/**",) if isinstance(t.get("spec"), str) else ()
    return all(w in CAT_FIXED_WRITES + own and CAT_WRITE_RE.fullmatch(w) and _rel_segments_ok(w)
               for w in t["writes"])


def _pw_test_args_ok(args):
    """`test`: at most one `<spec-filter>`, `--update-snapshots=none`, a bare `--update-snapshots`
    as the last element only (Chris C13b-1), and `--grep <literal>`."""
    i, positionals = 0, 0
    while i < len(args):
        a = args[i]
        if a == "<spec-filter>":
            positionals += 1
        elif a == "--grep" and i + 1 < len(args) and CAT_PW_GREP_RE.fullmatch(args[i + 1]):
            i += 1
        elif not (a == CAT_PW_SNAPSHOTS_NONE or (a == CAT_PW_SNAPSHOTS_BARE and i == len(args) - 1)):
            return False
        i += 1
    return positionals <= 1


def _pw_screenshot_args_ok(args):
    """`screenshot`: an optional viewport flag, then exactly `{url}` and `<out>/<run-id>.png`."""
    head = args[:-len(CAT_PW_SCREENSHOT_TAIL)]
    return (args[-len(CAT_PW_SCREENSHOT_TAIL):] == CAT_PW_SCREENSHOT_TAIL and len(head) <= 1
            and all(CAT_PW_VIEWPORT_RE.fullmatch(a) for a in head))


def _playwright_argv_ok(t):
    if t.get("bin") != "playwright":
        return True
    argv = t["argv"]
    if not argv or argv[0] not in CAT_PLAYWRIGHT_COMMANDS:
        return False
    return _pw_test_args_ok(argv[1:]) if argv[0] == "test" else _pw_screenshot_args_ok(argv[1:])


def _axe_argv_ok(t):
    return t.get("bin") != "axe" or t["argv"] == CAT_AXE_ARGV


def _rel_segments_ok(path):
    return not path.startswith("/") and all(seg not in ("", ".", "..") for seg in path.split("/"))


def _semantics_ok(t):
    """Values that are well-formed but would switch a required check off (Sentinel W12 S2-7)."""
    playwright_test = (t["runner"] == "project-bin" and t.get("bin") == "playwright"
                       and t["argv"][:1] == ["test"])
    executes = set(t["executes"])
    refs = set(re.findall(r"<run-json:([a-z_]+)>", " ".join(t["argv"])))
    return (
        ("e3", not playwright_test or t["e3"] is not None),
        # E3 kind `spec` covers only the named spec, so it is right exactly when argv filters to it
        ("e3", (t["e3"] == "spec") == ("<spec-filter>" in t["argv"])),
        ("bin", t["runner"] != "project-bin" or t["bin"] in CAT_BINS),
        ("argv", _playwright_argv_ok(t) and _axe_argv_ok(t)),
        ("executes", t["e3"] is None or E3_EXECUTES[t["e3"]] <= executes),
        ("executes", t["runner"] != "project-bin" or {"package-json", "lockfiles"} <= executes),
        ("executes", t.get("bin") != "playwright" or "playwright-config" in executes),
        ("params", all(t["params"].get(n, kind) == kind for n, kind in PARAM_NAME_KINDS.items())),
        ("params", all(t["params"].get(r) == "run_ref" for r in refs)),
        ("network", (t["network"] == "url") == any(k == "url" for k in t["params"].values())),
        ("writes", _writes_ok(t)),
        ("artifacts", all(CAT_ARTIFACT_RE.fullmatch(a) for a in t["artifacts"])),
        ("spec", "spec" not in t or (CAT_SPEC_RE.fullmatch(t["spec"]) is not None and t["e3"] == "spec")),
        ("script", t["runner"] != "plugin-python" or CAT_NAME_RE.fullmatch(t["script"]) is not None),
        ("bin", t["runner"] != "project-bin" or CAT_NAME_RE.fullmatch(t["bin"]) is not None),
    )


def _validate_template(name, t):
    """One field name per failure; an unknown value never switches a check off (Chris W12 S-4),
    and neither does a known value on a template that needs the check (Sentinel W12 S2-7)."""
    if not isinstance(t, dict) or not CAT_TEMPLATE_KEYS <= set(t) or set(t) - CAT_TEMPLATE_KEYS - CAT_OPTIONAL_KEYS:
        return "keys"
    checks = (
        ("runner", t["runner"] in CAT_RUNNERS),
        ("phases", _str_list(t["phases"]) and t["phases"] and set(t["phases"]) <= set(CAT_PHASES)),
        ("executes", _str_list(t["executes"]) and set(t["executes"]) <= set(CAT_EXECUTES)),
        ("e3", t["e3"] in CAT_E3 and (t["e3"] != "spec" or isinstance(t.get("spec"), str))),
        ("network", t["network"] in CAT_NETWORK),
        ("stdout_json", type(t["stdout_json"]) is bool),
        ("timeout_s", type(t["timeout_s"]) is int and 1 <= t["timeout_s"] <= MAX_TEMPLATE_TIMEOUT_S),
        ("argv", _str_list(t["argv"])),
        ("writes", _str_list(t["writes"])),
        ("artifacts", _str_list(t["artifacts"])),
        ("params", isinstance(t["params"], dict) and all(_param_kind_ok(k) for k in t["params"].values())),
        ("script", t["runner"] != "plugin-python" or isinstance(t.get("script"), str)),
        ("bin", t["runner"] != "project-bin" or isinstance(t.get("bin"), str)),
        ("spec", "spec" not in t or (isinstance(t["spec"], str) and "feature" in t["params"])),
    )
    field = next((field for field, ok in checks if not ok), None)
    return field or next((field for field, ok in _semantics_ok(t) if not ok), None)


def _validate_catalogue(cat):
    if (not isinstance(cat, dict) or set(cat) != {"schema", "max_runs", "templates"}
            or type(cat["schema"]) is not int or cat["schema"] != 1):
        raise Blocked("design-run-schema", "catalogue top-level")
    if type(cat["max_runs"]) is not int or not 1 <= cat["max_runs"] <= 8:
        raise Blocked("design-run-schema", "catalogue max_runs")
    if not isinstance(cat["templates"], dict) or not cat["templates"]:
        raise Blocked("design-run-schema", "catalogue templates")
    for name in sorted(cat["templates"]):
        field = _validate_template(name, cat["templates"][name])
        if field:
            raise Blocked("design-run-schema", "catalogue %s %s" % (_show(name), field))


def _prepare(args, ctx):
    """Steps 0-8. Raises Blocked on any failure."""
    # step 0
    ctx.root = os.path.realpath(os.getcwd())
    if not _is_isolated() or _inside(os.path.realpath(sys.executable), ctx.root):
        raise Blocked("design-run-untrusted-input", "interpreter")
    ctx.path_entries = _sanitise_path(os.environ.get("PATH", ""), ctx.root)
    git_exe = _resolve_tool("git", ctx.path_entries, ctx.root)
    if git_exe is None:
        raise Blocked("design-run-untrusted-input", "no-git")
    ctx.git = Git(git_exe, _env_from(GIT_ENV_NAMES, ctx.path_entries), ctx.root)
    ctx.catalogue, ctx.catalogue_sha = _load_catalogue()
    _validate_catalogue(ctx.catalogue)
    # step 0a, 1, 2
    ctx.git_version = ctx.git.version()
    ctx.config_scan, ctx.git_dir, ctx.common_dir, ctx.deny_records = _config_scan(ctx.git, ctx.root)
    top = ctx.git.run(["rev-parse", "--show-toplevel"], ok=None)
    if top.returncode != 0:
        raise Blocked("design-run-untrusted-input", "no-git")
    if os.path.realpath(os.fsdecode(top.stdout).strip()) != ctx.root:
        raise Blocked("design-run-untrusted-input", "cwd")
    # step 2a
    e0, ctx.gitlinks = _e0_check(ctx.git, ctx.root, ctx.common_dir)
    if e0:
        raise Blocked("design-run-untrusted-input", "; ".join(e0))
    # step 3, 4
    m = ORDER_PATH_RE.fullmatch(args.order)
    if not m or ".." in m.group("task"):
        raise Blocked("design-run-schema", "order-path")
    ctx.order_rel = args.order
    ctx.order, ctx.order_sha = _read_pinned(ctx.root, args.order, args.sha256, "order", "design-run-order-hash")
    _validate_order(ctx.order, m.groupdict())
    ctx.change_paths = list(ctx.order["change_paths"])
    req, ctx.request_sha = _read_pinned(ctx.root, ctx.order["request_path"], ctx.order["request_sha256"],
                                        "request", "design-run-request-hash")
    # step 5
    runs = _validate_request(req, ctx.order, ctx.catalogue)
    # step 6
    plan = []
    for run in runs:
        tpl = ctx.catalogue["templates"][run["script_id"]]
        item = {"id": run["id"], "script_id": run["script_id"], "tpl": tpl, "params": run["params"],
                "spec": tpl["spec"].replace("{feature}", run["params"]["feature"]) if tpl.get("spec") else None}
        if tpl["runner"] == "project-bin":
            item["exe"] = _resolve_bin(tpl["bin"], ctx.root)
            if _resolve_tool("node", ctx.path_entries, ctx.root) is None:
                raise Blocked("design-run-tool-missing", "node (%s)" % (DEVOPS_HINT % "node"))
        else:
            script = (SCRIPTS_DIR / tpl["script"]).resolve()
            if script.parent != SCRIPTS_DIR.resolve() or not script.is_file():
                raise Blocked("design-run-tool-missing", tpl["script"])
        plan.append(item)
    # step 7
    ctx.tree_records = _tree_check(ctx, plan)
    # step 8
    _prepare_outputs(ctx, args)
    return plan


def _prepare_outputs(ctx, args):
    """Step 8. The private dir comes first, so a failure there leaves no report or run dir that
    would block a retry (Chris W12 L-1); the report file is the last thing created."""
    ctx.private = _private_dir(ctx.root)
    stem = os.path.basename(args.order)[:-len(".json")]
    base = os.path.join(ctx.root, "outputs", ctx.order["task"], "design-run")
    cur = ctx.root
    for seg in ("outputs", ctx.order["task"], "design-run"):
        cur = os.path.join(cur, seg)
        st = _lstat(cur)
        if st is None:
            os.mkdir(cur)
        elif not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise Blocked("design-run-untrusted-input", "%s (symlink)" % os.path.relpath(cur, ctx.root))
    run_dir = os.path.join(base, stem)
    report_path = os.path.join(base, stem + ".report.json")
    if _lstat(report_path) is not None:
        raise Blocked("design-run-output-exists", os.path.relpath(report_path, ctx.root))
    try:
        os.mkdir(run_dir)
    except FileExistsError:
        raise Blocked("design-run-output-exists", os.path.relpath(run_dir, ctx.root))
    try:
        ctx.report_fd = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except FileExistsError:
        os.rmdir(run_dir)
        raise Blocked("design-run-output-exists", os.path.relpath(report_path, ctx.root))
    ctx.run_dir, ctx.report_path = run_dir, report_path


def _resolve_bin(name, root):
    link = os.path.join(root, "node_modules", ".bin", name)
    if _lstat(link) is None:
        raise Blocked("design-run-tool-missing", "%s (%s)" % (name, DEVOPS_HINT % name))
    real = os.path.realpath(link)
    nm = os.path.realpath(os.path.join(root, "node_modules"))
    st = _lstat(real)
    if (not _inside(real, nm) or st is None or not stat.S_ISREG(st.st_mode) or not os.access(real, os.X_OK)):
        raise Blocked("design-run-tool-unsafe", name)
    return real


def _redact_fields(record, names):
    """A copy of a report record whose host- or project-chosen string fields went through
    _redact_value."""
    return dict(record, **{k: _redact_value(record[k]) for k in names if isinstance(record.get(k), str)})


def _report(ctx, runs, code, error=None):
    """Every host- or project-chosen string the report carries goes through _redact_value (Bella
    L-2, SAC-27), except the router-chosen task id in `order.path`, `request.path`, `run_dir` and
    the stream and artifact paths, which the executor must open as written (R64; TASK_RE, and a
    token-shaped id is refused at step 3); the run's own argv, reasons and names were redacted
    where they were made."""
    scan = ctx.config_scan
    if scan is not None:
        # base redaction first, then the any-case AKIA/ASIA pass (Sentinel S31-1)
        scan = dict(scan, deny_set_keys=[dict(r, key=_redact_aws_id_any_case(r["key"])) for r in
                                         (_redact_fields(k, ("key", "origin")) for k in scan["deny_set_keys"])])
    return {
        "runner": {"version": RUNNER_VERSION, "catalogue_sha256": ctx.catalogue_sha,
                   "python": {"executable": _redact_value(sys.executable),
                              "realpath": _redact_value(os.path.realpath(sys.executable))}},
        "order": {"path": ctx.order_rel, "sha256": ctx.order_sha},
        "request": {"path": ctx.order.get("request_path") if ctx.order else None, "sha256": ctx.request_sha},
        "path_sanitised": [_redact_value(p) for p in ctx.path_entries],
        "git": {"path": _redact_value(ctx.git.exe) if ctx.git else None,
                "version": _redact_value(ctx.git_version) if ctx.git_version else ctx.git_version,
                "config_scan": scan, "gitlinks": [_redact_fields(g, ("path",)) for g in ctx.gitlinks],
                "index_flags": [_redact_fields(f, ("path",)) for f in ctx.flag_results]},
        "tree_check": [_redact_fields(t, ("path", "source")) for t in ctx.tree_records],
        "run_dir": os.path.relpath(ctx.run_dir, ctx.root) if ctx.run_dir else None,
        "runs": [_redact_fields(r, ("cwd", "executable")) for r in runs], "exit": code, "error": error,
    }


CLEANUP_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


def _mask_signals(old):
    """Ignore TERM/HUP/INT for the cleanup (Sentinel S2-5 / Chris N-4); every handler replaced here
    is recorded in `old` (unless already recorded) so _restore_signal_handlers puts it back."""
    for sig in CLEANUP_SIGNALS:
        try:
            previous = signal.signal(sig, signal.SIG_IGN)
        except ValueError:  # not the main thread
            continue
        old.setdefault(sig, previous)


def _write_report(ctx, code, error=None):
    """Write the report once (its fd is open from step 8 on) and print the report line. Signals are
    masked first, so the exit code returned always equals the one in the report."""
    _mask_signals(ctx.old_handlers)
    fd, ctx.report_fd = ctx.report_fd, None
    try:
        os.write(fd, json.dumps(_report(ctx, ctx.results, code, error), indent=2, ensure_ascii=True).encode() + b"\n")
    finally:
        os.close(fd)
    ctx.exit_written = code
    sys.stdout.write("design-run: report=%s exit=%d\n" % (os.path.relpath(ctx.report_path, ctx.root), code))
    return code


def _install_signal_handlers(ctx):
    """The first SIGTERM/SIGHUP/SIGINT raises SystemExit so every `finally` runs (child group
    killed, report written, private dir removed); the handler masks TERM/HUP/INT before raising,
    so a second delivery cannot interrupt that cleanup (Sentinel W12 S3-3: SIGINT included). A
    SIGINT already ignored at start stays ignored, as CPython itself does. Returns the previous
    handlers for restore."""
    old = {}

    def handler(signum, _frame):
        _mask_signals(old)
        ctx.signal = signal.Signals(signum).name
        raise SystemExit(EXIT_RUN_FAILED)

    for sig in CLEANUP_SIGNALS:
        if sig == signal.SIGINT and signal.getsignal(sig) == signal.SIG_IGN:
            continue
        try:
            old[sig] = signal.signal(sig, handler)
        except ValueError:  # not the main thread: keep the default action
            pass
    return old


def _restore_signal_handlers(old):
    for sig, previous in old.items():
        signal.signal(sig, previous)


def _show_exception_filenames(exc):
    """OSError.__str__ prints `filename` / `filename2` as a repr, whose escapes (`\\n`, `\\x1b`)
    defeat redaction; replace them in the whole chain with their _show form before the traceback
    is formatted (Sentinel S13b-1)."""
    stack, seen = [exc], set()
    while stack:
        e = stack.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        if isinstance(e, OSError):
            for attr in ("filename", "filename2"):
                value = getattr(e, attr, None)
                if isinstance(value, (str, bytes)):
                    setattr(e, attr, _show(os.fsdecode(value)))
        stack += [e.__cause__, e.__context__]


def _remove_private(path):
    """Remove the private directory, and say so on stderr when it could not be (Chris C24-5).

    A child can take the permissions off a directory it made in there, which would keep rmtree
    from removing the raw streams (Sentinel S16-I3), so owner rwx is put back on every directory
    first (bounded like the E3 walk; a symlink is never descended). The child runs as the same
    user, so a race gains it nothing it could not do itself: a symlink it swaps in between the
    lstat and the chmod makes the runner set that directory's pre-swap mode plus owner rwx on the
    link's same-uid target, and the walk may then continue below that target (chmod only; the
    removal never follows a link) (Sentinel S24-5). A tree nested deeper than shutil.rmtree's
    recursion (or open-fd) limit is flattened first and removed again (Sentinel S24-6)."""
    stack, count = [path], 0
    while stack and count < WALK_MAX_ENTRIES:
        count += 1
        d = stack.pop()
        try:
            st = os.lstat(d)
            if not stat.S_ISDIR(st.st_mode):
                continue
            os.chmod(d, stat.S_IMODE(st.st_mode) | stat.S_IRWXU)
            with os.scandir(d) as it:
                stack += [e.path for e in it if e.is_dir(follow_symlinks=False)]
        except OSError:
            continue
    _rmtree_quiet(path)
    if os.path.lexists(path):
        _flatten(path)
        _rmtree_quiet(path)
    if os.path.lexists(path):
        sys.stderr.write("design-run: private dir not removed: %s\n" % _show(path))


def _rmtree_quiet(path):
    """shutil.rmtree, errors ignored; a RecursionError on a deeply nested tree is caught too, since
    ignore_errors does not cover it (Sentinel S24-6)."""
    try:
        shutil.rmtree(path, ignore_errors=True)
    except RecursionError:
        pass


def _flatten(path):
    """Move every directory below `path` up into `path` before emptying it, so the tree left is at
    most one level deep. Every step is relative to an open directory fd and never follows a link
    (O_NOFOLLOW open, renameat, unlinkat), a constant number of directory fds is open at a time
    (two, plus scandir's dups), and it is bounded like the E3 walk. Errors leave the rest for the caller's check."""
    try:
        top = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return
    prefix = ".design-run-flat-%s-" % os.urandom(6).hex()
    seq, count = 0, 0
    try:
        with os.scandir(top) as it:
            stack = [e.name for e in it]
        while stack and count < WALK_MAX_ENTRIES:
            count += 1
            name = stack.pop()
            try:
                st = os.stat(name, dir_fd=top, follow_symlinks=False)
                if not stat.S_ISDIR(st.st_mode):
                    os.unlink(name, dir_fd=top)
                    continue
                _owner_rwx(name, st, top)
                fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=top)
                try:
                    with os.scandir(fd) as it:
                        entries = [(e.name, e.stat(follow_symlinks=False)) for e in it]
                    for child, child_st in entries:
                        if stat.S_ISDIR(child_st.st_mode):
                            seq += 1
                            _owner_rwx(child, child_st, fd)     # moving a directory may need its w bit
                            os.rename(child, prefix + str(seq), src_dir_fd=fd, dst_dir_fd=top)
                            stack.append(prefix + str(seq))
                        else:
                            os.unlink(child, dir_fd=fd)
                finally:
                    os.close(fd)
                os.rmdir(name, dir_fd=top)
            except OSError:
                continue
    finally:
        os.close(top)


def _owner_rwx(name, st, dir_fd):
    """Owner rwx on the directory `name` under dir_fd, without following a link where the platform
    allows it (elsewhere the S24-5 race in _remove_private applies)."""
    os.chmod(name, stat.S_IMODE(st.st_mode) | stat.S_IRWXU, dir_fd=dir_fd,
             follow_symlinks=os.chmod not in os.supports_follow_symlinks)


def _mark_terminated(ctx, name):
    """The run that was in progress when the signal arrived gets an explicit status."""
    if ctx.current is not None:
        ctx.current.update(status="terminated", reason="terminated (%s)" % name)
        ctx.current = None


def main(argv=None):
    args = _parser().parse_args(argv)
    ctx = Ctx()
    ctx.old_handlers = old_handlers = _install_signal_handlers(ctx)
    try:
        # the signal clause is outside this inner try, so a signal that lands inside one of its
        # except clauses is handled the same way as one in the body (Chris W12 R3-1)
        try:
            plan = _prepare(args, ctx)
            runs = _execute(ctx, plan)
            ok = all(r["status"] == "exit" and r["exit_code"] == 0 for r in runs)
            return _write_report(ctx, EXIT_OK if ok else EXIT_RUN_FAILED)
        except Blocked as b:
            detail = _r(b.detail)
            if ctx.report_fd is not None:
                # every Blocked after step 8 is caught per run; once the report is open the outcome
                # is recorded there with exit 1, never exit 3 (Chris W12 S-1, N-2)
                return _write_report(ctx, EXIT_RUN_FAILED, "BLOCKED: %s %s" % (b.token, detail))
            sys.stderr.write("BLOCKED: %s%s\n" % (b.token, " " + detail if detail else ""))
            return EXIT_BLOCKED
        except Exception as exc:  # noqa: BLE001 -- exit 4 records any unexpected failure, redacted
            _show_exception_filenames(exc)
            tb = _redact_escaped(traceback.format_exc())[0]
            if ctx.report_fd is not None:
                return _write_report(ctx, EXIT_INTERNAL, tb)
            sys.stderr.write(tb)
            return EXIT_INTERNAL
    except (SystemExit, KeyboardInterrupt):
        _mask_signals(old_handlers)
        name = ctx.signal or "SIGINT"
        if ctx.exit_written is not None:  # the report was already written: keep its exit code
            return ctx.exit_written
        _mark_terminated(ctx, name)
        if ctx.report_fd is not None:
            return _write_report(ctx, EXIT_RUN_FAILED, "terminated (%s)" % name)
        sys.stderr.write("design-run: terminated (%s)\n" % name)
        return EXIT_INTERNAL
    finally:
        _mask_signals(old_handlers)
        if ctx.report_fd is not None:
            os.close(ctx.report_fd)
        if ctx.private:
            _remove_private(ctx.private)
        _restore_signal_handlers(old_handlers)


if __name__ == "__main__":
    sys.exit(main())
